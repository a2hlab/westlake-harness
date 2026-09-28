// ============================================================================
// android_window_show_native.cpp
//
// [WALL nativeShowWindow — 2026-06-29] dlsym-fallback resolver for
//   int adapter.window.WindowSessionAdapter.nativeShowWindow(int)
//
// WHY HERE (not in the bridge):
//   The launch-coherent GOLDEN bridge (liboh_adapter_bridge.so md5 52929345)
//   does NOT register nativeShowWindow in its JNINativeMethod table.  When the
//   app calls it, ART's unregistered-native path falls back to dlsym for the
//   C symbol Java_adapter_window_WindowSessionAdapter_nativeShowWindow across
//   ALL loaded libs.  liboh_android_runtime.so is loaded, hot-swappable,
//   non-BCP, and unrelated to the launch ABI — so defining the symbol HERE
//   resolves the UnsatisfiedLinkError with ZERO launch-regression risk.
//   (Both rebuilt bridges that *did* register nativeShowWindow regressed the
//   launch ABI → LIFECYCLE_TIMEOUT.  So we must not rebuild the bridge.)
//
// WHAT IT DOES (safe success stub — return 0):
//   In the golden bridge's window model, createSession ALREADY performs the
//   real display work: IWindowManager::AddWindow (window shown) + RequestFocus
//   (oh_window_manager_client.cpp:387,483).  nativeShowWindow is only the
//   re-foreground / re-focus path (AddWindow is just a safety net there).  By
//   the time this native is reached the window is already added and displayed,
//   so returning 0 (success) skips only a redundant re-focus and lets the
//   render path (GfxDevice init → eglCreateWindowSurface → first frame)
//   proceed.  The real OHWindowManagerClient::showWindow lives in the bridge
//   with INTERNAL visibility (not exported), so it cannot be linked/dlsym'd
//   from here; the stub is the correct low-risk resolution.  Upgrade only if a
//   first frame fails specifically for lack of re-focus.
//
//   A hilog line (domain 0xD000F00 / tag "OH_WSHOW") confirms the native is
//   hit on-device.
// ============================================================================

#include <jni.h>

extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...);
#define HLOG_INFO(fmt, ...) HiLogPrint(3, 4, 0xD000F00u, "OH_WSHOW", fmt, ##__VA_ARGS__)

extern "C" JNIEXPORT jint JNICALL
Java_adapter_window_WindowSessionAdapter_nativeShowWindow(JNIEnv* /*env*/,
                                                          jobject /*thiz*/,
                                                          jint sessionId) {
    HLOG_INFO("nativeShowWindow(sessionId=%d) HIT (runtime dlsym-fallback stub) "
              "-> return 0; window already AddWindow'd+focused at createSession",
              (int)sessionId);
    return 0;
}
