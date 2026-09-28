#include "apk_native_inventory.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <array>
#include <cerrno>
#include <dirent.h>
#include <fcntl.h>
#include <fstream>
#include <iterator>
#include <sys/mman.h>
#include <unistd.h>

namespace {
using namespace manifest_fixture;
using namespace oh_adapter;
using V = NativeInventoryVerdict;
using Bytes = std::vector<uint8_t>;
struct Entry { std::string name; Bytes bytes; bool deflate = false; size_t alignment = 1; };
Bytes Elf(const std::string& name)
{
    std::ifstream input(std::string(ELF_FIXTURE_DIRECTORY) + "/" + name, std::ios::binary);
    Require(input.good(), "ELF fixture available");
    return Bytes(std::istreambuf_iterator<char>(input), {});
}
Bytes Deflate(const Bytes& input)
{
    z_stream stream{};
    Require(deflateInit2(&stream, Z_DEFAULT_COMPRESSION, Z_DEFLATED, -MAX_WBITS, 8,
        Z_DEFAULT_STRATEGY) == Z_OK, "fixture deflate init");
    Bytes output(compressBound(input.size()));
    stream.next_in = const_cast<Bytef*>(input.data()); stream.avail_in = input.size();
    stream.next_out = output.data(); stream.avail_out = output.size();
    const int rc = deflate(&stream, Z_FINISH);
    const auto size = stream.total_out;
    deflateEnd(&stream);
    Require(rc == Z_STREAM_END, "fixture deflate complete");
    output.resize(size); return output;
}
Bytes Zip(const std::vector<Entry>& entries)
{
    struct Central { Entry entry; Bytes packed; uint32_t offset, crc; };
    Bytes bytes; std::vector<Central> central;
    for (const auto& entry : entries) {
        Central c{entry, entry.deflate ? Deflate(entry.bytes) : entry.bytes,
            static_cast<uint32_t>(bytes.size()), static_cast<uint32_t>(crc32(0, entry.bytes.data(), entry.bytes.size()))};
        size_t extra = 0;
        if (entry.alignment > 1) {
            extra = (entry.alignment - ((bytes.size() + 30 + entry.name.size()) % entry.alignment)) % entry.alignment;
            if (extra > 0 && extra < 4) extra += entry.alignment;
        }
        U32(&bytes, 0x04034b50); U16(&bytes, 20); U16(&bytes, 0);
        U16(&bytes, entry.deflate ? 8 : 0); U16(&bytes, 0); U16(&bytes, 0);
        U32(&bytes, c.crc); U32(&bytes, c.packed.size()); U32(&bytes, entry.bytes.size());
        U16(&bytes, entry.name.size()); U16(&bytes, extra);
        bytes.insert(bytes.end(), entry.name.begin(), entry.name.end());
        if (extra) { U16(&bytes, 0xcafe); U16(&bytes, extra - 4); bytes.resize(bytes.size() + extra - 4); }
        bytes.insert(bytes.end(), c.packed.begin(), c.packed.end()); central.push_back(std::move(c));
    }
    const auto centralOffset = bytes.size();
    for (const auto& c : central) {
        U32(&bytes, 0x02014b50); U16(&bytes, 20); U16(&bytes, 20); U16(&bytes, 0);
        U16(&bytes, c.entry.deflate ? 8 : 0); U16(&bytes, 0); U16(&bytes, 0);
        U32(&bytes, c.crc); U32(&bytes, c.packed.size()); U32(&bytes, c.entry.bytes.size());
        U16(&bytes, c.entry.name.size()); U16(&bytes, 0); U16(&bytes, 0);
        U16(&bytes, 0); U16(&bytes, 0); U32(&bytes, 0); U32(&bytes, c.offset);
        bytes.insert(bytes.end(), c.entry.name.begin(), c.entry.name.end());
    }
    const auto centralSize = bytes.size() - centralOffset;
    U32(&bytes, 0x06054b50); U16(&bytes, 0); U16(&bytes, 0);
    U16(&bytes, entries.size()); U16(&bytes, entries.size());
    U32(&bytes, centralSize); U32(&bytes, centralOffset); U16(&bytes, 0);
    return bytes;
}
Bytes Zip64End(const Bytes& ordinary)
{
    auto output = ordinary; output.resize(output.size() - 22);
    const auto end64 = output.size();
    auto u64 = [&](uint64_t v) { U32(&output, v); U32(&output, v >> 32); };
    U32(&output, 0x06064b50); u64(44); U16(&output, 45); U16(&output, 45);
    U32(&output, 0); U32(&output, 0);
    const auto count = ordinary.at(ordinary.size() - 12) | (ordinary.at(ordinary.size() - 11) << 8);
    u64(count); u64(count); u64(FixtureRead32(ordinary, ordinary.size() - 10));
    u64(FixtureRead32(ordinary, ordinary.size() - 6));
    U32(&output, 0x07064b50); U32(&output, 0); u64(end64); U32(&output, 1);
    U32(&output, 0x06054b50); U16(&output, 0); U16(&output, 0);
    U16(&output, 0xffff); U16(&output, 0xffff); U32(&output, 0xffffffff); U32(&output, 0xffffffff); U16(&output, 0);
    return output;
}
struct Input {
    int fd = -1, sourceFd = -1;
    std::string path, digest;
    uint64_t length = 0;
    Input(const Bytes& bytes, int seals = F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL)
    {
        char filename[] = "/tmp/native-inventory-XXXXXX";
        sourceFd = mkstemp(filename); path = filename;
        Require(sourceFd >= 0, "fixture temp APK");
        try {
            Require(write(sourceFd, bytes.data(), bytes.size()) == static_cast<ssize_t>(bytes.size()), "fixture APK write");
            fd = memfd_create("verified-apk", MFD_CLOEXEC | MFD_ALLOW_SEALING);
            Require(fd >= 0, "real memfd required");
            std::array<uint8_t, 4096> buffer{};
            for (size_t at = 0; at < bytes.size();) {
                const auto count = pread(sourceFd, buffer.data(), buffer.size(), at);
                Require(count > 0 && write(fd, buffer.data(), count) == count, "fixture same-file snapshot copy");
                at += count;
            }
            if (seals) Require(fcntl(fd, F_ADD_SEALS, seals) == 0, "real seals required");
            digest = Sha(bytes); length = bytes.size();
        } catch (...) { Cleanup(); throw; }
    }
    Input(const Input&) = delete;
    Input& operator=(const Input&) = delete;
    void Cleanup() { if (fd >= 0) close(fd); if (sourceFd >= 0) close(sourceFd); unlink(path.c_str()); }
    ~Input() { Cleanup(); }
    ApkNativeInventory Read(const NativeInventoryProfile& p, const ApkNativeInventoryLimits& l = {}) const
    { return ReadApkNativeInventory(fd, length, digest, p, l); }
};
NativeInventoryProfile Profile(std::vector<std::string> abis = {"x86_64", "x86"}, uint64_t page = 4096)
{ return {{true, std::move(abis)}, page}; }
size_t FdCount()
{
    DIR* dir = opendir("/proc/self/fd"); Require(dir != nullptr, "FD count fixture");
    size_t count = 0; while (readdir(dir)) ++count; closedir(dir); return count;
}
TEST(SPC_47_Contract, Valid)
{
    for (const auto& bytes : {Zip({}), Zip({{"AndroidManifest.xml", {1, 2, 3}}})}) {
        Input input(bytes); const auto result = input.Read(Profile());
        EXPECT_EQ(result.verdict, V::NO_NATIVE) << result.reason;
        EXPECT_TRUE(result.artifacts.empty()); EXPECT_EQ(result.apkSha256, input.digest);
    }
    const auto elf32 = Elf("dependency32.elf"), elf64 = Elf("dependency64.elf");
    Input input(Zip({{"lib/x86/libfixturedep.so", elf32, false, 4096},
        {"lib/x86_64/libfixturedep.so", elf64, false, 16384}}));
    Input zip64(Zip64End(Zip({{"lib/x86_64/libfixturedep.so", elf64}})));
    EXPECT_EQ(zip64.Read(Profile()).verdict, V::MATCHED_NATIVE);
    const auto count = FdCount(); const auto offset = lseek(input.fd, 7, SEEK_SET);
    const auto result = input.Read(Profile());
    ASSERT_EQ(result.verdict, V::MATCHED_NATIVE) << result.reason;
    ASSERT_EQ(result.artifacts.size(), 2U);
    EXPECT_EQ(result.artifacts[0].abi, "x86"); EXPECT_EQ(result.artifacts[1].abi, "x86_64");
    EXPECT_EQ(result.artifacts[0].entrySha256, Sha(elf32));
    EXPECT_EQ(result.artifacts[1].entrySha256, Sha(elf64));
    for (const auto& artifact : result.artifacts) {
        ASSERT_TRUE(artifact.elfFacts); EXPECT_EQ(artifact.elfFacts->apkSha256, input.digest);
        EXPECT_TRUE(artifact.supportedByProfile); EXPECT_TRUE(artifact.directlyLoadable);
        EXPECT_EQ(artifact.compressionMethod, 0); EXPECT_EQ(artifact.dataOffset % 4096, 0U);
    }
    const auto page16 = input.Read(Profile({"x86_64", "x86"}, 16384));
    ASSERT_EQ(page16.verdict, V::MATCHED_NATIVE);
    EXPECT_FALSE(page16.artifacts.at(0).directlyLoadable);
    EXPECT_TRUE(page16.artifacts.at(1).directlyLoadable);
    EXPECT_EQ(lseek(input.fd, 0, SEEK_CUR), offset); EXPECT_EQ(FdCount(), count);
    EXPECT_EQ(pwrite(input.fd, "X", 1, 0), -1); EXPECT_EQ(errno, EPERM);
    EXPECT_EQ(ftruncate(input.fd, 0), -1); EXPECT_EQ(errno, EPERM);
    // Replace the source pathname. The production API has only the sealed FD.
    ASSERT_EQ(unlink(input.path.c_str()), 0);
    { std::ofstream replacement(input.path, std::ios::binary); replacement << "replaced"; }
    const auto after = input.Read(Profile({"x86"}));
    ASSERT_EQ(after.verdict, V::MATCHED_NATIVE); ASSERT_EQ(after.artifacts.size(), 2U);
    EXPECT_EQ(after.apkSha256, input.digest);
    EXPECT_TRUE(after.artifacts[0].supportedByProfile); EXPECT_FALSE(after.artifacts[1].supportedByProfile);
    Input mismatch(Zip({{"lib/x86/libfixturedep.so", elf32}}));
    const auto unmatched = mismatch.Read(Profile({"x86_64"}));
    EXPECT_EQ(unmatched.verdict, V::NO_MATCHING_ABIS); ASSERT_EQ(unmatched.artifacts.size(), 1U);
    EXPECT_TRUE(unmatched.artifacts[0].elfFacts); EXPECT_FALSE(unmatched.artifacts[0].supportedByProfile);
    Input compressed(Zip({{"lib/x86_64/libfixturedep.so", elf64, true, 4096}}));
    const auto packed = compressed.Read(Profile());
    ASSERT_EQ(packed.verdict, V::MATCHED_NATIVE); ASSERT_EQ(packed.artifacts.size(), 1U);
    EXPECT_EQ(packed.artifacts[0].compressionMethod, 8); EXPECT_FALSE(packed.artifacts[0].directlyLoadable);
    EXPECT_EQ(packed.artifacts[0].entrySha256, Sha(elf64));
    Input unaligned(Zip({{"lib/x86_64/libfixturedep.so", elf64}}));
    const auto unalignedResult = unaligned.Read(Profile());
    ASSERT_EQ(unalignedResult.verdict, V::MATCHED_NATIVE);
    EXPECT_FALSE(unalignedResult.artifacts.at(0).directlyLoadable);
    Input unknown(Zip({{"lib/futureabi/libfixturedep.so", elf64}}));
    const auto unsupported = unknown.Read(Profile());
    EXPECT_EQ(unsupported.verdict, V::NO_MATCHING_ABIS);
    ASSERT_EQ(unsupported.artifacts.size(), 1U); EXPECT_FALSE(unsupported.artifacts[0].elfFacts);
}
TEST(SPC_47_Contract, Rejected)
{
    const auto elf = Elf("dependency64.elf");
    const auto zip = Zip({{"lib/x86_64/libfixturedep.so", elf}});
    Input input(zip);
    EXPECT_EQ(ReadApkNativeInventory(-1, input.length, input.digest, Profile()).verdict, V::INVALID_INPUT);
    EXPECT_EQ(ReadApkNativeInventory(input.fd, input.length + 1, input.digest, Profile()).verdict, V::INVALID_INPUT);
    EXPECT_EQ(ReadApkNativeInventory(input.fd, input.length, std::string(64, '0'), Profile()).verdict, V::DIGEST_MISMATCH);
    EXPECT_EQ(ReadApkNativeInventory(input.sourceFd, input.length, input.digest, Profile()).verdict, V::FD_NOT_SEALED);
    for (const int seals : {0, F_SEAL_WRITE, F_SEAL_GROW | F_SEAL_SHRINK}) {
        Input unsealed(zip, seals); EXPECT_EQ(unsealed.Read(Profile()).verdict, V::FD_NOT_SEALED);
    }
    EXPECT_EQ(input.Read({}).verdict, V::PROFILE_UNAVAILABLE);
    EXPECT_EQ(input.Read(Profile({"x86_64"}, 3)).verdict, V::PROFILE_UNAVAILABLE);
    for (int which = 0; which < 4; ++which) {
        ApkNativeInventoryLimits limits;
        if (which == 0) limits.maxApkBytes = zip.size() - 1;
        if (which == 1) limits.maxEntryBytes = elf.size() - 1;
        if (which == 2) limits.maxTotalNativeBytes = elf.size() - 1;
        if (which == 3) limits.maxEntries = 0;
        EXPECT_EQ(input.Read(Profile(), limits).verdict, V::LIMIT_EXCEEDED);
    }
    auto truncated = zip; truncated.resize(truncated.size() - 10);
    auto crc = zip; crc.at(30 + std::string("lib/x86_64/libfixturedep.so").size() + 60) ^= 1;
    auto alias = zip; alias.at(30) = 'x'; // local and central names disagree
    auto encrypted = zip; encrypted.at(6) = 1;
    encrypted.at(FixtureRead32(zip, zip.size() - 6) + 8) = 1;
    auto trailing = Zip({{"lib/x86_64/libfixturedep.so", elf, true}});
    const auto centralAt = FixtureRead32(trailing, trailing.size() - 6);
    const auto packedSize = FixtureRead32(trailing, 18);
    trailing.insert(trailing.begin() + centralAt, 0);
    Patch32(&trailing, 18, packedSize + 1);
    Patch32(&trailing, centralAt + 1 + 20, packedSize + 1);
    Patch32(&trailing, trailing.size() - 6, centralAt + 1);
    auto hidden = zip;
    hidden.at(hidden.size() - 14) = 0; hidden.at(hidden.size() - 12) = 0;
    const auto count = FdCount();
    for (const auto& bad : {Bytes{1, 2, 3}, truncated, crc, alias, encrypted, trailing, hidden}) {
        Input broken(bad); auto result = broken.Read(Profile());
        EXPECT_EQ(result.verdict, V::CORRUPT_APK) << result.reason;
        EXPECT_TRUE(result.artifacts.empty()); EXPECT_TRUE(result.apkSha256.empty());
    }
    for (const auto& entries : std::vector<std::vector<Entry>>{
        {{"lib/../bad.so", elf}}, {{"lib/x86_64/libbad.so", elf}, {"lib/x86_64/libbad.so", elf}}}) {
        Input broken(Zip(entries)); auto result = broken.Read(Profile());
        EXPECT_EQ(result.verdict, V::INVALID_ENTRY) << result.reason; EXPECT_TRUE(result.artifacts.empty());
    }
    Input wrongAbi(Zip({{"lib/x86/libfixturedep.so", elf}}));
    const auto wrong = wrongAbi.Read(Profile());
    EXPECT_EQ(wrong.verdict, V::ELF_REJECTED); EXPECT_TRUE(wrong.artifacts.empty());
    EXPECT_EQ(wrong.elfVerdict, package_transaction::ElfPrepassVerdict::ABI_MISMATCH);
    // An error after a valid first entry cannot publish a partial inventory.
    Input partial(Zip({{"lib/x86_64/libok.so", elf}, {"lib/x86_64/libbad.so", {1, 2, 3}}}));
    const auto partialResult = partial.Read(Profile());
    EXPECT_EQ(partialResult.verdict, V::ELF_REJECTED); EXPECT_TRUE(partialResult.artifacts.empty());
    EXPECT_EQ(FdCount(), count + 4); // the two still-live Inputs each own two FDs
}
}
