// Offline replay only. No device access, credential change, IPC or source mutation.
#include "host_window_record_reader.h"
#include <iostream>
#include <unistd.h>

int main(int argc, char** argv) {
    if (argc != 2) return 2;
    namespace hw = westlake::host_window;
    const auto result = hw::ReadWindowRecord(argv[1], getuid(), getgid());
    const char* status = "unknown";
    switch (result.status) {
        case hw::Status::Candidate: status = "Candidate"; break;
        case hw::Status::Unavailable: status = "Unavailable"; break;
        case hw::Status::RejectedFile: status = "RejectedFile"; break;
        case hw::Status::InvalidRecord: status = "InvalidRecord"; break;
        case hw::Status::Drift: status = "Drift"; break;
    }
    std::cout << "{\"status\":\"" << status << "\",\"local_uid\":" << getuid()
              << ",\"local_gid\":" << getgid();
    if (result.candidate) {
        const auto& c = *result.candidate;
        const bool ready = c.source_event == hw::SourceEvent::WindowReady;
        // Exact pure admission expression from accepted session_recovery.cpp:3-6.
        // This does not invoke session recovery or establish OH access/foreground.
        const bool foreground = ready ||
            (c.source_event == hw::SourceEvent::StageEvent && c.stage_event &&
             (*c.stage_event == 1 || *c.stage_event == 2));
        std::cout << ",\"id\":" << c.window_id << ",\"source_event\":\""
                  << (ready ? "WindowReady" : "StageEvent") << "\",\"stage\":";
        if (c.stage_event) std::cout << *c.stage_event;
        else std::cout << "null";
        std::cout << ",\"foreground_predicate\":" << (foreground ? "true" : "false");
    } else {
        std::cout << ",\"id\":null,\"source_event\":null,\"stage\":null,\"foreground_predicate\":null";
    }
    std::cout << "}\n";
    return 0; // Invocation completed; status and predicate are separate results.
}
