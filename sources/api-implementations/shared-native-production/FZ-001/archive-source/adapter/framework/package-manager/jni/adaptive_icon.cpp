/*
 * adaptive_icon.cpp — see adaptive_icon.h.
 *
 * Bounded implementation notes:
 * - The <adaptive-icon> document only needs two child element refs:
 *   android:foreground / android:background. Element names are matched as
 *   plain strings ("adaptive-icon", "foreground", "background") because the
 *   compiled AXML carries element names in its string pool directly.
 * - A layer value may be TYPE_REFERENCE (resolve via arsc to a raster path),
 *   TYPE_STRING (raw file path — rare), or TYPE_INT_COLOR_ARGB8/RGB8 for the
 *   background (solid fill). Vector/webp foregrounds decode-fail -> false.
 * - Composition canvas: max(width,height) square across layers, min 108.
 *   Nearest-neighbour downscale / bilinear-ish (2x2 average) upscale, alpha
 *   composite fg-over-bg, premultiplied-safe by construction (uint8 RGBA,
 *   no negative channels; rounding by truncation is acceptable for an icon).
 */
#include "adaptive_icon.h"

#include "arsc_resolver.h"
#include "axml_parser.h"

#include "hilog/log.h"
#include "lodepng.h"

#include <unzip.h>            // minizip reader (compiled into this lib)

#include <algorithm>
#include <cmath>
#include <cstring>
#include <string>
#include <vector>

namespace oh_adapter {
namespace {

#define LOG_DOMAIN 0xD001802
#define LOG_TAG "OH_AdaptiveIcon"
#define AI_LOGI(...) OHOS::HiviewDFX::HiLog::Info({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)
#define AI_LOGW(...) OHOS::HiviewDFX::HiLog::Warn({LOG_CORE, LOG_DOMAIN, LOG_TAG}, __VA_ARGS__)

struct Rgba {
    unsigned char r, g, b, a;
};

// arsc_resolver.cpp's ReadZipEntry lives in its anonymous namespace, so this
// TU carries its own identical reader (minizip, already linked into the lib).
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

bool DecodePngToRgba(const std::vector<uint8_t>& bytes, std::vector<Rgba>& px,
                     unsigned& w, unsigned& h) {
    std::vector<unsigned char> out;
    unsigned iw = 0, ih = 0;
    if (lodepng::decode(out, iw, ih, bytes) != 0) {
        return false;  // not a decodable PNG (webp/vector)
    }
    w = iw;
    h = ih;
    px.resize(static_cast<size_t>(iw) * ih);
    std::memcpy(px.data(), out.data(), px.size() * 4);
    return true;
}

// Scale an RGBA layer to size x size with 2x2-average upscale and
// nearest-neighbour downscale. Icon-grade resampling; keeps it dependency-free.
std::vector<Rgba> ScaleToSquare(const std::vector<Rgba>& src, unsigned sw, unsigned sh,
                                unsigned size) {
    std::vector<Rgba> dst(static_cast<size_t>(size) * size);
    for (unsigned y = 0; y < size; ++y) {
        const double sy = (static_cast<double>(y) + 0.5) * sh / size - 0.5;
        const int y0 = std::max(0, static_cast<int>(std::floor(sy)));
        const int y1 = std::min(static_cast<int>(sh) - 1, y0 + 1);
        const double fy = sy - y0;
        for (unsigned x = 0; x < size; ++x) {
            const double sx = (static_cast<double>(x) + 0.5) * sw / size - 0.5;
            const int x0 = std::max(0, static_cast<int>(std::floor(sx)));
            const int x1 = std::min(static_cast<int>(sw) - 1, x0 + 1);
            const double fx = sx - x0;
            // bilinear on each channel
            const Rgba& p00 = src[static_cast<size_t>(y0) * sw + x0];
            const Rgba& p10 = src[static_cast<size_t>(y0) * sw + x1];
            const Rgba& p01 = src[static_cast<size_t>(y1) * sw + x0];
            const Rgba& p11 = src[static_cast<size_t>(y1) * sw + x1];
            Rgba d;
            const auto mix = [&](int c00, int c10, int c01, int c11) {
                const double top = c00 + (c10 - c00) * fx;
                const double bot = c01 + (c11 - c01) * fx;
                return static_cast<unsigned char>(top + (bot - top) * fy + 0.5);
            };
            d.r = mix(p00.r, p10.r, p01.r, p11.r);
            d.g = mix(p00.g, p10.g, p01.g, p11.g);
            d.b = mix(p00.b, p10.b, p01.b, p11.b);
            d.a = mix(p00.a, p10.a, p01.a, p11.a);
            dst[static_cast<size_t>(y) * size + x] = d;
        }
    }
    return dst;
}

// Resolve one layer reference to PNG bytes via the arsc highest-density path.
bool LayerRefToPng(const std::string& arscApk, uint32_t resId,
                   std::vector<uint8_t>& outPng) {
    std::string entry;
    if (!ResolveResourceIdToFile(arscApk, resId, entry)) {
        AI_LOGW("adaptive layer 0x%{public}08x: no file entry in %{public}s",
                resId, arscApk.c_str());
        return false;
    }
    if (entry.size() >= 4 && entry.compare(entry.size() - 4, 4, ".xml") == 0) {
        AI_LOGW("adaptive layer 0x%{public}08x -> nested XML %{public}s (vector) unsupported",
                resId, entry.c_str());
        return false;
    }
    if (!ReadZipEntry(arscApk, entry, outPng) || outPng.empty()) {
        AI_LOGW("adaptive layer 0x%{public}08x: cannot read %{public}s", resId, entry.c_str());
        return false;
    }
    return true;
}

}  // namespace

bool ComposeAdaptiveIcon(const std::string& apkPath, const std::string& arscApk,
                         const std::vector<uint8_t>& xmlBytes,
                         std::vector<uint8_t>& outPng) {
    AxmlParser parser;
    if (parser.setTo(xmlBytes.data(), xmlBytes.size()) != 0) {
        AI_LOGW("adaptive icon: AXML setTo failed (%{public}zu bytes)", xmlBytes.size());
        return false;
    }
    uint32_t fgRef = 0, bgRef = 0;
    unsigned bgColor = 0;
    bool haveFg = false, haveBg = false, haveBgColor = false;
    bool inAdaptive = false;
    for (AxmlParser::EventCode ev = parser.next();
         ev != AxmlParser::EC_END_DOCUMENT;
         ev = parser.next()) {
        if (ev == AxmlParser::EC_BAD_DOCUMENT) {
            break;
        }
        if (ev == AxmlParser::EC_START_TAG) {
            size_t len = 0;
            const char* name = parser.getElementName(&len);
            const std::string el(name ? name : "", len);
            if (el == "adaptive-icon") {
                inAdaptive = true;
                continue;
            }
            if (!inAdaptive) {
                continue;
            }
            const bool isFg = (el == "foreground");
            const bool isBg = (el == "background");
            if (!isFg && !isBg) {
                continue;
            }
            for (size_t i = 0; i < parser.getAttributeCount(); ++i) {
                ResValue v;
                if (parser.getAttributeValue(i, &v) != 0) {
                    continue;
                }
                if (v.dataType == ResValue::TYPE_REFERENCE && v.data != 0) {
                    if (isFg && !haveFg) {
                        fgRef = v.data; haveFg = true;
                    } else if (isBg && !haveBg) {
                        bgRef = v.data; haveBg = true;
                    }
                } else if (isBg &&
                           (v.dataType == ResValue::TYPE_INT_COLOR_ARGB8 ||
                            v.dataType == ResValue::TYPE_INT_COLOR_RGB8)) {
                    bgColor = v.data; haveBgColor = true;
                }
            }
        } else if (ev == AxmlParser::EC_END_TAG) {
            size_t len = 0;
            const char* name = parser.getElementName(&len);
            if (len == 13 && std::memcmp(name, "adaptive-icon", 13) == 0) {
                break;
            }
        }
    }
    if (!haveFg) {
        AI_LOGW("adaptive icon: no foreground reference found");
        return false;
    }
    if (!haveBg && !haveBgColor) {
        // Android default background is opaque white when unspecified.
        bgColor = 0xFFFFFFFFu;
        haveBgColor = true;
    }

    // foreground must decode to a raster
    std::vector<uint8_t> fgPng;
    if (!LayerRefToPng(arscApk, fgRef, fgPng)) {
        return false;
    }
    std::vector<Rgba> fgPx, bgPx;
    unsigned fw = 0, fh = 0, bw = 0, bh = 0;
    if (!DecodePngToRgba(fgPng, fgPx, fw, fh)) {
        AI_LOGW("adaptive icon: foreground decode failed (webp/vector?)");
        return false;
    }
    if (haveBg) {
        std::vector<uint8_t> bgPng;
        if (LayerRefToPng(arscApk, bgRef, bgPng) && DecodePngToRgba(bgPng, bgPx, bw, bh)) {
            haveBgColor = false;  // raster background wins
        } else {
            AI_LOGW("adaptive icon: background raster failed, using fallback fill");
            haveBg = false;
            bgColor = 0xFFFFFFFFu;
            haveBgColor = true;
        }
    }

    unsigned canvas = std::max({fw, fh, bw, bh, 108u});
    // cap the canvas so huge foregrounds do not explode memory
    canvas = std::min(canvas, 512u);
    std::vector<Rgba> fgS = ScaleToSquare(fgPx, fw, fh, canvas);
    std::vector<Rgba> bgS;
    if (haveBg) {
        bgS = ScaleToSquare(bgPx, bw, bh, canvas);
    } else {
        bgS.assign(static_cast<size_t>(canvas) * canvas,
                   Rgba{static_cast<unsigned char>((bgColor >> 16) & 0xff),
                        static_cast<unsigned char>((bgColor >> 8) & 0xff),
                        static_cast<unsigned char>(bgColor & 0xff),
                        static_cast<unsigned char>((bgColor >> 24) & 0xff)});
    }

    // fg src-over bg
    std::vector<unsigned char> rgba(static_cast<size_t>(canvas) * canvas * 4);
    for (size_t i = 0; i < fgS.size(); ++i) {
        const Rgba& f = fgS[i];
        const Rgba& b = bgS[i];
        const unsigned fa = f.a;
        Rgba o;
        o.a = static_cast<unsigned char>(fa + b.a * (255 - fa) / 255);
        const unsigned inv = 255 - fa;
        o.r = static_cast<unsigned char>((f.r * fa + b.r * b.a * inv / 255) / (o.a ? o.a : 1));
        o.g = static_cast<unsigned char>((f.g * fa + b.g * b.a * inv / 255) / (o.a ? o.a : 1));
        o.b = static_cast<unsigned char>((f.b * fa + b.b * b.a * inv / 255) / (o.a ? o.a : 1));
        rgba[i * 4 + 0] = o.r;
        rgba[i * 4 + 1] = o.g;
        rgba[i * 4 + 2] = o.b;
        rgba[i * 4 + 3] = o.a;
    }
    std::vector<unsigned char> png;
    if (lodepng::encode(png, rgba, canvas, canvas) != 0) {
        AI_LOGW("adaptive icon: PNG encode failed");
        return false;
    }
    outPng = std::move(png);
    AI_LOGI("adaptive icon: composed %{public}ux%{public}u from fg 0x%{public}08x "
            "(%{public}ux%{public}u) + %{public}s (%{public}zu bytes)",
            canvas, canvas, fgRef, fw, fh,
            haveBg ? "raster bg" : "color bg", outPng.size());
    return true;
}

}  // namespace oh_adapter
