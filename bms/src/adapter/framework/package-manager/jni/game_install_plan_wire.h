#ifndef OH_ADAPTER_GAME_INSTALL_PLAN_WIRE_H
#define OH_ADAPTER_GAME_INSTALL_PLAN_WIRE_H
#include "game_install_plan_v1.h"
#include <stdint.h>
#ifdef __cplusplus
extern "C" {
#endif
#define GAME_INSTALL_PLAN_WIRE_ABI 1u
// Legacy game fields keep the exact GameInstallPlanV1 prefix layout. The
// separately negotiated prepass wire has its own struct size; it is never
// accepted as a GameInstallPlanV1 or an ApkInstallPlanV2 by size coercion.
typedef struct GameInstallPlanWire {
    uint32_t abiVersion, structSize;
    int32_t apkFd;
    uint32_t schemeVersion;
    char apkSha256Hex[GAME_INSTALL_PLAN_SHA256_HEX_CHARS + 1u];
    uint32_t signerCount;
    char signerSha256Hex[GAME_INSTALL_PLAN_MAX_SIGNERS][GAME_INSTALL_PLAN_SHA256_HEX_CHARS + 1u];
    char packageName[GAME_INSTALL_PLAN_MAX_PACKAGE_NAME];
    uint32_t versionCode;
    char versionName[GAME_INSTALL_PLAN_MAX_VERSION_NAME];
    char launcherActivity[GAME_INSTALL_PLAN_MAX_ACTIVITY_NAME];
    char primaryAbi[GAME_INSTALL_PLAN_MAX_ABI_NAME];
    uint32_t debuggable;
    int32_t prepassFd;
    uint32_t reservedZero;
    uint64_t prepassByteLength;
    char prepassSha256Hex[GAME_INSTALL_PLAN_SHA256_HEX_CHARS + 1u];
    uint8_t reservedTail[7];
} GameInstallPlanWire;
enum GameInstallPlanWireStatus {
    GAME_INSTALL_PLAN_WIRE_OK = 0,
    GAME_INSTALL_PLAN_WIRE_BAD_ABI = -6201,
    GAME_INSTALL_PLAN_WIRE_BAD_STRUCT_SIZE = -6202,
    GAME_INSTALL_PLAN_WIRE_BAD_LEGACY_FIELDS = -6203,
    GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_FD = -6204,
    GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_LENGTH = -6205,
    GAME_INSTALL_PLAN_WIRE_BAD_PREPASS_DIGEST = -6206,
    GAME_INSTALL_PLAN_WIRE_RESERVED_NONZERO = -6207,
    GAME_INSTALL_PLAN_WIRE_VERSION_REQUIRES_V2 = -6208,
};
// Legacy structural check; like GameInstallPlanV1 it does not authenticate the
// caller or inspect descriptor contents. Use the new V2 path for general APKs.
int GameInstallPlanWire_Validate(const GameInstallPlanWire* plan);
// No truncation: a nonzero major returns VERSION_REQUIRES_V2 and changes nothing.
int GameInstallPlanWire_TrySetVersion(GameInstallPlanWire* plan,
    uint32_t majorBits, uint32_t minorBits);
#ifdef __cplusplus
}
#endif
#endif
