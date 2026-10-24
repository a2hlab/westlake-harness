#pragma once
#include "host_window_record_reader.h"
#include <cstdint>
#include <atomic>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <set>
#include <string>
#include <vector>

namespace westlake::recovery {
// A gate belongs to one immutable callback endpoint, never to a reusable actual ID.
// Closing waits for already admitted callbacks to finish before publication.
struct CallbackGate {
    std::recursive_mutex mutex;
    bool enabled = true;
    bool buffering = false, overflow = false;
    std::vector<std::function<void()>> pending;
    void close() {
        std::lock_guard<std::recursive_mutex> l(mutex);
        enabled = false; buffering = false; pending.clear();
    }
    void beginBuffering() {
        std::lock_guard<std::recursive_mutex> l(mutex);
        enabled = false; buffering = true; overflow = false; pending.clear();
    }
    void submit(std::function<void()> callback) {
        std::lock_guard<std::recursive_mutex> l(mutex);
        if (enabled) { callback(); return; }
        if (!buffering || overflow) return; // Retired endpoints never replay.
        if (pending.size() == 64) { overflow = true; pending.clear(); return; }
        pending.push_back(std::move(callback));
    }
    bool activate() {
        std::lock_guard<std::recursive_mutex> l(mutex);
        if (overflow || (!buffering && !enabled)) return false;
        if (enabled) return true;
        auto callbacks = std::move(pending);
        buffering = false; enabled = true;
        for (auto& callback : callbacks) callback();
        return true;
    }
};
struct Observation {
    host_window::Candidate candidate;

};
bool Foreground(const host_window::Candidate& candidate);
std::optional<Observation> ReadObservation(const std::string& path, uid_t uid, gid_t gid);
enum class Reply { Ok, Missing, Rejected, Unknown };
struct ParentReply { Reply status; int32_t main_id; };
struct Created { Reply status; int32_t actual_id; };
struct Binding { int32_t logical, actual, parent; uint64_t generation = 0; };

// No ownership authentication is represented here. Candidate trust is t1's
// same-application private record; ParentReply only establishes main-window kind.
struct Port {
    virtual ~Port() = default;
    virtual bool current() const = 0;
    virtual ParentReply parent(int32_t id) = 0;
    virtual Created create(int32_t parent, uint64_t generation) = 0;
    virtual Reply connect(int32_t actual) = 0;
    virtual Reply discard(int32_t actual) = 0;
    virtual void quiesceOldCallbacks() = 0;
    virtual bool publish(const Binding& previous, const Binding& next) = 0;
};
enum class Outcome { Idle, Throttled, InFlight, Rejected, Failed, StoppedUnknown, Committed };
class Coordinator {
public:
    explicit Coordinator(Binding b) : binding_(b) {}
    Outcome poll(uint64_t now_ms, const std::function<std::optional<Observation>()>& read, Port& port);
    Binding binding() const { return binding_; } // caller serializes lifetime/access
private:
    Binding binding_;
    std::mutex transaction_;
    bool attempted_ = false, stopped_ = false;
    uint64_t last_poll_ = 0;
    std::vector<host_window::FileIdentity> seen_;
};

class ParentCache {
public:
    static ParentCache& instance();
    int32_t committed() const { return parent_.load(std::memory_order_acquire); }
    void publish(int32_t verifiedParent) { parent_.store(verifiedParent, std::memory_order_release); }
private:
    std::atomic<int32_t> parent_{0};
};

// Input callers pass through this table BEFORE existing channel lookups.
// Untouched non-recovery sessions retain their old ID. Retired IDs never fall back.
class Routes {
public:
    static Routes& instance();
    bool install(int32_t logical, int32_t actual);
    bool replace(int32_t logical, int32_t old_actual, int32_t next_actual);
    void erase(int32_t logical);
    int32_t logical(int32_t actual) const;
private:
    mutable std::mutex mutex_;
    std::map<int32_t,int32_t> by_actual_;
    std::set<int32_t> retired_;
};
} // namespace westlake::recovery
