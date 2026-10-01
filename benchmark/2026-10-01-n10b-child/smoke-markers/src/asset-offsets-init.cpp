// AOSP14 r1 android_util_AssetManager registration side effect.
// Separate from frozen nativeOpenAssetFd (FZ-003). U8 has a second cache
// in libandroid.so, whose NDK AAssetManager_fromJava also reads mObject.
#include <jni.h>
#include <dlfcn.h>
#include <hilog/log.h>

namespace android {
// Exact layout from android_runtime/android_util_AssetManager.h (one field).
struct assetmanager_offsets_t { jfieldID mObject; };
extern assetmanager_offsets_t gAssetManagerOffsets;
}

extern "C" int initialize_n10b_asset_offsets(JNIEnv* env) {
    jclass clazz = env->FindClass("android/content/res/AssetManager");
    if (!clazz) return -1;
    jfieldID field = env->GetFieldID(clazz, "mObject", "J");
    env->DeleteLocalRef(clazz);
    if (!field || env->ExceptionCheck()) return -1;

    // Keep this owner's cache valid without rerunning RegisterNatives.
    android::gAssetManagerOffsets.mObject = field;
    // Call after HWUI registration: use the NDK library in the same route
    // domain. Retain its handle, so the initialized cache cannot unload.
    void* ndk = dlopen("libandroid.so", RTLD_NOW | RTLD_LOCAL);
    if (!ndk) return -1;
    auto* offsets = reinterpret_cast<android::assetmanager_offsets_t*>(
        dlsym(ndk, "_ZN7android20gAssetManagerOffsetsE"));
    if (!offsets) return -1;
    offsets->mObject = field;
    HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_AssetOffsets",
        "AssetManager.mObject cached in runtime and libandroid NDK owner");
    return 0;
}
