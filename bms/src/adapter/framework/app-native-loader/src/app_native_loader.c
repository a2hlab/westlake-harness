/*
 * The OpenHarmony musl headers deliberately hide PATH_MAX, strtok_r(), and
 * realpath() from a strict C11 translation unit unless it explicitly opts
 * into the X/Open interfaces.  This loader uses all three as part of its
 * path-admission boundary, so the contract belongs to this translation unit
 * rather than to a particular build recipe.  Keep this before every system
 * (and project) include: a caller's feature macros must not decide whether
 * the production source has the declarations it needs.
 */
#if defined(_XOPEN_SOURCE) && _XOPEN_SOURCE < 700
#undef _XOPEN_SOURCE
#endif
#ifndef _XOPEN_SOURCE
#define _XOPEN_SOURCE 700
#endif

#include "app_native_loader.h"
#include "oh_dlns_abi.h"

#include <errno.h>
#include <limits.h>
#include <stdarg.h>
#include <stdatomic.h>
#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

struct AnlDomain {
    Dl_namespace app;
    Dl_namespace bridge;
    bool has_bridge;
    char app_paths[PATH_MAX];
    char app_permitted_paths[PATH_MAX];
    AnlRuntimeGateV1 runtime_gate;
    void* bridge_bootstrap_handle;
};

static _Atomic unsigned long g_domain_id = 1;
static _Atomic unsigned int g_runtime_gate_state = 0;
static AnlRuntimeGateV1 g_runtime_gate;
static _Thread_local char g_error[512];
static _Thread_local bool g_gate_active;
static _Thread_local bool g_gate_reentry_detected;

static int failf(const char* fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(g_error, sizeof(g_error), fmt, ap);
    va_end(ap);
    return -1;
}

static bool text_contains_any(const char* text, const char* const* needles,
                              size_t count) {
    if (text == NULL) return false;
    for (size_t i = 0; i < count; ++i) {
        if (strstr(text, needles[i]) != NULL) return true;
    }
    return false;
}

/*
 * CORE-006/CORE-008: a failed app load must report one of three typed
 * classes, never a generic "dlopen failed".  The platform linker only hands
 * back free-form text, so the class is recovered from its characteristic
 * phrases; the raw text (carrying the failing SONAME, ELF machine or symbol)
 * is always appended to the diagnostic.  Phrases overlap ("symbol not found"
 * contains "not found"), so the most specific class is tested first.  Text
 * matching no class fails closed to F02-A12-UNCLASSIFIED instead of
 * collapsing into a generic message.
 */
static const char* classify_load_error(const char* raw) {
    static const char* const abi_mismatch[] = {
        "machine type mismatch", "e_machine", "wrong ELF class", "ELFCLASS",
        "is for EM_", "not for this architecture", "ABI mismatch",
        "wordsize mismatch", "wrong endianness",
    };
    static const char* const unsupported_symbol[] = {
        "undefined symbol", "cannot locate symbol", "unresolved symbol",
        "symbol not found", "cannot resolve symbol", "Error relocating",
    };
    static const char* const missing_dependency[] = {
        "not found", "No such file", "could not load library",
        "unable to find library", "cannot open shared object",
        "cannot open library",
    };
    if (text_contains_any(raw, abi_mismatch,
                          sizeof(abi_mismatch) / sizeof(abi_mismatch[0]))) {
        return ANL_LOAD_ERROR_ABI_MISMATCH;
    }
    if (text_contains_any(raw, unsupported_symbol,
                          sizeof(unsupported_symbol) /
                              sizeof(unsupported_symbol[0]))) {
        return ANL_LOAD_ERROR_UNSUPPORTED_SYMBOL;
    }
    if (text_contains_any(raw, missing_dependency,
                          sizeof(missing_dependency) /
                              sizeof(missing_dependency[0]))) {
        return ANL_LOAD_ERROR_MISSING_DEPENDENCY;
    }
    return ANL_LOAD_ERROR_UNCLASSIFIED;
}

static bool forbidden_path(const char* path) {
    size_t len = strlen(path);
    return path[0] != '/' || strstr(path, "/../") != NULL ||
           (len >= 3 && strcmp(path + len - 3, "/..") == 0) ||
           strncmp(path, "/data/local/tmp", 15) == 0;
}

static int validate_archive_search_path(const char* path, const char* field) {
    const char* marker = strstr(path, "!/");
    if (marker == NULL) return 0;
    if (strstr(marker + 2, "!/") != NULL) {
        return failf("%s archive path contains multiple !/ delimiters: %s",
                     field, path);
    }

    size_t archive_len = (size_t)(marker - path);
    const char* entry = marker + 2;
    size_t entry_len = strlen(entry);
    if (archive_len == 0U || archive_len >= PATH_MAX ||
        entry_len == 0U || entry[0] == '/' || strstr(entry, "//") != NULL ||
        strcmp(entry, "..") == 0 || strncmp(entry, "../", 3) == 0 ||
        strstr(entry, "/../") != NULL ||
        (entry_len >= 3U && strcmp(entry + entry_len - 3U, "/..") == 0)) {
        return failf("%s contains invalid archive search path: %s", field, path);
    }

    char archive[PATH_MAX];
    memcpy(archive, path, archive_len);
    archive[archive_len] = '\0';
    struct stat st;
    if (forbidden_path(archive) || stat(archive, &st) != 0 ||
        !S_ISREG(st.st_mode)) {
        return failf("%s archive is not an existing regular file: %s",
                     field, archive);
    }
    return 1;
}

static int validate_path_list(const char* paths, const char* field,
                              bool allow_archive_search) {
    if (paths == NULL || paths[0] == '\0') {
        return failf("%s is empty", field);
    }

    size_t paths_len = strlen(paths);
    if (paths[0] == ':' || paths[paths_len - 1] == ':' || strstr(paths, "::") != NULL) {
        return failf("%s contains an empty path", field);
    }

    char copy[PATH_MAX];
    if (snprintf(copy, sizeof(copy), "%s", paths) >= (int)sizeof(copy)) {
        return failf("%s exceeds PATH_MAX", field);
    }

    char* save = NULL;
    for (char* part = strtok_r(copy, ":", &save); part != NULL;
         part = strtok_r(NULL, ":", &save)) {
        struct stat st;
        if (forbidden_path(part)) {
            return failf("%s contains forbidden path: %s", field, part);
        }
        if (strstr(part, "!/") != NULL) {
            int archive_result = allow_archive_search
                ? validate_archive_search_path(part, field) : -1;
            if (archive_result == 1) continue;
            if (!allow_archive_search) {
                return failf("%s does not permit archive search paths: %s",
                             field, part);
            }
            return -1;
        }
        if (stat(part, &st) != 0 || !S_ISDIR(st.st_mode)) {
            return failf("%s path is not an existing directory: %s", field, part);
        }
    }
    return 0;
}

static int validate_sonames(const char* sonames) {
    if (sonames == NULL || sonames[0] == '\0') {
        return failf("bridge_shared_sonames is empty");
    }
    size_t sonames_len = strlen(sonames);
    if (sonames[0] == ':' || sonames[sonames_len - 1] == ':' ||
        strstr(sonames, "::") != NULL) {
        return failf("bridge_shared_sonames contains an empty entry");
    }
    char copy[4096];
    if (snprintf(copy, sizeof(copy), "%s", sonames) >= (int)sizeof(copy)) {
        return failf("bridge_shared_sonames is too long");
    }
    char* save = NULL;
    for (char* part = strtok_r(copy, ":", &save); part != NULL;
         part = strtok_r(NULL, ":", &save)) {
        if (part[0] == '\0' || strchr(part, '/') != NULL || strstr(part, "..") != NULL) {
            return failf("invalid bridge SONAME: %s", part);
        }
    }
    return 0;
}

static int validate_single_soname(const char* soname, const char* field) {
    if (soname == NULL || soname[0] == '\0' || strchr(soname, '/') != NULL ||
        strstr(soname, "..") != NULL || strstr(soname, ".so") == NULL) {
        return failf("%s is invalid", field);
    }
    return 0;
}

static bool path_is_in_app_domain(const AnlDomain* domain, const char* path) {
    if (path == NULL || path[0] == '\0') return false;
    if (strchr(path, '/') == NULL) return true;
    if (path[0] != '/') return false;

    char target[PATH_MAX];
    if (realpath(path, target) == NULL) return false;

    char copy[2 * PATH_MAX];
    snprintf(copy, sizeof(copy), "%s:%s", domain->app_paths, domain->app_permitted_paths);
    char* save = NULL;
    for (char* part = strtok_r(copy, ":", &save); part != NULL;
         part = strtok_r(NULL, ":", &save)) {
        char root[PATH_MAX];
        if (realpath(part, root) == NULL) continue;
        size_t root_len = strlen(root);
        if (strncmp(target, root, root_len) == 0 &&
            (target[root_len] == '/' || target[root_len] == '\0')) {
            return true;
        }
    }
    return false;
}

static int verify_runtime_ready(const AnlRuntimeGateV1* gate,
                                const char* operation) {
    if (gate == NULL || gate->verify_current_thread_ready == NULL) {
        return failf("runtime READY gate is unavailable for %s", operation);
    }
    if (g_gate_active) {
        g_gate_reentry_detected = true;
        return failf("runtime READY gate reentry rejected for %s", operation);
    }
    g_gate_active = true;
    g_gate_reentry_detected = false;
    int gate_result = gate->verify_current_thread_ready(gate->context);
    bool gate_reentered = g_gate_reentry_detected;
    g_gate_active = false;
    if (gate_result != 1 || gate_reentered) {
        /* 2026-09-30 #91-2 unlock direction (user-approved, mirrors the
         * B9 hash-lock removal pattern): the guest-thread READY verdict is
         * advisory. Westlake has no such gate at all — Flutter's Dart
         * workers load before attach and die here. Log and allow; the
         * verdict code is preserved and can be re-armed with
         * ANL_GATE_STRICT=1. Structural failures (unavailable/reentry)
         * above still hard-fail. */
        const char* strict = getenv("ANL_GATE_STRICT");
        if (strict != NULL && strict[0] == '1') {
            return failf("current thread is not READY for guest %s", operation);
        }
        fprintf(stderr,
                "[ANL-GATE] thread not READY for guest %s (result=%d reentry=%d)"
                " — log-and-allow (set ANL_GATE_STRICT=1 to re-arm)\n",
                operation, gate_result, (int)gate_reentered);
        return 0;
    }
    return 0;
}

int ANL_InstallRuntimeGate(const AnlRuntimeGateV1* gate) {
    if (gate == NULL ||
        gate->abi_version != ANL_RUNTIME_GATE_ABI_VERSION ||
        gate->struct_size != sizeof(*gate) ||
        gate->verify_current_thread_ready == NULL ||
        gate->namespace_host_ops.abi_version !=
            ANL_NAMESPACE_HOST_OPS_ABI_VERSION ||
        gate->namespace_host_ops.struct_size !=
            sizeof(gate->namespace_host_ops) ||
        gate->namespace_host_ops.runtime_generation == 0U ||
        gate->namespace_host_ops.create_configured_namespaces == NULL ||
        gate->namespace_host_ops.open_namespace == NULL ||
        gate->namespace_host_ops.reserved_zero[0] != 0U ||
        gate->namespace_host_ops.reserved_zero[1] != 0U ||
        gate->namespace_host_ops.reserved_zero[2] != 0U ||
        gate->namespace_host_ops.reserved_zero[3] != 0U ||
        gate->reserved_zero[0] != 0U || gate->reserved_zero[1] != 0U ||
        gate->reserved_zero[2] != 0U || gate->reserved_zero[3] != 0U ||
        atomic_load_explicit(&g_domain_id, memory_order_acquire) != 1UL) {
        return failf("runtime gate installation rejected");
    }
    unsigned int expected = 0U;
    if (!atomic_compare_exchange_strong_explicit(
            &g_runtime_gate_state, &expected, 1U,
            memory_order_acq_rel, memory_order_acquire)) {
        return failf("runtime gate already installed or failed");
    }
    g_runtime_gate = *gate;
    atomic_store_explicit(&g_runtime_gate_state, 2U, memory_order_release);
    g_error[0] = '\0';
    return 0;
}

int ANL_CreateDomain(const AnlDomainConfig* config, AnlDomain** out_domain) {
    if (config == NULL || out_domain == NULL) return failf("invalid argument");
    *out_domain = NULL;

    if (atomic_load_explicit(&g_runtime_gate_state,
                             memory_order_acquire) != 2U) {
        return failf("runtime READY gate is not installed");
    }
    if (verify_runtime_ready(&g_runtime_gate, "create-domain") != 0) {
        return -1;
    }

    if (validate_path_list(config->app_search_paths, "app_search_paths", true) != 0 ||
        validate_path_list(config->app_permitted_paths, "app_permitted_paths", false) != 0) {
        return -1;
    }

    bool wants_bridge = config->bridge_search_paths != NULL ||
                        config->bridge_permitted_paths != NULL ||
                        config->bridge_shared_sonames != NULL ||
                        config->bridge_bootstrap_soname != NULL;
    bool has_complete_bridge = config->bridge_search_paths != NULL &&
                               config->bridge_permitted_paths != NULL &&
                               config->bridge_shared_sonames != NULL;
    if (wants_bridge && !has_complete_bridge) {
        return failf("bridge configuration must be all-or-none");
    }
    if (wants_bridge &&
        (validate_path_list(config->bridge_search_paths, "bridge_search_paths", false) != 0 ||
         validate_path_list(config->bridge_permitted_paths, "bridge_permitted_paths", false) != 0 ||
         validate_sonames(config->bridge_shared_sonames) != 0)) {
        return -1;
    }
    if (config->bridge_bootstrap_soname != NULL &&
        (validate_single_soname(config->bridge_bootstrap_soname,
                                "bridge_bootstrap_soname") != 0 ||
         g_runtime_gate.pthread_bridge_ops.abi_version != WLPB_ABI_VERSION ||
         g_runtime_gate.pthread_bridge_ops.struct_size !=
             sizeof(WlpbHostOpsV1) ||
         g_runtime_gate.pthread_bridge_ops.generation == 0U)) {
        return failf("pthread bridge bootstrap contract is unavailable");
    }

    AnlDomain* domain = calloc(1, sizeof(*domain));
    if (domain == NULL) return failf("calloc failed: %d", errno);
    snprintf(domain->app_paths, sizeof(domain->app_paths), "%s", config->app_search_paths);
    snprintf(domain->app_permitted_paths, sizeof(domain->app_permitted_paths), "%s", config->app_permitted_paths);
    domain->runtime_gate = g_runtime_gate;

    unsigned long id = atomic_fetch_add_explicit(&g_domain_id, 1, memory_order_relaxed);
    char bridge_name[NS_NAME_MAX + 1] = {0};
    char app_name[NS_NAME_MAX + 1] = {0};

    if (wants_bridge) {
        snprintf(bridge_name, sizeof(bridge_name),
                 "westlake.anl.bridge.%ld.%lu", (long)getpid(), id);
    }
    snprintf(app_name, sizeof(app_name), "westlake.anl.app.%ld.%lu",
             (long)getpid(), id);
    /* Westlake resolves native dependencies from its runtime root before APK
     * archive entries. Reuse the already-validated bridge roots for dependency
     * lookup here; direct app loads still use domain->app_paths and the original
     * permitted-path check. Only the fixed OH platform root below is added by this adapter. */
    char dependency_search[PATH_MAX];
    char dependency_permitted[PATH_MAX];
    const char* search_paths = config->app_search_paths;
    const char* permitted_paths = config->app_permitted_paths;
    if (wants_bridge) {
        /* OH6.1 keeps the runtime C++ library in chipset-sdk-sp, outside
         * platformsdk. Match the platform runtime root already used by the
         * parent process; never use arbitrary LD_LIBRARY_PATH from the app. */
        const char* platform_root = "";
#if defined(__OHOS__)
        if (validate_path_list("/system/lib64/chipset-sdk-sp",
                               "OH runtime dependency root", false) != 0) {
            free(domain);
            return -1;
        }
        platform_root = ":/system/lib64/chipset-sdk-sp";
#endif
        int sn = snprintf(dependency_search, sizeof(dependency_search), "%s%s:%s",
                          config->bridge_search_paths, platform_root,
                          config->app_search_paths);
        int pn = snprintf(dependency_permitted, sizeof(dependency_permitted), "%s%s:%s",
                          config->bridge_permitted_paths, platform_root,
                          config->app_permitted_paths);
        if (sn < 0 || (size_t)sn >= sizeof(dependency_search) ||
            pn < 0 || (size_t)pn >= sizeof(dependency_permitted)) {
            free(domain);
            return failf("runtime dependency paths exceed namespace limit");
        }
        search_paths = dependency_search;
        permitted_paths = dependency_permitted;
        fprintf(stderr, "[B87-NS] runtime dependency search=%s\n", search_paths);
    }
    /* liblog's OH6.1 NEEDED closure must be inherited by name too. The
     * default namespace already owns these platform libraries; do not add
     * broad system directories to the app's permitted paths. */
    char log_shared_sonames[PATH_MAX];
    const char* shared_sonames = config->bridge_shared_sonames;
    const char* log_name = wants_bridge ? strstr(shared_sonames, "liblog.so") : NULL;
    if (log_name != NULL &&
        (log_name == shared_sonames || log_name[-1] == ':') &&
        (log_name[9] == '\0' || log_name[9] == ':')) {
        int n = snprintf(log_shared_sonames, sizeof(log_shared_sonames),
                         "%s:libbionic_compat.so:libc++.so:libhilog.so:"
                         "libbegetutil.z.so:libsec_shared.z.so:libconfigpolicy_util.z.so:"
                         "libsystemparam.z.so:libc.so",
                         shared_sonames);
        if (n < 0 || (size_t)n >= sizeof(log_shared_sonames)) {
            free(domain);
            return failf("log dependency sonames exceed namespace limit");
        }
        shared_sonames = log_shared_sonames;
    }
    void* bootstrap_handle = NULL;
    int rc = domain->runtime_gate.namespace_host_ops.create_configured_namespaces(
        wants_bridge ? &domain->bridge : NULL,
        wants_bridge ? bridge_name : NULL,
        wants_bridge ? config->bridge_search_paths : NULL,
        wants_bridge ? config->bridge_permitted_paths : NULL,
        wants_bridge ? shared_sonames : NULL,
        wants_bridge ? config->bridge_bootstrap_soname : NULL,
        wants_bridge ? &domain->runtime_gate.pthread_bridge_ops : NULL,
        &bootstrap_handle, &domain->app, app_name,
        search_paths, permitted_paths);
    if (rc != 0) {
        free(domain);
        return failf("default-owner namespace configuration failed: %d", rc);
    }
    domain->has_bridge = wants_bridge;
    domain->bridge_bootstrap_handle = bootstrap_handle;

    g_error[0] = '\0';
    *out_domain = domain;
    return 0;
}

void* ANL_Dlopen(AnlDomain* domain, const char* path, int mode) {
    if (domain == NULL || !path_is_in_app_domain(domain, path)) {
        failf("path is outside app domain: %s", path == NULL ? "(null)" : path);
        return NULL;
    }
    if ((mode & RTLD_GLOBAL) != 0) {
        failf("RTLD_GLOBAL is forbidden for app domains");
        return NULL;
    }
    if (verify_runtime_ready(&domain->runtime_gate, "dlopen") != 0) {
        return NULL;
    }
    dlerror();
    void* handle = domain->runtime_gate.namespace_host_ops.open_namespace(
        &domain->app, path, mode | RTLD_LOCAL);
    if (handle == NULL) {
        const char* error = dlerror();
        failf("%s: dlopen_ns failed for %s: %s", classify_load_error(error),
              path,
              error == NULL ? "linker produced no diagnostic" : error);
    } else {
        g_error[0] = '\0';
    }
    return handle;
}

void* ANL_Dlsym(void* handle, const char* symbol) {
    if (handle == NULL || symbol == NULL || symbol[0] == '\0') {
        failf("invalid dlsym argument");
        return NULL;
    }
    dlerror();
    void* value = dlsym(handle, symbol);
    const char* error = dlerror();
    if (error != NULL) {
        failf("dlsym failed for %s: %s", symbol, error);
        return NULL;
    }
    g_error[0] = '\0';
    return value;
}

int ANL_Dlclose(void* handle) {
    if (handle == NULL) return failf("invalid dlclose handle");
    if (atomic_load_explicit(&g_runtime_gate_state,
                             memory_order_acquire) != 2U ||
        verify_runtime_ready(&g_runtime_gate, "dlclose") != 0) {
        return -1;
    }
    dlerror();
    int rc = dlclose(handle);
    if (rc != 0) {
        const char* error = dlerror();
        return failf("dlclose failed: %s", error == NULL ? "unknown" : error);
    }
    g_error[0] = '\0';
    return 0;
}

const char* ANL_Dlerror(void) {
    return g_error[0] == '\0' ? NULL : g_error;
}

const char* ANL_GetNamespaceName(const AnlDomain* domain) {
    return domain == NULL ? NULL : domain->app.name;
}

void ANL_ReleaseDomainHandle(AnlDomain* domain) {
    free(domain);
}
