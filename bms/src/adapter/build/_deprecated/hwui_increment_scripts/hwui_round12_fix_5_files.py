#!/usr/bin/env python3
"""Round 12: fix the 5 source files whose missing .o causes 19 unresolved
symbols in libhwui.so:
  - renderthread/EglManager.cpp
  - Readback.cpp
  - hwui/ImageDecoder.cpp
  - hwui/Canvas.cpp
  - RecordingCanvas.cpp

Strategy:
  - Update shim headers to provide missing types/macros
  - Patch source files only when needed (prefer header shims)
  - Cumulative: re-applies all earlier rounds first via .orig
"""
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

# ============================================================================
# 1. SkAndroidFrameworkUtils.h — REMOVE the ResetClip macro from round 11
#    (It conflicts with Skia's internal SkCanvasPriv::ResetClip class member)
#    Provide SkAndroidFrameworkUtils as an aliased class instead.
# ============================================================================
with open(f'{COMPAT}/SkAndroidFrameworkUtils.h', 'w') as f:
    f.write('''#pragma once
#include "android/SkAndroidFrameworkUtils.h"
#include <cstdint>
class SkCanvas;
// Adapter extension: SkAndroidFrameworkUtils helpers that AOSP expects but
// OH Skia M133 does not export. Provide as inline static methods on a class
// that mirrors the Android-flavored Skia naming.
class SkAndroidFrameworkUtilsAdapter {
public:
    struct LinearGradientInfo {
        int fColorCount = 0;
        const uint32_t* fColors = nullptr;
        const float* fColorOffsets = nullptr;
        float fPoints[4] = {0,0,0,0};
        int fTileMode = 0;
        uint32_t fGradientFlags = 0;
        float fMatrix[9] = {1,0,0,0,1,0,0,0,1};
    };
    static int SaveBehind(SkCanvas*, const SkRect*) { return 0; }
    static bool ShouldCollapseSrcOver(const void*, int) { return false; }
    // Note: ResetClip is intentionally NOT a macro here — Skia's SkCanvasPriv
    // has a member named ResetClip that would otherwise be mangled.
    static void ResetClip(SkCanvas*) {}
    static int ShaderAsALinearGradient(class SkShader*, LinearGradientInfo*) { return 0; }
};
// Alias so AOSP code that does `SkAndroidFrameworkUtils::Foo` finds it.
typedef SkAndroidFrameworkUtilsAdapter SkAndroidFrameworkUtils;
''')
print('SkAndroidFrameworkUtils.h: removed ResetClip macro, aliased class')

# ============================================================================
# 2. android/native_window.h — add ANativeWindow_setBuffersDataSpace decl
# ============================================================================
nw_h = f'{COMPAT}/android/native_window.h'
with open(nw_h) as f:
    nw_content = f.read()
if 'ANativeWindow_setBuffersDataSpace' not in nw_content:
    # Append at end (it was already done in round 9 but might have been undone)
    nw_content += '''
// Round 12: explicitly declare these for EglManager.cpp
#ifdef __cplusplus
extern "C" {
#endif
int ANativeWindow_setBuffersDataSpace(ANativeWindow* window, int dataSpace);
int ANativeWindow_getBuffersDataSpace(ANativeWindow* window);
#ifdef __cplusplus
}
#endif
'''
    with open(nw_h, 'w') as f:
        f.write(nw_content)
print('android/native_window.h: setBuffersDataSpace declared')

# ============================================================================
# 3. vulkan/vulkan.h — add the full set of PFN_vk* function pointer typedefs
# ============================================================================
with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f:
    f.write('''#pragma once
#define VKAPI_PTR
#define VKAPI_ATTR
#define VKAPI_CALL

// Stub: HWUI_NO_VULKAN should disable Vulkan paths but headers still reference types.
#include <cstdint>

typedef void* VkInstance;
typedef void* VkDevice;
typedef void* VkPhysicalDevice;
typedef void* VkQueue;
typedef void* VkCommandBuffer;
typedef void* VkImage;
typedef void* VkImageView;
typedef void* VkBuffer;
typedef void* VkSemaphore;
typedef void* VkFence;
typedef void* VkRenderPass;
typedef void* VkFramebuffer;
typedef void* VkSurfaceKHR;
typedef void* VkSwapchainKHR;
typedef void* VkSampler;
typedef void* VkDescriptorPool;
typedef void* VkDescriptorSet;
typedef void* VkDescriptorSetLayout;
typedef void* VkPipelineLayout;
typedef void* VkPipeline;
typedef void* VkShaderModule;
typedef void* VkDeviceMemory;
typedef void* VkEvent;
typedef void* VkQueryPool;
typedef void* VkBufferView;
typedef int VkResult;
typedef int VkFormat;
typedef int VkImageLayout;
typedef int VkImageUsageFlags;
typedef int VkSampleCountFlagBits;
typedef int VkSharingMode;
typedef int VkImageTiling;
typedef int VkColorSpaceKHR;
typedef int VkPresentModeKHR;
typedef unsigned int VkBool32;
typedef unsigned int VkFlags;
typedef unsigned long long VkDeviceSize;
typedef unsigned int VkStructureType;

enum {
    VK_IMAGE_LAYOUT_UNDEFINED = 0,
    VK_NULL_HANDLE = 0,
    VK_SUCCESS = 0,
    VK_FALSE = 0,
    VK_TRUE = 1,
};

struct VkExtent2D { unsigned int width, height; };
struct VkExtent3D { unsigned int width, height, depth; };
struct VkPhysicalDeviceFeatures { VkBool32 robustBufferAccess; };
struct VkPhysicalDeviceFeatures2 { VkStructureType sType; void* pNext; VkPhysicalDeviceFeatures features; };
struct VkPhysicalDeviceProperties { uint32_t apiVersion; };
struct VkPhysicalDeviceMemoryProperties { uint32_t memoryTypeCount; };
struct VkApplicationInfo { VkStructureType sType; };
struct VkInstanceCreateInfo { VkStructureType sType; };
struct VkDeviceCreateInfo { VkStructureType sType; };
struct VkQueueFamilyProperties { uint32_t queueCount; };
struct VkAllocationCallbacks { void* pUserData; };
struct VkCommandPool { void* p; };
struct VkExtensionProperties { char extensionName[256]; uint32_t specVersion; };
struct VkLayerProperties { char layerName[256]; uint32_t specVersion; uint32_t implVersion; char description[256]; };
struct VkImageFormatProperties2 { VkStructureType sType; void* pNext; };
struct VkPhysicalDeviceImageFormatInfo2 { VkStructureType sType; void* pNext; };

typedef int VkPipelineStageFlags;
typedef int VkAccessFlags;
typedef int VkImageAspectFlags;
typedef int VkMemoryHeapFlags;
typedef int VkMemoryPropertyFlags;
typedef int VkSurfaceTransformFlagBitsKHR;
typedef int VkCompositeAlphaFlagBitsKHR;
typedef int VkExternalMemoryHandleTypeFlagBits;
typedef int VkDescriptorType;
typedef int VkShaderStageFlags;

// Function pointer typedefs (PFN_*)
typedef VkResult (VKAPI_PTR *PFN_vkVoidFunction)(void);
typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetInstanceProcAddr)(VkInstance, const char*);
typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetDeviceProcAddr)(VkDevice, const char*);

typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceVersion)(uint32_t*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceExtensionProperties)(const char*, uint32_t*, VkExtensionProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceLayerProperties)(uint32_t*, VkLayerProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkCreateInstance)(const void*, const VkAllocationCallbacks*, VkInstance*);
typedef void     (VKAPI_PTR *PFN_vkDestroyInstance)(VkInstance, const VkAllocationCallbacks*);

typedef VkResult (VKAPI_PTR *PFN_vkEnumeratePhysicalDevices)(VkInstance, uint32_t*, VkPhysicalDevice*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceProperties)(VkPhysicalDevice, VkPhysicalDeviceProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceQueueFamilyProperties)(VkPhysicalDevice, uint32_t*, VkQueueFamilyProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceFeatures2)(VkPhysicalDevice, VkPhysicalDeviceFeatures2*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceImageFormatProperties2)(VkPhysicalDevice, const VkPhysicalDeviceImageFormatInfo2*, VkImageFormatProperties2*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceMemoryProperties)(VkPhysicalDevice, VkPhysicalDeviceMemoryProperties*);
typedef void     (VKAPI_PTR *PFN_vkGetPhysicalDeviceMemoryProperties2)(VkPhysicalDevice, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceFormatProperties)(VkPhysicalDevice, VkFormat, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceFormatProperties2)(VkPhysicalDevice, VkFormat, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceCapabilitiesKHR)(VkPhysicalDevice, VkSurfaceKHR, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceFormatsKHR)(VkPhysicalDevice, VkSurfaceKHR, uint32_t*, void*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfacePresentModesKHR)(VkPhysicalDevice, VkSurfaceKHR, uint32_t*, VkPresentModeKHR*);
typedef VkResult (VKAPI_PTR *PFN_vkGetPhysicalDeviceSurfaceSupportKHR)(VkPhysicalDevice, uint32_t, VkSurfaceKHR, VkBool32*);

typedef VkResult (VKAPI_PTR *PFN_vkCreateDevice)(VkPhysicalDevice, const void*, const VkAllocationCallbacks*, VkDevice*);
typedef void     (VKAPI_PTR *PFN_vkDestroyDevice)(VkDevice, const VkAllocationCallbacks*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateDeviceExtensionProperties)(VkPhysicalDevice, const char*, uint32_t*, VkExtensionProperties*);
typedef VkResult (VKAPI_PTR *PFN_vkEnumerateDeviceLayerProperties)(VkPhysicalDevice, uint32_t*, VkLayerProperties*);

typedef void     (VKAPI_PTR *PFN_vkGetDeviceQueue)(VkDevice, uint32_t, uint32_t, VkQueue*);
typedef VkResult (VKAPI_PTR *PFN_vkDeviceWaitIdle)(VkDevice);
typedef VkResult (VKAPI_PTR *PFN_vkQueueWaitIdle)(VkQueue);
typedef VkResult (VKAPI_PTR *PFN_vkQueueSubmit)(VkQueue, uint32_t, const void*, VkFence);

// Catch-all for any other unused PFN — typedef as opaque function pointer
typedef PFN_vkVoidFunction PFN_vkAllocateMemory;
typedef PFN_vkVoidFunction PFN_vkFreeMemory;
typedef PFN_vkVoidFunction PFN_vkMapMemory;
typedef PFN_vkVoidFunction PFN_vkUnmapMemory;
typedef PFN_vkVoidFunction PFN_vkBindBufferMemory;
typedef PFN_vkVoidFunction PFN_vkBindImageMemory;
typedef PFN_vkVoidFunction PFN_vkCreateImage;
typedef PFN_vkVoidFunction PFN_vkDestroyImage;
typedef PFN_vkVoidFunction PFN_vkCreateBuffer;
typedef PFN_vkVoidFunction PFN_vkDestroyBuffer;
typedef PFN_vkVoidFunction PFN_vkCreateImageView;
typedef PFN_vkVoidFunction PFN_vkDestroyImageView;
typedef PFN_vkVoidFunction PFN_vkCreateBufferView;
typedef PFN_vkVoidFunction PFN_vkDestroyBufferView;
typedef PFN_vkVoidFunction PFN_vkCreateFramebuffer;
typedef PFN_vkVoidFunction PFN_vkDestroyFramebuffer;
typedef PFN_vkVoidFunction PFN_vkCreateRenderPass;
typedef PFN_vkVoidFunction PFN_vkDestroyRenderPass;
typedef PFN_vkVoidFunction PFN_vkCreateCommandPool;
typedef PFN_vkVoidFunction PFN_vkDestroyCommandPool;
typedef PFN_vkVoidFunction PFN_vkAllocateCommandBuffers;
typedef PFN_vkVoidFunction PFN_vkFreeCommandBuffers;
typedef PFN_vkVoidFunction PFN_vkResetCommandPool;
typedef PFN_vkVoidFunction PFN_vkBeginCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkEndCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkResetCommandBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdPipelineBarrier;
typedef PFN_vkVoidFunction PFN_vkCmdCopyBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdCopyImage;
typedef PFN_vkVoidFunction PFN_vkCmdCopyBufferToImage;
typedef PFN_vkVoidFunction PFN_vkCmdCopyImageToBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdBeginRenderPass;
typedef PFN_vkVoidFunction PFN_vkCmdEndRenderPass;
typedef PFN_vkVoidFunction PFN_vkCmdNextSubpass;
typedef PFN_vkVoidFunction PFN_vkCmdBindPipeline;
typedef PFN_vkVoidFunction PFN_vkCmdBindDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkCmdBindVertexBuffers;
typedef PFN_vkVoidFunction PFN_vkCmdBindIndexBuffer;
typedef PFN_vkVoidFunction PFN_vkCmdDraw;
typedef PFN_vkVoidFunction PFN_vkCmdDrawIndexed;
typedef PFN_vkVoidFunction PFN_vkCmdSetViewport;
typedef PFN_vkVoidFunction PFN_vkCmdSetScissor;
typedef PFN_vkVoidFunction PFN_vkCmdClearColorImage;
typedef PFN_vkVoidFunction PFN_vkCmdClearDepthStencilImage;
typedef PFN_vkVoidFunction PFN_vkCmdClearAttachments;
typedef PFN_vkVoidFunction PFN_vkCmdResolveImage;
typedef PFN_vkVoidFunction PFN_vkCreateSemaphore;
typedef PFN_vkVoidFunction PFN_vkDestroySemaphore;
typedef PFN_vkVoidFunction PFN_vkCreateFence;
typedef PFN_vkVoidFunction PFN_vkDestroyFence;
typedef PFN_vkVoidFunction PFN_vkResetFences;
typedef PFN_vkVoidFunction PFN_vkGetFenceStatus;
typedef PFN_vkVoidFunction PFN_vkWaitForFences;
typedef PFN_vkVoidFunction PFN_vkCreateSampler;
typedef PFN_vkVoidFunction PFN_vkDestroySampler;
typedef PFN_vkVoidFunction PFN_vkCreateDescriptorPool;
typedef PFN_vkVoidFunction PFN_vkDestroyDescriptorPool;
typedef PFN_vkVoidFunction PFN_vkAllocateDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkFreeDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkUpdateDescriptorSets;
typedef PFN_vkVoidFunction PFN_vkCreateDescriptorSetLayout;
typedef PFN_vkVoidFunction PFN_vkDestroyDescriptorSetLayout;
typedef PFN_vkVoidFunction PFN_vkCreatePipelineLayout;
typedef PFN_vkVoidFunction PFN_vkDestroyPipelineLayout;
typedef PFN_vkVoidFunction PFN_vkCreateGraphicsPipelines;
typedef PFN_vkVoidFunction PFN_vkCreateComputePipelines;
typedef PFN_vkVoidFunction PFN_vkDestroyPipeline;
typedef PFN_vkVoidFunction PFN_vkCreateShaderModule;
typedef PFN_vkVoidFunction PFN_vkDestroyShaderModule;
typedef PFN_vkVoidFunction PFN_vkGetBufferMemoryRequirements;
typedef PFN_vkVoidFunction PFN_vkGetImageMemoryRequirements;
typedef PFN_vkVoidFunction PFN_vkGetImageMemoryRequirements2;
typedef PFN_vkVoidFunction PFN_vkGetBufferMemoryRequirements2;
typedef PFN_vkVoidFunction PFN_vkInvalidateMappedMemoryRanges;
typedef PFN_vkVoidFunction PFN_vkFlushMappedMemoryRanges;
typedef PFN_vkVoidFunction PFN_vkBindImageMemory2;
typedef PFN_vkVoidFunction PFN_vkBindBufferMemory2;
''')
print('vulkan/vulkan.h: full PFN_* typedef set added')

# ============================================================================
# 4. SkCanvas::ColorBehavior shim — inject via hwui_force_include.h
# ============================================================================
with open(f'{COMPAT}/hwui_force_include.h') as f:
    fi_content = f.read()
if 'SkCanvasColorBehaviorShim' not in fi_content:
    fi_content += '''

// Round 12: SkCanvas::ColorBehavior was removed in Skia M133, but
// android::ImageDecoder.cpp references it. Provide a stub via macro.
// (Cannot patch SkCanvas itself — it's in OH Skia headers.)
namespace SkCanvasColorBehaviorShim {
    enum Behavior { kRespect = 0, kIgnore = 1 };
}
#ifndef SkCanvas_ColorBehavior_DEFINED
#define SkCanvas_ColorBehavior_DEFINED
// Use a non-conflicting name; AOSP code that does SkCanvas::ColorBehavior::kIgnore
// must be patched in source via round12 patch_image_decoder() below.
#endif
'''
    with open(f'{COMPAT}/hwui_force_include.h', 'w') as f:
        f.write(fi_content)
print('hwui_force_include.h: ColorBehavior shim added')

# ============================================================================
# 5. Source patches (cumulative — these complement existing rounds)
# ============================================================================

# 5a. Readback.cpp - already needs the vulkan PFN typedefs (now provided)
#     plus our existing round 5 patches. Just re-apply via the .orig restore.
def patch_readback(c):
    # Re-apply round 5 ARect stub
    if 'ARect_stub' not in c:
        c = c.replace('#include "Readback.h"',
            '#include "Readback.h"\ntypedef struct ARect_stub { int32_t left, top, right, bottom; } ARect;')
    c = re.sub(r'SkSurface::MakeRenderTarget\(', 'SkSurfaces::RenderTarget(', c)
    return c
patch(f'{HWUI}/Readback.cpp', patch_readback)

# 5b. RecordingCanvas.cpp - cumulative fix:
#     - SkMesh API moves
#     - SkCanvas::flush removal
#     - SkAndroidFrameworkUtils references (now valid via aliased class)
#     - DisplayListOps.in enum issue
def patch_recording_canvas(c):
    # SkMesh API moves
    c = re.sub(r'SkMesh::CopyVertexBuffer\(', 'SkMeshes::CopyVertexBuffer(', c)
    c = re.sub(r'SkMesh::CopyIndexBuffer\(',  'SkMeshes::CopyIndexBuffer(',  c)
    # SkMesh::Make signature change — stub
    c = re.sub(r'gpuMesh = SkMesh::Make\([^;]+\);',
               'gpuMesh = SkMesh{}; /* M133 */', c)
    # SkCanvas::flush removed
    c = re.sub(r'(\w+)->flush\(\)\s*;', r'/* M133 */ (void)\1;', c)
    # SkSurface::MakeRenderTarget
    c = re.sub(r'SkSurface::MakeRenderTarget\(', 'SkSurfaces::RenderTarget(', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_recording_canvas)

# 5c. hwui/Canvas.cpp - RecordingCanvas is abstract because of pure virtual
#     methods. The fix is to use SkiaRecordingCanvas (a concrete derived class)
#     which Canvas.cpp already uses. The error suggests an inheritance chain
#     issue. Most likely Canvas::create_canvas is being upcast incorrectly.
#     Look at line 34: try a different cast.
def patch_canvas(c):
    # Find line 34 and inject explicit cast if needed.
    # Pattern: `return new uirenderer::skiapipeline::SkiaRecordingCanvas(...)`
    c = re.sub(
        r'return new ::?uirenderer::skiapipeline::SkiaRecordingCanvas',
        'return reinterpret_cast<Canvas*>(new ::uirenderer::skiapipeline::SkiaRecordingCanvas',
        c)
    # Close the cast (count opening paren and add a closing paren)
    # Simpler: just use static_cast
    return c
# Actually for hwui/Canvas.cpp we'll try a more targeted approach below

# 5d. hwui/ImageDecoder.cpp - SkCanvas::ColorBehavior removed
def patch_image_decoder(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    return c
patch(f'{HWUI}/hwui/ImageDecoder.cpp', patch_image_decoder)

# 5e. hwui/Canvas.cpp - the abstract class issue is in SkiaRecordingCanvas.h
#     which inherits from RecordingCanvas. Let's inspect what's pure-virtual.
#     For now, try a static_cast and see.
def patch_hwui_canvas(c):
    # The error: cannot initialize return object of type 'android::Canvas *'
    # with rvalue 'uirenderer::skiapipeline::SkiaRecordingCanvas *'
    # Cause: SkiaRecordingCanvas is abstract so the return is rejected.
    # Without making it concrete, return nullptr explicitly cast.
    # But this would break Hello World...
    # Better: identify pure virtual and stub them.
    # For now use a reinterpret_cast (compiler will accept but RTTI broken)
    return c  # placeholder — will need a separate header patch
patch(f'{HWUI}/hwui/Canvas.cpp', patch_hwui_canvas)

# ============================================================================
# 6. SkiaRecordingCanvas abstract issue — needs investigation
#    Likely RecordingCanvas (in libhwui) declares pure virtual methods that
#    SkiaRecordingCanvas doesn't override. We need to find them.
# ============================================================================
# This will be diagnosed in a follow-up step.

print('\nRound 12 patches applied')
