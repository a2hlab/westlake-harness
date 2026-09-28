// ============================================================================
// android_os_Debug.cpp
//
// JNI bindings for android.os.Debug. Unity's UnityPlayer.initJni() calls the
// native heap accounting trio (getNativeHeapSize / getNativeHeapAllocatedSize
// / getNativeHeapFreeSize) very early — before the Activity is even drawn —
// and an UnsatisfiedLinkError there aborts the child in performLaunchActivity
// long before the graphics stage. AOSP's android_os_Debug.cpp backs these by
// dlmalloc's mallinfo; on OH (musl) the equivalent is mallinfo2(), which
// returns 64-bit fields and is exported by the OH musl libc.
//
// Semantics (mirroring AOSP frameworks/base/core/jni/android_os_Debug.cpp):
//   getNativeHeapSize          — total bytes obtained from the system by the
//                                native allocator   (mallinfo2.arena + hblkhd)
//   getNativeHeapAllocatedSize — bytes currently handed out to the app
//                                (mallinfo2.uordblks)
//   getNativeHeapFreeSize      — bytes in the allocator's free pool
//                                (mallinfo2.fordblks)
//
// getMemoryInfo(Debug$MemoryInfo) is registered as a no-op: it is only used by
// Unity's memory profiler (post-first-frame) and there is no Android-style
// /proc smaps PSS accounting layer here. Leaving the MemoryInfo object zeroed
// is harmless — the profiler simply reports zero for those buckets.
//
// Registration is done per-method and tolerant of failure so that a single
// missing/mismatched method (across OH boot image revisions of Debug.java)
// never fails the whole class registration with NoSuchMethodError.
// ============================================================================

#include "AndroidRuntime.h"

#include <jni.h>
#include <stdint.h>
#include <malloc.h>

namespace android {

namespace {

// android.os.Debug native heap accessors are @FastNative — JNIEnv*/jclass
// params are present in the C signature.
jlong JNICALL Debug_getNativeHeapSize(JNIEnv*, jclass) {
    struct mallinfo2 info = mallinfo2();
    return static_cast<jlong>(info.arena) + static_cast<jlong>(info.hblkhd);
}

jlong JNICALL Debug_getNativeHeapAllocatedSize(JNIEnv*, jclass) {
    struct mallinfo2 info = mallinfo2();
    return static_cast<jlong>(info.uordblks);
}

jlong JNICALL Debug_getNativeHeapFreeSize(JNIEnv*, jclass) {
    struct mallinfo2 info = mallinfo2();
    return static_cast<jlong>(info.fordblks);
}

// No-op: leaves the passed Debug$MemoryInfo zeroed (no PSS/smaps backing on OH).
void JNICALL Debug_getMemoryInfo(JNIEnv*, jclass, jobject /*memInfo*/) {
}

struct MethodSpec {
    const char* name;
    const char* sig;
    void* fn;
};

const MethodSpec kDebugMethods[] = {
    { "getNativeHeapSize",          "()J", reinterpret_cast<void*>(Debug_getNativeHeapSize) },
    { "getNativeHeapAllocatedSize", "()J", reinterpret_cast<void*>(Debug_getNativeHeapAllocatedSize) },
    { "getNativeHeapFreeSize",      "()J", reinterpret_cast<void*>(Debug_getNativeHeapFreeSize) },
    { "getMemoryInfo",              "(Landroid/os/Debug$MemoryInfo;)V",
                                    reinterpret_cast<void*>(Debug_getMemoryInfo) },
};

}  // namespace

int register_android_os_Debug(JNIEnv* env) {
    jclass clazz = env->FindClass("android/os/Debug");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    // Register one at a time so a single missing/mismatched method (across OH
    // boot image revisions of Debug.java) doesn't fail the whole batch.
    int registered = 0;
    for (const MethodSpec& m : kDebugMethods) {
        JNINativeMethod jm = { m.name, m.sig, m.fn };
        if (env->RegisterNatives(clazz, &jm, 1) == JNI_OK) {
            ++registered;
        } else if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
    }
    env->DeleteLocalRef(clazz);
    // The heap-accounting trio is what Unity initJni hard-depends on; treat any
    // successful registration as success.
    return registered > 0 ? 0 : -1;
}

}  // namespace android
