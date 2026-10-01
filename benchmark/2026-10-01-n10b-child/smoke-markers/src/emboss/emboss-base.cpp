#include "include/core/SkImageFilter.h"
#include "include/core/SkMatrix.h"
#include "src/core/SkMaskFilterBase.h"
bool SkMaskFilterBase::asABlur(BlurRec*) const {
    return false;
}

sk_sp<SkImageFilter> SkMaskFilterBase::asImageFilter(const SkMatrix& ctm) const {
    return nullptr;
}

SkMaskFilterBase::FilterReturn
SkMaskFilterBase::filterRRectToNine(const SkRRect&, const SkMatrix&,
                                    const SkIRect& clipBounds, SkTLazy<NinePatch>*) const {
    return kUnimplemented_FilterReturn;
}

SkMaskFilterBase::FilterReturn
SkMaskFilterBase::filterRectsToNine(const SkRect[], int count, const SkMatrix&,
                                    const SkIRect& clipBounds, SkTLazy<NinePatch>*) const {
    return kUnimplemented_FilterReturn;
}

void SkMaskFilterBase::computeFastBounds(const SkRect& src, SkRect* dst) const {
    SkMask srcM(nullptr, src.roundOut(), 0, SkMask::kA8_Format);
    SkMaskBuilder dstM;

    SkIPoint margin;    // ignored
    if (this->filterMask(&dstM, srcM, SkMatrix::I(), &margin)) {
        dst->set(dstM.fBounds);
    } else {
        dst->set(srcM.fBounds);
    }
}


#ifdef SKIA_OHOS
bool SkMaskFilterBase::directFilterRRectMaskGPU(GrRecordingContext* context,
                                                skgpu::ganesh::SurfaceDrawContext* sdc,
                                                GrPaint&& paint,
                                                const GrClip* clip,
                                                const SkMatrix& viewMatrix,
                                                const GrStyledShape& shape,
                                                const SkRRect& srcRRect) const
{
    return false;
}

bool SkMaskFilterBase::quick_check_gpu_draw(const SkMatrix& viewMatrix,
                                            SkIRect& devSpaceShapeBounds) const
{
    return false;
}
#endif // SKIA_OHOS
