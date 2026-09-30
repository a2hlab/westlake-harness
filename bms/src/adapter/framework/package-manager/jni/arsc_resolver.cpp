/*
 * arsc_resolver.cpp
 *
 * Minimal Android resources.arsc (ResTable) resolver — see arsc_resolver.h.
 *
 * Format reference:
 *   AOSP frameworks/base/libs/androidfw/include/androidfw/ResourceTypes.h
 *
 * The algorithm (resId -> best raster file path) was validated against the
 * deployed framework-res.apk: 0x0108009b resolves to
 * res/drawable-xhdpi-v4/ic_dialog_info.png, matching what stock Android shows.
 *
 * We parse only what is needed to turn a resource ID into a file-path string:
 *   1. the global value string pool (holds "res/.../foo.png" path strings),
 *   2. every ResTable_package chunk whose id matches the target package,
 *   3. within those, every ResTable_type chunk whose type id matches, decoding
 *      the entry offset for the target index under whichever offset encoding
 *      (sparse / offset16 / dense) the chunk uses,
 *   4. the entry's Res_value; when it is a string, its data indexes the global
 *      string pool to give the file path.
 *
 * All reads are bounds-checked because this runs inside the BMS/installd
 * process during install; a malformed arsc must fail gracefully, never crash.
 */
#include "arsc_resolver.h"

#include <cstring>
#include <algorithm>
#include <vector>

#include <unzip.h>  // minizip
#include "hilog/log.h"

#undef LOG_DOMAIN
#undef LOG_TAG
#define LOG_DOMAIN 0xD001802
#define LOG_TAG "OH_ArscResolver"
#define ARSC_LOGI(...) OHOS::HiviewDFX::HiLog::Info({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)
#define ARSC_LOGW(...) OHOS::HiviewDFX::HiLog::Warn({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)
#define ARSC_LOGE(...) OHOS::HiviewDFX::HiLog::Error({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)

namespace oh_adapter {
namespace {

// ResChunk_header types.
constexpr uint16_t RES_STRING_POOL_TYPE   = 0x0001;
constexpr uint16_t RES_TABLE_TYPE         = 0x0002;
constexpr uint16_t RES_TABLE_PACKAGE_TYPE = 0x0200;
constexpr uint16_t RES_TABLE_TYPE_TYPE    = 0x0201;

constexpr uint32_t STRING_POOL_UTF8_FLAG  = 1u << 8;

// ResTable_type.flags
constexpr uint8_t  TYPE_FLAG_SPARSE       = 0x01;
constexpr uint8_t  TYPE_FLAG_OFFSET16     = 0x02;

// ResTable_entry.flags
constexpr uint16_t ENTRY_FLAG_COMPLEX     = 0x0001;

// Res_value.dataType
constexpr uint8_t  RES_VALUE_TYPE_STRING  = 0x03;
constexpr uint8_t  RES_VALUE_TYPE_REFERENCE = 0x01;

constexpr uint32_t NO_ENTRY_32 = 0xffffffffu;
constexpr uint16_t NO_ENTRY_16 = 0xffffu;

// Bounds-checked little-endian readers over a byte buffer.
class Reader {
public:
    Reader(const uint8_t* p, size_t n) : data_(p), size_(n) {}
    bool u8(size_t o, uint8_t& v) const {
        if (o + 1 > size_) return false;
        v = data_[o];
        return true;
    }
    bool u16(size_t o, uint16_t& v) const {
        if (o + 2 > size_) return false;
        std::memcpy(&v, data_ + o, 2);
        return true;
    }
    bool u32(size_t o, uint32_t& v) const {
        if (o + 4 > size_) return false;
        std::memcpy(&v, data_ + o, 4);
        return true;
    }
    const uint8_t* at(size_t o) const { return data_ + o; }
    size_t size() const { return size_; }
private:
    const uint8_t* data_;
    size_t size_;
};

// Read a single string at `index` from a ResStringPool chunk located at
// `poolOff`. Returns false if out of range. Decodes both UTF-8 and UTF-16.
bool ReadPoolString(const Reader& r, size_t poolOff, uint32_t index, std::string& out) {
    uint32_t count = 0, flags = 0, strStart = 0;
    if (!r.u32(poolOff + 8, count) || !r.u32(poolOff + 16, flags) ||
        !r.u32(poolOff + 20, strStart)) {
        return false;
    }
    if (index >= count) return false;
    uint32_t entryOff = 0;
    if (!r.u32(poolOff + 28 + 4 * index, entryOff)) return false;
    size_t p = poolOff + strStart + entryOff;
    const bool utf8 = (flags & STRING_POOL_UTF8_FLAG) != 0;
    if (utf8) {
        // UTF-8: u8/u16 char count, then u8/u16 byte length, then bytes.
        uint8_t b = 0;
        if (!r.u8(p, b)) return false;
        p += 1;
        if (b & 0x80) { p += 1; }  // 2-byte char count
        uint8_t bl0 = 0;
        if (!r.u8(p, bl0)) return false;
        p += 1;
        uint32_t byteLen = bl0;
        if (bl0 & 0x80) {
            uint8_t bl1 = 0;
            if (!r.u8(p, bl1)) return false;
            byteLen = ((static_cast<uint32_t>(bl0) & 0x7f) << 8) | bl1;
            p += 1;
        }
        if (p + byteLen > r.size()) return false;
        out.assign(reinterpret_cast<const char*>(r.at(p)), byteLen);
        return true;
    }
    // UTF-16: u16/u32 char count, then char count * 2 bytes.
    uint16_t l0 = 0;
    if (!r.u16(p, l0)) return false;
    p += 2;
    uint32_t charLen = l0;
    if (l0 & 0x8000) {
        uint16_t l1 = 0;
        if (!r.u16(p, l1)) return false;
        charLen = ((static_cast<uint32_t>(l0) & 0x7fff) << 16) | l1;
        p += 2;
    }
    if (p + static_cast<size_t>(charLen) * 2 > r.size()) return false;
    out.clear();
    out.reserve(charLen);
    for (uint32_t i = 0; i < charLen; ++i) {
        uint16_t c = 0;
        if (!r.u16(p + 2 * i, c)) return false;
        // Resource paths are ASCII; narrow the BMP code unit. Non-ASCII (rare
        // in res paths) degrades to a low byte, which is acceptable here.
        out.push_back(static_cast<char>(c & 0xff));
    }
    return true;
}

// Append a Unicode code point to `out` as UTF-8.
void AppendUtf8(std::string& out, uint32_t cp) {
    if (cp < 0x80) {
        out.push_back(static_cast<char>(cp));
    } else if (cp < 0x800) {
        out.push_back(static_cast<char>(0xc0 | (cp >> 6)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3f)));
    } else if (cp < 0x10000) {
        out.push_back(static_cast<char>(0xe0 | (cp >> 12)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3f)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3f)));
    } else {
        out.push_back(static_cast<char>(0xf0 | (cp >> 18)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 12) & 0x3f)));
        out.push_back(static_cast<char>(0x80 | ((cp >> 6) & 0x3f)));
        out.push_back(static_cast<char>(0x80 | (cp & 0x3f)));
    }
}

// Same layout as ReadPoolString but decodes UTF-16 pools to real UTF-8
// (including surrogate pairs). Labels are user-visible and frequently
// non-ASCII, so the ASCII-narrowing in ReadPoolString is not acceptable here.
bool ReadPoolStringUtf8(const Reader& r, size_t poolOff, uint32_t index, std::string& out) {
    uint32_t count = 0, flags = 0, strStart = 0;
    if (!r.u32(poolOff + 8, count) || !r.u32(poolOff + 16, flags) ||
        !r.u32(poolOff + 20, strStart)) {
        return false;
    }
    if (index >= count) return false;
    uint32_t entryOff = 0;
    if (!r.u32(poolOff + 28 + 4 * index, entryOff)) return false;
    size_t p = poolOff + strStart + entryOff;
    const bool utf8 = (flags & STRING_POOL_UTF8_FLAG) != 0;
    if (utf8) {
        uint8_t b = 0;
        if (!r.u8(p, b)) return false;
        p += 1;
        if (b & 0x80) { p += 1; }  // 2-byte char count
        uint8_t bl0 = 0;
        if (!r.u8(p, bl0)) return false;
        p += 1;
        uint32_t byteLen = bl0;
        if (bl0 & 0x80) {
            uint8_t bl1 = 0;
            if (!r.u8(p, bl1)) return false;
            byteLen = ((static_cast<uint32_t>(bl0) & 0x7f) << 8) | bl1;
            p += 1;
        }
        if (p + byteLen > r.size()) return false;
        out.assign(reinterpret_cast<const char*>(r.at(p)), byteLen);
        return true;
    }
    // UTF-16: u16/u32 char count, then char count * 2 bytes.
    uint16_t l0 = 0;
    if (!r.u16(p, l0)) return false;
    p += 2;
    uint32_t charLen = l0;
    if (l0 & 0x8000) {
        uint16_t l1 = 0;
        if (!r.u16(p, l1)) return false;
        charLen = ((static_cast<uint32_t>(l0) & 0x7fff) << 16) | l1;
        p += 2;
    }
    if (p + static_cast<size_t>(charLen) * 2 > r.size()) return false;
    out.clear();
    out.reserve(charLen * 2);
    for (uint32_t i = 0; i < charLen; ++i) {
        uint16_t c = 0;
        if (!r.u16(p + 2 * i, c)) return false;
        if (c >= 0xd800 && c <= 0xdbff && i + 1 < charLen) {
            uint16_t lo = 0;
            if (!r.u16(p + 2 * (i + 1), lo)) return false;
            if (lo >= 0xdc00 && lo <= 0xdfff) {
                AppendUtf8(out, 0x10000u +
                    ((static_cast<uint32_t>(c) - 0xd800u) << 10) +
                    (static_cast<uint32_t>(lo) - 0xdc00u));
                ++i;
                continue;
            }
        }
        AppendUtf8(out, c);
    }
    return true;
}

// A ResTable_type chunk is the "default" configuration for label purposes when
// its ResTable_config locale field is zero (no language/country qualifier).
// Layout: chunk header 8B, id u8, res0 u8, res1 u16, entryCount u32,
// entriesStart u32, then ResTable_config (size u32 at +20, imsi 4B at +24,
// locale: language u16 + country u16 at +28).
bool TypeConfigHasDefaultLocale(const Reader& r, size_t typeOff) {
    uint32_t configSize = 0;
    if (!r.u32(typeOff + 20, configSize) || configSize < 12) return false;
    uint16_t language = 0, country = 0;
    if (!r.u16(typeOff + 28, language) || !r.u16(typeOff + 30, country)) return false;
    return language == 0 && country == 0;
}

// Decode the entry byte-offset (relative to entriesStart) for `entryIdx` in a
// ResTable_type chunk at `typeOff`, honoring sparse / offset16 / dense layout.
// Returns false when the entry is absent in this config variant.
bool EntryOffsetFor(const Reader& r, size_t typeOff, uint32_t entryIdx, uint32_t& outOff) {
    uint16_t headerSize = 0;
    uint8_t flags = 0;
    uint32_t entryCount = 0;
    if (!r.u16(typeOff + 2, headerSize) || !r.u8(typeOff + 9, flags) ||
        !r.u32(typeOff + 12, entryCount)) {
        return false;
    }
    const size_t arr = typeOff + headerSize;  // offset array starts after header
    if (flags & TYPE_FLAG_SPARSE) {
        // entryCount pairs of { u16 idx, u16 offset/4 }, sorted by idx.
        for (uint32_t i = 0; i < entryCount; ++i) {
            uint16_t idx = 0, off = 0;
            if (!r.u16(arr + 4 * i, idx) || !r.u16(arr + 4 * i + 2, off)) return false;
            if (idx == entryIdx) {
                outOff = static_cast<uint32_t>(off) * 4u;
                return true;
            }
        }
        return false;
    }
    if (flags & TYPE_FLAG_OFFSET16) {
        if (entryIdx >= entryCount) return false;
        uint16_t v = 0;
        if (!r.u16(arr + 2 * entryIdx, v)) return false;
        if (v == NO_ENTRY_16) return false;
        outOff = static_cast<uint32_t>(v) * 4u;
        return true;
    }
    // Dense u32 offsets.
    if (entryIdx >= entryCount) return false;
    uint32_t v = 0;
    if (!r.u32(arr + 4 * entryIdx, v)) return false;
    if (v == NO_ENTRY_32) return false;
    outOff = v;
    return true;
}

// Higher score = preferred. Raster strongly preferred over XML (adaptive/vector);
// among rasters, higher density wins.
int CandidateScore(const std::string& path) {
    int score = 0;
    if (path.size() >= 4 && path.compare(path.size() - 4, 4, ".xml") == 0) {
        score -= 1000;
    }
    struct { const char* tag; int rank; } kDensities[] = {
        {"-xxxhdpi", 6}, {"-xxhdpi", 5}, {"-xhdpi", 4}, {"-hdpi", 3},
        {"-tvdpi", 2}, {"-mdpi", 1}, {"-ldpi", 0}, {"-nodpi", 1},
    };
    for (const auto& d : kDensities) {
        if (path.find(d.tag) != std::string::npos) {
            score += d.rank * 10;
            break;
        }
    }
    return score;
}

// Read a named zip entry from an APK into memory.
bool ReadZipEntry(const std::string& apkPath, const std::string& entryName,
                  std::vector<uint8_t>& out) {
    unzFile zf = unzOpen(apkPath.c_str());
    if (zf == nullptr) return false;
    bool ok = false;
    if (unzLocateFile(zf, entryName.c_str(), 0) == UNZ_OK) {
        unz_file_info info{};
        if (unzGetCurrentFileInfo(zf, &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK &&
            unzOpenCurrentFile(zf) == UNZ_OK) {
            out.resize(info.uncompressed_size);
            int n = out.empty() ? 0 : unzReadCurrentFile(zf, out.data(), info.uncompressed_size);
            unzCloseCurrentFile(zf);
            ok = (n == static_cast<int>(info.uncompressed_size));
        }
    }
    unzClose(zf);
    return ok;
}

}  // namespace

bool ResolveResourceIdToFile(const std::string& apkPath, uint32_t resId,
                             std::string& outFilePath) {
    std::vector<uint8_t> arsc;
    if (!ReadZipEntry(apkPath, "resources.arsc", arsc) || arsc.size() < 12) {
        ARSC_LOGW("ResolveResourceIdToFile: cannot read resources.arsc from %{public}s",
                  apkPath.c_str());
        return false;
    }
    const Reader r(arsc.data(), arsc.size());

    uint16_t tableType = 0, tableHeaderSize = 0;
    if (!r.u16(0, tableType) || !r.u16(2, tableHeaderSize) || tableType != RES_TABLE_TYPE) {
        ARSC_LOGW("ResolveResourceIdToFile: not a RES_TABLE (type=0x%{public}04x)", tableType);
        return false;
    }

    const uint32_t wantPkg = (resId >> 24) & 0xff;
    size_t globalPoolOff = 0;
    bool haveGlobalPool = false;
    std::vector<std::string> candidates;

    // Walk top-level chunks: the first string pool is the global value pool;
    // each matching package chunk contributes type chunks for our type id.
    size_t o = tableHeaderSize;
    while (o + 8 <= arsc.size()) {
        uint16_t ctype = 0, chsize = 0;
        uint32_t csize = 0;
        if (!r.u16(o, ctype) || !r.u16(o + 2, chsize) || !r.u32(o + 4, csize)) break;
        if (csize < 8 || o + csize > arsc.size()) break;

        if (ctype == RES_STRING_POOL_TYPE && !haveGlobalPool) {
            globalPoolOff = o;
            haveGlobalPool = true;
        } else if (ctype == RES_TABLE_PACKAGE_TYPE) {
            uint32_t pkgId = 0;
            if (r.u32(o + 8, pkgId) && pkgId == wantPkg) {
                // Iterate nested chunks for matching ResTable_type chunks.
                size_t no = o + chsize;
                const size_t end = o + csize;
                while (no + 8 <= end) {
                    uint16_t nt = 0;
                    uint32_t nsz = 0;
                    if (!r.u16(no, nt) || !r.u32(no + 4, nsz) || nsz < 8) break;
                    if (nt == RES_TABLE_TYPE_TYPE) {
                        uint8_t typeId = 0;
                        if (r.u8(no + 8, typeId) && typeId == wantType) {
                            uint32_t eoff = 0;
                            if (EntryOffsetFor(r, no, wantEntry, eoff)) {
                                uint32_t entriesStart = 0;
                                if (r.u32(no + 16, entriesStart)) {
                                    size_t ent = no + entriesStart + eoff;
                                    uint16_t esize = 0, eflags = 0;
                                    if (r.u16(ent, esize) && r.u16(ent + 2, eflags) &&
                                        !(eflags & ENTRY_FLAG_COMPLEX)) {
                                        size_t val = ent + esize;  // Res_value
                                        uint8_t vtype = 0;
                                        uint32_t vdata = 0;
                                        if (r.u8(val + 3, vtype) && r.u32(val + 4, vdata) &&
                                            vtype == RES_VALUE_TYPE_STRING && haveGlobalPool) {
                                            std::string path;
                                            if (ReadPoolString(r, globalPoolOff, vdata, path) &&
                                                !path.empty()) {
                                                candidates.push_back(std::move(path));
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    no += nsz;
                }
            }
        }
        o += csize;
    }

    if (candidates.empty()) {
        ARSC_LOGW("ResolveResourceIdToFile: 0x%{public}08x not found as a file in %{public}s",
                  resId, apkPath.c_str());
        return false;
    }

    // Pick the best candidate (highest-density raster).
    const std::string* best = &candidates[0];
    int bestScore = CandidateScore(*best);
    for (size_t i = 1; i < candidates.size(); ++i) {
        int s = CandidateScore(candidates[i]);
        if (s > bestScore) {
            bestScore = s;
            best = &candidates[i];
        }
    }
    outFilePath = *best;
    ARSC_LOGI("ResolveResourceIdToFile: 0x%{public}08x -> %{public}s (%{public}zu candidates)",
              resId, outFilePath.c_str(), candidates.size());
    return true;
}

bool ResolveResourceIdToString(const std::string& apkPath, uint32_t resId,
                               std::string& outString) {
    std::vector<uint8_t> arsc;
    if (!ReadZipEntry(apkPath, "resources.arsc", arsc) || arsc.size() < 12) {
        ARSC_LOGW("ResolveResourceIdToString: cannot read resources.arsc from %{public}s",
                  apkPath.c_str());
        return false;
    }
    const Reader r(arsc.data(), arsc.size());

    uint16_t tableType = 0, tableHeaderSize = 0;
    if (!r.u16(0, tableType) || !r.u16(2, tableHeaderSize) || tableType != RES_TABLE_TYPE) {
        ARSC_LOGW("ResolveResourceIdToString: not a RES_TABLE (type=0x%{public}04x)", tableType);
        return false;
    }

    const uint32_t wantPkg = (resId >> 24) & 0xff;
    const uint32_t wantType = (resId >> 16) & 0xff;
    const uint32_t wantEntry = resId & 0xffff;

    size_t globalPoolOff = 0;
    bool haveGlobalPool = false;
    // (value, isDefaultLocale) per config variant that defines this entry.
    std::vector<std::pair<std::string, bool>> candidates;

    size_t o = tableHeaderSize;
    while (o + 8 <= arsc.size()) {
        uint16_t ctype = 0, chsize = 0;
        uint32_t csize = 0;
        if (!r.u16(o, ctype) || !r.u16(o + 2, chsize) || !r.u32(o + 4, csize)) break;
        if (csize < 8 || o + csize > arsc.size()) break;

        if (ctype == RES_STRING_POOL_TYPE && !haveGlobalPool) {
            globalPoolOff = o;
            haveGlobalPool = true;
        } else if (ctype == RES_TABLE_PACKAGE_TYPE) {
            uint32_t pkgId = 0;
            if (r.u32(o + 8, pkgId) && pkgId == wantPkg) {
                size_t no = o + chsize;
                const size_t end = o + csize;
                while (no + 8 <= end) {
                    uint16_t nt = 0;
                    uint32_t nsz = 0;
                    if (!r.u16(no, nt) || !r.u32(no + 4, nsz) || nsz < 8) break;
                    if (nt == RES_TABLE_TYPE_TYPE) {
                        uint8_t typeId = 0;
                        if (r.u8(no + 8, typeId) && typeId == wantType) {
                            uint32_t eoff = 0;
                            if (EntryOffsetFor(r, no, wantEntry, eoff)) {
                                uint32_t entriesStart = 0;
                                if (r.u32(no + 16, entriesStart)) {
                                    size_t ent = no + entriesStart + eoff;
                                    uint16_t esize = 0, eflags = 0;
                                    if (r.u16(ent, esize) && r.u16(ent + 2, eflags) &&
                                        !(eflags & ENTRY_FLAG_COMPLEX)) {
                                        size_t val = ent + esize;  // Res_value
                                        uint8_t vtype = 0;
                                        uint32_t vdata = 0;
                                        if (r.u8(val + 3, vtype) && r.u32(val + 4, vdata) &&
                                            vtype == RES_VALUE_TYPE_STRING && haveGlobalPool) {
                                            std::string s;
                                            if (ReadPoolStringUtf8(r, globalPoolOff, vdata, s) &&
                                                !s.empty()) {
                                                candidates.emplace_back(
                                                    std::move(s),
                                                    TypeConfigHasDefaultLocale(r, no));
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                    no += nsz;
                }
            }
        }
        o += csize;
    }

    if (candidates.empty()) {
        ARSC_LOGW("ResolveResourceIdToString: 0x%{public}08x not found as a string in %{public}s",
                  resId, apkPath.c_str());
        return false;
    }

    // Prefer the default-locale variant (what Android shows when no locale
    // qualifier matches); fall back to the first candidate otherwise.
    const std::string* best = &candidates[0].first;
    for (const auto& c : candidates) {
        if (c.second) {
            best = &c.first;
            break;
        }
    }
    outString = *best;
    ARSC_LOGI("ResolveResourceIdToString: 0x%{public}08x -> %{public}s (%{public}zu candidates)",
              resId, outString.c_str(), candidates.size());
    return true;
}

bool ResolveApkResourceIdToString(const std::string& apkPath, uint32_t resId,
                                  std::string& outString)
{
    if (resId == 0) {
        return false;
    }
    const uint32_t packageId = (resId >> 24) & 0xff;
    const std::string resourceOwner = packageId == 0x01
        ? std::string("/system/android/framework/framework-res.apk")
        : apkPath;
    return ResolveResourceIdToString(resourceOwner, resId, outString);
}

}  // namespace oh_adapter
