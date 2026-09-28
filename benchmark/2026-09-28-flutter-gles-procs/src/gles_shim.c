// gles_shim.c
// GLES shim that repairs the OH eglGetProcAddress extension-proc gap for Impeller.
//
// On OH's Mali (r32p0) driver, eglGetProcAddress returns NULL for a set of GL
// extension entry points (e.g. glBlitFramebuffer*, glRenderbufferStorageMultisample*,
// glDiscard/Invalidate, glMapBufferRangeEXT, debug markers, ...) even though the
// SAME procs are present as direct dlsym exports in libGLESv2/libGLESv3. Impeller's
// cbz-guarded ProcTableGLES loader skips the NULL store, so a dispatch-table slot
// (#468) stays 0 and the raster thread calls it -> pc=0. See results.json.
//
// The shim interposes eglGetProcAddress: forward to the real one; on NULL, return
// the real driver export via dlsym(libGLESv2/libGLESv3) -- a genuine forward, not a
// stub. Only a proc absent from BOTH is a MISS (logged, returned NULL = next_blocker).
//
// Injection: staged as /data/local/tmp/asx/lib/arm64-v8a/libEGL.so (the isolated
// bionic namespace searches asx first), soname set to libEGL_shim.so, DT_NEEDED to
// libEG2.so (a soname-renamed copy of the real libEGL) so libflutter's other 19
// egl* resolve to the real lib while only eglGetProcAddress is interposed.
//
// Export surface is intentionally just eglGetProcAddress (policy: eglGetProcAddress
// + gl* only; no libc symbols -- see KNOWLEDGE-DIGEST D-suppl).
#define _GNU_SOURCE
#include <dlfcn.h>
#include <stdio.h>
#include <pthread.h>
#include <unistd.h>

typedef void (*GLPROC)(void);
typedef GLPROC (*EGP)(const char *);

static EGP            g_real;
static void          *g_gl2, *g_gl3;
static pthread_once_t g_once = PTHREAD_ONCE_INIT;

static void wl_init(void) {
    g_real = (EGP) dlsym(RTLD_NEXT, "eglGetProcAddress");
    g_gl2  = dlopen("libGLESv2.so", RTLD_NOW | RTLD_GLOBAL);
    g_gl3  = dlopen("libGLESv3.so", RTLD_NOW | RTLD_GLOBAL);
    fprintf(stderr, "[gles_shim] armed pid=%d real=%p gl2=%p gl3=%p\n",
            (int) getpid(), (void *) g_real, g_gl2, g_gl3);
    fflush(stderr);
}

__attribute__((visibility("default")))
GLPROC eglGetProcAddress(const char *name) {
    pthread_once(&g_once, wl_init);
    GLPROC r = g_real ? g_real(name) : (GLPROC) 0;
    if (!r && name) {
        void *d = g_gl2 ? dlsym(g_gl2, name) : (void *) 0;
        const char *src = "gl2";
        if (!d && g_gl3) { d = dlsym(g_gl3, name); src = "gl3"; }
        if (d) {
            r = (GLPROC) d;
            fprintf(stderr, "[gles_shim] FORWARD %s -> %p (%s driver export)\n", name, d, src);
        } else {
            // No driver export anywhere: this proc has no equivalent to forward to.
            // Returning NULL preserves the original blocker (recorded as next_blocker);
            // a no-op gl* stub would only be added here for a PROVEN non-load-bearing proc.
            fprintf(stderr, "[gles_shim] MISS %s (no driver export; next_blocker)\n", name);
        }
        fflush(stderr);
    }
    return r;
}
