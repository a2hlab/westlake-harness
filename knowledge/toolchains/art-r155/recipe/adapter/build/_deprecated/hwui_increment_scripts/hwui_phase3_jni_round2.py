#!/usr/bin/env python3
"""Phase 3 JNI Round 2: jniRegisterNativeMethods + remaining shims."""
import os

COMPAT = '/home/HanBingChen/adapter/build/skia_compat_headers'

def stub(name, content):
    p = f'{COMPAT}/{name}'
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, 'w') as f:
        f.write('#pragma once\n' + content)

# 1. Update JNIPlatformHelp to add jniRegisterNativeMethods + jniGetNioBufferPointer
stub('nativehelper/JNIPlatformHelp.h', '''#include <jni.h>
#include <cstddef>
// Stub: provides JNI plat helpers; libnativehelper not present in adapter build.
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
inline jint jniThrowNullPointerException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/NullPointerException", msg);
}
inline jint jniThrowRuntimeException(JNIEnv* env, const char* msg) {
    return jniThrowException(env, "java/lang/RuntimeException", msg);
}
inline jint jniThrowIOException(JNIEnv* env, int) {
    return jniThrowException(env, "java/io/IOException", "");
}
''')

# 2. utils/SkFrontBufferedStream.h - point to client_utils/android version
stub('utils/SkFrontBufferedStream.h', '''#include "client_utils/android/FrontBufferedStream.h"
''')

# Also fix the bare FrontBufferedStream.h shim (was redirect-only)
stub('FrontBufferedStream.h', '''#include "client_utils/android/FrontBufferedStream.h"
''')

# 3. minikin/FontVariation.h
stub('minikin/FontVariation.h', '''#include "MinikinFont.h"
''')

# 4. jpeglib.h - stub
stub('jpeglib.h', '''#include <cstddef>
#include <cstdint>
#include <cstdio>
typedef int boolean;
typedef int J_COLOR_SPACE;
typedef int J_DCT_METHOD;
typedef unsigned int JDIMENSION;
typedef unsigned char JSAMPLE;
typedef JSAMPLE* JSAMPROW;
typedef JSAMPROW* JSAMPARRAY;
struct jpeg_error_mgr { int msg_code; };
struct jpeg_compress_struct {
    struct jpeg_error_mgr* err;
    JDIMENSION image_width, image_height;
    int input_components;
    J_COLOR_SPACE in_color_space;
};
struct jpeg_decompress_struct {
    struct jpeg_error_mgr* err;
    JDIMENSION image_width, image_height;
    JDIMENSION output_width, output_height;
    int output_components;
};
typedef struct jpeg_compress_struct* j_compress_ptr;
typedef struct jpeg_decompress_struct* j_decompress_ptr;
inline jpeg_error_mgr* jpeg_std_error(jpeg_error_mgr* e) { return e; }
inline void jpeg_create_compress(j_compress_ptr) {}
inline void jpeg_destroy_compress(j_compress_ptr) {}
inline void jpeg_set_defaults(j_compress_ptr) {}
inline void jpeg_set_quality(j_compress_ptr, int, boolean) {}
inline void jpeg_start_compress(j_compress_ptr, boolean) {}
inline void jpeg_finish_compress(j_compress_ptr) {}
inline JDIMENSION jpeg_write_scanlines(j_compress_ptr, JSAMPARRAY, JDIMENSION) { return 0; }
''')

# 5. stats_event.h
stub('stats_event.h', '''typedef struct AStatsEvent AStatsEvent;
inline AStatsEvent* AStatsEvent_obtain() { return nullptr; }
inline void AStatsEvent_setAtomId(AStatsEvent*, int) {}
inline void AStatsEvent_writeInt32(AStatsEvent*, int) {}
inline void AStatsEvent_writeInt64(AStatsEvent*, long) {}
inline void AStatsEvent_writeString(AStatsEvent*, const char*) {}
inline int AStatsEvent_write(AStatsEvent*) { return 0; }
inline void AStatsEvent_release(AStatsEvent*) {}
''')

print('Phase 3 JNI Round 2 patches applied')
