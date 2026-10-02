#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>
#include <errno.h>

#define WLASC_NOINLINE
#define APPSPAWN_LOGI(format, ...) record_log(format)
#define APPSPAWN_LOGE(format, ...) record_log(format)
#define CREATE_INHERIT_DEFAULT 1
#define LOCAL_NS_PREFERED 4
typedef struct { int unused; } WlpbHostOpsV1;
static int sequence, bootstrap_sequence, first_compat_query, last_sealed_inherit;
static int compat_queries, verified, unavailable, app_compat_edges;
static bool compat_mapped, map_in_bootstrap, default_visible;

static void record_log(const char *format)
{
    ++sequence;
    if (strstr(format, "[U10-COMPAT-VISIBLE] owner_verified")) ++verified;
    if (strstr(format, "[U10-COMPAT-VISIBLE] unavailable")) ++unavailable;
    printf("EVENT %d LOG %s\n", sequence, format);
}
int dlns_get(const char *name, Dl_namespace *output) {
    ++sequence;
    if (strcmp(name, "default") == 0 && !default_visible) return ENOENT;
    strcpy(output->name, name);
    return 0;
}
int dlns_init(Dl_namespace *domain, const char *name) { strcpy(domain->name, name); ++sequence; return 0; }
int dlns_create2(Dl_namespace *domain, const char *paths, int flags) { ++sequence; return 0; }
int dlns_set_namespace_separated(const char *name, bool separated) { ++sequence; return 0; }
int dlns_set_namespace_permitted_paths(const char *name, const char *paths) { ++sequence; return 0; }
int dlns_set_namespace_allowed_libs(const char *name, const char *libs) { ++sequence; return 0; }
int dlns_inherit(Dl_namespace *domain, Dl_namespace *parent, const char *shared)
{
    ++sequence;
    printf("EVENT %d INHERIT %s -> %s %s\n", sequence, domain->name, parent->name, shared);
    if (strstr(domain->name, ".app.") && strstr(shared, "libbionic_compat.so")) ++app_compat_edges;
    if (strcmp(parent->name, "westlake.sealed.child") == 0) last_sealed_inherit = sequence;
    return 0;
}
void *dlopen_ns(Dl_namespace *domain, const char *path, int flags)
{
    ++sequence;
    printf("EVENT %d OPEN %s %s flags=%d\n", sequence, domain->name, path, flags);
    if (strcmp(path, "libbionic_compat.so") == 0) {
        ++compat_queries;
        if (!first_compat_query) first_compat_query = sequence;
        if (!compat_mapped) return NULL;
        return (void *)(uintptr_t)(strcmp(domain->name, "default") == 0 ? 20 : 10);
    }
    if (strcmp(path, "libpthread_bridge.so") == 0) {
        bootstrap_sequence = sequence;
        if (map_in_bootstrap) compat_mapped = true;
    }
    return (void *)(uintptr_t)30;
}
static int install(const WlpbHostOpsV1 *ops) { return 0; }
void *dlsym(void *handle, const char *name)
{
    if (strcmp(name, "WLPB_InstallHostOps") == 0) {
        int (*method)(const WlpbHostOpsV1 *) = install;
        void *symbol;
        memcpy(&symbol, &method, sizeof(symbol));
        return symbol;
    }
    return (void *)(uintptr_t)(strcmp(name, "android_set_abort_message") == 0 ? 100 : strcmp(name, "android_get_abort_message") == 0 ? 200 : 300);
}
int dlclose(void *handle) { return 0; }
char *dlerror(void) { return NULL; }

#include "resident-compat.h"
#include "n11h-owner.h"
#include "callback-body.h"

int main(int argc, char **argv)
{
    if (argc != 2) return 2;
    compat_mapped = strcmp(argv[1], "early") == 0 || strcmp(argv[1], "private") == 0;
    map_in_bootstrap = strcmp(argv[1], "late") == 0;
    default_visible = !map_in_bootstrap;
    const char *path = strcmp(argv[1], "private") == 0
        ? "/system/android/lib64/westlake_native:/data/app/app.organicmaps/lib" : "/data/app/plain.app/lib";
    char app[256], bridge[256];
    snprintf(app, sizeof(app), "westlake.anl.app.%ld.1", (long)getpid());
    snprintf(bridge, sizeof(bridge), "westlake.anl.bridge.%ld.1", (long)getpid());
    Dl_namespace app_namespace, bridge_namespace;
    WlpbHostOpsV1 ops = {0};
    void *handle;
    int result = StockCreateConfiguredNamespaces(&bridge_namespace, bridge, "/system/android/lib64",
        "/system/android/lib64", "libandroid.so:libEGL.so", "libpthread_bridge.so", &ops,
        &handle, &app_namespace, app, path, path);
    printf("RESULT {\"callback_rc\":%d,\"bootstrap_sequence\":%d,\"first_compat_query\":%d,\"compat_queries\":%d,\"verified\":%d,\"unavailable\":%d,\"app_compat_edges\":%d,\"last_sealed_inherit\":%d}\n",
        result, bootstrap_sequence, first_compat_query, compat_queries, verified, unavailable, app_compat_edges, last_sealed_inherit);
    return result;
}
