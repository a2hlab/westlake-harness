#!/usr/bin/env python3
"""Round 9: cleanup duplicate enums, fix vk shim path, finish header shims."""
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

# Direct stub headers (instead of redirects since these don't exist in OH skia)
def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

# 1. Remove duplicate FamilyVariant from MinikinFont.h (use existing FamilyVariant.h)
with open(f'{COMPAT}/minikin/MinikinFont.h') as f: c = f.read()
c = re.sub(r'enum class FamilyVariant : uint8_t \{ DEFAULT = 0, COMPACT = 1, ELEGANT = 2 \};\n', '', c)
# Forward-include FamilyVariant.h instead
if '#include "FamilyVariant.h"' not in c:
    c = c.replace('namespace minikin {', '#include "FamilyVariant.h"\nnamespace minikin {')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f: f.write(c)
print('MinikinFont.h: dedup FamilyVariant')

# 2. vk/GrVkBackendContext.h - rewrite as direct stub (no redirect)
with open(f'{COMPAT}/vk/GrVkBackendContext.h', 'w') as f:
    f.write('#pragma once\n// Stub: HWUI Vulkan disabled\nstruct GrVkBackendContext {};\n')
print('vk/GrVkBackendContext.h rewritten as stub')

# 3. Update SkAndroidFrameworkUtils.h - add the actual class with SaveBehind
with open(f'{COMPAT}/SkAndroidFrameworkUtils.h', 'w') as f:
    f.write('''#pragma once
class SkCanvas;
class SkRect;
class SkAndroidFrameworkTraceUtil {
public:
    static void setEnableTracing(bool) {}
    static void setUsePerfettoTrackEvents(bool) {}
    static bool getEnableTracing() { return false; }
};
class SkAndroidFrameworkUtils {
public:
    static int SaveBehind(SkCanvas*, const SkRect*) { return 0; }
    static bool ShouldCollapseSrcOver(const void*, int) { return false; }
};
''')
print('SkAndroidFrameworkUtils.h rewritten')

# 4. More direct stubs for missing Skia headers
stub('SkWebpEncoder.h',        'namespace SkWebpEncoder { struct Options {}; }\n')
stub('SkShadowUtils.h',        'class SkPath; class SkPaint; class SkCanvas; namespace SkShadowUtils { inline void DrawShadow(SkCanvas*, const SkPath&, const void*, const void*, const void*, unsigned, unsigned, float, unsigned) {} }\n')
stub('SkOverdrawColorFilter.h','class SkColorFilter; namespace SkOverdrawColorFilter { inline void* MakeWithSkColors(const unsigned*) { return nullptr; } }\n')
stub('SkCodecAnimation.h',     'namespace SkCodecAnimation { enum class Blend { kSrc, kSrcOver }; enum class DisposalMethod { kKeep, kRestoreBGColor, kRestorePrevious }; }\n')
print('More Skia stubs created')

# 5. ANativeWindow_setBuffersDataSpace stub - add to NDK shim
nw_h = f'{COMPAT}/android/native_window.h'
if os.path.exists(nw_h):
    with open(nw_h) as f: nw = f.read()
    if 'setBuffersDataSpace' not in nw:
        nw = nw.replace('NATIVE_WINDOW_FORMAT = 4,',
            '''NATIVE_WINDOW_FORMAT = 4,
};
extern "C" int ANativeWindow_setBuffersDataSpace(ANativeWindow* window, int dataSpace);
extern "C" int ANativeWindow_getBuffersDataSpace(ANativeWindow* window);
enum {''')
    with open(nw_h, 'w') as f: f.write(nw)
print('android/native_window.h extended')

# 6. mat3 typedef - add to force-include header
with open(f'{COMPAT}/hwui_force_include.h') as f: c = f.read()
if 'struct mat3' not in c:
    c = c.replace('struct float3 { float x, y, z; };',
                  'struct float3 { float x, y, z; };\nstruct mat3 { float m[9]; };')
with open(f'{COMPAT}/hwui_force_include.h', 'w') as f: f.write(c)
print('hwui_force_include.h: mat3 added')

# 7. GrGLFramebufferInfo - add to GL types header
gl_h = f'{COMPAT}/gl/GrGLTypes.h'
if os.path.exists(gl_h):
    with open(gl_h) as f: gl = f.read()
    if 'GrGLFramebufferInfo' not in gl:
        # Append struct definition
        gl += '\n#ifndef GR_GL_FRAMEBUFFER_INFO_DEFINED\n#define GR_GL_FRAMEBUFFER_INFO_DEFINED\nstruct GrGLFramebufferInfo { unsigned fFBOID; unsigned fFormat; };\n#endif\n'
        with open(gl_h, 'w') as f: f.write(gl)
print('gl/GrGLTypes.h extended')

# 8. BlobCache::InsertResult::kKeyTooBig
with open(f'{COMPAT}/FileBlobCache.h') as f: c = f.read()
if 'kKeyTooBig' not in c:
    c = c.replace('kInvalidKeySize = 6',
                  'kInvalidKeySize = 6, kKeyTooBig = 7, kValueTooBig = 8')
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f: f.write(c)
print('FileBlobCache.h extended')

# 9. Fix HardwareBitmapUploader - the regex from round 5 left a stray ');'
def patch_hbu(c):
    # The redefinitions removed - let me re-do cleanly
    # If we still have a stray ');', remove it
    c = re.sub(r'/\* M133: out-of-line redefinition removed \*/\s*\)\s*;', '/* removed */', c)
    c = re.sub(r'^\s*\);\s*$', '/* removed */', c, flags=re.MULTILINE)
    return c
hbu = f'{HWUI}/HardwareBitmapUploader.cpp'
patch(hbu, patch_hbu)

print('\nRound 9 patches applied')
