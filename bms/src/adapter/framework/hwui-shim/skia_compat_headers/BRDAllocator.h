#pragma once
// Stub for BRDAllocator.h
#include <core/SkBitmap.h>
namespace android {
namespace skia {
class BRDAllocator : public SkBitmap::Allocator {
public:
    virtual ~BRDAllocator() {}
};
}
}
