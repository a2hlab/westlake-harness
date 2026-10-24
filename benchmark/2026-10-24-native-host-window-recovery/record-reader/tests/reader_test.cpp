#include "host_window_record_reader.h"
#include <chrono>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <sys/stat.h>
#include <unistd.h>
#include <vector>
using namespace westlake::host_window;
namespace fs = std::filesystem;
static unsigned passed = 0;
static void Check(bool ok, const std::string& name) {
    if (!ok) throw std::runtime_error(name);
    ++passed;
    std::cout << "PASS " << name << '\n';
}
static std::string Bytes(const fs::path& p) {
    std::ifstream f(p, std::ios::binary);
    return {std::istreambuf_iterator<char>(f), std::istreambuf_iterator<char>()};
}
static void Put(const fs::path& p, const std::string& data, mode_t mode = 0660) {
    std::ofstream f(p, std::ios::binary | std::ios::trunc);
    f.write(data.data(), data.size()); f.close();
    if (!f || ::chmod(p.c_str(), mode)) throw std::runtime_error("fixture write failed");
}
int main(int argc, char** argv) {
    try {
        if (argc != 2) throw std::runtime_error("fresh fixture directory argument required");
        fs::path dir(argv[1]);
        if (!fs::create_directory(dir)) throw std::runtime_error("fixture directory already exists");
        const auto file = dir / "record.json";
        const std::string ready = R"({"event":"window-ready","details":{"id":32}})";
        const std::string stage = R"({"event":"stage-event","details":{"window":{"id":62}}})";
        auto read = [&] { return ReadWindowRecord(file.string(), ::getuid(), ::getgid()); };
        for (const auto& item : std::vector<std::pair<std::string,int>>{{ready,32},{stage,62}}) {
            Put(file, item.first);
            struct stat a{}, b{}; ::stat(file.c_str(), &a);
            auto r = read(); ::stat(file.c_str(), &b);
            Check(r.status == Status::Candidate && r.candidate && r.candidate->window_id == item.second &&
                  r.candidate->source_event == (item.second == 32 ? SourceEvent::WindowReady : SourceEvent::StageEvent) &&
                  !r.candidate->stage_event,
                  "0660 candidate " + std::to_string(item.second));
            Check(r.candidate->file.device == static_cast<std::uint64_t>(a.st_dev) &&
                  r.candidate->file.inode == a.st_ino && r.candidate->file.size == a.st_size &&
                  r.candidate->file.uid == ::getuid() && r.candidate->file.gid == ::getgid() &&
                  (r.candidate->file.mode & 0777) == 0660, "candidate file identity");
            Check(Bytes(file) == item.first && a.st_size == b.st_size && a.st_ino == b.st_ino &&
                  a.st_mode == b.st_mode, "input unchanged");
        }
        for (int event : {1, 2, 4}) {
            Put(file, std::string(R"({"event":"stage-event","details":{"event":)") +
                std::to_string(event) + R"(,"window":{"id":62}}})");
            auto r = read();
            Check(r.status == Status::Candidate && r.candidate && r.candidate->window_id == 62 &&
                  r.candidate->source_event == SourceEvent::StageEvent && r.candidate->stage_event == event,
                  "raw stage SHOWN/ACTIVE/HIDDEN preserved " + std::to_string(event));
        }
        Put(file, R"({"event":"stage-event","details":{"event":true,"window":{"id":62}}})");
        Check(read().status == Status::InvalidRecord && !read().candidate, "noninteger stage rejected");
        unsigned i = 0;
        for (auto data : {R"({"event":"foreground","details":{}})",
                          R"({"event":"background","details":{}})",
                          R"({"event":"window-ready","details":{}})",
                          R"({"event":"stage-event","details":{"window":{}}})",
                          R"({"event":"stage-event","details":{}})",
                          R"({"event":"window-ready"})"}) {
            Put(file, data); auto r = read();
            Check(r.status == Status::Unavailable && !r.candidate, "unavailable event " + std::to_string(++i));
        }
        std::vector<std::string> bad = {
            R"({"event":"window-ready","details":{"id":32,"id":62}})",
            R"({"event":"window-ready","details":{"id":32,"\u0069d":62}})",
            R"({"event":"window-ready","event":"stage-event","details":{"id":32}})",
            ready + " trailing", ready + "{}", ready.substr(0, ready.size()-1),
            "[]", "null", "{}", R"({"event":true})", R"({"event":"window-ready","details":[]})",
            R"({"event":"stage-event","details":{"window":null}})",
            R"({"event":"window-ready","details":{"id":32},"x":{"a":1,"a":2}})",
            ready + std::string(1, '\0'), ready + std::string("\0junk", 5),
            R"({"event":"window-ready","details":{"id":32},"x":")" + std::string(1, char(0xff)) + "\"}"
        };
        for (auto id : {"0","-1","true","false","null","1.5","32.0","1e1","\"62\"",
                        "2147483648","18446744073709551615","-9223372036854775809","1e999"})
            bad.push_back(std::string(R"({"event":"window-ready","details":{"id":)") + id + "}}");
        i = 0;
        for (const auto& data : bad) {
            Put(file, data); auto r = read();
            Check(r.status == Status::InvalidRecord && !r.candidate, "invalid JSON/id " + std::to_string(++i));
        }
        Put(file, R"({"event":"window-ready","details":{"id":2147483647}})");
        Check(read().candidate->window_id == 2147483647, "maximum int32");
        auto nested = [&](unsigned n) {
            return std::string(R"({"event":"window-ready","details":{"id":32},"extra":)") +
                   std::string(n, '[') + "0" + std::string(n, ']') + "}";
        };
        Put(file, nested(15)); Check(read().status == Status::Candidate, "depth16 allowed");
        Put(file, nested(16)); Check(read().status == Status::InvalidRecord, "depth17 rejected");
        Put(file, ready + std::string(kMaxRecordBytes-ready.size(), ' '));
        Check(read().status == Status::Candidate, "8192 bytes allowed");
        Put(file, ready + std::string(kMaxRecordBytes-ready.size()+1, ' '));
        Check(read().status == Status::RejectedFile, "8193 bytes rejected");
        Put(file, ready, 0666); Check(read().status == Status::RejectedFile, "world writable rejected");
        Put(file, ready);
        Check(ReadWindowRecord(file.string(), ::getuid()+1, ::getgid()).status == Status::RejectedFile,
              "wrong expected UID rejected");
        Check(ReadWindowRecord(file.string(), ::getuid(), ::getgid()+1).status == Status::RejectedFile,
              "wrong expected GID rejected");
        fs::create_symlink(file.filename(), dir/"link");
        Check(!ReadWindowRecord((dir/"link").string(), ::getuid(), ::getgid()).candidate, "symlink rejected");
        if (::mkfifo((dir/"fifo").c_str(),0600)) throw std::runtime_error("mkfifo failed");
        auto begin = std::chrono::steady_clock::now();
        auto fifo = ReadWindowRecord((dir/"fifo").string(), ::getuid(), ::getgid());
        Check(fifo.status == Status::RejectedFile && !fifo.candidate &&
              std::chrono::steady_clock::now()-begin < std::chrono::seconds(1), "FIFO nonblocking rejection");
        Check(ReadWindowRecord(dir.string(), ::getuid(), ::getgid()).status == Status::RejectedFile,
              "directory rejected");
        Check(ReadWindowRecord((dir/"missing").string(), ::getuid(), ::getgid()).status == Status::Unavailable,
              "missing unavailable");
        Check(ReadWindowRecord(file.string()+std::string(1,'\0')+"x", ::getuid(), ::getgid()).status ==
              Status::RejectedFile, "embedded NUL path rejected");
        auto original = read().candidate->file;
        Check(detail::StableRead(original, original, original, original.size), "stable production predicate");
        Check(!detail::StableRead(original, original, original, original.size-1), "short read rejected");
        std::vector<FileIdentity> changed;
        auto c = original; ++c.device; changed.push_back(c);
        c=original; ++c.inode; changed.push_back(c);
        c=original; --c.size; changed.push_back(c);
        c=original; ++c.mtime_seconds; changed.push_back(c);
        c=original; ++c.mtime_nanoseconds; changed.push_back(c);
        c=original; ++c.ctime_seconds; changed.push_back(c);
        c=original; ++c.ctime_nanoseconds; changed.push_back(c);
        c=original; ++c.uid; changed.push_back(c);
        c=original; ++c.gid; changed.push_back(c);
        c=original; c.mode |= S_IWOTH; changed.push_back(c);
        i=0;
        for (const auto& drift : changed) {
            Check(!detail::StableRead(original, drift, original, original.size),
                  "post-fstat drift " + std::to_string(++i));
            Check(!detail::StableRead(original, original, drift, original.size),
                  "current path drift " + std::to_string(i));
        }
        // Distinct objects may use the same key; a global duplicate-key set is wrong.
        Put(file, R"({"event":"window-ready","details":{"id":32},"other":{"id":62}})");
        Check(read().status == Status::Candidate, "keys isolated by object");
        std::cout << "{\"passed\":" << passed << ",\"failed\":0,\"production_reader\":true}\n";
        return 0;
    } catch (const std::exception& e) {
        std::cerr << "FAIL " << e.what() << '\n';
        return 1;
    }
}
