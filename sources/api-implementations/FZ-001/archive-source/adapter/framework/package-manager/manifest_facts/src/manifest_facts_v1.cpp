#include "manifest_facts_v1.h"

#include "axml_parser.h"
#include "../../application_attributes/src/manifest_version_parser.h"
#include "sha256.h"
#include "../../application_attributes/src/sdk_rules.h"

#include <algorithm>
#include <cerrno>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <set>
#include <sstream>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>

#include <zlib.h>

namespace oh_adapter::manifest_facts {
namespace {

constexpr const char* PARSER_VERSION = "bridge-manifest-facts-v1";
constexpr uint32_t ZIP_LOCAL_SIGNATURE = 0x04034b50;
constexpr uint32_t ZIP_CENTRAL_SIGNATURE = 0x02014b50;
constexpr uint32_t ZIP_EOCD_SIGNATURE = 0x06054b50;
constexpr const char* MANIFEST_NAME = "AndroidManifest.xml";

uint16_t Read16(const uint8_t* data)
{
    return static_cast<uint16_t>(data[0]) |
        static_cast<uint16_t>(static_cast<uint16_t>(data[1]) << 8);
}

uint32_t Read32(const uint8_t* data)
{
    return static_cast<uint32_t>(data[0]) |
        (static_cast<uint32_t>(data[1]) << 8) |
        (static_cast<uint32_t>(data[2]) << 16) |
        (static_cast<uint32_t>(data[3]) << 24);
}

bool RangeFits(size_t offset, size_t length, size_t total)
{
    return offset <= total && length <= total - offset;
}

std::string Hex(const uint8_t* bytes, size_t length)
{
    static constexpr char DIGITS[] = "0123456789abcdef";
    std::string result;
    result.reserve(length * 2);
    for (size_t index = 0; index < length; ++index) {
        result.push_back(DIGITS[bytes[index] >> 4]);
        result.push_back(DIGITS[bytes[index] & 0x0f]);
    }
    return result;
}

std::string Sha256Hex(const std::vector<uint8_t>& bytes)
{
    uint8_t digest[32];
    sha256(bytes.empty() ? nullptr : bytes.data(), bytes.size(), digest);
    return Hex(digest, sizeof(digest));
}

bool IsLowerHexSha256(const std::string& value)
{
    return value.size() == 64 &&
        std::all_of(value.begin(), value.end(), [](char c) {
            return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
        });
}

std::string Json(const std::string& value)
{
    std::string result = "\"";
    for (unsigned char c : value) {
        switch (c) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (c < 0x20) {
                    static constexpr char DIGITS[] = "0123456789abcdef";
                    result += "\\u00";
                    result.push_back(DIGITS[c >> 4]);
                    result.push_back(DIGITS[c & 0xf]);
                } else {
                    result.push_back(static_cast<char>(c));
                }
        }
    }
    result.push_back('"');
    return result;
}

ManifestParseReceiptV1 Reject(const ManifestParseRequestV1& request,
    ManifestParseVerdict verdict, const std::string& reason)
{
    ManifestParseReceiptV1 receipt;
    receipt.requestId = request.requestId;
    receipt.verdict = verdict;
    receipt.reason = reason;
    receipt.artifactSha256 = request.artifactSha256;
    receipt.artifactSetDigest = request.artifactSet.artifactSetDigest;
    receipt.parserVersion = PARSER_VERSION;
    return receipt;
}

bool ReadIdentityBytes(const ManifestParseRequestV1& request,
    const ManifestParserLimitsV1& limits, std::vector<uint8_t>* bytes,
    ManifestParseReceiptV1* rejection)
{
    if (request.byteLength > limits.maxArtifactBytes ||
        request.byteLength > static_cast<uint64_t>(
            std::numeric_limits<size_t>::max())) {
        *rejection = Reject(request, ManifestParseVerdict::LIMIT_EXCEEDED,
            "artifact byteLength exceeds v1 limit");
        return false;
    }

    struct stat status {};
    if (fstat(request.artifactFd, &status) != 0) {
        *rejection = Reject(request, ManifestParseVerdict::IO_ERROR,
            "fstat failed: " + std::to_string(errno));
        return false;
    }
    if (!S_ISREG(status.st_mode)) {
        *rejection = Reject(request, ManifestParseVerdict::INVALID_ENVELOPE,
            "artifact fd is not a regular immutable byte object");
        return false;
    }
    if (status.st_size < 0 ||
        static_cast<uint64_t>(status.st_size) != request.byteLength) {
        *rejection = Reject(request, ManifestParseVerdict::BYTE_LENGTH_MISMATCH,
            "fstat size differs from declared byteLength");
        return false;
    }

#if defined(__linux__) && defined(F_GET_SEALS)
    if (request.requireLinuxSeals) {
        const int seals = fcntl(request.artifactFd, F_GET_SEALS);
        const int required = F_SEAL_SEAL | F_SEAL_SHRINK | F_SEAL_GROW |
            F_SEAL_WRITE;
        if (seals < 0 || (seals & required) != required) {
            *rejection = Reject(request, ManifestParseVerdict::FD_NOT_SEALED,
                "fd lacks immutable Linux memfd seals");
            return false;
        }
    }
#else
    if (request.requireLinuxSeals) {
        *rejection = Reject(request, ManifestParseVerdict::NOT_SUPPORTED,
            "sealed-fd enforcement is unavailable on this host");
        return false;
    }
#endif

    try {
        bytes->assign(static_cast<size_t>(request.byteLength), 0);
    } catch (const std::bad_alloc&) {
        *rejection = Reject(request, ManifestParseVerdict::LIMIT_EXCEEDED,
            "artifact allocation failed under v1 limit");
        return false;
    }

    size_t offset = 0;
    while (offset < bytes->size()) {
        const ssize_t count = pread(request.artifactFd, bytes->data() + offset,
            bytes->size() - offset, static_cast<off_t>(offset));
        if (count < 0 && errno == EINTR) continue;
        if (count < 0) {
            *rejection = Reject(request, ManifestParseVerdict::IO_ERROR,
                "pread failed: " + std::to_string(errno));
            return false;
        }
        if (count == 0) {
            *rejection = Reject(request,
                ManifestParseVerdict::BYTE_LENGTH_MISMATCH,
                "fd truncated during immutable read");
            return false;
        }
        offset += static_cast<size_t>(count);
    }

    struct stat readback {};
    if (fstat(request.artifactFd, &readback) != 0 ||
        readback.st_dev != status.st_dev || readback.st_ino != status.st_ino ||
        readback.st_size != status.st_size) {
        *rejection = Reject(request, ManifestParseVerdict::IO_ERROR,
            "artifact fd identity changed during read");
        return false;
    }
    return true;
}

struct ZipManifest {
    std::vector<uint8_t> bytes;
    uint32_t crc32 = 0;
    uint64_t localOffset = 0;
};

bool ExtractManifest(const ManifestParseRequestV1& request,
    const ManifestParserLimitsV1& limits,
    const std::vector<uint8_t>& archive, ZipManifest* manifest,
    ManifestParseReceiptV1* rejection)
{
    if (archive.size() < 22) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "ZIP EOCD is absent");
        return false;
    }
    const size_t searchStart =
        archive.size() > 65557 ? archive.size() - 65557 : 0;
    size_t eocd = std::numeric_limits<size_t>::max();
    for (size_t cursor = archive.size() - 22;; --cursor) {
        if (Read32(archive.data() + cursor) == ZIP_EOCD_SIGNATURE) {
            eocd = cursor;
            break;
        }
        if (cursor == searchStart) break;
    }
    if (eocd == std::numeric_limits<size_t>::max() ||
        !RangeFits(eocd, 22, archive.size())) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "ZIP EOCD is malformed");
        return false;
    }
    const uint16_t disk = Read16(archive.data() + eocd + 4);
    const uint16_t centralDisk = Read16(archive.data() + eocd + 6);
    const uint16_t diskMembers = Read16(archive.data() + eocd + 8);
    const uint16_t totalMembers = Read16(archive.data() + eocd + 10);
    const uint32_t centralSize = Read32(archive.data() + eocd + 12);
    const uint32_t centralOffset = Read32(archive.data() + eocd + 16);
    const uint16_t commentLength = Read16(archive.data() + eocd + 20);
    if (disk != 0 || centralDisk != 0 || diskMembers != totalMembers ||
        totalMembers == 0xffff || centralOffset == 0xffffffffU ||
        centralSize == 0xffffffffU) {
        *rejection = Reject(request, ManifestParseVerdict::NOT_SUPPORTED,
            "multi-disk or ZIP64 APK is outside v1");
        return false;
    }
    if (totalMembers > limits.maxZipMembers) {
        *rejection = Reject(request, ManifestParseVerdict::LIMIT_EXCEEDED,
            "ZIP member count exceeds v1 limit");
        return false;
    }
    if (!RangeFits(eocd + 22, commentLength, archive.size()) ||
        eocd + 22ULL + commentLength != archive.size() ||
        !RangeFits(centralOffset, centralSize, archive.size()) ||
        static_cast<size_t>(centralOffset) + centralSize > eocd) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "ZIP central directory range is invalid");
        return false;
    }

    size_t cursor = centralOffset;
    bool found = false;
    uint16_t method = 0;
    uint16_t flags = 0;
    uint32_t compressedSize = 0;
    uint32_t uncompressedSize = 0;
    uint32_t expectedCrc = 0;
    uint32_t localOffset = 0;
    for (uint32_t member = 0; member < totalMembers; ++member) {
        if (!RangeFits(cursor, 46, archive.size()) ||
            Read32(archive.data() + cursor) != ZIP_CENTRAL_SIGNATURE) {
            *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
                "ZIP central member is malformed");
            return false;
        }
        const uint16_t nameLength = Read16(archive.data() + cursor + 28);
        const uint16_t extraLength = Read16(archive.data() + cursor + 30);
        const uint16_t memberCommentLength =
            Read16(archive.data() + cursor + 32);
        const size_t recordSize = 46ULL + nameLength + extraLength +
            memberCommentLength;
        if (!RangeFits(cursor, recordSize, archive.size())) {
            *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
                "ZIP central member range is invalid");
            return false;
        }
        const std::string name(reinterpret_cast<const char*>(
            archive.data() + cursor + 46), nameLength);
        if (name == MANIFEST_NAME) {
            if (found) {
                *rejection = Reject(request,
                    ManifestParseVerdict::MANIFEST_DUPLICATE,
                    "APK contains duplicate AndroidManifest.xml members");
                return false;
            }
            found = true;
            flags = Read16(archive.data() + cursor + 8);
            method = Read16(archive.data() + cursor + 10);
            expectedCrc = Read32(archive.data() + cursor + 16);
            compressedSize = Read32(archive.data() + cursor + 20);
            uncompressedSize = Read32(archive.data() + cursor + 24);
            localOffset = Read32(archive.data() + cursor + 42);
        }
        cursor += recordSize;
    }
    if (cursor != static_cast<size_t>(centralOffset) + centralSize) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "ZIP central directory size does not match member records");
        return false;
    }
    if (!found) {
        *rejection = Reject(request, ManifestParseVerdict::MANIFEST_NOT_FOUND,
            "AndroidManifest.xml is absent");
        return false;
    }
    if ((flags & 1U) != 0 || (method != 0 && method != 8)) {
        *rejection = Reject(request, ManifestParseVerdict::NOT_SUPPORTED,
            "encrypted or unsupported-compression manifest");
        return false;
    }
    if (compressedSize > limits.maxManifestCompressedBytes ||
        uncompressedSize > limits.maxManifestBytes) {
        *rejection = Reject(request, ManifestParseVerdict::LIMIT_EXCEEDED,
            "manifest expansion exceeds v1 limit");
        return false;
    }
    if (!RangeFits(localOffset, 30, archive.size()) ||
        Read32(archive.data() + localOffset) != ZIP_LOCAL_SIGNATURE) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "manifest local header is malformed");
        return false;
    }
    const uint16_t localNameLength =
        Read16(archive.data() + localOffset + 26);
    const uint16_t localExtraLength =
        Read16(archive.data() + localOffset + 28);
    const uint16_t localFlags = Read16(archive.data() + localOffset + 6);
    const uint16_t localMethod = Read16(archive.data() + localOffset + 8);
    const size_t dataOffset = static_cast<size_t>(localOffset) + 30 +
        localNameLength + localExtraLength;
    if (!RangeFits(localOffset + 30, localNameLength + localExtraLength,
            archive.size()) ||
        !RangeFits(dataOffset, compressedSize, archive.size())) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "manifest compressed range is invalid");
        return false;
    }
    const std::string localName(reinterpret_cast<const char*>(
        archive.data() + localOffset + 30), localNameLength);
    if (localName != MANIFEST_NAME || localFlags != flags ||
        localMethod != method) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "central/local manifest identity or method mismatch");
        return false;
    }

    try {
        manifest->bytes.assign(uncompressedSize, 0);
    } catch (const std::bad_alloc&) {
        *rejection = Reject(request, ManifestParseVerdict::LIMIT_EXCEEDED,
            "manifest allocation failed under v1 limit");
        return false;
    }
    if (method == 0) {
        if (compressedSize != uncompressedSize) {
            *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
                "stored manifest sizes disagree");
            return false;
        }
        std::copy(archive.begin() + static_cast<ptrdiff_t>(dataOffset),
            archive.begin() + static_cast<ptrdiff_t>(dataOffset + compressedSize),
            manifest->bytes.begin());
    } else {
        z_stream stream {};
        stream.next_in = const_cast<Bytef*>(reinterpret_cast<const Bytef*>(
            archive.data() + dataOffset));
        stream.avail_in = compressedSize;
        stream.next_out = reinterpret_cast<Bytef*>(manifest->bytes.data());
        stream.avail_out = uncompressedSize;
        if (inflateInit2(&stream, -MAX_WBITS) != Z_OK) {
            *rejection = Reject(request, ManifestParseVerdict::INTERNAL_ERROR,
                "raw-deflate initialization failed");
            return false;
        }
        const int inflateResult = inflate(&stream, Z_FINISH);
        inflateEnd(&stream);
        if (inflateResult != Z_STREAM_END ||
            stream.total_out != uncompressedSize ||
            stream.total_in != compressedSize) {
            *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
                "manifest raw-deflate stream is invalid");
            return false;
        }
    }
    const uint32_t actualCrc = crc32(0L,
        reinterpret_cast<const Bytef*>(manifest->bytes.data()),
        manifest->bytes.size());
    if (actualCrc != expectedCrc) {
        *rejection = Reject(request, ManifestParseVerdict::ZIP_MALFORMED,
            "manifest CRC32 mismatch");
        return false;
    }
    manifest->crc32 = actualCrc;
    manifest->localOffset = localOffset;
    return true;
}

struct Attribute {
    bool present = false;
    std::string text;
    ResValue typed {};
    bool hasTyped = false;
};

bool ParseUtf8Length(const uint8_t* begin, const uint8_t* end,
    const uint8_t** next, size_t* value)
{
    if (begin >= end) return false;
    uint8_t first = *begin++;
    if ((first & 0x80U) == 0) {
        *value = first;
        *next = begin;
        return true;
    }
    if (begin >= end) return false;
    *value = static_cast<size_t>(first & 0x7fU) << 8 | *begin++;
    *next = begin;
    return true;
}

bool ParseUtf16Length(const uint8_t* begin, const uint8_t* end,
    const uint8_t** next, size_t* value)
{
    if (end - begin < 2) return false;
    uint16_t first = Read16(begin);
    begin += 2;
    if ((first & 0x8000U) == 0) {
        *value = first;
        *next = begin;
        return true;
    }
    if (end - begin < 2) return false;
    *value = (static_cast<size_t>(first & 0x7fffU) << 16) |
        Read16(begin);
    *next = begin + 2;
    return true;
}

bool ValidateBinaryXmlLayout(const std::vector<uint8_t>& bytes,
    std::string* reason)
{
    if (bytes.size() < 8 || Read16(bytes.data()) != 0x0003) {
        *reason = "binary XML top-level header is absent";
        return false;
    }
    const uint16_t topHeader = Read16(bytes.data() + 2);
    const uint32_t topSize = Read32(bytes.data() + 4);
    if (topHeader < 8 || topHeader > topSize || topSize != bytes.size()) {
        *reason = "binary XML top-level size/header is inconsistent";
        return false;
    }
    size_t cursor = topHeader;
    uint32_t stringCount = 0;
    bool hasStringPool = false;
    bool hasElement = false;
    while (cursor < bytes.size()) {
        if (!RangeFits(cursor, 8, bytes.size())) {
            *reason = "binary XML chunk header is truncated";
            return false;
        }
        const uint16_t type = Read16(bytes.data() + cursor);
        const uint16_t headerSize = Read16(bytes.data() + cursor + 2);
        const uint32_t chunkSize = Read32(bytes.data() + cursor + 4);
        if (headerSize < 8 || headerSize > chunkSize ||
            !RangeFits(cursor, chunkSize, bytes.size())) {
            *reason = "binary XML chunk size/header is inconsistent";
            return false;
        }
        const uint8_t* chunk = bytes.data() + cursor;
        if (type == 0x0001) {
            if (hasStringPool || headerSize < 28 || chunkSize < 28) {
                *reason = "binary XML string pool header is invalid";
                return false;
            }
            stringCount = Read32(chunk + 8);
            const uint32_t styleCount = Read32(chunk + 12);
            const uint32_t flags = Read32(chunk + 16);
            const uint32_t stringsStart = Read32(chunk + 20);
            const uint32_t stylesStart = Read32(chunk + 24);
            const uint64_t offsetBytes =
                (static_cast<uint64_t>(stringCount) + styleCount) * 4;
            if (offsetBytes > chunkSize ||
                static_cast<uint64_t>(headerSize) + offsetBytes > chunkSize ||
                stringsStart < headerSize + offsetBytes ||
                stringsStart > chunkSize ||
                (stylesStart != 0 &&
                    (stylesStart < stringsStart || stylesStart > chunkSize))) {
                *reason = "binary XML string pool ranges are invalid";
                return false;
            }
            const size_t stringsEnd =
                stylesStart == 0 ? chunkSize : stylesStart;
            for (uint32_t index = 0; index < stringCount; ++index) {
                const uint32_t offset =
                    Read32(chunk + headerSize + index * 4ULL);
                if (offset >= stringsEnd - stringsStart) {
                    *reason = "binary XML string offset is out of range";
                    return false;
                }
                const uint8_t* value = chunk + stringsStart + offset;
                const uint8_t* end = chunk + stringsEnd;
                const uint8_t* next = nullptr;
                size_t encodedLength = 0;
                if ((flags & (1U << 8)) != 0) {
                    size_t ignoredUtf16Length = 0;
                    if (!ParseUtf8Length(value, end, &next,
                            &ignoredUtf16Length) ||
                        !ParseUtf8Length(next, end, &value,
                            &encodedLength) ||
                        encodedLength >= static_cast<size_t>(end - value) ||
                        value[encodedLength] != 0) {
                        *reason = "binary XML UTF-8 string is truncated";
                        return false;
                    }
                } else {
                    if (!ParseUtf16Length(value, end, &next,
                            &encodedLength) ||
                        encodedLength >
                            static_cast<size_t>(end - next) / 2 ||
                        encodedLength * 2 + 2 >
                            static_cast<size_t>(end - next) ||
                        Read16(next + encodedLength * 2) != 0) {
                        *reason = "binary XML UTF-16 string is truncated";
                        return false;
                    }
                }
            }
            hasStringPool = true;
        } else if (type == 0x0180) {
            if (!hasStringPool || (chunkSize - headerSize) % 4 != 0) {
                *reason = "binary XML resource map is invalid";
                return false;
            }
        } else if (type == 0x0102) {
            if (!hasStringPool || headerSize < 16 ||
                chunkSize < static_cast<uint32_t>(headerSize) + 20U) {
                *reason = "binary XML start element header is invalid";
                return false;
            }
            const uint8_t* extension = chunk + headerSize;
            const uint32_t nameRef = Read32(extension + 4);
            const uint16_t attrStart = Read16(extension + 8);
            const uint16_t attrSize = Read16(extension + 10);
            const uint16_t attrCount = Read16(extension + 12);
            const uint64_t attrsEnd = static_cast<uint64_t>(headerSize) +
                attrStart + static_cast<uint64_t>(attrSize) * attrCount;
            if (nameRef >= stringCount || attrStart < 20 || attrSize < 20 ||
                attrsEnd > chunkSize) {
                *reason = "binary XML start element ranges are invalid";
                return false;
            }
            const uint8_t* attributes = extension + attrStart;
            for (uint32_t index = 0; index < attrCount; ++index) {
                const uint8_t* attribute = attributes + index * attrSize;
                const uint32_t attributeName = Read32(attribute + 4);
                const uint32_t rawValue = Read32(attribute + 8);
                const uint16_t valueSize = Read16(attribute + 12);
                const uint8_t dataType = attribute[15];
                const uint32_t data = Read32(attribute + 16);
                if (attributeName >= stringCount || valueSize < 8 ||
                    (rawValue != 0xffffffffU && rawValue >= stringCount) ||
                    (dataType == ResValue::TYPE_STRING &&
                        data >= stringCount)) {
                    *reason = "binary XML attribute reference is invalid";
                    return false;
                }
            }
            hasElement = true;
        } else if (type == 0x0103) {
            if (!hasStringPool || headerSize < 16 ||
                chunkSize < static_cast<uint32_t>(headerSize) + 8U ||
                Read32(chunk + headerSize + 4) >= stringCount) {
                *reason = "binary XML end element is invalid";
                return false;
            }
        } else if (type >= 0x0100 && type <= 0x017f) {
            if (!hasStringPool || headerSize < 16) {
                *reason = "binary XML node header is invalid";
                return false;
            }
        } else {
            *reason = "binary XML contains an unsupported chunk type";
            return false;
        }
        cursor += chunkSize;
    }
    if (cursor != bytes.size() || !hasStringPool || !hasElement) {
        *reason = "binary XML document is incomplete";
        return false;
    }
    return true;
}

bool GetUniqueAttribute(const AxmlParser& parser, const std::string& name,
    Attribute* output)
{
    size_t matches = 0;
    for (size_t index = 0; index < parser.getAttributeCount(); ++index) {
        size_t length = 0;
        const char* attributeName = parser.getAttributeName(index, &length);
        if (attributeName == nullptr ||
            std::string(attributeName, length) != name) {
            continue;
        }
        ++matches;
        size_t valueLength = 0;
        const char* value = parser.getAttributeStringValue(index, &valueLength);
        if (value != nullptr) output->text.assign(value, valueLength);
        output->hasTyped =
            parser.getAttributeValue(index, &output->typed) == 0;
    }
    output->present = matches == 1;
    return matches <= 1;
}

// Identity follows Android's TypedArray resource IDs, not unqualified names.
bool ReadSdkAttribute(const AxmlParser& parser, uint32_t id, SdkAttributeV2* output)
{
    bool seen = false;
    for (size_t i = 0; i < parser.getAttributeCount(); ++i) {
        if (parser.getAttributeNameResID(i) != id) continue;
        if (seen) return false;
        seen = true;
        ResValue value{};
        if (parser.getAttributeValue(i, &value) != 0) return false;
        output->present = true;
        output->type = value.dataType;
        output->bits = value.data;
        if (value.dataType == ResValue::TYPE_STRING) {
            size_t length = 0;
            const char* text = parser.getAttributeStringValue(i, &length);
            if (text == nullptr) return false;
            output->text.assign(text, length);
        }
    }
    return true;
}

bool ToBool(const Attribute& attribute, bool* value)
{
    if (!attribute.present) return true;
    if (attribute.hasTyped &&
        attribute.typed.dataType == ResValue::TYPE_INT_BOOLEAN) {
        *value = attribute.typed.data != 0;
        return true;
    }
    if (attribute.text == "true") {
        *value = true;
        return true;
    }
    if (attribute.text == "false") {
        *value = false;
        return true;
    }
    return false;
}

std::string ResolveClassName(const std::string& name,
    const std::string& packageName)
{
    if (name.empty()) return name;
    if (name.front() == '.') return packageName + name;
    if (name.find('.') == std::string::npos) return packageName + "." + name;
    return name;
}

void AddProvenance(ManifestFactsOutputV1* facts, const std::string& field,
    const std::string& artifactSha, const std::string& manifestSha,
    size_t chunkOffset)
{
    facts->provenance.push_back({
        field, artifactSha, manifestSha, static_cast<uint64_t>(chunkOffset),
    });
}

bool ParseAxml(const ManifestParseRequestV1& request,
    const ManifestParserLimitsV1& limits, const ZipManifest& manifest,
    ManifestFactsOutputV1* facts, ManifestVersionV2* version,
    std::vector<UsesSdkDeclarationV2>* sdkDeclarations,
    ManifestParseReceiptV1* rejection)
{
    std::string layoutReason;
    if (!ValidateBinaryXmlLayout(manifest.bytes, &layoutReason)) {
        *rejection = Reject(request, ManifestParseVerdict::MANIFEST_MALFORMED,
            layoutReason);
        return false;
    }
    AxmlParser parser;
    if (parser.setTo(manifest.bytes.data(), manifest.bytes.size()) != 0) {
        *rejection = Reject(request, ManifestParseVerdict::MANIFEST_MALFORMED,
            "AndroidManifest.xml is not supported binary XML");
        return false;
    }
    const std::string manifestSha = Sha256Hex(manifest.bytes);
    uint32_t depth = 0;
    uint32_t manifestCount = 0;
    uint32_t applicationCount = 0;
    uint32_t usesSdkDepth = 0;
    bool applicationOpen = false;
    std::set<std::pair<std::string, std::string>> components;

    for (;;) {
        const AxmlParser::EventCode event = parser.next();
        if (event == AxmlParser::EC_END_DOCUMENT) break;
        if (event == AxmlParser::EC_BAD_DOCUMENT) {
            *rejection = Reject(request,
                ManifestParseVerdict::MANIFEST_MALFORMED,
                "binary XML event stream is malformed");
            return false;
        }
        if (event == AxmlParser::EC_END_TAG) {
            if (depth == 0) {
                *rejection = Reject(request,
                    ManifestParseVerdict::MANIFEST_MALFORMED,
                    "binary XML nesting underflow");
                return false;
            }
            size_t endNameLength = 0;
            const char* endName = parser.getElementName(&endNameLength);
            if (endName == nullptr) {
                *rejection = Reject(request,
                    ManifestParseVerdict::MANIFEST_MALFORMED,
                    "end element name is absent");
                return false;
            }
            if (std::string(endName, endNameLength) == "application") {
                applicationOpen = false;
            }
            if (depth == usesSdkDepth) usesSdkDepth = 0;
            --depth;
            continue;
        }
        if (event != AxmlParser::EC_START_TAG) continue;
        ++depth;
        size_t elementLength = 0;
        const char* elementName = parser.getElementName(&elementLength);
        if (elementName == nullptr) {
            *rejection = Reject(request,
                ManifestParseVerdict::MANIFEST_MALFORMED,
                "element name is absent");
            return false;
        }
        const std::string element(elementName, elementLength);
        const size_t chunkOffset = parser.getCurrentOffset();

        if (usesSdkDepth != 0 && depth > usesSdkDepth) {
            // Unknown children and nested extension content are skipped as in Android.
            if (depth == usesSdkDepth + 1 && element == "extension-sdk") {
                ExtensionSdkDeclarationV2 extension;
                if (!ReadSdkAttribute(parser, 0x01010610, &extension.sdk) ||
                    !ReadSdkAttribute(parser, 0x01010611, &extension.minimum)) {
                    *rejection = Reject(request, ManifestParseVerdict::MANIFEST_MALFORMED,
                        "extension SDK attributes are duplicated or malformed");
                    return false;
                }
                sdkDeclarations->back().extensions.push_back(std::move(extension));
            }
            continue;
        }

        if (element == "manifest") {
            ++manifestCount;
            if (manifestCount != 1 || depth != 1) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "manifest root is duplicated or nested");
                return false;
            }
            Attribute packageName;
            Attribute versionName;
            if (!GetUniqueAttribute(parser, "package", &packageName) ||
                !GetUniqueAttribute(parser, "versionName", &versionName)) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "manifest contains duplicate identity attributes");
                return false;
            }
            if (!packageName.present || packageName.text.empty() ||
                !application_attributes::manifest_parser::ReadVersion(parser, version)) {
                *rejection = Reject(request,
                    ManifestParseVerdict::MANIFEST_MALFORMED,
                    "manifest package/version declaration is invalid");
                return false;
            }
            facts->packageName = packageName.text;
            facts->versionCode = version->minor.bits;
            facts->versionName = versionName.text;
            AddProvenance(facts, "packageName", request.artifactSha256,
                manifestSha, chunkOffset);
            AddProvenance(facts, "versionCode", request.artifactSha256,
                manifestSha, chunkOffset);
            AddProvenance(facts, "versionCodeMajor", request.artifactSha256,
                manifestSha, chunkOffset);
            AddProvenance(facts, "versionName", request.artifactSha256,
                manifestSha, chunkOffset);
        } else if (element == "uses-sdk") {
            // Only direct manifest children are declarations; repeated tags replace
            // the complete SDK state after each preceding tag has been validated.
            if (depth != 2 || manifestCount != 1) continue;
            UsesSdkDeclarationV2 sdk;
            if (!ReadSdkAttribute(parser, 0x0101020c, &sdk.minimum) ||
                !ReadSdkAttribute(parser, 0x01010270, &sdk.target) ||
                !ReadSdkAttribute(parser, 0x01010271, &sdk.maximum)) {
                *rejection = Reject(request, ManifestParseVerdict::MANIFEST_MALFORMED,
                    "SDK attributes are duplicated or malformed");
                return false;
            }
            sdkDeclarations->push_back(std::move(sdk));
            usesSdkDepth = depth;
            AddProvenance(facts, "minSdk", request.artifactSha256,
                manifestSha, chunkOffset);
            AddProvenance(facts, "targetSdk", request.artifactSha256,
                manifestSha, chunkOffset);
        } else if (element == "application") {
            ++applicationCount;
            if (applicationCount != 1 || manifestCount != 1 || depth != 2) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "application declaration is duplicated or precedes manifest");
                return false;
            }
            applicationOpen = true;
            Attribute name;
            Attribute label;
            if (!GetUniqueAttribute(parser, "name", &name) ||
                !GetUniqueAttribute(parser, "label", &label)) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "application declaration contains duplicate attributes");
                return false;
            }
            facts->applicationClassName =
                ResolveClassName(name.text, facts->packageName);
            facts->applicationLabel = label.text;
            AddProvenance(facts, "application", request.artifactSha256,
                manifestSha, chunkOffset);
        } else if (element == "activity" || element == "activity-alias" ||
            element == "service" || element == "receiver" ||
            element == "provider") {
            if (applicationCount != 1 || !applicationOpen || depth != 3) {
                *rejection = Reject(request,
                    ManifestParseVerdict::MANIFEST_MALFORMED,
                    "component declaration is outside application");
                return false;
            }
            Attribute name;
            Attribute exported;
            if (!GetUniqueAttribute(parser, "name", &name) ||
                !GetUniqueAttribute(parser, "exported", &exported) ||
                !name.present || name.text.empty()) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "component identity is absent or duplicated");
                return false;
            }
            package_transaction::ManifestComponentFactV1 component;
            component.kind = element;
            component.name = ResolveClassName(name.text, facts->packageName);
            if (exported.present) {
                bool value = false;
                if (!ToBool(exported, &value)) {
                    *rejection = Reject(request,
                        ManifestParseVerdict::MANIFEST_MALFORMED,
                        "component exported declaration is invalid");
                    return false;
                }
                component.exported = value;
            }
            if (!components.insert({component.kind, component.name}).second) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "duplicate component identity");
                return false;
            }
            if (facts->components.size() >= limits.maxComponents) {
                *rejection = Reject(request,
                    ManifestParseVerdict::LIMIT_EXCEEDED,
                    "component count exceeds v1 limit");
                return false;
            }
            const size_t index = facts->components.size();
            facts->components.push_back(std::move(component));
            AddProvenance(facts, "components[" + std::to_string(index) + "]",
                request.artifactSha256, manifestSha, chunkOffset);
        } else if (element == "uses-permission") {
            Attribute name;
            if (!GetUniqueAttribute(parser, "name", &name) ||
                !name.present || name.text.empty()) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "uses-permission identity is absent or duplicated");
                return false;
            }
            facts->requestedPermissions.push_back(name.text);
            AddProvenance(facts, "requestedPermissions[" +
                std::to_string(facts->requestedPermissions.size() - 1) + "]",
                request.artifactSha256, manifestSha, chunkOffset);
        } else if (element == "permission") {
            Attribute name;
            if (!GetUniqueAttribute(parser, "name", &name) ||
                !name.present || name.text.empty()) {
                *rejection = Reject(request,
                    ManifestParseVerdict::DECLARATION_CONFLICT,
                    "permission identity is absent or duplicated");
                return false;
            }
            facts->declaredPermissions.push_back(name.text);
            AddProvenance(facts, "declaredPermissions[" +
                std::to_string(facts->declaredPermissions.size() - 1) + "]",
                request.artifactSha256, manifestSha, chunkOffset);
        }
    }
    if (depth != 0 || manifestCount != 1 || applicationCount != 1 ||
        facts->packageName.empty()) {
        *rejection = Reject(request, ManifestParseVerdict::MANIFEST_MALFORMED,
            "required manifest/application structure is incomplete");
        return false;
    }
    return true;
}

}  // namespace

ManifestFactsParserV1::ManifestFactsParserV1(ManifestParserLimitsV1 limits)
    : limits_(std::move(limits))
{
}

ManifestParseReceiptV1 ManifestFactsParserV1::Parse(
    const ManifestParseRequestV1& request, ManifestParseFault fault) const
{
    if (request.schemaVersion != 1 || request.requestId.empty() ||
        request.artifactFd < 0 || request.byteLength == 0 ||
        !IsLowerHexSha256(request.artifactSha256)) {
        return Reject(request, ManifestParseVerdict::INVALID_ENVELOPE,
            "v1 request identity is incomplete or schema is unsupported");
    }
    if (request.userId != 0 || request.artifactSet.schemaVersion != 1 ||
        request.artifactSet.artifacts.size() != 1 ||
        request.artifactSet.artifacts.front().role !=
            package_transaction::ArtifactRole::BASE) {
        return Reject(request, ManifestParseVerdict::NOT_SUPPORTED,
            "v1 supports one base APK for primary user");
    }
    const auto& descriptor = request.artifactSet.artifacts.front();
    if (descriptor.artifactId.empty() ||
        descriptor.byteLength != request.byteLength ||
        descriptor.sha256 != request.artifactSha256 ||
        !descriptor.bytes.empty()) {
        return Reject(request, ManifestParseVerdict::ARTIFACT_SET_MISMATCH,
            "artifact-set descriptor differs from immutable fd identity");
    }
    const std::string computedSet =
        package_transaction::ComputeArtifactSetDigest(request.artifactSet);
    if (!IsLowerHexSha256(request.artifactSet.artifactSetDigest) ||
        request.artifactSet.artifactSetDigest != computedSet) {
        return Reject(request, ManifestParseVerdict::ARTIFACT_SET_MISMATCH,
            "artifactSetDigest differs from canonical v1 descriptor");
    }

    std::vector<uint8_t> archive;
    ManifestParseReceiptV1 rejection;
    if (!ReadIdentityBytes(request, limits_, &archive, &rejection)) {
        return rejection;
    }
    if (fault == ManifestParseFault::INTERRUPT_AFTER_IDENTITY_READ) {
        return Reject(request, ManifestParseVerdict::INTERRUPTED,
            "fault seam interrupted after immutable identity read");
    }
    const std::string actualSha = Sha256Hex(archive);
    if (actualSha != request.artifactSha256) {
        return Reject(request, ManifestParseVerdict::DIGEST_MISMATCH,
            "fd bytes differ from declared SHA-256");
    }
    if (fault == ManifestParseFault::FORCE_INTERNAL_ERROR) {
        return Reject(request, ManifestParseVerdict::INTERNAL_ERROR,
            "fault seam forced parser internal failure");
    }

    ZipManifest manifest;
    if (!ExtractManifest(request, limits_, archive, &manifest, &rejection)) {
        return rejection;
    }
    ManifestFactsOutputV1 facts;
    facts.artifactSetDigest = computedSet;
    facts.parserVersion = PARSER_VERSION;
    ManifestVersionV2 version;
    std::vector<UsesSdkDeclarationV2> sdkDeclarations;
    if (!ParseAxml(request, limits_, manifest, &facts, &version, &sdkDeclarations, &rejection)) {
        return rejection;
    }

    std::optional<SdkCompatibilityResultV2> compatibility;
    std::optional<ResolvedSdkV2> sdk;
    if (request.sdkProfile) {
        compatibility = application_attributes::EvaluateSdkRequirements(
            sdkDeclarations, *request.sdkProfile, request.apkInApex);
        sdk = compatibility->resolved;
    } else {
        sdk = application_attributes::ResolveNumericSdkDeclarations(sdkDeclarations);
        if (!sdk || request.apkInApex) {
            sdk.reset();
            compatibility = SdkCompatibilityResultV2{SdkCompatibilityVerdictV2::PROFILE_UNAVAILABLE,
                SdkFailureStageV2::PROFILE, "SDK compatibility requires an explicit runtime profile", {}};
        }
    }
    if (!sdk) {
        auto rejected = Reject(request, ManifestParseVerdict::NOT_SUPPORTED, compatibility->reason);
        rejected.sdkDeclarations = std::move(sdkDeclarations);
        rejected.sdkCompatibility = std::move(compatibility);
        return rejected;
    }
    facts.minSdk = static_cast<uint32_t>(sdk->minimum);
    facts.targetSdk = static_cast<uint32_t>(sdk->target);

    ManifestParseReceiptV1 receipt;
    receipt.requestId = request.requestId;
    receipt.verdict = ManifestParseVerdict::PARSED;
    receipt.reason = "complete facts parsed from immutable artifact bytes";
    receipt.artifactSha256 = actualSha;
    receipt.artifactSetDigest = computedSet;
    receipt.parserVersion = PARSER_VERSION;
    receipt.facts = std::move(facts);
    receipt.versionV2 = version;
    receipt.sdkDeclarations = std::move(sdkDeclarations);
    receipt.sdkCompatibility = std::move(compatibility);
    return receipt;
}

const char* ManifestParseVerdictName(ManifestParseVerdict verdict)
{
    switch (verdict) {
        case ManifestParseVerdict::PARSED: return "PARSED";
        case ManifestParseVerdict::INVALID_ENVELOPE: return "INVALID_ENVELOPE";
        case ManifestParseVerdict::NOT_SUPPORTED: return "NOT_SUPPORTED";
        case ManifestParseVerdict::FD_NOT_SEALED: return "FD_NOT_SEALED";
        case ManifestParseVerdict::BYTE_LENGTH_MISMATCH:
            return "BYTE_LENGTH_MISMATCH";
        case ManifestParseVerdict::DIGEST_MISMATCH: return "DIGEST_MISMATCH";
        case ManifestParseVerdict::ARTIFACT_SET_MISMATCH:
            return "ARTIFACT_SET_MISMATCH";
        case ManifestParseVerdict::ZIP_MALFORMED: return "ZIP_MALFORMED";
        case ManifestParseVerdict::MANIFEST_NOT_FOUND:
            return "MANIFEST_NOT_FOUND";
        case ManifestParseVerdict::MANIFEST_DUPLICATE:
            return "MANIFEST_DUPLICATE";
        case ManifestParseVerdict::MANIFEST_MALFORMED:
            return "MANIFEST_MALFORMED";
        case ManifestParseVerdict::DECLARATION_CONFLICT:
            return "DECLARATION_CONFLICT";
        case ManifestParseVerdict::LIMIT_EXCEEDED: return "LIMIT_EXCEEDED";
        case ManifestParseVerdict::IO_ERROR: return "IO_ERROR";
        case ManifestParseVerdict::INTERRUPTED: return "INTERRUPTED";
        case ManifestParseVerdict::INTERNAL_ERROR: return "INTERNAL_ERROR";
    }
    return "INTERNAL_ERROR";
}

std::string ManifestParseReceiptJson(const ManifestParseReceiptV1& receipt)
{
    std::ostringstream out;
    out << "{\"artifactSetDigest\":" << Json(receipt.artifactSetDigest)
        << ",\"artifactSha256\":" << Json(receipt.artifactSha256)
        << ",\"facts\":";
    if (!receipt.facts.has_value()) {
        out << "null";
    } else {
        const auto& facts = *receipt.facts;
        out << "{\"applicationClassName\":"
            << Json(facts.applicationClassName)
            << ",\"applicationLabel\":" << Json(facts.applicationLabel)
            << ",\"artifactSetDigest\":" << Json(facts.artifactSetDigest)
            << ",\"components\":[";
        for (size_t index = 0; index < facts.components.size(); ++index) {
            if (index != 0) out << ",";
            const auto& component = facts.components[index];
            out << "{\"exported\":";
            if (component.exported.has_value()) {
                out << (*component.exported ? "true" : "false");
            } else {
                out << "null";
            }
            out << ",\"kind\":" << Json(component.kind)
                << ",\"name\":" << Json(component.name) << "}";
        }
        out << "],\"minSdk\":" << facts.minSdk
            << ",\"packageName\":" << Json(facts.packageName)
            << ",\"parserVersion\":" << Json(facts.parserVersion)
            << ",\"provenance\":[";
        for (size_t index = 0; index < facts.provenance.size(); ++index) {
            if (index != 0) out << ",";
            const auto& provenance = facts.provenance[index];
            out << "{\"artifactSha256\":" << Json(provenance.artifactSha256)
                << ",\"field\":" << Json(provenance.field)
                << ",\"manifestChunkOffset\":"
                << provenance.manifestChunkOffset
                << ",\"manifestEntrySha256\":"
                << Json(provenance.manifestEntrySha256) << "}";
        }
        out << "],\"requestedPermissions\":[";
        for (size_t index = 0; index < facts.requestedPermissions.size();
             ++index) {
            if (index != 0) out << ",";
            out << Json(facts.requestedPermissions[index]);
        }
        out << "],\"declaredPermissions\":[";
        for (size_t index = 0; index < facts.declaredPermissions.size();
             ++index) {
            if (index != 0) out << ",";
            out << Json(facts.declaredPermissions[index]);
        }
        out << "],\"targetSdk\":" << facts.targetSdk
            << ",\"versionCode\":" << facts.versionCode
            << ",\"versionName\":" << Json(facts.versionName) << "}";
    }
    out << ",\"versionV2\":";
    using Source = VersionValueSourceV2;
    const auto& version = receipt.versionV2;
    const auto known = [](const VersionFieldV2& field) {
        return (field.source == Source::EXPLICIT && field.present) ||
            (field.source == Source::DEFAULT && field.bits == 0);
    };
    if (receipt.verdict != ManifestParseVerdict::PARSED || !receipt.facts ||
        !known(version.major) || !known(version.minor)) {
        out << "null";
    } else {
        const auto source = [](Source value) {
            return value == Source::EXPLICIT ? "explicit" : "default";
        };
        out << "{\"schemaVersion\":2,\"major\":" << Json(std::to_string(version.major.bits))
            << ",\"minor\":" << Json(std::to_string(version.minor.bits))
            << ",\"majorPresent\":" << (version.major.present ? "true" : "false")
            << ",\"minorPresent\":" << (version.minor.present ? "true" : "false")
            << ",\"majorSource\":" << Json(source(version.major.source))
            << ",\"minorSource\":" << Json(source(version.minor.source)) << "}";
    }
    out << ",\"parserVersion\":" << Json(receipt.parserVersion)
        << ",\"reason\":" << Json(receipt.reason)
        << ",\"requestId\":" << Json(receipt.requestId)
        << ",\"verdict\":" << Json(ManifestParseVerdictName(receipt.verdict))
        << "}";
    return out.str();
}

}  // namespace oh_adapter::manifest_facts
