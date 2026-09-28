#pragma once
// Forward to OH Skia's SkAndroidFrameworkUtils, then add missing helpers
// via a different namespace to avoid typedef collision.
#include "android/SkAndroidFrameworkUtils.h"
#include <cstdint>
class SkCanvas;
class SkRect;
class SkShader;

// AOSP code that does `SkAndroidFrameworkUtils::SaveBehind(canvas, &bounds)`
// needs SaveBehind on the same class. OH already provides SkAndroidFrameworkUtils
// (class), so we add a wrapper that exposes the missing static methods.
namespace adapter_sk_ext {
    struct LinearGradientInfo {
        int fColorCount = 0;
        const uint32_t* fColors = nullptr;
        const float* fColorOffsets = nullptr;
        float fPoints[4] = {0,0,0,0};
        int fTileMode = 0;
        uint32_t fGradientFlags = 0;
        float fMatrix[9] = {1,0,0,0,1,0,0,0,1};
    };
    inline int SaveBehind(SkCanvas*, const SkRect*) { return 0; }
    inline bool ShouldCollapseSrcOver(const void*, int) { return false; }
    inline void ResetClip(SkCanvas*) {}
    inline int ShaderAsALinearGradient(SkShader*, LinearGradientInfo*) { return 0; }
}

// SkAndroidFrameworkTraceUtil — also needed by Properties.cpp
class SkAndroidFrameworkTraceUtil {
public:
    static void setEnableTracing(bool) {}
    static void setUsePerfettoTrackEvents(bool) {}
    static bool getEnableTracing() { return false; }
};
