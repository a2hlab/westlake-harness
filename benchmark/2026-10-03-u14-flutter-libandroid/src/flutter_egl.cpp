// Copied R155 HWUI window translation + owner notification, sections 4/5.
// U14 (benchmark/2026-10-03-u14-flutter-libandroid): this copy of N6 14f79c5b is linked into the Flutter-private
// westlake_flutter/libandroid.so, which libflutter searches before libEGL.so. Two changes, both for the Flutter app
// namespace (where liboh_adapter_bridge.so is not shared by name but liboh_android_runtime.so is):
//   (1) the bridge is reached through the already-shared runtime's handle (dlsym(handle) searches its dependencies)
//       instead of a plain dlopen that could load a second bridge copy into this namespace;
//   (2) HiLogPrint is looked up the same way when RTLD_DEFAULT cannot see it, so the OH_EglHijack lines reach hilog.
// Extraction provenance and omitted readback probes are recorded in README.
#include <cstdint>
#include <dlfcn.h>
#include <mutex>
#include <unordered_map>
#include <cstdarg>
#include <cstdio>
// Logging uses the existing owner when visible; no new hilog dependency.
static int n6_log(int type, int level, unsigned domain, const char* tag, const char* format, ...) {
    char message[768]; va_list args; va_start(args, format);
    vsnprintf(message, sizeof(message), format, args); va_end(args);
    typedef int (*Log)(int,int,unsigned,const char*,const char*,...);
    static Log log = [] {
        Log found = reinterpret_cast<Log>(dlsym(RTLD_DEFAULT, "HiLogPrint"));
        if (!found) {  // U14 change (2)
            void* runtime = dlopen("liboh_android_runtime.so", RTLD_NOW | RTLD_NOLOAD);
            if (runtime) found = reinterpret_cast<Log>(dlsym(runtime, "HiLogPrint"));
        }
        return found;
    }();
    if (log) return log(type, level, domain, tag, "%{public}s", message);
    return fprintf(stderr, "[N6-%s] %s\n", tag, message);
}
// EGL types — minimal subset, avoid -I to OH's EGL/egl.h to keep this file
// self-contained. Layout matches Khronos egl.h: void*-typed handles, int32_t
// EGLint.
typedef void*    EGLDisplay;
typedef void*    EGLConfig;
typedef void*    EGLSurface;
typedef int32_t  EGLint;
typedef void*    EGLNativeWindowType;
typedef unsigned EGLBoolean;
#define EGL_NO_SURFACE ((EGLSurface) 0)

typedef void* (*oh_anw_get_oh_fn_t)(void* aosp);
typedef int (*oh_anw_notify_presented_fn_t)(void* aosp);
typedef EGLSurface (*real_eglCreateWindowSurface_fn_t)(EGLDisplay, EGLConfig,
                                                       EGLNativeWindowType,
                                                       const EGLint*);
typedef EGLBoolean (*real_eglDestroySurface_fn_t)(EGLDisplay, EGLSurface);

namespace {
    oh_anw_get_oh_fn_t                  g_oh_anw_get_oh_fn = nullptr;
    oh_anw_notify_presented_fn_t         g_oh_anw_notify_presented_fn = nullptr;
    real_eglCreateWindowSurface_fn_t    g_real_eglCreateWindowSurface_fn = nullptr;
    real_eglDestroySurface_fn_t          g_real_eglDestroySurface_fn = nullptr;
    bool                                g_egl_hijack_logged = false;
    std::mutex                          g_egl_surface_owner_mutex;
    std::unordered_map<EGLSurface, EGLNativeWindowType>
                                        g_egl_surface_owner;

    void resolve_egl_hijack_funcs() {
        if (!g_oh_anw_get_oh_fn || !g_oh_anw_notify_presented_fn) {
            // liboh_adapter_bridge.so is loaded by OHEnvironment static init
            // long before hwui RenderThread starts, so RTLD_NOLOAD finds it.
            void* h = dlopen("liboh_adapter_bridge.so", RTLD_NOW | RTLD_NOLOAD);
            if (!h) {
                (void) dlerror();
                // U14 change (1): never load a second bridge copy; reach the one the shared runtime depends on.
                h = dlopen("liboh_android_runtime.so", RTLD_NOW | RTLD_NOLOAD);
            }
            if (h) {
                g_oh_anw_get_oh_fn = reinterpret_cast<oh_anw_get_oh_fn_t>(
                    dlsym(h, "oh_anw_get_oh"));
                g_oh_anw_notify_presented_fn =
                    reinterpret_cast<oh_anw_notify_presented_fn_t>(
                        dlsym(h, "oh_anw_notify_presented"));
            }
        }
        if (!g_real_eglCreateWindowSurface_fn ||
            !g_real_eglDestroySurface_fn) {
            // libEGL.so is loaded by hwui RenderThread (via OH GLES init).
            // dlopen with RTLD_NOLOAD finds the already-loaded image; dlsym
            // on its handle returns OH libEGL's eglCreateWindowSurface — NOT
            // the hijack we install in libhwui — because dlsym(h) searches
            // that specific .so's symbol table, not the global one. This is
            // how we avoid infinite recursion when -Bsymbolic-functions
            // self-binds libhwui's internal references to our hijack.
            void* h = dlopen("libEGL.so", RTLD_NOW | RTLD_NOLOAD);
            if (!h) {
                (void) dlerror();
                h = dlopen("libEGL.so", RTLD_NOW);
            }
            if (h) {
                g_real_eglCreateWindowSurface_fn =
                    reinterpret_cast<real_eglCreateWindowSurface_fn_t>(
                        dlsym(h, "eglCreateWindowSurface"));
                g_real_eglDestroySurface_fn =
                    reinterpret_cast<real_eglDestroySurface_fn_t>(
                        dlsym(h, "eglDestroySurface"));
            }
        }
        if (!g_egl_hijack_logged) {
            n6_log(3, 4, 0xD000F00, "OH_EglHijack",
                       "resolve_egl_hijack_funcs: oh_anw_get_oh_fn=%p "
                       "notify_presented_fn=%p real_create=%p real_destroy=%p",
                       (void*) g_oh_anw_get_oh_fn,
                       (void*) g_oh_anw_notify_presented_fn,
                       (void*) g_real_eglCreateWindowSurface_fn,
                       (void*) g_real_eglDestroySurface_fn);
            if (g_oh_anw_get_oh_fn && g_oh_anw_notify_presented_fn &&
                g_real_eglCreateWindowSurface_fn &&
                g_real_eglDestroySurface_fn) {
                g_egl_hijack_logged = true;
            }
        }
    }
}  // anonymous namespace

extern "C" __attribute__((visibility("default")))
EGLSurface eglCreateWindowSurface(EGLDisplay dpy, EGLConfig config,
                                   EGLNativeWindowType window,
                                   const EGLint* attrib_list) {
    resolve_egl_hijack_funcs();

    EGLNativeWindowType actualWindow = window;
    if (g_oh_anw_get_oh_fn && window) {
        void* unwrapped = g_oh_anw_get_oh_fn(window);
        if (unwrapped) {
            n6_log(3, 4, 0xD000F00, "OH_EglHijack",
                       "eglCreateWindowSurface: detected ANW shim %p, "
                       "unwrapped to OH NativeWindow=%p",
                       window, unwrapped);
            actualWindow = (EGLNativeWindowType) unwrapped;
        }
    }

    if (!g_real_eglCreateWindowSurface_fn) {
        n6_log(3, 7, 0xD000F00, "OH_EglHijack",
                   "eglCreateWindowSurface: libEGL.so eglCreateWindowSurface "
                   "not resolved — returning EGL_NO_SURFACE");
        return EGL_NO_SURFACE;
    }

    EGLSurface surface = g_real_eglCreateWindowSurface_fn(
        dpy, config, actualWindow, attrib_list);
    if (surface != EGL_NO_SURFACE && actualWindow != window &&
        g_oh_anw_notify_presented_fn) {
        std::lock_guard<std::mutex> lock(g_egl_surface_owner_mutex);
        g_egl_surface_owner[surface] = window;
    }
    n6_log(3, 4, 0xD000F00, "OH_EglHijack",
               "eglCreateWindowSurface: dpy=%p config=%p window=%p (orig=%p) "
               "-> EGLSurface=%p",
               dpy, config, actualWindow, window, surface);
    return surface;
}

extern "C" __attribute__((visibility("default")))
EGLBoolean eglDestroySurface(EGLDisplay dpy, EGLSurface surface) {
    resolve_egl_hijack_funcs();
    if (!g_real_eglDestroySurface_fn) return 0;
    const EGLBoolean result = g_real_eglDestroySurface_fn(dpy, surface);
    if (result) {
        std::lock_guard<std::mutex> lock(g_egl_surface_owner_mutex);
        g_egl_surface_owner.erase(surface);
    }
    return result;
}

typedef EGLBoolean (*real_eglSwapBuffers_fn_t)(EGLDisplay, EGLSurface);
typedef EGLBoolean (*real_eglSwapBuffersWithDamageKHR_fn_t)(EGLDisplay, EGLSurface,
                                                            const EGLint*, EGLint);

namespace {
    real_eglSwapBuffers_fn_t                 g_real_eglSwapBuffers_fn = nullptr;
    real_eglSwapBuffersWithDamageKHR_fn_t    g_real_eglSwapBuffersWithDamageKHR_fn = nullptr;
    bool                                     g_swap_hijack_logged = false;

    void resolve_swap_hijack_funcs() {
        if (g_real_eglSwapBuffers_fn && g_real_eglSwapBuffersWithDamageKHR_fn) return;
        void* h = dlopen("libEGL.so", RTLD_NOW | RTLD_NOLOAD);
        if (!h) {
            (void) dlerror();
            h = dlopen("libEGL.so", RTLD_NOW);
        }
        if (h) {
            if (!g_real_eglSwapBuffers_fn) {
                g_real_eglSwapBuffers_fn = reinterpret_cast<real_eglSwapBuffers_fn_t>(
                    dlsym(h, "eglSwapBuffers"));
            }
            if (!g_real_eglSwapBuffersWithDamageKHR_fn) {
                g_real_eglSwapBuffersWithDamageKHR_fn =
                    reinterpret_cast<real_eglSwapBuffersWithDamageKHR_fn_t>(
                        dlsym(h, "eglSwapBuffersWithDamageKHR"));
            }
        }
        if (!g_swap_hijack_logged) {
            n6_log(3, 4, 0xD000F00, "OH_SwapHijack",
                       "resolve_swap_hijack_funcs: real_swap=%p real_swapDmgKHR=%p",
                       (void*) g_real_eglSwapBuffers_fn,
                       (void*) g_real_eglSwapBuffersWithDamageKHR_fn);
            if (g_real_eglSwapBuffers_fn && g_real_eglSwapBuffersWithDamageKHR_fn) {
                g_swap_hijack_logged = true;
            }
        }
    }

    void notify_presented_after_success(EGLSurface surface) {
        EGLNativeWindowType owner = nullptr;
        {
            std::lock_guard<std::mutex> lock(g_egl_surface_owner_mutex);
            const auto found = g_egl_surface_owner.find(surface);
            if (found != g_egl_surface_owner.end()) owner = found->second;
        }
        if (owner && g_oh_anw_notify_presented_fn) {
            (void)g_oh_anw_notify_presented_fn(owner);
        }
    }
}  // anonymous namespace

extern "C" __attribute__((visibility("default")))
EGLBoolean eglSwapBuffersWithDamageKHR(EGLDisplay dpy, EGLSurface surface,
                                        const EGLint* rects, EGLint n_rects) {
    resolve_swap_hijack_funcs();
    if (!g_real_eglSwapBuffersWithDamageKHR_fn) {
        n6_log(3, 7, 0xD000F00, "OH_SwapHijack",
                   "[G2.14ax] real eglSwapBuffersWithDamageKHR not resolved");
        return 0;
    }
    const EGLBoolean result =
        g_real_eglSwapBuffersWithDamageKHR_fn(dpy, surface, rects, n_rects);
    if (result) notify_presented_after_success(surface);
    return result;
}

extern "C" __attribute__((visibility("default")))
EGLBoolean eglSwapBuffers(EGLDisplay dpy, EGLSurface surface) {
    resolve_swap_hijack_funcs();
    if (!g_real_eglSwapBuffers_fn) {
        n6_log(3, 7, 0xD000F00, "OH_SwapHijack",
                   "[G2.14ax] real eglSwapBuffers not resolved");
        return 0;
    }
    const EGLBoolean result = g_real_eglSwapBuffers_fn(dpy, surface);
    if (result) notify_presented_after_success(surface);
    return result;
}

