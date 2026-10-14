#include "component_resolver_runtime_v1.h"

#include <jni.h>

#include <atomic>
#include <string>
#include <utility>
#include <vector>

namespace {

std::string StringValue(JNIEnv* env, jstring value)
{
    if (value == nullptr) return {};
    const char* chars = env->GetStringUTFChars(value, nullptr);
    if (chars == nullptr) return {};
    std::string result(chars);
    env->ReleaseStringUTFChars(value, chars);
    return result;
}

bool StringArrayValue(JNIEnv* env, jobjectArray array,
    std::vector<std::string>* values)
{
    if (values == nullptr) return false;
    values->clear();
    if (array == nullptr) return true;
    const jsize count = env->GetArrayLength(array);
    if (count < 0 || count > 16384) return false;
    values->reserve(static_cast<size_t>(count));
    for (jsize index = 0; index < count; ++index) {
        auto value = static_cast<jstring>(
            env->GetObjectArrayElement(array, index));
        if (env->ExceptionCheck() || value == nullptr) {
            if (value != nullptr) env->DeleteLocalRef(value);
            return false;
        }
        values->push_back(StringValue(env, value));
        env->DeleteLocalRef(value);
    }
    return true;
}

}  // namespace

extern "C" JNIEXPORT jstring JNICALL
Java_adapter_packagemanager_PackageManagerAdapter_nativeResolveCanonicalComponents(
    JNIEnv* env, jclass, jstring requestId, jstring componentKind,
    jstring action, jobjectArray categories, jstring resolvedType,
    jstring scheme, jstring host, jint port, jstring path,
    jstring packageSelector, jstring explicitPackage,
    jstring explicitClass, jlong flags, jboolean defaultOnly,
    jint userId, jint callingUid, jlong expectedCatalogRevision,
    jstring expectedIndexDigest, jlong expectedGeneration,
    jstring expectedCanonicalDigest)
{
    oh_adapter::component_resolver::ComponentResolveRequestV1 request;
    request.requestId = StringValue(env, requestId);
    const std::string kind = StringValue(env, componentKind);
    request.kindWasRecognized =
        oh_adapter::component_resolver::ParseComponentKindV1(
            kind, &request.kind);
    request.intent.action = StringValue(env, action);
    if (!StringArrayValue(env, categories, &request.intent.categories)) {
        request.schemaVersion = 0;
    }
    request.intent.resolvedType = StringValue(env, resolvedType);
    request.intent.scheme = StringValue(env, scheme);
    request.intent.host = StringValue(env, host);
    request.intent.port = static_cast<int32_t>(port);
    request.intent.path = StringValue(env, path);
    request.intent.packageSelector = StringValue(env, packageSelector);
    request.intent.explicitPackage = StringValue(env, explicitPackage);
    request.intent.explicitClass = StringValue(env, explicitClass);
    request.flags = static_cast<uint64_t>(flags);
    request.defaultOnly = defaultOnly == JNI_TRUE;
    request.userId = static_cast<uint32_t>(userId);
    if (expectedCatalogRevision > 0) {
        request.expectedCatalogRevision =
            static_cast<uint64_t>(expectedCatalogRevision);
    }
    const std::string indexDigest =
        StringValue(env, expectedIndexDigest);
    if (!indexDigest.empty()) request.expectedIndexDigest = indexDigest;
    if (expectedGeneration > 0) {
        request.expectedGeneration =
            static_cast<uint64_t>(expectedGeneration);
    }
    const std::string canonicalDigest =
        StringValue(env, expectedCanonicalDigest);
    if (!canonicalDigest.empty()) {
        request.expectedCanonicalDigest = canonicalDigest;
    }
    const std::string response =
        oh_adapter::component_resolver::QueryComponentResolverRuntimeJsonV1(
            std::move(request), static_cast<int32_t>(callingUid));
    return env->NewStringUTF(response.c_str());
}
