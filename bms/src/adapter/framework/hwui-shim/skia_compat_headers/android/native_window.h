#ifndef ANDROID_NATIVE_WINDOW_H_STUB
#define ANDROID_NATIVE_WINDOW_H_STUB
#include <cstdint>
#include <stdarg.h>
#include "hardware_buffer.h"

#ifdef __cplusplus
extern "C" {
#endif

struct ANativeWindow_Buffer {
    int32_t width;
    int32_t height;
    int32_t stride;
    int32_t format;
    void* bits;
    uint32_t reserved[6];
};

// Full ANativeWindow struct definition (matches Android nativebase/nativebase.h)
typedef struct ANativeWindow {
    int (*setSwapInterval)(struct ANativeWindow*, int);
    int (*dequeueBuffer_DEPRECATED)(struct ANativeWindow*, struct ANativeWindowBuffer**);
    int (*lockBuffer_DEPRECATED)(struct ANativeWindow*, struct ANativeWindowBuffer*);
    int (*queueBuffer_DEPRECATED)(struct ANativeWindow*, struct ANativeWindowBuffer*);
    int (*query)(const struct ANativeWindow*, int, int*);
    int (*perform)(struct ANativeWindow*, int, ...);
    int (*cancelBuffer_DEPRECATED)(struct ANativeWindow*, struct ANativeWindowBuffer*);
    int (*dequeueBuffer)(struct ANativeWindow*, struct ANativeWindowBuffer**, int*);
    int (*queueBuffer)(struct ANativeWindow*, struct ANativeWindowBuffer*, int);
    int (*cancelBuffer)(struct ANativeWindow*, struct ANativeWindowBuffer*, int);
    void* common[16];

#ifdef __cplusplus
    // Methods for sp<ANativeWindow> compatibility
    void incStrong(const void* /*id*/) const {}
    void decStrong(const void* /*id*/) const {}
#endif
} ANativeWindow;

// ANativeWindowBuffer struct
typedef struct ANativeWindowBuffer {
    void* common[8];  // padding
    int width;
    int height;
    int stride;
    int format;
    int usage;
    void* reserved[2];
    void* handle;
    void* reserved_proc[8];
} ANativeWindowBuffer_t;

// Query constants used by libhwui
enum {
    NATIVE_WINDOW_MIN_UNDEQUEUED_BUFFERS = 3,
    NATIVE_WINDOW_DEFAULT_WIDTH = 6,
    NATIVE_WINDOW_DEFAULT_HEIGHT = 7,
    NATIVE_WINDOW_TRANSFORM_HINT = 8,
    NATIVE_WINDOW_MAX_BUFFER_COUNT = 19,
    NATIVE_WINDOW_BUFFER_AGE = 20,
    NATIVE_WINDOW_FORMAT = 4,
    NATIVE_WINDOW_TRANSFORM_ROT_90 = 4,
    NATIVE_WINDOW_TRANSFORM_ROT_180 = 3,
    NATIVE_WINDOW_TRANSFORM_ROT_270 = 7,
    NATIVE_WINDOW_TRANSFORM_FLIP_H = 1,
    NATIVE_WINDOW_TRANSFORM_FLIP_V = 2,
    NATIVE_WINDOW_SCALING_MODE_FREEZE = 0,
    NATIVE_WINDOW_SCALING_MODE_SCALE_TO_WINDOW = 1,
    NATIVE_WINDOW_SCALING_MODE_SCALE_CROP = 2,
    NATIVE_WINDOW_SCALING_MODE_NO_SCALE_CROP = 3,
};

void ANativeWindow_acquire(ANativeWindow* window);
void ANativeWindow_release(ANativeWindow* window);
int32_t ANativeWindow_getWidth(ANativeWindow* window);
int32_t ANativeWindow_getHeight(ANativeWindow* window);
int32_t ANativeWindow_getFormat(ANativeWindow* window);
int32_t ANativeWindow_setBuffersGeometry(ANativeWindow* window, int32_t width, int32_t height, int32_t format);
int32_t ANativeWindow_lock(ANativeWindow* window, ANativeWindow_Buffer* outBuffer, void* inOutDirtyBounds);
int32_t ANativeWindow_unlockAndPost(ANativeWindow* window);
int32_t ANativeWindow_setBuffersTransform(ANativeWindow* window, int32_t transform);
int32_t ANativeWindow_setBuffersDataSpace(ANativeWindow* window, int32_t dataSpace);
int32_t ANativeWindow_getBuffersDataSpace(ANativeWindow* window);
int32_t ANativeWindow_setFrameRate(ANativeWindow* window, float frameRate, int8_t compatibility);
ANativeWindow* ANativeWindow_fromSurface(void* env, void* surface);

#ifdef __cplusplus
}
#endif

#endif
