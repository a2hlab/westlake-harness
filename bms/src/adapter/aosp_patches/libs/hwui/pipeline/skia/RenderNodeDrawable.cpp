/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#include "RenderNodeDrawable.h"
#include <cstring>
#include <cstdlib>
#include <gpu/ganesh/SkImageGanesh.h>
#include <SkPaint.h>
#include <SkPaintFilterCanvas.h>
#include <SkPoint.h>
#include <SkRRect.h>
#include <SkRect.h>
#include <gui/TraceUtils.h>
#include "RenderNode.h"
#include "AlexBridgePaintProbeCanvas.h"
#include "SkiaDisplayList.h"
#include "StretchMask.h"
#include "TransformCanvas.h"

#include <include/effects/SkImageFilters.h>

#include <optional>

namespace android {
namespace uirenderer {
namespace skiapipeline {

RenderNodeDrawable::RenderNodeDrawable(RenderNode* node, SkCanvas* canvas, bool composeLayer,
                                       bool inReorderingSection)
        : mRenderNode(node)
        , mRecordedTransform(canvas->getTotalMatrix())
        , mComposeLayer(composeLayer)
        , mInReorderingSection(inReorderingSection) {}

RenderNodeDrawable::~RenderNodeDrawable() {
    // Just here to move the destructor into the cpp file where we can access RenderNode.

    // TODO: Detangle the header nightmare.
}

void RenderNodeDrawable::drawBackwardsProjectedNodes(SkCanvas* canvas,
                                                     const SkiaDisplayList& displayList,
                                                     int nestLevel) const {
    LOG_ALWAYS_FATAL_IF(0 == nestLevel && !displayList.mProjectionReceiver);
    for (auto& child : displayList.mChildNodes) {
        const RenderProperties& childProperties = child.getNodeProperties();

        // immediate children cannot be projected on their parent
        if (childProperties.getProjectBackwards() && nestLevel > 0) {
            SkAutoCanvasRestore acr2(canvas, true);
            // Apply recorded matrix, which is a total matrix saved at recording time to avoid
            // replaying all DL commands.
            canvas->concat(child.getRecordedMatrix());
            child.drawContent(canvas);
        }

        // skip walking sub-nodes if current display list contains a receiver with exception of
        // level 0, which is a known receiver
        if (0 == nestLevel || !displayList.containsProjectionReceiver()) {
            SkAutoCanvasRestore acr(canvas, true);
            SkMatrix nodeMatrix;
            mat4 hwuiMatrix(child.getRecordedMatrix());
            const RenderNode* childNode = child.getRenderNode();
            childNode->applyViewPropertyTransforms(hwuiMatrix);
            hwuiMatrix.copyTo(nodeMatrix);
            canvas->concat(nodeMatrix);
            const SkiaDisplayList* childDisplayList = childNode->getDisplayList().asSkiaDl();
            if (childDisplayList) {
                drawBackwardsProjectedNodes(canvas, *childDisplayList, nestLevel + 1);
            }
        }
    }
}

static void clipOutline(const Outline& outline, SkCanvas* canvas, const SkRect* pendingClip) {
    Rect possibleRect;
    float radius;

    /* To match the existing HWUI behavior we only supports rectangles or
     * rounded rectangles; passing in a more complicated outline fails silently.
     */
    if (!outline.getAsRoundRect(&possibleRect, &radius)) {
        if (pendingClip) {
            canvas->clipRect(*pendingClip);
        }
        const SkPath* path = outline.getPath();
        if (path) {
            canvas->clipPath(*path, SkClipOp::kIntersect, true);
        }
        return;
    }

    SkRect rect = possibleRect.toSkRect();
    if (radius != 0.0f) {
        if (pendingClip && !pendingClip->contains(rect)) {
            canvas->clipRect(*pendingClip);
        }
        canvas->clipRRect(SkRRect::MakeRectXY(rect, radius, radius), SkClipOp::kIntersect, true);
    } else {
        if (pendingClip) {
            (void)rect.intersect(*pendingClip);
        }
        canvas->clipRect(rect);
    }
}

const RenderProperties& RenderNodeDrawable::getNodeProperties() const {
    return mRenderNode->properties();
}

void RenderNodeDrawable::onDraw(SkCanvas* canvas) {
    // G2.14au r4 probe — RenderNodeDrawable::onDraw entry (DisplayList replay)
    // marker: G214au_HWR_RNDOnDraw
    {
        static std::atomic<int> g_count{0};
        int n = ++g_count;
        // AlexBridge D600 diagnostic: the old #1-only sample proved only the
        // root RenderNode.  Sample the first small tree so missing child-node
        // publication is distinguishable from a Skia replay failure.
        if (n <= 64 || n % 100 == 0) {
            fprintf(stderr, "[G214au_HWR] RenderNodeDrawable::onDraw #%d canvas=%p inReorder=%d\n",
                    n, (void*)canvas, mInReorderingSection ? 1 : 0);
            // G2.14be probe A — log DisplayList state to distinguish empty-list
            // vs early-return vs silent-replay.  marker: G214be_DLProbe_A
            RenderNode* rnA = mRenderNode.get();
            SkiaDisplayList* dlA = rnA ? rnA->getDisplayList().asSkiaDl() : nullptr;
            fprintf(stderr,
                "[G214be] A dl-state #%d rn=%p dl=%p isEmpty=%d usedSize=%zu hasText=%d hasFunctor=%d hasVecDr=%d isRenderable=%d nothingToDraw=%d composeLayer=%d projDL=%p z=%.2f\n",
                n, (void*)rnA, (void*)dlA,
                dlA ? (int)dlA->isEmpty() : -1,
                dlA ? dlA->getUsedSize() : (size_t)-1,
                dlA ? (int)dlA->hasText() : -1,
                dlA ? (int)dlA->hasFunctor() : -1,
                dlA ? (int)dlA->hasVectorDrawables() : -1,
                rnA ? (int)rnA->isRenderable() : -1,
                rnA ? (int)rnA->nothingToDraw() : -1,
                mComposeLayer ? 1 : 0,
                (void*)mProjectedDisplayList,
                rnA ? (double)rnA->properties().getZ() : 0.0);
        }
    }

    // negative and positive Z order are drawn out of order, if this render node drawable is in
    // a reordering section
    if ((!mInReorderingSection) || MathUtils::isZero(mRenderNode->properties().getZ())) {
        this->forceDraw(canvas);
    }
}

class MarkDraw {
public:
    explicit MarkDraw(SkCanvas& canvas, RenderNode& node) : mCanvas(canvas), mNode(node) {
        if (CC_UNLIKELY(Properties::skpCaptureEnabled)) {
            mNode.markDrawStart(mCanvas);
        }
    }
    ~MarkDraw() {
        if (CC_UNLIKELY(Properties::skpCaptureEnabled)) {
            mNode.markDrawEnd(mCanvas);
        }
    }

private:
    SkCanvas& mCanvas;
    RenderNode& mNode;
};

void RenderNodeDrawable::forceDraw(SkCanvas* canvas) const {
    RenderNode* renderNode = mRenderNode.get();
    MarkDraw _marker{*canvas, *renderNode};

    // We only respect the nothingToDraw check when we are composing a layer. This
    // ensures that we paint the layer even if it is not currently visible in the
    // event that the properties change and it becomes visible.
    if ((mProjectedDisplayList == nullptr && !renderNode->isRenderable()) ||
        (renderNode->nothingToDraw() && mComposeLayer)) {
        // G2.14be probe B — forceDraw early-return diagnostic.
        // marker: G214be_DLProbe_B
        {
            static std::atomic<int> g_b_count{0};
            int nb = ++g_b_count;
            if (nb <= 64 || nb % 100 == 0) {
                fprintf(stderr,
                    "[G214be] B forceDraw #%d RETURN early-skip projDL=%p renderable=%d nothingToDraw=%d composeLayer=%d\n",
                    nb, (void*)mProjectedDisplayList,
                    (int)renderNode->isRenderable(),
                    (int)renderNode->nothingToDraw(),
                    mComposeLayer ? 1 : 0);
            }
        }
        return;
    }

    SkiaDisplayList* displayList = renderNode->getDisplayList().asSkiaDl();

    SkAutoCanvasRestore acr(canvas, true);
    const RenderProperties& properties = this->getNodeProperties();
    // pass this outline to the children that may clip backward projected nodes
    displayList->mProjectedOutline =
            displayList->containsProjectionReceiver() ? &properties.getOutline() : nullptr;
    if (!properties.getProjectBackwards()) {
        drawContent(canvas);
        if (mProjectedDisplayList) {
            acr.restore();  // draw projected children using parent matrix
            LOG_ALWAYS_FATAL_IF(!mProjectedDisplayList->mProjectedOutline);
            const bool shouldClip = mProjectedDisplayList->mProjectedOutline->getPath();
            SkAutoCanvasRestore acr2(canvas, shouldClip);
            canvas->setMatrix(mProjectedDisplayList->mParentMatrix);
            if (shouldClip) {
                canvas->clipPath(*mProjectedDisplayList->mProjectedOutline->getPath());
            }
            drawBackwardsProjectedNodes(canvas, *mProjectedDisplayList);
        }
    }
    displayList->mProjectedOutline = nullptr;
}

static bool layerNeedsPaint(const LayerProperties& properties, float alphaMultiplier,
                            SkPaint* paint) {
    if (alphaMultiplier < 1.0f || properties.alpha() < 255 ||
        properties.xferMode() != SkBlendMode::kSrcOver || properties.getColorFilter() != nullptr ||
        properties.getStretchEffect().requiresLayer()) {
        paint->setAlpha(properties.alpha() * alphaMultiplier);
        paint->setBlendMode(properties.xferMode());
        paint->setColorFilter(sk_ref_sp(properties.getColorFilter()));
        return true;
    }
    return false;
}

#include "OpInspectCanvas.h"


class AlphaFilterCanvas : public SkPaintFilterCanvas {
public:
    AlphaFilterCanvas(SkCanvas* canvas, float alpha) : SkPaintFilterCanvas(canvas), mAlpha(alpha) {}

protected:
    bool onFilter(SkPaint& paint) const override {
        paint.setAlpha((uint8_t)paint.getAlpha() * mAlpha);
        return true;
    }

    void onDrawDrawable(SkDrawable* drawable, const SkMatrix* matrix) override {
        // We unroll the drawable using "this" canvas, so that draw calls contained inside will
        // get their alpha applied. The default SkPaintFilterCanvas::onDrawDrawable does not unroll.
        drawable->draw(this, matrix);
    }

private:
    float mAlpha;
};

void RenderNodeDrawable::drawContent(SkCanvas* canvas) const {
    RenderNode* renderNode = mRenderNode.get();
    float alphaMultiplier = 1.0f;
    const RenderProperties& properties = renderNode->properties();

    // If we are drawing the contents of layer, we don't want to apply any of
    // the RenderNode's properties during this pass. Those will all be applied
    // when the layer is composited.
    if (mComposeLayer) {
        setViewProperties(properties, canvas, &alphaMultiplier);
    }
    SkiaDisplayList* displayList = mRenderNode->getDisplayList().asSkiaDl();
    displayList->mParentMatrix = canvas->getTotalMatrix();

    // TODO should we let the bound of the drawable do this for us?
    const SkRect bounds = SkRect::MakeWH(properties.getWidth(), properties.getHeight());
    bool quickRejected = properties.getClipToBounds() && canvas->quickReject(bounds);
    // G2.14be probe C — drawContent quickReject diagnostic.
    // marker: G214be_DLProbe_C
    {
        static std::atomic<int> g_c_count{0};
        int nc = ++g_c_count;
        if (nc <= 64 || nc % 100 == 0) {
            fprintf(stderr,
                "[G214be] C drawContent #%d quickReject=%d clipToBounds=%d boundsW=%.1f boundsH=%.1f\n",
                nc, quickRejected ? 1 : 0,
                properties.getClipToBounds() ? 1 : 0,
                (double)(bounds.width()), (double)(bounds.height()));
        }
    }
    if (!quickRejected) {
        auto clipBounds = canvas->getLocalClipBounds();
        SkIRect srcBounds = SkIRect::MakeWH(bounds.width(), bounds.height());
        SkIPoint offset = SkIPoint::Make(0.0f, 0.0f);
        SkiaDisplayList* displayList = renderNode->getDisplayList().asSkiaDl();
        const LayerProperties& layerProperties = properties.layerProperties();
        // ==== DIAG_ONLY_NOICE_NO_HW_LAYER (2026-07-03, Step-5 HW-layer fence bisect) ====
        // NOT a real fix. Env OH_DIAG_NOICE_NO_HW_LAYER=1 forces the NON-layer inline
        // path (render the RenderNode's DisplayList directly onto the target canvas)
        // instead of compositing via getLayerSurface()->makeImageSnapshot() (the
        // b/193145089 Fence::waitForever candidate). If noice then renders+swaps+shows
        // UI, the hardware-layer snapshot/fence IS the block. Revert=env unset.
        static int __diag_nohwl = -1;
        if (__diag_nohwl < 0) {
            const char* v = getenv("OH_DIAG_NOICE_NO_HW_LAYER");
            __diag_nohwl = (v && v[0]=='1') ? 1 : 0;
        }
        // composing a hardware layer
        if (renderNode->getLayerSurface() && mComposeLayer && !__diag_nohwl) {
            fprintf(stderr,"[02A LAYER] HW-layer composite ENTER (mComposeLayer=1)\n");
            SkASSERT(properties.effectiveLayerType() == LayerType::RenderLayer);
            SkPaint paint;
            layerNeedsPaint(layerProperties, alphaMultiplier, &paint);
            sk_sp<SkImage> snapshotImage;
            auto* imageFilter = layerProperties.getImageFilter();
            auto recordingContext = canvas->recordingContext();
            // On some GL vendor implementations, caching the result of
            // getLayerSurface->makeImageSnapshot() causes a call to
            // Fence::waitForever without a corresponding signal. This would
            // lead to ANRs throughout the system.
            // Instead only cache the SkImage created with the SkImageFilter
            // for supported devices. Otherwise just create a new SkImage with
            // the corresponding SkImageFilter each time.
            // See b/193145089 and b/197263715
            if (!Properties::enableRenderEffectCache) {
                fprintf(stderr,"[02A LAYER] makeImageSnapshot START (b/193145089 fence candidate) w=%d h=%d\n",
                        renderNode->getLayerSurface()->width(), renderNode->getLayerSurface()->height());
                snapshotImage = renderNode->getLayerSurface()->makeImageSnapshot();
                fprintf(stderr,"[02A LAYER] makeImageSnapshot DONE img=%p\n",(void*)snapshotImage.get());
                if (imageFilter) {
                    auto subset = SkIRect::MakeWH(srcBounds.width(), srcBounds.height());
                    snapshotImage = SkImages::MakeWithFilter(recordingContext, snapshotImage, imageFilter,
                                                                  subset, clipBounds.roundOut(),
                                                                  &srcBounds, &offset);
                }
            } else {
                const auto snapshotResult = renderNode->updateSnapshotIfRequired(
                        recordingContext, layerProperties.getImageFilter(), clipBounds.roundOut());
                snapshotImage = snapshotResult->snapshot;
                srcBounds = snapshotResult->outSubset;
                offset = snapshotResult->outOffset;
            }

            const auto dstBounds = SkIRect::MakeXYWH(offset.x(),
                                                     offset.y(),
                                                     srcBounds.width(),
                                                     srcBounds.height());
            SkSamplingOptions sampling(SkFilterMode::kLinear);

            // surfaces for layers are created on LAYER_SIZE boundaries (which are >= layer size) so
            // we need to restrict the portion of the surface drawn to the size of the renderNode.
            SkASSERT(renderNode->getLayerSurface()->width() >= bounds.width());
            SkASSERT(renderNode->getLayerSurface()->height() >= bounds.height());

            // If SKP recording is active save an annotation that indicates this drawImageRect
            // could also be rendered with the commands saved at ID associated with this node.
            if (CC_UNLIKELY(Properties::skpCaptureEnabled)) {
                canvas->drawAnnotation(bounds, String8::format(
                    "SurfaceID|%" PRId64, renderNode->uniqueId()).c_str(), nullptr);
            }

            const StretchEffect& stretch = properties.layerProperties().getStretchEffect();
            if (stretch.isEmpty() ||
                Properties::getStretchEffectBehavior() == StretchEffectBehavior::UniformScale) {
                // If we don't have any stretch effects, issue the filtered
                // canvas draw calls to make sure we still punch a hole
                // with the same canvas transformation + clip into the target
                // canvas then draw the layer on top
                if (renderNode->hasHolePunches()) {
                    canvas->save();
                    TransformCanvas transformCanvas(canvas, SkBlendMode::kDstOut);
                    displayList->draw(&transformCanvas);
                    canvas->restore();
                }
                fprintf(stderr,"[02A LAYER] drawImageRect(snapshot) START\n");
            canvas->drawImageRect(snapshotImage, SkRect::Make(srcBounds),
                                      SkRect::Make(dstBounds), sampling, &paint,
                                      SkCanvas::kStrict_SrcRectConstraint);
            fprintf(stderr,"[02A LAYER] drawImageRect(snapshot) DONE\n");
            } else {
                // If we do have stretch effects and have hole punches,
                // then create a mask and issue the filtered draw calls to
                // get the corresponding hole punches.
                // Then apply the stretch to the mask and draw the mask to
                // the destination
                // Also if the stretchy container has an ImageFilter applied
                // to it (i.e. blur) we need to take into account the offset
                // that will be generated with this result. Ex blurs will "grow"
                // the source image by the blur radius so we need to translate
                // the shader by the same amount to render in the same location
                SkMatrix matrix;
                matrix.setTranslate(
                    offset.x() - srcBounds.left(),
                    offset.y() - srcBounds.top()
                );
                if (renderNode->hasHolePunches()) {
                    GrRecordingContext* context = canvas->recordingContext();
                    StretchMask& stretchMask = renderNode->getStretchMask();
                    stretchMask.draw(context,
                                     stretch,
                                     bounds,
                                     displayList,
                                     canvas);
                }

                sk_sp<SkShader> stretchShader =
                        stretch.getShader(bounds.width(), bounds.height(), snapshotImage, &matrix);
                paint.setShader(stretchShader);
                canvas->drawRect(SkRect::Make(dstBounds), paint);
            }

            if (!renderNode->getSkiaLayer()->hasRenderedSinceRepaint) {
                renderNode->getSkiaLayer()->hasRenderedSinceRepaint = true;
                if (CC_UNLIKELY(Properties::debugLayersUpdates)) {
                    SkPaint layerPaint;
                    layerPaint.setColor(0x7f00ff00);
                    canvas->drawRect(bounds, layerPaint);
                } else if (CC_UNLIKELY(Properties::debugOverdraw)) {
                    // Render transparent rect to increment overdraw for repaint area.
                    // This can be "else if" because flashing green on layer updates
                    // will also increment the overdraw if it happens to be turned on.
                    SkPaint transparentPaint;
                    transparentPaint.setColor(SK_ColorTRANSPARENT);
                    canvas->drawRect(bounds, transparentPaint);
                }
            }
        } else {
            if (__diag_nohwl && renderNode->getLayerSurface() && mComposeLayer) {
                fprintf(stderr,"[02A LAYER] DIAG_NOICE_NO_HW_LAYER: inline replay (skip snapshot/fence)\n");
            }
            if (alphaMultiplier < 1.0f) {
                // Non-layer draw for a view with getHasOverlappingRendering=false, will apply
                // the alpha to the paint of each nested draw.
                AlphaFilterCanvas alphaCanvas(canvas, alphaMultiplier);
                AlexBridgePaintProbeCanvas paintProbe(&alphaCanvas);
                displayList->draw(&paintProbe);
            } else {
                AlexBridgePaintProbeCanvas paintProbe(canvas);
                displayList->draw(&paintProbe);
            }
        }
    }
}

void RenderNodeDrawable::setViewProperties(const RenderProperties& properties, SkCanvas* canvas,
                                           float* alphaMultiplier) {
    if (properties.getLeft() != 0 || properties.getTop() != 0) {
        canvas->translate(properties.getLeft(), properties.getTop());
    }
    if (properties.getStaticMatrix()) {
        canvas->concat(*properties.getStaticMatrix());
    } else if (properties.getAnimationMatrix()) {
        canvas->concat(*properties.getAnimationMatrix());
    }
    if (properties.hasTransformMatrix()) {
        if (properties.isTransformTranslateOnly()) {
            canvas->translate(properties.getTranslationX(), properties.getTranslationY());
        } else {
            canvas->concat(*properties.getTransformMatrix());
        }
    }
    if (Properties::getStretchEffectBehavior() == StretchEffectBehavior::UniformScale) {
        const StretchEffect& stretch = properties.layerProperties().getStretchEffect();
        if (!stretch.isEmpty()) {
            canvas->concat(
                    stretch.makeLinearStretch(properties.getWidth(), properties.getHeight()));
        }
    }
    const bool isLayer = properties.effectiveLayerType() != LayerType::None;
    int clipFlags = properties.getClippingFlags();
    if (properties.getAlpha() < 1) {
        if (isLayer) {
            clipFlags &= ~CLIP_TO_BOUNDS;  // bounds clipping done by layer
        }
        if (CC_LIKELY(isLayer || !properties.getHasOverlappingRendering())) {
            *alphaMultiplier = properties.getAlpha();
        } else {
            // savelayer needed to create an offscreen buffer
            Rect layerBounds(0, 0, properties.getWidth(), properties.getHeight());
            if (clipFlags) {
                properties.getClippingRectForFlags(clipFlags, &layerBounds);
                clipFlags = 0;  // all clipping done by savelayer
            }
            SkRect bounds = SkRect::MakeLTRB(layerBounds.left, layerBounds.top, layerBounds.right,
                                             layerBounds.bottom);
            canvas->saveLayerAlpha(&bounds, (int)(properties.getAlpha() * 255));
        }

        if (CC_UNLIKELY(ATRACE_ENABLED() && properties.promotedToLayer())) {
            // pretend alpha always causes savelayer to warn about
            // performance problem affecting old versions
            ATRACE_FORMAT("alpha caused saveLayer %dx%d", properties.getWidth(),
                          properties.getHeight());
        }
    }

    const SkRect* pendingClip = nullptr;
    SkRect clipRect;

    if (clipFlags) {
        Rect tmpRect;
        properties.getClippingRectForFlags(clipFlags, &tmpRect);
        clipRect = tmpRect.toSkRect();
        pendingClip = &clipRect;
    }

    if (properties.getRevealClip().willClip()) {
        canvas->clipPath(*properties.getRevealClip().getPath(), SkClipOp::kIntersect, true);
    } else if (properties.getOutline().willClip()) {
        clipOutline(properties.getOutline(), canvas, pendingClip);
        pendingClip = nullptr;
    }

    if (pendingClip) {
        canvas->clipRect(*pendingClip);
    }
}

}  // namespace skiapipeline
}  // namespace uirenderer
}  // namespace android
