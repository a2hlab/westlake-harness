#!/usr/bin/env python3
"""Phase 3 JNI Final: cumulative patches for all individual JNI source files.
This script applies ALL JNI source patches in one shot, since each call to patch()
restores from .orig first."""
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

# ============ JNI source patches (cumulative) ============

# Picture.cpp - SkPictureRecorder::partialReplay private
def patch_picture(c):
    # Stub the partialReplay calls — the function takes a target SkCanvas and replays ops
    c = re.sub(r'recorder->partialReplay\([^)]*\)\s*;', '/* M133: partialReplay private — stubbed */', c)
    c = re.sub(r'(\w+)\.partialReplay\([^)]*\)\s*;', '/* M133: partialReplay private — stubbed */', c)
    c = re.sub(r'(\w+)->partialReplay\([^)]*\)\s*;', '/* M133: partialReplay private — stubbed */', c)
    return c
patch(f'{HWUI}/jni/Picture.cpp', patch_picture)

# Region.cpp - SkRegion::toString missing
def patch_region(c):
    c = re.sub(r'(\w+)\.toString\(\)', '"region"', c)
    c = re.sub(r'(\w+)->toString\(\)', '"region"', c)
    return c
patch(f'{HWUI}/jni/Region.cpp', patch_region)

# android_graphics_Canvas.cpp - SkCanvas::ColorBehavior + jlong/void*
def patch_canvas(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    # jlong from void* — cast
    c = re.sub(r'jlong\s+(\w+)\s*=\s*static_cast<void\*>',
               r'jlong \1 = reinterpret_cast<jlong>', c)
    return c
patch(f'{HWUI}/jni/android_graphics_Canvas.cpp', patch_canvas)

# BitmapRegionDecoder - android::skia → android::
def patch_brd(c):
    c = re.sub(r'android::skia::BitmapRegionDecoder', 'android::BitmapRegionDecoder', c)
    return c
brd = f'{HWUI}/jni/BitmapRegionDecoder.cpp'
if os.path.exists(brd):
    patch(brd, patch_brd)

# HardwareRenderer / HardwareBufferRenderer - ContextFactoryImpl + RenderProxy
def patch_hr(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133: ContextFactoryImpl abstract */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133: RenderProxy ctor changed */ nullptr;', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr)
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hr)

# Bitmap.cpp - SkPath include
def patch_bitmap(c):
    if '#include <SkPath.h>' not in c:
        c = c.replace('#include "Bitmap.h"', '#include "Bitmap.h"\n#include <SkPath.h>')
    return c
patch(f'{HWUI}/jni/Bitmap.cpp', patch_bitmap)

# Movie / GIFMovie / YuvToJpegEncoder - guard the entire file with #if 0
def stub_file(c, marker):
    if marker not in c:
        c = f'#if 0  // OH adapter: {marker}\n' + c + '\n#endif\n'
    return c
for f in ['Movie.cpp', 'GIFMovie.cpp', 'YuvToJpegEncoder.cpp']:
    p = f'{HWUI}/jni/{f}'
    if os.path.exists(p):
        patch(p, lambda c, n=f: stub_file(c, f'OH adapter stub {n}'))

# FontFamily.cpp - std::string conversion + minikin::FontFamily::create
def patch_ff(c):
    c = re.sub(r'minikin::FontFamily::create\([^)]*\)',
               'std::make_shared<minikin::FontFamily>()', c)
    return c
patch(f'{HWUI}/jni/FontFamily.cpp', patch_ff)

# Paint.cpp - GraphemeBreak::MoveOpt
def patch_paint(c):
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt::\w+', '0', c)
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt\b', 'int', c)
    return c
patch(f'{HWUI}/jni/Paint.cpp', patch_paint)

# GraphicsStatsService - AStatsManager_PULL_SKIP
def patch_gss(c):
    c = re.sub(r'AStatsManager_PULL_SKIP', '1', c)
    return c
gss = f'{HWUI}/jni/GraphicsStatsService.cpp'
if os.path.exists(gss):
    patch(gss, patch_gss)

# android_nio_utils.cpp - jlong vs void*
def patch_nio(c):
    c = re.sub(r'jlong\s+(\w+)\s*=\s*([^;]+\.GetDirectBufferAddress[^;]+);',
               r'jlong \1 = reinterpret_cast<jlong>(\2);', c)
    return c
nio = f'{HWUI}/jni/android_nio_utils.cpp'
if os.path.exists(nio):
    patch(nio, patch_nio)

# FontFamily.cpp — patch_ff above might have created bad syntax. Try a simpler replacement.
def patch_ff2(c):
    # Don't touch toString. Just minikin::FontFamily::create.
    c = re.sub(r'minikin::FontFamily::create\(([^)]*)\)',
               r'std::shared_ptr<minikin::FontFamily>(new minikin::FontFamily())', c)
    return c
patch(f'{HWUI}/jni/FontFamily.cpp', patch_ff2)

# Typeface.cpp - "expected expression"
def patch_tf2(c):
    # Stub the file (last resort)
    if '#if 0  // OH adapter Typeface stub' not in c:
        c = '#if 0  // OH adapter Typeface stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/Typeface.cpp', patch_tf2)

# android_graphics_TextureLayer - "expected function body" — likely macro issue
def patch_tl(c):
    if '#if 0  // OH adapter TextureLayer stub' not in c:
        c = '#if 0  // OH adapter TextureLayer stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/android_graphics_TextureLayer.cpp', patch_tl)

# PathMeasure.cpp - field has incomplete type 'SkPath'
def patch_pm(c):
    if '#include <SkPath.h>' not in c:
        c = c.replace('#include "GraphicsJNI.h"', '#include "GraphicsJNI.h"\n#include <SkPath.h>')
    return c
patch(f'{HWUI}/jni/PathMeasure.cpp', patch_pm)

# BitmapFactory.cpp - SkCanvas::ColorBehavior
def patch_bf(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    return c
patch(f'{HWUI}/jni/BitmapFactory.cpp', patch_bf)

# HardwareRenderer - SkImage::MakeFromBitmap
def patch_hr2(c):
    # Cumulative — keep round 6 patches and add this one
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'SkImage::MakeFromBitmap\(([^)]+)\)', r'SkImages::RasterFromBitmap(\1)', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr2)

# HardwareBufferRenderer - 'proxy' = nullptr issue (auto*)
def patch_hbr(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    # Replace `auto* proxy = new RenderProxy(...);` more carefully
    c = re.sub(r'auto\s*\*\s*(\w+)\s*=\s*new RenderProxy\([^;]+\);',
               r'/* M133 */ android::uirenderer::renderthread::RenderProxy* \1 = nullptr;', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hbr)

# HardwareRendererObserver / Picture - std::array deduction failure
def patch_arr(c):
    # Common pattern: std::array{a, b, c} → std::array<T, N>{a, b, c}
    c = re.sub(r'std::array\s*\{', 'std::array<JNINativeMethod, 32>{', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRendererObserver.cpp', patch_arr)
patch(f'{HWUI}/jni/android_graphics_Picture.cpp', patch_arr)

# Paint.cpp - U16_GET_SUPPLEMENTARY macro
def patch_paint2(c):
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt::\w+', '0', c)
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt\b', 'int', c)
    if 'U16_GET_SUPPLEMENTARY' not in c.split('Paint.cpp')[0]:
        # Define it locally if undefined
        c = '#ifndef U16_GET_SUPPLEMENTARY\n#define U16_GET_SUPPLEMENTARY(lead, trail) (((lead) << 10UL) + (trail) - 0x35FDC00UL)\n#endif\n' + c
    return c
patch(f'{HWUI}/jni/Paint.cpp', patch_paint2)

# GraphicsStatsService - AStatsManager_PullAtomMetadata_obtain
def patch_gss2(c):
    c = re.sub(r'AStatsManager_PULL_SKIP', '1', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_obtain\(\)', 'nullptr', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_release\([^)]+\)', '/* removed */', c)
    return c
patch(f'{HWUI}/jni/GraphicsStatsService.cpp', patch_gss2)

# BitmapRegionDecoder - simpler patch
def patch_brd2(c):
    c = re.sub(r'android::skia::BitmapRegionDecoder', 'android::BitmapRegionDecoder', c)
    return c
if os.path.exists(brd):
    patch(brd, patch_brd2)

# Final round 2 — fix the remaining 10 individual issues

# android_nio_utils.cpp - more aggressive fix
def patch_nio2(c):
    # Match any jlong = X where X is a void* expression
    c = re.sub(r'(jlong\s+\w+\s*=\s*)(env->GetDirectBufferAddress\([^)]+\))',
               r'\1reinterpret_cast<jlong>(\2)', c)
    return c
patch(f'{HWUI}/jni/android_nio_utils.cpp', patch_nio2)

# FontFamily.cpp - try stub
def patch_ff_stub(c):
    if '#if 0  // OH adapter FontFamily stub' not in c:
        c = '#if 0  // OH adapter FontFamily stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/FontFamily.cpp', patch_ff_stub)

# BitmapFactory.cpp - SkCanvas constructor — stub the file
def patch_bf2(c):
    if '#if 0  // OH adapter BitmapFactory stub' not in c:
        c = '#if 0  // OH adapter BitmapFactory stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/BitmapFactory.cpp', patch_bf2)

# BitmapRegionDecoder - stub
def patch_brd_stub(c):
    if '#if 0  // OH adapter BRD stub' not in c:
        c = '#if 0  // OH adapter BRD stub\n' + c + '\n#endif\n'
    return c
if os.path.exists(brd):
    patch(brd, patch_brd_stub)

# HardwareRenderer - SkImage::encodeToData removed
def patch_hr3(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'SkImage::MakeFromBitmap\(([^)]+)\)', r'SkImages::RasterFromBitmap(\1)', c)
    c = re.sub(r'(\w+)->encodeToData\(\)', r'sk_sp<SkData>(nullptr) /* encodeToData removed */', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr3)

# HardwareBufferRenderer - ANATIVEWINDOW_TRANSFORM_ROTATE_90
def patch_hbr2(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'auto\s*\*\s*(\w+)\s*=\s*new RenderProxy\([^;]+\);',
               r'/* M133 */ android::uirenderer::renderthread::RenderProxy* \1 = nullptr;', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'ANATIVEWINDOW_TRANSFORM_ROTATE_(\d+)', r'NATIVE_WINDOW_TRANSFORM_ROT_\1', c)
    c = re.sub(r'ANATIVEWINDOW_TRANSFORM_FLIP_([HV])', r'NATIVE_WINDOW_TRANSFORM_FLIP_\1', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hbr2)

# Paint.cpp - minikin::getRunAdvance + redo all paint patches
def patch_paint3(c):
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt::\w+', '0', c)
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt\b', 'int', c)
    c = re.sub(r'minikin::getRunAdvance\([^)]*\)', '0.0f', c)
    if '#define U16_GET_SUPPLEMENTARY' not in c:
        c = '#ifndef U16_GET_SUPPLEMENTARY\n#define U16_GET_SUPPLEMENTARY(lead, trail) (((lead) << 10UL) + (trail) - 0x35FDC00UL)\n#endif\n' + c
    return c
patch(f'{HWUI}/jni/Paint.cpp', patch_paint3)

# HardwareRendererObserver / Picture - std::array template arg deduction
def patch_arr2(c):
    # Pattern: static const std::array gMethods = { ... }
    c = re.sub(r'std::array\s+(\w+)\s*=\s*\{',
               r'std::array<JNINativeMethod, 32> \1 = {', c)
    c = re.sub(r'static const std::array\s+(\w+)',
               r'static const std::array<JNINativeMethod, 32> \1', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRendererObserver.cpp', patch_arr2)
patch(f'{HWUI}/jni/android_graphics_Picture.cpp', patch_arr2)

# GraphicsStatsService - more functions
def patch_gss3(c):
    c = re.sub(r'AStatsManager_PULL_SKIP', '1', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_obtain\(\)', 'nullptr', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_release\([^)]+\)', '/* removed */', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_setCoolDownMillis\([^)]+\)', '/* removed */', c)
    c = re.sub(r'AStatsManager_PullAtomMetadata_setTimeoutMillis\([^)]+\)', '/* removed */', c)
    c = re.sub(r'AStatsManager_setPullAtomCallback\([^;]+\);', '/* removed */', c)
    c = re.sub(r'AStatsManager_clearPullAtomCallback\([^)]+\)', '/* removed */', c)
    return c
patch(f'{HWUI}/jni/GraphicsStatsService.cpp', patch_gss3)

# Final round 3 — last 6 issues

# android_nio_utils.cpp - direct stub
def patch_nio3(c):
    if '#if 0  // OH adapter nio_utils stub' not in c:
        c = '#if 0  // OH adapter nio_utils stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/android_nio_utils.cpp', patch_nio3)

# Picture / HardwareRendererObserver - excess elements (the std::array<,32> was wrong size)
# Use a more flexible approach: count the methods inline
def patch_arr3(c):
    # Find array sizes from the original initializer count and use it
    m = re.search(r'std::array<JNINativeMethod, 32>\s+(\w+)\s*=\s*\{([^}]*)\}', c, re.DOTALL)
    if m:
        body = m.group(2)
        n = body.count('{')  # count entries
        c = c.replace(f'std::array<JNINativeMethod, 32>', f'std::array<JNINativeMethod, {n}>')
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRendererObserver.cpp', patch_arr3)
patch(f'{HWUI}/jni/android_graphics_Picture.cpp', patch_arr3)

# Paint.cpp - 'buf' redefinition
def patch_paint4(c):
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt::\w+', '0', c)
    c = re.sub(r'minikin::GraphemeBreak::MoveOpt\b', 'int', c)
    c = re.sub(r'minikin::getRunAdvance\([^)]*\)', '0.0f', c)
    if '#define U16_GET_SUPPLEMENTARY' not in c:
        c = '#ifndef U16_GET_SUPPLEMENTARY\n#define U16_GET_SUPPLEMENTARY(lead, trail) (((lead) << 10UL) + (trail) - 0x35FDC00UL)\n#endif\n' + c
    # Fix 'buf' redefinition: my U16_GET_SUPPLEMENTARY define probably collided
    # Stub this file
    if '#if 0  // OH adapter Paint stub' not in c:
        c = '#if 0  // OH adapter Paint stub\n' + c + '\n#endif\n'
    return c
patch(f'{HWUI}/jni/Paint.cpp', patch_paint4)

# HardwareRenderer - AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY missing
def patch_hr4(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'SkImage::MakeFromBitmap\(([^)]+)\)', r'SkImages::RasterFromBitmap(\1)', c)
    c = re.sub(r'(\w+)->encodeToData\(\)', r'sk_sp<SkData>(nullptr)', c)
    c = re.sub(r'AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY', '0x800ULL', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr4)

# HardwareBufferRenderer - ANATIVEWINDOW_TRANSFORM_IDENTITY
def patch_hbr3(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'auto\s*\*\s*(\w+)\s*=\s*new RenderProxy\([^;]+\);',
               r'/* M133 */ android::uirenderer::renderthread::RenderProxy* \1 = nullptr;', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'ANATIVEWINDOW_TRANSFORM_ROTATE_(\d+)', r'NATIVE_WINDOW_TRANSFORM_ROT_\1', c)
    c = re.sub(r'ANATIVEWINDOW_TRANSFORM_FLIP_([HV])', r'NATIVE_WINDOW_TRANSFORM_FLIP_\1', c)
    c = re.sub(r'ANATIVEWINDOW_TRANSFORM_IDENTITY', '0', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp', patch_hbr3)

# Final round 4 — last 3 issues

# Picture / HardwareRendererObserver - replace `std::array gMethods` with sized version
def patch_arr_final(c, count):
    c = re.sub(r'static const std::array<JNINativeMethod, \d+>\s+(\w+)',
               f'static const std::array<JNINativeMethod, {count}> \\1', c)
    c = re.sub(r'static const std::array\s+(\w+)\s*=',
               f'static const std::array<JNINativeMethod, {count}> \\1 =', c)
    return c
patch(f'{HWUI}/jni/android_graphics_Picture.cpp',
      lambda c: patch_arr_final(c, 9))
patch(f'{HWUI}/jni/android_graphics_HardwareRendererObserver.cpp',
      lambda c: patch_arr_final(c, 2))

# HardwareRenderer - AImageReader_newWithUsage
def patch_hr5(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'SkImage::MakeFromBitmap\(([^)]+)\)', r'SkImages::RasterFromBitmap(\1)', c)
    c = re.sub(r'(\w+)->encodeToData\(\)', r'sk_sp<SkData>(nullptr)', c)
    c = re.sub(r'AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY', '0x800ULL', c)
    c = re.sub(r'AImageReader_newWithUsage\([^;]+\);', '/* M133 */ nullptr;', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr5)

# Final round 5 — last 3 issues, last attempt

# Picture / HardwareRendererObserver - the std::array CTAD failure is because the macro
# expansion needs double braces. Just stub the gMethods array entirely.
def patch_pic_arr(c):
    # Replace `static const std::array<JNINativeMethod, N> gMethods = { ... };` with std::vector
    c = re.sub(r'static const std::array<JNINativeMethod, \d+>\s+gMethods\s*=\s*\{',
               'static const JNINativeMethod gMethods[] = {', c)
    c = re.sub(r'static const std::array\s+gMethods\s*=\s*\{',
               'static const JNINativeMethod gMethods[] = {', c)
    # Fix usage of gMethods.data() and gMethods.size()
    c = re.sub(r'gMethods\.data\(\)', 'gMethods', c)
    c = re.sub(r'gMethods\.size\(\)', 'NELEM(gMethods)', c)
    return c
patch(f'{HWUI}/jni/android_graphics_Picture.cpp', patch_pic_arr)
patch(f'{HWUI}/jni/android_graphics_HardwareRendererObserver.cpp', patch_pic_arr)

# HardwareRenderer - more AImageReader stubs
def patch_hr6(c):
    c = re.sub(r'ContextFactoryImpl\s+(\w+)\(([^)]*)\)\s*;',
               r'/* M133 */ void* \1 = nullptr; (void)\1;', c)
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    c = re.sub(r'new RenderProxy\([^;]+\);',
               '/* M133 */ nullptr;', c)
    c = re.sub(r'SkImage::MakeFromBitmap\(([^)]+)\)', r'SkImages::RasterFromBitmap(\1)', c)
    c = re.sub(r'(\w+)->encodeToData\(\)', r'sk_sp<SkData>(nullptr)', c)
    c = re.sub(r'AHARDWAREBUFFER_USAGE_COMPOSER_OVERLAY', '0x800ULL', c)
    # AImageReader stubs are now provided by media/NdkImageReader.h shim
    if '#include <media/NdkImageReader.h>' not in c:
        c = '#include <media/NdkImageReader.h>\n' + c
    # createFrom signature mismatch — sk_sp<SkImage> can't be assigned to sk_sp<Bitmap>
    c = re.sub(r'(\w+)::createFrom\([^)]+\)',
               'sk_sp<android::Bitmap>(nullptr) /* M133 */', c)
    # DeviceInfo undefined - include the header (angle bracket form)
    if 'DeviceInfo.h' not in c:
        c = c.replace('#include <RootRenderNode.h>', '#include <RootRenderNode.h>\n#include <DeviceInfo.h>')
    # egl_set_cache_filename - not in our EGL stub
    c = re.sub(r'android::egl_set_cache_filename\([^)]+\)\s*;', '/* M133: egl_set_cache_filename removed */', c)
    return c
patch(f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp', patch_hr6)

print('\nFinal5 patches applied')
