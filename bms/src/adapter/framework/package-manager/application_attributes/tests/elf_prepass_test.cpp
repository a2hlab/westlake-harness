#include "elf_prepass_analyzer.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <fstream>
#include <iterator>

namespace {
using namespace oh_adapter::package_transaction;
using namespace manifest_fixture;
using V = ElfPrepassVerdict;
std::vector<uint8_t> ReadFixture(const std::string& name)
{
    std::ifstream in(std::string(ELF_FIXTURE_DIRECTORY) + "/" + name, std::ios::binary);
    Require(in.good(), "ELF fixture open failed");
    return {std::istreambuf_iterator<char>(in), std::istreambuf_iterator<char>()};
}
ElfPrepassInput Input(int bits, bool dependency = false)
{
    const auto name = std::string(dependency ? "dependency" : "consumer") + std::to_string(bits) + ".elf";
    const auto bytes = ReadFixture(name);
    const auto abi = bits == 32 ? "x86" : "x86_64";
    const auto entry = std::string("lib/") + abi + (dependency ? "/libfixturedep.so" : "/libfixture.so");
    const auto apk = MakeZip({{entry, bytes}});
    return {Sha(apk), entry, abi, Sha(bytes), bytes};
}
ElfPrepassInput ChainInput(int bits, const std::string& name)
{
    auto input = Input(bits);
    input.bytes = ReadFixture(name + std::to_string(bits) + ".elf");
    input.entryName = "lib/" + input.abi + "/lib" + name + ".so";
    input.expectedElfSha256 = Sha(input.bytes);
    input.apkSha256 = Sha(MakeZip({{input.entryName, input.bytes}}));
    return input;
}
void Put(std::vector<uint8_t>* bytes, size_t offset, uint64_t value, size_t width)
{
    Require(offset + width <= bytes->size(), "ELF mutation out of bounds");
    for (size_t i = 0; i < width; ++i) (*bytes)[offset + i] = static_cast<uint8_t>(value >> (8 * i));
}
void Reidentify(ElfPrepassInput* input) { input->expectedElfSha256 = Sha(input->bytes); }
void Rejected(const ElfPrepassResult& result, V verdict)
{
    EXPECT_EQ(result.verdict, verdict) << "SPC44_WRONG_REJECTION " << result.reason;
    EXPECT_FALSE(result.facts.has_value()) << "SPC44_REJECTED_ELF_EXPOSED";
}
TEST(SPC_44_Contract, Valid)
{
    for (int bits : {32, 64}) {
        SCOPED_TRACE(bits);
        auto dependency = InspectElf(Input(bits, true));
        ASSERT_EQ(dependency.verdict, V::ANALYZED) << dependency.reason;
        ASSERT_TRUE(dependency.facts.has_value());
        auto input = Input(bits);
        auto result = AnalyzeElf(input, {*dependency.facts});
        ASSERT_EQ(result.verdict, V::ANALYZED) << "SPC44_REAL_ELF_REJECTED " << result.reason;
        ASSERT_TRUE(result.facts.has_value());
        const auto facts = *result.facts;
        EXPECT_EQ(facts.elfClass, bits == 32 ? 1 : 2);
        EXPECT_EQ(facts.machine, bits == 32 ? 3 : 62);
        EXPECT_EQ(facts.apkSha256, input.apkSha256);
        EXPECT_EQ(facts.elfSha256, Sha(input.bytes));
        EXPECT_EQ(facts.entryName, input.entryName);
        EXPECT_EQ(facts.abi, input.abi);
        EXPECT_FALSE(facts.analyzerVersion.empty());
        EXPECT_EQ(facts.soname, "libfixture.so");
        ASSERT_EQ(facts.loadSegments.size(), 4U);
        EXPECT_EQ(facts.loadSegments[0].offset, 0U);
        EXPECT_EQ(facts.loadSegments[0].fileSize, bits == 32 ? 0x1e8U : 0x358U);
        EXPECT_EQ(facts.loadSegments[1].virtualAddress, 0x1000U);
        EXPECT_EQ(facts.loadSegments[1].flags, 5U);
        EXPECT_EQ(facts.loadSegments[3].alignment, 0x1000U);
        EXPECT_EQ(facts.neededLibraries, std::vector<std::string>{"libfixturedep.so"});
        EXPECT_EQ(facts.exportedSymbols, std::vector<std::string>{"fixture_export"});
        ASSERT_EQ(facts.requiredSymbols.size(), 1U);
        EXPECT_EQ(facts.requiredSymbols[0].name, "fixture_dependency");
        EXPECT_FALSE(facts.requiredSymbols[0].weak);
        {
            SCOPED_TRACE("SPC44_TRANSITIVE_SYMBOL_LOOKUP");
            auto middle = InspectElf(ChainInput(bits, "middle"));
            ASSERT_EQ(middle.verdict, V::ANALYZED) << middle.reason;
            auto root = AnalyzeElf(ChainInput(bits, "root"), {*middle.facts, *dependency.facts});
            ASSERT_EQ(root.verdict, V::ANALYZED) << "SPC44_TRANSITIVE_SYMBOL_REJECTED " << root.reason;
            EXPECT_EQ(root.facts->neededLibraries, std::vector<std::string>{"libmiddle.so"});
            ASSERT_EQ(root.facts->requiredSymbols.size(), 1U);
            EXPECT_EQ(root.facts->requiredSymbols[0].name, "fixture_dependency");
        }
        // Dynamic information is authoritative even without a section-header table.
        Put(&input.bytes, bits == 32 ? 32 : 40, 0, bits == 32 ? 4 : 8);
        Put(&input.bytes, bits == 32 ? 48 : 60, 0, 2);
        Put(&input.bytes, bits == 32 ? 50 : 62, 0, 2);
        Reidentify(&input);
        result = AnalyzeElf(input, {*dependency.facts});
        ASSERT_EQ(result.verdict, V::ANALYZED) << "SPC44_STRIPPED_SECTIONS_REJECTED " << result.reason;
        EXPECT_EQ(result.facts->neededLibraries, facts.neededLibraries);
    }
}
TEST(SPC_44_Contract, Rejected)
{
    for (int bits : {32, 64}) {
        const auto original = Input(bits);
        auto dependency = InspectElf(Input(bits, true));
        ASSERT_EQ(dependency.verdict, V::ANALYZED) << dependency.reason;
        auto middle = InspectElf(ChainInput(bits, "middle"));
        ASSERT_EQ(middle.verdict, V::ANALYZED) << middle.reason;
        {
            SCOPED_TRACE("SPC44_TRANSITIVE_DEPENDENCY_MISSING");
            Rejected(AnalyzeElf(ChainInput(bits, "root"), {*middle.facts}), V::DEPENDENCY_MISSING);
        }
        for (uint64_t address : {uint64_t{0x9000}, uint64_t{0x1000}}) {
            SCOPED_TRACE("SPC44_DYNAMIC_MAPPING");
            auto unmapped = original;
            // GNU readelf confirms DYNAMIC is program header index 4 in both fixtures.
            const size_t ph = (bits == 32 ? 52 : 64) + 4 * (bits == 32 ? 32 : 56);
            Put(&unmapped.bytes, ph + (bits == 32 ? 8 : 16), address, bits == 32 ? 4 : 8);
            Reidentify(&unmapped);
            Rejected(InspectElf(unmapped), V::MALFORMED_ELF);
        }
        Rejected(AnalyzeElf(original, {}), V::DEPENDENCY_MISSING);
        auto wrongAbi = *dependency.facts; wrongAbi.abi = "another-abi";
        Rejected(AnalyzeElf(original, {wrongAbi}), V::DEPENDENCY_MISSING);
        auto noSymbol = *dependency.facts; noSymbol.exportedSymbols.clear();
        Rejected(AnalyzeElf(original, {noSymbol}), V::SYMBOL_MISSING);
        auto changed = original; changed.expectedElfSha256 = std::string(64, '0');
        Rejected(InspectElf(changed), V::DIGEST_MISMATCH);
        changed = original; changed.apkSha256.clear();
        Rejected(InspectElf(changed), V::INVALID_INPUT);
        changed = original; changed.abi = bits == 32 ? "x86_64" : "x86";
        Rejected(InspectElf(changed), V::ABI_MISMATCH);
        for (size_t length : {size_t{0}, size_t{3}, size_t{16}, size_t{40}, size_t{64}}) {
            changed = original; changed.bytes.resize(length); Reidentify(&changed);
            Rejected(InspectElf(changed), V::MALFORMED_ELF);
        }
        // Independent byte mutations of compiler-generated headers and PT_LOAD.
        const size_t phoff = bits == 32 ? 52 : 64;
        const size_t width = bits == 32 ? 4 : 8;
        const std::vector<std::pair<size_t, uint64_t>> mutations = {
            {0, 0}, {20, 0},
            {phoff + (bits == 32 ? 4 : 8), UINT32_MAX},
            {phoff + (bits == 32 ? 16 : 32), UINT32_MAX},
            {phoff + (bits == 32 ? 20 : 40), 0},
            {phoff + (bits == 32 ? 28 : 48), 3},
        };
        for (const auto& [offset, value] : mutations) {
            changed = original; Put(&changed.bytes, offset, value, offset < phoff ? 4 : width);
            Reidentify(&changed); Rejected(InspectElf(changed), V::MALFORMED_ELF);
        }
        changed = original; Put(&changed.bytes, 18, 0xffff, 2); Reidentify(&changed);
        Rejected(InspectElf(changed), V::ABI_MISMATCH);
    }
}
}
