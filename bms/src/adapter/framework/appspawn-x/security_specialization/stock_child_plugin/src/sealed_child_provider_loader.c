#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include "sealed_child_provider_loader.h"
#include "westlake_sha256.h"

#ifndef WLSCPL_TESTING
#include "westlake_elf_identity.h"
#include "oh_dlns_abi.h"
#endif

#include <dlfcn.h>
#include <limits.h>
#include <stdio.h>
#include <string.h>
#ifndef WLSCPL_TESTING
#include <sys/sysmacros.h>
#include <sys/types.h>
#endif
#include <unistd.h>

#define WLSCPL_UNVISITED UINT8_C(0)
#define WLSCPL_VISITING UINT8_C(1)
#define WLSCPL_VISITED UINT8_C(2)
#define WLSCPL_PRELOADED_REGISTRY_PATH \
    "/system/lib64/libwestlake_thread_guard_registry.so"
#define WLSCPL_PRELOADED_BIONIC_COMPAT_PATH \
    "/system/android/lib64/libbionic_compat.so"
#define WLSCPL_PRELOADED_LZMA_PATH "/system/android/lib64/liblzma.so"
#define WLSCPL_SYSTEM_LIBRARY_ROOT "/system/android/lib64/"
#define WLSCPL_SEALED_NAMESPACE "westlake.sealed.child"

_Static_assert(sizeof(WlscplManifestV2) == 72U,
               "WlscplManifestV2 canonical digest layout drift");

#ifdef WLSCPL_TESTING
typedef WlscplVerifiedObjectV2 WlscplVerifiedObject;
#else
typedef struct WlscplVerifiedObject {
    int64_t descriptor_token;
    uint64_t device;
    uint64_t inode;
    uint64_t size;
} WlscplVerifiedObject;
#endif

typedef struct WlscplOps {
    uint64_t (*current_pid)(void *context);
    int (*verify_identity)(void *context, const WlscplArtifactV2 *artifact,
                           uint16_t elf_machine,
                           WlscplVerifiedObject *verified);
    int (*mapping_state)(void *context, const WlscplArtifactV2 *artifact,
                         const WlscplVerifiedObject *verified);
    void *(*open_verified_local_now)(
        void *context, const WlscplArtifactV2 *artifact,
        const WlscplVerifiedObject *verified, int flags);
    int (*mapped_identity_matches)(
        void *context, const WlscplArtifactV2 *artifact,
        const WlscplVerifiedObject *verified, void *handle);
    int (*close_verified)(void *context, WlscplVerifiedObject *verified);
    void *context;
} WlscplOps;

static size_t BoundedLength(const char *value, size_t maximum)
{
    size_t length;
    if (value == NULL) return maximum;
    for (length = 0U; length < maximum && value[length] != '\0'; ++length) {}
    return length;
}

static int ExactLowerHex(const char *value, size_t digits)
{
    size_t index;
    if (value == NULL || BoundedLength(value, digits + 1U) != digits) return 0;
    for (index = 0U; index < digits; ++index) {
        if (!((value[index] >= '0' && value[index] <= '9') ||
              (value[index] >= 'a' && value[index] <= 'f'))) return 0;
    }
    return 1;
}

static int HexHasNonzeroDigit(const char *value, size_t digits)
{
    size_t index;
    for (index = 0U; index < digits; ++index) if (value[index] != '0') return 1;
    return 0;
}

static int AbsoluteCanonicalForm(const char *path)
{
    const char *cursor;
    size_t length;
    if (path == NULL || path[0] != '/' || path[1] == '\0' ||
        (length = BoundedLength(path, PATH_MAX)) == PATH_MAX) return 0;
    for (cursor = path; *cursor != '\0'; ++cursor) {
        if ((cursor[0] == '/' && cursor[1] == '/') ||
            (cursor[0] == '/' && cursor[1] == '.' &&
             (cursor[2] == '/' || cursor[2] == '\0')) ||
            (cursor[0] == '/' && cursor[1] == '.' && cursor[2] == '.' &&
             (cursor[3] == '/' || cursor[3] == '\0'))) return 0;
    }
    return path[length - 1U] != '/';
}

static int IsInheritedThreadGuardRegistry(const WlscplArtifactV2 *artifact)
{
    return artifact != NULL &&
        artifact->artifact_kind == WLSCPL_ARTIFACT_SEALED_LOAD &&
        strcmp(artifact->absolute_path, WLSCPL_PRELOADED_REGISTRY_PATH) == 0 &&
        strcmp(artifact->soname,
               "libwestlake_thread_guard_registry.so") == 0;
}

/* The proven AppSpawnX route preloads these provider DSOs in the parent.
 * They are still verified by inode below, but must not be rejected as a
 * premature child mapping or opened a second time in the child. */
static int IsInheritedPreloadedProvider(const WlscplArtifactV2 *artifact)
{
    if (IsInheritedThreadGuardRegistry(artifact)) return 1;
    return artifact != NULL &&
        artifact->artifact_kind == WLSCPL_ARTIFACT_SEALED_LOAD &&
        ((strcmp(artifact->absolute_path, WLSCPL_PRELOADED_LZMA_PATH) == 0 &&
          strcmp(artifact->soname, "liblzma.so") == 0) ||
         (strcmp(artifact->absolute_path,
                 WLSCPL_PRELOADED_BIONIC_COMPAT_PATH) == 0 &&
          strcmp(artifact->soname, "libbionic_compat.so") == 0));
}

static int ManifestShapeValid(const WlscplManifestV2 *manifest)
{
    uint32_t left;
    uint32_t external_count = 0U;
    if (manifest == NULL || manifest->abi_version != WLSCPL_ABI_VERSION ||
        manifest->struct_size != sizeof(*manifest) ||
        manifest->elf_machine == UINT16_C(0) ||
        manifest->reserved_zero != UINT16_C(0) ||
        manifest->reserved_zero1 != UINT32_C(0) ||
        manifest->artifact_count == UINT32_C(0) ||
        manifest->artifact_count > WLSCPL_MAX_ARTIFACTS ||
        manifest->root_index >= manifest->artifact_count ||
        manifest->artifacts == NULL ||
        wlgr_v2_bytes_zero(manifest->manifest_digest,
                           sizeof(manifest->manifest_digest))) return 0;
    for (left = 0U; left < manifest->artifact_count; ++left) {
        const WlscplArtifactV2 *artifact = &manifest->artifacts[left];
        uint32_t right;
        uint32_t needed;
        int sealed = artifact->artifact_kind == WLSCPL_ARTIFACT_SEALED_LOAD;
        int external = artifact->artifact_kind == WLSCPL_ARTIFACT_OH_SYSTEM_ROOT;
        if (!AbsoluteCanonicalForm(artifact->absolute_path) ||
            !ExactLowerHex(artifact->sha256_hex, 64U) ||
            !HexHasNonzeroDigit(artifact->sha256_hex, 64U) ||
            ((!ExactLowerHex(artifact->build_id_hex, 40U) &&
              !ExactLowerHex(artifact->build_id_hex, 32U)) ||
             !HexHasNonzeroDigit(artifact->build_id_hex,
                 BoundedLength(artifact->build_id_hex,
                               WLSCPL_BUILD_ID_HEX_SIZE))) ||
            (!sealed && !external) ||
            BoundedLength(artifact->soname, WLSCPL_SONAME_SIZE) == 0U ||
            BoundedLength(artifact->soname, WLSCPL_SONAME_SIZE) ==
                WLSCPL_SONAME_SIZE || strchr(artifact->soname, '/') != NULL ||
            artifact->needed_count > WLSCPL_MAX_NEEDED ||
            !wlgr_v2_bytes_zero((const uint8_t *)artifact->reserved_zero,
                                sizeof(artifact->reserved_zero))) return 0;
        if (external) ++external_count;
        for (needed = 0U; needed < artifact->needed_count; ++needed) {
            uint32_t candidate = artifact->needed_indices[needed];
            uint32_t prior;
            if (candidate >= manifest->artifact_count || candidate == left) return 0;
            for (prior = 0U; prior < needed; ++prior)
                if (artifact->needed_indices[prior] == candidate) return 0;
        }
        for (right = left + 1U; right < manifest->artifact_count; ++right) {
            if (strcmp(artifact->absolute_path,
                       manifest->artifacts[right].absolute_path) == 0 ||
                strcmp(artifact->soname,
                       manifest->artifacts[right].soname) == 0) return 0;
        }
    }
    return external_count == manifest->external_root_count &&
        manifest->artifacts[manifest->root_index].artifact_kind ==
            WLSCPL_ARTIFACT_SEALED_LOAD &&
        strcmp(manifest->artifacts[manifest->root_index].soname,
               WLSCPL_PROVIDER_SONAME) == 0;
}

static int DigestBytes(WlSha256Context *context, const void *data, size_t size)
{
    return WLSha256Update(context, data, size);
}

static int DigestU16(WlSha256Context *context, uint16_t value)
{
    uint8_t encoded[2] = {
        (uint8_t)value,
        (uint8_t)(value >> 8U),
    };
    return DigestBytes(context, encoded, sizeof(encoded));
}

static int DigestU32(WlSha256Context *context, uint32_t value)
{
    uint8_t encoded[4] = {
        (uint8_t)value,
        (uint8_t)(value >> 8U),
        (uint8_t)(value >> 16U),
        (uint8_t)(value >> 24U),
    };
    return DigestBytes(context, encoded, sizeof(encoded));
}

static int DigestString(WlSha256Context *context, const char *value,
                        size_t maximum)
{
    size_t length = BoundedLength(value, maximum);
    if (length >= maximum || length > UINT32_MAX ||
        DigestU32(context, (uint32_t)length) != 0)
        return -1;
    return DigestBytes(context, value, length);
}

static int ComputeManifestDigest(
    const WlscplManifestV2 *manifest,
    uint8_t digest[WLGR_V2_SHA256_SIZE])
{
    static const uint8_t domain[] = "WLSCPL-MANIFEST-V2";
    WlSha256Context context;
    uint32_t artifact_index;
    if (manifest == NULL || digest == NULL) return -1;
    WLSha256Init(&context);
    if (DigestBytes(&context, domain, sizeof(domain) - 1U) != 0 ||
        DigestU32(&context, manifest->abi_version) != 0 ||
        DigestU32(&context, manifest->struct_size) != 0 ||
        DigestU16(&context, manifest->elf_machine) != 0 ||
        DigestU32(&context, manifest->artifact_count) != 0 ||
        DigestU32(&context, manifest->root_index) != 0 ||
        DigestU32(&context, manifest->external_root_count) != 0)
        return -1;
    for (artifact_index = 0U; artifact_index < manifest->artifact_count;
         ++artifact_index) {
        const WlscplArtifactV2 *artifact =
            &manifest->artifacts[artifact_index];
        uint32_t needed_index;
        if (DigestString(&context, artifact->absolute_path, PATH_MAX) != 0 ||
            DigestString(&context, artifact->sha256_hex,
                         WLSCPL_SHA256_HEX_SIZE) != 0 ||
            DigestString(&context, artifact->build_id_hex,
                         WLSCPL_BUILD_ID_HEX_SIZE) != 0 ||
            DigestString(&context, artifact->soname,
                         WLSCPL_SONAME_SIZE) != 0 ||
            DigestU32(&context, artifact->artifact_kind) != 0 ||
            DigestU32(&context, artifact->needed_count) != 0)
            return -1;
        for (needed_index = 0U; needed_index < artifact->needed_count;
             ++needed_index) {
            if (DigestU32(&context,
                    artifact->needed_indices[needed_index]) != 0)
                return -1;
        }
    }
    return WLSha256Final(&context, digest);
}

static int VisitClosure(const WlscplManifestV2 *manifest, uint32_t index,
                        uint8_t marks[WLSCPL_MAX_ARTIFACTS],
                        uint32_t order[WLSCPL_MAX_ARTIFACTS],
                        uint32_t *order_count)
{
    const WlscplArtifactV2 *artifact;
    uint32_t needed;
    if (marks[index] == WLSCPL_VISITING) return -1;
    if (marks[index] == WLSCPL_VISITED) return 0;
    marks[index] = WLSCPL_VISITING;
    artifact = &manifest->artifacts[index];
    for (needed = 0U; needed < artifact->needed_count; ++needed) {
        if (VisitClosure(manifest, artifact->needed_indices[needed], marks,
                         order, order_count) != 0) return -1;
    }
    marks[index] = WLSCPL_VISITED;
    order[(*order_count)++] = index;
    return 0;
}

#ifndef WLSCPL_TESTING
static Dl_namespace g_sealed_namespace;
static int g_sealed_namespace_prepared;
static char g_sealed_namespace_paths[PATH_MAX * 2U];

static int PrepareSealedNamespace(const WlscplManifestV2 *manifest)
{
    const char *root_path;
    const char *last_separator;
    size_t directory_length;
    int written;

    if (g_sealed_namespace_prepared != 0) return 0;
    if (manifest == NULL || manifest->artifacts == NULL ||
        manifest->root_index >= manifest->artifact_count) return -1;
    root_path = manifest->artifacts[manifest->root_index].absolute_path;
    last_separator = strrchr(root_path, '/');
    if (last_separator == NULL || last_separator == root_path) return -1;
    directory_length = (size_t)(last_separator - root_path);
    written = snprintf(g_sealed_namespace_paths,
                       sizeof(g_sealed_namespace_paths),
                       "%.*s:/system/android/lib64:/system/lib64",
                       (int)directory_length, root_path);
    if (written <= 0 || (size_t)written >= sizeof(g_sealed_namespace_paths))
        return -1;
    dlns_init(&g_sealed_namespace, WLSCPL_SEALED_NAMESPACE);
    if (dlns_create2(&g_sealed_namespace, g_sealed_namespace_paths,
                     CREATE_INHERIT_DEFAULT) != 0)
        return -1;
    g_sealed_namespace_prepared = 1;
    return 0;
}

void *WLSCPL_OpenPreparedNamespace(const char *absolute_path, int flags)
{
    if (g_sealed_namespace_prepared == 0 || absolute_path == NULL ||
        absolute_path[0] == '\0') return NULL;
    return dlopen(absolute_path, flags);
}

static uint64_t RealCurrentPid(void *context)
{
    (void)context;
    return (uint64_t)getpid();
}

static int RealVerifyIdentity(void *context, const WlscplArtifactV2 *artifact,
                              uint16_t elf_machine,
                              WlscplVerifiedObject *verified)
{
    WleiVerifiedFile file;
    int result;
    (void)context;
    if (artifact->artifact_kind == WLSCPL_ARTIFACT_SEALED_LOAD) {
        result = WLEI_OpenVerifiedFileHex(
            artifact->absolute_path, elf_machine, artifact->sha256_hex,
            artifact->build_id_hex, &file);
    } else {
        result = WLEI_OpenVerifiedSystemFileHex(
            artifact->absolute_path, elf_machine, artifact->sha256_hex,
            artifact->build_id_hex, &file);
    }
    if (result != 0) return -1;
    verified->descriptor_token = (int64_t)file.descriptor;
    verified->device = file.device;
    verified->inode = file.inode;
    verified->size = file.size;
    return 0;
}

static int MapsState(const WlscplArtifactV2 *artifact,
                     const WlscplVerifiedObject *verified,
                     int require_bound_inode)
{
    FILE *maps = fopen("/proc/self/maps", "re");
    char line[PATH_MAX + 256U];
    int basename_seen = 0;
    if (maps == NULL) return -1;
    while (fgets(line, sizeof(line), maps) != NULL) {
        unsigned int major_value = 0U;
        unsigned int minor_value = 0U;
        unsigned long long inode_value = 0U;
        char *path = strchr(line, '/');
        const char *base;
        int basename_matches;
        if (path == NULL) continue;
        base = strrchr(path, '/');
        base = base == NULL ? path : base + 1;
        {
            char *newline = strchr(base, '\n');
            if (newline != NULL) *newline = '\0';
        }
        basename_matches = strcmp(base, artifact->soname) == 0;
        if (basename_matches) basename_seen = 1;
        /*
         * A verified OH root may have a canonical mapped basename that is
         * different from its dependency SONAME (for example libc.so maps as
         * ld-musl-aarch64.so.1 on D600). Its device/inode pair is the exact
         * identity; the basename filter is only needed when detecting whether
         * an unsealed SONAME was already mapped.
         */
        if (require_bound_inode == 0 && !basename_matches) continue;
        if (sscanf(line, "%*llx-%*llx %*4s %*llx %x:%x %llu",
                   &major_value, &minor_value, &inode_value) == 3 &&
            inode_value == (unsigned long long)verified->inode) {
            if (major_value == major((dev_t)verified->device) &&
                minor_value == minor((dev_t)verified->device)) {
                (void)fclose(maps);
                return 1;
            }
        }
    }
    if (fclose(maps) != 0) return -1;
    return require_bound_inode != 0 ? 0 : basename_seen;
}

static int RealMappingState(void *context, const WlscplArtifactV2 *artifact,
                            const WlscplVerifiedObject *verified)
{
    (void)context;
    if (artifact->artifact_kind == WLSCPL_ARTIFACT_OH_SYSTEM_ROOT ||
        IsInheritedPreloadedProvider(artifact))
        return MapsState(artifact, verified, 1);
    return MapsState(artifact, verified, 0);
}

static void *RealOpenVerifiedLocalNow(
    void *context, const WlscplArtifactV2 *artifact,
    const WlscplVerifiedObject *verified, int flags)
{
    char descriptor_path[64];
    int length;
    (void)context;
    (void)artifact;
    length = snprintf(descriptor_path, sizeof(descriptor_path),
                      "/proc/self/fd/%lld",
                      (long long)verified->descriptor_token);
    if (length <= 0 || (size_t)length >= sizeof(descriptor_path)) return NULL;
    if (g_sealed_namespace_prepared == 0) return NULL;
    return dlopen(descriptor_path, flags);
}

static int RealMappedIdentityMatches(
    void *context, const WlscplArtifactV2 *artifact,
    const WlscplVerifiedObject *verified, void *handle)
{
    (void)context;
    if (handle == NULL) return -1;
    return MapsState(artifact, verified, 1) == 1 ? 0 : -1;
}

static int RealCloseVerified(void *context, WlscplVerifiedObject *verified)
{
    WleiVerifiedFile file;
    (void)context;
    (void)memset(&file, 0, sizeof(file));
    file.descriptor = (int)verified->descriptor_token;
    verified->descriptor_token = -1;
    return WLEI_CloseVerifiedFile(&file);
}
#endif

static void CloseVerifiedRange(const WlscplOps *ops,
                               WlscplVerifiedObject *verified,
                               uint32_t count)
{
    uint32_t index;
    for (index = 0U; index < count; ++index) {
        if (verified[index].descriptor_token >= 0)
            (void)ops->close_verified(ops->context, &verified[index]);
    }
}

static void SetResult(const WlscplLoadRequestV2 *request,
                      const WlscplLoaderV2 *loader,
                      WlscplLoadResultV2 *result, WlscplError error,
                      uint32_t validated, void *provider_handle)
{
    if (result == NULL) return;
    (void)memset(result, 0, sizeof(*result));
    result->abi_version = WLSCPL_ABI_VERSION;
    result->struct_size = (uint32_t)sizeof(*result);
    result->error = error;
    result->validated_artifact_count = validated;
    if (loader != NULL) {
        result->mapped_artifact_count = loader->handle_count;
        result->constructor_completed_count =
            loader->constructor_completed_count;
        if (loader->constructor_completed_count != 0U)
            result->constructor_timing =
                WLSCPL_CONSTRUCTORS_COMPLETE_BEFORE_DLOPEN_RETURN;
    }
    if (request != NULL && request->generation_identity != NULL)
        result->generation_identity = *request->generation_identity;
    result->provider_handle = provider_handle;
}

static WlscplError Fail(WlscplLoaderV2 *loader,
                        const WlscplLoadRequestV2 *request,
                        WlscplLoadResultV2 *result, WlscplError error,
                        uint32_t validated, const WlscplOps *ops,
                        WlscplVerifiedObject *verified, uint32_t verified_count)
{
    if (ops != NULL && verified != NULL)
        CloseVerifiedRange(ops, verified, verified_count);
    if (loader != NULL) {
        loader->first_error = error;
        __atomic_store_n(&loader->state,
            loader->constructor_completed_count == 0U ?
                WLSCPL_STATE_FAILED : WLSCPL_STATE_FAILED_AFTER_CONSTRUCTORS,
            __ATOMIC_RELEASE);
    }
    SetResult(request, loader, result, error, validated, NULL);
    return error;
}

static WlscplError LoadWithOps(WlscplLoaderV2 *loader,
                               const WlscplLoadRequestV2 *request,
                               WlscplLoadResultV2 *result,
                               const WlscplOps *ops)
{
    uint8_t marks[WLSCPL_MAX_ARTIFACTS] = {0};
    uint32_t order[WLSCPL_MAX_ARTIFACTS] = {0};
    WlscplVerifiedObject verified[WLSCPL_MAX_ARTIFACTS];
    uint8_t computed_manifest_digest[WLGR_V2_SHA256_SIZE];
    uint32_t order_count = 0U;
    uint32_t expected = WLSCPL_STATE_EMPTY;
    uint32_t index;
    for (index = 0U; index < WLSCPL_MAX_ARTIFACTS; ++index)
        verified[index].descriptor_token = -1;
    if (loader == NULL || request == NULL || result == NULL || ops == NULL ||
        ops->current_pid == NULL || ops->verify_identity == NULL ||
        ops->mapping_state == NULL || ops->open_verified_local_now == NULL ||
        ops->mapped_identity_matches == NULL || ops->close_verified == NULL ||
        request->abi_version != WLSCPL_ABI_VERSION ||
        request->struct_size != sizeof(*request) ||
        request->reserved_zero != UINT32_C(0)) {
        SetResult(request, loader, result, WLSCPL_ERROR_INVALID_ARGUMENT, 0U, NULL);
        return WLSCPL_ERROR_INVALID_ARGUMENT;
    }
    if (!__atomic_compare_exchange_n(&loader->state, &expected,
            WLSCPL_STATE_LOADING, 0, __ATOMIC_ACQ_REL, __ATOMIC_ACQUIRE)) {
        SetResult(request, loader, result, WLSCPL_ERROR_ALREADY_ATTEMPTED, 0U, NULL);
        return WLSCPL_ERROR_ALREADY_ATTEMPTED;
    }
    loader->first_error = WLSCPL_OK;
    loader->handle_count = 0U;
    loader->root_handle_index = UINT32_MAX;
    loader->constructor_completed_count = 0U;
    if (request->specialization_complete != UINT32_C(1) ||
        request->parent_pid == UINT64_C(0) ||
        request->generation_identity == NULL ||
        request->parent_pid == request->generation_identity->child_pid ||
        ops->current_pid(ops->context) !=
            request->generation_identity->child_pid)
        return Fail(loader, request, result,
                    WLSCPL_ERROR_NOT_SPECIALIZED_CHILD, 0U, ops, verified, 0U);
    if (request->hook_table_ready != UINT32_C(1))
        return Fail(loader, request, result,
                    WLSCPL_ERROR_HOOK_TABLE_NOT_READY, 0U, ops, verified, 0U);
    if (request->generation_seal_verified != UINT32_C(1))
        return Fail(loader, request, result,
                    WLSCPL_ERROR_SEAL_NOT_VERIFIED, 0U, ops, verified, 0U);
    if (!wlgr_v2_identity_valid(request->generation_identity) ||
        !ManifestShapeValid(request->manifest) ||
        ComputeManifestDigest(request->manifest,
                              computed_manifest_digest) != 0 ||
        !wlgr_v2_bytes_equal(
            computed_manifest_digest, request->manifest->manifest_digest,
            WLGR_V2_SHA256_SIZE) ||
        !wlgr_v2_bytes_equal(
            request->generation_identity->artifact_manifest_digest,
            computed_manifest_digest, WLGR_V2_SHA256_SIZE))
        return Fail(loader, request, result,
                    WLSCPL_ERROR_GENERATION_IDENTITY, 0U, ops, verified, 0U);
    loader->generation_identity = *request->generation_identity;
    if (VisitClosure(request->manifest, request->manifest->root_index, marks,
                     order, &order_count) != 0 ||
        order_count != request->manifest->artifact_count)
        return Fail(loader, request, result, WLSCPL_ERROR_CLOSURE_INVALID,
                    0U, ops, verified, 0U);
    for (index = 0U; index < order_count; ++index) {
        uint32_t artifact_index = order[index];
        const WlscplArtifactV2 *artifact =
            &request->manifest->artifacts[artifact_index];
        int state;
        if (ops->verify_identity(ops->context, artifact,
                request->manifest->elf_machine,
                &verified[artifact_index]) != 0)
            return Fail(loader, request, result,
                        WLSCPL_ERROR_ARTIFACT_IDENTITY, index, ops, verified,
                        request->manifest->artifact_count);
        state = ops->mapping_state(ops->context, artifact,
                                   &verified[artifact_index]);
        if (artifact->artifact_kind == WLSCPL_ARTIFACT_SEALED_LOAD &&
            !IsInheritedPreloadedProvider(artifact) &&
            state != 0)
            return Fail(loader, request, result,
                        WLSCPL_ERROR_PREMATURE_MAPPING, index + 1U, ops,
                        verified, request->manifest->artifact_count);
        if (artifact->artifact_kind == WLSCPL_ARTIFACT_OH_SYSTEM_ROOT &&
            state != 1)
            return Fail(loader, request, result,
                        WLSCPL_ERROR_EXTERNAL_ROOT, index + 1U, ops, verified,
                        request->manifest->artifact_count);
        if (IsInheritedPreloadedProvider(artifact) && state != 1)
            return Fail(loader, request, result,
                        WLSCPL_ERROR_EXTERNAL_ROOT, index + 1U, ops, verified,
                        request->manifest->artifact_count);
    }
#ifndef WLSCPL_TESTING
    if (PrepareSealedNamespace(request->manifest) != 0)
        return Fail(loader, request, result, WLSCPL_ERROR_DLOPEN,
                    order_count, ops, verified,
                    request->manifest->artifact_count);
#endif
    for (index = 0U; index < order_count; ++index) {
        uint32_t artifact_index = order[index];
        const WlscplArtifactV2 *artifact =
            &request->manifest->artifacts[artifact_index];
        void *handle;
        if (artifact->artifact_kind == WLSCPL_ARTIFACT_OH_SYSTEM_ROOT ||
            IsInheritedPreloadedProvider(artifact)) continue;
        handle = ops->open_verified_local_now(
            ops->context, artifact, &verified[artifact_index],
            RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL)
            return Fail(loader, request, result, WLSCPL_ERROR_DLOPEN,
                        order_count, ops, verified,
                        request->manifest->artifact_count);
        loader->handles[loader->handle_count] = handle;
        if (artifact_index == request->manifest->root_index)
            loader->root_handle_index = loader->handle_count;
        ++loader->handle_count;
        ++loader->constructor_completed_count;
#ifdef WLSCPL_MUTANT_SKIP_MAPPED_INODE_BIND
        (void)ops->mapped_identity_matches(ops->context, artifact,
                &verified[artifact_index], handle);
#else
        if (ops->mapped_identity_matches(ops->context, artifact,
                &verified[artifact_index], handle) != 0)
            return Fail(loader, request, result,
                        WLSCPL_ERROR_MAPPED_IDENTITY, order_count, ops,
                        verified, request->manifest->artifact_count);
#endif
        (void)ops->close_verified(ops->context, &verified[artifact_index]);
    }
    CloseVerifiedRange(ops, verified, request->manifest->artifact_count);
    if (loader->root_handle_index == UINT32_MAX)
        return Fail(loader, request, result, WLSCPL_ERROR_CLOSURE_INVALID,
                    order_count, ops, verified, 0U);
    __atomic_store_n(&loader->state, WLSCPL_STATE_LOADED, __ATOMIC_RELEASE);
    SetResult(request, loader, result, WLSCPL_OK, order_count,
              loader->handles[loader->root_handle_index]);
    return WLSCPL_OK;
}

#ifndef WLSCPL_TESTING
WlscplError WLSCPL_LoadSealedProvider(
    WlscplLoaderV2 *loader, const WlscplLoadRequestV2 *request,
    WlscplLoadResultV2 *result)
{
    static const WlscplOps ops = {
        RealCurrentPid, RealVerifyIdentity, RealMappingState,
        RealOpenVerifiedLocalNow, RealMappedIdentityMatches,
        RealCloseVerified, NULL,
    };
    return LoadWithOps(loader, request, result, &ops);
}
#endif

#ifdef WLSCPL_TESTING
int WLSCPL_ComputeManifestDigestForTest(
    const WlscplManifestV2 *manifest,
    uint8_t digest[WLGR_V2_SHA256_SIZE])
{
    return ComputeManifestDigest(manifest, digest);
}

WlscplError WLSCPL_LoadSealedProviderForTest(
    WlscplLoaderV2 *loader, const WlscplLoadRequestV2 *request,
    WlscplLoadResultV2 *result, const WlscplTestOpsV2 *test_ops)
{
    WlscplOps ops;
    if (test_ops == NULL) {
        SetResult(request, loader, result, WLSCPL_ERROR_INVALID_ARGUMENT, 0U, NULL);
        return WLSCPL_ERROR_INVALID_ARGUMENT;
    }
    ops.current_pid = test_ops->current_pid;
    ops.verify_identity = test_ops->verify_identity;
    ops.mapping_state = test_ops->mapping_state;
    ops.open_verified_local_now = test_ops->open_verified_local_now;
    ops.mapped_identity_matches = test_ops->mapped_identity_matches;
    ops.close_verified = test_ops->close_verified;
    ops.context = test_ops->context;
    return LoadWithOps(loader, request, result, &ops);
}
#endif
