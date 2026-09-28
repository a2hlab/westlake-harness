#pragma once

#include <SkPaint.h>
#include <SkPaintFilterCanvas.h>
#include <SkDrawable.h>
#include <SkTextBlob.h>

#include <atomic>
#include <cstdio>

namespace android {
namespace uirenderer {
namespace skiapipeline {

// Diagnostic-only transparent canvas used by the HelloWorld r13 paint probe.
// It forwards every operation unchanged and records the exact SkPaint payload
// seen during DisplayList replay.  Keeping the probe here makes the experiment
// adapter-owned; no AOSP or OpenHarmony source file is modified.
class AlexBridgePaintProbeCanvas final : public SkPaintFilterCanvas {
public:
    explicit AlexBridgePaintProbeCanvas(SkCanvas* canvas) : SkPaintFilterCanvas(canvas) {}

protected:
    bool onFilter(SkPaint& paint) const override {
        static std::atomic<int> count{0};
        const int n = ++count;
        if (n <= 320) {
            const SkColor4f color = paint.getColor4f();
            fprintf(stderr,
                    "[ALEX_PAINT] #%d rgba=(%.4f,%.4f,%.4f,%.4f) alpha=%.4f "
                    "argb=%08x style=%d aa=%d blend=%d shader=%p cf=%p if=%p "
                    "mf=%p pe=%p blender=%p\n",
                    n,
                    static_cast<double>(color.fR),
                    static_cast<double>(color.fG),
                    static_cast<double>(color.fB),
                    static_cast<double>(color.fA),
                    static_cast<double>(paint.getAlphaf()),
                    paint.getColor(),
                    static_cast<int>(paint.getStyle()),
                    paint.isAntiAlias() ? 1 : 0,
                    static_cast<int>(paint.getBlendMode_or(SkBlendMode::kSrcOver)),
                    static_cast<void*>(paint.getShader()),
                    static_cast<void*>(paint.getColorFilter()),
                    static_cast<void*>(paint.getImageFilter()),
                    static_cast<void*>(paint.getMaskFilter()),
                    static_cast<void*>(paint.getPathEffect()),
                    static_cast<void*>(paint.getBlender()));
            fflush(stderr);
        }
        return true;
    }

    // OH Skia does not export SkPaintFilterCanvas::onDrawDrawable.  Unroll
    // nested drawables through this probe, matching HanBing's proven
    // OpInspectCanvas route and avoiding a new eager-relocation dependency.
    void onDrawDrawable(SkDrawable* drawable, const SkMatrix* matrix) override {
        drawable->draw(this, matrix);
    }

    // This callback is on the real replay path.  SkTextBlob's bounds and ID
    // accessors are inline in OH Skia m133, so the probe adds no hidden Skia
    // iterator/ABI dependency.  START/DONE brackets prove forwarding reached
    // and returned from the wrapped GPU canvas.
    void onDrawTextBlob(const SkTextBlob* blob, SkScalar x, SkScalar y,
                        const SkPaint& paint) override {
        static std::atomic<int> blobCount{0};
        const int n = ++blobCount;
        if (!blob || n > 96) {
            SkPaintFilterCanvas::onDrawTextBlob(blob, x, y, paint);
            return;
        }

        const SkRect& bounds = blob->bounds();
        fprintf(stderr,
                "[ALEX_TEXTBLOB] #%d START blob=%p id=%u xy=(%.2f,%.2f) "
                "bounds=(%.2f,%.2f,%.2f,%.2f) argb=%08x alpha=%.3f\n",
                n, static_cast<const void*>(blob), blob->uniqueID(),
                static_cast<double>(x), static_cast<double>(y),
                static_cast<double>(bounds.left()), static_cast<double>(bounds.top()),
                static_cast<double>(bounds.right()), static_cast<double>(bounds.bottom()),
                paint.getColor(), static_cast<double>(paint.getAlphaf()));

        SkPaintFilterCanvas::onDrawTextBlob(blob, x, y, paint);
        fprintf(stderr, "[ALEX_TEXTBLOB] #%d DONE blob=%p id=%u\n",
                n, static_cast<const void*>(blob), blob->uniqueID());
        fflush(stderr);
    }
};

}  // namespace skiapipeline
}  // namespace uirenderer
}  // namespace android
