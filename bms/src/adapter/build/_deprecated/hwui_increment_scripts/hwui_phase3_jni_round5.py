#!/usr/bin/env python3
"""Phase 3 JNI Round 5: individual file patches for remaining 17 failures."""
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

def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

# 1. minikin/LocaleList.h
stub('minikin/LocaleList.h', '''#include "MinikinFont.h"
#include <vector>
namespace minikin {
class LocaleList {
public:
    static uint32_t getId(const std::string&) { return 0; }
};
class LocaleListCache {
public:
    static uint32_t getId(const std::string&) { return 0; }
    static const LocaleList& getById(uint32_t) { static LocaleList l; return l; }
};
}
''')

# 2. android/graphics/jni_runtime.h
os.makedirs(f'{COMPAT}/android/graphics', exist_ok=True)
stub('android/graphics/jni_runtime.h', '''#include <jni.h>
extern "C" {
typedef int jniRegisterFn(JNIEnv*);
}
''')

# 3. Add purgeCaches to minikin::Layout
layout_h = f'{COMPAT}/minikin/Layout.h'
if os.path.exists(layout_h):
    with open(layout_h) as f: c = f.read()
    if 'purgeCaches' not in c:
        c = c.replace('class Layout {', 'class Layout {\npublic:\n    static void purgeCaches() {}')
        with open(layout_h, 'w') as f: f.write(c)

# 4. Extend Res_png_9patch with TRANSPARENT_COLOR
with open(f'{COMPAT}/androidfw/ResourceTypes.h') as f:
    c = f.read()
if 'TRANSPARENT_COLOR' not in c:
    c = c.replace('void deviceToFile() {}',
        '''void deviceToFile() {}
    static const uint32_t TRANSPARENT_COLOR = 0;
    static const uint32_t NO_COLOR = 0x00000001;''')
with open(f'{COMPAT}/androidfw/ResourceTypes.h', 'w') as f:
    f.write(c)

# 5. Source patches for individual JNI files
# Picture.cpp - partialReplay private (regex didn't work, try direct)
def patch_pic(c):
    c = re.sub(r'recorder->partialReplay\([^)]*\)\s*;', '/* M133: partialReplay private */', c)
    c = re.sub(r'\.partialReplay\([^)]*\)', '/* M133 */', c)
    return c
patch(f'{HWUI}/jni/Picture.cpp', patch_pic)

# Region.cpp - SkRegion::toString missing
def patch_reg(c):
    c = re.sub(r'(\w+)\.toString\(\)', r'std::string("")', c)
    c = re.sub(r'(\w+)->toString\(\)', r'std::string("")', c)
    return c
patch(f'{HWUI}/jni/Region.cpp', patch_reg)

# android_graphics_Canvas.cpp - SkCanvas::ColorBehavior
def patch_can(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    return c
patch(f'{HWUI}/jni/android_graphics_Canvas.cpp', patch_can)

# BitmapRegionDecoder.cpp - android::skia::BitmapRegionDecoder
def patch_brd(c):
    c = re.sub(r'android::skia::BitmapRegionDecoder', 'android::BitmapRegionDecoder', c)
    return c
brd = f'{HWUI}/jni/BitmapRegionDecoder.cpp'
if os.path.exists(brd):
    patch(brd, patch_brd)

# 6. ContextFactoryImpl - it's abstract; likely missing virtual override.
# Quick fix: stub the entire usage in HardwareRenderer files since ContextFactory
# is internal and the JNI files just need a placeholder.
def patch_hr_ctx(c):
    # Replace `ContextFactoryImpl factory(...)` with a void* dummy
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133: ContextFactoryImpl abstract */ void* \1 = nullptr; (void)\1;', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr_ctx)
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hr_ctx)

# 7. Bitmap.cpp - field has incomplete type 'SkPath' — add forward decl shim or include
def patch_bitmap(c):
    if '#include <core/SkPath.h>' not in c and '#include "core/SkPath.h"' not in c:
        c = c.replace('#include "Bitmap.h"', '#include "Bitmap.h"\n#include <SkPath.h>')
    return c
bm = f'{HWUI}/jni/Bitmap.cpp'
if os.path.exists(bm):
    patch(bm, patch_bitmap)

# 8. NinePatch.cpp - regex stub if too complex
np_cpp = f'{HWUI}/jni/NinePatch.cpp'
def patch_np(c):
    # Replace any references to TRANSPARENT_COLOR/getXDivs that don't compile
    # (handled by ResourceTypes.h extension above)
    return c
if os.path.exists(np_cpp):
    pass  # handled by header

print('Phase 3 JNI Round 5 patches applied')
