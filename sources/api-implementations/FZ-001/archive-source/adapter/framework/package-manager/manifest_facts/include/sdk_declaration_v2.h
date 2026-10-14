#ifndef OH_ADAPTER_SDK_DECLARATION_V2_H
#define OH_ADAPTER_SDK_DECLARATION_V2_H

#include <cstdint>
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace oh_adapter::manifest_facts {

struct SdkAttributeV2 {
    bool present = false;
    uint8_t type = 0;
    uint32_t bits = 0;
    std::string text;
};
struct ExtensionSdkDeclarationV2 {
    SdkAttributeV2 sdk;
    SdkAttributeV2 minimum;
};
struct UsesSdkDeclarationV2 {
    SdkAttributeV2 minimum;
    SdkAttributeV2 target;
    SdkAttributeV2 maximum;
    std::vector<ExtensionSdkDeclarationV2> extensions;
};

// Supplied by the product/profile owner, never inferred from the APK or OH version.
struct SdkProfileV2 {
    int32_t sdkVersion = 0;
    std::string codename;
    std::vector<std::string> activeCodenames;
    std::vector<std::string> knownCodenames;
    std::map<int32_t, int32_t> extensionVersions;
};

enum class SdkCompatibilityVerdictV2 {
    READY, OLDER_SDK, NEWER_SDK, MANIFEST_MALFORMED, PARSE_UNEXPECTED_EXCEPTION, PROFILE_UNAVAILABLE,
};
enum class SdkFailureStageV2 { NONE, PROFILE, TARGET, MINIMUM, MAXIMUM, EXTENSION };
struct ResolvedSdkV2 {
    int32_t minimum = 1;
    int32_t target = 0;
    int32_t maximum = INT32_MAX;
    std::map<int32_t, int32_t> minimumExtensions;
};
struct SdkCompatibilityResultV2 {
    SdkCompatibilityVerdictV2 verdict = SdkCompatibilityVerdictV2::PROFILE_UNAVAILABLE;
    SdkFailureStageV2 stage = SdkFailureStageV2::PROFILE;
    std::string reason;
    std::optional<ResolvedSdkV2> resolved;
};

}  // namespace oh_adapter::manifest_facts
#endif
