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
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <unistd.h>

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
}  // namespace

__attribute__((constructor)) static void a0_entry_ctor()
{
    if (!is_probe_process()) return;
    char comm[64]; read_comm(comm, sizeof(comm)); char cmd[256]; read_cmdline(cmd, sizeof(cmd));
    Log("[A0] entry ctor pid=%d comm=%s cmdline=%s", getpid(), comm, cmd);
}

extern "C" __attribute__((visibility("default"))) int JNI_OnLoad(void* vm, void* reserved)
{
    (void)vm;
    (void)reserved;
    if (!is_probe_process()) {
        return 0x00010006;                             // guard: not the probe process -> do nothing
    }
    char comm[64]; read_comm(comm, sizeof(comm));
    Log("[A0] entry JNI_OnLoad pid=%d comm=%s (runtime load point)", getpid(), comm);

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
