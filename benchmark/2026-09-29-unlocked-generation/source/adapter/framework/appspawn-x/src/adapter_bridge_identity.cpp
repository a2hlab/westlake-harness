#include "adapter_bridge_identity.h"
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
