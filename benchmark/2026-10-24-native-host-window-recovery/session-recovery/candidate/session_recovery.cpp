#include "session_recovery.h"
namespace westlake::recovery {
bool Foreground(const host_window::Candidate& c) {
    return c.source_event == host_window::SourceEvent::WindowReady ||
        (c.source_event == host_window::SourceEvent::StageEvent && c.stage_event &&
         (*c.stage_event == 1 || *c.stage_event == 2));
}
std::optional<Observation> ReadObservation(const std::string& path, uid_t uid, gid_t gid) {
    auto result = host_window::ReadWindowRecord(path, uid, gid);
    if (result.status != host_window::Status::Candidate || !result.candidate) return {};
    return Observation{*result.candidate};
}
Outcome Coordinator::poll(uint64_t now, const std::function<std::optional<Observation>()>& read, Port& p) {
    std::unique_lock<std::mutex> transaction(transaction_, std::try_to_lock);
    if (!transaction.owns_lock()) return Outcome::InFlight;
    if (stopped_) return Outcome::StoppedUnknown;
    if (attempted_ && (now < last_poll_ || now - last_poll_ < 1000)) return Outcome::Throttled;
    attempted_ = true; last_poll_ = now;
    auto o = read();
    if (!o || !Foreground(o->candidate) || o->candidate.window_id <= 0 || o->candidate.window_id == binding_.parent)
        return Outcome::Idle;
    const auto& identity = o->candidate.file;
    for (const auto& seen : seen_)
        if (host_window::detail::SameIdentity(seen, identity)) return Outcome::Idle;
    // Stop instead of allowing unbounded per-generation attempts or memory growth.
    if (seen_.size() == 128) { stopped_ = true; return Outcome::StoppedUnknown; }
    auto old = p.parent(binding_.parent);
    if (old.status == Reply::Unknown) { stopped_ = true; return Outcome::StoppedUnknown; }
    if (old.status != Reply::Missing) return Outcome::Rejected;
    auto candidate = p.parent(o->candidate.window_id);
    if (candidate.status == Reply::Unknown) { stopped_ = true; return Outcome::StoppedUnknown; }
    if (candidate.status != Reply::Ok || candidate.main_id != o->candidate.window_id) return Outcome::Rejected;
    auto unchanged = [&] {
        auto current = read();
        return current && Foreground(current->candidate) && current->candidate.window_id == o->candidate.window_id &&
            host_window::detail::SameIdentity(current->candidate.file, identity);
    };
    if (!unchanged() || !p.current()) return Outcome::Rejected;
    // No old callback may race publication. Original rendering resources stay owned.
    seen_.push_back(identity); // Only consume a generation immediately before side effects.
    p.quiesceOldCallbacks();
    auto created = p.create(o->candidate.window_id, binding_.generation + 1);
    if (created.status == Reply::Unknown) { stopped_ = true; return Outcome::StoppedUnknown; }
    if (created.status != Reply::Ok || created.actual_id <= 0) return Outcome::Failed;
    auto cleanup = [&] {
        if (p.discard(created.actual_id) != Reply::Ok) {
            stopped_ = true; return Outcome::StoppedUnknown;
        }
        return Outcome::Failed;
    };
    if (!unchanged() || !p.current()) return cleanup();
    auto connected = p.connect(created.actual_id);
    if (connected == Reply::Unknown) {
        // Remote result is ambiguous: keep endpoint/resources, stop all later creates.
        stopped_ = true; return Outcome::StoppedUnknown;
    }
    if (connected != Reply::Ok || !unchanged() || !p.current()) return cleanup();
    Binding next{binding_.logical, created.actual_id, o->candidate.window_id, binding_.generation + 1};
    if (!p.publish(binding_, next)) return cleanup();
    binding_ = next;
    return Outcome::Committed;
}
ParentCache& ParentCache::instance() { static ParentCache cache; return cache; }
Routes& Routes::instance() { static Routes table; return table; }
bool Routes::install(int32_t l, int32_t a) {
    std::lock_guard<std::mutex> g(mutex_);
    if (l <= 0 || a <= 0 || retired_.count(a) || by_actual_.count(a)) return false;
    by_actual_[a] = l; return true;
}
bool Routes::replace(int32_t l, int32_t old, int32_t next) {
    std::lock_guard<std::mutex> g(mutex_);
    auto it = by_actual_.find(old);
    if (it == by_actual_.end() || it->second != l || next <= 0 || next == old ||
        by_actual_.count(next) || retired_.count(next)) return false;
    by_actual_.erase(it); retired_.insert(old); by_actual_[next] = l; return true;
}
void Routes::erase(int32_t logical) {
    std::lock_guard<std::mutex> g(mutex_);
    for (auto it=by_actual_.begin(); it!=by_actual_.end();) {
        if (it->second == logical) { retired_.insert(it->first); it=by_actual_.erase(it); }
        else ++it;
    }
}
int32_t Routes::logical(int32_t actual) const {
    std::lock_guard<std::mutex> g(mutex_);
    if (retired_.count(actual)) return -1;
    auto it=by_actual_.find(actual); return it==by_actual_.end() ? actual : it->second;
}
} // namespace westlake::recovery
