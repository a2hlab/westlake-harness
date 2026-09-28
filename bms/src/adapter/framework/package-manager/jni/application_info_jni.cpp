#include "application_info_public_entry_v1.h"

#include <jni.h>

#include <string>

extern "C" JNIEXPORT jstring JNICALL
Java_adapter_packagemanager_PackageManagerAdapter_nativeGetCanonicalApplicationInfo(
    JNIEnv* env, jclass, jstring packageName, jlong flags, jint userId,
    jint callingUid)
{
    if (packageName == nullptr) return nullptr;
    const char* packageChars = env->GetStringUTFChars(packageName, nullptr);
    if (packageChars == nullptr) return nullptr;
    const std::string package(packageChars);
    env->ReleaseStringUTFChars(packageName, packageChars);
    const std::string response =
        oh_adapter::application_info::QueryCanonicalApplicationInfoEntryV1(
            package, static_cast<uint64_t>(flags),
            static_cast<uint32_t>(userId), static_cast<int32_t>(callingUid));
    return env->NewStringUTF(response.c_str());
}
