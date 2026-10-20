#pragma once
#include <cstdint>
#include "native_window/external_window.h"
struct OH_NativeImage { int id; };
struct OH_OnFrameAvailableListener { void* context; void (*onFrameAvailable)(void*); };
extern "C" {
OH_NativeImage* OH_NativeImage_CreateWithSingleBufferMode(uint32_t,uint32_t,bool);
OHNativeWindow* OH_NativeImage_AcquireNativeWindow(OH_NativeImage*);
void OH_NativeImage_Destroy(OH_NativeImage**);
int32_t OH_ConsumerSurface_SetDefaultSize(OH_NativeImage*,int32_t,int32_t);
int32_t OH_NativeImage_SetOnFrameAvailableListener(OH_NativeImage*,OH_OnFrameAvailableListener);
int32_t OH_NativeImage_UnsetOnFrameAvailableListener(OH_NativeImage*);
int32_t OH_NativeImage_UpdateSurfaceImage(OH_NativeImage*);
int32_t OH_NativeImage_ReleaseTextImage(OH_NativeImage*);
int32_t OH_NativeImage_DetachContext(OH_NativeImage*);
int32_t OH_NativeImage_AttachContext(OH_NativeImage*,uint32_t);
int32_t OH_NativeImage_GetTransformMatrix(OH_NativeImage*,float*);
int64_t OH_NativeImage_GetTimestamp(OH_NativeImage*);
int32_t OH_NativeImage_Release(OH_NativeImage*);
}
