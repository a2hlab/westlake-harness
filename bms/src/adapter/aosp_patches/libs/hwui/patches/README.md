# aosp_patches/libs/hwui/patches/

Per-file unified diff patches for AOSP libhwui modifications, one `.patch` per modified source file.

## Layout

Each `.patch` mirrors the corresponding AOSP source path relative to `libs/hwui/`:

```
libs/hwui/Android.bp                    → patches/Android.bp.patch
libs/hwui/hwui/Bitmap.cpp               → patches/hwui/Bitmap.cpp.patch
libs/hwui/jni/android_nio_utils.cpp     → patches/jni/android_nio_utils.cpp.patch
libs/hwui/pipeline/skia/SkiaPipeline.cpp → patches/pipeline/skia/SkiaPipeline.cpp.patch
libs/hwui/renderthread/RenderThread.cpp → patches/renderthread/RenderThread.cpp.patch
```

## History

- **Phase A (2026-05-21)**: Mechanical split of `aosp_patches/libs/hwui/hwui_rk3568.patch`
  (1558 lines / 50 files / 137 hunks) into 50 individual `.patch` files. Byte-identical
  decomposition; same effective net diff as the original bulk patch.
- **Phase B (planned)**: Decouple chain dependencies — for files where the 7 per-file
  diff patches in `aosp_patches/frameworks/base/libs/hwui/` further modify on top of
  the bulk's effect, merge into single pristine→final standalone `.patch` here.

## Why

The original `hwui_rk3568.patch` was a bulk dump from historical Python increment
scripts. With AOSP/minikin/skia upstream evolving, many bulk hunks became stale
(43/50 files failed apply on May 2026 source state). Per-file granularity allows:

- Selective application (only apply patches that match current upstream)
- Easier review and maintenance (one .patch per file ≈ one logical change)
- No chain assumptions (each .patch is pristine→final standalone after Phase B)
- Compliance with project rule "AOSP/OH patches must be .patch unified diff files"

## How to apply

```bash
cd ~/aosp/frameworks/base
for p in aosp_patches/libs/hwui/patches/**/*.patch; do
    patch -p1 < "$p"
done
```

(The 50 patches' `--- a/libs/hwui/...` headers all use `-p1` stripping convention.)

## Status (2026-05-21 end of Phase A)

- 50 .patch files generated
- Original `hwui_rk3568.patch` retained until Phase D (when `restore_after_sync.sh`
  is updated to consume `patches/` directly)
- 7 files still have chain dependency on the corresponding per-file patches at
  `aosp_patches/frameworks/base/libs/hwui/<file>.patch`:
  - DeferredLayerUpdater.cpp.patch
  - HardwareBitmapUploader.cpp.patch
  - pipeline/skia/RenderNodeDrawable.cpp.patch
  - pipeline/skia/SkiaOpenGLPipeline.cpp.patch
  - renderthread/CanvasContext.cpp.patch
  - renderthread/EglManager.cpp.patch
  - renderthread/RenderThread.cpp.patch

Phase B will resolve the chain.
