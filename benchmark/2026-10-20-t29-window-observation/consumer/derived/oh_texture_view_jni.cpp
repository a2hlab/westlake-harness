/*
 * android.view.TextureView JNI at the OHOS native-window boundary.
 *
 * TextureView's hardware path is owned by TextureLayer/HWUI.  These methods
 * only keep the producer native window used by the optional software-canvas
 * API.  Preserve Android's Java object and store a referenced OH producer
 * endpoint in mNativeWindow.
 */

#include "external_window.h"

#include <jni.h>

#include <cstdio>
#include <cstring>
#include <cstdint>

// T29 derivation: observe-only. The ONLY change vs the pinned original (sha256 7189e5c2…1878a0558b)
// is this include plus the r29c_observe() calls in nDestroy/nCreate. No provider/getter is added and
// no control flow or lifecycle is changed: destroy-before-getter, unref-before-ref, and SetLongField
// after ref are all preserved exactly.
#include "observe29c.h"

extern "C" jlong oh_surface_texture_get_native_window(JNIEnv* env, jobject surfaceTexture);

namespace android {
namespace {

jfieldID gTextureViewNativeWindow = nullptr;

// T29 observe-only: a diagnostic out-struct lets nCreate CORRELATE the old window it tore down with
// the new window it installs, in ONE record and WITHOUT any extra JNI/getter call. The original
// nDestroy body is extracted verbatim into destroyNativeWindowImpl; both the public nDestroy and
// nCreate call it, so the JNI/OH call order and count stay exactly as the original (nCreate still
// destroys-then-creates). diag carries only values the body ALREADY read.
struct R29cDestroyDiag {
    bool      field_resolved;
    bool      had_window;
    uintptr_t old_window;
    bool      unref_called;
    int32_t   unref_rc;
};

void destroyNativeWindowImpl(JNIEnv* env, jobject textureView, R29cDestroyDiag* diag)
{
    const uintptr_t _self = reinterpret_cast<uintptr_t>(&destroyNativeWindowImpl);
    const uintptr_t _caller = reinterpret_cast<uintptr_t>(__builtin_return_address(0));
    if (diag != nullptr) {
        diag->field_resolved = false; diag->had_window = false;
        diag->old_window = 0; diag->unref_called = false; diag->unref_rc = 0;
    }
    if (gTextureViewNativeWindow == nullptr) {
        {   // T29 observe-only: entered but the JNI field is unresolved. We add NO GetLongField, so the
            // window is unknown: a called=0 destroy with all window fields unknown.
            r29c_record _r;
            std::memset(&_r, 0, sizeof(_r));
            _r.phase = R29C_PRODUCER_DESTROY;
            _r.call = r29c_call_id();
            _r.self = _self; _r.caller = _caller;
            _r.wrapper = 0;              // unknown identity -> invalid/overflow lane
            _r.invalid = 1;             // an early-return with no action taken
            _r.called = 0;
            _r.unref_called = 0;
            _r.unref_rc_valid = 0;      // no unref ran -> no rc
            r29c_observe(&_r);
        }
        return;
    }
    if (diag != nullptr) diag->field_resolved = true;
    auto* window = reinterpret_cast<OHNativeWindow*>(
        env->GetLongField(textureView, gTextureViewNativeWindow));
    int32_t unrefRc = 0;
    bool unrefCalled = false;
    if (window != nullptr) {
        // Same single call as the original — its int32 return was ignored there; we only CAPTURE it.
        unrefRc = OH_NativeWindow_NativeObjectUnreference(window);
        unrefCalled = true;
        env->SetLongField(textureView, gTextureViewNativeWindow, 0);
    }
    if (diag != nullptr) {   // hand the ALREADY-READ old window + unref result back to nCreate
        diag->had_window = (window != nullptr);
        diag->old_window = reinterpret_cast<uintptr_t>(window);
        diag->unref_called = unrefCalled;
        diag->unref_rc = unrefRc;
    }
    {   // T29 observe-only: producer-destroy. unref_rc is a REAL int32 return (valid=1 when the call
        // ran), independent of any method rc. Values only; `window` is a local, never dereferenced.
        r29c_record _r;
        std::memset(&_r, 0, sizeof(_r));
        _r.phase = R29C_PRODUCER_DESTROY;
        _r.call = r29c_call_id();
        _r.self = _self; _r.caller = _caller;
        _r.wrapper = reinterpret_cast<uintptr_t>(window);   // 0 when there was nothing to destroy
        if (unrefCalled) {
            _r.valid |= R29C_OLDWIN | R29C_OH | R29C_UNREFRC;
            _r.old_window = reinterpret_cast<uintptr_t>(window);
            _r.oh = reinterpret_cast<uintptr_t>(window);     // the OH window IS the correlation handle
            _r.unref_called = 1;
            _r.unref_rc_valid = 1;
            _r.unref_rc = unrefRc;
            _r.called = 1;
            _r.transition = 1;        // the producer endpoint was torn down
        }
        r29c_observe(&_r);
    }
}

void TextureView_nDestroyNativeWindow(JNIEnv* env, jobject textureView)
{
    // Public JNI entry: identical behavior to the original (forwards to the extracted body, no diag).
    destroyNativeWindowImpl(env, textureView, nullptr);
}

void TextureView_nCreateNativeWindow(JNIEnv* env, jobject textureView,
                                     jobject surfaceTexture)
{
    const uintptr_t _self = reinterpret_cast<uintptr_t>(&TextureView_nCreateNativeWindow);
    const uintptr_t _caller = reinterpret_cast<uintptr_t>(__builtin_return_address(0));
    R29cDestroyDiag diag;
    destroyNativeWindowImpl(env, textureView, &diag);   // same destroy-first call as the original
    const jlong handle = oh_surface_texture_get_native_window(env, surfaceTexture);
    auto* window = reinterpret_cast<OHNativeWindow*>(handle);
    int32_t refRc = 0;
    bool refCalled = false;
    if (window != nullptr) {
        // Same single call as the original — its int32 return was ignored there; we only CAPTURE it.
        // The original SetLongField strategy (always, after ref, within this branch) is unchanged.
        refRc = OH_NativeWindow_NativeObjectReference(window);
        refCalled = true;
        env->SetLongField(textureView, gTextureViewNativeWindow, handle);
    }
    {   // T29 observe-only: producer-replace. This SINGLE record correlates the OLD window (captured by
        // the destroy body via diag — no extra read) with the NEW window, so no cross-call/cross-thread
        // guessing is needed. ref_rc is a REAL int32 return (valid=1 when the call ran). Values only.
        r29c_record _r;
        std::memset(&_r, 0, sizeof(_r));
        _r.phase = R29C_PRODUCER_REPLACE;
        _r.call = r29c_call_id();
        _r.self = _self; _r.caller = _caller;
        _r.wrapper = reinterpret_cast<uintptr_t>(window);   // 0 when the getter returned no window
        _r.transition = 1;
        if (diag.had_window) {   // the OLD window this replace tore down (old-side snapshot)
            _r.valid |= R29C_OLDWIN;
            _r.old_window = diag.old_window;
            if (diag.unref_called) {
                _r.valid |= R29C_UNREFRC;
                _r.unref_called = 1;
                _r.unref_rc_valid = 1;
                _r.unref_rc = diag.unref_rc;
            }
        }
        if (refCalled) {         // the NEW window this replace installed (new-side snapshot)
            _r.valid |= R29C_NEWWIN | R29C_OH | R29C_REFRC;
            _r.new_window = reinterpret_cast<uintptr_t>(window);
            _r.oh = reinterpret_cast<uintptr_t>(window);     // the new OH window IS the correlation handle
            _r.ref_called = 1;
            _r.ref_rc_valid = 1;
            _r.ref_rc = refRc;
            _r.called = 1;
        }
        r29c_observe(&_r);
    }
    fprintf(stderr, "[WESTLAKE-TEXTUREVIEW] create surfaceTexture=%p window=%p\n",
            surfaceTexture, window);
    fflush(stderr);
}

jboolean TextureView_nLockCanvas(JNIEnv*, jclass, jlong nativeWindow,
                                 jobject, jobject)
{
    // Software Canvas requires binding an OH buffer to android.graphics.Canvas.
    // Report unavailable truthfully; TextureView's normal HWUI path is independent.
    return nativeWindow != 0 ? JNI_FALSE : JNI_FALSE;
}

void TextureView_nUnlockCanvasAndPost(JNIEnv*, jclass, jlong, jobject)
{
}

const JNINativeMethod kTextureViewMethods[] = {
    {"nCreateNativeWindow", "(Landroid/graphics/SurfaceTexture;)V",
     reinterpret_cast<void*>(TextureView_nCreateNativeWindow)},
    {"nDestroyNativeWindow", "()V",
     reinterpret_cast<void*>(TextureView_nDestroyNativeWindow)},
    {"nLockCanvas", "(JLandroid/graphics/Canvas;Landroid/graphics/Rect;)Z",
     reinterpret_cast<void*>(TextureView_nLockCanvas)},
    {"nUnlockCanvasAndPost", "(JLandroid/graphics/Canvas;)V",
     reinterpret_cast<void*>(TextureView_nUnlockCanvasAndPost)},
};

}  // namespace

int register_android_view_TextureView_oh(JNIEnv* env)
{
    jclass clazz = env->FindClass("android/view/TextureView");
    if (clazz == nullptr) {
        if (env->ExceptionCheck()) {
            env->ExceptionClear();
        }
        return -1;
    }
    gTextureViewNativeWindow = env->GetFieldID(clazz, "mNativeWindow", "J");
    if (env->ExceptionCheck() || gTextureViewNativeWindow == nullptr) {
        env->ExceptionClear();
        env->DeleteLocalRef(clazz);
        return -1;
    }

    const int result = env->RegisterNatives(
        clazz, kTextureViewMethods,
        static_cast<jint>(sizeof(kTextureViewMethods) / sizeof(kTextureViewMethods[0])));
    if (env->ExceptionCheck()) {
        env->ExceptionClear();
    }
    env->DeleteLocalRef(clazz);
    fprintf(stderr, "[WESTLAKE-TEXTUREVIEW] register rc=%d\n", result);
    fflush(stderr);
    return result;
}

}  // namespace android
