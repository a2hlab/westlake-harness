#include "game_install_plan_wire.h"
#include "apk_install_plan_v2.h"
_Static_assert(sizeof(GameInstallPlanV1) == 1208, "published game V1 unchanged");
_Static_assert(sizeof(GameInstallPlanWire) == 1296, "legacy prepass wire size");
_Static_assert(sizeof(ApkInstallFdV2) == 88, "FD span size");
_Static_assert(sizeof(ApkInstallArtifactV2) == 312, "artifact size");
_Static_assert(sizeof(ApkInstallPlanV2) == 21032, "V2 size");
_Static_assert(_Alignof(ApkInstallPlanV2) == 8, "SPC50_V2_ALIGNMENT_8");
#define PREFIX(field) _Static_assert(offsetof(GameInstallPlanWire, field) == offsetof(GameInstallPlanV1, field), "V1 prefix " #field)
PREFIX(abiVersion); PREFIX(structSize); PREFIX(schemeVersion); PREFIX(apkSha256Hex); PREFIX(signerCount);
PREFIX(signerSha256Hex); PREFIX(packageName); PREFIX(versionCode); PREFIX(versionName); PREFIX(launcherActivity);
PREFIX(primaryAbi); PREFIX(debuggable);
_Static_assert(offsetof(GameInstallPlanWire, apkFd) == offsetof(GameInstallPlanV1, sealedFd), "FD prefix");
_Static_assert(offsetof(GameInstallPlanWire, prepassFd) == sizeof(GameInstallPlanV1), "append only legacy wire");
int install_wire_c_probe(const ApkInstallPlanV2* plan)
{
    uint64_t (*abi)(void) = oh_adapter_apk_install_plan_abi_v2;
    if (abi() != (((uint64_t)APK_INSTALL_PLAN_ABI_V2 << 32) | sizeof(ApkInstallPlanV2))) return -1;
    return ApkInstallPlanV2_Validate(plan);
}
