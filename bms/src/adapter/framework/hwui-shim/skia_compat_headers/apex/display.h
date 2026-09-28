#ifndef APEX_DISPLAY_H_STUB
#define APEX_DISPLAY_H_STUB
#include <cstdint>
#include <cstddef>
#include <android/data_space.h>
#include <android/hardware_buffer.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef struct ADisplay ADisplay;
typedef struct ADisplayConfig ADisplayConfig;

typedef enum {
    DISPLAY_TYPE_INTERNAL = 0,
    DISPLAY_TYPE_EXTERNAL = 1,
} ADisplayType;

int ADisplay_acquirePhysicalDisplays(ADisplay*** outDisplays);
void ADisplay_release(ADisplay** displays);
ADisplayType ADisplay_getDisplayType(ADisplay* display);
float ADisplay_getMaxSupportedFps(ADisplay* display);
int ADisplay_getCurrentConfig(ADisplay* display, ADisplayConfig** outConfig);
float ADisplayConfig_getDensity(ADisplayConfig* config);
float ADisplayConfig_getFps(ADisplayConfig* config);
int32_t ADisplayConfig_getWidth(ADisplayConfig* config);
int32_t ADisplayConfig_getHeight(ADisplayConfig* config);
int64_t ADisplayConfig_getAppVsyncOffsetNanos(ADisplayConfig* config);
int64_t ADisplayConfig_getSfVsyncOffsetNanos(ADisplayConfig* config);
int64_t ADisplayConfig_getCompositorTimingNanos(ADisplayConfig* config);
void ADisplay_getPreferredWideColorFormat(ADisplay* display, ADataSpace* outDataspace, AHardwareBuffer_Format* outFormat);
int64_t ADisplay_getDeadlineNanos(ADisplay* display, int64_t now);
ADataSpace ADisplay_getPreferredDataSpace(ADisplay* display);

#ifdef __cplusplus
}
#endif

#endif
