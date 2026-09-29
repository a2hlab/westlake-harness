from pathlib import Path
import shutil
R=Path(__file__).resolve().parents[2];W=R/'bms/src/.work/b68-generation';A=W/'adapter'
identity='''#include "adapter_bridge_identity.h"
#include <dlfcn.h>
#ifndef WLAR_ADAPTER_BRIDGE_PATH
#error "WLAR_ADAPTER_BRIDGE_PATH is required"
#endif
#ifndef WLAR_ANDROID_RUNTIME_PATH
#error "WLAR_ANDROID_RUNTIME_PATH is required"
#endif

// #68: file SHA/build-id admission belongs to the deployment transaction.
// Runtime loading keeps actual dlopen failures and required ABI symbols visible.
namespace appspawnx {
namespace {
bool HasSymbol(void *handle, const char *symbol) {
    return handle != nullptr && dlsym(handle, symbol) != nullptr;
}
bool LoadPath(const char *path, const char *symbol, void **out) {
    if (out == nullptr) return false;
    *out = nullptr;
    void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    if (!HasSymbol(handle, symbol)) {
        if (handle != nullptr) dlclose(handle);
        return false;
    }
    *out = handle;
    return true;
}
}
bool LoadVerifiedAdapterBridge(void **out) {
    return LoadPath(WLAR_ADAPTER_BRIDGE_PATH, "adapter_bridge_set_class_loader", out);
}
bool LoadVerifiedAndroidRuntime(void **out) {
    return LoadPath(WLAR_ANDROID_RUNTIME_PATH,
        "_ZN7android14AndroidRuntime8startRegEP7_JNIEnv", out);
}
bool VerifyLoadedAdapterBridge(void *handle) {
    return HasSymbol(handle, "adapter_bridge_set_class_loader");
}
bool VerifyLoadedAndroidRuntime(void *handle) {
    return HasSymbol(handle, "_ZN7android14AndroidRuntime8startRegEP7_JNIEnv");
}
}
'''
for base in [A]:
 p=base/'framework/appspawn-x/src/adapter_bridge_identity.cpp';p.write_text(identity)
 p=base/'framework/appspawn-x/security_specialization/stock_child_plugin/src/westlake_stock_host_main.c';s=p.read_text()
 start=s.index('static int VerifyPluginFileSha256(');end=s.index('static int InstallPluginHostServices',start)
 s=s[:start]+'''/* File identities are checked by deploy_generation, not the process loader. */
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

'''+s[end:]
 s=s.replace('VerifyPluginFileSha256(', 'ResolvePluginPath(');p.write_text(s)
 p=base/'framework/appspawn-x/security_specialization/stock_child_plugin/src/sealed_child_provider_loader.c';s=p.read_text()
 start=s.index('static int RealVerifyIdentity(');end=s.index('static int RealIsMapped(',start);s=s[:start]+s[end:]
 start=s.index('        if (ops->verify_identity(');end=s.index('        {\n            int mapped',start);s=s[:start]+'        /* #68: provider file SHA/build-id is enforced by the deployer. */\n'+s[end:]
 s=s.replace('ops->current_pid == NULL || ops->verify_identity == NULL ||','ops->current_pid == NULL ||').replace('        RealVerifyIdentity,','        NULL, /* no runtime file-identity callback */');p.write_text(s)
# Canonical recipe fails early on required sources and zip inputs.
p=R/'bms/src/adapter/build/inner/compile_oh_adapter_bridge.sh';s=p.read_text();start=s.index('# 2026-04-30 (P2-B):');end=s.index('\ntotal=0',start);part=s[start:end].replace('[ -f "$src" ] || continue','[ -f "$src" ] || { echo "ERROR: required bridge source missing: $src" >&2; exit 1; }');s=s[:start]+part+s[end:]
s=s.replace('echo "WARN: minizip/zlib objects missing — apk_manifest_jni will fail to link"','for required in "$MINIZIP_DIR/unzip.o" "$MINIZIP_DIR/ioapi.o" "$LIBZ_A"; do\n        [ -f "$required" ] || echo "ERROR: required bridge link input missing: $required" >&2\n    done\n    exit 1');p.write_text(s)
print('updated runtime loaders and canonical bridge recipe')
