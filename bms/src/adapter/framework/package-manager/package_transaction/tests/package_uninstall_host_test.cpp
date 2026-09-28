#include "package_transaction_v1.h"

#include <chrono>
#include <condition_variable>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

using namespace oh_adapter::package_transaction;

namespace {

int gFailures = 0;
int gCases = 0;
std::ofstream gResults;

#define CHECK_CASE(name, condition)                                           \
    do {                                                                      \
        ++gCases;                                                             \
        const bool passed = static_cast<bool>(condition);                     \
        gResults << "{\"case\":\"" << name << "\",\"passed\":"         \
                 << (passed ? "true" : "false") << "}\n";                  \
        if (!passed) {                                                        \
            ++gFailures;                                                      \
            std::cerr << "FAIL " << name << " line=" << __LINE__ << "\n"; \
        }                                                                     \
    } while (0)

std::string Repeat(char value)
{
    return std::string(64, value);
}

std::string TestSha256(const std::vector<uint8_t>& bytes);

InstallRequestV1 MakeInstall(const std::string& packageName,
    const std::string& transactionId, char byte)
{
    InstallRequestV1 request;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "fixture-job-" + transactionId;
    request.admission.memberId = "fixture-member-" + transactionId;
    request.admission.memberIndex = 0;
    request.admission.operation = "INSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Repeat('a');
    request.admission.policySnapshotId = "fixture-policy-v1";
    request.userId = 0;
    request.expectedPackageName = packageName;
    request.expectedGeneration = 0;
    request.policyRef = "fixture-policy-v1";
    request.retryIdentity = "fixture-retry-" + transactionId;

    ArtifactDescriptorV1 artifact;
    artifact.artifactId = "fixture-input";
    artifact.role = ArtifactRole::BASE;
    artifact.bytes = {
        static_cast<uint8_t>(byte),
        static_cast<uint8_t>(byte + 1),
        static_cast<uint8_t>(byte + 2),
    };
    artifact.byteLength = artifact.bytes.size();
    request.artifactSet.artifacts.push_back(artifact);
    request.artifactSet.artifacts.front().sha256 =
        TestSha256(request.artifactSet.artifacts.front().bytes);
    request.artifactSet.artifactSetDigest =
        ComputeArtifactSetDigest(request.artifactSet);
    request.manifest.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.manifest.parserVersion = "fixture-parser-v1";
    request.manifest.packageName = packageName;
    request.manifest.versionCode = 1;
    request.manifest.versionName = "1";
    request.manifest.minSdk = 1;
    request.manifest.targetSdk = 35;
    request.signing.artifactSetDigest =
        request.artifactSet.artifactSetDigest;
    request.signing.verifierVersion = "fixture-verifier-v1";
    request.signing.policyProfile = request.policyRef;
    request.signing.verified = true;
    request.signing.schemeVersions = {3};
    request.signing.signerCertificateDigests = {Repeat('b')};
    request.admission.requestDigest =
        ComputeInstallRequestDigest(request);
    return request;
}

// Small local SHA-256 bridge for fixture bytes. This is test input
// construction, not a product identity shortcut.
extern "C" {
#include "sha256.h"
}

std::string TestSha256(const std::vector<uint8_t>& bytes)
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

UninstallRequestV1 MakeUninstall(const std::string& packageName,
    uint64_t generation, const std::string& transactionId)
{
    UninstallRequestV1 request;
    request.admission.schemaVersion = 1;
    request.admission.jobId = "fixture-job-" + transactionId;
    request.admission.memberId = "fixture-member-" + transactionId;
    request.admission.memberIndex = 0;
    request.admission.operation = "UNINSTALL";
    request.admission.transactionId = transactionId;
    request.admission.jobRecordVersion = 1;
    request.admission.callerScopeDigest = Repeat('c');
    request.admission.policySnapshotId = "fixture-policy-v1";
    request.userId = 0;
    request.packageSelector = packageName;
    request.expectedPackageName = packageName;
    request.expectedGeneration = generation;
    request.policyRef = "fixture-policy-v1";
    request.retryIdentity = "fixture-retry-" + transactionId;
    request.admission.requestDigest =
        ComputeUninstallRequestDigest(request);
    return request;
}

UpdateRequestV1 MakeRemovalGuardUpdate(
    const InstallRequestV1& installed,
    uint64_t generation, const std::string& transactionId)
{
    UpdateRequestV1 request;
    request.admission = installed.admission;
    request.admission.operation = "UPDATE";
    request.admission.transactionId = transactionId;
    request.admission.jobId = "fixture-job-" + transactionId;
    request.admission.memberId = "fixture-member-" + transactionId;
    request.artifactSet = installed.artifactSet;
    request.manifest = installed.manifest;
    request.signing = installed.signing;
    request.userId = 0;
    request.expectedPackageName = installed.manifest.packageName;
    request.expectedGeneration = generation;
    request.policyRef = installed.policyRef;
    request.retryIdentity = "fixture-retry-" + transactionId;
    request.policySnapshot.policyId = request.policyRef;
    request.policySnapshot.policyVersion = "1";
    request.policySnapshot.rulesDigest = Repeat('d');
    request.signingContinuity.decisionDigest = Repeat('e');
    request.signingContinuity.signingReceiptDigest = Repeat('f');
    request.admission.requestDigest = ComputeUpdateRequestDigest(request);
    return request;
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

    bool SimulatesProcessCrash() const override
    {
        return true;
    }

private:
    DurablePhase phase_;
    bool fired_ = false;
};

class FailOnceCleanup final : public PackageFileStager {
public:
    explicit FailOnceCleanup(std::string root)
        : delegate_(std::move(root)) {}

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
        if (!failed_) {
            failed_ = true;
            if (error != nullptr) *error = "fixture cleanup failure";
            return false;
        }
        return delegate_.Cleanup(managedFiles, error);
    }

private:
    PosixPackageFileStager delegate_;
    bool failed_ = false;
};

class BlockingCleanup final : public PackageFileStager {
public:
    explicit BlockingCleanup(std::string root)
        : delegate_(std::move(root)) {}

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
        std::unique_lock<std::mutex> lock(mutex_);
        entered_ = true;
        condition_.notify_all();
        condition_.wait(lock, [&] { return released_; });
        lock.unlock();
        return delegate_.Cleanup(managedFiles, error);
    }

    void WaitEntered()
    {
        std::unique_lock<std::mutex> lock(mutex_);
        condition_.wait(lock, [&] { return entered_; });
    }

    void Release()
    {
        std::lock_guard<std::mutex> lock(mutex_);
        released_ = true;
        condition_.notify_all();
    }

private:
    PosixPackageFileStager delegate_;
    std::mutex mutex_;
    std::condition_variable condition_;
    bool entered_ = false;
    bool released_ = false;
};

PublishedPackageSnapshotV1 InstallPackage(
    FilePackageStore* store, PackageFileStager* stager,
    const InstallRequestV1& request)
{
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(store, stager, &noFault);
    const auto receipt = coordinator.Install(request);
    CHECK_CASE("setup.install_committed",
        receipt.verdict == InstallVerdict::COMMITTED);
    PublishedPackageSnapshotV1 snapshot;
    std::string error;
    CHECK_CASE("setup.install_readback",
        store->ReadPublishedPackage(
            request.userId, request.manifest.packageName,
            &snapshot, &error));
    return snapshot;
}

bool RemoveLastDurableEvent(const std::filesystem::path& eventLog)
{
    std::ifstream input(eventLog);
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(input, line)) {
        lines.push_back(line);
    }
    if (lines.empty()) return false;
    lines.pop_back();
    std::ofstream output(eventLog, std::ios::trunc);
    for (const auto& retained : lines) {
        output << retained << "\n";
    }
    output.flush();
    return output.good();
}

void TestPositiveAndIsolation(const std::filesystem::path& root)
{
    const auto storeRoot = root / "positive-store";
    const auto managedRoot = root / "positive-managed";
    std::filesystem::create_directories(storeRoot);
    FilePackageStore store(storeRoot.string());
    PosixPackageFileStager stager(managedRoot.string());
    std::string error;
    CHECK_CASE("P01.store_open", store.Open(&error));
    const auto first = MakeInstall(
        "fixture.input.alpha", "install-alpha", 'a');
    const auto second = MakeInstall(
        "fixture.input.beta", "install-beta", 'd');
    const auto firstSnapshot =
        InstallPackage(&store, &stager, first);
    const auto secondSnapshot =
        InstallPackage(&store, &stager, second);
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &stager, &noFault);
    auto request = MakeUninstall(first.manifest.packageName,
        firstSnapshot.generation, "remove-alpha");
    const auto removed = coordinator.Uninstall(request);
    CHECK_CASE("P01.removed",
        removed.verdict == UninstallVerdict::REMOVED &&
        removed.terminalState == "CLOSED_REMOVED" &&
        removed.residualObligations.empty());
    PackageManagementReadV1 state;
    CHECK_CASE("P01.absent_readback",
        store.ReadPackageManagementState(0,
            first.manifest.packageName, &state, &error) &&
        !state.removing && !state.canonical.has_value() &&
        !state.publicationToken.has_value() &&
        !state.projection.has_value());
    PublishedPackageSnapshotV1 survivor;
    CHECK_CASE("P01.other_package_untouched",
        store.ReadPublishedPackage(0,
            second.manifest.packageName, &survivor, &error) &&
        survivor.canonicalDigest ==
            secondSnapshot.canonicalDigest);
    const auto replay = coordinator.Uninstall(request);
    CHECK_CASE("P02.closed_replay_same_receipt",
        SerializeUninstallReceipt(replay) ==
            SerializeUninstallReceipt(removed));
    auto crossTransactionRetry = MakeUninstall(
        first.manifest.packageName, firstSnapshot.generation,
        "caller-proposed-new-remove-transaction");
    const auto reused =
        coordinator.Uninstall(crossTransactionRetry);
    CHECK_CASE("P02.matching_retry_reuses_owner_transaction",
        reused.transactionId == removed.transactionId &&
        SerializeUninstallReceipt(reused) ==
            SerializeUninstallReceipt(removed));
    RemovalTombstoneV1 tombstone;
    CHECK_CASE("P02.closed_tombstone",
        store.ReadRemovalTombstone(
            removed.transactionId, &tombstone, &error) &&
        tombstone.state ==
            RemovalTombstoneState::CLOSED_REMOVED);
}

void TestNegatives(const std::filesystem::path& root)
{
    const auto storeRoot = root / "negative-store";
    const auto managedRoot = root / "negative-managed";
    std::filesystem::create_directories(storeRoot);
    FilePackageStore store(storeRoot.string());
    PosixPackageFileStager stager(managedRoot.string());
    std::string error;
    CHECK_CASE("N00.store_open", store.Open(&error));
    const auto install = MakeInstall(
        "fixture.input.negative", "install-negative", 'g');
    const auto snapshot =
        InstallPackage(&store, &stager, install);
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &stager, &noFault);

    auto missing = MakeUninstall(
        "fixture.input.absent", 1, "remove-absent");
    const auto missingResult = coordinator.Uninstall(missing);
    CHECK_CASE("N01.not_found_identity_null",
        missingResult.verdict ==
            UninstallVerdict::PACKAGE_NOT_FOUND &&
        !missingResult.packageName.has_value());

    auto mismatch = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-selector-mismatch");
    mismatch.expectedPackageName = "fixture.constraint.other";
    mismatch.admission.requestDigest =
        ComputeUninstallRequestDigest(mismatch);
    CHECK_CASE("N01.selector_mismatch",
        coordinator.Uninstall(mismatch).verdict ==
            UninstallVerdict::SELECTOR_MISMATCH);

    auto generation = MakeUninstall(
        install.manifest.packageName, snapshot.generation + 1,
        "remove-generation-mismatch");
    CHECK_CASE("N01.generation_mismatch",
        coordinator.Uninstall(generation).verdict ==
            UninstallVerdict::GENERATION_MISMATCH);

    auto unsupported = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-user-mismatch");
    unsupported.userId = 10;
    unsupported.admission.requestDigest =
        ComputeUninstallRequestDigest(unsupported);
    CHECK_CASE("N02.user_not_supported",
        coordinator.Uninstall(unsupported).verdict ==
            UninstallVerdict::NOT_SUPPORTED);

    auto invalid = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-invalid-digest");
    invalid.admission.requestDigest = Repeat('9');
    CHECK_CASE("N02.digest_rejected",
        coordinator.Uninstall(invalid).verdict ==
            UninstallVerdict::INVALID_ENVELOPE);

    auto first = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-idempotency");
    auto p0Fault = OneShotFault(
        DurablePhase::P0_INPUT_FROZEN);
    PackageTransactionCoordinator faulting(
        &store, &stager, &p0Fault);
    CHECK_CASE("N02.idempotency_setup",
        faulting.Uninstall(first).verdict ==
            UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
    auto conflict = first;
    conflict.packageSelector = "fixture.input.changed";
    conflict.admission.requestDigest =
        ComputeUninstallRequestDigest(conflict);
    CHECK_CASE("N02.idempotency_conflict",
        coordinator.Uninstall(conflict).verdict ==
            UninstallVerdict::IDEMPOTENCY_CONFLICT);
}

void TestCallerOwnership(const std::filesystem::path& root)
{
    const auto closedStoreRoot = root / "caller-closed-store";
    const auto closedManagedRoot = root / "caller-closed-managed";
    std::filesystem::create_directories(closedStoreRoot);
    FilePackageStore closedStore(closedStoreRoot.string());
    PosixPackageFileStager closedStager(
        closedManagedRoot.string());
    std::string error;
    CHECK_CASE("N04.closed_store_open",
        closedStore.Open(&error));
    const auto install = MakeInstall(
        "fixture.input.caller.closed",
        "install-caller-closed", 'b');
    const auto snapshot =
        InstallPackage(&closedStore, &closedStager, install);
    NoFaultInjector noFault;
    PackageTransactionCoordinator closedCoordinator(
        &closedStore, &closedStager, &noFault);
    const auto owner = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-caller-owner");
    const auto removed =
        closedCoordinator.Uninstall(owner);
    CHECK_CASE("N04.owner_removed",
        removed.verdict == UninstallVerdict::REMOVED);

    auto sameTransactionStaleDigest = owner;
    sameTransactionStaleDigest.admission.callerScopeDigest =
        Repeat('d');
    const auto staleResult =
        closedCoordinator.Uninstall(
            sameTransactionStaleDigest);
    CHECK_CASE("N04.same_transaction_foreign_stale_digest",
        staleResult.verdict ==
            UninstallVerdict::INVALID_ENVELOPE &&
        !staleResult.packageName.has_value() &&
        !staleResult.generation.has_value() &&
        !staleResult.canonicalDigest.has_value() &&
        !staleResult.tombstoneDigest.has_value());

    auto sameTransactionRecomputed = owner;
    sameTransactionRecomputed.admission.callerScopeDigest =
        Repeat('d');
    sameTransactionRecomputed.admission.requestDigest =
        ComputeUninstallRequestDigest(
            sameTransactionRecomputed);
    const auto conflictResult =
        closedCoordinator.Uninstall(
            sameTransactionRecomputed);
    CHECK_CASE("N04.same_transaction_foreign_conflict_no_leak",
        conflictResult.verdict ==
            UninstallVerdict::IDEMPOTENCY_CONFLICT &&
        !conflictResult.packageName.has_value() &&
        !conflictResult.generation.has_value() &&
        !conflictResult.canonicalDigest.has_value() &&
        !conflictResult.tombstoneDigest.has_value());

    auto newTransactionForeign = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-caller-foreign");
    newTransactionForeign.admission.callerScopeDigest =
        Repeat('d');
    newTransactionForeign.admission.requestDigest =
        ComputeUninstallRequestDigest(newTransactionForeign);
    const auto foreignClosedResult =
        closedCoordinator.Uninstall(
            newTransactionForeign);
    CHECK_CASE("N04.closed_foreign_caller_no_owner_reuse",
        foreignClosedResult.verdict ==
            UninstallVerdict::PACKAGE_NOT_FOUND &&
        foreignClosedResult.transactionId ==
            newTransactionForeign.admission.transactionId &&
        !foreignClosedResult.packageName.has_value() &&
        !foreignClosedResult.generation.has_value() &&
        !foreignClosedResult.canonicalDigest.has_value() &&
        !foreignClosedResult.tombstoneDigest.has_value());

    const auto sameCallerRetry = closedCoordinator.Uninstall(
        MakeUninstall(install.manifest.packageName,
            snapshot.generation,
            "remove-caller-same-scope-retry"));
    CHECK_CASE("N04.closed_same_caller_reuses_owner",
        sameCallerRetry.verdict ==
            UninstallVerdict::REMOVED &&
        sameCallerRetry.transactionId ==
            owner.admission.transactionId);

    const auto openStoreRoot = root / "caller-open-store";
    const auto openManagedRoot = root / "caller-open-managed";
    std::filesystem::create_directories(openStoreRoot);
    FilePackageStore openStore(openStoreRoot.string());
    PosixPackageFileStager openStager(openManagedRoot.string());
    CHECK_CASE("N04.open_store_open",
        openStore.Open(&error));
    const auto openInstall = MakeInstall(
        "fixture.input.caller.open",
        "install-caller-open", 'e');
    const auto openSnapshot =
        InstallPackage(&openStore, &openStager, openInstall);
    OneShotFault p5Fault(
        DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED);
    PackageTransactionCoordinator ownerCoordinator(
        &openStore, &openStager, &p5Fault);
    const auto openOwner = MakeUninstall(
        openInstall.manifest.packageName,
        openSnapshot.generation,
        "remove-caller-open-owner");
    CHECK_CASE("N04.open_owner_published",
        ownerCoordinator.Uninstall(openOwner).verdict ==
            UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE);
    PackageManagementReadV1 beforeForeign;
    CHECK_CASE("N04.open_before_foreign",
        openStore.ReadPackageManagementState(
            0, openInstall.manifest.packageName,
            &beforeForeign, &error) &&
        beforeForeign.removing &&
        beforeForeign.canonical.has_value());

    auto openForeign = MakeUninstall(
        openInstall.manifest.packageName,
        openSnapshot.generation,
        "remove-caller-open-foreign");
    openForeign.admission.callerScopeDigest = Repeat('d');
    openForeign.admission.requestDigest =
        ComputeUninstallRequestDigest(openForeign);
    PackageTransactionCoordinator retryCoordinator(
        &openStore, &openStager, &noFault);
    const auto foreignOpenResult =
        retryCoordinator.Uninstall(openForeign);
    PackageManagementReadV1 afterForeign;
    const bool afterRead =
        openStore.ReadPackageManagementState(
            0, openInstall.manifest.packageName,
            &afterForeign, &error);
    CHECK_CASE("N04.open_foreign_caller_typed_no_leak",
        foreignOpenResult.verdict ==
            UninstallVerdict::PACKAGE_REMOVING &&
        foreignOpenResult.transactionId ==
            openForeign.admission.transactionId &&
        !foreignOpenResult.packageName.has_value() &&
        !foreignOpenResult.generation.has_value() &&
        !foreignOpenResult.canonicalDigest.has_value() &&
        !foreignOpenResult.tombstoneDigest.has_value());
    CHECK_CASE("N04.open_foreign_zero_canonical_mutation",
        afterRead && afterForeign.removing &&
        afterForeign.catalogRevision ==
            beforeForeign.catalogRevision &&
        afterForeign.canonical.has_value() &&
        afterForeign.canonical->canonicalDigest ==
            beforeForeign.canonical->canonicalDigest);
    const auto openSameCaller = retryCoordinator.Uninstall(
        MakeUninstall(openInstall.manifest.packageName,
            openSnapshot.generation,
            "remove-caller-open-same-scope"));
    CHECK_CASE("N04.open_same_caller_reuses_owner",
        openSameCaller.verdict ==
            UninstallVerdict::REMOVED &&
        openSameCaller.transactionId ==
            openOwner.admission.transactionId);
}

void TestPrePublicationRecovery(const std::filesystem::path& root)
{
    const auto storeRoot = root / "pre-p5-store";
    const auto managedRoot = root / "pre-p5-managed";
    std::filesystem::create_directories(storeRoot);
    const auto install = MakeInstall(
        "fixture.input.prepublication",
        "install-prepublication", 'v');
    const auto requestId = std::string("remove-prepublication");
    uint64_t generation = 0;
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F00.pre_p5_open", store.Open(&error));
        const auto snapshot =
            InstallPackage(&store, &stager, install);
        generation = snapshot.generation;
        OneShotFault fault(DurablePhase::P1_PLAN_DURABLE);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &fault);
        const auto interrupted = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation, requestId));
        CHECK_CASE("F01.pre_p5_interrupted",
            interrupted.verdict ==
                UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE &&
            interrupted.terminalState == "OPEN_NON_READY");
        PackageManagementReadV1 state;
        CHECK_CASE("F01.pre_p5_active_preserved",
            store.ReadPackageManagementState(0,
                install.manifest.packageName, &state, &error) &&
            !state.removing && state.canonical.has_value() &&
            state.canonical->generation == generation);
        RemovalTombstoneV1 prepared;
        CHECK_CASE("F01.pre_p5_plan_not_published",
            store.ReadRemovalTombstone(
                requestId, &prepared, &error) &&
            prepared.state ==
                RemovalTombstoneState::PREPARED);
    }
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F02.pre_p5_restart_open",
            store.Open(&error));
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        const auto recovered = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation, requestId));
        CHECK_CASE("F02.pre_p5_retry_converges",
            recovered.verdict == UninstallVerdict::REMOVED);
    }
}

void TestTerminalReceiptRecovery(const std::filesystem::path& root)
{
    const auto storeRoot = root / "terminal-receipt-store";
    const auto managedRoot = root / "terminal-receipt-managed";
    std::filesystem::create_directories(storeRoot);
    const auto install = MakeInstall(
        "fixture.input.terminalreceipt",
        "install-terminalreceipt", 'y');
    const auto requestId = std::string("remove-terminalreceipt");
    uint64_t generation = 0;
    std::string expectedTombstoneDigest;
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F04.terminal_store_open",
            store.Open(&error));
        const auto snapshot =
            InstallPackage(&store, &stager, install);
        generation = snapshot.generation;
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        const auto removed = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation, requestId));
        CHECK_CASE("F04.terminal_setup_removed",
            removed.verdict == UninstallVerdict::REMOVED &&
            removed.tombstoneDigest.has_value());
        expectedTombstoneDigest =
            removed.tombstoneDigest.value_or("");
    }
    CHECK_CASE("F04.crash_image_without_p6",
        RemoveLastDurableEvent(storeRoot / "events.v1.log"));
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F04.closed_cas_replay_open",
            store.Open(&error));
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        auto foreign = MakeUninstall(
            install.manifest.packageName,
            generation, "foreign-terminal-retry");
        foreign.admission.callerScopeDigest = Repeat('d');
        foreign.admission.requestDigest =
            ComputeUninstallRequestDigest(foreign);
        const auto foreignResult =
            coordinator.Uninstall(foreign);
        CHECK_CASE("F04.closed_cas_foreign_caller_rejected",
            foreignResult.verdict ==
                UninstallVerdict::PACKAGE_NOT_FOUND &&
            foreignResult.transactionId ==
                foreign.admission.transactionId &&
            !foreignResult.packageName.has_value() &&
            !foreignResult.generation.has_value() &&
            !foreignResult.canonicalDigest.has_value() &&
            !foreignResult.tombstoneDigest.has_value());
        const auto recovered = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation,
                "same-caller-terminal-retry"));
        CHECK_CASE("F04.closed_cas_forward_closes_receipt",
            recovered.verdict == UninstallVerdict::REMOVED &&
            recovered.transactionId == requestId &&
            recovered.tombstoneDigest ==
                std::optional<std::string>(
                    expectedTombstoneDigest) &&
            recovered.residualObligations.empty());
        UninstallReceiptV1 readback;
        CHECK_CASE("F04.recovered_receipt_durable",
            store.ReadUninstallReceipt(
                requestId, &readback, &error) &&
            SerializeUninstallReceipt(readback) ==
                SerializeUninstallReceipt(recovered));
    }
}

void TestRestartAndResidual(const std::filesystem::path& root)
{
    const auto storeRoot = root / "restart-store";
    const auto managedRoot = root / "restart-managed";
    std::filesystem::create_directories(storeRoot);
    const auto install = MakeInstall(
        "fixture.input.restart", "install-restart", 'j');
    uint64_t generation = 0;
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F00.store_open", store.Open(&error));
        const auto snapshot =
            InstallPackage(&store, &stager, install);
        generation = snapshot.generation;
        OneShotFault fault(
            DurablePhase::P5_ACTIVE_GENERATION_PUBLISHED);
        PackageTransactionCoordinator coordinator(
            &store, &stager, &fault);
        const auto interrupted = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation, "remove-restart"));
        CHECK_CASE("F01.p5_forward_only",
            interrupted.verdict ==
                UninstallVerdict::INTERRUPTED_AFTER_DURABLE_WRITE &&
            interrupted.residualObligations.size() == 7);
        PackageManagementReadV1 state;
        CHECK_CASE("F01.removing_readback",
            store.ReadPackageManagementState(0,
                install.manifest.packageName, &state, &error) &&
            state.removing && state.canonical.has_value());
    }
    {
        FilePackageStore store(storeRoot.string());
        PosixPackageFileStager stager(managedRoot.string());
        std::string error;
        CHECK_CASE("F02.replay_open", store.Open(&error));
        NoFaultInjector noFault;
        PackageTransactionCoordinator coordinator(
            &store, &stager, &noFault);
        const auto recovered = coordinator.Uninstall(
            MakeUninstall(install.manifest.packageName,
                generation, "remove-restart"));
        CHECK_CASE("F02.restart_converges",
            recovered.verdict == UninstallVerdict::REMOVED &&
            recovered.transactionId == "remove-restart" &&
            recovered.residualObligations.empty());
    }

    const auto residualStore = root / "residual-store";
    const auto residualManaged = root / "residual-managed";
    std::filesystem::create_directories(residualStore);
    FilePackageStore store(residualStore.string());
    FailOnceCleanup stager(residualManaged.string());
    std::string error;
    CHECK_CASE("F03.residual_open", store.Open(&error));
    const auto residualInstall = MakeInstall(
        "fixture.input.residual", "install-residual", 'm');
    const auto snapshot =
        InstallPackage(&store, &stager, residualInstall);
    NoFaultInjector noFault;
    PackageTransactionCoordinator coordinator(
        &store, &stager, &noFault);
    const auto request = MakeUninstall(
        residualInstall.manifest.packageName,
        snapshot.generation, "remove-residual");
    const auto failed = coordinator.Uninstall(request);
    CHECK_CASE("F03.residual_exposed",
        failed.verdict == UninstallVerdict::INTERNAL_IO_ERROR &&
        failed.terminalState == "RECOVERING_FORWARD" &&
        !failed.residualObligations.empty());
    const auto retried = coordinator.Uninstall(request);
    CHECK_CASE("F03.matching_retry_converges",
        retried.verdict == UninstallVerdict::REMOVED);
}

void TestRemovingZeroQueue(const std::filesystem::path& root)
{
    const auto storeRoot = root / "concurrent-store";
    const auto managedRoot = root / "concurrent-managed";
    std::filesystem::create_directories(storeRoot);
    FilePackageStore store(storeRoot.string());
    BlockingCleanup stager(managedRoot.string());
    std::string error;
    CHECK_CASE("N03.store_open", store.Open(&error));
    const auto install = MakeInstall(
        "fixture.input.concurrent", "install-concurrent", 'p');
    const auto snapshot =
        InstallPackage(&store, &stager, install);
    NoFaultInjector noFault;
    PackageTransactionCoordinator remover(
        &store, &stager, &noFault);
    const auto remove = MakeUninstall(
        install.manifest.packageName, snapshot.generation,
        "remove-concurrent");
    UninstallReceiptV1 final;
    std::thread worker([&] {
        final = remover.Uninstall(remove);
    });
    stager.WaitEntered();

    PosixPackageFileStager otherStager(
        (root / "other-managed").string());
    PackageTransactionCoordinator concurrent(
        &store, &otherStager, &noFault);
    auto secondInstall = MakeInstall(
        install.manifest.packageName,
        "install-during-removal", 's');
    const auto begin = std::chrono::steady_clock::now();
    const auto installGuard =
        concurrent.Install(secondInstall);
    const auto updateGuard = concurrent.Update(
        MakeRemovalGuardUpdate(install,
            snapshot.generation, "update-during-removal"));
    auto otherRemove = MakeUninstall(
        install.manifest.packageName, snapshot.generation + 1,
        "remove-during-removal");
    const auto uninstallGuard =
        concurrent.Uninstall(otherRemove);
    const auto elapsed =
        std::chrono::duration_cast<std::chrono::milliseconds>(
            std::chrono::steady_clock::now() - begin).count();
    CHECK_CASE("N03.install_immediate_package_removing",
        installGuard.verdict ==
            InstallVerdict::PACKAGE_REMOVING);
    CHECK_CASE("N03.update_immediate_package_removing",
        updateGuard.verdict ==
            UpdateVerdict::PACKAGE_REMOVING);
    CHECK_CASE("N03.nonmatching_uninstall_immediate",
        uninstallGuard.verdict ==
            UninstallVerdict::PACKAGE_REMOVING);
    CHECK_CASE("N03.zero_queue_timeline", elapsed < 500);
    stager.Release();
    worker.join();
    CHECK_CASE("N03.owner_finishes",
        final.verdict == UninstallVerdict::REMOVED);
}

}  // namespace

int main(int argc, char** argv)
{
    if (argc != 2 || argv[1][0] != '/') {
        std::cerr << "usage: package_uninstall_host_test ABSOLUTE_TEMP_ROOT\n";
        return 2;
    }
    const std::filesystem::path root(argv[1]);
    std::filesystem::create_directories(root);
    gResults.open(root / "results.jsonl");
    TestPositiveAndIsolation(root);
    TestNegatives(root);
    TestCallerOwnership(root);
    TestPrePublicationRecovery(root);
    TestTerminalReceiptRecovery(root);
    TestRestartAndResidual(root);
    TestRemovingZeroQueue(root);
    gResults.flush();
    std::cout << "developer_cases=" << gCases
              << " failures=" << gFailures
              << " formal_verdict=NOT_ISSUED\n";
    return gFailures == 0 ? 0 : 1;
}
