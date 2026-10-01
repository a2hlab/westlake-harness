#include <assert.h>
#include <fcntl.h>
#include <pthread.h>
#include <stdarg.h>

static int fixture_mode;
static int requests;
static int posts;
static int cancels;
static int maps_without_fence;
static int issued_fence = -1;
static int reused_fence = -1;
static int wrapper_windows[2];
static int owner_windows[2];
static unsigned char fixture_pixels[32];
static WlOHBufferHandle fixture_handle;

static void* FixtureGetWindow(void* window)
{
    if (fixture_mode == 1) return NULL;
    if (window == &wrapper_windows[0]) return &owner_windows[0];
    if (window == &wrapper_windows[1]) return &owner_windows[1];
    assert(!"wrapper identity mismatch");
    return NULL;
}

void* dlsym(void* owner, const char* name)
{
    assert(owner == RTLD_DEFAULT);
    assert(strcmp(name, "oh_anw_get_oh") == 0);
    return (void*)FixtureGetWindow;
}

int32_t NativeWindowHandleOpt(WlOHNativeWindow* window, int code, ...)
{
    assert(window == (void*)&owner_windows[0] || window == (void*)&owner_windows[1]);
    assert(code == 5);
    va_list arguments;
    va_start(arguments, code);
    assert(va_arg(arguments, uint64_t) == 3);
    va_end(arguments);
    return fixture_mode == 2 ? -1 : 0;
}

int32_t NativeWindowRequestBuffer(WlOHNativeWindow* window, WlOHNativeWindowBuffer** buffer, int32_t* fence)
{
    assert(window == (void*)&owner_windows[0] || window == (void*)&owner_windows[1]);
    ++requests;
    if (fixture_mode == 3) return -1;
    *buffer = (void*)window;
    *fence = -1;
    if (fixture_mode == 4 || fixture_mode == 5) {
        issued_fence = open("/dev/null", O_RDONLY);
        assert(issued_fence >= 0);
        *fence = issued_fence;
    }
    return 0;
}

WlOHNativeBuffer* OH_NativeBufferFromNativeWindowBuffer(WlOHNativeWindowBuffer* buffer)
{
    return (void*)buffer;
}

WlOHBufferHandle* GetBufferHandleFromNative(WlOHNativeWindowBuffer* buffer)
{
    assert(buffer != NULL);
    return fixture_mode == 7 ? NULL : &fixture_handle;
}

int32_t OH_NativeBuffer_MapWaitFence(WlOHNativeBuffer* buffer, int32_t fence, void** address)
{
    assert(buffer != NULL);
    if (fixture_mode == 5 || fixture_mode == 6) return -1;
    *address = fixture_pixels;
    if (fence >= 0) {
        assert(close(fence) == 0);
        reused_fence = open("/dev/null", O_RDONLY);
        assert(reused_fence == fence);
    }
    return 0;
}

int32_t OH_NativeBuffer_Map(WlOHNativeBuffer* buffer, void** address)
{
    assert(buffer != NULL);
    ++maps_without_fence;
    *address = fixture_pixels;
    return 0;
}

int32_t NativeWindowCancelBuffer(WlOHNativeWindow* window, WlOHNativeWindowBuffer* buffer)
{
    assert((void*)window == (void*)buffer);
    ++cancels;
    return 0;
}

int32_t NativeWindowFlushBuffer(WlOHNativeWindow* window, WlOHNativeWindowBuffer* buffer, int32_t fence, WlOHRegion region)
{
    assert((void*)window == (void*)buffer);
    assert(fence == -1 && region.rects == NULL && region.rect_number == 0);
    ++posts;
    return fixture_mode == 8 ? -1 : 0;
}

static void* ConcurrentLock(void* output)
{
    WlANativeWindowBuffer buffer;
    *(int*)output = ANativeWindow_lock(&wrapper_windows[0], &buffer, NULL);
    return NULL;
}

int main(int argc, char** argv)
{
    assert(argc == 2);
    fixture_mode = atoi(argv[1]);
    memset(&fixture_handle, 0, sizeof(fixture_handle));
    fixture_handle.fd = -1;
    fixture_handle.width = 2;
    fixture_handle.height = 2;
    fixture_handle.stride = 16;
    fixture_handle.size = 32;
    fixture_handle.format = 12;
    fixture_handle.vir_addr = fixture_pixels;
    WlANativeWindowBuffer returned;
    memset(&returned, 0xff, sizeof(returned));
    WlAndroidRect dirty = {1, 1, 2, 2};
    if (fixture_mode == 9) {
        int results[2] = {123, 123};
        pthread_t threads[2];
        for (size_t index = 0; index < 2; ++index) assert(pthread_create(&threads[index], NULL, ConcurrentLock, &results[index]) == 0);
        for (size_t index = 0; index < 2; ++index) assert(pthread_join(threads[index], NULL) == 0);
        assert((results[0] == 0 && results[1] == -EINVAL) || (results[1] == 0 && results[0] == -EINVAL));
        assert(requests == 1);
        assert(ANativeWindow_unlockAndPost(&wrapper_windows[0]) == 0);
        return 0;
    }
    const int result = ANativeWindow_lock(&wrapper_windows[0], &returned, &dirty);
    if (fixture_mode == 1 || fixture_mode == 2 || fixture_mode == 3 || fixture_mode == 5 || fixture_mode == 7) {
        assert(result != 0);
        assert(ANativeWindow_unlockAndPost(&wrapper_windows[0]) == -EINVAL);
        if (fixture_mode == 1 || fixture_mode == 2) assert(requests == 0);
        if (fixture_mode == 5 || fixture_mode == 7) assert(cancels == 1);
        if (fixture_mode == 5) {
            assert(fcntl(issued_fence, F_GETFD) == -1 && errno == EBADF);
            assert(maps_without_fence == 0);
        }
        return 0;
    }
    assert(result == 0);
    assert(returned.width == 2 && returned.height == 2 && returned.stride == 4 && returned.format == 1);
    assert(returned.bits == fixture_pixels);
    for (size_t index = 0; index < 6; ++index) assert(returned.reserved[index] == 0);
    assert(dirty.left == 0 && dirty.top == 0 && dirty.right == 2 && dirty.bottom == 2);
    assert(ANativeWindow_lock(&wrapper_windows[0], &returned, NULL) == -EINVAL && requests == 1);
    if (fixture_mode == 4) {
        assert(fcntl(reused_fence, F_GETFD) != -1);
        close(reused_fence);
    }
    if (fixture_mode == 6) assert(maps_without_fence == 1);
    assert(ANativeWindow_unlockAndPost(&wrapper_windows[0]) == (fixture_mode == 8 ? -1 : 0));
    assert(posts == 1 && cancels == (fixture_mode == 8 ? 1 : 0));
    assert(ANativeWindow_unlockAndPost(&wrapper_windows[0]) == -EINVAL);
    if (fixture_mode == 10) {
        assert(ANativeWindow_lock(&wrapper_windows[0], &returned, NULL) == 0);
        assert(ANativeWindow_lock(&wrapper_windows[1], &returned, NULL) == 0);
        assert(ANativeWindow_unlockAndPost(&wrapper_windows[1]) == 0);
        assert(ANativeWindow_unlockAndPost(&wrapper_windows[0]) == 0);
    }
    return 0;
}
