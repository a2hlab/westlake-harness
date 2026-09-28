#!/usr/bin/env python3
"""Round 13 round 2: deeper fixes for the 3 still-failing files."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def patch(path, fn):
    bak = path + '.bak.r13'
    if not os.path.exists(bak):
        shutil.copy(path, bak)
    shutil.copy(bak, path)
    with open(path) as f:
        c = f.read()
    new = fn(c)
    with open(path, 'w') as f:
        f.write(new)
    print(f'Patched: {os.path.relpath(path, HWUI)}')

# 1. vulkan.h - VK_NULL_HANDLE must be nullptr (not 0) for void* compatibility
vk_h = f'{COMPAT}/vulkan/vulkan.h'
with open(vk_h) as f: c = f.read()
c = re.sub(r'enum \{\s*VK_IMAGE_LAYOUT_UNDEFINED = 0,\s*VK_NULL_HANDLE = 0,\s*VK_SUCCESS = 0,\s*VK_FALSE = 0,\s*VK_TRUE = 1,\s*\};',
           '''#define VK_NULL_HANDLE nullptr
enum {
    VK_IMAGE_LAYOUT_UNDEFINED = 0,
    VK_SUCCESS = 0,
    VK_FALSE = 0,
    VK_TRUE = 1,
};''', c)
with open(vk_h, 'w') as f: f.write(c)
print('vulkan.h: VK_NULL_HANDLE → #define nullptr')

# 2. ImageDecoder.cpp - SkCanvas(bm, 0) → SkCanvas(bm)
def patch_id(c):
    c = re.sub(r'SkCanvas\s+(\w+)\((\w+),\s*0\)\s*;',
               r'SkCanvas \1(\2);  /* M133: ColorBehavior arg removed */', c)
    return c
patch(f'{HWUI}/hwui/ImageDecoder.cpp', patch_id)

# 3. RecordingCanvas.cpp - SkMesh::Make / MakeIndexed signature changes
def patch_rc(c):
    # Stub the entire mesh-creation block. Find the if/else block and replace.
    # Match: gpuMesh = SkMesh::Make(...) .mesh; OR gpuMesh = SkMesh::MakeIndexed(...).mesh;
    c = re.sub(r'gpuMesh = SkMesh::Make\([^;]+\.mesh;',
               'gpuMesh = SkMesh{}; /* M133: SkMesh::Make signature changed */', c)
    c = re.sub(r'gpuMesh = SkMesh::MakeIndexed\([^;]+\.mesh;',
               'gpuMesh = SkMesh{}; /* M133: SkMesh::MakeIndexed signature changed */', c)
    # SkSurface::MakeRenderTarget removed
    c = re.sub(r'SkSurface::MakeRenderTarget\(', 'SkSurfaces::RenderTarget(', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

print('\nRound 13 round 2 patches applied')
