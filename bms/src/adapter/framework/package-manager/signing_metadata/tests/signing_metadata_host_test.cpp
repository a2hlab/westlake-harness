#include "signing_metadata_v1.h"

#include "sha256.h"

#include <algorithm>
#include <array>
#include <cerrno>
#include <cstdlib>
#include <filesystem>
#include <fcntl.h>
#include <fstream>
#include <iostream>
#include <string>
#include <sys/mman.h>
#include <sys/stat.h>
#include <thread>
#include <unistd.h>
#include <vector>

using namespace oh_adapter;
using namespace oh_adapter::package_transaction;
using namespace oh_adapter::signing_metadata;
namespace fs = std::filesystem;

namespace {

int gFailures = 0;
std::ofstream gResponses;
size_t gCases = 0;

#define EXPECT_TRUE(condition)                                                   \
    do {                                                                         \
        if (!(condition)) {                                                       \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << " "         \
                      << #condition << "\n";                                     \
            ++gFailures;                                                          \
        }                                                                         \
    } while (0)

#define EXPECT_EQ(left, right)                                                    \
    do {                                                                         \
        const auto leftValue = (left);                                             \
        const auto rightValue = (right);                                           \
        if (!(leftValue == rightValue)) {                                          \
            std::cerr << "FAIL " << __FILE__ << ":" << __LINE__ << " "         \
                      << #left << " != " << #right << "\n";                     \
            ++gFailures;                                                          \
        }                                                                         \
    } while (0)

std::vector<uint8_t> ReadBytes(const std::string& path)
{
    std::ifstream input(path, std::ios::binary);
    return std::vector<uint8_t>(
        std::istreambuf_iterator<char>(input),
        std::istreambuf_iterator<char>());
}

std::string Digest(const std::vector<uint8_t>& bytes)
{
    unsigned char digest[32]{};
    sha256(bytes.data(), bytes.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

int SealedFd(const std::vector<uint8_t>& bytes)
{
    const int fd = memfd_create(
        "fn01-a13-fixture", MFD_CLOEXEC | MFD_ALLOW_SEALING);
    if (fd < 0 || ftruncate(fd, static_cast<off_t>(bytes.size())) != 0) {
        if (fd >= 0) close(fd);
        return -1;
    }
    size_t offset = 0;
    while (offset < bytes.size()) {
        const ssize_t count = pwrite(fd, bytes.data() + offset,
            bytes.size() - offset, static_cast<off_t>(offset));
        if (count < 0 && errno == EINTR) continue;
        if (count <= 0) {
            close(fd);
            return -1;
        }
        offset += static_cast<size_t>(count);
    }
    constexpr int kSeals =
        F_SEAL_WRITE | F_SEAL_GROW | F_SEAL_SHRINK | F_SEAL_SEAL;
    if (fsync(fd) != 0 || fcntl(fd, F_ADD_SEALS, kSeals) != 0 ||
        (fcntl(fd, F_GET_SEALS) & kSeals) != kSeals) {
        close(fd);
        return -1;
    }
    return fd;
}

SigningMetadataRequestV1 RequestFor(
    const std::vector<uint8_t>& bytes, const std::string& requestId)
{
    ArtifactDescriptorV1 base;
    base.artifactId = "input-base";
    base.role = ArtifactRole::BASE;
    base.byteLength = bytes.size();
    base.sha256 = Digest(bytes);
    PackageArtifactSetV1 artifactSet;
    artifactSet.artifacts.push_back(std::move(base));
    artifactSet.artifactSetDigest = ComputeArtifactSetDigest(artifactSet);

    SigningMetadataRequestV1 request;
    request.requestId = requestId;
    request.artifactSet = std::move(artifactSet);
    request.policy.policyVersion = "fn01-signing-policy-v1";
    request.policy.verifierVersion = "native-apk-verifier-v1";
    request.policy.minimumSchemeVersion = 2;
    return request;
}

class OneShotFault final : public SigningMetadataFaultInjector {
public:
    explicit OneShotFault(SigningMetadataFaultPoint point) : point_(point) {}

    bool InterruptAfter(SigningMetadataFaultPoint point) override
    {
        if (!fired_ && point == point_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    SigningMetadataFaultPoint point_;
    bool fired_ = false;
};

class TestPolicyProvider final : public SigningMetadataPolicyProvider {
public:
    bool Resolve(const std::string& policyVersion,
        SigningMetadataPolicyV1* policy, std::string* error) const override
    {
        if (policy == nullptr) {
            if (error != nullptr) *error = "policy output is null";
            return false;
        }
        if (policyVersion != "fn01-signing-policy-v1" &&
            policyVersion != "fn01-signing-policy-v4") {
            if (error != nullptr) *error = "policy version is not registered";
            return false;
        }
        policy->schemaVersion = 1;
        policy->policyVersion = policyVersion;
        policy->verifierVersion = "native-apk-verifier-v1";
        policy->minimumSchemeVersion =
            policyVersion == "fn01-signing-policy-v4" ? 4 : 2;
        policy->targetPlatformSdk = 35;
        if (error != nullptr) error->clear();
        return true;
    }
};

void Record(const std::string& caseId,
    const SigningMetadataResponseV1& response)
{
    ++gCases;
    std::cout << caseId << " "
              << SigningMetadataVerdictName(response.verdict)
              << " signerTruthVisible="
              << (response.signerTruthVisible ? "true" : "false")
              << " replayed=" << (response.replayed ? "true" : "false")
              << "\n";
    if (gResponses) {
        gResponses << "{\"caseId\":\"" << caseId << "\",\"response\":"
                   << SerializeSigningMetadataResponseJsonV1(response)
                   << "}\n";
    }
}

fs::path OnlyReceipt(const fs::path& root)
{
    for (const auto& entry : fs::directory_iterator(root)) {
        if (entry.path().extension() == ".receipt") return entry.path();
    }
    return {};
}

size_t ReceiptCount(const fs::path& root)
{
    size_t count = 0;
    for (const auto& entry : fs::directory_iterator(root)) {
        if (entry.path().extension() == ".receipt") ++count;
    }
    return count;
}

SigningMetadataResponseV1 Execute(
    const std::vector<uint8_t>& bytes,
    const SigningMetadataRequestV1& request,
    SigningMetadataServiceV1* service)
{
    const int fd = SealedFd(bytes);
    EXPECT_TRUE(fd >= 0);
    if (fd < 0) return {};
    const auto response = service->VerifyAndPersist(fd, request);
    close(fd);
    return response;
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 6) {
        std::cerr << "usage: signing_metadata_host_test "
                     "<signed.apk> <evidence-dir> "
                     "<algorithm-list-mismatch.apk> "
                     "<v31-block-stripped.apk> "
                     "<v31-target-sdk-positive.apk>\n";
        return 2;
    }
    const std::vector<uint8_t> signedBytes = ReadBytes(argv[1]);
    const std::vector<uint8_t> algorithmMismatchBytes =
        ReadBytes(argv[3]);
    const std::vector<uint8_t> v31StrippedBytes = ReadBytes(argv[4]);
    const std::vector<uint8_t> v31PositiveBytes = ReadBytes(argv[5]);
    EXPECT_TRUE(!signedBytes.empty());
    EXPECT_TRUE(!algorithmMismatchBytes.empty());
    EXPECT_TRUE(!v31StrippedBytes.empty());
    EXPECT_TRUE(!v31PositiveBytes.empty());
    const fs::path evidenceRoot(argv[2]);
    fs::create_directories(evidenceRoot);
    gResponses.open(evidenceRoot / "responses.jsonl",
        std::ios::out | std::ios::trunc);

    char tempTemplate[] = "/tmp/fn01-a13-host-XXXXXX";
    char* created = mkdtemp(tempTemplate);
    EXPECT_TRUE(created != nullptr);
    if (created == nullptr || signedBytes.empty()) return 1;
    const fs::path root(created);

    NoSigningMetadataFaultInjector noFault;
    TestPolicyProvider policyProvider;
    FileSigningMetadataReceiptStore store((root / "main").string());
    std::string error;
    EXPECT_TRUE(store.Open(&error));
    SigningMetadataServiceV1 service(
        &store, &policyProvider, &noFault);

    auto request = RequestFor(signedBytes, "p01-core");
    auto response = Execute(signedBytes, request, &service);
    Record("P01-core-success", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.receipt.has_value());
    EXPECT_TRUE(response.signerTruthVisible);
    EXPECT_TRUE(!response.replayed);
    EXPECT_TRUE(response.receipt.has_value() &&
        !response.receipt->signers.empty());
    EXPECT_TRUE(response.receipt.has_value() &&
        !response.receipt->contentDigests.empty());
    EXPECT_TRUE(response.receipt.has_value() &&
        !response.receipt->continuityDecision.has_value());
    const std::string receiptDigest = response.receipt.has_value() ?
        response.receipt->receiptDigest : "";
    const auto signer = response.receipt.has_value() ?
        response.receipt->signers.front().certificateSha256 : "";

    request.requestId = "p02-replay-other-request";
    response = Execute(signedBytes, request, &service);
    Record("P02-idempotent-replay", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.replayed);
    EXPECT_TRUE(response.receipt.has_value() &&
        response.receipt->receiptDigest == receiptDigest);
    EXPECT_EQ(ReceiptCount(root / "main"), 1u);

    PriorSigningFactsV1 samePrior;
    Sha256Digest signerDigest{};
    for (size_t index = 0; index < signerDigest.size(); ++index) {
        const auto byte = signer.substr(index * 2, 2);
        signerDigest[index] = static_cast<uint8_t>(
            std::strtoul(byte.c_str(), nullptr, 16));
    }
    samePrior.currentSignerSha256.push_back(signerDigest);
    request.requestId = "p02-continuity-same-signer";
    request.priorSigningFacts = samePrior;
    response = Execute(signedBytes, request, &service);
    Record("P02-continuity-same-signer", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.receipt.has_value() &&
        response.receipt->receiptDigest == receiptDigest);
    EXPECT_TRUE(response.receipt.has_value() &&
        response.receipt->continuityDecision.has_value() &&
        response.receipt->continuityDecision->allowed &&
        response.receipt->continuityDecision->capabilityPath ==
            "SAME_SIGNER_SET" &&
        response.receipt->continuityDecision->
            priorSigningFactsDigest.size() == 64 &&
        response.receipt->continuityDecision->decisionDigest.size() == 64);

    auto unsupported = RequestFor(signedBytes, "n01-v4-unsupported");
    unsupported.policy.policyVersion = "fn01-signing-policy-v4";
    unsupported.policy.minimumSchemeVersion = 4;
    response = Execute(signedBytes, unsupported, &service);
    Record("N01-v4-typed-reject", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::NOT_SUPPORTED_SCHEME);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto v31Positive = RequestFor(
        v31PositiveBytes, "p01-v31-target-sdk-positive");
    response = Execute(v31PositiveBytes, v31Positive, &service);
    Record("P01-v31-target-sdk-positive", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.receipt.has_value() &&
        response.receipt->schemeVersion == 3 &&
        !response.receipt->signers.empty());

    auto downgraded = RequestFor(signedBytes, "n01-policy-downgrade");
    downgraded.policy.minimumSchemeVersion = 1;
    response = Execute(signedBytes, downgraded, &service);
    Record("N01-caller-policy-downgrade", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::POLICY_MISMATCH);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto unknownPolicy = RequestFor(signedBytes, "n01-policy-unknown");
    unknownPolicy.policy.policyVersion = "fn01-signing-policy-unknown";
    response = Execute(signedBytes, unknownPolicy, &service);
    Record("N01-unknown-policy", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::POLICY_NOT_FOUND);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto incompatible = RequestFor(signedBytes, "n01-update-incompatible");
    PriorSigningFactsV1 alienPrior;
    Sha256Digest alien{};
    alien.fill(0xa5);
    alienPrior.currentSignerSha256.push_back(alien);
    incompatible.priorSigningFacts = alienPrior;
    response = Execute(signedBytes, incompatible, &service);
    Record("N01-update-incompatible", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::UPDATE_INCOMPATIBLE);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto digestMismatch = RequestFor(signedBytes, "n02-digest-mismatch");
    digestMismatch.artifactSet.artifacts.front().sha256 =
        std::string(64, '0');
    digestMismatch.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(digestMismatch.artifactSet);
    response = Execute(signedBytes, digestMismatch, &service);
    Record("N02-artifact-digest-mismatch", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::ARTIFACT_DIGEST_MISMATCH);
    EXPECT_TRUE(!response.signerTruthVisible);

    auto split = RequestFor(signedBytes, "n02-split-profile");
    auto splitArtifact = split.artifactSet.artifacts.front();
    splitArtifact.artifactId = "input-split";
    splitArtifact.role = ArtifactRole::SPLIT_CONFIG;
    split.artifactSet.artifacts.push_back(std::move(splitArtifact));
    split.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(split.artifactSet);
    response = Execute(signedBytes, split, &service);
    Record("N02-split-profile", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE);

    auto algorithmMismatch = RequestFor(
        algorithmMismatchBytes, "n02-algorithm-list-mismatch");
    response = Execute(
        algorithmMismatchBytes, algorithmMismatch, &service);
    Record("N02-signature-digest-algorithm-list-mismatch", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::SIGNATURE_INVALID);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto v31Stripped = RequestFor(
        v31StrippedBytes, "n02-v31-block-stripped");
    response = Execute(v31StrippedBytes, v31Stripped, &service);
    Record("N02-v31-block-stripped", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::BAD_LINEAGE);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    auto tamperedBytes = signedBytes;
    tamperedBytes[std::min<size_t>(100, tamperedBytes.size() - 1)] ^= 0xff;
    auto tampered = RequestFor(tamperedBytes, "f01-tamper");
    response = Execute(tamperedBytes, tampered, &service);
    Record("F01-tamper", response);
    EXPECT_TRUE(response.verdict ==
        SigningMetadataVerdict::SIGNATURE_INVALID ||
        response.verdict == SigningMetadataVerdict::BAD_LINEAGE);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    std::vector<uint8_t> truncated(
        signedBytes.begin(),
        signedBytes.begin() + std::min<size_t>(4096, signedBytes.size()));
    auto truncatedRequest = RequestFor(truncated, "f01-truncated");
    response = Execute(truncated, truncatedRequest, &service);
    Record("F01-truncation", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::SIGNATURE_INVALID);
    EXPECT_TRUE(!response.signerTruthVisible);

    const fs::path swapSource = root / "swap-source.apk";
    {
        std::ofstream output(swapSource, std::ios::binary);
        output.write(reinterpret_cast<const char*>(signedBytes.data()),
            static_cast<std::streamsize>(signedBytes.size()));
    }
    const auto snapshotted = ReadBytes(swapSource.string());
    const int swapFd = SealedFd(snapshotted);
    {
        std::ofstream output(swapSource,
            std::ios::binary | std::ios::trunc);
        output.write(reinterpret_cast<const char*>(tamperedBytes.data()),
            static_cast<std::streamsize>(tamperedBytes.size()));
    }
    auto swapRequest = RequestFor(snapshotted, "f01-path-swap");
    response = service.VerifyAndPersist(swapFd, swapRequest);
    close(swapFd);
    Record("F01-path-swap-cannot-replace-sealed-fd", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.receipt.has_value() &&
        response.receipt->artifactSha256 == Digest(snapshotted));

    FileSigningMetadataReceiptStore prePersistStore(
        (root / "pre-persist").string());
    EXPECT_TRUE(prePersistStore.Open(&error));
    OneShotFault prePersistFault(
        SigningMetadataFaultPoint::AFTER_CRYPTOGRAPHIC_VERIFY);
    SigningMetadataServiceV1 prePersistService(
        &prePersistStore, &policyProvider, &prePersistFault);
    auto restartRequest = RequestFor(signedBytes, "f02-before-persist");
    response = Execute(signedBytes, restartRequest, &prePersistService);
    Record("F02-before-persist-interrupt", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::INTERRUPTED);
    EXPECT_EQ(ReceiptCount(root / "pre-persist"), 0u);

    FileSigningMetadataReceiptStore postPersistStore(
        (root / "post-persist").string());
    EXPECT_TRUE(postPersistStore.Open(&error));
    OneShotFault postPersistFault(
        SigningMetadataFaultPoint::AFTER_RECEIPT_PERSIST);
    SigningMetadataServiceV1 postPersistService(
        &postPersistStore, &policyProvider, &postPersistFault);
    restartRequest.requestId = "f02-after-persist";
    response = Execute(signedBytes, restartRequest, &postPersistService);
    Record("F02-after-persist-interrupt", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::INTERRUPTED);
    EXPECT_TRUE(!response.signerTruthVisible);
    EXPECT_EQ(ReceiptCount(root / "post-persist"), 1u);

    FileSigningMetadataReceiptStore restartedStore(
        (root / "post-persist").string());
    EXPECT_TRUE(restartedStore.Open(&error));
    SigningMetadataServiceV1 restartedService(
        &restartedStore, &policyProvider, &noFault);
    restartRequest.requestId = "f02-restart-replay";
    response = Execute(signedBytes, restartRequest, &restartedService);
    Record("F02-restart-replay", response);
    EXPECT_EQ(response.verdict, SigningMetadataVerdict::VERIFIED);
    EXPECT_TRUE(response.replayed && response.signerTruthVisible);

    const fs::path corruptPath = OnlyReceipt(root / "post-persist");
    EXPECT_TRUE(!corruptPath.empty());
    {
        std::ofstream output(corruptPath,
            std::ios::out | std::ios::trunc);
        output << "corrupt";
    }
    response = Execute(signedBytes, restartRequest, &restartedService);
    Record("F02-corrupt-readback", response);
    EXPECT_EQ(response.verdict,
        SigningMetadataVerdict::READBACK_FAILED);
    EXPECT_TRUE(!response.receipt.has_value() &&
        !response.signerTruthVisible);

    FileSigningMetadataReceiptStore concurrentStore(
        (root / "concurrent").string());
    EXPECT_TRUE(concurrentStore.Open(&error));
    constexpr size_t kConcurrentWorkers = 8;
    std::array<SigningMetadataResponseV1, kConcurrentWorkers>
        concurrentResponses;
    std::vector<std::thread> workers;
    workers.reserve(kConcurrentWorkers);
    for (size_t index = 0; index < kConcurrentWorkers; ++index) {
        workers.emplace_back([&, index] {
            NoSigningMetadataFaultInjector threadFault;
            SigningMetadataServiceV1 threadService(
                &concurrentStore, &policyProvider, &threadFault);
            auto concurrentRequest = RequestFor(
                signedBytes, "p02-concurrent-" + std::to_string(index));
            concurrentResponses[index] = Execute(
                signedBytes, concurrentRequest, &threadService);
        });
    }
    for (auto& worker : workers) worker.join();
    for (size_t index = 0; index < kConcurrentWorkers; ++index) {
        Record("P02-concurrent-immutable-" + std::to_string(index),
            concurrentResponses[index]);
        EXPECT_EQ(concurrentResponses[index].verdict,
            SigningMetadataVerdict::VERIFIED);
        EXPECT_TRUE(concurrentResponses[index].receipt.has_value());
    }
    EXPECT_EQ(ReceiptCount(root / "concurrent"), 1u);

    {
        std::ofstream artifact(evidenceRoot / "artifact-hashes.json",
            std::ios::out | std::ios::trunc);
        artifact << "{\"fixtureSha256\":\"" << Digest(signedBytes)
                 << "\",\"fixtureByteLength\":" << signedBytes.size()
                 << ",\"productPackageConstants\":[]}\n";
    }
    {
        std::ofstream summary(evidenceRoot / "summary.json",
            std::ios::out | std::ios::trunc);
        summary << "{\"actionId\":\"Fn01.A13\","
                << "\"developerVerdict\":\""
                << (gFailures == 0 ? "BUILD_TEST_PASS" : "FAIL")
                << "\",\"formalVerdictIssued\":false,"
                << "\"caseCount\":" << gCases
                << ",\"failures\":" << gFailures << "}\n";
    }
    gResponses.close();
    fs::remove_all(root);

    if (gFailures != 0) {
        std::cerr << "FAIL Fn01.A13 developer matrix failures="
                  << gFailures << "\n";
        return 1;
    }
    std::cout << "PASS Fn01.A13 developer P/N/F/restart matrix cases="
              << gCases << " formal_verdict=NOT_ISSUED\n";
    return 0;
}
