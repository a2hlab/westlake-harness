// ============================================================================
// AndroidRuntime.cpp
//
// OH-Adapter's replacement of frameworks/base/core/jni/AndroidRuntime.cpp's
// startReg() dispatch. Kept intentionally small: each entry is a register_*
// function that has already been implemented in this project.
//
// Adding a new JNI module:
//   1. Write src/android_<area>_<Class>.cpp with a `register_android_*` fn.
//   2. Declare it in include/AndroidRuntime.h.
//   3. Add a line to `kRegJNI[]` below.
//   4. Rebuild liboh_android_runtime.so.
// ============================================================================

#include "AndroidRuntime.h"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <dlfcn.h>
#include <errno.h>   // [port-a1a2d4 2026-07-30]
#include <poll.h>
#include <pthread.h>
#include <string>   // §441 payload uses std::string (sibling TUs already STL)
#include <hilog/log.h>
#include <nativehelper/JNIHelp.h>  // jniRegisterNativeMethods (L2)

// [STAGE2-GL 2026-06-28] The raw AOSP android_opengl_GLES{20,30,31}.cpp define
// register_android_opengl_jni_GLES* in the GLOBAL namespace (unlike the
// adapter's EGL14 copy which was wrapped in namespace android). Declare them at
// global scope here and reference them ::-qualified from kRegJNI_GL below.
extern "C++" int register_android_opengl_jni_GLES20(JNIEnv* env);
extern "C++" int register_android_opengl_jni_GLES30(JNIEnv* env);
extern "C++" int register_android_opengl_jni_GLES31(JNIEnv* env);

// Task 79 A3: board-ICU C-ABI bridge. ICU is bound before any other startReg
// work; NativeConverter (13/16) and regex (15/15) are registered at the tail
// so JNI last-writer-wins ordering is explicit and auditable.
// [port-a3-junction 2026-07-30] verbatim junctions from sol-2 commit 2a6a669bc
// (src/adapter copy) onto the AlexBridge canonical tree (port-a1a2d4 payload carrier).
extern int westlake_icu_early_init();
extern int westlake_register_charset_natives(JNIEnv* env);
extern int westlake_register_regex_natives(JNIEnv* env);

namespace android {

// Cached JavaVM for callback-local central JNI admission.
static JavaVM* g_vm = nullptr;

void AndroidRuntime::setJavaVM(JavaVM* vm) { g_vm = vm; }
JavaVM* AndroidRuntime::getJavaVM() { return g_vm; }

// 2026-05-18 (L2): AOSP-compatible static helper used by frameworks/base/
// core/jni/core_jni_helpers.h when AOSP JNI source (e.g., MotionEvent.cpp)
// registers its native methods.  Trivial passthrough to libnativehelper —
// mirrors frameworks/base/core/jni/AndroidRuntime.cpp.
/*static*/ int AndroidRuntime::registerNativeMethods(JNIEnv* env,
        const char* className, const JNINativeMethod* gMethods, int numMethods) {
    return jniRegisterNativeMethods(env, className, gMethods, numMethods);
}

// G2.4 (2026-04-30): graphics JNI compat shim — last-wins overrides for
// methods whose libhwui impl aborts (fid==null) or whose AOSP libandroid_runtime
// impl is missing (we don't cross-compile that .so).  Spec: doc/graphics_jni_inventory.html §4.1.
extern int register_android_graphics_compat_shim(JNIEnv* env);

// G2.14k (2026-05-01) + 2026-05-02 audit: NAR applyFreeFunction guard.
// User flagged for removal as "defensive hack" but empirical removal breaks
// initChild Java entry on main thread (SIGSEGV pc=0).  TODO P1: identify the
// implicit class-init dependency this provides, then replace.  See header
// comment in libcore_util_NativeAllocationRegistry_guard.cpp.
extern int register_libcore_util_NativeAllocationRegistry_guard(JNIEnv* env);

// G2.14n (2026-05-01): PropertyValuesHolder JNI cache for animation framework.
// View.setContentView path triggers Animator/PropertyValuesHolder static init
// which calls nGetFloatMethod / nGetIntMethod via JNI.
extern int register_android_animation_PropertyValuesHolder(JNIEnv* env);

// B.15: register_android_graphics_Typeface — minimal in-runtime impl.
// Earlier dlopen("libhwui.so") attempt hung (libhwui has heavy GPU init not
// safe in init service ctx).  Compiled directly into liboh_android_runtime.so.
extern int register_android_graphics_Typeface(JNIEnv* env);

// G2.14u (2026-05-07): AOSP-ported android_os_Parcel.cpp.  Provides ~30
// Parcel native methods needed by SurfaceControl / Bundle / Intent / Binder
// IPC paths that ViewRootImpl.relayoutWindow follows on first frame.
// Source: frameworks/base/core/jni/android_os_Parcel.cpp (918 lines), pulled
// in via SRCS_AOSP (compile_oh_android_runtime.sh).
extern int register_android_os_Parcel(JNIEnv* env);

// G2.14w (2026-05-08): adapter-rewritten android_view_KeyCharacterMap.cpp.
// Provides 13 native methods for android.view.KeyCharacterMap.  KCM.load
// fallback path (KCM.obtainEmptyMap → nativeObtainEmptyKeyCharacterMap)
// previously hit UnsatisfiedLinkError because no register_X covered it,
// blocking PhoneWindow.preparePanel after InputManagerAdapter VIRTUAL_KEYBOARD
// double mapping landed.  Source pattern: frameworks/base/core/jni/
// android_view_KeyCharacterMap.cpp (AOSP 14, 284 lines), adapter-adapted to
// strip <binder/Parcel.h> + <input/*.h> deps; mMap permanently nullptr in
// Phase 1 (Phase 3 will populate from OH MMI keymap data).
extern int register_android_view_KeyCharacterMap(JNIEnv* env);

// 2026-05-18: adapter-rewritten android_view_MotionEvent_aosp.cpp.  Provides
// all 51 native methods for android.view.MotionEvent.  Final dependency for
// Input_Adapter_design §3.3.5 Phase 2 — without it, MotionEvent.obtain
// throws UnsatisfiedLinkError on nativeInitialize, blocking helloworld
// touch dispatch (CHANGE COLOR button click never reaches APK onClick).
// Source pattern: AOSP 14 frameworks/base/core/jni/android_view_MotionEvent.cpp
// (917 lines), but reimplemented with a self-contained OhMotionEvent struct
// to avoid pulling libinput.so / libui.so / ui::Transform / HmacKeyManager /
// IInputConstants AIDL chain into liboh_android_runtime.
extern int register_android_view_MotionEvent(JNIEnv* env);

// 2026-05-26: register_android_view_KeyEvent — 3 natives (nativeNextId /
// nativeKeyCodeToString / nativeKeyCodeFromString).  android.view.KeyEvent
// .<init> calls nativeNextId() to allocate its mId; without this registration
// every KeyEvent construction (e.g. dispatchKeyFromWorker building a BACK key)
// throws UnsatisfiedLinkError before the event can reach ViewRootImpl.  Backed
// by adapter-private android_view_KeyEvent_aosp.cpp.
extern int register_android_view_KeyEvent(JNIEnv* env);

// B.20.r7: register_android_os_GraphicsEnvironment — 11 natives, all no-op
// safe defaults. setupGraphicsSupport line 6680 calls isDebuggable() then
// (within setup) calls layer/driver/ANGLE configuration natives.  AOSP
// registers these in libandroid_servers.so (system_server-side); on OH the
// child process needs them resolved in liboh_android_runtime.so.
extern int register_android_os_GraphicsEnvironment(JNIEnv* env);

// 2026-06-28: SQLite JNI group (android_database_SQLite{Connection,Global,Debug}.cpp).
extern int register_android_database_SQLiteConnection(JNIEnv* env);
extern int register_android_database_SQLiteGlobal(JNIEnv* env);
extern int register_android_database_SQLiteDebug(JNIEnv* env);
extern int register_android_database_CursorWindow(JNIEnv* env);

// [STAGE2-UNITY 2026-06-28] android.opengl.EGL14 JNI (android_opengl_EGL14_adapter.cpp,
// AOSP port minus SurfaceTexture/libgui path; window via ANativeWindow_fromSurface).
// Needed for pure-Java EGL apps (eglprobe render-bridge proof). Unity uses native
// libEGL directly so doesn't need this; harmless to register.
extern int register_android_opengl_jni_EGL14(JNIEnv* env);

// 2026-07-10 (L12 视频探针): register_android_media_MediaPlayer — 49 个 native
// 方法的桩实现（android_media_MediaPlayer.cpp）。Java 类 android.media.
// MediaPlayer 本身已在 framework.jar 里（AOSP 真源随 framework.jar 整体编译
// 带入，不属于 mainline-stubs 范畴），此前 kRegJNI[] 从未注册它的任何 native
// 方法 —— 任何触碰 MediaPlayer 的调用都会在 native_init 这一步就
// UnsatisfiedLinkError（类的 static 初始化块会立即调 native_init）。这是
// L12"视频/媒体插件"楼层第一个具体实现：不做真实解码（没有 mediaserver/
// libstagefright），只保证类可加载、生命周期方法不崩溃、Surface 能交接到
// 已验证的 ANativeWindow_fromSurface 路径。详见文件头注释的完整证据链和
// 明确的能力边界（不写像素、不真解码）。
extern int register_android_media_MediaPlayer(JNIEnv* env);

// BoatAttack FMOD's Java AudioTrack backend reaches AudioFormat.<clinit>,
// which initializes these three AudioSystem framework capability constants.
extern __attribute__((visibility("hidden")))
int register_android_media_AudioSystemCapabilities(JNIEnv* env);
extern __attribute__((visibility("hidden")))
int register_android_media_AudioProductStrategy(JNIEnv* env);
extern __attribute__((visibility("hidden")))
int register_android_media_AudioTrack(JNIEnv* env);

// [STAGE2-GL 2026-06-28] Whole android.opengl.GLES2/3 family, ported from AOSP
// android_opengl_GLES{20,30,31}.cpp.  Registered fault-tolerantly below (see
// kRegJNI_GL).  Externs declared at GLOBAL scope above (raw AOSP sources put
// these in the global namespace, not namespace android).  Needed for pure-Java
// GLES apps (eglprobe glClear red) and Unity (GLES2/3 Java bindings).

// Phase 2 r27 (2026-04-28): all graphics register_X functions
// (Paint/Canvas/RenderNode/HardwareRenderer/Matrix/Path/...) come from real
// cross-compiled libhwui.so via dlopen+dlsym in startReg below.  Stub
// register_android_graphics_Canvas / HardwareRenderer / RenderNode / Paint
// are retired (no longer compiled into liboh_android_runtime).

struct RegJNIRec {
    const char* name;
    int (*proc)(JNIEnv*);
};

// Dispatch table. Grows as we port more AOSP register_* functions.
static const RegJNIRec kRegJNI[] = {
    { "register_android_util_Log",            register_android_util_Log },
    { "register_android_util_EventLog",       register_android_util_EventLog },
    { "register_android_app_Activity",        register_android_app_Activity },
    { "register_android_os_SystemProperties", register_android_os_SystemProperties },
    { "register_android_os_Trace",            register_android_os_Trace },
    { "register_android_os_Process",          register_android_os_Process },
    { "register_android_os_SystemClock",      register_android_os_SystemClock },
    { "register_android_os_Binder",           register_android_os_Binder },
    // 2026-06-29 [STAGE2-UNITY wall#3]: android.os.Debug native heap trio.
    // UnityPlayer.initJni() calls getNativeHeapAllocatedSize / Size / FreeSize
    // before the Activity draws; missing natives → UnsatisfiedLinkError abort
    // in performLaunchActivity. Backed by musl mallinfo2(); getMemoryInfo is a
    // no-op (profiler-only, no smaps/PSS layer on OH).
    { "register_android_os_Debug",            register_android_os_Debug },
    // 2026-06-29 [STAGE2-UNITY wall#4]: android.hardware.SystemSensorManager.
    // UnityPlayer.toggleGyroscopeSensor (jadx :1051) does
    // getSystemService("sensor"); the SystemSensorManager ctor unconditionally
    // calls nativeClassInit/nativeCreate/nativeGetSensorAtIndex → hard
    // UnsatisfiedLinkError abort if unregistered. Zero-sensor stub (empty list)
    // makes getDefaultSensor(11) return null and registerListener(...,null,...)
    // return false gracefully — same as a real no-gyro device; design-consistent
    // with the NDK ASensor "zero sensors" stub.
    { "register_android_hardware_SensorManager", register_android_hardware_SensorManager },
    // 2026-05-07 G2.14u: AOSP-ported android_os_Parcel.cpp providing
    // ~30 Parcel native methods (nativeCreate / nativeWriteToParcel /
    // nativeMarshall / etc).  HelloWorld TextView path → ViewRootImpl
    // .performTraversals → relayoutWindow → adapter WindowSessionAdapter
    // .relayout → SurfaceControl.<init> → Parcel.obtain → Parcel.<init>
    // → Parcel.nativeCreate UnsatisfiedLinkError before this entry.
    { "register_android_os_Parcel",           register_android_os_Parcel },
    { "register_android_view_SurfaceControl", register_android_view_SurfaceControl },
    { "register_android_view_SurfaceSession", register_android_view_SurfaceSession },
    { "register_android_view_DisplayEventReceiver", register_android_view_DisplayEventReceiver },
    { "register_android_view_InputChannel",   register_android_view_InputChannel },
    { "register_android_view_KeyCharacterMap", register_android_view_KeyCharacterMap },
    // 2026-05-18: MotionEvent JNI must register BEFORE InputEventReceiver
    // so the worker-thread MotionEvent.obtain JNI lookup (cached in
    // ensureJavaRefs at first dispatch) finds nativeInitialize already
    // bound.  Both register_X are last-wins-safe regardless of order.
    //
    // 2026-05-18 (Plan A): restored.  Now backed by adapter-private
    // android_view_MotionEvent_aosp.cpp (replaces AOSP direct-reference
    // MotionEvent.cpp; class layout under adapter control, no ABI drift).
    { "register_android_view_MotionEvent",    register_android_view_MotionEvent },
    // 2026-05-26: KeyEvent natives (nativeNextId) — register before
    // InputEventReceiver, same rationale as MotionEvent above: the worker
    // thread's dispatchKeyFromWorker constructs KeyEvent via JNI NewObject,
    // whose <init> calls nativeNextId.  Order-independent (last-wins-safe).
    { "register_android_view_KeyEvent",       register_android_view_KeyEvent },
    { "register_android_view_InputEventReceiver", register_android_view_InputEventReceiver },
    { "register_android_content_AssetManager", register_android_content_AssetManager },
    { "register_android_os_MessageQueue",     register_android_os_MessageQueue },
    { "register_android_content_res_ApkAssets", register_android_content_res_ApkAssets },
    { "register_android_content_StringBlock", register_android_content_StringBlock },
    { "register_android_content_XmlBlock",    register_android_content_XmlBlock },
    { "register_com_android_internal_os_ClassLoaderFactory", register_com_android_internal_os_ClassLoaderFactory },
    { "register_com_android_internal_util_VirtualRefBasePtr", register_com_android_internal_util_VirtualRefBasePtr },
    { "register_android_graphics_Typeface",   register_android_graphics_Typeface },
    { "register_android_os_GraphicsEnvironment", register_android_os_GraphicsEnvironment },
    // 2026-05-02 audit: kept; see libcore_util_NativeAllocationRegistry_guard.cpp
    // header.  TODO P1: identify implicit dep then replace + remove.
    { "register_libcore_util_NativeAllocationRegistry_guard",
      register_libcore_util_NativeAllocationRegistry_guard },
    { "register_android_animation_PropertyValuesHolder",
      register_android_animation_PropertyValuesHolder },
    // 2026-06-28: SQLite JNI group — Room/androidx.sqlite calls
    // android.database.sqlite.SQLiteConnection.nativeOpen which was
    // UnsatisfiedLinkError'ing (no register_X covered it).  These three port
    // the AOSP frameworks/base/core/jni/android_database_* register functions;
    // sqlite3 itself is the AOSP amalgamation (external/sqlite/dist/sqlite3.c)
    // compiled into this .so, with a no-ICU sqlite3_android shim.  CursorWindow
    // JNI is included too; its two Parcel-marshalling natives are stubbed (OH
    // has no Binder) — Room accesses cursors in-process only.
    { "register_android_database_SQLiteConnection",
      register_android_database_SQLiteConnection },
    { "register_android_database_SQLiteGlobal",
      register_android_database_SQLiteGlobal },
    { "register_android_database_SQLiteDebug",
      register_android_database_SQLiteDebug },
    { "register_android_database_CursorWindow",
      register_android_database_CursorWindow },
    // [STAGE2-UNITY 2026-06-28] EGL14 Java JNI (eglprobe render-bridge proof).
    { "register_android_opengl_jni_EGL14",
      register_android_opengl_jni_EGL14 },
    { "register_android_media_AudioSystemCapabilities",
      register_android_media_AudioSystemCapabilities },
    { "register_android_media_AudioProductStrategy",
      register_android_media_AudioProductStrategy },
    { "register_android_media_AudioTrack",
      register_android_media_AudioTrack },
    // 2026-07-10 (L12 视频探针): see extern decl above for full rationale.
    { "register_android_media_MediaPlayer",
      register_android_media_MediaPlayer },
    // Phase 2 (r27): graphics natives provided by real libhwui.so via dlopen
    // block in startReg below — see kHwuiRegFns table.
};

static constexpr size_t kRegJNICount = sizeof(kRegJNI) / sizeof(kRegJNI[0]);

// 2026-05-01 G2.14n: hook RegisterNatives to dump every (class, method, sig, fnPtr)
// registration. Goal: identify which Java method's ArtMethod entry_point is being
// set to a corrupted address that lands in lib .bss when later invoked via
// art_quick_invoke_stub_internal blx r12 → SIGILL.
namespace {
using OrigRegisterNatives = jint (*)(JNIEnv*, jclass, const JNINativeMethod*, jint);
static OrigRegisterNatives g_orig_register_natives = nullptr;

static jint hooked_RegisterNatives(JNIEnv* env, jclass clazz,
                                    const JNINativeMethod* methods, jint nMethods) {
    // Resolve class name for logging. Use stack buffer to avoid heap allocation
    // here (we re-enter JNI carefully — no recursion into RegisterNatives).
    char className[256] = "?";
    if (clazz) {
        // Use original FindClass/GetMethodID/CallObjectMethod/GetStringUTFChars
        // through env->functions, but those are unaffected by our hook (only
        // RegisterNatives is patched).
        jclass cls = env->GetObjectClass(clazz);  // returns Class.class
        if (cls) {
            jmethodID mGetName = env->GetMethodID(cls, "getName", "()Ljava/lang/String;");
            if (mGetName) {
                jstring nameStr = (jstring)env->CallObjectMethod(clazz, mGetName);
                if (nameStr) {
                    const char* utf = env->GetStringUTFChars(nameStr, nullptr);
                    if (utf) {
                        snprintf(className, sizeof(className), "%s", utf);
                        env->ReleaseStringUTFChars(nameStr, utf);
                    }
                    env->DeleteLocalRef(nameStr);
                }
            }
            env->DeleteLocalRef(cls);
        }
        if (env->ExceptionCheck()) env->ExceptionClear();
    }
    for (jint i = 0; i < nMethods; i++) {
        // 2026-05-02 G2.14n+: enhanced flagging for suspicious fnPtr.
        // SIGILL crash signature: PC ends in f98 (ARM) or f99 (Thumb bit set)
        // and falls inside libskia_canvaskit.z.so .text. Flag both criteria.
        uintptr_t fp = (uintptr_t)methods[i].fnPtr;
        uintptr_t pageOff = fp & 0xFFFu;
        bool offHit = (pageOff == 0xf98u) || (pageOff == 0xf99u);
        bool libHit = false;
        const char* libName = "?";
        Dl_info info;
        if (methods[i].fnPtr && dladdr(methods[i].fnPtr, &info) && info.dli_fname) {
            libName = info.dli_fname;
            if (strstr(info.dli_fname, "libskia_canvaskit") != nullptr) libHit = true;
        }
        const char* tag = (offHit || libHit) ? "OH_RegHook_BAD" : "OH_RegHook";
        HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, tag,
            "%{public}s%{public}s::%{public}s%{public}s -> fn=%{public}p (lib=%{public}s pageOff=0x%{public}x)",
            (offHit || libHit) ? "[!!! SUSPECT] " : "",
            className,
            methods[i].name ? methods[i].name : "?",
            methods[i].signature ? methods[i].signature : "?",
            methods[i].fnPtr, libName, pageOff);
    }
    return g_orig_register_natives(env, clazz, methods, nMethods);
}

static void install_register_natives_hook(JNIEnv* env) {
    if (g_orig_register_natives) return;  // already installed
    // env->functions is `const struct JNINativeInterface*`. We allocate a copy
    // we can patch, then point env->functions at the copy.
    static struct JNINativeInterface patched;
    const struct JNINativeInterface* orig =
        *(const struct JNINativeInterface**)env;
    memcpy(&patched, orig, sizeof(patched));
    g_orig_register_natives = orig->RegisterNatives;
    patched.RegisterNatives = hooked_RegisterNatives;
    // Cast away const and overwrite the JNIEnv's functions pointer.
    *(const struct JNINativeInterface**)env = &patched;
    HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_RegHook",
        "RegisterNatives hook INSTALLED orig=%{public}p hook=%{public}p",
        (void*)g_orig_register_natives, (void*)hooked_RegisterNatives);
}
}  // namespace

// ===== [port-a1a2d4 2026-07-30] Tier A1/A2 TLS §441+JSSE + D4 §404 (westlake-piercing port, verbatim blocks) =====
static void WestlakeRegisterJsseShim(JNIEnv* env) {
    jclass provCls = env->FindClass("adapter/compat/WestlakeJsseProvider");
    if (provCls == nullptr) {
        env->ExceptionClear();
        fprintf(stderr, "[WESTLAKE-JSSE] adapter.compat.WestlakeJsseProvider NOT FOUND\n");
        fflush(stderr);
        return;
    }
    jmethodID ctor = env->GetMethodID(provCls, "<init>", "()V");
    jobject prov = (ctor != nullptr) ? env->NewObject(provCls, ctor) : nullptr;
    if (prov == nullptr) {
        env->ExceptionDescribe();
        env->ExceptionClear();
        fprintf(stderr, "[WESTLAKE-JSSE] could not construct provider\n");
        fflush(stderr);
        return;
    }
    jclass secCls = env->FindClass("java/security/Security");
    jmethodID add = (secCls != nullptr)
            ? env->GetStaticMethodID(secCls, "addProvider", "(Ljava/security/Provider;)I")
            : nullptr;
    if (add == nullptr) {
        env->ExceptionClear();
        fprintf(stderr, "[WESTLAKE-JSSE] Security.addProvider not found\n");
        fflush(stderr);
        return;
    }
    jint rc = env->CallStaticIntMethod(secCls, add, prov);
    if (env->ExceptionCheck()) { env->ExceptionDescribe(); env->ExceptionClear(); }
    fprintf(stderr, "[WESTLAKE-JSSE] Security.addProvider(WestlakeJSSE) rc=%d\n", (int) rc);
    fflush(stderr);
}

// WESTLAKE §404 — repair java.lang.invoke classes that arrive INITIALISED but EMPTY.
//
// §202 established that some classes reach this child already marked initialised even though
// their <clinit> never ran in any process, so their `static final` reference fields stay null
// forever and ART never reports an initialisation failure.  libart carries a hardcoded repair
// for java.io.BufferedInputStream (class_linker.cc `[WESTLAKE-REPAIR]`); this is the same repair,
// done from the bridge so it can cover a list of classes without rebuilding libart.
//
// The class that matters here is java.lang.invoke.MethodType: `internTable` is null, and
// MethodType.makeImpl()'s very first statement is `internTable.get(...)`, so EVERY
// invokedynamic / Kotlin-lambda path throws
//   NullPointerException: Attempt to invoke InvokeType(2) method
//   'java.lang.Object java.lang.invoke.MethodType$ConcurrentWeakInternSet.get(java.lang.Object)'
//   on a null object reference
// (§403 counted ~3100 of these in one run).  noice's click listeners are all Kotlin lambdas, so
// this is what makes every delivered touch abort the child.
//
// Detection is allow-listed on purpose: a null static reference field is perfectly legal in
// general, so it cannot be used as a global test (same reasoning as the libart repair).
//
// Repair = invoke <clinit> directly.  ART's GetStaticMethodID resolves "<clinit>" like any other
// direct static method, which is exactly what libart's repair does natively.
static bool wl_class_has_null_static_ref(JNIEnv* env, jclass cls, const char* desc) {
    // Enumerate static fields reflectively: JNI has no field iteration.
    jclass clsCls = env->FindClass("java/lang/Class");
    jclass fieldCls = env->FindClass("java/lang/reflect/Field");
    jclass modCls = env->FindClass("java/lang/reflect/Modifier");
    if (!clsCls || !fieldCls || !modCls) { if (env->ExceptionCheck()) env->ExceptionClear(); return false; }
    jmethodID getDF = env->GetMethodID(clsCls, "getDeclaredFields", "()[Ljava/lang/reflect/Field;");
    jmethodID getMod = env->GetMethodID(fieldCls, "getModifiers", "()I");
    jmethodID getType = env->GetMethodID(fieldCls, "getType", "()Ljava/lang/Class;");
    jmethodID getName = env->GetMethodID(fieldCls, "getName", "()Ljava/lang/String;");
    jmethodID setAcc = env->GetMethodID(fieldCls, "setAccessible", "(Z)V");
    jmethodID fGet = env->GetMethodID(fieldCls, "get", "(Ljava/lang/Object;)Ljava/lang/Object;");
    jmethodID isPrim = env->GetMethodID(clsCls, "isPrimitive", "()Z");
    jmethodID isStatic = env->GetStaticMethodID(modCls, "isStatic", "(I)Z");
    if (!getDF || !getMod || !getType || !getName || !setAcc || !fGet || !isPrim || !isStatic) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        return false;
    }
    jobjectArray fields = static_cast<jobjectArray>(env->CallObjectMethod(cls, getDF));
    if (env->ExceptionCheck()) { env->ExceptionClear(); return false; }
    if (fields == nullptr) return false;
    bool needs = false;
    const jsize n = env->GetArrayLength(fields);
    for (jsize i = 0; i < n && !needs; ++i) {
        jobject f = env->GetObjectArrayElement(fields, i);
        if (f == nullptr) continue;
        const jint mods = env->CallIntMethod(f, getMod);
        if (!env->CallStaticBooleanMethod(modCls, isStatic, mods)) { env->DeleteLocalRef(f); continue; }
        jobject ftype = env->CallObjectMethod(f, getType);
        const bool prim = ftype ? (env->CallBooleanMethod(ftype, isPrim) == JNI_TRUE) : true;
        if (ftype) env->DeleteLocalRef(ftype);
        if (prim) { env->DeleteLocalRef(f); continue; }
        env->CallVoidMethod(f, setAcc, JNI_TRUE);
        if (env->ExceptionCheck()) env->ExceptionClear();
        jobject val = env->CallObjectMethod(f, fGet, nullptr);
        if (env->ExceptionCheck()) { env->ExceptionClear(); env->DeleteLocalRef(f); continue; }
        if (val == nullptr) {
            jstring jn = static_cast<jstring>(env->CallObjectMethod(f, getName));
            const char* nm = jn ? env->GetStringUTFChars(jn, nullptr) : nullptr;
            fprintf(stderr, "[WESTLAKE-404] %s: static ref field '%s' is NULL\n",
                    desc, nm ? nm : "?");
            if (jn && nm) env->ReleaseStringUTFChars(jn, nm);
            if (jn) env->DeleteLocalRef(jn);
            needs = true;
        } else {
            env->DeleteLocalRef(val);
        }
        env->DeleteLocalRef(f);
    }
    env->DeleteLocalRef(fields);
    if (env->ExceptionCheck()) env->ExceptionClear();
    return needs;
}

void wl_repair_invoke_classes(JNIEnv* env) {  // [port-h5-second-pass 2026-07-30] external linkage for setArgV0Native hitchhike (cc6 7945f723 首选裁定)
    // [port-h5-second-pass 2026-07-30] H5: guard de-one-shot-ified — re-entry rescans;
    // already-repaired classes probe non-null and fast-skip (payload idempotent by design).
    static int wl_pass_no = 0;
    wl_pass_no++;
    fprintf(stderr, "[WESTLAKE-404] invoke-class repair pass %d begin\n", wl_pass_no);
    // MethodType first: everything else in java.lang.invoke depends on it.
    static const char* kClasses[] = {
        "java/lang/invoke/MethodType",
        "java/lang/invoke/MethodTypeForm",
        "java/lang/invoke/MethodHandleStatics",
        "java/lang/invoke/MethodHandleNatives",
        "java/lang/invoke/MethodHandles",
        "java/lang/invoke/MethodHandleImpl",
        "java/lang/invoke/LambdaMetafactory",
        "java/lang/invoke/InnerClassLambdaMetafactory",
        "java/lang/invoke/Invokers",
        "java/lang/invoke/CallSite",
    };
    for (const char* desc : kClasses) {
        if (env->PushLocalFrame(64) < 0) { continue; }
        jclass cls = env->FindClass(desc);
        if (cls == nullptr || env->ExceptionCheck()) {
            env->ExceptionClear();
            fprintf(stderr, "[WESTLAKE-404] %s: not found\n", desc);
            env->PopLocalFrame(nullptr);
            continue;
        }
        if (wl_class_has_null_static_ref(env, cls, desc)) {
            jmethodID clinit = env->GetStaticMethodID(cls, "<clinit>", "()V");
            if (env->ExceptionCheck()) { env->ExceptionClear(); clinit = nullptr; }
            if (clinit != nullptr) {
                env->CallStaticVoidMethod(cls, clinit);
                if (env->ExceptionCheck()) {
                    fprintf(stderr, "[WESTLAKE-404] %s: <clinit> THREW:\n", desc);
                    env->ExceptionDescribe();
                    env->ExceptionClear();
                }
                const bool still = wl_class_has_null_static_ref(env, cls, desc);
                fprintf(stderr, "[WESTLAKE-404] %s: direct <clinit> done, stillNull=%d\n",
                        desc, still ? 1 : 0);
            } else {
                fprintf(stderr, "[WESTLAKE-404] %s: no <clinit> method to invoke\n", desc);
            }
        } else {
            fprintf(stderr, "[WESTLAKE-404] %s: statics OK\n", desc);
        }
        env->PopLocalFrame(nullptr);
    }
    // Last resort for the one field that actually blocks input: build the intern set by hand.
    // MethodType.makeImpl() only needs `internTable` to be non-null to stop NPE-ing.
    if (env->PushLocalFrame(16) >= 0) {
        jclass mt = env->FindClass("java/lang/invoke/MethodType");
        if (env->ExceptionCheck()) env->ExceptionClear();
        jfieldID it = mt ? env->GetStaticFieldID(mt, "internTable",
            "Ljava/lang/invoke/MethodType$ConcurrentWeakInternSet;") : nullptr;
        if (env->ExceptionCheck()) { env->ExceptionClear(); it = nullptr; }
        jobject cur = it ? env->GetStaticObjectField(mt, it) : nullptr;
        fprintf(stderr, "[WESTLAKE-404] MethodType.internTable fid=%d null=%d\n",
                it ? 1 : 0, cur == nullptr ? 1 : 0);
        if (it != nullptr && cur == nullptr) {
            jclass setCls = env->FindClass("java/lang/invoke/MethodType$ConcurrentWeakInternSet");
            if (env->ExceptionCheck()) env->ExceptionClear();
            jmethodID ctor = setCls ? env->GetMethodID(setCls, "<init>", "()V") : nullptr;
            if (env->ExceptionCheck()) { env->ExceptionClear(); ctor = nullptr; }
            jobject inst = ctor ? env->NewObject(setCls, ctor) : nullptr;
            if (env->ExceptionCheck()) { env->ExceptionDescribe(); env->ExceptionClear(); inst = nullptr; }
            if (inst != nullptr) {
                env->SetStaticObjectField(mt, it, inst);
                if (env->ExceptionCheck()) { env->ExceptionDescribe(); env->ExceptionClear(); }
                jobject chk = env->GetStaticObjectField(mt, it);
                fprintf(stderr, "[WESTLAKE-404] internTable INSTALLED by hand, nowNull=%d\n",
                        chk == nullptr ? 1 : 0);
            } else {
                fprintf(stderr, "[WESTLAKE-404] could not construct ConcurrentWeakInternSet\n");
            }
        }
        env->PopLocalFrame(nullptr);
    }
    if (env->ExceptionCheck()) env->ExceptionClear();
    fflush(stderr);
}

// ===================== WESTLAKE §441: REAL TLS (was a passthrough stub) =====================
// adapter.compat.WestlakeSSLSocketFactory used to hand OkHttp back the *plain* socket, so the app
// spoke cleartext HTTP to port 443; the server hung up and OkHttp reported
// "EOFException: \n not found: limit=0". This implements the TLS client at the ABI boundary
// (the westlake way) on top of OHOS's own OpenSSL 3.x, which ships on the device:
//   /system/lib64/platformsdk/libssl_openssl.z.so  +  libcrypto_openssl.z.so
// Certificates are really verified against /etc/ssl/certs/cacert.pem, and the hostname is checked
// by OpenSSL itself via SSL_set1_host (OkHttp's OkHostnameVerifier then checks it a second time
// using the leaf certificate we hand back through getPeerCertificates()).
namespace {

struct WlSslApi {
    void* libssl = nullptr;
    void* libcrypto = nullptr;
    const void* (*TLS_client_method)();
    void* (*SSL_CTX_new)(const void*);
    int   (*SSL_CTX_load_verify_locations)(void*, const char*, const char*);
    void  (*SSL_CTX_set_verify)(void*, int, void*);
    void* (*SSL_new)(void*);
    int   (*SSL_set_fd)(void*, int);
    long  (*SSL_ctrl)(void*, int, long, void*);
    int   (*SSL_set1_host)(void*, const char*);
    int   (*SSL_connect)(void*);
    int   (*SSL_read)(void*, void*, int);
    int   (*SSL_write)(void*, const void*, int);
    int   (*SSL_get_error)(const void*, int);
    long  (*SSL_get_verify_result)(const void*);
    void* (*SSL_get1_peer_certificate)(const void*);
    const char* (*SSL_get_version)(const void*);
    const void* (*SSL_get_current_cipher)(const void*);
    const char* (*SSL_CIPHER_get_name)(const void*);
    int   (*SSL_shutdown)(void*);
    void  (*SSL_free)(void*);
    int   (*i2d_X509)(void*, unsigned char**);
    void  (*X509_free)(void*);
    void* ctx = nullptr;
    bool  ready = false;
    bool  tried = false;
};
static WlSslApi g_tls;
static pthread_mutex_t g_tls_lock = PTHREAD_MUTEX_INITIALIZER;

static const char* kCaFile = "/etc/ssl/certs/cacert.pem";

static void* wl_tls_dlopen(const char* const* names) {
    for (int i = 0; names[i] != nullptr; i++) {
        void* h = dlopen(names[i], RTLD_NOW | RTLD_GLOBAL);
        if (h != nullptr) {
            fprintf(stderr, "[WESTLAKE-441] dlopen %s OK\n", names[i]);
            return h;
        }
    }
    return nullptr;
}

#define WL_TLS_SYM(handle, field)                                                   \
    do {                                                                            \
        g_tls.field = reinterpret_cast<decltype(g_tls.field)>(dlsym(handle, #field)); \
        if (g_tls.field == nullptr) {                                               \
            fprintf(stderr, "[WESTLAKE-441] MISSING symbol %s\n", #field);          \
            missing++;                                                              \
        }                                                                           \
    } while (0)

static bool wl_tls_init() {
    pthread_mutex_lock(&g_tls_lock);
    if (g_tls.tried) { pthread_mutex_unlock(&g_tls_lock); return g_tls.ready; }
    g_tls.tried = true;

    static const char* kSslNames[] = {
        "libssl_openssl.z.so",
        "/system/lib64/platformsdk/libssl_openssl.z.so",
        "/system/lib64/chipset-sdk/libssl_openssl.z.so", nullptr };
    static const char* kCryptoNames[] = {
        "libcrypto_openssl.z.so",
        "/system/lib64/platformsdk/libcrypto_openssl.z.so",
        "/system/lib64/chipset-sdk-sp/libcrypto_openssl.z.so", nullptr };
    g_tls.libssl    = wl_tls_dlopen(kSslNames);
    g_tls.libcrypto = wl_tls_dlopen(kCryptoNames);
    if (g_tls.libssl == nullptr || g_tls.libcrypto == nullptr) {
        fprintf(stderr, "[WESTLAKE-441] dlopen FAILED ssl=%p crypto=%p err=%s\n",
                g_tls.libssl, g_tls.libcrypto, dlerror());
        fflush(stderr); pthread_mutex_unlock(&g_tls_lock); return false;
    }

    int missing = 0;
    void* s = g_tls.libssl;
    WL_TLS_SYM(s, TLS_client_method);      WL_TLS_SYM(s, SSL_CTX_new);
    WL_TLS_SYM(s, SSL_CTX_load_verify_locations); WL_TLS_SYM(s, SSL_CTX_set_verify);
    WL_TLS_SYM(s, SSL_new);                WL_TLS_SYM(s, SSL_set_fd);
    WL_TLS_SYM(s, SSL_ctrl);               WL_TLS_SYM(s, SSL_set1_host);
    WL_TLS_SYM(s, SSL_connect);            WL_TLS_SYM(s, SSL_read);
    WL_TLS_SYM(s, SSL_write);              WL_TLS_SYM(s, SSL_get_error);
    WL_TLS_SYM(s, SSL_get_verify_result);  WL_TLS_SYM(s, SSL_get1_peer_certificate);
    WL_TLS_SYM(s, SSL_get_version);        WL_TLS_SYM(s, SSL_get_current_cipher);
    WL_TLS_SYM(s, SSL_CIPHER_get_name);    WL_TLS_SYM(s, SSL_shutdown);
    WL_TLS_SYM(s, SSL_free);
    void* c = g_tls.libcrypto;
    WL_TLS_SYM(c, i2d_X509);               WL_TLS_SYM(c, X509_free);
    if (missing > 0) {
        fprintf(stderr, "[WESTLAKE-441] %d symbol(s) missing — TLS unavailable\n", missing);
        fflush(stderr); pthread_mutex_unlock(&g_tls_lock); return false;
    }

    g_tls.ctx = g_tls.SSL_CTX_new(g_tls.TLS_client_method());
    if (g_tls.ctx == nullptr) {
        fprintf(stderr, "[WESTLAKE-441] SSL_CTX_new FAILED\n");
        fflush(stderr); pthread_mutex_unlock(&g_tls_lock); return false;
    }
    const int loaded = g_tls.SSL_CTX_load_verify_locations(g_tls.ctx, kCaFile, nullptr);
    // SSL_VERIFY_PEER = 1. Keep verification ON: a silently-insecure client is worse than none.
    g_tls.SSL_CTX_set_verify(g_tls.ctx, 1, nullptr);
    fprintf(stderr, "[WESTLAKE-441] SSL_CTX ready ca=%s loaded=%d verify=PEER\n", kCaFile, loaded);
    fflush(stderr);
    g_tls.ready = (loaded == 1);
    if (!g_tls.ready) {
        fprintf(stderr, "[WESTLAKE-441] CA bundle did NOT load — refusing to run unverified\n");
        fflush(stderr);
    }
    pthread_mutex_unlock(&g_tls_lock);
    return g_tls.ready;
}

static void wl_tls_throw_io(JNIEnv* env, const char* what, int err) {
    char buf[192];
    snprintf(buf, sizeof(buf), "WestlakeTLS: %s failed (ssl_err=%d)", what, err);
    jclass ioe = env->FindClass("javax/net/ssl/SSLException");
    if (ioe == nullptr) { env->ExceptionClear(); ioe = env->FindClass("java/io/IOException"); }
    if (ioe != nullptr) env->ThrowNew(ioe, buf);
}

// Drive a would-block SSL op. Returns true to retry, false if it really failed/timed out.
static bool wl_tls_wait(int fd, int sslErr, int timeoutMs) {
    if (sslErr != 2 /*WANT_READ*/ && sslErr != 3 /*WANT_WRITE*/) return false;
    struct pollfd p;
    p.fd = fd;
    p.events = (sslErr == 2) ? POLLIN : POLLOUT;
    p.revents = 0;
    const int r = poll(&p, 1, timeoutMs);
    return r > 0;
}

// §447: dump the first few HTTP bytes each way so we can see the actual request/response.
static int g_tls_dump_count = 0;
static void wl_tls_dump(const char* op, const jbyte* data, int n) {
    if (g_tls_dump_count >= 6 || n <= 0) return;
    g_tls_dump_count++;
    const int cap = (n < 420) ? n : 420;
    std::string out;
    out.reserve((size_t)cap + 8);
    for (int i = 0; i < cap; i++) {
        const unsigned char c = (unsigned char)data[i];
        if (c == '\r') { out += "\\r"; }
        else if (c == '\n') { out += "\\n"; }
        else if (c >= 32 && c < 127) { out += (char)c; }
        else { out += '.'; }
    }
    fprintf(stderr, "[WESTLAKE-447] %s %d bytes: %s%s\n", op, n, out.c_str(),
            (n > cap) ? " ...(truncated)" : "");
    fflush(stderr);
}

// §446: bounded I/O tracing so a premature EOF can be told apart from a real one.
static int g_tls_io_logged = 0;
static void wl_tls_log_io(const char* op, const char* what, int n, int sslErr, int fd) {
    const bool interesting = (strcmp(what, "ok") != 0);
    if (!interesting && g_tls_io_logged >= 12) return;
    if (g_tls_io_logged >= 200) return;
    g_tls_io_logged++;
    fprintf(stderr, "[WESTLAKE-446] tls %s %s fd=%d n=%d ssl_err=%d errno=%s\n",
            op, what, fd, n, sslErr, (errno != 0) ? strerror(errno) : "-");
    fflush(stderr);
}

static jlong WL_TLS_handshake(JNIEnv* env, jclass, jint fd, jstring jhost, jint timeoutMs) {
    if (!wl_tls_init()) { wl_tls_throw_io(env, "init", 0); return 0; }
    const char* host = (jhost != nullptr) ? env->GetStringUTFChars(jhost, nullptr) : nullptr;

    void* ssl = g_tls.SSL_new(g_tls.ctx);
    if (ssl == nullptr) {
        if (host) env->ReleaseStringUTFChars(jhost, host);
        wl_tls_throw_io(env, "SSL_new", 0); return 0;
    }
    g_tls.SSL_set_fd(ssl, (int)fd);
    if (host != nullptr) {
        // SNI: SSL_CTRL_SET_TLSEXT_HOSTNAME=55, TLSEXT_NAMETYPE_host_name=0
        g_tls.SSL_ctrl(ssl, 55, 0, const_cast<char*>(host));
        g_tls.SSL_set1_host(ssl, host);   // OpenSSL-side hostname verification
    }

    const int deadline = (timeoutMs > 0) ? timeoutMs : 30000;
    int rc;
    for (;;) {
        rc = g_tls.SSL_connect(ssl);
        if (rc == 1) break;
        const int e = g_tls.SSL_get_error(ssl, rc);
        if (!wl_tls_wait((int)fd, e, deadline)) {
            fprintf(stderr, "[WESTLAKE-441] handshake FAILED host=%s rc=%d ssl_err=%d errno=%s\n",
                    host ? host : "?", rc, e, strerror(errno));
            fflush(stderr);
            g_tls.SSL_free(ssl);
            if (host) env->ReleaseStringUTFChars(jhost, host);
            wl_tls_throw_io(env, "handshake", e);
            return 0;
        }
    }
    const long vr = g_tls.SSL_get_verify_result(ssl);
    if (vr != 0 /*X509_V_OK*/) {
        fprintf(stderr, "[WESTLAKE-441] CERT VERIFY FAILED host=%s result=%ld\n",
                host ? host : "?", vr);
        fflush(stderr);
        g_tls.SSL_free(ssl);
        if (host) env->ReleaseStringUTFChars(jhost, host);
        wl_tls_throw_io(env, "certificate verification", (int)vr);
        return 0;
    }
    const char* ver = g_tls.SSL_get_version(ssl);
    const void* cip = g_tls.SSL_get_current_cipher(ssl);
    fprintf(stderr, "[WESTLAKE-441] HANDSHAKE OK host=%s proto=%s cipher=%s verify=OK\n",
            host ? host : "?", ver ? ver : "?",
            cip ? g_tls.SSL_CIPHER_get_name(cip) : "?");
    fflush(stderr);
    if (host) env->ReleaseStringUTFChars(jhost, host);
    return (jlong)(uintptr_t)ssl;
}

static jint WL_TLS_read(JNIEnv* env, jclass, jlong handle, jint fd, jbyteArray buf,
                        jint off, jint len, jint timeoutMs) {
    void* ssl = (void*)(uintptr_t)handle;
    if (ssl == nullptr || buf == nullptr) return -1;
    if (len <= 0) return 0;
    jbyte* tmp = (jbyte*)malloc((size_t)len);
    if (tmp == nullptr) return -1;
    const int deadline = (timeoutMs > 0) ? timeoutMs : 60000;
    int n;
    for (;;) {
        errno = 0;
        n = g_tls.SSL_read(ssl, tmp, len);
        if (n > 0) break;
        const int e = g_tls.SSL_get_error(ssl, n);
        if (e == 6 /*SSL_ERROR_ZERO_RETURN*/) {          // peer closed cleanly
            wl_tls_log_io("read", "peer closed (ZERO_RETURN)", n, e, fd);
            free(tmp); return -1;
        }
        if (e == 2 /*WANT_READ*/ || e == 3 /*WANT_WRITE*/) {
            if (!wl_tls_wait((int)fd, e, deadline)) {
                wl_tls_log_io("read", "poll timeout/error", n, e, fd);
                free(tmp); return -1;
            }
            continue;
        }
        // §446: SSL_ERROR_SYSCALL with a retryable errno is NOT end-of-stream. Treating it as EOF
        // is what produced OkHttp's "EOFException: \n not found: limit=0" on a healthy connection.
        if (e == 5 /*SSL_ERROR_SYSCALL*/ && n < 0 &&
            (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
            if (!wl_tls_wait((int)fd, 2 /*poll readable*/, deadline)) {
                wl_tls_log_io("read", "poll after EAGAIN failed", n, e, fd);
                free(tmp); return -1;
            }
            continue;
        }
        wl_tls_log_io("read", "fatal", n, e, fd);
        free(tmp); return -1;
    }
    env->SetByteArrayRegion(buf, off, n, tmp);
    wl_tls_dump("<-- recv", tmp, n);
    free(tmp);
    wl_tls_log_io("read", "ok", n, 0, fd);
    return n;
}

static jint WL_TLS_write(JNIEnv* env, jclass, jlong handle, jint fd, jbyteArray buf,
                         jint off, jint len, jint timeoutMs) {
    void* ssl = (void*)(uintptr_t)handle;
    if (ssl == nullptr || buf == nullptr) return -1;
    if (len <= 0) return 0;
    jbyte* tmp = (jbyte*)malloc((size_t)len);
    if (tmp == nullptr) return -1;
    env->GetByteArrayRegion(buf, off, len, tmp);
    wl_tls_dump("--> send", tmp, len);
    const int deadline = (timeoutMs > 0) ? timeoutMs : 60000;
    int done = 0;
    while (done < len) {
        errno = 0;
        const int n = g_tls.SSL_write(ssl, tmp + done, len - done);
        if (n > 0) { done += n; continue; }
        const int e = g_tls.SSL_get_error(ssl, n);
        if (e == 2 /*WANT_READ*/ || e == 3 /*WANT_WRITE*/) {
            if (!wl_tls_wait((int)fd, e, deadline)) {
                wl_tls_log_io("write", "poll timeout/error", n, e, fd);
                free(tmp); return -1;
            }
            continue;
        }
        if (e == 5 /*SSL_ERROR_SYSCALL*/ && n < 0 &&
            (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
            if (!wl_tls_wait((int)fd, 3 /*poll writable*/, deadline)) {
                wl_tls_log_io("write", "poll after EAGAIN failed", n, e, fd);
                free(tmp); return -1;
            }
            continue;
        }
        wl_tls_log_io("write", "fatal", n, e, fd);
        free(tmp); return -1;
    }
    free(tmp);
    wl_tls_log_io("write", "ok", done, 0, fd);
    return done;
}

static jbyteArray WL_TLS_peerCert(JNIEnv* env, jclass, jlong handle) {
    void* ssl = (void*)(uintptr_t)handle;
    if (ssl == nullptr) return nullptr;
    void* x = g_tls.SSL_get1_peer_certificate(ssl);
    if (x == nullptr) return nullptr;
    unsigned char* der = nullptr;
    const int n = g_tls.i2d_X509(x, &der);
    jbyteArray out = nullptr;
    if (n > 0 && der != nullptr) {
        out = env->NewByteArray(n);
        if (out != nullptr) env->SetByteArrayRegion(out, 0, n, (const jbyte*)der);
    }
    g_tls.X509_free(x);
    return out;
}

static jstring WL_TLS_info(JNIEnv* env, jclass, jlong handle, jint which) {
    void* ssl = (void*)(uintptr_t)handle;
    if (ssl == nullptr) return nullptr;
    if (which == 0) {
        const char* v = g_tls.SSL_get_version(ssl);
        return v ? env->NewStringUTF(v) : nullptr;
    }
    const void* c = g_tls.SSL_get_current_cipher(ssl);
    const char* n = c ? g_tls.SSL_CIPHER_get_name(c) : nullptr;
    return n ? env->NewStringUTF(n) : nullptr;
}

static void WL_TLS_close(JNIEnv*, jclass, jlong handle) {
    void* ssl = (void*)(uintptr_t)handle;
    if (ssl == nullptr) return;
    g_tls.SSL_shutdown(ssl);
    g_tls.SSL_free(ssl);
}

}  // namespace

static void wl_register_tls_natives(JNIEnv* env) {
    jclass cls = env->FindClass("adapter/compat/WestlakeSSLSocket");
    if (cls == nullptr || env->ExceptionCheck()) {
        env->ExceptionClear();
        fprintf(stderr, "[WESTLAKE-441] adapter/compat/WestlakeSSLSocket NOT FOUND — TLS off\n");
        fflush(stderr);
        return;
    }
    static const JNINativeMethod m[] = {
        {"nativeHandshake", "(ILjava/lang/String;I)J", reinterpret_cast<void*>(WL_TLS_handshake)},
        {"nativeRead",  "(JI[BIII)I", reinterpret_cast<void*>(WL_TLS_read)},
        {"nativeWrite", "(JI[BIII)I", reinterpret_cast<void*>(WL_TLS_write)},
        {"nativePeerCert", "(J)[B",   reinterpret_cast<void*>(WL_TLS_peerCert)},
        {"nativeInfo", "(JI)Ljava/lang/String;", reinterpret_cast<void*>(WL_TLS_info)},
        {"nativeClose", "(J)V",       reinterpret_cast<void*>(WL_TLS_close)},
    };
    const jint rc = env->RegisterNatives(cls, m, 6);
    if (env->ExceptionCheck()) env->ExceptionClear();
    fprintf(stderr, "[WESTLAKE-441] RegisterNatives(WestlakeSSLSocket) rc=%d\n", (int)rc);
    fflush(stderr);
    env->DeleteLocalRef(cls);
}
// ===== [port-a1a2d4 2026-07-30] end payload =====

int AndroidRuntime::startReg(JNIEnv* env) {
    if (::westlake_icu_early_init() != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 ICU early init failed; "
                "aborting startReg\n");
        return -1;
    }
    // Pre-register immediately after ICU admission, before any later startReg
    // module can initialize these Java classes and cache the previous native
    // finalizer. The tail registration remains mandatory: it repeats the same
    // fail-hard cohort after all other native writers so A3 still wins.
    if (::westlake_register_charset_natives(env) != 0 ||
        ::westlake_register_regex_natives(env) != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 ICU early registration failed; "
                "aborting startReg\n");
        return -1;
    }
    fprintf(stderr,
            "[liboh_android_runtime] A3 ICU PRE-REGISTERED "
            "NativeConverter=13/16 regex=15/15\n");

    fprintf(stderr, "[liboh_android_runtime] startReg entering (%zu modules)\n",
            kRegJNICount);

    WestlakeRegisterJsseShim(env);  // [port-a1a2d4 2026-07-30] §441 JSSE provider before any module registers

    // Cache JavaVM so AOSP-ported sources (ApkAssets.cpp et al.) can call
    // AndroidRuntime::getJavaVM() from callback-local central JNI admission.
    JavaVM* vm = nullptr;
    if (env->GetJavaVM(&vm) == JNI_OK) {
        setJavaVM(vm);
        fprintf(stderr, "[liboh_android_runtime] cached JavaVM=%p\n", (void*)vm);
    }

    // 2026-05-02 G2.14n+: install RegisterNatives audit hook unconditionally
    // for this debug iteration. Hook flags fnPtrs whose page offset is f98/f99
    // OR whose containing lib is libskia_canvaskit (per SIGILL signature).
    // Tag: OH_RegHook (normal) / OH_RegHook_BAD (suspicious).
    install_register_natives_hook(env);

    // 2026-05-02 G2.14r: bootstrap libjavacore.so by invoking its JNI_OnLoad
    // ONCE before our own kRegJNI loop runs.  Adapter never calls
    // System.loadLibrary("javacore") on the Java side, so absent this hook
    // libjavacore's 12 register_libcore_* / register_sun_misc_Unsafe /
    // register_java_lang_invoke_* / register_android_system_OsConstants
    // never run, leaving the corresponding native methods unbound.  ART can
    // intrinsify some (sun.misc.Unsafe atomics) but not e.g.
    // NativeAllocationRegistry.applyFreeFunction — first GC cycle calls it
    // and SEGV pc=0 follows (G2.14r root cause).  Calling JNI_OnLoad here
    // restores the canonical AOSP init flow once for the parent process;
    // child forks inherit the registrations.
    {
        void* libjc = dlopen("libjavacore.so", RTLD_NOW);
        if (libjc != nullptr) {
            using OnLoadFn = jint (*)(JavaVM*, void*);
            OnLoadFn onload = reinterpret_cast<OnLoadFn>(
                dlsym(libjc, "JNI_OnLoad"));
            if (onload != nullptr && vm != nullptr) {
                jint rc = onload(vm, nullptr);
                fprintf(stderr,
                    "[liboh_android_runtime] libjavacore JNI_OnLoad rc=0x%x %s\n",
                    rc, (rc == JNI_VERSION_1_6) ? "(OK)" : "(unexpected)");
                if (env->ExceptionCheck()) {
                    fprintf(stderr,
                        "[liboh_android_runtime] libjavacore JNI_OnLoad raised exception:\n");
                    env->ExceptionDescribe();
                    env->ExceptionClear();
                }
            } else {
                fprintf(stderr,
                    "[liboh_android_runtime] libjavacore JNI_OnLoad symbol missing or vm=null\n");
            }
        } else {
            fprintf(stderr,
                "[liboh_android_runtime] libjavacore.so dlopen FAILED: %s\n",
                dlerror() ? dlerror() : "(null)");
        }
    }

    // Bound a local-ref frame generously; each register_* may create a handful
    // of class / method references that won't be released until frame pop.
    if (env->PushLocalFrame(200) < 0) {
        fprintf(stderr, "[liboh_android_runtime] PushLocalFrame failed\n");
        return -1;
    }

    for (size_t i = 0; i < kRegJNICount; ++i) {
        int rc = kRegJNI[i].proc(env);
        if (rc < 0) {
            fprintf(stderr, "[liboh_android_runtime] %s failed (rc=%d)\n",
                    kRegJNI[i].name, rc);
            env->PopLocalFrame(nullptr);
            return -1;
        }
        fprintf(stderr, "[liboh_android_runtime]   ok %s\n", kRegJNI[i].name);
    }

    env->PopLocalFrame(nullptr);

    // ============================================================
    // [STAGE2-GL 2026-06-28] Batch-register the android.opengl.GLES* family
    // (GLES20/30/31/31Ext/32 + EGLExt) FAULT-TOLERANTLY.
    //
    // Why a separate, log+continue table (NOT folded into the strict kRegJNI[]
    // above, which 铁律-forbids SKIP): the GLESxx register_X functions cache
    // NO global jclass/jfieldID (each android_opengl_GLESxx.cpp nativeClassInit
    // is empty — verified), so a failed/absent one cannot cause the "NULL g*_
    // cache → far NULL-deref" trap the strict-table rule guards against.  The
    // GL bindings are optional-per-version (an app using only GLES20 must not
    // die because the GLES32 Java class is absent from framework.jar).  Running
    // them tolerantly lets ONE cold boot dump the FULL gap set instead of
    // aborting on the first miss.  Each entry's native impls call real OH
    // libGLESv2/libGLESv3 (linked); jniRegisterNativeMethods only binds the
    // method pointers here, GL is not invoked until the app draws.
    // ============================================================
    {
        static const RegJNIRec kRegJNI_GL[] = {
            { "register_android_opengl_jni_GLES20",    ::register_android_opengl_jni_GLES20 },
            { "register_android_opengl_jni_GLES30",    ::register_android_opengl_jni_GLES30 },
            { "register_android_opengl_jni_GLES31",    ::register_android_opengl_jni_GLES31 },
        };
        const size_t kRegJNI_GL_Count = sizeof(kRegJNI_GL) / sizeof(kRegJNI_GL[0]);
        int gl_ok = 0, gl_fail = 0;
        for (size_t i = 0; i < kRegJNI_GL_Count; ++i) {
            if (env->PushLocalFrame(128) < 0) {
                fprintf(stderr, "[STAGE2-GL] PushLocalFrame failed at %s\n", kRegJNI_GL[i].name);
                continue;
            }
            int rc = kRegJNI_GL[i].proc(env);
            // jniRegisterNativeMethods throws (e.g. ClassNotFound / NoSuchMethod)
            // on failure; clear it so the next entry + the rest of startup are clean.
            if (env->ExceptionCheck()) {
                env->ExceptionDescribe();
                env->ExceptionClear();
                rc = (rc < 0) ? rc : -2;
            }
            if (rc < 0) {
                fprintf(stderr, "[STAGE2-GL] MISSING %s (rc=%d)\n", kRegJNI_GL[i].name, rc);
                gl_fail++;
            } else {
                fprintf(stderr, "[STAGE2-GL] ok %s\n", kRegJNI_GL[i].name);
                gl_ok++;
            }
            env->PopLocalFrame(nullptr);
        }
        fprintf(stderr, "[STAGE2-GL] SUMMARY: %d ok, %d missing (of %zu GL register fns)\n",
                gl_ok, gl_fail, kRegJNI_GL_Count);
    }

    // ============================================================
    // Phase 2 (r27) — dlopen real libhwui.so + invoke its 27 register_X
    // functions to register Paint/Canvas/RenderNode/HardwareRenderer/...
    // graphics natives with REAL Skia-backed implementations.  No stubs.
    //
    // libhwui.so is OH-cross-built (DT_NEEDED: liboh_hwui_shim.so /
    // liboh_skia_rtti_shim.so / libskia_canvaskit.z.so / libEGL.so
    // / libGLESv3.so / libutils.so etc., all available on device).
    // Earlier r15 diag confirmed libhwui dlopen alone succeeds in JVM ctx.
    // ============================================================
    if (env->PushLocalFrame(50) >= 0) {
        const char* kHwuiPaths[] = {
            "/system/android/lib/libhwui.so",
            "libhwui.so",
        };
        void* hwui = nullptr;
        for (const char* p : kHwuiPaths) {
            hwui = dlopen(p, RTLD_NOW | RTLD_GLOBAL);
            if (hwui) {
                fprintf(stderr, "[liboh_android_runtime] dlopen %s OK\n", p);
                break;
            } else {
                fprintf(stderr, "[liboh_android_runtime] dlopen %s FAIL: %s\n",
                        p, dlerror());
            }
        }
        if (hwui) {
            // 45 register_X mangled symbol names extracted from libhwui.so
            // dynsym table (`llvm-readelf --dyn-syms ... | grep register_android`).
            // Mangled names use Itanium C++ ABI:
            //   - `_Z<len>register_android_*P7_JNIEnv` for global-namespace fns
            //   - `_ZN7android<len>register_android_*EP7_JNIEnv` for android:: fns
            using RegFn = int (*)(JNIEnv*);
            struct HwuiReg { const char* name; const char* sym; };
            static const HwuiReg kHwuiRegFns[] = {
                // 2026-05-07 G2.14s: Graphics is registered below, AFTER ColorSpace,
                // matching AOSP frameworks/base/libs/hwui/apex/jni_runtime.cpp:104-109
                // canonical order (Canvas, ColorSpace, Graphics, Bitmap, ...).
                // History blame for the prior SKIP: see the larger comment at the
                // ColorSpace → Graphics block below.
                {"BitmapFactory",                "_Z39register_android_graphics_BitmapFactoryP7_JNIEnv"},
                {"Matrix",                       "_ZN7android32register_android_graphics_MatrixEP7_JNIEnv"},
                {"BitmapRegionDecoder",          "_Z45register_android_graphics_BitmapRegionDecoderP7_JNIEnv"},
                {"Interpolator",                 "_Z38register_android_graphics_InterpolatorP7_JNIEnv"},
                {"CreateJavaOutputStreamAdaptor","_Z55register_android_graphics_CreateJavaOutputStreamAdaptorP7_JNIEnv"},
                {"PathMeasure",                  "_ZN7android37register_android_graphics_PathMeasureEP7_JNIEnv"},
                {"GraphicsStatsService",         "_Z46register_android_graphics_GraphicsStatsServiceP7_JNIEnv"},
                {"Picture",                      "_ZN7android33register_android_graphics_PictureEP7_JNIEnv"},
                {"ColorFilter",                  "_ZN7android37register_android_graphics_ColorFilterEP7_JNIEnv"},
                {"Camera",                       "_Z32register_android_graphics_CameraP7_JNIEnv"},
                {"Gainmap",                      "_ZN7android33register_android_graphics_GainmapEP7_JNIEnv"},
                {"Region",                       "_ZN7android32register_android_graphics_RegionEP7_JNIEnv"},
                {"Paint",                        "_ZN7android31register_android_graphics_PaintEP7_JNIEnv"},
                {"DisplayListCanvas",            "_ZN7android39register_android_view_DisplayListCanvasEP7_JNIEnv"},
                {"ByteBufferStreamAdaptor",      "_Z49register_android_graphics_ByteBufferStreamAdaptorP7_JNIEnv"},
                {"Movie",                        "_Z31register_android_graphics_MovieP7_JNIEnv"},
                {"Mesh",                         "_ZN7android30register_android_graphics_MeshEP7_JNIEnv"},
                {"ThreadedRenderer",             "_ZN7android38register_android_view_ThreadedRendererEP7_JNIEnv"},
                {"PathIterator",                 "_ZN7android38register_android_graphics_PathIteratorEP7_JNIEnv"},
                // 2026-04-30 G2.4 (graphics_jni_inventory §3.3): ColorSpace
                // must register BEFORE ImageDecoder/Bitmap/HardwareBufferRenderer.
                // ImageDecoder's register_X caches a jfieldID for ColorSpace
                // static field (e.g. SRGB).  If ColorSpace class isn't loaded
                // when ImageDecoder.cpp does GetStaticFieldID, the cached fid
                // stays null → first nGetColorSpace call CheckJNI-aborts with
                // "JNI DETECTED ERROR IN APPLICATION: fid == null".
                // (Was previously after ImageDecoder; moved up here.)
                {"ColorSpace",                   "_ZN7android36register_android_graphics_ColorSpaceEP7_JNIEnv"},
                // 2026-05-07 G2.14s: Graphics MUST be registered here — after ColorSpace
                // (which Graphics's register fn reads via gColorSpace_Named_class for
                // SRGB/EXTENDED_SRGB/etc fields) and before ANY Paint/Bitmap/Region/
                // Canvas native gets first invoked at runtime.
                //
                // register_android_graphics_Graphics initializes the file-static
                // globals gFontMetricsInt_class / gFontMetrics_class / gRect_class /
                // gRectF_class / gPoint_class / gPointF_class / gBitmapConfig_class /
                // gCanvas_class / gPicture_class / gRegion_class / gByte_class /
                // gVMRuntime_class / gColorSpace_class / gColorSpaceRGB_class /
                // gTransferParameters_class plus their associated fieldIDs in
                // libhwui's own translation units.  Paint.cpp's nGetFontMetricsInt
                // does `IsInstanceOf(metrics, gFontMetricsInt_class)` and SetIntField
                // on gFontMetricsInt_top/ascent/descent/bottom/leading — without this
                // call those globals stay NULL → JNI DETECTED ERROR aborts in CheckJNI.
                //
                // History blame: 2026-05-06 SKIPPED on the false-attribution theory
                // that adding Graphics required a boot image rebuild, which itself
                // had failed with `Class mismatch String objectSize 467 vs 459`
                // dex2oat ABI mismatch.  That ABI mismatch is an INDEPENDENT issue
                // (ART build flags drift vs device libart) and has nothing to do
                // with whether libhwui's register_X is invoked at startReg time.
                // Verification (2026-05-07):
                //   nm -D libhwui.so | grep register_android_graphics_Graphics
                //   → 000dedcd T _Z34register_android_graphics_GraphicsP7_JNIEnv
                // The symbol IS exported; dlsym at startReg succeeds; the call
                // initializes Graphics's LOCAL g_* globals (LOCAL is fine — same .so
                // internal access, see jni_Graphics.o objdump showing 'b' BSS for
                // _ZL18gFontMetrics_class etc).  Paint native then sees init'd globals.
                {"Graphics",                     "_Z34register_android_graphics_GraphicsP7_JNIEnv"},
                {"AnimatedImageDrawable",        "_Z56register_android_graphics_drawable_AnimatedImageDrawableP7_JNIEnv"},
                {"PathParser",                   "_ZN7android32register_android_util_PathParserEP7_JNIEnv"},
                {"TextureLayer",                 "_ZN7android38register_android_graphics_TextureLayerEP7_JNIEnv"},
                {"AnimatedVectorDrawable",       "_ZN7android57register_android_graphics_drawable_AnimatedVectorDrawableEP7_JNIEnv"},
                {"NativeInterpolatorFactory",    "_ZN7android61register_android_graphics_animation_NativeInterpolatorFactoryEP7_JNIEnv"},
                {"ImageDecoder",                 "_Z38register_android_graphics_ImageDecoderP7_JNIEnv"},
                {"RenderNode",                   "_ZN7android32register_android_view_RenderNodeEP7_JNIEnv"},
                {"DrawFilter",                   "_ZN7android36register_android_graphics_DrawFilterEP7_JNIEnv"},
                {"RenderEffect",                 "_Z38register_android_graphics_RenderEffectP7_JNIEnv"},
                {"NinePatch",                    "_Z35register_android_graphics_NinePatchP7_JNIEnv"},
                {"Canvas",                       "_ZN7android32register_android_graphics_CanvasEP7_JNIEnv"},
                {"HardwareBufferRenderer",       "_ZN7android48register_android_graphics_HardwareBufferRendererEP7_JNIEnv"},
                {"Bitmap",                       "_Z32register_android_graphics_BitmapP7_JNIEnv"},
                {"HardwareRendererObserver",     "_ZN7android50register_android_graphics_HardwareRendererObserverEP7_JNIEnv"},
                {"Path",                         "_ZN7android30register_android_graphics_PathEP7_JNIEnv"},
                {"Shader",                       "_Z32register_android_graphics_ShaderP7_JNIEnv"},
                {"VectorDrawable",               "_ZN7android49register_android_graphics_drawable_VectorDrawableEP7_JNIEnv"},
                {"MaskFilter",                   "_Z36register_android_graphics_MaskFilterP7_JNIEnv"},
                {"PathEffect",                   "_Z36register_android_graphics_PathEffectP7_JNIEnv"},
                {"RenderNodeAnimator",           "_ZN7android54register_android_graphics_animation_RenderNodeAnimatorEP7_JNIEnv"},
                {"CanvasProperty",               "_ZN7android40register_android_graphics_CanvasPropertyEP7_JNIEnv"},
                {"YuvImage",                     "_Z34register_android_graphics_YuvImageP7_JNIEnv"},
                {"FontFamily",                   "_ZN7android36register_android_graphics_FontFamilyEP7_JNIEnv"},
                {"MeshSpecification",            "_ZN7android43register_android_graphics_MeshSpecificationEP7_JNIEnv"},
                // 2026-05-02 G2.14r: NEW font API (android.graphics.fonts.*)
                // — required by AOSP SystemFonts.buildSystemFallback chain.
                // Without these, Font$Builder.nInitBuilder() throws
                // UnsatisfiedLinkError → setSystemFontMap NPE → handleBindApplication
                // fails → mInitialApplication = null → ConfigurationController NPE.
                // libhwui exports them via fonts/Font.cpp + fonts/FontFamily.cpp
                // (compiled into libhwui.so in G2.14q Path A).
                {"fonts.Font",                   "_ZN7android36register_android_graphics_fonts_FontEP7_JNIEnv"},
                {"fonts.FontFamily",             "_ZN7android42register_android_graphics_fonts_FontFamilyEP7_JNIEnv"},
                // 2026-05-07 G2.14t: text/* register fns required by AOSP
                // apex/jni_runtime.cpp:149-152.  Order kept identical to AOSP
                // (MeasuredText → LineBreaker → TextShaper → GraphemeBreak).
                //
                // Without these registered, HelloWorld TextView.onMeasure path
                // → StaticLayout.generate → LineBreaker$Builder.build →
                // LineBreaker.<clinit>:450 → nGetReleaseFunc() throws
                // UnsatisfiedLinkError (No implementation found for ...) →
                // ART runtime exception → AMS schedulerDied → kill -9 child.
                //
                // Build dependency: build/compile_libhwui_jni.sh must compile
                // frameworks/base/libs/hwui/jni/text/*.cpp (4 files); the main
                // loop in that script globs jni/*.cpp (top level only) so
                // jni/text/ subdir was previously missed.  G2.14t patched both
                // sides simultaneously.
                // mangled name lengths verified against actual nm -D libhwui.so output:
                //   MeasuredText = 43 chars, LineBreaker = 42, TextShaper = 41, GraphemeBreak = 44
                {"text.MeasuredText",            "_ZN7android43register_android_graphics_text_MeasuredTextEP7_JNIEnv"},
                {"text.LineBreaker",             "_ZN7android42register_android_graphics_text_LineBreakerEP7_JNIEnv"},
                {"text.TextShaper",              "_ZN7android41register_android_graphics_text_TextShaperEP7_JNIEnv"},
                {"text.GraphemeBreak",           "_ZN7android44register_android_graphics_text_GraphemeBreakEP7_JNIEnv"},
                // 2026-05-01 G2.14n: Typeface real-impl from libhwui DEFERRED
                // — libhwui register_android_graphics_Typeface aborts during
                // startReg (SIGABRT in parent appspawn-x).  Likely needs
                // init_FontUtils / GraphicsJNI prior init that we haven't wired.
                // Keep stub for now; revisit after addressing init path.
            };
            int hwui_ok = 0, hwui_fail = 0;
            for (const auto& r : kHwuiRegFns) {
                RegFn fn = reinterpret_cast<RegFn>(dlsym(hwui, r.sym));
                if (!fn) {
                    fprintf(stderr, "[liboh_android_runtime]   dlsym %s FAIL: %s\n",
                            r.name, dlerror());
                    hwui_fail++;
                    continue;
                }
                int rc = fn(env);
                if (env->ExceptionCheck()) {
                    env->ExceptionDescribe();
                    env->ExceptionClear();
                    hwui_fail++;
                    continue;
                }
                if (rc == 0) {
                    fprintf(stderr, "[liboh_android_runtime]   libhwui:register_%s OK\n", r.name);
                    hwui_ok++;
                } else {
                    fprintf(stderr, "[liboh_android_runtime]   libhwui:register_%s rc=%d\n", r.name, rc);
                    hwui_fail++;
                }
            }
            fprintf(stderr, "[liboh_android_runtime] libhwui register: %d ok / %d fail\n",
                    hwui_ok, hwui_fail);
        } else {
            fprintf(stderr, "[liboh_android_runtime] WARN: libhwui not loaded — graphics natives unbound\n");
        }

        // G2.4 (2026-04-30): apply graphics JNI compat shim — last-wins
        // RegisterNatives that override libhwui impls known to abort
        // (e.g., ImageDecoder.nGetColorSpace fid==null) and fill in
        // framework JNI methods we don't have a real libandroid_runtime
        // for (Surface / BLASTBufferQueue / DisplayEventReceiver).
        // MUST run AFTER libhwui's register loop above so our overrides win.
        register_android_graphics_compat_shim(env);

        env->PopLocalFrame(nullptr);
    }

    wl_register_tls_natives(env);   // [port-a1a2d4 2026-07-30] §441 real TLS over OpenSSL 3.x
    wl_repair_invoke_classes(env);  // [port-a1a2d4 2026-07-30] §404 invoke-class statics repair

    // Task 79 A3: these registrations must also remain at the startReg tail.
    // ART has already installed its ICU stubs during JNI_CreateJavaVM, and
    // JNI RegisterNatives is last-writer-wins. Charset is deliberately 13/16
    // (provider/enumeration methods remain ART-owned); regex is a coupled
    // Pattern+Matcher 15/15 cohort. Any partial registration aborts appspawn
    // before mixed native-handle layouts can execute.
    if (::westlake_register_charset_natives(env) != 0 ||
        ::westlake_register_regex_natives(env) != 0) {
        fprintf(stderr,
                "[liboh_android_runtime] A3 ICU late registration failed; "
                "aborting startReg\n");
        return -1;
    }
    fprintf(stderr,
            "[liboh_android_runtime] A3 ICU ACTIVE "
            "NativeConverter=13/16 regex=15/15\n");

    fprintf(stderr, "[liboh_android_runtime] startReg exiting (ok)\n");
    return 0;
}

}  // namespace android
