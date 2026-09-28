#pragma once
#include <SkBitmap.h>
class SkData;
namespace android {
class BitmapRegionDecoder {
public:
    static BitmapRegionDecoder* Create(const void*, size_t) { return nullptr; }
    static BitmapRegionDecoder* Create(SkData*) { return nullptr; }
    bool decodeRegion(SkBitmap*, void*, int, int, int, int, int, int) { return false; }
    int width() const { return 0; }
    int height() const { return 0; }
};
}
