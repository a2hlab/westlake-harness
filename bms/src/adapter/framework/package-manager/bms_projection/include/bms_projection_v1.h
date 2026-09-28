#ifndef OH_ADAPTER_BMS_PROJECTION_V1_H
#define OH_ADAPTER_BMS_PROJECTION_V1_H

#include <cstdint>
#include <string>

namespace oh_adapter::bms_projection {

enum class ProjectionState {
    NONE,
    PREPARED,
    ACTIVE,
};

enum class PublicationTokenState {
    PREPARED,
    CANONICAL_SELECTED,
    EXTERNAL_READY,
};

enum class ProjectionVerdict {
    PREPARED,
    ACTIVATED,
    REPLAYED,
    INVALID_REQUEST,
    NOT_SUPPORTED_USER,
    CALLER_SCOPE_MISMATCH,
    RESOURCE_RECEIPT_MISMATCH,
    TRANSACTION_MISMATCH,
    GENERATION_MISMATCH,
    DIGEST_MISMATCH,
    HOST_COLLISION,
    HOST_DENIED,
    UNSUPPORTED_FIELD,
    ACTIVATION_NOT_AUTHORIZED,
    READBACK_MISMATCH,
    TOKEN_CAS_FAILED,
    IO_ERROR,
    INTERRUPTED,
    // Append-only: preserve the numeric identity of all pre-existing verdicts.
    IDEMPOTENCY_CONFLICT,
};

enum class BackendResult {
    OK,
    NOT_FOUND,
    COLLISION,
    OWNER_MISMATCH,
    DENIED,
    UNSUPPORTED,
    IO_ERROR,
};

enum class ProjectionFaultPhase {
    AFTER_INTENT_DURABLE,
    AFTER_PREPARED_DURABLE,
    BEFORE_PREPARED_READBACK,
    AFTER_ACTIVATION_INTENT_DURABLE,
    AFTER_ACTIVE_DURABLE,
    BEFORE_TOKEN_CAS,
    AFTER_TOKEN_CAS,
};

struct CommandEnvelopeV1 {
    uint32_t schemaVersion = 1;
    std::string requestId;
    std::string callerScopeDigest;
    std::string policyVersion;
};

struct P4CandidateFixtureV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t candidateGeneration = 0;
    std::string canonicalDigest;
    std::string resourcePayloadDigest;
    std::string componentFactsDigest;
    std::string managedPathDigest;
    std::string canonicalCandidateState;
    ProjectionState projectionState = ProjectionState::NONE;
    PublicationTokenState tokenState = PublicationTokenState::PREPARED;
    std::string transactionId;
    uint64_t recordVersion = 0;
};

struct PostP5ActivationFixtureV1 {
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string projectionDigest;
    std::string resourcePayloadDigest;
    std::string canonicalState;
    ProjectionState projectionState = ProjectionState::PREPARED;
    PublicationTokenState tokenState =
        PublicationTokenState::CANONICAL_SELECTED;
    std::string transactionId;
    uint64_t recordVersion = 0;
};

// Dependency-view DTO copied field-for-field from the public/provenance subset
// of resource_projection::ResourceProjectionReceiptV1. Keeping the view local
// avoids coupling A10 to A08 implementation headers; verdict is the exact
// ResourceProjectionBuilderV1::VerdictName value ("READY" is required).
struct ResourceProjectionReadyReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A08";
    std::string requestId;
    std::string transactionId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string resourceInputDigest;
    std::string resourcePayloadDigest;
    std::string buildPolicyVersion;
    std::string payloadKind;
    std::string state;
    std::string verdict;
};

struct HostIdentityV1 {
    std::string bundleName;
    std::string appId;
    uint64_t uid = 0;
    uint64_t accessTokenId = 0;
};

struct HostProjectionPayloadV1 {
    uint32_t schemaVersion = 1;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    HostIdentityV1 hostIdentity;
    std::string canonicalDigest;
    std::string resourcePayloadDigest;
    std::string componentFactsDigest;
    std::string managedPathDigest;
};

struct HostProjectionRuntimeV1 {
    HostProjectionPayloadV1 payload;
    std::string projectionDigest;
    ProjectionState state = ProjectionState::NONE;
};

struct ProjectionReceiptV1 {
    uint32_t schemaVersion = 1;
    std::string actionId = "Fn01.A10";
    std::string requestId;
    std::string transactionId;
    std::string packageName;
    uint32_t userId = 0;
    uint64_t generation = 0;
    std::string canonicalDigest;
    std::string resourcePayloadDigest;
    std::string projectionDigest;
    ProjectionState projectionState = ProjectionState::NONE;
    PublicationTokenState tokenState = PublicationTokenState::PREPARED;
    ProjectionVerdict verdict = ProjectionVerdict::INVALID_REQUEST;
    std::string reason;
    // Appended during pre-promotion remediation; do not insert above legacy
    // fields because their source-level order is intentionally preserved.
    std::string operation;
    std::string requestDigest;
};

class ProjectionFaultInjector {
public:
    virtual ~ProjectionFaultInjector() = default;
    virtual bool InterruptAt(ProjectionFaultPhase phase) = 0;
};

class ProjectionOutboxV1 {
public:
    virtual ~ProjectionOutboxV1() = default;
    // Atomic create-if-absent-or-exact contract. Returns true only when this
    // requestId was newly bound to encodedIntent or was already bound to the
    // byte-identical value. A conflicting existing value must remain unchanged
    // and return false; GetIntent lets the coordinator distinguish conflict
    // from storage failure without returning another request's receipt.
    virtual bool PutIntent(
        const std::string& requestId, const std::string& encodedIntent) = 0;
    virtual bool GetIntent(
        const std::string& requestId, std::string* encodedIntent) const = 0;
    virtual bool PutReceipt(
        const std::string& requestId, const ProjectionReceiptV1& receipt) = 0;
    virtual bool GetReceipt(
        const std::string& requestId, ProjectionReceiptV1* receipt) const = 0;
};

class BmsProjectionAdapterV1 {
public:
    virtual ~BmsProjectionAdapterV1() = default;
    virtual BackendResult AllocateIdentity(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string& transactionId, HostIdentityV1* identity) = 0;
    virtual BackendResult CreatePrepared(
        const HostProjectionRuntimeV1& expected,
        const std::string& transactionId,
        HostProjectionRuntimeV1* readback) = 0;
    virtual BackendResult Activate(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string& canonicalDigest,
        const std::string& projectionDigest,
        const std::string& transactionId,
        HostProjectionRuntimeV1* readback) = 0;
    virtual BackendResult Read(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        HostProjectionRuntimeV1* readback) const = 0;
    virtual BackendResult RemovePrepared(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        const std::string& transactionId) = 0;
};

class PublicationTokenStoreV1 {
public:
    virtual ~PublicationTokenStoreV1() = default;
    virtual bool Read(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        PublicationTokenState* state) const = 0;
    virtual bool CompareAndSwap(
        const std::string& packageName, uint32_t userId, uint64_t generation,
        PublicationTokenState expected, PublicationTokenState desired) = 0;
};

struct BmsProjectionPolicyV1 {
    uint32_t schemaVersion = 1;
    std::string policyVersion;
    std::string expectedCallerScopeDigest;
};

class BmsProjectionCoordinatorV1 final {
public:
    BmsProjectionCoordinatorV1(
        BmsProjectionPolicyV1 policy, ProjectionOutboxV1* outbox,
        BmsProjectionAdapterV1* adapter, PublicationTokenStoreV1* tokenStore);

    ProjectionReceiptV1 Prepare(
        const CommandEnvelopeV1& envelope,
        const P4CandidateFixtureV1& candidate,
        const ResourceProjectionReadyReceiptV1& resourceReceipt,
        ProjectionFaultInjector* faultInjector);

    ProjectionReceiptV1 Activate(
        const CommandEnvelopeV1& envelope,
        const PostP5ActivationFixtureV1& fixture,
        const ResourceProjectionReadyReceiptV1& resourceReceipt,
        ProjectionFaultInjector* faultInjector);

    static std::string CanonicalPayload(
        const HostProjectionPayloadV1& payload);
    static std::string ProjectionDigest(
        const HostProjectionPayloadV1& payload);
    static std::string SerializeReceipt(const ProjectionReceiptV1& receipt);
    static const char* VerdictName(ProjectionVerdict verdict);
    static const char* ProjectionStateName(ProjectionState state);
    static const char* TokenStateName(PublicationTokenState state);

private:
    BmsProjectionPolicyV1 policy_;
    ProjectionOutboxV1* outbox_;
    BmsProjectionAdapterV1* adapter_;
    PublicationTokenStoreV1* tokenStore_;
};

}  // namespace oh_adapter::bms_projection

#endif  // OH_ADAPTER_BMS_PROJECTION_V1_H
