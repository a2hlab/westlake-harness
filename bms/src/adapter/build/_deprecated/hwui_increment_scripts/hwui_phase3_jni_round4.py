#!/usr/bin/env python3
"""Phase 3 JNI Round 4: fix jniRegister conflicts + remaining stubs."""
import os, re, shutil

HWUI = '/home/HanBingChen/aosp/frameworks/base/libs/hwui'
COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

def shim(name, target):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write(f'#pragma once\n#include "{target}"\n')

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

# 1. JNIPlatformHelp.h - use weak attribute so real libnativehelper can override
stub('nativehelper/JNIPlatformHelp.h', '''#include <jni.h>
#include <cstddef>
#ifndef NELEM
#define NELEM(x) (sizeof(x) / sizeof(*(x)))
#endif
#ifndef JNI_HELP_DEFINED
#define JNI_HELP_DEFINED
// Use weak attribute so real libnativehelper definitions (if linked) override these.
__attribute__((weak)) inline jobject jniCreateFileDescriptor(JNIEnv*, int) { return nullptr; }
__attribute__((weak)) inline int jniGetFDFromFileDescriptor(JNIEnv*, jobject) { return -1; }
__attribute__((weak)) inline void jniSetFileDescriptorOfFD(JNIEnv*, jobject, int) {}
__attribute__((weak)) inline int jniRegisterNativeMethods(JNIEnv* env, const char* className, const JNINativeMethod* methods, int n) {
    jclass c = env->FindClass(className);
    if (!c) return -1;
    return env->RegisterNatives(c, methods, n);
}
__attribute__((weak)) inline void* jniGetNioBufferPointer(JNIEnv* env, jobject buffer) {
    return env->GetDirectBufferAddress(buffer);
}
__attribute__((weak)) inline jlong jniGetNioBufferBaseArrayOffset(JNIEnv*, jobject) { return 0; }
__attribute__((weak)) inline jarray jniGetNioBufferBaseArray(JNIEnv*, jobject) { return nullptr; }
__attribute__((weak)) inline jint jniGetNioBufferFields(JNIEnv*, jobject, jint*, jint*, jint*) { return 0; }
__attribute__((weak)) inline jint jniThrowException(JNIEnv* env, const char* className, const char* msg) {
    jclass c = env->FindClass(className);
    if (c) env->ThrowNew(c, msg);
    return -1;
}
__attribute__((weak)) inline jint jniThrowExceptionFmt(JNIEnv* env, const char* className, const char* fmt, ...) {
    return jniThrowException(env, className, fmt);
}
__attribute__((weak)) inline jint jniThrowNullPointerException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/NullPointerException", msg);
}
__attribute__((weak)) inline jint jniThrowRuntimeException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/RuntimeException", msg);
}
__attribute__((weak)) inline jint jniThrowIOException(JNIEnv* env, int) {
    return jniThrowException(env, "java/io/IOException", "");
}
#endif // JNI_HELP_DEFINED
''')

# 2. SkTableMaskFilter.h
shim('SkTableMaskFilter.h', 'effects/SkTableMaskFilter.h')

# 3. jerror.h stub
stub('jerror.h', '''#include "jpeglib.h"
#define JMSG_LASTMSGCODE 0
inline void jpeg_std_error_msg(int) {}
''')

# 4. Extend Res_png_9patch with getXDivs/fileToDevice (used by NinePatch.cpp)
with open(f'{COMPAT}/androidfw/ResourceTypes.h') as f:
    c = f.read()
if 'getXDivs' not in c:
    c = c.replace('size_t serializedSize() const { return 0; }',
        '''size_t serializedSize() const { return 0; }
    int32_t* getXDivs() const { return xDivs; }
    int32_t* getYDivs() const { return yDivs; }
    uint32_t* getColors() const { return colors; }
    void fileToDevice() {}
    void deviceToFile() {}''')
with open(f'{COMPAT}/androidfw/ResourceTypes.h', 'w') as f:
    f.write(c)

# 5. Patch JNI source files for individual issues

# YuvToJpegEncoder - GifFileType incomplete + jpeglib issues
def patch_yuv(c):
    # Stub the entire file by guarding with #if 0
    if '#if 0  // OH adapter: YUV/JPEG encoder stubbed' not in c:
        c = '#if 0  // OH adapter: YUV/JPEG encoder stubbed\n' + c + '\n#endif\n'
    return c
yuv = f'{HWUI}/jni/YuvToJpegEncoder.cpp'
if os.path.exists(yuv):
    patch(yuv, patch_yuv)

# Movie.cpp - GifFileType incomplete
movie = f'{HWUI}/jni/Movie.cpp'
def patch_movie(c):
    if '#if 0  // OH adapter: Movie GIF stubbed' not in c:
        c = '#if 0  // OH adapter: Movie GIF stubbed\n' + c + '\n#endif\n'
    return c
if os.path.exists(movie):
    patch(movie, patch_movie)

gif = f'{HWUI}/jni/GIFMovie.cpp'
if os.path.exists(gif):
    patch(gif, patch_movie)

# Picture.cpp - SkPictureRecorder::partialReplay private
def patch_pic(c):
    c = re.sub(r'\.partialReplay\([^)]*\)', '/* partialReplay private in M133 */', c)
    return c
pic = f'{HWUI}/jni/Picture.cpp'
if os.path.exists(pic):
    patch(pic, patch_pic)

# Region.cpp - SkRegion::toString missing
def patch_reg(c):
    c = re.sub(r'\.toString\(\)', '/* M133: toString removed */ ""', c)
    return c
reg = f'{HWUI}/jni/Region.cpp'
if os.path.exists(reg):
    patch(reg, patch_reg)

# Canvas.cpp - SkCanvas::ColorBehavior missing
def patch_can(c):
    c = re.sub(r'SkCanvas::ColorBehavior::\w+', '0', c)
    c = re.sub(r'SkCanvas::ColorBehavior\b', 'int', c)
    return c
can = f'{HWUI}/jni/android_graphics_Canvas.cpp'
if os.path.exists(can):
    patch(can, patch_can)

# 6. ContextFactoryImpl - this is internal hwui type used by HardwareRenderer.
# Patch the file to declare it as ContextFactory.
def patch_hr(c):
    c = re.sub(r'\bContextFactoryImpl\b', 'IContextFactory', c)
    return c
hr = f'{HWUI}/jni/android_graphics_HardwareRenderer.cpp'
if os.path.exists(hr):
    patch(hr, patch_hr)
hbr = f'{HWUI}/jni/android_graphics_HardwareBufferRenderer.cpp'
if os.path.exists(hbr):
    patch(hbr, patch_hr)

print('Phase 3 JNI Round 4 patches applied')
