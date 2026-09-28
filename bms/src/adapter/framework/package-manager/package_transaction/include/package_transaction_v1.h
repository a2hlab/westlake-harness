#ifndef OH_ADAPTER_PACKAGE_TRANSACTION_V1_H
#define OH_ADAPTER_PACKAGE_TRANSACTION_V1_H

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::package_authority {
class PackageAuthorityServiceV1;
}

namespace oh_adapter::package_transaction {

enum class ArtifactRole {
    BASE,
    SPLIT_CONFIG,
    SPLIT_FEATURE,
};

enum class DurablePhase {
    P0_INPUT_FROZEN,
    P1_PLAN_DURABLE,
    P2_FILES_PREPARED,
    P3_CANONICAL_PREPARED,
    P4_PUBLICATION_PREPARED,
    P5_ACTIVE_GENERATION_PUBLISHED,
    P6_RECEIPT_CLOSED,
};

enum class PublicationState {
    NONE,
    PREPARED,
    CANONICAL_SELECTED,
    EXTERNAL_READY,
};

enum class HostProjectionState {
    NONE,
    PREPARED,
    ACTIVE,
    STALE,
    REMOVING,
};

enum class InstallVerdict {
    COMMITTED,
    NOT_SUPPORTED,
    NOT_SUPPORTED_ARTIFACT_PROFILE,
    INVALID_ENVELOPE,
    ARTIFACT_DIGEST_MISMATCH,
    IDENTITY_MISMATCH,
    SIGNING_REJECTED,
    POLICY_REJECTED,
    PACKAGE_ALREADY_EXISTS,
    PACKAGE_REMOVING,
    GENERATION_MISMATCH,
    IDEMPOTENCY_CONFLICT,
    DATA_INCONSISTENT,
    INTERNAL_IO_ERROR,
    INTERRUPTED_AFTER_DURABLE_WRITE,
};

enum class RestartRecoveryVerdict {
    RESTORED_COMMITTED,
    NON_READY,
    ABSENT,
    IDENTITY_MISMATCH,
    DATA_INCONSISTENT,
};

struct ArtifactDescriptorV1 {
    std::string artifactId;
    ArtifactRole role = ArtifactRole::BASE;
    std::vector<uint8_t> bytes;
    uint64_t byteLength = 0;
    std::string sha256;
};

struct PackageArtifactSetV1 {
    uint32_t schemaVersion = 1;
    std::vector<ArtifactDescriptorV1> artifacts;
    std::string artifactSetDigest;
};

struct ManifestComponentFactV1 {
    std::string kind;
    std::string name;
    std::optional<bool> exported;
};

struct ManifestFieldProvenanceV1 {
    std::string field;
    std::string artifactSha256;
    std::string manifestEntrySha256;
    uint64_t manifestChunkOffset = 0;
};

struct ManifestFactsV1 {
    std::string artifactSetDigest;
    std::string parserVersion;
    std::string packageName;
    uint64_t versionCode = 0;
    std::string versionName;
    uint32_t minSdk = 0;
    uint32_t targetSdk = 0;
    std::string applicationClassName;
    std::string applicationLabel;
    std::vector<ManifestComponentFactV1> components;
    std::vector<std::string> requestedPermissions;
    std::vector<std::string> declaredPermissions;
    std::vector<ManifestFieldProvenanceV1> provenance;
};

struct PackageSigningLineageFactV1 {
    std::string certificateSha256;
    uint32_t capabilities = 0;
};

struct SigningFactsV1 {
    std::string artifactSetDigest;
    std::string verifierVersion;
    std::string policyProfile;
    bool verified = false;
    std::vector<uint32_t> schemeVersions;
    std::vector<std::string> signerCertificateDigests;
    std::vector<std::string> signerCertificateDerHex;
    std::vector<PackageSigningLineageFactV1> lineage;
    std::optional<std::string> lineageDigest;
    std::optional<std::string> sourceReceiptDigest;
};

struct JobMemberFirstAdmissionEnvelopeV1 {
    uint32_t schemaVersion = 1;
    std::string jobId;
    std::string memberId;
    uint32_t memberIndex = 0;
    std::string operation = "INSTALL";
    std::string transactionId;
    std::string requestDigest;
    uint64_t jobRecordVersion = 0;
    std::string callerScopeDigest;
    std::string policySnapshotId;
};

struct InstallRequestV1 {
    JobMemberFirstAdmissionEnvelopeV1 admission;
    PackageArtifactSetV1 artifactSet;
    ManifestFactsV1 manifest;
    SigningFactsV1 signing;
    uint32_t userId = 0;
    std::optional<std::string> expectedPackageName;
    std::optional<uint64_t> expectedGeneration;
    std::string policyRef;
    std::string retryIdentity;
};

struct UpdatePolicySnapshotV1 {
    uint32_t schemaVersion = 1;
    std::string policyId;
    std::string policyVersion;
    std::string rulesDigest;
    std::string ruleId;
    bool permitsUpdate = false;
};

struct SigningContinuityAttestationV1 {
    uint32_t schemaVersion = 1;
    std::string priorSigningFactsDigest;
    std::string signingReceiptDigest;
    std::string decisionDigest;
    std::string capabilityPath;
    bool allowed = false;
};

struct UpdateRequestV1 {
    JobMemberFirstAdmissionEnvelopeV1 admission;
    PackageArtifactSetV1 artifactSet;
    ManifestFactsV1 manifest;
    SigningFactsV1 signing;
    uint32_t userId = 0;
    std::optional<std::string> expectedPackageName;
    std::optional<uint64_t> expectedGeneration;
    std::string policyRef;
    std::string retryIdentity;
    UpdatePolicySnapshotV1 policySnapshot;
    SigningContinuityAttestationV1 signingContinuity;
};

enum class UpdateVerdict {
    UPDATED,
    INVALID_ENVELOPE,
    NOT_SUPPORTED,
    NOT_SUPPORTED_ARTIFACT_PROFILE,
    ARTIFACT_DIGEST_MISMATCH,
    IDENTITY_MISMATCH,
    SIGNING_REJECTED,
    POLICY_REJECTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_REMOVING,
    GENERATION_MISMATCH,
    IDEMPOTENCY_CONFLICT,
    DATA_INCONSISTENT,
    INTERNAL_IO_ERROR,
    INTERRUPTED_AFTER_DURABLE_WRITE,
};

enum class UninstallVerdict {
    REMOVED,
    INVALID_ENVELOPE,
    NOT_SUPPORTED,
    PACKAGE_NOT_FOUND,
    PACKAGE_REMOVING,
    SELECTOR_MISMATCH,
    GENERATION_MISMATCH,
    IDEMPOTENCY_CONFLICT,
    DATA_INCONSISTENT,
    INTERNAL_IO_ERROR,
    INTERRUPTED_AFTER_DURABLE_WRITE,
};

enum class RemovalTombstoneState {
    PREPARED,
    OPEN,
    CLOSED_REMOVED,
};

enum class RemovalObligationState {
    OPEN,
    CLOSED,
};

struct UninstallRequestV1 {
    JobMemberFirstAdmissionEnvelopeV1 admission;
    uint32_t userId = 0;
    std::string packageSelector;
    std::optional<std::string> expectedPackageName;
    std::optional<uint64_t> expectedGeneration;
    std::string policyRef;
    std::string retryIdentity;
};

struct RemovalObligationV1 {
    std::string kind;
    std::string identityDigest;
    RemovalObligationState state = RemovalObligationState::OPEN;
    std::string closeResult;
    uint64_t closedRecordVersion = 0;
};

struct RemovalTombstoneV1 {
    uint32_t schemaVersion = 1;
    std::string transactionId;
    std::string requestDigest;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string managedCodePath;
    std::string managedCodeDigest;
    RemovalTombstoneState state = RemovalTombstoneState::PREPARED;
    std::vector<RemovalObligationV1> obligations;
    uint64_t recordVersion = 0;
    std::string tombstoneDigest;
};

struct UninstallReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A15";
    std::string transactionId;
    std::string requestDigest;
    std::optional<std::string> packageName;
    std::optional<uint64_t> generation;
    std::optional<std::string> canonicalDigest;
    std::optional<std::string> tombstoneDigest;
    std::vector<std::string> residualObligations;
    UninstallVerdict verdict = UninstallVerdict::DATA_INCONSISTENT;
    std::string terminalState;
};

enum class RetirementPlanState {
    OPEN,
    ACTIVE,
    CLOSED,
};

enum class RetirementObligationState {
    OPEN,
    CLOSED,
};

struct RetirementObligationV1 {
    std::string kind;
    std::string identityDigest;
    RetirementObligationState state = RetirementObligationState::OPEN;
    std::string closeResult;
    uint64_t closedRecordVersion = 0;
};

struct GenerationRetirementPlanV1 {
    uint32_t schemaVersion = 1;
    std::string transactionId;
    std::string journalRef;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t oldGeneration = 0;
    uint64_t newGeneration = 0;
    std::string oldCanonicalDigest;
    std::string oldManagedCodePath;
    std::string oldManagedCodeDigest;
    std::string sharedDataRootIdentity;
    bool sharedDataPreserved = true;
    HostProjectionState oldProjectionState = HostProjectionState::NONE;
    RetirementPlanState state = RetirementPlanState::OPEN;
    std::vector<RetirementObligationV1> obligations;
    uint64_t recordVersion = 0;
    std::string planDigest;
};

struct UpdateReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A14";
    std::string transactionId;
    std::string requestDigest;
    std::optional<std::string> packageName;
    std::optional<uint64_t> oldGeneration;
    std::optional<uint64_t> newGeneration;
    std::optional<std::string> artifactSetDigest;
    std::optional<std::string> canonicalDigest;
    std::string policyRuleId;
    std::string policyVersion;
    std::string policyRulesDigest;
    std::optional<std::string> retirementPlanDigest;
    UpdateVerdict verdict = UpdateVerdict::DATA_INCONSISTENT;
    std::string terminalState;
};

struct ManagedFilesV1 {
    std::string baseCodePath;
    std::string baseCodeDigest;
};

struct PrimaryUserStateV1 {
    uint32_t userId = 0;
    bool installed = false;
    bool enabled = false;
    bool stopped = false;
    bool hidden = false;
};

struct RecoveredArtifactV1 {
    std::string artifactId;
    uint64_t byteLength = 0;
    std::string sha256;
};

struct PackageLifecycleReceiptV1 {
    std::string transactionId;
    std::optional<std::string> packageName;
    std::optional<uint64_t> generation;
    std::string requestDigest;
    std::optional<std::string> artifactSetDigest;
    std::optional<std::string> durableRecordDigest;
    std::string terminalState;
    InstallVerdict verdict = InstallVerdict::DATA_INCONSISTENT;
};

struct PublishedPackageSnapshotV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string artifactSetDigest;
    std::string canonicalDigest;
    ManagedFilesV1 managedFiles;
    PrimaryUserStateV1 primaryUserState;
    std::vector<RecoveredArtifactV1> artifacts;
    std::optional<ManifestFactsV1> manifestFacts;
    std::optional<SigningFactsV1> signingFacts;
    PublicationState publicationState = PublicationState::NONE;
};

struct PublicationTokenV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    PublicationState state = PublicationState::NONE;
};

struct HostProjectionRuntimeV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    HostProjectionState state = HostProjectionState::NONE;
};

struct PackageManagementReadV1 {
    uint64_t catalogRevision = 0;
    bool removing = false;
    std::optional<PublishedPackageSnapshotV1> canonical;
    std::optional<PublicationTokenV1> publicationToken;
    std::optional<HostProjectionRuntimeV1> projection;
};

struct RestartBoundaryV1 {
    std::string beforeBootId;
    std::string afterBootId;
    std::string beforeServiceId;
    std::string afterServiceId;
};

struct RestartRecoveryRequestV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string transactionId;
    RestartBoundaryV1 boundary;
    std::optional<std::string> expectedRequestDigest;
    std::optional<std::string> expectedPackageName;
    std::optional<std::string> expectedArtifactSetDigest;
    std::optional<uint64_t> expectedGeneration;
    std::optional<std::string> expectedCanonicalDigest;
    std::optional<DurablePhase> expectedPhase;
};

struct RestartRecoveryReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A11";
    std::string requestId;
    std::string transactionId;
    std::string requestDigest;
    std::optional<std::string> packageName;
    std::optional<std::string> artifactSetDigest;
    std::optional<uint64_t> generation;
    std::optional<std::string> canonicalDigest;
    std::optional<ManagedFilesV1> managedFiles;
    std::optional<PrimaryUserStateV1> primaryUserState;
    std::vector<RecoveredArtifactV1> artifacts;
    DurablePhase durablePhase = DurablePhase::P0_INPUT_FROZEN;
    PublicationState publicationState = PublicationState::NONE;
    HostProjectionState hostProjectionState = HostProjectionState::NONE;
    RestartRecoveryVerdict verdict = RestartRecoveryVerdict::DATA_INCONSISTENT;
    bool journalPresent = false;
    bool consumerReady = false;
    uint64_t catalogRevision = 0;
    RestartBoundaryV1 boundary;
    std::string terminalState;
    std::string reason;
};

class FaultInjector {
public:
    virtual ~FaultInjector() = default;
    virtual bool InterruptAfter(DurablePhase phase) = 0;
    virtual bool SimulatesProcessCrash() const
    {
        return false;
    }
};

class NoFaultInjector final : public FaultInjector {
public:
    bool InterruptAfter(DurablePhase) override
    {
        return false;
    }
};

class PackageFileStager {
public:
    virtual ~PackageFileStager() = default;
    virtual bool Stage(const std::string& packageName, uint32_t userId,
        uint64_t generation, const ArtifactDescriptorV1& artifact,
        ManagedFilesV1* managedFiles, std::string* error) = 0;
    virtual bool Cleanup(const ManagedFilesV1& managedFiles,
        std::string* error) = 0;
};

class PosixPackageFileStager final : public PackageFileStager {
public:
    explicit PosixPackageFileStager(std::string managedRoot);

    bool Stage(const std::string& packageName, uint32_t userId,
        uint64_t generation, const ArtifactDescriptorV1& artifact,
        ManagedFilesV1* managedFiles, std::string* error) override;
    bool Cleanup(const ManagedFilesV1& managedFiles,
        std::string* error) override;

private:
    std::string managedRoot_;
};

class FilePackageStore {
public:
    explicit FilePackageStore(std::string storeRoot);
    ~FilePackageStore();

    FilePackageStore(const FilePackageStore&) = delete;
    FilePackageStore& operator=(const FilePackageStore&) = delete;

    bool Open(std::string* error);
    // Query-only runtimes replay an existing durable snapshot without
    // acquiring or retaining the mutation writer lease.  The call fails
    // closed when the store is absent or a different process is mutating it.
    bool OpenReadOnly(std::string* error);
    bool ReadPublishedPackage(uint32_t userId, const std::string& packageName,
        PublishedPackageSnapshotV1* snapshot, std::string* error) const;
    bool ReadReceipt(const std::string& transactionId,
        PackageLifecycleReceiptV1* receipt, std::string* error) const;
    bool ReadPublicationToken(uint32_t userId, const std::string& packageName,
        PublicationTokenV1* token, std::string* error) const;
    bool ReadPackageManagementState(uint32_t userId,
        const std::string& packageName, PackageManagementReadV1* state,
        std::string* error) const;
    bool ReadUpdateReceipt(const std::string& transactionId,
        UpdateReceiptV1* receipt, std::string* error) const;
    bool ReadRetirementPlan(const std::string& transactionId,
        GenerationRetirementPlanV1* plan, std::string* error) const;
    bool ReadRemovalTombstone(const std::string& transactionId,
        RemovalTombstoneV1* tombstone, std::string* error) const;
    bool ReadUninstallReceipt(const std::string& transactionId,
        UninstallReceiptV1* receipt, std::string* error) const;
    RestartRecoveryReceiptV1 RecoverAfterRestart(
        const RestartRecoveryRequestV1& request);

#if defined(FN01_ENABLE_REFERENCE_FIXTURES)
    // Host-verifier seam only. Production builds do not expose this method.
    bool SeedRemovalTombstoneForFixture(uint32_t userId,
        const std::string& packageName, uint64_t generation,
        std::string* error);
    bool SeedHostProjectionForFixture(uint32_t userId,
        const std::string& packageName, uint64_t generation,
        const std::string& canonicalDigest,
        HostProjectionState projectionState,
        PublicationState tokenState, std::string* error);
#endif

private:
    friend class PackageTransactionCoordinator;
    friend class package_authority::PackageAuthorityServiceV1;

    bool CommitExternalReady(uint32_t userId,
        const std::string& packageName, uint64_t generation,
        const std::string& canonicalDigest, std::string* error);

    struct Impl;
    Impl* impl_;
};

class PackageTransactionCoordinator {
public:
    PackageTransactionCoordinator(FilePackageStore* store,
        PackageFileStager* stager, FaultInjector* faultInjector);

    PackageLifecycleReceiptV1 Install(const InstallRequestV1& request);
    UpdateReceiptV1 Update(const UpdateRequestV1& request);
    UninstallReceiptV1 Uninstall(const UninstallRequestV1& request);

private:
    UpdateReceiptV1 FinishUpdateRetirement(
        const UpdateRequestV1& request);

    FilePackageStore* store_;
    PackageFileStager* stager_;
    FaultInjector* faultInjector_;
};

std::string ComputeArtifactSetDigest(const PackageArtifactSetV1& artifactSet);
std::string ComputeInstallRequestDigest(const InstallRequestV1& request);
std::string ComputeUpdateRequestDigest(const UpdateRequestV1& request);
std::string ComputeUninstallRequestDigest(
    const UninstallRequestV1& request);
std::string ComputePackageSigningFactsDigest(const SigningFactsV1& signing);
const char* InstallVerdictName(InstallVerdict verdict);
const char* UpdateVerdictName(UpdateVerdict verdict);
const char* UninstallVerdictName(UninstallVerdict verdict);
const char* RemovalTombstoneStateName(RemovalTombstoneState state);
const char* RemovalObligationStateName(RemovalObligationState state);
const char* RetirementPlanStateName(RetirementPlanState state);
const char* RetirementObligationStateName(
    RetirementObligationState state);
const char* PublicationStateName(PublicationState state);
const char* HostProjectionStateName(HostProjectionState state);
const char* DurablePhaseName(DurablePhase phase);
const char* RestartRecoveryVerdictName(RestartRecoveryVerdict verdict);
std::string SerializeRestartRecoveryReceipt(
    const RestartRecoveryReceiptV1& receipt);
std::string SerializeUpdateReceipt(const UpdateReceiptV1& receipt);
std::string SerializeRetirementPlan(
    const GenerationRetirementPlanV1& plan);
std::string SerializeRemovalTombstone(
    const RemovalTombstoneV1& tombstone);
std::string SerializeUninstallReceipt(
    const UninstallReceiptV1& receipt);

}  // namespace oh_adapter::package_transaction

#endif  // OH_ADAPTER_PACKAGE_TRANSACTION_V1_H
