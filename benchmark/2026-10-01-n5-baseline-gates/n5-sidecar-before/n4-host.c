/*
 * Adapter-owned main for a stock OH appspawn host on the AppSpawnX socket.
 * All socket, decoder, context, fork, security-hook and result-pipe behavior
 * remains in the frozen stock StartSpawnService implementation.
 */

#include <dlfcn.h>
#include <elf.h>
#include <errno.h>
#include <limits.h>
#include <pthread.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "appspawn_modulemgr.h"
#include "appspawn_service.h"
#include "appspawn_utils.h"
#include "securec.h"
#include "westlake_elf_identity.h"
#include "westlake_stock_host_services.h"

#define WLASC_STOCK_PRELOAD "libappspawn_helper.z.so"
#define WLASC_PLUGIN_NAME "westlake_android_child"
#define WLASC_PLUGIN_PATH \
    "/system/lib64/appspawn/libwestlake_android_child.z.so"
#define WLASC_SOCKET_NAME "AppSpawnX"
#define WLASC_SERVICE_NAME "appspawn-x"
#define WLASC_BIONIC_COMPAT_PATH \
    "/system/android/lib64/libbionic_compat.so"

typedef int (*WlascInheritAndroidRuntimeV1)(void *target_namespace);

#ifndef WLASC_PLUGIN_GENERATION_SHA_HEX
#error "WLASC_PLUGIN_GENERATION_SHA_HEX must bind the plugin input closure"
#endif
#ifndef WLAR_GENERATION_SHA_HEX
#error "WLAR_GENERATION_SHA_HEX must bind the runtime provider generation"
#endif

_Static_assert(sizeof(WlascStockHostServicesV1) == 256,
               "stock host services ABI drift");
_Static_assert(sizeof(pthread_t) <= sizeof(uint64_t),
               "pthread_t does not fit the host thread-token ABI");

#if defined(__GNUC__) || defined(__clang__)
#define WLASC_NOINLINE __attribute__((noinline))
#else
#define WLASC_NOINLINE
#endif

static int NamespaceNameOwnedByCurrentProcess(const char *name,
                                              const char *kind)
{
    char prefix[96];
    const char *suffix;
    int prefix_length;
    pid_t pid = getpid();

    if (name == NULL || kind == NULL || pid <= 0) {
        return 0;
    }
    prefix_length = snprintf(prefix, sizeof(prefix), "westlake.anl.%s.%ld.",
                             kind, (long)pid);
    if (prefix_length <= 0 || (size_t)prefix_length >= sizeof(prefix) ||
        strncmp(name, prefix, (size_t)prefix_length) != 0) {
        return 0;
    }
    suffix = name + prefix_length;
    if (*suffix == '\0') {
        return 0;
    }
    while (*suffix != '\0') {
        if (*suffix < '0' || *suffix > '9') {
            return 0;
        }
        ++suffix;
    }
    return 1;
}

static WLASC_NOINLINE int NamespaceResultFence(int result)
{
    volatile int fenced = result;
    return fenced;
}

static WLASC_NOINLINE void *NamespaceHandleFence(void *handle)
{
    void *volatile fenced = handle;
    return fenced;
}

static int NamespaceInputsPresent(const char *search_paths,
                                  const char *permitted_paths)
{
    return search_paths != NULL && search_paths[0] != '\0' &&
        permitted_paths != NULL && permitted_paths[0] != '\0';
}

static bool flutter_package_path(const char* text) {
    static const char* const packages[] = {
        "chat.fluffy.fluffychat", "app.alextran.immich", "com.tombursch.kitchenowl",
        "deckers.thibault.aves.libre", "com.adilhanney.saber", "org.localsend.localsend_app"
    };
    for (size_t i = 0; i < sizeof(packages)/sizeof(packages[0]); ++i) {
        const char* p = text;
        while ((p = strstr(p, packages[i])) != NULL) {
            size_t n = strlen(packages[i]);
            if ((p == text || p[-1] == '/') && (p[n] == '/' || p[n] == ':' || p[n] == '\0')) return true;
            p += n;
        }
    }
    return false;
}

static bool native_cluster_path(const char* text) {
    const char* packages[] = {"com.ichi2.anki", "com.unciv.app", "app.organicmaps",
        "com.nextcloud.client", "com.mcdonalds.app", "io.anuke.mindustry",
        "com.emn8.mobilem8.nativeapp.bk", "im.vector.app",
        "org.mozilla.firefox", "org.mozilla.fennec_fdroid", "org.videolan.vlc", "org.ppsspp.ppsspp", "com.shatteredpixel.shatteredpixeldungeon"};
    for (size_t i=0; i<sizeof(packages)/sizeof(packages[0]); ++i) {
        const char* q=text;
        while ((q=strstr(q, packages[i])) != NULL) {
            size_t n=strlen(packages[i]);
            if ((q==text || q[-1]=='/') && (q[n]=='/' || q[n]==':' || q[n]=='\0')) return true;
            q+=n;
        }
    }
    return false;
}


static WLASC_NOINLINE int StockCreateConfiguredNamespaces(
    void *bridge_namespace_opaque, const char *bridge_name,
    const char *bridge_search_paths, const char *bridge_permitted_paths,
    const char *bridge_shared_sonames, const char *bridge_bootstrap_soname,
    const WlpbHostOpsV1 *pthread_bridge_ops,
    void **out_bridge_bootstrap_handle, void *app_namespace_opaque,
    const char *app_name, const char *app_search_paths,
    const char *app_permitted_paths)
{
    Dl_namespace *bridge_namespace =
        (Dl_namespace *)bridge_namespace_opaque;
    Dl_namespace *app_namespace = (Dl_namespace *)app_namespace_opaque;
    void *bootstrap_handle = NULL;
    int result;
    const bool wants_bridge = bridge_namespace != NULL;

    if (out_bridge_bootstrap_handle == NULL || app_namespace == NULL ||
        !NamespaceNameOwnedByCurrentProcess(app_name, "app") ||
        !NamespaceInputsPresent(app_search_paths, app_permitted_paths)) {
        return NamespaceResultFence(EINVAL);
    }
    *out_bridge_bootstrap_handle = NULL;
    if (wants_bridge != (bridge_name != NULL) ||
        wants_bridge != (bridge_search_paths != NULL) ||
        wants_bridge != (bridge_permitted_paths != NULL) ||
        wants_bridge != (bridge_shared_sonames != NULL)) {
        return NamespaceResultFence(EINVAL);
    }
    if (!wants_bridge &&
        (bridge_bootstrap_soname != NULL || pthread_bridge_ops != NULL)) {
        return NamespaceResultFence(EINVAL);
    }

    if (wants_bridge) {
        if (!NamespaceNameOwnedByCurrentProcess(bridge_name, "bridge") ||
            !NamespaceInputsPresent(bridge_search_paths,
                                    bridge_permitted_paths) ||
            bridge_shared_sonames[0] == '\0' ||
            (bridge_bootstrap_soname != NULL &&
             (bridge_bootstrap_soname[0] == '\0' ||
              strchr(bridge_bootstrap_soname, '/') != NULL ||
              pthread_bridge_ops == NULL))) {
            return NamespaceResultFence(EINVAL);
        }
        dlns_init(bridge_namespace, bridge_name);
        result = dlns_create2(bridge_namespace, bridge_search_paths,
                              CREATE_INHERIT_DEFAULT);
        if (result != 0) {
            return NamespaceResultFence(result);
        }
        result = dlns_set_namespace_separated(bridge_namespace->name, true);
        if (result != 0) {
            return NamespaceResultFence(result);
        }
        result = dlns_set_namespace_permitted_paths(
            bridge_namespace->name, bridge_permitted_paths);
        if (result != 0) {
            return NamespaceResultFence(result);
        }
        result = dlns_set_namespace_allowed_libs(
            bridge_namespace->name, bridge_shared_sonames);
        if (result != 0) {
            return NamespaceResultFence(result);
        }

        if (bridge_bootstrap_soname != NULL) {
            typedef int (*InstallBridgeOps)(const WlpbHostOpsV1 *ops);
            InstallBridgeOps install = NULL;
            void *symbol;

            dlerror();
            bootstrap_handle = dlopen_ns(
                bridge_namespace, bridge_bootstrap_soname,
                RTLD_NOW | RTLD_LOCAL);
            if (bootstrap_handle == NULL) {
                return NamespaceResultFence(ENOENT);
            }
            dlerror();
            symbol = dlsym(bootstrap_handle, "WLPB_InstallHostOps");
            if (symbol == NULL || dlerror() != NULL ||
                sizeof(symbol) != sizeof(install)) {
                (void)dlclose(bootstrap_handle);
                return NamespaceResultFence(ENOEXEC);
            }
            (void)memcpy(&install, &symbol, sizeof(install));
            result = install(pthread_bridge_ops);
            if (result != 0) {
                (void)dlclose(bootstrap_handle);
                return NamespaceResultFence(result);
            }
            *out_bridge_bootstrap_handle = bootstrap_handle;
        }
    }

    dlns_init(app_namespace, app_name);
    result = dlns_create2(app_namespace, app_search_paths,
                          LOCAL_NS_PREFERED);
    if (result != 0) {
        return NamespaceResultFence(result);
    }
    result = dlns_set_namespace_separated(app_namespace->name, true);
    if (result != 0) {
        return NamespaceResultFence(result);
    }
    result = dlns_set_namespace_permitted_paths(
        app_namespace->name, app_permitted_paths);
    if (result != 0) {
        return NamespaceResultFence(result);
    }
    /* Westlake OpenInAndroidNamespace: use a direct edge to the existing
     * owner. OH musl inheritance is one hop. Only the exact Flutter/native package lists with private search prefixes
     * request this branch; baseline control domains do not.
     * No system search roots and no extra DFX/runtime instances in the app. */
    const bool flutter_private = wants_bridge &&
        strncmp(app_search_paths, "/system/android/lib64/westlake_flutter:",
                strlen("/system/android/lib64/westlake_flutter:")) == 0 &&
        (flutter_package_path(app_search_paths) || flutter_package_path(app_permitted_paths));
    const bool native_private = wants_bridge &&
        strncmp(app_search_paths, "/system/android/lib64/westlake_native:",
                strlen("/system/android/lib64/westlake_native:")) == 0 &&
        (native_cluster_path(app_search_paths) || native_cluster_path(app_permitted_paths));
    if (flutter_private || native_private) {
        Dl_namespace system_owner, runtime_owner;
        result = dlns_get("default", &system_owner);
        if (result != 0) return NamespaceResultFence(result);
        result = dlns_get("westlake.sealed.child", &runtime_owner);
        if (result != 0) return NamespaceResultFence(result);
        result = dlns_inherit(app_namespace, &system_owner,
            "libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libsurface.z.so:liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:libstdc++.so:libOpenSLES.so");
        if (result != 0) return NamespaceResultFence(result);
        result = dlns_inherit(app_namespace, &runtime_owner,
            "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so");
        if (result != 0) return NamespaceResultFence(result);
        const bool needs_runtime = flutter_private ||
            strstr(app_search_paths, "/com.emn8.mobilem8.nativeapp.bk/") ||
            strstr(app_search_paths, "/com.mcdonalds.app/") ||
            strstr(app_search_paths, "/app.organicmaps/") ||
            strstr(app_search_paths, "/im.vector.app/") ||
            strstr(app_search_paths, "/org.ppsspp.ppsspp/");
        if (needs_runtime) {
        /* real-work WLSCPL_InheritAndroidRuntimeV1 publishes the resident object
         * by exact absolute path after inheritance. Ordinary lookup follows lazy
         * owner edges. Device acceptance requires one runtime instance. */
        void* resident = dlopen_ns(app_namespace,
            "/system/android/lib64/liboh_android_runtime.so",
            RTLD_NOW | RTLD_GLOBAL);
        if (resident == NULL) {
            APPSPAWN_LOGE("[N3-OWNER] resident runtime unavailable: %{public}s", dlerror());
            return NamespaceResultFence(ENOENT);
        }
        APPSPAWN_LOGI("[N3-OWNER] resident runtime published for %{public}s", app_name);
        }
        if (native_private && (strstr(app_search_paths, "/io.anuke.mindustry/") ||
                               strstr(app_permitted_paths, "/io.anuke.mindustry/") ||
                               strstr(app_search_paths, "/org.ppsspp.ppsspp/") ||
                               strstr(app_permitted_paths, "/org.ppsspp.ppsspp/"))) {
            /* Open the OH audio implementation from its platform owner, not a
             * second copy inside the app. Android extension IIDs come from the
             * private Westlake ABI library loaded below. */
            void* audio = dlopen_ns(app_namespace, "/system/lib64/libOpenSLES.so",
                                    RTLD_NOW | RTLD_GLOBAL);
            if (audio == NULL) {
                APPSPAWN_LOGE("[N4-AUDIO] app-owner open failed: %{public}s", dlerror());
                return NamespaceResultFence(ENOENT);
            }
            const char* audio_symbols[] = {
                "slCreateEngine", "SL_IID_ENGINE", "SL_IID_VOLUME", "SL_IID_PLAY", "SL_IID_BUFFERQUEUE"
            };
            for (size_t symbol_index = 0;
                 symbol_index < sizeof(audio_symbols) / sizeof(audio_symbols[0]); ++symbol_index) {
                if (dlsym(audio, audio_symbols[symbol_index]) == NULL) {
                    APPSPAWN_LOGE("[N4-AUDIO] provider lacks %{public}s", audio_symbols[symbol_index]);
                    return NamespaceResultFence(ENOENT);
                }
            }
        }
    }
    if (wants_bridge) {
        result = dlns_inherit(app_namespace, bridge_namespace,
                              bridge_shared_sonames);
        if (result != 0) {
            return NamespaceResultFence(result);
        }
    }
    if (flutter_private || native_private) {
        /* OH 6.1 musl ignores DF_1_GLOBAL: its add_syms/removal is controlled
         * by dlopen mode. Promote only the declared ABI DSO in selected app
         * domains, not arbitrary app libraries or system providers. */
        const char* abi = flutter_private
            ? "/system/android/lib64/westlake_flutter/libwestlake_native_abi.so"
            : "/system/android/lib64/westlake_native/libwestlake_native_abi.so";
        void* handle = dlopen_ns(app_namespace, abi, RTLD_NOW | RTLD_GLOBAL);
        if (handle == NULL) return NamespaceResultFence(ENOENT);
        fprintf(stderr, "[N2-OWNER] %s ABI global ready; search=%s permitted=%s\n",
                app_name, app_search_paths, app_permitted_paths);
    }
    return NamespaceResultFence(0);
}

static WLASC_NOINLINE void *StockOpenNamespace(
    void *app_namespace_opaque, const char *path, int mode)
{
    Dl_namespace *app_namespace = (Dl_namespace *)app_namespace_opaque;
    void *handle;

    if (app_namespace == NULL || path == NULL || path[0] == '\0' ||
        !NamespaceNameOwnedByCurrentProcess(app_namespace->name, "app") ||
        (mode & RTLD_GLOBAL) != 0) {
        return NamespaceHandleFence(NULL);
    }
    handle = dlopen_ns(app_namespace, path, mode | RTLD_LOCAL);
    return NamespaceHandleFence(handle);
}

static uint8_t HexNibble(char value)
{
    if (value >= '0' && value <= '9') {
        return (uint8_t)(value - '0');
    }
    if (value >= 'a' && value <= 'f') {
        return (uint8_t)(value - 'a' + 10);
    }
    return UINT8_C(255);
}

static int FillHex(uint8_t *output, size_t output_size,
                   const char *hex, size_t hex_size)
{
    size_t index;
    if (output == NULL || hex == NULL ||
        hex_size != output_size * 2U + 1U ||
        hex[hex_size - 1U] != '\0') {
        return -1;
    }
    for (index = 0; index < output_size; ++index) {
        uint8_t high = HexNibble(hex[index * 2U]);
        uint8_t low = HexNibble(hex[index * 2U + 1U]);
        if (high == UINT8_C(255) || low == UINT8_C(255)) {
            return -1;
        }
        output[index] = (uint8_t)((high << 4U) | low);
    }
    return 0;
}

static uint64_t RuntimeGeneration(void)
{
    static const char runtime_generation_hex[] = WLAR_GENERATION_SHA_HEX;
    uint64_t generation = UINT64_C(0);
    size_t index;
    for (index = 0; index < 8U; ++index) {
        uint8_t high = HexNibble(runtime_generation_hex[index * 2U]);
        uint8_t low = HexNibble(runtime_generation_hex[index * 2U + 1U]);
        if (high == UINT8_C(255) || low == UINT8_C(255)) {
            return UINT64_C(0);
        }
        generation = (generation << 8U) |
            (uint64_t)((high << 4U) | low);
    }
    return generation;
}

static uint64_t CurrentThreadToken(void)
{
    pthread_t thread = pthread_self();
    uint64_t token = UINT64_C(0);
    (void)memcpy(&token, &thread, sizeof(thread));
    return token;
}

/* File identities are checked by deploy_generation, not the process loader. */
static int ResolvePluginPath(char resolved_path[PATH_MAX])
{
    return realpath(WLASC_PLUGIN_PATH, resolved_path) == NULL ? -1 : 0;
}

static int LookupExactPluginSymbol(void *plugin_handle,
                                   const char *plugin_path,
                                   const char *symbol_name,
                                   void **out_symbol)
{
    if (plugin_handle == NULL || plugin_path == NULL ||
        symbol_name == NULL || out_symbol == NULL) return -1;
    *out_symbol = dlsym(plugin_handle, symbol_name);
    return *out_symbol == NULL ? -1 : 0;
}

static int InstallPluginHostServices(void *plugin_handle,
                                     const char *plugin_path)
{
    typedef const WlascContractV1 *(*GetContract)(void);
    typedef int (*InstallServices)(const WlascStockHostServicesV1 *);
    static const char plugin_generation_hex[] =
        WLASC_PLUGIN_GENERATION_SHA_HEX;
    static const char runtime_generation_hex[] = WLAR_GENERATION_SHA_HEX;
    WlascStockHostServicesV1 services;
    WlncParentIdentityV1 parent_identity;
    const WlascContractV1 *contract;
    void *contract_symbol;
    void *install_symbol;
    GetContract get_contract = NULL;
    InstallServices install_services = NULL;
    int install_result;
    pid_t parent_pid;
    _Static_assert(sizeof(get_contract) == sizeof(contract_symbol),
                   "function/data pointer ABI mismatch");
    _Static_assert(sizeof(install_services) == sizeof(install_symbol),
                   "function/data pointer ABI mismatch");

    if (LookupExactPluginSymbol(
            plugin_handle, plugin_path, "WLASC_GetContractV1",
            &contract_symbol) != 0) {
        return -1;
    }
    (void)memcpy(&get_contract, &contract_symbol, sizeof(get_contract));
    contract = get_contract();
    if (contract == NULL || contract->abi_version != WLASC_ABI_VERSION ||
        contract->struct_size != sizeof(*contract) ||
        contract->preload_priority != WLASC_PRELOAD_PRIORITY ||
        contract->parent_stage != WLASC_PARENT_STAGE ||
        contract->child_stage != WLASC_CHILD_STAGE ||
        contract->tail_priority != WLASC_TAIL_PRIORITY ||
        contract->no_sandbox_flag_index != WLASC_FLAG_NO_SANDBOX ||
        contract->ignore_sandbox_flag_index != WLASC_FLAG_IGNORE_SANDBOX ||
        contract->stock_security_owner_required != UINT32_C(1) ||
        contract->runtime_security_operations_required_zero != UINT32_C(1) ||
        contract->request_size != sizeof(WlascAndroidChildRequestV1) ||
        contract->receipt_size != sizeof(WlascStockStageReceiptV1)) {
        return -1;
    }

    if (LookupExactPluginSymbol(
            plugin_handle, plugin_path,
            "WLASC_InstallStockHostServicesV1", &install_symbol) != 0) {
        return -1;
    }
    (void)memcpy(&install_services, &install_symbol,
                 sizeof(install_services));

    (void)memset(&services, 0, sizeof(services));
    services.abi_version = WLASC_STOCK_HOST_SERVICES_ABI_VERSION;
    services.struct_size = sizeof(services);
    services.runtime_generation = RuntimeGeneration();
    if (services.runtime_generation == UINT64_C(0) ||
        FillHex(services.runtime_provider_sha256,
                sizeof(services.runtime_provider_sha256),
                runtime_generation_hex,
                sizeof(runtime_generation_hex)) != 0 ||
        FillHex(services.plugin_generation_sha256,
                sizeof(services.plugin_generation_sha256),
                plugin_generation_hex,
                sizeof(plugin_generation_hex)) != 0 ||
        0 /* plugin file identity fields remain zero; ABI slots retained */) {
        return -1;
    }
    services.add_server_stage_hook = AddServerStageHook;
    services.add_app_spawn_hook = AddAppSpawnHook;
    services.get_app_spawn_msg_info = GetAppSpawnMsgInfo;
    services.check_app_spawn_msg_flag = CheckAppSpawnMsgFlag;
    services.reg_child_looper = RegChildLooper;
    services.clear_child_environment = AppSpawnEnvClear;
    services.current_thread_token = CurrentThreadToken;
    services.prepare_parent_runtime =
        westlake_native_compat_prepare_parent_runtime;
    services.verify_parent_preload_thread_ready =
        westlake_native_compat_verify_parent_preload_thread_ready;
    services.prepare_main_thread =
        westlake_native_compat_prepare_main_thread;
    services.verify_current_thread_ready =
        westlake_native_compat_verify_current_thread_ready;
    services.get_audit_snapshot =
        westlake_native_compat_get_audit_snapshot;
    services.get_pthread_bridge_ops =
        westlake_native_compat_get_pthread_bridge_ops;
    services.create_configured_namespaces =
        StockCreateConfiguredNamespaces;
    services.open_namespace = StockOpenNamespace;
    install_result = install_services(&services);
    if (install_result != 0) {
        return -1;
    }

    parent_pid = getpid();
    if (parent_pid <= 0) {
        return -1;
    }
    (void)memset(&parent_identity, 0, sizeof(parent_identity));
    parent_identity.abi_version = WLNC_ABI_VERSION;
    parent_identity.struct_size = sizeof(parent_identity);
    parent_identity.runtime_generation = services.runtime_generation;
    parent_identity.pid = (uint32_t)parent_pid;
    parent_identity.uid = (uint32_t)getuid();
    parent_identity.gid = (uint32_t)getgid();
    (void)memcpy(parent_identity.runtime_provider_sha256,
                 services.runtime_provider_sha256,
                 sizeof(parent_identity.runtime_provider_sha256));
    return services.prepare_parent_runtime(&parent_identity) ==
                   WLNC_PREPARE_OK
               ? 0
               : -1;
}

static void CheckPreload(char *const argv[])
{
    char buffer[256] = WLASC_STOCK_PRELOAD;
    char *preload = getenv("LD_PRELOAD");
    char *position = preload != NULL ?
        strstr(preload, WLASC_STOCK_PRELOAD) : NULL;
    if (position != NULL) {
        int prefix_length = (int)(position - preload);
        int length = sprintf_s(buffer, sizeof(buffer), "%.*s%s",
                               prefix_length, preload,
                               position + strlen(WLASC_STOCK_PRELOAD));
        APPSPAWN_CHECK(length >= 0, return,
                       "preload too long?: %{public}s", preload);
        if (length == 0) {
            int result = unsetenv("LD_PRELOAD");
            APPSPAWN_CHECK(result == 0, return,
                           "unsetenv fail(%{public}d)", errno);
        } else {
            int result = setenv("LD_PRELOAD", buffer, true);
            APPSPAWN_CHECK(result == 0, return,
                           "setenv fail(%{public}d): %{public}s", errno,
                           buffer);
        }
        return;
    }
    if (preload != NULL && preload[0] != '\0') {
        int length = sprintf_s(buffer, sizeof(buffer), "%s:"
                               WLASC_STOCK_PRELOAD, preload);
        APPSPAWN_CHECK(length > 0, return,
                       "preload too long: %{public}s", preload);
    }
    {
        int result = setenv("LD_PRELOAD", buffer, true);
        ssize_t read_count;
        APPSPAWN_CHECK(result == 0, return,
                       "setenv fail(%{public}d): %{public}s", errno, buffer);
        read_count = readlink("/proc/self/exe", buffer, sizeof(buffer) - 1U);
        APPSPAWN_CHECK(read_count != -1, return,
                       "readlink fail: /proc/self/exe: %{public}d", errno);
        buffer[read_count] = '\0';
        if (strcmp(buffer, "/system/bin/nativespawn") != 0) {
            result = execv(buffer, argv);
            APPSPAWN_LOGE("execv fail: %{public}s: %{public}d: %{public}d",
                          buffer, errno, result);
        }
    }
}

int main(int argc, char *const argv[])
{
    static const AppSpawnStartArg start_argument = {
        MODE_FOR_APP_SPAWN,
        MODULE_DEFAULT,
        WLASC_SOCKET_NAME,
        WLASC_SERVICE_NAME,
        1,
    };
    char stock_long_proc_name[APP_LEN_PROC_NAME];
    char *stock_argv[2];
    AppSpawnContent *content;
    char plugin_path[PATH_MAX];
    char plugin_path_after_load[PATH_MAX];
    void *plugin_handle;
    if (argc <= 0 || argv == (char *const *)0 || argv[0] == (char *)0) {
        return 1;
    }
    if (memset_s(stock_long_proc_name, sizeof(stock_long_proc_name), 0,
                 sizeof(stock_long_proc_name)) != EOK ||
        strncpy_s(stock_long_proc_name, sizeof(stock_long_proc_name),
                  WLASC_SERVICE_NAME, strlen(WLASC_SERVICE_NAME)) != EOK) {
        return 1;
    }
    stock_argv[0] = stock_long_proc_name;
    stock_argv[1] = (char *)0;
    InitCommonEnv();
    CheckPreload(argv);
    (void)signal(SIGPIPE, SIG_IGN);

    /*
     * This creates MODULE_DEFAULT before StartSpawnService, so its later
     * AppSpawnLoadAutoRunModules(MODULE_DEFAULT) cannot scan the ACE child
     * processor directory. MODULE_COMMON is still loaded unchanged.
     */
    if (ResolvePluginPath(plugin_path) != 0 ||
        AppSpawnModuleMgrInstall(WLASC_PLUGIN_NAME) != 0 ||
        ResolvePluginPath(plugin_path_after_load) != 0 ||
        strcmp(plugin_path, plugin_path_after_load) != 0) {
        return 1;
    }
    plugin_handle = dlopen(plugin_path, RTLD_NOW | RTLD_NOLOAD);
    if (plugin_handle == NULL ||
        InstallPluginHostServices(plugin_handle, plugin_path) != 0) {
        if (plugin_handle != NULL) {
            (void)dlclose(plugin_handle);
        }
        return 1;
    }
    if (dlclose(plugin_handle) != 0) {
        return 1;
    }
    content = StartSpawnService(&start_argument, sizeof(stock_long_proc_name),
                                1, stock_argv);
    if (content == (AppSpawnContent *)0 ||
        content->runAppSpawn == (void (*)(AppSpawnContent *, int,
                                          char *const []))0) {
        return 1;
    }
    content->runAppSpawn(content, 1, stock_argv);
    return 1;
}
