#include "package_transaction_v1.h"

#include "sha256.h"

#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <vector>

using namespace oh_adapter::package_transaction;

namespace {

int gFailures = 0;

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
                      << #left << " != " << #right << "\n";                       \
            ++gFailures;                                                          \
        }                                                                         \
    } while (0)

std::string Sha256Hex(std::string_view value)
{
    unsigned char digest[32]{};
    sha256(reinterpret_cast<const unsigned char*>(value.data()), value.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

class OneShotFault final : public FaultInjector {
public:
    explicit OneShotFault(std::optional<DurablePhase> target)
        : target_(target)
    {
    }

    bool InterruptAfter(DurablePhase phase) override
    {
        if (target_.has_value() && *target_ == phase && !fired_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    std::optional<DurablePhase> target_;
    bool fired_ = false;
};

InstallRequestV1 MakeRequest(const std::string& packageName,
    const std::string& transactionId, std::string_view bytes)
{
    InstallRequestV1 request;
    ArtifactDescriptorV1 artifact;
    artifact.artifactId = "base";
    artifact.role = ArtifactRole::BASE;
    artifact.bytes.assign(bytes.begin(), bytes.end());
    artifact.byteLength = artifact.bytes.size();
    artifact.sha256 = Sha256Hex(bytes);
    request.artifactSet.artifacts.push_back(artifact);
    request.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(request.artifactSet);

    request.manifest.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.manifest.parserVersion = "host-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 17;
    request.manifest.versionName = "1.7";
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;

    request.signing.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "host-verifier-v1";
    request.signing.policyProfile = "policy-stable-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2, 3};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };

    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "policy-stable-v1";
    request.retryIdentity = "retry:" + transactionId;

    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.memberIndex = 0;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha256Hex("caller:primary");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest = ComputeInstallRequestDigest(request);
    return request;
}

std::string StorePath(const std::string& root, const std::string& name)
{
    return root + "/" + name + "/store";
}

std::string FilesPath(const std::string& root, const std::string& name)
{
    return root + "/" + name + "/files";
}

void TestCanonicalArtifactSetVector()
{
    InstallRequestV1 request = MakeRequest("org.example.vector", "tx-vector", "abc");
    EXPECT_EQ(request.artifactSet.artifacts.front().sha256,
        std::string("ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb"
                    "410ff61f20015ad"));
    EXPECT_EQ(request.artifactSet.artifactSetDigest,
        std::string("d21db4677a06e8f0b363a03fd17887c61bb2bad44b793ee9c"
                    "26a55f3015a3899"));
}

void TestTwoPackagesAndDurableReplay(const std::string& root)
{
    NoFaultInjector noFault;
    {
        FilePackageStore store(StorePath(root, "positive"));
        PosixPackageFileStager stager(FilesPath(root, "positive"));
        PackageTransactionCoordinator coordinator(&store, &stager, &noFault);

        InstallRequestV1 first =
            MakeRequest("org.example.alpha", "tx-alpha", "alpha-apk-content");
        const PackageLifecycleReceiptV1 firstReceipt = coordinator.Install(first);
        EXPECT_EQ(firstReceipt.verdict, InstallVerdict::COMMITTED);
        EXPECT_EQ(firstReceipt.generation, std::optional<uint64_t>(1));

        InstallRequestV1 second =
            MakeRequest("net.sample.beta", "tx-beta", "different-beta-content");
        const PackageLifecycleReceiptV1 secondReceipt = coordinator.Install(second);
        EXPECT_EQ(secondReceipt.verdict, InstallVerdict::COMMITTED);
        EXPECT_EQ(secondReceipt.generation, std::optional<uint64_t>(1));
        EXPECT_TRUE(firstReceipt.durableRecordDigest !=
            secondReceipt.durableRecordDigest);

        const PackageLifecycleReceiptV1 replay = coordinator.Install(first);
        EXPECT_EQ(replay.verdict, InstallVerdict::COMMITTED);
        EXPECT_EQ(replay.durableRecordDigest, firstReceipt.durableRecordDigest);
    }

    FilePackageStore reopened(StorePath(root, "positive"));
    std::string error;
    EXPECT_TRUE(reopened.Open(&error));
    PublishedPackageSnapshotV1 alpha;
    PublishedPackageSnapshotV1 beta;
    EXPECT_TRUE(reopened.ReadPublishedPackage(
        0, "org.example.alpha", &alpha, &error));
    EXPECT_TRUE(reopened.ReadPublishedPackage(
        0, "net.sample.beta", &beta, &error));
    EXPECT_EQ(alpha.publicationState, PublicationState::CANONICAL_SELECTED);
    EXPECT_EQ(alpha.generation, static_cast<uint64_t>(1));
    EXPECT_EQ(beta.generation, static_cast<uint64_t>(1));
    PublicationTokenV1 alphaToken;
    EXPECT_TRUE(reopened.ReadPublicationToken(
        0, "org.example.alpha", &alphaToken, &error));
    EXPECT_EQ(alphaToken.state, PublicationState::CANONICAL_SELECTED);
    EXPECT_EQ(alphaToken.canonicalDigest, alpha.canonicalDigest);
    EXPECT_TRUE(alpha.managedFiles.baseCodePath.find("org.example.alpha") ==
        std::string::npos);
}

void TestTypedNegativeReceipts(const std::string& root)
{
    NoFaultInjector noFault;
    FilePackageStore store(StorePath(root, "negative"));
    PosixPackageFileStager stager(FilesPath(root, "negative"));
    PackageTransactionCoordinator coordinator(&store, &stager, &noFault);

    InstallRequestV1 tampered =
        MakeRequest("org.example.tampered", "tx-tampered", "original");
    tampered.artifactSet.artifacts.front().bytes.push_back('!');
    PackageLifecycleReceiptV1 result = coordinator.Install(tampered);
    EXPECT_EQ(result.verdict, InstallVerdict::ARTIFACT_DIGEST_MISMATCH);
    EXPECT_TRUE(!result.packageName.has_value());
    PackageLifecycleReceiptV1 persisted;
    std::string error;
    EXPECT_TRUE(store.ReadReceipt("tx-tampered", &persisted, &error));
    EXPECT_EQ(persisted.verdict, InstallVerdict::ARTIFACT_DIGEST_MISMATCH);

    InstallRequestV1 split =
        MakeRequest("org.example.split", "tx-split", "split");
    split.artifactSet.artifacts.front().role = ArtifactRole::SPLIT_FEATURE;
    split.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(split.artifactSet);
    split.manifest.artifactSetDigest = split.artifactSet.artifactSetDigest;
    split.signing.artifactSetDigest = split.artifactSet.artifactSetDigest;
    split.admission.requestDigest = ComputeInstallRequestDigest(split);
    result = coordinator.Install(split);
    EXPECT_EQ(result.verdict, InstallVerdict::NOT_SUPPORTED_ARTIFACT_PROFILE);

    InstallRequestV1 secondary =
        MakeRequest("org.example.secondary", "tx-secondary", "secondary");
    secondary.userId = 10;
    secondary.admission.requestDigest = ComputeInstallRequestDigest(secondary);
    result = coordinator.Install(secondary);
    EXPECT_EQ(result.verdict, InstallVerdict::NOT_SUPPORTED);

    InstallRequestV1 identity =
        MakeRequest("org.example.identity", "tx-identity", "identity");
    identity.expectedPackageName = "caller.injected.name";
    identity.admission.requestDigest = ComputeInstallRequestDigest(identity);
    result = coordinator.Install(identity);
    EXPECT_EQ(result.verdict, InstallVerdict::IDENTITY_MISMATCH);
    EXPECT_EQ(result.packageName,
        std::optional<std::string>("org.example.identity"));

    InstallRequestV1 existing =
        MakeRequest("org.example.existing", "tx-existing-1", "existing");
    EXPECT_EQ(coordinator.Install(existing).verdict, InstallVerdict::COMMITTED);
    InstallRequestV1 duplicate =
        MakeRequest("org.example.existing", "tx-existing-2", "existing");
    EXPECT_EQ(coordinator.Install(duplicate).verdict,
        InstallVerdict::PACKAGE_ALREADY_EXISTS);

    InstallRequestV1 conflict = existing;
    conflict.expectedPackageName = "different.constraint";
    conflict.admission.requestDigest = ComputeInstallRequestDigest(conflict);
    EXPECT_EQ(coordinator.Install(conflict).verdict,
        InstallVerdict::IDEMPOTENCY_CONFLICT);
}

void TestRemovalGuardFixture(const std::string& root)
{
    NoFaultInjector noFault;
    FilePackageStore store(StorePath(root, "removal"));
    std::string error;
    EXPECT_TRUE(store.Open(&error));
    EXPECT_TRUE(store.SeedRemovalTombstoneForFixture(
        0, "org.example.removing", 4, &error));
    PosixPackageFileStager stager(FilesPath(root, "removal"));
    PackageTransactionCoordinator coordinator(&store, &stager, &noFault);
    InstallRequestV1 request =
        MakeRequest("org.example.removing", "tx-removing", "removing");
    const PackageLifecycleReceiptV1 result = coordinator.Install(request);
    EXPECT_EQ(result.verdict, InstallVerdict::PACKAGE_REMOVING);
    PublishedPackageSnapshotV1 snapshot;
    EXPECT_TRUE(!store.ReadPublishedPackage(
        0, "org.example.removing", &snapshot, &error));
}

void TestPreP5Rollback(const std::string& root)
{
    OneShotFault fault(DurablePhase::P2_FILES_PREPARED);
    FilePackageStore store(StorePath(root, "rollback"));
    PosixPackageFileStager stager(FilesPath(root, "rollback"));
    PackageTransactionCoordinator coordinator(&store, &stager, &fault);
    InstallRequestV1 request =
        MakeRequest("org.example.rollback", "tx-rollback", "rollback");
    const PackageLifecycleReceiptV1 result = coordinator.Install(request);
    EXPECT_EQ(result.verdict, InstallVerdict::INTERNAL_IO_ERROR);
    EXPECT_EQ(result.terminalState, std::string("CLOSED_ROLLED_BACK"));
    PublishedPackageSnapshotV1 snapshot;
    std::string error;
    EXPECT_TRUE(!store.ReadPublishedPackage(
        0, "org.example.rollback", &snapshot, &error));
    PublicationTokenV1 token;
    EXPECT_TRUE(!store.ReadPublicationToken(
        0, "org.example.rollback", &token, &error));
    EXPECT_EQ(coordinator.Install(request).terminalState,
        std::string("CLOSED_ROLLED_BACK"));
}

void TestPostP5ForwardRecovery(const std::string& root)
{
    InstallRequestV1 request =
        MakeRequest("org.example.recover", "tx-recover", "recover");
    {
        OneShotFault fault(DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED);
        FilePackageStore store(StorePath(root, "recovery"));
        PosixPackageFileStager stager(FilesPath(root, "recovery"));
        PackageTransactionCoordinator coordinator(&store, &stager, &fault);
        const PackageLifecycleReceiptV1 interrupted = coordinator.Install(request);
        EXPECT_EQ(interrupted.verdict,
            InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
        EXPECT_EQ(interrupted.terminalState, std::string("RECOVERING_FORWARD"));
    }
    NoFaultInjector noFault;
    FilePackageStore reopened(StorePath(root, "recovery"));
    PosixPackageFileStager stager(FilesPath(root, "recovery"));
    PackageTransactionCoordinator coordinator(&reopened, &stager, &noFault);
    const PackageLifecycleReceiptV1 recovered = coordinator.Install(request);
    EXPECT_EQ(recovered.verdict, InstallVerdict::COMMITTED);
    EXPECT_EQ(recovered.generation, std::optional<uint64_t>(1));
    EXPECT_EQ(recovered.terminalState, std::string("CLOSED_COMMITTED"));
}

void TestCorruptStoreFailsClosed(const std::string& root)
{
    const std::string storePath = StorePath(root, "corrupt");
    {
        NoFaultInjector noFault;
        FilePackageStore store(storePath);
        PosixPackageFileStager stager(FilesPath(root, "corrupt"));
        PackageTransactionCoordinator coordinator(&store, &stager, &noFault);
        InstallRequestV1 request =
            MakeRequest("org.example.corrupt", "tx-corrupt-1", "corrupt");
        EXPECT_EQ(coordinator.Install(request).verdict, InstallVerdict::COMMITTED);
    }
    {
        std::ofstream output(storePath + "/events.v1.log",
            std::ios::binary | std::ios::app);
        output << "truncated-without-checksum";
    }
    NoFaultInjector noFault;
    FilePackageStore corrupt(storePath);
    PosixPackageFileStager stager(FilesPath(root, "corrupt"));
    PackageTransactionCoordinator coordinator(&corrupt, &stager, &noFault);
    InstallRequestV1 request =
        MakeRequest("org.example.other", "tx-corrupt-2", "other");
    EXPECT_EQ(coordinator.Install(request).verdict,
        InstallVerdict::DATA_INCONSISTENT);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 || argv[1] == nullptr || argv[1][0] != '/') {
        std::cerr << "usage: package_transaction_host_test ABSOLUTE_TEMP_ROOT\n";
        return 2;
    }
    const std::string root = argv[1];
    TestCanonicalArtifactSetVector();
    TestTwoPackagesAndDurableReplay(root);
    TestTypedNegativeReceipts(root);
    TestRemovalGuardFixture(root);
    TestPreP5Rollback(root);
    TestPostP5ForwardRecovery(root);
    TestCorruptStoreFailsClosed(root);
    if (gFailures != 0) {
        std::cerr << "FAIL fn01_a01_package_transaction failures=" << gFailures
                  << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a01_package_transaction"
              << " positive=2 negative=7 failure=3 restart=2"
              << " product_hardcoding=none runtime_pass=false\n";
    return 0;
}
