import hashlib
from pathlib import Path


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASE_SHA = "507bf160dfae87851345c8fc564c9378356a773cc84272d2ec0635b1c0ef0c50"
R3_SHA = "65cc3535ebf22bdf664b3c8ddf932ccd7f42d936be1c861e1221a80b12a00284"


def sha(filename):
    return hashlib.sha256(Path(filename).read_bytes()).hexdigest()


def candidate():
    filename = HERE / "inputs/host-r3.c"
    if sha(filename) != BASE_SHA:
        raise ValueError("accepted r3 source changed")
    original = filename.read_text()
    start = original.index("static WLASC_NOINLINE int StockCreateConfiguredNamespaces(")
    end = original.index("static uint8_t HexNibble(", start)
    create = original[start:original.index("static WLASC_NOINLINE void *StockOpenNamespace(", start)]
    validation = create.index("    if (wants_bridge) {\n        if (!NamespaceNameOwnedByCurrentProcess")
    bridge_init = create.index("        dlns_init(bridge_namespace, bridge_name);")
    bootstrap = create.index("        if (bridge_bootstrap_soname != NULL) {")
    app_init = create.index("    dlns_init(app_namespace, app_name);")
    private = create.index("    if (flutter_private || native_private) {\n        Dl_namespace system_owner, runtime_owner;")
    loads = create.index("        const bool needs_runtime = flutter_private ||")
    old_bridge = create.index("    if (wants_bridge) {\n        result = dlns_inherit(app_namespace, bridge_namespace,")
    abi = create.index("    if (flutter_private || native_private) {\n        /* OH 6.1 musl ignores")
    guard = create[:bridge_init] + "    }\n"
    prepare = """
    Dl_namespace sealed_owner;
    result = dlns_get(N11H_OWNER_NS, &sealed_owner);
    if (result != 0) {
        APPSPAWN_LOGE("[N11h-HOST-OWNER] action=reject target=%{public}s owner=sealed rc=%{public}d", app_name, result);
        return NamespaceResultFence(result);
    }
    result = N11hCheckOwners(&sealed_owner, app_name);
    if (result != 0) return NamespaceResultFence(result);
    if (wants_bridge) {
"""
    bridge = create[bridge_init:bootstrap] + """        result = dlns_inherit(bridge_namespace, &sealed_owner, N11H_OWNER_LIBS);
        APPSPAWN_LOGI("[N11h-HOST-OWNER] action=inherit target=%{public}s owner=westlake.sealed.child shared=%{public}s rc=%{public}d",
                      bridge_name, N11H_OWNER_LIBS, result);
        if (result != 0) return NamespaceResultFence(result);
    }

"""
    app = create[app_init:private] + """    Dl_namespace compat_owner;
    const bool compat_ready = wants_bridge && !flutter_private && !native_private &&
        U10ShareResidentCompat(&compat_owner) == 0;
    const bool compat_sealed = compat_ready && strcmp(compat_owner.name, N11H_OWNER_NS) == 0;
    const char *owner_shared = (flutter_private || native_private) ? N11H_PRIVATE_LIBS :
        (compat_sealed ? N11H_COMPAT_LIBS : N11H_OWNER_LIBS);
    result = dlns_inherit(app_namespace, &sealed_owner, owner_shared);
    APPSPAWN_LOGI("[N11h-HOST-OWNER] action=inherit target=%{public}s owner=westlake.sealed.child shared=%{public}s rc=%{public}d",
                  app_name, owner_shared, result);
    if (result != 0) return NamespaceResultFence(result);
    if (flutter_private || native_private) {
        Dl_namespace system_owner;
        result = dlns_get("default", &system_owner);
        if (result != 0) return NamespaceResultFence(result);
        result = dlns_inherit(app_namespace, &system_owner,
            "libc.so:libdl.so:libm.so:libEGL.so:libGLESv3.so:libsurface.z.so:liboh_android_runtime.so:libbionic_compat.so:liblog.so:libc++.so:libstdc++.so:libOpenSLES.so");
        if (result != 0) return NamespaceResultFence(result);
    }
    if (wants_bridge) {
        result = dlns_inherit(app_namespace, bridge_namespace, bridge_shared_sonames);
        if (result != 0) return NamespaceResultFence(result);
        if (compat_ready && !compat_sealed) {
            int compat_result = dlns_inherit(app_namespace, &compat_owner, "libbionic_compat.so");
            if (compat_result != 0) {
                APPSPAWN_LOGE("[U10-COMPAT-VISIBLE] unavailable inherit result=%{public}d; namespace continues", compat_result);
            }
        }
"""
    old_bootstrap = create[bootstrap:app_init].rstrip()
    if not old_bootstrap.endswith("    }"):
        raise ValueError("bridge bootstrap boundary changed")
    app += old_bootstrap + "\n\n"
    rewritten = guard + prepare + bridge + app + "    if (flutter_private || native_private) {\n" + create[loads:old_bridge] + create[abi:]
    opened = """static WLASC_NOINLINE void *StockOpenNamespace(
    void *app_namespace_opaque, const char *path, int mode)
{
    Dl_namespace *app_namespace = (Dl_namespace *)app_namespace_opaque;
    void *handle;
    if (app_namespace == NULL || path == NULL || path[0] == '\\0' ||
        !NamespaceNameOwnedByCurrentProcess(app_namespace->name, "app") ||
        (mode & RTLD_GLOBAL) != 0) {
        return NamespaceHandleFence(NULL);
    }
    const char *owner_path = N11hOwnerPath(path);
    if (owner_path != NULL) {
        Dl_namespace owner;
        int result = dlns_get(N11H_OWNER_NS, &owner);
        handle = result == 0 ? N11hResidentHandle(&owner, owner_path, app_namespace->name) : NULL;
        APPSPAWN_LOGI("[N11h-HOST-OPEN] action=%{public}s path=%{public}s target=%{public}s handle=%{public}p rc=%{public}d",
                      handle == NULL ? "reject" : "resident", path, app_namespace->name, handle,
                      result != 0 ? result : (handle == NULL ? ENOENT : 0));
        return NamespaceHandleFence(handle);
    }
    if (N11hProtectedName(path)) {
        APPSPAWN_LOGE("[N11h-HOST-OPEN] action=reject path=%{public}s target=%{public}s handle=NULL rc=%{public}d", path, app_namespace->name, EINVAL);
        return NamespaceHandleFence(NULL);
    }
    handle = dlopen_ns(app_namespace, path, mode | RTLD_LOCAL);
    return NamespaceHandleFence(handle);
}

"""
    text = original[:start] + rewritten + opened + original[end:]
    text = text.replace('#include "resident-compat.h"', '#include "resident-compat.h"\n#include "n11h-owner.h"', 1)
    return text


if __name__ == "__main__":
    print(candidate(), end="")
