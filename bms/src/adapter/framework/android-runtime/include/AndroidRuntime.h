// ============================================================================
// AndroidRuntime.h
//
// Minimal public header for OH-Adapter's replacement of libandroid_runtime.so.
//
// Target symbol signature (mangled): _ZN7android14AndroidRuntime8startRegEP7_JNIEnv
//   = int android::AndroidRuntime::startReg(JNIEnv*)
//
// This is what appspawn-x's `registerNativeMethods()` looks up via dlsym to
// register all framework JNI bindings. Progressive replacement: Stage 1 only
// wires the JNI methods Hello World actually exercises; further stages add
// more register_* modules until the full AOSP list is covered.
// ============================================================================

#pragma once
#include <jni.h>

namespace android {

class AndroidRuntime {
public:
    // Returns 0 on success, -1 on failure.
    static int startReg(JNIEnv* env);

    // Cached VM used by callback-local central JNI admission.
    static JavaVM* getJavaVM();

    // Internal: stash the JavaVM at startReg entry.
    static void setJavaVM(JavaVM* vm);

    // AOSP-compatible static helper used by frameworks/base/core/jni/
    // core_jni_helpers.h's jniRegisterNativeMethods inline wrapper.
    // Trivial passthrough — mirrors frameworks/base/core/jni/AndroidRuntime.cpp.
    static int registerNativeMethods(JNIEnv* env, const char* className,
                                      const JNINativeMethod* gMethods,
                                      int numMethods);
};

// Forward declarations of register_* functions (one per AOSP JNI module).
// Each is defined in its own .cpp and added to the dispatch table inside
// AndroidRuntime::startReg when Hello World or later stages need it.
int register_android_util_Log(JNIEnv* env);
int register_android_util_EventLog(JNIEnv* env);
int register_android_app_Activity(JNIEnv* env);
int register_android_view_SurfaceSession(JNIEnv* env);
int register_android_view_DisplayEventReceiver(JNIEnv* env);
int register_android_view_InputChannel(JNIEnv* env);
int register_android_view_InputEventReceiver(JNIEnv* env);
int register_android_os_SystemProperties(JNIEnv* env);
int register_android_os_Trace(JNIEnv* env);
int register_android_os_Process(JNIEnv* env);
int register_android_os_SystemClock(JNIEnv* env);
int register_android_os_Binder(JNIEnv* env);
int register_android_os_Debug(JNIEnv* env);
// 2026-06-29 [STAGE2-UNITY wall#4]: android.hardware.SystemSensorManager (+ its
// $BaseEventQueue). getSystemService("sensor") (UnityPlayer.toggleGyroscopeSensor,
// jadx :1051) hard-calls nativeClassInit/nativeCreate/nativeGetSensorAtIndex in
// the SystemSensorManager constructor; zero-sensor stub, design-consistent with
// the NDK ASensor stub. See android_hardware_SensorManager.cpp.
int register_android_hardware_SensorManager(JNIEnv* env);
int register_android_view_SurfaceControl(JNIEnv* env);
int register_android_content_AssetManager(JNIEnv* env);
int register_android_os_MessageQueue(JNIEnv* env);
int register_android_content_res_ApkAssets(JNIEnv* env);
int register_android_content_StringBlock(JNIEnv* env);
int register_android_content_XmlBlock(JNIEnv* env);
int register_com_android_internal_os_ClassLoaderFactory(JNIEnv* env);
int register_com_android_internal_util_VirtualRefBasePtr(JNIEnv* env);

}  // namespace android
