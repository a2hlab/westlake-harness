#!/usr/bin/env python3
"""Round 6: comprehensive header shims + minor patches for libhwui Phase 2/3."""
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

# ============ Skia header redirect shims ============

def shim(name, target):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(f'#pragma once\n#include "{target}"\n')

# Skia header redirects (M116 flat → M133 layout)
shim('SkRuntimeEffect.h',     'effects/SkRuntimeEffect.h')
shim('SkNoDrawCanvas.h',      'utils/SkNoDrawCanvas.h')
shim('SkPaintFilterCanvas.h', 'utils/SkPaintFilterCanvas.h')
shim('SkAnimatedImage.h',     'android/SkAnimatedImage.h')
shim('SkAndroidCodec.h',      'codec/SkAndroidCodec.h')
print('Skia redirect shims created')

# ============ Stub headers for missing Android/NDK headers ============

# androidfw/ResourceTypes.h (libandroidfw is large; we only need basic types for hwui)
os.makedirs(f'{COMPAT}/androidfw', exist_ok=True)
with open(f'{COMPAT}/androidfw/ResourceTypes.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
#include <string>
#include <vector>
namespace android {
struct Res_value {
    uint8_t size; uint8_t res0; uint16_t dataType;
    union { uint32_t data; float fdata; };
    enum {
        TYPE_NULL = 0x00, TYPE_REFERENCE = 0x01, TYPE_INT_DEC = 0x10,
        TYPE_FLOAT = 0x04, TYPE_DIMENSION = 0x05, TYPE_STRING = 0x03,
    };
};
struct ResStringPool_header { uint32_t header; };
class ResStringPool { public: const char16_t* stringAt(size_t, size_t*) const { return nullptr; } };
class ResTable { public: int getError() const { return 0; } };
}
''')
print('androidfw/ResourceTypes.h stub created')

# private/android/choreographer.h
os.makedirs(f'{COMPAT}/private/android', exist_ok=True)
with open(f'{COMPAT}/private/android/choreographer.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
typedef struct AChoreographer AChoreographer;
typedef struct AChoreographerFrameCallbackData AChoreographerFrameCallbackData;
extern "C" {
typedef void (*AChoreographer_vsyncCallback)(const AChoreographerFrameCallbackData*, void*);
void AChoreographer_postVsyncCallback(AChoreographer*, AChoreographer_vsyncCallback, void*);
int64_t AChoreographer_getFrameInterval(const AChoreographer*);
int64_t AChoreographerFrameCallbackData_getFrameTimeNanos(const AChoreographerFrameCallbackData*);
size_t AChoreographerFrameCallbackData_getFrameTimelinesLength(const AChoreographerFrameCallbackData*);
size_t AChoreographerFrameCallbackData_getPreferredFrameTimelineIndex(const AChoreographerFrameCallbackData*);
int64_t AChoreographerFrameCallbackData_getFrameTimelineDeadlineNanos(const AChoreographerFrameCallbackData*, size_t);
int64_t AChoreographerFrameCallbackData_getFrameTimelineExpectedPresentationTimeNanos(const AChoreographerFrameCallbackData*, size_t);
int64_t AChoreographerFrameCallbackData_getFrameTimelineVsyncId(const AChoreographerFrameCallbackData*, size_t);
}
''')
print('private/android/choreographer.h stub created')

# vulkan/vulkan.h - HWUI_NO_VULKAN should mean we don't need it. Provide a degenerate stub.
os.makedirs(f'{COMPAT}/vulkan', exist_ok=True)
with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f:
    f.write('''#pragma once
// Stub: HWUI_NO_VULKAN=1 should disable Vulkan paths.
typedef void* VkInstance;
typedef void* VkDevice;
typedef void* VkPhysicalDevice;
typedef int VkResult;
typedef int VkFormat;
enum { VK_IMAGE_LAYOUT_UNDEFINED = 0 };
''')
print('vulkan/vulkan.h stub created')

# media/NdkImageReader.h
with open(f'{COMPAT}/media/NdkImageReader.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
typedef struct AImageReader AImageReader;
typedef int media_status_t;
''')
print('media/NdkImageReader.h stub created')

# ui/ColorSpace.h
os.makedirs(f'{COMPAT}/ui', exist_ok=True)
with open(f'{COMPAT}/ui/ColorSpace.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
namespace android { class ColorSpace { public: enum class Named : uint8_t { Srgb = 0 }; }; }
''')
print('ui/ColorSpace.h stub created')

# android/api-level.h
os.makedirs(f'{COMPAT}/android', exist_ok=True)
with open(f'{COMPAT}/android/api-level.h', 'w') as f:
    f.write('''#pragma once
#define __ANDROID_API__ 34
static inline int android_get_device_api_level(void) { return 34; }
''')
print('android/api-level.h stub created')

# ============ Update existing stubs ============

# minikin/MinikinFont.h - add localeListId and EmbeddedBitmaps_Shift
with open(f'{COMPAT}/minikin/MinikinFont.h') as f:
    content = f.read()
if 'localeListId' not in content:
    content = content.replace('uint32_t fontFlags = 0;',
        'uint32_t fontFlags = 0;\n    uint32_t localeListId = 0;')
if 'EmbeddedBitmaps_Shift' not in content:
    content = content.replace('constexpr int Subpixel_Shift = 2;',
        'constexpr int Subpixel_Shift = 2;\nconstexpr int EmbeddedBitmaps_Shift = 3;\nconstexpr int ForceAutoHinting_Shift = 4;')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f:
    f.write(content)
print('MinikinFont.h extended')

# FileBlobCache.h - add kDidClean
with open(f'{COMPAT}/FileBlobCache.h') as f:
    content = f.read()
if 'kDidClean' not in content:
    content = content.replace(
        'enum class InsertResult { kInserted = 0, kKeyTooLarge = 1, kValueTooLarge = 2 };',
        'enum class InsertResult { kInserted = 0, kKeyTooLarge = 1, kValueTooLarge = 2, kDidClean = 3, kNotEnoughSpace = 4 };')
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f:
    f.write(content)
print('FileBlobCache.h extended')

# ============ Source patches ============

# Stub SkAndroidFrameworkTraceUtil reference (tests path)
def patch_canvas(c):
    c = re.sub(r'SkAndroidFrameworkTraceUtil::\w+\(\s*[^)]*\)', '/* M133: trace util stub */ (void)0', c)
    return c

# Patch hwui/Canvas.cpp
canvas_cpp = f'{HWUI}/hwui/Canvas.cpp'
if os.path.exists(canvas_cpp):
    patch(canvas_cpp, patch_canvas)

# dprintf typo fix (some hwui file calls dprintf which doesn't exist on musl)
def fix_dprintf(c):
    return c.replace('dprintf(', 'fprintf(stdout, ')
# Check files that might have it
for f in ['Properties.cpp', 'utils/StringUtils.cpp']:
    p = f'{HWUI}/{f}'
    if os.path.exists(p):
        with open(p) as fh: content = fh.read()
        if 'dprintf(' in content and 'fprintf(stdout,' not in content:
            patch(p, fix_dprintf)

# __c11_atomic_thread_fence - C++17 doesn't have it via std::; provide via macro
# Inject force-include patch into compile
print('\nRound 6 patches applied')
