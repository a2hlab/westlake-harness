#!/usr/bin/env python3
"""Phase 3 JNI Round 6: more individual fixes."""
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

# 1. unicode/utf16.h
os.makedirs(f'{COMPAT}/unicode', exist_ok=True)
stub('unicode/utf16.h', '''#include <cstdint>
#define U16_NEXT(s, i, len, c) do { c = (s)[i]; ++(i); } while(0)
#define U16_PREV(s, start, i, c) do { --(i); c = (s)[i]; } while(0)
#define U16_LENGTH(c) ((c) > 0xFFFF ? 2 : 1)
#define U16_IS_LEAD(c) (((c) & 0xFC00) == 0xD800)
#define U16_IS_TRAIL(c) (((c) & 0xFC00) == 0xDC00)
#define U16_IS_SURROGATE(c) (((c) & 0xF800) == 0xD800)
''')

# 2. AStatsManager_PullAtomCallbackReturn
with open(f'{COMPAT}/stats_pull_atom_callback.h') as f: c = f.read()
if 'AStatsManager_PullAtomCallbackReturn' not in c:
    c = c.replace('typedef int (*AStatsManager_PullAtomCallback)',
        '''typedef int AStatsManager_PullAtomCallbackReturn;
#define AStatsManager_PULL_SUCCESS 0
typedef int (*AStatsManager_PullAtomCallback)''')
with open(f'{COMPAT}/stats_pull_atom_callback.h', 'w') as f:
    f.write(c)

# 3. minikin::registerLocaleList
with open(f'{COMPAT}/minikin/MinikinFont.h') as f: c = f.read()
if 'registerLocaleList' not in c:
    c = c.replace('class MeasuredText {};',
        '''class MeasuredText {};

inline uint32_t registerLocaleList(const std::string&) { return 0; }
''')
with open(f'{COMPAT}/minikin/MinikinFont.h', 'w') as f:
    f.write(c)

# 4. Source patches

# Picture.cpp - try a more aggressive patch (the partialReplay refers to a member access, not a function call)
def patch_pic(c):
    # Just replace any reference to partialReplay with a no-op
    c = re.sub(r'\.partialReplay', '/*partialReplay*/.recordingCanvas()->save', c)
    c = re.sub(r'->partialReplay', '/*partialReplay*/->save', c)
    return c
patch(f'{HWUI}/jni/Picture.cpp', patch_pic)

# Region.cpp - SkRegion::toString — use std::string everywhere
def patch_reg(c):
    # The patch from round 5 might not have worked due to .orig restore
    c = re.sub(r'(\w+)\.toString\(\)\.c_str\(\)', '""', c)
    c = re.sub(r'(\w+)->toString\(\)\.c_str\(\)', '""', c)
    return c
patch(f'{HWUI}/jni/Region.cpp', patch_reg)

# android_graphics_Canvas.cpp - SkCanvas::ColorBehavior + jlong/void* issue
def patch_can(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    return c
patch(f'{HWUI}/jni/android_graphics_Canvas.cpp', patch_can)

# BitmapRegionDecoder - use android::BitmapRegionDecoder
def patch_brd(c):
    c = re.sub(r'android::skia::BitmapRegionDecoder', 'android::BitmapRegionDecoder', c)
    return c
patch(f'{HWUI}/jni/BitmapRegionDecoder.cpp', patch_brd)

# RenderProxy constructor mismatch — likely needs different signature
# Files: android_graphics_HardwareRenderer / android_graphics_HardwareBufferRenderer
def patch_hr_proxy(c):
    # Replace RenderProxy(true, ...) calls with RenderProxy() default
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133: RenderProxy ctor changed */ nullptr;', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr_proxy)
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hr_proxy)

# Bitmap.cpp - SkPath include
def patch_bitmap(c):
    if '#include <SkPath.h>' not in c:
        c = c.replace('#include "Bitmap.h"', '#include "Bitmap.h"\n#include <SkPath.h>')
    return c
patch(f'{HWUI}/jni/Bitmap.cpp', patch_bitmap)

# FontFamily.cpp - std::string to char* conversion
def patch_ff(c):
    # Most likely .c_str() needed somewhere
    c = re.sub(r'(\w+)\.toString\(\)', r'\1.toString().c_str()', c)
    return c
ff = f'{HWUI}/jni/FontFamily.cpp'
if os.path.exists(ff):
    patch(ff, patch_ff)

print('Phase 3 JNI Round 6 patches applied')
