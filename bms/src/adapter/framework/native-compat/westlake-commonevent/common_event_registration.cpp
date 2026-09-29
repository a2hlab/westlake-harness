// Five CommonEvent JNI methods copied from Westlake (oc-t4 f6a60fc0).
// The retained 84695d62 bridge already implements OHCommonEventClient.
// Register only this family: an unrelated optional ability native in older
// all-in-one tables can abort registration before these entries are reached.
#include "oh_common_event_client.h"
#include <jni.h>
#include <cstdio>
using namespace oh_adapter;
namespace {
std::string jstr(JNIEnv* env, jstring s) {
    if (!s) return "";
    const char* raw = env->GetStringUTFChars(s, nullptr);
    std::string result(raw);
    env->ReleaseStringUTFChars(s, raw);
    return result;
}

// -------- ability (5) --------

std::vector<std::string> jstrArr(JNIEnv* env, jobjectArray arr) {
    std::vector<std::string> out;
    if (!arr) return out;
    int count = env->GetArrayLength(arr);
    for (int i = 0; i < count; ++i) {
        jstring s = (jstring)env->GetObjectArrayElement(arr, i);
        out.push_back(jstr(env, s));
        if (s) env->DeleteLocalRef(s);
    }
    return out;
}

jint nativeSubscribeCommonEvent_impl(JNIEnv* env, jclass,
                                     jint subscriptionId, jobjectArray ohEventNames,
                                     jint priority, jstring permission) {
    auto events = jstrArr(env, ohEventNames);
    std::string perm = jstr(env, permission);
    return OHCommonEventClient::getInstance().subscribe(
            subscriptionId, events, priority, perm);
}

jint nativeUnsubscribeCommonEvent_impl(JNIEnv*, jclass, jint subscriptionId) {
    return OHCommonEventClient::getInstance().unsubscribe(subscriptionId);
}

jint nativePublishCommonEvent_impl(JNIEnv* env, jclass,
                                   jstring ohAction, jstring extrasJson, jstring uri,
                                   jint code, jstring data,
                                   jboolean ordered, jboolean sticky,
                                   jobjectArray subscriberPermissions) {
    std::string action = jstr(env, ohAction);
    std::string extras = jstr(env, extrasJson);
    std::string uriStr = jstr(env, uri);
    std::string dataStr = jstr(env, data);
    auto permissions = jstrArr(env, subscriberPermissions);
    return OHCommonEventClient::getInstance().publish(
            action, extras, uriStr, code, dataStr, ordered, sticky, permissions);
}

jint nativeFinishCommonEvent_impl(JNIEnv* env, jclass,
                                  jint subscriptionId, jint resultCode,
                                  jstring resultData, jboolean abortEvent) {
    std::string data = jstr(env, resultData);
    return OHCommonEventClient::getInstance().finishReceiver(
            subscriptionId, resultCode, data, abortEvent);
}

jstring nativeGetStickyCommonEvent_impl(JNIEnv* env, jclass, jstring ohEventName) {
    std::string event = jstr(env, ohEventName);
    std::string result = OHCommonEventClient::getInstance().getStickyEvent(event);
    if (result.empty()) return nullptr;
    return env->NewStringUTF(result.c_str());
}

const JNINativeMethod kMethods[] = {
    // broadcast
    {"nativeSubscribeCommonEvent",
        "(I[Ljava/lang/String;ILjava/lang/String;)I",
        (void*)nativeSubscribeCommonEvent_impl},
    {"nativeUnsubscribeCommonEvent", "(I)I",
        (void*)nativeUnsubscribeCommonEvent_impl},
    {"nativePublishCommonEvent",
        "(Ljava/lang/String;Ljava/lang/String;Ljava/lang/String;"
        "ILjava/lang/String;ZZ[Ljava/lang/String;)I",
        (void*)nativePublishCommonEvent_impl},
    {"nativeFinishCommonEvent",
        "(IILjava/lang/String;Z)I",
        (void*)nativeFinishCommonEvent_impl},
    {"nativeGetStickyCommonEvent",
        "(Ljava/lang/String;)Ljava/lang/String;",
        (void*)nativeGetStickyCommonEvent_impl},
};
}
namespace android {
int register_westlake_CommonEvent(JNIEnv* env) {
    jclass clazz = env->FindClass("adapter/activity/ActivityManagerAdapter");
    if (clazz == nullptr) return JNI_ERR;
    const jint rc = env->RegisterNatives(clazz, kMethods, sizeof(kMethods)/sizeof(kMethods[0]));
    env->DeleteLocalRef(clazz);
    fprintf(stderr, "[WL-COMMONEVENT] RegisterNatives 5 methods rc=%d\n", rc);
    return rc;
}
}
