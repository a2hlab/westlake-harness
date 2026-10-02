#ifndef WESTLAKE_N11H_OWNER_H
#define WESTLAKE_N11H_OWNER_H

#define N11H_BRIDGE_PATH "/system/android/lib64/liboh_adapter_bridge.so"
#define N11H_RUNTIME_PATH "/system/android/lib64/liboh_android_runtime.so"
#define N11H_OWNER_NS "westlake.sealed.child"
#define N11H_OWNER_LIBS "liboh_adapter_bridge.so:liboh_android_runtime.so"
#define N11H_PRIVATE_LIBS "liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:liboh_adapter_bridge.so"
#define N11H_COMPAT_LIBS "liboh_adapter_bridge.so:liboh_android_runtime.so:libbionic_compat.so"

static const char *N11hOwnerPath(const char *path)
{
    if (strcmp(path, N11H_BRIDGE_PATH) == 0) return N11H_BRIDGE_PATH;
    if (strcmp(path, N11H_RUNTIME_PATH) == 0) return N11H_RUNTIME_PATH;
    return NULL;
}

static bool N11hProtectedName(const char *path)
{
    const char *base = strrchr(path, '/');
    base = base == NULL ? path : base + 1;
    return strcmp(base, "liboh_adapter_bridge.so") == 0 ||
           strcmp(base, "liboh_android_runtime.so") == 0;
}

static void *N11hResidentHandle(Dl_namespace *owner, const char *path,
                               const char *target)
{
    void *handle = dlopen_ns(owner, path, RTLD_NOW | RTLD_LOCAL | RTLD_NOLOAD);
    APPSPAWN_LOGI("[N11h-HOST-OWNER] action=resident-check target=%{public}s owner=%{public}s handle=%{public}p rc=%{public}d",
                  target, path, handle, handle == NULL ? ENOENT : 0);
    return handle;
}

static int N11hCheckOwners(Dl_namespace *owner, const char *target)
{
    void *bridge = N11hResidentHandle(owner, N11H_BRIDGE_PATH, target);
    if (bridge == NULL) return ENOENT;
    void *runtime = N11hResidentHandle(owner, N11H_RUNTIME_PATH, target);
    (void)dlclose(bridge);
    if (runtime == NULL) return ENOENT;
    (void)dlclose(runtime);
    return 0;
}

#endif
