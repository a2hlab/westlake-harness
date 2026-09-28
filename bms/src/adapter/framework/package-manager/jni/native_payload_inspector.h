/*
 * Typed APK native-payload inspection.
 *
 * This header is dependency-free so the exact production scanner can also be
 * exercised by host fixture tests. It reads only the ZIP central directory;
 * APK signature verification remains the caller's separate prerequisite.
 */
#ifndef OH_ADAPTER_NATIVE_PAYLOAD_INSPECTOR_H
#define OH_ADAPTER_NATIVE_PAYLOAD_INSPECTOR_H

#include <algorithm>
#include <array>
#include <cstdint>
#include <fstream>
#include <limits>
#include <string>
#include <vector>

namespace oh_adapter {

enum class NativePayloadState : uint8_t {
    NONE = 0,
    SUPPORTED = 1,
    UNSUPPORTED = 2,
    UNREADABLE = 3,
};

struct NativePayloadInfo {
    NativePayloadState state = NativePayloadState::UNREADABLE;
    std::string primaryAbi;
    std::string error;
};

inline const char* NativePayloadStateName(NativePayloadState state)
{
    switch (state) {
        case NativePayloadState::NONE:
            return "none";
        case NativePayloadState::SUPPORTED:
            return "supported";
        case NativePayloadState::UNSUPPORTED:
            return "unsupported";
        case NativePayloadState::UNREADABLE:
            return "unreadable";
    }
    return "unreadable";
}

namespace native_payload_detail {

constexpr uint32_t ZIP_EOCD_SIGNATURE = 0x06054b50;
constexpr uint32_t ZIP_CENTRAL_SIGNATURE = 0x02014b50;
constexpr size_t ZIP_EOCD_SIZE = 22;
constexpr size_t ZIP_MAX_COMMENT = 65535;
constexpr size_t ZIP_CENTRAL_HEADER_SIZE = 46;

inline uint16_t ReadLe16(const unsigned char* bytes)
{
    return static_cast<uint16_t>(bytes[0]) |
        static_cast<uint16_t>(static_cast<uint16_t>(bytes[1]) << 8);
}

inline uint32_t ReadLe32(const unsigned char* bytes)
{
    return static_cast<uint32_t>(bytes[0]) |
        (static_cast<uint32_t>(bytes[1]) << 8) |
        (static_cast<uint32_t>(bytes[2]) << 16) |
        (static_cast<uint32_t>(bytes[3]) << 24);
}

inline bool ReadAt(std::ifstream& input, uint64_t offset, unsigned char* data, size_t size)
{
    if (offset > static_cast<uint64_t>(std::numeric_limits<std::streamoff>::max())) {
        return false;
    }
    input.clear();
    input.seekg(static_cast<std::streamoff>(offset), std::ios::beg);
    if (!input.good()) {
        return false;
    }
    input.read(reinterpret_cast<char*>(data), static_cast<std::streamsize>(size));
    return input.good() || input.gcount() == static_cast<std::streamsize>(size);
}

inline bool IsRootNativeDso(const std::string& entryName, std::string* abi)
{
    constexpr const char* prefix = "lib/";
    if (entryName.compare(0, 4, prefix) != 0) {
        return false;
    }
    const size_t abiEnd = entryName.find('/', 4);
    if (abiEnd == std::string::npos || abiEnd == 4 ||
        entryName.find('/', abiEnd + 1) != std::string::npos) {
        return false;
    }
    const std::string fileName = entryName.substr(abiEnd + 1);
    if (fileName.size() <= 3 || fileName.compare(fileName.size() - 3, 3, ".so") != 0) {
        return false;
    }
    *abi = entryName.substr(4, abiEnd - 4);
    return true;
}

}  // namespace native_payload_detail

inline NativePayloadInfo InspectApkNativePayload(const std::string& apkPath)
{
    using namespace native_payload_detail;

    std::ifstream input(apkPath, std::ios::binary);
    if (!input.is_open()) {
        return {NativePayloadState::UNREADABLE, "", "open failed"};
    }
    input.seekg(0, std::ios::end);
    const std::streamoff end = input.tellg();
    if (end < static_cast<std::streamoff>(ZIP_EOCD_SIZE)) {
        return {NativePayloadState::UNREADABLE, "", "file is too small for ZIP EOCD"};
    }
    const uint64_t fileSize = static_cast<uint64_t>(end);
    const uint64_t tailSize = std::min<uint64_t>(
        fileSize, static_cast<uint64_t>(ZIP_EOCD_SIZE + ZIP_MAX_COMMENT));
    const uint64_t tailOffset = fileSize - tailSize;
    std::vector<unsigned char> tail(static_cast<size_t>(tailSize));
    if (!ReadAt(input, tailOffset, tail.data(), tail.size())) {
        return {NativePayloadState::UNREADABLE, "", "ZIP tail read failed"};
    }

    size_t eocdInTail = std::string::npos;
    for (size_t index = tail.size() - ZIP_EOCD_SIZE + 1; index-- > 0;) {
        if (ReadLe32(tail.data() + index) != ZIP_EOCD_SIGNATURE) {
            continue;
        }
        const uint16_t commentSize = ReadLe16(tail.data() + index + 20);
        if (tailOffset + index + ZIP_EOCD_SIZE + commentSize == fileSize) {
            eocdInTail = index;
            break;
        }
    }
    if (eocdInTail == std::string::npos) {
        return {NativePayloadState::UNREADABLE, "", "ZIP EOCD not found"};
    }

    const unsigned char* eocd = tail.data() + eocdInTail;
    const uint16_t diskNumber = ReadLe16(eocd + 4);
    const uint16_t centralDisk = ReadLe16(eocd + 6);
    const uint16_t entriesOnDisk = ReadLe16(eocd + 8);
    const uint16_t totalEntries = ReadLe16(eocd + 10);
    const uint32_t centralSize = ReadLe32(eocd + 12);
    const uint32_t centralOffset = ReadLe32(eocd + 16);
    if (diskNumber != 0 || centralDisk != 0 || entriesOnDisk != totalEntries ||
        totalEntries == 0xffff || centralSize == 0xffffffff || centralOffset == 0xffffffff) {
        return {NativePayloadState::UNREADABLE, "", "multi-disk or ZIP64 APK is unsupported"};
    }
    const uint64_t centralEnd = static_cast<uint64_t>(centralOffset) + centralSize;
    const uint64_t eocdOffset = tailOffset + eocdInTail;
    if (centralEnd < centralOffset || centralEnd > eocdOffset) {
        return {NativePayloadState::UNREADABLE, "", "invalid central-directory bounds"};
    }

    bool sawRootNativeDso = false;
    bool sawArm64 = false;
    bool sawArm32 = false;
    uint64_t cursor = centralOffset;
    for (uint16_t entry = 0; entry < totalEntries; ++entry) {
        std::array<unsigned char, ZIP_CENTRAL_HEADER_SIZE> header{};
        if (cursor + header.size() > centralEnd ||
            !ReadAt(input, cursor, header.data(), header.size()) ||
            ReadLe32(header.data()) != ZIP_CENTRAL_SIGNATURE) {
            return {NativePayloadState::UNREADABLE, "", "invalid central-directory entry"};
        }
        const uint16_t nameSize = ReadLe16(header.data() + 28);
        const uint16_t extraSize = ReadLe16(header.data() + 30);
        const uint16_t commentSize = ReadLe16(header.data() + 32);
        const uint64_t recordSize = ZIP_CENTRAL_HEADER_SIZE +
            static_cast<uint64_t>(nameSize) + extraSize + commentSize;
        if (nameSize == 0 || cursor + recordSize < cursor || cursor + recordSize > centralEnd) {
            return {NativePayloadState::UNREADABLE, "", "invalid central-directory record size"};
        }
        std::vector<unsigned char> nameBytes(nameSize);
        if (!ReadAt(input, cursor + ZIP_CENTRAL_HEADER_SIZE, nameBytes.data(), nameBytes.size())) {
            return {NativePayloadState::UNREADABLE, "", "ZIP entry-name read failed"};
        }
        const std::string entryName(nameBytes.begin(), nameBytes.end());
        std::string abi;
        if (IsRootNativeDso(entryName, &abi)) {
            sawRootNativeDso = true;
            sawArm64 = sawArm64 || abi == "arm64-v8a";
            sawArm32 = sawArm32 || abi == "armeabi-v7a";
        }
        cursor += recordSize;
    }
    if (cursor != centralEnd) {
        return {NativePayloadState::UNREADABLE, "", "central-directory cursor mismatch"};
    }

    if (!sawRootNativeDso) {
        return {NativePayloadState::NONE, "", ""};
    }
    if (sawArm64) {
        return {NativePayloadState::SUPPORTED, "arm64-v8a", ""};
    }
    if (sawArm32) {
        return {NativePayloadState::SUPPORTED, "armeabi-v7a", ""};
    }
    return {NativePayloadState::UNSUPPORTED, "", "no supported ABI for native payload"};
}

}  // namespace oh_adapter

#endif  // OH_ADAPTER_NATIVE_PAYLOAD_INSPECTOR_H
