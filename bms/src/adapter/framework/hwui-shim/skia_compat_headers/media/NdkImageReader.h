#pragma once
#include <cstdint>
typedef struct AImageReader AImageReader;
typedef struct AImage AImage;
typedef int media_status_t;
struct ANativeWindow;
extern "C" {
inline media_status_t AImageReader_newWithUsage(int32_t, int32_t, int32_t, uint64_t, int32_t, AImageReader**) { return 0; }
inline media_status_t AImageReader_new(int32_t, int32_t, int32_t, int32_t, AImageReader**) { return 0; }
inline void AImageReader_delete(AImageReader*) {}
inline media_status_t AImageReader_getWindow(AImageReader*, ANativeWindow**) { return 0; }
inline media_status_t AImageReader_acquireNextImage(AImageReader*, AImage**) { return 0; }
inline media_status_t AImageReader_acquireLatestImage(AImageReader*, AImage**) { return 0; }
inline void AImage_delete(AImage*) {}
}
#define AMEDIA_OK 0

extern "C" {
inline media_status_t AImage_getHardwareBuffer(AImage*, struct AHardwareBuffer**) { return 0; }
inline media_status_t AImage_getWidth(const AImage*, int32_t*) { return 0; }
inline media_status_t AImage_getHeight(const AImage*, int32_t*) { return 0; }
inline media_status_t AImage_getFormat(const AImage*, int32_t*) { return 0; }
}
