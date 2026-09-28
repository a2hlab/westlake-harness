#include "manifest_facts_v1.h"

#include "sha256.h"

#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <map>
#include <sstream>
#include <stdexcept>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>
#include <utility>
#include <vector>

#include <zlib.h>

using oh_adapter::manifest_facts::ManifestFactsParserV1;
using oh_adapter::manifest_facts::ManifestParseFault;
using oh_adapter::manifest_facts::ManifestParseReceiptJson;
using oh_adapter::manifest_facts::ManifestParseRequestV1;
using oh_adapter::manifest_facts::ManifestParseVerdict;
using oh_adapter::package_transaction::ArtifactDescriptorV1;
using oh_adapter::package_transaction::ArtifactRole;
using oh_adapter::package_transaction::ComputeArtifactSetDigest;

namespace {

constexpr const char* MANIFEST_NAME = "AndroidManifest.xml";

void Require(bool condition, const std::string& message)
{
    if (!condition) throw std::runtime_error(message);
}

void U16(std::vector<uint8_t>* out, uint16_t value)
{
    out->push_back(static_cast<uint8_t>(value));
    out->push_back(static_cast<uint8_t>(value >> 8));
}

void U32(std::vector<uint8_t>* out, uint32_t value)
{
    out->push_back(static_cast<uint8_t>(value));
    out->push_back(static_cast<uint8_t>(value >> 8));
    out->push_back(static_cast<uint8_t>(value >> 16));
    out->push_back(static_cast<uint8_t>(value >> 24));
}

void Patch32(std::vector<uint8_t>* out, size_t offset, uint32_t value)
{
    Require(offset + 4 <= out->size(), "Patch32 range");
    for (size_t index = 0; index < 4; ++index) {
        (*out)[offset + index] =
            static_cast<uint8_t>(value >> (index * 8));
    }
}

std::string Hex(const uint8_t* bytes, size_t length)
{
    static constexpr char DIGITS[] = "0123456789abcdef";
    std::string result;
    result.reserve(length * 2);
    for (size_t index = 0; index < length; ++index) {
        result.push_back(DIGITS[bytes[index] >> 4]);
        result.push_back(DIGITS[bytes[index] & 0xf]);
    }
    return result;
}

std::string Sha(const std::vector<uint8_t>& bytes)
{
    uint8_t digest[32];
    sha256(bytes.empty() ? nullptr : bytes.data(), bytes.size(), digest);
    return Hex(digest, sizeof(digest));
}

std::vector<uint8_t> ReadFile(const std::string& path)
{
    std::ifstream input(path, std::ios::binary);
    Require(input.good(), "fixture open failed");
    return std::vector<uint8_t>(std::istreambuf_iterator<char>(input), {});
}

void WriteFile(const std::string& path, const std::string& content)
{
    std::ofstream output(path, std::ios::binary | std::ios::trunc);
    Require(output.good(), "evidence output open failed: " + path);
    output << content;
    Require(output.good(), "evidence output write failed: " + path);
}

struct Attr {
    std::string name;
    std::string text;
    bool integer = false;
    uint32_t integerValue = 0;
    bool boolean = false;
    bool booleanValue = false;
};

struct Node {
    std::string name;
    std::vector<Attr> attrs;
    bool end = false;
};

std::vector<uint8_t> MakeAxml(const std::string& packageName,
    bool duplicateApplication, bool duplicatePackageAttribute)
{
    std::vector<Node> nodes = {
        {"manifest", {
            {"package", packageName},
            {"versionCode", "", true, 42},
            {"versionName", "4.2"},
        }, false},
        {"uses-sdk", {
            {"minSdkVersion", "", true, 23},
            {"targetSdkVersion", "", true, 35},
        }, false},
        {"uses-sdk", {}, true},
        {"application", {
            {"name", ".BridgeApplication"},
            {"label", "Fixture"},
        }, false},
        {"activity", {
            {"name", ".MainActivity"},
            {"exported", "", false, 0, true, true},
        }, false},
        {"activity", {}, true},
        {"application", {}, true},
    };
    if (duplicatePackageAttribute) {
        nodes.front().attrs.push_back({"package", packageName + ".conflict"});
    }
    if (duplicateApplication) {
        nodes.push_back({"application", {}, false});
        nodes.push_back({"application", {}, true});
    }
    nodes.push_back({"manifest", {}, true});

    std::vector<std::string> strings;
    std::map<std::string, uint32_t> refs;
    auto intern = [&](const std::string& value) {
        auto found = refs.find(value);
        if (found != refs.end()) return found->second;
        const uint32_t ref = static_cast<uint32_t>(strings.size());
        strings.push_back(value);
        refs.emplace(value, ref);
        return ref;
    };
    for (const Node& node : nodes) {
        intern(node.name);
        for (const Attr& attr : node.attrs) {
            intern(attr.name);
            if (!attr.integer && !attr.boolean) intern(attr.text);
        }
    }

    std::vector<uint8_t> poolData;
    std::vector<uint32_t> offsets;
    for (const std::string& value : strings) {
        Require(value.size() < 128, "synthetic AXML string too long");
        offsets.push_back(static_cast<uint32_t>(poolData.size()));
        poolData.push_back(static_cast<uint8_t>(value.size()));
        poolData.push_back(static_cast<uint8_t>(value.size()));
        poolData.insert(poolData.end(), value.begin(), value.end());
        poolData.push_back(0);
    }
    while ((poolData.size() % 4) != 0) poolData.push_back(0);

    std::vector<uint8_t> document;
    U16(&document, 0x0003);
    U16(&document, 8);
    U32(&document, 0);

    const uint32_t poolSize =
        static_cast<uint32_t>(28 + offsets.size() * 4 + poolData.size());
    U16(&document, 0x0001);
    U16(&document, 28);
    U32(&document, poolSize);
    U32(&document, static_cast<uint32_t>(strings.size()));
    U32(&document, 0);
    U32(&document, 1U << 8);
    U32(&document, static_cast<uint32_t>(28 + offsets.size() * 4));
    U32(&document, 0);
    for (uint32_t offset : offsets) U32(&document, offset);
    document.insert(document.end(), poolData.begin(), poolData.end());

    for (const Node& node : nodes) {
        if (!node.end) {
            const uint32_t chunkSize =
                static_cast<uint32_t>(36 + node.attrs.size() * 20);
            U16(&document, 0x0102);
            U16(&document, 16);
            U32(&document, chunkSize);
            U32(&document, 1);
            U32(&document, 0xffffffffU);
            U32(&document, 0xffffffffU);
            U32(&document, refs.at(node.name));
            U16(&document, 20);
            U16(&document, 20);
            U16(&document, static_cast<uint16_t>(node.attrs.size()));
            U16(&document, 0);
            U16(&document, 0);
            U16(&document, 0);
            for (const Attr& attr : node.attrs) {
                U32(&document, 0xffffffffU);
                U32(&document, refs.at(attr.name));
                if (attr.integer || attr.boolean) {
                    U32(&document, 0xffffffffU);
                } else {
                    U32(&document, refs.at(attr.text));
                }
                U16(&document, 8);
                document.push_back(0);
                document.push_back(attr.boolean ? 0x12 :
                    (attr.integer ? 0x10 : 0x03));
                U32(&document, attr.boolean ?
                    (attr.booleanValue ? 1U : 0U) :
                    (attr.integer ? attr.integerValue : refs.at(attr.text)));
            }
        } else {
            U16(&document, 0x0103);
            U16(&document, 16);
            U32(&document, 24);
            U32(&document, 1);
            U32(&document, 0xffffffffU);
            U32(&document, 0xffffffffU);
            U32(&document, refs.at(node.name));
        }
    }
    Patch32(&document, 4, static_cast<uint32_t>(document.size()));
    return document;
}

std::vector<uint8_t> MakeZip(
    const std::vector<std::pair<std::string, std::vector<uint8_t>>>& entries)
{
    struct Central {
        std::string name;
        uint32_t crc = 0;
        uint32_t size = 0;
        uint32_t offset = 0;
    };
    std::vector<uint8_t> archive;
    std::vector<Central> central;
    for (const auto& entry : entries) {
        Central record;
        record.name = entry.first;
        record.crc = crc32(0L, reinterpret_cast<const Bytef*>(
            entry.second.data()), entry.second.size());
        record.size = static_cast<uint32_t>(entry.second.size());
        record.offset = static_cast<uint32_t>(archive.size());
        U32(&archive, 0x04034b50);
        U16(&archive, 20);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, record.crc);
        U32(&archive, record.size);
        U32(&archive, record.size);
        U16(&archive, static_cast<uint16_t>(record.name.size()));
        U16(&archive, 0);
        archive.insert(archive.end(), record.name.begin(), record.name.end());
        archive.insert(archive.end(), entry.second.begin(), entry.second.end());
        central.push_back(std::move(record));
    }
    const uint32_t centralOffset = static_cast<uint32_t>(archive.size());
    for (const Central& record : central) {
        U32(&archive, 0x02014b50);
        U16(&archive, 20);
        U16(&archive, 20);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, record.crc);
        U32(&archive, record.size);
        U32(&archive, record.size);
        U16(&archive, static_cast<uint16_t>(record.name.size()));
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U16(&archive, 0);
        U32(&archive, 0);
        U32(&archive, record.offset);
        archive.insert(archive.end(), record.name.begin(), record.name.end());
    }
    const uint32_t centralSize =
        static_cast<uint32_t>(archive.size()) - centralOffset;
    U32(&archive, 0x06054b50);
    U16(&archive, 0);
    U16(&archive, 0);
    U16(&archive, static_cast<uint16_t>(central.size()));
    U16(&archive, static_cast<uint16_t>(central.size()));
    U32(&archive, centralSize);
    U32(&archive, centralOffset);
    U16(&archive, 0);
    return archive;
}

int SealedFd(const std::vector<uint8_t>& bytes, bool seal)
{
#if !defined(__linux__)
    (void)bytes;
    (void)seal;
    throw std::runtime_error("test requires Linux memfd seals");
#else
    const int fd = memfd_create("fn01-a03-fixture", MFD_ALLOW_SEALING);
    Require(fd >= 0, "memfd_create failed");
    size_t offset = 0;
    while (offset < bytes.size()) {
        const ssize_t count =
            write(fd, bytes.data() + offset, bytes.size() - offset);
        if (count < 0 && errno == EINTR) continue;
        Require(count > 0, "memfd write failed");
        offset += static_cast<size_t>(count);
    }
    if (seal) {
        Require(fcntl(fd, F_ADD_SEALS, F_SEAL_SEAL | F_SEAL_SHRINK |
            F_SEAL_GROW | F_SEAL_WRITE) == 0, "memfd seal failed");
    }
    return fd;
#endif
}

ManifestParseRequestV1 RequestFor(const std::string& id,
    int fd, const std::vector<uint8_t>& bytes)
{
    ManifestParseRequestV1 request;
    request.requestId = id;
    request.artifactFd = fd;
    request.byteLength = bytes.size();
    request.artifactSha256 = Sha(bytes);
    ArtifactDescriptorV1 artifact;
    artifact.artifactId = "base";
    artifact.role = ArtifactRole::BASE;
    artifact.byteLength = request.byteLength;
    artifact.sha256 = request.artifactSha256;
    request.artifactSet.artifacts.push_back(std::move(artifact));
    request.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(request.artifactSet);
    return request;
}

void Expect(ManifestParseVerdict expected,
    const oh_adapter::manifest_facts::ManifestParseReceiptV1& receipt,
    std::ostringstream* evidence)
{
    *evidence << ManifestParseReceiptJson(receipt) << "\n";
    Require(receipt.verdict == expected,
        "unexpected verdict for " + receipt.requestId + ": " +
        oh_adapter::manifest_facts::ManifestParseVerdictName(receipt.verdict));
    Require((expected == ManifestParseVerdict::PARSED) ==
        receipt.facts.has_value(), "facts admission is not fail-closed");
}

}  // namespace

int main(int argc, char** argv)
{
    try {
        Require(argc == 3, "usage: test <independent-apk> <evidence-dir>");
        const std::string output = argv[2];
        ManifestFactsParserV1 parser;
        std::ostringstream receipts;
        size_t positive = 0;
        size_t negative = 0;
        size_t failure = 0;

        const std::vector<uint8_t> independent = ReadFile(argv[1]);
        const int independentFd = SealedFd(independent, true);
        auto independentRequest =
            RequestFor("P01-independent-apk", independentFd, independent);
        errno = 0;
        const uint8_t attemptedMutation = 0;
        Require(pwrite(independentFd, &attemptedMutation, 1, 0) == -1 &&
            errno == EPERM, "sealed fixture unexpectedly remained writable");
        const auto independentReceipt = parser.Parse(independentRequest);
        Expect(ManifestParseVerdict::PARSED, independentReceipt, &receipts);
        Require(!independentReceipt.facts->packageName.empty(),
            "independent APK packageName absent");
        Require(!independentReceipt.facts->components.empty(),
            "independent APK components absent");
        ++positive;

        const auto replayReceipt = parser.Parse(independentRequest);
        Expect(ManifestParseVerdict::PARSED, replayReceipt, &receipts);
        Require(ManifestParseReceiptJson(independentReceipt) ==
            ManifestParseReceiptJson(replayReceipt),
            "same sealed identity is not deterministic");
        ++positive;
        close(independentFd);

        const auto genericAxml =
            MakeAxml("org.fixture.second", false, false);
        const auto genericApk =
            MakeZip({{MANIFEST_NAME, genericAxml}});
        const int genericFd = SealedFd(genericApk, true);
        auto genericRequest =
            RequestFor("P02-second-package", genericFd, genericApk);
        const auto genericReceipt = parser.Parse(genericRequest);
        Expect(ManifestParseVerdict::PARSED, genericReceipt, &receipts);
        Require(genericReceipt.facts->packageName == "org.fixture.second",
            "package identity was not content-derived");
        Require(genericReceipt.facts->components.size() == 1,
            "synthetic component set mismatch");
        ++positive;
        close(genericFd);

        const auto duplicateAxml =
            MakeAxml("org.fixture.duplicate", true, false);
        const auto duplicateApk =
            MakeZip({{MANIFEST_NAME, duplicateAxml}});
        const int duplicateFd = SealedFd(duplicateApk, true);
        auto duplicateRequest =
            RequestFor("N01-duplicate-declaration", duplicateFd, duplicateApk);
        Expect(ManifestParseVerdict::DECLARATION_CONFLICT,
            parser.Parse(duplicateRequest), &receipts);
        ++negative;
        close(duplicateFd);

        const auto conflictAxml =
            MakeAxml("org.fixture.conflict", false, true);
        const auto conflictApk =
            MakeZip({{MANIFEST_NAME, conflictAxml}});
        const int conflictFd = SealedFd(conflictApk, true);
        auto conflictRequest =
            RequestFor("N01-conflicting-identity", conflictFd, conflictApk);
        Expect(ManifestParseVerdict::DECLARATION_CONFLICT,
            parser.Parse(conflictRequest), &receipts);
        ++negative;
        close(conflictFd);

        const auto duplicateMemberApk = MakeZip({
            {MANIFEST_NAME, genericAxml}, {MANIFEST_NAME, genericAxml},
        });
        const int duplicateMemberFd = SealedFd(duplicateMemberApk, true);
        auto duplicateMemberRequest = RequestFor(
            "N01-duplicate-manifest-member", duplicateMemberFd,
            duplicateMemberApk);
        Expect(ManifestParseVerdict::MANIFEST_DUPLICATE,
            parser.Parse(duplicateMemberRequest), &receipts);
        ++negative;
        close(duplicateMemberFd);

        auto malformedAxml = genericAxml;
        size_t startElementOffset = 0;
        for (size_t index = 0; index + 4 <= malformedAxml.size(); ++index) {
            if (malformedAxml[index] == 0x02 &&
                malformedAxml[index + 1] == 0x01 &&
                malformedAxml[index + 2] == 0x10 &&
                malformedAxml[index + 3] == 0x00) {
                startElementOffset = index;
                break;
            }
        }
        Require(startElementOffset != 0, "synthetic start element absent");
        malformedAxml[startElementOffset + 28] = 0xff;
        malformedAxml[startElementOffset + 29] = 0xff;
        const auto malformedAxmlApk =
            MakeZip({{MANIFEST_NAME, malformedAxml}});
        const int malformedAxmlFd = SealedFd(malformedAxmlApk, true);
        auto malformedAxmlRequest = RequestFor(
            "N01-malformed-axml-range", malformedAxmlFd, malformedAxmlApk);
        Expect(ManifestParseVerdict::MANIFEST_MALFORMED,
            parser.Parse(malformedAxmlRequest), &receipts);
        ++negative;
        close(malformedAxmlFd);

        const int splitFd = SealedFd(genericApk, true);
        auto splitRequest =
            RequestFor("N01-unsupported-split", splitFd, genericApk);
        ArtifactDescriptorV1 split;
        split.artifactId = "split_config.en";
        split.role = ArtifactRole::SPLIT_CONFIG;
        split.byteLength = genericApk.size();
        split.sha256 = Sha(genericApk);
        splitRequest.artifactSet.artifacts.push_back(split);
        splitRequest.artifactSet.artifactSetDigest =
            ComputeArtifactSetDigest(splitRequest.artifactSet);
        Expect(ManifestParseVerdict::NOT_SUPPORTED,
            parser.Parse(splitRequest), &receipts);
        ++negative;
        close(splitFd);

        const int mismatchFd = SealedFd(genericApk, true);
        auto digestRequest =
            RequestFor("N02-digest-mismatch", mismatchFd, genericApk);
        digestRequest.artifactSha256 = std::string(64, '0');
        digestRequest.artifactSet.artifacts.front().sha256 =
            digestRequest.artifactSha256;
        digestRequest.artifactSet.artifactSetDigest =
            ComputeArtifactSetDigest(digestRequest.artifactSet);
        Expect(ManifestParseVerdict::DIGEST_MISMATCH,
            parser.Parse(digestRequest), &receipts);
        ++negative;
        close(mismatchFd);

        const int lengthFd = SealedFd(genericApk, true);
        auto lengthRequest =
            RequestFor("N02-length-mismatch", lengthFd, genericApk);
        ++lengthRequest.byteLength;
        lengthRequest.artifactSet.artifacts.front().byteLength =
            lengthRequest.byteLength;
        lengthRequest.artifactSet.artifactSetDigest =
            ComputeArtifactSetDigest(lengthRequest.artifactSet);
        Expect(ManifestParseVerdict::BYTE_LENGTH_MISMATCH,
            parser.Parse(lengthRequest), &receipts);
        ++negative;
        close(lengthFd);

        const int unsealedFd = SealedFd(genericApk, false);
        auto unsealedRequest =
            RequestFor("F01-unsealed-fd", unsealedFd, genericApk);
        Expect(ManifestParseVerdict::FD_NOT_SEALED,
            parser.Parse(unsealedRequest), &receipts);
        ++failure;
        close(unsealedFd);

        std::vector<uint8_t> truncated(genericApk.begin(),
            genericApk.begin() + genericApk.size() / 2);
        const int truncatedFd = SealedFd(truncated, true);
        auto truncatedRequest =
            RequestFor("F01-truncated-zip", truncatedFd, truncated);
        Expect(ManifestParseVerdict::ZIP_MALFORMED,
            parser.Parse(truncatedRequest), &receipts);
        ++failure;
        close(truncatedFd);

        const int interruptedFd = SealedFd(genericApk, true);
        auto interruptedRequest =
            RequestFor("F02-interrupt-replay", interruptedFd, genericApk);
        Expect(ManifestParseVerdict::INTERRUPTED,
            parser.Parse(interruptedRequest,
                ManifestParseFault::INTERRUPT_AFTER_IDENTITY_READ),
            &receipts);
        const auto afterRestart = parser.Parse(interruptedRequest);
        Expect(ManifestParseVerdict::PARSED, afterRestart, &receipts);
        Require(afterRestart.facts->packageName == "org.fixture.second",
            "replay after interruption changed facts");
        failure += 2;
        close(interruptedFd);

        const int internalFd = SealedFd(genericApk, true);
        auto internalRequest =
            RequestFor("F01-internal-failure", internalFd, genericApk);
        Expect(ManifestParseVerdict::INTERNAL_ERROR,
            parser.Parse(internalRequest,
                ManifestParseFault::FORCE_INTERNAL_ERROR),
            &receipts);
        ++failure;
        close(internalFd);

        oh_adapter::manifest_facts::ManifestParserLimitsV1 lowLimits;
        lowLimits.maxArtifactBytes = genericApk.size() - 1;
        ManifestFactsParserV1 limitedParser(lowLimits);
        const int limitedFd = SealedFd(genericApk, true);
        auto limitedRequest =
            RequestFor("F01-artifact-limit", limitedFd, genericApk);
        Expect(ManifestParseVerdict::LIMIT_EXCEEDED,
            limitedParser.Parse(limitedRequest), &receipts);
        ++failure;
        close(limitedFd);

        WriteFile(output + "/receipts.jsonl", receipts.str());
        std::ostringstream fixtureEvidence;
        fixtureEvidence
            << "{\"construction\":\"tracked independent APK copied byte-for-byte "
               "into memfd_create(MFD_ALLOW_SEALING)\","
            << "\"fixtureSha256\":\"" << Sha(independent) << "\","
            << "\"fixtureByteLength\":" << independent.size() << ","
            << "\"readbackSha256\":\"" << Sha(independent) << "\","
            << "\"requiredSeals\":[\"F_SEAL_SEAL\",\"F_SEAL_SHRINK\","
               "\"F_SEAL_GROW\",\"F_SEAL_WRITE\"],"
            << "\"sealCheck\":\"enforced-by-parser\","
            << "\"syntheticGenericSha256\":\"" << Sha(genericApk) << "\"}\n";
        WriteFile(output + "/fixture-provenance.json", fixtureEvidence.str());
        std::ostringstream variants;
        variants << Sha(genericApk) << "  generic-second-package.apk\n"
            << Sha(duplicateApk) << "  duplicate-declaration.apk\n"
            << Sha(conflictApk) << "  conflicting-identity.apk\n"
            << Sha(duplicateMemberApk) << "  duplicate-manifest-member.apk\n"
            << Sha(malformedAxmlApk) << "  malformed-axml-range.apk\n"
            << Sha(truncated) << "  truncated-zip.apk\n";
        WriteFile(output + "/variants.sha256", variants.str());

        std::cout << "PASS fn01_a03_manifest_facts positive=" << positive
            << " negative=" << negative << " failure=" << failure
            << " deterministic_replay=true partial_facts=false"
            << " product_hardcoding=none runtime_pass=false\n";
        return 0;
    } catch (const std::exception& error) {
        std::cerr << "FAIL fn01_a03_manifest_facts: " << error.what() << "\n";
        return 1;
    }
}
