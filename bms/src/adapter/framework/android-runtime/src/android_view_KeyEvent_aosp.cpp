// ============================================================================
// android_view_KeyEvent_aosp.cpp
//
// 2026-05-26: adapter-private JNI binding for android.view.KeyEvent.
//
// Mirrors AOSP frameworks/base/core/jni/android_view_KeyEvent.cpp's native
// method table (names + signatures) verbatim so the Java side sees an
// identical JNI surface.  Without this, android.view.KeyEvent.<init> — which
// calls nativeNextId() to allocate the per-event id (KeyEvent.java:1605) —
// throws UnsatisfiedLinkError.  Observed 2026-05-26 as the sole blocker
// preventing BACK key events from reaching ViewRootImpl on HelloWorld: the
// client worker thread DID receive the key datagram and reached
// NewObject(KeyEvent) in android_view_InputEventReceiver.cpp::
// dispatchKeyFromWorker, but the constructor aborted because nativeNextId was
// never registered (adapter registered MotionEvent's natives via Plan A but
// never KeyEvent's).
//
// Implementation routes to adapter-private android::InputEvent /
// InputEventLookup (include/input/{Input.h,InputEventLabels.h}) rather than
// AOSP's classes, following the android_view_MotionEvent_aosp.cpp model — we
// must NOT include AOSP's <input/Input.h>, whose deep transitive include chain
// (attestation/, ui::Transform, ...) caused SIGBUS in libicu_jni.so on this
// project (see android_view_MotionEvent_aosp.cpp header for the full story).
//
// Only nativeNextId carries real behaviour (per-process monotonic id, shared
// with the MotionEvent path via InputEvent::nextId()).  nativeKeyCodeToString
// / nativeKeyCodeFromString route to InputEventLookup, which is a Phase 1 stub
// (returns nullptr / nullopt); KeyEvent.keyCodeToString()/keyCodeFromString()
// are debug/diagnostic-only and not on the BACK-key dispatch path.  This file
// registers no fieldIDs: the client worker constructs KeyEvent via the Java
// NewObject path (dispatchKeyFromWorker), not a native fromNative/toNative
// bridge, so no field cache is needed.
// ============================================================================

#include "input/Input.h"
#include "input/InputEventLabels.h"

#include <jni.h>
#include <nativehelper/JNIHelp.h>
#include <nativehelper/ScopedUtfChars.h>

#include <android/log.h>

#define LOG_TAG "KeyEvent-aosp"

namespace android {

// android.view.KeyEvent.<init> allocates its mId via this call
// (KeyEvent.java:1605).  Shares InputEvent's per-process monotonic id
// allocator with the MotionEvent JNI path so key and motion events draw from
// one id sequence — matching AOSP, where both call InputEvent::nextId().
static jint nativeNextId(JNIEnv* /*env*/, jclass /*clazz*/) {
    return static_cast<jint>(InputEvent::nextId());
}

// AOSP: env->NewStringUTF(KeyEvent::getLabel(keyCode)).  Phase 1:
// InputEventLookup is a stub (returns nullptr); fall back to "KEYCODE_UNKNOWN"
// so callers always receive a non-null string.
static jstring nativeKeyCodeToString(JNIEnv* env, jclass /*clazz*/, jint keyCode) {
    const char* label = InputEventLookup::getLabelByKeyCode(keyCode);
    return env->NewStringUTF(label != nullptr ? label : "KEYCODE_UNKNOWN");
}

// AOSP: KeyEvent::getKeyCodeFromLabel(label).value_or(AKEYCODE_UNKNOWN).
// AKEYCODE_UNKNOWN == 0.
static jint nativeKeyCodeFromString(JNIEnv* env, jclass /*clazz*/, jstring label) {
    ScopedUtfChars keyLabel(env, label);
    return InputEventLookup::getKeyCodeByLabel(keyLabel.c_str()).value_or(0 /*AKEYCODE_UNKNOWN*/);
}

static const JNINativeMethod g_methods[] = {
        {"nativeKeyCodeToString", "(I)Ljava/lang/String;", (void*)nativeKeyCodeToString},
        {"nativeKeyCodeFromString", "(Ljava/lang/String;)I", (void*)nativeKeyCodeFromString},
        {"nativeNextId", "()I", (void*)nativeNextId},
};

int register_android_view_KeyEvent(JNIEnv* env) {
    jclass clazz = env->FindClass("android/view/KeyEvent");
    if (clazz == nullptr) {
        __android_log_print(ANDROID_LOG_FATAL, LOG_TAG,
                            "FindClass android/view/KeyEvent failed");
        return -1;
    }
    if (env->RegisterNatives(clazz, g_methods,
                             sizeof(g_methods) / sizeof(g_methods[0])) < 0) {
        __android_log_print(ANDROID_LOG_FATAL, LOG_TAG, "RegisterNatives failed");
        env->DeleteLocalRef(clazz);
        return -1;
    }
    env->DeleteLocalRef(clazz);
    __android_log_print(ANDROID_LOG_INFO, LOG_TAG,
                        "registered 3 KeyEvent native methods (nativeNextId live)");
    return 0;
}

}  // namespace android
