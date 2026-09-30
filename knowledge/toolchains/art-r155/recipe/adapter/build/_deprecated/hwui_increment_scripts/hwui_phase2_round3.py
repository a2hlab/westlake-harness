#!/usr/bin/env python3
"""Round 3 patches for libhwui Phase 2 — fix Skia M133 API + minikin issues."""
import os
import re
import shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def backup_restore(path):
    orig = path + '.orig'
    if not os.path.exists(orig):
        shutil.copy(path, orig)
    shutil.copy(orig, path)

def patch(path, fn):
    backup_restore(path)
    with open(path) as f:
        c = f.read()
    new = fn(c)
    with open(path, 'w') as f:
        f.write(new)
    print(f'Patched: {os.path.basename(path)}')

# === Stub header updates ===

# 1. FileBlobCache::clear() and ::set
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write("""#pragma once
#include <cstdint>
#include <cstddef>
#include <string>
#include <memory>
namespace android {
class FileBlobCache {
public:
    FileBlobCache(size_t, size_t, const std::string&) {}
    void set(const void*, size_t, const void*, size_t) {}
    size_t get(const void*, size_t, void*, size_t) { return 0; }
    void writeToFile() {}
    void clear() {}
};
}
""")
print('FileBlobCache.h updated')

# 2. native_window.h - add NATIVE_WINDOW_TRANSFORM_ROT_*
with open(f'{COMPAT}/android/native_window.h') as f:
    c = f.read()
if 'NATIVE_WINDOW_TRANSFORM_ROT_90' not in c:
    c = c.replace('NATIVE_WINDOW_FORMAT = 4,',
'''NATIVE_WINDOW_FORMAT = 4,
    NATIVE_WINDOW_TRANSFORM_ROT_90 = 4,
    NATIVE_WINDOW_TRANSFORM_ROT_180 = 3,
    NATIVE_WINDOW_TRANSFORM_ROT_270 = 7,
    NATIVE_WINDOW_TRANSFORM_FLIP_H = 1,
    NATIVE_WINDOW_TRANSFORM_FLIP_V = 2,''')
with open(f'{COMPAT}/android/native_window.h', 'w') as f:
    f.write(c)
print('native_window.h updated')

# 3. minikin/MinikinPaint.h
with open(f'{COMPAT}/minikin/MinikinPaint.h', 'w') as f:
    f.write('#pragma once\n#include "MinikinFont.h"\n')

# 4. minikin/Measurement.h
with open(f'{COMPAT}/minikin/Measurement.h', 'w') as f:
    f.write("""#pragma once
#include <cstddef>
#include "MinikinFont.h"
namespace minikin { class Layout; }
""")
print('Measurement.h created')

# 5. FontFamily.h - add getClosestMatch
with open(f'{COMPAT}/minikin/FontFamily.h', 'w') as f:
    f.write("""#ifndef MINIKIN_FONTFAMILY_H_STUB
#define MINIKIN_FONTFAMILY_H_STUB
#include "MinikinFont.h"
namespace minikin {
class FontFamily {
public:
    FontFamily() = default;
    Font getClosestMatch(FontStyle) const { return Font(); }
};
}
#endif
""")
print('FontFamily.h updated')

# 6. AHardwareBuffer_getDataSpace stub
with open(f'{COMPAT}/android/hardware_buffer.h') as f:
    c = f.read()
if 'AHardwareBuffer_getDataSpace' not in c:
    c = c.replace('int  AHardwareBuffer_recvHandleFromUnixSocket',
                  'int32_t AHardwareBuffer_getDataSpace(AHardwareBuffer* buffer);\nint  AHardwareBuffer_recvHandleFromUnixSocket')
    with open(f'{COMPAT}/android/hardware_buffer.h', 'w') as f:
        f.write(c)
print('hardware_buffer.h updated')

# === Source code patches ===

# RecordingCanvas - stub mesh creation
def patch_rc(c):
    c = re.sub(r'SkMeshes::CopyVertexBuffer\([^)]*\)', 'sk_sp<SkMesh::VertexBuffer>()', c)
    c = re.sub(r'SkMeshes::CopyIndexBuffer\([^)]*\)', 'sk_sp<SkMesh::IndexBuffer>()', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

# DeferredLayerUpdater - stub texture target
def patch_dlu(c):
    return re.sub(r'ASurfaceTexture_getCurrentTextureTarget\([^)]*\)', '0x8D65', c)
patch(f'{HWUI}/DeferredLayerUpdater.cpp', patch_dlu)

# AutoBackendTextureRelease - GrBackendSurfaceMutableState removed
def patch_abtr(c):
    c = re.sub(r'SkImage::ReleaseContext', 'SkImages::ReleaseContext', c)
    # Comment out or replace GrBackendSurfaceMutableState
    c = re.sub(r'GrBackendSurfaceMutableState\b', 'void* /* removed M133 */', c)
    return c
patch(f'{HWUI}/AutoBackendTextureRelease.cpp', patch_abtr)

# HardwareBitmapUploader
def patch_hbu(c):
    if 'gpu/ganesh/SkImageGanesh.h' not in c:
        c = c.replace('#include "HardwareBitmapUploader.h"',
                      '#include "HardwareBitmapUploader.h"\n#include <gpu/ganesh/SkImageGanesh.h>\n#include <android/SkImageAndroid.h>')
    c = re.sub(r'SkImage::MakeFromAHardwareBufferWithData', 'SkImages::TextureFromAHardwareBufferWithData', c)
    c = re.sub(r'\.submit\(true\)', '.submit(GrSyncCpu::kYes)', c)
    c = re.sub(r'\.submit\(false\)', '.submit(GrSyncCpu::kNo)', c)
    return c
patch(f'{HWUI}/HardwareBitmapUploader.cpp', patch_hbu)

# Mesh.cpp - already removed assertions, but check fIOffset still references
def patch_mesh(c):
    c = re.sub(r'^\s*SkASSERT\([^)]*f[A-Z][A-Za-z]*[^)]*\);\s*$', '', c, flags=re.MULTILINE)
    return c
patch(f'{HWUI}/Mesh.cpp', patch_mesh)

# AnimatedImageDrawable - sk_sp release
def patch_aid(c):
    c = re.sub(r'mSkAnimatedImage->newPictureSnapshot\(\)',
               'mSkAnimatedImage->makePictureSnapshot().release()', c)
    return c
patch(f'{HWUI}/hwui/AnimatedImageDrawable.cpp', patch_aid)

# GLFunctorDrawable - topLayerBackendRenderTarget
def patch_glfd(c):
    return re.sub(r'canvas->topLayerBackendRenderTarget\(\)',
                  'GrBackendRenderTarget() /* stub */', c)
patch(f'{HWUI}/pipeline/skia/GLFunctorDrawable.cpp', patch_glfd)

print('\nAll round-3 patches applied')
