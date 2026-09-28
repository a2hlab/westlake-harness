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
#include "display_manager.h"
#include "display.h"
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
extern "C" void OH_NativeWindow_DestroyNativeWindow(OHNativeWindow* window);
// [S23 cut4 2026-07-09] Seed the REAL OH NativeWindow's window->config geometry
// directly. Proven: ProducerSurface::SetDefaultWidthAndHeight does NOT propagate
// to the shared server BufferQueue default (both seeded self-draw surfaces still
// alloc Buffer[0 0] -> NO_BUFFER 50002000 storm). native_window.cpp:229
// NativeWindowRequestBuffer reads window->config.{width,height}, which is set by
// OH_NativeWindow_NativeWindowHandleOpt(SET_BUFFER_GEOMETRY,w,h) — a DIFFERENT
// path than the (proven-inert) default-queue one. Variadic per
// external_window.h; SET_BUFFER_GEOMETRY == 0 (OH_NativeWindowOperation).
extern "C" int32_t OH_NativeWindow_NativeWindowHandleOpt(OHNativeWindow* window, int code, ...);
#ifndef OH_NW_OP_SET_BUFFER_GEOMETRY
#define OH_NW_OP_SET_BUFFER_GEOMETRY 0
#endif
// [S23 cut6 2026-07-09] in-process Unity present surface (surface_oh_helper.cpp,
// same .so). Creates an in-process BufferQueue whose CONSUMER default geometry is
// set to w x h (the sole authority over BufferQueue alloc — client producer side
// proven zero-authority over RS self-draw nodes across cut1-5). Its drain listener
// zero-copy-presents each Unity frame to presentTargetRaw (on-screen RS node
// producer) via AttachBufferToQueue+FlushBuffer. Returns the Unity-facing OHOS::Surface*.
extern "C" void* surface_oh_create_unity_present_surface(void* presentTargetRaw,
                                                         int32_t w, int32_t h);

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
extern "C" void oh_anw_destroy(struct ANativeWindow* aosp);
extern "C" OHNativeWindow* oh_anw_get_oh(struct ANativeWindow* aosp);
extern "C" int oh_anw_configure_direct_path(struct ANativeWindow* aosp,
                                             int32_t sessionId,
                                             uint64_t generation,
                                             int32_t width,
                                             int32_t height);
extern "C" int oh_anw_update_direct_path_geometry(struct ANativeWindow* aosp,
                                                   uint64_t generation,
                                                   int32_t width,
                                                   int32_t height);
extern "C" int oh_anw_mark_surface_lost(struct ANativeWindow* aosp,
                                         uint64_t generation);
extern "C" void oh_rs_release_session_surfaces(int32_t sessionId,
                                                uint64_t generation);
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

namespace {
std::atomic<uint64_t> g_nextSurfaceGeneration{1};

bool resolveSurfaceExtent(int32_t requestedWidth, int32_t requestedHeight,
                          int32_t* resolvedWidth, int32_t* resolvedHeight)
{
    if (!resolvedWidth || !resolvedHeight) return false;
    int32_t width = requestedWidth;
    int32_t height = requestedHeight;
    if (width <= 0 || height <= 0) {
        auto display = OHOS::Rosen::DisplayManager::GetInstance().GetDefaultDisplay();
        if (!display) return false;
        if (width <= 0) width = static_cast<int32_t>(display->GetWidth());
        if (height <= 0) height = static_cast<int32_t>(display->GetHeight());
    }
    if (width <= 0 || height <= 0) return false;
    *resolvedWidth = width;
    *resolvedHeight = height;
    return true;
}
}  // namespace

// §3.1.4.1 — Android LayoutParams.type → OH WindowType.
//
// Android main DecorView (TYPE_BASE_APPLICATION=1 / TYPE_APPLICATION=2 /
// TYPE_APPLICATION_STARTING=3) is downgraded to OH WINDOW_TYPE_APP_SUB_WINDOW
// because OH manages the actual main window through the Ability lifecycle —
// CreateAndConnectSpecificSession is OH's IPC for sub windows / system windows
// only, and would reject a main-window-typed property.
//
// Casting Android's enum value directly to OH WindowType (the pre-fix behavior)
// dropped values 2/3/etc. into OH enum gaps -> WindowSessionProperty
// Marshalling rejected them -> server returned ERR_INVALID_DATA -> proxy logged
// "SendRequest failed". This map is the actual G2.13 fix.
static OHOS::Rosen::WindowType mapAndroidWindowType(int32_t androidType) {
    using OHOS::Rosen::WindowType;
    // G2.14c (legacy mode) — main app DecorView maps to APP_MAIN_WINDOW (1).
    // SUB_WINDOW (1001) requires parent windowId via property->SetParentId,
    // which adapter can't supply for a top-level Activity. Legacy WMS's
    // CheckSystemWindowPermission allows APP_MAIN_WINDOW for any caller (it
    // only blocks SystemWindow types 2000+ for non-SA callers).
    switch (androidType) {
        case 1:        // TYPE_BASE_APPLICATION
        case 2:        // TYPE_APPLICATION
        case 3:        // TYPE_APPLICATION_STARTING
            return WindowType::WINDOW_TYPE_APP_MAIN_WINDOW;
        // Real sub windows must have parent set explicitly by caller; for
        // now downgrade to MAIN type as well — adapter doesn't yet plumb
        // parent linkage for Android sub windows.
        case 1000:     // TYPE_APPLICATION_PANEL
        case 1001:     // TYPE_APPLICATION_MEDIA
        case 1002:     // TYPE_APPLICATION_SUB_PANEL
        case 1003:     // TYPE_APPLICATION_ATTACHED_DIALOG
            return WindowType::WINDOW_TYPE_APP_MAIN_WINDOW;
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
    LOGI("Connecting to OH IWindowManager (legacy) via SA %d ...", SCENE_SESSION_MANAGER_ID);

    auto samgr = OHOS::SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgr == nullptr) {
        LOGE("Failed to get SystemAbilityManager");
        return false;
    }

    // SA 4606 = WINDOW_MANAGER_SERVICE_ID. On this OH 7.0.0.18 build (legacy
    // mode, window_manager_use_sceneboard=false), this SA hosts
    // WindowManagerService which exposes IWindowManager directly. Single
    // iface_cast — no 3-hop chain needed.
    ssmProxy_ = samgr->GetSystemAbility(SCENE_SESSION_MANAGER_ID);
    if (ssmProxy_ == nullptr) {
        LOGE("SAMGR returned null for SA %d", SCENE_SESSION_MANAGER_ID);
        return false;
    }

    LOGI("Connected to IWindowManager (legacy) via SA %d", SCENE_SESSION_MANAGER_ID);
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

// Android LayoutParams flags (AOSP 14 / WindowManager.java) that the Java-side
// SUPPORTED_LAYOUT_FLAGS allowlist may pass through.  Only flags with a direct
// OH WindowProperty equivalent are mapped here; the rest are accepted as no-op
// because AOSP PhoneWindow.generateLayout() sets them for ordinary Activities
// and rejecting them would prevent any app window from opening.
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

static void applyAndroidFlagsToWindowProperty(int32_t androidFlags,
                                              OHOS::sptr<OHOS::Rosen::WindowProperty>& property) {
    // Only flags that are explicitly allowlisted by Java SUPPORTED_LAYOUT_FLAGS
    // reach native.  Log any bits that have no direct OH WindowProperty mapping
    // so the no-op decision is auditable.
    int32_t mappedMask = ANDROID_FLAG_FULLSCREEN
                       | ANDROID_FLAG_KEEP_SCREEN_ON
                       | ANDROID_FLAG_SHOW_WHEN_LOCKED
                       | ANDROID_FLAG_TURN_SCREEN_ON
                       | ANDROID_FLAG_DISMISS_KEYGUARD;
    int32_t noOpAllowedMask = ANDROID_FLAG_HARDWARE_ACCELERATED
                            | ANDROID_FLAG_LAYOUT_IN_SCREEN
                            | ANDROID_FLAG_LAYOUT_INSET_DECOR
                            | ANDROID_FLAG_SPLIT_TOUCH
                            | ANDROID_FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS;
    int32_t loggedMask = mappedMask | noOpAllowedMask;
    int32_t extraFlags = androidFlags & ~loggedMask;
    if (extraFlags != 0) {
        LOGW("createSession: unexpected LayoutParams flags 0x%{public}x reached native; "
             "Java allowlist and native mapping are out of sync", extraFlags);
    }
    int32_t noOpFlags = androidFlags & noOpAllowedMask;
    if (noOpFlags != 0) {
        LOGI("createSession: allowed LayoutParams flags 0x%{public}x have no OH "
             "WindowProperty mapping on the legacy path; accepted as no-op",
             noOpFlags);
    }

    property->SetKeepScreenOn((androidFlags & ANDROID_FLAG_KEEP_SCREEN_ON) != 0);
    property->SetTurnScreenOn((androidFlags & ANDROID_FLAG_TURN_SCREEN_ON) != 0);

    // OH WindowProperty exposes lock-screen visibility, but no separate bit
    // for Android's legacy "dismiss only a non-secure keyguard" behavior.
    // Map either request to the closest security-preserving OH behavior:
    // visibility above the lock screen without disabling or bypassing a secure
    // lock. Unknown Android bits still fail in the Java allowlist.
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
                    "bundle=%{public}s ability=%{public}s name=%{public}s w=%{public}d h=%{public}d flags=0x%{public}x ohToken=0x%{public}llx",
                    bundleName.c_str(), abilityName.c_str(), windowName.c_str(),
                    requestedWidth, requestedHeight,
                    androidFlags,
                    (unsigned long long)ohTokenAddr);
    // §3.1.5.6.2 — wsErr defaults capture the most likely cause of early-exit.
    OHWindowSession result;
    result.wsErr = static_cast<int32_t>(OHOS::Rosen::WSError::WS_ERROR_IPC_FAILED);
    int32_t resolvedWidth = 0;
    int32_t resolvedHeight = 0;
    if (!resolveSurfaceExtent(requestedWidth, requestedHeight,
                              &resolvedWidth, &resolvedHeight)) {
        LOGE("createSession: no valid requested/display extent (%dx%d)",
             requestedWidth, requestedHeight);
        result.wsErr = 1001;
        return result;
    }

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

    // G2.14c — legacy IWindow callback stub (single per-window endpoint, no
    // separate ISessionStage/IWindowEventChannel split).
    OHOS::sptr<WindowCallbackAdapter> windowCallback =
        new WindowCallbackAdapter(jvm, androidWindow);

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

    // Legacy WindowProperty (NOT V7 WindowSessionProperty). Fewer fields,
    // no SessionInfo / TokenState dance.
    OHOS::sptr<OHOS::Rosen::WindowProperty> property = new OHOS::Rosen::WindowProperty();
    property->SetWindowName(windowName);
    property->SetWindowType(ohType);
    // AOSP DecorView assumes the window can cover the whole display; the
    // distinction between a fullscreen and a non-fullscreen Activity is driven
    // by whether the status-bar avoid area is retained after AddWindow.
    property->SetWindowMode(OHOS::Rosen::WindowMode::WINDOW_MODE_FULLSCREEN);
    OHOS::Rosen::Rect rect{0, 0,
        static_cast<uint32_t>(resolvedWidth), static_cast<uint32_t>(resolvedHeight)};
    property->SetWindowRect(rect);
    property->SetRequestRect(rect);  // legacy WMS uses requestRect for AddWindow
    property->SetOriginRect(rect);
    property->SetDisplayId(displayId);

    // §3.1.4.1 / E02 — apply allowed Android LayoutParams flags to OH property.
    // FLAG_FULLSCREEN is consumed below by controlling the NEED_AVOID state.
    applyAndroidFlagsToWindowProperty(androidFlags, property);

    // Bug B fix (2026-05-18): SetTokenState(true) when valid abilityToken exists.
    //
    // Root cause: WMS server stub (foundation/window/window_manager/wmserver/src/
    // zidl/window_manager_stub.cpp:49-51) gates Parcel token deserialization on
    // property.GetTokenState():
    //   sptr<IRemoteObject> token = nullptr;
    //   if (windowProperty && windowProperty->GetTokenState()) {
    //       token = data.ReadRemoteObject();
    //   }
    //   ... CreateWindow(..., token);
    // adapter has been passing token through wmsProxy->CreateWindow but keeping
    // property.tokenState_=false (default) → WMS server side reads token=nullptr
    // → node->abilityToken_=nullptr → FindWindowNodeWithToken(token) returns null
    // both for (a) WindowController::CreateWindow's "replace starting window
    // with main window" replacement path (line 268), and (b) CancelStartingWindow
    // on ability death (window_controller.cpp:117). Net effect: every cold start
    // creates an orphan leashWindow+startingWindow pair that force-stop never
    // cleans up — the "white block covers desktop" leak.
    //
    // OH native WindowImpl::Create (~wm/src/window_impl.cpp:1554-1557) sets
    // tokenState_=true whenever context_->GetToken() returns non-null. We mirror
    // that. The earlier "§3.1.4.6.6 keep TokenState=false matrix" comment was
    // based on an assumption empirically invalidated by hilog evidence.
    if (token != nullptr) {
        property->SetTokenState(true);
    } else {
        property->SetTokenState(false);
    }

    // 2026-07-26: Pre-set NEED_AVOID for ALL windows before AddWindow.
    // When CreateWindow replaces an OH starting window, the inherited leash
    // is safe-area sized.  Pre-setting NEED_AVOID lets AddWindow's layout
    // pass compute a safe-area winRect that matches the leash, producing a
    // real rect diff when we later clear the flag.  Without this pre-set,
    // AddWindow copies the requested full rect into a safe-area leash with no
    // transition, so leash SetBounds is never triggered and the top/bottom
    // black bands remain.  This applies to both fullscreen and non-fullscreen
    // cold-start paths.
    const uint32_t mappedOhWindowFlags = property->GetWindowFlags();
    property->SetWindowFlags(mappedOhWindowFlags | static_cast<uint32_t>(
        OHOS::Rosen::WindowFlag::WINDOW_FLAG_NEED_AVOID));

    auto wmsInterface = OHOS::iface_cast<OHOS::Rosen::IWindowManager>(ssmProxy_);
    if (wmsInterface == nullptr) {
        LOGE("createSession: Failed to cast to IWindowManager");
        result.wsErr = 1001;
        return result;
    }

    // Step 1: CreateWindow — pass our IWindow stub IN; server allocates windowId.
    uint32_t windowId = 0;
    OHOS::sptr<OHOS::Rosen::IWindow> windowProxy(windowCallback.GetRefPtr());
    auto retCreate = wmsInterface->CreateWindow(windowProxy, property, surfaceNode,
                                                 windowId, token);
    if (retCreate != OHOS::Rosen::WMError::WM_OK) {
        LOGE("createSession: IWindowManager::CreateWindow failed ret=%{public}d",
             static_cast<int>(retCreate));
        result.wsErr = static_cast<int32_t>(retCreate);
        return result;
    }
    LOGI("createSession: CreateWindow OK, windowId=%{public}u", windowId);

    // Step 2: AddWindow — actually display the window. WMS reads
    // property->GetWindowId() server-side; out-param windowId from CreateWindow
    // doesn't auto-propagate, so we must SetWindowId on the property before
    // sending it through the AddWindow IPC.
    property->SetWindowId(windowId);
    auto retAdd = wmsInterface->AddWindow(property);
    if (retAdd != OHOS::Rosen::WMError::WM_OK) {
        LOGE("createSession: IWindowManager::AddWindow failed ret=%{public}d (windowId=%{public}u)",
             static_cast<int>(retAdd), windowId);
        result.wsErr = static_cast<int32_t>(retAdd);
        wmsInterface->RemoveWindow(windowId, true);  // cleanup partial
        return result;
    }

    // Clear NEED_AVOID after AddWindow for ALL windows so the leash
    // transitions from the safe-area state (established above and inherited
    // from the starting window leash) to the full requested display rect.
    // The pre-set + clear sequence produces a real rect diff that drives
    // leash SetBounds for every cold start, eliminating top/bottom black
    // bands for both fullscreen and non-fullscreen Activities.
    property->SetWindowFlags(mappedOhWindowFlags);
    auto retFs = wmsInterface->UpdateProperty(
        property, OHOS::Rosen::PropertyChangeAction::ACTION_UPDATE_FLAGS);
    if (retFs != OHOS::Rosen::WMError::WM_OK) {
        // P2: returning a "successful" session while the OH leash remains
        // safe-area would make AOSP layout and OH rendering disagree.  Treat
        // this as a creation failure, clean up the partial window, and surface
        // the error to Java.
        LOGE("createSession: clear NEED_AVOID failed rc=%{public}d; destroying partial window",
             static_cast<int>(retFs));
        wmsInterface->RemoveWindow(windowId, true);
        wmsInterface->DestroyWindow(windowId, false);
        result.wsErr = static_cast<int32_t>(retFs);
        return result;
    }
    LOGI("createSession: cleared NEED_AVOID -> full display layout");

    // All successful windows are full-sized on this legacy path.  Return the
    // requested rect as attachedFrame so AOSP and OH agree.  When real
    // safe-area/insets plumbing is added, this will be replaced by a
    // WMS-side rect query.
    OHOS::Rosen::Rect actualRect { 0, 0,
        static_cast<uint32_t>(resolvedWidth),
        static_cast<uint32_t>(resolvedHeight) };
    LOGI("createSession: attachedFrame=[0,0,%{public}u,%{public}u]",
         actualRect.width_, actualRect.height_);

    int64_t surfaceNodeId = static_cast<int64_t>(surfaceNode->GetId());
    int32_t persistentId = static_cast<int32_t>(windowId);

    int32_t sessionId;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        sessionId = persistentId > 0 ? persistentId : nextSessionId_++;
        // Legacy path: sessionProxy/stageAdapter/eventChannel are unused.
        // Store windowCallback in stageAdapter slot (sptr type compatible
        // through reinterpret) — TODO P2: refactor SessionEntry to be
        // path-aware (legacy vs V7). For now, keep stage/channel null and
        // hold windowCallback separately via static map keyed by sessionId.
        SessionEntry entry{};
        entry.sessionId = sessionId;
        entry.surfaceNodeId = surfaceNodeId;
        entry.sessionProxy = nullptr;
        entry.stageAdapter = nullptr;
        entry.eventChannel = nullptr;
        entry.surfaceNode = surfaceNode;
        // 2026-05-19: store WMS-side identity + property + visibility state
        // for hideWindow / showWindow helpers (counterpart to AddWindow above).
        entry.windowId = windowId;
        entry.windowProperty = property;
        entry.wmsShown = true;  // AddWindow above succeeded
        // 2026-06-29 PRESENT-FIX: remember requested size for the self-drawing
        // content child created lazily in getOhNativeWindow().
        entry.reqWidth = resolvedWidth;
        entry.reqHeight = resolvedHeight;
        entry.surfaceGeneration =
            g_nextSurfaceGeneration.fetch_add(1, std::memory_order_relaxed);
        sessions_[sessionId] = entry;
        // Keep windowCallback alive for the session's lifetime.
        static std::map<int32_t, OHOS::sptr<WindowCallbackAdapter>> windowCallbacks;
        windowCallbacks[sessionId] = windowCallback;
    }

    result.sessionId = sessionId;
    result.surfaceNodeId = static_cast<int32_t>(surfaceNodeId);
    result.displayId = displayId;
    result.width = resolvedWidth;
    result.height = resolvedHeight;
    result.frameLeft = actualRect.posX_;
    result.frameTop = actualRect.posY_;
    result.frameRight = actualRect.posX_ + static_cast<int32_t>(actualRect.width_);
    result.frameBottom = actualRect.posY_ + static_cast<int32_t>(actualRect.height_);
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

    // 2026-05-18: request input focus.  Without this, OH MMI server keeps the
    // launcher window as the focus target and routes all PointerEvents to it,
    // so HelloWorld's window receives 0 taps despite being on top.  Mirrors
    // OH native WindowImpl::RequestFocus() (foundation/window/window_manager/
    // wm/src/window_impl.cpp:2621).  Call it BEFORE subscribeMmi so that by
    // the time MMI begins routing, this window is already the focus target.
    {
        OHOS::Rosen::WMError focusRet = wmsInterface->RequestFocus(windowId);
        if (focusRet == OHOS::Rosen::WMError::WM_OK) {
            LOGI("createSession: RequestFocus(windowId=%{public}u) OK", windowId);
        } else {
            LOGW("createSession: RequestFocus(windowId=%{public}u) failed rc=%{public}d",
                 windowId, static_cast<int>(focusRet));
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

    if (width <= 0 || height <= 0) {
        LOGE("updateSessionRect: invalid geometry session=%d rect=[%d,%d,%d,%d]",
             sessionId, x, y, width, height);
        return -1;
    }

    OHOS::sptr<OHOS::Rosen::WindowProperty> property;
    uint64_t generation = 0;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end() || !it->second.windowProperty) return -2;
        property = it->second.windowProperty;
        generation = it->second.surfaceGeneration;
    }
    if (!connected_ || !ssmProxy_) return -3;
    auto wms = OHOS::iface_cast<OHOS::Rosen::IWindowManager>(ssmProxy_);
    if (!wms) return -4;

    OHOS::Rosen::Rect rect {
        x, y, static_cast<uint32_t>(width), static_cast<uint32_t>(height)
    };
    property->SetWindowRect(rect);
    property->SetRequestRect(rect);
    property->SetOriginRect(rect);
    auto wmRc = wms->UpdateProperty(
        property, OHOS::Rosen::PropertyChangeAction::ACTION_UPDATE_RECT);
    if (wmRc != OHOS::Rosen::WMError::WM_OK) {
        LOGE("updateSessionRect: WMS ACTION_UPDATE_RECT failed session=%d rc=%d",
             sessionId, static_cast<int32_t>(wmRc));
        return static_cast<int32_t>(wmRc);
    }

    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it == sessions_.end() ||
            it->second.surfaceGeneration != generation) {
            return -5;
        }
        it->second.reqWidth = width;
        it->second.reqHeight = height;
        if (it->second.surfaceNode) {
            it->second.surfaceNode->SetBounds(
                static_cast<float>(x), static_cast<float>(y),
                static_cast<float>(width), static_cast<float>(height));
            it->second.surfaceNode->SetFrame(
                static_cast<float>(x), static_cast<float>(y),
                static_cast<float>(width), static_cast<float>(height));
        }
        if (it->second.contentChildNode) {
            it->second.contentChildNode->SetBounds(
                0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
            it->second.contentChildNode->SetFrame(
                0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
        }
        if (it->second.producerSurface) {
            it->second.producerSurface->SetDefaultWidthAndHeight(width, height);
        }
        if (it->second.ohNativeWindow) {
            int trackRc = ::oh_anw_update_direct_path_geometry(
                reinterpret_cast<ANativeWindow*>(it->second.ohNativeWindow),
                generation, width, height);
            if (trackRc != 0) {
                LOGE("updateSessionRect: native-window geometry failed "
                     "session=%d generation=%llu rc=%d",
                     sessionId, (unsigned long long)generation, trackRc);
                return trackRc;
            }
        }
    }
    OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
    LOGI("updateSessionRect: committed session=%d generation=%llu rect=[%d,%d,%d,%d]",
         sessionId, (unsigned long long)generation, x, y, width, height);
    return 0;
}

int OHWindowManagerClient::notifyDrawingCompleted(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.notifyDrawingCompleted", "session=%{public}d", sessionId);
    // [Fn04.A13] legacy IWindowManager has no DrawingCompleted IPC.
    // On SceneBoard/ISession paths this would call ISession.DrawingCompleted().
    // On legacy WMS the completion semantic is carried by RSTransaction::FlushImplicitTransaction()
    // in OHSurfaceBridge::notifyDrawingCompleted().
    LOGI("[Fn04.A13] WMClient.notifyDrawingCompleted legacy no-op session=%{public}d", sessionId);
    return 0;
}

void OHWindowManagerClient::destroySession(int32_t sessionId) {
    OH_BR_IPC_SCOPE("WMClient.destroySession", "session=%{public}d", sessionId);

    OHOS::sptr<OHOS::Rosen::ISession> sessionProxy;
    uint64_t surfaceGeneration = 0;
    void* nativeWindow = nullptr;
    OHNativeWindow* rawNativeWindow = nullptr;
    {
        std::lock_guard<std::mutex> lock(sessionMutex_);
        auto it = sessions_.find(sessionId);
        if (it != sessions_.end()) {
            sessionProxy = it->second.sessionProxy;
            surfaceGeneration = it->second.surfaceGeneration;
            nativeWindow = it->second.ohNativeWindow;
            if (nativeWindow && surfaceGeneration != 0) {
                rawNativeWindow = ::oh_anw_get_oh(
                    reinterpret_cast<ANativeWindow*>(nativeWindow));
                ::oh_anw_mark_surface_lost(
                    reinterpret_cast<ANativeWindow*>(nativeWindow),
                    surfaceGeneration);
            }
            sessions_.erase(it);
        }
    }
    if (surfaceGeneration != 0) {
        ::oh_rs_release_session_surfaces(sessionId, surfaceGeneration);
    }
    if (rawNativeWindow) {
        ::OH_NativeWindow_DestroyNativeWindow(rawNativeWindow);
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
        alreadyShown = it->second.wmsShown;
        property = it->second.windowProperty;
        windowId = it->second.windowId;
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

uint64_t OHWindowManagerClient::getSurfaceGeneration(int32_t sessionId) {
    std::lock_guard<std::mutex> lock(sessionMutex_);
    auto it = sessions_.find(sessionId);
    return it == sessions_.end() ? 0 : it->second.surfaceGeneration;
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
    int32_t sessionId = -1;
    uint64_t generation = 0;
    uint64_t parentNodeId = 0;
    int32_t width = 0;
    int32_t height = 0;
    std::shared_ptr<OHOS::Rosen::RSSurfaceNode> parent;
    std::shared_ptr<OHOS::Rosen::RSSurfaceNode> node;
    OHOS::sptr<OHOS::Surface> producer;        // [cut6] on-screen RS node producer = present target
    OHOS::sptr<OHOS::Surface> unityProducer;   // [cut6] in-process Unity-facing producer
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
    // Parent = WMS-registered main window node (already in RS display tree).
    auto parent = oh_adapter::OHWindowManagerClient::getInstance().getRSSurfaceNode(sessionId);
    uint64_t generation =
        oh_adapter::OHWindowManagerClient::getInstance().getSurfaceGeneration(sessionId);
    if (!parent) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: no parent RSSurfaceNode for session %{public}d",
                   sessionId);
        return nullptr;
    }
    if (generation == 0 ||
        !oh_adapter::resolveSurfaceExtent(width, height, &width, &height)) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: no live generation/extent "
                   "session=%{public}d generation=%{public}llu requested=%{public}dx%{public}d",
                   sessionId, (unsigned long long)generation, width, height);
        return nullptr;
    }
    uint64_t parentNodeId = parent->GetId();
    {
        std::lock_guard<std::mutex> lk(oh_adapter::g_childSurfaceMutex);
        auto cit = oh_adapter::g_childSurfaces.find(childKey);
        if (cit != oh_adapter::g_childSurfaces.end()) {
            auto& existing = cit->second;
            if (existing.sessionId == sessionId &&
                existing.generation == generation &&
                existing.parentNodeId == parentNodeId &&
                existing.aospAnw) {
                if (existing.width != width || existing.height != height) {
                    existing.node->SetBounds(
                        0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
                    existing.node->SetFrame(
                        0.0f, 0.0f, static_cast<float>(width), static_cast<float>(height));
                    int rc = ::oh_anw_update_direct_path_geometry(
                        reinterpret_cast<ANativeWindow*>(existing.aospAnw),
                        generation, width, height);
                    if (rc != 0) return nullptr;
                    existing.width = width;
                    existing.height = height;
                    OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
                }
                return existing.aospAnw;
            }
            if (existing.aospAnw && existing.generation != 0) {
                auto* staleOh = ::oh_anw_get_oh(
                    reinterpret_cast<ANativeWindow*>(existing.aospAnw));
                ::oh_anw_mark_surface_lost(
                    reinterpret_cast<ANativeWindow*>(existing.aospAnw),
                    existing.generation);
                if (staleOh) ::OH_NativeWindow_DestroyNativeWindow(staleOh);
            }
            if (existing.parent && existing.node) {
                existing.parent->RemoveChild(existing.node);
            }
            oh_adapter::g_childSurfaces.erase(cit);
        }
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
    // [S22-G2.3 2026-07-09] golden class-2 acquire: a self-drawing (isWindow=false)
    // RSSurfaceNode is only scheduled/acquired by RS once it is told a UI buffer is
    // available. Without this, RS never排 drawable / never AcquireBuffer on this
    // producer -> buffers stay REQUESTED/half-allocated (NO_BUFFER 50002000) -> the
    // consumer (Mali via the bare OH window) dequeues a malformed buffer and derefs a
    // wild pointer inside libGLES_mali (UnityMain SIGSEGV). Enable notify so RS
    // properly acquires this self-draw producer's buffers. Single-variable first cut.
    child->SetIsNotifyUIBufferAvailable(true);
    // [S23 cut8 2026-07-09] THE missing 团结 lever: mark this self-drawing child as
    // an XCOM (XComponent) hardware layer. This is what ArkUI XComponent / libtuanjie
    // do (rosen_render_context.cpp CreateHardwareSurface: RSSurfaceNode::Create(
    // isWindow=false) + SetHardwareEnabled(true, XCOM)) and it is byte-for-byte why
    // 团结 (variant-2, com.tuanjie.unityshell) runs 60FPS on the SAME Mali without
    // the 0x0 alloc wall: RS assigns the node's BufferQueue geometry via the HWC
    // layer path (authoritative at node-establish time) instead of leaving an empty
    // producer default. This replaces cut6's in-process BufferQueue workaround (which
    // was racy: NO_BUFFER storm returned run-to-run) with the single-owner model —
    // producer(Unity EGL) and consumer(RenderService) are the two ends of ONE
    // RSSurfaceNode BufferQueue. cut6 code (surface_oh_create_unity_present_surface /
    // PresentDrainListener) is left in surface_oh_helper.cpp as a fallback, unused.
    child->SetHardwareEnabled(true, OHOS::Rosen::SelfDrawingNodeType::XCOM);
    // Add to the window subtree so RS composites it (gives it a live consumer).
    parent->AddChild(child, -1);
    OHOS::Rosen::RSTransaction::FlushImplicitTransaction();

    // [S23 cut8 2026-07-09] SINGLE-OWNER model (团结 / ArkUI XComponent, byte-exact):
    // hand Unity the child RS node's OWN producer surface. With SetHardwareEnabled(
    // XCOM) above, RS assigns this node's BufferQueue geometry via the HWC layer path,
    // so the producer allocates the resolved display geometry authoritatively
    // (no cut6 in-process BQ, no
    // consumer-side geometry race, no NO_BUFFER storm). producer(Unity EGL) and
    // consumer(RenderService) are the two ends of this ONE RSSurfaceNode's queue.
    auto producer = child->GetSurface();
    if (!producer) {
        HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window: child GetSurface() null");
        return nullptr;
    }
    producer->SetQueueSize(3);
    // Store the sptr in the session entry so the backing queue survives hwui/Unity's
    // async refcount churn (a local sptr would drop it). Wrap the bare OHNativeWindow*
    // in AdapterAnw for the AOSP ANativeWindow ABI face that bionic Unity + Java
    // Surface.mNativeObject require (the WALL7 eglCreateWindowSurface shim unwraps it
    // back to the bare OH nw for OH's EGL — an identity round-trip, ref L203/L209).
    OHNativeWindow* nw = nullptr;
    void* aospAnw = nullptr;
    {
        std::lock_guard<std::mutex> lk(oh_adapter::g_childSurfaceMutex);
        auto& e = oh_adapter::g_childSurfaces[childKey];
        e.sessionId = sessionId;
        e.generation = generation;
        e.parentNodeId = parentNodeId;
        e.width = width;
        e.height = height;
        e.parent = parent;
        e.node = child;
        e.producer = producer;                                         // single-owner RS node producer
        nw = ::CreateNativeWindowFromSurface(&e.producer);
        if (!nw) {
            parent->RemoveChild(child);
            oh_adapter::g_childSurfaces.erase(childKey);
            OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
            HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                       "oh_rs_get_child_surface_window: CreateNativeWindowFromSurface failed");
            return nullptr;
        }
        // Seed the exact producer instance before it is exposed through the
        // AOSP ANativeWindow face. SurfaceView has already resolved the live
        // child extent here; without this write Unity inherits the stale
        // full-height producer geometry on its first buffer allocation.
        int32_t geometryRc = ::OH_NativeWindow_NativeWindowHandleOpt(
            nw, OH_NW_OP_SET_BUFFER_GEOMETRY, width, height);
        if (geometryRc != 0) {
            ::OH_NativeWindow_DestroyNativeWindow(nw);
            parent->RemoveChild(child);
            oh_adapter::g_childSurfaces.erase(childKey);
            OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
            HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                       "oh_rs_get_child_surface_window: initial geometry "
                       "%{public}dx%{public}d failed rc=%{public}d",
                       width, height, geometryRc);
            return nullptr;
        }
        aospAnw = ::oh_anw_wrap(nw);
        if (!aospAnw) {
            ::OH_NativeWindow_DestroyNativeWindow(nw);
            parent->RemoveChild(child);
            oh_adapter::g_childSurfaces.erase(childKey);
            OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
            HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                       "oh_rs_get_child_surface_window: oh_anw_wrap failed");
            return nullptr;
        }
        if (::oh_anw_configure_direct_path(
                reinterpret_cast<ANativeWindow*>(aospAnw),
                sessionId, generation, width, height) != 0) {
            ::oh_anw_destroy(reinterpret_cast<ANativeWindow*>(aospAnw));
            ::OH_NativeWindow_DestroyNativeWindow(nw);
            parent->RemoveChild(child);
            oh_adapter::g_childSurfaces.erase(childKey);
            OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
            HiLogPrint(LOG_CORE, LOG_ERROR, 0xD000F00u, "OH_WindowMgrClient",
                       "oh_rs_get_child_surface_window: direct-path identity bind failed");
            return nullptr;
        }
        e.aospAnw = aospAnw;
        HiLogPrint(LOG_CORE, LOG_INFO, 0xD000F00u, "OH_WindowMgrClient",
                   "oh_rs_get_child_surface_window[cut8 single-owner XCOM]: "
                   "session=%{public}d childKey=0x%{public}llx producer_uid=0x%{public}llx "
                   "nw=%{public}p anw=%{public}p (%{public}dx%{public}d)",
                   sessionId, (unsigned long long)childKey,
                   (unsigned long long)producer->GetUniqueId(),
                   (void*)nw, aospAnw, width, height);
    }
    return aospAnw;
}

extern "C" __attribute__((visibility("default")))
void oh_rs_release_session_surfaces(int32_t sessionId, uint64_t generation) {
    bool changed = false;
    std::lock_guard<std::mutex> lk(oh_adapter::g_childSurfaceMutex);
    for (auto it = oh_adapter::g_childSurfaces.begin();
         it != oh_adapter::g_childSurfaces.end();) {
        auto& entry = it->second;
        if (entry.sessionId != sessionId || entry.generation != generation) {
            ++it;
            continue;
        }
        if (entry.aospAnw) {
            auto* ohWindow = ::oh_anw_get_oh(
                reinterpret_cast<ANativeWindow*>(entry.aospAnw));
            ::oh_anw_mark_surface_lost(
                reinterpret_cast<ANativeWindow*>(entry.aospAnw), generation);
            if (ohWindow) ::OH_NativeWindow_DestroyNativeWindow(ohWindow);
        }
        if (entry.parent && entry.node) entry.parent->RemoveChild(entry.node);
        it = oh_adapter::g_childSurfaces.erase(it);
        changed = true;
    }
    if (changed) OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
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
    // 2026-06-29 PRESENT-FIX: RS does NOT composite a bare APP_WINDOW_NODE's own
    // GetSurface() consumer buffer in unirender — main windows are expected to
    // draw via RSCanvasRenderNode children.  hwui's single-buffer Activity decor
    // reached the producer queue (DoFlushBufferLocked dirtyList=1) but was never
    // acquired/composited (RSTree: DrawableVec:[10], OpaqueRegion[Empty],
    // selfDrawingType_[0]; display stayed on launcher).  A SELF-DRAWING child
    // node (isWindow=false) AddChild'd under the WMS-registered window node IS
    // GPU-composited into the parent window layer (mirrors ArkUI XComponent
    // rosen_render_xcomponent.cpp:85 and the SurfaceView path
    // oh_rs_get_child_surface_window).  Hand hwui that child's producer instead
    // of the window node's own (orphan-consumer) producer.
    if (!it->second.contentChildNode) {
        OHOS::Rosen::RSSurfaceNodeConfig childCfg;
        childCfg.SurfaceNodeName = "AdapterActivityContent";
        auto child = OHOS::Rosen::RSSurfaceNode::Create(childCfg, /*isWindow=*/false);
        if (!child) {
            LOGE("getOhNativeWindow: self-drawing content child Create failed sessionId=%d", sessionId);
            return nullptr;
        }
        // createSession resolves missing dimensions from OH DisplayManager, so
        // this path never substitutes an application- or board-specific panel.
        if (it->second.reqWidth <= 0 || it->second.reqHeight <= 0) {
            LOGE("getOhNativeWindow: invalid resolved extent %dx%d sessionId=%d",
                 it->second.reqWidth, it->second.reqHeight, sessionId);
            return nullptr;
        }
        float cw = static_cast<float>(it->second.reqWidth);
        float ch = static_cast<float>(it->second.reqHeight);
        child->SetBounds(0.0f, 0.0f, cw, ch);
        child->SetFrame(0.0f, 0.0f, cw, ch);
        child->SetVisible(true);
        // [S22-G2.3] golden class-2 acquire: tell RS a UI buffer is available so it
        // schedules/acquires this self-draw producer (else buffers stay half-allocated
        // and Mali dequeues a malformed buffer -> wild-ptr SIGSEGV). Same switch already
        // on AdapterSurfaceView; AdapterActivityContent is Unity's real render surface.
        child->SetIsNotifyUIBufferAvailable(true);
        it->second.surfaceNode->AddChild(child, -1);
        OHOS::Rosen::RSTransaction::FlushImplicitTransaction();
        it->second.contentChildNode = child;
        LOGI("getOhNativeWindow: created self-drawing content child=%p under window node "
             "(%dx%d) sessionId=%d", child.get(), (int)cw, (int)ch, sessionId);
    }
    // 2026-05-08 G2.14ab: store sptr<Surface> in SessionEntry (not local var)
    // so its lifetime equals session lifetime. hwui RenderThread holds
    // OHNativeWindow* and async IncStrongRef on the backing ProducerSurface;
    // a local sptr would release on return, leading to use-after-free
    // (libsurface RefBase::IncStrongRef on 0xcafe5c02 poisoned memory).
    if (!it->second.producerSurface) {
        it->second.producerSurface = it->second.contentChildNode->GetSurface();
        // [S21 BUFFER-GEOM-FIX 2026-07-09] Seed the self-drawing child producer's
        // DEFAULT buffer geometry to the window (createSession) size. A freshly
        // created RSSurfaceNode producer defaults to 0x0, so hwui's first
        // RequestBuffer allocates Buffer[0 0] -> Bufferqueue SetupNewBufferLocked
        // "Fail to alloc or map Buffer[0 0]" ret:0x50002000 (NO_BUFFER). The 0x0
        // EGL surface then trips hwui's eglSetDamageRegion -> EGL_BAD_ACCESS ->
        // abort() (S20 末墙). Setting the default width/height (+ queue size, like
        // the oh_rs_get_child_surface_window path) makes RequestBuffer allocate a
        // real display-sized buffer even before hwui calls setBuffersGeometry.
        if (it->second.producerSurface) {
            int32_t bw = it->second.reqWidth;
            int32_t bh = it->second.reqHeight;
            it->second.producerSurface->SetDefaultWidthAndHeight(bw, bh);
            it->second.producerSurface->SetQueueSize(3);
            LOGI("getOhNativeWindow: seeded self-draw producer default buffer geometry "
                 "%dx%d queueSize=3 sessionId=%d", bw, bh, sessionId);
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
    // [S23 cut4 2026-07-09] Seed window->config geometry on the REAL OH nw so
    // native_window.cpp:229 NativeWindowRequestBuffer dequeues real-size buffers
    // (not Buffer[0 0] -> NO_BUFFER). Proven-distinct from SetDefaultWidthAndHeight
    // (default-queue) which does not propagate to the server BufferQueue. Real
    // geometry comes from the generation-bound session extent resolved through
    // DisplayManager; no fixed panel fallback is allowed here.
    {
        int32_t gw = it->second.reqWidth;
        int32_t gh = it->second.reqHeight;
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
        ::OH_NativeWindow_DestroyNativeWindow(nw);
        return nullptr;
    }
    if (::oh_anw_configure_direct_path(
            reinterpret_cast<ANativeWindow*>(aospAnw),
            sessionId, it->second.surfaceGeneration,
            it->second.reqWidth, it->second.reqHeight) != 0) {
        LOGE("getOhNativeWindow: direct-path identity bind failed "
             "sessionId=%d generation=%llu",
             sessionId, (unsigned long long)it->second.surfaceGeneration);
        ::oh_anw_destroy(reinterpret_cast<ANativeWindow*>(aospAnw));
        ::OH_NativeWindow_DestroyNativeWindow(nw);
        return nullptr;
    }
    it->second.ohNativeWindow = aospAnw;  // hwui-facing handle (AOSP ABI)
    LOGI("getOhNativeWindow: sessionId=%d -> AOSP-compat ANativeWindow=%p "
         "(oh=%p, surfaceNodeId=%lld)",
         sessionId, aospAnw, (void*)nw, (long long)it->second.surfaceNodeId);
    return aospAnw;
}

}  // namespace oh_adapter
