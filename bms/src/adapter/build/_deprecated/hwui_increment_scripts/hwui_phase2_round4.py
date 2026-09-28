#!/usr/bin/env python3
"""Round 4 patches for libhwui Phase 2 - final round."""
import os
import re
import shutil

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
    print(f'Patched: {os.path.basename(path)}')

# 1. minikin/MinikinRect.h stub
with open(f'{COMPAT}/minikin/MinikinRect.h', 'w') as f:
    f.write('#pragma once\n#include "MinikinFont.h"\n')

# 2. FileBlobCache constructor variants
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write("""#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <memory>
namespace android {
class BlobCache {
public:
    BlobCache(size_t, size_t, size_t) {}
};
class FileBlobCache : public BlobCache {
public:
    FileBlobCache(size_t a, size_t b, const std::string&) : BlobCache(a, b, 0) {}
    FileBlobCache(size_t a, size_t b, size_t c, const std::string&) : BlobCache(a, b, c) {}
    void set(const void*, size_t, const void*, size_t) {}
    size_t get(const void*, size_t, void*, size_t) { return 0; }
    void writeToFile() {}
    void clear() {}
};
}
""")
print('FileBlobCache.h fixed')

# 3. GLFunctorDrawable - GrGLTypes include
def patch_glfd(c):
    if 'gpu/ganesh/gl/GrGLTypes.h' not in c:
        c = c.replace('#include "GLFunctorDrawable.h"',
                      '#include "GLFunctorDrawable.h"\n#include <gpu/ganesh/gl/GrGLTypes.h>')
    return c
patch(f'{HWUI}/pipeline/skia/GLFunctorDrawable.cpp', patch_glfd)

# 4. RecordingCanvas - SkCanvas::flush() removed; remove the call entirely
def patch_rc(c):
    c = re.sub(r'(\w+)->flush\(\);', r'/* \1->flush() removed in M133 */', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

# 5. AutoBackendTextureRelease - SkImage::MakeFromTexture
def patch_abtr(c):
    if 'gpu/ganesh/SkImageGanesh.h' not in c:
        c = c.replace('#include "AutoBackendTextureRelease.h"',
                      '#include "AutoBackendTextureRelease.h"\n#include <gpu/ganesh/SkImageGanesh.h>')
    c = re.sub(r'SkImage::MakeFromTexture', 'SkImages::BorrowTextureFrom', c)
    c = re.sub(r'SkImage::ReleaseContext', 'SkImages::ReleaseContext', c)
    c = re.sub(r'GrBackendSurfaceMutableState\b', 'void* /* removed M133 */', c)
    return c
patch(f'{HWUI}/AutoBackendTextureRelease.cpp', patch_abtr)

# 6. HardwareBitmapUploader - submit signature
def patch_hbu(c):
    if 'gpu/ganesh/SkImageGanesh.h' not in c:
        c = c.replace('#include "HardwareBitmapUploader.h"',
                      '#include "HardwareBitmapUploader.h"\n#include <gpu/ganesh/SkImageGanesh.h>\n#include <android/SkImageAndroid.h>')
    c = re.sub(r'SkImage::MakeFromAHardwareBufferWithData', 'SkImages::TextureFromAHardwareBufferWithData', c)
    # The submit() with bool arg - try various forms
    c = re.sub(r'->submit\(true\)', '->submit(GrSyncCpu::kYes)', c)
    c = re.sub(r'->submit\(false\)', '->submit(GrSyncCpu::kNo)', c)
    c = re.sub(r'\.submit\(true\)', '.submit(GrSyncCpu::kYes)', c)
    c = re.sub(r'\.submit\(false\)', '.submit(GrSyncCpu::kNo)', c)
    return c
patch(f'{HWUI}/HardwareBitmapUploader.cpp', patch_hbu)

# 7. Readback - SkImage::MakeFromAHardwareBuffer
def patch_readback(c):
    if 'android/SkImageAndroid.h' not in c:
        c = c.replace('#include "Readback.h"',
                      '#include "Readback.h"\n#include <android/SkImageAndroid.h>\n#include <gpu/ganesh/SkImageGanesh.h>')
    c = re.sub(r'SkImage::MakeFromAHardwareBuffer\(', 'SkImages::DeferredFromAHardwareBuffer(', c)
    return c
patch(f'{HWUI}/Readback.cpp', patch_readback)

# 8. MinikinPaint constructor - libhwui passes args, our stub has no args
# Just leave the failure for now - it's a deeper minikin issue
# Same for Typeface getClosestMatch returning Font::font - just stub the access

# 9. DeferredLayerUpdater - check what's still broken
# Read the file and see line 58
import subprocess
result = subprocess.run(['sed', '-n', '55,62p', f'{HWUI}/DeferredLayerUpdater.cpp'],
                       capture_output=True, text=True)
print('DeferredLayerUpdater line 55-62:')
print(result.stdout)

print('\nAll round-4 patches applied')
