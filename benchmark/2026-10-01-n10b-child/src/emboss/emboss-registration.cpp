// AOSP14 r1 JNI constructor via cc-t3 handoff; OH m133 backing implementation.
#include <jni.h>
#include <nativehelper/JNIHelp.h>
#include <log/log.h>
#include "include/core/SkMaskFilter.h"
#include "include/effects/SkBlurMaskFilter.h"
#include "src/core/SkBlurMask.h"
enum JNIAccess { kRO_JNIAccess, kRW_JNIAccess };
class AutoJavaFloatArray {
public:
    AutoJavaFloatArray(JNIEnv* env, jfloatArray array,
                       int minLength = 0, JNIAccess = kRW_JNIAccess);
    ~AutoJavaFloatArray();

    float* ptr() const { return fPtr; }
    int    length() const { return fLen; }

private:
    JNIEnv*     fEnv;
    jfloatArray fArray;
    float*      fPtr;
    int         fLen;
    int         fReleaseMode;
};
static void doThrowIAE(JNIEnv* env, const char* msg = nullptr) { jniThrowException(env, "java/lang/IllegalArgumentException", msg); }
AutoJavaFloatArray::AutoJavaFloatArray(JNIEnv* env, jfloatArray array,
                                       int minLength, JNIAccess access)
: fEnv(env), fArray(array), fPtr(NULL), fLen(0) {
    ALOG_ASSERT(env);
    if (array) {
        fLen = env->GetArrayLength(array);
        if (fLen < minLength) {
            LOG_ALWAYS_FATAL("bad length");
        }
        fPtr = env->GetFloatArrayElements(array, NULL);
    }
    fReleaseMode = (access == kRO_JNIAccess) ? JNI_ABORT : 0;
}

AutoJavaFloatArray::~AutoJavaFloatArray() {
    if (fPtr) {
        fEnv->ReleaseFloatArrayElements(fArray, fPtr, fReleaseMode);
    }
}


static void ThrowIAE_IfNull(JNIEnv* env, void* ptr) {
    if (NULL == ptr) {
        doThrowIAE(env);
    }
}

// AOSP 14 r1 createEmboss (verbatim):
static jlong createEmboss(JNIEnv* env, jobject, jfloatArray dirArray,
                          jfloat ambient, jfloat specular, jfloat radius) {
    SkScalar direction[3];

    AutoJavaFloatArray autoDir(env, dirArray, 3);
    float* values = autoDir.ptr();
    for (int i = 0; i < 3; i++) {
        direction[i] = values[i];
    }

    SkScalar sigma = SkBlurMask::ConvertRadiusToSigma(radius);
    SkMaskFilter* filter = SkBlurMaskFilter::MakeEmboss(sigma,
            direction, ambient, specular).release();
    ThrowIAE_IfNull(env, filter);
    return reinterpret_cast<jlong>(filter);
}


extern "C" int register_n10b_Emboss(JNIEnv* env) {
    static const JNINativeMethod methods[] = {
        {"nativeConstructor", "([FFFF)J", reinterpret_cast<void*>(createEmboss)},
    };
    jclass cls = env->FindClass("android/graphics/EmbossMaskFilter");
    if (!cls) return -1;
    int result = env->RegisterNatives(cls, methods, 1);
    env->DeleteLocalRef(cls);
    return result;
}
