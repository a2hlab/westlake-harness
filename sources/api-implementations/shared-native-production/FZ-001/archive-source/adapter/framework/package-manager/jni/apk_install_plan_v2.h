#ifndef OH_ADAPTER_APK_INSTALL_PLAN_V2_H
#define OH_ADAPTER_APK_INSTALL_PLAN_V2_H
#include "prepass_context_wire.h"
#include <stddef.h>
#include <stdint.h>
#ifdef __cplusplus
#define OH_APK_INSTALL_WIRE_ALIGN8 alignas(8)
extern "C" {
#else
#define OH_APK_INSTALL_WIRE_ALIGN8 _Alignas(8)
#endif
#define APK_INSTALL_PLAN_ABI_V2 2u
#define APK_INSTALL_PAYLOAD_SCHEMA_V2 2u
#define APK_INSTALL_PLAN_V2_MAX_ARTIFACTS 64u
#define APK_INSTALL_PLAN_V2_ARTIFACT_ID_CAPACITY 128u
#define APK_INSTALL_PLAN_V2_CAP_FULL_VERSION UINT64_C(1)
#define APK_INSTALL_PLAN_V2_CAP_GENERAL_APK UINT64_C(2)
#define APK_INSTALL_PLAN_V2_CAP_SEALED_INPUTS UINT64_C(4)
#define APK_INSTALL_PLAN_V2_CAPABILITIES UINT64_C(7)
#define APK_INSTALL_VERSION_MAJOR_PRESENT 1u
#define APK_INSTALL_VERSION_MINOR_PRESENT 2u
#define APK_INSTALL_VERSION_SOURCE_DEFAULT 1u
#define APK_INSTALL_VERSION_SOURCE_EXPLICIT 2u
#define APK_INSTALL_ARTIFACT_BASE 0u
#define APK_INSTALL_ARTIFACT_SPLIT_CONFIG 1u
#define APK_INSTALL_ARTIFACT_SPLIT_FEATURE 2u

typedef struct ApkInstallFdV2 {
    OH_APK_INSTALL_WIRE_ALIGN8 int32_t fd;
    uint32_t reservedZero;
    uint64_t byteLength;
    char sha256Hex[65];
    uint8_t reservedTail[7];
} ApkInstallFdV2;
// Each APK's prepass binds that APK's actual digest. A set never relabels every
// member's ELF facts as if they all came from the base APK.
typedef struct ApkInstallArtifactV2 {
    uint32_t role;
    uint32_t reservedZero;
    char artifactId[APK_INSTALL_PLAN_V2_ARTIFACT_ID_CAPACITY];
    ApkInstallFdV2 apk;
    ApkInstallFdV2 prepass;
} ApkInstallArtifactV2;
typedef struct ApkInstallPlanV2 {
    OH_APK_INSTALL_WIRE_ALIGN8 uint32_t abiVersion;
    uint32_t structSize;
    uint64_t capabilities;
    PrepassContextWire context;
    uint32_t versionMajorBits;
    uint32_t versionMinorBits;
    uint32_t versionPresenceBits;
    uint32_t majorSource;
    uint32_t minorSource;
    uint32_t artifactCount;
    uint32_t payloadSchemaVersion;
    uint32_t reservedZero;
    char artifactSetSha256Hex[65];
    uint8_t reservedTail[7];
    // Canonical schema V2 JSON carries the complete parser receipt and signing
    // facts. Optional versionName and launcher are not mandatory wire fields.
    ApkInstallFdV2 manifestSigning;
    ApkInstallArtifactV2 artifacts[APK_INSTALL_PLAN_V2_MAX_ARTIFACTS];
} ApkInstallPlanV2;
enum ApkInstallPlanStatusV2 {
    APK_INSTALL_PLAN_V2_OK = 0,
    APK_INSTALL_PLAN_V2_BAD_ARGUMENT = -6301,
    APK_INSTALL_PLAN_V2_BAD_ABI = -6302,
    APK_INSTALL_PLAN_V2_BAD_SIZE = -6303,
    APK_INSTALL_PLAN_V2_BAD_CAPABILITIES = -6304,
    APK_INSTALL_PLAN_V2_BAD_RESERVED = -6305,
    APK_INSTALL_PLAN_V2_BAD_CONTEXT = -6306,
    APK_INSTALL_PLAN_V2_BAD_VERSION = -6307,
    APK_INSTALL_PLAN_V2_BAD_ARTIFACT_SET = -6308,
    APK_INSTALL_PLAN_V2_BAD_FD = -6309,
    APK_INSTALL_PLAN_V2_BAD_LENGTH = -6310,
    APK_INSTALL_PLAN_V2_BAD_DIGEST = -6311,
    APK_INSTALL_PLAN_V2_UNSEALED_FD = -6312,
    APK_INSTALL_PLAN_V2_BAD_PREPASS = -6313,
    APK_INSTALL_PLAN_V2_BAD_PAYLOAD = -6314,
    APK_INSTALL_PLAN_V2_RESOURCE_ERROR = -6315,
    APK_INSTALL_PLAN_V2_UNSUPPORTED_PLATFORM = -6316,
};
uint64_t oh_adapter_apk_install_plan_abi_v2(void);
// Init requires an unowned output object; all FD slots become -1.
void ApkInstallPlanV2_Init(ApkInstallPlanV2* plan);
// Borrows an immutable full object and its FDs for this synchronous call. Does
// not move offsets, close caller FDs, perform installation or authenticate a
// self-authored plan. The producer/consumer must establish trusted provenance.
// Checks actual Linux/OH seals, lengths, bytes/digests and schema/binding. At
// byte-buffer boundaries use ValidateBytes to check bounds and alignment first.
int ApkInstallPlanV2_Validate(const ApkInstallPlanV2* plan);
int ApkInstallPlanV2_ValidateBytes(const void* bytes, size_t byteLength);
// Only the owner of a same-process initialized V2 plan may call Release.
// Closes all owned descriptors once, resets every slot, and is idempotent.
// Does not interpret an unknown ABI or incompatible size as an owned V2 plan.
void ApkInstallPlanV2_Release(ApkInstallPlanV2* plan);
#ifdef __cplusplus
}
#endif
#undef OH_APK_INSTALL_WIRE_ALIGN8
#endif
