#ifndef APEX_WINDOW_H_STUB
#define APEX_WINDOW_H_STUB
// Stub for apex/window.h — provides ANativeWindow_* function pointer typedefs
// and interceptor functions used by libhwui's ReliableSurface

#include <stdarg.h>
#include <cstdint>
#include <cstddef>
#include <android/native_window.h>
#include <android/hardware_buffer.h>

#ifdef __cplusplus
extern "C" {
#endif

// Forward declarations
struct AHardwareBuffer;
struct ANativeWindow_FrameTimelineInfo;


typedef struct ANativeWindow_FrameTimelineInfo {
    uint64_t frameNumber;
    int64_t frameTimelineVsyncId;
    int32_t inputEventId;
    int64_t startTimeNanos;
    int useForRefreshRateSelection;
    int64_t skippedFrameVsyncId;
    int64_t skippedFrameStartTimeNanos;
} ANativeWindow_FrameTimelineInfo;

// perform op codes
enum ANativeWindowPerform {
    NATIVE_WINDOW_SET_USAGE = 0,
    NATIVE_WINDOW_SET_BUFFERS_GEOMETRY = 5,
    NATIVE_WINDOW_SET_BUFFERS_FORMAT = 9,
    NATIVE_WINDOW_SET_BUFFER_COUNT = 10,
    NATIVE_WINDOW_API_CONNECT = 13,
    NATIVE_WINDOW_API_DISCONNECT = 14,
    NATIVE_WINDOW_SET_BUFFERS_DATA_SPACE = 21,
};

// Function pointer typedefs (matching AOSP apex/window.h)
typedef int (*ANativeWindow_cancelBufferFn)(ANativeWindow* window, ANativeWindowBuffer* buffer, int fenceFd);
typedef int (*ANativeWindow_dequeueBufferFn)(ANativeWindow* window, ANativeWindowBuffer** buffer, int* fenceFd);
typedef int (*ANativeWindow_queueBufferFn)(ANativeWindow* window, ANativeWindowBuffer* buffer, int fenceFd);
typedef int (*ANativeWindow_performFn)(ANativeWindow* window, int operation, va_list args);
typedef int (*ANativeWindow_queryFn)(const ANativeWindow* window, int what, int* value);

// Interceptor function pointer types
typedef int (*ANativeWindow_cancelBufferInterceptor)(ANativeWindow*, ANativeWindow_cancelBufferFn, void*, ANativeWindowBuffer*, int);
typedef int (*ANativeWindow_dequeueBufferInterceptor)(ANativeWindow*, ANativeWindow_dequeueBufferFn, void*, ANativeWindowBuffer**, int*);
typedef int (*ANativeWindow_queueBufferInterceptor)(ANativeWindow*, ANativeWindow_queueBufferFn, void*, ANativeWindowBuffer*, int);
typedef int (*ANativeWindow_performInterceptor)(ANativeWindow*, ANativeWindow_performFn, void*, int, va_list);
typedef int (*ANativeWindow_queryInterceptor)(const ANativeWindow*, ANativeWindow_queryFn, void*, int, int*);

// Interceptor registration
int ANativeWindow_setCancelBufferInterceptor(ANativeWindow*, ANativeWindow_cancelBufferInterceptor, void*);
int ANativeWindow_setDequeueBufferInterceptor(ANativeWindow*, ANativeWindow_dequeueBufferInterceptor, void*);
int ANativeWindow_setQueueBufferInterceptor(ANativeWindow*, ANativeWindow_queueBufferInterceptor, void*);
int ANativeWindow_setPerformInterceptor(ANativeWindow*, ANativeWindow_performInterceptor, void*);
int ANativeWindow_setQueryInterceptor(ANativeWindow*, ANativeWindow_queryInterceptor, void*);

// Buffer dequeue / queue / cancel (low-level)
int ANativeWindow_dequeueBuffer(ANativeWindow* window, ANativeWindowBuffer** buffer, int* fenceFd);
int ANativeWindow_queueBuffer(ANativeWindow* window, ANativeWindowBuffer* buffer, int fenceFd);
int ANativeWindow_cancelBuffer(ANativeWindow* window, ANativeWindowBuffer* buffer, int fenceFd);
int ANativeWindow_perform(ANativeWindow* window, int operation, ...);

// Frame timeline / present time
int ANativeWindow_setFrameTimelineInfo(ANativeWindow*, struct ANativeWindow_FrameTimelineInfo*);

// Get last queued buffer
int ANativeWindow_getLastQueuedBuffer2(ANativeWindow* window, AHardwareBuffer** outBuffer, int* outFenceFd, /*ARect*/void* outCrop, uint32_t* outTransform);

// Native window connect/disconnect API levels
#ifndef NATIVE_WINDOW_API_EGL
#define NATIVE_WINDOW_API_EGL 1
#endif

int native_window_api_connect(ANativeWindow*, int);
int native_window_api_disconnect(ANativeWindow*, int);
int native_window_set_buffers_format(ANativeWindow*, int);
int native_window_set_buffers_data_space(ANativeWindow*, int);
int native_window_set_buffers_dimensions(ANativeWindow*, int, int);
int native_window_set_buffers_transform(ANativeWindow*, int);
int native_window_set_buffer_count(ANativeWindow*, int);
int native_window_set_usage(ANativeWindow*, uint64_t);
int native_window_set_auto_prerotation(ANativeWindow*, bool);
int native_window_set_scaling_mode(struct ANativeWindow*, int);
int native_window_set_frame_timeline_info(struct ANativeWindow*, uint64_t, int64_t, int32_t, int64_t, bool);

#ifdef __cplusplus
}
#endif

#endif

#ifdef __cplusplus
extern "C" {
#endif
int native_window_enable_frame_timestamps(struct ANativeWindow*, bool);
int native_window_get_frame_timestamps(struct ANativeWindow*, uint64_t, int64_t*, int64_t*, int64_t*, int64_t*, int64_t*, int64_t*, int64_t*, int64_t*, int64_t*);
#ifdef __cplusplus
}
#endif
