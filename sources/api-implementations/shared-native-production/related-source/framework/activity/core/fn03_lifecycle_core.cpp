#include "fn03_lifecycle_core.h"

#include <algorithm>
#include <cctype>
#include <functional>
#include <sstream>
#include <utility>

namespace oh_adapter::fn03 {

OhTarget OhTargetFromWireState(int32_t wireState)
{
    switch (wireState) {
        case 0:
            return OhTarget::kInitial;
        case 1:
            return OhTarget::kInactive;
        case 5:
            return OhTarget::kForeground;
        case 6:
            return OhTarget::kBackground;
        default:
            return OhTarget::kUnknown;
    }
}

namespace {

Result MakeResult(Code code, std::string reason,
                  std::string operationId = {}, bool emitted = false)
{
    return Result{code, std::move(reason), std::move(operationId), emitted};
}

std::string Join(const std::vector<std::string>& values)
{
    std::ostringstream stream;
    for (size_t index = 0; index < values.size(); ++index) {
        if (index != 0) {
            stream << ',';
        }
        stream << values[index];
    }
    return stream.str();
}

bool ActionAllows(const LifecycleRequest& request)
{
    if (request.actionId == "Fn03.A01") {
        return request.source == ActivityState::kRegistered &&
               request.target == OhTarget::kLaunch;
    }
    if (request.actionId == "Fn03.A02") {
        return request.target == OhTarget::kForeground &&
               (request.source == ActivityState::kCreated ||
                request.source == ActivityState::kPaused ||
                request.source == ActivityState::kStopped);
    }
    if (request.actionId == "Fn03.A03") {
        return request.source == ActivityState::kResumed &&
               request.target == OhTarget::kForeground;
    }
    if (request.actionId == "Fn03.A04") {
        return request.source == ActivityState::kPaused &&
               request.target == OhTarget::kBackground;
    }
    return false;
}

bool SameLifecycleRequest(const LifecycleRequest& left,
                          const LifecycleRequest& right)
{
    return left.actionId == right.actionId && left.key == right.key &&
           left.transitionId == right.transitionId &&
           left.source == right.source && left.target == right.target &&
           left.mappingVersion == right.mappingVersion &&
           left.requireFirstFrame == right.requireFirstFrame &&
           left.queuedAtMs == right.queuedAtMs;
}

bool IsSha256(const std::string& value)
{
    return value.size() == 64 &&
           std::all_of(value.begin(), value.end(), [](unsigned char byte) {
               return std::isxdigit(byte) != 0;
           });
}

bool FirstFrameTimeoutElapsed(int64_t createdAtMs, int64_t nowMs)
{
    if (nowMs < createdAtMs) {
        return false;
    }
    return static_cast<uint64_t>(nowMs) -
               static_cast<uint64_t>(createdAtMs) >=
           static_cast<uint64_t>(kPolicyTimeoutMs);
}

}  // namespace

bool ActivityKey::operator==(const ActivityKey& other) const
{
    return owner == other.owner && processEpoch == other.processEpoch &&
           generation == other.generation && tokenHandle == other.tokenHandle;
}

bool ActivityKey::IsValid() const
{
    return !owner.empty() && processEpoch != 0 && generation != 0 &&
           tokenHandle != 0;
}

std::string ActivityKey::StableString() const
{
    return owner + ":" + std::to_string(processEpoch) + ":" +
           std::to_string(generation) + ":" + std::to_string(tokenHandle);
}

size_t ActivityKeyHash::operator()(const ActivityKey& key) const
{
    return std::hash<std::string>{}(key.StableString());
}

MappingDecision DecideMapping(ActivityState source, OhTarget target,
                              const std::string& mappingVersion,
                              bool requireFirstFrame,
                              const std::string& ingress)
{
    if (mappingVersion != kMappingVersion) {
        return {Code::kRejected, "WRONG_MAPPING_VERSION", {}, {}, {}, false};
    }
    if (target == OhTarget::kInactive) {
        return {Code::kRejected, "UNSUPPORTED_OH_STAGE_STATE", {}, {}, {},
                false};
    }
    MappingDecision decision;
    decision.code = Code::kAccepted;
    decision.reason = "MAPPED";
    decision.requireFirstFrame = requireFirstFrame;

    if (source == ActivityState::kRegistered && target == OhTarget::kLaunch) {
        decision.transactions = {"LaunchActivityItem"};
        decision.callbacks = {"onCreate"};
        decision.requiredReceipts = {"CREATE_TERMINAL"};
    } else if (source == ActivityState::kCreated &&
               target == OhTarget::kForeground) {
        decision.transactions = {"ResumeActivityItem"};
        decision.callbacks = {"onStart", "onResume"};
        decision.requiredReceipts = {"RESUME_TERMINAL"};
    } else if (source == ActivityState::kPaused &&
               target == OhTarget::kForeground) {
        decision.transactions = {"ResumeActivityItem"};
        decision.callbacks = {"onResume"};
        decision.requiredReceipts = {"RESUME_TERMINAL"};
    } else if (source == ActivityState::kStopped &&
               target == OhTarget::kForeground) {
        decision.transactions = {"ResumeActivityItem"};
        decision.callbacks = {"onRestart", "onStart", "onResume"};
        decision.requiredReceipts = {"RESUME_TERMINAL"};
    } else if (source == ActivityState::kResumed &&
               target == OhTarget::kForeground) {
        decision.transactions = {"PauseActivityItem"};
        decision.callbacks = {"onPause"};
        decision.requiredReceipts = {"PAUSE_TERMINAL"};
        decision.requireFirstFrame = false;
    } else if (source == ActivityState::kResumed &&
               target == OhTarget::kBackground) {
        decision.transactions = {"PauseActivityItem", "StopActivityItem"};
        decision.callbacks = {"onPause", "onStop"};
        decision.requiredReceipts = {"PAUSE_TERMINAL", "STOP_TERMINAL"};
        decision.requireFirstFrame = false;
    } else if (source == ActivityState::kPaused &&
               target == OhTarget::kBackground) {
        decision.transactions = {"StopActivityItem"};
        decision.callbacks = {"onStop"};
        decision.requiredReceipts = {"STOP_TERMINAL"};
        decision.requireFirstFrame = false;
    } else if (source == ActivityState::kFinishRequested &&
               target == OhTarget::kInitial) {
        decision.transactions = {"DestroyActivityItem"};
        decision.callbacks = {"onDestroy"};
        decision.requiredReceipts = {"HOST_TERMINATE_ACCEPTED",
                                     "ANDROID_DESTROYED",
                                     "OH_CLEAN_OR_DEATH"};
        decision.requireFirstFrame = false;
    } else if (target == OhTarget::kInitial &&
               ingress == "ANDROID_FINISH" &&
               (source == ActivityState::kResumed ||
                source == ActivityState::kPaused ||
                source == ActivityState::kStopped)) {
        return {Code::kRejected, "UNSUPPORTED_ANDROID_FINISH_SOURCE_STATE_V1",
                {}, {}, {}, false};
    } else if (source == ActivityState::kStopped &&
               target == OhTarget::kInitial && ingress == "OH_INITIATED") {
        return {Code::kRejected, "UNSUPPORTED_OH_INITIATED_TERMINATION_V1",
                {}, {}, {}, false};
    } else {
        return {Code::kRejected, "REJECT_UNSUPPORTED_STATE_BEFORE_CALLBACK",
                {}, {}, {}, false};
    }
    if (decision.requireFirstFrame) {
        decision.requiredReceipts.push_back("FOREGROUND_READY");
    }
    return decision;
}

std::string TokenRegistry::NonceKey(const TokenRegistryRequest& request)
{
    return request.owner + ":" + std::to_string(request.processEpoch) + ":" +
           std::to_string(request.generation) + ":" + request.nonce;
}

std::string TokenRegistry::OperationKey(const TokenRegistryRequest& request)
{
    return std::to_string(static_cast<int>(request.op)) + ":" +
           NonceKey(request);
}

bool TokenRegistry::SamePayload(const Entry& entry,
                                const TokenRegistryRequest& request)
{
    return entry.owner == request.owner &&
           entry.processEpoch == request.processEpoch &&
           entry.generation == request.generation &&
           entry.nonce == request.nonce &&
           entry.ohToken == request.ohToken &&
           entry.androidToken == request.androidToken;
}

bool TokenRegistry::SameOperation(const TokenRegistryRequest& left,
                                  const TokenRegistryRequest& right)
{
    return left.op == right.op && left.owner == right.owner &&
           left.processEpoch == right.processEpoch &&
           left.generation == right.generation &&
           left.nonce == right.nonce && left.ohToken == right.ohToken &&
           left.androidToken == right.androidToken &&
           left.capabilityHandle == right.capabilityHandle;
}

bool TokenRegistry::Authorized(const Entry& entry,
                               const TokenRegistryRequest& request) const
{
    return entry.owner == request.owner &&
           entry.processEpoch == request.processEpoch &&
           entry.generation == request.generation;
}

TokenRegistryReceipt TokenRegistry::Apply(const TokenRegistryRequest& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (request.owner.empty() || request.processEpoch == 0 ||
        request.generation == 0 || request.nonce.empty()) {
        return {Code::kRejected, "INVALID_REGISTRY_IDENTITY", 0, {}, {}};
    }
    const std::string operationKey = OperationKey(request);
    const auto oldOperation = operations_.find(operationKey);
    if (oldOperation != operations_.end()) {
        if (!SameOperation(oldOperation->second.first, request)) {
            return {Code::kRejected, "NONCE_PAYLOAD_CONFLICT", 0, {}, {}};
        }
        TokenRegistryReceipt replay = oldOperation->second.second;
        if (request.op != RegistryOp::kRevoke &&
            tombstones_.count(replay.capabilityHandle) != 0) {
            return {Code::kRejected, "REVOKED_CAPABILITY",
                    replay.capabilityHandle, {},
                    tombstones_.at(replay.capabilityHandle)};
        }
        replay.code = Code::kDuplicate;
        switch (request.op) {
            case RegistryOp::kRegister:
                replay.reason = "REGISTER_REPLAY";
                break;
            case RegistryOp::kResolveForward:
                replay.reason = "RESOLVE_FORWARD_REPLAY";
                break;
            case RegistryOp::kResolveReverse:
                replay.reason = "RESOLVE_REVERSE_REPLAY";
                break;
            case RegistryOp::kRevoke:
                replay.reason = "REVOKE_REPLAY";
                break;
        }
        return replay;
    }
    const auto remember = [&](TokenRegistryReceipt receipt) {
        operations_.emplace(operationKey,
                            std::make_pair(request, receipt));
        return receipt;
    };
    if (request.op == RegistryOp::kRegister) {
        if (request.ohToken.empty() || request.androidToken.empty()) {
            return {Code::kRejected, "MISSING_TOKEN_PAIR", 0, {}, {}};
        }
        const std::string nonceKey = NonceKey(request);
        const auto nonce = nonceToHandle_.find(nonceKey);
        if (nonce != nonceToHandle_.end()) {
            const auto entry = byHandle_.find(nonce->second);
            if (entry != byHandle_.end() && SamePayload(entry->second, request)) {
                return {Code::kDuplicate, "REGISTER_REPLAY",
                        entry->second.handle, {}, {}};
            }
            return {Code::kRejected, "NONCE_PAYLOAD_CONFLICT", 0, {}, {}};
        }
        if (byOhToken_.count(request.ohToken) != 0 ||
            byAndroidToken_.count(request.androidToken) != 0) {
            return {Code::kRejected, "TOKEN_ALREADY_REGISTERED", 0, {}, {}};
        }
        const uint64_t handle = nextHandle_++;
        Entry entry{request.owner, request.processEpoch, request.generation,
                    request.nonce, request.ohToken, request.androidToken,
                    handle};
        byHandle_.emplace(handle, entry);
        byOhToken_.emplace(entry.ohToken, handle);
        byAndroidToken_.emplace(entry.androidToken, handle);
        nonceToHandle_.emplace(nonceKey, handle);
        return remember(
            {Code::kAccepted, "REGISTERED", handle, {}, {}});
    }

    const auto found = byHandle_.find(request.capabilityHandle);
    if (found == byHandle_.end()) {
        if (tombstones_.count(request.capabilityHandle) != 0) {
            return {Code::kRejected, "REVOKED_CAPABILITY",
                    request.capabilityHandle, {},
                    tombstones_.at(request.capabilityHandle)};
        }
        return {Code::kRejected, "UNKNOWN_CAPABILITY", 0, {}, {}};
    }
    if (!Authorized(found->second, request)) {
        return {Code::kRejected, "CAPABILITY_OWNER_OR_GENERATION_MISMATCH",
                0, {}, {}};
    }
    const Entry entry = found->second;
    if (request.op == RegistryOp::kResolveForward) {
        return remember({Code::kAccepted, "RESOLVED_FORWARD", entry.handle,
                         entry.androidToken, {}});
    }
    if (request.op == RegistryOp::kResolveReverse) {
        return remember({Code::kAccepted, "RESOLVED_REVERSE", entry.handle,
                         entry.ohToken, {}});
    }
    if (request.op == RegistryOp::kRevoke) {
        const std::string tombstone =
            "tombstone:" + std::to_string(entry.handle) + ":" +
            std::to_string(entry.generation);
        byOhToken_.erase(entry.ohToken);
        byAndroidToken_.erase(entry.androidToken);
        byHandle_.erase(found);
        tombstones_[entry.handle] = tombstone;
        return remember(
            {Code::kAccepted, "REVOKED", entry.handle, {}, tombstone});
    }
    return {Code::kRejected, "UNKNOWN_REGISTRY_OPERATION", 0, {}, {}};
}

size_t TokenRegistry::ActiveSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return byHandle_.size();
}

size_t TokenRegistry::TombstoneSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return tombstones_.size();
}

bool ProcessKey::operator==(const ProcessKey& other) const
{
    return packageName == other.packageName &&
           processName == other.processName && userId == other.userId &&
           processEpoch == other.processEpoch;
}

std::string ProcessKey::StableString() const
{
    return packageName + ":" + processName + ":" + std::to_string(userId) +
           ":" + std::to_string(processEpoch);
}

Result BindLaunchGate::BeginBind(const ProcessKey& key,
                                 const std::string& bindId)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (key.packageName.empty() || key.processName.empty() ||
        key.processEpoch == 0 || bindId.empty()) {
        return MakeResult(Code::kRejected, "INVALID_BIND_IDENTITY");
    }
    for (auto pending = pending_.begin(); pending != pending_.end();) {
        const ProcessKey& old = pending->second.process;
        if (old.packageName != key.packageName ||
            old.processName != key.processName || old.userId != key.userId ||
            old.processEpoch == key.processEpoch) {
            ++pending;
            continue;
        }
        failed_[pending->first] = "STALE_PROCESS_EPOCH";
        pending = pending_.erase(pending);
    }
    for (auto& process : processes_) {
        const ProcessKey& old = process.second.key;
        if (old.packageName != key.packageName ||
            old.processName != key.processName || old.userId != key.userId ||
            old.processEpoch == key.processEpoch) {
            continue;
        }
        process.second.state = BindState::kBindFailed;
        for (auto pending = pending_.begin(); pending != pending_.end();) {
            if (!(pending->second.process == old)) {
                ++pending;
                continue;
            }
            failed_[pending->first] = "STALE_PROCESS_EPOCH";
            pending = pending_.erase(pending);
        }
        for (auto admitted = admitted_.begin();
             admitted != admitted_.end();) {
            if (!(admitted->second.process == old)) {
                ++admitted;
                continue;
            }
            failed_[admitted->first] = "STALE_PROCESS_EPOCH";
            admitted = admitted_.erase(admitted);
        }
    }
    auto& record = processes_[key.StableString()];
    record.key = key;
    if (record.state != BindState::kUnbound) {
        if (record.bindId == bindId) {
            return MakeResult(Code::kDuplicate, "BIND_REPLAY", bindId);
        }
        return MakeResult(Code::kRejected, "SECOND_BIND_ID", bindId);
    }
    record.state = BindState::kBinding;
    record.bindId = bindId;
    return MakeResult(Code::kAccepted, "BINDING", bindId);
}

std::string BindLaunchGate::LaunchOperationKey(
    const ProcessKey& process, const LaunchEnvelope& launch)
{
    return process.StableString() + ":" + launch.key.StableString() + ":" +
           launch.launchId;
}

std::string BindLaunchGate::ActivitySlotKey(const LaunchEnvelope& launch)
{
    return launch.key.owner + ":" +
           std::to_string(launch.key.processEpoch) + ":" +
           std::to_string(launch.key.tokenHandle);
}

std::string BindLaunchGate::FailureReason(
    BindBoundaryOutcome outcome, const std::string& detail)
{
    switch (outcome) {
        case BindBoundaryOutcome::kJniUnavailable:
            return "JNI_UNAVAILABLE" + (detail.empty() ? "" : ":" + detail);
        case BindBoundaryOutcome::kJniMethodMissing:
            return "JNI_METHOD_MISSING" +
                   (detail.empty() ? "" : ":" + detail);
        case BindBoundaryOutcome::kJniException:
            return "JNI_EXCEPTION" + (detail.empty() ? "" : ":" + detail);
        case BindBoundaryOutcome::kBinderTransportFailed:
            return "BINDER_TRANSPORT_FAILED" +
                   (detail.empty() ? "" : ":" + detail);
        case BindBoundaryOutcome::kPayloadRejected:
            return "BIND_PAYLOAD_REJECTED" +
                   (detail.empty() ? "" : ":" + detail);
        case BindBoundaryOutcome::kBound:
            return "";
    }
    return "UNKNOWN_BIND_BOUNDARY_FAILURE";
}

BindCompletion BindLaunchGate::CompleteBind(
    const ProcessKey& key, const std::string& bindId,
    BindBoundaryOutcome outcome, const std::string& detail)
{
    std::lock_guard<std::mutex> lock(mutex_);
    BindCompletion completion;
    auto process = processes_.find(key.StableString());
    if (process == processes_.end()) {
        completion.receipt =
            MakeResult(Code::kRejected, "UNKNOWN_BIND", bindId);
        return completion;
    }
    if (process->second.state != BindState::kBinding) {
        if (process->second.bindId != bindId) {
            completion.receipt =
                MakeResult(Code::kRejected, "BIND_ID_MISMATCH", bindId);
        } else if (process->second.hasTerminalReceipt &&
                   process->second.terminalOutcome == outcome &&
                   (outcome == BindBoundaryOutcome::kBound ||
                    process->second.terminalReceipt.reason ==
                        FailureReason(outcome, detail))) {
            completion.receipt = process->second.terminalReceipt;
        } else {
            completion.receipt =
                MakeResult(Code::kRejected, "BIND_TERMINAL_CONFLICT",
                           bindId);
        }
        return completion;
    }
    if (process->second.bindId != bindId) {
        completion.receipt =
            MakeResult(Code::kRejected, "BIND_ID_MISMATCH", bindId);
        return completion;
    }
    const bool success = outcome == BindBoundaryOutcome::kBound;
    process->second.state = success ? BindState::kBound
                                    : BindState::kBindFailed;
    process->second.failureReason = FailureReason(outcome, detail);
    for (auto pending = pending_.begin(); pending != pending_.end();) {
        if (!(pending->second.process == key)) {
            ++pending;
            continue;
        }
        if (success) {
            admitted_[pending->first] = pending->second;
            completion.released.push_back(pending->second.envelope);
        } else {
            failed_[pending->first] = process->second.failureReason;
        }
        pending = pending_.erase(pending);
    }
    completion.receipt =
        MakeResult(success ? Code::kReady : Code::kFailedTyped,
                   success ? "BIND_TERMINAL" : process->second.failureReason,
                   bindId, success);
    process->second.terminalOutcome = outcome;
    process->second.terminalReceipt = completion.receipt;
    process->second.hasTerminalReceipt = true;
    return completion;
}

Result BindLaunchGate::SubmitLaunch(const ProcessKey& process,
                                    const LaunchEnvelope& launch)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (process.packageName.empty() || process.processName.empty() ||
        process.processEpoch == 0 || !launch.key.IsValid() ||
        launch.launchId.empty() ||
        launch.payloadDigest.empty() ||
        launch.key.processEpoch != process.processEpoch) {
        return MakeResult(Code::kRejected, "INVALID_LAUNCH_ENVELOPE",
                          launch.launchId);
    }
    if (launch.key.owner != process.packageName) {
        return MakeResult(Code::kRejected, "OWNER_PROCESS_MISMATCH",
                          launch.launchId);
    }
    const std::string operationKey = LaunchOperationKey(process, launch);
    const std::string activitySlot = ActivitySlotKey(launch);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        launch.key.generation <= retired->second) {
        return MakeResult(Code::kFailedTyped,
                          "RETIRED_ACTIVITY_GENERATION", launch.launchId);
    }
    auto generation = activeGenerations_.find(activitySlot);
    if (generation == activeGenerations_.end()) {
        activeGenerations_[activitySlot] = launch.key.generation;
    } else if (launch.key.generation < generation->second) {
        failed_[operationKey] = "STALE_ACTIVITY_GENERATION";
        return MakeResult(Code::kFailedTyped, "STALE_ACTIVITY_GENERATION",
                          launch.launchId);
    } else if (launch.key.generation > generation->second) {
        for (auto pending = pending_.begin(); pending != pending_.end();) {
            if (ActivitySlotKey(pending->second.envelope) != activitySlot ||
                pending->second.envelope.key.generation ==
                    launch.key.generation) {
                ++pending;
                continue;
            }
            failed_[pending->first] = "STALE_ACTIVITY_GENERATION";
            pending = pending_.erase(pending);
        }
        generation->second = launch.key.generation;
    }
    const auto failed = failed_.find(operationKey);
    if (failed != failed_.end()) {
        return MakeResult(Code::kFailedTyped, failed->second,
                          launch.launchId);
    }
    const auto admitted = admitted_.find(operationKey);
    if (admitted != admitted_.end()) {
        if (admitted->second.envelope.payloadDigest == launch.payloadDigest &&
            admitted->second.envelope.key == launch.key) {
            return MakeResult(Code::kDuplicate, "LAUNCH_REPLAY",
                              launch.launchId);
        }
        return MakeResult(Code::kRejected, "LAUNCH_ID_PAYLOAD_CONFLICT",
                          launch.launchId);
    }
    const auto existing = pending_.find(operationKey);
    if (existing != pending_.end()) {
        if (existing->second.envelope.payloadDigest == launch.payloadDigest &&
            existing->second.envelope.key == launch.key) {
            return MakeResult(Code::kDuplicate, "PENDING_LAUNCH_REPLAY",
                              launch.launchId);
        }
        return MakeResult(Code::kRejected, "LAUNCH_ID_PAYLOAD_CONFLICT",
                          launch.launchId);
    }
    auto& processRecord = processes_[process.StableString()];
    processRecord.key = process;
    if (processRecord.state == BindState::kUnbound ||
        processRecord.state == BindState::kBinding) {
        pending_[operationKey] = PendingLaunch{process, launch};
        return MakeResult(Code::kPending, "QUEUED_AWAITING_BIND",
                          launch.launchId);
    }
    if (processRecord.state == BindState::kBindFailed) {
        const std::string& reason = processRecord.failureReason.empty()
                                        ? std::string("BIND_FAILED")
                                        : processRecord.failureReason;
        return MakeResult(Code::kFailedTyped, reason,
                          launch.launchId);
    }
    admitted_[operationKey] = PendingLaunch{process, launch};
    return MakeResult(Code::kAccepted, "LAUNCH_ADMITTED", launch.launchId,
                      true);
}

Result BindLaunchGate::Retire(const ActivityKey& key)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid()) {
        return MakeResult(Code::kRejected, "INVALID_RETIRE_IDENTITY");
    }
    const std::string activitySlot =
        key.owner + ":" + std::to_string(key.processEpoch) + ":" +
        std::to_string(key.tokenHandle);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kDuplicate,
                          "ACTIVITY_GENERATION_ALREADY_RETIRED");
    }
    retiredGenerations_[activitySlot] = key.generation;
    activeGenerations_.erase(activitySlot);
    for (auto pending = pending_.begin(); pending != pending_.end();) {
        if (ActivitySlotKey(pending->second.envelope) != activitySlot ||
            pending->second.envelope.key.generation > key.generation) {
            ++pending;
            continue;
        }
        failed_[pending->first] = "RETIRED_ACTIVITY_GENERATION";
        pending = pending_.erase(pending);
    }
    for (auto admitted = admitted_.begin(); admitted != admitted_.end();) {
        if (ActivitySlotKey(admitted->second.envelope) != activitySlot ||
            admitted->second.envelope.key.generation > key.generation) {
            ++admitted;
            continue;
        }
        failed_[admitted->first] = "RETIRED_ACTIVITY_GENERATION";
        admitted = admitted_.erase(admitted);
    }
    return MakeResult(Code::kAccepted, "ACTIVITY_GENERATION_RETIRED");
}

std::vector<Result> BindLaunchGate::Expire(int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    std::vector<Result> results;
    for (auto pending = pending_.begin(); pending != pending_.end();) {
        if (nowMs - pending->second.envelope.acceptedAtMs <
            kPolicyTimeoutMs) {
            ++pending;
            continue;
        }
        results.push_back(MakeResult(
            Code::kFailedTyped, "BIND_WAIT_TIMEOUT",
            pending->second.envelope.launchId));
        failed_[pending->first] = "BIND_WAIT_TIMEOUT";
        pending = pending_.erase(pending);
    }
    return results;
}

size_t BindLaunchGate::PendingSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return pending_.size();
}

size_t BindLaunchGate::AdmittedCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return admitted_.size();
}

std::string LifecycleReducer::KeyFor(const LifecycleRequest& request)
{
    return request.actionId + ":" + request.key.StableString() + ":" +
           request.transitionId;
}

std::string LifecycleReducer::ActivitySlotKey(const ActivityKey& key)
{
    return key.owner + ":" + std::to_string(key.processEpoch) + ":" +
           std::to_string(key.tokenHandle);
}

ActivityState LifecycleReducer::CommittedState(
    const LifecycleRequest& request)
{
    if (request.actionId == "Fn03.A01") {
        return ActivityState::kCreated;
    }
    if (request.actionId == "Fn03.A02") {
        return ActivityState::kResumed;
    }
    if (request.actionId == "Fn03.A03") {
        return ActivityState::kPaused;
    }
    return ActivityState::kStopped;
}

Result LifecycleReducer::Queue(const LifecycleRequest& request)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!request.key.IsValid() || request.actionId.empty() ||
        request.transitionId.empty()) {
        return MakeResult(Code::kRejected, "INVALID_LIFECYCLE_IDENTITY");
    }
    if (!ActionAllows(request)) {
        return MakeResult(Code::kRejected, "ACTION_MAPPING_MISMATCH",
                          request.transitionId);
    }
    const MappingDecision mapping =
        DecideMapping(request.source, request.target, request.mappingVersion,
                      request.requireFirstFrame);
    if (mapping.code != Code::kAccepted) {
        return MakeResult(mapping.code, mapping.reason,
                          request.transitionId);
    }
    const std::string activitySlot = ActivitySlotKey(request.key);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        request.key.generation <= retired->second) {
        return MakeResult(Code::kFailedTyped,
                          "RETIRED_ACTIVITY_GENERATION",
                          request.transitionId);
    }
    auto activity = activityStates_.find(activitySlot);
    if (activity == activityStates_.end()) {
        if (request.actionId != "Fn03.A01" ||
            request.source != ActivityState::kRegistered) {
            return MakeResult(Code::kRejected, "ACTIVITY_NOT_REGISTERED",
                              request.transitionId);
        }
        activity = activityStates_
                       .emplace(activitySlot,
                                ActivityRecord{request.key.generation,
                                               ActivityState::kRegistered})
                       .first;
    } else if (request.key.generation < activity->second.generation) {
        return MakeResult(Code::kFailedTyped, "STALE_ACTIVITY_GENERATION",
                          request.transitionId);
    } else if (request.key.generation > activity->second.generation) {
        if (request.actionId != "Fn03.A01" ||
            request.source != ActivityState::kRegistered) {
            return MakeResult(Code::kRejected,
                              "ACTIVITY_GENERATION_NOT_REGISTERED",
                              request.transitionId);
        }
        activity->second =
            ActivityRecord{request.key.generation, ActivityState::kRegistered};
        inFlight_.erase(activitySlot);
    }
    const std::string key = KeyFor(request);
    if (records_.count(key) != 0) {
        return MakeResult(Code::kDuplicate, "TRANSITION_REPLAY",
                          request.transitionId);
    }
    if (activity->second.state != request.source) {
        return MakeResult(Code::kRejected, "SOURCE_STATE_MISMATCH",
                          request.transitionId);
    }
    if (inFlight_.count(activitySlot) != 0) {
        return MakeResult(Code::kRejected, "TRANSITION_IN_FLIGHT",
                          request.transitionId);
    }
    records_.emplace(key, Record{request, mapping, 0, false,
                                 Code::kPending});
    inFlight_[activitySlot] = key;
    return MakeResult(Code::kAccepted,
                      "QUEUED:" + Join(mapping.transactions),
                      request.transitionId, true);
}

Result LifecycleReducer::Callback(const LifecycleRequest& request,
                                  const std::string& callback, bool success)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const std::string key = KeyFor(request);
    auto record = records_.find(key);
    if (record == records_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_TRANSITION",
                          request.transitionId);
    }
    if (!SameLifecycleRequest(record->second.request, request)) {
        return MakeResult(Code::kRejected, "LIFECYCLE_REQUEST_MISMATCH",
                          request.transitionId);
    }
    const std::string activitySlot = ActivitySlotKey(request.key);
    const auto activity = activityStates_.find(activitySlot);
    if (activity == activityStates_.end() ||
        activity->second.generation != request.key.generation) {
        return MakeResult(Code::kFailedTyped, "STALE_ACTIVITY_GENERATION",
                          request.transitionId);
    }
    if (record->second.terminal) {
        return MakeResult(Code::kDuplicate, "CALLBACK_REPLAY",
                          request.transitionId);
    }
    const auto& callbacks = record->second.mapping.callbacks;
    if (record->second.nextCallback > 0 &&
        callbacks[record->second.nextCallback - 1] == callback) {
        return MakeResult(Code::kDuplicate, "CALLBACK_REPLAY",
                          request.transitionId);
    }
    if (record->second.nextCallback >= callbacks.size() ||
        callbacks[record->second.nextCallback] != callback) {
        return MakeResult(Code::kRejected, "CALLBACK_OUT_OF_ORDER",
                          request.transitionId);
    }
    if (!success) {
        record->second.terminal = true;
        record->second.code = Code::kFailedTyped;
        if (inFlight_[activitySlot] == key) {
            inFlight_.erase(activitySlot);
        }
        return MakeResult(Code::kFailedTyped, "CALLBACK_FAILED",
                          request.transitionId);
    }
    ++record->second.nextCallback;
    ++callbackCounts_[request.actionId];
    if (record->second.nextCallback != callbacks.size()) {
        return MakeResult(Code::kPending, callback + "_OBSERVED",
                          request.transitionId);
    }
    record->second.terminal = true;
    record->second.code = Code::kReady;
    activity->second.state = CommittedState(record->second.request);
    if (inFlight_[activitySlot] == key) {
        inFlight_.erase(activitySlot);
    }
    return MakeResult(Code::kReady, callback + "_TERMINAL",
                      request.transitionId);
}

Result LifecycleReducer::Expire(const LifecycleRequest& request,
                                int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    const std::string key = KeyFor(request);
    auto record = records_.find(key);
    if (record == records_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_TRANSITION",
                          request.transitionId);
    }
    const std::string activitySlot = ActivitySlotKey(request.key);
    const auto activity = activityStates_.find(activitySlot);
    if (activity == activityStates_.end() ||
        activity->second.generation != request.key.generation) {
        return MakeResult(Code::kFailedTyped, "STALE_ACTIVITY_GENERATION",
                          request.transitionId);
    }
    if (record->second.terminal) {
        return MakeResult(Code::kDuplicate, "ALREADY_TERMINAL",
                          request.transitionId);
    }
    if (nowMs - record->second.request.queuedAtMs < kPolicyTimeoutMs) {
        return MakeResult(Code::kPending, "CALLBACK_PENDING",
                          request.transitionId);
    }
    record->second.terminal = true;
    record->second.code = Code::kReconcileRequired;
    if (inFlight_[activitySlot] == key) {
        inFlight_.erase(activitySlot);
    }
    return MakeResult(Code::kReconcileRequired, "CALLBACK_TIMEOUT",
                      request.transitionId);
}

Result LifecycleReducer::Retire(const ActivityKey& key)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid()) {
        return MakeResult(Code::kRejected, "INVALID_RETIRE_IDENTITY");
    }
    const std::string activitySlot = ActivitySlotKey(key);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kDuplicate,
                          "ACTIVITY_GENERATION_ALREADY_RETIRED");
    }
    const auto activity = activityStates_.find(activitySlot);
    if (activity == activityStates_.end() ||
        activity->second.generation != key.generation) {
        return MakeResult(Code::kRejected, "UNKNOWN_ACTIVITY_GENERATION");
    }
    retiredGenerations_[activitySlot] = key.generation;
    activityStates_.erase(activity);
    inFlight_.erase(activitySlot);
    for (auto record = records_.begin(); record != records_.end();) {
        if (ActivitySlotKey(record->second.request.key) != activitySlot ||
            record->second.request.key.generation > key.generation) {
            ++record;
            continue;
        }
        record = records_.erase(record);
    }
    return MakeResult(Code::kAccepted, "ACTIVITY_GENERATION_RETIRED");
}

size_t LifecycleReducer::CallbackCount(const std::string& actionId) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto found = callbackCounts_.find(actionId);
    return found == callbackCounts_.end() ? 0 : found->second;
}

std::optional<ActivityState> LifecycleReducer::CurrentState(
    const ActivityKey& key) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    const auto found = activityStates_.find(ActivitySlotKey(key));
    if (found == activityStates_.end() ||
        found->second.generation != key.generation) {
        return std::nullopt;
    }
    return found->second.state;
}

size_t LifecycleReducer::PendingSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return inFlight_.size();
}

std::string FirstFrameGate::KeyFor(const ActivityKey& key,
                                   uint64_t windowGeneration)
{
    return key.StableString() + ":" + std::to_string(windowGeneration);
}

std::string FirstFrameGate::ActivitySlotKey(const ActivityKey& key)
{
    return key.owner + ":" + std::to_string(key.processEpoch) + ":" +
           std::to_string(key.tokenHandle);
}

Result FirstFrameGate::Create(const ActivityKey& key,
                              uint64_t windowGeneration,
                              const std::string& transitionId,
                              bool requireFirstFrame, int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!requireFirstFrame) {
        return MakeResult(Code::kRejected, "FIRST_FRAME_NOT_REQUIRED",
                          transitionId);
    }
    if (transitionId.size() > kFirstFrameTransitionIdMaxBytes) {
        return MakeResult(Code::kFailedTyped,
                          "FIRST_FRAME_TRANSITION_ID_TOO_LONG");
    }
    if (!key.IsValid() || windowGeneration == 0 || transitionId.empty()) {
        return MakeResult(Code::kRejected, "INVALID_FIRST_FRAME_JOIN",
                          transitionId);
    }
    const auto retired = retiredGenerations_.find(ActivitySlotKey(key));
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kFailedTyped,
                          "RETIRED_ACTIVITY_GENERATION", transitionId);
    }
    const std::string stable = KeyFor(key, windowGeneration);
    auto existing = joins_.find(stable);
    std::unordered_set<std::string> seenTransitionIds;
    int64_t createdAtMs = nowMs;
    if (existing != joins_.end()) {
        if (existing->second.transitionId == transitionId) {
            return MakeResult(Code::kDuplicate, existing->second.reason,
                              transitionId);
        }
        if (existing->second.seenTransitionIds.count(transitionId) != 0) {
            return MakeResult(Code::kDuplicate,
                              "FIRST_FRAME_TRANSITION_REPLAY",
                              transitionId);
        }
        if (existing->second.terminal) {
            return MakeResult(Code::kRejected,
                              "FIRST_FRAME_JOIN_ALREADY_TERMINAL",
                              transitionId);
        }
        if (existing->second.seenTransitionIds.size() >=
            kFirstFrameDistinctTransitionsPerJoin) {
            return MakeResult(Code::kFailedTyped,
                              "FIRST_FRAME_TRANSITION_CAPACITY_REACHED",
                              transitionId);
        }
        createdAtMs = existing->second.createdAtMs;
        seenTransitionIds = std::move(existing->second.seenTransitionIds);
    }
    seenTransitionIds.insert(transitionId);
    joins_[stable] = Join{key, windowGeneration, transitionId, createdAtMs, false,
                          false, false, Code::kPending,
                          "AWAITING_FIRST_FRAME",
                          std::move(seenTransitionIds)};
    return MakeResult(Code::kAccepted, "AWAITING_FIRST_FRAME",
                      transitionId);
}

Result FirstFrameGate::MaybeReady(Join& join)
{
    if (!join.terminal && join.resumed && join.presented) {
        join.terminal = true;
        join.code = Code::kReady;
        join.reason = "FOREGROUND_READY";
        ++readyCount_;
        return MakeResult(Code::kReady, join.reason, join.transitionId, true);
    }
    return MakeResult(Code::kPending, "WAITING_FOR_JOIN",
                      join.transitionId);
}

Result FirstFrameGate::Resume(const ActivityKey& key,
                              uint64_t windowGeneration,
                              const std::string& transitionId)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto join = joins_.find(KeyFor(key, windowGeneration));
    if (join == joins_.end() || join->second.transitionId != transitionId) {
        return MakeResult(Code::kRejected, "NO_OPEN_FIRST_FRAME_JOIN",
                          transitionId);
    }
    if (join->second.terminal) {
        return MakeResult(Code::kDuplicate, join->second.reason,
                          transitionId);
    }
    join->second.resumed = true;
    return MaybeReady(join->second);
}

Result FirstFrameGate::Present(const FirstFrameReceipt& receipt)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto join = joins_.find(KeyFor(receipt.key, receipt.windowGeneration));
    if (join == joins_.end()) {
        return MakeResult(Code::kRejected, "NO_OPEN_FIRST_FRAME_JOIN");
    }
    if (join->second.terminal) {
        return MakeResult(Code::kDuplicate, join->second.reason,
                          join->second.transitionId);
    }
    if (!receipt.presented || receipt.contentOrigin !=
                                  ContentOrigin::kAppContent ||
        receipt.producerActionId != "Fn04.A02" ||
        !IsSha256(receipt.evidenceRunSha256) || receipt.frameId == 0) {
        return MakeResult(Code::kRejected, "INVALID_FIRST_CONTENT_PRESENT",
                          join->second.transitionId);
    }
    join->second.presented = true;
    return MaybeReady(join->second);
}

Result FirstFrameGate::Supersede(const ActivityKey& key,
                                 uint64_t windowGeneration,
                                 const std::string& reason)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto join = joins_.find(KeyFor(key, windowGeneration));
    if (join == joins_.end() || join->second.terminal) {
        return MakeResult(Code::kDuplicate, "NO_OPEN_FIRST_FRAME_JOIN");
    }
    join->second.terminal = true;
    join->second.code = Code::kFailedTyped;
    join->second.reason = reason.empty() ? "SUPERSEDED" : reason;
    return MakeResult(Code::kFailedTyped, join->second.reason,
                      join->second.transitionId);
}

Result FirstFrameGate::Expire(const ActivityKey& key,
                              uint64_t windowGeneration, int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto join = joins_.find(KeyFor(key, windowGeneration));
    if (join == joins_.end()) {
        return MakeResult(Code::kRejected, "NO_OPEN_FIRST_FRAME_JOIN");
    }
    if (join->second.terminal) {
        return MakeResult(Code::kDuplicate, join->second.reason,
                          join->second.transitionId);
    }
    if (!FirstFrameTimeoutElapsed(join->second.createdAtMs, nowMs)) {
        return MakeResult(Code::kPending, "FIRST_FRAME_PENDING",
                          join->second.transitionId);
    }
    join->second.terminal = true;
    join->second.code = Code::kFailedTyped;
    join->second.reason = "FIRST_FRAME_TIMEOUT";
    return MakeResult(Code::kFailedTyped, join->second.reason,
                      join->second.transitionId);
}

Result FirstFrameGate::Retire(const ActivityKey& key)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid()) {
        return MakeResult(Code::kRejected, "INVALID_RETIRE_IDENTITY");
    }
    const std::string activitySlot = ActivitySlotKey(key);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kDuplicate,
                          "ACTIVITY_GENERATION_ALREADY_RETIRED");
    }
    retiredGenerations_[activitySlot] = key.generation;
    for (auto join = joins_.begin(); join != joins_.end();) {
        if (ActivitySlotKey(join->second.key) != activitySlot ||
            join->second.key.generation > key.generation) {
            ++join;
            continue;
        }
        join = joins_.erase(join);
    }
    return MakeResult(Code::kAccepted, "ACTIVITY_GENERATION_RETIRED");
}

size_t FirstFrameGate::ReadyCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return readyCount_;
}

size_t FirstFrameGate::ActiveSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return joins_.size();
}

std::string AckReducer::KeyFor(const ActivityKey& key,
                               const std::string& transitionId)
{
    return key.StableString() + ":" + transitionId;
}

std::string AckReducer::ActivitySlotKey(const ActivityKey& key)
{
    return key.owner + ":" + std::to_string(key.processEpoch) + ":" +
           std::to_string(key.tokenHandle);
}

Result AckReducer::Open(const ActivityKey& key,
                        const std::string& transitionId,
                        const std::vector<std::string>& requiredReceipts,
                        int64_t)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid() || transitionId.empty() || requiredReceipts.empty()) {
        return MakeResult(Code::kRejected, "INVALID_ACK_TRANSITION",
                          transitionId);
    }
    const auto retired = retiredGenerations_.find(ActivitySlotKey(key));
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kFailedTyped,
                          "RETIRED_ACTIVITY_GENERATION", transitionId);
    }
    const std::string stable = KeyFor(key, transitionId);
    if (acks_.count(stable) != 0) {
        return MakeResult(Code::kDuplicate, "ACK_TRANSITION_REPLAY",
                          transitionId);
    }
    Ack ack;
    ack.key = key;
    ack.required.insert(requiredReceipts.begin(), requiredReceipts.end());
    acks_.emplace(stable, std::move(ack));
    return MakeResult(Code::kAccepted, "ACK_TRANSITION_OPEN", transitionId);
}

Result AckReducer::Receipt(const ActivityKey& key,
                           const std::string& transitionId,
                           const std::string& receipt, int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto ack = acks_.find(KeyFor(key, transitionId));
    if (ack == acks_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_ACK_TRANSITION",
                          transitionId);
    }
    if (ack->second.terminal) {
        return MakeResult(Code::kDuplicate, "ACK_ALREADY_TERMINAL",
                          transitionId);
    }
    if (ack->second.required.count(receipt) == 0) {
        return MakeResult(Code::kRejected, "UNEXPECTED_RECEIPT",
                          transitionId);
    }
    if (!ack->second.received.insert(receipt).second) {
        return MakeResult(Code::kDuplicate, "RECEIPT_REPLAY",
                          transitionId);
    }
    if (ack->second.received == ack->second.required) {
        ack->second.sent = true;
        ack->second.sentAtMs = nowMs;
        ++sendCount_;
        return MakeResult(Code::kReady, "ABILITY_TRANSITION_DONE_SENT",
                          transitionId, true);
    }
    return MakeResult(Code::kPending, "WAITING_REQUIRED_RECEIPTS",
                      transitionId);
}

Result AckReducer::DisplayFailed(const ActivityKey& key,
                                 const std::string& transitionId)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto ack = acks_.find(KeyFor(key, transitionId));
    if (ack == acks_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_ACK_TRANSITION",
                          transitionId);
    }
    if (ack->second.sent) {
        return MakeResult(Code::kReconcileRequired,
                          "DISPLAY_FAILED_AFTER_SEND", transitionId);
    }
    ack->second.terminal = true;
    ack->second.code = Code::kFailedTyped;
    return MakeResult(Code::kFailedTyped, "FIRST_FRAME_NOT_PRESENTED",
                      transitionId);
}

Result AckReducer::HostResult(const ActivityKey& key,
                              const std::string& transitionId,
                              std::optional<int> hostResult)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto ack = acks_.find(KeyFor(key, transitionId));
    if (ack == acks_.end() || !ack->second.sent) {
        return MakeResult(Code::kRejected, "ACK_NOT_SENT", transitionId);
    }
    if (ack->second.terminal) {
        return MakeResult(Code::kDuplicate, "HOST_RESULT_REPLAY",
                          transitionId);
    }
    if (!hostResult.has_value()) {
        ack->second.terminal = true;
        ack->second.code = Code::kReconcileRequired;
        return MakeResult(Code::kReconcileRequired,
                          "UNKNOWN_HOST_ACK_RESULT", transitionId);
    }
    ack->second.terminal = true;
    if (*hostResult == 0) {
        ack->second.code = Code::kReady;
        return MakeResult(Code::kReady, "HOST_ACKED", transitionId);
    }
    ack->second.code = Code::kFailedTyped;
    return MakeResult(Code::kFailedTyped, "HOST_ACK_REJECTED",
                      transitionId);
}

Result AckReducer::ExpireHostAck(const ActivityKey& key,
                                 const std::string& transitionId,
                                 int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto ack = acks_.find(KeyFor(key, transitionId));
    if (ack == acks_.end() || !ack->second.sent) {
        return MakeResult(Code::kRejected, "ACK_NOT_SENT", transitionId);
    }
    if (ack->second.terminal) {
        return MakeResult(Code::kDuplicate, "ACK_ALREADY_TERMINAL",
                          transitionId);
    }
    if (nowMs - ack->second.sentAtMs < kPolicyTimeoutMs) {
        return MakeResult(Code::kPending, "HOST_ACK_PENDING",
                          transitionId);
    }
    ack->second.terminal = true;
    ack->second.code = Code::kReconcileRequired;
    return MakeResult(Code::kReconcileRequired, "HOST_ACK_TIMEOUT",
                      transitionId);
}

Result AckReducer::Retire(const ActivityKey& key)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid()) {
        return MakeResult(Code::kRejected, "INVALID_RETIRE_IDENTITY");
    }
    const std::string activitySlot = ActivitySlotKey(key);
    const auto retired = retiredGenerations_.find(activitySlot);
    if (retired != retiredGenerations_.end() &&
        key.generation <= retired->second) {
        return MakeResult(Code::kDuplicate,
                          "ACTIVITY_GENERATION_ALREADY_RETIRED");
    }
    retiredGenerations_[activitySlot] = key.generation;
    for (auto ack = acks_.begin(); ack != acks_.end();) {
        if (ActivitySlotKey(ack->second.key) != activitySlot ||
            ack->second.key.generation > key.generation) {
            ++ack;
            continue;
        }
        ack = acks_.erase(ack);
    }
    return MakeResult(Code::kAccepted, "ACTIVITY_GENERATION_RETIRED");
}

size_t AckReducer::SendCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return sendCount_;
}

size_t AckReducer::PendingSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return acks_.size();
}

std::string TerminationCoordinator::KeyFor(const ActivityKey& key)
{
    return key.StableString();
}

Result TerminationCoordinator::BeginFinish(const ActivityKey& key,
                                           ActivityState source,
                                           const std::string& finishId,
                                           const std::string& mappingVersion,
                                           int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    if (!key.IsValid() || finishId.empty()) {
        return MakeResult(Code::kRejected, "INVALID_FINISH_IDENTITY");
    }
    if (mappingVersion != kMappingVersion) {
        return MakeResult(Code::kRejected, "WRONG_MAPPING_VERSION");
    }
    if (source != ActivityState::kCreated) {
        return MakeResult(Code::kRejected,
                          "UNSUPPORTED_ANDROID_FINISH_SOURCE_STATE_V1");
    }
    const std::string stable = KeyFor(key);
    auto existing = terminals_.find(stable);
    if (existing != terminals_.end()) {
        if (existing->second.finishId == finishId) {
            return MakeResult(Code::kDuplicate, "FINISH_REPLAY",
                              existing->second.transitionId);
        }
        return MakeResult(Code::kRejected, "SECOND_FINISH_IN_FLIGHT");
    }
    const std::string transition =
        "finish-transition-" + std::to_string(nextTransition_++);
    terminals_.emplace(
        stable, Terminal{key, finishId, transition, {}, nowMs, 0, false,
                         false, false, false, false, false,
                         Code::kPending});
    return MakeResult(Code::kAccepted, "FINISH_REQUESTED", transition, true);
}

Result TerminationCoordinator::MaybeDispatch(Terminal& terminal)
{
    if (terminal.hostAccepted && terminal.initialArrived &&
        !terminal.destroyDispatched) {
        terminal.destroyDispatched = true;
        ++destroyDispatchCount_;
        return MakeResult(Code::kReady, "DESTROY_DISPATCHED",
                          terminal.transitionId, true);
    }
    return MakeResult(Code::kPending, "QUEUED_AWAITING_HOST_ACCEPT",
                      terminal.transitionId);
}

Result TerminationCoordinator::HostTerminateResult(const ActivityKey& key,
                                                   bool accepted,
                                                   int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_FINISH");
    }
    if (terminal->second.terminal) {
        return MakeResult(Code::kDuplicate, "FINISH_ALREADY_TERMINAL",
                          terminal->second.transitionId);
    }
    if (terminal->second.hostAccepted) {
        return MakeResult(Code::kDuplicate, "HOST_ACCEPT_REPLAY",
                          terminal->second.transitionId);
    }
    if (!accepted) {
        terminal->second.terminal = true;
        terminal->second.code = Code::kFailedTyped;
        return MakeResult(Code::kFailedTyped, "HOST_TERMINATE_REJECTED",
                          terminal->second.transitionId);
    }
    terminal->second.hostAccepted = true;
    terminal->second.firstTerminalAtMs = nowMs;
    return MaybeDispatch(terminal->second);
}

Result TerminationCoordinator::Initial(const ActivityKey& key,
                                       const std::string& ohTransitionId,
                                       int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end()) {
        return MakeResult(Code::kRejected, "INITIAL_WITHOUT_FINISH");
    }
    if (ohTransitionId.empty()) {
        return MakeResult(Code::kRejected, "INVALID_OH_TRANSITION_ID",
                          terminal->second.transitionId);
    }
    if (terminal->second.initialArrived) {
        if (terminal->second.ohTransitionId == ohTransitionId) {
            return MakeResult(Code::kDuplicate, "INITIAL_REPLAY",
                              terminal->second.transitionId);
        }
        return MakeResult(Code::kRejected, "SECOND_INITIAL_TRANSITION");
    }
    terminal->second.initialArrived = true;
    terminal->second.ohTransitionId = ohTransitionId;
    if (terminal->second.firstTerminalAtMs == 0) {
        terminal->second.firstTerminalAtMs = nowMs;
    }
    return MaybeDispatch(terminal->second);
}

Result TerminationCoordinator::MaybeClean(Terminal& terminal)
{
    if (terminal.hostAccepted && terminal.androidDestroyed &&
        terminal.ohClean) {
        terminal.terminal = true;
        terminal.code = Code::kReady;
        return MakeResult(Code::kReady, "CLEANED", terminal.transitionId,
                          true);
    }
    return MakeResult(Code::kPending, "TERMINAL_JOIN_PENDING",
                      terminal.transitionId);
}

Result TerminationCoordinator::AndroidDestroyed(const ActivityKey& key)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end() ||
        !terminal->second.destroyDispatched) {
        return MakeResult(Code::kRejected, "DESTROY_NOT_DISPATCHED");
    }
    if (terminal->second.androidDestroyed) {
        return MakeResult(Code::kDuplicate, "DESTROY_RECEIPT_REPLAY",
                          terminal->second.transitionId);
    }
    terminal->second.androidDestroyed = true;
    return MaybeClean(terminal->second);
}

Result TerminationCoordinator::OhClean(const ActivityKey& key)
{
    return OhTerminated(key, OhTerminalFact::kClean);
}

Result TerminationCoordinator::OhTerminated(const ActivityKey& key,
                                            OhTerminalFact fact)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_FINISH");
    }
    if (terminal->second.ohClean) {
        return MakeResult(Code::kDuplicate, "OH_TERMINAL_FACT_REPLAY",
                          terminal->second.transitionId);
    }
    switch (fact) {
        case OhTerminalFact::kClean:
        case OhTerminalFact::kProcessDeath:
            break;
        default:
            return MakeResult(Code::kRejected, "INVALID_OH_TERMINAL_FACT",
                              terminal->second.transitionId);
    }
    terminal->second.ohClean = true;
    return MaybeClean(terminal->second);
}

Result TerminationCoordinator::ExpireHostAccept(const ActivityKey& key,
                                                int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_FINISH");
    }
    if (terminal->second.terminal) {
        return MakeResult(Code::kDuplicate, "FINISH_ALREADY_TERMINAL",
                          terminal->second.transitionId);
    }
    if (terminal->second.hostAccepted) {
        return MakeResult(Code::kDuplicate, "HOST_ALREADY_ACCEPTED",
                          terminal->second.transitionId);
    }
    if (nowMs - terminal->second.finishAtMs < kPolicyTimeoutMs) {
        return MakeResult(Code::kPending, "HOST_TERMINATE_PENDING",
                          terminal->second.transitionId);
    }
    terminal->second.terminal = true;
    terminal->second.code = Code::kReconcileRequired;
    return MakeResult(Code::kReconcileRequired,
                      "HOST_TERMINATE_ACCEPT_TIMEOUT",
                      terminal->second.transitionId);
}

Result TerminationCoordinator::ExpireTerminalJoin(const ActivityKey& key,
                                                  int64_t nowMs)
{
    std::lock_guard<std::mutex> lock(mutex_);
    auto terminal = terminals_.find(KeyFor(key));
    if (terminal == terminals_.end()) {
        return MakeResult(Code::kRejected, "UNKNOWN_FINISH");
    }
    if (terminal->second.terminal) {
        return MakeResult(Code::kDuplicate, "FINISH_ALREADY_TERMINAL",
                          terminal->second.transitionId);
    }
    if (terminal->second.firstTerminalAtMs == 0 ||
        nowMs - terminal->second.firstTerminalAtMs < kPolicyTimeoutMs) {
        return MakeResult(Code::kPending, "TERMINAL_JOIN_PENDING",
                          terminal->second.transitionId);
    }
    terminal->second.terminal = true;
    terminal->second.code = Code::kReconcileRequired;
    return MakeResult(Code::kReconcileRequired, "TERMINAL_JOIN_TIMEOUT",
                      terminal->second.transitionId);
}

size_t TerminationCoordinator::DestroyDispatchCount() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return destroyDispatchCount_;
}

bool TerminationCoordinator::AdmissionClosed(const ActivityKey& key) const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return terminals_.count(KeyFor(key)) != 0;
}

size_t TerminationCoordinator::PendingSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return std::count_if(terminals_.begin(), terminals_.end(),
                         [](const auto& entry) {
                             return !entry.second.terminal;
                         });
}

size_t TerminationCoordinator::TombstoneSize() const
{
    std::lock_guard<std::mutex> lock(mutex_);
    return std::count_if(terminals_.begin(), terminals_.end(),
                         [](const auto& entry) {
                             return entry.second.terminal;
                         });
}

}  // namespace oh_adapter::fn03
