#!/usr/bin/env python3
"""Round 10: final cleanup - VKAPI macros, PRI* format macros, individual file patches."""
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

# 1. Update vulkan.h - add VKAPI_PTR, VKAPI_ATTR, VKAPI_CALL macros
with open(f'{COMPAT}/vulkan/vulkan.h') as f: c = f.read()
if 'VKAPI_PTR' not in c:
    c = c.replace('#pragma once\n',
        '''#pragma once
#define VKAPI_PTR
#define VKAPI_ATTR
#define VKAPI_CALL
''')
with open(f'{COMPAT}/vulkan/vulkan.h', 'w') as f: f.write(c)
print('vulkan.h: VKAPI macros added')

# 2. Update force-include - add <inttypes.h> for PRIu32 etc.
with open(f'{COMPAT}/hwui_force_include.h') as f: c = f.read()
if 'inttypes.h' not in c:
    c = c.replace('#include <atomic>', '#include <atomic>\n#include <inttypes.h>')
with open(f'{COMPAT}/hwui_force_include.h', 'w') as f: f.write(c)
print('hwui_force_include.h: inttypes added')

# 3. SkAndroidFrameworkUtils - add LinearGradientInfo
with open(f'{COMPAT}/SkAndroidFrameworkUtils.h', 'w') as f:
    f.write('''#pragma once
#include <cstdint>
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
};
''')
print('SkAndroidFrameworkUtils.h with LinearGradientInfo')

# 4. SkEncodedOrigin.h, SkCanvasStateUtils.h direct stubs
def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

stub('SkEncodedOrigin.h', 'enum SkEncodedOrigin { kTopLeft_SkEncodedOrigin = 1, kDefault_SkEncodedOrigin = 1 };\n')
stub('SkCanvasStateUtils.h', 'class SkCanvas; struct SkCanvasState; namespace SkCanvasStateUtils { inline SkCanvas* CreateFromCanvasState(const SkCanvasState*) { return nullptr; } inline SkCanvasState* CaptureCanvasState(SkCanvas*) { return nullptr; } inline void ReleaseCanvasState(SkCanvasState*) {} }\n')

# 5. Fix SkShadowUtils — wrap as namespace
with open(f'{COMPAT}/SkShadowUtils.h', 'w') as f:
    f.write('''#pragma once
class SkPath; class SkPaint; class SkCanvas;
class SkShadowUtils {
public:
    static void DrawShadow(SkCanvas*, const SkPath&, const void*, const void*, const void*, unsigned, unsigned, float, unsigned) {}
};
''')

# 6. SkWebpEncoder - the existing redirect target may exist; provide as namespace
with open(f'{COMPAT}/SkWebpEncoder.h', 'w') as f:
    f.write('''#pragma once
namespace SkWebpEncoder {
    struct Options { int fQuality = 100; int fCompression = 0; };
    template<typename T> inline bool Encode(T*, const void*, const Options&) { return false; }
}
''')

# 7. minikin: add fontFeatureSettings
with open(f'{COMPAT}/minikin/MinikinFont.h') as f: c = f.read()
if 'fontFeatureSettings' not in c:
    c = c.replace('FamilyVariant familyVariant',
                  'std::string fontFeatureSettings;\n    FamilyVariant familyVariant')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f: f.write(c)
print('MinikinFont.h: fontFeatureSettings added')

# 8. BlobCache: kCombinedTooBig
with open(f'{COMPAT}/FileBlobCache.h') as f: c = f.read()
if 'kCombinedTooBig' not in c:
    c = c.replace('kKeyTooBig = 7, kValueTooBig = 8',
                  'kKeyTooBig = 7, kValueTooBig = 8, kCombinedTooBig = 9')
with open(f'{COMPAT}/FileBlobCache.h', 'w') as f: f.write(c)
print('FileBlobCache.h: kCombinedTooBig added')

# 9. ANativeWindow_setBuffersDataSpace - the round 9 sed broke; redo with valid structure
nw_h = f'{COMPAT}/android/native_window.h'
with open(nw_h) as f: c = f.read()
if 'setBuffersDataSpace' not in c:
    c += '\nextern "C" int ANativeWindow_setBuffersDataSpace(ANativeWindow* window, int dataSpace);\nextern "C" int ANativeWindow_getBuffersDataSpace(ANativeWindow* window);\n'
    with open(nw_h, 'w') as f: f.write(c)
print('android/native_window.h: setBuffersDataSpace appended')

# 10. Patch RecordingCanvas - SkCanvas::flush() removed
def patch_rc(c):
    c = re.sub(r'(\w+)->flush\(\)\s*;', r'/* M133: SkCanvas::flush removed */ (void)\1;', c)
    return c
patch(f'{HWUI}/RecordingCanvas.cpp', patch_rc)

print('\nRound 10 patches applied')
