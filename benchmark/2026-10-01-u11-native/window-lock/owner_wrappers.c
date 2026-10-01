#include <pthread.h>

extern void* dlsym(void*, const char*);

typedef struct U11WindowLock {
    void* window;
    WlLockedPixels pixels;
    struct U11WindowLock* next;
} U11WindowLock;

static pthread_mutex_t u11_mutex = PTHREAD_MUTEX_INITIALIZER;
static U11WindowLock* u11_locked;

static void* u11_oh_window(void* window)
{
    typedef void* (*GetWindow)(void*);
    GetWindow get_window = (GetWindow)dlsym(RTLD_DEFAULT, "oh_anw_get_oh");
    return window != NULL && get_window != NULL ? get_window(window) : NULL;
}

__attribute__((visibility("default")))
int32_t ANativeWindow_lock(void* window, void* output, void* dirty_bounds)
{
    void* oh_window = u11_oh_window(window);
    if (oh_window == NULL || output == NULL) return -EINVAL;
    pthread_mutex_lock(&u11_mutex);
    for (U11WindowLock* entry = u11_locked; entry != NULL; entry = entry->next) {
        if (entry->window == oh_window) {
            pthread_mutex_unlock(&u11_mutex);
            return -EINVAL;
        }
    }
    U11WindowLock* entry = calloc(1, sizeof(*entry));
    if (entry == NULL) {
        pthread_mutex_unlock(&u11_mutex);
        return -ENOMEM;
    }
    if (NativeWindowHandleOpt(oh_window, 5, (uint64_t)3) != 0) {
        free(entry);
        pthread_mutex_unlock(&u11_mutex);
        return -EIO;
    }
    int32_t result = U11DonorWindowLock(oh_window, output, NULL);
    if (result == 0) {
        entry->window = oh_window;
        entry->pixels = g_locked_pixels;
        entry->next = u11_locked;
        u11_locked = entry;
        const WlANativeWindowBuffer* returned = output;
        if (dirty_bounds != NULL) {
            WlAndroidRect* dirty = dirty_bounds;
            dirty->left = 0;
            dirty->top = 0;
            dirty->right = returned->width;
            dirty->bottom = returned->height;
        }
    } else {
        free(entry);
    }
    memset(&g_locked_pixels, 0, sizeof(g_locked_pixels));
    pthread_mutex_unlock(&u11_mutex);
    return result;
}

__attribute__((visibility("default")))
int32_t ANativeWindow_unlockAndPost(void* window)
{
    void* oh_window = u11_oh_window(window);
    if (oh_window == NULL) return -EINVAL;
    pthread_mutex_lock(&u11_mutex);
    U11WindowLock** link = &u11_locked;
    while (*link != NULL && (*link)->window != oh_window) link = &(*link)->next;
    U11WindowLock* entry = *link;
    if (entry == NULL) {
        pthread_mutex_unlock(&u11_mutex);
        return -EINVAL;
    }
    g_locked_pixels = entry->pixels;
    const int32_t result = U11DonorWindowPost(oh_window);
    if (result != 0) NativeWindowCancelBuffer(oh_window, entry->pixels.oh_buffer);
    *link = entry->next;
    free(entry);
    pthread_mutex_unlock(&u11_mutex);
    return result;
}
