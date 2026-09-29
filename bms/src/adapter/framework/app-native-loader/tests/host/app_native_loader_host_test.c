#include "app_native_loader.h"
#include "mock_dlns.h"

#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <pthread.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

static int g_checks;
static int g_failures;

typedef enum GateMode {
    GATE_ALLOW = 0,
    GATE_DENY = 1,
    GATE_RETURN_TWO = 2,
    GATE_REENTER = 3,
    GATE_OWNER_THREAD_ONLY = 4,
    GATE_REENTER_CLOSE = 5,
} GateMode;

static GateMode g_gate_mode;
static AnlDomain* g_reentry_domain;
static void* g_reentry_close_handle;
static pthread_t g_gate_owner;

static int runtime_gate(void* context) {
    (void)context;
    if (g_gate_mode == GATE_DENY) return 0;
    if (g_gate_mode == GATE_RETURN_TWO) return 2;
    if (g_gate_mode == GATE_REENTER) {
        (void)ANL_Dlopen(g_reentry_domain, "libroot.so", RTLD_NOW);
        return 1;
    }
    if (g_gate_mode == GATE_REENTER_CLOSE) {
        (void)ANL_Dlclose(g_reentry_close_handle);
        return 1;
    }
    if (g_gate_mode == GATE_OWNER_THREAD_ONLY) {
        return pthread_equal(pthread_self(), g_gate_owner) ? 1 : 0;
    }
    return 1;
}

static int bridge_issue(void* context, WlpbTicketStorageV1* ticket) {
    (void)context;
    (void)ticket;
    return 1;
}

static int bridge_cancel(void* context, const WlpbTicketStorageV1* ticket) {
    (void)context;
    (void)ticket;
    return 1;
}

static int bridge_prepare(void* context, const WlpbTicketStorageV1* ticket,
                          WlpbReceiptStorageV1* receipt) {
    (void)context;
    (void)ticket;
    (void)receipt;
    return 1;
}

static int bridge_verify(void* context,
                         const WlpbReceiptStorageV1* receipt) {
    (void)context;
    (void)receipt;
    return 1;
}

static int bridge_retire(void* context,
                         const WlpbReceiptStorageV1* receipt) {
    (void)context;
    (void)receipt;
    return 1;
}

static uint64_t bridge_thread_id(void* context) {
    (void)context;
    return UINT64_C(1);
}

static int bridge_pthread_create(void* context, uint64_t* thread,
                                 const WlpbMuslAttrStorageV1* attribute,
                                 WlpbStartRoutine start, void* argument) {
    (void)context;
    (void)thread;
    (void)attribute;
    (void)start;
    (void)argument;
    return 0;
}

static void bridge_pthread_exit(void* context, void* result) {
    (void)context;
    (void)result;
}

static int bridge_attr_init(void* context,
                            WlpbMuslAttrStorageV1* attribute) {
    (void)context;
    (void)attribute;
    return 0;
}

static int bridge_attr_destroy(void* context,
                               WlpbMuslAttrStorageV1* attribute) {
    (void)context;
    (void)attribute;
    return 0;
}

static int bridge_attr_setdetachstate(void* context,
                                      WlpbMuslAttrStorageV1* attribute,
                                      int state) {
    (void)context;
    (void)attribute;
    (void)state;
    return 0;
}

static int bridge_attr_setstacksize(void* context,
                                    WlpbMuslAttrStorageV1* attribute,
                                    size_t size) {
    (void)context;
    (void)attribute;
    (void)size;
    return 0;
}

static int bridge_attr_getstack(void* context,
                                const WlpbMuslAttrStorageV1* attribute,
                                void** stack_base, size_t* stack_size) {
    (void)context;
    (void)attribute;
    (void)stack_base;
    (void)stack_size;
    return 0;
}

static int bridge_getattr_np(void* context, uint64_t thread,
                             WlpbMuslAttrStorageV1* attribute) {
    (void)context;
    (void)thread;
    (void)attribute;
    return 0;
}

static void bridge_fatal(void* context, uint32_t reason) {
    (void)context;
    (void)reason;
}

static WlpbHostOpsV1 bridge_host_ops(void) {
    WlpbHostOpsV1 ops = {
        .abi_version = WLPB_ABI_VERSION,
        .struct_size = sizeof(ops),
        .context = NULL,
        .issue_thread_ticket = bridge_issue,
        .cancel_thread_ticket = bridge_cancel,
        .prepare_current_thread = bridge_prepare,
        .verify_current_thread_ready = bridge_verify,
        .retire_current_thread = bridge_retire,
        .get_current_thread_id = bridge_thread_id,
        .real_pthread_create = bridge_pthread_create,
        .real_pthread_exit = bridge_pthread_exit,
        .real_pthread_attr_init = bridge_attr_init,
        .real_pthread_attr_destroy = bridge_attr_destroy,
        .real_pthread_attr_setdetachstate = bridge_attr_setdetachstate,
        .real_pthread_attr_setstacksize = bridge_attr_setstacksize,
        .real_pthread_attr_getstack = bridge_attr_getstack,
        .real_pthread_getattr_np = bridge_getattr_np,
        .fatal_process = bridge_fatal,
        .generation = UINT64_C(45),
    };
    return ops;
}

static int host_create_configured_namespaces(
        Dl_namespace* bridge_namespace, const char* bridge_name,
        const char* bridge_search_paths, const char* bridge_permitted_paths,
        const char* bridge_shared_sonames, const char* bridge_bootstrap_soname,
        const WlpbHostOpsV1* pthread_bridge_ops,
        void** out_bridge_bootstrap_handle, Dl_namespace* app_namespace,
        const char* app_name, const char* app_search_paths,
        const char* app_permitted_paths) {
    if (out_bridge_bootstrap_handle == NULL || app_namespace == NULL ||
        app_name == NULL || app_search_paths == NULL ||
        app_permitted_paths == NULL) {
        return -1;
    }
    *out_bridge_bootstrap_handle = NULL;
    if (bridge_namespace != NULL) {
        if (bridge_name == NULL || bridge_search_paths == NULL ||
            bridge_permitted_paths == NULL || bridge_shared_sonames == NULL) {
            return -2;
        }
        dlns_init(bridge_namespace, bridge_name);
        if (dlns_create2(bridge_namespace, bridge_search_paths,
                         CREATE_INHERIT_DEFAULT) != 0 ||
            dlns_set_namespace_separated(bridge_namespace->name, true) != 0 ||
            dlns_set_namespace_permitted_paths(
                bridge_namespace->name, bridge_permitted_paths) != 0 ||
            dlns_set_namespace_allowed_libs(
                bridge_namespace->name, bridge_shared_sonames) != 0) {
            return -3;
        }
        if (bridge_bootstrap_soname != NULL) {
            typedef int (*InstallBridgeOps)(const WlpbHostOpsV1*);
            *out_bridge_bootstrap_handle = dlopen_ns(
                bridge_namespace, bridge_bootstrap_soname,
                RTLD_NOW | RTLD_LOCAL);
            if (*out_bridge_bootstrap_handle == NULL) return -4;
            dlerror();
            union {
                void* object;
                InstallBridgeOps function;
            } install = {
                .object = dlsym(*out_bridge_bootstrap_handle,
                                "WLPB_InstallHostOps"),
            };
            const char* error = dlerror();
            if (install.function == NULL || error != NULL ||
                pthread_bridge_ops == NULL ||
                install.function(pthread_bridge_ops) != 0) {
                return -5;
            }
        }
    }

    dlns_init(app_namespace, app_name);
    if (dlns_create2(app_namespace, app_search_paths,
                     LOCAL_NS_PREFERED) != 0 ||
        dlns_set_namespace_separated(app_namespace->name, true) != 0 ||
        dlns_set_namespace_permitted_paths(
            app_namespace->name, app_permitted_paths) != 0) {
        return -6;
    }
    if (bridge_namespace != NULL &&
        dlns_inherit(app_namespace, bridge_namespace,
                     bridge_shared_sonames) != 0) {
        return -7;
    }
    return 0;
}

static void* host_open_namespace(Dl_namespace* app_namespace,
                                 const char* path, int mode) {
    return dlopen_ns(app_namespace, path, mode);
}

static AnlNamespaceHostOpsV1 namespace_host_ops(void) {
    AnlNamespaceHostOpsV1 ops = {
        .abi_version = ANL_NAMESPACE_HOST_OPS_ABI_VERSION,
        .struct_size = sizeof(ops),
        .runtime_generation = UINT64_C(45),
        .create_configured_namespaces = host_create_configured_namespaces,
        .open_namespace = host_open_namespace,
    };
    return ops;
}

#define CHECK(condition, ...)                                                   \
    do {                                                                        \
        ++g_checks;                                                             \
        if (!(condition)) {                                                     \
            ++g_failures;                                                       \
            fprintf(stderr, "FAIL %s:%d: ", __func__, __LINE__);              \
            fprintf(stderr, __VA_ARGS__);                                       \
            fputc('\n', stderr);                                                \
        }                                                                       \
    } while (0)

typedef struct Fixture {
    char base[PATH_MAX];
    char app[PATH_MAX];
    char bridge[PATH_MAX];
    char outside[PATH_MAX];
    char app_so[PATH_MAX];
    char outside_so[PATH_MAX];
    char archive[PATH_MAX];
} Fixture;

static void join_path(char* out, size_t size, const char* root, const char* leaf) {
    int count = snprintf(out, size, "%s/%s", root, leaf);
    if (count < 0 || (size_t)count >= size) {
        fprintf(stderr, "fixture path exceeds PATH_MAX\n");
        exit(2);
    }
}

static void make_dir(const char* path) {
    if (mkdir(path, 0700) != 0) {
        fprintf(stderr, "mkdir %s failed: %s\n", path, strerror(errno));
        exit(2);
    }
}

static void make_file(const char* path) {
    int fd = open(path, O_CREAT | O_EXCL | O_WRONLY, 0600);
    if (fd < 0) {
        fprintf(stderr, "open %s failed: %s\n", path, strerror(errno));
        exit(2);
    }
    close(fd);
}

static Fixture fixture_create(void) {
    Fixture fixture = {0};
    snprintf(fixture.base, sizeof(fixture.base), "/tmp/westlake-anl-host.XXXXXX");
    if (mkdtemp(fixture.base) == NULL) {
        fprintf(stderr, "mkdtemp failed: %s\n", strerror(errno));
        exit(2);
    }
    join_path(fixture.app, sizeof(fixture.app), fixture.base, "app");
    join_path(fixture.bridge, sizeof(fixture.bridge), fixture.base, "bridge");
    join_path(fixture.outside, sizeof(fixture.outside), fixture.base, "outside");
    make_dir(fixture.app);
    make_dir(fixture.bridge);
    make_dir(fixture.outside);
    join_path(fixture.app_so, sizeof(fixture.app_so), fixture.app, "libroot.so");
    join_path(fixture.outside_so, sizeof(fixture.outside_so), fixture.outside,
              "liboutside.so");
    join_path(fixture.archive, sizeof(fixture.archive), fixture.base,
              "base.apk");
    make_file(fixture.app_so);
    make_file(fixture.outside_so);
    make_file(fixture.archive);
    return fixture;
}

static void fixture_destroy(const Fixture* fixture) {
    unlink(fixture->app_so);
    unlink(fixture->outside_so);
    unlink(fixture->archive);
    rmdir(fixture->app);
    rmdir(fixture->bridge);
    rmdir(fixture->outside);
    rmdir(fixture->base);
}

static AnlDomainConfig base_config(const Fixture* fixture) {
    AnlDomainConfig config = {
        .app_search_paths = fixture->app,
        .app_permitted_paths = fixture->app,
    };
    return config;
}

static void install_runtime_gate(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    CHECK(ANL_CreateDomain(&config, &domain) != 0,
          "domain created before runtime gate installation");
    CHECK(domain == NULL, "pre-gate create returned a domain");
    CHECK(ANL_InstallRuntimeGate(NULL) != 0, "null runtime gate accepted");
    AnlRuntimeGateV1 gate = {
        .abi_version = ANL_RUNTIME_GATE_ABI_VERSION,
        .struct_size = sizeof(gate),
        .context = NULL,
        .verify_current_thread_ready = runtime_gate,
        .pthread_bridge_ops = bridge_host_ops(),
        .namespace_host_ops = namespace_host_ops(),
    };
    CHECK(ANL_InstallRuntimeGate(&gate) == 0,
          "valid runtime gate rejected: %s", ANL_Dlerror());
    CHECK(ANL_InstallRuntimeGate(&gate) != 0,
          "second runtime gate installation accepted");
}

static void expect_create_rejected(AnlDomainConfig* config, const char* label) {
    AnlDomain* domain = NULL;
    MockDlnsReset();
    int rc = ANL_CreateDomain(config, &domain);
    CHECK(rc != 0, "%s unexpectedly accepted", label);
    CHECK(domain == NULL, "%s returned a domain on rejection", label);
    if (domain != NULL) ANL_ReleaseDomainHandle(domain);
}

static void test_valid_app_domain(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "valid app domain rejected: %s",
          ANL_Dlerror());
    CHECK(domain != NULL, "valid app domain returned null");
    CHECK(MockDlnsGet()->create_calls == 1, "expected one namespace create");
    CHECK(MockDlnsGet()->last_create_flags == LOCAL_NS_PREFERED,
          "app namespace flags=%d", MockDlnsGet()->last_create_flags);
    ANL_ReleaseDomainHandle(domain);
}

static void test_create_domain_runtime_gate(const Fixture* fixture) {
    setenv("ANL_GATE_STRICT", "1", 1);
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    g_gate_mode = GATE_DENY;
    CHECK(ANL_CreateDomain(&config, &domain) != 0,
          "create-domain gate return 0 accepted");
    CHECK(domain == NULL, "denied create-domain returned a domain");
    g_gate_mode = GATE_RETURN_TWO;
    CHECK(ANL_CreateDomain(&config, &domain) != 0,
          "create-domain gate return 2 accepted");
    CHECK(MockDlnsGet()->create_calls == 0,
          "denied create-domain reached namespace creation");
    g_gate_mode = GATE_ALLOW;
    unsetenv("ANL_GATE_STRICT");
}

static void test_path_list_empty_segments(const Fixture* fixture) {
    char leading[sizeof(fixture->app) + 1];
    char trailing[sizeof(fixture->app) + 1];
    char doubled[sizeof(fixture->app) + sizeof(fixture->bridge) + 1];
    snprintf(leading, sizeof(leading), ":%s", fixture->app);
    snprintf(trailing, sizeof(trailing), "%s:", fixture->app);
    snprintf(doubled, sizeof(doubled), "%s::%s", fixture->app, fixture->bridge);

    AnlDomainConfig config = base_config(fixture);
    config.app_search_paths = leading;
    expect_create_rejected(&config, "leading empty app path segment");
    config.app_search_paths = trailing;
    expect_create_rejected(&config, "trailing empty app path segment");
    config.app_search_paths = doubled;
    expect_create_rejected(&config, "interior empty app path segment");
}

static void test_forbidden_paths(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    config.app_search_paths = "relative/path";
    expect_create_rejected(&config, "relative app path");
    config.app_search_paths = "/tmp/../tmp";
    expect_create_rejected(&config, "parent traversal app path");
    config.app_search_paths = "/data/local/tmp";
    expect_create_rejected(&config, "local tmp app path");
    config.app_search_paths = "/data/local/tmp/unity";
    expect_create_rejected(&config, "local tmp child app path");
}

static void test_archive_search_paths(const Fixture* fixture) {
    char valid[PATH_MAX * 2];
    char missing[PATH_MAX * 2];
    char directory_archive[PATH_MAX * 2];
    char multiple[PATH_MAX * 2];
    char empty_entry[PATH_MAX * 2];
    char traversal[PATH_MAX * 2];
    snprintf(valid, sizeof(valid), "%s!/lib/arm64-v8a", fixture->archive);
    snprintf(missing, sizeof(missing), "%s/missing.apk!/lib/arm64-v8a",
             fixture->base);
    snprintf(directory_archive, sizeof(directory_archive),
             "%s!/lib/arm64-v8a", fixture->app);
    snprintf(multiple, sizeof(multiple), "%s!/lib!/arm64-v8a",
             fixture->archive);
    snprintf(empty_entry, sizeof(empty_entry), "%s!/", fixture->archive);
    snprintf(traversal, sizeof(traversal), "%s!/lib/../arm64-v8a",
             fixture->archive);

    AnlDomainConfig config = base_config(fixture);
    config.app_search_paths = valid;
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0,
          "valid APK archive search path rejected: %s", ANL_Dlerror());
    CHECK(domain != NULL && MockDlnsGet()->create_calls == 1,
          "valid archive path did not reach one namespace create");
    ANL_ReleaseDomainHandle(domain);

    config = base_config(fixture);
    config.app_search_paths = missing;
    expect_create_rejected(&config, "missing APK archive");
    config.app_search_paths = directory_archive;
    expect_create_rejected(&config, "directory used as APK archive");
    config.app_search_paths = multiple;
    expect_create_rejected(&config, "multiple APK archive delimiters");
    config.app_search_paths = empty_entry;
    expect_create_rejected(&config, "empty APK archive entry");
    config.app_search_paths = traversal;
    expect_create_rejected(&config, "APK archive entry traversal");

    config = base_config(fixture);
    config.app_permitted_paths = valid;
    expect_create_rejected(&config, "archive path in app permitted roots");
    config = base_config(fixture);
    config.bridge_search_paths = valid;
    config.bridge_permitted_paths = fixture->bridge;
    config.bridge_shared_sonames = "libbridge.so";
    expect_create_rejected(&config, "archive path in bridge search roots");
}

static void test_bridge_all_or_none(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    config.bridge_permitted_paths = fixture->bridge;
    expect_create_rejected(&config, "bridge permitted path without search path");

    config = base_config(fixture);
    config.bridge_shared_sonames = "libbridge.so";
    expect_create_rejected(&config, "bridge SONAME without bridge paths");

    config = base_config(fixture);
    config.bridge_search_paths = fixture->bridge;
    expect_create_rejected(&config, "bridge search path without policy fields");

    config = base_config(fixture);
    config.bridge_search_paths = fixture->bridge;
    config.bridge_permitted_paths = fixture->bridge;
    config.bridge_shared_sonames = "libbridge.so";
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "complete bridge rejected: %s",
          ANL_Dlerror());
    CHECK(MockDlnsGet()->create_calls == 2, "complete bridge did not create two namespaces");
    CHECK(MockDlnsGet()->create_flags[0] == CREATE_INHERIT_DEFAULT,
          "bridge namespace flags=%d", MockDlnsGet()->create_flags[0]);
    CHECK(MockDlnsGet()->create_flags[1] == LOCAL_NS_PREFERED,
          "app namespace flags=%d", MockDlnsGet()->create_flags[1]);
    CHECK(MockDlnsGet()->inherit_calls == 1, "complete bridge did not inherit exactly once");
    CHECK(MockDlnsGet()->allowed_calls == 1, "complete bridge did not set allowed libs");
    CHECK(strcmp(MockDlnsGet()->last_inherited_libs, "libbridge.so") == 0,
          "unexpected inherited libs: %s", MockDlnsGet()->last_inherited_libs);
    CHECK(strcmp(MockDlnsGet()->last_allowed_libs, "libbridge.so") == 0,
          "unexpected bridge allowlist: %s", MockDlnsGet()->last_allowed_libs);
    ANL_ReleaseDomainHandle(domain);
}

static void test_log_dependency_inheritance(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    config.bridge_search_paths = fixture->bridge;
    config.bridge_permitted_paths = fixture->bridge;
    config.bridge_shared_sonames = "liblog.so";
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "log namespace rejected");
    CHECK(strstr(MockDlnsGet()->last_inherited_libs, ":libc++.so:") != NULL,
          "log's C++ dependency not shared");
    CHECK(strstr(MockDlnsGet()->last_inherited_libs, ":libwm.z.so:") != NULL,
          "bridge window-manager dependency not shared");
    CHECK(strlen(MockDlnsGet()->last_inherited_libs) < 4096,
          "direct OH boundary unexpectedly expanded to full transitive graph");
    CHECK(strstr(MockDlnsGet()->last_inherited_libs, ":libzuri.z.so") != NULL,
          "tail of complete OH dependency list was truncated");
    int before = MockDlnsGet()->dlopen_calls;
    CHECK(ANL_Dlopen(domain, fixture->outside_so, RTLD_NOW) == NULL,
          "runtime dependency sharing broadened direct app file access");
    CHECK(MockDlnsGet()->dlopen_calls == before, "foreign path reached loader");
    ANL_ReleaseDomainHandle(domain);
}

static void test_bridge_bootstrap(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    config.bridge_search_paths = fixture->bridge;
    config.bridge_permitted_paths = fixture->bridge;
    config.bridge_shared_sonames =
        "libwestlake_bionic_pthread_bridge.so";
    config.bridge_bootstrap_soname =
        "libwestlake_bionic_pthread_bridge.so";
    AnlDomain* domain = NULL;

    MockDlnsReset();
    MockDlnsSetBridgeSymbolAvailable(false);
    CHECK(ANL_CreateDomain(&config, &domain) != 0,
          "bridge missing-symbol fixture accepted");
    CHECK(domain == NULL, "bridge missing-symbol fixture returned domain");
    CHECK(MockDlnsGet()->create_calls == 1,
          "missing bridge symbol reached app namespace creation");
    CHECK(MockDlnsGet()->dlsym_calls == 1 &&
          MockDlnsGet()->bridge_install_calls == 0,
          "missing bridge symbol did not fail at exact bootstrap boundary");

    MockDlnsReset();
    MockDlnsSetBridgeInstallResult(EINVAL);
    CHECK(ANL_CreateDomain(&config, &domain) != 0,
          "bridge rejected-install fixture accepted");
    CHECK(domain == NULL, "bridge rejected-install fixture returned domain");
    CHECK(MockDlnsGet()->create_calls == 1,
          "rejected bridge install reached app namespace creation");
    CHECK(MockDlnsGet()->bridge_install_calls == 1 &&
          MockDlnsGet()->bridge_install_create_calls == 1,
          "bridge install did not run after bridge namespace and before app");

    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0,
          "bridge bootstrap rejected: %s", ANL_Dlerror());
    CHECK(domain != NULL, "bridge bootstrap returned null domain");
    CHECK(MockDlnsGet()->create_calls == 2 &&
          MockDlnsGet()->bridge_install_create_calls == 1,
          "bridge install/app namespace order drifted");
    CHECK(MockDlnsGet()->dlopen_calls == 1 &&
          strcmp(MockDlnsGet()->last_dlopen_file,
                 "libwestlake_bionic_pthread_bridge.so") == 0 &&
          MockDlnsGet()->last_dlopen_mode == (RTLD_NOW | RTLD_LOCAL),
          "bridge bootstrap dlopen_ns contract drifted");
    CHECK(MockDlnsGet()->dlsym_calls == 1 &&
          strcmp(MockDlnsGet()->last_dlsym_symbol,
                 "WLPB_InstallHostOps") == 0 &&
          MockDlnsGet()->bridge_install_calls == 1,
          "bridge bootstrap dlsym/install contract drifted");
    CHECK(MockDlnsGet()->inherit_calls == 1,
          "bootstrapped bridge was not inherited by app namespace");
    ANL_ReleaseDomainHandle(domain);
}

static void test_rtld_global_rejected(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "fixture domain create failed");
    int calls_before = MockDlnsGet()->dlopen_calls;
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW | RTLD_GLOBAL) == NULL,
          "RTLD_GLOBAL load unexpectedly accepted");
    CHECK(MockDlnsGet()->dlopen_calls == calls_before,
          "RTLD_GLOBAL reached dlopen_ns");
    ANL_ReleaseDomainHandle(domain);
}

static void test_app_domain_boundary(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "fixture domain create failed");

    CHECK(ANL_Dlopen(domain, fixture->app_so, RTLD_NOW) != NULL,
          "in-domain absolute path rejected: %s", ANL_Dlerror());
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) != NULL,
          "SONAME load rejected: %s", ANL_Dlerror());

    int calls_before = MockDlnsGet()->dlopen_calls;
    CHECK(ANL_Dlopen(domain, fixture->outside_so, RTLD_NOW) == NULL,
          "outside absolute path accepted");
    CHECK(ANL_Dlopen(domain, "relative/libroot.so", RTLD_NOW) == NULL,
          "relative path with slash accepted");
    CHECK(MockDlnsGet()->dlopen_calls == calls_before,
          "outside-domain path reached dlopen_ns");
    ANL_ReleaseDomainHandle(domain);
}

static void* second_thread_open(void* opaque) {
    AnlDomain* domain = (AnlDomain*)opaque;
    return ANL_Dlopen(domain, "libroot.so", RTLD_NOW);
}

static void* second_thread_close(void* opaque) {
    return (void*)(intptr_t)(ANL_Dlclose(opaque) == 0 ? 1 : 0);
}

static void test_dlclose_runtime_gate(const Fixture* fixture) {
    setenv("ANL_GATE_STRICT", "1", 1);
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    g_gate_mode = GATE_ALLOW;
    CHECK(ANL_CreateDomain(&config, &domain) == 0,
          "close-gate fixture domain create failed");
    void* handle = ANL_Dlopen(domain, "libroot.so", RTLD_NOW);
    CHECK(handle != NULL, "close-gate fixture load failed: %s", ANL_Dlerror());
    int before = MockDlnsGet()->dlclose_calls;

    g_gate_mode = GATE_DENY;
    CHECK(ANL_Dlclose(handle) != 0, "close gate return 0 accepted");
    g_gate_mode = GATE_RETURN_TWO;
    CHECK(ANL_Dlclose(handle) != 0, "close gate return 2 accepted as success");
    CHECK(MockDlnsGet()->dlclose_calls == before,
          "denied close reached real dlclose");

    g_reentry_close_handle = handle;
    g_gate_mode = GATE_REENTER_CLOSE;
    CHECK(ANL_Dlclose(handle) != 0, "reentrant close outer operation accepted");
    CHECK(MockDlnsGet()->dlclose_calls == before,
          "reentrant close reached real dlclose");

    g_gate_owner = pthread_self();
    g_gate_mode = GATE_OWNER_THREAD_ONLY;
    pthread_t worker;
    CHECK(pthread_create(&worker, NULL, second_thread_close, handle) == 0,
          "second-thread close fixture creation failed");
    void* worker_result = (void*)1;
    CHECK(pthread_join(worker, &worker_result) == 0,
          "second-thread close fixture join failed");
    CHECK(worker_result == NULL, "unadmitted second-thread close succeeded");
    CHECK(MockDlnsGet()->dlclose_calls == before,
          "unadmitted second thread reached real dlclose");

    g_gate_mode = GATE_ALLOW;
    CHECK(ANL_Dlclose(handle) == 0, "admitted close rejected: %s", ANL_Dlerror());
    CHECK(MockDlnsGet()->dlclose_calls == before + 1,
          "admitted close did not reach real dlclose exactly once");
    CHECK(MockDlnsGet()->last_dlclose_handle == handle,
          "admitted close changed the handle");
    ANL_ReleaseDomainHandle(domain);
    unsetenv("ANL_GATE_STRICT");
}

static void test_runtime_gate_fail_closed(const Fixture* fixture) {
    setenv("ANL_GATE_STRICT", "1", 1);
    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0,
          "gate fixture domain create failed");

    int before = MockDlnsGet()->dlopen_calls;
    g_gate_mode = GATE_DENY;
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) == NULL,
          "gate return 0 accepted");
    g_gate_mode = GATE_RETURN_TWO;
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) == NULL,
          "gate return 2 accepted as success");
    CHECK(MockDlnsGet()->dlopen_calls == before,
          "failed gate reached dlopen_ns");

    g_reentry_domain = domain;
    g_gate_mode = GATE_REENTER;
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) == NULL,
          "reentrant gate outer load accepted");
    CHECK(MockDlnsGet()->dlopen_calls == before,
          "reentrant gate reached dlopen_ns");

    g_gate_owner = pthread_self();
    g_gate_mode = GATE_OWNER_THREAD_ONLY;
    pthread_t worker;
    CHECK(pthread_create(&worker, NULL, second_thread_open, domain) == 0,
          "second-thread fixture creation failed");
    void* worker_result = (void*)1;
    CHECK(pthread_join(worker, &worker_result) == 0,
          "second-thread fixture join failed");
    CHECK(worker_result == NULL, "unadmitted second-thread load succeeded");
    CHECK(MockDlnsGet()->dlopen_calls == before,
          "unadmitted second thread reached dlopen_ns");

    g_gate_mode = GATE_ALLOW;
    ANL_ReleaseDomainHandle(domain);
    unsetenv("ANL_GATE_STRICT");
}

static void test_load_error_classification(const Fixture* fixture) {
    typedef struct {
        const char* raw;
        const char* code;
        const char* identity;
    } ClassificationCase;
    static const ClassificationCase cases[] = {
        {"dlopen failed: library \"libdep.so\" not found",
         ANL_LOAD_ERROR_MISSING_DEPENDENCY, "libdep.so"},
        {"dlopen failed: \"libwrong.so\" has unexpected e_machine: 40 "
         "(EM_ARM) instead of EM_AARCH64",
         ANL_LOAD_ERROR_ABI_MISMATCH, "e_machine"},
        {"dlopen failed: cannot locate symbol \"missing_entry\" referenced by "
         "\"libroot.so\"...",
         ANL_LOAD_ERROR_UNSUPPORTED_SYMBOL, "missing_entry"},
        {"dlopen failed: TLS generation overflow in dynamic linker",
         ANL_LOAD_ERROR_UNCLASSIFIED, "TLS generation overflow"},
    };

    AnlDomainConfig config = base_config(fixture);
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0,
          "classification fixture domain create failed");

    MockDlnsSetDlopenFailure(NULL);
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) != NULL,
          "classification success-path load rejected: %s", ANL_Dlerror());
    CHECK(ANL_Dlerror() == NULL,
          "successful load left a stale diagnostic behind");

    for (size_t i = 0; i < sizeof(cases) / sizeof(cases[0]); ++i) {
        MockDlnsSetDlopenFailure(cases[i].raw);
        CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) == NULL,
              "case %zu: injected linker failure returned a handle", i);
        const char* error = ANL_Dlerror();
        CHECK(error != NULL && error[0] != '\0',
              "case %zu: load failure produced an empty diagnostic", i);
        if (error == NULL) continue;
        CHECK(strstr(error, cases[i].code) != NULL,
              "case %zu: expected %s, got: %s", i, cases[i].code, error);
        CHECK(strstr(error, cases[i].identity) != NULL,
              "case %zu: diagnostic lost the failing identity (%s): %s", i,
              cases[i].identity, error);
        CHECK(strstr(error, cases[i].raw) != NULL,
              "case %zu: raw linker text was dropped: %s", i, error);
    }

    MockDlnsSetDlopenFailure(NULL);
    CHECK(ANL_Dlopen(domain, "libroot.so", RTLD_NOW) != NULL,
          "load after classified failures rejected: %s", ANL_Dlerror());
    CHECK(ANL_Dlerror() == NULL,
          "recovery load did not clear the previous classified diagnostic");
    ANL_ReleaseDomainHandle(domain);
}


/* The Flutter ReLinker fallback is inside libraryPermittedPath, not search. */
static void test_app_permitted_boundary(const Fixture* fixture) {
    AnlDomainConfig config = base_config(fixture);
    config.app_permitted_paths = fixture->outside;
    AnlDomain* domain = NULL;
    MockDlnsReset();
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "permitted fixture create failed");
    CHECK(ANL_Dlopen(domain, fixture->outside_so, RTLD_NOW) != NULL,
          "permitted absolute Flutter path rejected: %s", ANL_Dlerror());
    CHECK(ANL_Dlopen(domain, fixture->app_so, RTLD_NOW) != NULL,
          "search root lost when permitted root differs");
    char escape[PATH_MAX];
    join_path(escape, sizeof(escape), fixture->outside, "escape.so");
    char foreign[PATH_MAX];
    join_path(foreign, sizeof(foreign), fixture->bridge, "foreign.so");
    make_file(foreign);
    CHECK(symlink(foreign, escape) == 0, "create test symlink");
    int calls_before = MockDlnsGet()->dlopen_calls;
    CHECK(ANL_Dlopen(domain, escape, RTLD_NOW) == NULL,
          "permitted symlink escaped into foreign directory");
    CHECK(ANL_Dlopen(domain, foreign, RTLD_NOW) == NULL,
          "foreign absolute path accepted");
    CHECK(MockDlnsGet()->dlopen_calls == calls_before,
          "foreign path reached loader backend");
    unlink(escape); unlink(foreign);
    ANL_ReleaseDomainHandle(domain);
}

static void test_runtime_gate_default_allows_guest(const Fixture* fixture) {
    AnlDomain* domain = NULL;
    AnlDomainConfig config = base_config(fixture);
    unsetenv("ANL_GATE_STRICT");
    MockDlnsReset();
    g_gate_mode = GATE_ALLOW;
    CHECK(ANL_CreateDomain(&config, &domain) == 0, "default create-domain failed");
    g_gate_mode = GATE_DENY;
    void* handle = ANL_Dlopen(domain, "libguest.so", RTLD_NOW);
    CHECK(handle != NULL, "default mode denied a not-READY guest dlopen");
    g_gate_mode = GATE_ALLOW;
    ANL_ReleaseDomainHandle(domain);
}

int main(void) {
    Fixture fixture = fixture_create();
    install_runtime_gate(&fixture);
    test_create_domain_runtime_gate(&fixture);
    test_valid_app_domain(&fixture);
    test_path_list_empty_segments(&fixture);
    test_forbidden_paths(&fixture);
    test_archive_search_paths(&fixture);
    test_bridge_all_or_none(&fixture);
    test_log_dependency_inheritance(&fixture);
    test_bridge_bootstrap(&fixture);
    test_rtld_global_rejected(&fixture);
    test_app_domain_boundary(&fixture);
    test_app_permitted_boundary(&fixture);
    test_runtime_gate_fail_closed(&fixture);
    test_runtime_gate_default_allows_guest(&fixture);
    test_dlclose_runtime_gate(&fixture);
    test_load_error_classification(&fixture);
    fixture_destroy(&fixture);

    printf("ANL host contract: %d checks, %d failures\n", g_checks, g_failures);
    return g_failures == 0 ? 0 : 1;
}
