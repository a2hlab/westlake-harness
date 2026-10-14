#ifndef OH_ADAPTER_SDK_RULES_H
#define OH_ADAPTER_SDK_RULES_H
#include "../../manifest_facts/include/sdk_declaration_v2.h"

namespace oh_adapter::application_attributes {
// Evaluates declarations in document order; a later tag never masks an earlier error.
manifest_facts::SdkCompatibilityResultV2 EvaluateSdkRequirements(
    const std::vector<manifest_facts::UsesSdkDeclarationV2>& declarations,
    const manifest_facts::SdkProfileV2& profile, bool apkInApex);
// Declaration-only legacy path. Never asserts compatibility without a profile.
std::optional<manifest_facts::ResolvedSdkV2> ResolveNumericSdkDeclarations(
    const std::vector<manifest_facts::UsesSdkDeclarationV2>& declarations);
}
#endif
