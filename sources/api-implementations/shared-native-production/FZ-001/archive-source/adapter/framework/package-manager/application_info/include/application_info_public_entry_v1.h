#ifndef OH_ADAPTER_APPLICATION_INFO_PUBLIC_ENTRY_V1_H
#define OH_ADAPTER_APPLICATION_INFO_PUBLIC_ENTRY_V1_H

#include <cstdint>
#include <string>

namespace oh_adapter::application_info {

// Native public-entry core shared by the JNI export and executable host seam.
std::string QueryCanonicalApplicationInfoEntryV1(
    const std::string& packageName, uint64_t flags, uint32_t userId,
    int32_t callingUid);

}  // namespace oh_adapter::application_info

#endif  // OH_ADAPTER_APPLICATION_INFO_PUBLIC_ENTRY_V1_H
