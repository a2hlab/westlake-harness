/*
 * ability_connection_adapter.cpp
 *
 * OH IAbilityConnection stub implementation.
 * Routes connection/disconnection callbacks to Java ServiceConnectionRegistry.
 *
 * 2026-05-06 — Refactored to use ScopedJniAttach RAII (see anonymous namespace
 * below). Same root cause as ability_scheduler_adapter.cpp: original getJNIEnv()
 * member function lacked a needsDetach signal so binder threads were never
 * detached when the binder pool destroyed them, causing ART CheckJNI fatal-abort
 * "thread exited without DetachCurrentThread". 2 call sites converted
 * (OnAbilityConnectDone + OnAbilityDisconnectDone); getJNIEnv() member function
 * and its .h declaration removed.
 */
#include "ability_connection_adapter.h"
#include "oh_callback_handler.h"
#include "westlake_jni_attach_admission.h"

#include <android/log.h>

#define LOG_TAG "OH_AbilityConnAdapter"
#define ALOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define ALOGW(...) __android_log_print(ANDROID_LOG_WARN, LOG_TAG, __VA_ARGS__)
#define ALOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

namespace oh_adapter {

namespace {

// 2026-05-06 ScopedJniAttach RAII — fixes binder-callback thread JNI attach leak.
// Original getJNIEnv() called AttachCurrentThread without returning a needsDetach
// flag.  When the OH binder thread pool tore down a thread that had been
// passively attached, ART CheckJNI fatal-aborted with
//   "thread exited without DetachCurrentThread"
// (cppcrash thread name = <pre-initialize>, SIGABRT).
//
// Usage:
//   ScopedJniAttach attach(jvm_);
//   JNIEnv* env = attach.env();
//   if (!env) return ...;
//   // ... use env ...
//
// Nesting is safe: an inner ScopedJniAttach on an already-attached thread sees
// JNI_OK from GetEnv and skips both attach and detach.
using ScopedJniAttach = westlake::jni::ScopedJniAttachment;

}  // namespace

// Cached JNI references for ServiceConnectionRegistry
static jclass sRegistryClass = nullptr;
static jmethodID sGetInstanceMethod = nullptr;
static jmethodID sOnConnectedMethod = nullptr;
static jmethodID sOnConnectionFailedMethod = nullptr;
static jmethodID sOnDisconnectedMethod = nullptr;
static bool sJniInitialized = false;

static bool initJniCache(JNIEnv* env) {
    if (sJniInitialized) return true;

    jclass cls = env->FindClass("adapter/activity/ServiceConnectionRegistry");
    if (!cls) {
        ALOGE("ServiceConnectionRegistry class not found");
        env->ExceptionClear();
        return false;
    }
    sRegistryClass = reinterpret_cast<jclass>(env->NewGlobalRef(cls));
    env->DeleteLocalRef(cls);

    sGetInstanceMethod = env->GetStaticMethodID(sRegistryClass, "getInstance",
            "()Ladapter/activity/ServiceConnectionRegistry;");
    sOnConnectedMethod = env->GetMethodID(sRegistryClass, "onServiceConnected",
            "(ILjava/lang/String;Ljava/lang/String;Landroid/os/IBinder;)V");
    sOnConnectionFailedMethod = env->GetMethodID(
            sRegistryClass, "onServiceConnectionFailed",
            "(ILjava/lang/String;Ljava/lang/String;I)V");
    sOnDisconnectedMethod = env->GetMethodID(sRegistryClass, "onServiceDisconnected",
            "(ILjava/lang/String;Ljava/lang/String;)V");

    if (!sGetInstanceMethod || !sOnConnectedMethod
            || !sOnConnectionFailedMethod || !sOnDisconnectedMethod) {
        ALOGE("Failed to find ServiceConnectionRegistry methods");
        env->ExceptionClear();
        return false;
    }

    sJniInitialized = true;
    return true;
}

AbilityConnectionAdapter::AbilityConnectionAdapter(JavaVM* jvm, int connectionId)
    : jvm_(jvm), connectionId_(connectionId)
{
    ALOGI("AbilityConnectionAdapter created: connectionId=%d", connectionId);
}

AbilityConnectionAdapter::~AbilityConnectionAdapter()
{
    ALOGI("AbilityConnectionAdapter destroyed: connectionId=%d", connectionId_);
}

void AbilityConnectionAdapter::OnAbilityConnectDone(
    const OHOS::AppExecFwk::ElementName& element,
    const OHOS::sptr<OHOS::IRemoteObject>& remoteObject,
    int resultCode)
{
    std::string bundleName = element.GetBundleName();
    std::string abilityName = element.GetAbilityName();

    ALOGI("[BRIDGED] OnAbilityConnectDone: connId=%d, bundle=%s, ability=%s, result=%d",
          connectionId_, bundleName.c_str(), abilityName.c_str(), resultCode);

    const bool connectionFailed = resultCode != 0;
    if (connectionFailed) {
        // 失败清理必须先于一切 JNI 操作：即使 Attach/Class/Java 回调失败，
        // native adapter 也不会泄漏，且下一次 bind 可消费失败标记并恢复。
        OHCallbackHandler::getInstance().markAbilityConnectionFailed(connectionId_);
        OHCallbackHandler::getInstance().removeAbilityConnection(connectionId_);
    }

    ScopedJniAttach attach(jvm_);
    JNIEnv* env = attach.env();
    if (!env) return;

    if (!initJniCache(env)) return;

    jobject registry = env->CallStaticObjectMethod(sRegistryClass, sGetInstanceMethod);
    if (!registry) {
        ALOGE("Failed to get ServiceConnectionRegistry instance");
        return;
    }

    jstring jBundle = env->NewStringUTF(bundleName.c_str());
    jstring jAbility = env->NewStringUTF(abilityName.c_str());

    if (!connectionFailed) {
        // A02 尚未提供 OH IRemoteObject -> Android IBinder 封装；A01 只证明
        // 原始 IServiceConnection.connected 到达，应用侧会观察 onNullBinding。
        env->CallVoidMethod(registry, sOnConnectedMethod,
                            static_cast<jint>(connectionId_),
                            jBundle, jAbility,
                            static_cast<jobject>(nullptr));
    } else {
        // OH 异步完成码同样只有 ERR_OK(0) 表示成功；失败不得伪装成连接回调。
        env->CallVoidMethod(registry, sOnConnectionFailedMethod,
                            static_cast<jint>(connectionId_),
                            jBundle, jAbility,
                            static_cast<jint>(resultCode));
    }

    if (env->ExceptionCheck()) {
        ALOGE("Java exception in onServiceConnected");
        env->ExceptionDescribe();
        env->ExceptionClear();
    } else if (connectionFailed) {
        // Java 注册表已确认清理；无需留给下一次 bind 做恢复。
        OHCallbackHandler::getInstance().consumeAbilityConnectionFailed(connectionId_);
    }

    env->DeleteLocalRef(jBundle);
    env->DeleteLocalRef(jAbility);
    env->DeleteLocalRef(registry);
}

void AbilityConnectionAdapter::OnAbilityDisconnectDone(
    const OHOS::AppExecFwk::ElementName& element,
    int resultCode)
{
    std::string bundleName = element.GetBundleName();
    std::string abilityName = element.GetAbilityName();

    ALOGI("[BRIDGED] OnAbilityDisconnectDone: connId=%d, bundle=%s, ability=%s, result=%d",
          connectionId_, bundleName.c_str(), abilityName.c_str(), resultCode);

    ScopedJniAttach attach(jvm_);
    JNIEnv* env = attach.env();
    if (!env) return;

    if (!initJniCache(env)) return;

    jobject registry = env->CallStaticObjectMethod(sRegistryClass, sGetInstanceMethod);
    if (!registry) {
        ALOGE("Failed to get ServiceConnectionRegistry instance");
        return;
    }

    jstring jBundle = env->NewStringUTF(bundleName.c_str());
    jstring jAbility = env->NewStringUTF(abilityName.c_str());

    env->CallVoidMethod(registry, sOnDisconnectedMethod,
                        static_cast<jint>(connectionId_),
                        jBundle, jAbility);

    if (env->ExceptionCheck()) {
        ALOGE("Java exception in onServiceDisconnected");
        env->ExceptionDescribe();
        env->ExceptionClear();
    }

    env->DeleteLocalRef(jBundle);
    env->DeleteLocalRef(jAbility);
    env->DeleteLocalRef(registry);
}

}  // namespace oh_adapter
