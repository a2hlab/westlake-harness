// =============================================================================
// [U17 fd-plus] Software Surface.lockCanvas / unlockCanvasAndPost
// A2: pure-Java via JNI upcalls + inner libsurface. REV2: unwrap the AdapterAnw('ANW1').
//
// This block REPLACES the two hard stubs in android::(anonymous) (so it matches the Surface
// JNI RegisterNatives table). The GLOBAL types/externs it uses (::OHNativeWindow,
// ::oh_anw_get_oh, ::NativeWindowRequestBuffer, ::NativeWindowFlushBuffer,
// ::GetBufferHandleFromNative) are declared at global scope by a2-globals.inc.cpp (spliced
// near the top). We ::-qualify them so lookup never binds to an anon-namespace tag.
//
// REV2 CORRECTION (cc-t3 A0 window18/19, board 98ab67b9e8 + window19 on-screen):
// Surface.mNativeObject is an AdapterAnw wrapper (oh_anativewindow_shim.cpp:
// { ANativeWindow aosp; OHNativeWindow* oh @ +0xc0; uint32_t magic == 'ANW1' 0x414E5731; }),
// NOT a raw OH OHNativeWindow*. oh_window_manager_client.cpp wraps the raw OH window with
// oh_anw_wrap() for BOTH the SurfaceView child path (:1380) and the SurfaceControl path
// (:1589); SurfaceTexture surfaces get a 0xCAFE5C0X sentinel. So ALL usable software
// Surface/SurfaceView mNativeObjects are ANW1 wrappers. Passing the wrapper straight to
// libsurface / OH_NativeWindow_* trips OH's magic check -> rc=40001000 (board-proven).
// We unwrap via the runtime-EXPORTED oh_anw_get_oh (NOT a raw +0xc0 offset): it checks the
// 'ANW1' magic + directPathLive and returns a->oh (the real OH window). cc-t3 window19 lit
// a SurfaceView through exactly this unwrap. Legacy direct-path mNativeObjects (already raw)
// fall through unchanged; sentinels return 0 (as the old stub did for HelloWorld).
//
// WHY A2 (not A1 native graphics::Canvas / not OHCanvasRenderer): both add a new NEEDED
// (libhwui / libnative_drawing) and fail gate ③. A2 uses only already-NEEDED libs
// (libsurface inner API + liboh_adapter_bridge's oh_anw_get_oh) + JNI upcalls to the real
// registered Java Bitmap/Canvas -> zero new NEEDED, zero new object.
// -----------------------------------------------------------------------------
namespace {
struct SwLockA2 {
    jlong key;                    // Surface.mNativeObject (ANW1 wrapper ptr) -- stable lock/unlock key
    ::OHNativeWindow* nw;         // UNWRAPPED real OH window (a->oh) for libsurface
    ::OHNativeWindowBuffer* buf; jobject bmp;
    void* addr; int32_t stride; int32_t w; int32_t h; bool used;
};
static volatile int gSwLockSpin = 0;
static SwLockA2 gSwLocks[16];
static inline void swlock_lock()   { while (__atomic_test_and_set(&gSwLockSpin, __ATOMIC_ACQUIRE)) {} }
static inline void swlock_unlock() { __atomic_clear(&gSwLockSpin, __ATOMIC_RELEASE); }
static SwLockA2* swlock_find(jlong key) {
    for (int i = 0; i < 16; ++i) if (gSwLocks[i].used && gSwLocks[i].key == key) return &gSwLocks[i];
    return nullptr;
}
static SwLockA2* swlock_alloc() {
    for (int i = 0; i < 16; ++i) if (!gSwLocks[i].used) return &gSwLocks[i];
    return nullptr;
}
// Sentinel (0xCAFE5C0X) check -- a Surface with no real BBQ-bound buffer (is_sentinel_handle
// is defined later at global scope, not visible here, so inline the same test).
static inline bool swlock_is_sentinel(jlong h) {
    if (h == 0) return true;
    int32_t m = *reinterpret_cast<int32_t*>(h);
    return (m & 0xFFFFFFF0) == 0xCAFE5C00;
}
// Unwrap the AdapterAnw('ANW1') wrapper -> the real OH window.
// REV3: we CANNOT rely only on the exported oh_anw_get_oh. On the board its build gates on
// directPathLive (oh_anativewindow_shim.cpp: `return a && directPathLive(a) ? a->oh : nullptr`),
// which is FALSE on the software-lockCanvas path -- cc-t3 A0 window19 read oh_anw_get_oh == 0
// for exactly a SurfaceView's ANW1 wrapper. Relying on it alone makes A2 a no-op (RequestBuffer
// rejects the raw ANW1 wrapper -> lockCanvas returns 0 -> "Surface was not locked" persists).
// So: try oh_anw_get_oh first (fast path when the direct path is live, and on ungated builds),
// and if it returns 0, read the wrapper's ->oh field directly after validating the 'ANW1' magic.
// Offsets DOUBLE-CONFIRMED: (a) disasm of oh_anw_get_oh in liboh_adapter_bridge.so --
//   `ldr w8,[x0,#200]`(magic @ +0xc8) cmp 0x414E5731 'ANW1'; `ldr x0,[x0,#192]`(oh @ +0xc0);
// (b) cc-t3 A0 window19 on-board (+0xc0 is the real OH window; GetSurfaceId/SurfaceUtils OK).
// Struct (oh_anativewindow_shim.cpp): AdapterAnw { ANativeWindow aosp (sizeof 0xc0);
//   OHNativeWindow* oh @ +0xc0; uint32_t magic @ +0xc8 == 'ANW1'; ... }. The magic check gates
// the raw read so only a genuine wrapper is dereferenced at +0xc0 (same field oh_anw_get_oh
// returns, minus the directPathLive gate -- window19 proved ->oh is valid for software lock
// even when directPathLive is false). TODO(next-U runtime): export an UNGATED oh_anw_unwrap so
// this raw offset can be dropped (see README).
static inline ::OHNativeWindow* swlock_oh(jlong n) {
    if (!n) return nullptr;
    ::OHNativeWindow* oh = ::oh_anw_get_oh(reinterpret_cast< ::ANativeWindow*>(n));  // exported; directPathLive-gated
    if (oh) return oh;
    unsigned char* p = reinterpret_cast<unsigned char*>(n);
    if (*reinterpret_cast<uint32_t*>(p + 0xc8) == 0x414E5731u /*'ANW1'*/)
        return *reinterpret_cast< ::OHNativeWindow**>(p + 0xc0);   // wrapper ->oh (gate bypassed)
    return reinterpret_cast< ::OHNativeWindow*>(n);  // not a wrapper: legacy raw window
}
}  // namespace

jlong S_nativeLockCanvas(JNIEnv* env, jclass, jlong nativeObject, jobject canvas, jobject /*dirtyRect*/) {
    if (swlock_is_sentinel(nativeObject)) {
        ALOGW("[SWLOCK] lockCanvas: sentinel/null nativeObject 0x%{public}llx -> 0 (unbound surface)",
              (long long)nativeObject);
        return 0;
    }
    ::OHNativeWindow* nw = swlock_oh(nativeObject);   // unwrap ANW1 -> real OH window (board: 40001000 fix)
    ::OHNativeWindowBuffer* buf = nullptr;
    int fenceFd = -1;
    int32_t rc = ::NativeWindowRequestBuffer(nw, &buf, &fenceFd);
    if (rc != 0 || !buf) {
        ALOGE("[SWLOCK] RequestBuffer nativeObj=0x%{public}llx oh=%{public}p rc=%{public}d buf=%{public}p -> 0",
              (long long)nativeObject, (void*)nw, rc, (void*)buf);
        return 0;
    }
    if (fenceFd >= 0) close(fenceFd);  // v1: no fence wait (board-verify risk)
    ::OHBufferHandleA2* bh = ::GetBufferHandleFromNative(buf);
    ::OHFlushRegionA2 whole{nullptr, 0};
    if (!bh || !bh->virAddr || bh->width <= 0 || bh->height <= 0) {
        ALOGE("[SWLOCK] bad buffer handle bh=%{public}p virAddr=%{public}p -> flush+0",
              (void*)bh, bh ? bh->virAddr : nullptr);
        ::NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    // bmp = Bitmap.createBitmap(w, h, Bitmap.Config.ARGB_8888)   [JNI upcall, real skia Bitmap]
    jclass bmpCls = env->FindClass("android/graphics/Bitmap");
    jclass cfgCls = env->FindClass("android/graphics/Bitmap$Config");
    if (!bmpCls || !cfgCls) { env->ExceptionClear(); ::NativeWindowFlushBuffer(nw, buf, -1, whole); return 0; }
    jfieldID argbFid = env->GetStaticFieldID(cfgCls, "ARGB_8888", "Landroid/graphics/Bitmap$Config;");
    jobject argb = argbFid ? env->GetStaticObjectField(cfgCls, argbFid) : nullptr;
    jmethodID createMid = env->GetStaticMethodID(
        bmpCls, "createBitmap", "(IILandroid/graphics/Bitmap$Config;)Landroid/graphics/Bitmap;");
    jobject bmp = (createMid && argb) ? env->CallStaticObjectMethod(bmpCls, createMid, bh->width, bh->height, argb)
                                      : nullptr;
    if (!bmp || env->ExceptionCheck()) {
        env->ExceptionClear();
        ALOGE("[SWLOCK] createBitmap %{public}dx%{public}d failed -> flush+0", bh->width, bh->height);
        ::NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    // canvas.setBitmap(bmp)  -> the app's draw calls now land on this bitmap   [JNI upcall]
    jclass canCls = env->GetObjectClass(canvas);
    jmethodID setBmpMid = canCls ? env->GetMethodID(canCls, "setBitmap", "(Landroid/graphics/Bitmap;)V") : nullptr;
    if (setBmpMid) env->CallVoidMethod(canvas, setBmpMid, bmp);
    if (env->ExceptionCheck()) env->ExceptionClear();
    // record the lock (keyed by the ORIGINAL nativeObject; both lock & unlock receive it)
    swlock_lock();
    SwLockA2* s = swlock_find(nativeObject);
    if (!s) s = swlock_alloc();
    if (s) {
        s->used = true; s->key = nativeObject; s->nw = nw; s->buf = buf; s->bmp = env->NewGlobalRef(bmp);
        s->addr = bh->virAddr; s->stride = bh->stride; s->w = bh->width; s->h = bh->height;
    }
    swlock_unlock();
    env->DeleteLocalRef(bmp);
    if (!s) {
        ALOGE("[SWLOCK] no free lock slot -> flush+0");
        ::NativeWindowFlushBuffer(nw, buf, -1, whole);
        return 0;
    }
    ALOGI("[SWLOCK] lockCanvas nativeObj=0x%{public}llx oh=%{public}p %{public}dx%{public}d stride=%{public}d -> mLockedObject",
          (long long)nativeObject, (void*)nw, bh->width, bh->height, bh->stride);
    return nativeObject;  // non-zero -> Surface.mLockedObject != 0 -> unlock will not throw
}

void S_nativeUnlockCanvasAndPost(JNIEnv* env, jclass, jlong nativeObject, jobject canvas) {
    swlock_lock();
    SwLockA2* s = swlock_find(nativeObject);
    SwLockA2 local{};
    if (s) { local = *s; s->used = false; s->bmp = nullptr; }
    swlock_unlock();
    if (!s) { ALOGW("[SWLOCK] unlock: no lock for nativeObj=0x%{public}llx (noop)", (long long)nativeObject); return; }
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
    ::OHFlushRegionA2 whole{nullptr, 0};  // rectNumber=0 -> flush the whole buffer
    int32_t rc = ::NativeWindowFlushBuffer(local.nw, local.buf, -1, whole);
    ALOGI("[SWLOCK] unlock nativeObj=0x%{public}llx oh=%{public}p flush rc=%{public}d",
          (long long)nativeObject, (void*)local.nw, rc);
}
