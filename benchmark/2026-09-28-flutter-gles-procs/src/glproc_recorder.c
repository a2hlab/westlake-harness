// glproc_recorder.c  (v2 -- adds provenance per blackboard #7-A)
//
// LD_PRELOAD interposer for eglGetProcAddress. Pure observer: forwards every
// call to the real eglGetProcAddress (dlsym RTLD_NEXT) and returns its result
// UNCHANGED. For each call it records the queried name, the returned pointer,
// the caller's return address and the library that address falls in (must be
// libflutter for a genuine hit -- else "unknown", never fabricated).
//
// One source, two targets (Android/bionic oracle, OpenHarmony device):
//   built with -fvisibility=hidden + a version script so the ONLY exported
//   symbol is eglGetProcAddress. Exporting libc symbols from a preload/dlopen
//   library breaks the OH runtime loader (KNOWLEDGE-DIGEST D-suppl 2026-09-27).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

typedef void (*wl_glproc)(void);
typedef wl_glproc (*wl_egpa)(const char *);

static wl_egpa        g_real;
static pthread_once_t g_once = PTHREAD_ONCE_INIT;

static const char *wl_libof(void *addr, void **base) {
    Dl_info di;
    if (addr && dladdr(addr, &di) && di.dli_fname) {
        if (base) *base = di.dli_fbase;
        return di.dli_fname;
    }
    if (base) *base = (void *) 0;
    return "unknown";
}

static void wl_init(void) {
    g_real = (wl_egpa) dlsym(RTLD_NEXT, "eglGetProcAddress");

    // target process
    char cmd[256];
    cmd[0] = 0;
    FILE *f = fopen("/proc/self/cmdline", "r");
    if (f) {
        size_t n = fread(cmd, 1, sizeof(cmd) - 1, f);
        for (size_t i = 0; i + 1 < n; i++) if (cmd[i] == 0) cmd[i] = ' ';
        cmd[n < sizeof(cmd) ? n : sizeof(cmd) - 1] = 0;
        fclose(f);
    }
    fprintf(stderr, "[glproc_rec] pid=%d cmd=%s\n", (int) getpid(), cmd);

    // where THIS recorder is loaded from, and where the real impl lives
    void *base = 0;
    fprintf(stderr, "[glproc_rec] recorder_lib=%s\n", wl_libof((void *) wl_init, &base));
    fprintf(stderr, "[glproc_rec] real_eglGetProcAddress=%p in %s\n",
            (void *) g_real, wl_libof((void *) g_real, &base));
    fflush(stderr);
}

__attribute__((visibility("default")))
wl_glproc eglGetProcAddress(const char *name) {
    pthread_once(&g_once, wl_init);
    wl_glproc ret = (wl_glproc) 0;
    if (g_real) ret = g_real(name);

    void *caller = __builtin_return_address(0);
    void *cbase  = 0;
    const char *callerlib = wl_libof(caller, &cbase);

    if (name) {
        if (ret == (wl_glproc) 0)
            fprintf(stderr, "eglGetProcAddress NULL %s\n", name);
        fprintf(stderr, "eglGetProcAddress QUERY %s ret=%p caller=%p callerlib=%s\n",
                name, (void *) ret, caller, callerlib);
        fflush(stderr);
    }
    return ret;
}
