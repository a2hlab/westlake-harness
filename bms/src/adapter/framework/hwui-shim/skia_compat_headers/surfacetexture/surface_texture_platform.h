#pragma once
#include <cstdint>
struct ASurfaceTexture;
struct ANativeWindow;
inline ASurfaceTexture* ASurfaceTexture_routeAcquireANativeWindow(struct ANativeWindow*) { return nullptr; }
inline void ASurfaceTexture_routeRelease(ASurfaceTexture*) {}
inline int ASurfaceTexture_routeAttachToGLContext(ASurfaceTexture*, uint32_t) { return -1; }
inline int ASurfaceTexture_routeDetachFromGLContext(ASurfaceTexture*) { return -1; }
inline int ASurfaceTexture_routeUpdateTexImage(ASurfaceTexture*) { return -1; }
inline void ASurfaceTexture_routeGetTransformMatrix(ASurfaceTexture*, float[16]) {}
inline int64_t ASurfaceTexture_routeGetTimestamp(ASurfaceTexture*) { return 0; }
