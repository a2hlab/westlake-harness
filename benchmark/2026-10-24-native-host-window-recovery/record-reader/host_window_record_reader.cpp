#include "host_window_record_reader.h"
#include "vendor/nlohmann/json.hpp"

#include <array>
#include <cstring>
#include <fcntl.h>
#include <limits>
#include <set>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>

namespace westlake::host_window {
namespace {
using Json = nlohmann::json;
struct ParseRejected {};
struct Fd {
    int value;
    ~Fd() { if (value >= 0) ::close(value); } // never retry close
};
Result Empty(Status status) { return {status, std::nullopt}; }
FileIdentity Identity(const struct stat& s) {
#if defined(__APPLE__)
    auto mt = s.st_mtimespec;
    auto ct = s.st_ctimespec;
#else
    auto mt = s.st_mtim;
    auto ct = s.st_ctim;
#endif
    return {static_cast<std::uint64_t>(s.st_dev), static_cast<std::uint64_t>(s.st_ino),
            s.st_size, mt.tv_sec, mt.tv_nsec, ct.tv_sec, ct.tv_nsec,
            s.st_uid, s.st_gid, s.st_mode};
}
Result Parse(const char* bytes, std::size_t size, const FileIdentity& file) {
    // A literal NUL is not JSON whitespace; some lexers treat it as EOF.
    if (std::memchr(bytes, '\0', size)) return Empty(Status::InvalidRecord);
    // The callback runs during parsing, before deeper structures can be built.
    // Keys are decoded JSON strings, so escaped duplicates are also rejected.
    std::vector<std::set<std::string>> containers;
    auto callback = [&](int, Json::parse_event_t event, Json& value) {
        switch (event) {
        case Json::parse_event_t::object_start:
        case Json::parse_event_t::array_start:
            if (containers.size() >= kMaxJsonDepth) throw ParseRejected{};
            containers.emplace_back();
            break;
        case Json::parse_event_t::key:
            if (containers.empty() || !containers.back().insert(value.get<std::string>()).second)
                throw ParseRejected{};
            break;
        case Json::parse_event_t::object_end:
        case Json::parse_event_t::array_end:
            containers.pop_back();
            break;
        default: break;
        }
        return true;
    };
    Json root = Json::parse(bytes, bytes + size, callback, true, false);
    if (!root.is_object()) return Empty(Status::InvalidRecord);
    auto event = root.find("event");
    if (event == root.end() || !event->is_string()) return Empty(Status::InvalidRecord);
    if (*event != "window-ready" && *event != "stage-event") return Empty(Status::Unavailable);
    auto details = root.find("details");
    if (details == root.end()) return Empty(Status::Unavailable);
    if (!details->is_object()) return Empty(Status::InvalidRecord);
    const Json* container = &*details;
    SourceEvent source_event = SourceEvent::WindowReady;
    std::optional<std::int64_t> stage_event;
    if (*event == "stage-event") {
        source_event = SourceEvent::StageEvent;
        auto stage = details->find("event");
        if (stage != details->end()) {
            if (!stage->is_number_integer() ||
                (stage->is_number_unsigned() && stage->get<std::uint64_t>() >
                 static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max())))
                return Empty(Status::InvalidRecord);
            stage_event = stage->get<std::int64_t>();
        }
        auto window = container->find("window");
        if (window == container->end()) return Empty(Status::Unavailable);
        if (!window->is_object()) return Empty(Status::InvalidRecord);
        container = &*window;
    }
    auto id = container->find("id");
    if (id == container->end()) return Empty(Status::Unavailable);
    if (!id->is_number_integer() || *id < 1 || *id > std::numeric_limits<std::int32_t>::max())
        return Empty(Status::InvalidRecord);
    return {Status::Candidate, Candidate{id->get<std::int32_t>(), file, source_event, stage_event}};
}
} // namespace

bool detail::SameIdentity(const FileIdentity& a, const FileIdentity& b) {
    return a.device == b.device && a.inode == b.inode && a.size == b.size &&
           a.mtime_seconds == b.mtime_seconds && a.mtime_nanoseconds == b.mtime_nanoseconds &&
           a.ctime_seconds == b.ctime_seconds && a.ctime_nanoseconds == b.ctime_nanoseconds &&
           a.uid == b.uid && a.gid == b.gid && a.mode == b.mode;
}
bool detail::StableRead(const FileIdentity& before, const FileIdentity& after,
                        const FileIdentity& current_path, std::size_t bytes_read) {
    return before.size >= 0 && static_cast<std::uint64_t>(before.size) == bytes_read &&
           SameIdentity(before, after) && SameIdentity(after, current_path);
}
Result ReadWindowRecord(const std::string& path, uid_t expected_uid, gid_t expected_gid) {
    if (path.empty() || path.size() > 4096 || path.find('\0') != std::string::npos)
        return Empty(Status::RejectedFile);
    Fd fd{::open(path.c_str(), O_RDONLY | O_CLOEXEC | O_NOFOLLOW | O_NONBLOCK)};
    if (fd.value < 0) return Empty(Status::Unavailable);
    struct stat before{}, after{}, current{};
    if (::fstat(fd.value, &before) != 0) return Empty(Status::Unavailable);
    if (!S_ISREG(before.st_mode) || before.st_uid != expected_uid || before.st_gid != expected_gid ||
        (before.st_mode & S_IWOTH) || before.st_size < 0 ||
        static_cast<std::uint64_t>(before.st_size) > kMaxRecordBytes)
        return Empty(Status::RejectedFile);
    std::array<char, kMaxRecordBytes + 1> buffer{};
    std::size_t count = 0;
    bool eof = false;
    // At most 16 reads, including EOF. Errors/EINTR are unavailable, not retries.
    for (unsigned calls = 0; calls < 16 && count < buffer.size(); ++calls) {
        auto n = ::read(fd.value, buffer.data() + count, buffer.size() - count);
        if (n < 0) return Empty(Status::Unavailable);
        if (n == 0) { eof = true; break; }
        count += static_cast<std::size_t>(n);
    }
    if (::fstat(fd.value, &after) != 0 || ::lstat(path.c_str(), &current) != 0)
        return Empty(Status::Unavailable);
    if (!eof || !detail::StableRead(Identity(before), Identity(after), Identity(current), count))
        return Empty(Status::Drift);
    try {
        return Parse(buffer.data(), count, Identity(before));
    } catch (const ParseRejected&) {
        return Empty(Status::InvalidRecord);
    } catch (const Json::exception&) {
        return Empty(Status::InvalidRecord);
    } catch (const std::bad_alloc&) {
        return Empty(Status::Unavailable);
    }
}
} // namespace westlake::host_window
