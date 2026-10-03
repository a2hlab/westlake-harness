// U16 Flutter/Impeller GLES ProcTable gap — eglGetProcAddress interposer for the Flutter-private libandroid.so.
// See design: benchmark/2026-10-03-u16-flutter-impeller-proc/ (slot #468 = glDepthRange, build 0d216f3f).
//
// Built as an extra object INTO the U14 flutter-libandroid (fff9be31), via build_flutter_android_hw248.sh, which
// compiles extras with clang++ -std=c++17 -nostdinc++ -fno-exceptions -fno-rtti. The export is `extern "C"` so it
// matches the version script's `eglGetProcAddress`. HiLogPrint is resolved by dlsym (RTLD_DEFAULT, then the shared
// liboh_android_runtime.so handle) exactly as U14's flutter_egl.cpp n6_log does, so there is NO undefined symbol for
// -Wl,--no-undefined,--fatal-warnings. No libc++ / STL use -> no new NEEDED beyond fff9's.
//
// libflutter imports eglGetProcAddress and resolves it in the Flutter domain; an interposer only wins if it is the
// first definer in libflutter's lookup order, which the private libandroid (NEEDED position 4, before platform libEGL
// at 5) is — the same mechanism U14 used for eglCreateWindowSurface.
#include <dlfcn.h>
#include <string.h>
#include <stddef.h>

typedef float  GLfloat;
typedef double GLclampd;

// --- HiLogPrint via dlsym (no UND), same resolution order as U14 flutter_egl.cpp ---
typedef int (*LogFn)(int, int, unsigned, const char*, const char*, ...);
static void gl_log(const char* name) {
    static LogFn fn;
    static bool tried;
    if (!tried) {
        tried = true;
        fn = reinterpret_cast<LogFn>(dlsym(RTLD_DEFAULT, "HiLogPrint"));
        if (!fn) {
            void* rt = dlopen("liboh_android_runtime.so", RTLD_NOW | RTLD_NOLOAD);
            if (rt) fn = reinterpret_cast<LogFn>(dlsym(rt, "HiLogPrint"));
        }
    }
    if (fn) fn(3, 4, 0xD000F00u, "FLUTTER-GLSTUB", "%{public}s", name);
}

// --- case B: desktop-GL double entries -> GLES float variant (the driver has no glDepthRange/glClearDepth) ---
static void (*p_glDepthRangef)(GLfloat, GLfloat);
static void (*p_glClearDepthf)(GLfloat);
static void wl_glDepthRange(GLclampd n, GLclampd f) { if (p_glDepthRangef) p_glDepthRangef((GLfloat)n, (GLfloat)f); }
static void wl_glClearDepth(GLclampd d)             { if (p_glClearDepthf) p_glClearDepthf((GLfloat)d); }

// --- case C: logged no-op, so no gl* slot is ever left 0 ---
static void wl_gl_noop(void) {}

static void* g_gles2;
static void* g_gles3;
static void ensure_driver(void) {
    if (!g_gles2) g_gles2 = dlopen("libGLESv2.so", RTLD_NOLOAD | RTLD_NOW);
    if (!g_gles3) g_gles3 = dlopen("libGLESv3.so", RTLD_NOLOAD | RTLD_NOW);
    if (!p_glDepthRangef) {
        void* s = g_gles2 ? dlsym(g_gles2, "glDepthRangef") : NULL;
        if (!s && g_gles3) s = dlsym(g_gles3, "glDepthRangef");
        p_glDepthRangef = reinterpret_cast<void (*)(GLfloat, GLfloat)>(s);
    }
    if (!p_glClearDepthf) {
        void* s = g_gles2 ? dlsym(g_gles2, "glClearDepthf") : NULL;
        if (!s && g_gles3) s = dlsym(g_gles3, "glClearDepthf");
        p_glClearDepthf = reinterpret_cast<void (*)(GLfloat)>(s);
    }
}

// dedupe the [FLUTTER-GLSTUB] log to once per name per process.
static const char* g_seen[128];
static int g_seen_n;
static bool first_time(const char* name) {
    for (int i = 0; i < g_seen_n; i++)
        if (g_seen[i] == name || (g_seen[i] && strcmp(g_seen[i], name) == 0)) return false;
    if (g_seen_n < (int)(sizeof(g_seen) / sizeof(g_seen[0]))) g_seen[g_seen_n++] = name;
    return true;
}

extern "C" __attribute__((visibility("default")))
void* eglGetProcAddress(const char* name) {
    // (1) real platform eglGetProcAddress first (NOLOAD; libEGL.so is a different soname than this libandroid.so,
    //     so this is the platform entry, never recursive).
    static void* (*real)(const char*);
    if (!real) {
        void* egl = dlopen("libEGL.so", RTLD_NOLOAD | RTLD_NOW);
        if (egl) real = reinterpret_cast<void* (*)(const char*)>(dlsym(egl, "eglGetProcAddress"));
    }
    void* p = real ? real(name) : NULL;
    if (p) return p;
    if (!name) return NULL;

    ensure_driver();

    // (B) desktop double entries -> 'f' variant shim (crash slot: glDepthRange).
    if (strcmp(name, "glDepthRange") == 0) return reinterpret_cast<void*>(&wl_glDepthRange);
    if (strcmp(name, "glClearDepth") == 0) return reinterpret_cast<void*>(&wl_glClearDepth);

    // (A) the 41 extension procs: real driver export via dlsym.
    void* s = g_gles2 ? dlsym(g_gles2, name) : NULL;
    if (!s && g_gles3) s = dlsym(g_gles3, name);
    if (s) return s;

    // (C) residual gl* gap: logged no-op (once per name), never leave a null slot.
    if (name[0] == 'g' && name[1] == 'l') {
        if (first_time(name)) gl_log(name);
        return reinterpret_cast<void*>(&wl_gl_noop);
    }
    return NULL;  // non-gl*: leave as the driver decided.
}
