#!/usr/bin/env python3
"""Round 13 round 3: SkMeshes API + SkSurfaces::RenderTarget include."""
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

# RecordingCanvas.cpp - SkMeshes::Copy* takes only 1 arg now (no directContext)
def patch_rc(c):
    # SkMeshes::CopyVertexBuffer(directContext, cpuMesh.refVertexBuffer())
    #   → SkMeshes::CopyVertexBuffer(cpuMesh.refVertexBuffer())
    c = re.sub(r'SkMeshes::CopyVertexBuffer\([^,]+,\s*([^)]+)\)',
               r'SkMeshes::CopyVertexBuffer(\1)', c)
    c = re.sub(r'SkMeshes::CopyIndexBuffer\([^,]+,\s*([^)]+)\)',
               r'SkMeshes::CopyIndexBuffer(\1)', c)
    # SkMesh API simplifications already done in round 13.2
    # SkSurface::MakeRenderTarget already replaced
    # Add the SkSurfaces::RenderTarget include
    if '#include <gpu/ganesh/SkSurfaceGanesh.h>' not in c:
        c = c.replace('#include "RecordingCanvas.h"',
                      '#include "RecordingCanvas.h"\n#include <gpu/ganesh/SkSurfaceGanesh.h>')
    # SkAndroidFrameworkUtils references
    c = re.sub(r'SkAndroidFrameworkUtils::SaveBehind',
               'adapter_sk_ext::SaveBehind', c)
    c = re.sub(r'SkAndroidFrameworkUtils::ShouldCollapseSrcOver',
               'adapter_sk_ext::ShouldCollapseSrcOver', c)
    c = re.sub(r'SkAndroidFrameworkUtils::ResetClip',
               'adapter_sk_ext::ResetClip', c)
    # SkSurfaces::RenderTarget should be visible from SkSurfaceGanesh.h after include
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

# Readback.cpp - same SkSurfaces fix + SkImage::MakeFromAHardwareBuffer
def patch_rb(c):
    if '#include <gpu/ganesh/SkSurfaceGanesh.h>' not in c:
        c = c.replace('#include "Readback.h"',
                      '#include "Readback.h"\n#include <gpu/ganesh/SkSurfaceGanesh.h>\n#include <android/SkImageAndroid.h>')
    # SkImage::MakeFromAHardwareBuffer → SkImages::DeferredFromAHardwareBuffer
    c = re.sub(r'SkImage::MakeFromAHardwareBuffer\(', 'SkImages::DeferredFromAHardwareBuffer(', c)
    return c
patch(f'{HWUI}/Readback.cpp', patch_rb)

print('\nRound 13 round 3 patches applied')
