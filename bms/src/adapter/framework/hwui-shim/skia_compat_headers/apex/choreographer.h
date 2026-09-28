#ifndef APEX_CHOREOGRAPHER_H_STUB
#define APEX_CHOREOGRAPHER_H_STUB
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct AChoreographer AChoreographer;
typedef int64_t AVsyncId;
typedef struct AChoreographerFrameCallbackData AChoreographerFrameCallbackData;
typedef void (*AChoreographer_frameCallback)(long frameTimeNanos, void* data);
typedef void (*AChoreographer_frameCallback64)(int64_t frameTimeNanos, void* data);
typedef void (*AChoreographer_vsyncCallback)(const AChoreographerFrameCallbackData* callbackData, void* data);
typedef void (*AChoreographer_extendedFrameCallback)(int64_t vsyncId, int64_t frameTimeNanos, int64_t frameDeadline, void* data);
typedef void (*AChoreographer_refreshRateCallback)(int64_t vsyncPeriod, void* data);

AChoreographer* AChoreographer_getInstance();
void AChoreographer_postExtendedFrameCallback(AChoreographer*, AChoreographer_extendedFrameCallback, void*);
void AChoreographer_postVsyncCallback(AChoreographer*, AChoreographer_vsyncCallback, void*);
void AChoreographer_registerRefreshRateCallback(AChoreographer*, AChoreographer_refreshRateCallback, void*);
void AChoreographer_unregisterRefreshRateCallback(AChoreographer*, AChoreographer_refreshRateCallback, void*);
int64_t AChoreographer_getFrameDelay(const AChoreographer*);
int64_t AChoreographerFrameCallbackData_getFrameTimeNanos(const AChoreographerFrameCallbackData*);
int64_t AChoreographerFrameCallbackData_getVsyncId(const AChoreographerFrameCallbackData*);
size_t AChoreographerFrameCallbackData_getFrameTimelinesLength(const AChoreographerFrameCallbackData*);
size_t AChoreographerFrameCallbackData_getPreferredFrameTimelineIndex(const AChoreographerFrameCallbackData*);
int64_t AChoreographerFrameCallbackData_getFrameTimelineVsyncId(const AChoreographerFrameCallbackData*, size_t);
int64_t AChoreographerFrameCallbackData_getFrameTimelineExpectedPresentationTimeNanos(const AChoreographerFrameCallbackData*, size_t);
int64_t AChoreographerFrameCallbackData_getFrameTimelineDeadlineNanos(const AChoreographerFrameCallbackData*, size_t);

#ifdef __cplusplus
}
#endif

#endif

// Additional functions used by libhwui RenderThread
#ifdef __cplusplus
extern "C" {
#endif
AChoreographer* AChoreographer_create();
void AChoreographer_destroy(AChoreographer*);
int AChoreographer_getFd(AChoreographer* choreographer);
void AChoreographer_handlePendingEvents(AChoreographer* choreographer, void* data);
#ifdef __cplusplus
}
#endif
