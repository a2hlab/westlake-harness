#include "adapter_bridge_identity.h"

#include "westlake_elf_identity.h"

#include <dlfcn.h>
#include <elf.h>
#include <limits.h>

#ifndef WLAR_ADAPTER_BRIDGE_PATH
#error "WLAR_ADAPTER_BRIDGE_PATH must bind the deployed adapter bridge path"
#endif
#ifndef WLAR_ADAPTER_BRIDGE_SHA256_HEX
#error "WLAR_ADAPTER_BRIDGE_SHA256_HEX must bind the exact adapter bridge"
#endif
#ifndef WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX
#error "WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX must bind the bridge ELF Build-ID"
#endif
#ifndef WLAR_ANDROID_RUNTIME_PATH
#error "WLAR_ANDROID_RUNTIME_PATH must bind the deployed Android runtime path"
#endif
#ifndef WLAR_ANDROID_RUNTIME_SHA256_HEX
#error "WLAR_ANDROID_RUNTIME_SHA256_HEX must bind the exact Android runtime"
#endif
#ifndef WLAR_ANDROID_RUNTIME_BUILD_ID_HEX
#error "WLAR_ANDROID_RUNTIME_BUILD_ID_HEX must bind the runtime ELF Build-ID"
#endif

namespace appspawnx {

namespace {

bool LoadVerified(const char *path, const char *sha256,
                  const char *buildId, const char *identitySymbol,
                  void **outHandle)
{
    char resolvedPath[PATH_MAX];
    void *identity = nullptr;
    if (outHandle == nullptr ||
        WLEI_VerifyFileHex(path, EM_AARCH64, sha256, buildId,
                           resolvedPath, sizeof(resolvedPath)) != 0) {
        return false;
    }
    void *handle = dlopen(resolvedPath, RTLD_NOW | RTLD_LOCAL);
    if (handle == nullptr ||
        WLEI_VerifyLoadedSymbolHex(
            handle, identitySymbol, path, EM_AARCH64, sha256, buildId,
            &identity) != 0 || identity == nullptr) {
        if (handle != nullptr) {
            (void)dlclose(handle);
        }
        return false;
    }
    *outHandle = handle;
    return true;
}

bool VerifyLoaded(void *handle, const char *path, const char *sha256,
                  const char *buildId, const char *identitySymbol)
{
    void *identity = nullptr;
    return WLEI_VerifyLoadedSymbolHex(
               handle, identitySymbol, path, EM_AARCH64, sha256, buildId,
               &identity) == 0 && identity != nullptr;
}

}  // namespace

bool LoadVerifiedAdapterBridge(void **outHandle)
{
    static const char bridgeSha256[] = WLAR_ADAPTER_BRIDGE_SHA256_HEX;
    static const char bridgeBuildId[] = WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX;
    return LoadVerified(
        WLAR_ADAPTER_BRIDGE_PATH, bridgeSha256, bridgeBuildId,
        "adapter_bridge_set_class_loader", outHandle);
}

bool LoadVerifiedAndroidRuntime(void **outHandle)
{
    static const char runtimeSha256[] = WLAR_ANDROID_RUNTIME_SHA256_HEX;
    static const char runtimeBuildId[] = WLAR_ANDROID_RUNTIME_BUILD_ID_HEX;
    return LoadVerified(
        WLAR_ANDROID_RUNTIME_PATH, runtimeSha256, runtimeBuildId,
        "_ZN7android14AndroidRuntime8startRegEP7_JNIEnv", outHandle);
}

bool VerifyLoadedAdapterBridge(void *handle)
{
    static const char bridgeSha256[] = WLAR_ADAPTER_BRIDGE_SHA256_HEX;
    static const char bridgeBuildId[] = WLAR_ADAPTER_BRIDGE_BUILD_ID_HEX;
    void *identitySymbol = nullptr;
    return WLEI_VerifyLoadedSymbolHex(
        handle, "adapter_bridge_set_class_loader",
        WLAR_ADAPTER_BRIDGE_PATH, EM_AARCH64, bridgeSha256,
        bridgeBuildId, &identitySymbol) == 0 && identitySymbol != nullptr;
}

bool VerifyLoadedAndroidRuntime(void *handle)
{
    static const char runtimeSha256[] = WLAR_ANDROID_RUNTIME_SHA256_HEX;
    static const char runtimeBuildId[] = WLAR_ANDROID_RUNTIME_BUILD_ID_HEX;
    return VerifyLoaded(
        handle, WLAR_ANDROID_RUNTIME_PATH, runtimeSha256, runtimeBuildId,
        "_ZN7android14AndroidRuntime8startRegEP7_JNIEnv");
}

}  // namespace appspawnx
