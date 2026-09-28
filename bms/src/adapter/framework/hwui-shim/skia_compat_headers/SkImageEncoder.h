#pragma once
#include <encode/SkEncoder.h>
#include <encode/SkJpegEncoder.h>
#include <encode/SkPngEncoder.h>
#include <encode/SkWebpEncoder.h>

// Legacy aggregator - SkImageEncoder was removed in Skia M133
class SkImage;
class SkWStream;

// Stub for legacy SkEncodeImage function
namespace SkLegacy {
    inline bool SkEncodeImage(SkWStream*, const SkImage*, int) { return false; }
}
