#!/usr/bin/env python3
"""Round 2 batch patches for libhwui Phase 2 files."""
import os
import re
import shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

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

# 1. Fix SkShadowFlags redefinition - check if it's already in some Skia header
# Make our stub conditional
with open(f'{COMPAT}/include/private/SkShadowFlags.h', 'w') as f:
    f.write("""#pragma once
#ifndef SK_SHADOW_FLAGS_DEFINED
#define SK_SHADOW_FLAGS_DEFINED
enum SkShadowFlags_Compat {
    kNone_ShadowFlag = 0x00,
    kTransparentOccluder_ShadowFlag = 0x01,
    kGeometricOnly_ShadowFlag = 0x02,
    kDirectionalLight_ShadowFlag = 0x04,
    kConcaveBlurOnly_ShadowFlag = 0x08,
    kAll_ShadowFlag = 0x0F,
};
#endif
""")

# 2. ShaderCache.h needs GrDirectContext - add forward declare
def patch_sch(c):
    if 'gpu/ganesh/GrDirectContext.h' not in c:
        c = c.replace('#pragma once', '#pragma once\n#include <gpu/ganesh/GrDirectContext.h>')
    return c
patch(f'{HWUI}/pipeline/skia/ShaderCache.h', patch_sch)

# 3. Stub android/surface_texture.h
with open(f'{COMPAT}/android/surface_texture.h', 'w') as f:
    f.write("""#ifndef ANDROID_SURFACE_TEXTURE_H_STUB
#define ANDROID_SURFACE_TEXTURE_H_STUB
#include <cstdint>
#ifdef __cplusplus
extern "C" {
#endif
struct ASurfaceTexture;
struct ANativeWindow;
ASurfaceTexture* ASurfaceTexture_fromSurfaceTexture(void* env, void* surfaceTexture);
ANativeWindow* ASurfaceTexture_acquireANativeWindow(ASurfaceTexture* st);
void ASurfaceTexture_release(ASurfaceTexture* st);
int ASurfaceTexture_attachToGLContext(ASurfaceTexture* st, uint32_t texName);
int ASurfaceTexture_detachFromGLContext(ASurfaceTexture* st);
int ASurfaceTexture_updateTexImage(ASurfaceTexture* st);
void ASurfaceTexture_getTransformMatrix(ASurfaceTexture* st, float mtx[16]);
int64_t ASurfaceTexture_getTimestamp(ASurfaceTexture* st);
#ifdef __cplusplus
}
#endif
#endif
""")

# 4. GLFunctorDrawable.cpp - GrGLFramebufferInfo needs include
def patch_glfd(c):
    if 'gpu/ganesh/gl/GrGLTypes.h' not in c:
        c = c.replace('#include "GLFunctorDrawable.h"',
                      '#include "GLFunctorDrawable.h"\n#include <gpu/ganesh/gl/GrGLTypes.h>')
    return c
patch(f'{HWUI}/pipeline/skia/GLFunctorDrawable.cpp', patch_glfd)

# 5. Add minikin::FontVariation, MinikinPaint, etc. to minikin/FontCollection.h
with open(f'{COMPAT}/minikin/FontCollection.h', 'w') as f:
    f.write("""#ifndef MINIKIN_FONTCOLLECTION_H_STUB
#define MINIKIN_FONTCOLLECTION_H_STUB
#include <memory>
#include <vector>
#include <cstdint>
namespace minikin {
struct FontStyle {
    uint16_t weight = 400;
    uint8_t  slant = 0;
    enum Slant : uint8_t { kUpright = 0, kItalic = 1 };
    constexpr FontStyle() = default;
    constexpr FontStyle(uint16_t w, Slant s) : weight(w), slant((uint8_t)s) {}
};
struct FontVariation {
    uint32_t axisTag = 0;
    float value = 0.0f;
    FontVariation() = default;
    FontVariation(uint32_t t, float v) : axisTag(t), value(v) {}
};
struct FontFakery {
    bool isFakeBold = false;
    bool isFakeItalic = false;
};
class MinikinPaint {
public:
    float size = 14.0f;
    float scaleX = 1.0f;
    float skewX = 0.0f;
    FontStyle fontStyle;
    int32_t letterSpacing = 0;
    int32_t wordSpacing = 0;
    uint32_t paintFlags = 0;
};
class FontFamily;
class Font;
class Hyphenator;
class FontCollection {
public:
    FontCollection() = default;
    static std::shared_ptr<FontCollection> create() { return std::make_shared<FontCollection>(); }
};
class MinikinFont {};
class Layout {};
class LineBreaker {};
class MeasuredText {};
class GraphemeBreak {};
}
#endif
""")

# 6. AnimatedImageDrawable.cpp - newPictureSnapshot was renamed
def patch_aid(c):
    # Replace newPictureSnapshot() with makePictureSnapshot() or similar
    return re.sub(r'mSkAnimatedImage->newPictureSnapshot\(\)',
                  'mSkAnimatedImage->makePictureSnapshot()  /* OH adapter */', c)
patch(f'{HWUI}/hwui/AnimatedImageDrawable.cpp', patch_aid)

# 7. RecordingCanvas.cpp - SkCanvas::flush() removed in M133
def patch_rc2(c):
    return re.sub(r'(\w+)->flush\(\)',
                  r'/* \1->flush() removed in M133 */', c)
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc2)

# 8. AutoBackendTextureRelease.cpp - SkImage::MakeFromTexture
def patch_abtr2(c):
    if 'gpu/ganesh/SkImageGanesh.h' not in c:
        c = c.replace('#include "AutoBackendTextureRelease.h"',
                      '#include "AutoBackendTextureRelease.h"\n#include <gpu/ganesh/SkImageGanesh.h>')
    return re.sub(r'SkImage::MakeFromTexture', 'SkImages::BorrowTextureFrom', c)
patch(f'{HWUI}/AutoBackendTextureRelease.cpp', patch_abtr2)

# 9. HardwareBitmapUploader.cpp - submit signature change
def patch_hbu2(c):
    # The submit() in M133 takes GrSyncCpu enum
    c = re.sub(r'\.submit\(true\)', '.submit(GrSyncCpu::kYes)', c)
    c = re.sub(r'\.submit\(false\)', '.submit(GrSyncCpu::kNo)', c)
    return c
patch(f'{HWUI}/HardwareBitmapUploader.cpp', patch_hbu2)

# 10. Readback.cpp - ARect type
def patch_readback(c):
    # ARect comes from <android/rect.h>
    if '<android/rect.h>' not in c:
        c = c.replace('#include "Readback.h"',
                      '#include "Readback.h"\n#include <android/rect.h>')
    return c
patch(f'{HWUI}/Readback.cpp', patch_readback)

# 11. Mesh.cpp - my prior patch broke 'remove' identifier
# Restore from .orig and re-patch correctly
def patch_mesh(c):
    # Just remove SkASSERT lines containing fICount
    c = re.sub(r'^\s*SkASSERT\([^)]*fICount[^)]*\);?\s*$', '', c, flags=re.MULTILINE)
    return c
patch(f'{HWUI}/Mesh.cpp', patch_mesh)

print('All v2 patches applied')
