// M2 route-a native backend shim (benchmark/2026-10-03-m2-route-a-native). The thin JNI entry the runtime
// System.load's (B7BindFixes.loadWestlakeNativeLibs) in the app namespace. Its only job, copied verbatim from cc-t3's
// A0 entry (../westlake-harness-t3/benchmark/2026-10-03-m2-a0-probe/src/native/a0_entry.cpp, worker ddcbdd46), is to
// dlopen_ns the worker (libwl_nweb_backend.so) into nweb_ns -- where libarkweb_core_loader.z.so and its closure
// resolve -- then hand the JavaVM to the worker's C-ABI nweb_backend_register, which RegisterNatives the 20
// NativeNWebBackend methods. One C-ABI symbol crosses the ns boundary (no C++/shared_ptr ABI, no second engine copy).
//
// Namespace rule (DIGEST 761, cc-t3 A0 window10): formal route-a leaves nweb_ns ENTIRELY to NWebHelper -- OH's own
// GetWebEngine does dlns_create("nweb_ns", /data/storage/el1/bundle/arkwebcore/libs/arm64)+inherit ndk to load the
// engine, and whoever creates nweb_ns first wins its lib_path (OH's create then hits EEXIST and reuses the wrong
// lib_path -> engine dlopen errno=2). So the self-loader uses nweb_ns_legacy (is_permitted's PERMITIED_TARGET2,
// dynlink.c:4189; OH never touches it on an evergreen board). The worker's NEEDED (libarkweb_core_loader.z.so etc.)
// are system libs that resolve through inherit-default; the arkweb ENGINE is loaded by NWebHelper::Init into OH's
// own nweb_ns, not here -- so this ns's lib_path is just the worker dir (no arkwebcore engine dir). This shim/worker
// neither create nor touch nweb_ns.
//
// Difference from A0: A0 guards to the single probe process AND co-owned nweb_ns (experimental convenience, not
// formal, per DIGEST 761); the route-a backend serves every app that hosts a WebView and uses nweb_ns_legacy. Loading
// the arkweb closure in every process is heavy, so the recommended wiring (see README) is to gate this on "the app
// hosts a WebView" and/or defer the worker load to the first NativeNWebBackend.create(); the gate is the runtime
// loader's. JNI_VERSION_1_6 = 0x00010006.
#include <dlfcn.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

extern int HiLogPrint(int type, int level, unsigned int domain, const char* tag, const char* fmt, ...);

static const char* const WORKER_DIR = "/system/android/lib64";   // deployed next to the runtime libs
static const char* const WORKER_SO = "libwl_nweb_backend.so";
static const char* const NS_NAME = "nweb_ns_legacy";             // PERMITIED_TARGET2 (dynlink.c:4189); NOT nweb_ns
// Legacy ns lib_path = the worker dir only. The worker's NEEDED resolve through inherit-default; the arkweb engine is
// loaded by NWebHelper::Init into OH's own nweb_ns (DIGEST 761), so this ns must NOT list the arkwebcore engine dir.
static const char* const NS_LIB_PATH = "/system/android/lib64";

typedef int (*RegisterFn)(void* /*JavaVM*/);
typedef int (*DlnsGetFn)(const char*, void*);
typedef void (*DlnsInitFn)(void*, const char*);
typedef int (*DlnsCreateFn)(void*, const char*);
typedef int (*DlnsInheritFn)(void*, void*, const char*);
typedef void* (*DlopenNsFn)(void*, const char*, int);

static void Log(const char* fmt, ...)
{
    char buf[700];
    va_list ap; va_start(ap, fmt); vsnprintf(buf, sizeof(buf), fmt, ap); va_end(ap);
    HiLogPrint(3, 4, 0xD000F00u, "WL-NWEB", "%{public}s", buf);
    fprintf(stderr, "[NWEB-SHIM] %s\n", buf); fflush(stderr);
}

// Dl_namespace is { char name[80]; } in OH musl; a 128-byte blob is safe for get/init/create/inherit/open.
typedef struct { char _[128]; } NsBlob;

__attribute__((visibility("default"))) int JNI_OnLoad(void* vm, void* reserved)
{
    (void)reserved;
    DlnsGetFn dlnsGet = (DlnsGetFn)dlsym(RTLD_DEFAULT, "dlns_get");
    DlnsInitFn dlnsInit = (DlnsInitFn)dlsym(RTLD_DEFAULT, "dlns_init");
    DlnsCreateFn dlnsCreate = (DlnsCreateFn)dlsym(RTLD_DEFAULT, "dlns_create");
    DlnsInheritFn dlnsInherit = (DlnsInheritFn)dlsym(RTLD_DEFAULT, "dlns_inherit");
    DlopenNsFn dlopenNs = (DlopenNsFn)dlsym(RTLD_DEFAULT, "dlopen_ns");
    if (!dlnsGet || !dlnsInit || !dlnsCreate || !dlnsInherit || !dlopenNs) {
        Log("musl namespace ops unavailable (get=%p init=%p create=%p inherit=%p open=%p)",
            (void*)dlnsGet, (void*)dlnsInit, (void*)dlnsCreate, (void*)dlnsInherit, (void*)dlopenNs);
        return 0x00010006;
    }
    NsBlob ns; memset(&ns, 0, sizeof(ns));
    int grc_ns = dlnsGet(NS_NAME, &ns);            // reuse nweb_ns_legacy if it exists; else create-and-inherit default
    int crc = -1, grc = -1, irc = -1;
    if (grc_ns != 0) {
        dlnsInit(&ns, NS_NAME);
        crc = dlnsCreate(&ns, NS_LIB_PATH);
        NsBlob def; memset(&def, 0, sizeof(def));
        grc = dlnsGet("default", &def);
        irc = dlnsInherit(&ns, &def, "allow_all_shared_libs");
    }
    Log("ns %s (lib_paths=%s): get=%d create=%d get(default)=%d inherit=%d (nweb_ns left to NWebHelper, DIGEST 761)",
        NS_NAME, NS_LIB_PATH, grc_ns, crc, grc, irc);
    dlerror();
    void* h = dlopenNs(&ns, WORKER_SO, RTLD_NOW);
    if (h == NULL) {
        const char* e1 = dlerror();
        char abs[160];
        snprintf(abs, sizeof(abs), "%s/%s", WORKER_DIR, WORKER_SO);
        dlerror();
        h = dlopenNs(&ns, abs, RTLD_NOW);
        Log("dlopen_ns(%s) err=%s ; abs(%s)=%p", WORKER_SO, e1 ? e1 : "(null)", abs, h);
    }
    if (h == NULL) { Log("worker load FAILED"); return 0x00010006; }
    RegisterFn reg = (RegisterFn)dlsym(h, "nweb_backend_register");
    if (reg == NULL) { Log("nweb_backend_register not found in %s", WORKER_SO); return 0x00010006; }
    int rc = reg(vm);
    Log("worker nweb_backend_register rc=%d (handle=%p)", rc, h);
    return 0x00010006;
}
