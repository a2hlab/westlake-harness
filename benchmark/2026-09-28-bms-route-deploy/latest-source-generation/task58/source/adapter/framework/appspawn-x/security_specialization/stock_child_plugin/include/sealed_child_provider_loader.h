#ifndef WESTLAKE_SEALED_CHILD_PROVIDER_LOADER_H
#define WESTLAKE_SEALED_CHILD_PROVIDER_LOADER_H

#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

#define WLSCPL_ABI_VERSION UINT32_C(1)
#define WLSCPL_MAX_ARTIFACTS UINT32_C(64)
#define WLSCPL_MAX_NEEDED UINT32_C(32)
#define WLSCPL_SHA256_HEX_SIZE UINT32_C(65)
#define WLSCPL_BUILD_ID_HEX_SIZE UINT32_C(41)
#define WLSCPL_SONAME_SIZE UINT32_C(128)
#define WLSCPL_PROVIDER_SONAME "libwestlake_android_runtime_provider.so"

typedef enum WlscplState {
    WLSCPL_STATE_EMPTY = 0,
    WLSCPL_STATE_LOADING = 1,
    WLSCPL_STATE_LOADED = 2,
    WLSCPL_STATE_FAILED = 3
} WlscplState;

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
    WLSCPL_ERROR_DLOPEN = 10
} WlscplError;

typedef struct WlscplArtifactV1 {
    const char *absolute_path;
    char sha256_hex[WLSCPL_SHA256_HEX_SIZE];
    char build_id_hex[WLSCPL_BUILD_ID_HEX_SIZE];
    char soname[WLSCPL_SONAME_SIZE];
    uint32_t needed_count;
    uint32_t needed_indices[WLSCPL_MAX_NEEDED];
} WlscplArtifactV1;

typedef struct WlscplManifestV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint16_t elf_machine;
    uint16_t reserved_zero;
    uint32_t artifact_count;
    uint32_t root_index;
    uint64_t artifact_generation;
    const WlscplArtifactV1 *artifacts;
} WlscplManifestV1;

typedef struct WlscplLoadRequestV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    uint32_t specialization_complete;
    uint32_t hook_table_ready;
    uint32_t generation_seal_verified;
    uint32_t reserved_zero;
    uint64_t parent_pid;
    uint64_t child_pid;
    const WlscplManifestV1 *manifest;
} WlscplLoadRequestV1;

typedef struct WlscplLoaderV1 {
    uint32_t state;
    WlscplError first_error;
    uint64_t child_pid;
    uint64_t artifact_generation;
    uint32_t handle_count;
    uint32_t root_handle_index;
    void *handles[WLSCPL_MAX_ARTIFACTS];
} WlscplLoaderV1;

typedef struct WlscplLoadResultV1 {
    uint32_t abi_version;
    uint32_t struct_size;
    WlscplError error;
    uint32_t validated_artifact_count;
    uint64_t child_pid;
    uint64_t artifact_generation;
    void *provider_handle;
} WlscplLoadResultV1;

/*
 * Validates the complete sealed closure before the first mapping and then
 * maps every member by its exact absolute path using RTLD_NOW|RTLD_LOCAL.
 * This function is child-only and one-shot. It never performs a global symbol
 * lookup and deliberately has no fallback or unload-success API.
 */
WlscplError WLSCPL_LoadSealedProvider(
    WlscplLoaderV1 *loader, const WlscplLoadRequestV1 *request,
    WlscplLoadResultV1 *result);

void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags);

/* Build-generated, immutable and generation-bound; never returns a fallback. */
const WlscplManifestV1 *WLSCPL_GetBuildGeneratedManifest(void);

#ifdef WLSCPL_TESTING
typedef struct WlscplTestOpsV1 {
    uint64_t (*current_pid)(void *context);
    int (*verify_identity)(void *context, const WlscplArtifactV1 *artifact,
                           uint16_t elf_machine);
    int (*is_mapped)(void *context, const WlscplArtifactV1 *artifact);
    void *(*open_local_now)(void *context, const char *absolute_path,
                            int flags);
    int (*close_handle)(void *context, void *handle);
    void *context;
} WlscplTestOpsV1;

WlscplError WLSCPL_LoadSealedProviderForTest(
    WlscplLoaderV1 *loader, const WlscplLoadRequestV1 *request,
    WlscplLoadResultV1 *result, const WlscplTestOpsV1 *ops);
#endif

#ifdef __cplusplus
}
#endif

#endif
