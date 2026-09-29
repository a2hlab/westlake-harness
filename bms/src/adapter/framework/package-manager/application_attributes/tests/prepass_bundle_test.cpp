#include "prepass_bundle.h"
#include "apk_native_inventory.h"
#include "manifest_fixture.h"
#include <gtest/gtest.h>
#include <algorithm>
#include <fcntl.h>
#include <fstream>
#include <functional>
#include <iterator>
#include <limits>
#include <sys/mman.h>
#include <unistd.h>

namespace {
using namespace oh_adapter;
using namespace oh_adapter::package_transaction;
using namespace manifest_fixture;
using Record = wire::PrepassBundleRecord;
using Bytes = std::vector<uint8_t>;
std::string Hash(const std::string& input) { return Sha(Bytes(input.begin(), input.end())); }
PrepassBundle Base()
{
    PrepassBundle b; b.requestId = "request-a"; b.packageName = "org.example.app";
    b.userId = 10; b.packageGeneration = "generation-a";
    b.apkDigest = std::string(64, 'b'); b.contractDigest = std::string(64, 'a');
    b.policyDigest = std::string(64, 'c'); b.toolDigest = std::string(64, 'd');
    b.topologyDigest = std::string(64, 'e'); b.runtimeGenerationSealDigest = std::string(64, 'f');
    return b;
}
PrepassBundle Native()
{
    auto b = Base();
    std::vector<std::pair<std::string, Bytes>> entries;
    for (const auto& item : {std::pair{"x86", "dependency32.elf"}, std::pair{"x86_64", "consumer64.elf"}}) {
        std::ifstream file(std::string(ELF_FIXTURE_DIRECTORY) + "/" + item.second, std::ios::binary);
        Require(file.good(), "real ELF fixture available");
        entries.push_back({std::string("lib/") + item.first + "/libfixture.so", Bytes(std::istreambuf_iterator<char>(file), {})});
    }
    const auto zip = MakeZip(entries);
    const int fd = memfd_create("prepass-test-apk", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    Require(fd >= 0, "real Linux memfd required");
    struct CloseFd { int fd; ~CloseFd() { close(fd); } } owned{fd};
    Require(write(fd, zip.data(), zip.size()) == static_cast<ssize_t>(zip.size()), "fixture APK write");
    Require(fcntl(fd, F_ADD_SEALS, F_SEAL_WRITE | F_SEAL_SHRINK | F_SEAL_GROW | F_SEAL_SEAL) == 0, "fixture seals");
    b.apkDigest = Sha(zip);
    const auto inventory = ReadApkNativeInventory(fd, zip.size(), b.apkDigest, {{true, {"x86_64", "x86"}}, 4096});
    Require(inventory.verdict == NativeInventoryVerdict::MATCHED_NATIVE, inventory.reason);
    b.disposition = PrepassDisposition::HAS_NATIVE_ELF; b.nativeEntryCount = inventory.artifacts.size();
    for (const auto& artifact : inventory.artifacts) { Require(artifact.elfFacts.has_value(), "actual ELF analysis"); b.elfFacts.push_back(*artifact.elfFacts); }
    return b;
}
Record Encode(const PrepassBundle& b)
{
    Record record; std::string error;
    Require(PrepassBundleCodec::Encode(b, &record, &error), error); return record;
}
void Roundtrip(const PrepassBundle& input)
{
    auto record = Encode(input); PrepassBundle decoded; std::string error;
    ASSERT_TRUE(PrepassBundleCodec::Decode(record, &decoded, &error)) << error;
    EXPECT_EQ(decoded.requestId, input.requestId); EXPECT_EQ(decoded.packageName, input.packageName);
    EXPECT_EQ(decoded.userId, input.userId); EXPECT_EQ(decoded.packageGeneration, input.packageGeneration);
    EXPECT_EQ(decoded.topologyDigest, input.topologyDigest); EXPECT_EQ(decoded.disposition, input.disposition);
    EXPECT_EQ(decoded.nativeEntryCount, input.nativeEntryCount); EXPECT_EQ(decoded.elfFacts.size(), input.elfFacts.size());
    const auto again = Encode(decoded);
    EXPECT_EQ(again.canonicalPayload, record.canonicalPayload); EXPECT_EQ(again.payloadSha256, Hash(again.canonicalPayload));
    EXPECT_EQ(again.payloadSha256, record.payloadSha256);
}
TEST(SPC_45_Contract, Valid)
{
    auto empty = Base(); Roundtrip(empty); // original materializer's no-native decode contract
    auto b = Native(); Roundtrip(b);
    auto record = Encode(b); std::reverse(b.elfFacts.begin(), b.elfFacts.end());
    EXPECT_EQ(Encode(b).canonicalPayload, record.canonicalPayload);
    b.disposition = PrepassDisposition::NO_MATCHING_ABIS; Roundtrip(b);
    b.elfFacts.clear(); b.nativeEntryCount = 1; Roundtrip(b); // unknown ABI remains native, not NO_NATIVE
    // Codec bit-width/ordering probe. It does not claim to re-analyze these DTO facts.
    b = Native(); auto& elf = b.elfFacts.at(1);
    elf.loadSegments.at(0).virtualAddress = (uint64_t{1} << 63) + 4096;
    elf.neededLibraries = {"libz.so", "liba.so"}; elf.requiredSymbols.push_back({"optional", true});
    Roundtrip(b); auto ordered = Encode(b); PrepassBundle decoded; std::string error;
    ASSERT_TRUE(PrepassBundleCodec::Decode(ordered, &decoded, &error));
    EXPECT_EQ(decoded.elfFacts.at(1).loadSegments.at(0).virtualAddress, (uint64_t{1} << 63) + 4096);
    EXPECT_EQ(decoded.elfFacts.at(1).neededLibraries, (std::vector<std::string>{"libz.so", "liba.so"}));
    EXPECT_TRUE(decoded.elfFacts.at(1).requiredSymbols.back().weak);
    auto sameObject = b;
    ASSERT_TRUE(PrepassBundleCodec::DecodePayload(ordered.canonicalPayload, ordered.payloadSha256,
        sameObject, &sameObject, &error)) << "SPC45_ALIAS_TRUSTED_BINDING_DESTROYED: " << error;
    EXPECT_EQ(Encode(sameObject).canonicalPayload, ordered.canonicalPayload);
}
TEST(SPC_45_Contract, Rejected)
{
    const auto b = Native(); const auto record = Encode(b); std::string error; PrepassBundle decoded;
    // Any payload byte (including every consumed ELF field) is hash-bound.
    for (size_t index = 0; index < record.canonicalPayload.size(); ++index) {
        auto changed = record; changed.canonicalPayload[index] ^= 1;
        ASSERT_FALSE(PrepassBundleCodec::Decode(changed, &decoded, &error)) << index;
        EXPECT_TRUE(decoded.elfFacts.empty());
    }
    using Change = std::function<void(PrepassBundle&)>;
    const std::vector<Change> identities{
        [](auto& x) { x.requestId += "x"; }, [](auto& x) { x.packageName += "x"; },
        [](auto& x) { ++x.userId; }, [](auto& x) { x.packageGeneration += "x"; },
        [](auto& x) { x.apkDigest[0] = '0'; for (auto& f : x.elfFacts) f.apkSha256 = x.apkDigest; },
        [](auto& x) { x.contractDigest[0] = '0'; }, [](auto& x) { x.policyDigest[0] = '0'; },
        [](auto& x) { x.toolDigest[0] = '0'; }, [](auto& x) { x.topologyDigest[0] = '0'; },
        [](auto& x) { x.runtimeGenerationSealDigest[0] = '0'; },
    };
    for (const auto& change : identities) {
        auto modified = b; change(modified); auto other = Encode(modified);
        EXPECT_NE(other.payloadSha256, record.payloadSha256);
        // Even a recomputed checksum cannot replace the trusted request identity.
        EXPECT_FALSE(PrepassBundleCodec::DecodePayload(other.canonicalPayload, other.payloadSha256,
            record.binding, &decoded, &error));
        auto wrongEnvelope = record; wrongEnvelope.binding = other.binding;
        EXPECT_FALSE(PrepassBundleCodec::Decode(wrongEnvelope, &decoded, &error));
    }
    for (const size_t offset : {size_t{0}, size_t{8}, size_t{12}}) {
        auto changed = record; changed.canonicalPayload[offset] ^= 0x7f;
        changed.payloadSha256 = Hash(changed.canonicalPayload);
        EXPECT_FALSE(PrepassBundleCodec::Decode(changed, &decoded, &error)); // magic/version/reserved
    }
    for (auto payload : {record.canonicalPayload.substr(0, 10), record.canonicalPayload + "x"}) {
        EXPECT_FALSE(PrepassBundleCodec::DecodePayload(payload, Hash(payload), record.binding, &decoded, &error));
    }
    auto oversized = record; oversized.canonicalPayload.resize(PrepassBundleCodec::MAX_PAYLOAD_BYTES + 1);
    EXPECT_FALSE(PrepassBundleCodec::Decode(oversized, &decoded, &error));
    const std::vector<Change> invalid{
        [](auto& x) { x.requestId.clear(); }, [](auto& x) { x.packageName += '\0'; },
        [](auto& x) { x.userId = -1; }, [](auto& x) { x.packageGeneration.resize(4097, 'x'); },
        [](auto& x) { x.contractDigest[0] = 'A'; }, [](auto& x) { x.elfFacts[0].apkSha256[0] = '0'; },
        [](auto& x) { x.elfFacts.push_back(x.elfFacts[0]); ++x.nativeEntryCount; },
        [](auto& x) { x.disposition = PrepassDisposition::NO_NATIVE_ELF; },
        [](auto& x) { x.nativeEntryCount = 0; }, [](auto& x) { x.nativeEntryCount = PrepassBundleCodec::MAX_NATIVE_ENTRIES + 1; },
        [](auto& x) { x.disposition = static_cast<PrepassDisposition>(99); },
        [](auto& x) { x.elfFacts[0].loadSegments[0].fileSize = std::numeric_limits<uint64_t>::max(); },
    };
    for (const auto& change : invalid) {
        auto bad = b; change(bad); auto out = record;
        EXPECT_FALSE(PrepassBundleCodec::Encode(bad, &out, &error));
        EXPECT_FALSE(error.empty()); EXPECT_TRUE(out.canonicalPayload.empty()); EXPECT_TRUE(out.payloadSha256.empty());
    }
    EXPECT_FALSE(PrepassBundleCodec::Encode(b, nullptr, &error));
    EXPECT_FALSE(PrepassBundleCodec::Decode(record, nullptr, &error));
    auto sameObject = b;
    auto corrupted = record.canonicalPayload; corrupted.back() ^= 1;
    EXPECT_FALSE(PrepassBundleCodec::DecodePayload(corrupted, record.payloadSha256,
        sameObject, &sameObject, &error));
    EXPECT_TRUE(sameObject.requestId.empty()); EXPECT_EQ(sameObject.userId, -1);
    EXPECT_TRUE(sameObject.elfFacts.empty());
}
}
