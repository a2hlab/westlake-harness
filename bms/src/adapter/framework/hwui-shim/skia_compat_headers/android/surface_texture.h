#ifndef ANDROID_SURFACE_TEXTURE_H_STUB
#define ANDROID_SURFACE_TEXTURE_H_STUB
#include <cstdint>
#ifdef __cplusplus
extern "C" {
#endif
struct ASurfaceTexture;
struct ANativeWindow;
ASurfaceTexture* ASurfaceTexture_fromSurfaceTexture(void* env, void* surfaceTexture);
ANativeWindow* ASurfaceTexture_acquireANativeWindow(ASurfaceTexture* st);
void ASurfaceTexture_release(ASurfaceTexture* st);
int ASurfaceTexture_attachToGLContext(ASurfaceTexture* st, uint32_t texName);
int ASurfaceTexture_detachFromGLContext(ASurfaceTexture* st);
int ASurfaceTexture_updateTexImage(ASurfaceTexture* st);
void ASurfaceTexture_getTransformMatrix(ASurfaceTexture* st, float mtx[16]);
int64_t ASurfaceTexture_getTimestamp(ASurfaceTexture* st);
#ifdef __cplusplus
}
#endif
#endif
