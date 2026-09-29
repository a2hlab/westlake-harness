#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "sealed_child_provider_loader.h"

#ifndef WLSCPL_TESTING
#include "westlake_elf_identity.h"
#endif

#include <dlfcn.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define WLSCPL_UNVISITED UINT8_C(0)
#define WLSCPL_VISITING UINT8_C(1)
#define WLSCPL_VISITED UINT8_C(2)
#define WLSCPL_PRELOADED_REGISTRY_PATH \
    "/system/lib64/libwestlake_thread_guard_registry.so"
#define WLSCPL_PRELOADED_BIONIC_COMPAT_PATH \
    "/system/android/lib64/libbionic_compat.so"

typedef struct WlscplOps {
    uint64_t (*current_pid)(void *context);
    int (*verify_identity)(void *context, const WlscplArtifactV1 *artifact,
                           uint16_t elf_machine);
    int (*is_mapped)(void *context, const WlscplArtifactV1 *artifact);
    void *(*open_local_now)(void *context, const char *absolute_path,
                            int flags);
    int (*close_handle)(void *context, void *handle);
    void *context;
} WlscplOps;

static size_t BoundedLength(const char *value, size_t maximum)
{
    size_t length;
    if (value == NULL) {
        return maximum;
    }
    for (length = 0U; length < maximum && value[length] != '\0'; ++length) {
    }
    return length;
}

static int ExactLowerHex(const char *value, size_t digits)
{
    size_t index;
    if (value == NULL || BoundedLength(value, digits + 1U) != digits) {
        return 0;
    }
    for (index = 0U; index < digits; ++index) {
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) {
            return 0;
        }
    }
    return 1;
}

static int HexHasNonzeroDigit(const char *value, size_t digits)
{
    size_t index;
    for (index = 0U; index < digits; ++index) {
        if (value[index] != '0') {
            return 1;
        }
    }
    return 0;
}

static int AbsoluteCanonicalForm(const char *path)
{
    const char *cursor;
    if (path == NULL || path[0] != '/' || path[1] == '\0' ||
        BoundedLength(path, PATH_MAX) == PATH_MAX) {
        return 0;
    }
    for (cursor = path; *cursor != '\0'; ++cursor) {
        if ((cursor[0] == '/' && cursor[1] == '/') ||
            (cursor[0] == '/' && cursor[1] == '.' &&
             (cursor[2] == '/' || cursor[2] == '\0')) ||
            (cursor[0] == '/' && cursor[1] == '.' && cursor[2] == '.' &&
             (cursor[3] == '/' || cursor[3] == '\0'))) {
            return 0;
        }
    }
    return path[BoundedLength(path, PATH_MAX) - 1U] != '/';
}

static int ManifestShapeValid(const WlscplManifestV1 *manifest)
{
    uint32_t left;
    if (manifest == NULL || manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        manifest->elf_machine == UINT16_C(0) ||
        manifest->reserved_zero != UINT16_C(0) ||
        manifest->artifact_count == UINT32_C(0) ||
        manifest->artifact_count > WLSCPL_MAX_ARTIFACTS ||
        manifest->root_index >= manifest->artifact_count ||
        manifest->artifact_generation == UINT64_C(0) ||
        manifest->artifacts == NULL) {
        return 0;
    }
    for (left = 0U; left < manifest->artifact_count; ++left) {
        const WlscplArtifactV1 *artifact = &manifest->artifacts[left];
        uint32_t right;
        uint32_t needed;
        if (!AbsoluteCanonicalForm(artifact->absolute_path) ||
            !ExactLowerHex(artifact->sha256_hex, 64U) ||
            !HexHasNonzeroDigit(artifact->sha256_hex, 64U) ||
            (!ExactLowerHex(artifact->build_id_hex, 40U) && !ExactLowerHex(artifact->build_id_hex, 32U)) ||
            !HexHasNonzeroDigit(artifact->build_id_hex, strlen(artifact->build_id_hex)) ||
            BoundedLength(artifact->soname, WLSCPL_SONAME_SIZE) == 0U ||
            BoundedLength(artifact->soname, WLSCPL_SONAME_SIZE) ==
                WLSCPL_SONAME_SIZE ||
            strchr(artifact->soname, '/') != NULL ||
            artifact->needed_count > WLSCPL_MAX_NEEDED) {
            return 0;
        }
        for (needed = 0U; needed < artifact->needed_count; ++needed) {
            uint32_t candidate = artifact->needed_indices[needed];
            uint32_t prior;
            if (candidate >= manifest->artifact_count || candidate == left) {
                return 0;
            }
            for (prior = 0U; prior < needed; ++prior) {
                if (artifact->needed_indices[prior] == candidate) {
                    return 0;
                }
            }
        }
        for (right = left + 1U; right < manifest->artifact_count; ++right) {
            if (strcmp(artifact->absolute_path,
                       manifest->artifacts[right].absolute_path) == 0 ||
                strcmp(artifact->soname,
                       manifest->artifacts[right].soname) == 0) {
                return 0;
            }
        }
    }
    return strcmp(manifest->artifacts[manifest->root_index].soname,
                  WLSCPL_PROVIDER_SONAME) == 0;
}

static int IsPreloadedRegistryUnityArtifact(
    const WlscplArtifactV1 *artifact)
{
    return artifact != NULL &&
        strcmp(artifact->absolute_path,
               WLSCPL_PRELOADED_REGISTRY_PATH) == 0 &&
        strcmp(artifact->soname,
               "libwestlake_thread_guard_registry.so") == 0;
}

static int IsPreloadedBionicCompatUnityArtifact(
    const WlscplArtifactV1 *artifact)
{
    return artifact != NULL &&
        strcmp(artifact->absolute_path,
               WLSCPL_PRELOADED_BIONIC_COMPAT_PATH) == 0 &&
        strcmp(artifact->soname, "libbionic_compat.so") == 0;
}

static int VisitClosure(const WlscplManifestV1 *manifest, uint32_t index,
                        uint8_t marks[WLSCPL_MAX_ARTIFACTS],
                        uint32_t order[WLSCPL_MAX_ARTIFACTS],
                        uint32_t *order_count)
{
    const WlscplArtifactV1 *artifact;
    uint32_t needed;
    if (marks[index] == WLSCPL_VISITING) {
        return -1;
    }
    if (marks[index] == WLSCPL_VISITED) {
        return 0;
    }
    marks[index] = WLSCPL_VISITING;
    artifact = &manifest->artifacts[index];
    for (needed = 0U; needed < artifact->needed_count; ++needed) {
        if (VisitClosure(manifest, artifact->needed_indices[needed], marks,
                         order, order_count) != 0) {
            return -1;
        }
    }
    marks[index] = WLSCPL_VISITED;
    order[*order_count] = index;
    *order_count += UINT32_C(1);
    return 0;
}

#ifndef WLSCPL_TESTING
static uint64_t RealCurrentPid(void *context)
{
    (void)context;
    return (uint64_t)getpid();
}

static int RealIsMapped(void *context, const WlscplArtifactV1 *artifact)
{
    FILE *maps;
    char line[PATH_MAX + 256U];
    (void)context;
    maps = fopen("/proc/self/maps", "re");
    if (maps == NULL) {
        return -1;
    }
    while (fgets(line, sizeof(line), maps) != NULL) {
        char *path = strchr(line, '/');
        if (path != NULL) {
            char *newline = strchr(path, '\n');
            const char *base;
            if (newline != NULL) {
                *newline = '\0';
            }
            base = strrchr(path, '/');
            base = base == NULL ? path : base + 1;
            if (strcmp(path, artifact->absolute_path) == 0 ||
                strcmp(base, artifact->soname) == 0) {
                (void)fclose(maps);
                return 1;
            }
        }
    }
    return fclose(maps) == 0 ? 0 : -1;
}

static Dl_namespace closure_namespace;
static int namespace_prepared;

void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags)
{
    /* R155 ends this wrapper with a sibling call to dlopen. OH musl uses
     * the return address to select the caller namespace; keep the caller in
     * the sealed provider, not in this default-namespace plugin. A stack
     * array here prevents the sibling call with the locked compiler. The
     * post-link instruction check is part of admission for this wrapper. */
    static const char prefix[] = "/system/android/lib64/";
    if (namespace_prepared != 1 || !AbsoluteCanonicalForm(absolute_path) ||
        strncmp(absolute_path, prefix, sizeof(prefix) - 1U) != 0 ||
        absolute_path[sizeof(prefix) - 1U] == '\0' ||
        (flags & (RTLD_NOW | RTLD_GLOBAL)) != RTLD_NOW) return NULL;
    return dlopen(absolute_path, flags);
}

static void *RealOpenLocalNow(void *context, const char *absolute_path,
                              int flags)
{
    (void)context;
    if (namespace_prepared == 0) {
        char search_path[PATH_MAX];
        char *slash;
        size_t length = strlen(absolute_path);
        if (length == 0U || length >= sizeof(search_path)) {
            return NULL;
        }
        (void)memcpy(search_path, absolute_path, length + 1U);
        slash = strrchr(search_path, '/');
        if (slash == NULL || slash == search_path) {
            return NULL;
        }
        *slash = '\0';
        dlns_init(&closure_namespace, "westlake.sealed.child");
        if (dlns_create2(&closure_namespace, search_path,
                         CREATE_INHERIT_CURRENT) != 0) {
            return NULL;
        }
        namespace_prepared = 1;
    }
    return dlopen_ns(&closure_namespace, absolute_path, flags);
}

static int RealCloseHandle(void *context, void *handle)
{
    (void)context;
    return dlclose(handle);
}
#endif

static void SetResult(const WlscplLoadRequestV1 *request,
                      WlscplLoadResultV1 *result, WlscplError error,
                      uint32_t validated, void *provider_handle)
{
    if (result == NULL) {
        return;
    }
    (void)memset(result, 0, sizeof(*result));
    result->abi_version = WLSCPL_ABI_VERSION;
    result->struct_size = (uint32_t)sizeof(*result);
    result->error = error;
    result->validated_artifact_count = validated;
    if (request != NULL && request->manifest != NULL) {
        result->child_pid = request->child_pid;
        result->artifact_generation =
            request->manifest->artifact_generation;
    }
    result->provider_handle = provider_handle;
}

static WlscplError Fail(WlscplLoaderV1 *loader,
                        const WlscplLoadRequestV1 *request,
                        WlscplLoadResultV1 *result, WlscplError error,
                        uint32_t validated, const WlscplOps *ops)
{
    while (loader != NULL && loader->handle_count > UINT32_C(0)) {
        uint32_t index = loader->handle_count - UINT32_C(1);
        if (loader->handles[index] != NULL && ops != NULL) {
            (void)ops->close_handle(ops->context, loader->handles[index]);
        }
        loader->handles[index] = NULL;
        loader->handle_count = index;
    }
    if (loader != NULL) {
        loader->first_error = error;
        __atomic_store_n(&loader->state, WLSCPL_STATE_FAILED,
                         __ATOMIC_RELEASE);
    }
    SetResult(request, result, error, validated, NULL);
    return error;
}

static WlscplError LoadWithOps(WlscplLoaderV1 *loader,
                               const WlscplLoadRequestV1 *request,
                               WlscplLoadResultV1 *result,
                               const WlscplOps *ops)
{
    uint8_t marks[WLSCPL_MAX_ARTIFACTS] = {0};
    uint8_t inherited[WLSCPL_MAX_ARTIFACTS] = {0};
    uint32_t order[WLSCPL_MAX_ARTIFACTS] = {0};
    uint32_t order_count = UINT32_C(0);
    uint32_t expected = WLSCPL_STATE_EMPTY;
    uint32_t index;
    if (loader == NULL || request == NULL || result == NULL || ops == NULL ||
        ops->current_pid == NULL ||
        ops->is_mapped == NULL || ops->open_local_now == NULL ||
        ops->close_handle == NULL ||
        request->abi_version != WLSCPL_ABI_VERSION ||
        request->struct_size != sizeof(*request) ||
        request->reserved_zero != UINT32_C(0)) {
        SetResult(request, result, WLSCPL_ERROR_INVALID_ARGUMENT, 0U, NULL);
        return WLSCPL_ERROR_INVALID_ARGUMENT;
    }
    if (!__atomic_compare_exchange_n(&loader->state, &expected,
                                     WLSCPL_STATE_LOADING, 0,
                                     __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        SetResult(request, result, WLSCPL_ERROR_ALREADY_ATTEMPTED, 0U,
                  NULL);
        return WLSCPL_ERROR_ALREADY_ATTEMPTED;
    }
    loader->first_error = WLSCPL_OK;
    loader->child_pid = request->child_pid;
    loader->handle_count = UINT32_C(0);
    if (request->specialization_complete != UINT32_C(1) ||
        request->parent_pid == UINT64_C(0) ||
        request->child_pid == UINT64_C(0) ||
        request->parent_pid == request->child_pid ||
        ops->current_pid(ops->context) != request->child_pid) {
        return Fail(loader, request, result,
                    WLSCPL_ERROR_NOT_SPECIALIZED_CHILD, 0U, ops);
    }
    if (request->hook_table_ready != UINT32_C(1)) {
        return Fail(loader, request, result,
                    WLSCPL_ERROR_HOOK_TABLE_NOT_READY, 0U, ops);
    }
    if (request->generation_seal_verified != UINT32_C(1)) {
        return Fail(loader, request, result,
                    WLSCPL_ERROR_SEAL_NOT_VERIFIED, 0U, ops);
    }
    if (!ManifestShapeValid(request->manifest)) {
        return Fail(loader, request, result, WLSCPL_ERROR_MANIFEST_INVALID,
                    0U, ops);
    }
    loader->artifact_generation = request->manifest->artifact_generation;
    if (VisitClosure(request->manifest, request->manifest->root_index, marks,
                     order, &order_count) != 0 ||
        order_count != request->manifest->artifact_count) {
        return Fail(loader, request, result, WLSCPL_ERROR_CLOSURE_INVALID,
                    0U, ops);
    }
    for (index = 0U; index < order_count; ++index) {
        const WlscplArtifactV1 *artifact =
            &request->manifest->artifacts[order[index]];
        /* #68: provider file SHA/build-id is enforced by the deployer. */
        {
            int mapped = ops->is_mapped(ops->context, artifact);
            int allowed = IsPreloadedRegistryUnityArtifact(artifact) ||
                IsPreloadedBionicCompatUnityArtifact(artifact) ||
                (strcmp(artifact->absolute_path, "/system/android/lib64/liblzma.so") == 0 &&
                 strcmp(artifact->soname, "liblzma.so") == 0);
            if ((allowed && mapped != 1) || (!allowed && mapped != 0)) {
                return Fail(loader, request, result,
                            WLSCPL_ERROR_PREMATURE_MAPPING, index + UINT32_C(1), ops);
            }
            inherited[order[index]] = (uint8_t)allowed;
        }
    }
    for (index = 0U; index < order_count; ++index) {
        uint32_t artifact_index = order[index];
        if (inherited[artifact_index]) continue;
        void *handle = ops->open_local_now(
            ops->context,
            request->manifest->artifacts[artifact_index].absolute_path,
            RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL) {
            return Fail(loader, request, result, WLSCPL_ERROR_DLOPEN,
                        order_count, ops);
        }
        loader->handles[loader->handle_count] = handle;
        if (artifact_index == request->manifest->root_index) {
            loader->root_handle_index = loader->handle_count;
        }
        loader->handle_count += UINT32_C(1);
    }
    __atomic_store_n(&loader->state, WLSCPL_STATE_LOADED,
                     __ATOMIC_RELEASE);
    SetResult(request, result, WLSCPL_OK, order_count,
              loader->handles[loader->root_handle_index]);
    return WLSCPL_OK;
}

#ifndef WLSCPL_TESTING
WlscplError WLSCPL_LoadSealedProvider(
    WlscplLoaderV1 *loader, const WlscplLoadRequestV1 *request,
    WlscplLoadResultV1 *result)
{
    static const WlscplOps ops = {
        RealCurrentPid,
        NULL, /* no runtime file-identity callback */
        RealIsMapped,
        RealOpenLocalNow,
        RealCloseHandle,
        NULL,
    };
    return LoadWithOps(loader, request, result, &ops);
}
#endif

#ifdef WLSCPL_TESTING
WlscplError WLSCPL_LoadSealedProviderForTest(
    WlscplLoaderV1 *loader, const WlscplLoadRequestV1 *request,
    WlscplLoadResultV1 *result, const WlscplTestOpsV1 *test_ops)
{
    WlscplOps ops;
    if (test_ops == NULL) {
        SetResult(request, result, WLSCPL_ERROR_INVALID_ARGUMENT, 0U, NULL);
        return WLSCPL_ERROR_INVALID_ARGUMENT;
    }
    ops.current_pid = test_ops->current_pid;
    ops.verify_identity = test_ops->verify_identity;
    ops.is_mapped = test_ops->is_mapped;
    ops.open_local_now = test_ops->open_local_now;
    ops.close_handle = test_ops->close_handle;
    ops.context = test_ops->context;
    return LoadWithOps(loader, request, result, &ops);
}
#endif
