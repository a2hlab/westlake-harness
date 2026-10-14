#include "apk_native_inventory.h"
#include "sha256.h"
#include <unzip.h>
#include <algorithm>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <memory>
#include <stdexcept>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

namespace oh_adapter {
namespace {
using V = NativeInventoryVerdict;
struct Failure : std::runtime_error {
    V verdict;
    std::optional<NativeEntryVerdict> entry;
    std::optional<package_transaction::ElfPrepassVerdict> elf;
    Failure(V v, const std::string& text) : std::runtime_error(text), verdict(v) {}
};
void Check(bool ok, V verdict, const char* reason)
{ if (!ok) throw Failure(verdict, reason); }
struct Fd {
    int value;
    explicit Fd(int input) : value(fcntl(input, F_DUPFD_CLOEXEC, 0)) {}
    ~Fd() { if (value >= 0) close(value); }
    Fd(const Fd&) = delete;
    Fd& operator=(const Fd&) = delete;
};
struct Mapping {
    const uint8_t* data;
    size_t size;
    Mapping(int fd, size_t length) : data(static_cast<const uint8_t*>(
        mmap(nullptr, length, PROT_READ, MAP_PRIVATE, fd, 0))), size(length)
    { Check(data != MAP_FAILED, V::IO_ERROR, "Cannot map sealed APK"); }
    ~Mapping() { munmap(const_cast<uint8_t*>(data), size); }
    Mapping(const Mapping&) = delete;
    Mapping& operator=(const Mapping&) = delete;
    uint64_t Number(uint64_t at, size_t width) const
    {
        Check(at <= size && width <= size - at, V::CORRUPT_APK, "ZIP field is outside sealed APK");
        uint64_t value = 0;
        for (size_t i = 0; i < width; ++i) value |= static_cast<uint64_t>(data[at + i]) << (8 * i);
        return value;
    }
};
std::string Digest(const uint8_t* bytes, size_t count)
{
    uint8_t result[32]; sha256(bytes, count, result);
    constexpr char hex[] = "0123456789abcdef";
    std::string text; text.reserve(64);
    for (uint8_t byte : result) { text += hex[byte >> 4]; text += hex[byte & 15]; }
    return text;
}
bool IsDigest(const std::string& digest)
{
    return digest.size() == 64 && std::all_of(digest.begin(), digest.end(), [](char c) {
        return (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
    });
}
struct Directory { uint64_t start, end, count; };
Directory ValidateDirectory(const Mapping& map, uint64_t maxEntries)
{
    // Bound the backwards EOCD search by the ZIP comment's uint16 length.
    Check(map.size >= 22, V::CORRUPT_APK, "ZIP end record is missing");
    const auto first = map.size > 22 + 65535 ? map.size - 22 - 65535 : 0;
    size_t end = map.size - 22;
    for (;;) {
        if (map.Number(end, 4) == 0x06054b50 && map.Number(end + 20, 2) == map.size - end - 22) break;
        Check(end > first, V::CORRUPT_APK, "ZIP end record is malformed"); --end;
    }
    Check(map.Number(end + 4, 2) == 0 && map.Number(end + 6, 2) == 0,
        V::CORRUPT_APK, "Spanned APK ZIP is unsupported");
    uint64_t count = map.Number(end + 10, 2), bytes = map.Number(end + 12, 4);
    uint64_t start = map.Number(end + 16, 4), directoryEnd = end;
    Check(map.Number(end + 8, 2) == count, V::CORRUPT_APK, "ZIP entry counts disagree");
    if (count == 0xffff || bytes == 0xffffffff || start == 0xffffffff) {
        Check(end >= 20 && map.Number(end - 20, 4) == 0x07064b50 &&
            map.Number(end - 16, 4) == 0 && map.Number(end - 4, 4) == 1,
            V::CORRUPT_APK, "ZIP64 locator is invalid");
        const uint64_t record = map.Number(end - 12, 8);
        Check(record <= end - 20 && end - 20 - record >= 56 &&
            map.Number(record, 4) == 0x06064b50 && map.Number(record + 4, 8) == end - 20 - record - 12,
            V::CORRUPT_APK, "ZIP64 end record is invalid");
        Check(map.Number(record + 16, 4) == 0 && map.Number(record + 20, 4) == 0 &&
            map.Number(record + 24, 8) == map.Number(record + 32, 8),
            V::CORRUPT_APK, "ZIP64 disk or count is invalid");
        count = map.Number(record + 32, 8); bytes = map.Number(record + 40, 8);
        start = map.Number(record + 48, 8); directoryEnd = record;
    }
    Check(count <= maxEntries, V::LIMIT_EXCEEDED, "APK ZIP has too many entries");
    Check(start <= directoryEnd && bytes == directoryEnd - start,
        V::CORRUPT_APK, "ZIP central directory range disagrees with end record");
    uint64_t at = start;
    for (uint64_t i = 0; i < count; ++i) {
        Check(at <= directoryEnd && directoryEnd - at >= 46 && map.Number(at, 4) == 0x02014b50,
            V::CORRUPT_APK, "ZIP central directory entry is invalid");
        const uint64_t length = 46 + map.Number(at + 28, 2) + map.Number(at + 30, 2) + map.Number(at + 32, 2);
        Check(length <= directoryEnd - at && map.Number(at + 34, 2) == 0,
            V::CORRUPT_APK, "ZIP central entry range or disk is invalid");
        at += length;
    }
    Check(at == directoryEnd, V::CORRUPT_APK, "ZIP count leaves unaccounted central directory bytes");
    return {start, directoryEnd, count};
}
// Minizip reads the mapping of the borrowed, sealed FD. No filename is resolved,
// and neither lseek nor a shared file-description offset is used.
struct Stream { const Mapping& map; uint64_t position = 0; bool error = false; };
voidpf ZCALLBACK Open(voidpf opaque, const void*, int mode)
{
    auto* stream = static_cast<Stream*>(opaque);
    if ((mode & ZLIB_FILEFUNC_MODE_READWRITEFILTER) != ZLIB_FILEFUNC_MODE_READ) return nullptr;
    stream->position = 0; return stream;
}
uLong ZCALLBACK Read(voidpf, voidpf handle, void* output, uLong count)
{
    auto& stream = *static_cast<Stream*>(handle);
    const auto actual = std::min<uint64_t>(count, stream.map.size - stream.position);
    std::memcpy(output, stream.map.data + stream.position, actual);
    stream.position += actual; return static_cast<uLong>(actual);
}
uLong ZCALLBACK Write(voidpf, voidpf handle, const void*, uLong)
{ static_cast<Stream*>(handle)->error = true; return 0; }
ZPOS64_T ZCALLBACK Tell(voidpf, voidpf handle)
{ return static_cast<Stream*>(handle)->position; }
long ZCALLBACK Seek(voidpf, voidpf handle, ZPOS64_T offset, int origin)
{
    auto& stream = *static_cast<Stream*>(handle);
    uint64_t base = 0;
    if (origin == ZLIB_FILEFUNC_SEEK_CUR) base = stream.position;
    else if (origin == ZLIB_FILEFUNC_SEEK_END) base = stream.map.size;
    else if (origin != ZLIB_FILEFUNC_SEEK_SET) { stream.error = true; return -1; }
    if (offset > stream.map.size - base) { stream.error = true; return -1; }
    stream.position = base + offset; return 0;
}
int ZCALLBACK Close(voidpf, voidpf) { return 0; }
int ZCALLBACK Error(voidpf, voidpf handle) { return static_cast<Stream*>(handle)->error; }
struct ZipClose { void operator()(void* zip) const { if (zip) unzClose(zip); } };
using Zip = std::unique_ptr<void, ZipClose>;
std::vector<uint8_t> ReadNativeBytes(const Mapping& map, uint64_t offset, const unz_file_info64& info)
{
    Check(offset <= map.size && info.compressed_size <= map.size - offset,
        V::CORRUPT_APK, "Native data range exceeds sealed APK");
    const auto* input = map.data + offset;
    std::vector<uint8_t> bytes(static_cast<size_t>(info.uncompressed_size) + 1);
    if (info.compression_method == 0) {
        Check(info.compressed_size == info.uncompressed_size, V::CORRUPT_APK, "STORE lengths disagree");
        std::memcpy(bytes.data(), input, info.uncompressed_size);
    } else {
        z_stream stream{};
        Check(inflateInit2(&stream, -MAX_WBITS) == Z_OK, V::IO_ERROR, "Cannot initialize DEFLATE reader");
        stream.next_in = const_cast<Bytef*>(input); stream.avail_in = info.compressed_size;
        stream.next_out = bytes.data(); stream.avail_out = bytes.size();
        const int code = inflate(&stream, Z_FINISH);
        const bool complete = code == Z_STREAM_END && stream.total_in == info.compressed_size &&
            stream.total_out == info.uncompressed_size;
        inflateEnd(&stream);
        Check(complete, V::CORRUPT_APK, "Native DEFLATE stream is incomplete or has trailing bytes");
    }
    bytes.resize(info.uncompressed_size);
    Check(crc32(0, bytes.data(), bytes.size()) == info.crc, V::CORRUPT_APK, "Native ZIP CRC mismatch");
    return bytes;
}
ApkNativeInventory Scan(const Mapping& map, const Directory& directory, const std::string& digest,
    const NativeInventoryProfile& profile, const ApkNativeInventoryLimits& limits)
{
    ApkNativeInventory result; result.apkSha256 = digest; result.apkByteLength = map.size;
    result.verdict = V::NO_NATIVE; result.reason = "APK has no native shared objects";
    if (directory.count == 0) return result;
    Stream stream{map};
    zlib_filefunc64_def io{Open, Read, Write, Tell, Seek, Close, Error, &stream};
    Zip zip(unzOpen2_64(nullptr, &io));
    Check(zip != nullptr, V::CORRUPT_APK, "Cannot read ZIP directory from sealed APK");
    unz_global_info64 global{};
    Check(unzGetGlobalInfo64(zip.get(), &global) == UNZ_OK && global.number_entry == directory.count &&
        unzGoToFirstFile(zip.get()) == UNZ_OK, V::CORRUPT_APK, "ZIP directory enumeration failed");
    uint64_t totalBytes = 0;
    std::set<std::string> seen;
    // Recognized formats are not runtime capabilities. Only profile.abis can
    // declare support; every recognized ELF is still inspected when unmatched.
    const NativeAbiProfile recognized{true, {"armeabi", "armeabi-v7a", "arm64-v8a", "x86", "x86_64", "riscv64"}};
    for (uint64_t index = 0; index < directory.count; ++index) {
        unz_file_info64 info{};
        Check(unzGetCurrentFileInfo64(zip.get(), &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK,
            V::CORRUPT_APK, "ZIP entry metadata is invalid");
        Check(info.size_filename <= 4096, V::INVALID_ENTRY, "ZIP entry name exceeds limit");
        std::vector<char> name(info.size_filename + 1);
        Check(unzGetCurrentFileInfo64(zip.get(), &info, name.data(), name.size(), nullptr, 0, nullptr, 0) == UNZ_OK,
            V::CORRUPT_APK, "ZIP entry name cannot be read");
        ApkNativeEntryInput entry; entry.entryName.assign(name.data(), info.size_filename);
        entry.apkSha256 = digest; entry.zipVersionMadeBy = info.version; entry.zipExternalAttributes = info.external_fa;
        // Empty capability set asks the production name validator to classify
        // and reserve native names without pretending to inspect absent bytes.
        const auto classified = ValidateApkNativeEntry(entry, {true, {}}, seen);
        if (classified.verdict != NativeEntryVerdict::NOT_NATIVE &&
            classified.verdict != NativeEntryVerdict::ABI_UNSUPPORTED) {
            Failure failure(V::INVALID_ENTRY, classified.reason); failure.entry = classified.verdict; throw failure;
        }
        if (classified.verdict == NativeEntryVerdict::ABI_UNSUPPORTED) {
            Check((info.flag & (1U | 64U)) == 0 && (info.compression_method == 0 || info.compression_method == 8),
                V::CORRUPT_APK, "Encrypted or unsupported native compression");
            Check(info.uncompressed_size <= limits.maxEntryBytes && info.compressed_size <= limits.maxEntryBytes &&
                info.uncompressed_size < std::numeric_limits<uInt>::max() && info.compressed_size <= std::numeric_limits<uInt>::max() &&
                totalBytes <= limits.maxTotalNativeBytes && info.uncompressed_size <= limits.maxTotalNativeBytes - totalBytes,
                V::LIMIT_EXCEEDED, "Native entries exceed byte limits");
            totalBytes += info.uncompressed_size;
            Check(unzOpenCurrentFile3(zip.get(), nullptr, nullptr, 1, nullptr) == UNZ_OK,
                V::CORRUPT_APK, "Native local ZIP header is invalid");
            const uint64_t dataOffset = unzGetCurrentFileZStreamPos64(zip.get());
            const int extraLength = unzGetLocalExtrafield(zip.get(), nullptr, 0);
            Check(extraLength >= 0 && dataOffset >= 30 + entry.entryName.size() + static_cast<uint64_t>(extraLength) &&
                dataOffset <= directory.start && info.compressed_size <= directory.start - dataOffset,
                V::CORRUPT_APK, "Native local data range is invalid");
            const uint64_t local = dataOffset - 30 - entry.entryName.size() - extraLength;
            Check(map.Number(local, 4) == 0x04034b50 && map.Number(local + 6, 2) == info.flag &&
                std::memcmp(map.data + local + 30, entry.entryName.data(), entry.entryName.size()) == 0,
                V::CORRUPT_APK, "Local and central ZIP names or flags disagree");
            entry.bytes = ReadNativeBytes(map, dataOffset, info);
            Check(unzCloseCurrentFile(zip.get()) == UNZ_OK, V::CORRUPT_APK, "Cannot finish native ZIP entry");
            entry.entrySha256 = Digest(entry.bytes.data(), entry.bytes.size());
            // Canonical three-component shape was established by the validator.
            const auto slash = entry.entryName.find('/', 4);
            ApkNativeArtifact artifact; artifact.entryName = entry.entryName;
            artifact.abi = entry.entryName.substr(4, slash - 4); artifact.entrySha256 = entry.entrySha256;
            artifact.dataOffset = dataOffset; artifact.compressedSize = info.compressed_size;
            artifact.uncompressedSize = info.uncompressed_size; artifact.compressionMethod = info.compression_method;
            std::set<std::string> singleEntry;
            auto validation = ValidateApkNativeEntry(entry, recognized, singleEntry);
            if (validation.verdict == NativeEntryVerdict::VALID_NATIVE) {
                artifact.elfFacts = std::move(validation.elfFacts);
                artifact.supportedByProfile = profile.abis.available && std::find(profile.abis.supportedAbis.begin(),
                    profile.abis.supportedAbis.end(), artifact.abi) != profile.abis.supportedAbis.end();
            } else if (validation.verdict != NativeEntryVerdict::ABI_UNSUPPORTED) {
                Failure failure(V::ELF_REJECTED, validation.reason); failure.entry = validation.verdict;
                failure.elf = validation.elfVerdict; throw failure;
            }
            artifact.directlyLoadable = info.compression_method == 0 && profile.pageSize != 0 &&
                dataOffset % profile.pageSize == 0;
            result.artifacts.push_back(std::move(artifact));
        }
        const int next = unzGoToNextFile(zip.get());
        Check(next == (index + 1 == directory.count ? UNZ_END_OF_LIST_OF_FILE : UNZ_OK),
            V::CORRUPT_APK, "ZIP enumeration count or next entry is invalid");
    }
    if (result.artifacts.empty()) return result;
    Check(profile.abis.available && profile.pageSize != 0 &&
        (profile.pageSize & (profile.pageSize - 1)) == 0, V::PROFILE_UNAVAILABLE, "Runtime ABI/page-size facts are unavailable");
    const bool matched = std::any_of(result.artifacts.begin(), result.artifacts.end(),
        [](const auto& item) { return item.supportedByProfile; });
    result.verdict = matched ? V::MATCHED_NATIVE : V::NO_MATCHING_ABIS;
    result.reason = matched ? "Native inventory contains supported ABI facts" : "Native entries exist but no runtime ABI matches";
    return result;
}
}
ApkNativeInventory ReadApkNativeInventory(int sealedFd, uint64_t expectedLength,
    const std::string& expectedSha256, const NativeInventoryProfile& profile,
    const ApkNativeInventoryLimits& limits)
{
    try {
        Check(sealedFd >= 0 && expectedLength != 0 && IsDigest(expectedSha256), V::INVALID_INPUT, "Invalid sealed APK identity input");
        Check(expectedLength <= limits.maxApkBytes, V::LIMIT_EXCEEDED, "APK exceeds byte limit");
        Check(expectedLength <= std::numeric_limits<size_t>::max() && expectedLength <= static_cast<uint64_t>(std::numeric_limits<off_t>::max()),
            V::LIMIT_EXCEEDED, "APK exceeds host addressable range");
        Fd owned(sealedFd); Check(owned.value >= 0, V::IO_ERROR, "Cannot retain APK descriptor");
        struct stat facts{};
        Check(fstat(owned.value, &facts) == 0, V::IO_ERROR, "Cannot stat APK descriptor");
        Check(S_ISREG(facts.st_mode) && facts.st_size >= 0 && static_cast<uint64_t>(facts.st_size) == expectedLength,
            V::INVALID_INPUT, "APK descriptor length or type disagrees with identity");
        constexpr int required = F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL;
        const int seals = fcntl(owned.value, F_GET_SEALS);
        Check(seals >= 0 && (seals & required) == required, V::FD_NOT_SEALED, "APK descriptor is not fully sealed");
        Mapping map(owned.value, expectedLength);
        Check(Digest(map.data, map.size) == expectedSha256, V::DIGEST_MISMATCH, "Sealed APK digest disagrees with verified identity");
        const auto directory = ValidateDirectory(map, limits.maxEntries);
        return Scan(map, directory, expectedSha256, profile, limits);
    } catch (const Failure& failure) {
        ApkNativeInventory result; result.verdict = failure.verdict; result.reason = failure.what();
        result.entryVerdict = failure.entry; result.elfVerdict = failure.elf; return result;
    } catch (const std::bad_alloc&) {
        ApkNativeInventory result; result.verdict = V::LIMIT_EXCEEDED; result.reason = "Native inventory allocation failed"; return result;
    } catch (const std::exception& exception) {
        ApkNativeInventory result; result.verdict = V::IO_ERROR; result.reason = exception.what(); return result;
    }
}
}
