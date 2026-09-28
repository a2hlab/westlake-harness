#include "package_authority_service_v1.h"

#include "sha256.h"

#include <iostream>
#include <optional>
#include <string>
#include <string_view>

using namespace oh_adapter::package_authority;
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
    sha256(reinterpret_cast<const unsigned char*>(value.data()),
        value.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(64, '0');
    for (size_t index = 0; index < 32; ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

InstallRequestV1 MakeInstall(const std::string& packageName,
    const std::string& activityName, const std::string& transactionId,
    std::string_view bytes)
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
    request.manifest.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.manifest.parserVersion = "authority-host-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 1;
    ManifestComponentFactV1 activity;
    activity.kind = "activity";
    activity.name = activityName;
    activity.exported = true;
    request.manifest.components.push_back(activity);
    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "authority-host-verifier-v1";
    request.signing.policyProfile = "authority-policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "authority-policy-v1";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha256Hex("authority-caller");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest = ComputeInstallRequestDigest(request);
    return request;
}

CallerContextV1 CallerFor(const std::string& packageName)
{
    CallerContextV1 caller;
    caller.callerId = "authority-host-caller";
    caller.visibilityScopeDigest = Sha256Hex("authority-visibility");
    caller.visiblePackageNames = {packageName};
    return caller;
}

GetPackageRequestV1 MakeQuery(const std::string& packageName)
{
    GetPackageRequestV1 request;
    request.requestId = "query:" + packageName;
    request.packageName = packageName;
    request.caller = CallerFor(packageName);
    return request;
}

LaunchResolutionRequestV1 MakeLaunch(
    const std::string& packageName,
    const std::optional<std::string>& activityName = std::nullopt)
{
    LaunchResolutionRequestV1 request;
    request.requestId = "launch:" + packageName;
    request.packageName = packageName;
    request.caller = CallerFor(packageName);
    request.activityName = activityName;
    return request;
}

RestartRecoveryRequestV1 MakeRecovery(const InstallRequestV1& install,
    const AuthorityInstallReceiptV1& receipt)
{
    RestartRecoveryRequestV1 request;
    request.requestId = "recover:" + install.admission.transactionId;
    request.transactionId = install.admission.transactionId;
    request.boundary.beforeBootId = "boot-before";
    request.boundary.afterBootId = "boot-after";
    request.boundary.beforeServiceId = "service-before";
    request.boundary.afterServiceId = "service-after";
    request.expectedRequestDigest = install.admission.requestDigest;
    request.expectedPackageName = install.manifest.packageName;
    request.expectedArtifactSetDigest =
        install.artifactSet.artifactSetDigest;
    request.expectedGeneration = receipt.canonicalReceipt.generation;
    request.expectedCanonicalDigest =
        receipt.canonicalReceipt.durableRecordDigest;
    request.expectedPhase = DurablePhase::P6_RECEIPT_CLOSED;
    return request;
}

class FakeBmsCarrier final : public BmsExecutionCarrierV1 {
public:
    enum class Mode {
        SUCCEED,
        FAIL,
        MISMATCH,
    };

    explicit FakeBmsCarrier(Mode mode) : mode_(mode) {}

    bool EnsureActive(const BmsProjectionCommandV1& command,
        BmsProjectionReadbackV1* readback) override
    {
        ++calls;
        lastCommand = command;
        if (mode_ == Mode::FAIL) return false;
        readback->idempotencyKey = command.idempotencyKey;
        readback->packageName = command.packageName;
        readback->userId = command.userId;
        readback->generation = command.generation;
        readback->canonicalDigest = command.canonicalDigest;
        readback->active = true;
        readback->reason = "ACTIVE";
        if (mode_ == Mode::MISMATCH) {
            readback->canonicalDigest = Sha256Hex("other-generation");
        }
        return true;
    }

    void SetMode(Mode mode)
    {
        mode_ = mode;
    }

    int calls = 0;
    BmsProjectionCommandV1 lastCommand;

private:
    Mode mode_;
};

void TestPositiveGenericReadyAndRecovery(const std::string& root)
{
    const std::string lane = root + "/positive";
    const InstallRequestV1 first = MakeInstall("org.example.alpha",
        "org.example.alpha.Entry", "tx-alpha", "alpha-apk");
    AuthorityInstallReceiptV1 firstReceipt;
    {
        FilePackageStore store(lane + "/store");
        PosixPackageFileStager stager(lane + "/files");
        NoFaultInjector noFault;
        FakeBmsCarrier carrier(FakeBmsCarrier::Mode::SUCCEED);
        PackageAuthorityServiceV1 authority(
            &store, &stager, &noFault, &carrier);

        firstReceipt = authority.Install(first);
        EXPECT_EQ(firstReceipt.verdict, AuthorityInstallVerdict::READY);
        EXPECT_TRUE(firstReceipt.consumerReady);
        EXPECT_EQ(carrier.lastCommand.packageName,
            std::string("org.example.alpha"));
        EXPECT_EQ(carrier.lastCommand.manifest.packageName,
            std::string("org.example.alpha"));
        EXPECT_TRUE(!carrier.lastCommand.baseCodePath.empty());
        EXPECT_EQ(carrier.calls, 1);
        EXPECT_EQ(authority.Query(
            MakeQuery("org.example.alpha")).verdict,
            PackageQueryVerdict::READY);
        const auto launch = authority.ResolveLaunch(
            MakeLaunch("org.example.alpha"));
        EXPECT_EQ(launch.verdict, LaunchResolutionVerdict::READY);
        EXPECT_TRUE(launch.resolution.has_value());
        EXPECT_EQ(launch.resolution->activityName,
            std::string("org.example.alpha.Entry"));

        const auto replay = authority.Install(first);
        EXPECT_EQ(replay.verdict, AuthorityInstallVerdict::READY);
        EXPECT_EQ(replay.reason, std::string("IDEMPOTENT_READY_REPLAY"));
        EXPECT_EQ(replay.canonicalReceipt.generation,
            firstReceipt.canonicalReceipt.generation);
        EXPECT_EQ(carrier.calls, 1);

        const InstallRequestV1 second = MakeInstall("net.sample.beta",
            "net.sample.beta.Home", "tx-beta", "beta-apk");
        EXPECT_EQ(authority.Install(second).verdict,
            AuthorityInstallVerdict::READY);
        EXPECT_EQ(authority.ResolveLaunch(
            MakeLaunch("net.sample.beta", "net.sample.beta.Home")).verdict,
            LaunchResolutionVerdict::READY);
    }

    FilePackageStore reopened(lane + "/store");
    PackageAuthorityServiceV1 recoveredAuthority(
        &reopened, nullptr, nullptr, nullptr);
    const auto recovered =
        recoveredAuthority.Recover(MakeRecovery(first, firstReceipt));
    EXPECT_EQ(recovered.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_TRUE(recovered.consumerReady);
    const auto replayRecovery =
        recoveredAuthority.Recover(MakeRecovery(first, firstReceipt));
    EXPECT_EQ(replayRecovery.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_EQ(replayRecovery.generation, recovered.generation);
    EXPECT_EQ(recoveredAuthority.Query(
        MakeQuery("org.example.alpha")).verdict,
        PackageQueryVerdict::READY);
}

void TestNegativeCarrierCannotPublish(const std::string& root)
{
    const std::string lane = root + "/negative";
    FilePackageStore store(lane + "/store");
    PosixPackageFileStager stager(lane + "/files");
    NoFaultInjector noFault;
    FakeBmsCarrier carrier(FakeBmsCarrier::Mode::MISMATCH);
    PackageAuthorityServiceV1 authority(
        &store, &stager, &noFault, &carrier);
    const InstallRequestV1 install = MakeInstall("dev.dynamic.gamma",
        "dev.dynamic.gamma.Start", "tx-gamma", "gamma-apk");

    const auto mismatch = authority.Install(install);
    EXPECT_EQ(mismatch.verdict,
        AuthorityInstallVerdict::CARRIER_READBACK_MISMATCH);
    EXPECT_TRUE(!mismatch.consumerReady);
    EXPECT_EQ(authority.Query(
        MakeQuery("dev.dynamic.gamma")).verdict,
        PackageQueryVerdict::PACKAGE_NOT_READY);
    EXPECT_EQ(authority.ResolveLaunch(
        MakeLaunch("dev.dynamic.gamma")).verdict,
        LaunchResolutionVerdict::PACKAGE_NOT_READY);

    carrier.SetMode(FakeBmsCarrier::Mode::SUCCEED);
    const auto repaired = authority.Install(install);
    EXPECT_EQ(repaired.verdict, AuthorityInstallVerdict::READY);
    EXPECT_EQ(repaired.canonicalReceipt.generation,
        std::optional<uint64_t>(1));
}

void TestFailureNeverReportsReady(const std::string& root)
{
    const std::string lane = root + "/failure";
    FilePackageStore store(lane + "/store");
    PosixPackageFileStager stager(lane + "/files");
    NoFaultInjector noFault;
    FakeBmsCarrier carrier(FakeBmsCarrier::Mode::FAIL);
    PackageAuthorityServiceV1 authority(
        &store, &stager, &noFault, &carrier);
    InstallRequestV1 install = MakeInstall("io.failure.delta",
        "io.failure.delta.Main", "tx-delta", "delta-apk");

    const auto failed = authority.Install(install);
    EXPECT_EQ(failed.verdict, AuthorityInstallVerdict::CARRIER_FAILED);
    EXPECT_TRUE(!failed.consumerReady);
    EXPECT_EQ(authority.Query(
        MakeQuery("io.failure.delta")).verdict,
        PackageQueryVerdict::PACKAGE_NOT_READY);

    InstallRequestV1 conflict = install;
    conflict.retryIdentity = "conflicting-retry";
    conflict.admission.requestDigest = Sha256Hex("conflicting-request");
    const auto rejected = authority.Install(conflict);
    EXPECT_EQ(rejected.verdict,
        AuthorityInstallVerdict::CANONICAL_REJECTED);
    EXPECT_EQ(rejected.canonicalReceipt.verdict,
        InstallVerdict::IDEMPOTENCY_CONFLICT);
    EXPECT_TRUE(!rejected.consumerReady);
    EXPECT_EQ(carrier.calls, 1);
}

void TestRestartCompletesForwardIdempotently(const std::string& root)
{
    const std::string lane = root + "/restart-forward";
    const InstallRequestV1 install = MakeInstall("app.restart.epsilon",
        "app.restart.epsilon.Entry", "tx-epsilon", "epsilon-apk");
    AuthorityInstallReceiptV1 failed;
    {
        FilePackageStore store(lane + "/store");
        PosixPackageFileStager stager(lane + "/files");
        NoFaultInjector noFault;
        FakeBmsCarrier carrier(FakeBmsCarrier::Mode::FAIL);
        PackageAuthorityServiceV1 authority(
            &store, &stager, &noFault, &carrier);
        failed = authority.Install(install);
        EXPECT_EQ(failed.verdict, AuthorityInstallVerdict::CARRIER_FAILED);
    }

    FilePackageStore reopened(lane + "/store");
    FakeBmsCarrier recoveredCarrier(FakeBmsCarrier::Mode::SUCCEED);
    PackageAuthorityServiceV1 recoveredAuthority(
        &reopened, nullptr, nullptr, &recoveredCarrier);
    const RestartRecoveryRequestV1 recovery = MakeRecovery(install, failed);
    const auto recovered = recoveredAuthority.Recover(recovery);
    EXPECT_EQ(recovered.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_TRUE(recovered.consumerReady);
    EXPECT_EQ(recoveredCarrier.calls, 1);
    const auto replay = recoveredAuthority.Recover(recovery);
    EXPECT_EQ(replay.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_TRUE(replay.consumerReady);
    EXPECT_EQ(recoveredCarrier.calls, 1);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2) {
        std::cerr << "usage: package_authority_host_test RUN_ROOT\n";
        return 2;
    }
    const std::string root = argv[1];
    TestPositiveGenericReadyAndRecovery(root);
    TestNegativeCarrierCannotPublish(root);
    TestFailureNeverReportsReady(root);
    TestRestartCompletesForwardIdempotently(root);
    if (gFailures != 0) {
        std::cerr << "package_authority_host_test failures="
                  << gFailures << "\n";
        return 1;
    }
    std::cout
        << "PACKAGE_AUTHORITY_HOST_PNF_OK device_verdict=NOT_RUN\n";
    return 0;
}
