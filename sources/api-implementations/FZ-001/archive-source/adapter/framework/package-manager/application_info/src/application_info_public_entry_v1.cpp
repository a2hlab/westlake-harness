#include "application_info_public_entry_v1.h"

#include "application_info_runtime_owner_v1.h"
#include "application_info_runtime_v1.h"

#include <atomic>

namespace oh_adapter::application_info {
namespace {
std::atomic<uint64_t> requestSequence {1};
}

std::string QueryCanonicalApplicationInfoEntryV1(
    const std::string& packageName, uint64_t flags, uint32_t userId,
    int32_t callingUid)
{
    const std::string requestId = "android-getApplicationInfo-" +
        std::to_string(requestSequence.fetch_add(1));
    // The projection precondition may become available after process start.
    // Retry the idempotent owner here instead of letting an early missing
    // store/facts directory permanently disable A05 or the whole adapter.
    std::string startError;
    StartProductApplicationInfoRuntimeV1(&startError);
    return QueryApplicationInfoRuntimeJsonV1(
        requestId, packageName, flags, userId, callingUid);
}

}  // namespace oh_adapter::application_info
