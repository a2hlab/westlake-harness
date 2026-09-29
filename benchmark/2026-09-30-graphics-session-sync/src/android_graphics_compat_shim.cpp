// ============================================================================
// android_graphics_compat_shim.cpp
//
// Last-wins JNI override shim for graphics native methods that either
//   (a) abort with "fid == null" / "mid == null" CheckJNI errors because
//       libhwui's register_X caches a JField/Method ID at register time
//       and the lookup silently failed (often when the AOSP class layout
//       differs from our framework.jar mainline version), or
//   (b) live in AOSP libandroid_runtime.so (which we don't cross-compile)
//       and would otherwise UnsatisfiedLinkError at first call.
//
// Spec: doc/graphics_jni_inventory.html §4.1
// Related: doc/window_manager_ipc_adapter_design.html §3.2 (SurfaceControl
//          equivalent path for Surface/BLASTBufferQueue)
//
// Strategy: explicit RegisterNatives for each problem method.  In ART, when
// liboh_android_runtime's register_X runs after libhwui's RegisterNatives,
// last-wins applies — our stub replaces libhwui's broken impl.  All overrides
// here are SAFE no-op or null returns; they don't render anything but they
// stop the abort/crash so HelloWorld setContentView/onResume can progress
// to the next-layer issue (which we then diagnose via the §3.7/§3.8 stderr
// + FATAL bridges).
//
// Each method below documents:
//   - Which class/method on Java side
//   - Why the "real" hwui/libgui impl can't run on OH
//   - What a real adapter implementation would do (P1 future work)
// ============================================================================

#include "AndroidRuntime.h"

#include <jni.h>
#include <cstring>  // 2026-05-02 G2.14r: std::strncpy / std::strcpy in BBQ alloc
#include <cstdlib>  // getenv for explicit runtime diagnostics
#include <cstdint>  // uint64_t NativeWindow usage bits
#include <cstdio>   // [STAGE2-UNITY] fprintf(stderr) render checkpoints
#include <unistd.h> // [STAGE2-UNITY] usleep for eglCreateWindowSurface retry
// [WALL2-FMT 2026-06-29] AOSP EGL_NATIVE_VISUAL_ID pixel formats (RGBA_8888=1)
// must be translated to OH GraphicPixelFormat (RGBA_8888=12) before they reach
// OH_OP_SET_FORMAT — OH format 1 = CLUT (garbage) → gralloc rejects. Single
// source of truth = the existing surface/jni mapper (build adds its -I path).
#include "pixel_format_mapper.h"

extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...)
    __attribute__((__format__(printf, 5, 6)));
#define ALOGI(...) HiLogPrint(3, 4, 0xD000F00u, "OH_GfxShim", __VA_ARGS__)
#define ALOGW(...) HiLogPrint(3, 5, 0xD000F00u, "OH_GfxShim", __VA_ARGS__)
#define ALOGE(...) HiLogPrint(3, 6, 0xD000F00u, "OH_GfxShim", __VA_ARGS__)

// [STAGE2-UNITY 2026-06-28] Weak no-op fallbacks for the SQLite JNI register
// group that 2026-06-28 added to AndroidRuntime.cpp's gRegJNI table. The
// unity/render runtime build (compile_runtime_local.sh) does NOT compile
// android_database_SQLite*.cpp (no libsqlite), so without these the table's
// references are UNDEFINED imports → child [JNI-REG-CHILD] dlopen relocation
// "symbol not found" SIGSEGV (regressed the render runtime). Declared weak so
// the REAL impls (noice build, which compiles the SQLite .cpp) override; for
// Unity/eglprobe (no Android SQLite) the no-op is harmless.
namespace android {
__attribute__((weak)) int register_android_database_SQLiteConnection(JNIEnv*) { return 0; }
__attribute__((weak)) int register_android_database_SQLiteGlobal(JNIEnv*)     { return 0; }
__attribute__((weak)) int register_android_database_SQLiteDebug(JNIEnv*)      { return 0; }
__attribute__((weak)) int register_android_database_CursorWindow(JNIEnv*)     { return 0; }
}  // namespace android

namespace android {
namespace {

// =====================================================================
// android.graphics.ImageDecoder
// =====================================================================
// G2.4 (2026-04-30): nGetColorSpace's libhwui impl caches gColorSpace
// jfieldID via GetStaticFieldID at register time.  When that fails (class
// layout mismatch on our framework.jar), the cached fid stays null;
// subsequent GetStaticObjectField(env, ..., null) trips CheckJNI abort.
// Override: return null so caller's getColorSpace() returns null.  No
// Android UI path I know of strict-requires non-null ColorSpace; sRGB
// is assumed when null.
jobject ID_nGetColorSpace(JNIEnv*, jclass, jlong /*nativePtr*/) {
    return nullptr;
}

// G2.4 (2026-04-30 follow-up): nGetPadding hits same fid/jclass cache
// problem as nGetColorSpace.  libhwui calls IsInstanceOf on a cached
// gNinePatchInsetsClass that's null → CheckJNI abort.  Override: leave
// outRect at default (0,0,0,0) — Android Rect default-init is empty.
void ID_nGetPadding(JNIEnv*, jclass, jlong /*nativePtr*/, jobject /*outRect*/) { }

// Stub the remaining ImageDecoder natives to avoid future surprises if
// libhwui's register caches more null IDs.  HelloWorld doesn't decode any
// images so these stubs only fire if some unexpected path hits them.
jobject ID_nCreateAsset(JNIEnv*, jclass, jlong, jboolean, jobject) { return nullptr; }
jobject ID_nCreateByteBuffer(JNIEnv*, jclass, jobject, jint, jint, jboolean, jobject) {
    return nullptr;
}
jobject ID_nCreateByteArray(JNIEnv*, jclass, jbyteArray, jint, jint, jboolean, jobject) {
    return nullptr;
}
jobject ID_nCreateInputStream(JNIEnv*, jclass, jobject, jbyteArray, jboolean, jobject) {
    return nullptr;
}
jobject ID_nCreateFd(JNIEnv*, jclass, jobject, jlong, jboolean, jobject) { return nullptr; }
jobject ID_nDecodeBitmap(JNIEnv*, jclass, jlong, jobject, jboolean, jint, jint,
                         jobject, jboolean, jint, jobject, jboolean, jboolean,
                         jlong, jboolean) {
    return nullptr;
}
jobject ID_nGetSampledSize(JNIEnv*, jclass, jlong, jint) { return nullptr; }
void ID_nClose(JNIEnv*, jclass, jlong /*nativePtr*/) { }
jstring ID_nGetMimeType(JNIEnv* env, jclass, jlong) { return env->NewStringUTF("image/unknown"); }

const JNINativeMethod kImageDecoderMethods[] = {
    { "nGetColorSpace", "(J)Landroid/graphics/ColorSpace;",
      reinterpret_cast<void*>(ID_nGetColorSpace) },
    { "nGetPadding", "(JLandroid/graphics/Rect;)V",
      reinterpret_cast<void*>(ID_nGetPadding) },
    { "nClose", "(J)V",
      reinterpret_cast<void*>(ID_nClose) },
    { "nGetMimeType", "(J)Ljava/lang/String;",
      reinterpret_cast<void*>(ID_nGetMimeType) },
    { "nGetSampledSize", "(JI)Landroid/util/Size;",
      reinterpret_cast<void*>(ID_nGetSampledSize) },
    // nCreate / nDecodeBitmap variants left unbound — if the AOSP overload
    // signature differs subtly, RegisterNatives fails this method only
    // (we register one-by-one) and the rest still bind.
};

// =====================================================================
// android.view.Surface (subset — most-frequently called by ViewRootImpl)
// =====================================================================
// AOSP register_android_view_Surface lives in libandroid_runtime.so which
// we don't cross-compile.  Without RegisterNatives, first call → JNI auto
// resolution by symbol name; if our adapter doesn't export Java_android_view_Surface_*
// → UnsatisfiedLinkError.  Provide a minimum-viable stub set.

// 2026-05-08 G2.14ae: forward decls + types for the SC→sessionId→OHNativeWindow
// chain reused by Surface stubs (below) and BLASTBufferQueue (next section).
// We are already inside `namespace android { namespace { ... } }`, so these
// land in the same anonymous namespace as the definitions in the BBQ block.
extern "C" int32_t oh_sc_get_session(jlong scNativeObject);
static void*   oh_wm_get_native_window(int32_t sessionId);

// OhBlastBufferQueue moved up here (was in BBQ section ~line 299) so Surface
// stubs below can use as_bbq() / b->ohNativeWindow when bridging
// nativeGetFromBlastBufferQueue. Definition, alloc_bbq, as_bbq are now here;
// the BBQ section keeps using them, just defined earlier in the same TU.
struct OhBlastBufferQueue {
    int32_t magic;
    char name[64];
    int32_t width;
    int32_t height;
    int32_t format;
    void* ohNativeWindow;   // resolved by BBQ_nativeUpdate
    int32_t sessionId;      // resolved from SurfaceControl during nativeUpdate
};
constexpr int32_t kOhBbqMagic = 0x4F484251;  // 'OHBQ'

static OhBlastBufferQueue* as_bbq(jlong p) {
    auto* b = reinterpret_cast<OhBlastBufferQueue*>(p);
    if (!b || b->magic != kOhBbqMagic) return nullptr;
    return b;
}

// Resolve a SurfaceControl* to a real OHNativeWindow* (the same handle BBQ
// stamps into Java Surface.mNativeObject). Only the SC's own session is
// accepted. An unresolved owner returns 0 —
// hwui's ANativeWindow_fromSurface treats that as "no surface, retry".
static jlong sc_to_oh_native_window(jlong surfaceControl) {
    int32_t scSessionId = surfaceControl ? oh_sc_get_session(surfaceControl) : 0;
    int32_t sessionId = scSessionId;
    int32_t lastSessionId = 0;
    if (sessionId == 0) {
        ALOGW("[DEBUG] sc_to_oh_native_window: sc=0x%llx scSessionId=0 lastSessionId=0 -> 0",
              (long long)surfaceControl);
        return 0;
    }
    void* nw = oh_wm_get_native_window(sessionId);
    if (!nw) {
        ALOGW("[DEBUG] sc_to_oh_native_window: sc=0x%llx scSessionId=%d lastSessionId=%d sessionId=%d "
              "oh_wm_get_native_window returned nullptr -> 0",
              (long long)surfaceControl, scSessionId, lastSessionId, sessionId);
        return 0;
    }
    ALOGI("[DEBUG] sc_to_oh_native_window: sc=0x%llx scSessionId=%d lastSessionId=%d sessionId=%d -> nw=%p",
          (long long)surfaceControl, scSessionId, lastSessionId, sessionId, nw);
    return reinterpret_cast<jlong>(nw);
}

jlong S_nativeCreateFromSurfaceTexture(JNIEnv*, jclass, jobject /*surfaceTexture*/) {
    // Real impl: take the SurfaceTexture's IGraphicBufferProducer and wrap in
    // an OH NativeWindow.  HelloWorld doesn't use SurfaceTexture; return 0.
    return 0;
}
jlong S_nativeCreateFromSurfaceControl(JNIEnv*, jclass, jlong surfaceControl) {
    // 2026-05-08 G2.14ae: real bridge — was returning 0xCAFE5C01 sentinel,
    // which leaked through to hwui's ANativeWindow_fromSurface and made it
    // return null → hwuiTask0 deref crash. Now resolve the OHNativeWindow
    // via the same SC→sessionId→getOhNativeWindow chain BBQ uses.
    jlong nw = sc_to_oh_native_window(surfaceControl);
    ALOGI("S_nativeCreateFromSurfaceControl(sc=0x%llx) -> ohNativeWindow=0x%llx",
          (long long)surfaceControl, (long long)nw);
    return nw;  // 0 if unresolved — caller retries
}
jlong S_nativeCreateFromSurfaceControlNew(JNIEnv*, jclass,
                                          jlong surfaceControl, jlong /*nativeOldSurface*/) {
    return S_nativeCreateFromSurfaceControl(nullptr, nullptr, surfaceControl);
}
void S_nativeRelease(JNIEnv*, jclass, jlong /*nativeObject*/) { }
jboolean S_nativeIsValid(JNIEnv*, jclass, jlong nativeObject) {
    return nativeObject != 0 ? JNI_TRUE : JNI_FALSE;
}
jboolean S_nativeIsConsumerRunningBehind(JNIEnv*, jclass, jlong /*nativeObject*/) {
    return JNI_FALSE;
}
jlong S_nativeReadFromParcel(JNIEnv*, jclass, jlong nativeObject, jobject /*parcel*/) {
    return nativeObject;
}
void S_nativeWriteToParcel(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*parcel*/) { }
jlong S_nativeLockCanvas(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/, jobject /*dirtyRect*/) {
    // Without a real surface buffer to lock, lockCanvas can't return a real
    // canvas.  HelloWorld doesn't use Surface.lockCanvas (hwui owns drawing).
    return 0;
}
void S_nativeUnlockCanvasAndPost(JNIEnv*, jclass, jlong /*nativeObject*/, jobject /*canvas*/) { }
void S_nativeAllocateBuffers(JNIEnv*, jclass, jlong /*nativeObject*/) { }
jint S_nativeGetWidth(JNIEnv*, jclass, jlong /*nativeObject*/) { return 720; }
jint S_nativeGetHeight(JNIEnv*, jclass, jlong /*nativeObject*/) { return 1280; }
// 2026-05-01 G2.14n: AOSP Surface.java declares these as `int` returns; we were
// registering with `(...)V` signatures and void-returning impls.  RegisterNatives
// in ART silently accepts mismatched signatures; Java callers then read garbage
// register r0 as the int return value → unpredictable behavior downstream.
jint S_nativeAttachAndQueueBufferWithColorSpace(JNIEnv*, jclass, jlong, jobject, jint) { return 0; }
jint S_nativeForceScopedDisconnect(JNIEnv*, jclass, jlong) { return 0; }
jint S_nativeSetFrameRate(JNIEnv*, jclass, jlong, jfloat, jint, jint) { return 0; }

// G2.14v r2 (2026-05-07) — Surface 9 missing fn 补全（同 SurfaceControl A/B/C 范式）。
// AOSP 14 共 22 native，原表 13 项，缺 9（含触发 G2.14v r1 部署后下一层 ULE 的
// nativeGetFromSurfaceControl）。
//
// 本类全 stub，因 OH 没有 Android Surface 等价物（OH 的 ProducerSurface 由
// RSSurfaceNode 持有、走 OHNativeWindow 路径，不通过 Surface JNI 桥）。
// 真渲染走 BLASTBufferQueue 路径（compat_shim §BBQ）；这里只确保 Java 端
// Surface.copyFrom / Surface.release 等不再 ULE。

// nativeGetFromSurfaceControl(currSurface, sc) → long
// AOSP: 把 Surface 对接到 SurfaceControl 的 BufferQueue 上，返回新 mNativeObject。
// 2026-05-08 G2.14ae: real bridge via SC→sessionId→OHNativeWindow chain
// (was returning 0xCAFE5C02 sentinel; same crash mode as nativeCreateFromSurfaceControl).
jlong S_nativeGetFromSurfaceControl(JNIEnv*, jclass, jlong /*nativeObject*/, jlong surfaceControl) {
    jlong nw = sc_to_oh_native_window(surfaceControl);
    ALOGI("S_nativeGetFromSurfaceControl(sc=0x%llx) -> ohNativeWindow=0x%llx",
          (long long)surfaceControl, (long long)nw);
    return nw;
}
// nativeGetFromBlastBufferQueue(currSurface, bbq) → long
// 2026-05-08 G2.14ae: real bridge — was returning the raw BBQ struct ptr as
// if it were ANativeWindow*, which hwui then dereferenced as OHNativeWindow
// (different layout) → crash. Now extract b->ohNativeWindow set by
// BBQ_nativeUpdate. If BBQ.update has not yet run, fall back to the
// explicit BBQ session; an unbound BBQ stays unresolved.
jlong S_nativeGetFromBlastBufferQueue(JNIEnv*, jclass, jlong /*nativeObject*/, jlong blastBufferQueue) {
    auto* b = as_bbq(blastBufferQueue);
    if (b && b->ohNativeWindow) {
        ALOGI("S_nativeGetFromBlastBufferQueue(bbq=0x%llx sessionId=%d) -> ohNativeWindow=%p",
              (long long)blastBufferQueue, b->sessionId, b->ohNativeWindow);
        return reinterpret_cast<jlong>(b->ohNativeWindow);
    }
    ALOGW("S_nativeGetFromBlastBufferQueue(bbq=0x%llx): unresolved -> 0",
          (long long)blastBufferQueue);
    return 0;
}
void S_nativeDestroy(JNIEnv*, jclass, jlong /*nativeObject*/) { /* no-op; OH RS 自管 */ }
jlong S_nativeGetNextFrameNumber(JNIEnv*, jclass, jlong /*nativeObject*/) { return 0; }
jint S_nativeSetAutoRefreshEnabled(JNIEnv*, jclass, jlong /*nativeObject*/, jboolean /*enabled*/) { return 0; }
jint S_nativeSetScalingMode(JNIEnv*, jclass, jlong /*nativeObject*/, jint /*mode*/) { return 0; }
jint S_nativeSetSharedBufferModeEnabled(JNIEnv*, jclass, jlong /*nativeObject*/, jboolean /*enabled*/) { return 0; }

const JNINativeMethod kSurfaceMethods[] = {
    { "nativeCreateFromSurfaceTexture", "(Landroid/graphics/SurfaceTexture;)J",
      reinterpret_cast<void*>(S_nativeCreateFromSurfaceTexture) },
    { "nativeCreateFromSurfaceControl", "(J)J",
      reinterpret_cast<void*>(S_nativeCreateFromSurfaceControl) },
    { "nativeGetFromSurfaceControl", "(JJ)J",
      reinterpret_cast<void*>(S_nativeGetFromSurfaceControl) },
    { "nativeGetFromBlastBufferQueue", "(JJ)J",
      reinterpret_cast<void*>(S_nativeGetFromBlastBufferQueue) },
    { "nativeRelease", "(J)V", reinterpret_cast<void*>(S_nativeRelease) },
    { "nativeDestroy", "(J)V", reinterpret_cast<void*>(S_nativeDestroy) },
    { "nativeIsValid", "(J)Z", reinterpret_cast<void*>(S_nativeIsValid) },
    { "nativeIsConsumerRunningBehind", "(J)Z",
      reinterpret_cast<void*>(S_nativeIsConsumerRunningBehind) },
    { "nativeReadFromParcel", "(JLandroid/os/Parcel;)J",
      reinterpret_cast<void*>(S_nativeReadFromParcel) },
    { "nativeWriteToParcel", "(JLandroid/os/Parcel;)V",
      reinterpret_cast<void*>(S_nativeWriteToParcel) },
    { "nativeLockCanvas", "(JLandroid/graphics/Canvas;Landroid/graphics/Rect;)J",
      reinterpret_cast<void*>(S_nativeLockCanvas) },
    { "nativeUnlockCanvasAndPost", "(JLandroid/graphics/Canvas;)V",
      reinterpret_cast<void*>(S_nativeUnlockCanvasAndPost) },
    { "nativeAllocateBuffers", "(J)V",
      reinterpret_cast<void*>(S_nativeAllocateBuffers) },
    { "nativeGetWidth", "(J)I", reinterpret_cast<void*>(S_nativeGetWidth) },
    { "nativeGetHeight", "(J)I", reinterpret_cast<void*>(S_nativeGetHeight) },
    { "nativeGetNextFrameNumber", "(J)J",
      reinterpret_cast<void*>(S_nativeGetNextFrameNumber) },
    { "nativeForceScopedDisconnect", "(J)I",
      reinterpret_cast<void*>(S_nativeForceScopedDisconnect) },
    { "nativeSetFrameRate", "(JFII)I",
      reinterpret_cast<void*>(S_nativeSetFrameRate) },
    { "nativeAttachAndQueueBufferWithColorSpace",
      "(JLandroid/hardware/HardwareBuffer;I)I",
      reinterpret_cast<void*>(S_nativeAttachAndQueueBufferWithColorSpace) },
    { "nativeSetAutoRefreshEnabled", "(JZ)I",
      reinterpret_cast<void*>(S_nativeSetAutoRefreshEnabled) },
    { "nativeSetScalingMode", "(JI)I",
      reinterpret_cast<void*>(S_nativeSetScalingMode) },
    { "nativeSetSharedBufferModeEnabled", "(JZ)I",
      reinterpret_cast<void*>(S_nativeSetSharedBufferModeEnabled) },
};

// =====================================================================
// android.graphics.BLASTBufferQueue
// =====================================================================
// AOSP register_android_graphics_BLASTBufferQueue lives in libandroid_runtime.
// Used by hwui's HardwareRenderer to submit frames.
//
// 2026-05-02 G2.14r — UPGRADED FROM PURE STUB to real OH wire-up.
//   Pre-G2.14r: BBQ_nativeCreate returned a fake sentinel int*; nativeGetSurface
//   returned nullptr; ViewRoot.mSurface stayed empty (mNativeObject=0); hwui's
//   eglCreateWindowSurface(NULL) → LOG_ALWAYS_FATAL → abort 12ms after
//   activityResumed.  Now we allocate a real OhBlastBufferQueue struct, read
//   the WSAdapter session ID from the SurfaceControl in nativeUpdate, and
//   resolve it to an OHNativeWindow* via OHWindowManagerClient.getOhNativeWindow.
//   nativeGetSurface returns a real Java Surface whose mNativeObject points to
//   the OHNativeWindow — hwui's eglCreateWindowSurface accepts it directly.
//
// Forward-declared C exports from sibling translation units:
//   android_view_SurfaceControl.cpp::oh_sc_get_session(jlong sc) → int32_t
//   oh_window_manager_client.cpp::getOhNativeWindow(int32_t) → void*
extern "C" int32_t oh_sc_get_session(jlong scNativeObject);
namespace oh_adapter {
class OHWindowManagerClient;
}

// 2026-05-08 G2.14ae: OhBlastBufferQueue / kOhBbqMagic / as_bbq moved up to
// line ~110 so Surface section (above) can also use them. Only alloc_bbq
// remains here (only used by BBQ_nativeCreate just below).
static OhBlastBufferQueue* alloc_bbq(const char* nameUtf) {
    auto* b = new OhBlastBufferQueue();
    b->magic = kOhBbqMagic;
    b->width = 0; b->height = 0; b->format = 1;
    b->ohNativeWindow = nullptr;
    b->sessionId = 0;
    if (nameUtf) {
        std::strncpy(b->name, nameUtf, sizeof(b->name) - 1);
        b->name[sizeof(b->name) - 1] = 0;
    } else {
        std::strcpy(b->name, "OhBBQ");
    }
    return b;
}

jlong BBQ_nativeCreate(JNIEnv* env, jclass, jstring jname, jboolean /*updateDestinationFrame*/) {
    const char* nameUtf = jname ? env->GetStringUTFChars(jname, nullptr) : nullptr;
    OhBlastBufferQueue* b = alloc_bbq(nameUtf);
    if (jname && nameUtf) env->ReleaseStringUTFChars(jname, nameUtf);
    ALOGI("BBQ.create name=%s ptr=%p", b->name, b);
    fprintf(stderr, "[BBQ-CP] nativeCreate name=%s ptr=%p\n", b->name ? b->name : "(null)", b); fflush(stderr);
    return reinterpret_cast<jlong>(b);
}

void BBQ_nativeDestroy(JNIEnv*, jclass, jlong ptr) {
    auto* b = as_bbq(ptr);
    if (b) {
        b->magic = 0;
        // ohNativeWindow is owned by surface_utils via RSSurfaceNode lifecycle
        // (see oh_window_manager_client.cpp::getOhNativeWindow).  We don't
        // free it here — the RSSurfaceNode in OHWindowManagerClient holds the
        // strong ref; destroy on session teardown.
        delete b;
    }
}

// Forward declaration so we can reference getOhNativeWindow without pulling
// the entire oh_window_manager_client header chain into compat_shim.
//
// 2026-05-02 G2.14r: these two symbols live in liboh_adapter_bridge.so but
// are referenced from liboh_android_runtime.so (this file).  Cross-.so
// link-time linkage is not declared (bridge.so is loaded later by JNI_OnLoad
// on adapter side), so resolve dynamically via dlsym to avoid "symbol not
// found" at dlopen of liboh_android_runtime.so.  Cached after first lookup.
#include <dlfcn.h>
typedef void* (*oh_wm_get_native_window_fn_t)(int32_t);
// 2026-06-28 [STAGE2-SURFACEVIEW]: child SurfaceView surface composition.
typedef void* (*oh_rs_get_child_surface_window_fn_t)(int32_t, int64_t, int32_t, int32_t);
static oh_wm_get_native_window_fn_t g_oh_wm_get_native_window_fn = nullptr;
static oh_rs_get_child_surface_window_fn_t g_oh_rs_get_child_surface_window_fn = nullptr;
static void resolve_oh_wm_funcs() {
    static bool s_logged = false;
    if (g_oh_wm_get_native_window_fn &&
        g_oh_rs_get_child_surface_window_fn) return;

    // 2026-05-09 G2.14ac: previous code used dlsym(RTLD_DEFAULT, ...) which on
    // OH only searches the caller's linker namespace and the main executable
    // (appspawn-x). The target symbols live in liboh_adapter_bridge.so which
    // lives in a different namespace, so RTLD_DEFAULT misses them — dlerror
    // confirmed: "Symbol not found ... so=/system/bin/appspawn-x".
    //
    // The runtime has an exact DT_NEEDED edge to liboh_adapter_bridge.so.
    // Resolve only that already-loaded object. A fresh-by-name/absolute-path
    // fallback can create a second namespace instance and split the window
    // session state, so a NOLOAD miss is a hard boundary failure.
    static void* s_bridgeHandle = nullptr;
    if (!s_bridgeHandle) {
        s_bridgeHandle = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);
        if (s_bridgeHandle) {
            ALOGI("[DEBUG] resolve_oh_wm_funcs: exact loaded bridge handle=%p",
                  s_bridgeHandle);
        } else {
            const char* err = dlerror();
            ALOGE("[DEBUG] resolve_oh_wm_funcs: required loaded bridge absent dlerror='%s'",
                  err ? err : "(null)");
            return;
        }
    }

    if (!g_oh_wm_get_native_window_fn) {
        g_oh_wm_get_native_window_fn = reinterpret_cast<oh_wm_get_native_window_fn_t>(
            dlsym(s_bridgeHandle, "oh_wm_get_native_window"));
    }
    if (!g_oh_rs_get_child_surface_window_fn) {
        g_oh_rs_get_child_surface_window_fn = reinterpret_cast<oh_rs_get_child_surface_window_fn_t>(
            dlsym(s_bridgeHandle, "oh_rs_get_child_surface_window"));
    }
    if (!s_logged) {
        const char* err = dlerror();
        ALOGI("[DEBUG] resolve_oh_wm_funcs: get_native_window_fn=%p dlerror='%s'",
              (void*)g_oh_wm_get_native_window_fn,
              err ? err : "(null)");
        if (g_oh_wm_get_native_window_fn) {
            s_logged = true;
        }
    }
}
static void* oh_wm_get_native_window(int32_t sessionId) {
    resolve_oh_wm_funcs();
    return g_oh_wm_get_native_window_fn ? g_oh_wm_get_native_window_fn(sessionId) : nullptr;
}
// 2026-06-28 [STAGE2-SURFACEVIEW]: resolve a dedicated, RS-composited child
// surface for a SurfaceView (so its EGL producer has a live consumer instead of
// colliding with the main window's APP_WINDOW_NODE producer). See
// oh_window_manager_client.cpp::oh_rs_get_child_surface_window.
static void* oh_rs_get_child_surface_window(int32_t sessionId, int64_t childKey,
                                            int32_t w, int32_t h) {
    resolve_oh_wm_funcs();
    return g_oh_rs_get_child_surface_window_fn
        ? g_oh_rs_get_child_surface_window_fn(sessionId, childKey, w, h) : nullptr;
}

// [S23 cut5] fwd decl (definition ~line 1090); poke geometry on the exact nw
// instance stamped into b->ohNativeWindow at resolve/stamp time (belt) — the
// STAGE0 handoff (suspenders) covers the cached/pre-resolved case.
extern "C" void nwfs_seed_window_geometry(void* nw, const char* where);

// [STAGE2-UNITY 2026-06-28] Signature aligned to THIS framework.jar's
// BLASTBufferQueue.java: nativeUpdate(long ptr, long sc, long width,
// long height, int format) = (JJJJI)V. Prior shim used (JJJIIIJ)V (7-arg,
// different framework gen) → RegisterNatives silently failed → SurfaceView
// (eglprobe / UnityPlayerActivity) hit UnsatisfiedLinkError on first traversal.
void BBQ_nativeUpdate(JNIEnv*, jclass, jlong bbqPtr, jlong scPtr,
                      jlong width, jlong height, jint format) {
    fprintf(stderr, "[BBQ-CP] nativeUpdate ENTER bbq=0x%llx sc=0x%llx %lldx%lld fmt=%d\n",
            (long long)bbqPtr, (long long)scPtr, (long long)width, (long long)height, format); fflush(stderr);
    auto* b = as_bbq(bbqPtr);
    if (!b) {
        ALOGW("BBQ.update: invalid bbqPtr=%lld", (long long)bbqPtr);
        return;
    }
    b->width = static_cast<int32_t>(width);
    b->height = static_cast<int32_t>(height);
    b->format = format;
    int32_t sessionId = oh_sc_get_session(scPtr);
    if (b->sessionId != sessionId) b->ohNativeWindow = nullptr;
    b->sessionId = sessionId;
    if (sessionId == 0) {
        ALOGW("BBQ.update: no sessionId resolvable (no explicit SC owner); "
              "render will use empty Surface");
        return;
    }
    // 2026-06-28 [STAGE2-SURFACEVIEW]: route SurfaceView BBQs to a dedicated
    // RS-composited child surface node; keep the main window (ViewRootImpl) BBQ
    // on the APP_WINDOW_NODE producer.  AOSP names the SurfaceView's BBQ
    // "SurfaceView[<title>]" (SurfaceView.java:1055/1160) vs the main window's
    // "ViewRootImpl[<title>]" (ViewRootImpl.java mTag) — name disambiguates.
    // Without a dedicated child node the SurfaceView's EGL collides with the
    // main producer -> eglCreateWindowSurface EGL_BAD_ALLOC (§12-13).
    bool isSurfaceView = (std::strstr(b->name, "SurfaceView") != nullptr);
    void* nw = nullptr;
    if (isSurfaceView) {
        nw = oh_rs_get_child_surface_window(sessionId, bbqPtr,
                                            static_cast<int32_t>(width),
                                            static_cast<int32_t>(height));
        if (!nw) {
            ALOGW("BBQ.update: child surface window null for SurfaceView '%s' "
                  "session=%d; falling back to main producer", b->name, sessionId);
            nw = oh_wm_get_native_window(sessionId);
        } else {
            ALOGI("BBQ.update: SurfaceView '%s' -> dedicated child surface anw=%p",
                  b->name, nw);
            fprintf(stderr, "[BBQ-CP] nativeUpdate SurfaceView '%s' -> child anw=%p\n",
                    b->name, nw); fflush(stderr);
        }
    } else {
        // Resolve sessionId → OHNativeWindow*.  Cached per-session in
        // OHWindowManagerClient so repeated update() calls get the same pointer.
        nw = oh_wm_get_native_window(sessionId);
    }
    if (!nw) {
        ALOGW("BBQ.update: getOhNativeWindow(sessionId=%d) returned null", sessionId);
        return;
    }
    b->ohNativeWindow = nw;
    nwfs_seed_window_geometry(nw, "BBQ.update-stamp");  // [S23 cut5 belt]
    ALOGI("BBQ.update: sessionId=%d → OHNativeWindow=%p (%dx%d fmt=%d)",
          sessionId, nw, (int)width, (int)height, format);
    fprintf(stderr, "[BBQ-CP] nativeUpdate RESOLVED sessionId=%d OHNativeWindow=%p (%lldx%lld)\n",
            sessionId, nw, (long long)width, (long long)height); fflush(stderr);
}

// Forward declaration: AOSP exposes a JNI helper to construct a Java Surface
// from a native ANativeWindow*.  See frameworks/base/core/jni/android_view_Surface.cpp.
// On OH our OHNativeWindow* is pin-compatible with ANativeWindow*.
extern "C" jobject android_view_Surface_createFromIGraphicBufferProducer(
        JNIEnv* env, void* /*producer*/) __attribute__((weak));

jobject BBQ_nativeGetSurface(JNIEnv* env, jclass, jlong bbqPtr,
                              jboolean /*includeSurfaceControlHandle*/) {
    auto* b = as_bbq(bbqPtr);
    if (!b) {
        ALOGW("BBQ.getSurface: invalid bbqPtr=%lld", (long long)bbqPtr);
        return nullptr;
    }
    fprintf(stderr, "[BBQ-CP] getSurface ENTER bbq=0x%llx ohNativeWindow=%p sessionId=%d\n",
            (long long)bbqPtr, b->ohNativeWindow, b->sessionId); fflush(stderr);
    // [PATCH-B / WALL2 2026-06-29] Lazy window resolution.  Unity inits its
    // GfxDevice by calling getSurface() and (unlike hwui) does NOT retry on a
    // null window — so if BBQ_nativeUpdate hasn't run yet, returning an empty
    // Surface (mNativeObject=0) permanently strands Unity with no EGL window.
    // Before giving up, attempt the SAME resolution chain BBQ_nativeUpdate uses
    // so mNativeObject is a real OHNativeWindow* by the time we fromSurface.
    if (!b->ohNativeWindow) {
        int32_t sessionId = b->sessionId;
        if (sessionId != 0) {
            b->sessionId = sessionId;
            void* nw = nullptr;
            bool isSurfaceView = (std::strstr(b->name, "SurfaceView") != nullptr);
            if (isSurfaceView) {
                nw = oh_rs_get_child_surface_window(sessionId, bbqPtr,
                                                    b->width, b->height);
            } else {
                nw = oh_wm_get_native_window(sessionId);
            }
            if (nw) {
                b->ohNativeWindow = nw;
                nwfs_seed_window_geometry(nw, "BBQ.getSurface-lazy");  // [S23 cut5 belt]
                ALOGI("BBQ.getSurface: lazy-resolved sessionId=%d -> OHNativeWindow=%p "
                      "(BBQ.update had not run before Unity GfxDevice init)",
                      sessionId, nw);
                fprintf(stderr, "[BBQ-CP] getSurface LAZY-RESOLVED sessionId=%d nw=%p\n",
                        sessionId, nw); fflush(stderr);
            }
        }
    }
    if (!b->ohNativeWindow) {
        ALOGW("BBQ.getSurface: ohNativeWindow null (sessionId=%d not attached "
              "or BBQ.update not yet called) — returning empty Surface so "
              "ViewRoot.mSurface.transferFrom doesn't NPE",
              b->sessionId);
        // Return an empty Surface so transferFrom() has a non-null target;
        // hwui will then operate on an empty surface (same as pre-G2.14r
        // behavior, but at least no NPE on transferFrom).
        jclass surfaceCls = env->FindClass("android/view/Surface");
        if (!surfaceCls) {
            if (env->ExceptionCheck()) env->ExceptionClear();
            return nullptr;
        }
        jmethodID ctor = env->GetMethodID(surfaceCls, "<init>", "()V");
        if (!ctor) {
            if (env->ExceptionCheck()) env->ExceptionClear();
            env->DeleteLocalRef(surfaceCls);
            return nullptr;
        }
        jobject empty = env->NewObject(surfaceCls, ctor);
        env->DeleteLocalRef(surfaceCls);
        return empty;
    }

    // Construct a real Java Surface and stamp ohNativeWindow into its
    // mNativeObject field.  On AOSP, Surface(long nativeObject) is a private
    // constructor that adopts the native handle — but that's not part of the
    // public API.  Use reflection: default-construct, then set mNativeObject.
    //
    // Important: AOSP Surface destructor calls nativeRelease which would try
    // to dec-ref a real ANativeWindow.  Our OHNativeWindow has a different
    // ref-count protocol (managed by surface_utils + RSSurfaceNode lifecycle).
    // To avoid double-free, we DO NOT take ownership: when the Java Surface
    // is GC'd, mNativeObject is set to 0 first via reflection in our future
    // session-teardown path.  For HelloWorld P1 this is sufficient.
    jclass surfaceCls = env->FindClass("android/view/Surface");
    if (!surfaceCls) {
        ALOGW("BBQ.getSurface: FindClass(android/view/Surface) failed");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return nullptr;
    }
    jmethodID ctor = env->GetMethodID(surfaceCls, "<init>", "()V");
    if (!ctor) {
        ALOGW("BBQ.getSurface: GetMethodID(<init>) failed");
        if (env->ExceptionCheck()) env->ExceptionClear();
        env->DeleteLocalRef(surfaceCls);
        return nullptr;
    }
    jobject surface = env->NewObject(surfaceCls, ctor);
    if (!surface) {
        ALOGW("BBQ.getSurface: NewObject(Surface) failed");
        if (env->ExceptionCheck()) env->ExceptionClear();
        env->DeleteLocalRef(surfaceCls);
        return nullptr;
    }
    jfieldID mNativeObjectFid = env->GetFieldID(surfaceCls, "mNativeObject", "J");
    if (!mNativeObjectFid) {
        ALOGW("BBQ.getSurface: GetFieldID(mNativeObject) failed");
        if (env->ExceptionCheck()) env->ExceptionClear();
        env->DeleteLocalRef(surfaceCls);
        return surface;
    }
    env->SetLongField(surface, mNativeObjectFid, reinterpret_cast<jlong>(b->ohNativeWindow));
    ALOGI("BBQ.getSurface: returning Surface with mNativeObject=%p (sessionId=%d)",
          b->ohNativeWindow, b->sessionId);
    env->DeleteLocalRef(surfaceCls);
    return surface;
}

// Android 15 exposes the sync callback API directly. The OH queue does not
// have SurfaceFlinger's transaction-acquisition callback, so report that no
// callback was armed. Callers retain their transaction and can submit it via
// the ordinary SurfaceControl path.
jboolean BBQ_nativeSyncNextTransaction(JNIEnv*, jclass, jlong, jobject, jboolean) {
    return JNI_FALSE;
}
void BBQ_nativeStopContinuousSyncTransaction(JNIEnv*, jclass, jlong) { }
void BBQ_nativeClearSyncTransaction(JNIEnv*, jclass, jlong) { }
void BBQ_nativeMergeWithNextTransaction(JNIEnv*, jclass, jlong, jlong, jlong) { }
jlong BBQ_nativeGetLastAcquiredFrameNum(JNIEnv*, jclass, jlong) { return 0; }
void BBQ_nativeApplyPendingTransactions(JNIEnv*, jclass, jlong, jlong) { }
jobject BBQ_nativeGatherPendingTransactions(JNIEnv* env, jclass, jlong, jlong) {
    // Match AOSP's ownership contract: return a live Transaction object whose
    // native state is owned by that Java wrapper. There is no pending SF-side
    // transaction to merge in the OH implementation.
    jclass transaction = env->FindClass("android/view/SurfaceControl$Transaction");
    if (!transaction || env->ExceptionCheck()) {
        std::fprintf(stderr, "[SOURCE-BLAST] gather FindClass failed exception=%d\n",
                     env->ExceptionCheck() ? 1 : 0);
        return nullptr;
    }
    jmethodID ctor = env->GetMethodID(transaction, "<init>", "()V");
    if (!ctor || env->ExceptionCheck()) {
        std::fprintf(stderr, "[SOURCE-BLAST] gather constructor failed exception=%d\n",
                     env->ExceptionCheck() ? 1 : 0);
        env->DeleteLocalRef(transaction);
        return nullptr;
    }
    jobject result = env->NewObject(transaction, ctor);
    env->DeleteLocalRef(transaction);
    return result;
}
void BBQ_nativeSetTransactionHangCallback(JNIEnv*, jclass, jlong, jobject) { }

// 2026-05-20 R5: BBQ.isSameSurfaceControl — compare by sessionId, not by ptr.
// AOSP uses SF IBinder handle for stable SC identity; OH has no SF so adapter
// stamps sessionId on every OhSurfaceControl (see SC_nativeCreate / Copy /
// ReadFromParcel R5 patches). Two SCs with the same non-zero sessionId
// represent the same logical OH session → BBQ should reuse, not rebuild.
// Without this method registered, JVM falls back to default JNI symbol
// resolution → either ULE-with-fallback or "always false" stub → BBQ rebuilds
// every relayout → hwui setSurface storm → flicker / EGL_NO_SURFACE abort.
jboolean BBQ_nativeIsSameSurfaceControl(JNIEnv*, jclass, jlong bbqPtr, jlong scPtr) {
    auto* b = as_bbq(bbqPtr);
    if (!b) return JNI_FALSE;
    // oh_sc_get_session is the cross-TU extern "C" helper exported by
    // android_view_SurfaceControl.cpp:988 — it validates magic + returns 0 on
    // bad ptr. Used here (and at line 146 sc_to_oh_native_window) to avoid
    // pulling OhSurfaceControl struct into this TU.
    int32_t scSessionId = scPtr ? oh_sc_get_session(scPtr) : 0;
    return (b->sessionId != 0 && b->sessionId == scSessionId) ? JNI_TRUE : JNI_FALSE;
}

const JNINativeMethod kBlastBufferQueueMethods[] = {
    { "nativeCreate", "(Ljava/lang/String;Z)J",
      reinterpret_cast<void*>(BBQ_nativeCreate) },
    { "nativeDestroy", "(J)V",
      reinterpret_cast<void*>(BBQ_nativeDestroy) },
    { "nativeGetSurface", "(JZ)Landroid/view/Surface;",
      reinterpret_cast<void*>(BBQ_nativeGetSurface) },
    { "nativeSyncNextTransaction", "(JLjava/util/function/Consumer;Z)Z",
      reinterpret_cast<void*>(BBQ_nativeSyncNextTransaction) },
    { "nativeStopContinuousSyncTransaction", "(J)V",
      reinterpret_cast<void*>(BBQ_nativeStopContinuousSyncTransaction) },
    { "nativeClearSyncTransaction", "(J)V",
      reinterpret_cast<void*>(BBQ_nativeClearSyncTransaction) },
    { "nativeUpdate", "(JJJJI)V",
      reinterpret_cast<void*>(BBQ_nativeUpdate) },
    { "nativeMergeWithNextTransaction", "(JJJ)V",
      reinterpret_cast<void*>(BBQ_nativeMergeWithNextTransaction) },
    { "nativeGetLastAcquiredFrameNum", "(J)J",
      reinterpret_cast<void*>(BBQ_nativeGetLastAcquiredFrameNum) },
    { "nativeApplyPendingTransactions", "(JJ)V",
      reinterpret_cast<void*>(BBQ_nativeApplyPendingTransactions) },
    { "nativeGatherPendingTransactions", "(JJ)Landroid/view/SurfaceControl$Transaction;",
      reinterpret_cast<void*>(BBQ_nativeGatherPendingTransactions) },
    // 2026-05-20 R5: register IsSameSurfaceControl so BBQ.isSameSurfaceControl
    // routes to adapter (compares by sessionId, not by ptr / SF binder handle).
    { "nativeIsSameSurfaceControl", "(JJ)Z",
      reinterpret_cast<void*>(BBQ_nativeIsSameSurfaceControl) },
    { "nativeSetTransactionHangCallback",
      "(JLandroid/graphics/BLASTBufferQueue$TransactionHangCallback;)V",
      reinterpret_cast<void*>(BBQ_nativeSetTransactionHangCallback) },
};

// =====================================================================
// android.view.DisplayEventReceiver
// =====================================================================
// AOSP register_android_view_DisplayEventReceiver lives in libandroid_runtime.
// hwui Choreographer subclasses this to receive vsync.  Without a real
// impl, Choreographer.scheduleVsync NPE on first call.  Stub: return a
// non-null sentinel; manual frame scheduling won't be vsync-aligned but
// HelloWorld static layout doesn't strictly need vsync.

jlong DER_nativeInit(JNIEnv*, jclass, jobject /*receiverWeak*/, jobject /*messageQueue*/,
                    jint /*vsyncSource*/, jint /*eventRegistration*/, jlong /*layerHandle*/) {
    static int sDerSentinel = 0xCAFE0DE5;
    return reinterpret_cast<jlong>(&sDerSentinel);
}
void DER_nativeDispose(JNIEnv*, jclass, jlong /*receiverPtr*/) { }
void DER_nativeScheduleVsync(JNIEnv*, jclass, jlong /*receiverPtr*/) {
    // Real impl: register a one-shot OH RSDisplayNode vsync callback.
    // No-op for now — Choreographer will time out, then re-schedule;
    // each vsync cycle ~16.6ms the Choreographer falls back to a manual
    // tick (it uses currentTimeNanos delta) so animations may be jittery.
}
jobject DER_nativeGetLatestVsyncEventData(JNIEnv*, jclass, jlong) {
    return nullptr;
}

const JNINativeMethod kDisplayEventReceiverMethods[] = {
    { "nativeInit",
      "(Ljava/lang/ref/WeakReference;Landroid/os/MessageQueue;IIJ)J",
      reinterpret_cast<void*>(DER_nativeInit) },
    { "nativeDispose", "(J)V",
      reinterpret_cast<void*>(DER_nativeDispose) },
    { "nativeScheduleVsync", "(J)V",
      reinterpret_cast<void*>(DER_nativeScheduleVsync) },
    { "nativeGetLatestVsyncEventData",
      "(J)Landroid/view/DisplayEventReceiver$VsyncEventData;",
      reinterpret_cast<void*>(DER_nativeGetLatestVsyncEventData) },
};

// =====================================================================
// Helper: register one method-array, method-by-method, tolerate failures
// =====================================================================
int registerOne(JNIEnv* env, const char* className,
                const JNINativeMethod* methods, size_t count) {
    jclass clazz = env->FindClass(className);
    if (!clazz) {
        ALOGW("FindClass(%s) failed — class not in BCP yet?", className);
        if (env->ExceptionCheck()) env->ExceptionClear();
        return -1;
    }
    int ok = 0, fail = 0;
    for (size_t i = 0; i < count; ++i) {
        jint rc = env->RegisterNatives(clazz, &methods[i], 1);
        if (rc == JNI_OK) {
            ++ok;
        } else {
            ++fail;
            ALOGW("compat_shim: register %s.%s%s failed",
                  className, methods[i].name, methods[i].signature);
            if (env->ExceptionCheck()) env->ExceptionClear();
        }
    }
    env->DeleteLocalRef(clazz);
    ALOGI("compat_shim: %s registered %d/%zu", className, ok, count);
    return 0;  // never propagate failure to caller — shim is best-effort
}

// =====================================================================
// 2026-05-11 G2.14ar — G2.14an BaseCanvas / G2.14ao HardwareRenderer
//                       diagnostic probes REMOVED.
// =====================================================================
// G2.14an installed 13 last-wins overrides on android.graphics.BaseCanvas
// nDrawXxx (non-forwarding stubs, log only).  G2.14ao installed similar
// stubs on HardwareRenderer.nSyncAndDrawFrame.
//
// Both violated the project architecture invariant: BaseCanvas / Canvas /
// Paint / RenderNode / HardwareRenderer JNI MUST use the AOSP-native
// libhwui implementation registered via dlsym at startReg
// (AndroidRuntime.cpp ~line 411 `register_android_graphics_Canvas` and
// related entries).  adapter is a thin bridge, not an hwui replacement
// (parallel evidence: `android_graphics_Canvas.cpp`,
// `_HardwareRenderer.cpp`, `_RenderNode.cpp`, `_Paint.cpp` are all
// retired stubs in compile_oh_android_runtime.sh — already excluded from
// the .so build for this exact reason).
//
// Diagnostic value already captured (memory project_g214aq_rs_pid_bypass
// notes: probes 0 fire confirms Java-side BaseCanvas.nDrawXxx is never
// called; root cause is upstream in View tree record path — independent
// of whether libhwui or stub is bound here).
// =====================================================================

// =====================================================================
// [UNITY-CW] hwui HardwareRenderer RenderThread neuter  (2026-07-01)
// =====================================================================
// WHY (device-confirmed, host-source-proven):
//   The bionic UnityPlayer requests FLAG_HARDWARE_ACCELERATED on its window.
//   ViewRootImpl.setView -> enableHardwareAcceleration (Java/BCP) -> ThreadedRenderer
//   .create() -> HardwareRenderer ctor -> nCreateProxy(real libhwui, registered
//   above by the kHwuiRegFns dlsym loop as register_android_view_ThreadedRenderer)
//   -> new RenderProxy -> RenderThread::getInstance() SPAWNS the hwui RenderThread
//   + its OH RenderService client (RSRenderThread / RSInterfaces, in-process).
//   This happens DURING setView, BEFORE WindowSessionAdapter.addToDisplay runs.
//   addToDisplay -> nativeCreateSession -> OHWindowManagerClient::createSession then
//   issues synchronous OH RS IPC (RSSurfaceNode::Create, RSInterfaces::
//   GetDefaultScreenId).  The freshly-spawned hwui RenderThread's RS-client init
//   contends with / DEADLOCKS that IPC -> [OH_WSA] PRE-native logged, POST-native
//   never.  tj_shell (plain SurfaceView, HW_ACCEL=false) spawns NO RenderThread and
//   createSession completes — that is the exact state we force here.
//
// WHY NOT strip FLAG_HARDWARE_ACCELERATED in the native createSession shim:
//   (a) IMPOSSIBLE — nativeCreateSession's JNI signature carries NO flags arg
//       (window_session_adapter.cpp / WindowSessionAdapter.java: type/displayId/
//       w/h/token only); attrs.flags never crosses into native.
//   (b) MOOT — even if it did, the RenderThread is already spawned (in setView,
//       upstream of addToDisplay), so a strip at createSession is too late.
//   The boundary-correct, timing-correct, NON-BCP fix is here: make nCreateProxy
//   a no-op so the RenderThread is never born.  We do NOT touch ViewRootImpl /
//   ThreadedRenderer Java (AonB black-box law) — only last-wins RegisterNatives
//   at the JNI boundary in our own liboh_android_runtime.so.
//
// DEMO-SAFETY (this .so is SHARED — also serves demos via $SA/lib64):
//   GATED on OHUB_VARIANT naming a known Unity/CW-shell variant (originally
//   just "cardwords"; 2026-07-10 widened to an enumerated allowlist OR'd with
//   OHUB_UNITY_LIBDIR presence — see the widened gate implementation below,
//   in register_android_graphics_compat_shim()) set in the Unity/CW launch
//   env (launch_asx_unityshell.sh / launch_game1r*.sh / launch_game2r*.sh /
//   betweenworlds variants).  Demo processes set neither -> they keep the
//   REAL libhwui HardwareRenderer + RenderThread (they DO render UI via
//   hwui).  A prior unconditional HardwareRenderer stub (G2.14ao) was
//   correctly reverted for the noice/demo line for exactly this reason; the
//   env gate is what makes the Unity-only neuter coexist with demo rendering
//   in shared source.
//
// CONSEQUENCE (intended): the Unity DecorView window no longer renders via hwui;
//   Unity draws on its own SurfaceView EGL surface (libunity eglCreateWindowSurface
//   on the OH-backed ANativeWindow) — the tj_shell model.  All proxy-handle-taking
//   natives are no-op'd so ViewRootImpl's later draw path cannot deref the fake
//   proxy handle.
static const jlong kHRNeuterFakeHandle = 1L;
void     HRN_v0(JNIEnv*, jclass) {}
void     HRN_v1(JNIEnv*, jclass, jlong) {}
void     HRN_v2str(JNIEnv*, jclass, jstring, jstring) {}
jlong    HRN_make(JNIEnv*, jclass) { return kHRNeuterFakeHandle; }
jlong    HRN_proxy(JNIEnv*, jclass, jboolean, jlong) { return kHRNeuterFakeHandle; }
jlong    HRN_layer(JNIEnv*, jclass, jlong) { return kHRNeuterFakeHandle; }
jboolean HRN_false_j(JNIEnv*, jclass, jlong) { return JNI_FALSE; }
jboolean HRN_false0(JNIEnv*, jclass) { return JNI_FALSE; }
jboolean HRN_true0(JNIEnv*, jclass) { return JNI_TRUE; }
jint     HRN_zero_j(JNIEnv*, jclass, jlong) { return 0; }
jfloat   HRN_one_ji(JNIEnv*, jclass, jlong, jint) { return 1.0f; }
jint     HRN_sync(JNIEnv*, jclass, jlong, jlongArray, jint) { return 0; }

// =====================================================================
// 2026-07-10 coverage-gap fix (route3-rssurface-stack-confirmed memory,
// "RenderThread正交墙未证明完整覆盖" side-finding follow-up):
//
// The original 39-entry table above only neuters natives that are reached
// THROUGH a `HardwareRenderer` Java instance (i.e. downstream of nCreateProxy,
// which is itself stubbed).  Source audit of AOSP frameworks/base found TWO
// static natives on the SAME `android/graphics/HardwareRenderer` class whose
// C++ impl (libs/hwui/renderthread/RenderProxy.cpp) calls
// `RenderThread::getInstance()` UNCONDITIONALLY (no `hasInstance()` guard),
// and are NOT gated by nCreateProxy at all — a caller can reach them without
// ever constructing a HardwareRenderer object:
//
//   - "preload" ()V -> RenderProxy::preload() -> RenderThread::getInstance()
//     (comment in AOSP source literally: "Create RenderThread object and
//     start the thread.").  Reachable UNCONDITIONALLY, BEFORE any Activity/
//     View/HardwareRenderer object exists: ActivityThread.handleLaunchActivity()
//     calls `HardwareRenderer.preload()` directly, gated only on
//     `ThreadedRenderer.sRendererEnabled` (AOSP default true; only false for
//     system_server-class processes) && activityInfo.FLAG_HARDWARE_ACCELERATED
//     (this adapter's AppSchedulerBridge.java:787 FORCES this flag on for
//     every ability by default).  This call happens BEFORE
//     performLaunchActivity() -> BEFORE ViewRootImpl.setView -> BEFORE
//     nCreateProxy.  So on THIS adapter, `preload()` is expected to run on
//     essentially every activity launch and construct the REAL global
//     RenderThread singleton regardless of whether nCreateProxy is later
//     stubbed — the "no proxy => no RenderThread" invariant the original
//     comment block above relies on does not hold once this entry point is
//     considered.  This is assessed (2026-07-10, source-only, not yet
//     device-confirmed) as the most likely mechanism behind the previously
//     unexplained 2/12 truly-cold RenderThread crash recurrence recorded in
//     route3-rssurface-stack-confirmed.md ("追查上一节side finding" section):
//     RenderThread is silently alive on every run via preload(); it only
//     crashes on the runs where its SurfaceView-position-update upcall race
//     wins against the older UnityMain SIGSEGV that otherwise kills the
//     process first.
//   - "nOverrideProperty" (Ljava/lang/String;Ljava/lang/String;)V ->
//     RenderProxy::overrideProperty() -> RenderThread::getInstance()
//     (also unconditional).  No automatic AOSP framework caller was found
//     (public @hide dev-tool API, not on the activity-launch path) — added
//     defensively for structural completeness while this table was already
//     being audited, not because a concrete reachable call site was found.
//
// Both stubbed as pure no-ops below (matches the "no proxy => no RenderThread"
// intent of the rest of this table).
// =====================================================================

#define HRN_SF "Landroid/view/Surface;"
const JNINativeMethod kHardwareRendererNeuterMethods[] = {
    // RenderThread birth — the load-bearing entries: no proxy, and no other
    // reachable entry point, => no RenderThread.
    {"nCreateRootRenderNode", "()J",            (void*)HRN_make},
    {"nCreateProxy",          "(ZJ)J",          (void*)HRN_proxy},
    {"nDeleteProxy",          "(J)V",           (void*)HRN_v1},
    // 2026-07-10: RenderThread::getInstance() entry points that bypass
    // nCreateProxy entirely (see block comment above).
    {"preload",               "()V",            (void*)HRN_v0},
    {"nOverrideProperty",     "(Ljava/lang/String;Ljava/lang/String;)V",
                                                 (void*)HRN_v2str},
    // proxy-handle-taking lifecycle/draw natives — no-op so the fake handle is
    // never dereferenced by libhwui once ViewRootImpl tries to draw the decor.
    {"nGetRenderThreadTid",   "(J)I",           (void*)HRN_zero_j},
    {"nLoadSystemProperties", "(J)Z",           (void*)HRN_false_j},
    {"nSetName",              "(JLjava/lang/String;)V", (void*)HRN_v1},
    {"nSetSurface",           "(J" HRN_SF "Z)V",(void*)HRN_v0},
    {"nSetSurfaceControl",    "(JJ)V",           (void*)HRN_v0},
    {"nPause",                "(J)Z",            (void*)HRN_false_j},
    {"nSetStopped",           "(JZ)V",           (void*)HRN_v0},
    {"nSetLightGeometry",     "(JFFFF)V",        (void*)HRN_v0},
    {"nSetLightAlpha",        "(JFF)V",          (void*)HRN_v0},
    {"nSetOpaque",            "(JZ)V",           (void*)HRN_v0},
    {"nSetColorMode",         "(JI)F",           (void*)HRN_one_ji},
    {"nSetTargetSdrHdrRatio", "(JF)V",           (void*)HRN_v0},
    {"nSetSdrWhitePoint",     "(JF)V",           (void*)HRN_v0},
    {"nSyncAndDrawFrame",     "(J[JI)I",         (void*)HRN_sync},
    {"nDestroy",              "(JJ)V",           (void*)HRN_v0},
    {"nRegisterAnimatingRenderNode","(JJ)V",     (void*)HRN_v0},
    {"nRegisterVectorDrawableAnimator","(JJ)V",  (void*)HRN_v0},
    {"nCreateTextureLayer",   "(J)J",            (void*)HRN_layer},
    {"nBuildLayer",           "(JJ)V",           (void*)HRN_v0},
    {"nPushLayerUpdate",      "(JJ)V",           (void*)HRN_v0},
    {"nCancelLayerUpdate",    "(JJ)V",           (void*)HRN_v0},
    {"nDetachSurfaceTexture", "(JJ)V",           (void*)HRN_v0},
    {"nDestroyHardwareResources","(J)V",         (void*)HRN_v1},
    {"nFence",                "(J)V",            (void*)HRN_v1},
    {"nStopDrawing",          "(J)V",            (void*)HRN_v1},
    {"nNotifyFramePending",   "(J)V",            (void*)HRN_v1},
    {"nAddRenderNode",        "(JJZ)V",          (void*)HRN_v0},
    {"nRemoveRenderNode",     "(JJ)V",           (void*)HRN_v0},
    {"nDrawRenderNode",       "(JJ)V",           (void*)HRN_v0},
    {"nSetContentDrawBounds", "(JIIII)V",        (void*)HRN_v0},
    {"nForceDrawNextFrame",   "(J)V",            (void*)HRN_v1},
    {"nAddObserver",          "(JJ)V",           (void*)HRN_v0},
    {"nRemoveObserver",       "(JJ)V",           (void*)HRN_v0},
    {"nAllocateBuffers",      "(J)V",            (void*)HRN_v1},
    {"nSetForceDark",         "(JZ)V",           (void*)HRN_v0},
    {"nIsDrawingEnabled",     "()Z",             (void*)HRN_true0},
};

}  // namespace

// Public entry called by AndroidRuntime::startReg AFTER libhwui's
// register_X loop, so our overrides win (last-wins JNI semantics).
int register_android_graphics_compat_shim(JNIEnv* env) {
    registerOne(env, "android/graphics/ImageDecoder",
                kImageDecoderMethods,
                sizeof(kImageDecoderMethods) / sizeof(kImageDecoderMethods[0]));
    registerOne(env, "android/view/Surface",
                kSurfaceMethods,
                sizeof(kSurfaceMethods) / sizeof(kSurfaceMethods[0]));
    registerOne(env, "android/graphics/BLASTBufferQueue",
                kBlastBufferQueueMethods,
                sizeof(kBlastBufferQueueMethods) / sizeof(kBlastBufferQueueMethods[0]));
    // [UNITY-CW] neuter hwui HardwareRenderer (no RenderThread) for the Unity/CW
    // engine process ONLY — gated below on an OHUB_VARIANT allowlist OR
    // OHUB_UNITY_LIBDIR presence (see 2026-07-10 note immediately below) so
    // demo processes (served by $SA/lib64) keep the real libhwui RenderThread.
    // See the
    // kHardwareRendererNeuterMethods block above for the full causal chain
    // (prevents the hwui RenderThread RS-client deadlock vs createSession's RS IPC).
    // 2026-07-10 (route3-rssurface-stack-confirmed memory, "RenderThread正交墙
    // 修复方案钉死"): the original gate below only matched OHUB_VARIANT=="cardwords".
    // route3's own launch scripts (launch_game1r.sh / launch_game1r_g34.sh /
    // launch_game2r.sh / launch_cw_g34.sh / betweenworlds variants) all pass
    // OHUB_VARIANT=game1|game2|betweenworlds — never "cardwords" — so this
    // fully-implemented neuter was 100% dead code for every route3 process.
    // Widened to (a) an enumerated allowlist of every known Unity-bridge-shell
    // variant string observed across all launch scripts, OR'd with (b) presence
    // of OHUB_UNITY_LIBDIR (set pairwise with OHUB_VARIANT by every one of those
    // launch scripts; never set by non-Unity/demo processes) as a
    // forward-compatible catch-all so a future variant-name rename can't silently
    // re-introduce this same dead-code trap.
    {
        const char* variant = getenv("OHUB_VARIANT");
        const bool variant_match = variant && (
            strcmp(variant, "cardwords") == 0 ||
            strcmp(variant, "game1") == 0 ||
            strcmp(variant, "game2") == 0 ||
            strcmp(variant, "betweenworlds") == 0);
        const bool unity_libdir_present = getenv("OHUB_UNITY_LIBDIR") != nullptr;
        if (variant_match || unity_libdir_present) {
            ALOGI("compat_shim: [UNITY-CW] neutering hwui HardwareRenderer "
                  "(OHUB_VARIANT=%s, OHUB_UNITY_LIBDIR%s) -> no RenderThread, "
                  "createSession unblocks",
                  variant ? variant : "(null)",
                  unity_libdir_present ? " set" : " unset");
            registerOne(env, "android/graphics/HardwareRenderer",
                        kHardwareRendererNeuterMethods,
                        sizeof(kHardwareRendererNeuterMethods)
                            / sizeof(kHardwareRendererNeuterMethods[0]));
        }
    }
    // 2026-05-11 G2.14ar — G2.14an BaseCanvas probe + G2.14ao HardwareRenderer
    // probe registerOne() calls REMOVED.  BaseCanvas / Canvas / Paint /
    // HardwareRenderer / RenderNode JNI now bind only to the AOSP-native
    // libhwui impls registered via dlsym in startReg (AndroidRuntime.cpp
    // ~line 411 register_android_graphics_Canvas etc).  See the removed
    // diagnostic-probe block comment above for full rationale.
    // 2026-05-01 G2.14n: DisplayEventReceiver registration REMOVED from compat
    // shim.  The real timer-based vsync impl already lives in
    // android_view_DisplayEventReceiver.cpp (registered via kRegJNI).  Letting
    // compat_shim re-register here with a no-op DER_nativeScheduleVsync was
    // overriding the real impl (last-wins) — Choreographer never received vsync
    // ticks → ViewRootImpl.performTraversals never ran → HWUI never started →
    // blank window.
    return 0;
}

}  // namespace android

// =============================================================================
// 2026-05-08 G2.14ad: ANativeWindow NDK bridges (relocated from atrace_stubs.cpp)
// =============================================================================
//
// libhwui ThreadedRenderer (jni/android_graphics_HardwareRenderer.cpp:1100)
// does dlopen("libandroid.so") + dlsym("ANativeWindow_*"). On our device
// libandroid.so is symlinked to liboh_android_runtime.so (this library), so
// the dlsym hits the impls below.
//
// They live in compat_shim.cpp because the upstream of mNativeObject — the
// `BBQ_nativeGetSurface` call that stuffs an OHNativeWindow* into the Java
// Surface — is in the same file (~ line 440). Putting both ends of the
// mNativeObject contract here keeps the surface-handle invariants visible
// in one place.
//
// Real impl strategy:
//   - ANativeWindow_fromSurface: read mNativeObject from Java Surface; if it
//     looks like a sentinel (set by S_nativeCreateFromSurfaceControl etc.
//     when no real BBQ-bound surface is available yet), return null so
//     hwui retries on the next frame. Otherwise hand back the OHNativeWindow*
//     directly — on OH `OHNativeWindow ≡ ANativeWindow`, no conversion needed.
//   - ANativeWindow_acquire/release: route to OH NativeObjectReference/Unreference.
//   - getWidth/Height/getFormat: route to OH NativeWindowHandleOpt.
//
// All lifecycle / dimension queries land in OH inner_api/surface/window.h.

// Opaque alias — same layout as OHNativeWindow
struct ANativeWindow;
struct OHNativeWindow;

// OH inner API forward decls (graphic_surface/interfaces/inner_api/surface/window.h)
extern "C" int32_t NativeObjectReference(void *obj);
extern "C" int32_t NativeObjectUnreference(void *obj);
extern "C" int32_t NativeWindowHandleOpt(OHNativeWindow *window, int code, ...);
#define OH_OP_SET_BUFFER_GEOMETRY 0
#define OH_OP_GET_BUFFER_GEOMETRY 1
#define OH_OP_GET_FORMAT          2

// OH NDK surface identity query used by the real on-screen window path.
extern "C" int32_t OH_NativeWindow_GetSurfaceId(OHNativeWindow* window, uint64_t* surfaceId);
// NativeWindowOperation codes / GraphicPixelFormat / BufferUsage values mirror
// graphic_surface/interfaces/inner_api/surface/{external_window.h,surface_type.h}.
#define OH_OP_SET_USAGE                 5
#define GRAPHIC_PIXEL_FMT_RGBA_8888     12
#define BUFFER_USAGE_MEM_DMA            (1ULL << 3)
#define BUFFER_USAGE_HW_RENDER          (1ULL << 8)
#define BUFFER_USAGE_HW_TEXTURE         (1ULL << 9)

// G2.14ag: AdapterAnw shim probes (impl in framework/window/jni/
// oh_anativewindow_shim.cpp, packed into liboh_adapter_bridge.so). We
// do not #include the header here to avoid cross-target include path
// drift; opaque struct fwd decls above are sufficient.
extern "C" int oh_anw_try_acquire(struct ANativeWindow* aosp);
extern "C" int oh_anw_try_release(struct ANativeWindow* aosp);
extern "C" struct OHNativeWindow* oh_anw_get_oh(struct ANativeWindow* aosp);

// Unwrap an ANativeWindow* — if it's an AdapterAnw shim, return the
// embedded real OHNativeWindow*. Otherwise pass through (assume `w` is
// already an OHNativeWindow*, the pre-G2.14ae direct cast invariant).
static inline OHNativeWindow* anw_unwrap(ANativeWindow* w) {
    if (!w) return nullptr;
    OHNativeWindow* oh = oh_anw_get_oh(w);
    return oh ? oh : reinterpret_cast<OHNativeWindow*>(w);
}

// HiLogPrint forward-decl above (line 35) takes int level. Use the same magic
// numbers as ALOGI/ALOGW: type 3 = LOG_CORE, level 4/5/6 = INFO/WARN/ERROR.
#define NWFS_INFO(fmt, ...) \
    HiLogPrint(3, 4, 0xD000F00u, "OH_NWFromSurface", fmt, ##__VA_ARGS__)
#define NWFS_WARN(fmt, ...) \
    HiLogPrint(3, 5, 0xD000F00u, "OH_NWFromSurface", fmt, ##__VA_ARGS__)

// Sentinels (0xCAFE5C0X) live in BSS/RDATA of liboh_android_runtime.so as
// `static int sSentinelStorage = 0xCAFE5C0X;`. A Java Surface whose
// mNativeObject points at one of these has no real BBQ-bound buffer.
// Detect by reading the first 4 bytes — sentinel storage holds the magic
// value, while a real OHNativeWindow's first word is its vtable / RefBase.
static inline bool is_sentinel_handle(jlong h) {
    if (h == 0) return true;
    int32_t magic = *reinterpret_cast<int32_t*>(h);
    return (magic & 0xFFFFFFF0) == 0xCAFE5C00;
}

// [S23 cut5 2026-07-09] Seed the geometry of the EXACT OHNativeWindow instance
// Unity dequeues from, on the last-mile handoff. cut4 proved SET_BUFFER_GEOMETRY
// (rc=0) reaches window->config, but the bridge poked a sibling nw
// (oh_rs_get_child_surface_window's 0x..B50) while Unity uses the instance stamped
// into Surface.mNativeObject / returned by ANativeWindow_fromSurface (0x..A20).
// native_window.cpp:229 NativeWindowRequestBuffer reads THIS instance's config;
// if it is 0x0 the server allocs Buffer[0 0] -> NO_BUFFER 50002000 storm, no pixels.
// Poke here (creation/stamp + handoff) so the dequeued instance carries 1200x1920
// BEFORE Unity's first RequestBuffer. 5bb5 panel = 1200x1920 (hard fallback; never
// 0/1). Log the instance address so "same instance as Unity RequestBuffer nw_B" is
// nailed in the log.
extern "C" void nwfs_seed_window_geometry(void* nw, const char* where) {
    if (!nw) return;
    int32_t w = 1200, h = 1920;  // TODO: prefer live display bounds; 5bb5 panel is 1200x1920
    // [S23 cut5.1] nw handed to Unity is the AdapterAnw shim (AOSP ABI), NOT a raw
    // OHNativeWindow. SET_BUFFER_GEOMETRY on the shim -> rc=0x40001000 (invalid arg).
    // Unwrap to the shim's embedded real OHNativeWindow first (same pattern as
    // ANativeWindow_getWidth line ~1140). This is the SAME underlying producer
    // Unity's RequestBuffer (shim wrapper -> OH_NativeWindow_NativeWindowRequestBuffer)
    // dequeues from, so config now reaches the storming path.
    OHNativeWindow* oh = anw_unwrap(reinterpret_cast<ANativeWindow*>(nw));
    int32_t rc = NativeWindowHandleOpt(oh, OH_OP_SET_BUFFER_GEOMETRY, w, h);
    HiLogPrint(3, 4, 0xD000F00u, "OH_NWSeed",
               "[%{public}s] SET_BUFFER_GEOMETRY shim=%{public}p oh=%{public}p %{public}dx%{public}d rc=%{public}d",
               where, nw, (void*)oh, w, h, rc);
}

extern "C" ANativeWindow* ANativeWindow_fromSurface(JNIEnv* env, jobject surface) {
    NWFS_INFO("[STAGE0] ENTER env=%{public}p surface=%{public}p",
              (void*)env, (void*)surface);
    if (!env || !surface) {
        NWFS_WARN("[STAGE0] null arg -> null");
        return nullptr;
    }
    jclass cls = env->FindClass("android/view/Surface");
    if (!cls) { env->ExceptionClear();
        NWFS_WARN("[STAGE0] FindClass failed -> null"); return nullptr; }
    jfieldID fid = env->GetFieldID(cls, "mNativeObject", "J");
    env->DeleteLocalRef(cls);
    if (!fid) { env->ExceptionClear();
        NWFS_WARN("[STAGE0] GetFieldID failed -> null"); return nullptr; }
    jlong nativeObj = env->GetLongField(surface, fid);
    NWFS_INFO("[STAGE0] mNativeObject=0x%{public}llx",
              (unsigned long long)nativeObj);
    if (nativeObj == 0) {
        NWFS_WARN("[STAGE0] mNativeObject==0 -> null");
        return nullptr;
    }
    if (is_sentinel_handle(nativeObj)) {
        NWFS_WARN("[STAGE0] sentinel handle 0x%{public}llx -> null "
                  "(no real BBQ-bound surface yet; hwui will retry)",
                  (unsigned long long)nativeObj);
        return nullptr;
    }
    // Real OHNativeWindow* set by BBQ_nativeGetSurface above. On OH,
    // OHNativeWindow ≡ ANativeWindow, so hand it back to hwui directly.
    // [S23 cut5 PRIMARY] last-mile: this is the exact instance Unity dequeues
    // from — seed its geometry before returning so its first RequestBuffer
    // carries 1200x1920 (not Buffer[0 0]). Instance-identity nailed via the log.
    nwfs_seed_window_geometry(reinterpret_cast<void*>(nativeObj), "STAGE0-handoff");
    NWFS_INFO("[STAGE0] returning OHNativeWindow=%{public}p directly",
              reinterpret_cast<void*>(nativeObj));
    return reinterpret_cast<ANativeWindow*>(nativeObj);
}

// G2.14ag: detect AdapterAnw shim (post-G2.14ae). When hwui passes a shim
// here, route refcount to AdapterAnw's atomic (AOSP common.incRef/decRef
// equivalent); else forward to OH NativeObjectReference. See
// doc/graphics_rendering_design.html §7.13 (ref counting).
extern "C" void ANativeWindow_acquire(ANativeWindow* w) {
    if (!w) return;
    if (oh_anw_try_acquire(w)) return;          // shim path
    NativeObjectReference(reinterpret_cast<void*>(w));
}

extern "C" void ANativeWindow_release(ANativeWindow* w) {
    if (!w) return;
    if (oh_anw_try_release(w)) return;          // shim path
    NativeObjectUnreference(reinterpret_cast<void*>(w));
}

extern "C" int32_t ANativeWindow_getWidth(ANativeWindow* w) {
    if (!w) return 0;
    int32_t width = 0, height = 0, format = 0;
    NativeWindowHandleOpt(anw_unwrap(w),        // G2.14ag: unwrap shim
                           OH_OP_GET_BUFFER_GEOMETRY, &height, &width, &format);
    return width;
}

extern "C" int32_t ANativeWindow_getHeight(ANativeWindow* w) {
    if (!w) return 0;
    int32_t width = 0, height = 0, format = 0;
    NativeWindowHandleOpt(anw_unwrap(w),        // G2.14ag: unwrap shim
                           OH_OP_GET_BUFFER_GEOMETRY, &height, &width, &format);
    return height;
}

extern "C" int32_t ANativeWindow_getFormat(ANativeWindow* w) {
    if (!w) return 0;
    int32_t format = 0;
    NativeWindowHandleOpt(anw_unwrap(w),        // G2.14ag: unwrap shim
                           OH_OP_GET_FORMAT, &format);
    return format;
}

// [UNITY-PATCH-C] NDK buffer-config + query shims.
// Unity's EGL bring-up (and AOSP hwui via libandroid.so dlsym) calls these
// NDK entry points on the ANativeWindow returned by ANativeWindow_fromSurface.
// Before this patch they were absent → dlsym(nullptr) → Unity aborted before
// the first eglSwapBuffers. Route geometry/format to OH NativeWindowHandleOpt;
// dataspace is advisory (OH RSSurfaceNode owns colorspace).
#define OH_OP_SET_BUFFER_GEOMETRY 0
#define OH_OP_SET_FORMAT          3
extern "C" int32_t ANativeWindow_setBuffersGeometry(ANativeWindow* w,
        int32_t width, int32_t height, int32_t format) {
    if (!w) return -1;
    OHNativeWindow* oh = anw_unwrap(w);
    int32_t rc = NativeWindowHandleOpt(oh, OH_OP_SET_BUFFER_GEOMETRY, width, height);
    if (format > 0) {
        // [WALL2-FMT 2026-06-29] Translate AOSP visual-id pixel format → OH
        // GraphicPixelFormat (e.g. RGBA_8888 1 → 12). androidToOHPixelFormat
        // clamps unknown/1/0 to OH RGBA_8888=12, never passing CLUT (1) to OH.
        int32_t ohFormat = oh_adapter::androidToOHPixelFormat(format);
        NativeWindowHandleOpt(oh, OH_OP_SET_FORMAT, ohFormat);
        NWFS_INFO("ANativeWindow_setBuffersGeometry fmt-map AOSP=%{public}d -> OH=%{public}d",
                  format, ohFormat);
    }
    NWFS_INFO("ANativeWindow_setBuffersGeometry w=%{public}d h=%{public}d fmt=%{public}d rc=%{public}d",
              width, height, format, rc);
    return 0;
}
extern "C" int32_t ANativeWindow_setBuffersDataSpace(ANativeWindow* w, int32_t dataSpace) {
    if (!w) return -1;
    NWFS_INFO("ANativeWindow_setBuffersDataSpace ds=%{public}d (advisory no-op)", dataSpace);
    return 0;
}
extern "C" int32_t ANativeWindow_query(const ANativeWindow* w, int32_t what, int32_t* value) {
    if (!w || !value) return -1;
    OHNativeWindow* oh = anw_unwrap(const_cast<ANativeWindow*>(w));
    switch (what) {
        case 0: {  // NATIVE_WINDOW_WIDTH
            int32_t h = 0, ww = 0, f = 0;
            NativeWindowHandleOpt(oh, OH_OP_GET_BUFFER_GEOMETRY, &h, &ww, &f);
            *value = ww; return 0;
        }
        case 1: {  // NATIVE_WINDOW_HEIGHT
            int32_t h = 0, ww = 0, f = 0;
            NativeWindowHandleOpt(oh, OH_OP_GET_BUFFER_GEOMETRY, &h, &ww, &f);
            *value = h; return 0;
        }
        case 2: {  // NATIVE_WINDOW_FORMAT
            int32_t f = 1;
            NativeWindowHandleOpt(oh, OH_OP_GET_FORMAT, &f);
            *value = f; return 0;
        }
        default:
            *value = 0; return 0;
    }
}

// [UNITY-EGL-UNWRAP]  Wall 4 — eglCreateWindowSurface de-wrap interposer.
//
// libunity.so calls eglCreateWindowSurface() with the AOSP ANativeWindow it
// got from ANativeWindow_fromSurface().  On OH that handle is an AdapterAnw
// wrapper (magic '_wnd') around the real OHNativeWindow; OH's libEGL only
// accepts the bare OHNativeWindow, so the wrapped pointer would be rejected
// (EGL_NO_SURFACE / fatal).  We unwrap via oh_anw_get_oh() (strong T symbol in
// liboh_adapter_bridge.so, forward-declared at the top of this file) and call
// through to OH's real eglCreateWindowSurface resolved by name from libEGL.so.
//
// Why this binds without LD_PRELOAD / -Bsymbolic: libunity's DT_NEEDED lists
// libandroid.so (== this runtime) BEFORE libEGL.so, so the breadth-first
// global symbol resolution binds libunity's eglCreateWindowSurface reference to
// our strong definition here.  Non-wrapped windows (magic != '_wnd') return
// nullptr from oh_anw_get_oh and are passed through untouched, so hwui's own
// EGL path is not disturbed.
//
// libEGL.so is an exact DT_NEEDED dependency of this runtime. Reuse only the
// already-loaded provider; never create a second/global/absolute-path instance.
typedef void*    EGLDisplay;
typedef void*    EGLConfig;
typedef void*    EGLSurface;
typedef int32_t  EGLint;
typedef EGLSurface (*PFN_eglCreateWindowSurface)(EGLDisplay, EGLConfig, void*,
                                                 const EGLint*);

extern "C" EGLSurface eglCreateWindowSurface(EGLDisplay dpy, EGLConfig cfg,
                                             void* win, const EGLint* attrs) {
    static PFN_eglCreateWindowSurface s_real = nullptr;
    static bool s_resolved = false;
    if (!s_resolved) {
        s_resolved = true;
        // dlfcn.h was #included inside namespace android above, so the dl*
        // symbols live in android:: — qualify them from this global scope.
        void* h = android::dlopen("libEGL.so", RTLD_NOW | RTLD_NOLOAD);
        if (h) {
            s_real = reinterpret_cast<PFN_eglCreateWindowSurface>(
                android::dlsym(h, "eglCreateWindowSurface"));
        }
        NWFS_INFO("[UNITY-EGL] resolve eglCreateWindowSurface handle=%{public}p real=%{public}p",
                  h, reinterpret_cast<void*>(s_real));
    }
    if (!s_real) {
        NWFS_WARN("[UNITY-EGL] real eglCreateWindowSurface unresolved -> EGL_NO_SURFACE");
        return nullptr;   // EGL_NO_SURFACE
    }
    OHNativeWindow* oh = win ? oh_anw_get_oh(reinterpret_cast<ANativeWindow*>(win))
                             : nullptr;

    if (!oh) {
        NWFS_WARN("[UNITY-EGL] adapter window has no OHNativeWindow; fail closed");
        return nullptr;
    }

    // [STAGE2-UNITY 2026-06-28] Prime the unwrapped OH window with GPU-render
    // usage + format BEFORE eglCreateWindowSurface. The RSSurfaceNode producer
    // from the SurfaceView/BLAST path has no HW_RENDER usage by default → OH's
    // libEGL can't allocate GPU-renderable buffers → EGL_BAD_ALLOC (0x3003).
    // (eglprobe FAILed here with err=0x3003; offscreen path already did this.)
    if (oh) {
        int32_t gh = 0, gw = 0, gf = 0;
        NativeWindowHandleOpt(oh, OH_OP_GET_BUFFER_GEOMETRY, &gh, &gw, &gf);
        int32_t qsz = -1;
        NativeWindowHandleOpt(oh, 17 /*GET_BUFFERQUEUE_SIZE*/, &qsz);
        NWFS_INFO("[STAGE2-EGL] pre-prime window geometry h=%{public}d w=%{public}d fmt=%{public}d QUEUE_SIZE=%{public}d", gh, gw, gf, qsz);
        NativeWindowHandleOpt(oh, OH_OP_SET_FORMAT, GRAPHIC_PIXEL_FMT_RGBA_8888);
        NativeWindowHandleOpt(oh, OH_OP_SET_USAGE,
                              (uint64_t)(BUFFER_USAGE_HW_RENDER |
                                         BUFFER_USAGE_HW_TEXTURE |
                                         BUFFER_USAGE_MEM_DMA));
        int32_t sw = (gw > 0) ? gw : 1200, sh = (gh > 0) ? gh : 1794;
        NativeWindowHandleOpt(oh, OH_OP_SET_BUFFER_GEOMETRY, sw, sh);
    }
    void* target = reinterpret_cast<void*>(oh);
    NWFS_INFO("[UNITY-EGL] eglCreateWindowSurface win=%{public}p oh=%{public}p (%{public}s)",
              win, reinterpret_cast<void*>(oh), oh ? "unwrapped" : "passthrough");
    // [STAGE2-UNITY 2026-06-28 W11] RETRY: noice/HWUI succeeds because it calls
    // eglCreateWindowSurface/getOhNativeWindow REPEATEDLY in its render loop —
    // the RSSurfaceNode producer's RenderService consumer isn't acquire-ready on
    // the FIRST try → first eglCreateWindowSurface returns EGL_NO_SURFACE
    // (EGL_BAD_ALLOC). Java EGL14 callers (eglprobe / Unity) call ONCE and give
    // up. Retry internally (blocking the render thread briefly during init) so
    // the consumer has time to connect/acquire, mirroring HWUI's loop.
    EGLSurface result = s_real(dpy, cfg, target, attrs);
    if (result == (EGLSurface)0 /*EGL_NO_SURFACE*/ && oh) {
        for (int i = 0; i < 60 && result == (EGLSurface)0; ++i) {
            usleep(25000);  // 25ms; up to ~1.5s total
            result = s_real(dpy, cfg, target, attrs);
        }
        NWFS_INFO("[STAGE2-EGL] eglCreateWindowSurface RETRY done result=%{public}p", result);
    }
    return result;
}
