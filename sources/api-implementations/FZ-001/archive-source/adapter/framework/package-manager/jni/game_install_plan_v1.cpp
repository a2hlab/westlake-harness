#include "game_install_plan_v1.h"

#include <cstring>

namespace {

bool IsLowerHexSha256(const char* s)
{
    size_t len = 0;
    while (len <= GAME_INSTALL_PLAN_SHA256_HEX_CHARS && s[len] != '\0') ++len;
    if (len != GAME_INSTALL_PLAN_SHA256_HEX_CHARS) return false;
    for (size_t i = 0; i < len; ++i) {
        const char c = s[i];
        const bool isDigit = c >= '0' && c <= '9';
        const bool isLowerHex = c >= 'a' && c <= 'f';
        if (!isDigit && !isLowerHex) return false;
    }
    return true;
}

bool IsBoundedNulTerminated(const char* s, size_t bufSize)
{
    for (size_t i = 0; i < bufSize; ++i) {
        if (s[i] == '\0') return i > 0;  // non-empty and terminated within bounds
    }
    return false;  // no terminator within the buffer
}

}  // namespace

extern "C" int GameInstallPlanV1_Validate(const GameInstallPlanV1* plan)
{
    if (plan == nullptr) return GAME_INSTALL_PLAN_BAD_STRUCT_SIZE;
    if (plan->abiVersion != GAME_INSTALL_PLAN_ABI_V1) return GAME_INSTALL_PLAN_BAD_ABI;
    if (plan->structSize != sizeof(GameInstallPlanV1)) return GAME_INSTALL_PLAN_BAD_STRUCT_SIZE;
    if (plan->sealedFd < 0) return GAME_INSTALL_PLAN_BAD_FD;
    if (plan->schemeVersion != 2u && plan->schemeVersion != 3u) return GAME_INSTALL_PLAN_BAD_SCHEME;
    if (!IsLowerHexSha256(plan->apkSha256Hex)) return GAME_INSTALL_PLAN_BAD_DIGEST;
    if (plan->signerCount == 0 || plan->signerCount > GAME_INSTALL_PLAN_MAX_SIGNERS) {
        return GAME_INSTALL_PLAN_BAD_SIGNER_COUNT;
    }
    for (uint32_t i = 0; i < plan->signerCount; ++i) {
        if (!IsLowerHexSha256(plan->signerSha256Hex[i])) return GAME_INSTALL_PLAN_BAD_SIGNER_HEX;
    }
    if (!IsBoundedNulTerminated(plan->packageName, sizeof(plan->packageName))) {
        return GAME_INSTALL_PLAN_BAD_PACKAGE_NAME;
    }
    if (!IsBoundedNulTerminated(plan->launcherActivity, sizeof(plan->launcherActivity))) {
        return GAME_INSTALL_PLAN_BAD_LAUNCHER_ACTIVITY;
    }
    if (!IsBoundedNulTerminated(plan->primaryAbi, sizeof(plan->primaryAbi))) {
        return GAME_INSTALL_PLAN_BAD_PRIMARY_ABI;
    }
    // A01 game-min profile: single base.apk, arm64-v8a only (spec section 2:
    // "APK 必须声明/包含 arm64-v8a"). Compatibility field only; native
    // extraction/layout verification is L02.A07/A12 scope.
    if (std::strcmp(plan->primaryAbi, "arm64-v8a") != 0) {
        return GAME_INSTALL_PLAN_MISSING_ARM64_ABI;
    }
    if (plan->debuggable != 0 && plan->debuggable != 1) return GAME_INSTALL_PLAN_UNSEALED_STRINGS;
    return GAME_INSTALL_PLAN_OK;
}
