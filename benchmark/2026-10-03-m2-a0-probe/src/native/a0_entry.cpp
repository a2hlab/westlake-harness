// M2 A0 runtime-side entry (2026-10-03-m2-a0-runtime-plan, window 7). Built as libwestlake_html_compat.so and
// bind-mounted onto /system/android/lib64/libwestlake_html_compat.so, which the runtime's
// B7BindFixes.loadWestlakeNativeLibs loads with System.load in every app's bind.
//
// JNI's jint JNI_OnLoad(JavaVM*, void*); int(void*,void*) is ABI-identical (no jni.h needed). The guard reads the
// process name first and returns immediately for any process that is not the probe bundle. For the probe process it
// loads the worker (libwl_a0_nweb.so, which NEEDs libarkweb_core_loader.z.so and its 152-lib closure) in a namespace
// that inherits OH's "default" namespace -- the closure study (evidence/arkweb-core-closure.txt) showed the 14 libs the
// narrow runtime CL namespace cannot see (12 in /system/lib64, 2 in /system/lib64/ndk) are all in "default". This is
// OH's own arkweb_utils.cpp ArkWebBridgeHelperLoadLibFile pattern (dlns_init/create + dlns_get("default") +
// dlns_inherit(allow_all_shared_libs) + dlopen_ns). The C-ABI boundary (one dlsym of a0_probe_start) avoids any C++
// name-mangling / shared_ptr ABI across the boundary. JNI_VERSION_1_6 = 0x00010006.
#include <dlfcn.h>
#include <jni.h>
#include <pthread.h>
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <unistd.h>

extern "C" int setenv(const char* name, const char* value, int overwrite);  // sysroot stdlib.h gates it; declare explicitly
extern "C" int HiLogPrint(int type, int level, unsigned int domain, const char* tag, const char* fmt, ...);

namespace {
const char* const PROBE_PROC = "org.westlake.a0probe";
const char* const WORKER_DIR = "/data/local/tmp";       // run_a0.sh pushes libwl_a0_nweb.so here (labelled like the deployed libs)
const char* const WORKER_SO = "libwl_a0_nweb.so";
#ifdef WL_A0_LEGACY_NS
// LEGACY-NS variant (window 15, the "cleaner fallback" from window 10, = cc-wiki's formal shim): load the worker into
// nweb_ns_legacy (dynlink.c:4189 PERMITIED_TARGET2 whitelist name) and NEVER create/touch nweb_ns, so NWebHelper::Init
// does its own dlns_create(nweb_ns, arkwebcore dir) + inherit ndk to load the engine (no EEXIST). The worker ns only
// needs the worker dir (+ inherit default for core_loader + the 14-lib closure).
const char* const NS_NAME = "nweb_ns_legacy";
const char* const NS_LIB_PATH = "/data/local/tmp";
#else
// Default variant (windows 10-14): co-own nweb_ns with BOTH the worker dir AND the arkwebcore engine dir; OH's
// ArkWebBridgeHelper then reuses the existing nweb_ns (EEXIST) to dlopen_ns libarkweb_engine.so.
const char* const NS_NAME = "nweb_ns";
const char* const NS_LIB_PATH = "/data/local/tmp:/data/storage/el1/bundle/arkwebcore/libs/arm64";
#endif

typedef int (*StartFn)(const char*);
typedef int (*DlnsGetFn)(const char*, Dl_namespace*);
typedef void (*DlnsInitFn)(Dl_namespace*, const char*);
typedef int (*DlnsCreateFn)(Dl_namespace*, const char*);
typedef int (*DlnsInheritFn)(Dl_namespace*, Dl_namespace*, const char*);
typedef void* (*DlopenNsFn)(Dl_namespace*, const char*, int);

void Log(const char* fmt, ...)
{
    char buf[700];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    HiLogPrint(3, 4, 0xD000F00u, "WL-A0", "%{public}s", buf);
    fprintf(stderr, "[A0] %s\n", buf);
    fflush(stderr);
}

void read_comm(char* out, size_t cap)
{
    out[0] = 0;
    FILE* f = fopen("/proc/self/comm", "r");
    if (f != nullptr) { size_t n = fread(out, 1, cap - 1, f); fclose(f); if (n < cap) out[n] = 0;
        for (size_t i = 0; i < cap && out[i]; i++) if (out[i] == '\n') { out[i] = 0; break; } }
}

void read_cmdline(char* out, size_t cap)
{
    out[0] = 0;
    FILE* f = fopen("/proc/self/cmdline", "r");
    if (f != nullptr) { size_t n = fread(out, 1, cap - 1, f); fclose(f); if (n < cap) out[n] = 0; }
}

bool is_probe_process()
{
    char comm[64]; read_comm(comm, sizeof(comm));
    return strncmp(comm, "org.westlake.a0", 15) == 0;
}

// ---- window 17/18: register MainActivity.nativeSurfaceReady from the runtime load point (this lib), not the app ns ----
JavaVM* g_jvm = nullptr;

// Registered onto org.westlake.a0probe.MainActivity.nativeSurfaceReady; runs in THIS lib (the entry), loaded by the
// runtime into the runtime-adjacent namespace (window 16: the app-ns a0shim could not do this). The (x,y,w,h) is the
// SurfaceView's content-area rect in the window (getLocationInWindow + size) -> env WL_A0_CONTENT_XY, which the worker
// uses for the mode-32 child-node bounds so the page sits in the content area, off the status bar.
//
// Window 18: ANativeWindow_fromSurface is NOT resolvable via dlsym(RTLD_DEFAULT) in this ns (window 17: fromSurface=0),
// so instead read android.view.Surface.mNativeObject via JNI. In this runtime that long field IS the OHNativeWindow*
// directly (cc-wiki fd-plus坐实, landed benchmark/2026-10-03-u17-fd-plus-surface: S_nativeGetFromBlastBufferQueue returns
// b->ohNativeWindow and ANativeWindow_fromSurface casts mNativeObject straight to it). Publish it as WL_A0_SV_OHWIN; the
// worker uses it directly for OH_NativeWindow_GetSurfaceId -> SurfaceUtils::GetSurface. mNativeObject==0 -> log + FAIL.
void A0_nativeSurfaceReady(JNIEnv* env, jclass clazz, jobject surface, jint x, jint y, jint w, jint h)
{
    (void)clazz;
    char xy[64];
    snprintf(xy, sizeof(xy), "%d,%d,%d,%d", (int)x, (int)y, (int)w, (int)h);
    setenv("WL_A0_CONTENT_XY", xy, 1);
    long nobj = 0;
    if (surface != nullptr) {
        jclass scls = env->GetObjectClass(surface);
        jfieldID fid = scls ? env->GetFieldID(scls, "mNativeObject", "J") : nullptr;
        if (env->ExceptionCheck()) { env->ExceptionClear(); fid = nullptr; }
        if (fid != nullptr) nobj = static_cast<long>(env->GetLongField(surface, fid));
    }
    char buf[64];
    snprintf(buf, sizeof(buf), "%p", reinterpret_cast<void*>(nobj));
    if (nobj != 0) setenv("WL_A0_SV_OHWIN", buf, 1);
    Log("[A0] entry nativeSurfaceReady Surface.mNativeObject=%p content=%s WL_A0_SV_OHWIN=%s",
        reinterpret_cast<void*>(nobj), xy, nobj != 0 ? buf : "(not set; mNativeObject=0 -> FAIL)");
}

// Reach the APP PathClassLoader (NOT the system CL that a FindClass on a native-attached thread would use, JNI spec):
// android.app.ActivityThread.currentApplication() -> getClassLoader() -> loadClass("org.westlake.a0probe.MainActivity").
// currentApplication() is null until the stock handleBindApplication/makeApplication has run (repo U11d), so the caller
// retries. ActivityThread/Context/ClassLoader are framework classes the system CL CAN see, so FindClass on them is fine.
bool TryRegister(JNIEnv* env)
{
    jclass atCls = env->FindClass("android/app/ActivityThread");
    if (atCls == nullptr) { env->ExceptionClear(); return false; }
    jmethodID mCur = env->GetStaticMethodID(atCls, "currentApplication", "()Landroid/app/Application;");
    if (mCur == nullptr) { env->ExceptionClear(); return false; }
    jobject app = env->CallStaticObjectMethod(atCls, mCur);
    if (env->ExceptionCheck()) { env->ExceptionClear(); }
    if (app == nullptr) return false;                           // app not bound yet -> retry
    jclass ctxCls = env->FindClass("android/content/Context");
    jmethodID mGetCl = ctxCls ? env->GetMethodID(ctxCls, "getClassLoader", "()Ljava/lang/ClassLoader;") : nullptr;
    if (mGetCl == nullptr) { env->ExceptionClear(); return false; }
    jobject cl = env->CallObjectMethod(app, mGetCl);
    if (env->ExceptionCheck()) { env->ExceptionClear(); }
    if (cl == nullptr) { Log("[A0] entry reg: app getClassLoader null"); return false; }
    jclass clCls = env->FindClass("java/lang/ClassLoader");
    jmethodID mLoad = clCls ? env->GetMethodID(clCls, "loadClass", "(Ljava/lang/String;)Ljava/lang/Class;") : nullptr;
    if (mLoad == nullptr) { env->ExceptionClear(); return false; }
    jstring name = env->NewStringUTF("org.westlake.a0probe.MainActivity");
    jclass mainCls = (jclass)env->CallObjectMethod(cl, mLoad, name);
    if (env->ExceptionCheck()) { env->ExceptionClear(); Log("[A0] entry reg: loadClass(MainActivity) threw"); return false; }
    if (mainCls == nullptr) { Log("[A0] entry reg: MainActivity null"); return false; }
    JNINativeMethod m;
    m.name = const_cast<char*>("nativeSurfaceReady");
    m.signature = const_cast<char*>("(Ljava/lang/Object;IIII)V");
    m.fnPtr = reinterpret_cast<void*>(&A0_nativeSurfaceReady);
    int rc = env->RegisterNatives(mainCls, &m, 1);
    if (env->ExceptionCheck()) { env->ExceptionClear(); }
    Log("[A0] entry reg: RegisterNatives(MainActivity.nativeSurfaceReady)=%d (app PathClassLoader path)", rc);
    return rc == 0;
}

void* reg_thread(void*)
{
    JNIEnv* env = nullptr;
    if (g_jvm == nullptr || g_jvm->AttachCurrentThread(&env, nullptr) != JNI_OK || env == nullptr) {
        Log("[A0] entry reg: AttachCurrentThread failed");
        return nullptr;
    }
    bool ok = false;
    for (int i = 0; i < 120 && !ok; i++) {   // ~30s: currentApplication() becomes non-null after handleBindApplication
        ok = TryRegister(env);
        if (!ok) usleep(250 * 1000);
    }
    if (!ok) Log("[A0] entry reg: gave up (MainActivity.nativeSurfaceReady NOT registered within 30s)");
    g_jvm->DetachCurrentThread();
    return nullptr;
}
}  // namespace

__attribute__((constructor)) static void a0_entry_ctor()
{
    if (!is_probe_process()) return;
    char comm[64]; read_comm(comm, sizeof(comm)); char cmd[256]; read_cmdline(cmd, sizeof(cmd));
    Log("[A0] entry ctor pid=%d comm=%s cmdline=%s", getpid(), comm, cmd);
}

extern "C" __attribute__((visibility("default"))) jint JNI_OnLoad(JavaVM* vm, void* reserved)
{
    (void)reserved;
    if (!is_probe_process()) {
        return 0x00010006;                             // guard: not the probe process -> do nothing
    }
    char comm[64]; read_comm(comm, sizeof(comm));
    Log("[A0] entry JNI_OnLoad pid=%d comm=%s (runtime load point)", getpid(), comm);

    // Window 17: register MainActivity.nativeSurfaceReady from here (the runtime load point, same load path as the formal
    // backend shim), so the surface conversion runs in this namespace. Independent of the worker load below; start now.
    g_jvm = vm;
    pthread_t th;
    if (pthread_create(&th, nullptr, reg_thread, nullptr) == 0) {
        pthread_detach(th);
        Log("[A0] entry: nativeSurfaceReady registration thread started");
    } else {
        Log("[A0] entry: pthread_create(reg) failed");
    }

    DlnsGetFn dlnsGet = (DlnsGetFn)dlsym(RTLD_DEFAULT, "dlns_get");
    DlnsInitFn dlnsInit = (DlnsInitFn)dlsym(RTLD_DEFAULT, "dlns_init");
    DlnsCreateFn dlnsCreate = (DlnsCreateFn)dlsym(RTLD_DEFAULT, "dlns_create");
    DlnsInheritFn dlnsInherit = (DlnsInheritFn)dlsym(RTLD_DEFAULT, "dlns_inherit");
    DlopenNsFn dlopenNs = (DlopenNsFn)dlsym(RTLD_DEFAULT, "dlopen_ns");
    if (!dlnsGet || !dlnsInit || !dlnsCreate || !dlnsInherit || !dlopenNs) {
        Log("[A0] entry: musl namespace ops unavailable (get=%p init=%p create=%p inherit=%p open=%p)",
            (void*)dlnsGet, (void*)dlnsInit, (void*)dlnsCreate, (void*)dlnsInherit, (void*)dlopenNs);
        return 0x00010006;
    }

    // Target name MUST be "nweb_ns": is_permitted (dynlink.c:4190) allows the target nweb_ns from ANY caller, so this
    // passes from westlake.anl.app. Get-or-create: OH may already own nweb_ns in this process.
    Dl_namespace ns;
    int grc_ns = -1, crc = -1, grc = -1, irc = -1;
#ifdef WL_A0_LEGACY_NS
    // Never touch nweb_ns: create our own nweb_ns_legacy (permitted target name) and let NWebHelper::Init do its own
    // dlns_create(nweb_ns, arkwebcore dir) + inherit ndk for the engine (no EEXIST).
    dlnsInit(&ns, NS_NAME);
    crc = dlnsCreate(&ns, NS_LIB_PATH);
    Dl_namespace def;
    grc = dlnsGet("default", &def);
    irc = dlnsInherit(&ns, &def, "allow_all_shared_libs");
#else
    grc_ns = dlnsGet(NS_NAME, &ns);                    // 0 if OH already created nweb_ns (then its lib_path drives search)
    if (grc_ns != 0) {
        dlnsInit(&ns, NS_NAME);
        crc = dlnsCreate(&ns, NS_LIB_PATH);             // dlns_create2(..., CREATE_INHERIT_DEFAULT): inherits default -> 14 resolve
        Dl_namespace def;
        grc = dlnsGet("default", &def);
        irc = dlnsInherit(&ns, &def, "allow_all_shared_libs");
    }
#endif
    Log("[A0] entry ns %s (lib_paths=%s): dlns_get=%d create=%d dlns_get(default)=%d inherit=%d",
        NS_NAME, NS_LIB_PATH, grc_ns, crc, grc, irc);
    dlerror();
    void* h = dlopenNs(&ns, WORKER_SO, RTLD_NOW);
    if (h == nullptr) {
        const char* e1 = dlerror();
        char abs[128];
        snprintf(abs, sizeof(abs), "%s/%s", WORKER_DIR, WORKER_SO);
        dlerror();
        h = dlopenNs(&ns, abs, RTLD_NOW);              // fallback: absolute path (if the ns lib_path lacks /data/local/tmp)
        Log("[A0] entry dlopen_ns(%s)=%p err=%s ; abs(%s)=%p err=%s", WORKER_SO, (void*)nullptr, e1 ? e1 : "(null)",
            abs, h, h ? "-" : (dlerror() ? dlerror() : "(null)"));
    }
    if (h == nullptr) {
        Log("[A0] entry worker load FAILED both ways");
        return 0x00010006;
    }
    StartFn start = (StartFn)dlsym(h, "a0_probe_start");
    if (start == nullptr) {
        Log("[A0] entry: a0_probe_start not found in %s", WORKER_SO);
        return 0x00010006;
    }
    int rc = start(PROBE_PROC);
    Log("[A0] entry: worker a0_probe_start rc=%d (handle=%p)", rc, h);
    return 0x00010006;
}
