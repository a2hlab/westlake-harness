// ============================================================================
// com_android_internal_os_ClassLoaderFactory.cpp
//
// JNI registration for ClassLoaderFactory.createClassloaderNamespace.
//
// The JNI boundary preserves AOSP's exact seven-argument contract. The
// adapter-owned libnativeloader implementation maps the Java ClassLoader to a
// strict OpenHarmony dlns domain and returns a Java error string on failure.
// ============================================================================

#include "AndroidRuntime.h"

#include <jni.h>
#include <nativeloader/native_loader.h>

namespace android {

namespace {

jstring CLF_createClassloaderNamespace(JNIEnv* env, jclass /*clazz*/,
        jobject classLoader, jint targetSdkVersion,
        jstring librarySearchPath, jstring libraryPermittedPath,
        jboolean isShared, jstring dexPath, jstring sonameList) {
    return CreateClassLoaderNamespace(env, targetSdkVersion, classLoader,
            isShared == JNI_TRUE, dexPath, librarySearchPath,
            libraryPermittedPath, sonameList);
}

const JNINativeMethod kMethods[] = {
    { "createClassloaderNamespace",
      "(Ljava/lang/ClassLoader;ILjava/lang/String;Ljava/lang/String;ZLjava/lang/String;Ljava/lang/String;)Ljava/lang/String;",
      reinterpret_cast<void*>(CLF_createClassloaderNamespace) },
};

}  // namespace

int register_com_android_internal_os_ClassLoaderFactory(JNIEnv* env) {
    jclass clazz = env->FindClass("com/android/internal/os/ClassLoaderFactory");
    if (!clazz) return -1;
    jint rc = env->RegisterNatives(clazz, kMethods,
                                    sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    return rc == JNI_OK ? 0 : -1;
}

}  // namespace android
