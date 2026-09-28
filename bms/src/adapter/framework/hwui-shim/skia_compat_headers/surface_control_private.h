#ifndef SURFACE_CONTROL_PRIVATE_H_STUB
#define SURFACE_CONTROL_PRIVATE_H_STUB
#include <cstdint>
#include <android/surface_control.h>

typedef void (*ASurfaceControl_SurfaceStatsListener)(void* context, int32_t controlFd, ASurfaceTransactionStats* stats);
inline void ASurfaceControl_registerSurfaceStatsListener(ASurfaceControl, int32_t, void*, ASurfaceControl_SurfaceStatsListener) {}
inline void ASurfaceControl_unregisterSurfaceStatsListener(void*, ASurfaceControl_SurfaceStatsListener) {}
inline int64_t ASurfaceControlStats_getAcquireTime(ASurfaceTransactionStats*) { return 0; }
inline uint64_t ASurfaceControlStats_getFrameNumber(ASurfaceTransactionStats*) { return 0; }
#endif
