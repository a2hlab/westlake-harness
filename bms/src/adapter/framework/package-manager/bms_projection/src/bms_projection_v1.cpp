#include "bms_projection_v1.h"

#include "sha256.h"

#include <algorithm>
#include <cctype>
#include <sstream>
#include <string_view>
#include <utility>

namespace oh_adapter::bms_projection {
namespace {

std::string JsonEscape(std::string_view value)
{
    std::string result;
    result.reserve(value.size() + 8);
    for (const unsigned char character : value) {
        switch (character) {
            case '"': result += "\\\""; break;
            case '\\': result += "\\\\"; break;
            case '\b': result += "\\b"; break;
            case '\f': result += "\\f"; break;
            case '\n': result += "\\n"; break;
            case '\r': result += "\\r"; break;
            case '\t': result += "\\t"; break;
            default:
                if (character < 0x20) {
                    static constexpr char kHex[] = "0123456789abcdef";
                    result += "\\u00";
                    result.push_back(kHex[character >> 4]);
                    result.push_back(kHex[character & 0x0f]);
                } else {
                    result.push_back(static_cast<char>(character));
                }
        }
    }
    return result;
}

std::string Sha256Hex(std::string_view value)
{
    unsigned char digest[32]{};
    sha256(reinterpret_cast<const uint8_t*>(value.data()), value.size(), digest);
    static constexpr char kHex[] = "0123456789abcdef";
    std::string result(sizeof(digest) * 2, '0');
    for (size_t index = 0; index < sizeof(digest); ++index) {
        result[index * 2] = kHex[digest[index] >> 4];
        result[index * 2 + 1] = kHex[digest[index] & 0x0f];
    }
    return result;
}

bool IsLowerHexDigest(const std::string& value)
{
    return value.size() == 64 &&
        std::all_of(value.begin(), value.end(), [](const unsigned char value) {
            return std::isdigit(value) || (value >= 'a' && value <= 'f');
        });
}

bool IsSafeIdentifier(const std::string& value, bool packageName)
{
    if (value.empty() || value.size() > 255 || value == "." || value == "..") {
        return false;
    }
    bool hasDot = false;
    for (const unsigned char character : value) {
        const bool accepted =
            std::isalnum(character) || character == '_' || character == '-' ||
            (packageName && character == '.');
        if (!accepted) return false;
        hasDot = hasDot || character == '.';
    }
    return !packageName || hasDot;
}

bool Interrupted(
    ProjectionFaultInjector* injector, ProjectionFaultPhase phase)
{
    return injector != nullptr && injector->InterruptAt(phase);
}

ProjectionReceiptV1 BaseReceipt(
    const CommandEnvelopeV1& envelope, const std::string& transactionId,
    const std::string& packageName, uint32_t userId, uint64_t generation,
    const std::string& canonicalDigest,
    const std::string& resourcePayloadDigest)
{
    ProjectionReceiptV1 receipt;
    receipt.requestId = envelope.requestId;
    receipt.transactionId = transactionId;
    receipt.packageName = packageName;
    receipt.userId = userId;
    receipt.generation = generation;
    receipt.canonicalDigest = canonicalDigest;
    receipt.resourcePayloadDigest = resourcePayloadDigest;
    return receipt;
}

ProjectionReceiptV1 Reject(
    ProjectionReceiptV1 receipt, ProjectionVerdict verdict, std::string reason)
{
    receipt.verdict = verdict;
    receipt.reason = std::move(reason);
    return receipt;
}

ProjectionVerdict BackendVerdict(BackendResult result)
{
    switch (result) {
        case BackendResult::COLLISION:
            return ProjectionVerdict::HOST_COLLISION;
        case BackendResult::OWNER_MISMATCH:
            return ProjectionVerdict::TRANSACTION_MISMATCH;
        case BackendResult::DENIED:
            return ProjectionVerdict::HOST_DENIED;
        case BackendResult::UNSUPPORTED:
            return ProjectionVerdict::UNSUPPORTED_FIELD;
        case BackendResult::IO_ERROR:
        case BackendResult::NOT_FOUND:
            return ProjectionVerdict::IO_ERROR;
        case BackendResult::OK:
            break;
    }
    return ProjectionVerdict::IO_ERROR;
}

bool SameIdentity(
    const HostIdentityV1& left, const HostIdentityV1& right)
{
    return left.bundleName == right.bundleName &&
        left.appId == right.appId && left.uid == right.uid &&
        left.accessTokenId == right.accessTokenId;
}

bool SamePayload(
    const HostProjectionPayloadV1& left,
    const HostProjectionPayloadV1& right)
{
    return left.schemaVersion == right.schemaVersion &&
        left.packageName == right.packageName &&
        left.userId == right.userId &&
        left.generation == right.generation &&
        SameIdentity(left.hostIdentity, right.hostIdentity) &&
        left.canonicalDigest == right.canonicalDigest &&
        left.resourcePayloadDigest == right.resourcePayloadDigest &&
        left.componentFactsDigest == right.componentFactsDigest &&
        left.managedPathDigest == right.managedPathDigest;
}

bool SameRuntime(
    const HostProjectionRuntimeV1& left,
    const HostProjectionRuntimeV1& right)
{
    return SamePayload(left.payload, right.payload) &&
        left.projectionDigest == right.projectionDigest &&
        left.state == right.state;
}

bool ResourceMatches(
    const ResourceProjectionReadyReceiptV1& receipt,
    const std::string& packageName, uint32_t userId, uint64_t generation,
    const std::string& transactionId, const std::string& canonicalDigest,
    const std::string& resourcePayloadDigest)
{
    return receipt.schemaVersion == 1 && receipt.actionId == "Fn01.A08" &&
        IsSafeIdentifier(receipt.requestId, false) &&
        receipt.transactionId == transactionId &&
        IsSafeIdentifier(receipt.transactionId, false) &&
        receipt.packageName == packageName && receipt.userId == userId &&
        receipt.generation == generation &&
        receipt.canonicalDigest == canonicalDigest &&
        IsLowerHexDigest(receipt.resourceInputDigest) &&
        receipt.resourcePayloadDigest == resourcePayloadDigest &&
        IsSafeIdentifier(receipt.buildPolicyVersion, false) &&
        (receipt.payloadKind == "MATERIALIZED" ||
            receipt.payloadKind == "EMPTY") &&
        receipt.state == "READY" && receipt.verdict == "READY";
}

const char* ProjectionStateIdentity(ProjectionState state)
{
    switch (state) {
        case ProjectionState::NONE: return "NONE";
        case ProjectionState::PREPARED: return "PREPARED";
        case ProjectionState::ACTIVE: return "ACTIVE";
    }
    return "UNKNOWN";
}

const char* TokenStateIdentity(PublicationTokenState state)
{
    switch (state) {
        case PublicationTokenState::PREPARED: return "PREPARED";
        case PublicationTokenState::CANONICAL_SELECTED:
            return "CANONICAL_SELECTED";
        case PublicationTokenState::EXTERNAL_READY: return "EXTERNAL_READY";
    }
    return "UNKNOWN";
}

std::string ResourceReceiptIdentity(
    const ResourceProjectionReadyReceiptV1& receipt)
{
    std::ostringstream output;
    output << "{\"actionId\":\"" << JsonEscape(receipt.actionId)
           << "\",\"buildPolicyVersion\":\""
           << JsonEscape(receipt.buildPolicyVersion)
           << "\",\"canonicalDigest\":\"" << receipt.canonicalDigest
           << "\",\"generation\":" << receipt.generation
           << ",\"packageName\":\"" << JsonEscape(receipt.packageName)
           << "\",\"payloadKind\":\"" << JsonEscape(receipt.payloadKind)
           << "\",\"requestId\":\"" << JsonEscape(receipt.requestId)
           << "\",\"resourceInputDigest\":\""
           << receipt.resourceInputDigest
           << "\",\"resourcePayloadDigest\":\""
           << receipt.resourcePayloadDigest
           << "\",\"schemaVersion\":" << receipt.schemaVersion
           << ",\"state\":\"" << JsonEscape(receipt.state)
           << "\",\"transactionId\":\""
           << JsonEscape(receipt.transactionId)
           << "\",\"userId\":" << receipt.userId
           << ",\"verdict\":\"" << JsonEscape(receipt.verdict) << "\"}";
    return output.str();
}

std::string PrepareRequestPayload(
    const CommandEnvelopeV1& envelope,
    const P4CandidateFixtureV1& candidate,
    const ResourceProjectionReadyReceiptV1& resourceReceipt)
{
    std::ostringstream output;
    output << "{\"actionId\":\"Fn01.A10\","
           << "\"callerScopeDigest\":\"" << envelope.callerScopeDigest
           << "\",\"canonicalCandidateState\":\""
           << JsonEscape(candidate.canonicalCandidateState)
           << "\",\"canonicalDigest\":\"" << candidate.canonicalDigest
           << "\",\"componentFactsDigest\":\""
           << candidate.componentFactsDigest
           << "\",\"generation\":" << candidate.candidateGeneration
           << ",\"managedPathDigest\":\"" << candidate.managedPathDigest
           << "\",\"operation\":\"PREPARE\",\"packageName\":\""
           << JsonEscape(candidate.packageName)
           << "\",\"policyVersion\":\""
           << JsonEscape(envelope.policyVersion)
           << "\",\"projectionState\":\""
           << ProjectionStateIdentity(candidate.projectionState)
           << "\",\"recordVersion\":" << candidate.recordVersion
           << ",\"requestId\":\"" << JsonEscape(envelope.requestId)
           << "\",\"resourcePayloadDigest\":\""
           << candidate.resourcePayloadDigest
           << "\",\"resourceReceipt\":"
           << ResourceReceiptIdentity(resourceReceipt)
           << ",\"schemaVersion\":" << envelope.schemaVersion
           << ",\"tokenState\":\""
           << TokenStateIdentity(candidate.tokenState)
           << "\",\"transactionId\":\""
           << JsonEscape(candidate.transactionId)
           << "\",\"userId\":" << candidate.userId
           << "}";
    return output.str();
}

std::string ActivationRequestPayload(
    const CommandEnvelopeV1& envelope,
    const PostP5ActivationFixtureV1& fixture,
    const ResourceProjectionReadyReceiptV1& resourceReceipt)
{
    std::ostringstream output;
    output << "{\"actionId\":\"Fn01.A10\","
           << "\"callerScopeDigest\":\"" << envelope.callerScopeDigest
           << "\",\"canonicalDigest\":\"" << fixture.canonicalDigest
           << "\",\"canonicalState\":\""
           << JsonEscape(fixture.canonicalState)
           << "\",\"generation\":" << fixture.generation
           << ",\"operation\":\"ACTIVATE\",\"packageName\":\""
           << JsonEscape(fixture.packageName)
           << "\",\"policyVersion\":\""
           << JsonEscape(envelope.policyVersion)
           << "\",\"projectionDigest\":\"" << fixture.projectionDigest
           << "\",\"projectionState\":\""
           << ProjectionStateIdentity(fixture.projectionState)
           << "\",\"recordVersion\":" << fixture.recordVersion
           << ",\"requestId\":\"" << JsonEscape(envelope.requestId)
           << "\",\"resourcePayloadDigest\":\""
           << fixture.resourcePayloadDigest
           << "\",\"resourceReceipt\":"
           << ResourceReceiptIdentity(resourceReceipt)
           << ",\"schemaVersion\":" << envelope.schemaVersion
           << ",\"tokenState\":\""
           << TokenStateIdentity(fixture.tokenState)
           << "\",\"transactionId\":\""
           << JsonEscape(fixture.transactionId)
           << "\",\"userId\":" << fixture.userId
           << "}";
    return output.str();
}

std::string DurableIntent(
    const char* operation, const std::string& requestDigest,
    const std::string& requestPayload)
{
    std::ostringstream output;
    output << "{\"actionId\":\"Fn01.A10\",\"operation\":\""
           << operation << "\",\"requestDigest\":\"" << requestDigest
           << "\",\"request\":" << requestPayload << "}";
    return output.str();
}

bool ClosedReplayMatches(
    const ProjectionOutboxV1& outbox, const std::string& requestId,
    const char* operation, const std::string& requestDigest,
    const std::string& expectedIntent,
    const ProjectionReceiptV1& expected,
    const ProjectionReceiptV1& replay)
{
    std::string storedIntent;
    return replay.schemaVersion == 1 &&
        replay.actionId == "Fn01.A10" &&
        replay.operation == operation &&
        replay.requestId == requestId &&
        replay.requestDigest == requestDigest &&
        replay.transactionId == expected.transactionId &&
        replay.packageName == expected.packageName &&
        replay.userId == expected.userId &&
        replay.generation == expected.generation &&
        replay.canonicalDigest == expected.canonicalDigest &&
        replay.resourcePayloadDigest == expected.resourcePayloadDigest &&
        replay.projectionDigest == expected.projectionDigest &&
        replay.projectionState == expected.projectionState &&
        replay.tokenState == expected.tokenState &&
        replay.verdict == expected.verdict &&
        outbox.GetIntent(requestId, &storedIntent) &&
        storedIntent == expectedIntent;
}

}  // namespace

BmsProjectionCoordinatorV1::BmsProjectionCoordinatorV1(
    BmsProjectionPolicyV1 policy, ProjectionOutboxV1* outbox,
    BmsProjectionAdapterV1* adapter, PublicationTokenStoreV1* tokenStore)
    : policy_(std::move(policy)),
      outbox_(outbox),
      adapter_(adapter),
      tokenStore_(tokenStore)
{
}

ProjectionReceiptV1 BmsProjectionCoordinatorV1::Prepare(
    const CommandEnvelopeV1& envelope,
    const P4CandidateFixtureV1& candidate,
    const ResourceProjectionReadyReceiptV1& resourceReceipt,
    ProjectionFaultInjector* faultInjector)
{
    ProjectionReceiptV1 receipt = BaseReceipt(envelope, candidate.transactionId,
        candidate.packageName, candidate.userId, candidate.candidateGeneration,
        candidate.canonicalDigest, candidate.resourcePayloadDigest);
    if (outbox_ == nullptr || adapter_ == nullptr || tokenStore_ == nullptr) {
        return Reject(std::move(receipt), ProjectionVerdict::INVALID_REQUEST,
            "required seam is null");
    }
    if (envelope.schemaVersion != 1 || policy_.schemaVersion != 1 ||
        !IsLowerHexDigest(policy_.expectedCallerScopeDigest) ||
        !IsLowerHexDigest(envelope.callerScopeDigest) ||
        !IsSafeIdentifier(policy_.policyVersion, false) ||
        !IsSafeIdentifier(envelope.policyVersion, false) ||
        envelope.policyVersion != policy_.policyVersion ||
        !IsSafeIdentifier(envelope.requestId, false) ||
        !IsSafeIdentifier(candidate.transactionId, false) ||
        !IsSafeIdentifier(candidate.packageName, true) ||
        candidate.candidateGeneration == 0 ||
        candidate.recordVersion == 0 ||
        candidate.canonicalCandidateState != "DURABLE" ||
        candidate.projectionState != ProjectionState::NONE ||
        candidate.tokenState != PublicationTokenState::PREPARED ||
        !IsLowerHexDigest(candidate.canonicalDigest) ||
        !IsLowerHexDigest(candidate.resourcePayloadDigest) ||
        !IsLowerHexDigest(candidate.componentFactsDigest) ||
        !IsLowerHexDigest(candidate.managedPathDigest)) {
        return Reject(std::move(receipt), ProjectionVerdict::INVALID_REQUEST,
            "invalid P4 candidate envelope");
    }
    if (candidate.userId != 0) {
        return Reject(std::move(receipt),
            ProjectionVerdict::NOT_SUPPORTED_USER,
            "v1 only supports primary user");
    }
    if (envelope.callerScopeDigest !=
        policy_.expectedCallerScopeDigest) {
        return Reject(std::move(receipt),
            ProjectionVerdict::CALLER_SCOPE_MISMATCH,
            "caller scope digest mismatch");
    }
    if (resourceReceipt.transactionId != candidate.transactionId) {
        return Reject(std::move(receipt),
            ProjectionVerdict::TRANSACTION_MISMATCH,
            "A08 READY receipt transaction owner mismatch");
    }
    if (!ResourceMatches(resourceReceipt, candidate.packageName,
            candidate.userId, candidate.candidateGeneration,
            candidate.transactionId, candidate.canonicalDigest,
            candidate.resourcePayloadDigest)) {
        return Reject(std::move(receipt),
            ProjectionVerdict::RESOURCE_RECEIPT_MISMATCH,
            "A08 READY receipt identity/digest mismatch");
    }
    const std::string requestPayload =
        PrepareRequestPayload(envelope, candidate, resourceReceipt);
    const std::string requestDigest = Sha256Hex(requestPayload);
    const std::string intent =
        DurableIntent("PREPARE", requestDigest, requestPayload);
    receipt.operation = "PREPARE";
    receipt.requestDigest = requestDigest;
    ProjectionReceiptV1 replay;
    if (outbox_->GetReceipt(envelope.requestId, &replay)) {
        HostProjectionRuntimeV1 replayRuntime;
        const bool runtimeMatches =
            adapter_->Read(candidate.packageName, candidate.userId,
                candidate.candidateGeneration, &replayRuntime) ==
                BackendResult::OK &&
            replayRuntime.payload.packageName == candidate.packageName &&
            replayRuntime.payload.userId == candidate.userId &&
            replayRuntime.payload.generation ==
                candidate.candidateGeneration &&
            replayRuntime.payload.canonicalDigest ==
                candidate.canonicalDigest &&
            replayRuntime.payload.resourcePayloadDigest ==
                candidate.resourcePayloadDigest &&
            replayRuntime.payload.componentFactsDigest ==
                candidate.componentFactsDigest &&
            replayRuntime.payload.managedPathDigest ==
                candidate.managedPathDigest &&
            IsLowerHexDigest(replayRuntime.projectionDigest) &&
            (replayRuntime.state == ProjectionState::PREPARED ||
                replayRuntime.state == ProjectionState::ACTIVE);
        ProjectionReceiptV1 expected = receipt;
        expected.projectionDigest =
            runtimeMatches ? replayRuntime.projectionDigest : "";
        expected.projectionState = ProjectionState::PREPARED;
        expected.tokenState = PublicationTokenState::PREPARED;
        expected.verdict = ProjectionVerdict::PREPARED;
        if (ClosedReplayMatches(*outbox_, envelope.requestId, "PREPARE",
                requestDigest, intent, expected, replay) &&
            runtimeMatches) {
            return replay;
        }
        return Reject(std::move(receipt),
            ProjectionVerdict::IDEMPOTENCY_CONFLICT,
            "requestId is bound to a different operation or input");
    }
    std::string storedIntent;
    if (outbox_->GetIntent(envelope.requestId, &storedIntent)) {
        if (storedIntent != intent) {
            return Reject(std::move(receipt),
                ProjectionVerdict::IDEMPOTENCY_CONFLICT,
                "requestId has a different durable prepare intent");
        }
    } else if (!outbox_->PutIntent(envelope.requestId, intent)) {
        if (outbox_->GetIntent(envelope.requestId, &storedIntent) &&
            storedIntent != intent) {
            return Reject(std::move(receipt),
                ProjectionVerdict::IDEMPOTENCY_CONFLICT,
                "requestId raced with a different durable intent");
        }
        return Reject(std::move(receipt), ProjectionVerdict::IO_ERROR,
            "prepare intent durable write failed");
    }
    PublicationTokenState tokenState;
    if (!tokenStore_->Read(candidate.packageName, candidate.userId,
            candidate.candidateGeneration, &tokenState) ||
        tokenState != PublicationTokenState::PREPARED) {
        return Reject(std::move(receipt), ProjectionVerdict::DIGEST_MISMATCH,
            "P4 token precondition mismatch");
    }
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::AFTER_INTENT_DURABLE)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted after prepare intent durable");
    }

    HostIdentityV1 identity;
    const BackendResult allocation = adapter_->AllocateIdentity(
        candidate.packageName, candidate.userId,
        candidate.candidateGeneration, candidate.transactionId, &identity);
    if (allocation != BackendResult::OK) {
        return Reject(std::move(receipt), BackendVerdict(allocation),
            "host identity allocation failed");
    }

    HostProjectionPayloadV1 payload;
    payload.packageName = candidate.packageName;
    payload.userId = candidate.userId;
    payload.generation = candidate.candidateGeneration;
    payload.hostIdentity = identity;
    payload.canonicalDigest = candidate.canonicalDigest;
    payload.resourcePayloadDigest = candidate.resourcePayloadDigest;
    payload.componentFactsDigest = candidate.componentFactsDigest;
    payload.managedPathDigest = candidate.managedPathDigest;

    HostProjectionRuntimeV1 expected;
    expected.payload = payload;
    expected.projectionDigest = ProjectionDigest(payload);
    expected.state = ProjectionState::PREPARED;
    HostProjectionRuntimeV1 createReadback;
    const BackendResult create = adapter_->CreatePrepared(
        expected, candidate.transactionId, &createReadback);
    if (create != BackendResult::OK) {
        return Reject(std::move(receipt), BackendVerdict(create),
            "host PREPARED create failed");
    }
    receipt.projectionDigest = expected.projectionDigest;
    receipt.projectionState = ProjectionState::PREPARED;
    receipt.tokenState = PublicationTokenState::PREPARED;
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::AFTER_PREPARED_DURABLE)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted after PREPARED durable");
    }
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::BEFORE_PREPARED_READBACK)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted before PREPARED readback");
    }
    HostProjectionRuntimeV1 readback;
    const BackendResult read = adapter_->Read(candidate.packageName,
        candidate.userId, candidate.candidateGeneration, &readback);
    if (read != BackendResult::OK ||
        !SameRuntime(expected, createReadback) ||
        !SameRuntime(expected, readback)) {
        adapter_->RemovePrepared(candidate.packageName, candidate.userId,
            candidate.candidateGeneration, candidate.transactionId);
        receipt.projectionState = ProjectionState::NONE;
        return Reject(std::move(receipt),
            ProjectionVerdict::READBACK_MISMATCH,
            "PREPARED readback did not match immutable payload");
    }
    receipt.verdict = ProjectionVerdict::PREPARED;
    receipt.reason = "same-generation PREPARED projection read back";
    if (!outbox_->PutReceipt(envelope.requestId, receipt)) {
        return Reject(std::move(receipt), ProjectionVerdict::IO_ERROR,
            "prepare receipt durable write failed");
    }
    return receipt;
}

ProjectionReceiptV1 BmsProjectionCoordinatorV1::Activate(
    const CommandEnvelopeV1& envelope,
    const PostP5ActivationFixtureV1& fixture,
    const ResourceProjectionReadyReceiptV1& resourceReceipt,
    ProjectionFaultInjector* faultInjector)
{
    ProjectionReceiptV1 receipt = BaseReceipt(envelope, fixture.transactionId,
        fixture.packageName, fixture.userId, fixture.generation,
        fixture.canonicalDigest, fixture.resourcePayloadDigest);
    receipt.projectionDigest = fixture.projectionDigest;
    receipt.projectionState = ProjectionState::PREPARED;
    receipt.tokenState = fixture.tokenState;
    if (outbox_ == nullptr || adapter_ == nullptr || tokenStore_ == nullptr) {
        return Reject(std::move(receipt), ProjectionVerdict::INVALID_REQUEST,
            "required seam is null");
    }
    if (envelope.schemaVersion != 1 || policy_.schemaVersion != 1 ||
        !IsLowerHexDigest(policy_.expectedCallerScopeDigest) ||
        !IsLowerHexDigest(envelope.callerScopeDigest) ||
        !IsSafeIdentifier(policy_.policyVersion, false) ||
        !IsSafeIdentifier(envelope.policyVersion, false) ||
        envelope.policyVersion != policy_.policyVersion ||
        !IsSafeIdentifier(envelope.requestId, false) ||
        !IsSafeIdentifier(fixture.transactionId, false) ||
        !IsSafeIdentifier(fixture.packageName, true) ||
        fixture.generation == 0 || fixture.recordVersion == 0 ||
        fixture.canonicalState != "ACTIVE" ||
        fixture.projectionState != ProjectionState::PREPARED ||
        fixture.tokenState != PublicationTokenState::CANONICAL_SELECTED ||
        !IsLowerHexDigest(fixture.canonicalDigest) ||
        !IsLowerHexDigest(fixture.projectionDigest) ||
        !IsLowerHexDigest(fixture.resourcePayloadDigest)) {
        return Reject(std::move(receipt), ProjectionVerdict::INVALID_REQUEST,
            "invalid post-P5 activation envelope");
    }
    if (fixture.userId != 0) {
        return Reject(std::move(receipt),
            ProjectionVerdict::NOT_SUPPORTED_USER,
            "v1 only supports primary user");
    }
    if (envelope.callerScopeDigest !=
        policy_.expectedCallerScopeDigest) {
        return Reject(std::move(receipt),
            ProjectionVerdict::CALLER_SCOPE_MISMATCH,
            "caller scope digest mismatch");
    }
    if (resourceReceipt.transactionId != fixture.transactionId) {
        return Reject(std::move(receipt),
            ProjectionVerdict::TRANSACTION_MISMATCH,
            "A08 READY receipt transaction owner mismatch");
    }
    if (!ResourceMatches(resourceReceipt, fixture.packageName, fixture.userId,
            fixture.generation, fixture.transactionId,
            fixture.canonicalDigest,
            fixture.resourcePayloadDigest)) {
        return Reject(std::move(receipt),
            ProjectionVerdict::RESOURCE_RECEIPT_MISMATCH,
            "A08 READY receipt identity/digest mismatch");
    }
    const std::string requestPayload =
        ActivationRequestPayload(envelope, fixture, resourceReceipt);
    const std::string requestDigest = Sha256Hex(requestPayload);
    const std::string intent =
        DurableIntent("ACTIVATE", requestDigest, requestPayload);
    receipt.operation = "ACTIVATE";
    receipt.requestDigest = requestDigest;
    ProjectionReceiptV1 replay;
    if (outbox_->GetReceipt(envelope.requestId, &replay)) {
        ProjectionReceiptV1 expected = receipt;
        expected.projectionState = ProjectionState::ACTIVE;
        expected.tokenState = PublicationTokenState::EXTERNAL_READY;
        expected.verdict = ProjectionVerdict::ACTIVATED;
        if (ClosedReplayMatches(*outbox_, envelope.requestId, "ACTIVATE",
                requestDigest, intent, expected, replay)) {
            return replay;
        }
        return Reject(std::move(receipt),
            ProjectionVerdict::IDEMPOTENCY_CONFLICT,
            "requestId is bound to a different operation or input");
    }
    std::string storedIntent;
    if (outbox_->GetIntent(envelope.requestId, &storedIntent)) {
        if (storedIntent != intent) {
            return Reject(std::move(receipt),
                ProjectionVerdict::IDEMPOTENCY_CONFLICT,
                "requestId has a different durable activation intent");
        }
    } else if (!outbox_->PutIntent(envelope.requestId, intent)) {
        if (outbox_->GetIntent(envelope.requestId, &storedIntent) &&
            storedIntent != intent) {
            return Reject(std::move(receipt),
                ProjectionVerdict::IDEMPOTENCY_CONFLICT,
                "requestId raced with a different durable intent");
        }
        return Reject(std::move(receipt), ProjectionVerdict::IO_ERROR,
            "activation intent durable write failed");
    }

    HostProjectionRuntimeV1 before;
    if (adapter_->Read(fixture.packageName, fixture.userId, fixture.generation,
            &before) != BackendResult::OK) {
        return Reject(std::move(receipt), ProjectionVerdict::GENERATION_MISMATCH,
            "expected PREPARED generation is absent");
    }
    if (before.payload.generation != fixture.generation) {
        return Reject(std::move(receipt), ProjectionVerdict::GENERATION_MISMATCH,
            "PREPARED generation mismatch");
    }
    if (before.payload.canonicalDigest != fixture.canonicalDigest ||
        before.payload.resourcePayloadDigest !=
            fixture.resourcePayloadDigest ||
        before.projectionDigest != fixture.projectionDigest) {
        return Reject(std::move(receipt), ProjectionVerdict::DIGEST_MISMATCH,
            "PREPARED digest join mismatch");
    }
    if (before.state != ProjectionState::PREPARED &&
        before.state != ProjectionState::ACTIVE) {
        return Reject(std::move(receipt), ProjectionVerdict::DIGEST_MISMATCH,
            "projection is neither PREPARED nor recoverable ACTIVE");
    }

    PublicationTokenState actualToken;
    if (!tokenStore_->Read(fixture.packageName, fixture.userId,
            fixture.generation, &actualToken) ||
        (actualToken != PublicationTokenState::CANONICAL_SELECTED &&
            actualToken != PublicationTokenState::EXTERNAL_READY)) {
        return Reject(std::move(receipt),
            ProjectionVerdict::ACTIVATION_NOT_AUTHORIZED,
            "activation requires post-P5 CANONICAL_SELECTED token");
    }
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::AFTER_ACTIVATION_INTENT_DURABLE)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted after activation intent durable");
    }

    HostProjectionRuntimeV1 activeReadback;
    const BackendResult activation = adapter_->Activate(fixture.packageName,
        fixture.userId, fixture.generation, fixture.canonicalDigest,
        fixture.projectionDigest, fixture.transactionId, &activeReadback);
    if (activation != BackendResult::OK) {
        return Reject(std::move(receipt), BackendVerdict(activation),
            "host activation failed");
    }
    if (activeReadback.state != ProjectionState::ACTIVE ||
        activeReadback.projectionDigest != fixture.projectionDigest ||
        activeReadback.payload.canonicalDigest != fixture.canonicalDigest ||
        activeReadback.payload.resourcePayloadDigest !=
            fixture.resourcePayloadDigest) {
        return Reject(std::move(receipt),
            ProjectionVerdict::READBACK_MISMATCH,
            "ACTIVE readback did not match expected digests");
    }
    receipt.projectionState = ProjectionState::ACTIVE;
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::AFTER_ACTIVE_DURABLE)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted after ACTIVE durable");
    }
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::BEFORE_TOKEN_CAS)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted before EXTERNAL_READY CAS");
    }

    if (actualToken == PublicationTokenState::CANONICAL_SELECTED &&
        !tokenStore_->CompareAndSwap(fixture.packageName, fixture.userId,
            fixture.generation, PublicationTokenState::CANONICAL_SELECTED,
            PublicationTokenState::EXTERNAL_READY)) {
        PublicationTokenState observed;
        if (!tokenStore_->Read(fixture.packageName, fixture.userId,
                fixture.generation, &observed) ||
            observed != PublicationTokenState::EXTERNAL_READY) {
            return Reject(std::move(receipt),
                ProjectionVerdict::TOKEN_CAS_FAILED,
                "CANONICAL_SELECTED to EXTERNAL_READY CAS failed");
        }
    }
    receipt.tokenState = PublicationTokenState::EXTERNAL_READY;
    if (Interrupted(faultInjector,
            ProjectionFaultPhase::AFTER_TOKEN_CAS)) {
        return Reject(std::move(receipt), ProjectionVerdict::INTERRUPTED,
            "interrupted after EXTERNAL_READY CAS");
    }
    receipt.verdict = ProjectionVerdict::ACTIVATED;
    receipt.reason =
        actualToken == PublicationTokenState::EXTERNAL_READY
        ? "forward recovery observed ACTIVE plus EXTERNAL_READY"
        : "ACTIVE readback verified before EXTERNAL_READY CAS";
    if (!outbox_->PutReceipt(envelope.requestId, receipt)) {
        return Reject(std::move(receipt), ProjectionVerdict::IO_ERROR,
            "activation receipt durable write failed");
    }
    return receipt;
}

std::string BmsProjectionCoordinatorV1::CanonicalPayload(
    const HostProjectionPayloadV1& payload)
{
    // RFC 8785 key order; all v1 fields are present and implementation-private
    // data, projectionDigest, and mutable state are intentionally excluded.
    std::ostringstream output;
    output << "{\"accessTokenId\":" << payload.hostIdentity.accessTokenId
           << ",\"appId\":\"" << JsonEscape(payload.hostIdentity.appId)
           << "\",\"bundleName\":\""
           << JsonEscape(payload.hostIdentity.bundleName)
           << "\",\"canonicalDigest\":\"" << payload.canonicalDigest
           << "\",\"componentFactsDigest\":\""
           << payload.componentFactsDigest
           << "\",\"generation\":" << payload.generation
           << ",\"managedPathDigest\":\"" << payload.managedPathDigest
           << "\",\"packageName\":\"" << JsonEscape(payload.packageName)
           << "\",\"resourcePayloadDigest\":\""
           << payload.resourcePayloadDigest
           << "\",\"schemaVersion\":" << payload.schemaVersion
           << ",\"uid\":" << payload.hostIdentity.uid
           << ",\"userId\":" << payload.userId << "}";
    return output.str();
}

std::string BmsProjectionCoordinatorV1::ProjectionDigest(
    const HostProjectionPayloadV1& payload)
{
    return Sha256Hex(CanonicalPayload(payload));
}

std::string BmsProjectionCoordinatorV1::SerializeReceipt(
    const ProjectionReceiptV1& receipt)
{
    std::ostringstream output;
    output << "{\"schemaVersion\":" << receipt.schemaVersion
           << ",\"actionId\":\"" << JsonEscape(receipt.actionId) << "\","
           << "\"operation\":\"" << JsonEscape(receipt.operation)
           << "\",\"requestId\":\"" << JsonEscape(receipt.requestId)
           << "\",\"requestDigest\":\"" << receipt.requestDigest
           << "\",\"transactionId\":\""
           << JsonEscape(receipt.transactionId)
           << "\",\"packageName\":\"" << JsonEscape(receipt.packageName)
           << "\",\"userId\":" << receipt.userId
           << ",\"generation\":" << receipt.generation
           << ",\"canonicalDigest\":\"" << receipt.canonicalDigest
           << "\",\"resourcePayloadDigest\":\""
           << receipt.resourcePayloadDigest
           << "\",\"projectionDigest\":\"" << receipt.projectionDigest
           << "\",\"projectionState\":\""
           << ProjectionStateName(receipt.projectionState)
           << "\",\"tokenState\":\"" << TokenStateName(receipt.tokenState)
           << "\",\"verdict\":\"" << VerdictName(receipt.verdict)
           << "\",\"reason\":\"" << JsonEscape(receipt.reason) << "\"}";
    return output.str();
}

const char* BmsProjectionCoordinatorV1::VerdictName(
    ProjectionVerdict verdict)
{
    switch (verdict) {
        case ProjectionVerdict::PREPARED: return "PREPARED";
        case ProjectionVerdict::ACTIVATED: return "ACTIVATED";
        case ProjectionVerdict::REPLAYED: return "REPLAYED";
        case ProjectionVerdict::INVALID_REQUEST: return "INVALID_REQUEST";
        case ProjectionVerdict::NOT_SUPPORTED_USER:
            return "NOT_SUPPORTED_USER";
        case ProjectionVerdict::CALLER_SCOPE_MISMATCH:
            return "CALLER_SCOPE_MISMATCH";
        case ProjectionVerdict::RESOURCE_RECEIPT_MISMATCH:
            return "RESOURCE_RECEIPT_MISMATCH";
        case ProjectionVerdict::TRANSACTION_MISMATCH:
            return "TRANSACTION_MISMATCH";
        case ProjectionVerdict::GENERATION_MISMATCH:
            return "GENERATION_MISMATCH";
        case ProjectionVerdict::DIGEST_MISMATCH:
            return "DIGEST_MISMATCH";
        case ProjectionVerdict::IDEMPOTENCY_CONFLICT:
            return "IDEMPOTENCY_CONFLICT";
        case ProjectionVerdict::HOST_COLLISION: return "HOST_COLLISION";
        case ProjectionVerdict::HOST_DENIED: return "HOST_DENIED";
        case ProjectionVerdict::UNSUPPORTED_FIELD:
            return "UNSUPPORTED_FIELD";
        case ProjectionVerdict::ACTIVATION_NOT_AUTHORIZED:
            return "ACTIVATION_NOT_AUTHORIZED";
        case ProjectionVerdict::READBACK_MISMATCH:
            return "READBACK_MISMATCH";
        case ProjectionVerdict::TOKEN_CAS_FAILED:
            return "TOKEN_CAS_FAILED";
        case ProjectionVerdict::IO_ERROR: return "IO_ERROR";
        case ProjectionVerdict::INTERRUPTED: return "INTERRUPTED";
    }
    return "INVALID_REQUEST";
}

const char* BmsProjectionCoordinatorV1::ProjectionStateName(
    ProjectionState state)
{
    switch (state) {
        case ProjectionState::NONE: return "NONE";
        case ProjectionState::PREPARED: return "PREPARED";
        case ProjectionState::ACTIVE: return "ACTIVE";
    }
    return "NONE";
}

const char* BmsProjectionCoordinatorV1::TokenStateName(
    PublicationTokenState state)
{
    switch (state) {
        case PublicationTokenState::PREPARED: return "PREPARED";
        case PublicationTokenState::CANONICAL_SELECTED:
            return "CANONICAL_SELECTED";
        case PublicationTokenState::EXTERNAL_READY:
            return "EXTERNAL_READY";
    }
    return "PREPARED";
}

}  // namespace oh_adapter::bms_projection
