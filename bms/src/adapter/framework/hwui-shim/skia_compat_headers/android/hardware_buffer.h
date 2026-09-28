#ifndef ANDROID_HARDWARE_BUFFER_H_STUB
#define ANDROID_HARDWARE_BUFFER_H_STUB
#include <cstdint>

#ifdef __cplusplus
extern "C" {
#endif

enum AHardwareBuffer_Format {
    AHARDWAREBUFFER_FORMAT_R8G8B8A8_UNORM           = 1,
    AHARDWAREBUFFER_FORMAT_R8G8B8X8_UNORM           = 2,
    AHARDWAREBUFFER_FORMAT_R8G8B8_UNORM             = 3,
    AHARDWAREBUFFER_FORMAT_R5G6B5_UNORM             = 4,
    AHARDWAREBUFFER_FORMAT_R16G16B16A16_FLOAT       = 22,
    AHARDWAREBUFFER_FORMAT_R10G10B10A2_UNORM        = 43,
    AHARDWAREBUFFER_FORMAT_BLOB                     = 33,
    AHARDWAREBUFFER_FORMAT_D16_UNORM                = 48,
    AHARDWAREBUFFER_FORMAT_D24_UNORM                = 49,
    AHARDWAREBUFFER_FORMAT_D24_UNORM_S8_UINT        = 50,
    AHARDWAREBUFFER_FORMAT_D32_FLOAT                = 51,
    AHARDWAREBUFFER_FORMAT_D32_FLOAT_S8_UINT        = 52,
    AHARDWAREBUFFER_FORMAT_S8_UINT                  = 53,
    AHARDWAREBUFFER_FORMAT_Y8Cb8Cr8_420             = 35,
    AHARDWAREBUFFER_FORMAT_R8                       = 0x38,
};

enum AHardwareBuffer_UsageFlags {
    AHARDWAREBUFFER_USAGE_CPU_READ_NEVER            = 0,
    AHARDWAREBUFFER_USAGE_CPU_READ_RARELY           = 2,
    AHARDWAREBUFFER_USAGE_CPU_READ_OFTEN            = 3,
    AHARDWAREBUFFER_USAGE_CPU_READ_MASK             = 0xF,
    AHARDWAREBUFFER_USAGE_CPU_WRITE_NEVER           = 0,
    AHARDWAREBUFFER_USAGE_CPU_WRITE_RARELY          = 0x20,
    AHARDWAREBUFFER_USAGE_CPU_WRITE_OFTEN           = 0x30,
    AHARDWAREBUFFER_USAGE_CPU_WRITE_MASK            = 0xF0,
    AHARDWAREBUFFER_USAGE_GPU_SAMPLED_IMAGE         = 0x100,
    AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT          = 0x200,
    AHARDWAREBUFFER_USAGE_GPU_FRAMEBUFFER           = AHARDWAREBUFFER_USAGE_GPU_COLOR_OUTPUT,
    AHARDWAREBUFFER_USAGE_PROTECTED_CONTENT         = 0x4000,
    AHARDWAREBUFFER_USAGE_GPU_DATA_BUFFER           = 0x1000000,
    AHARDWAREBUFFER_USAGE_GPU_CUBE_MAP              = 0x2000000,
    AHARDWAREBUFFER_USAGE_GPU_MIPMAP_COMPLETE       = 0x4000000,
};

typedef struct AHardwareBuffer AHardwareBuffer;
typedef struct AHardwareBuffer_Desc {
    uint32_t width;
    uint32_t height;
    uint32_t layers;
    uint32_t format;
    uint64_t usage;
    uint32_t stride;
    uint32_t rfu0;
    uint64_t rfu1;
} AHardwareBuffer_Desc;

int  AHardwareBuffer_allocate(const AHardwareBuffer_Desc* desc, AHardwareBuffer** outBuffer);
void AHardwareBuffer_acquire(AHardwareBuffer* buffer);
void AHardwareBuffer_release(AHardwareBuffer* buffer);
void AHardwareBuffer_describe(const AHardwareBuffer* buffer, AHardwareBuffer_Desc* outDesc);
int  AHardwareBuffer_lock(AHardwareBuffer* buffer, uint64_t usage, int32_t fence, const void* rect, void** outVirtualAddress);
int  AHardwareBuffer_unlock(AHardwareBuffer* buffer, int32_t* fence);
int  AHardwareBuffer_sendHandleToUnixSocket(const AHardwareBuffer* buffer, int socketFd);
int32_t AHardwareBuffer_getDataSpace(AHardwareBuffer* buffer);
int  AHardwareBuffer_recvHandleFromUnixSocket(int socketFd, AHardwareBuffer** outBuffer);

#ifdef __cplusplus
}
#endif

#endif
