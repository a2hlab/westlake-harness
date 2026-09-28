#!/usr/bin/env python3
"""Phase 3 JNI Round 3: NELEM macro, more shims, fix jniRegister conflict."""
import os

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

# 1. Add NELEM macro and fix the inline conflict in JNIPlatformHelp.h
# The conflict happens when a file also includes the real libnativehelper header.
# Solution: only declare these as inline if not already defined.
stub('nativehelper/JNIPlatformHelp.h', '''#include <jni.h>
#include <cstddef>
#ifndef NELEM
#define NELEM(x) (sizeof(x) / sizeof(*(x)))
#endif
// Stub: provides JNI plat helpers; libnativehelper not present in adapter build.
#ifndef JNI_HELP_DEFINED
#define JNI_HELP_DEFINED
inline jobject jniCreateFileDescriptor(JNIEnv*, int) { return nullptr; }
inline int jniGetFDFromFileDescriptor(JNIEnv*, jobject) { return -1; }
inline void jniSetFileDescriptorOfFD(JNIEnv*, jobject, int) {}
inline int jniRegisterNativeMethods(JNIEnv* env, const char* className, const JNINativeMethod* methods, int n) {
    jclass c = env->FindClass(className);
    if (!c) return -1;
    return env->RegisterNatives(c, methods, n);
}
inline void* jniGetNioBufferPointer(JNIEnv* env, jobject buffer) {
    return env->GetDirectBufferAddress(buffer);
}
inline jlong jniGetNioBufferBaseArrayOffset(JNIEnv*, jobject) { return 0; }
inline jarray jniGetNioBufferBaseArray(JNIEnv*, jobject) { return nullptr; }
inline jint jniGetNioBufferFields(JNIEnv*, jobject, jint*, jint*, jint*) { return 0; }
inline jint jniThrowException(JNIEnv* env, const char* className, const char* msg) {
    jclass c = env->FindClass(className);
    if (c) env->ThrowNew(c, msg);
    return -1;
}
inline jint jniThrowExceptionFmt(JNIEnv* env, const char* className, const char* fmt, ...) {
    return jniThrowException(env, className, fmt);
}
inline jint jniThrowNullPointerException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/NullPointerException", msg);
}
inline jint jniThrowRuntimeException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/RuntimeException", msg);
}
inline jint jniThrowIOException(JNIEnv* env, int) {
    return jniThrowException(env, "java/io/IOException", "");
}
#endif // JNI_HELP_DEFINED
''')

# Also create JNIHelp.h as alias (libnativehelper's primary header)
stub('nativehelper/JNIHelp.h', '#include "JNIPlatformHelp.h"\n')
stub('JNIHelp.h', '#include "nativehelper/JNIPlatformHelp.h"\n')

# 2. Skia header redirects (M133 paths)
shim('SkImageFilters.h',     'effects/SkImageFilters.h')
shim('SkColorMatrixFilter.h','effects/SkColorMatrixFilter.h')
shim('SkBlurMaskFilter.h',   'effects/SkBlurMaskFilter.h')
shim('Sk1DPathEffect.h',     'effects/Sk1DPathEffect.h')
shim('Sk2DPathEffect.h',     'effects/Sk2DPathEffect.h')
shim('SkDashPathEffect.h',   'effects/SkDashPathEffect.h')
shim('SkCornerPathEffect.h', 'effects/SkCornerPathEffect.h')
shim('SkDiscretePathEffect.h','effects/SkDiscretePathEffect.h')
shim('SkPictureRecorder.h',  'core/SkPictureRecorder.h')
shim('SkPicture.h',          'core/SkPicture.h')
shim('SkColorFilter.h',      'core/SkColorFilter.h')
shim('SkImageInfo.h',        'core/SkImageInfo.h')
shim('SkRefCnt.h',           'core/SkRefCnt.h')
shim('SkRegion.h',           'core/SkRegion.h')
shim('SkPath.h',             'core/SkPath.h')
shim('SkPathMeasure.h',      'core/SkPathMeasure.h')
shim('SkBitmap.h',           'core/SkBitmap.h')
shim('SkData.h',             'core/SkData.h')
shim('SkStream.h',           'core/SkStream.h')
shim('SkString.h',           'core/SkString.h')
shim('SkRect.h',             'core/SkRect.h')
shim('SkPoint.h',            'core/SkPoint.h')
shim('SkMatrix.h',           'core/SkMatrix.h')
shim('SkM44.h',              'core/SkM44.h')
shim('SkColor.h',            'core/SkColor.h')
shim('SkColorSpace.h',       'core/SkColorSpace.h')
shim('SkPaint.h',            'core/SkPaint.h')
shim('SkFont.h',             'core/SkFont.h')
shim('SkFontMgr.h',          'core/SkFontMgr.h')
shim('SkFontMetrics.h',      'core/SkFontMetrics.h')
shim('SkFontStyle.h',        'core/SkFontStyle.h')
shim('SkTypeface.h',         'core/SkTypeface.h')
shim('SkTextBlob.h',         'core/SkTextBlob.h')
shim('SkRSXform.h',          'core/SkRSXform.h')
shim('SkVertices.h',         'core/SkVertices.h')
shim('SkBlendMode.h',        'core/SkBlendMode.h')
shim('SkPixmap.h',           'core/SkPixmap.h')
shim('SkClipOp.h',           'core/SkClipOp.h')
shim('SkDrawLooper.h',       'core/SkDrawLooper.h')
shim('SkMaskFilter.h',       'core/SkMaskFilter.h')
shim('SkPathEffect.h',       'core/SkPathEffect.h')
shim('SkShader.h',           'core/SkShader.h')

# 3. private/EGL/cache.h
stub('private/EGL/cache.h', '''namespace android {
class egl_cache_t {
public:
    static egl_cache_t* get() { return nullptr; }
    void initialize(void*) {}
    void terminate() {}
    void setBlob(const void*, size_t, const void*, size_t) {}
    size_t getBlob(const void*, size_t, void*, size_t) { return 0; }
};
}
''')

# 4. statslog_hwui.h
stub('statslog_hwui.h', '''#include <cstdint>
namespace android { namespace util {
inline int stats_write(int, ...) { return 0; }
}}
''')

print('Phase 3 JNI Round 3 patches applied')
