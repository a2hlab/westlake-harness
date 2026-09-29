#include "prepass_context_wire.h"
#include <cstring>

namespace {
static_assert(sizeof(PrepassContextWire) == 856 && alignof(PrepassContextWire) == 4,
    "Prepass context ABI requires the published C layout");
size_t BoundedLength(const char* value, size_t capacity)
{
    size_t length = 0;
    while (length < capacity && value[length] != '\0') ++length;
    return length;
}
bool Identity(const char* value, size_t capacity)
{
    const size_t length = BoundedLength(value, capacity);
    if (length == 0 || length == capacity) return false;
    for (size_t i = length + 1; i < capacity; ++i) if (value[i] != '\0') return false;
    return true;
}
bool Digest(const char* value, size_t length)
{
    if (!value || length != 64) return false;
    for (size_t i = 0; i < length; ++i) {
        const char c = value[i];
        if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'))) return false;
    }
    return true;
}
}

extern "C" int PrepassContextWire_Validate(const PrepassContextWire* context)
{
    if (!context) return PREPASS_CONTEXT_WIRE_MISSING;
    if (context->abiVersion != PREPASS_CONTEXT_WIRE_ABI) return PREPASS_CONTEXT_WIRE_BAD_ABI;
    if (context->structSize != sizeof(*context)) return PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE;
    if (context->reservedZero != 0 || context->reservedTail[0] != 0 ||
        context->reservedTail[1] != 0 || context->reservedTail[2] != 0) return PREPASS_CONTEXT_WIRE_RESERVED_NONZERO;
    if (context->userId < 0 || !Identity(context->requestId, sizeof(context->requestId)) ||
        !Identity(context->packageName, sizeof(context->packageName)) ||
        !Identity(context->candidateGeneration, sizeof(context->candidateGeneration))) return PREPASS_CONTEXT_WIRE_BAD_IDENTITY;
    const char* digests[] = {context->contractSha256Hex, context->policySha256Hex, context->toolSha256Hex,
        context->topologySha256Hex, context->runtimeGenerationSealSha256Hex};
    for (const auto* field : digests) if (!Digest(field, 64) || field[64] != '\0') return PREPASS_CONTEXT_WIRE_BAD_DIGEST;
    return PREPASS_CONTEXT_WIRE_OK;
}

extern "C" int PrepassContextWire_ValidateBytes(const void* bytes, size_t byteLength)
{
    if (!bytes) return PREPASS_CONTEXT_WIRE_MISSING;
    if (byteLength != sizeof(PrepassContextWire)) return PREPASS_CONTEXT_WIRE_BAD_STRUCT_SIZE;
    PrepassContextWire context;
    std::memcpy(&context, bytes, sizeof(context));
    return PrepassContextWire_Validate(&context);
}

extern "C" int PrepassContextWire_ValidateForApk(const PrepassContextWire* context,
    const char* apkSha256, size_t apkSha256Length)
{
    const int status = PrepassContextWire_Validate(context);
    if (status != PREPASS_CONTEXT_WIRE_OK) return status;
    return Digest(apkSha256, apkSha256Length) ? PREPASS_CONTEXT_WIRE_OK : PREPASS_CONTEXT_WIRE_BAD_DIGEST;
}

extern "C" int PrepassContextWire_MatchPackageUser(const PrepassContextWire* context,
    const char* packageName, int32_t userId)
{
    const int status = PrepassContextWire_Validate(context);
    if (status != PREPASS_CONTEXT_WIRE_OK) return status;
    if (!packageName || userId != context->userId) return PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH;
    const size_t length = BoundedLength(packageName, PREPASS_CONTEXT_PACKAGE_CAPACITY);
    if (length == 0 || length == PREPASS_CONTEXT_PACKAGE_CAPACITY ||
        length != BoundedLength(context->packageName, sizeof(context->packageName)) ||
        std::memcmp(packageName, context->packageName, length) != 0) return PREPASS_CONTEXT_WIRE_PACKAGE_USER_MISMATCH;
    return PREPASS_CONTEXT_WIRE_OK;
}

extern "C" int PrepassContextWire_MatchBoundInput(const PrepassContextWire* context,
    const char* apkSha256, size_t apkSha256Length, const PrepassContextWire* expected,
    const char* expectedApkSha256, size_t expectedApkSha256Length)
{
    int status = PrepassContextWire_ValidateForApk(context, apkSha256, apkSha256Length);
    if (status != PREPASS_CONTEXT_WIRE_OK) return status;
    status = PrepassContextWire_ValidateForApk(expected, expectedApkSha256, expectedApkSha256Length);
    if (status != PREPASS_CONTEXT_WIRE_OK) return status;
    status = PrepassContextWire_MatchPackageUser(context, expected->packageName, expected->userId);
    if (status != PREPASS_CONTEXT_WIRE_OK) return status;
    if (std::memcmp(context->requestId, expected->requestId, sizeof(context->requestId)) != 0 ||
        std::memcmp(context->candidateGeneration, expected->candidateGeneration, sizeof(context->candidateGeneration)) != 0)
        return PREPASS_CONTEXT_WIRE_IDENTITY_MISMATCH;
    if (std::memcmp(context->contractSha256Hex, expected->contractSha256Hex, PREPASS_CONTEXT_DIGEST_CAPACITY) != 0 ||
        std::memcmp(context->policySha256Hex, expected->policySha256Hex, PREPASS_CONTEXT_DIGEST_CAPACITY) != 0 ||
        std::memcmp(context->toolSha256Hex, expected->toolSha256Hex, PREPASS_CONTEXT_DIGEST_CAPACITY) != 0 ||
        std::memcmp(context->topologySha256Hex, expected->topologySha256Hex, PREPASS_CONTEXT_DIGEST_CAPACITY) != 0 ||
        std::memcmp(context->runtimeGenerationSealSha256Hex, expected->runtimeGenerationSealSha256Hex, PREPASS_CONTEXT_DIGEST_CAPACITY) != 0)
        return PREPASS_CONTEXT_WIRE_PROFILE_MISMATCH;
    if (std::memcmp(apkSha256, expectedApkSha256, 64) != 0) return PREPASS_CONTEXT_WIRE_APK_MISMATCH;
    return PREPASS_CONTEXT_WIRE_OK;
}
