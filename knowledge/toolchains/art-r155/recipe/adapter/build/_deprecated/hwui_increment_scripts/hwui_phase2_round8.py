#!/usr/bin/env python3
"""Round 8: vulkan types, more shims, force-include update."""
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

def shim(name, target):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(f'#pragma once\n#include "{target}"\n')

# Skia shims
shim('SkPngChunkReader.h',     'codec/SkPngChunkReader.h')
shim('SkPathOps.h',            'pathops/SkPathOps.h')
shim('SkHighContrastFilter.h', 'effects/SkHighContrastFilter.h')

# Vulkan stub - add VkPhysicalDeviceFeatures2 + everything libhwui touches
with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f:
    f.write('''#pragma once
// Stub: HWUI_NO_VULKAN should disable Vulkan paths but headers still reference types.
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
typedef unsigned int VkDeviceSize;
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
typedef int VkPipelineLayoutCreateFlags;
typedef int VkPipelineCreateFlags;
typedef int VkBlendFactor;
typedef int VkBlendOp;
typedef int VkLogicOp;
typedef int VkPrimitiveTopology;
typedef int VkPolygonMode;
typedef int VkCullModeFlags;
typedef int VkFrontFace;
typedef int VkCompareOp;
typedef int VkStencilOp;
typedef int VkAttachmentLoadOp;
typedef int VkAttachmentStoreOp;
typedef int VkSubpassContents;
typedef int VkPipelineBindPoint;
typedef int VkBufferUsageFlags;
typedef int VkSamplerAddressMode;
typedef int VkFilter;
typedef int VkSamplerMipmapMode;
typedef int VkBorderColor;
typedef int VkMemoryAllocateInfo;
''')
print('vulkan/vulkan.h upgraded')

# Stub vk/GrVkBackendContext.h via direct write (the redirect target doesn't exist)
os.makedirs(f'{COMPAT}/vk', exist_ok=True)
with open(f'{COMPAT}/vk/GrVkBackendContext.h', 'w') as f:
    f.write('#pragma once\n// Stub: HWUI Vulkan disabled\nstruct GrVkBackendContext {};\n')
with open(f'{COMPAT}/vk/GrVkTypes.h', 'w') as f:
    f.write('#pragma once\nstruct GrVkImageInfo {};\nstruct GrVkAlloc {};\nstruct GrVkYcbcrConversionInfo {};\n')
print('vk/* stubs created')

# Update force-include header
with open(f'{COMPAT}/hwui_force_include.h', 'w') as f:
    f.write('''#pragma once
// libhwui-wide compatibility shim — force-included via -include
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <unistd.h>

// __c11_atomic_thread_fence is a clang builtin, but utils/LightRefBase.h
// references it via std::__c11_atomic_thread_fence which doesn't exist in libcxx-ohos.
namespace std {
    inline void __c11_atomic_thread_fence(int order) { __atomic_thread_fence(order); }
}

// dprintf alias
#ifndef dprintf
extern "C" int dprintf(int fd, const char* fmt, ...);
#endif

// Skia trace util used by Properties.cpp
namespace SkAndroidFrameworkTraceUtil {
    inline void setEnableTracing(bool) {}
    inline void setUsePerfettoTrackEvents(bool) {}
    inline bool getEnableTracing() { return false; }
}

// SkMSec / float3 typedefs
typedef uint32_t SkMSec;
struct float3 { float x, y, z; };

// LOG_ALWAYS_FATAL fallback (may be needed before liblog is included)
#ifndef LOG_ALWAYS_FATAL
#define LOG_ALWAYS_FATAL(...) do { fprintf(stderr, __VA_ARGS__); abort(); } while(0)
#endif
''')
print('hwui_force_include.h updated')

# minikin/MinikinFont.h - FamilyVariant enum, Embolden_Flag fix
with open(f'{COMPAT}/minikin/MinikinFont.h') as f:
    content = f.read()
if 'enum class FamilyVariant' not in content:
    content = content.replace('class FontCollection;  // forward',
        '''class FontCollection;  // forward
enum class FamilyVariant : int { DEFAULT = 0, COMPACT = 1, ELEGANT = 2 };''')
    content = content.replace('int familyVariant = 0;',
        'FamilyVariant familyVariant = FamilyVariant::DEFAULT;')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f:
    f.write(content)
print('MinikinFont.h FamilyVariant added')

# FileBlobCache - add kInvalidKeySize
with open(f'{COMPAT}/FileBlobCache.h') as f:
    content = f.read()
if 'kInvalidKeySize' not in content:
    content = content.replace('kInvalidValueSize = 5',
        'kInvalidValueSize = 5, kInvalidKeySize = 6')
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write(content)
print('FileBlobCache.h extended')

print('\nRound 8 patches applied')
