#!/bin/bash
# Batch fix for remaining Phase 2 libhwui files
HWUI=/home/HanBingChen/aosp/frameworks/base/libs/hwui
COMPAT=/home/HanBingChen/adapter/build/skia_compat_headers

# Create stub headers
mkdir -p $COMPAT/include/private $COMPAT/include/gpu
mkdir -p $COMPAT/openssl $COMPAT/shaders $COMPAT/surfacetexture $COMPAT/private/android

# SkShadowFlags stub
cat > $COMPAT/include/private/SkShadowFlags.h << 'STUB1'
#pragma once
enum SkShadowFlags {
    kNone_ShadowFlag = 0x00,
    kTransparentOccluder_ShadowFlag = 0x01,
    kGeometricOnly_ShadowFlag = 0x02,
    kDirectionalLight_ShadowFlag = 0x04,
    kConcaveBlurOnly_ShadowFlag = 0x08,
    kAll_ShadowFlag = 0x0F,
};
STUB1

# openssl/sha.h stub
cat > $COMPAT/openssl/sha.h << 'STUB2'
#pragma once
#include <cstdint>
#include <cstddef>
#define SHA256_DIGEST_LENGTH 32
typedef struct SHA256state_st { uint8_t data[64]; uint32_t state[8]; uint64_t bitlen; } SHA256_CTX;
#ifdef __cplusplus
extern "C" {
#endif
inline int SHA256_Init(SHA256_CTX*) { return 1; }
inline int SHA256_Update(SHA256_CTX*, const void*, size_t) { return 1; }
inline int SHA256_Final(unsigned char*, SHA256_CTX*) { return 1; }
inline unsigned char* SHA256(const unsigned char*, size_t, unsigned char* md) { return md; }
#ifdef __cplusplus
}
#endif
STUB2

# shaders/shaders.h stub
cat > $COMPAT/shaders/shaders.h << 'STUB3'
#pragma once
#include <vector>
#include <string>
#include <cstdint>
namespace android::shaders {
struct ShaderCacheEntry { std::vector<uint8_t> blob; };
struct ShaderCache {};
}
STUB3

# minikin/Font.h
cat > $COMPAT/minikin/Font.h << 'STUB4'
#pragma once
#include <memory>
namespace minikin {
class Font { public: Font() = default; };
class MinikinFont;
}
STUB4

# surfacetexture/surface_texture_platform.h
cat > $COMPAT/surfacetexture/surface_texture_platform.h << 'STUB5'
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
STUB5

# private/android/AHardwareBufferHelpers.h
cat > $COMPAT/private/android/AHardwareBufferHelpers.h << 'STUB6'
#pragma once
#include <android/hardware_buffer.h>
namespace android {
typedef int32_t status_t;
inline uint32_t AHardwareBuffer_convertFromPixelFormat(uint32_t f) { return f; }
inline uint32_t AHardwareBuffer_convertToPixelFormat(uint32_t f) { return f; }
inline uint64_t AHardwareBuffer_convertFromGrallocUsageBits(uint64_t u) { return u; }
inline uint64_t AHardwareBuffer_convertToGrallocUsageBits(uint64_t u) { return u; }
inline status_t AHardwareBuffer_to_GraphicBuffer(const AHardwareBuffer*, void**) { return -1; }
}
STUB6

# include/gpu/GrDirectContext.h shim
echo '#include "include/gpu/ganesh/GrDirectContext.h"' > $COMPAT/include/gpu/GrDirectContext.h

echo "Stubs created"
