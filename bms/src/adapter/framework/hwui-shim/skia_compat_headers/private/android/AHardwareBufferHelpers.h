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

struct ANativeWindowBuffer;
inline ANativeWindowBuffer* AHardwareBuffer_to_ANativeWindowBuffer(AHardwareBuffer* b) {
    return reinterpret_cast<ANativeWindowBuffer*>(b);
}
inline const ANativeWindowBuffer* AHardwareBuffer_to_ANativeWindowBuffer(const AHardwareBuffer* b) {
    return reinterpret_cast<const ANativeWindowBuffer*>(b);
}
