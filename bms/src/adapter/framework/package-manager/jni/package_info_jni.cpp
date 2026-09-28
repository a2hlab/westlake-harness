#include "package_info_runtime_v1.h"

#include <jni.h>

#include <atomic>
#include <string>

namespace {
std::atomic<uint64_t> requestSequence {1};
}

extern "C" JNIEXPORT jstring JNICALL
Java_adapter_packagemanager_PackageManagerAdapter_nativeGetCanonicalPackageInfo(
    JNIEnv* env, jclass, jstring packageName, jlong flags, jint userId,
    jint callingUid)
{
    if (packageName == nullptr) return nullptr;
    const char* packageChars = env->GetStringUTFChars(packageName, nullptr);
    if (packageChars == nullptr) return nullptr;
    const std::string package(packageChars);
    env->ReleaseStringUTFChars(packageName, packageChars);
    const std::string requestId = "android-getPackageInfo-" +
        std::to_string(requestSequence.fetch_add(1));
    const std::string response =
        oh_adapter::package_info::QueryPackageInfoRuntimeJsonV1(
            requestId, package, static_cast<uint64_t>(flags),
            static_cast<uint32_t>(userId), static_cast<int32_t>(callingUid));
    return env->NewStringUTF(response.c_str());
}
