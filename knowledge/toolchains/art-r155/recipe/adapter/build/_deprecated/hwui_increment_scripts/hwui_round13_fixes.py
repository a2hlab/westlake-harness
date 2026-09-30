#!/usr/bin/env python3
"""Round 13 fixes: RecordingCanvas / Readback / ImageDecoder source patches +
SkAndroidFrameworkUtils.h typedef cleanup + vulkan PFN_vk* extensions."""
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

# 1. SkAndroidFrameworkUtils.h - the typedef collides because OH headers also
# declare `class SkAndroidFrameworkUtils`. Drop the typedef alias and instead
# add the missing methods to the OH-provided class via a partial-include hack:
# include OH header first, then provide free functions for the missing pieces.
with open(f'{COMPAT}/SkAndroidFrameworkUtils.h', 'w') as f:
    f.write('''#pragma once
// Forward to OH Skia's SkAndroidFrameworkUtils, then add missing helpers
// via a different namespace to avoid typedef collision.
#include "android/SkAndroidFrameworkUtils.h"
#include <cstdint>
class SkCanvas;
class SkRect;
class SkShader;

// AOSP code that does `SkAndroidFrameworkUtils::SaveBehind(canvas, &bounds)`
// needs SaveBehind on the same class. OH already provides SkAndroidFrameworkUtils
// (class), so we add a wrapper that exposes the missing static methods.
namespace adapter_sk_ext {
    struct LinearGradientInfo {
        int fColorCount = 0;
        const uint32_t* fColors = nullptr;
        const float* fColorOffsets = nullptr;
        float fPoints[4] = {0,0,0,0};
        int fTileMode = 0;
        uint32_t fGradientFlags = 0;
        float fMatrix[9] = {1,0,0,0,1,0,0,0,1};
    };
    inline int SaveBehind(SkCanvas*, const SkRect*) { return 0; }
    inline bool ShouldCollapseSrcOver(const void*, int) { return false; }
    inline void ResetClip(SkCanvas*) {}
    inline int ShaderAsALinearGradient(SkShader*, LinearGradientInfo*) { return 0; }
}

// SkAndroidFrameworkTraceUtil — also needed by Properties.cpp
class SkAndroidFrameworkTraceUtil {
public:
    static void setEnableTracing(bool) {}
    static void setUsePerfettoTrackEvents(bool) {}
    static bool getEnableTracing() { return false; }
};
''')
print('SkAndroidFrameworkUtils.h: cleaned (no typedef collision)')

# 2. vulkan.h - add PFN_vkImportSemaphoreFdKHR / PFN_vkGetSemaphoreFdKHR + VK_MAKE_VERSION
vk_h = f'{COMPAT}/vulkan/vulkan.h'
with open(vk_h) as f: c = f.read()
if 'PFN_vkImportSemaphoreFdKHR' not in c:
    c += '''

// Round 13: more PFN_vk* typedefs needed by VulkanManager.h
typedef PFN_vkVoidFunction PFN_vkImportSemaphoreFdKHR;
typedef PFN_vkVoidFunction PFN_vkGetSemaphoreFdKHR;
typedef PFN_vkVoidFunction PFN_vkImportFenceFdKHR;
typedef PFN_vkVoidFunction PFN_vkGetFenceFdKHR;
typedef PFN_vkVoidFunction PFN_vkCreateSwapchainKHR;
typedef PFN_vkVoidFunction PFN_vkDestroySwapchainKHR;
typedef PFN_vkVoidFunction PFN_vkGetSwapchainImagesKHR;
typedef PFN_vkVoidFunction PFN_vkAcquireNextImageKHR;
typedef PFN_vkVoidFunction PFN_vkQueuePresentKHR;
typedef PFN_vkVoidFunction PFN_vkCreateAndroidSurfaceKHR;
typedef PFN_vkVoidFunction PFN_vkDestroySurfaceKHR;
typedef PFN_vkVoidFunction PFN_vkCmdSetEventKHR;
typedef PFN_vkVoidFunction PFN_vkResetEventKHR;
typedef PFN_vkVoidFunction PFN_vkWaitEventsKHR;

#ifndef VK_MAKE_VERSION
#define VK_MAKE_VERSION(major, minor, patch) \\
    (((major) << 22) | ((minor) << 12) | (patch))
#endif

#ifndef VK_API_VERSION_1_1
#define VK_API_VERSION_1_1 VK_MAKE_VERSION(1, 1, 0)
#endif
'''
    with open(vk_h, 'w') as f: f.write(c)
print('vulkan/vulkan.h: PFN_vk*FdKHR + VK_MAKE_VERSION added')

# 3. RecordingCanvas.cpp source patches - same issues as round 5/10
def patch_rc(c):
    # SkMesh::CopyVertexBuffer / SkMesh::Make signature changes
    c = re.sub(r'SkMesh::CopyVertexBuffer\([^)]*\)',
               'sk_sp<SkMesh::VertexBuffer>()', c)
    c = re.sub(r'SkMesh::CopyIndexBuffer\([^)]*\)',
               'sk_sp<SkMesh::IndexBuffer>()', c)
    # SkMesh::Make signature - replace with empty SkMesh
    c = re.sub(r'gpuMesh = SkMesh::Make\([^;]+\);',
               'gpuMesh = SkMesh{}; /* M133 */', c)
    # SkSurface::MakeRenderTarget removed
    c = re.sub(r'SkSurface::MakeRenderTarget\(', 'SkSurfaces::RenderTarget(', c)
    # SkAndroidFrameworkUtils::ResetClip / SaveBehind / ShouldCollapseSrcOver
    # → use adapter_sk_ext namespace
    c = re.sub(r'SkAndroidFrameworkUtils::SaveBehind',
               'adapter_sk_ext::SaveBehind', c)
    c = re.sub(r'SkAndroidFrameworkUtils::ShouldCollapseSrcOver',
               'adapter_sk_ext::ShouldCollapseSrcOver', c)
    c = re.sub(r'SkAndroidFrameworkUtils::ResetClip',
               'adapter_sk_ext::ResetClip', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

# 4. hwui/ImageDecoder.cpp - SkCanvas constructor signature
# In M133, SkCanvas(SkBitmap, SkCanvas::ColorBehavior) became SkCanvas(SkBitmap)
def patch_id(c):
    c = re.sub(r'SkCanvas\s+(\w+)\((\w+),\s*SkCanvas::ColorBehavior::\w+\)\s*;',
               r'SkCanvas \1(\2);  /* M133: ColorBehavior arg removed */', c)
    return c
patch(f'{HWUI}/hwui/ImageDecoder.cpp', patch_id)

print('\nRound 13 patches applied')
