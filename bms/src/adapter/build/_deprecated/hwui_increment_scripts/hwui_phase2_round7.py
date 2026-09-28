#!/usr/bin/env python3
"""Round 7: more shims (SkEncodedImageFormat, Vk types) + atomic_thread_fence fix."""
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

# ============ Skia header redirect shims ============
shim('SkEncodedImageFormat.h', 'codec/SkEncodedImageFormat.h')
shim('SkGradientShader.h',     'effects/SkGradientShader.h')
shim('SkCodec.h',              'codec/SkCodec.h')
shim('SkCamera.h',             'utils/SkCamera.h')
print('More Skia shims created')

# ============ Vulkan stub upgrade ============
with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f:
    f.write('''#pragma once
// Stub: HWUI_NO_VULKAN should disable Vulkan paths but some headers still reference types.
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
typedef unsigned int uint32_t_vk;
enum {
    VK_IMAGE_LAYOUT_UNDEFINED = 0,
    VK_NULL_HANDLE = 0,
    VK_SUCCESS = 0,
};
struct VkExtent2D { unsigned int width, height; };
struct VkExtent3D { unsigned int width, height, depth; };
''')
print('vulkan/vulkan.h upgraded')

# ============ Force-include header for atomic_thread_fence and other globals ============
with open(f'{COMPAT}/hwui_force_include.h', 'w') as f:
    f.write('''#pragma once
// libhwui-wide compatibility shim — force-included via -include
#include <atomic>

// __c11_atomic_thread_fence is a clang builtin, but utils/LightRefBase.h
// references it via std::__c11_atomic_thread_fence (incorrect on libcxx-ohos).
// Provide an alias.
namespace std {
    inline void __c11_atomic_thread_fence(int order) { __atomic_thread_fence(order); }
}

// dprintf is in POSIX, libcxx-ohos may not expose it via <cstdio>.
#include <cstdio>
#include <unistd.h>
#ifndef dprintf
extern "C" int dprintf(int fd, const char* fmt, ...);
#endif

// Skia trace util used by Properties.cpp - provide an empty namespace
namespace SkAndroidFrameworkTraceUtil_ns {
    inline void setEnableTracing(bool) {}
    inline void setUsePerfettoTrackEvents(bool) {}
    inline bool getEnableTracing() { return false; }
}
#define SkAndroidFrameworkTraceUtil SkAndroidFrameworkTraceUtil_ns
''')
print('hwui_force_include.h created')

# ============ Update existing stubs ============

# minikin/MinikinFont.h - add familyVariant, Embolden_Flag etc.
with open(f'{COMPAT}/minikin/MinikinFont.h') as f:
    content = f.read()
if 'familyVariant' not in content:
    content = content.replace('uint32_t localeListId = 0;',
        'uint32_t localeListId = 0;\n    int familyVariant = 0;')
if 'Embolden_Flag' not in content:
    content = content.replace('constexpr int EmbeddedBitmaps_Shift = 3;',
        '''constexpr int EmbeddedBitmaps_Shift = 3;
constexpr uint32_t Embolden_Flag = 1u << 0;
constexpr uint32_t LinearMetrics_Flag = 1u << 1;
constexpr uint32_t Subpixel_Flag = 1u << 2;
constexpr uint32_t EmbeddedBitmaps_Flag = 1u << 3;
constexpr uint32_t ForceAutoHinting_Flag = 1u << 4;''')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f:
    f.write(content)
print('MinikinFont.h further extended')

# FileBlobCache.h - add kInvalidValueSize
with open(f'{COMPAT}/FileBlobCache.h') as f:
    content = f.read()
if 'kInvalidValueSize' not in content:
    content = content.replace(
        'kNotEnoughSpace = 4',
        'kNotEnoughSpace = 4, kInvalidValueSize = 5')
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write(content)
print('FileBlobCache.h extended')

# androidfw/ResourceTypes.h - add Res_png_9patch
with open(f'{COMPAT}/androidfw/ResourceTypes.h') as f:
    content = f.read()
if 'Res_png_9patch' not in content:
    content = content.replace('class ResTable',
        '''struct Res_png_9patch {
    int8_t wasDeserialized = 0;
    uint8_t numXDivs = 0;
    uint8_t numYDivs = 0;
    uint8_t numColors = 0;
    int32_t* xDivs = nullptr;
    int32_t* yDivs = nullptr;
    int32_t paddingLeft = 0, paddingRight = 0, paddingTop = 0, paddingBottom = 0;
    uint32_t* colors = nullptr;
    static Res_png_9patch* deserialize(void*) { return nullptr; }
    void* serialize() const { return nullptr; }
    size_t serializedSize() const { return 0; }
};
class ResTable''')
with open(f'{COMPAT}/androidfw/ResourceTypes.h', 'w') as f:
    f.write(content)
print('androidfw/ResourceTypes.h extended')

# SkMSec typedef + float3 stub - add to skia_m133_compat.h (force-included)
compat_h = f'{COMPAT}/skia_m133_compat.h'
if os.path.exists(compat_h):
    with open(compat_h) as f: content = f.read()
else:
    content = '#pragma once\n'
if 'typedef uint32_t SkMSec' not in content:
    content += '\n#include <cstdint>\ntypedef uint32_t SkMSec;\n'
if 'typedef float float3' not in content:
    content += '\nstruct float3 { float x, y, z; };\n'
with open(compat_h, 'w') as f:
    f.write(content)
print('skia_m133_compat.h extended')

print('\nRound 7 patches applied')
