/*
 * session_stage_adapter.cpp
 *
 * Implementation of SessionStageAdapter.
 * Bridges OH ISessionStage callbacks to Android IWindow via JNI.
 */

#include "session_stage_adapter.h"
#include "adapter_bridge.h"
#include "westlake_jni_attach_admission.h"

#include <android/log.h>
#include <cstdarg>

#include "oh_br_trace.h"   // G2.14ac IPC trace+log macros

#define LOG_TAG "OH_SessionStageAdapter"
#define ALOGD(...) __android_log_print(ANDROID_LOG_DEBUG, LOG_TAG, __VA_ARGS__)
#define ALOGI(...) __android_log_print(ANDROID_LOG_INFO,  LOG_TAG, __VA_ARGS__)
#define ALOGW(...) __android_log_print(ANDROID_LOG_WARN,  LOG_TAG, __VA_ARGS__)
#define ALOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)

using namespace OHOS::Rosen;
using WSError = OHOS::Rosen::WSError;
using WSErrorCode = OHOS::Rosen::WSErrorCode;
using WMError = OHOS::Rosen::WMError;

namespace oh_adapter {

// ================================================================
// Construction / Destruction
// ================================================================

SessionStageAdapter::SessionStageAdapter(JavaVM* jvm, jobject androidWindow)
    : jvm_(jvm)
{
    ALOGI("SessionStageAdapter created");

    westlake::jni::ScopedJniAttachment attachment(
        jvm_, "OH_SessionStageAdapter");
    JNIEnv* env = attachment.env();
    if (!env) {
        ALOGE("Failed to get JNIEnv in constructor");
        return;
    }

    androidWindow_ = env->NewGlobalRef(androidWindow);

    jclass localBridgeClass = env->FindClass(
        "adapter/window/SessionStageBridge");
    if (!localBridgeClass) {
        ALOGE("Failed to find SessionStageBridge class");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }
    bridgeClass_ = reinterpret_cast<jclass>(env->NewGlobalRef(localBridgeClass));
    env->DeleteLocalRef(localBridgeClass);

    jmethodID ctor = env->GetMethodID(bridgeClass_, "<init>",
        "(Ljava/lang/Object;)V");
    if (!ctor) {
        ALOGE("Failed to find SessionStageBridge constructor");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }

    jobject localBridgeObj = env->NewObject(bridgeClass_, ctor, androidWindow_);
    if (!localBridgeObj) {
        ALOGE("Failed to create SessionStageBridge instance");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }
    bridgeObj_ = env->NewGlobalRef(localBridgeObj);
    env->DeleteLocalRef(localBridgeObj);

    // SessionStageBridge does not project OH focus into ViewRootImpl.  Reuse
    // the already shipped WindowCallbackBridge, whose public callback follows
    // the Android window-focus path used by UnityPlayer.
    jclass localFocusBridgeClass = env->FindClass(
        "adapter/window/WindowCallbackBridge");
    if (!localFocusBridgeClass) {
        ALOGE("Failed to find WindowCallbackBridge class");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }
    focusBridgeClass_ = reinterpret_cast<jclass>(
        env->NewGlobalRef(localFocusBridgeClass));
    env->DeleteLocalRef(localFocusBridgeClass);

    jmethodID focusCtor = env->GetMethodID(focusBridgeClass_, "<init>",
        "(Ljava/lang/Object;)V");
    if (!focusCtor) {
        ALOGE("Failed to find WindowCallbackBridge constructor");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }

    jobject localFocusBridgeObj = env->NewObject(
        focusBridgeClass_, focusCtor, androidWindow_);
    if (!localFocusBridgeObj) {
        ALOGE("Failed to create WindowCallbackBridge instance");
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }
    focusBridgeObj_ = env->NewGlobalRef(localFocusBridgeObj);
    env->DeleteLocalRef(localFocusBridgeObj);

    ALOGI("SessionStageAdapter initialized successfully");
}

SessionStageAdapter::~SessionStageAdapter()
{
    ALOGI("SessionStageAdapter destroyed");

    westlake::jni::ScopedJniAttachment attachment(
        jvm_, "OH_SessionStageAdapter");
    JNIEnv* env = attachment.env();
    if (env) {
        if (androidWindow_) { env->DeleteGlobalRef(androidWindow_); androidWindow_ = nullptr; }
        if (bridgeObj_)     { env->DeleteGlobalRef(bridgeObj_);     bridgeObj_     = nullptr; }
        if (bridgeClass_)   { env->DeleteGlobalRef(bridgeClass_);   bridgeClass_   = nullptr; }
        if (focusBridgeObj_) {
            env->DeleteGlobalRef(focusBridgeObj_);
            focusBridgeObj_ = nullptr;
        }
        if (focusBridgeClass_) {
            env->DeleteGlobalRef(focusBridgeClass_);
            focusBridgeClass_ = nullptr;
        }
    }
}

void SessionStageAdapter::SetInheritsParentFocus(bool inheritsParentFocus)
{
    std::lock_guard<std::mutex> lock(jniMutex_);
    inheritsParentFocus_ = inheritsParentFocus;
}

bool SessionStageAdapter::EnableRootBlastForTopLevelContent()
{
    OH_BR_IPC_SCOPE("SessionStage.EnableRootBlast", "");

    std::lock_guard<std::mutex> lock(jniMutex_);
    westlake::jni::ScopedJniAttachment attachment(
        jvm_, "OH_SessionStageAdapter.EnableRootBlast");
    JNIEnv* env = attachment.env();
    if (!env || !androidWindow_) {
        ALOGE("EnableRootBlast: missing JNIEnv or Android IWindow");
        return false;
    }

    bool enabled = false;
    jclass windowClass = nullptr;
    jobject weakViewRoot = nullptr;
    jclass weakReferenceClass = nullptr;
    jobject viewRoot = nullptr;
    jclass viewRootClass = nullptr;

    windowClass = env->GetObjectClass(androidWindow_);
    if (!windowClass) {
        ALOGE("EnableRootBlast: Android IWindow class unavailable");
        goto cleanup;
    }

    {
        jfieldID viewAncestorField = env->GetFieldID(windowClass, "mViewAncestor",
            "Ljava/lang/ref/WeakReference;");
        if (!viewAncestorField) {
            ALOGE("EnableRootBlast: ViewRootImpl.W.mViewAncestor unavailable");
            goto cleanup;
        }
        weakViewRoot = env->GetObjectField(androidWindow_, viewAncestorField);
    }
    if (!weakViewRoot) {
        ALOGE("EnableRootBlast: ViewRootImpl weak reference is null");
        goto cleanup;
    }

    weakReferenceClass = env->FindClass("java/lang/ref/WeakReference");
    if (!weakReferenceClass) {
        ALOGE("EnableRootBlast: WeakReference class unavailable");
        goto cleanup;
    }
    {
        jmethodID getMethod = env->GetMethodID(weakReferenceClass, "get",
            "()Ljava/lang/Object;");
        if (!getMethod) {
            ALOGE("EnableRootBlast: WeakReference.get unavailable");
            goto cleanup;
        }
        viewRoot = env->CallObjectMethod(weakViewRoot, getMethod);
    }
    if (env->ExceptionCheck() || !viewRoot) {
        ALOGE("EnableRootBlast: ViewRootImpl is unavailable");
        goto cleanup;
    }

    viewRootClass = env->GetObjectClass(viewRoot);
    if (!viewRootClass) {
        ALOGE("EnableRootBlast: ViewRootImpl class unavailable");
        goto cleanup;
    }
    {
        jfieldID useBlastField = env->GetFieldID(viewRootClass,
            "mUseBLASTAdapter", "Z");
        if (!useBlastField) {
            ALOGE("EnableRootBlast: ViewRootImpl.mUseBLASTAdapter unavailable");
            goto cleanup;
        }
        const jboolean wasEnabled = env->GetBooleanField(viewRoot, useBlastField);
        env->SetBooleanField(viewRoot, useBlastField, JNI_TRUE);
        if (!env->ExceptionCheck()) {
            enabled = env->GetBooleanField(viewRoot, useBlastField) == JNI_TRUE;
            ALOGI("EnableRootBlast: mUseBLASTAdapter %{public}s -> %{public}s",
                wasEnabled == JNI_TRUE ? "true" : "false",
                enabled ? "true" : "false");
        }
    }

cleanup:
    if (env->ExceptionCheck()) {
        ALOGE("EnableRootBlast: clearing JNI exception");
        env->ExceptionClear();
    }
    if (viewRootClass) env->DeleteLocalRef(viewRootClass);
    if (viewRoot) env->DeleteLocalRef(viewRoot);
    if (weakReferenceClass) env->DeleteLocalRef(weakReferenceClass);
    if (weakViewRoot) env->DeleteLocalRef(weakViewRoot);
    if (windowClass) env->DeleteLocalRef(windowClass);
    return enabled;
}

// ================================================================
// Category 1: Session Lifecycle
// ================================================================

WSError SessionStageAdapter::SetActive(bool active)
{
    OH_BR_IPC_SCOPE("SessionStage.SetActive", "active=%{public}d", static_cast<int>(active));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onSetActive", "(Z)V", static_cast<jboolean>(active));
    if (inheritsParentFocus_) {
        OH_BR_IPC_SCOPE("SessionStage.InheritedParentFocus",
                        "focused=%{public}d", static_cast<int>(active));
        callFocusBridgeVoidMethod("onUpdateFocusStatus", "(Z)V",
            static_cast<jboolean>(active));
    }

    return WSError::WS_OK;
}

void SessionStageAdapter::NotifySessionForeground(uint32_t reason, bool withAnimation)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifySessionForeground",
                    "reason=%{public}u anim=%{public}d", reason, static_cast<int>(withAnimation));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifySessionForeground", "(IZ)V",
        static_cast<jint>(reason), static_cast<jboolean>(withAnimation));
}

void SessionStageAdapter::NotifySessionBackground(
    uint32_t reason, bool withAnimation, bool /*isFromInnerkits*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifySessionBackground",
                    "reason=%{public}u anim=%{public}d", reason, static_cast<int>(withAnimation));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifySessionBackground", "(IZ)V",
        static_cast<jint>(reason), static_cast<jboolean>(withAnimation));
}

WSError SessionStageAdapter::NotifyDestroy()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyDestroy", "");

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifyDestroy", "()V");

    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyWindowVisibility(bool isVisible)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyWindowVisibility",
                    "isVisible=%{public}d", static_cast<int>(isVisible));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifyWindowVisibility", "(Z)V",
        static_cast<jboolean>(isVisible));

    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyWindowOcclusionState(const WindowVisibilityState state)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyWindowOcclusionState",
                    "state=%{public}d (OH_ONLY)", static_cast<int>(state));
    return WSError::WS_OK;
}

void SessionStageAdapter::NotifyForegroundInteractiveStatus(bool interactive)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyForegroundInteractiveStatus",
                    "interactive=%{public}d", static_cast<int>(interactive));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifyForegroundInteractiveStatus", "(Z)V",
        static_cast<jboolean>(interactive));
}

void SessionStageAdapter::NotifyLifecyclePausedStatus()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyLifecyclePausedStatus",
                    "(OH_ONLY: Android uses Activity.onPause)");
}

// ================================================================
// Category 2: Window Geometry
// ================================================================

WSError SessionStageAdapter::UpdateRect(const WSRect& rect, SizeChangeReason reason,
    const SceneAnimationConfig& /*config*/,
    const std::map<AvoidAreaType, AvoidArea>& /*avoidAreas*/)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateRect",
                    "rect=[%{public}d,%{public}d,%{public}d,%{public}d] reason=%{public}d",
                    rect.posX_, rect.posY_, rect.width_, rect.height_,
                    static_cast<int>(reason));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateRect", "(IIIII)V",
        static_cast<jint>(rect.posX_),
        static_cast<jint>(rect.posY_),
        static_cast<jint>(rect.width_),
        static_cast<jint>(rect.height_),
        static_cast<jint>(reason));

    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateGlobalDisplayRectFromServer(
    const WSRect& rect, SizeChangeReason reason)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateGlobalDisplayRectFromServer",
                    "rect=[%{public}d,%{public}d,%{public}d,%{public}d] reason=%{public}d",
                    rect.posX_, rect.posY_, rect.width_, rect.height_,
                    static_cast<int>(reason));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateGlobalDisplayRectFromServer", "(IIIII)V",
        static_cast<jint>(rect.posX_),
        static_cast<jint>(rect.posY_),
        static_cast<jint>(rect.width_),
        static_cast<jint>(rect.height_),
        static_cast<jint>(reason));

    return WSError::WS_OK;
}

// ================================================================
// Category 3: Window Mode
// ================================================================

WSError SessionStageAdapter::UpdateWindowMode(WindowMode mode)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateWindowMode", "mode=%{public}d", static_cast<int>(mode));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateWindowMode", "(I)V", static_cast<jint>(mode));

    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateMaximizeMode(MaximizeMode mode)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateMaximizeMode",
                    "mode=%{public}d (OH_ONLY)", static_cast<int>(mode));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyLayoutFinishAfterWindowModeChange(WindowMode mode)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyLayoutFinishAfterWindowModeChange",
                    "mode=%{public}d (OH_ONLY)", static_cast<int>(mode));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SwitchFreeMultiWindow(bool enable)
{
    OH_BR_IPC_SCOPE("SessionStage.SwitchFreeMultiWindow",
                    "enable=%{public}d (OH_ONLY)", static_cast<int>(enable));
    return WSError::WS_OK;
}

// ================================================================
// Category 4: Focus
// ================================================================

WSError SessionStageAdapter::UpdateFocus(
    const OHOS::sptr<FocusNotifyInfo>& /*focusNotifyInfo*/, bool isFocused)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateFocus",
                    "isFocused=%{public}d", static_cast<int>(isFocused));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callFocusBridgeVoidMethod("onUpdateFocusStatus", "(Z)V",
        static_cast<jboolean>(isFocused));

    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyHighlightChange(
    const OHOS::sptr<HighlightNotifyInfo>& /*highlightNotifyInfo*/, bool isHighlight)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyHighlightChange",
                    "isHighlight=%{public}d (OH_ONLY)", static_cast<int>(isHighlight));
    return WSError::WS_OK;
}

// ================================================================
// Category 5: Avoid Area / Insets
// ================================================================

WSError SessionStageAdapter::UpdateAvoidArea(
    const OHOS::sptr<AvoidArea>& avoidArea, AvoidAreaType type)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateAvoidArea",
                    "type=%{public}d", static_cast<int>(type));

    if (!avoidArea) {
        ALOGW("UpdateAvoidArea: avoidArea is null");
        return WSError::WS_ERROR_NULLPTR;
    }

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateAvoidArea", "(IIIII)V",
        static_cast<jint>(type),
        static_cast<jint>(avoidArea->topRect_.posX_),
        static_cast<jint>(avoidArea->topRect_.posY_),
        static_cast<jint>(avoidArea->bottomRect_.posX_ + avoidArea->bottomRect_.width_),
        static_cast<jint>(avoidArea->bottomRect_.posY_ + avoidArea->bottomRect_.height_));

    return WSError::WS_OK;
}

void SessionStageAdapter::NotifyOccupiedAreaChangeInfo(
    OHOS::sptr<OccupiedAreaChangeInfo> info,
    const std::shared_ptr<RSTransaction>& /*rsTransaction*/,
    const Rect& /*callingSessionRect*/,
    const std::map<AvoidAreaType, AvoidArea>& /*avoidAreas*/)
{
    int occupiedHeight = 0;
    if (info) {
        occupiedHeight = info->rect_.height_;
    }
    OH_BR_IPC_SCOPE("SessionStage.NotifyOccupiedAreaChangeInfo",
                    "imeHeight=%{public}d", occupiedHeight);

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onNotifyOccupiedAreaChangeInfo", "(I)V",
        static_cast<jint>(occupiedHeight));
}

// ================================================================
// Category 6: Back Event
// ================================================================

WSError SessionStageAdapter::HandleBackEvent()
{
    OH_BR_IPC_SCOPE("SessionStage.HandleBackEvent", "");

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onHandleBackEvent", "()V");

    return WSError::WS_OK;
}

// ================================================================
// Category 7: Input Events
// ================================================================

WSError SessionStageAdapter::MarkProcessed(int32_t eventId)
{
    OH_BR_IPC_SCOPE("SessionStage.MarkProcessed",
                    "eventId=%{public}d (OH_ONLY)", eventId);
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyTouchOutside()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyTouchOutside", "(OH_ONLY)");
    return WSError::WS_OK;
}

// ================================================================
// Category 8: Display / Density / Orientation
// ================================================================

void SessionStageAdapter::UpdateDensity()
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateDensity", "");

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateDensity", "()V");
}

WSError SessionStageAdapter::UpdateOrientation()
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateOrientation", "");

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateOrientation", "()V");

    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateDisplayId(uint64_t displayId)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateDisplayId",
                    "displayId=%{public}llu", static_cast<unsigned long long>(displayId));

    std::lock_guard<std::mutex> lock(jniMutex_);
    callBridgeVoidMethod("onUpdateDisplayId", "(J)V", static_cast<jlong>(displayId));

    return WSError::WS_OK;
}

void SessionStageAdapter::NotifyDisplayMove(DisplayId from, DisplayId to)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyDisplayMove",
                    "from=%{public}llu to=%{public}llu (OH_ONLY)",
                    static_cast<unsigned long long>(from),
                    static_cast<unsigned long long>(to));
}

WSError SessionStageAdapter::UpdateSessionViewportConfig(const SessionViewportConfig& /*config*/)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateSessionViewportConfig", "(OH_ONLY)");
    return WSError::WS_OK;
}

// ================================================================
// Category 9: PiP
// ================================================================

WSError SessionStageAdapter::SetPipActionEvent(const std::string& action, int32_t status)
{
    OH_BR_IPC_SCOPE("SessionStage.SetPipActionEvent",
                    "action=%{public}s status=%{public}d (OH_ONLY)", action.c_str(), status);
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyPipWindowSizeChange(double width, double height, double scale)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyPipWindowSizeChange",
                    "w=%{public}f h=%{public}f s=%{public}f (OH_ONLY)", width, height, scale);
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyPiPActiveStatusChange(bool status)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyPiPActiveStatusChange",
                    "status=%{public}d (OH_ONLY)", static_cast<int>(status));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SetPiPControlEvent(
    WsPiPControlType controlType, WsPiPControlStatus status)
{
    OH_BR_IPC_SCOPE("SessionStage.SetPiPControlEvent",
                    "type=%{public}d status=%{public}d (OH_ONLY)",
                    static_cast<int>(controlType), static_cast<int>(status));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyCloseExistPipWindow()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyCloseExistPipWindow", "(OH_ONLY)");
    return WSError::WS_OK;
}

// ================================================================
// Category 10: Rotation
// ================================================================

WSError SessionStageAdapter::SetCurrentRotation(int32_t currentRotation)
{
    OH_BR_IPC_SCOPE("SessionStage.SetCurrentRotation",
                    "rotation=%{public}d (OH_ONLY)", currentRotation);
    return WSError::WS_OK;
}

// ================================================================
// Category 11: Screenshot
// ================================================================

void SessionStageAdapter::NotifyScreenshot()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyScreenshot", "(OH_ONLY)");
}

WSError SessionStageAdapter::NotifyScreenshotAppEvent(ScreenshotEventType type)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyScreenshotAppEvent",
                    "type=%{public}d (OH_ONLY)", static_cast<int>(type));
    return WSError::WS_OK;
}

// ================================================================
// Category 12: Extension / Component Data
// ================================================================

WSError SessionStageAdapter::NotifyTransferComponentData(
    const OHOS::AAFwk::WantParams& /*wantParams*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyTransferComponentData", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSErrorCode SessionStageAdapter::NotifyTransferComponentDataSync(
    const OHOS::AAFwk::WantParams& /*wantParams*/,
    OHOS::AAFwk::WantParams& /*reWantParams*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyTransferComponentDataSync", "(OH_ONLY)");
    return WSErrorCode::WS_OK;
}

WSError SessionStageAdapter::NotifyExtensionSecureLimitChange(bool isLimit)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyExtensionSecureLimitChange",
                    "isLimit=%{public}d (OH_ONLY)", static_cast<int>(isLimit));
    return WSError::WS_OK;
}

// ================================================================
// Category 13: Debug / Diagnostic
// ================================================================

void SessionStageAdapter::DumpSessionElementInfo(const std::vector<std::string>& params)
{
    OH_BR_IPC_SCOPE("SessionStage.DumpSessionElementInfo",
                    "paramCount=%{public}zu (OH_ONLY)", params.size());
}

WMError SessionStageAdapter::GetRouterStackInfo(std::string& routerStackInfo)
{
    OH_BR_IPC_SCOPE("SessionStage.GetRouterStackInfo", "(OH_ONLY)");
    routerStackInfo = "{}";
    return WMError::WM_OK;
}

WSError SessionStageAdapter::GetTopNavDestinationName(std::string& topNavDestName)
{
    OH_BR_IPC_SCOPE("SessionStage.GetTopNavDestinationName", "(OH_ONLY)");
    topNavDestName = "";
    return WSError::WS_OK;
}

// ================================================================
// Category 14: Transform / UI
// ================================================================

void SessionStageAdapter::NotifyTransformChange(const Transform& /*transform*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyTransformChange", "(OH_ONLY)");
}

void SessionStageAdapter::NotifySingleHandTransformChange(
    const SingleHandTransform& /*singleHandTransform*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifySingleHandTransformChange", "(OH_ONLY)");
}

WSError SessionStageAdapter::NotifyDialogStateChange(bool isForeground)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyDialogStateChange",
                    "isForeground=%{public}d (OH_ONLY)", static_cast<int>(isForeground));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateTitleInTargetPos(bool isShow, int32_t height)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateTitleInTargetPos",
                    "show=%{public}d height=%{public}d (OH_ONLY)", static_cast<int>(isShow), height);
    return WSError::WS_OK;
}

// ================================================================
// Category 15: Remaining OH_ONLY methods
// ================================================================

WSError SessionStageAdapter::NotifyAppForceLandscapeConfigUpdated()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyAppForceLandscapeConfigUpdated", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyAppForceLandscapeConfigEnableUpdated()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyAppForceLandscapeConfigEnableUpdated", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifyAppHookWindowInfoUpdated()
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyAppHookWindowInfoUpdated", "(OH_ONLY)");
    return WSError::WS_OK;
}

void SessionStageAdapter::NotifyAppUseControlStatus(bool isUseControl)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyAppUseControlStatus",
                    "isUseControl=%{public}d (OH_ONLY)", static_cast<int>(isUseControl));
}

void SessionStageAdapter::SetUniqueVirtualPixelRatio(bool useUniqueDensity, float virtualPixelRatio)
{
    OH_BR_IPC_SCOPE("SessionStage.SetUniqueVirtualPixelRatio",
                    "unique=%{public}d ratio=%{public}f (OH_ONLY)",
                    static_cast<int>(useUniqueDensity), virtualPixelRatio);
}

void SessionStageAdapter::UpdateAnimationSpeed(float speed)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateAnimationSpeed",
                    "speed=%{public}f (OH_ONLY)", speed);
}

WSError SessionStageAdapter::GetUIContentRemoteObj(
    OHOS::sptr<OHOS::IRemoteObject>& uiContentRemoteObj)
{
    OH_BR_IPC_SCOPE("SessionStage.GetUIContentRemoteObj", "(OH_ONLY)");
    uiContentRemoteObj = nullptr;
    return WSError::WS_OK;
}

WSError SessionStageAdapter::LinkKeyFrameNode()
{
    OH_BR_IPC_SCOPE("SessionStage.LinkKeyFrameNode", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SetStageKeyFramePolicy(const KeyFramePolicy& /*keyFramePolicy*/)
{
    OH_BR_IPC_SCOPE("SessionStage.SetStageKeyFramePolicy", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SetSplitButtonVisible(bool isVisible)
{
    OH_BR_IPC_SCOPE("SessionStage.SetSplitButtonVisible",
                    "isVisible=%{public}d (OH_ONLY)", static_cast<int>(isVisible));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SetEnableDragBySystem(bool dragEnable)
{
    OH_BR_IPC_SCOPE("SessionStage.SetEnableDragBySystem",
                    "dragEnable=%{public}d (OH_ONLY)", static_cast<int>(dragEnable));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SetDragActivated(bool dragActivated)
{
    OH_BR_IPC_SCOPE("SessionStage.SetDragActivated",
                    "dragActivated=%{public}d (OH_ONLY)", static_cast<int>(dragActivated));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::SendContainerModalEvent(
    const std::string& eventName, const std::string& eventValue)
{
    OH_BR_IPC_SCOPE("SessionStage.SendContainerModalEvent",
                    "name=%{public}s value=%{public}s (OH_ONLY)",
                    eventName.c_str(), eventValue.c_str());
    return WSError::WS_OK;
}

void SessionStageAdapter::NotifyWindowCrossAxisChange(CrossAxisState state)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifyWindowCrossAxisChange",
                    "state=%{public}d (OH_ONLY)", static_cast<int>(state));
}

WSError SessionStageAdapter::SendFbActionEvent(const std::string& action)
{
    OH_BR_IPC_SCOPE("SessionStage.SendFbActionEvent",
                    "action=%{public}s (OH_ONLY)", action.c_str());
    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateIsShowDecorInFreeMultiWindow(bool isShow)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateIsShowDecorInFreeMultiWindow",
                    "isShow=%{public}d (OH_ONLY)", static_cast<int>(isShow));
    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateBrightness(float brightness)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateBrightness",
                    "brightness=%{public}f (OH_ONLY)", brightness);
    return WSError::WS_OK;
}

WMError SessionStageAdapter::UpdateWindowModeForUITest(int32_t updateMode)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateWindowModeForUITest",
                    "updateMode=%{public}d (OH_ONLY)", updateMode);
    return WMError::WM_OK;
}

// ================================================================
// JNI Helpers
// ================================================================

void SessionStageAdapter::callBridgeVoidMethod(
    const char* methodName, const char* signature, ...)
{
    if (!bridgeObj_ || !bridgeClass_) {
        ALOGW("callBridgeVoidMethod(%s): bridge not initialized", methodName);
        return;
    }

    westlake::jni::ScopedJniAttachment attachment(
        jvm_, "OH_SessionStageAdapter");
    JNIEnv* env = attachment.env();
    if (!env) {
        ALOGE("callBridgeVoidMethod(%s): failed to get JNIEnv", methodName);
        return;
    }

    jmethodID method = env->GetMethodID(bridgeClass_, methodName, signature);
    if (!method) {
        ALOGE("callBridgeVoidMethod: method %s%s not found", methodName, signature);
        env->ExceptionClear();
        return;
    }

    va_list args;
    va_start(args, signature);
    env->CallVoidMethodV(bridgeObj_, method, args);
    va_end(args);

    if (env->ExceptionCheck()) {
        ALOGE("callBridgeVoidMethod(%s): Java exception occurred", methodName);
        env->ExceptionDescribe();
        env->ExceptionClear();
    }

}

void SessionStageAdapter::callFocusBridgeVoidMethod(
    const char* methodName, const char* signature, ...)
{
    if (!focusBridgeObj_ || !focusBridgeClass_) {
        ALOGW("callFocusBridgeVoidMethod(%s): focus bridge not initialized", methodName);
        return;
    }

    westlake::jni::ScopedJniAttachment attachment(
        jvm_, "OH_SessionStageAdapter.Focus");
    JNIEnv* env = attachment.env();
    if (!env) {
        ALOGE("callFocusBridgeVoidMethod(%s): failed to get JNIEnv", methodName);
        return;
    }

    jmethodID method = env->GetMethodID(focusBridgeClass_, methodName, signature);
    if (!method) {
        ALOGE("callFocusBridgeVoidMethod: method %s%s not found", methodName, signature);
        if (env->ExceptionCheck()) env->ExceptionClear();
        return;
    }

    va_list args;
    va_start(args, signature);
    env->CallVoidMethodV(focusBridgeObj_, method, args);
    va_end(args);

    if (env->ExceptionCheck()) {
        ALOGE("callFocusBridgeVoidMethod(%s): Java exception occurred", methodName);
        env->ExceptionDescribe();
        env->ExceptionClear();
    }
}

// ================================================================
// V7-only newly added pure virtuals — no-op OH_ONLY (no Android counterpart)
// ================================================================

WSError SessionStageAdapter::NotifySubWindowAfterParentWindowSizeChange(OHOS::Rosen::Rect /*rect*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifySubWindowAfterParentWindowSizeChange", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::NotifySubWindowAfterParentWindowStatusChange(OHOS::Rosen::WindowMode /*mode*/)
{
    OH_BR_IPC_SCOPE("SessionStage.NotifySubWindowAfterParentWindowStatusChange", "(OH_ONLY)");
    return WSError::WS_OK;
}

WSError SessionStageAdapter::GetSceneNodeCount(uint32_t& nodeCount)
{
    OH_BR_IPC_SCOPE("SessionStage.GetSceneNodeCount", "(OH_ONLY)");
    nodeCount = 0;
    return WSError::WS_OK;
}

WSError SessionStageAdapter::UpdateAppHookWindowInfo(const OHOS::Rosen::HookWindowInfo& /*hookWindowInfo*/)
{
    OH_BR_IPC_SCOPE("SessionStage.UpdateAppHookWindowInfo", "(OH_ONLY)");
    return WSError::WS_OK;
}

}  // namespace oh_adapter
