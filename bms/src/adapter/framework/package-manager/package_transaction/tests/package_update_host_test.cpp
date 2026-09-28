#include "package_query_v1.h"
#include "package_transaction_v1.h"

#include "sha256.h"

#include <cerrno>
#include <fstream>
#include <functional>
#include <iostream>
#include <optional>
#include <string>
#include <string_view>
#include <unistd.h>
#include <vector>

using namespace oh_adapter::package_query;
using namespace oh_adapter::package_transaction;

namespace {

int gFailures = 0;
std::ofstream gResults;

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

std::string StorePath(const std::string& root, const std::string& lane)
{
    return root + "/" + lane + "/store";
}

std::string FilesPath(const std::string& root, const std::string& lane)
{
    return root + "/" + lane + "/files";
}

InstallRequestV1 MakeInstall(const std::string& packageName,
    const std::string& transactionId, std::string_view bytes,
    uint64_t versionCode = 10)
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
    request.manifest.parserVersion = "a14-host-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = versionCode;
    request.manifest.versionName = std::to_string(versionCode);
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;
    request.manifest.applicationClassName = packageName + ".Application";
    request.manifest.applicationLabel = "host-fixture";
    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "a13-host-verifier-v1";
    request.signing.policyProfile = "update-policy";
    request.signing.verified = true;
    request.signing.schemeVersions = {2, 3};
    request.signing.signerCertificateDigests = {
        Sha256Hex("signer:" + packageName),
    };
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.policyRef = "update-policy";
    request.retryIdentity = "retry:" + transactionId;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest =
        Sha256Hex("caller:primary");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest =
        ComputeInstallRequestDigest(request);
    return request;
}

UpdateRequestV1 MakeUpdate(const PublishedPackageSnapshotV1& oldSnapshot,
    const std::string& transactionId, std::string_view bytes,
    uint64_t versionCode = 20)
{
    UpdateRequestV1 request;
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
    request.manifest.parserVersion = "a14-host-parser-v1";
    request.manifest.packageName = oldSnapshot.packageName;
    request.manifest.versionCode = versionCode;
    request.manifest.versionName = std::to_string(versionCode);
    request.manifest.minSdk = 26;
    request.manifest.targetSdk = 35;
    request.manifest.applicationClassName =
        oldSnapshot.packageName + ".Application";
    request.manifest.applicationLabel = "updated-host-fixture";
    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "a13-host-verifier-v1";
    request.signing.policyProfile = "update-policy";
    request.signing.verified = true;
    request.signing.schemeVersions = {2, 3};
    request.signing.signerCertificateDigests =
        oldSnapshot.signingFacts->signerCertificateDigests;
    request.signing.lineageDigest =
        oldSnapshot.signingFacts->lineageDigest;
    request.userId = oldSnapshot.userId;
    request.expectedPackageName = oldSnapshot.packageName;
    request.expectedGeneration = oldSnapshot.generation;
    request.policyRef = "update-policy";
    request.retryIdentity = "retry:" + transactionId;
    request.policySnapshot.schemaVersion = 1;
    request.policySnapshot.policyId = request.policyRef;
    request.policySnapshot.policyVersion = "policy-version-2026.07";
    request.policySnapshot.rulesDigest =
        Sha256Hex("policy-rules:2026.07");
    request.policySnapshot.ruleId = "ALLOW_SIGNER_CONTINUITY";
    request.policySnapshot.permitsUpdate = true;
    request.signingContinuity.schemaVersion = 1;
    request.signingContinuity.priorSigningFactsDigest =
        ComputePackageSigningFactsDigest(
            *oldSnapshot.signingFacts);
    request.signingContinuity.signingReceiptDigest =
        Sha256Hex("a13-receipt:" + transactionId);
    request.signingContinuity.capabilityPath = "SAME_SIGNER_SET";
    request.signingContinuity.allowed = true;
    request.signing.sourceReceiptDigest =
        request.signingContinuity.signingReceiptDigest;
    request.signingContinuity.decisionDigest = Sha256Hex(
        "SigningContinuityDecisionV1\n" +
        request.signingContinuity.signingReceiptDigest + "\n" +
        request.signingContinuity.priorSigningFactsDigest +
        "\nALLOWED\n" +
        request.signingContinuity.capabilityPath);
    request.admission.schemaVersion = 1;
    request.admission.jobId = "job:" + transactionId;
    request.admission.memberId = "member:" + transactionId;
    request.admission.operation = "UPDATE";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest =
        Sha256Hex("caller:primary");
    request.admission.policySnapshotId = request.policyRef;
    request.admission.requestDigest =
        ComputeUpdateRequestDigest(request);
    return request;
}

PublishedPackageSnapshotV1 InstallActive(
    FilePackageStore* store, PackageFileStager* stager,
    const std::string& packageName, const std::string& transactionId,
    std::string_view bytes, uint64_t versionCode = 10)
{
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(store, stager, &noFault);
    const auto install = MakeInstall(
        packageName, transactionId, bytes, versionCode);
    const auto receipt = coordinator.Install(install);
    EXPECT_EQ(receipt.verdict, InstallVerdict::COMMITTED);
    PublishedPackageSnapshotV1 snapshot;
    std::string error;
    EXPECT_TRUE(store->ReadPublishedPackage(
        0, packageName, &snapshot, &error));
    EXPECT_TRUE(store->SeedHostProjectionForFixture(
        0, packageName, snapshot.generation, snapshot.canonicalDigest,
        HostProjectionState::ACTIVE,
        PublicationState::EXTERNAL_READY, &error));
    return snapshot;
}

GetPackageResponseV1 Query(FilePackageStore* store,
    const std::string& packageName)
{
    NoQueryFaultInjector noFault;
    PackageQueryService service(store, &noFault);
    GetPackageRequestV1 request;
    request.requestId = "query:" + packageName;
    request.packageName = packageName;
    request.userId = 0;
    request.caller.callerId = "a14-host-verifier";
    request.caller.visibilityScopeDigest =
        Sha256Hex("scope:" + packageName);
    request.caller.canSeeAllPackages = true;
    return service.GetPackage(request);
}

void Record(const UpdateReceiptV1& receipt)
{
    gResults << SerializeUpdateReceipt(receipt) << "\n";
    gResults.flush();
}

void Record(const GenerationRetirementPlanV1& plan)
{
    gResults << SerializeRetirementPlan(plan) << "\n";
    gResults.flush();
}

class OneShotFault final : public FaultInjector {
public:
    explicit OneShotFault(DurablePhase phase) : phase_(phase) {}

    bool InterruptAfter(DurablePhase phase) override
    {
        if (!fired_ && phase == phase_) {
            fired_ = true;
            return true;
        }
        return false;
    }

private:
    DurablePhase phase_;
    bool fired_ = false;
};

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

class FailOldCleanupOnceStager final : public PackageFileStager {
public:
    explicit FailOldCleanupOnceStager(std::string root)
        : delegate_(std::move(root))
    {
    }

    bool Stage(const std::string& packageName, uint32_t userId,
        uint64_t generation, const ArtifactDescriptorV1& artifact,
        ManagedFilesV1* managedFiles, std::string* error) override
    {
        return delegate_.Stage(packageName, userId, generation,
            artifact, managedFiles, error);
    }

    bool Cleanup(const ManagedFilesV1& managedFiles,
        std::string* error) override
    {
        if (failOnce_) {
            failOnce_ = false;
            if (error != nullptr) *error = "injected cleanup failure";
            return false;
        }
        return delegate_.Cleanup(managedFiles, error);
    }

private:
    PosixPackageFileStager delegate_;
    bool failOnce_ = true;
};

void TestSuccessReplayRestartAndSharedData(const std::string& root)
{
    const std::string lane = "p01-success-replay";
    const std::string packageName = "org.example.dynamic.alpha";
    const std::string sharedData =
        root + "/shared-data-" + lane + ".txt";
    {
        std::ofstream output(sharedData);
        output << "preserve-me";
    }
    std::string oldCodePath;
    UpdateRequestV1 update;
    UpdateReceiptV1 closed;
    uint64_t revisionAfterClose = 0;
    {
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        const auto old = InstallActive(&store, &stager, packageName,
            "tx-install-alpha", "old-alpha");
        oldCodePath = old.managedFiles.baseCodePath;
        EXPECT_EQ(Query(&store, packageName).verdict,
            PackageQueryVerdict::READY);
        update = MakeUpdate(old, "tx-update-alpha", "new-alpha");
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        closed = coordinator.Update(update);
        Record(closed);
        EXPECT_EQ(closed.verdict, UpdateVerdict::UPDATED);
        EXPECT_EQ(closed.oldGeneration,
            std::optional<uint64_t>(1));
        EXPECT_EQ(closed.newGeneration,
            std::optional<uint64_t>(2));
        PublishedPackageSnapshotV1 current;
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, packageName, &current, &error));
        EXPECT_EQ(current.generation, static_cast<uint64_t>(2));
        EXPECT_TRUE(current.managedFiles.baseCodePath != oldCodePath);
        EXPECT_TRUE(access(oldCodePath.c_str(), F_OK) != 0 &&
            errno == ENOENT);
        EXPECT_TRUE(access(
            current.managedFiles.baseCodePath.c_str(), F_OK) == 0);
        EXPECT_EQ(Query(&store, packageName).verdict,
            PackageQueryVerdict::PACKAGE_NOT_READY);
        GenerationRetirementPlanV1 plan;
        EXPECT_TRUE(store.ReadRetirementPlan(
            update.admission.transactionId, &plan, &error));
        Record(plan);
        EXPECT_EQ(plan.state, RetirementPlanState::CLOSED);
        EXPECT_TRUE(plan.sharedDataPreserved);
        EXPECT_EQ(plan.oldProjectionState,
            HostProjectionState::NONE);
        EXPECT_EQ(plan.obligations.size(), static_cast<size_t>(3));
        for (const auto& obligation : plan.obligations) {
            EXPECT_EQ(obligation.state,
                RetirementObligationState::CLOSED);
        }
        PackageManagementReadV1 management;
        EXPECT_TRUE(store.ReadPackageManagementState(
            0, packageName, &management, &error));
        revisionAfterClose = management.catalogRevision;
        const UpdateReceiptV1 replay = coordinator.Update(update);
        Record(replay);
        EXPECT_EQ(replay.verdict, UpdateVerdict::UPDATED);
        EXPECT_EQ(replay.canonicalDigest, closed.canonicalDigest);
        EXPECT_EQ(replay.retirementPlanDigest,
            closed.retirementPlanDigest);
        EXPECT_TRUE(store.ReadPackageManagementState(
            0, packageName, &management, &error));
        EXPECT_EQ(management.catalogRevision, revisionAfterClose);
    }
    {
        FilePackageStore reopened(StorePath(root, lane));
        std::string error;
        EXPECT_TRUE(reopened.Open(&error));
        UpdateReceiptV1 recovered;
        EXPECT_TRUE(reopened.ReadUpdateReceipt(
            update.admission.transactionId, &recovered, &error));
        Record(recovered);
        EXPECT_EQ(recovered.verdict, UpdateVerdict::UPDATED);
        PublishedPackageSnapshotV1 current;
        EXPECT_TRUE(reopened.ReadPublishedPackage(
            0, packageName, &current, &error));
        EXPECT_EQ(current.generation, static_cast<uint64_t>(2));
        GenerationRetirementPlanV1 plan;
        EXPECT_TRUE(reopened.ReadRetirementPlan(
            update.admission.transactionId, &plan, &error));
        EXPECT_EQ(plan.state, RetirementPlanState::CLOSED);
    }
    std::ifstream shared(sharedData);
    std::string value;
    shared >> value;
    EXPECT_EQ(value, std::string("preserve-me"));
}

void TestPolicyOwnsVersionDecision(const std::string& root)
{
    const std::string lane = "p02-policy-version";
    FilePackageStore store(StorePath(root, lane));
    PosixPackageFileStager stager(FilesPath(root, lane));
    const auto old = InstallActive(&store, &stager,
        "net.sample.version.policy", "tx-install-policy",
        "old-policy", 50);
    UpdateRequestV1 update = MakeUpdate(
        old, "tx-update-policy", "new-policy", 3);
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &stager, &noFault);
    const UpdateReceiptV1 receipt = coordinator.Update(update);
    Record(receipt);
    EXPECT_EQ(receipt.verdict, UpdateVerdict::UPDATED);
    PublishedPackageSnapshotV1 current;
    std::string error;
    EXPECT_TRUE(store.ReadPublishedPackage(
        0, old.packageName, &current, &error));
    EXPECT_TRUE(current.manifestFacts.has_value());
    EXPECT_EQ(current.manifestFacts->versionCode,
        static_cast<uint64_t>(3));
    EXPECT_EQ(receipt.policyRuleId,
        std::string("ALLOW_SIGNER_CONTINUITY"));
    EXPECT_EQ(receipt.policyVersion,
        std::string("policy-version-2026.07"));
}

UpdateReceiptV1 RunNegative(const std::string& root,
    const std::string& lane,
    const std::function<void(UpdateRequestV1&)>& mutate,
    bool install = true)
{
    FilePackageStore store(StorePath(root, lane));
    PosixPackageFileStager stager(FilesPath(root, lane));
    PublishedPackageSnapshotV1 old;
    if (install) {
        old = InstallActive(&store, &stager,
            "org.negative." + lane, "tx-install-" + lane,
            "old-" + lane);
    } else {
        old.packageName = "org.negative." + lane;
        old.userId = 0;
        old.generation = 1;
        SigningFactsV1 signing;
        signing.signerCertificateDigests = {
            Sha256Hex("signer:" + old.packageName),
        };
        old.signingFacts = signing;
    }
    UpdateRequestV1 update = MakeUpdate(
        old, "tx-update-" + lane, "new-" + lane);
    mutate(update);
    update.admission.requestDigest =
        ComputeUpdateRequestDigest(update);
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &stager, &noFault);
    const UpdateReceiptV1 receipt = coordinator.Update(update);
    Record(receipt);
    if (install) {
        PublishedPackageSnapshotV1 current;
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, old.packageName, &current, &error));
        EXPECT_EQ(current.generation, old.generation);
        EXPECT_EQ(current.canonicalDigest, old.canonicalDigest);
    }
    return receipt;
}

void TestTypedNegativeMatrix(const std::string& root)
{
    EXPECT_EQ(RunNegative(root, "identity",
        [](UpdateRequestV1& request) {
            request.expectedPackageName = "caller.injected.package";
        }).verdict, UpdateVerdict::IDENTITY_MISMATCH);
    EXPECT_EQ(RunNegative(root, "generation",
        [](UpdateRequestV1& request) {
            request.expectedGeneration = 99;
        }).verdict, UpdateVerdict::GENERATION_MISMATCH);
    EXPECT_EQ(RunNegative(root, "signer-denied",
        [](UpdateRequestV1& request) {
            request.signingContinuity.allowed = false;
        }).verdict, UpdateVerdict::SIGNING_REJECTED);
    EXPECT_EQ(RunNegative(root, "signer-prior",
        [](UpdateRequestV1& request) {
            request.signingContinuity.priorSigningFactsDigest =
                Sha256Hex("wrong-prior");
        }).verdict, UpdateVerdict::SIGNING_REJECTED);
    EXPECT_EQ(RunNegative(root, "signer-decision-splice",
        [](UpdateRequestV1& request) {
            request.signingContinuity.capabilityPath =
                "CURRENT_LINEAGE_INSTALLED_DATA";
        }).verdict, UpdateVerdict::SIGNING_REJECTED);
    EXPECT_EQ(RunNegative(root, "signer-receipt-splice",
        [](UpdateRequestV1& request) {
            request.signing.sourceReceiptDigest =
                Sha256Hex("foreign-a13-receipt");
        }).verdict, UpdateVerdict::SIGNING_REJECTED);
    const auto denied = RunNegative(root, "policy-denied",
        [](UpdateRequestV1& request) {
            request.policySnapshot.permitsUpdate = false;
            request.policySnapshot.ruleId = "DENY_VERSION_POLICY";
            request.policySnapshot.policyVersion = "policy-deny-v9";
        });
    EXPECT_EQ(denied.verdict, UpdateVerdict::POLICY_REJECTED);
    EXPECT_EQ(denied.policyRuleId,
        std::string("DENY_VERSION_POLICY"));
    EXPECT_EQ(denied.policyVersion,
        std::string("policy-deny-v9"));
    EXPECT_EQ(RunNegative(root, "policy-id",
        [](UpdateRequestV1& request) {
            request.policySnapshot.policyId = "foreign-policy";
        }).verdict, UpdateVerdict::POLICY_REJECTED);
    EXPECT_EQ(RunNegative(root, "artifact",
        [](UpdateRequestV1& request) {
            request.artifactSet.artifacts.front().bytes.push_back('!');
        }).verdict, UpdateVerdict::ARTIFACT_DIGEST_MISMATCH);
    EXPECT_EQ(RunNegative(root, "secondary",
        [](UpdateRequestV1& request) {
            request.userId = 10;
        }).verdict, UpdateVerdict::NOT_SUPPORTED);
    EXPECT_EQ(RunNegative(root, "absent",
        [](UpdateRequestV1&) {}, false).verdict,
        UpdateVerdict::PACKAGE_NOT_FOUND);

    {
        const std::string lane = "removing";
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        const auto old = InstallActive(&store, &stager,
            "org.negative.removing", "tx-install-removing",
            "old-removing");
        std::string error;
        EXPECT_TRUE(store.SeedRemovalTombstoneForFixture(
            0, old.packageName, old.generation, &error));
        auto update = MakeUpdate(
            old, "tx-update-removing", "new-removing");
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        const auto receipt = coordinator.Update(update);
        Record(receipt);
        EXPECT_EQ(receipt.verdict,
            UpdateVerdict::PACKAGE_REMOVING);
    }

    {
        const std::string lane = "idempotency";
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        const auto old = InstallActive(&store, &stager,
            "org.negative.idempotency", "tx-install-idempotency",
            "old-idempotency");
        auto update = MakeUpdate(
            old, "tx-update-idempotency", "new-idempotency");
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        EXPECT_EQ(coordinator.Update(update).verdict,
            UpdateVerdict::UPDATED);
        update.expectedGeneration = 99;
        update.admission.requestDigest =
            ComputeUpdateRequestDigest(update);
        const auto conflict = coordinator.Update(update);
        Record(conflict);
        EXPECT_EQ(conflict.verdict,
            UpdateVerdict::IDEMPOTENCY_CONFLICT);
    }
}

void TestPreP5FaultMatrix(const std::string& root)
{
    const std::vector<DurablePhase> phases = {
        DurablePhase::P0_INPUT_FROZEN,
        DurablePhase::P1_PLAN_DURABLE,
        DurablePhase::P2_FILES_PREPARED,
        DurablePhase::P3_CANONICAL_PREPARED,
        DurablePhase::P4_PUBLICATION_PREPARED,
    };
    for (size_t index = 0; index < phases.size(); ++index) {
        const std::string lane =
            "f01-phase-" + std::to_string(index);
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        const auto old = InstallActive(&store, &stager,
            "org.failure.phase" + std::to_string(index),
            "tx-install-phase-" + std::to_string(index),
            "old-phase-" + std::to_string(index));
        const auto update = MakeUpdate(old,
            "tx-update-phase-" + std::to_string(index),
            "new-phase-" + std::to_string(index));
        OneShotFault fault(phases[index]);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &fault);
        UpdateReceiptV1 receipt = coordinator.Update(update);
        if (phases[index] ==
            DurablePhase::P0_INPUT_FROZEN) {
            EXPECT_EQ(receipt.verdict,
                UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
            NoFaultInjector noFault;
            PackageTransactionCoordinator recovery(
                &store, &stager, &noFault);
            receipt = recovery.Update(update);
        }
        Record(receipt);
        EXPECT_EQ(receipt.terminalState,
            std::string("CLOSED_ROLLED_BACK"));
        PublishedPackageSnapshotV1 current;
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, old.packageName, &current, &error));
        EXPECT_EQ(current.generation, old.generation);
        EXPECT_EQ(current.canonicalDigest, old.canonicalDigest);
        EXPECT_TRUE(access(
            old.managedFiles.baseCodePath.c_str(), F_OK) == 0);
        EXPECT_EQ(Query(&store, old.packageName).verdict,
            PackageQueryVerdict::READY);
    }
}

void TestPreP5CrashRestartRollback(const std::string& root)
{
    const std::string lane = "f02-pre-p5-crash";
    UpdateRequestV1 update;
    PublishedPackageSnapshotV1 old;
    {
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        old = InstallActive(&store, &stager,
            "org.failure.precrash", "tx-install-precrash",
            "old-precrash");
        update = MakeUpdate(
            old, "tx-update-precrash", "new-precrash");
        ProcessCrashFault fault(
            DurablePhase::P2_FILES_PREPARED);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &fault);
        const auto interrupted = coordinator.Update(update);
        Record(interrupted);
        EXPECT_EQ(interrupted.verdict,
            UpdateVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
    }
    {
        FilePackageStore reopened(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &reopened, &stager, &noFault);
        const auto rolledBack = coordinator.Update(update);
        Record(rolledBack);
        EXPECT_EQ(rolledBack.terminalState,
            std::string("CLOSED_ROLLED_BACK"));
        PublishedPackageSnapshotV1 current;
        std::string error;
        EXPECT_TRUE(reopened.ReadPublishedPackage(
            0, old.packageName, &current, &error));
        EXPECT_EQ(current.generation, old.generation);
        EXPECT_EQ(current.canonicalDigest, old.canonicalDigest);
    }
}

void TestPostP5CrashForwardOnly(const std::string& root)
{
    const std::string lane = "f03-post-p5-crash";
    UpdateRequestV1 update;
    PublishedPackageSnapshotV1 old;
    {
        FilePackageStore store(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        old = InstallActive(&store, &stager,
            "org.failure.postcrash", "tx-install-postcrash",
            "old-postcrash");
        update = MakeUpdate(
            old, "tx-update-postcrash", "new-postcrash");
        ProcessCrashFault fault(
            DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &fault);
        const auto interrupted = coordinator.Update(update);
        Record(interrupted);
        EXPECT_EQ(interrupted.terminalState,
            std::string("RECOVERING_FORWARD"));
        PublishedPackageSnapshotV1 current;
        std::string error;
        EXPECT_TRUE(store.ReadPublishedPackage(
            0, old.packageName, &current, &error));
        EXPECT_EQ(current.generation, static_cast<uint64_t>(2));
        const auto query = Query(&store, old.packageName);
        EXPECT_EQ(query.verdict,
            PackageQueryVerdict::PACKAGE_NOT_READY);
        EXPECT_TRUE(!query.package.has_value());
    }
    {
        FilePackageStore reopened(StorePath(root, lane));
        PosixPackageFileStager stager(FilesPath(root, lane));
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &reopened, &stager, &noFault);
        const auto recovered = coordinator.Update(update);
        Record(recovered);
        EXPECT_EQ(recovered.verdict, UpdateVerdict::UPDATED);
        GenerationRetirementPlanV1 plan;
        std::string error;
        EXPECT_TRUE(reopened.ReadRetirementPlan(
            update.admission.transactionId, &plan, &error));
        Record(plan);
        EXPECT_EQ(plan.state, RetirementPlanState::CLOSED);
        EXPECT_TRUE(access(
            old.managedFiles.baseCodePath.c_str(), F_OK) != 0 &&
            errno == ENOENT);
    }
}

void TestRetirementRetryAfterCleanupFailure(const std::string& root)
{
    const std::string lane = "f04-retirement-retry";
    FilePackageStore store(StorePath(root, lane));
    PosixPackageFileStager installStager(FilesPath(root, lane));
    const auto old = InstallActive(&store, &installStager,
        "org.failure.cleanup", "tx-install-cleanup",
        "old-cleanup");
    const auto update = MakeUpdate(
        old, "tx-update-cleanup", "new-cleanup");
    FailOldCleanupOnceStager failingStager(FilesPath(root, lane));
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &failingStager, &noFault);
    const auto pending = coordinator.Update(update);
    Record(pending);
    EXPECT_EQ(pending.terminalState,
        std::string("RECOVERING_FORWARD"));
    PublishedPackageSnapshotV1 current;
    std::string error;
    EXPECT_TRUE(store.ReadPublishedPackage(
        0, old.packageName, &current, &error));
    EXPECT_EQ(current.generation, static_cast<uint64_t>(2));
    EXPECT_TRUE(access(
        old.managedFiles.baseCodePath.c_str(), F_OK) == 0);
    const auto recovered = coordinator.Update(update);
    Record(recovered);
    EXPECT_EQ(recovered.verdict, UpdateVerdict::UPDATED);
    EXPECT_TRUE(access(
        old.managedFiles.baseCodePath.c_str(), F_OK) != 0 &&
        errno == ENOENT);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 || argv[1] == nullptr || argv[1][0] != '/') {
        std::cerr << "usage: package_update_host_test ABSOLUTE_TEMP_ROOT\n";
        return 2;
    }
    const std::string root = argv[1];
    gResults.open(root + "/results.jsonl",
        std::ios::out | std::ios::trunc);
    if (!gResults) {
        std::cerr << "unable to open results.jsonl\n";
        return 2;
    }
    TestSuccessReplayRestartAndSharedData(root);
    TestPolicyOwnsVersionDecision(root);
    TestTypedNegativeMatrix(root);
    TestPreP5FaultMatrix(root);
    TestPreP5CrashRestartRollback(root);
    TestPostP5CrashForwardOnly(root);
    TestRetirementRetryAfterCleanupFailure(root);
    if (gFailures != 0) {
        std::cerr << "FAIL fn01_a14_update failures=" << gFailures
                  << "\n";
        return 1;
    }
    std::cout << "PASS fn01_a14_update positive=4 negative=13"
              << " failure=8 restart=3 policy_externalized=1"
              << " product_hardcoding=none runtime_pass=false\n";
    return 0;
}
