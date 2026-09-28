#include "package_query_v1.h"

#include "sha256.h"

#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>

using namespace oh_adapter::package_query;
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

InstallRequestV1 MakeInstallRequest(const std::string& packageName,
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
    request.manifest.versionCode = 1;
    request.signing.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "host-verifier-v1";
    request.signing.policyProfile = "policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "policy-v1";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha256Hex("caller");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest = ComputeInstallRequestDigest(request);
    return request;
}

GetPackageRequestV1 MakeQuery(
    const std::string& requestId, const std::string& packageName)
{
    GetPackageRequestV1 request;
    request.requestId = requestId;
    request.packageName = packageName;
    request.caller.callerId = "caller:" + requestId;
    request.caller.visibilityScopeDigest = Sha256Hex("visibility:" + requestId);
    request.caller.visiblePackageNames = {packageName};
    return request;
}

class OneShotQueryFault final : public QueryFaultInjector {
public:
    explicit OneShotQueryFault(std::optional<QueryPhase> phase)
        : phase_(phase)
    {
    }

    bool InterruptAfter(QueryPhase phase) override
    {
        if (phase_ == phase && !fired_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    std::optional<QueryPhase> phase_;
    bool fired_ = false;
};

void SeedCommitted(FilePackageStore* store, PackageTransactionCoordinator* coordinator,
    const std::string& packageName, const std::string& transactionId,
    std::string_view bytes, PublicationState tokenState,
    const std::optional<std::string>& projectionDigest = std::nullopt)
{
    const auto receipt =
        coordinator->Install(MakeInstallRequest(packageName, transactionId, bytes));
    EXPECT_EQ(receipt.verdict, InstallVerdict::COMMITTED);
    EXPECT_TRUE(receipt.generation.has_value());
    EXPECT_TRUE(receipt.durableRecordDigest.has_value());
    std::string error;
    EXPECT_TRUE(store->SeedHostProjectionForFixture(0, packageName,
        receipt.generation.value_or(0),
        projectionDigest.value_or(receipt.durableRecordDigest.value_or("")),
        HostProjectionState::ACTIVE, tokenState, &error));
}

void TestPositiveAndReplay(const std::string& root)
{
    NoFaultInjector noInstallFault;
    FilePackageStore store(root + "/positive/store");
    PosixPackageFileStager stager(root + "/positive/files");
    PackageTransactionCoordinator coordinator(&store, &stager, &noInstallFault);
    SeedCommitted(&store, &coordinator, "org.example.reader", "tx-reader",
        "reader-apk", PublicationState::EXTERNAL_READY);
    SeedCommitted(&store, &coordinator, "net.sample.second", "tx-second",
        "different-apk", PublicationState::EXTERNAL_READY);

    NoQueryFaultInjector noQueryFault;
    PackageQueryService service(&store, &noQueryFault);
    const auto request = MakeQuery("query-reader", "org.example.reader");
    const auto first = service.GetPackage(request);
    const auto replay = service.GetPackage(request);
    EXPECT_EQ(first.verdict, PackageQueryVerdict::READY);
    EXPECT_TRUE(first.package.has_value());
    EXPECT_EQ(first.package->lifecycle, std::string("ACTIVE"));
    EXPECT_EQ(first.package->readiness, std::string("READY"));
    EXPECT_EQ(first.catalogRevision, replay.catalogRevision);
    EXPECT_EQ(first.package->canonicalDigest, replay.package->canonicalDigest);
    const auto second =
        service.GetPackage(MakeQuery("query-second", "net.sample.second"));
    EXPECT_EQ(second.verdict, PackageQueryVerdict::READY);
    EXPECT_TRUE(second.package->canonicalDigest != first.package->canonicalDigest);
}

void TestTypedNegatives(const std::string& root)
{
    NoFaultInjector noInstallFault;
    FilePackageStore store(root + "/negative/store");
    PosixPackageFileStager stager(root + "/negative/files");
    PackageTransactionCoordinator coordinator(&store, &stager, &noInstallFault);
    SeedCommitted(&store, &coordinator, "org.example.visible", "tx-visible",
        "visible-apk", PublicationState::EXTERNAL_READY);
    std::string error;
    EXPECT_TRUE(store.SeedRemovalTombstoneForFixture(
        0, "org.example.removing", 7, &error));

    NoQueryFaultInjector noQueryFault;
    PackageQueryService service(&store, &noQueryFault);
    EXPECT_EQ(service.GetPackage(
        MakeQuery("query-missing", "org.example.missing")).verdict,
        PackageQueryVerdict::PACKAGE_NOT_FOUND);
    auto hidden = MakeQuery("query-hidden", "org.example.visible");
    hidden.caller.visiblePackageNames.clear();
    const auto hiddenResult = service.GetPackage(hidden);
    EXPECT_EQ(hiddenResult.verdict, PackageQueryVerdict::PACKAGE_NOT_VISIBLE);
    EXPECT_TRUE(!hiddenResult.package.has_value());
    EXPECT_EQ(hiddenResult.catalogRevision, static_cast<uint64_t>(0));
    EXPECT_EQ(service.GetPackage(
        MakeQuery("query-removing", "org.example.removing")).verdict,
        PackageQueryVerdict::PACKAGE_REMOVING);
    auto secondary = MakeQuery("query-secondary", "org.example.visible");
    secondary.userId = 10;
    EXPECT_EQ(service.GetPackage(secondary).verdict,
        PackageQueryVerdict::NOT_SUPPORTED);
    auto flags = MakeQuery("query-flags", "org.example.visible");
    flags.flags = 1;
    EXPECT_EQ(service.GetPackage(flags).verdict,
        PackageQueryVerdict::NOT_SUPPORTED);
}

void TestMismatchAndNotReady(const std::string& root)
{
    NoFaultInjector noInstallFault;
    FilePackageStore store(root + "/failure/store");
    PosixPackageFileStager stager(root + "/failure/files");
    PackageTransactionCoordinator coordinator(&store, &stager, &noInstallFault);
    SeedCommitted(&store, &coordinator, "org.example.pending", "tx-pending",
        "pending-apk", PublicationState::CANONICAL_SELECTED);

    NoQueryFaultInjector noQueryFault;
    PackageQueryService service(&store, &noQueryFault);
    EXPECT_EQ(service.GetPackage(
        MakeQuery("query-pending", "org.example.pending")).verdict,
        PackageQueryVerdict::PACKAGE_NOT_READY);

    PublishedPackageSnapshotV1 canonical;
    std::string error;
    EXPECT_TRUE(store.ReadPublishedPackage(
        0, "org.example.pending", &canonical, &error));
    EXPECT_TRUE(store.SeedHostProjectionForFixture(
        0, "org.example.pending", canonical.generation,
        Sha256Hex("wrong-generation-digest"), HostProjectionState::ACTIVE,
        PublicationState::EXTERNAL_READY, &error));
    EXPECT_EQ(service.GetPackage(
        MakeQuery("query-mismatch", "org.example.pending")).verdict,
        PackageQueryVerdict::DATA_INCONSISTENT);
    EXPECT_TRUE(store.SeedHostProjectionForFixture(
        0, "org.example.pending", canonical.generation,
        canonical.canonicalDigest, HostProjectionState::ACTIVE,
        PublicationState::EXTERNAL_READY, &error));
    auto expected = MakeQuery("query-expected", "org.example.pending");
    expected.expectedGeneration = canonical.generation + 1;
    EXPECT_EQ(service.GetPackage(expected).verdict,
        PackageQueryVerdict::DATA_INCONSISTENT);
}

void TestRestartAndInterruptions(const std::string& root)
{
    const std::string storePath = root + "/restart/store";
    {
        NoFaultInjector noInstallFault;
        FilePackageStore store(storePath);
        PosixPackageFileStager stager(root + "/restart/files");
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noInstallFault);
        SeedCommitted(&store, &coordinator, "org.example.restart", "tx-restart",
            "restart-apk", PublicationState::EXTERNAL_READY);
    }
    FilePackageStore reopened(storePath);
    for (QueryPhase phase : {QueryPhase::SNAPSHOT_FROZEN,
             QueryPhase::VISIBILITY_CHECKED, QueryPhase::RESPONSE_SERIALIZED}) {
        OneShotQueryFault fault(phase);
        PackageQueryService interrupted(&reopened, &fault);
        EXPECT_EQ(interrupted.GetPackage(
            MakeQuery("query-interrupt", "org.example.restart")).verdict,
            PackageQueryVerdict::PACKAGE_NOT_READY);
        NoQueryFaultInjector noFault;
        PackageQueryService replay(&reopened, &noFault);
        EXPECT_EQ(replay.GetPackage(
            MakeQuery("query-replay", "org.example.restart")).verdict,
            PackageQueryVerdict::READY);
    }
}

void TestCorruptStoreFailsClosed(const std::string& root)
{
    const std::string storePath = root + "/corrupt/store";
    {
        FilePackageStore store(storePath);
        std::string error;
        EXPECT_TRUE(store.Open(&error));
    }
    {
        std::ofstream output(
            storePath + "/events.v1.log", std::ios::binary | std::ios::app);
        output << "corrupt";
    }
    FilePackageStore corrupt(storePath);
    NoQueryFaultInjector noFault;
    PackageQueryService service(&corrupt, &noFault);
    EXPECT_EQ(service.GetPackage(
        MakeQuery("query-corrupt", "org.example.any")).verdict,
        PackageQueryVerdict::DATA_INCONSISTENT);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 || argv[1] == nullptr || argv[1][0] != '/') {
        std::cerr << "usage: package_query_host_test ABSOLUTE_TEMP_ROOT\n";
        return 2;
    }
    const std::string root = argv[1];
    TestPositiveAndReplay(root);
    TestTypedNegatives(root);
    TestMismatchAndNotReady(root);
    TestRestartAndInterruptions(root);
    TestCorruptStoreFailsClosed(root);
    if (gFailures != 0) {
        std::cerr << "FAIL fn01_a02_package_query failures="
                  << gFailures << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a02_package_query"
              << " positive=2 negative=5 failure=6 restart=3"
              << " product_hardcoding=none runtime_pass=false\n";
    return 0;
}
