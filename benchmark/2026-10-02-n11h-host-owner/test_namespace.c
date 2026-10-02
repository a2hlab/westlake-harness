#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

#define WLASC_NOINLINE
#define APPSPAWN_LOGI(...) (++logs)
#define APPSPAWN_LOGE(...) (++logs)
#define CREATE_INHERIT_DEFAULT 1
#define LOCAL_NS_PREFERED 4
typedef struct { int unused; } WlpbHostOpsV1;

typedef struct { char child[256]; char parent[256]; char shared[512]; } Edge;
static Edge edges[8];
static int edge_count, fresh_count, probe_count, close_count, logs, installs;
static int failure, compat_choice;
static bool enforce_edges;
static char app_name[256], bridge_name[256], last_domain[256], last_path[512];
static int last_flags;

static Edge *edge(const char *child, const char *parent)
{
    for (int index = 0; index < edge_count; ++index) {
        if (strcmp(edges[index].child, child) == 0 && strcmp(edges[index].parent, parent) == 0) return &edges[index];
    }
    return NULL;
}

int dlns_get(const char *name, Dl_namespace *output)
{
    if (failure == 1 && strcmp(name, "westlake.sealed.child") == 0) return 2;
    strcpy(output->name, name);
    return 0;
}
int dlns_init(Dl_namespace *domain, const char *name) { strcpy(domain->name, name); return 0; }
int dlns_create2(Dl_namespace *domain, const char *paths, int flags) { return failure == 6 ? 13 : 0; }
int dlns_set_namespace_separated(const char *name, bool separated) { return 0; }
int dlns_set_namespace_permitted_paths(const char *name, const char *paths) { return 0; }
int dlns_set_namespace_allowed_libs(const char *name, const char *libs) { return 0; }
int dlns_inherit(Dl_namespace *domain, Dl_namespace *parent, const char *shared)
{
    assert(fresh_count == 0);
    assert(edge(domain->name, parent->name) == NULL);
    if (failure == 7 && strcmp(shared, "libbionic_compat.so") == 0) return 13;
    if (failure == 8 && strcmp(parent->name, "westlake.sealed.child") == 0) return 13;
    assert(edge_count < 8);
    Edge *entry = &edges[edge_count++];
    strcpy(entry->child, domain->name);
    strcpy(entry->parent, parent->name);
    strcpy(entry->shared, shared);
    return 0;
}
void *dlopen_ns(Dl_namespace *domain, const char *path, int flags)
{
    strcpy(last_domain, domain->name);
    strcpy(last_path, path);
    last_flags = flags;
    if (flags & RTLD_NOLOAD) {
        ++probe_count;
        assert(strcmp(domain->name, "westlake.sealed.child") == 0 || strcmp(domain->name, "default") == 0);
        if (strcmp(path, "libbionic_compat.so") == 0) {
            if (compat_choice == 2 || (compat_choice == 1 && strcmp(domain->name, "default") == 0)) return NULL;
            return (void *)(uintptr_t)(strcmp(domain->name, "default") == 0 ? 20 : 10);
        }
        assert(strcmp(domain->name, "westlake.sealed.child") == 0);
        if (strcmp(path, "/system/android/lib64/liboh_adapter_bridge.so") == 0) return failure == 2 ? NULL : (void *)(uintptr_t)40;
        assert(strcmp(path, "/system/android/lib64/liboh_android_runtime.so") == 0);
        return failure == 3 ? NULL : (void *)(uintptr_t)50;
    }
    ++fresh_count;
    if (enforce_edges) {
        Edge *application = edge(app_name, "westlake.sealed.child");
        assert(application && strstr(application->shared, "liboh_adapter_bridge.so") && strstr(application->shared, "liboh_android_runtime.so"));
        Edge *bridge = edge(bridge_name, "westlake.sealed.child");
        assert(bridge && strcmp(bridge->shared, "liboh_adapter_bridge.so:liboh_android_runtime.so") == 0);
    }
    return failure == 9 ? NULL : (void *)(uintptr_t)30;
}
static int install(const WlpbHostOpsV1 *ops) { assert(ops); ++installs; return failure == 10 ? 13 : 0; }
void *dlsym(void *handle, const char *name)
{
    if (strcmp(name, "WLPB_InstallHostOps") == 0) {
        if (failure == 4) return NULL;
        int (*method)(const WlpbHostOpsV1 *) = install;
        void *result;
        memcpy(&result, &method, sizeof(result));
        return result;
    }
    uintptr_t value = strcmp(name, "android_set_abort_message") == 0 ? 100 : strcmp(name, "android_get_abort_message") == 0 ? 200 : 300;
    if (compat_choice == 3 && handle == (void *)(uintptr_t)20) ++value;
    return (void *)value;
}
int dlclose(void *handle) { assert(handle); ++close_count; return 0; }
char *dlerror(void) { return NULL; }

#include "resident-compat.h"
#include "n11h-owner.h"
#include "namespace-body.h"

static void reset(void)
{
    edge_count = fresh_count = probe_count = close_count = logs = installs = 0;
    failure = compat_choice = 0;
    enforce_edges = false;
    snprintf(app_name, sizeof(app_name), "westlake.anl.app.%ld.1", (long)getpid());
    snprintf(bridge_name, sizeof(bridge_name), "westlake.anl.bridge.%ld.1", (long)getpid());
}
static int create(const char *path, bool wants_bridge)
{
    Dl_namespace bridge, application;
    WlpbHostOpsV1 ops = {0};
    void *bootstrap = NULL;
    enforce_edges = wants_bridge;
    int result = StockCreateConfiguredNamespaces(wants_bridge ? &bridge : NULL,
        wants_bridge ? bridge_name : NULL, wants_bridge ? "/system/android/lib64" : NULL,
        wants_bridge ? "/system/android/lib64" : NULL, wants_bridge ? "libandroid.so:libEGL.so" : NULL,
        wants_bridge ? "libpthread_bridge.so" : NULL, wants_bridge ? &ops : NULL,
        &bootstrap, &application, app_name, path, path);
    if (result == 0 && wants_bridge) assert(bootstrap && installs == 1);
    return result;
}

static void namespaces(void)
{
    const char *paths[] = {"/data/app/plain.app/lib",
        "/system/android/lib64/westlake_native:/data/app/app.organicmaps/lib",
        "/system/android/lib64/westlake_flutter:/data/app/chat.fluffy.fluffychat/lib",
        "/system/android/lib64/westlake_native:/data/app/io.anuke.mindustry/lib"};
    for (int variant = 0; variant < 4; ++variant) {
        for (int choice = 0; choice < 4; ++choice) {
            reset(); compat_choice = choice;
            assert(create(paths[variant], true) == 0);
            Edge *owner = edge(app_name, N11H_OWNER_NS);
            assert(owner);
            if (variant != 0) {
                assert(strcmp(owner->shared, N11H_PRIVATE_LIBS) == 0);
                Edge *system = edge(app_name, "default");
                assert(system && strstr(system->shared, "libsurface.z.so") && strstr(system->shared, "libstdc++.so") && strstr(system->shared, "libOpenSLES.so"));
                assert(probe_count == 2 && edge_count == 4 && fresh_count == 3);
            } else if (choice == 1) {
                assert(strcmp(owner->shared, N11H_COMPAT_LIBS) == 0 && !edge(app_name, "default"));
                assert(edge_count == 3);
            } else {
                assert(strcmp(owner->shared, N11H_OWNER_LIBS) == 0);
                assert((edge(app_name, "default") != NULL) == (choice == 0));
            }
            assert(strcmp(edge(app_name, bridge_name)->shared, "libandroid.so:libEGL.so") == 0);
            assert(logs > 0);
        }
    }
    for (int broken = 1; broken <= 10; ++broken) {
        if (broken == 5) continue;
        reset(); failure = broken;
        int result = create(paths[0], true);
        assert((result == 0) == (broken == 7));
        if (broken <= 3 || broken == 6 || broken == 8) assert(fresh_count == 0);
        if (broken == 3) assert(close_count == 1);
    }
    reset(); assert(create(paths[0], false) == 0);
    assert(edge_count == 1 && fresh_count == 0 && probe_count == 2 && close_count == 2);
    reset(); strcpy(app_name, "westlake.anl.app.0.1");
    assert(create(paths[0], true) == EINVAL && probe_count == 0);
    reset(); assert(create("", true) == EINVAL && probe_count == 0);
    reset(); strcpy(bridge_name, "wrong-owner");
    assert(create(paths[0], true) == EINVAL && probe_count == 0);
    puts("namespace replay PASS: once-only merged edges before fresh loads; r3 permissions; guards; failures; bootstrap");
}

static void opens(void)
{
    const char *owners[] = {N11H_BRIDGE_PATH, N11H_RUNTIME_PATH};
    for (int variant = 0; variant < 2; ++variant) {
        for (int broken = 0; broken <= 3; ++broken) {
            reset(); failure = broken;
            Dl_namespace application; strcpy(application.name, app_name);
            void *result = StockOpenNamespace(&application, owners[variant], RTLD_NOW);
            bool missing = broken == 1 || broken == variant + 2;
            assert((result == NULL) == missing);
            assert(fresh_count == 0 && probe_count == (broken == 1 ? 0 : 1));
            if (broken != 1) assert(strcmp(last_domain, N11H_OWNER_NS) == 0 && (last_flags & RTLD_NOLOAD));
            assert(logs > 0);
        }
    }
    const char *aliases[] = {"liboh_adapter_bridge.so", "liboh_android_runtime.so", "/other/liboh_adapter_bridge.so",
        "/system/android/lib64/./liboh_android_runtime.so", "/system/android/lib64/westlake_native/liboh_android_runtime.so"};
    for (int variant = 0; variant < 5; ++variant) {
        reset(); Dl_namespace application; strcpy(application.name, app_name);
        assert(!StockOpenNamespace(&application, aliases[variant], RTLD_NOW));
        assert(fresh_count == 0 && probe_count == 0 && logs > 0);
    }
    reset(); Dl_namespace application; strcpy(application.name, app_name);
    assert(StockOpenNamespace(&application, "libandroid.so", RTLD_NOW));
    assert(fresh_count == 1 && probe_count == 0 && strcmp(last_domain, app_name) == 0 && last_flags == RTLD_NOW);
    reset(); strcpy(application.name, app_name);
    assert(!StockOpenNamespace(NULL, owners[0], RTLD_NOW));
    assert(!StockOpenNamespace(&application, NULL, RTLD_NOW));
    assert(!StockOpenNamespace(&application, "", RTLD_NOW));
    assert(!StockOpenNamespace(&application, owners[0], RTLD_GLOBAL));
    strcpy(application.name, "westlake.anl.app.0.1");
    assert(!StockOpenNamespace(&application, owners[0], RTLD_NOW));
    assert(fresh_count == 0 && probe_count == 0);
    puts("open replay PASS: two exact paths sealed NOLOAD only; no app/default fallback; aliases rejected; old nonowner guards/routing retained");
}

int main(int argc, char **argv)
{
    assert(argc == 2);
    if (strcmp(argv[1], "namespace") == 0) namespaces();
    else { assert(strcmp(argv[1], "open") == 0); opens(); }
    return 0;
}
