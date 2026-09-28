#!/usr/bin/env python3
"""Round 11: convert stub headers to redirects (use real M133 headers when they exist)."""
import os, shutil

COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'
SKIA_OH = '/home/HanBingChen/oh/third_party/skia/m133'

def shim(name, target):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(f'#pragma once\n#include "{target}"\n')

# Convert stubs to redirects (real M133 headers do exist - we just need to find them)
shim('SkShadowUtils.h',         'utils/SkShadowUtils.h')
shim('SkEncodedOrigin.h',       'codec/SkEncodedOrigin.h')
shim('SkCanvasStateUtils.h',    'utils/SkCanvasStateUtils.h')
shim('SkOverdrawColorFilter.h', 'effects/SkOverdrawColorFilter.h')
shim('SkCodecAnimation.h',      'codec/SkCodecAnimation.h')
shim('SkWebpEncoder.h',         'encode/SkWebpEncoder.h')
shim('SkAndroidFrameworkUtils.h','android/SkAndroidFrameworkUtils.h')
print('Converted stubs to redirects')

# Update vulkan.h - add PFN_vkEnumerateInstanceVersion typedef
with open(f'{COMPAT}/vulkan/vulkan.h') as f: c = f.read()
if 'PFN_vkEnumerateInstanceVersion' not in c:
    c += '\ntypedef VkResult (VKAPI_PTR *PFN_vkEnumerateInstanceVersion)(uint32_t* pApiVersion);\n'
    c += 'typedef VkResult (VKAPI_PTR *PFN_vkVoidFunction)(void);\n'
    c += 'typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetInstanceProcAddr)(VkInstance instance, const char* pName);\n'
    c += 'typedef PFN_vkVoidFunction (VKAPI_PTR *PFN_vkGetDeviceProcAddr)(VkDevice device, const char* pName);\n'
    with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f: f.write(c)
print('vulkan.h: PFN typedefs added')

# minikin: add U16StringPiece
with open(f'{COMPAT}/minikin/MinikinFont.h') as f: c = f.read()
if 'U16StringPiece' not in c:
    c = c.replace('class MeasuredText {};',
        '''class MeasuredText {};

class U16StringPiece {
    const uint16_t* mData = nullptr;
    size_t mLength = 0;
public:
    U16StringPiece() = default;
    U16StringPiece(const uint16_t* d, size_t l) : mData(d), mLength(l) {}
    const uint16_t* data() const { return mData; }
    size_t size() const { return mLength; }
    size_t length() const { return mLength; }
};''')
    with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f: f.write(c)
print('MinikinFont.h: U16StringPiece added')

# SkAndroidFrameworkUtils — the redirect points to OH header which doesn't have ResetClip/ShaderAsALinearGradient
# Need to add those to the redirect target via a wrapper
# Actually: write the wrapper header that includes OH's then adds extras
with open(f'{COMPAT}/SkAndroidFrameworkUtils.h', 'w') as f:
    f.write('''#pragma once
#include "android/SkAndroidFrameworkUtils.h"
#include <cstdint>
class SkCanvas;
// Extension: add adapter helpers that AOSP expects but OH doesn't have
#ifndef ADAPTER_SK_ANDROID_EXT
#define ADAPTER_SK_ANDROID_EXT
namespace adapter_sk_ext {
    inline void ResetClip(SkCanvas*) {}
}
#define ResetClip adapter_sk_ext::ResetClip
#endif
''')
print('SkAndroidFrameworkUtils.h: wrapper with extensions')

print('\nRound 11 patches applied')
