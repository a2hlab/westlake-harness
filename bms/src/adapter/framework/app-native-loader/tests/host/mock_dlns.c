#include "mock_dlns.h"
#include "westlake_bionic_pthread_bridge.h"

#include <stdio.h>
#include <string.h>

static MockDlnsState g_state;
static char g_handle;
static bool g_bridge_symbol_available;
static int g_bridge_install_result;
static const char* g_dlerror;
static const char* g_dlopen_failure;

static int MockBridgeInstall(const WlpbHostOpsV1* ops) {
    (void)ops;
    ++g_state.bridge_install_calls;
    g_state.bridge_install_create_calls = g_state.create_calls;
    return g_bridge_install_result;
}

void MockDlnsReset(void) {
    memset(&g_state, 0, sizeof(g_state));
    g_bridge_symbol_available = true;
    g_bridge_install_result = 0;
    g_dlerror = NULL;
    g_dlopen_failure = NULL;
}

const MockDlnsState* MockDlnsGet(void) {
    return &g_state;
}

void MockDlnsSetBridgeSymbolAvailable(bool available) {
    g_bridge_symbol_available = available;
}

void MockDlnsSetBridgeInstallResult(int result) {
    g_bridge_install_result = result;
}

void MockDlnsSetDlopenFailure(const char* error_text) {
    g_dlopen_failure = error_text;
}

void dlns_init(Dl_namespace* ns, const char* name) {
    ++g_state.init_calls;
    snprintf(ns->name, sizeof(ns->name), "%s", name);
}

int dlns_get(const char* name, Dl_namespace* ns) {
    (void)name;
    (void)ns;
    return -1;
}

int dlns_create2(Dl_namespace* ns, const char* lib_path, int flags) {
    (void)ns;
    (void)lib_path;
    if (g_state.create_calls < (int)(sizeof(g_state.create_flags) /
                                     sizeof(g_state.create_flags[0]))) {
        g_state.create_flags[g_state.create_calls] = flags;
    }
    ++g_state.create_calls;
    g_state.last_create_flags = flags;
    return 0;
}

int dlns_inherit(Dl_namespace* ns, Dl_namespace* inherited, const char* shared_libs) {
    (void)ns;
    (void)inherited;
    ++g_state.inherit_calls;
    snprintf(g_state.last_inherited_libs, sizeof(g_state.last_inherited_libs), "%s",
             shared_libs == NULL ? "" : shared_libs);
    return 0;
}

int dlns_set_namespace_separated(const char* name, bool separated) {
    (void)name;
    (void)separated;
    ++g_state.separated_calls;
    return 0;
}

int dlns_set_namespace_permitted_paths(const char* name, const char* permitted_paths) {
    (void)name;
    (void)permitted_paths;
    ++g_state.permitted_calls;
    return 0;
}

int dlns_set_namespace_allowed_libs(const char* name, const char* allowed_libs) {
    (void)name;
    ++g_state.allowed_calls;
    snprintf(g_state.last_allowed_libs, sizeof(g_state.last_allowed_libs), "%s",
             allowed_libs == NULL ? "" : allowed_libs);
    return 0;
}

void* dlopen_ns(Dl_namespace* ns, const char* file, int mode) {
    (void)ns;
    ++g_state.dlopen_calls;
    g_state.last_dlopen_mode = mode;
    snprintf(g_state.last_dlopen_file, sizeof(g_state.last_dlopen_file), "%s", file);
    if (g_dlopen_failure != NULL) {
        g_dlerror = g_dlopen_failure;
        return NULL;
    }
    return &g_handle;
}

void* dlsym(void* handle, const char* symbol) {
    (void)handle;
    ++g_state.dlsym_calls;
    snprintf(g_state.last_dlsym_symbol, sizeof(g_state.last_dlsym_symbol),
             "%s", symbol == NULL ? "" : symbol);
    if (symbol != NULL && strcmp(symbol, "WLPB_InstallHostOps") == 0) {
        if (!g_bridge_symbol_available) {
            g_dlerror = "mock bridge symbol unavailable";
            return NULL;
        }
        union {
            int (*function)(const WlpbHostOpsV1*);
            void* object;
        } conversion = {.function = MockBridgeInstall};
        g_dlerror = NULL;
        return conversion.object;
    }
    g_dlerror = NULL;
    return &g_handle;
}

char* dlerror(void) {
    const char* error = g_dlerror;
    g_dlerror = NULL;
    return (char*)error;
}

int dlclose(void* handle) {
    ++g_state.dlclose_calls;
    g_state.last_dlclose_handle = handle;
    return 0;
}
