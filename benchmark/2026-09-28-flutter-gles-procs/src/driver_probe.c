// driver_probe.c
// Driver-level GL/EGL proc oracle. For each candidate proc name (one per line in
// argv[1]) it records what the platform's GLES driver returns from the REAL
// eglGetProcAddress, plus a direct dlsym in libGLESv2/libGLESv3 (so the shim can
// tell "core export exists" from "extension-only / absent"). Also dumps
// GL_VENDOR/RENDERER/VERSION/EXTENSIONS after bringing up a headless pbuffer
// context (best-effort; eglGetProcAddress is queried regardless).
//
// One source, two targets: OpenHarmony (musl, board 5cd) and Android (bionic,
// reference phone). Output is line-oriented TSV on stdout:
//   HDR   <key>   <value>
//   PROC  <name>  egl=<hexptr|0>  gl2=<hexptr|0>  gl3=<hexptr|0>
#define _GNU_SOURCE
#include <stdio.h>
#include <string.h>
#include <dlfcn.h>

typedef void (*GLPROC)(void);
typedef GLPROC (*EGLGETPROC)(const char *);
typedef void *EGLDisplay; typedef void *EGLConfig; typedef void *EGLSurface; typedef void *EGLContext;
typedef unsigned EGLenum; typedef int EGLBoolean; typedef int EGLint;

#define EGL_DEFAULT_DISPLAY   ((void *)0)
#define EGL_NO_CONTEXT        ((void *)0)
#define EGL_OPENGL_ES_API     0x30A0
#define EGL_SURFACE_TYPE      0x3033
#define EGL_PBUFFER_BIT       0x0001
#define EGL_RENDERABLE_TYPE   0x3040
#define EGL_OPENGL_ES2_BIT    0x0004
#define EGL_WIDTH             0x3057
#define EGL_HEIGHT            0x3056
#define EGL_NONE              0x3038
#define EGL_CONTEXT_CLIENT_VERSION 0x3098
#define GL_VENDOR             0x1F00
#define GL_RENDERER           0x1F01
#define GL_VERSION            0x1F02
#define GL_EXTENSIONS         0x1F03

static void *dl_egl, *dl_gl2, *dl_gl3;

static void *open_first(const char **names) {
    for (int i = 0; names[i]; i++) {
        void *h = dlopen(names[i], RTLD_NOW | RTLD_GLOBAL);
        if (h) return h;
    }
    return (void *)0;
}

int main(int argc, char **argv) {
    if (argc < 2) { fprintf(stderr, "usage: driver_probe <names-file>\n"); return 2; }
    const char *egl_names[] = {"libEGL.so", "/system/lib64/platformsdk/libEGL.so",
                               "/system/lib64/libEGL.so", 0};
    const char *gl2_names[] = {"libGLESv2.so", "/system/lib64/ndk/libGLESv2.so",
                               "/system/lib64/libGLESv2.so", 0};
    const char *gl3_names[] = {"libGLESv3.so", "/system/lib64/platformsdk/libGLESv3.so",
                               "/system/lib64/libGLESv3.so", 0};
    dl_egl = open_first(egl_names);
    dl_gl2 = open_first(gl2_names);
    dl_gl3 = open_first(gl3_names);
    printf("HDR\tlibEGL\t%s\n", dl_egl ? "ok" : "FAIL");
    printf("HDR\tlibGLESv2\t%s\n", dl_gl2 ? "ok" : "FAIL");
    printf("HDR\tlibGLESv3\t%s\n", dl_gl3 ? "ok" : "FAIL");
    if (!dl_egl) { fprintf(stderr, "no libEGL: %s\n", dlerror()); return 3; }

    EGLGETPROC p_eglGetProcAddress = (EGLGETPROC) dlsym(dl_egl, "eglGetProcAddress");
    EGLDisplay (*p_eglGetDisplay)(void *) = (EGLDisplay(*)(void *)) dlsym(dl_egl, "eglGetDisplay");
    EGLBoolean (*p_eglInitialize)(EGLDisplay, EGLint *, EGLint *) = dlsym(dl_egl, "eglInitialize");
    EGLBoolean (*p_eglBindAPI)(EGLenum) = dlsym(dl_egl, "eglBindAPI");
    EGLBoolean (*p_eglChooseConfig)(EGLDisplay, const EGLint *, EGLConfig *, EGLint, EGLint *) = dlsym(dl_egl, "eglChooseConfig");
    EGLSurface (*p_eglCreatePbufferSurface)(EGLDisplay, EGLConfig, const EGLint *) = dlsym(dl_egl, "eglCreatePbufferSurface");
    EGLContext (*p_eglCreateContext)(EGLDisplay, EGLConfig, EGLContext, const EGLint *) = dlsym(dl_egl, "eglCreateContext");
    EGLBoolean (*p_eglMakeCurrent)(EGLDisplay, EGLSurface, EGLSurface, EGLContext) = dlsym(dl_egl, "eglMakeCurrent");
    const unsigned char *(*p_glGetString)(EGLenum) = dl_gl2 ? (const unsigned char *(*)(EGLenum)) dlsym(dl_gl2, "glGetString") : 0;

    printf("HDR\teglGetProcAddress\t%s\n", p_eglGetProcAddress ? "ok" : "FAIL");

    // Best-effort headless context so glGetString works. eglGetProcAddress is
    // queried below regardless of whether this succeeds.
    int ctx_ok = 0;
    if (p_eglGetDisplay && p_eglInitialize && p_eglChooseConfig && p_eglCreatePbufferSurface
            && p_eglCreateContext && p_eglMakeCurrent) {
        EGLDisplay dpy = p_eglGetDisplay(EGL_DEFAULT_DISPLAY);
        EGLint major = 0, minor = 0;
        if (dpy && p_eglInitialize(dpy, &major, &minor)) {
            printf("HDR\tEGL_VERSION\t%d.%d\n", major, minor);
            if (p_eglBindAPI) p_eglBindAPI(EGL_OPENGL_ES_API);
            EGLint cfg_attr[] = {EGL_SURFACE_TYPE, EGL_PBUFFER_BIT, EGL_RENDERABLE_TYPE,
                                 EGL_OPENGL_ES2_BIT, EGL_NONE};
            EGLConfig cfg; EGLint n = 0;
            if (p_eglChooseConfig(dpy, cfg_attr, &cfg, 1, &n) && n > 0) {
                EGLint pb_attr[] = {EGL_WIDTH, 16, EGL_HEIGHT, 16, EGL_NONE};
                EGLSurface surf = p_eglCreatePbufferSurface(dpy, cfg, pb_attr);
                EGLint ctx_attr[] = {EGL_CONTEXT_CLIENT_VERSION, 2, EGL_NONE};
                EGLContext ctx = p_eglCreateContext(dpy, cfg, EGL_NO_CONTEXT, ctx_attr);
                if (surf && ctx && p_eglMakeCurrent(dpy, surf, surf, ctx)) ctx_ok = 1;
            }
        }
    }
    printf("HDR\tcontext\t%s\n", ctx_ok ? "current" : "none");
    // Prefer glGetString via eglGetProcAddress (works on OH where the ndk
    // libGLESv2 dlsym path returns a dispatcher that yields NULL without the
    // wrapper's TLS). Fall back to the dlsym pointer.
    const unsigned char *(*gs)(EGLenum) = 0;
    if (p_eglGetProcAddress) gs = (const unsigned char *(*)(EGLenum)) p_eglGetProcAddress("glGetString");
    if (!gs) gs = p_glGetString;
    printf("HDR\tglGetString_src\t%s\n", gs == p_glGetString ? "dlsym" : (gs ? "eglGetProc" : "none"));
    if (gs) {
        const unsigned char *v;
        if ((v = gs(GL_VENDOR)))     printf("HDR\tGL_VENDOR\t%s\n", v);
        if ((v = gs(GL_RENDERER)))   printf("HDR\tGL_RENDERER\t%s\n", v);
        if ((v = gs(GL_VERSION)))    printf("HDR\tGL_VERSION\t%s\n", v);
        if ((v = gs(GL_EXTENSIONS))) printf("HDR\tGL_EXTENSIONS\t%s\n", v);
    }

    FILE *f = fopen(argv[1], "r");
    if (!f) { fprintf(stderr, "cannot open %s\n", argv[1]); return 4; }
    char line[256];
    while (fgets(line, sizeof line, f)) {
        size_t n = strlen(line);
        while (n && (line[n - 1] == '\n' || line[n - 1] == '\r' || line[n - 1] == ' ')) line[--n] = 0;
        if (!n) continue;
        GLPROC egl = p_eglGetProcAddress ? p_eglGetProcAddress(line) : (GLPROC) 0;
        void *d2 = dl_gl2 ? dlsym(dl_gl2, line) : (void *) 0;
        void *d3 = dl_gl3 ? dlsym(dl_gl3, line) : (void *) 0;
        printf("PROC\t%s\tegl=%p\tgl2=%p\tgl3=%p\n", line, (void *) egl, d2, d3);
    }
    fclose(f);
    return 0;
}
