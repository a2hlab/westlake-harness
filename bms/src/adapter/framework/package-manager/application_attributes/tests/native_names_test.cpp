#include "apk_native_inventory_names.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <unzip.h>
#include <fcntl.h>
#include <unistd.h>
#include <filesystem>
#include <fstream>
#include <iterator>

namespace {
using namespace oh_adapter;
using namespace manifest_fixture;
using V = NativeEntryVerdict;
std::vector<uint8_t> Elf(int bits)
{
    std::ifstream in(std::string(ELF_FIXTURE_DIRECTORY) + "/dependency" + std::to_string(bits) + ".elf", std::ios::binary);
    Require(in.good(), "SPC48 ELF fixture open");
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
// Write a real temporary ZIP, then read its central metadata and decompressed
// bytes with the production minizip dependency. No names/ABI logic lives here.
std::vector<NativeEntryResult> CheckZip(const std::vector<std::pair<std::string, std::vector<uint8_t>>>& members,
    NativeAbiProfile profile = {true, {"x86", "x86_64"}}, uint16_t madeBy = 0, uint32_t attributes = 0)
{
    auto bytes = MakeZip(members);
    // Patch only explicit central metadata in a valid ZIP for file-kind cases.
    size_t central = FixtureRead32(bytes, bytes.size() - 6);
    auto shortAt = [&](size_t at) { return static_cast<size_t>(bytes.at(at)) | (static_cast<size_t>(bytes.at(at + 1)) << 8); };
    for (size_t entry = 0; entry < members.size(); ++entry) {
        const size_t i = central;
        Require(FixtureRead32(bytes, i) == 0x02014b50, "SPC48 central fixture shape");
        central += 46 + shortAt(i + 28) + shortAt(i + 30) + shortAt(i + 32);
        bytes[i + 4] = static_cast<uint8_t>(madeBy);
        bytes[i + 5] = static_cast<uint8_t>(madeBy >> 8);
        for (size_t n = 0; n < 4; ++n) bytes[i + 38 + n] = static_cast<uint8_t>(attributes >> (n * 8));
    }
    std::string pattern = (std::filesystem::temp_directory_path() / "spc48-XXXXXX").string();
    std::vector<char> name(pattern.begin(), pattern.end()); name.push_back('\0');
    int fd = mkstemp(name.data()); Require(fd >= 0, "SPC48 mkstemp");
    size_t offset = 0;
    while (offset < bytes.size()) {
        auto count = write(fd, bytes.data() + offset, bytes.size() - offset);
        if (count <= 0) { close(fd); unlink(name.data()); throw std::runtime_error("SPC48 ZIP write"); }
        offset += static_cast<size_t>(count);
    }
    close(fd);
    unzFile zip = unzOpen64(name.data());
    struct ArchiveGuard {
        unzFile zip;
        const char* path;
        ~ArchiveGuard() { if (zip != nullptr) unzClose(zip); unlink(path); }
    } guard{zip, name.data()};
    Require(zip != nullptr, "SPC48 ZIP open");
    std::set<std::string> seen;
    std::vector<NativeEntryResult> results;
    int status = unzGoToFirstFile(zip);
    while (status == UNZ_OK) {
        unz_file_info64 info{};
        Require(unzGetCurrentFileInfo64(zip, &info, nullptr, 0, nullptr, 0, nullptr, 0) == UNZ_OK, "SPC48 ZIP metadata");
        std::vector<char> entryName(info.size_filename + 1);
        Require(unzGetCurrentFileInfo64(zip, &info, entryName.data(), entryName.size(), nullptr, 0, nullptr, 0) == UNZ_OK, "SPC48 ZIP name");
        Require(unzOpenCurrentFile(zip) == UNZ_OK, "SPC48 ZIP entry open");
        std::vector<uint8_t> entryBytes(info.uncompressed_size);
        size_t done = 0;
        while (done < entryBytes.size()) {
            int count = unzReadCurrentFile(zip, entryBytes.data() + done, static_cast<unsigned>(entryBytes.size() - done));
            Require(count > 0, "SPC48 ZIP decompress"); done += static_cast<size_t>(count);
        }
        Require(unzCloseCurrentFile(zip) == UNZ_OK, "SPC48 ZIP CRC");
        ApkNativeEntryInput input{std::string(entryName.data(), info.size_filename), Sha(bytes), Sha(entryBytes),
            std::move(entryBytes), static_cast<uint16_t>(info.version), static_cast<uint32_t>(info.external_fa)};
        results.push_back(ValidateApkNativeEntry(input, profile, seen));
        status = unzGoToNextFile(zip);
    }
    Require(status == UNZ_END_OF_LIST_OF_FILE, "SPC48 ZIP iteration");
    return results;
}
void Verdict(const NativeEntryResult& result, V expected)
{
    EXPECT_EQ(result.verdict, expected) << "SPC48_WRONG_NAME_OR_ABI_VERDICT " << result.reason;
    if (expected != V::VALID_NATIVE) EXPECT_FALSE(result.elfFacts.has_value());
}
TEST(SPC_48_Contract, Valid)
{
    const auto entries = CheckZip({{"lib/x86/libfixture.so", Elf(32)}, {"lib/x86_64/libfixture.so", Elf(64)},
        {"assets/data.bin", {1, 2}}, {"lib/", {}}, {"lib/x86/", {}}, {"lib/x86/readme.txt", {1}}});
    ASSERT_EQ(entries.size(), 6U);
    for (size_t i = 0; i < 2; ++i) {
        Verdict(entries[i], V::VALID_NATIVE);
        ASSERT_TRUE(entries[i].elfFacts.has_value());
        EXPECT_EQ(entries[i].abi, i == 0 ? "x86" : "x86_64");
        EXPECT_EQ(entries[i].fileName, "libfixture.so");
        EXPECT_EQ(entries[i].canonicalName, "lib/" + entries[i].abi + "/libfixture.so");
        EXPECT_EQ(entries[i].elfFacts->machine, i == 0 ? 3 : 62);
    }
    for (size_t i = 2; i < entries.size(); ++i) Verdict(entries[i], V::NOT_NATIVE);
    auto unixEntry = CheckZip({{"lib/x86/libfixture.so", Elf(32)}}, {true, {"x86"}}, 3 << 8, 0100644U << 16);
    Verdict(unixEntry.at(0), V::VALID_NATIVE);
}
TEST(SPC_48_Contract, Rejected)
{
    const auto elf = Elf(32);
    std::vector<std::string> bad = {"", "/lib/x86/libfixture.so", "../lib/x86/libfixture.so", "lib/../x86/libfixture.so",
        "lib/x86/../libfixture.so", "lib/./x86/libfixture.so", "lib//x86/libfixture.so", "lib/x86//libfixture.so",
        "lib\\x86\\libfixture.so", "C:/lib/x86/libfixture.so", "lib/x86/dir/libfixture.so",
        std::string("lib/x86/libfixture.so\0suffix", 28), "lib/x86/" + std::string(4096, 'a') + ".so"};
    for (const auto& name : bad) {
        SCOPED_TRACE(name);
        auto result = CheckZip({{name, elf}});
        Verdict(result.at(0), V::INVALID_NAME);
    }
    auto duplicate = CheckZip({{"lib/x86/libfixture.so", elf}, {"lib/x86/libfixture.so", elf}});
    Verdict(duplicate.at(0), V::VALID_NATIVE); Verdict(duplicate.at(1), V::DUPLICATE_ENTRY);
    const auto wrongElf = CheckZip({{"lib/x86_64/libfixture.so", elf}}).at(0);
    Verdict(wrongElf, V::ELF_REJECTED);
    ASSERT_TRUE(wrongElf.elfVerdict.has_value()) << "SPC48_TYPED_ELF_FAILURE_LOST";
    EXPECT_EQ(*wrongElf.elfVerdict, package_transaction::ElfPrepassVerdict::ABI_MISMATCH);
    Verdict(CheckZip({{"lib/x86/libfixture.so", {1, 2, 3}}}).at(0), V::ELF_REJECTED);
    Verdict(CheckZip({{"lib/x86/libfixture.so", elf}}, {false, {}}).at(0), V::PROFILE_UNAVAILABLE);
    Verdict(CheckZip({{"lib/x86/libfixture.so", elf}}, {true, {"x86_64"}}).at(0), V::ABI_UNSUPPORTED);
    Verdict(CheckZip({{"lib/unknown/libfixture.so", elf}}).at(0), V::ABI_UNSUPPORTED);
    for (uint32_t mode : {0120777U, 0040755U, 0010600U})
        Verdict(CheckZip({{"lib/x86/libfixture.so", elf}}, {true, {"x86"}}, 3 << 8, mode << 16).at(0), V::NON_REGULAR_ENTRY);
    Verdict(CheckZip({{"lib/x86/libfixture.so", elf}}, {true, {"x86"}}, 0, 0x10).at(0), V::NON_REGULAR_ENTRY);
}
}
