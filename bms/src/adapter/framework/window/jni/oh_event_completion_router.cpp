/*
 * oh_event_completion_router.cpp
 *
 * Fn05.A07 integration seam implementation.  See header for the contract
 * and the lock-ordering rules.
 */

#include "oh_event_completion_router.h"

namespace oh_adapter {
namespace input {

OhEventCompletionRouter::OhEventCompletionRouter(LedgerConfig config)
    : ledger_(std::move(config),
              [this](const std::string& generation, int64_t oh_event_id) {
                  resolveAndMark(generation, oh_event_id);
              }) {}

std::string OhEventCompletionRouter::openSession(int32_t session_id,
                                                 int64_t now_ns) {
    std::string old_generation;
    std::string new_generation;
    {
        std::lock_guard<std::mutex> lock(session_mutex_);
        // Persistent counter: survives closeSession so generation names are
        // never reused (a reused name is permanently torn down in the
        // ledger and would make every later event untrackable).
        const uint64_t counter = ++counters_[session_id];
        SessionState& state = sessions_[session_id];
        old_generation = state.generation;
        state.generation =
            "s" + std::to_string(session_id) + "-g" + std::to_string(counter);
        new_generation = state.generation;
    }
    if (!old_generation.empty()) {
        // Rotate: previous window generation is finished fail-closed.
        ledger_.teardownGeneration(old_generation, now_ns);
        purgeThunks(old_generation);
    }
    return new_generation;
}

void OhEventCompletionRouter::closeSession(int32_t session_id,
                                           int64_t now_ns) {
    std::string generation;
    {
        std::lock_guard<std::mutex> lock(session_mutex_);
        auto it = sessions_.find(session_id);
        if (it == sessions_.end()) {
            return;
        }
        generation = it->second.generation;
        sessions_.erase(it);
    }
    if (!generation.empty()) {
        ledger_.teardownGeneration(generation, now_ns);
        purgeThunks(generation);
    }
}

std::string OhEventCompletionRouter::generationFor(int32_t session_id) const {
    std::lock_guard<std::mutex> lock(session_mutex_);
    auto it = sessions_.find(session_id);
    return it == sessions_.end() ? std::string() : it->second.generation;
}

bool OhEventCompletionRouter::hasSession(int32_t session_id) const {
    std::lock_guard<std::mutex> lock(session_mutex_);
    return sessions_.find(session_id) != sessions_.end();
}

OhEventCompletionRouter::AcceptResult OhEventCompletionRouter::acceptEvent(
    int32_t session_id,
    int64_t oh_event_id,
    MarkProcessedThunk thunk) {
    const std::string generation = generationFor(session_id);
    if (generation.empty()) {
        return AcceptResult::UNTRACKED;
    }
    if (!ledger_.acceptEvent(generation, oh_event_id)) {
        // Ledger rejection (e.g. LEDGER_COLLISION) is already recorded
        // fail-closed; the caller must not ack this event.
        return AcceptResult::REJECTED;
    }
    // The thunk must be visible before the token can be ARMED: onFinished
    // only matches ARMED tokens, so storing the thunk here (before any arm)
    // guarantees resolveAndMark always finds it.
    std::lock_guard<std::mutex> lock(thunk_mutex_);
    thunks_[generation][oh_event_id] = std::move(thunk);
    return AcceptResult::ACCEPTED;
}

bool OhEventCompletionRouter::arm(int32_t session_id,
                                  int64_t oh_event_id,
                                  uint32_t android_seq,
                                  int64_t now_ns) {
    const std::string generation = generationFor(session_id);
    if (generation.empty()) {
        return false;
    }
    return ledger_.arm(generation, oh_event_id, android_seq, now_ns);
}

void OhEventCompletionRouter::publishReject(int32_t session_id,
                                            int64_t oh_event_id,
                                            int64_t now_ns,
                                            int64_t publish_rc) {
    const std::string generation = generationFor(session_id);
    if (generation.empty()) {
        return;
    }
    ledger_.cancelEvent(generation, oh_event_id, now_ns,
                        TerminalReason::PUBLISH_REJECT, publish_rc);
    purgeThunk(generation, oh_event_id);
}

void OhEventCompletionRouter::onFinished(int32_t session_id,
                                         uint32_t android_seq,
                                         int64_t now_ns,
                                         int64_t callback_tid,
                                         int handled) {
    const std::string generation = generationFor(session_id);
    if (generation.empty()) {
        return;  // FINISHED for a session we no longer track: drop.
    }
    ledger_.onFinished(generation, android_seq, now_ns, callback_tid,
                       handled);
}

void OhEventCompletionRouter::onFinishedGeneration(
    const std::string& generation,
    uint32_t android_seq,
    int64_t now_ns,
    int64_t callback_tid,
    int handled) {
    if (generation.empty()) {
        return;
    }
    ledger_.onFinished(generation, android_seq, now_ns, callback_tid,
                       handled);
}

void OhEventCompletionRouter::scanTimeouts(int64_t now_ns) {
    std::vector<std::pair<std::string, int64_t>> timed_out;
    ledger_.scanTimeouts(now_ns, &timed_out);
    for (const auto& entry : timed_out) {
        purgeThunk(entry.first, entry.second);
    }
}

std::vector<LedgerRow> OhEventCompletionRouter::getRows() const {
    return ledger_.getRows();
}

size_t OhEventCompletionRouter::inFlightCount() const {
    return ledger_.inFlightCount();
}

size_t OhEventCompletionRouter::pendingThunkCount() const {
    std::lock_guard<std::mutex> lock(thunk_mutex_);
    size_t count = 0;
    for (const auto& gen_pair : thunks_) {
        count += gen_pair.second.size();
    }
    return count;
}

void OhEventCompletionRouter::resolveAndMark(const std::string& generation,
                                             int64_t oh_event_id) {
    MarkProcessedThunk thunk;
    {
        std::lock_guard<std::mutex> lock(thunk_mutex_);
        auto gen_it = thunks_.find(generation);
        if (gen_it == thunks_.end()) {
            return;
        }
        auto ev_it = gen_it->second.find(oh_event_id);
        if (ev_it == gen_it->second.end()) {
            return;
        }
        thunk = std::move(ev_it->second);
        gen_it->second.erase(ev_it);
        if (gen_it->second.empty()) {
            thunks_.erase(gen_it);
        }
    }
    // Invoke outside thunk_mutex_ (leaf-lock rule).  The thunk is taken by
    // value, so it is invoked exactly once even if a teardown purge races:
    // the purge can no longer find it here, and a purged (erased) thunk is
    // never invoked.
    if (thunk) {
        thunk();
    }
}

void OhEventCompletionRouter::purgeThunk(const std::string& generation,
                                         int64_t oh_event_id) {
    std::lock_guard<std::mutex> lock(thunk_mutex_);
    auto gen_it = thunks_.find(generation);
    if (gen_it == thunks_.end()) {
        return;
    }
    gen_it->second.erase(oh_event_id);
    if (gen_it->second.empty()) {
        thunks_.erase(gen_it);
    }
}

void OhEventCompletionRouter::purgeThunks(const std::string& generation) {
    std::lock_guard<std::mutex> lock(thunk_mutex_);
    thunks_.erase(generation);
}

}  // namespace input
}  // namespace oh_adapter
