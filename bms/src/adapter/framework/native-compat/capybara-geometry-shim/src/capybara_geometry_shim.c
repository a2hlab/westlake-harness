/*
 * Capybara Adventure private ANativeWindow geometry policy.
 *
 * The original non-resizeable landscape APK renders into a 1200x750
 * size-compat frame on the 1200x1920 Android reference device.  OpenHarmony's
 * compatibility runtime currently preserves the stale 1200x1794 producer
 * geometry when Unity calls setBuffersGeometry(0, 0, ...), even after the
 * SurfaceView default size has changed to 1200x750.  This app-private DSO is
 * loaded by the private libunity.so copy.  The Unity import that owns the
 * reset is renamed to the private symbol below so an already-global
 * libandroid.so cannot win ELF symbol lookup first.
 *
 * It is never packaged into or written over the APK.  Removing the private
 * bind mounts restores the original installed files.
 */

#include <dlfcn.h>
#include <stdint.h>

typedef struct ANativeWindow ANativeWindow;

enum {
    CAPYBARA_WIDTH = 1200,
    CAPYBARA_HEIGHT = 750,
};

typedef int32_t (*SetBuffersGeometryFn)(
    ANativeWindow* window, int32_t width, int32_t height, int32_t format);
typedef ANativeWindow* (*FromSurfaceFn)(void* env, void* surface);

static void* resolve_libandroid_symbol(const char* name)
{
    static void* handle;
    if (handle == 0) handle = dlopen("libandroid.so", RTLD_NOW);
    return handle == 0 ? 0 : dlsym(handle, name);
}

static SetBuffersGeometryFn resolve_set_buffers_geometry(void)
{
    return (SetBuffersGeometryFn)resolve_libandroid_symbol(
        "ANativeWindow_setBuffersGeometry");
}

__attribute__((visibility("default")))
ANativeWindow* ANativeWindow_fromSurface(void* env, void* surface)
{
    FromSurfaceFn next = (FromSurfaceFn)resolve_libandroid_symbol(
        "ANativeWindow_fromSurface");
    if (next == 0) return 0;

    ANativeWindow* window = next(env, surface);
    SetBuffersGeometryFn set_geometry = resolve_set_buffers_geometry();
    if (window != 0 && set_geometry != 0) {
        (void)set_geometry(window, CAPYBARA_WIDTH, CAPYBARA_HEIGHT, 0);
    }
    return window;
}

__attribute__((visibility("default")))
int32_t ANativeWindow_getWidth(ANativeWindow* window)
{
    (void)window;
    return CAPYBARA_WIDTH;
}

__attribute__((visibility("default")))
int32_t ANativeWindow_getHeight(ANativeWindow* window)
{
    (void)window;
    return CAPYBARA_HEIGHT;
}

__attribute__((visibility("default")))
int32_t ANativeWindow_setBuffersGeometry(ANativeWindow* window,
    int32_t width, int32_t height, int32_t format)
{
    (void)width;
    (void)height;
    SetBuffersGeometryFn next = resolve_set_buffers_geometry();
    if (next == 0) return -1;
    return next(window, CAPYBARA_WIDTH, CAPYBARA_HEIGHT, format);
}

/*
 * libandroid.so is process-global before Unity is loaded.  Redirect only
 * libunity.so's relocation to this private name instead of relying on normal
 * DT_NEEDED interposition.
 */
__attribute__((visibility("default")))
int32_t capybara_ANativeWindow_setBuffersGeometry(ANativeWindow* window,
    int32_t width, int32_t height, int32_t format)
{
    return ANativeWindow_setBuffersGeometry(window, width, height, format);
}
