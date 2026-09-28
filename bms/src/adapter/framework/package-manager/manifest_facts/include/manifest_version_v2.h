#ifndef OH_ADAPTER_MANIFEST_VERSION_V2_H
#define OH_ADAPTER_MANIFEST_VERSION_V2_H

#include <cstdint>

namespace oh_adapter::manifest_facts {

// UNKNOWN is an unparsed/legacy value, distinct from an XML default of zero.
enum class VersionValueSourceV2 { UNKNOWN, DEFAULT, EXPLICIT };

struct VersionFieldV2 {
    uint32_t bits = 0;
    bool present = false;
    VersionValueSourceV2 source = VersionValueSourceV2::UNKNOWN;
};

struct ManifestVersionV2 {
    VersionFieldV2 major;
    VersionFieldV2 minor;
};

}  // namespace oh_adapter::manifest_facts

#endif  // OH_ADAPTER_MANIFEST_VERSION_V2_H
