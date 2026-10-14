#ifndef OH_ADAPTER_PREPASS_CONTEXT_WIRE_H
#define OH_ADAPTER_PREPASS_CONTEXT_WIRE_H
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif
#define PREPASS_CONTEXT_WIRE_ABI 1u
#define PREPASS_CONTEXT_REQUEST_CAPACITY 128u
#define PREPASS_CONTEXT_PACKAGE_CAPACITY 256u
#define PREPASS_CONTEXT_GENERATION_CAPACITY 128u
#define PREPASS_CONTEXT_DIGEST_CAPACITY 65u

typedef struct PrepassContextWire {
    uint32_t abiVersion;
    uint32_t structSize;
    int32_t userId;
    uint32_t reservedZero;
    char requestId[PREPASS_CONTEXT_REQUEST_CAPACITY];
    char packageName[PREPASS_CONTEXT_PACKAGE_CAPACITY];
    char candidateGeneration[PREPASS_CONTEXT_GENERATION_CAPACITY];
    char contractSha256Hex[PREPASS_CONTEXT_DIGEST_CAPACITY];
    char policySha256Hex[PREPASS_CONTEXT_DIGEST_CAPACITY];
    char toolSha256Hex[PREPASS_CONTEXT_DIGEST_CAPACITY];
    char topologySha256Hex[PREPASS_CONTEXT_DIGEST_CAPACITY];
    char runtimeGenerationSealSha256Hex[PREPASS_CONTEXT_DIGEST_CAPACITY];
    uint8_t reservedTail[3];
} PrepassContextWire;

enum PrepassContextWireStatus {
    PREPASS_CONTEXT_WIRE_OK = 0,
    PREPASS_CONTEXT_WIRE_MISSING = -6101,
    PREPASS_CONTEXT_WIRE_BAD_ABI = -6102,
    PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE = -6103,
    PREPASS_CONTEXT_WIRE_RESERVED_NONZERO = -6104,
    PREPASS_CONTEXT_WIRE_BAD_IDENTITY = -6105,
    PREPASS_CONTEXT_WIRE_BAD_DIGEST = -6106,
    PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH = -6107,
    PREPASS_CONTEXT_WIRE_IDENTITY_MISMATCH = -6108,
    PREPASS_CONTEXT_WIRE_PROFILE_MISMATCH = -6109,
    PREPASS_CONTEXT_WIRE_APK_MISMATCH = -6110,
};

// Structural checks are not authentication. The aligned pointer must address an
// immutable full object. Every identity has a NUL and zero-filled unused tail;
// digests are exactly 64 lowercase hex bytes + NUL. No implicit user/profile.
int PrepassContextWire_Validate(const PrepassContextWire* context);
// Use at byte-buffer boundaries; accepts unaligned bytes and never reads past
// byteLength. The ABI is same-process C layout, not a network byte order.
int PrepassContextWire_ValidateBytes(const void* bytes, size_t byteLength);
// APK digest is a separate verified input, completing the six codec bindings.
// Its buffer is exactly 64 bytes and need not have a trailing NUL.
int PrepassContextWire_ValidateForApk(const PrepassContextWire* context,
    const char* apkSha256, size_t apkSha256Length);
// packageName must be a valid C string; scanning is bounded to package capacity.
int PrepassContextWire_MatchPackageUser(const PrepassContextWire* context,
    const char* packageName, int32_t userId);
// expected and expectedApkSha256 must come from the trusted request/profile and
// verified APK owners, never from the same untrusted input being validated.
int PrepassContextWire_MatchBoundInput(const PrepassContextWire* context,
    const char* apkSha256, size_t apkSha256Length,
    const PrepassContextWire* expected,
    const char* expectedApkSha256, size_t expectedApkSha256Length);
#ifdef __cplusplus
}
#endif
#endif
