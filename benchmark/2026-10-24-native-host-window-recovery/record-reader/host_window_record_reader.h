#pragma once

#include <cstddef>
#include <cstdint>
#include <optional>
#include <string>
#include <sys/types.h>

namespace westlake::host_window {
inline constexpr std::size_t kMaxRecordBytes = 8192;
inline constexpr std::size_t kMaxJsonDepth = 16; // root container counts as one

enum class Status { Candidate, Unavailable, RejectedFile, InvalidRecord, Drift };
enum class SourceEvent { WindowReady, StageEvent };
struct FileIdentity {
    std::uint64_t device, inode;
    std::int64_t size, mtime_seconds, mtime_nanoseconds;
    std::int64_t ctime_seconds, ctime_nanoseconds;
    uid_t uid;
    gid_t gid;
    mode_t mode;
};
struct Candidate {
    std::int32_t window_id;
    FileIdentity file;
    SourceEvent source_event;
    // Raw stage enum value; missing is unknown, never inferred as visible.
    std::optional<std::int64_t> stage_event;
};
struct Result {
    Status status;
    std::optional<Candidate> candidate;
};

// No retained binding, IPC, authentication, polling or input writes.
// NOFOLLOW protects the final component; caller supplies a trusted parent path.
// This is bounded byte/syscall work, not a filesystem wall-clock timeout.
Result ReadWindowRecord(const std::string& path, uid_t expected_uid, gid_t expected_gid);

namespace detail {
// Production predicates exposed for deterministic identity/short-read tests.
bool SameIdentity(const FileIdentity& a, const FileIdentity& b);
bool StableRead(const FileIdentity& before, const FileIdentity& after,
                const FileIdentity& current_path, std::size_t bytes_read);
} // namespace detail
} // namespace westlake::host_window
