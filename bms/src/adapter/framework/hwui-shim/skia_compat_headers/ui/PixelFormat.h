#pragma once
#include <cstdint>
namespace android {
typedef int32_t PixelFormat;
enum {
    PIXEL_FORMAT_RGBA_8888 = 1,
    PIXEL_FORMAT_RGBA_FP16 = 22,
    PIXEL_FORMAT_RGBA_1010102 = 43,
};
}
