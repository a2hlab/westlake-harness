#!/usr/bin/env python3
"""Batch patches for libhwui Phase 2 files."""
import os
import re
import shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'

def backup(path):
    orig = path + '.orig'
    if not os.path.exists(orig):
        shutil.copy(path, orig)
    shutil.copy(orig, path)

def patch(path, fn):
    backup(path)
    with open(path) as f:
        c = f.read()
    new = fn(c)
    with open(path, 'w') as f:
        f.write(new)
    print(f'Patched: {os.path.basename(path)}')

# 1. StretchMask.cpp
def patch_stretchmask(c):
    if 'gpu/ganesh/SkSurfaceGanesh.h' not in c:
        c = c.replace('#include "StretchMask.h"',
                      '#include "StretchMask.h"\n#include <gpu/ganesh/SkSurfaceGanesh.h>')
    return re.sub(r'SkSurface::MakeRenderTarget', 'SkSurfaces::RenderTarget', c)
patch(f'{HWUI}/pipeline/skia/StretchMask.cpp', patch_stretchmask)

# 2. RenderNodeDrawable.cpp
def patch_rnd(c):
    if 'gpu/ganesh/SkImageGanesh.h' not in c:
        c = c.replace('#include "RenderNodeDrawable.h"',
                      '#include "RenderNodeDrawable.h"\n#include <gpu/ganesh/SkImageGanesh.h>')
    c = re.sub(r'snapshotImage->makeWithFilter\(recordingContext,',
               'SkImages::MakeWithFilter(recordingContext, snapshotImage,', c)
    return c
patch(f'{HWUI}/pipeline/skia/RenderNodeDrawable.cpp', patch_rnd)

# 3. GLFunctorDrawable.cpp - topLayerBackendRenderTarget removed
def patch_glfd(c):
    return re.sub(r'canvas->topLayerBackendRenderTarget\(\)',
                  'GrBackendRenderTarget() /* OH adapter stub */', c)
patch(f'{HWUI}/pipeline/skia/GLFunctorDrawable.cpp', patch_glfd)

# 4. hwui/Bitmap.cpp - SkEncodeImage replaced
def patch_bitmap(c):
    if 'encode/SkPngEncoder.h' not in c:
        c = c.replace('#include "Bitmap.h"',
                      '#include "Bitmap.h"\n#include <encode/SkPngEncoder.h>\n#include <encode/SkJpegEncoder.h>\n#include <encode/SkWebpEncoder.h>')
    # Replace SkEncodeImage call with format-specific encoder switch
    encoder_block = (
        'switch (fm) {\n'
        '        case SkEncodedImageFormat::kPNG: { SkPngEncoder::Options o; return SkPngEncoder::Encode(stream, bitmap.pixmap(), o); }\n'
        '        case SkEncodedImageFormat::kJPEG: { SkJpegEncoder::Options o; o.fQuality = quality; return SkJpegEncoder::Encode(stream, bitmap.pixmap(), o); }\n'
        '        case SkEncodedImageFormat::kWEBP: { SkWebpEncoder::Options o; o.fQuality = quality; return SkWebpEncoder::Encode(stream, bitmap.pixmap(), o); }\n'
        '        default: return false;\n'
        '    }'
    )
    c = c.replace('return SkEncodeImage(stream, bitmap, fm, quality);', encoder_block)
    return c
patch(f'{HWUI}/hwui/Bitmap.cpp', patch_bitmap)

# 5. CanvasTransform.cpp - filterColor signature change
def patch_ct(c):
    return re.sub(r'paint->getColorFilter\(\)->filterColor\(color\)',
                  'color /* OH adapter: filterColor stub */', c)
patch(f'{HWUI}/CanvasTransform.cpp', patch_ct)

# 6. AutoBackendTextureRelease.cpp
def patch_abtr(c):
    return re.sub(r'SkImage::ReleaseContext', 'SkImages::ReleaseContext', c)
patch(f'{HWUI}/AutoBackendTextureRelease.cpp', patch_abtr)

# 7. HardwareBitmapUploader.cpp
def patch_hbu(c):
    if 'android/SkImageAndroid.h' not in c:
        c = c.replace('#include "HardwareBitmapUploader.h"',
                      '#include "HardwareBitmapUploader.h"\n#include <android/SkImageAndroid.h>')
    return re.sub(r'SkImage::MakeFromAHardwareBufferWithData', 'SkImages::TextureFromAHardwareBufferWithData', c)
patch(f'{HWUI}/HardwareBitmapUploader.cpp', patch_hbu)

# 8. Mesh.cpp - fICount private access stub
def patch_mesh(c):
    c = re.sub(r'SkASSERT\(!fICount\);?', '/* SkASSERT(!fICount) removed */', c)
    c = re.sub(r'SkASSERT\(([^)]*fICount[^)]*)\);?', r'/* SkASSERT(\1) removed */', c)
    return c
patch(f'{HWUI}/Mesh.cpp', patch_mesh)

# 9. WebViewFunctorManager.cpp
def patch_wvfm(c):
    c = c.replace('ASURFACE_TRANSACTION_VISIBILITY_SHOW', '1')
    c = c.replace('ASURFACE_TRANSACTION_VISIBILITY_HIDE', '0')
    return c
patch(f'{HWUI}/WebViewFunctorManager.cpp', patch_wvfm)

# 10. RecordingCanvas.cpp - GrDirectContext.h path
def patch_rc(c):
    if 'gpu/ganesh/GrDirectContext.h' not in c:
        c = c.replace('#include "include/gpu/GrDirectContext.h"',
                      '#include <gpu/ganesh/GrDirectContext.h>')
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

print('All patches applied')
