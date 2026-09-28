/*
 * activity_task_manager_adapter.cpp
 *
 * JNI registration for adapter.activity.ActivityTaskManagerAdapter via
 * RegisterNatives.  Replaces the legacy
 * Java_adapter_bridge_ActivityTaskManagerAdapter_* exports that previously
 * lived in framework/core/jni/adapter_bridge.cpp.
 *
 * Class:  adapter/activity/ActivityTaskManagerAdapter  (BCP - oh-adapter-framework.jar)
 * Registered from adapter_bridge.cpp's JNI_OnLoad via
 *   register_ActivityTaskManagerAdapter(env).
 *
 * 8 natives: 2 generic (GetService + StartAbility) + 6 mission stack ops.
 * The 6 mission natives previously had no adapter_activity_* forwarder and
 * raised UnsatisfiedLinkError on first call from bridgeStartActivityWithStack —
 * see 2026-05-19 helloworld pid 2340 crash (build_patch_log entry).
 */

#include "oh_ability_manager_client.h"

#include <android/log.h>
#include <jni.h>
#include <string>

#define TAG "OH_ATMJNI"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, TAG, __VA_ARGS__)

using namespace oh_adapter;

namespace {

std::string jstr(JNIEnv* env, jstring s) {
    if (!s) return "";
    const char* raw = env->GetStringUTFChars(s, nullptr);
    std::string result(raw);
    env->ReleaseStringUTFChars(s, raw);
    return result;
}

// -------- generic (2) --------

jlong nativeGetOHAbilityManagerService_impl(JNIEnv*, jclass) {
    return (jlong)&OHAbilityManagerClient::getInstance();
}

jint nativeStartAbility_impl(JNIEnv* env, jclass,
                             jstring bundleName, jstring abilityName,
                             jstring action, jstring uri, jstring extraJson,
                             jlong callerOhTokenAddr, jint androidLaunchFlags) {
    WantParams want;
    want.bundleName = jstr(env, bundleName);
    want.abilityName = jstr(env, abilityName);
    want.action = jstr(env, action);
    want.uri = jstr(env, uri);
    want.parametersJson = jstr(env, extraJson);
    want.androidLaunchFlags = androidLaunchFlags;  // 2026-05-25 1D

    LOGI("nativeStartAbility: bundle=%s, ability=%s, action=%s, callerOhToken=0x%llx, flags=0x%x",
         want.bundleName.c_str(), want.abilityName.c_str(), want.action.c_str(),
         static_cast<unsigned long long>(callerOhTokenAddr),
         static_cast<unsigned int>(androidLaunchFlags));

    return OHAbilityManagerClient::getInstance().startAbilityWithCaller(
            want, callerOhTokenAddr);
}

// -------- mission stack (6) --------

jint nativeStartAbilityInMission_impl(JNIEnv* env, jclass,
                                      jstring bundleName, jstring abilityName,
                                      jstring action, jstring uri, jstring extraJson,
                                      jint missionId) {
    WantParams want;
    want.bundleName = jstr(env, bundleName);
    want.abilityName = jstr(env, abilityName);
    want.action = jstr(env, action);
    want.uri = jstr(env, uri);
    want.parametersJson = jstr(env, extraJson);

    LOGI("nativeStartAbilityInMission: bundle=%s, ability=%s, missionId=%d",
         want.bundleName.c_str(), want.abilityName.c_str(), missionId);

    return OHAbilityManagerClient::getInstance().startAbilityInMission(want, missionId);
}

jint nativeCleanMission_impl(JNIEnv*, jclass, jint missionId) {
    return OHAbilityManagerClient::getInstance().cleanMission(missionId);
}

jint nativeMoveMissionToFront_impl(JNIEnv*, jclass, jint missionId) {
    return OHAbilityManagerClient::getInstance().moveMissionToFront(missionId);
}

jboolean nativeIsTopAbility_impl(JNIEnv* env, jclass,
                                 jint missionId, jstring abilityName) {
    std::string name = jstr(env, abilityName);
    return (jboolean)OHAbilityManagerClient::getInstance().isTopAbility(missionId, name);
}

jint nativeClearAbilitiesAbove_impl(JNIEnv* env, jclass,
                                    jint missionId, jstring abilityName) {
    std::string name = jstr(env, abilityName);
    return OHAbilityManagerClient::getInstance().clearAbilitiesAbove(missionId, name);
}

jint nativeGetMissionIdForBundle_impl(JNIEnv* env, jclass, jstring bundleName) {
    std::string bundle = jstr(env, bundleName);
    return OHAbilityManagerClient::getInstance().getMissionIdForBundle(bundle);
}

const JNINativeMethod kMethods[] = {
    {"nativeGetOHAbilityManagerService", "()J",
        (void*)nativeGetOHAbilityManagerService_impl},
    {"nativeStartAbility",
        "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;JI)I",
        (void*)nativeStartAbility_impl},
    {"nativeStartAbilityInMission",
        "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;I)I",
        (void*)nativeStartAbilityInMission_impl},
    {"nativeCleanMission",         "(I)I",
        (void*)nativeCleanMission_impl},
    {"nativeMoveMissionToFront",   "(I)I",
        (void*)nativeMoveMissionToFront_impl},
    {"nativeIsTopAbility",
        "(ILjava/lang/String;)Z",
        (void*)nativeIsTopAbility_impl},
    {"nativeClearAbilitiesAbove",
        "(ILjava/lang/String;)I",
        (void*)nativeClearAbilitiesAbove_impl},
    {"nativeGetMissionIdForBundle",
        "(Ljava/lang/String;)I",
        (void*)nativeGetMissionIdForBundle_impl},
};

}  // namespace

int register_ActivityTaskManagerAdapter(JNIEnv* env) {
    jclass clazz = env->FindClass("adapter/activity/ActivityTaskManagerAdapter");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        LOGE("register_ActivityTaskManagerAdapter: FindClass returned null");
        return JNI_ERR;
    }
    jint rc = env->RegisterNatives(clazz, kMethods,
                                   sizeof(kMethods) / sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    if (rc != JNI_OK) {
        if (env->ExceptionCheck()) {
            env->ExceptionDescribe();
            env->ExceptionClear();
        }
        LOGE("register_ActivityTaskManagerAdapter: RegisterNatives failed rc=%d", (int)rc);
    } else {
        LOGI("register_ActivityTaskManagerAdapter: OK 8 methods");
    }
    return rc;
}
