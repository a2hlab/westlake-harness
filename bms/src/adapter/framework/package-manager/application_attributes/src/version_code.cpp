#include "version_code.h"

#include <limits>

namespace oh_adapter::application_attributes {

uint64_t ComposeVersionCodeBits(VersionCodeParts version) noexcept
{
    return (static_cast<uint64_t>(version.major) << 32U) | version.minor;
}

VersionCodeParts SplitVersionCodeBits(uint64_t bits) noexcept
{
    return {static_cast<uint32_t>(bits >> 32U), static_cast<uint32_t>(bits)};
}

int64_t JavaLongFromVersionBits(uint64_t bits) noexcept
{
    if (bits <= static_cast<uint64_t>(std::numeric_limits<int64_t>::max())) {
        return static_cast<int64_t>(bits);
    }
    // The complement fits int64_t; avoid an out-of-range unsigned-to-signed cast.
    return -INT64_C(1) - static_cast<int64_t>(std::numeric_limits<uint64_t>::max() - bits);
}

}  // namespace oh_adapter::application_attributes
