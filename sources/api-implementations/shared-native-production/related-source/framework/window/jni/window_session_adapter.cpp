/*
 * window_session_adapter.cpp
 *
 * JNI registration for adapter.window.WindowSessionAdapter via RegisterNatives.
 * Replaces the legacy Java_adapter_window_WindowSessionAdapter_* exports
 * previously in framework/core/jni/adapter_bridge.cpp.
 *
 * Class:  adapter/window/WindowSessionAdapter  (BCP - oh-adapter-framework.jar)
 * Registered from adapter_bridge.cpp's JNI_OnLoad via
 *   register_WindowSessionAdapter(env).
 *
 * 15 natives: 9 session + 6 surface/buffer management.
 */

#include "adapter_bridge.h"
#include "oh_window_manager_client.h"
#include "oh_input_bridge.h"
#include "oh_surface_bridge.h"
#include "oh_graphic_buffer_producer.h"

#include <android/log.h>
#include <jni.h>
#include <string>
#include <surface.h>   // OHOS::Surface — explicit include needed so sptr<Surface>
                        // dtor (instantiated through oh_window_manager_client.h
                        // refbase chain) sees the complete type; without this
                        // refbase.h:928 errors with "incomplete type OHOS::Surface".

#define TAG "OH_WSAJNI"
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

// -------- session (9) --------

jlong nativeGetOHSessionService_impl(JNIEnv*, jclass) {
    return (jlong)&OHWindowManagerClient::getInstance();
}

// Spec: doc/window_manager_ipc_adapter_design.html §3.1.5.6.2
// Returns int[10]: {sessionId, surfaceNodeId, displayId, w, h, wsErrCode,
//                   frameLeft, frameTop, frameRight, frameBottom}.
// frame* is the actual OH window rect after AddWindow layout; on the legacy
// WMS path all successful windows end at the full requested display rect.
static jintArray doCreateSession(JNIEnv* env, jobject androidWindow,
                                 jstring bundleNameJ, jstring abilityNameJ,
                                 jstring moduleNameJ, jstring windowNameJ,
                                 jint androidWindowType, jint displayId,
                                 jint requestedWidth, jint requestedHeight,
                                 jint androidFlags,
                                 jlong ohTokenAddrJ) {
    std::string bundleName  = jstr(env, bundleNameJ);
    std::string abilityName = jstr(env, abilityNameJ);
    std::string moduleName  = jstr(env, moduleNameJ);
    std::string windowName  = jstr(env, windowNameJ);
    if (moduleName.empty()) moduleName = "entry";          // HAP default
    if (abilityName.empty()) abilityName = "MainAbility";
    if (windowName.empty()) windowName = "AndroidWindow";

    JavaVM* jvm = AdapterBridge::getInstance().getJavaVM();
    OHWindowSession session = OHWindowManagerClient::getInstance().createSession(
            jvm, androidWindow,
            bundleName, abilityName, moduleName, windowName,
            androidWindowType, displayId,
            requestedWidth, requestedHeight,
            static_cast<int32_t>(androidFlags),
            static_cast<uint64_t>(ohTokenAddrJ));

    jintArray result = env->NewIntArray(10);
    jint info[10] = {
        session.sessionId,
        session.surfaceNodeId,
        session.displayId,
        session.width,
        session.height,
        session.wsErr,
        session.frameLeft,
        session.frameTop,
        session.frameRight,
        session.frameBottom,
    };
    env->SetIntArrayRegion(result, 0, 10, info);
    return result;
}

// Helper for the legacy JNI signature: returns the old int[6] format so
// pre-change BCP jars still link and run.  The frame fields are dropped;
// legacy callers receive width/height as before.
static jintArray packLegacySession(JNIEnv* env, const OHWindowSession& session) {
    jintArray result = env->NewIntArray(6);
    jint info[6] = {
        session.sessionId,
        session.surfaceNodeId,
        session.displayId,
        session.width,
        session.height,
        session.wsErr,
    };
    env->SetIntArrayRegion(result, 0, 6, info);
    return result;
}

// New signature: passes Android LayoutParams.flags to native for mapping.
jintArray nativeCreateSession_impl(JNIEnv* env, jclass,
                                   jobject androidWindow,
                                   jstring bundleNameJ, jstring abilityNameJ,
                                   jstring moduleNameJ, jstring windowNameJ,
                                   jint androidWindowType, jint displayId,
                                   jint requestedWidth, jint requestedHeight,
                                   jint androidFlags,
                                   jlong ohTokenAddrJ) {
    return doCreateSession(env, androidWindow,
                           bundleNameJ, abilityNameJ, moduleNameJ, windowNameJ,
                           androidWindowType, displayId,
                           requestedWidth, requestedHeight,
                           androidFlags,
                           ohTokenAddrJ);
}

// Compatibility signature for pre-change BCP jars that do not pass flags.
// Registered alongside the new signature so mixed-version deployments tolerate
// either side being updated first.
//
// The legacy native behavior was to always perform the safe-area -> fullscreen
// transition (pre-set NEED_AVOID then clear it).  Preserve that default by
// passing FLAG_FULLSCREEN here, so old BCP jars continue to get fullscreen
// layout even though their Java signature cannot express attrs.flags.
static constexpr int32_t LEGACY_DEFAULT_FULLSCREEN_FLAG = 0x00000400; // FLAG_FULLSCREEN

jintArray nativeCreateSession_compat_impl(JNIEnv* env, jclass,
                                          jobject androidWindow,
                                          jstring bundleNameJ, jstring abilityNameJ,
                                          jstring moduleNameJ, jstring windowNameJ,
                                          jint androidWindowType, jint displayId,
                                          jint requestedWidth, jint requestedHeight,
                                          jlong ohTokenAddrJ) {
    JavaVM* jvm = AdapterBridge::getInstance().getJavaVM();
    OHWindowSession session = OHWindowManagerClient::getInstance().createSession(
            jvm, androidWindow,
            jstr(env, bundleNameJ), jstr(env, abilityNameJ),
            jstr(env, moduleNameJ), jstr(env, windowNameJ),
            androidWindowType, displayId,
            requestedWidth, requestedHeight,
            LEGACY_DEFAULT_FULLSCREEN_FLAG,
            static_cast<uint64_t>(ohTokenAddrJ));
    return packLegacySession(env, session);
}

jint nativeUpdateSessionRect_impl(JNIEnv*, jclass,
                                  jint sessionId, jint x, jint y,
                                  jint width, jint height) {
    return OHWindowManagerClient::getInstance().updateSessionRect(
            sessionId, x, y, width, height);
}

jint nativeNotifyDrawingCompleted_impl(JNIEnv*, jclass, jint sessionId) {
    LOGI("[Fn04.A13] JNI nativeNotifyDrawingCompleted session=%d", sessionId);
    return OHWindowManagerClient::getInstance().notifyDrawingCompleted(sessionId);
}

void nativeDestroySession_impl(JNIEnv*, jclass, jint sessionId) {
    OHWindowManagerClient::getInstance().destroySession(sessionId);
}

// 2026-05-19: visibility transition helpers — counterpart to AddWindow at
// session creation.  See oh_window_manager_client.cpp::hideWindow / showWindow
// for design alternatives (A/B/C/D) — adapter uses in-App-process C++ cache
// (Option D), idempotent at native layer.
jint nativeHideWindow_impl(JNIEnv*, jclass, jint sessionId) {
    return OHWindowManagerClient::getInstance().hideWindow(sessionId);
}

jint nativeShowWindow_impl(JNIEnv*, jclass, jint sessionId) {
    return OHWindowManagerClient::getInstance().showWindow(sessionId);
}

jlong nativeGetSurfaceNodeId_impl(JNIEnv*, jclass, jint sessionId) {
    return OHWindowManagerClient::getInstance().getSurfaceNodeId(sessionId);
}

jint nativeInjectTouchEvent_impl(JNIEnv*, jclass,
                                 jint sessionId, jint action,
                                 jfloat x, jfloat y,
                                 jlong downTime, jlong eventTime) {
    return OHInputBridge::getInstance().injectSyntheticTouchEvent(
            sessionId, action, x, y, downTime, eventTime);
}

// -------- surface / buffer (6) --------

jboolean nativeCreateOHSurface_impl(JNIEnv* env, jclass,
                                    jint sessionId, jstring windowName,
                                    jint width, jint height, jint format) {
    std::string name = jstr(env, windowName);
    bool result = OHSurfaceBridge::getInstance().createSurface(
            sessionId, name.c_str(), width, height, format);
    return (jboolean)result;
}

jlong nativeGetSurfaceHandle_impl(JNIEnv*, jclass,
                                  jint sessionId, jint width, jint height,
                                  jint format) {
    return OHSurfaceBridge::getInstance().getSurfaceHandle(
            sessionId, width, height, format);
}

void nativeNotifySurfaceDrawingCompleted_impl(JNIEnv*, jclass, jint sessionId) {
    LOGI("[Fn04.A13/A14] JNI nativeNotifySurfaceDrawingCompleted session=%d", sessionId);
    OHSurfaceBridge::getInstance().notifyDrawingCompleted(sessionId);
}

void nativeUpdateSurfaceSize_impl(JNIEnv*, jclass,
                                  jint sessionId, jint width, jint height) {
    OHSurfaceBridge::getInstance().updateSurfaceSize(sessionId, width, height);
}

void nativeDestroyOHSurface_impl(JNIEnv*, jclass, jint sessionId) {
    OHSurfaceBridge::getInstance().destroySurface(sessionId);
}

jintArray nativeDequeueBuffer_impl(JNIEnv* env, jclass,
                                   jlong producerHandle, jint width, jint height,
                                   jint format, jlong usage) {
    auto* producer = reinterpret_cast<OHGraphicBufferProducer*>(producerHandle);
    if (!producer) {
        LOGE("nativeDequeueBuffer: null producer handle");
        return nullptr;
    }
    int slot = -1, fenceFd = -1;
    int ret = producer->dequeueBuffer(&slot, &fenceFd, width, height, format, usage);
    if (ret != 0) {
        LOGE("nativeDequeueBuffer: dequeueBuffer failed (ret=%d)", ret);
        return nullptr;
    }
    int32_t bufWidth = 0, bufHeight = 0, stride = 0, bufFormat = 0;
    producer->getBufferInfo(slot, &bufWidth, &bufHeight, &stride, &bufFormat);
    int dmabufFd = producer->getBufferFd(slot);

    jintArray result = env->NewIntArray(6);
    jint info[6] = { slot, fenceFd, dmabufFd, bufWidth, bufHeight, stride };
    env->SetIntArrayRegion(result, 0, 6, info);
    return result;
}

jint nativeQueueBuffer_impl(JNIEnv*, jclass,
                            jlong producerHandle, jint slot, jint fenceFd,
                            jlong timestamp,
                            jint cropLeft, jint cropTop, jint cropRight,
                            jint cropBottom) {
    auto* producer = reinterpret_cast<OHGraphicBufferProducer*>(producerHandle);
    if (!producer) {
        LOGE("nativeQueueBuffer: null producer handle");
        return -1;
    }
    return producer->queueBuffer(slot, fenceFd, timestamp,
                                 cropLeft, cropTop, cropRight, cropBottom);
}

jint nativeCancelBuffer_impl(JNIEnv*, jclass,
                             jlong producerHandle, jint slot, jint fenceFd) {
    auto* producer = reinterpret_cast<OHGraphicBufferProducer*>(producerHandle);
    if (!producer) {
        LOGE("nativeCancelBuffer: null producer handle");
        return -1;
    }
    return producer->cancelBuffer(slot, fenceFd);
}

const JNINativeMethod kMethods[] = {
    // session
    {"nativeGetOHSessionService", "()J", (void*)nativeGetOHSessionService_impl},
    {"nativeCreateSession",
        "(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;IIIIIJ)[I",
        (void*)nativeCreateSession_impl},
    {"nativeCreateSession",
        "(Ljava/lang/Object;Ljava/lang/String;Ljava/lang/String;"
        "Ljava/lang/String;Ljava/lang/String;IIIIJ)[I",
        (void*)nativeCreateSession_compat_impl},
    {"nativeUpdateSessionRect",        "(IIIII)I",   (void*)nativeUpdateSessionRect_impl},
    {"nativeNotifyDrawingCompleted",   "(I)I",       (void*)nativeNotifyDrawingCompleted_impl},
    {"nativeDestroySession",           "(I)V",       (void*)nativeDestroySession_impl},
    {"nativeHideWindow",               "(I)I",       (void*)nativeHideWindow_impl},
    {"nativeShowWindow",               "(I)I",       (void*)nativeShowWindow_impl},
    {"nativeGetSurfaceNodeId",         "(I)J",       (void*)nativeGetSurfaceNodeId_impl},
    {"nativeInjectTouchEvent",         "(IIFFJJ)I",  (void*)nativeInjectTouchEvent_impl},

    // surface / buffer
    {"nativeCreateOHSurface",
        "(ILjava/lang/String;III)Z",
        (void*)nativeCreateOHSurface_impl},
    {"nativeGetSurfaceHandle",         "(IIII)J",    (void*)nativeGetSurfaceHandle_impl},
    {"nativeNotifySurfaceDrawingCompleted", "(I)V",  (void*)nativeNotifySurfaceDrawingCompleted_impl},
    {"nativeUpdateSurfaceSize",        "(III)V",     (void*)nativeUpdateSurfaceSize_impl},
    {"nativeDestroyOHSurface",         "(I)V",       (void*)nativeDestroyOHSurface_impl},
    {"nativeDequeueBuffer",            "(JIIIJ)[I",  (void*)nativeDequeueBuffer_impl},
    {"nativeQueueBuffer",              "(JIIJIIII)I",(void*)nativeQueueBuffer_impl},
    {"nativeCancelBuffer",             "(JII)I",     (void*)nativeCancelBuffer_impl},
};

}  // namespace

int register_WindowSessionAdapter(JNIEnv* env) {
    jclass clazz = env->FindClass("adapter/window/WindowSessionAdapter");
    if (!clazz) {
        if (env->ExceptionCheck()) env->ExceptionClear();
        LOGE("register_WindowSessionAdapter: FindClass returned null");
        return JNI_ERR;
    }
    // [S20 JNI-TOLERANT 2026-07-09] Register PER-METHOD instead of one
    // all-or-nothing RegisterNatives(kMethods, N) call.
    //
    // Root cause (S20, device truly-cold): the DEPLOYED jar 9cb1a0ee is older
    // than this tree's kMethods table; at least one newer method here is absent
    // from the deployed WindowSessionAdapter class. A single RegisterNatives call
    // is all-or-nothing — one missing method aborts the WHOLE call, leaving even
    // nativeCreateOHSurface unregistered -> UnsatisfiedLinkError at
    // ViewRootImpl.relayout (right after CreateWindow windowId succeeds), before
    // getOhNativeWindow. The monolithic bridge 048b7576 exported per-method Java_*
    // symbols (auto-linked individually), so a missing method never broke the
    // others. Registering one method at a time restores that tolerance: every
    // method the deployed jar DOES declare (incl. nativeCreateOHSurface) binds;
    // methods it lacks are skipped harmlessly. All bind to THIS bridge's
    // OHWindowManagerClient (runtime 8394d433 has no WindowSessionAdapter natives),
    // so no split-brain.
    const int n = static_cast<int>(sizeof(kMethods) / sizeof(kMethods[0]));
    int okCount = 0, failCount = 0;
    for (int i = 0; i < n; ++i) {
        jint rc = env->RegisterNatives(clazz, &kMethods[i], 1);
        if (rc != JNI_OK) {
            if (env->ExceptionCheck()) env->ExceptionClear();
            ++failCount;
        } else {
            ++okCount;
        }
    }
    env->DeleteLocalRef(clazz);
    LOGI("register_WindowSessionAdapter: per-method OK=%d skipped=%d (of %d)",
         okCount, failCount, n);
    return JNI_OK;
}
