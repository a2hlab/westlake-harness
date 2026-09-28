#ifndef WESTLAKE_SEALED_CHILD_PROVIDER_LOADER_H
#define WESTLAKE_SEALED_CHILD_PROVIDER_LOADER_H

#include "westlake_generation_receipt_v2.h"

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WLSCPL_ABI_VERSION UINT32_C(2)
#define WLSCPL_MAX_ARTIFACTS UINT32_C(96)
#define WLSCPL_MAX_NEEDED UINT32_C(32)
#define WLSCPL_SHA256_HEX_SIZE UINT32_C(65)
#define WLSCPL_BUILD_ID_HEX_SIZE UINT32_C(41)
#define WLSCPL_SONAME_SIZE UINT32_C(128)
#define WLSCPL_PROVIDER_SONAME "libwestlake_android_runtime_provider.so"

typedef enum WlscplArtifactKindV2 {
    WLSCPL_ARTIFACT_SEALED_LOAD = 1,
    WLSCPL_ARTIFACT_OH_SYSTEM_ROOT = 2
} WlscplArtifactKindV2;

typedef enum WlscplConstructorTimingV2 {
    WLSCPL_CONSTRUCTOR_TIMING_NONE = 0,
    WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN = 1
} WlscplConstructorTimingV2;

typedef enum WlscplStateV2 {
    WLSCPL_STATE_EMPTY = 0,
    WLSCPL_STATE_LOADING = 1,
    WLSCPL_STATE_LOADED = 2,
    WLSCPL_STATE_FAILED = 3,
    WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS = 4
} WlscplStateV2;

typedef enum WlscplError {
    WLSCPL_OK = 0,
    WLSCPL_ERROR_INVALID_ARGUMENT = 1,
    WLSCPL_ERROR_NOT_SPECIALIZED_CHILD = 2,
    WLSCPL_ERROR_HOOK_TABLE_NOT_READY = 3,
    WLSCPL_ERROR_SEAL_NOT_VERIFIED = 4,
    WLSCPL_ERROR_ALREADY_ATTEMPTED = 5,
    WLSCPL_ERROR_MANIFEST_INVALID = 6,
    WLSCPL_ERROR_CLOSURE_INVALID = 7,
    WLSCPL_ERROR_ARTIFACT_IDENTITY = 8,
    WLSCPL_ERROR_PREMATURE_MAPPING = 9,
    WLSCPL_ERROR_DLOPEN = 10,
    WLSCPL_ERROR_MAPPED_IDENTITY = 11,
    WLSCPL_ERROR_GENERATION_IDENTITY = 12,
    WLSCPL_ERROR_EXTERNAL_ROOT = 13
} WlscplError;

typedef struct WlscplArtifactV2 {
    const char *absolute_path;
    char sha256_hex[WLSCPL_SHA256_HEX_SIZE];
    /* Exact 32-hex GNU UUID or 40-hex SHA1 Build-ID. */
    char build_id_hex[WLSCPL_BUILD_ID_HEX_SIZE];
    char soname[WLSCPL_SONAME_SIZE];
    uint32_t artifact_kind;
    uint32_t needed_count;
    uint32_t needed_indices[WLSCPL_MAX_NEEDED];
    uint32_t reserved_zero[4];
} WlscplArtifactV2;

typedef struct WlscplManifestV2 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint16_t elf_machine;
    uint16_t reserved_zero;
    uint32_t artifact_count;
    uint32_t root_index;
    uint32_t external_root_count;
    uint32_t reserved_zero1;
    uint8_t manifest_digest[WLGR_V2_SHA256_SIZE];
    const WlscplArtifactV2 *artifacts;
} WlscplManifestV2;

typedef struct WlscplLoadRequestV2 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t specialization_complete;
    uint32_t hook_table_ready;
    uint32_t generation_seal_verified;
    uint32_t reserved_zero;
    uint64_t parent_pid;
    const westlake_generation_identity_v2 *generation_identity;
    const WlscplManifestV2 *manifest;
} WlscplLoadRequestV2;

typedef struct WlscplLoaderV2 {
    uint32_t state;
    WlscplError first_error;
    westlake_generation_identity_v2 generation_identity;
    uint32_t handle_count;
    uint32_t root_handle_index;
    uint32_t constructor_completed_count;
    uint32_t reserved_zero;
    void *handles[WLSCPL_MAX_ARTIFACTS];
} WlscplLoaderV2;

typedef struct WlscplLoadResultV2 {
    uint32_t abi_version;
    uint32_t struct_size;
    WlscplError error;
    uint32_t validated_artifact_count;
    uint32_t mapped_artifact_count;
    uint32_t constructor_completed_count;
    uint32_t constructor_timing;
    uint32_t reserved_zero;
    westlake_generation_identity_v2 generation_identity;
    void *provider_handle;
} WlscplLoadResultV2;

/*
 * All identities and the full graph are validated before the first dlopen.
 * Sealed members are opened through retained verified descriptors and each
 * mapped dev/inode is rebound before continuing.  Every successful dlopen has
 * already run that object's constructors; failures after this point retain all
 * handles and require child fail-stop (there is intentionally no dlclose path).
 */
WlscplError WLSCPL_LoadSealedProvider(
    WlscplLoaderV2 *loader, const WlscplLoadRequestV2 *request,
    WlscplLoadResultV2 *result);

const WlscplManifestV2 *WLSCPL_GetBuildGeneratedManifest(void);

#ifndef WLSCPL_TESTING
/* Default-namespace caller proxy into the already-created sealed namespace. */
void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags);
#endif

#ifdef WLSCPL_TESTING
typedef struct WlscplVerifiedObjectV2 {
    int64_t descriptor_token;
    uint64_t device;
    uint64_t inode;
    uint64_t size;
} WlscplVerifiedObjectV2;

typedef struct WlscplTestOpsV2 {
    uint64_t (*current_pid)(void *context);
    int (*verify_identity)(void *context, const WlscplArtifactV2 *artifact,
                           uint16_t elf_machine,
                           WlscplVerifiedObjectV2 *verified);
    int (*mapping_state)(void *context, const WlscplArtifactV2 *artifact,
                         const WlscplVerifiedObjectV2 *verified);
    void *(*open_verified_local_now)(
        void *context, const WlscplArtifactV2 *artifact,
        const WlscplVerifiedObjectV2 *verified, int flags);
    int (*mapped_identity_matches)(
        void *context, const WlscplArtifactV2 *artifact,
        const WlscplVerifiedObjectV2 *verified, void *handle);
    int (*close_verified)(void *context, WlscplVerifiedObjectV2 *verified);
    void *context;
} WlscplTestOpsV2;

WlscplError WLSCPL_LoadSealedProviderForTest(
    WlscplLoaderV2 *loader, const WlscplLoadRequestV2 *request,
    WlscplLoadResultV2 *result, const WlscplTestOpsV2 *ops);
#endif

#ifdef __cplusplus
}
#endif

#endif
