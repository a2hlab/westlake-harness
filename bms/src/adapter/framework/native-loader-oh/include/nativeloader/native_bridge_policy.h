#ifndef WESTLAKE_NATIVE_LOADER_OH_NATIVE_BRIDGE_POLICY_H_
#define WESTLAKE_NATIVE_LOADER_OH_NATIVE_BRIDGE_POLICY_H_

#include <array>
#include <string_view>

namespace westlake::nativeloader::policy {

struct SystemLibrary {
  std::string_view soname;
  std::string_view path;
};

inline constexpr int kSchemaVersion = 1;
inline constexpr std::string_view kArchitecture = "arm64";
inline constexpr std::string_view kBridgeBootstrapSoname =
    "libwestlake_bionic_pthread_bridge.so";

inline constexpr std::array<std::string_view, 2> kBridgeSearchPaths = {
    "/system/android/lib64",
    "/system/lib64/platformsdk",
};

inline constexpr std::array<std::string_view, 2> kBridgePermittedPaths = {
    "/system/android/lib64",
    "/system/lib64/platformsdk",
};

inline constexpr std::array<std::string_view, 3> kSystemCallerRoots = {
    "/apex/",
    "/system/android/framework/",
    "/system/framework/",
};

inline constexpr std::array<SystemLibrary, 4> kSystemLibraries = {{
    {"libicu_jni.so", "/system/android/lib64/libicu_jni.so"},
    {"libjavacore.so", "/system/android/lib64/libjavacore.so"},
    {"libopenjdk.so", "/system/android/lib64/libopenjdk.so"},
    {"liboh_adapter_bridge.so", "/system/android/lib64/liboh_adapter_bridge.so"},
}};

// This is adapter policy, not an app-provided allowlist. A generation is not
// deployable until the closure gate binds every provider and transitive edge.
inline constexpr std::array<std::string_view, 6> kBridgeSharedSonames = {
    "libandroid.so",
    "libEGL.so",
    "liblog.so",
    "libmediandk.so",
    "libz.so",
    "libwestlake_bionic_pthread_bridge.so",
};

}  // namespace westlake::nativeloader::policy

#endif  // WESTLAKE_NATIVE_LOADER_OH_NATIVE_BRIDGE_POLICY_H_
