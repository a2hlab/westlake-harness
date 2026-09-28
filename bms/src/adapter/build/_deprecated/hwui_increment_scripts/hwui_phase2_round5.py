#!/usr/bin/env python3
"""Round 5: fix the remaining 10 Phase 2 + 4 JNI compile failures."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def patch(path, fn):
    orig = path + '.orig'
    if not os.path.exists(orig):
        shutil.copy(path, orig)
    shutil.copy(orig, path)
    with open(path) as f:
        c = f.read()
    new = fn(c)
    with open(path, 'w') as f:
        f.write(new)
    print(f'Patched: {os.path.relpath(path, HWUI)}')

# ============ Stub header updates ============

# 1. MinikinFont.h - add missing fields/types
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f:
    f.write('''#ifndef MINIKIN_MINIKINFONT_H_STUB
#define MINIKIN_MINIKINFONT_H_STUB
#include <cstdint>
#include <vector>
#include <string>
#include <memory>

namespace minikin {

class FontCollection;  // forward

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
    FontFakery() = default;
    FontFakery(bool b, bool i) : isFakeBold(b), isFakeItalic(i) {}
};

struct MinikinRect {
    float mLeft = 0;
    float mTop = 0;
    float mRight = 0;
    float mBottom = 0;
};

struct MinikinExtent {
    float ascent = 0;
    float descent = 0;
    float line_gap = 0;
};

// Bitfield shifts referenced by hwui MinikinSkia.cpp
constexpr int Embolden_Shift = 0;
constexpr int LinearMetrics_Shift = 1;
constexpr int Subpixel_Shift = 2;

class MinikinPaint {
public:
    float size = 14.0f;
    float scaleX = 1.0f;
    float skewX = 0.0f;
    FontStyle fontStyle;
    int32_t letterSpacing = 0;
    int32_t wordSpacing = 0;
    uint32_t paintFlags = 0;
    uint32_t fontFlags = 0;  // alias used by some hwui code paths
    std::shared_ptr<FontCollection> font;
    MinikinPaint() = default;
    MinikinPaint(const std::shared_ptr<FontCollection>& fc) : font(fc) {}
};

enum class Bidi : uint8_t {
    LTR = 0, RTL = 1, DEFAULT_LTR = 2, DEFAULT_RTL = 3, FORCE_LTR = 4, FORCE_RTL = 5,
};

class MinikinFont {
public:
    virtual ~MinikinFont() {}
    virtual float GetHorizontalAdvance(uint32_t, const MinikinPaint&, const FontFakery&) const { return 0; }
    virtual void GetHorizontalAdvances(uint16_t*, uint32_t, const MinikinPaint&, const FontFakery&, float*) const {}
    virtual void GetBounds(MinikinRect*, uint32_t, const MinikinPaint&, const FontFakery&) const {}
    virtual void GetFontExtent(MinikinExtent*, const MinikinPaint&, const FontFakery&) const {}
    virtual const std::string& GetFontPath() const { static std::string s; return s; }
    virtual int GetSourceId() const { return 0; }
    virtual int32_t GetUniqueId() const { return 0; }
    virtual int GetFontIndex() const { return 0; }
    virtual const std::vector<FontVariation>& GetAxes() const { static std::vector<FontVariation> v; return v; }
    virtual const void* GetFontData() const { return nullptr; }
    virtual size_t GetFontSize() const { return 0; }
};

class FontStub {  // helper used by Font::font field
public:
    std::shared_ptr<MinikinFont> typeface() const {
        static std::shared_ptr<MinikinFont> defaultFont = std::make_shared<MinikinFont>();
        return defaultFont;
    }
};

class Font {
public:
    Font() = default;
    FontStub* font = nullptr;
    std::shared_ptr<MinikinFont> typeface() const {
        static std::shared_ptr<MinikinFont> defaultFont = std::make_shared<MinikinFont>();
        return defaultFont;
    }
    class Builder {
    public:
        Builder(const Font&) {}
        Builder(const std::shared_ptr<MinikinFont>&) {}
        Font build() { return Font(); }
    };
};

class MeasuredText {};

}
#endif
''')
print('MinikinFont.h updated')

# 2. FileBlobCache.h - move get/set to BlobCache base
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <memory>
namespace android {
class BlobCache {
public:
    BlobCache(size_t = 0, size_t = 0, size_t = 0) {}
    enum class InsertResult { kInserted = 0, kKeyTooLarge = 1, kValueTooLarge = 2 };
    InsertResult set(const void*, size_t, const void*, size_t) { return InsertResult::kInserted; }
    InsertResult set(const std::string&, size_t, const void*, size_t) { return InsertResult::kInserted; }
    size_t get(const void*, size_t, void*, size_t) { return 0; }
};
class FileBlobCache : public BlobCache {
public:
    FileBlobCache(size_t a, size_t b, const std::string&) : BlobCache(a, b, 0) {}
    FileBlobCache(size_t a, size_t b, size_t c, const std::string&) : BlobCache(a, b, c) {}
    void writeToFile() {}
    void clear() {}
};
}
''')
print('FileBlobCache.h updated')

# 3. media/NdkImage.h stub
os.makedirs(f'{COMPAT}/media', exist_ok=True)
with open(f'{COMPAT}/media/NdkImage.h', 'w') as f:
    f.write('#pragma once\ntypedef struct AImage AImage;\ntypedef int media_status_t;\nenum { AIMAGE_FORMAT_RGBA_8888 = 1 };\n')
print('media/NdkImage.h created')

# 4. nativehelper/jni_macros.h stub
os.makedirs(f'{COMPAT}/nativehelper', exist_ok=True)
with open(f'{COMPAT}/nativehelper/jni_macros.h', 'w') as f:
    f.write('''#pragma once
// Stub: jni_macros for fast JNI method registration.
#define MAKE_JNI_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_FAST_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_CRITICAL_NATIVE_METHOD(name, sig, fnPtr) {(char*)name, (char*)sig, reinterpret_cast<void*>(fnPtr)}
#define MAKE_JNI_NATIVE_METHOD_AUTOSIG(name, fnPtr) {(char*)name, (char*)"()V", reinterpret_cast<void*>(fnPtr)}
''')
print('nativehelper/jni_macros.h created')

# 5. minikin/GraphemeBreak.h stub
with open(f'{COMPAT}/minikin/GraphemeBreak.h', 'w') as f:
    f.write('''#pragma once
#include <cstddef>
#include <cstdint>
namespace minikin {
class GraphemeBreak {
public:
    static size_t getTextRunCursor(const float*, const uint16_t*, size_t, size_t, size_t, int) { return 0; }
    static bool isGraphemeBreak(const float*, const uint16_t*, size_t, size_t, size_t) { return true; }
};
}
''')
print('minikin/GraphemeBreak.h created')

# ============ Source patches ============

# 6. AutoBackendTextureRelease.cpp - stub MutableTextureState block
def patch_abtr(c):
    c = re.sub(
        r'void\* /\* removed M133 \*/ newState\([^)]*\)',
        'void* newState = nullptr; (void)nullptr',
        c, flags=re.DOTALL)
    c = c.replace(
        'context->setBackendTextureState(mBackendTexture, newState, nullptr, releaseProc, this);',
        '/* M133: setBackendTextureState requires MutableTextureState; stubbed for adapter */ (void)releaseProc;')
    return c
patch(f'{HWUI}/AutoBackendTextureRelease.cpp', patch_abtr)

# 7. DeferredLayerUpdater.cpp - stub ASurfaceTexture/ARect
def patch_dlu(c):
    if 'OH adapter stubs for missing ASurfaceTexture' not in c:
        c = c.replace('#include "DeferredLayerUpdater.h"',
            '''#include "DeferredLayerUpdater.h"
// OH adapter stubs for missing ASurfaceTexture/ARect APIs
typedef struct ARect_stub { int32_t left, top, right, bottom; } ARect;
extern "C" {
static inline int ASurfaceTexture_releaseConsumerOwnership(void*) { return 0; }
static inline int ASurfaceTexture_takeConsumerOwnership(void*) { return 0; }
static inline int ASurfaceTexture_getTransformMatrix(void*, float[16]) { return 0; }
static inline int ASurfaceTexture_getCropRect(void*, ARect*) { return 0; }
}''')
    return c
patch(f'{HWUI}/DeferredLayerUpdater.cpp', patch_dlu)

# 8. HardwareBitmapUploader.cpp - remove duplicate definitions
def patch_hbu(c):
    c = re.sub(r'bool HardwareBitmapUploader::hasFP16Support\(\)\s*\{[^}]*\}\s*',
               '/* M133: out-of-line redefinition removed */\n', c)
    c = re.sub(r'bool HardwareBitmapUploader::has1010102Support\(\)\s*\{[^}]*\}\s*',
               '/* M133: out-of-line redefinition removed */\n', c)
    return c
patch(f'{HWUI}/HardwareBitmapUploader.cpp', patch_hbu)

# 9. MinikinSkia.cpp - fontFlags rename
def patch_msk(c):
    c = re.sub(r'paint\.fontFlags', 'paint.paintFlags', c)
    return c
patch(f'{HWUI}/hwui/MinikinSkia.cpp', patch_msk)

# 10. Typeface.cpp - access patterns
def patch_tf(c):
    c = re.sub(r'\.font->typeface\(\)', '.typeface()', c)
    c = re.sub(r'SkTypeface::MakeFromStream\([^)]*\)', 'sk_sp<SkTypeface>(nullptr)', c)
    return c
patch(f'{HWUI}/hwui/Typeface.cpp', patch_tf)

# 11. GLFunctorDrawable.cpp - topLayerBackendRenderTarget removed
def patch_glfd(c):
    c = c.replace('canvas->topLayerBackendRenderTarget()',
                  'GrBackendRenderTarget() /* M133 stub */')
    c = re.sub(r'renderTarget\.getGLFramebufferInfo\(&fboInfo\)',
               'false /* M133: getGLFramebufferInfo removed */', c)
    return c
patch(f'{HWUI}/pipeline/skia/GLFunctorDrawable.cpp', patch_glfd)

# 12. Readback.cpp - ARect + MakeRenderTarget
def patch_rb(c):
    if 'OH adapter stub for ARect' not in c:
        c = c.replace('#include "Readback.h"',
            '''#include "Readback.h"
// OH adapter stub for ARect
typedef struct ARect_stub { int32_t left, top, right, bottom; } ARect;''')
    c = re.sub(r'SkSurface::MakeRenderTarget\(', 'SkSurfaces::RenderTarget(', c)
    return c
patch(f'{HWUI}/Readback.cpp', patch_rb)

# 13. RecordingCanvas.cpp - SkMesh API moves
def patch_rc(c):
    c = re.sub(r'SkMesh::CopyVertexBuffer\(', 'SkMeshes::CopyVertexBuffer(', c)
    c = re.sub(r'SkMesh::CopyIndexBuffer\(',  'SkMeshes::CopyIndexBuffer(',  c)
    c = re.sub(r'gpuMesh = SkMesh::Make\([^;]+\);',
               'gpuMesh = SkMesh{}; /* M133: SkMesh::Make signature changed */', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

# ============ JNI source patches ============

# 14. android_graphics_HardwareRenderer.cpp - stub NdkImage include
def patch_jhr(c):
    c = c.replace('#include <media/NdkImage.h>',
                  '// #include <media/NdkImage.h>  // M133 stub')
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_jhr)

# 15. MaskFilter.cpp - SkBlurMaskFilter::MakeEmboss removed
def patch_mf(c):
    c = re.sub(r'SkBlurMaskFilter::MakeEmboss\([^;]+\);',
               'nullptr; /* M133: MakeEmboss removed */', c)
    return c
patch(f'{HWUI}/jni/MaskFilter.cpp', patch_mf)

print('\nRound 5 patches applied')
