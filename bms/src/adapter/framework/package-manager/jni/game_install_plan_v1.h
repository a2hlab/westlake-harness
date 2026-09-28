/**
 * game_install_plan_v1.h
 *
 * Versioned, typed, size-bounded plan that BMS consumes after
 * oh_adapter_verify_and_parse_apk_v1 succeeds. Replaces the legacy pathname
 * manifest/copy route and the ad hoc nlohmann::json bridge: BMS must not
 * consume owner-authored JSON with caller-supplied path/uid/gid, and must
 * not accept a struct whose ABI it cannot pin (abiVersion/structSize are
 * checked before any field is read).
 *
 * GameInstallPlanV1 = sealedFd + apkSha256 + signerIdentity
 *                    + package/version + launcherActivity + primaryAbi
 * (per L02.A01 spec section 1).
 *
 * What this plan does NOT carry, by design (spec invariant 14 / H1 "typed
 * plan" gate): destination pathname, UID, GID or AccessToken. Those remain
 * BMS/installs-owned and are derived from platform allocators, never from
 * this struct.
 */
#ifndef GAME_INSTALL_PLAN_V1_H
#define GAME_INSTALL_PLAN_V1_H

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define GAME_INSTALL_PLAN_ABI_V1 1u
#define GAME_INSTALL_PLAN_MAX_SIGNERS 8u
#define GAME_INSTALL_PLAN_SHA256_HEX_CHARS 64u
#define GAME_INSTALL_PLAN_MAX_PACKAGE_NAME 256u
#define GAME_INSTALL_PLAN_MAX_VERSION_NAME 64u
#define GAME_INSTALL_PLAN_MAX_ACTIVITY_NAME 256u
#define GAME_INSTALL_PLAN_MAX_ABI_NAME 16u

typedef struct GameInstallPlanV1 {
    uint32_t abiVersion;   // must equal GAME_INSTALL_PLAN_ABI_V1
    uint32_t structSize;   // must equal sizeof(GameInstallPlanV1)

    // Ownership of sealedFd transfers to the receiver on a successful
    // AtomicPublishVerifiedApk Binder call; the sender must not use it
    // afterward. Never a caller-supplied pathname.
    int32_t sealedFd;

    uint32_t schemeVersion;  // 2 or 3, from real v2/v3 cryptographic verification
    char apkSha256Hex[GAME_INSTALL_PLAN_SHA256_HEX_CHARS + 1u];

    uint32_t signerCount;
    char signerSha256Hex[GAME_INSTALL_PLAN_MAX_SIGNERS][GAME_INSTALL_PLAN_SHA256_HEX_CHARS + 1u];

    char packageName[GAME_INSTALL_PLAN_MAX_PACKAGE_NAME];
    uint32_t versionCode;
    char versionName[GAME_INSTALL_PLAN_MAX_VERSION_NAME];
    char launcherActivity[GAME_INSTALL_PLAN_MAX_ACTIVITY_NAME];
    char primaryAbi[GAME_INSTALL_PLAN_MAX_ABI_NAME];
    uint32_t debuggable;  // 0 or 1
} GameInstallPlanV1;

enum GameInstallPlanValidationStatus {
    GAME_INSTALL_PLAN_OK = 0,
    GAME_INSTALL_PLAN_BAD_ABI = -3001,
    GAME_INSTALL_PLAN_BAD_STRUCT_SIZE = -3002,
    GAME_INSTALL_PLAN_BAD_FD = -3003,
    GAME_INSTALL_PLAN_BAD_SCHEME = -3004,
    GAME_INSTALL_PLAN_BAD_DIGEST = -3005,
    GAME_INSTALL_PLAN_BAD_SIGNER_COUNT = -3006,
    GAME_INSTALL_PLAN_BAD_SIGNER_HEX = -3007,
    GAME_INSTALL_PLAN_BAD_PACKAGE_NAME = -3008,
    GAME_INSTALL_PLAN_BAD_LAUNCHER_ACTIVITY = -3009,
    GAME_INSTALL_PLAN_BAD_PRIMARY_ABI = -3010,
    GAME_INSTALL_PLAN_MISSING_ARM64_ABI = -3011,
    GAME_INSTALL_PLAN_UNSEALED_STRINGS = -3012,
};

/**
 * Platform-side validator: BMS calls this before trusting any field.
 * Never a substitute for the fd's own verified provenance (the sealedFd
 * must have come from a successful oh_adapter_verify_and_parse_apk_v1
 * call in the same process, never reconstructed from caller-supplied data).
 *
 * Checks: ABI/struct size pin, fd is non-negative, scheme is 2 or 3, all
 * hex digest/signer fields are exactly 64 lowercase hex chars and NUL
 * terminated within bounds, package/activity/abi strings are NUL
 * terminated within their bounds and non-empty, primaryAbi is exactly
 * "arm64-v8a" (A01 game-min profile: arm64-v8a only, per spec section 2).
 */
int GameInstallPlanV1_Validate(const GameInstallPlanV1* plan);

#ifdef __cplusplus
}
#endif

#endif  // GAME_INSTALL_PLAN_V1_H
