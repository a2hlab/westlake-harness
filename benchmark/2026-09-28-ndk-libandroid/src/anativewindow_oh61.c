/*
 * anativewindow_oh61.c — ANativeWindow_* NDK bridge for libandroid (T4).
 *
 * Ported from ~/orca/00.Workspace @ 72a2f0a52 (per outer-loop note, board #5/#8):
 *   - src/adapter/framework/android-runtime/src/android_graphics_compat_shim.cpp
 *     ("G2.14ad ANativeWindow NDK bridges", ANativeWindow_fromSurface/acquire/
 *     release/getWidth/getHeight/getFormat/setBuffersGeometry/query)
 *   - src/adapter/framework/hwui-shim/jni/oh_native_window_shim.c (OH bridging)
 *
 * Adaptations for OH 6.1.0.31 sysroot (verified, see ../PORTING-NOTES.md):
 *   1. Bare inner-API names do not exist here; all calls use the
 *      OH_NativeWindow_* prefixed NDK exports from libnative_window.so.
 *   2. GET_BUFFER_GEOMETRY varargs are exactly (&height, &width) — the
 *      source's 3-arg form (with &format) is an OH7 trace; format is
 *      queried separately via GET_FORMAT.
 *   3. AdapterAnw probe layer (oh_anw_try_acquire/... in
 *      liboh_adapter_bridge.so) does not exist in this runtime: removed.
 *      fromSurface returns Surface.mNativeObject directly (OHNativeWindow ≡
 *      ANativeWindow ABI on this target).
 *
 * Build: scripts/lab/dockbuild.sh cc -shared -fPIC ... -lnative_window
 */
#include <stdint.h>
#include <jni.h>

/* Opaque alias — OHNativeWindow* and ANativeWindow* are layout-identical. */
typedef struct ANativeWindow ANativeWindow;
typedef struct OHNativeWindow OHNativeWindow;

/* OH 6.1 NDK (external_window.h), all verified in sysroot: */
extern int32_t OH_NativeWindow_NativeObjectReference(OHNativeWindow *window);
extern int32_t OH_NativeWindow_NativeObjectUnreference(OHNativeWindow *window);
extern int32_t OH_NativeWindow_NativeWindowHandleOpt(OHNativeWindow *window,
                                                     int code, ...);

/* NativeWindowOperation codes (enum order in external_window.h @6.1). */
enum {
    OH_OP_SET_BUFFER_GEOMETRY = 0,
    OH_OP_GET_BUFFER_GEOMETRY = 1,
    OH_OP_GET_FORMAT          = 2,
    OH_OP_SET_FORMAT          = 3,
};

/* NDK ANativeWindow query keys (android/native_window.h, AOSP). */
enum {
    NATIVE_WINDOW_WIDTH  = 0,
    NATIVE_WINDOW_HEIGHT = 1,
    NATIVE_WINDOW_FORMAT = 2,
    NATIVE_WINDOW_IS_VALID = 6,
};

/* AOSP WINDOW_FORMAT_RGBA_8888 == 1; OH GRAPHIC_PIXEL_FMT_RGBA_8888 == 12.
 * Clamp unknown values to RGBA_8888 (mirrors 00.Workspace
 * androidToOHPixelFormat clamping; never pass CLUT through to OH). */
static int32_t android_to_oh_format(int32_t fmt) {
    return (fmt == 1 || fmt == 0) ? 12 : 12;
}

static void get_geometry(OHNativeWindow *oh, int32_t *h, int32_t *w) {
    *h = 0; *w = 0;
    /* 6.1 varargs: [out] int32_t *height, [out] int32_t *width — exactly 2. */
    OH_NativeWindow_NativeWindowHandleOpt(oh, OH_OP_GET_BUFFER_GEOMETRY, h, w);
}

ANativeWindow *ANativeWindow_fromSurface(JNIEnv *env, jobject surface) {
    if (!env || !surface) return 0;
    jclass cls = (*env)->FindClass(env, "android/view/Surface");
    if (!cls) { (*env)->ExceptionClear(env); return 0; }
    jfieldID fid = (*env)->GetFieldID(env, cls, "mNativeObject", "J");
    (*env)->DeleteLocalRef(env, cls);
    if (!fid) { (*env)->ExceptionClear(env); return 0; }
    jlong nativeObj = (*env)->GetLongField(env, surface, fid);
    if (nativeObj == 0) return 0;   /* no BBQ-bound surface yet; caller retries */
    /* mNativeObject holds a real OHNativeWindow*; hand it back unchanged. */
    return (ANativeWindow *)(intptr_t)nativeObj;
}

void ANativeWindow_acquire(ANativeWindow *w) {
    if (w) OH_NativeWindow_NativeObjectReference((OHNativeWindow *)w);
}

void ANativeWindow_release(ANativeWindow *w) {
    if (w) OH_NativeWindow_NativeObjectUnreference((OHNativeWindow *)w);
}

int32_t ANativeWindow_getWidth(ANativeWindow *w) {
    if (!w) return 0;
    int32_t h = 0, width = 0;
    get_geometry((OHNativeWindow *)w, &h, &width);
    return width;
}

int32_t ANativeWindow_getHeight(ANativeWindow *w) {
    if (!w) return 0;
    int32_t h = 0, width = 0;
    get_geometry((OHNativeWindow *)w, &h, &width);
    return h;
}

int32_t ANativeWindow_getFormat(ANativeWindow *w) {
    if (!w) return 0;
    int32_t format = 0;
    OH_NativeWindow_NativeWindowHandleOpt((OHNativeWindow *)w,
                                          OH_OP_GET_FORMAT, &format);
    return format;
}

int32_t ANativeWindow_setBuffersGeometry(ANativeWindow *w, int32_t width,
                                         int32_t height, int32_t format) {
    if (!w) return -1;
    OHNativeWindow *oh = (OHNativeWindow *)w;
    if (width <= 0 || height <= 0) {
        int32_t curH = 0, curW = 0;
        get_geometry(oh, &curH, &curW);
        if (curW <= 0 || curH <= 0) return -1;  /* no live geometry */
        width = curW;
        height = curH;
    }
    /* 6.1 varargs: [in] int32_t width, [in] int32_t height — exactly 2. */
    int32_t rc = OH_NativeWindow_NativeWindowHandleOpt(
        oh, OH_OP_SET_BUFFER_GEOMETRY, width, height);
    if (format > 0) {
        OH_NativeWindow_NativeWindowHandleOpt(
            oh, OH_OP_SET_FORMAT, android_to_oh_format(format));
    }
    return rc;
}

int32_t ANativeWindow_query(const ANativeWindow *w, int32_t what, int32_t *value) {
    if (!value) return -1;
    if (!w) {
        if (what == NATIVE_WINDOW_IS_VALID) { *value = 0; return 0; }
        return -1;
    }
    OHNativeWindow *oh = (OHNativeWindow *)(uintptr_t)w;
    int32_t h = 0, width = 0;
    switch (what) {
    case NATIVE_WINDOW_WIDTH:
        get_geometry(oh, &h, &width);
        *value = width;
        return 0;
    case NATIVE_WINDOW_HEIGHT:
        get_geometry(oh, &h, &width);
        *value = h;
        return 0;
    case NATIVE_WINDOW_FORMAT:
        return OH_NativeWindow_NativeWindowHandleOpt(
            oh, OH_OP_GET_FORMAT, value);
    case NATIVE_WINDOW_IS_VALID:
        *value = 1;
        return 0;
    default:
        return -1;
    }
}
