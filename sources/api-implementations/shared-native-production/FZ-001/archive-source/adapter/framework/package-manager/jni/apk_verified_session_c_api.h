/**
 * Stable C ABI used by libbms to consume one verified immutable APK session.
 */
#pragma once

#include <stdint.h>
#include "game_install_plan_v1.h"

#ifdef __cplusplus
extern "C" {
#endif

#define OH_ADAPTER_VERIFIED_APK_ABI_V1 1u
#define OH_ADAPTER_MAX_APK_SIGNERS 64u
#define OH_ADAPTER_SHA256_HEX_CHARS 64u

typedef struct OhAdapterApkLineageV1 {
    char sha256Hex[OH_ADAPTER_SHA256_HEX_CHARS + 1u];
    uint32_t capabilities;
} OhAdapterApkLineageV1;

typedef struct OhAdapterVerifiedApkV1 {
    uint32_t abiVersion;
    uint32_t structSize;
    int32_t sealedApkFd;
    uint32_t schemeVersion;
    uint32_t v3BlockId;
    char apkSha256Hex[OH_ADAPTER_SHA256_HEX_CHARS + 1u];
    uint32_t currentSignerCount;
    char currentSignerSha256Hex[OH_ADAPTER_MAX_APK_SIGNERS]
        [OH_ADAPTER_SHA256_HEX_CHARS + 1u];
    uint32_t lineageCount;
    OhAdapterApkLineageV1 lineage[OH_ADAPTER_MAX_APK_SIGNERS];
} OhAdapterVerifiedApkV1;

enum OhAdapterVerifiedApkStatusV1 {
    OH_ADAPTER_APK_VERIFY_OK = 0,
    OH_ADAPTER_APK_VERIFY_BAD_ARGUMENT = -2001,
    OH_ADAPTER_APK_VERIFY_SNAPSHOT_FAILED = -2002,
    OH_ADAPTER_APK_VERIFY_TRANSPORT_FAILED = -2003,
    OH_ADAPTER_APK_VERIFY_RESPONSE_REJECTED = -2004,
    OH_ADAPTER_APK_VERIFY_MANIFEST_FAILED = -2005,
    OH_ADAPTER_APK_VERIFY_OUTPUT_TOO_SMALL = -2006,
    OH_ADAPTER_APK_VERIFY_PREPASS_FAILED = -2007,
};

/**
 * Exact ABI guard required before resolving/calling
 * oh_adapter_verify_and_parse_apk_v1. New BMS + old installer therefore
 * fails before the call; old BMS + new installer is rejected by the
 * GameInstallPlanV1 struct-size gate.
 */
uint64_t oh_adapter_game_install_plan_abi_v1(void);

/**
 * Open the APK ingress once, create and verify a sealed snapshot, parse the
 * minimum game-install manifest from that same fd, and transfer the fd into
 * a typed plan. No JSON path/uid/gid/destination fields cross this boundary.
 */
int oh_adapter_verify_and_parse_apk_v1(const char* apkPath, int32_t userId,
    GameInstallPlanV1* plan);

void oh_adapter_close_game_install_plan_v1(GameInstallPlanV1* plan);

/* Retained only so an already-built old caller can close its own old struct. */
void oh_adapter_close_verified_apk_v1(OhAdapterVerifiedApkV1* verifiedApk);

#ifdef __cplusplus
}
#endif
