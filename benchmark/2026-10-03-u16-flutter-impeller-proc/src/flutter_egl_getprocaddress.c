// U16 Flutter/Impeller GLES ProcTable gap — eglGetProcAddress interposer.
//
// Home: compile into the Flutter-private libandroid.so (`westlake_flutter/libandroid.so`, ee2fb82c), the SAME
// level-1 object that the U14 flutter-egl-window fix added `eglCreateWindowSurface` to. libflutter imports
// `eglGetProcAddress` (one UND) and resolves it in the Flutter domain's by-name shared list; an interposer only
// wins if it is the FIRST definition in libflutter's lookup order, which the private libandroid (level 1) is —
// exactly the mechanism U14 used for eglCreateWindowSurface. New FILE, so nothing is added to a frozen source.
//
// Why: Impeller's GLES ProcTable resolves each proc via eglGetProcAddress and, for the extension region, SKIPS the
// store when the result is NULL (cbz-guarded loader). On the OH Mali-G57 driver eglGetProcAddress returns NULL for
// 59 of the names libflutter asks for; Impeller's raster path then calls an unfilled slot unconditionally -> pc=0.
// localsend's first fatal is slot #468 = "glDepthRange" (build 0d216f3f). See ../evidence/crash-slot-trace.txt.
//
// Three disjoint sub-cases, measured on the board (../evidence/driver-oracle-glDepthRange.txt):
//   A. 41 extension procs are NULL via eglGetProcAddress but ARE direct dlsym exports of libGLESv2/libGLESv3
//      (glBlitFramebufferANGLE/NV, glRenderbufferStorageMultisample*, glMapBufferRangeEXT, fences, ...): dlsym-forward.
//   B. desktop-GL double-precision entries that GLES simply does not have — glDepthRange, glClearDepth — are NULL on
//      eglGetProcAddress AND dlsym (oh_gl2=oh_gl3=0). The GLES float variant exists and is exported (glDepthRangef,
//      glClearDepthf). A dlsym-forward CANNOT fix these (nothing to forward to); they need a semantic shim to the
//      'f' variant. This is the crash slot's class and the correction over the 2026-09-28 RE's blanket forward.
//   C. anything NULL on both with no equivalent: a logged no-op gl* stub, so no slot is ever left 0.
//
// ABI note (case B): the stored function pointer is the raw proc (entry+16 / 0xe98); the crash call goes through a
// shared dispatcher (entry+24 / 0xea0). The shim below uses the DESKTOP glDepthRange signature (GLclampd,GLclampd)
// because the resolved name is the desktop name. Before building, confirm the exact call ABI from the dispatcher at
// [sp,#0x20] in JNI_OnLoad — crash-prevention (slot non-null) is ABI-independent, but correct depth-range needs the
// right argument widths. If Impeller calls it with float args, change the two params to GLfloat.

#include <dlfcn.h>
#include <string.h>
#include <stddef.h>

typedef float   GLfloat;
typedef double  GLclampd;
typedef void*   (*GetProcFn)(const char*);

extern void* HiLogPrint(int, int, unsigned, const char*, const char*, ...);  // optional logging (same domain as OH_EglHijack)

// ---- case B shims: desktop double entry -> GLES float variant, resolved once from the driver ----
static void (*p_glDepthRangef)(GLfloat, GLfloat);
static void (*p_glClearDepthf)(GLfloat);

static void wl_glDepthRange(GLclampd n, GLclampd f) { if (p_glDepthRangef) p_glDepthRangef((GLfloat)n, (GLfloat)f); }
static void wl_glClearDepth(GLclampd d)             { if (p_glClearDepthf) p_glClearDepthf((GLfloat)d); }

// ---- case C: logged no-op, so a residual gap never leaves a null slot ----
static void wl_gl_noop(void) { /* intentionally empty */ }

static void* g_libgles2;   // the real GLES libs, opened NOLOAD (already mapped in this process)
static void* g_libgles3;

static void ensure_driver(void) {
    if (!g_libgles2) g_libgles2 = dlopen("libGLESv2.so", RTLD_NOLOAD | RTLD_NOW);
    if (!g_libgles3) g_libgles3 = dlopen("libGLESv3.so", RTLD_NOLOAD | RTLD_NOW);
    if (!p_glDepthRangef) {
        void* s = g_libgles2 ? dlsym(g_libgles2, "glDepthRangef") : NULL;
        if (!s && g_libgles3) s = dlsym(g_libgles3, "glDepthRangef");
        p_glDepthRangef = (void (*)(GLfloat, GLfloat))s;
    }
    if (!p_glClearDepthf) {
        void* s = g_libgles2 ? dlsym(g_libgles2, "glClearDepthf") : NULL;
        if (!s && g_libgles3) s = dlsym(g_libgles3, "glClearDepthf");
        p_glClearDepthf = (void (*)(GLfloat))s;
    }
}

// Interposer. Exported so libflutter's level-1 lookup binds here before platform libEGL.
__attribute__((visibility("default")))
void* eglGetProcAddress(const char* name) {
    // (1) ask the real platform eglGetProcAddress first (NOLOAD; already mapped as libEGL.so).
    static GetProcFn real;
    if (!real) {
        void* egl = dlopen("libEGL.so", RTLD_NOLOAD | RTLD_NOW);
        if (egl) real = (GetProcFn)dlsym(egl, "eglGetProcAddress");
    }
    void* p = real ? real(name) : NULL;
    if (p) return p;
    if (!name) return NULL;

    ensure_driver();

    // (B) desktop double entries -> 'f' variant shim.
    if (strcmp(name, "glDepthRange") == 0) return (void*)wl_glDepthRange;
    if (strcmp(name, "glClearDepth") == 0) return (void*)wl_glClearDepth;

    // (A) the 41 extension procs: real driver export via dlsym.
    void* s = g_libgles2 ? dlsym(g_libgles2, name) : NULL;
    if (!s && g_libgles3) s = dlsym(g_libgles3, name);
    if (s) return s;

    // (C) residual gl* gap: logged no-op, never leave a null slot.
    if (name[0] == 'g' && name[1] == 'l') {
        HiLogPrint(3, 4, 0xD000F00u, "WL-GLES", "eglGetProcAddress gap stubbed: %{public}s", name);
        return (void*)wl_gl_noop;
    }
    return NULL;  // non-gl*: leave as the driver decided.
}
