/*
 * Keep the ART abort diagnostic boundary C-only.  AOSP16 intentionally hides
 * GetFaultMessageForAbortLogging() inside namespace art, while appspawn-x is
 * built by the OH clang15 cohort.  Returning std::string across those two C++
 * runtimes is neither linkable nor ABI-safe.
 */

#include <algorithm>
#include <cstddef>
#include <cstring>
#include <string>

namespace art {
std::string GetFaultMessageForAbortLogging();
}

extern "C" __attribute__((visibility("default"))) std::size_t
westlake_art_copy_fault_message_for_abort_logging(char* output,
                                                   std::size_t capacity) {
    const std::string message = art::GetFaultMessageForAbortLogging();
    if (output != nullptr && capacity != 0) {
        const std::size_t copied = std::min(message.size(), capacity - 1);
        std::memcpy(output, message.data(), copied);
        output[copied] = '\0';
    }
    return message.size();
}
