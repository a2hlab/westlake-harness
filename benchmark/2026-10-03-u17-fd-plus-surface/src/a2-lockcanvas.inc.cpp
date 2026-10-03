// =============================================================================
// [U17 fd-plus] Software Surface.lockCanvas / unlockCanvasAndPost
// A2: pure-Java via JNI upcalls + inner libsurface — ZERO new NEEDED, ZERO new TU.
//
// This is the exact text that apply_a2.py splices into android_graphics_compat_shim.cpp
// (post split.patch), REPLACING the two hard stubs at the Surface JNI block:
//     jlong S_nativeLockCanvas(...) { return 0; }
//     void  S_nativeUnlockCanvasAndPost(...) { }
//
// WHY A2 (evidence, see README "坐实"): our runtime's android.graphics.Canvas native
// (register_android_graphics_Canvas, skia-backed by the hwui port) exposes NO exported
// C++ setBuffer/setBitmap entry (readelf --dyn-syms: absent) and graphics::Canvas lives
// in libhwui, which the runtime does NOT list in NEEDED. So AOSP's native
// graphics::Canvas(env,obj).setBuffer path (A1) would add NEEDED libhwui; OHCanvasRenderer
// (OH_Drawing_*) would add NEEDED libnative_drawing. Both break gate ③ (NEEDED same).
// A2 touches ONLY:
//   (a) inner libsurface (already NEEDED; already supplies NativeWindowHandleOpt +
//       NativeObjectReference as the runtime's only two libsurface UND imports) for the
//       dequeue/queue/buffer-handle — the inner `NativeWindow*` names (NOT the `OH_` NDK
//       names, which live in libnative_window and would add a NEEDED); and
//   (b) JNI upcalls to the REAL registered Java android.graphics.Bitmap / Canvas (skia)
//       for the pixels — pure JNIEnv calls, no link symbol, no NEEDED.
//
// AOSP parity (frameworks/base/core/jni/android_view_Surface.cpp nativeLockCanvas):
// dequeue a buffer -> wrap its pixels in a bitmap -> bind that bitmap to the Java Canvas
// -> return a non-zero token stored as Surface.mLockedObject; unlockSwCanvasAndPost
// throws iff mLockedObject == 0 (Surface.java:507 — fd-plus's U14 first-fatal). We return
// the (non-zero) OHNativeWindow handle. Because our Surface nativeObject is a BARE
// OHNativeWindow* (there is no C++ Surface object to stash the dequeued buffer in — see
// S_nativeGetFromBlastBufferQueue returning b->ohNativeWindow, and ANativeWindow_fromSurface
// casting mNativeObject straight to OHNativeWindow*), the locked buffer is tracked in a
// tiny side-table keyed by that handle. On unlock we copy the bitmap pixels into the
// dequeued buffer (stride-correct) and NativeWindowFlushBuffer -> the AdapterSurfaceView
// child node -> GPU-composited (the window14-proven self-drawing-child path).
//
// v1 board-verify risks (do NOT affect the static ABI gates; flagged for cc-t3's board):
//   - no fence wait: RequestBuffer's release fence is closed, not waited on (possible
//     tearing, never a crash). A libsync wait would add a NEEDED, so deferred.
//   - channel order: Java ARGB_8888 (skia kN32 == RGBA_8888 byte order on little-endian
//     arm64) is assumed to match OH GRAPHIC_PIXEL_FMT_RGBA_8888 (12). If the board's
//     software SurfaceView buffer is BGRA/other, colours swap — a one-line format fix.
//   - dirtyRect ignored: we lock/flush the whole buffer (rectNumber=0). AOSP also writes
//     the clamped locked-rect back into dirtyRect; apps that read it see the full rect.
// -----------------------------------------------------------------------------

// Forward decls for the inner-libsurface buffer path. OHNativeWindow is re-forward-
// declared here (it is only declared ~line 1159, AFTER this block); a repeated
// `struct OHNativeWindow;` is legal. The 3 externs resolve from libsurface (already
// NEEDED): native_window.cpp -> ohos_shared_library("surface"). OHBufferHandle mirrors
// drivers/peripheral/base/buffer_handle.h EXACTLY; OHFlushRegion mirrors
// external_window.h `Region` (passed BY VALUE to NativeWindowFlushBuffer).
struct OHNativeWindow;
struct OHNativeWindowBuffer;  // opaque, pointer-only
typedef struct {
    int32_t fd; int32_t width; int32_t stride; int32_t height;
    int32_t size; int32_t format; uint64_t usage; void* virAddr;
    uint64_t phyAddr; uint32_t reserveFds; uint32_t reserveInts; int32_t reserve[0];
} OHBufferHandleA2;
struct OHFlushRectA2   { int32_t x; int32_t y; uint32_t w; uint32_t h; };
struct OHFlushRegionA2 { OHFlushRectA2* rects; int32_t rectNumber; };
extern "C" int32_t NativeWindowRequestBuffer(OHNativeWindow*, OHNativeWindowBuffer**, int*);
extern "C" int32_t NativeWindowFlushBuffer(OHNativeWindow*, OHNativeWindowBuffer*, int, OHFlushRegionA2);
extern "C" OHBufferHandleA2* GetBufferHandleFromNative(OHNativeWindowBuffer*);

// Tiny lock side-table keyed by the OHNativeWindow handle (our Surface nativeObject).
// Anonymous-namespace (internal linkage) -> no new export. Spinlock via compiler
// atomics so no new #include / no new NEEDED (pthread would also be libc, but this is
// zero-surface). 16 slots >> realistic concurrent software-locked SurfaceViews.
struct SwLockA2 {
    OHNativeWindow* nw; OHNativeWindowBuffer* buf; jobject bmp;
    void* addr; int32_t stride; int32_t w; int32_t h; bool used;
};
static volatile int gSwLockSpin = 0;
static SwLockA2 gSwLocks[16];
static inline void swlock_lock()   { while (__atomic_test_and_set(&gSwLockSpin, __ATOMIC_ACQUIRE)) {} }
static inline void swlock_unlock() { __atomic_clear(&gSwLockSpin, __ATOMIC_RELEASE); }
static SwLockA2* swlock_find(OHNativeWindow* nw) {
    for (int i = 0; i < 16; ++i) if (gSwLocks[i].used && gSwLocks[i].nw == nw) return &gSwLocks[i];
    return nullptr;
}
static SwLockA2* swlock_alloc() {
    for (int i = 0; i < 16; ++i) if (!gSwLocks[i].used) return &gSwLocks[i];
    return nullptr;
}
// Inline sentinel check (is_sentinel_handle is defined later in this TU): a Surface
// whose mNativeObject points at a 0xCAFE5C0X sentinel has no real BBQ-bound buffer.
static inline bool swlock_is_sentinel(jlong h) {
    if (h == 0) return true;
    int32_t m = *reinterpret_cast<int32_t*>(h);
    return (m & 0xFFFFFFF0) == 0xCAFE5C00;
}

jlong S_nativeLockCanvas(JNIEnv* env, jclass, jlong nativeObject, jobject canvas, jobject /*dirtyRect*/) {
    if (swlock_is_sentinel(nativeObject)) {
        ALOGW("[SWLOCK] lockCanvas: sentinel/null nativeObject 0x%{public}llx -> 0 (unbound surface)",
              (long long)nativeObject);
        return 0;  // mLockedObject stays 0 -> AOSP unlockSwCanvasAndPost throws, as before,
                   // only for genuinely unbound surfaces (HelloWorld's old behaviour).
    }
    OHNativeWindow* nw = reinterpret_cast<OHNativeWindow*>(nativeObject);
    OHNativeWindowBuffer* buf = nullptr;
    int fenceFd = -1;
    int32_t rc = NativeWindowRequestBuffer(nw, &buf, &fenceFd);
    if (rc != 0 || !buf) {
        ALOGE("[SWLOCK] RequestBuffer nw=%{public}p rc=%{public}d buf=%{public}p -> 0",
              (void*)nw, rc, (void*)buf);
        return 0;
    }
    if (fenceFd >= 0) close(fenceFd);  // v1: no fence wait (board-verify risk)
    OHBufferHandleA2* bh = GetBufferHandleFromNative(buf);
    OHFlushRegionA2 whole{nullptr, 0};
    if (!bh || !bh->virAddr || bh->width <= 0 || bh->height <= 0) {
        ALOGE("[SWLOCK] bad buffer handle bh=%{public}p virAddr=%{public}p -> flush+0",
              (void*)bh, bh ? bh->virAddr : nullptr);
        NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    // bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)   [JNI upcall, real skia Bitmap]
    jclass bmpCls = env->FindClass("android/graphics/Bitmap");
    jclass cfgCls = env->FindClass("android/graphics/Bitmap$Config");
    if (!bmpCls || !cfgCls) { env->ExceptionClear(); NativeWindowFlushBuffer(nw, buf, -1, whole); return 0; }
    jfieldID argbFid = env->GetStaticFieldID(cfgCls, "ARGB_8888", "Landroid/graphics/Bitmap$Config;");
    jobject argb = argbFid ? env->GetStaticObjectField(cfgCls, argbFid) : nullptr;
    jmethodID createMid = env->GetStaticMethodID(
        bmpCls, "createBitmap", "(IILandroid/graphics/Bitmap$Config;)Landroid/graphics/Bitmap;");
    jobject bmp = (createMid && argb) ? env->CallStaticObjectMethod(bmpCls, createMid, bh->width, bh->height, argb)
                                      : nullptr;
    if (!bmp || env->ExceptionCheck()) {
        env->ExceptionClear();
        ALOGE("[SWLOCK] createBitmap %{public}dx%{public}d failed -> flush+0", bh->width, bh->height);
        NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    // canvas.setBitmap(bmp)  -> the app's draw calls now land on this bitmap   [JNI upcall]
    jclass canCls = env->GetObjectClass(canvas);
    jmethodID setBmpMid = canCls ? env->GetMethodID(canCls, "setBitmap", "(Landroid/graphics/Bitmap;)V") : nullptr;
    if (setBmpMid) env->CallVoidMethod(canvas, setBmpMid, bmp);
    if (env->ExceptionCheck()) env->ExceptionClear();
    // record the lock (keyed by the OHNativeWindow handle; recovered by unlock)
    swlock_lock();
    SwLockA2* s = swlock_find(nw);
    if (!s) s = swlock_alloc();
    if (s) {
        s->used = true; s->nw = nw; s->buf = buf; s->bmp = env->NewGlobalRef(bmp);
        s->addr = bh->virAddr; s->stride = bh->stride; s->w = bh->width; s->h = bh->height;
    }
    swlock_unlock();
    env->DeleteLocalRef(bmp);
    if (!s) {
        ALOGE("[SWLOCK] no free lock slot -> flush+0");
        NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    ALOGI("[SWLOCK] lockCanvas nw=%{public}p %{public}dx%{public}d stride=%{public}d -> mLockedObject=0x%{public}llx",
          (void*)nw, bh->width, bh->height, bh->stride, (long long)nativeObject);
    return nativeObject;  // non-zero -> Surface.mLockedObject != 0 -> unlock will not throw
}

void S_nativeUnlockCanvasAndPost(JNIEnv* env, jclass, jlong nativeObject, jobject canvas) {
    OHNativeWindow* nw = reinterpret_cast<OHNativeWindow*>(nativeObject);
    swlock_lock();
    SwLockA2* s = swlock_find(nw);
    SwLockA2 local{};
    if (s) { local = *s; s->used = false; s->bmp = nullptr; }
    swlock_unlock();
    if (!s) { ALOGW("[SWLOCK] unlock: no lock for nw=%{public}p (noop)", (void*)nw); return; }
    // canvas.setBitmap(null) -> detach the bitmap from the Java Canvas   [JNI upcall]
    jclass canCls = env->GetObjectClass(canvas);
    jmethodID setBmpMid = canCls ? env->GetMethodID(canCls, "setBitmap", "(Landroid/graphics/Bitmap;)V") : nullptr;
    if (setBmpMid) env->CallVoidMethod(canvas, setBmpMid, nullptr);
    if (env->ExceptionCheck()) env->ExceptionClear();
    // copy the bitmap pixels into the dequeued buffer, stride-correct (Bitmap rowBytes = w*4
    // packed; OH buffer stride may be larger for alignment).
    const int32_t rowBytes = local.w * 4;
    void* tmp = malloc((size_t)rowBytes * (size_t)local.h);
    if (tmp && local.bmp) {
        jobject bb = env->NewDirectByteBuffer(tmp, (jlong)rowBytes * (jlong)local.h);
        jclass bmpCls = env->GetObjectClass(local.bmp);
        jmethodID copyMid = bmpCls ? env->GetMethodID(bmpCls, "copyPixelsToBuffer", "(Ljava/nio/Buffer;)V") : nullptr;
        if (bb && copyMid) {
            env->CallVoidMethod(local.bmp, copyMid, bb);
            if (env->ExceptionCheck()) env->ExceptionClear();
            else {
                for (int32_t r = 0; r < local.h; ++r)
                    memcpy((char*)local.addr + (size_t)r * (size_t)local.stride,
                           (char*)tmp       + (size_t)r * (size_t)rowBytes,
                           (size_t)rowBytes);
            }
        }
        if (bb) env->DeleteLocalRef(bb);
    }
    if (tmp) free(tmp);
    if (local.bmp) env->DeleteGlobalRef(local.bmp);
    OHFlushRegionA2 whole{nullptr, 0};  // rectNumber=0 -> flush the whole buffer
    int32_t rc = NativeWindowFlushBuffer(local.nw, local.buf, -1, whole);
    ALOGI("[SWLOCK] unlock nw=%{public}p flush rc=%{public}d", (void*)nw, rc);
}
