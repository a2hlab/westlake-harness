#ifndef OH_ADAPTER_APPLICATION_ATTRIBUTES_VERSION_CODE_H
#define OH_ADAPTER_APPLICATION_ATTRIBUTES_VERSION_CODE_H

#include <cstdint>

namespace oh_adapter::application_attributes {

struct VersionCodeParts {
    uint32_t major;
    uint32_t minor;
};

// These operations preserve bits. APK acceptance is a separate policy.
uint64_t ComposeVersionCodeBits(VersionCodeParts version) noexcept;
VersionCodeParts SplitVersionCodeBits(uint64_t bits) noexcept;
int64_t JavaLongFromVersionBits(uint64_t bits) noexcept;

}  // namespace oh_adapter::application_attributes

#endif  // OH_ADAPTER_APPLICATION_ATTRIBUTES_VERSION_CODE_H
