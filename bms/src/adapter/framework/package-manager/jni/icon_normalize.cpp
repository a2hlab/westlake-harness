/*
 * icon_normalize.cpp
 *
 * Task #65 launcher-icon unification (see icon_normalize.h for the two-stage
 * design and why detection-based padding finders were abandoned).
 * PNG decode / re-encode via vendored lodepng (src/adapter/third_party/lodepng);
 * bilinear resample is local and dependency-free. Fail-open throughout: any
 * anomaly returns false with the input bytes untouched.
 */
#include "icon_normalize.h"

#include "lodepng.h"

#include <algorithm>
#include <cmath>
#include <cstdio>
#include <cstring>

#if defined(ICON_NORMALIZE_HOST_TEST)
// Host-side unit-test build: plain stderr logging, no OH hilog.
#define NORM_LOGI(buf) do { std::fprintf(stderr, "[iconnorm I] %s\n", buf); } while (0)
#define NORM_LOGW(buf) do { std::fprintf(stderr, "[iconnorm W] %s\n", buf); } while (0)
#else
#include "hilog/log.h"
namespace {
// Same domain/tag as apk_installer.cpp so icon-chain logs stay in one stream.
constexpr unsigned int kNormLogDomain = 0xD001802;
constexpr const char* kNormLogTag = "ApkInstaller";
}  // namespace
#define NORM_LOGI(buf) OHOS::HiviewDFX::HiLog::Info({LOG_CORE, kNormLogDomain, kNormLogTag}, "%{public}s", buf)
#define NORM_LOGW(buf) OHOS::HiviewDFX::HiLog::Warn({LOG_CORE, kNormLogDomain, kNormLogTag}, "%{public}s", buf)
#endif

namespace oh_adapter {
namespace {

// Alpha threshold for "content": ignore near-invisible anti-aliasing residue
// at the canvas edge when finding the content bounding box.
constexpr uint8_t kAlphaThreshold = 8;
// Stage 1: icons whose largest transparent margin is below this are left
// untouched by the crop — they already read as full-bleed.
constexpr uint32_t kMinMarginPx = 4;
// Stage 2 gate: minimum alpha across the whole image must exceed this for the
// adaptive-crop to apply — any real transparency means the icon has genuine
// transparent structure and is never speculatively zoomed.
constexpr uint8_t kOpaqueMinAlpha = 250;
// Stage 2 ratio: Android adaptive icons use a 108dp canvas whose visible
// safe zone is the central 72dp -> crop 1/6 from each side. This is the zoom
// Android launchers themselves apply when rendering adaptive icons.
constexpr uint32_t kAdaptiveCropDivisor = 6;
// Sanity bound: launcher icons are <= 512 px in practice. Reject absurd
// decode results before trusting w*h*4 allocations.
constexpr uint32_t kMaxDimension = 1024;

struct RgbaImage {
    std::vector<uint8_t> px;  // RGBA8, row-major
    uint32_t w = 0;
    uint32_t h = 0;
};

// Finds the content bbox (alpha > kAlphaThreshold) and the minimum alpha in
// the image. Returns false for a fully transparent image.
bool FindContentBBox(const RgbaImage& img,
                     uint32_t& minX, uint32_t& minY,
                     uint32_t& maxX, uint32_t& maxY,
                     uint8_t& minAlpha) {
    minX = img.w; minY = img.h; maxX = 0; maxY = 0;
    minAlpha = 255;
    bool any = false;
    for (uint32_t y = 0; y < img.h; ++y) {
        const uint8_t* row = &img.px[static_cast<size_t>(y) * img.w * 4];
        for (uint32_t x = 0; x < img.w; ++x) {
            const uint8_t a = row[x * 4 + 3];
            minAlpha = std::min(minAlpha, a);
            if (a > kAlphaThreshold) {
                minX = std::min(minX, x); maxX = std::max(maxX, x);
                minY = std::min(minY, y); maxY = std::max(maxY, y);
                any = true;
            }
        }
    }
    return any;
}

// Bilinear resample of src[bbox] into dst (dst.w x dst.h, px preallocated).
// Sufficient for the ~1.2x-1.5x upscale typical here; deterministic, no deps.
void ResampleBilinear(const RgbaImage& src, uint32_t bx, uint32_t by,
                      uint32_t bw, uint32_t bh, RgbaImage& dst) {
    const double scaleX = static_cast<double>(bw) / dst.w;
    const double scaleY = static_cast<double>(bh) / dst.h;
    for (uint32_t dy = 0; dy < dst.h; ++dy) {
        double sy = (dy + 0.5) * scaleY - 0.5;
        sy = std::max(0.0, std::min(sy, static_cast<double>(bh - 1)));
        const uint32_t y0 = static_cast<uint32_t>(sy);
        const uint32_t y1 = std::min(y0 + 1, bh - 1);
        const double fy = sy - y0;
        for (uint32_t dx = 0; dx < dst.w; ++dx) {
            double sx = (dx + 0.5) * scaleX - 0.5;
            sx = std::max(0.0, std::min(sx, static_cast<double>(bw - 1)));
            const uint32_t x0 = static_cast<uint32_t>(sx);
            const uint32_t x1 = std::min(x0 + 1, bw - 1);
            const double fx = sx - x0;
            for (uint32_t c = 0; c < 4; ++c) {
                const double p00 = src.px[((by + y0) * src.w + (bx + x0)) * 4 + c];
                const double p10 = src.px[((by + y0) * src.w + (bx + x1)) * 4 + c];
                const double p01 = src.px[((by + y1) * src.w + (bx + x0)) * 4 + c];
                const double p11 = src.px[((by + y1) * src.w + (bx + x1)) * 4 + c];
                const double top = p00 + (p10 - p00) * fx;
                const double bot = p01 + (p11 - p01) * fx;
                const double v = top + (bot - top) * fy;
                dst.px[(dy * dst.w + dx) * 4 + c] =
                    static_cast<uint8_t>(std::max(0.0, std::min(255.0, v + 0.5)));
            }
        }
    }
}

// Crop src[bbox], scale it back into the original canvas (aspect preserved,
// centered on transparency), re-encode as RGBA8 PNG and swap into pngBytes.
// Returns false (input untouched) on any encode anomaly.
bool CropZoomEncode(const RgbaImage& src, uint32_t bx, uint32_t by,
                    uint32_t bw, uint32_t bh,
                    const char* modeTag, const char* modeDetail,
                    std::vector<uint8_t>& pngBytes) {
    char logBuf[224];
    const double fit = std::min(static_cast<double>(src.w) / bw,
                                static_cast<double>(src.h) / bh);
    const uint32_t fitW =
        std::max(1u, std::min(src.w, static_cast<uint32_t>(std::lround(bw * fit))));
    const uint32_t fitH =
        std::max(1u, std::min(src.h, static_cast<uint32_t>(std::lround(bh * fit))));

    RgbaImage scaled;
    scaled.w = fitW; scaled.h = fitH;
    scaled.px.resize(static_cast<size_t>(fitW) * fitH * 4);
    ResampleBilinear(src, bx, by, bw, bh, scaled);

    RgbaImage canvas;
    canvas.w = src.w; canvas.h = src.h;
    canvas.px.assign(static_cast<size_t>(src.w) * src.h * 4, 0);  // transparent
    const uint32_t offX = (src.w - fitW) / 2;
    const uint32_t offY = (src.h - fitH) / 2;
    for (uint32_t y = 0; y < fitH; ++y) {
        std::memcpy(&canvas.px[((offY + y) * canvas.w + offX) * 4],
                    &scaled.px[static_cast<size_t>(y) * fitW * 4],
                    static_cast<size_t>(fitW) * 4);
    }

    std::vector<uint8_t> out;
    const unsigned err =
        lodepng::encode(out, canvas.px.data(), canvas.w, canvas.h, LCT_RGBA, 8);
    if (err != 0 || out.empty()) {
        std::snprintf(logBuf, sizeof logBuf,
                      "icon normalize: %s encode failed (%s), keeping original",
                      modeTag, lodepng_error_text(err));
        NORM_LOGW(logBuf);
        return false;
    }

    std::snprintf(logBuf, sizeof logBuf,
                  "icon normalize: %s %ux%u %s -> content %ux%u (%zu -> %zu bytes)",
                  modeTag, src.w, src.h, modeDetail, fitW, fitH,
                  pngBytes.size(), out.size());
    NORM_LOGI(logBuf);
    pngBytes.swap(out);
    return true;
}

}  // namespace

bool NormalizeLauncherIconPng(std::vector<uint8_t>& pngBytes) {
    char logBuf[192];

    RgbaImage src;
    unsigned err = lodepng::decode(src.px, src.w, src.h, pngBytes);
    if (err != 0) {
        // Not a decodable PNG (e.g. webp fallback bytes) — cosmetic no-op.
        std::snprintf(logBuf, sizeof logBuf, "icon normalize: skip, not a decodable PNG (%s)",
                      lodepng_error_text(err));
        NORM_LOGI(logBuf);
        return false;
    }
    if (src.w == 0 || src.h == 0 || src.w > kMaxDimension || src.h > kMaxDimension) {
        std::snprintf(logBuf, sizeof logBuf,
                      "icon normalize: skip, dimension %ux%u out of bounds", src.w, src.h);
        NORM_LOGW(logBuf);
        return false;
    }

    uint32_t minX, minY, maxX, maxY;
    uint8_t minAlpha;
    if (!FindContentBBox(src, minX, minY, maxX, maxY, minAlpha)) {
        NORM_LOGW("icon normalize: skip, fully transparent image");
        return false;
    }
    const uint32_t marginL = minX;
    const uint32_t marginT = minY;
    const uint32_t marginR = src.w - 1 - maxX;
    const uint32_t marginB = src.h - 1 - maxY;
    const uint32_t maxMargin =
        std::max(std::max(marginL, marginT), std::max(marginR, marginB));

    if (maxMargin >= kMinMarginPx) {
        // Stage 1: real transparent margins — crop and zoom content to fill.
        // (For Genshin 158x159 in 192x192 this yields 191x192.)
        const uint32_t bw = maxX - minX + 1;
        const uint32_t bh = maxY - minY + 1;
        char detail[96];
        std::snprintf(detail, sizeof detail, "margins L%u T%u R%u B%u",
                      marginL, marginT, marginR, marginB);
        return CropZoomEncode(src, minX, minY, bw, bh, "crop", detail, pngBytes);
    }

    // Stage 2: no transparent margins. Painted adaptive safe-zone padding is
    // only possible if the image is effectively opaque; anything with real
    // transparency is left byte-identical (fail-open).
    if (minAlpha <= kOpaqueMinAlpha) {
        return false;  // genuine transparent structure; already full-bleed
    }
    // Effectively opaque + content to every edge: adaptive-composite
    // convention — the visible safe zone is the central 72dp of the 108dp
    // canvas, so crop 1/6 per side and zoom the center back to full canvas
    // (what Android launchers themselves render). Detection-based padding
    // finders were measured and abandoned (adaptive backgrounds are detailed
    // art, ring energy ~= center energy); the spec ratio is deterministic.
    const uint32_t cropX = src.w / kAdaptiveCropDivisor;
    const uint32_t cropY = src.h / kAdaptiveCropDivisor;
    const uint32_t bw = src.w - 2 * cropX;
    const uint32_t bh = src.h - 2 * cropY;
    if (bw < 8 || bh < 8) {
        NORM_LOGW("icon normalize: skip, canvas too small for adaptive crop");
        return false;
    }
    char detail[96];
    std::snprintf(detail, sizeof detail, "opaque adaptive ring %u/%u px", cropX, cropY);
    return CropZoomEncode(src, cropX, cropY, bw, bh, "adaptive-crop", detail, pngBytes);
}

}  // namespace oh_adapter
