#include "package_transaction_v1.h"

#include "sha256.h"

#include <fstream>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <sys/wait.h>
#include <unistd.h>
#include <vector>

using namespace oh_adapter::package_transaction;

namespace {

int gFailures = 0;
std::ofstream gResults;
const char* gProgramPath = nullptr;

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
    request.manifest.parserVersion = "a11-host-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 11;
    request.manifest.versionName = "1.1";
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;
    request.manifest.applicationClassName = packageName + ".Application";
    request.manifest.applicationLabel = "A11";
    request.signing.artifactSetDigest = request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "a11-host-verifier-v1";
    request.signing.policyProfile = "a11-policy-v1";
    request.signing.verified = true;
    request.signing.schemeVersions = {2, 3};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "a11-policy-v1";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Sha256Hex("a11-primary-caller");
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

RestartRecoveryRequestV1 RecoveryRequest(const InstallRequestV1& install,
    const std::string& suffix)
{
    RestartRecoveryRequestV1 request;
    request.requestId = "recover:" + suffix;
    request.transactionId = install.admission.transactionId;
    request.boundary.beforeBootId = "boot-before:" + suffix;
    request.boundary.afterBootId = "boot-after:" + suffix;
    request.boundary.beforeServiceId = "service-before:" + suffix;
    request.boundary.afterServiceId = "service-after:" + suffix;
    request.expectedRequestDigest = install.admission.requestDigest;
    request.expectedPackageName = install.manifest.packageName;
    request.expectedArtifactSetDigest =
        install.artifactSet.artifactSetDigest;
    request.expectedGeneration = 1;
    return request;
}

void Record(const RestartRecoveryReceiptV1& receipt)
{
    gResults << SerializeRestartRecoveryReceipt(receipt) << "\n";
    gResults.flush();
}

void TestExclusiveWriterLease(const std::string& root)
{
    const std::string storePath = StorePath(root, "n02-writer-lease");
    {
        FilePackageStore owner(storePath);
        std::string error;
        EXPECT_TRUE(owner.Open(&error));

        FilePackageStore sameProcessContender(storePath);
        error.clear();
        EXPECT_TRUE(!sameProcessContender.Open(&error));
        EXPECT_TRUE(error.find("writer lease") != std::string::npos);

        const pid_t child = fork();
        EXPECT_TRUE(child >= 0);
        if (child == 0) {
            execl(gProgramPath, gProgramPath, "--expect-lock-held",
                storePath.c_str(), static_cast<char*>(nullptr));
            _exit(127);
        }
        if (child > 0) {
            int status = 0;
            EXPECT_EQ(waitpid(child, &status, 0), child);
            EXPECT_TRUE(WIFEXITED(status));
            EXPECT_EQ(WEXITSTATUS(status), 0);
        }
    }
    FilePackageStore successor(storePath);
    std::string error;
    EXPECT_TRUE(successor.Open(&error));
}

void TestInvalidEnvelopeIsolation(const std::string& root)
{
    const std::string lane = "n02-invalid-envelope-isolation";
    InstallRequestV1 valid = MakeRequest(
        "org.a11.envelope", "tx-a11-envelope", "envelope-apk");
    InstallRequestV1 invalid = valid;
    invalid.admission.memberId.clear();
    PackageLifecycleReceiptV1 committed;
    {
        NoFaultInjector noFault;
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        PackageTransactionCoordinator coordinator(&store, &stager, &noFault);
        const PackageLifecycleReceiptV1 rejected =
            coordinator.Install(invalid);
        EXPECT_EQ(rejected.verdict, InstallVerdict::INVALID_ENVELOPE);
        EXPECT_EQ(rejected.terminalState, std::string("REJECTED_TYPED"));
        PackageLifecycleReceiptV1 absent;
        std::string error;
        EXPECT_TRUE(!store.ReadReceipt(
            invalid.admission.transactionId, &absent, &error));
        committed = coordinator.Install(valid);
        EXPECT_EQ(committed.verdict, InstallVerdict::COMMITTED);
        EXPECT_EQ(committed.generation, std::optional<uint64_t>(1));
    }
    FilePackageStore restarted(StorePath(root, lane));
    RestartRecoveryRequestV1 recovery =
        RecoveryRequest(valid, lane);
    recovery.expectedCanonicalDigest = committed.durableRecordDigest;
    recovery.expectedPhase = DurablePhase::P6_RECEIPT_CLOSED;
    const RestartRecoveryReceiptV1 recovered =
        restarted.RecoverAfterRestart(recovery);
    Record(recovered);
    EXPECT_EQ(recovered.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_EQ(recovered.generation, std::optional<uint64_t>(1));
}

class ProcessCrashFault final : public FaultInjector {
public:
    explicit ProcessCrashFault(DurablePhase phase) : phase_(phase) {}

    bool InterruptAfter(DurablePhase phase) override
    {
        if (!fired_ && phase == phase_) {
            fired_ = true;
            return true;
        }
        return false;
    }

    bool SimulatesProcessCrash() const override
    {
        return true;
    }

private:
    DurablePhase phase_;
    bool fired_ = false;
};

void TestClosedInstallRecovery(const std::string& root)
{
    const std::string lane = "p01-closed";
    InstallRequestV1 request =
        MakeRequest("org.a11.closed", "tx-a11-closed", "a11-closed-apk");
    PackageLifecycleReceiptV1 before;
    PublishedPackageSnapshotV1 beforeSnapshot;
    {
        NoFaultInjector noFault;
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        PackageTransactionCoordinator coordinator(&store, &stager, &noFault);
        before = coordinator.Install(request);
        EXPECT_EQ(before.verdict, InstallVerdict::COMMITTED);
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, request.manifest.packageName, &beforeSnapshot, &error));
    }

    FilePackageStore reopened(StorePath(root, lane));
    RestartRecoveryRequestV1 recovery = RecoveryRequest(request, lane);
    recovery.expectedCanonicalDigest = before.durableRecordDigest;
    recovery.expectedPhase = DurablePhase::P6_RECEIPT_CLOSED;
    const RestartRecoveryReceiptV1 result =
        reopened.RecoverAfterRestart(recovery);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_EQ(result.generation, before.generation);
    EXPECT_EQ(result.canonicalDigest, before.durableRecordDigest);
    EXPECT_EQ(result.artifactSetDigest, before.artifactSetDigest);
    EXPECT_TRUE(result.managedFiles.has_value());
    EXPECT_EQ(result.managedFiles->baseCodePath,
        beforeSnapshot.managedFiles.baseCodePath);
    EXPECT_EQ(result.managedFiles->baseCodeDigest,
        beforeSnapshot.managedFiles.baseCodeDigest);
    EXPECT_TRUE(result.primaryUserState.has_value());
    EXPECT_TRUE(result.primaryUserState->installed);
    EXPECT_TRUE(result.primaryUserState->enabled);
    EXPECT_TRUE(!result.primaryUserState->stopped);
    EXPECT_TRUE(!result.primaryUserState->hidden);
    EXPECT_EQ(result.artifacts.size(), static_cast<size_t>(1));
    EXPECT_EQ(result.artifacts.front().artifactId,
        request.artifactSet.artifacts.front().artifactId);
    EXPECT_EQ(result.artifacts.front().byteLength,
        request.artifactSet.artifacts.front().byteLength);
    EXPECT_EQ(result.artifacts.front().sha256,
        request.artifactSet.artifacts.front().sha256);
    EXPECT_TRUE(!result.consumerReady);

    RestartRecoveryRequestV1 replay = recovery;
    replay.requestId = "recover:p02-replay";
    replay.boundary.beforeServiceId = "service-before:p02";
    replay.boundary.afterServiceId = "service-after:p02";
    const RestartRecoveryReceiptV1 replayResult =
        reopened.RecoverAfterRestart(replay);
    Record(replayResult);
    EXPECT_EQ(replayResult.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_EQ(replayResult.catalogRevision, result.catalogRevision);
    EXPECT_EQ(replayResult.canonicalDigest, result.canonicalDigest);

    std::string error;
    EXPECT_TRUE(reopened.SeedHostProjectionForFixture(
        0, request.manifest.packageName, *before.generation,
        *before.durableRecordDigest, HostProjectionState::PREPARED,
        PublicationState::CANONICAL_SELECTED, &error));
    RestartRecoveryRequestV1 prepared =
        RecoveryRequest(request, "f02-prepared-projection");
    prepared.expectedCanonicalDigest = before.durableRecordDigest;
    prepared.expectedPhase = DurablePhase::P6_RECEIPT_CLOSED;
    const RestartRecoveryReceiptV1 preparedResult =
        reopened.RecoverAfterRestart(prepared);
    Record(preparedResult);
    EXPECT_EQ(preparedResult.verdict,
        RestartRecoveryVerdict::RESTORED_COMMITTED);
    EXPECT_TRUE(!preparedResult.consumerReady);
    EXPECT_EQ(preparedResult.hostProjectionState,
        HostProjectionState::PREPARED);
    PackageManagementReadV1 management;
    EXPECT_TRUE(reopened.ReadPackageManagementState(
        0, request.manifest.packageName, &management, &error));
    EXPECT_TRUE(management.projection.has_value());
    EXPECT_EQ(management.projection->state,
        HostProjectionState::PREPARED);
}

void TestPhaseMatrix(const std::string& root)
{
    {
        FilePackageStore empty(StorePath(root, "f01-before-p0"));
        RestartRecoveryRequestV1 missing;
        missing.requestId = "recover:f01-before-p0";
        missing.transactionId = "tx-before-p0";
        missing.boundary =
            {"boot-a", "boot-b", "service-a", "service-b"};
        const RestartRecoveryReceiptV1 result =
            empty.RecoverAfterRestart(missing);
        Record(result);
        EXPECT_EQ(result.verdict, RestartRecoveryVerdict::ABSENT);
        EXPECT_TRUE(!result.journalPresent);
    }

    const std::vector<DurablePhase> phases = {
        DurablePhase::P0_INPUT_FROZEN,
        DurablePhase::P1_PLAN_DURABLE,
        DurablePhase::P2_FILES_PREPARED,
        DurablePhase::P3_CANONICAL_PREPARED,
        DurablePhase::P4_PUBLICATION_PREPARED,
        DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED,
    };
    for (size_t index = 0; index < phases.size(); ++index) {
        const DurablePhase phase = phases[index];
        const std::string suffix = "f01-phase-" + std::to_string(index);
        InstallRequestV1 request = MakeRequest(
            "org.a11.phase" + std::to_string(index),
            "tx-a11-phase-" + std::to_string(index),
            "phase-apk-" + std::to_string(index));
        {
            ProcessCrashFault fault(phase);
            FilePackageStore store(StorePath(root, suffix));
            PosixPackageFileStager stager(FilesPath(root, suffix));
            PackageTransactionCoordinator coordinator(&store, &stager, &fault);
            const PackageLifecycleReceiptV1 interrupted =
                coordinator.Install(request);
            EXPECT_EQ(interrupted.verdict,
                InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
        }
        FilePackageStore restarted(StorePath(root, suffix));
        RestartRecoveryRequestV1 recovery =
            RecoveryRequest(request, suffix);
        const RestartRecoveryReceiptV1 result =
            restarted.RecoverAfterRestart(recovery);
        Record(result);
        if (phase == DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED) {
            EXPECT_EQ(result.verdict,
                RestartRecoveryVerdict::RESTORED_COMMITTED);
            EXPECT_EQ(result.durablePhase,
                DurablePhase::P6_RECEIPT_CLOSED);
        } else {
            EXPECT_EQ(result.verdict, RestartRecoveryVerdict::NON_READY);
            EXPECT_EQ(result.durablePhase, phase);
            EXPECT_TRUE(!result.consumerReady);
            PublishedPackageSnapshotV1 snapshot;
            std::string error;
            EXPECT_TRUE(!restarted.ReadPublishedPackage(
                0, request.manifest.packageName, &snapshot, &error));
            if (phase == DurablePhase::P4_PUBLICATION_PREPARED) {
                EXPECT_EQ(result.publicationState,
                    PublicationState::PREPARED);
            }
            NoFaultInjector noFault;
            PosixPackageFileStager stager(FilesPath(root, suffix));
            PackageTransactionCoordinator coordinator(
                &restarted, &stager, &noFault);
            const PackageLifecycleReceiptV1 retried =
                coordinator.Install(request);
            EXPECT_EQ(retried.verdict, InstallVerdict::COMMITTED);
            EXPECT_EQ(retried.generation, std::optional<uint64_t>(1));
            RestartRecoveryRequestV1 afterRetry =
                RecoveryRequest(request, suffix + "-retry");
            afterRetry.expectedCanonicalDigest =
                retried.durableRecordDigest;
            afterRetry.expectedPhase =
                DurablePhase::P6_RECEIPT_CLOSED;
            const RestartRecoveryReceiptV1 closed =
                restarted.RecoverAfterRestart(afterRetry);
            Record(closed);
            EXPECT_EQ(closed.verdict,
                RestartRecoveryVerdict::RESTORED_COMMITTED);
            EXPECT_EQ(closed.generation, std::optional<uint64_t>(1));
        }
    }
}

void TestCorruptionAndMissingFile(const std::string& root)
{
    {
        const std::string lane = "n01-corrupt";
        InstallRequestV1 request =
            MakeRequest("org.a11.corrupt", "tx-a11-corrupt", "corrupt-apk");
        {
            NoFaultInjector noFault;
            FilePackageStore store(StorePath(root, lane));
            PosixPackageFileStager stager(FilesPath(root, lane));
            PackageTransactionCoordinator coordinator(
                &store, &stager, &noFault);
            EXPECT_EQ(coordinator.Install(request).verdict,
                InstallVerdict::COMMITTED);
        }
        std::ofstream eventLog(
            StorePath(root, lane) + "/events.v1.log",
            std::ios::binary | std::ios::app);
        eventLog << "truncated";
        eventLog.close();
        FilePackageStore restarted(StorePath(root, lane));
        const RestartRecoveryReceiptV1 result =
            restarted.RecoverAfterRestart(RecoveryRequest(request, lane));
        Record(result);
        EXPECT_EQ(result.verdict,
            RestartRecoveryVerdict::DATA_INCONSISTENT);
        EXPECT_EQ(result.terminalState, std::string("QUARANTINED"));
    }
    {
        const std::string lane = "n01-missing-file";
        InstallRequestV1 request =
            MakeRequest("org.a11.missing", "tx-a11-missing", "missing-apk");
        std::string managedPath;
        {
            NoFaultInjector noFault;
            FilePackageStore store(StorePath(root, lane));
            PosixPackageFileStager stager(FilesPath(root, lane));
            PackageTransactionCoordinator coordinator(
                &store, &stager, &noFault);
            EXPECT_EQ(coordinator.Install(request).verdict,
                InstallVerdict::COMMITTED);
            PublishedPackageSnapshotV1 snapshot;
            std::string error;
            EXPECT_TRUE(store.ReadPublishedPackage(
                0, request.manifest.packageName, &snapshot, &error));
            managedPath = snapshot.managedFiles.baseCodePath;
        }
        EXPECT_EQ(unlink(managedPath.c_str()), 0);
        FilePackageStore restarted(StorePath(root, lane));
        const RestartRecoveryReceiptV1 result =
            restarted.RecoverAfterRestart(RecoveryRequest(request, lane));
        Record(result);
        EXPECT_EQ(result.verdict,
            RestartRecoveryVerdict::DATA_INCONSISTENT);
        EXPECT_EQ(result.terminalState, std::string("QUARANTINED"));
        PublishedPackageSnapshotV1 snapshot;
        std::string error;
        EXPECT_TRUE(!restarted.ReadPublishedPackage(
            0, request.manifest.packageName, &snapshot, &error));
        PackageLifecycleReceiptV1 receipt;
        EXPECT_TRUE(!restarted.ReadReceipt(
            request.admission.transactionId, &receipt, &error));
    }
    {
        const std::string lane = "f02-p5-live-corruption";
        InstallRequestV1 request = MakeRequest(
            "org.a11.livecorrupt", "tx-a11-livecorrupt", "live-corrupt-apk");
        ProcessCrashFault fault(DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED);
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        PackageTransactionCoordinator coordinator(&store, &stager, &fault);
        EXPECT_EQ(coordinator.Install(request).verdict,
            InstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
        PublishedPackageSnapshotV1 snapshot;
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, request.manifest.packageName, &snapshot, &error));
        EXPECT_EQ(unlink(snapshot.managedFiles.baseCodePath.c_str()), 0);
        NoFaultInjector noFault;
        PackageTransactionCoordinator retry(&store, &stager, &noFault);
        EXPECT_EQ(retry.Install(request).verdict,
            InstallVerdict::DATA_INCONSISTENT);
        EXPECT_TRUE(!store.ReadPublishedPackage(
            0, request.manifest.packageName, &snapshot, &error));
    }
}

void TestIdentityMismatch(const std::string& root)
{
    const std::string lane = "n02-identity";
    InstallRequestV1 request =
        MakeRequest("org.a11.identity", "tx-a11-identity", "identity-apk");
    PackageLifecycleReceiptV1 committed;
    {
        NoFaultInjector noFault;
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        PackageTransactionCoordinator coordinator(&store, &stager, &noFault);
        committed = coordinator.Install(request);
        EXPECT_EQ(committed.verdict, InstallVerdict::COMMITTED);
    }
    FilePackageStore restarted(StorePath(root, lane));
    RestartRecoveryRequestV1 wrongDigest = RecoveryRequest(request, lane);
    wrongDigest.expectedRequestDigest = Sha256Hex("wrong-request");
    RestartRecoveryReceiptV1 result =
        restarted.RecoverAfterRestart(wrongDigest);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::IDENTITY_MISMATCH);

    RestartRecoveryRequestV1 wrongGeneration =
        RecoveryRequest(request, lane + "-generation");
    wrongGeneration.expectedGeneration = 2;
    result = restarted.RecoverAfterRestart(wrongGeneration);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::IDENTITY_MISMATCH);

    RestartRecoveryRequestV1 wrongCanonical =
        RecoveryRequest(request, lane + "-canonical");
    wrongCanonical.expectedCanonicalDigest = Sha256Hex("wrong-canonical");
    result = restarted.RecoverAfterRestart(wrongCanonical);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::IDENTITY_MISMATCH);

    RestartRecoveryRequestV1 wrongPhase =
        RecoveryRequest(request, lane + "-phase");
    wrongPhase.expectedPhase = DurablePhase::P4_PUBLICATION_PREPARED;
    result = restarted.RecoverAfterRestart(wrongPhase);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::IDENTITY_MISMATCH);

    RestartRecoveryRequestV1 noRestart =
        RecoveryRequest(request, lane + "-boundary");
    noRestart.boundary.afterBootId = noRestart.boundary.beforeBootId;
    noRestart.boundary.afterServiceId =
        noRestart.boundary.beforeServiceId;
    result = restarted.RecoverAfterRestart(noRestart);
    Record(result);
    EXPECT_EQ(result.verdict,
        RestartRecoveryVerdict::IDENTITY_MISMATCH);

    RestartRecoveryRequestV1 unknown =
        RecoveryRequest(request, lane + "-transaction");
    unknown.transactionId = "tx-a11-unknown";
    result = restarted.RecoverAfterRestart(unknown);
    Record(result);
    EXPECT_EQ(result.verdict, RestartRecoveryVerdict::ABSENT);

    PublishedPackageSnapshotV1 snapshot;
    std::string error;
    EXPECT_TRUE(restarted.ReadPublishedPackage(
        0, request.manifest.packageName, &snapshot, &error));
    EXPECT_EQ(snapshot.generation, committed.generation.value_or(0));
    EXPECT_EQ(snapshot.canonicalDigest,
        committed.durableRecordDigest.value_or(""));
}

}  // namespace

int main(int argc, char** argv)
{
    gProgramPath = argv[0];
    if (argc == 3 && std::string(argv[1]) == "--expect-lock-held") {
        FilePackageStore contender(argv[2]);
        std::string error;
        return !contender.Open(&error) &&
            error.find("writer lease") != std::string::npos ? 0 : 1;
    }
    if (argc != 2 || argv[1] == nullptr || argv[1][0] != '/') {
        std::cerr << "usage: package_restart_recovery_host_test "
                     "ABSOLUTE_OUTPUT_ROOT\n";
        return 2;
    }
    const std::string root = argv[1];
    gResults.open(root + "/results.jsonl",
        std::ios::binary | std::ios::trunc);
    if (!gResults.good()) {
        std::cerr << "FAIL unable to open results.jsonl\n";
        return 2;
    }
    TestExclusiveWriterLease(root);
    TestInvalidEnvelopeIsolation(root);
    TestClosedInstallRecovery(root);
    TestPhaseMatrix(root);
    TestCorruptionAndMissingFile(root);
    TestIdentityMismatch(root);
    if (gFailures != 0) {
        std::cerr << "FAIL fn01_a11_restart_recovery failures="
                  << gFailures << "\n";
        return 1;
    }
    std::cout << "DEVELOPER_TEST_READY_FOR_HANDOFF action=Fn01.A11"
              << " positive=2 negative=2 failure=2 restart_phases=8"
              << " formal_verdict=NOT_ISSUED device_verified=false\n";
    return 0;
}
