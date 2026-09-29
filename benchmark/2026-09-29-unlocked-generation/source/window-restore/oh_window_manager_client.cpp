/*
 * oh_window_manager_client.cpp
 *
 * OpenHarmony WindowManager / SceneSessionManager IPC client implementation.
 *
 * Connects to OH SceneSessionManager (scene-based WMS) and provides window
 * session lifecycle management. Each Android window maps to an OH session
 * backed by an RSSurfaceNode for rendering.
 *
 * IPC flow for Hello World window display:
 *   1. createSession() -> SSM.CreateAndConnectSpecificSession()
 *      - Creates an OH scene session via ISceneSessionManager (system singleton)
 *      - Registers SessionStageAdapter as ISessionStage callback
 *      - Returns ISession proxy (per-window) + RSSurfaceNode ID
 *   2. updateSessionRect() -> ISession.UpdateSessionRect()
 *      - Sets window position and size via per-window ISession proxy
 *   3. notifyDrawingCompleted() -> ISession.DrawingCompleted()
 *      - Tells OH compositor the window is ready to display
 *   4. destroySession() -> ISession.Disconnect() + SSM.DestroyAndDisconnectSpecificSession()
 *      - Disconnects per-window session, then notifies SSM to clean up
 *
 * Reference:
 *   OH: wms/window_scene/session_manager/include/zidl/scene_session_manager_interface.h
 *   OH: wms/window_scene/session/host/include/zidl/session_interface.h
 */
#include "oh_window_manager_client.h"
#include "session_stage_adapter.h"
#include "window_callback_adapter.h"
#include "window_event_channel_adapter.h"
#include "oh_input_bridge.h"  // 2026-05-18 §3.3.5 MMI subscription
#include "../../activity/jni/oh_ability_manager_client.h"
#include <android/log.h>
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstdlib>
#include <map>

#include "ipc_skeleton.h"
#include "iservice_registry.h"  // OHOS::SystemAbilityManagerClient
#include "system_ability_manager_proxy.h"
#include "window_manager_hilog.h"
#include "ui/rs_surface_node.h"                       // RSSurfaceNode::Create
#include "transaction/rs_transaction.h"               // RSTransaction::FlushImplicitTransaction
#include "oh_br_trace.h"                              // G2.14ac IPC trace+log macros

// 2026-05-02 G2.14r: forward-declare CreateNativeWindowFromSurface from
// graphic_surface/interfaces/inner_api/surface/window.h.  Direct #include is
// ambiguous because OH has 10+ different files named window.h on its include
// path (window_manager/libwm/include/window.h gets picked first by the
// compiler).  The signature is stable: void* pSurface is `OHOS::sptr<OHOS::Surface>*`.
struct NativeWindow;
typedef struct NativeWindow OHNativeWindow;
extern "C" OHNativeWindow* CreateNativeWindowFromSurface(void* pSurface);
// 2026-05-12 G2.14aw probe A.1: read producer uniqueId from OHNativeWindow.
// Defined in libnative_window.so; signature stable per
// graphic_surface/interfaces/inner_api/surface/external_window.h:674.
extern "C" int32_t OH_NativeWindow_GetSurfaceId(OHNativeWindow* window, uint64_t* surfaceId);
// Seed the real OH NativeWindow configuration used by
// NativeWindowRequestBuffer. ProducerSurface::SetDefaultWidthAndHeight does not
// update this per-window configuration on the OH 6.1 RS surface path.
extern "C" int32_t OH_NativeWindow_NativeWindowHandleOpt(
    OHNativeWindow* window, int code, ...);
#ifndef OH_NW_OP_SET_BUFFER_GEOMETRY
#define OH_NW_OP_SET_BUFFER_GEOMETRY 0
#endif

// Keep the process-local render-session hint in this translation unit.  Calling
// the default-visible C export from inside the bridge is ELF-preemptible; when
// another loaded DSO exports the same compatibility symbol, the store can land
// in that DSO while exact-handle dlsym reads this bridge's untouched value.
namespace {
std::atomic<int32_t> g_lastAttachedSession{0};
constexpr const char* kSharedSessionEnv = "WESTLAKE_WINDOW_SESSION_ID_V1";
constexpr const char* kSharedNativeWindowEnv = "WESTLAKE_NATIVE_WINDOW_PTR_V1";

void setLastAttachedSessionLocal(int32_t sessionId) {
    OH_BR_IPC_SCOPE("oh_wm_set_last_session_local", "session=%{public}d", sessionId);
    g_lastAttachedSession.store(sessionId, std::memory_order_release);
}

void publishProcessWindowTarget(int32_t sessionId, void* nativeWindow) {
    char sessionText[16] = {};
    char pointerText[2 + sizeof(uintptr_t) * 2 + 1] = {};
    std::snprintf(sessionText, sizeof(sessionText), "%d", sessionId);
    std::snprintf(pointerText, sizeof(pointerText), "%p", nativeWindow);
    (void)setenv(kSharedNativeWindowEnv, pointerText, 1);
    (void)setenv(kSharedSessionEnv, sessionText, 1);
}

int32_t readProcessWindowSession() {
    const char* text = std::getenv(kSharedSessionEnv);
    if (text == nullptr || *text == '\0') return 0;
    char* end = nullptr;
    errno = 0;
    long value = std::strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value <= 0 ||
        value > INT32_MAX) return 0;
    return static_cast<int32_t>(value);
}

void* readProcessWindowTarget(int32_t sessionId) {
    if (readProcessWindowSession() != sessionId) return nullptr;
    const char* text = std::getenv(kSharedNativeWindowEnv);
    if (text == nullptr || *text == '\0') return nullptr;
    char* end = nullptr;
    errno = 0;
    unsigned long long value = std::strtoull(text, &end, 0);
    if (errno != 0 || end == text || *end != '\0' || value == 0) return nullptr;
    return reinterpret_cast<void*>(static_cast<uintptr_t>(value));
}
}  // namespace

// 2026-05-09 G2.14ae: oh_anw_wrap from oh_anativewindow_shim.cpp wraps a raw
// OH NativeWindow handle into an AOSP-ABI-compatible ANativeWindow struct so
// hwui can use AOSP NDK offsets without crashing on OH's RefBase / virtual
// class layout. See doc/graphics_rendering_design.html §7.11.
extern "C" struct ANativeWindow* oh_anw_wrap(OHNativeWindow* oh);
// G2.14c (2026-05-01) — pivot from SCB-style 3-hop chain to legacy
// IWindowManager. SA 4606 host on this OH 7.0.0.18 build is libwms.z.so's
// WindowManagerService (legacy), NOT libsms.z.so's MockSessionManagerService.
// Confirmed by: (a) /system/profile/foundation.json says SA 4606 -> libwms.z.so
// (b) deployed libwms.z.so contains only WindowManagerService symbols, no
// MockSessionManagerService (c) OH BUILD.gn shows libwms is the legacy WMS
// library when window_manager_use_sceneboard=false (the project default).
// So we use IWindowManager.CreateWindow + AddWindow instead of SCB's
// CreateAndConnectSpecificSession 3-hop chain.
#include "window_manager_interface.h"                 // IWindowManager (legacy)
#include "window_property.h"                          // legacy WindowProperty
// 2026-06-29 [OCCLUSION-FIX] V7 SCB connect path. ISceneSessionManager +
// WindowSessionProperty + SystemSessionConfig + SessionInfo come transitively
// from this header (it includes common/include/window_session_property.h and
// interfaces/include/ws_common.h). Needed so createSession can route through
// CreateAndConnectSpecificSession → a real SceneSession with sessionStage_ set,
// instead of the legacy CreateWindow+AddWindow stub whose dangling occlusion
// callback crashes OH foundation on RS occlusion change.
#include "scene_session_manager_interface.h"          // OHOS::Rosen::ISceneSessionManager
#include "session_manager.h"                          // official SCB three-hop proxy acquisition

#define LOG_TAG "OH_WindowMgrClient"
// B.37 sediment / memory feedback_prefer_inner_api.md: use OH HiLogPrint
// directly. __android_log_print is no-op on OH (the Android log shim isn't
// wired up for adapter .so bridge code). HiLogPrint goes straight to OH
// hilog so logs from this file actually appear.
#include "hilog/log.h"
#define LOGI(fmt, ...) HiLogPrint(LOG_CORE, LOG_INFO,  0xD000F00u, LOG_TAG, fmt, ##__VA_ARGS__)
#define LOGE(fmt, ...) HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, LOG_TAG, fmt, ##__VA_ARGS__)
#define LOGW(fmt, ...) HiLogPrint(LOG_CORE, LOG_WARN,  0xD000F00u, LOG_TAG, fmt, ##__VA_ARGS__)

// OH system ability IDs (per system_ability_definition.h:285)
//   4606 = WINDOW_MANAGER_SERVICE_ID — serves BOTH legacy IWindowManager AND
//          ISceneSessionManager (the latter extends the former); this is what
//          OH's own WindowAdapter / SessionManager call (window_adapter.cpp:508,
//          session_manager.cpp:243).
//   4607 = DISPLAY_MANAGER_SERVICE_SA_ID — serves IDisplayManager (NOT WMS).
//
// G2.14 root cause: pre-fix used 4607 → silent iface_cast<ISceneSessionManager>
// on a DisplayManager proxy → CreateAndConnectSpecificSession got "method not
// found" on the wrong server → SendRequest returned non-ERR_NONE. The
// IPCObjectProxy log line "desc:*.IDisplayManager error:1" came from the same
// proxy and was the smoking gun.
static constexpr int32_t SCENE_SESSION_MANAGER_ID = 4606;

namespace oh_adapter {

// §3.1.4.1 — Android LayoutParams.type → OH WindowType.
//
// Android main DecorView (TYPE_BASE_APPLICATION=1 / TYPE_APPLICATION=2 /
// TYPE_APPLICATION_STARTING=3) is represented as a child of the OH
// Ability-created MainSession. createSession() resolves that parent by the
// Ability token and fills both parent IDs before asking SCB to create this
// specific session. A parentless APP_SUB_WINDOW is rejected locally.
//
// Casting Android's enum value directly to OH WindowType (the pre-fix behavior)
// dropped values 2/3/etc. into OH enum gaps -> WindowSessionProperty
// Marshalling rejected them -> server returned ERR_INVALID_DATA -> proxy logged
// "SendRequest failed". This map is the actual G2.13 fix.
static OHOS::Rosen::WindowType mapAndroidWindowType(int32_t androidType) {
    using OHOS::Rosen::WindowType;
    switch (androidType) {
        case 1:        // TYPE_BASE_APPLICATION
        case 2:        // TYPE_APPLICATION
        case 3:        // TYPE_APPLICATION_STARTING
            return WindowType::WINDOW_TYPE_APP_SUB_WINDOW;
        // Real sub windows must have parent set explicitly by caller; for
        // now downgrade to MAIN type as well — adapter doesn't yet plumb
        // parent linkage for Android sub windows.
        case 1000:     // TYPE_APPLICATION_PANEL
        case 1001:     // TYPE_APPLICATION_MEDIA
        case 1002:     // TYPE_APPLICATION_SUB_PANEL
        case 1003:     // TYPE_APPLICATION_ATTACHED_DIALOG
            return WindowType::WINDOW_TYPE_APP_SUB_WINDOW;
        case 2003:     // TYPE_SYSTEM_ALERT
        case 2008:     // TYPE_SYSTEM_DIALOG
        case 2038:     // TYPE_APPLICATION_OVERLAY
            return WindowType::WINDOW_TYPE_DIALOG;
        case 2005:     // TYPE_TOAST
            return WindowType::WINDOW_TYPE_TOAST;
        case 2006:     // TYPE_SYSTEM_OVERLAY
            return WindowType::WINDOW_TYPE_FLOAT;
        case 2011:     // TYPE_INPUT_METHOD
        case 2012:     // TYPE_INPUT_METHOD_DIALOG
            return WindowType::WINDOW_TYPE_INPUT_METHOD_FLOAT;
        default:
            return WindowType::WINDOW_TYPE_APP_MAIN_WINDOW;
    }
}

OHWindowManagerClient& OHWindowManagerClient::getInstance() {
    static OHWindowManagerClient instance;
    return instance;
}

bool OHWindowManagerClient::connect() {
    OH_BR_IPC_SCOPE("WMClient.connect", "");
    LOGI("Connecting to OH SceneSessionManager through official SessionManager route ...");

    // OH 6.1.0.31 runs SceneBoard. SA 4606 is MockSessionManagerService, not
    // ISceneSessionManager itself. Use the platform's own SessionManager route:
    // SA 4606 -> IMockSessionManagerInterface -> ISessionManagerService
    //         -> ISceneSessionManager.
    // INVALID_USER_ID matches WindowAdapter::GetInstance()'s default/current
    // user semantics and lets the platform select the active WMS user.
    auto ssmInterface =
        OHOS::Rosen::SessionManager::GetInstance(OHOS::Rosen::INVALID_USER_ID)
            .GetSceneSessionManagerProxy();
    if (ssmInterface == nullptr) {
        LOGE("Official SessionManager returned null SceneSessionManager proxy");
        return false;
    }
    ssmProxy_ = ssmInterface->AsObject();
    if (ssmProxy_ == nullptr) {
        LOGE("SceneSessionManager proxy has no remote object");
        return false;
    }

    LOGI("Connected to SceneSessionManager through official SessionManager route");
    connected_ = true;
    return true;
}

void OHWindowManagerClient::disconnect() {
    OH_BR_IPC_SCOPE("WMClient.disconnect", "");
    LOGI("Disconnecting from OH window services");

    std::lock_guard<std::mutex> lock(sessionMutex_);
    sessions_.clear();
    ssmProxy_ = nullptr;
    connected_ = false;
}

// Android LayoutParams flags admitted by WindowSessionAdapter. SceneBoard's
// WindowSessionProperty carries the equivalent OH properties in the initial
// CreateAndConnectSpecificSession transaction.
static constexpr int32_t ANDROID_FLAG_HARDWARE_ACCELERATED    = 0x01000000;
static constexpr int32_t ANDROID_FLAG_LAYOUT_IN_SCREEN      = 0x00000100;
static constexpr int32_t ANDROID_FLAG_LAYOUT_INSET_DECOR    = 0x00010000;
static constexpr int32_t ANDROID_FLAG_SPLIT_TOUCH           = 0x00800000;
static constexpr int32_t ANDROID_FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS = 0x80000000;
static constexpr int32_t ANDROID_FLAG_FULLSCREEN            = 0x00000400;
static constexpr int32_t ANDROID_FLAG_KEEP_SCREEN_ON        = 0x00000080;
static constexpr int32_t ANDROID_FLAG_SHOW_WHEN_LOCKED      = 0x00080000;
static constexpr int32_t ANDROID_FLAG_TURN_SCREEN_ON        = 0x00200000;
static constexpr int32_t ANDROID_FLAG_DISMISS_KEYGUARD      = 0x00400000;

static void applyAndroidFlagsToWindowSessionProperty(
    int32_t androidFlags,
    const OHOS::sptr<OHOS::Rosen::WindowSessionProperty>& property)
{
    const int32_t mappedMask = ANDROID_FLAG_FULLSCREEN
        | ANDROID_FLAG_KEEP_SCREEN_ON
        | ANDROID_FLAG_SHOW_WHEN_LOCKED
        | ANDROID_FLAG_TURN_SCREEN_ON
        | ANDROID_FLAG_DISMISS_KEYGUARD;
    const int32_t noOpAllowedMask = ANDROID_FLAG_HARDWARE_ACCELERATED
        | ANDROID_FLAG_LAYOUT_IN_SCREEN
        | ANDROID_FLAG_LAYOUT_INSET_DECOR
        | ANDROID_FLAG_SPLIT_TOUCH
        | ANDROID_FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS;
    const int32_t extraFlags = androidFlags & ~(mappedMask | noOpAllowedMask);
    if (extraFlags != 0) {
        LOGW("createSession: unexpected LayoutParams flags 0x%{public}x reached native; "
             "Java allowlist and native mapping are out of sync", extraFlags);
    }

    property->SetKeepScreenOn((androidFlags & ANDROID_FLAG_KEEP_SCREEN_ON) != 0);
    property->SetTurnScreenOn((androidFlags & ANDROID_FLAG_TURN_SCREEN_ON) != 0);

    uint32_t ohWindowFlags = 0;
    if ((androidFlags & (ANDROID_FLAG_SHOW_WHEN_LOCKED
            | ANDROID_FLAG_DISMISS_KEYGUARD)) != 0) {
        ohWindowFlags |= static_cast<uint32_t>(
            OHOS::Rosen::WindowFlag::WINDOW_FLAG_SHOW_WHEN_LOCKED);
    }
    property->SetWindowFlags(ohWindowFlags);
}

OHWindowSession OHWindowManagerClient::createSession(
    JavaVM* jvm, jobject androidWindow,
    const std::string& bundleName, const std::string& abilityName,
    const std::string& moduleName, const std::string& windowName,
    int32_t androidWindowType, int32_t displayId,
    int32_t requestedWidth, int32_t requestedHeight,
    int32_t androidFlags,
    uint64_t ohTokenAddr)
{
    OH_BR_IPC_SCOPE("WMClient.createSession",
                    "bundle=%{public}s ability=%{public}s name=%{public}s w=%{public}d h=%{public}d ohToken=0x%{public}llx",
                    bundleName.c_str(), abilityName.c_str(), windowName.c_str(),
                    requestedWidth, requestedHeight,
                    (unsigned long long)ohTokenAddr);
    // §3.1.5.6.2 — wsErr defaults capture the most likely cause of early-exit.
    OHWindowSession result;
    result.wsErr = static_cast<int32_t>(OHOS::Rosen::WSError::WS_ERROR_IPC_FAILED);

    if (!connected_ || ssmProxy_ == nullptr) {
        LOGE("createSession: Not connected to SceneSessionManager");
        return result;
    }

    // §3.1.4.1 — translate Android type to a value OH SSM accepts. Direct cast
    // from Android type to OH WindowType drops most values into enum gaps and
    // makes WindowSessionProperty Marshalling reject the property → server
    // returns ERR_INVALID_DATA → proxy logs "SendRequest failed".
    OHOS::Rosen::WindowType ohType = mapAndroidWindowType(androidWindowType);

    // §3.1.5.6.1 — wrap raw OH token pointer into sptr for safe lifetime.
    // 0 = no token; we then keep TokenState=false to honor §3.1.4.6.6 矩阵.
    OHOS::sptr<OHOS::IRemoteObject> token = nullptr;
    if (ohTokenAddr != 0) {
        token = OHOS::sptr<OHOS::IRemoteObject>(
            reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr));
    }

    LOGI("createSession: bundle=%{public}s ability=%{public}s name=%{public}s, "
         "androidType=%{public}d -> ohType=%{public}u, "
         "display=%{public}d, size=%{public}dx%{public}d, "
         "ohTokenAddr=0x%{public}llx token=%{public}p",
         bundleName.c_str(), abilityName.c_str(), windowName.c_str(),
         androidWindowType, static_cast<uint32_t>(ohType),
         displayId, requestedWidth, requestedHeight,
         static_cast<unsigned long long>(ohTokenAddr),
         token.GetRefPtr());

    // V7 SceneSessionManager.CreateAndConnectSpecificSession wire format:
    //   (sessionStage, eventChannel, surfaceNode, property, persistentId&,
    //    session&, systemConfig&, token=nullptr)
    // V6 (stageAdapter, windowAdapter, sessionInfo, session&, ...) signature
    // and WindowCallbackAdapter (V6 IWindow) are no longer used here. Input
    // events still flow on the Android side via OHInputBridge → InputChannel;
    // the IWindowEventChannel stub here exists only so SSM has a non-null
    // callback target. The RSSurfaceNode is client-created and its node id is
    // what Android-side SurfaceControl renders into.

    // 2026-06-29 [OCCLUSION-FIX] V7 SCB path: instantiate the REAL ISessionStage
    // + IWindowEventChannel.  SessionStageAdapter is the object OH SceneSession
    // stores as sessionStage_ — and that field is set ONLY by Session::ConnectInner
    // (reached via CreateAndConnectSpecificSession), never by the legacy
    // CreateWindow+AddWindow path.  Its NotifyWindowOcclusionState() returns
    // WS_OK (session_stage_adapter.cpp:151), so when RenderService fires the
    // occlusion listener the call lands on a live callback rather than a dangling
    // legacy WMS occlusion stub (cb_ == 0 → NULL deref → foundation SIGSEGV →
    // device reboot).
    OHOS::sptr<SessionStageAdapter> stage =
        new SessionStageAdapter(jvm, androidWindow);
    OHOS::sptr<WindowEventChannelAdapter> eventChannel =
        new WindowEventChannelAdapter(jvm);

    OHOS::Rosen::RSSurfaceNodeConfig nodeCfg;
    nodeCfg.SurfaceNodeName = windowName;
    // 2026-05-11 G2.14aq — reverted UI_EXTENSION_COMMON_NODE → APP_WINDOW_NODE.
    //
    // History:
    //   G2.14ah identified IsCallingPidValid blocking PERMISSION_APP commands
    //   on TF_ASYNC path (callingPid=0 ≠ commandPid).  G2.14ai chose
    //   UI_EXTENSION_COMMON_NODE because nodeMap.IsUIExtensionSurfaceNode
    //   provided a second bypass in the same check.  That made commands pass,
    //   but UI_EXTENSION_COMMON_NODE has the side-effect that:
    //     IsMainWindowType() = false   (nodeType_ > SELF_DRAWING_WINDOW_NODE)
    //     IsAppWindow()      = false
    //   so OH RS main compose loop does NOT schedule the surface for
    //   composition — buffers reach the producer queue but never appear
    //   on screen (G2.14ap proved this via RS hidumper: OpaqueRegion=Empty,
    //   shouldPaint_=0, even with bounds/frame correctly set).
    //
    // G2.14aq fixes the root cause at the OH side via
    // ohos_patches/graphic_2d/.../rs_transaction_data.cpp.patch — when
    // IsCallingPidValid sees callingPid=0 (TF_ASYNC sentinel), it falls back
    // to the SendingPid (RSTransactionData::pid_) the client Marshalled into
    // the parcel, which DOES equal commandPid for normal-apl clients.  That
    // restores the natural pid_==commandPid bypass for our app, allowing us
    // to use APP_WINDOW_NODE here so the layer enters main compositing.
    //
    // SECURITY NOTE: the patch trusts a client-supplied pid_ when the kernel
    // sender_pid is 0.  Detailed risk analysis (and why it is acceptable for
    // an Android-adapter device topology with ≤1 normal-apl process) is in
    // doc/build_patch_log.html [Patch G2.14aq].
    auto surfaceNode = OHOS::Rosen::RSSurfaceNode::Create(
        nodeCfg,
        OHOS::Rosen::RSSurfaceNodeType::APP_WINDOW_NODE,
        /*isWindow=*/true);
    if (!surfaceNode) {
        LOGE("createSession: RSSurfaceNode::Create failed for %s", windowName.c_str());
        result.wsErr = 1001;  // WS_ERROR_NULLPTR equivalent
        return result;
    }

    // 2026-05-11 G2.14am-PROBE result captured (memory project_g214am_probe_red.md):
    // RED bg + isOpaque=0 → screen all red → hwui buffer is fully transparent
    // (no GL clear, no Skia draws).  Conclusion: hwui produces empty buffer.
    // Probe code removed; next diagnostic phase (G2.14an) intercepts Canvas
    // DrawOps at adapter/shim layer to confirm whether helloworld View.draw
    // submits any draws to BaseCanvas natives.  See compat_shim.cpp.

    // 2026-06-29 [OCCLUSION-FIX] V7 WindowSessionProperty (NOT legacy
    // WindowProperty).  CreateAndConnectSpecificSession requires this type;
    // SessionInfo carries the Android identity into the SceneSession so OH builds
    // a properly-keyed scene session (window_session_property.h:49/52/77 +
    // ws_common.h:399 SessionInfo).
    OHOS::sptr<OHOS::Rosen::WindowSessionProperty> property =
        new OHOS::Rosen::WindowSessionProperty();
    property->SetWindowName(windowName);
    property->SetWindowType(ohType);
    property->SetWindowMode(OHOS::Rosen::WindowMode::WINDOW_MODE_FULLSCREEN);
    OHOS::Rosen::Rect rect{0, 0,
        static_cast<uint32_t>(requestedWidth), static_cast<uint32_t>(requestedHeight)};
    property->SetRequestRect(rect);
    property->SetWindowRect(rect);
    property->SetDisplayId(static_cast<uint64_t>(displayId));
    applyAndroidFlagsToWindowSessionProperty(androidFlags, property);
    OHOS::Rosen::SessionInfo sessionInfo;
    sessionInfo.bundleName_ = bundleName;
    sessionInfo.abilityName_ = abilityName;
    sessionInfo.moduleName_ = moduleName;
    property->SetSessionInfo(sessionInfo);
    // Fn04/A07 wire invariant: the token-presence bit in the marshalled
    // WindowSessionProperty must agree with the final token argument.
    property->SetTokenState(token != nullptr);

    // 2026-06-29 [OCCLUSION-FIX] Cast SA 4606 to ISceneSessionManager (NOT the
    // legacy IWindowManager).  iface_cast builds a SceneSessionManagerProxy from
    // the remote via the runtime BrokerRegistration; if its BrokerDelegator is
    // not loaded into this process, or the SA hosts only the legacy WMS, this
    // returns null and we fail the call cleanly (no crash) — see RISK note.
    auto ssmInterface = OHOS::iface_cast<OHOS::Rosen::ISceneSessionManager>(ssmProxy_);
    if (ssmInterface == nullptr) {
        LOGE("createSession: iface_cast<ISceneSessionManager> on SA %d returned null "
             "(SceneSessionManagerProxy BrokerDelegator not loaded, or SA hosts "
             "legacy WMS only)", SCENE_SESSION_MANAGER_ID);
        result.wsErr = 1001;
        return result;
    }

    // OH6.1 creates the real application MainSession as part of Ability
    // activation before Android's DecorView reaches this adapter. Adopt that
    // identity instead of attempting another MainSession (rejected by the
    // specific-session API) or creating an orphan subwindow (never attached to
    // the scene tree). This is the narrow HelloWorld P2 route: one OH
    // MainSession, one Android-content child, tied by the same Ability token.
    const bool isAndroidTopLevel =
        androidWindowType == 1 || androidWindowType == 2 || androidWindowType == 3;
    if (isAndroidTopLevel) {
        if (token == nullptr) {
            LOGE("createSession: top-level Android window has no OH Ability token; "
                 "refusing parentless APP_SUB_WINDOW");
            result.wsErr =
                static_cast<int32_t>(OHOS::Rosen::WSError::WS_ERROR_INVALID_PARENT);
            return result;
        }

        // WMS GetFocusWindowInfoByAbilityToken is SA-only on OH6.1. AMS
        // GetMissionIdByToken is the application-authorized route: with
        // SceneBoard enabled, AMS returns
        // UIAbilityLifecycleManager::GetSessionIdByAbilityToken(token), which
        // is the MainSession persistentId assigned during Ability activation.
        int32_t parentPersistentId =
            OHAbilityManagerClient::getInstance().getMissionIdByTokenAddr(
                static_cast<jlong>(ohTokenAddr));
        LOGI("createSession: parent lookup via AMS token=%{public}p "
             "persistentId=%{public}d",
             token.GetRefPtr(), parentPersistentId);
        if (parentPersistentId <= 0) {
            LOGE("createSession: AMS returned no valid Ability MainSession; "
                 "refusing orphan child persistentId=%{public}d",
                 parentPersistentId);
            result.wsErr =
                static_cast<int32_t>(OHOS::Rosen::WSError::WS_ERROR_INVALID_PARENT);
            return result;
        }

        property->SetParentId(parentPersistentId);
        property->SetParentPersistentId(parentPersistentId);
        property->SetWindowType(
            OHOS::Rosen::WindowType::WINDOW_TYPE_APP_SUB_WINDOW);
        stage->SetInheritsParentFocus(true);
        if (!stage->EnableRootBlastForTopLevelContent()) {
            LOGE("createSession: failed to enable root BLAST for Android "
                 "top-level content; refusing a null-BBQ ViewRoot");
            result.wsErr = 1001;
            return result;
        }
        LOGI("createSession: bound Android top-level content to OH MainSession "
             "parentId=%{public}d", parentPersistentId);
    }

    // V7 SceneSessionManager.CreateAndConnectSpecificSession
    //   (sessionStage, eventChannel, surfaceNode, property, persistentId&,
    //    session&, systemConfig&, token)
    // signature: scene_session_manager_proxy.h:30 / scene_session_manager.h:243.
    // The server-side Session::ConnectInner sets sessionStage_ = our `stage`,
    // giving the SceneSession a non-null, live occlusion callback target.
    int32_t persistentId = 0;
    OHOS::sptr<OHOS::Rosen::ISession> session = nullptr;
    OHOS::Rosen::SystemSessionConfig systemConfig;
    OHOS::Rosen::WSError connErr = ssmInterface->CreateAndConnectSpecificSession(
        stage, eventChannel, surfaceNode, property,
        persistentId, session, systemConfig, token);
    if (connErr != OHOS::Rosen::WSError::WS_OK || session == nullptr) {
        LOGE("createSession: CreateAndConnectSpecificSession failed ws=%{public}d "
             "session=%{public}p persistentId=%{public}d",
             static_cast<int>(connErr), session.GetRefPtr(), persistentId);
        result.wsErr = static_cast<int32_t>(connErr);
        return result;
    }
    LOGI("createSession: CreateAndConnectSpecificSession OK persistentId=%{public}d "
         "session=%{public}p", persistentId, session.GetRefPtr());

    int64_t surfaceNodeId = static_cast<int64_t>(surfaceNode->GetId());

    int32_t sessionId;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        sessionId = persistentId > 0 ? persistentId : nextSessionId_++;
        // 2026-06-29 [OCCLUSION-FIX] V7 SCB path: store the live ISession proxy
        // plus the SessionStageAdapter + WindowEventChannelAdapter so OH holds a
        // fully Connect-ed SceneSession with a non-null sessionStage_ for the
        // lifetime of the session (the stage/channel sptrs must outlive the IPC).
        SessionEntry entry{};
        entry.sessionId = sessionId;
        entry.surfaceNodeId = surfaceNodeId;
        entry.sessionProxy = session;
        entry.sessionProperty = property;
        entry.stageAdapter = stage;
        entry.eventChannel = eventChannel;
        entry.surfaceNode = surfaceNode;
        entry.reqWidth = requestedWidth;
        entry.reqHeight = requestedHeight;
        entry.ohTokenAddr = ohTokenAddr;
        // persistentId doubles as the WMS-side window identity used by the
        // hide/show helpers.  windowProperty is the legacy-only field (type
        // WindowProperty) and stays null on the V7 path — showWindow guards
        // null before any legacy AddWindow, so it is a clean no-op there.
        entry.windowId = static_cast<uint32_t>(persistentId);
        entry.wmsShown = true;  // session is connected (shown)
        sessions_[sessionId] = entry;
    }

    result.sessionId = sessionId;
    result.surfaceNodeId = static_cast<int32_t>(surfaceNodeId);
    result.displayId = displayId;
    result.width = requestedWidth;
    result.height = requestedHeight;
    result.frameLeft = 0;
    result.frameTop = 0;
    result.frameRight = requestedWidth;
    result.frameBottom = requestedHeight;
    result.valid = true;
    result.wsErr = 0;  // §3.1.5.6.2 — explicit zero on success path

    LOGI("createSession: success, sessionId=%d, surfaceNodeId=%lld",
         sessionId, static_cast<long long>(surfaceNodeId));
    // 2026-05-02 G2.14r: stamp last-attached-session for BBQ_nativeUpdate
    // fallback (avoids BCP-jar boot-image rebuild for one new native method).
    setLastAttachedSessionLocal(sessionId);
    void* processWindowTarget = getOhNativeWindow(sessionId);
    if (processWindowTarget != nullptr) {
        publishProcessWindowTarget(sessionId, processWindowTarget);
        LOGI("createSession: published process window target session=%{public}d target=%{public}p",
             sessionId, processWindowTarget);
    } else {
        LOGW("createSession: process window target unavailable session=%{public}d", sessionId);
    }

    // 2026-06-29 [OCCLUSION-FIX] request input focus via the V7 SSM API
    // (RequestFocusStatus, scene_session_manager_proxy.h:45) keyed by
    // persistentId.  Replaces the legacy IWindowManager::RequestFocus(windowId).
    // Without focus, OH MMI keeps the launcher as focus target; call it BEFORE
    // subscribeMmi so this session is the focus target when routing begins.
    {
        OHOS::Rosen::WMError focusRet =
            ssmInterface->RequestFocusStatus(persistentId, /*isFocused=*/true);
        if (focusRet == OHOS::Rosen::WMError::WM_OK) {
            LOGI("createSession: RequestFocusStatus(persistentId=%{public}d) OK", persistentId);
        } else {
            LOGW("createSession: RequestFocusStatus(persistentId=%{public}d) failed rc=%{public}d",
                 persistentId, static_cast<int>(focusRet));
        }
    }

    // 2026-05-18: subscribe to OH MMI input events. Without this, MMI service
    // never dispatches PointerEvent / KeyEvent to this process and HelloWorld's
    // CHANGE COLOR button (and any other touch UI) never receives events.
    // Mirrors OH native InputTransferStation::AddInputWindow() called from
    // WindowImpl::Create on the OH side. See Input_Adapter_design §3.3.5.
    OHInputBridge::getInstance().subscribeMmi(sessionId);

    return result;
}

int OHWindowManagerClient::updateSessionRect(int32_t sessionId,
                                              int32_t x, int32_t y,
                                              int32_t width, int32_t height)
{
    OH_BR_IPC_SCOPE("WMClient.updateSessionRect",
                    "session=%{public}d rect=[%{public}d,%{public}d,%{public}d,%{public}d]",
                    sessionId, x, y, width, height);

    OHOS::sptr<OHOS::Rosen::ISession> session;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) {
            LOGW("updateSessionRect: session %{public}d not found", sessionId);
            return -1;
        }
        session = it->second.sessionProxy;
    }
    if (session == nullptr) {
        LOGE("updateSessionRect: V7 session proxy is null, session=%{public}d", sessionId);
        return -2;
    }

    OHOS::Rosen::WSRect rect {
        x,
        y,
        static_cast<uint32_t>(width),
        static_cast<uint32_t>(height)
    };
    auto rc = session->UpdateSessionRect(
        rect, OHOS::Rosen::SizeChangeReason::UNDEFINED);
    LOGI("updateSessionRect: V7 ISession.UpdateSessionRect session=%{public}d "
         "rect=[%{public}d,%{public}d,%{public}d,%{public}d] rc=%{public}d",
         sessionId, x, y, width, height, static_cast<int>(rc));
    return static_cast<int32_t>(rc);
}

int OHWindowManagerClient::notifyDrawingCompleted(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.notifyDrawingCompleted", "session=%{public}d", sessionId);
    OHOS::sptr<OHOS::Rosen::ISession> session;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) {
            LOGW("notifyDrawingCompleted: session %{public}d not found", sessionId);
            return -1;
        }
        session = it->second.sessionProxy;
    }
    if (session == nullptr) {
        LOGE("notifyDrawingCompleted: V7 session proxy is null, session=%{public}d", sessionId);
        return -2;
    }
    auto rc = session->DrawingCompleted();
    LOGI("notifyDrawingCompleted: V7 ISession.DrawingCompleted "
         "session=%{public}d rc=%{public}d", sessionId, static_cast<int>(rc));
    return static_cast<int32_t>(rc);
}

void OHWindowManagerClient::destroySession(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.destroySession", "session=%{public}d", sessionId);

    OHOS::sptr<OHOS::Rosen::ISession> sessionProxy;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it != sessions_.end()) {
            sessionProxy = it->second.sessionProxy;
            sessions_.erase(it);
        }
    }

    // G2.14c — legacy path uses IWindowManager.RemoveWindow + DestroyWindow.
    // sessionProxy is null in legacy path (V7-only field); skip Disconnect().
    if (connected_ && ssmProxy_ != nullptr) {
        auto wmsInterface = OHOS::iface_cast<OHOS::Rosen::IWindowManager>(ssmProxy_);
        if (wmsInterface) {
            wmsInterface->RemoveWindow(static_cast<uint32_t>(sessionId), true);
            wmsInterface->DestroyWindow(static_cast<uint32_t>(sessionId), false);
        }
    }
}

// 2026-05-19: visibility helpers — call OH WMS RemoveWindow / AddWindow to
// hide / show, gated by per-session wmsShown bool to make the IPC idempotent.
// Mirrors ArkUI WindowImpl::Hide (line 2034) / Show (line 1972) — keeps the
// adapter aligned with how OH native window clients toggle visibility.
//
// Design alternatives considered (see doc for full rationale):
//   A. Java-side Map<sessionId, Boolean> — adapter Java state, fast, but extra
//      state to keep in sync.
//   B. Reflect AOSP ViewRootImpl.mAppVisible — no adapter cache but fragile
//      (AOSP internal field name may change between API levels).
//   C. Call WMS RemoveWindow / AddWindow every relayout, let OH server's own
//      idempotency handle dups (WM_DO_NOTHING / WM_ERROR_INVALID_OPERATION).
//      No adapter state but adds binder IPC every relayout.
//   D. (chosen) In-App-process C++ cache on SessionEntry — state lives in
//      the data structure the adapter already maintains; Java caller is
//      stateless; per-relayout IPC only on actual transitions.
//
// Future drift mitigation: if adapter's wmsShown diverges from real OH state
// (e.g., WMS unilaterally hides due to AMS / focus policy), switch to A or B.

int32_t OHWindowManagerClient::hideWindow(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.hideWindow", "session=%{public}d", sessionId);

    // 2026-06-02 (post-revert rework): hide = RemoveWindow — the only way an
    // APP_MAIN_WINDOW yields the desktop in OH legacy WMS.  Evidence (hidumper,
    // after home): the backgrounded helloworld APP window (z=1) sits ABOVE the
    // launcher EntryView/DESKTOP (z=0) and keeps focus, so the desktop stays
    // hidden until the window is removed.  OH window-type z-order policy puts
    // APP above DESKTOP unconditionally, and OH has NO "keep surface but mark
    // invisible" path (its own minimize ends in RemoveWindowNode via the
    // animation callback).  So RemoveWindow is the native contract.
    //
    // Why this is safe now (the no-op was an over-correction):
    //   - The "repeated minimize/restore churns the surface -> RenderThread
    //     SIGSEGV after a few cycles" crash is fixed at the root by the libhwui
    //     CanvasContext commit-callback drain (renderthread/CanvasContext.cpp
    //     pauseSurface/stopDrawing) — not by skipping RemoveWindow.
    //   - This helper is called ONLY from WindowSessionAdapter.relayout() on the
    //     GONE edge, i.e. INSIDE the same main-thread relayout flow in which
    //     ViewRootImpl pauses its renderer + destroys its own BLASTBufferQueue.
    //     The removal is therefore sequenced with the App-side BBQ teardown — no
    //     in-flight frame hits a dead surface.  (The crash that motivated the
    //     no-op came from the decoupled recompute engine calling RemoveWindow on
    //     a separate 32ms handler, racing ViewRootImpl teardown — that engine is
    //     now removed.)
    //   - The covered-vs-minimized decision stays in relayout (isCoveredByNewer-
    //     Foreground keeps a covered window); destroy still flows through
    //     destroySession.  Idempotent via wmsShown so a stop-then-destroy back
    //     does not double-remove.
    uint32_t windowId = 0;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) {
            LOGW("hideWindow: session %{public}d not found", sessionId);
            return -1;
        }
        if (!it->second.wmsShown) {
            return 0;  // already hidden — idempotent (stop-then-destroy, repeat hide)
        }
        windowId = it->second.windowId;
    }
    if (!connected_ || ssmProxy_ == nullptr) {
        LOGW("hideWindow: ssmProxy not ready, session=%{public}d", sessionId);
        return -2;
    }
    auto wmsInterface = OHOS::iface_cast<OHOS::Rosen::IWindowManager>(ssmProxy_);
    if (wmsInterface == nullptr) {
        LOGE("hideWindow: cast IWindowManager failed");
        return -3;
    }
    auto rc = wmsInterface->RemoveWindow(windowId, /*isFromInnerkits=*/true);
    LOGI("hideWindow: RemoveWindow(windowId=%{public}u) rc=%{public}d",
         windowId, static_cast<int>(rc));
    if (rc == OHOS::Rosen::WMError::WM_OK) {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it != sessions_.end()) {
            it->second.wmsShown = false;
        }
    }
    return static_cast<int32_t>(rc);
}

int32_t OHWindowManagerClient::showWindow(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.showWindow", "session=%{public}d", sessionId);

    OHOS::sptr<OHOS::Rosen::ISession> session;
    OHOS::sptr<OHOS::Rosen::WindowSessionProperty> sessionProperty;
    OHOS::sptr<OHOS::Rosen::WindowProperty> property;
    uint32_t windowId = 0;
    bool alreadyShown = false;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end()) {
            LOGW("showWindow: session %{public}d not found", sessionId);
            return -1;
        }
        session = it->second.sessionProxy;
        sessionProperty = it->second.sessionProperty;
        alreadyShown = it->second.wmsShown;
        property = it->second.windowProperty;
        windowId = it->second.windowId;
    }

    // V7 specific sessions are shown through the per-window ISession returned
    // by CreateAndConnectSpecificSession. This mirrors OH6.1
    // WindowSceneSessionImpl::Show -> hostSession->Show(property).
    // Do not cross back into the
    // legacy IWindowManager path: it addresses a different window model and
    // previously returned RequestFocus=1005 while the V7 RS node stayed off-tree.
    if (session != nullptr) {
        if (sessionProperty == nullptr) {
            LOGE("showWindow: V7 sessionProperty is null, session=%{public}d", sessionId);
            return -2;
        }
        auto rc = session->Show(sessionProperty);
        LOGI("showWindow: V7 ISession.Show session=%{public}d rc=%{public}d",
             sessionId, static_cast<int>(rc));
        if (rc == OHOS::Rosen::WSError::WS_OK) {
            std::lock_guard<std::mutex> lock(sessionMutex_);
            auto it = sessions_.find(sessionId);
            if (it != sessions_.end()) {
                it->second.wmsShown = true;
            }
        }
        return static_cast<int32_t>(rc);
    }

    if (!connected_ || ssmProxy_ == nullptr) {
        LOGW("showWindow: ssmProxy not ready, session=%{public}d", sessionId);
        return -3;
    }
    auto wmsInterface = OHOS::iface_cast<OHOS::Rosen::IWindowManager>(ssmProxy_);
    if (wmsInterface == nullptr) {
        LOGE("showWindow: cast IWindowManager failed");
        return -4;
    }

    // 2026-06-01 (window-model rework): the window is AddWindow'd ONCE (at
    // createSession) and kept across background/foreground (hideWindow no longer
    // removes it).  So the normal re-foreground path here does NOT AddWindow again
    // (that churned the surface) — it just RequestFocus to bring this window back
    // to the foreground / input focus.  AddWindow is only used as a safety net if
    // the window somehow was never added (wmsShown=false).
    if (!alreadyShown) {
        if (property == nullptr) {
            LOGW("showWindow: session %{public}d has null windowProperty", sessionId);
            return -2;
        }
        auto rc = wmsInterface->AddWindow(property);
        LOGI("showWindow: AddWindow(windowId=%{public}u) rc=%{public}d (first add)",
             property->GetWindowId(), static_cast<int>(rc));
        if (rc == OHOS::Rosen::WMError::WM_OK) {
            windowId = property->GetWindowId();
            std::lock_guard<std::mutex> lock(sessionMutex_);
            auto it = sessions_.find(sessionId);
            if (it != sessions_.end()) {
                it->second.wmsShown = true;
            }
        } else {
            return static_cast<int32_t>(rc);
        }
    }

    // Bring this (re-)foregrounded window to input focus.  AOSP WMS focuses the
    // foreground window when it becomes visible; on a back-stack pop / recents
    // restore the revealed window must reclaim focus from whatever held it.
    auto focusRet = wmsInterface->RequestFocus(windowId);
    LOGI("showWindow: session=%{public}d RequestFocus(windowId=%{public}u) rc=%{public}d%{public}s",
         sessionId, windowId, static_cast<int>(focusRet),
         alreadyShown ? " (kept window, refocus)" : "");
    return 0;
}


int64_t OHWindowManagerClient::getSurfaceNodeId(int32_t sessionId) const {
    auto it = sessions_.find(sessionId);
    if (it != sessions_.end()) {
        return it->second.surfaceNodeId;
    }
    return -1;
}

// 2026-05-06 — Per design §5.1 / §9.1 三件套 condition #2:
//   Single-source rule for surfaceNode.  Used by oh_surface_bridge.cpp to fetch
//   the same RSSurfaceNode that was registered with WMS, so the WMS-side
//   layer node and the hwui-producer-side buffer feed share one node.
std::shared_ptr<OHOS::Rosen::RSSurfaceNode>
OHWindowManagerClient::getRSSurfaceNode(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.getRSSurfaceNode", "session=%{public}d", sessionId);
    std::lock_guard<std::mutex> lock(sessionMutex_);
    auto it = sessions_.find(sessionId);
    if (it == sessions_.end()) {
        LOGE("getRSSurfaceNode: unknown sessionId=%d", sessionId);
        return nullptr;
    }
    if (!it->second.surfaceNode) {
        LOGE("getRSSurfaceNode: sessionId=%d has no RSSurfaceNode", sessionId);
        return nullptr;
    }
    return it->second.surfaceNode;
}

// 2026-05-02 G2.14r: stable C wrapper for cross-.so callers (e.g.,
// liboh_android_runtime.so::compat_shim BBQ_nativeUpdate).  Avoids C++
// namespace + name mangling issues at the dlsym boundary.
extern "C" __attribute__((visibility("default")))
void* oh_wm_get_native_window(int32_t sessionId) {
    void* local = oh_adapter::OHWindowManagerClient::getInstance().getOhNativeWindow(sessionId);
    return local != nullptr ? local : readProcessWindowTarget(sessionId);
}

// 2026-05-02 G2.14r: cross-process "last touched session" hint.  Used by
// BBQ_nativeUpdate when its SurfaceControl carries no sessionId (avoids the
// need for a BCP-class native method to attach session, which would require
// boot image rebuild on every change).  Each child appspawn-x process spawns
// one app with one session, so a process-global last-session is unambiguous.
extern "C" __attribute__((visibility("default")))
int32_t oh_wm_get_last_session() {
    int32_t local = g_lastAttachedSession.load(std::memory_order_acquire);
    return local != 0 ? local : readProcessWindowSession();
}
extern "C" __attribute__((visibility("default")))
void oh_wm_set_last_session(int32_t sessionId) {
    setLastAttachedSessionLocal(sessionId);
}

// 2026-05-06 — Per design §5.6 / §9.1 三件套 condition #3:
//   Cross-.so C wrappers so liboh_android_runtime.so::android_view_SurfaceControl.cpp
//   (in a different .so) can route SurfaceControl property setters and apply()
//   into RSSurfaceNode + RSTransactionProxy without link-time dependency.
//   All callers use dlsym RTLD_DEFAULT; if liboh_adapter_bridge.so isn't yet
//   loaded into the process, the no-op fallback keeps the SC stub intact.
extern "C" __attribute__((visibility("default")))
void oh_rs_set_layer_bounds(int32_t sessionId, float x, float y, float w, float h) {
    OH_BR_IPC_SCOPE("oh_rs_set_layer_bounds",
                    "session=%{public}d xywh=[%{public}.1f,%{public}.1f,%{public}.1f,%{public}.1f]",
                    sessionId, x, y, w, h);
    auto node = oh_adapter::OHWindowManagerClient::getInstance().getRSSurfaceNode(sessionId);
    if (!node) return;
    // 2026-05-11 G2.14ap: OH RSNode requires SetBounds AND SetFrame as a pair
    // (per foundation/graphic/graphic_2d/.../rs_screen_render_node.h standard
    //  usage).  Without SetFrame, Frame stays at sentinel [-inf, -inf, -inf, -inf]
    //  and ClipToFrame=true (which adapter sets via SurfaceControl) clips the
    //  entire surface to an empty region — VisibleRegion / OpaqueRegion=Empty,
    //  shouldPaint_=0, localDrawRect_=[0,0,0,0] — hwui's frame submission then
    //  no-ops at the RS level even though buffers reach the producer queue.
    node->SetBounds(x, y, w, h);
    node->SetFrame(x, y, w, h);
}

extern "C" __attribute__((visibility("default")))
void oh_rs_set_layer_alpha(int32_t sessionId, float alpha) {
    OH_BR_IPC_SCOPE("oh_rs_set_layer_alpha", "session=%{public}d alpha=%{public}.2f", sessionId, alpha);
    auto node = oh_adapter::OHWindowManagerClient::getInstance().getRSSurfaceNode(sessionId);
    if (!node) return;
    node->SetAlpha(alpha);
}

extern "C" __attribute__((visibility("default")))
void oh_rs_set_layer_visible(int32_t sessionId, int32_t visible) {
    OH_BR_IPC_SCOPE("oh_rs_set_layer_visible", "session=%{public}d visible=%{public}d", sessionId, visible);
    auto node = oh_adapter::OHWindowManagerClient::getInstance().getRSSurfaceNode(sessionId);
    if (!node) return;
    node->SetVisible(visible != 0);
}

extern "C" __attribute__((visibility("default")))
void oh_rs_flush_transaction() {
    OH_BR_IPC_SCOPE("oh_rs_flush_transaction", "");
    // Triggers RSTransactionProxy::FlushImplicitTransaction which commits
    // pending RSCommand batch (createNode / setBounds / setAlpha / ...)
    // to RenderService via RSIClientToRenderConnection::CommitTransaction.
    OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
}

// 2026-05-11 G2.14al — bridge AOSP SurfaceControl.Transaction.setOpaque to OH.
// Java side: SurfaceControl.Transaction.setOpaque(sc, isOpaque) compiles to
//   nativeSetFlags(tx, sc, isOpaque ? SURFACE_OPAQUE : 0, SURFACE_OPAQUE=0x02)
// android_view_SurfaceControl.cpp SC_nativeSetFlags extracts the opaque bit
// and forwards here via dlsym RTLD_DEFAULT (same indirection pattern as
// oh_rs_set_layer_alpha / oh_rs_set_layer_visible — keeps liboh_android_
// runtime.so independent of OH C++ headers).
//
// OH equivalent: RSSurfaceNode::SetSurfaceBufferOpaque(bool isOpaque).
// Without this hint OH RS composes the layers underneath (the OH SCB
// starting/leash window stack, 720×1136 white), letting their white show
// through transparent helloworld surface even when hwui has drawn opaque
// TextView content into the buffer.
extern "C" __attribute__((visibility("default")))
void oh_rs_set_layer_opaque(int32_t sessionId, int32_t isOpaque) {
    OH_BR_IPC_SCOPE("oh_rs_set_layer_opaque",
                    "session=%{public}d isOpaque=%{public}d",
                    sessionId, isOpaque);
    auto node = oh_adapter::OHWindowManagerClient::getInstance()
                    .getRSSurfaceNode(sessionId);
    if (!node) return;
    node->SetSurfaceBufferOpaque(isOpaque != 0);
}

// ============================================================
// 2026-05-08 G2.14aa: ASurfaceControl/ASurfaceTransaction NDK 真桥 helpers
//
// AOSP hwui RenderThread (ASurfaceControlFunctions ctor in
// frameworks/base/libs/hwui/renderthread/RenderThread.cpp) dlopen("libandroid.so")
// + dlsym 9 个 NDK 符号。device 上 libandroid.so 是 liboh_android_runtime.so
// 的 symlink，需要在那边 export 9 个 wrapper；wrapper 通过 dlsym(RTLD_DEFAULT,
// "oh_rs_*") 找下面的 helper 真桥到 OH RS。
//
// OH RS = SurfaceFlinger 等价：
//   ASurfaceControl     ↔ RSSurfaceNode (sptr<>)
//   ASurfaceTransaction ↔ RSTransaction (隐式 transaction via RSTransactionProxy)
// ============================================================

/**
 * Create a sub-RSSurfaceNode (non-window). hwui WebViewFunctorManager 用此
 * 创建 child surface; helloworld 主路径不真触发。
 *
 * @return opaque RSSurfaceNode* (caller stores as void*; release via
 *         oh_rs_destroy_subsurface)
 */
extern "C" __attribute__((visibility("default")))
void* oh_rs_create_subsurface(const char* name) {
    OH_BR_IPC_SCOPE("oh_rs_create_subsurface", "name=%{public}s", name ? name : "(null)");
    OHOS::Rosen::RSSurfaceNodeConfig cfg;
    cfg.SurfaceNodeName = (name && *name) ? name : "adapter_subsurface";
    auto node = OHOS::Rosen::RSSurfaceNode::Create(cfg, /*isWindow=*/false);
    if (!node) {
        LOGE("oh_rs_create_subsurface: RSSurfaceNode::Create failed for %s", cfg.SurfaceNodeName.c_str());
        return nullptr;
    }
    // 转 sptr → raw 指针给 C ABI；wrapper 用 holder map 维持 sptr 引用
    auto* holder = new std::shared_ptr<OHOS::Rosen::RSSurfaceNode>(node);
    return holder;
}

/**
 * Release sub-RSSurfaceNode. Decrements sptr refcount (likely destroy).
 */
extern "C" __attribute__((visibility("default")))
void oh_rs_destroy_subsurface(void* opaque) {
    OH_BR_IPC_SCOPE("oh_rs_destroy_subsurface", "holder=%p", opaque);
    if (!opaque) return;
    delete reinterpret_cast<std::shared_ptr<OHOS::Rosen::RSSurfaceNode>*>(opaque);
}

/**
 * Register buffer-available listener on RSSurfaceNode. AOSP hwui
 * CanvasContext.cpp 通过 ASurfaceControl_registerSurfaceStatsListener 让
 * RenderThread 知道 buffer ready；OH 等价是 RSSurfaceNode::RegisterBufferAvailableListener。
 *
 * Callback 签名（hwui ASC_StatsListener）：
 *   void cb(void* context, int32_t controlFd, ASurfaceTransactionStats* stats)
 * 我们桥时 controlFd=0、stats=nullptr（OH 暂无 stats 等价；hwui 处理 null 安全）。
 */
extern "C" __attribute__((visibility("default")))
void oh_rs_register_buffer_listener(void* opaque,
                                     void (*cb)(void* /*context*/, int32_t /*ctlFd*/, void* /*stats*/),
                                     void* context) {
    OH_BR_IPC_SCOPE("oh_rs_register_buffer_listener",
                    "holder=%p cb=%p ctx=%p", opaque, (void*)cb, context);
    if (!opaque || !cb) return;
    auto* holder = reinterpret_cast<std::shared_ptr<OHOS::Rosen::RSSurfaceNode>*>(opaque);
    if (!*holder) return;
    // OH 7.0.0.18 public API 是 SetBufferAvailableCallback (signature: std::function<void()>)，
    // 内部走 RSRenderPipelineClient::RegisterBufferAvailableListener。一次只能 set 一个 cb。
    (*holder)->SetBufferAvailableCallback([cb, context]() {
        cb(context, 0, nullptr);
    });
}

// ============================================================
// 2026-06-28 [STAGE2-SURFACEVIEW] Child SurfaceView surface composition.
//
// Root cause (yue_refs/stage2_unity_run.md §12-13): a SurfaceView's EGL
// producer was resolved (via BBQ last-session fallback) to the MAIN window's
// single APP_WINDOW_NODE producer, which has no spare consumer for a 2nd EGL
// bind -> eglCreateWindowSurface EGL_BAD_ALLOC.  A naive *independent* child
// node gets standalone-prepared by RS -> marked COMPOSITION_CLIENT -> OH HDI
// rejects -> App SIGABRT (oh_surface_bridge.cpp:100-105).
//
// Correct composition mirrors ArkUI XComponent
// (rosen_render_xcomponent.cpp:85 = RSSurfaceNode::Create(cfg, isWindow=false)):
//   * DEFAULT-type (isWindow=false) self-drawing child node -> GPU-composited
//     INTO the parent window layer (no standalone HDI layer, so no
//     COMPOSITION_CLIENT rejection).
//   * AddChild under the WMS-registered APP_WINDOW_NODE so RS walks it as part
//     of the window subtree -> it gets an active RS consumer.
//   * SetBounds/SetFrame/SetVisible + flush, then hand its OWN producer surface
//     to the SurfaceView's EGL.  Its consumer is live -> eglCreateWindowSurface
//     can allocate.
// Keyed per childKey (the BLASTBufferQueue ptr) so repeat update() calls reuse.
// ============================================================
namespace {
struct ChildSurfaceEntry {
    std::shared_ptr<OHOS::Rosen::RSSurfaceNode> node;
    OHOS::sptr<OHOS::Surface> producer;
    void* aospAnw = nullptr;
};
std::mutex g_childSurfaceMutex;
std::map<int64_t, ChildSurfaceEntry> g_childSurfaces;
}  // namespace
}  // namespace oh_adapter

extern "C" __attribute__((visibility("default")))
void* oh_rs_get_child_surface_window(int32_t sessionId, int64_t childKey,
                                     int32_t width, int32_t height) {
    OH_BR_IPC_SCOPE("oh_rs_get_child_surface_window",
                    "session=%{public}d childKey=0x%{public}llx w=%{public}d h=%{public}d",
                    sessionId, (unsigned long long)childKey, width, height);
    {
        std::lock_guard<std::mutex> lk(oh_adapter::g_childSurfaceMutex);
        auto cit = oh_adapter::g_childSurfaces.find(childKey);
        if (cit != oh_adapter::g_childSurfaces.end() && cit->second.aospAnw) {
            return cit->second.aospAnw;
        }
    }
    // Parent = WMS-registered main window node (already in RS display tree).
    auto parent = oh_adapter::OHWindowManagerClient::getInstance().getRSSurfaceNode(sessionId);
    if (!parent) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: no parent RSSurfaceNode for session %{public}d",
                   sessionId);
        return nullptr;
    }
    if (width <= 0 || height <= 0) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: invalid resolved extent "
                   "%{public}dx%{public}d session=%{public}d",
                   width, height, sessionId);
        return nullptr;
    }

    OHOS::Rosen::RSSurfaceNodeConfig cfg;
    cfg.SurfaceNodeName = "AdapterSurfaceView";
    // isWindow=false => DEFAULT self-drawing node, GPU-composited into parent
    // layer (mirrors ArkUI XComponent rosen_render_xcomponent.cpp:85).
    auto child = OHOS::Rosen::RSSurfaceNode::Create(cfg, /*isWindow=*/false);
    if (!child) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: RSSurfaceNode::Create failed");
        return nullptr;
    }
    child->SetBounds(0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
    child->SetFrame(0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
    child->SetVisible(true);
    // Match the proven OpenHarmony XComponent/Tuanjie surface route: this is
    // one self-drawing hardware layer whose producer belongs to Unity and whose
    // consumer belongs to RenderService. Without these two properties RS never
    // establishes the child BufferQueue as a live XCOM presentation target.
    child->SetIsNotifyUIBufferAvailable(true);
    child->SetHardwareEnabled(true, OHOS::Rosen::SelfDrawingNodeType::XCOM);
    // Add to the window subtree so RS composites it (gives it a live consumer).
    parent->AddChild(child, -1);
    OHOS::Rosen::RSTransaction::FlushImplicitTransaction();

    auto producer = child->GetSurface();
    if (!producer) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: child GetSurface() null");
        return nullptr;
    }
    producer->SetDefaultWidthAndHeight(width, height);
    producer->SetQueueSize(3);
    OHNativeWindow* nw = ::CreateNativeWindowFromSurface(&producer);
    if (!nw) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: CreateNativeWindowFromSurface failed");
        return nullptr;
    }
    // Set geometry on the exact NativeWindow instance that Unity will dequeue
    // from. ProducerSurface defaults alone do not update this window-local
    // configuration on the OH 6.1 RS path.
    int32_t geometryRc = ::OH_NativeWindow_NativeWindowHandleOpt(
        nw, OH_NW_OP_SET_BUFFER_GEOMETRY, width, height);
    if (geometryRc != 0) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: initial geometry "
                   "%{public}dx%{public}d failed rc=%{public}d",
                   width, height, geometryRc);
        return nullptr;
    }
    void* aospAnw = ::oh_anw_wrap(nw);
    if (!aospAnw) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: oh_anw_wrap failed");
        return nullptr;
    }
    {
        std::lock_guard<std::mutex> lk(oh_adapter::g_childSurfaceMutex);
        auto& e = oh_adapter::g_childSurfaces[childKey];
        e.node = child;
        e.producer = producer;  // keep sptr alive past this scope
        e.aospAnw = aospAnw;
    }
    HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_WindowMgrClient",
               "oh_rs_get_child_surface_window: session=%{public}d childKey=0x%{public}llx "
               "child composed uniqueId=0x%{public}llx anw=%{public}p (%{public}dx%{public}d)",
               sessionId, (unsigned long long)childKey,
               (unsigned long long)producer->GetUniqueId(), aospAnw, width, height);
    return aospAnw;
}

namespace oh_adapter {

// 2026-05-02 G2.14r: bridge from sessionId to OHNativeWindow*.  Cached
// per-session so repeated calls return the same pointer (Java Surface lifecycle
// expects a stable native object).
void* OHWindowManagerClient::getOhNativeWindow(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.getOhNativeWindow", "session=%{public}d", sessionId);
    std::lock_guard<std::mutex> lock(sessionMutex_);
    auto it = sessions_.find(sessionId);
    if (it == sessions_.end()) {
        LOGE("getOhNativeWindow: unknown sessionId=%d", sessionId);
        return nullptr;
    }
    if (it->second.ohNativeWindow != nullptr) {
        return it->second.ohNativeWindow;
    }
    if (!it->second.surfaceNode) {
        LOGE("getOhNativeWindow: sessionId=%d has no RSSurfaceNode", sessionId);
        return nullptr;
    }
    // PRESENT-FIX: the SceneSession's APP_WINDOW_NODE is a WMS container;
    // unirender does not consume normal Activity content from its own
    // producer. A self-drawing child is the native OH content route used by
    // XComponent/SurfaceView and has a live consumer. Preserve the V7
    // session/token/stage route and change only the producer handed to hwui.
    if (!it->second.contentChildNode) {
        OHOS::Rosen::RSSurfaceNodeConfig childCfg;
        childCfg.SurfaceNodeName = "AdapterActivityContent";
        auto child = OHOS::Rosen::RSSurfaceNode::Create(childCfg, /*isWindow=*/false);
        if (!child) {
            LOGE("getOhNativeWindow: content child Create failed sessionId=%d", sessionId);
            return nullptr;
        }
        const float cw = it->second.reqWidth > 0
                ? static_cast<float>(it->second.reqWidth) : 1200.0f;
        const float ch = it->second.reqHeight > 0
                ? static_cast<float>(it->second.reqHeight) : 1920.0f;
        child->SetBounds(0.0f, 0.0f, cw, ch);
        child->SetFrame(0.0f, 0.0f, cw, ch);
        child->SetVisible(true);
        child->SetIsNotifyUIBufferAvailable(true);
        it->second.surfaceNode->AddChild(child, -1);
        OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
        it->second.contentChildNode = child;
        LOGI("getOhNativeWindow: created self-drawing content child=%p "
             "under V7 window node (%dx%d) sessionId=%d",
             child.get(), static_cast<int>(cw), static_cast<int>(ch), sessionId);
    }
    // 2026-05-08 G2.14ab: store sptr<Surface> in SessionEntry (not local var)
    // so its lifetime equals session lifetime. hwui RenderThread holds
    // OHNativeWindow* and async IncStrongRef on the backing ProducerSurface;
    // a local sptr would release on return, leading to use-after-free
    // (libsurface RefBase::IncStrongRef on 0xcafe5c02 poisoned memory).
    if (!it->second.producerSurface) {
        it->second.producerSurface = it->second.contentChildNode->GetSurface();
        if (it->second.producerSurface) {
            const int32_t bw = it->second.reqWidth > 0 ? it->second.reqWidth : 1200;
            const int32_t bh = it->second.reqHeight > 0 ? it->second.reqHeight : 1920;
            it->second.producerSurface->SetDefaultWidthAndHeight(bw, bh);
            it->second.producerSurface->SetQueueSize(3);
            LOGI("getOhNativeWindow: seeded content child producer %dx%d "
                 "queueSize=3 sessionId=%d", bw, bh, sessionId);
        }
    }
    if (!it->second.producerSurface) {
        LOGE("getOhNativeWindow: sessionId=%d RSSurfaceNode has no producer surface", sessionId);
        return nullptr;
    }
    // 2026-05-12 G2.14aw probe A.1 baseline: producer 出身证据.
    // surfaceNode->GetSurface() 拿到的 ProducerSurface 真身 + RS 服务端注册的 uniqueId,
    // 后面 wrap/swap 路径上的所有 uniqueId 都应等于此值才算同源.
    LOGI("getOhNativeWindow[probe-baseline]: sessionId=%d surfaceNode=%p surfaceNodeId=%lld "
         "producerSurface_sptrAddr=%p producerSurface_refPtr=%p uniqueId=0x%llx",
         sessionId, it->second.surfaceNode.get(),
         (long long)it->second.surfaceNodeId,
         (void*)&it->second.producerSurface,
         it->second.producerSurface.GetRefPtr(),
         (unsigned long long)it->second.producerSurface->GetUniqueId());
    // CreateNativeWindowFromSurface signature: OHNativeWindow* fn(void* pSurface)
    // expects address of sptr<Surface> (not the raw surface ptr).  See
    // foundation/graphic/graphic_surface/surface/src/native_window.cpp.
    // Pass address of SessionEntry-held sptr so the backing producer survives
    // hwui's async refcount increments.
    OHNativeWindow* nw = ::CreateNativeWindowFromSurface(&it->second.producerSurface);
    if (!nw) {
        LOGE("getOhNativeWindow: CreateNativeWindowFromSurface failed for sessionId=%d", sessionId);
        return nullptr;
    }
    // HanBing/AlexBridge S23 cut4: set geometry on the exact OH NativeWindow
    // handed to the AOSP-ABI shim. This prevents the first RenderThread dequeue
    // from requesting Buffer[0 0].
    {
        int32_t gw = it->second.reqWidth > 0 ? it->second.reqWidth : 1200;
        int32_t gh = it->second.reqHeight > 0 ? it->second.reqHeight : 1920;
        int32_t grc = ::OH_NativeWindow_NativeWindowHandleOpt(
            nw, OH_NW_OP_SET_BUFFER_GEOMETRY, gw, gh);
        LOGI("getOhNativeWindow: SET_BUFFER_GEOMETRY %dx%d rc=%d sessionId=%d",
             gw, gh, grc, sessionId);
    }
    // 2026-05-12 G2.14aw probe A.1: post-CreateNativeWindowFromSurface uniqueId.
    // OH NativeWindow internally copies sptr<Surface>, so uniqueId here MUST match the baseline above.
    // Mismatch ⇒ CreateNativeWindowFromSurface silently swapped the backing surface (very unlikely
    // but worth checking once — if equal we can drop this log later).
    {
        uint64_t uidPost = 0;
        int32_t qrc = ::OH_NativeWindow_GetSurfaceId(nw, &uidPost);
        LOGI("getOhNativeWindow[probe-postCreate]: sessionId=%d nw=%p uniqueId=0x%llx (rc=%d)",
             sessionId, (void*)nw, (unsigned long long)uidPost, qrc);
    }
    // 2026-05-09 G2.14ae: hwui treats ANativeWindow as an AOSP POD struct
    // with a function-pointer table at fixed offsets (system/window.h).
    // OH NativeWindow is a C++ virtual class deriving from RefBase with
    // sptr<Surface> / unordered_map / atomic members — completely
    // incompatible layout. Returning the raw OH handle to hwui caused
    // SIGSEGV in CanvasContext::setupPipelineSurface where hwui dereferenced
    // an offset that, on AOSP, would be common.reserved[2] but on OH falls
    // inside RefBase internals.
    //
    // Wrap the OH handle in an adapter-allocated AOSP-ABI-compatible
    // ANativeWindow struct whose 10 function pointers route to wrappers
    // calling OH_NativeWindow_* NDK equivalents. hwui sees the AOSP ABI
    // it expects; OH-side details stay hidden behind the wrapper.
    //
    // Reference: doc/graphics_rendering_design.html §7.11.
    void* aospAnw = ::oh_anw_wrap(reinterpret_cast<OHNativeWindow*>(nw));
    if (!aospAnw) {
        LOGE("getOhNativeWindow: oh_anw_wrap failed for sessionId=%d", sessionId);
        return nullptr;
    }
    it->second.ohNativeWindow = aospAnw;  // hwui-facing handle (AOSP ABI)
    LOGI("getOhNativeWindow: sessionId=%d -> AOSP-compat ANativeWindow=%p "
         "(oh=%p, surfaceNodeId=%lld)",
         sessionId, aospAnw, (void*)nw, (long long)it->second.surfaceNodeId);
    return aospAnw;
}

}  // namespace oh_adapter
