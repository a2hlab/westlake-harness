/*
 * oh_ability_manager_client.cpp
 *
 * OpenHarmony AbilityManager IPC client implementation.
 *
 * Connects to OH AbilityManagerService via SystemAbilityManager and sends
 * IPC requests (StartAbility, ConnectAbility, etc.) using OH IPC framework.
 *
 * Reference paths:
 *   OH: ability_rt/interfaces/inner_api/ability_manager/include/ability_manager_interface.h
 *   OH: ability_rt/services/abilitymgr/include/ability_manager_proxy.h
 */
#include "oh_ability_manager_client.h"
#include "oh_app_mgr_client.h"  // G2.14i: ApplicationForegrounded reverse IPC
#include "oh_callback_handler.h"
#include "fn03_lifecycle_core.h"
#include "sha256.h"
#include <android/log.h>
#include <chrono>
#include <iomanip>
#include <mutex>
#include <sstream>
#include <unordered_map>
#include <unistd.h>

#include "ipc_skeleton.h"
#include "iservice_registry.h"
#include "system_ability_manager_proxy.h"
#include "ability_manager_interface.h"
// [S20 ABILITYMGR-VTABLE-FIX] Removed "ability_manager_proxy.h" (the concrete
// oh61-wukong100 AbilityManagerProxy declaration). This TU only does
// iface_cast<IAbilityManager>, which resolves the proxy via the runtime-registered
// BrokerDelegator inside libability_manager.z.so — the concrete header is not
// needed. It was also INCOMPATIBLE with the 6.1.0.31 ability_manager_interface.h
// mirror we now shadow (device-correct IAbilityManager vtable, AttachAbilityThread
// @ slot 54/#432 vs the skewed slot 56/#448): the newer proxy declared `override`
// on methods absent from the device-version interface. Dropping it keeps this TU's
// IAbilityManager virtual-call slots consistent with the mirror (and the device).
#include "want.h"

#define LOG_TAG "OH_AbilityMgrClient"
#define LOGI(...) __android_log_print(ANDROID_LOG_INFO, LOG_TAG, __VA_ARGS__)
#define LOGE(...) __android_log_print(ANDROID_LOG_ERROR, LOG_TAG, __VA_ARGS__)
#define LOGW(...) __android_log_print(ANDROID_LOG_WARN, LOG_TAG, __VA_ARGS__)

extern "C" int HiLogPrint(int type, int level, unsigned int domain,
                          const char* tag, const char* fmt, ...);

// OH system ability ID for AbilityManagerService
static constexpr int32_t ABILITY_MGR_SERVICE_ID = 180;

namespace oh_adapter {

namespace {

struct Fn03ForegroundInstance {
    fn03::ActivityKey key;
    uint64_t rawOhToken = 0;
    uint64_t windowGeneration = 0;
    std::string transitionId;
};

std::mutex g_fn03ForegroundMutex;
fn03::TokenRegistry g_fn03TokenRegistry;
fn03::FirstFrameGate g_fn03FirstFrameGate;
fn03::AckReducer g_fn03AckReducer;
std::unordered_map<uint64_t, Fn03ForegroundInstance> g_fn03ForegroundByToken;
uint64_t g_fn03NextActivityGeneration = 1;

int64_t Fn03NowMs()
{
    return std::chrono::duration_cast<std::chrono::milliseconds>(
               std::chrono::steady_clock::now().time_since_epoch())
        .count();
}

uint64_t Fn03ProcessEpoch()
{
    static const uint64_t epoch =
        (static_cast<uint64_t>(getpid()) << 32) ^
        static_cast<uint64_t>(Fn03NowMs());
    return epoch == 0 ? 1 : epoch;
}

std::string Fn03Hex(uint64_t value)
{
    std::ostringstream out;
    out << std::hex << value;
    return out.str();
}

std::string Fn03ReceiptSha256(const Fn03ForegroundInstance& instance,
                              uint64_t frameId)
{
    const std::string payload =
        std::string("Fn04.A02|APP_CONTENT|") +
        instance.key.StableString() + "|" +
        std::to_string(instance.windowGeneration) + "|" +
        std::to_string(frameId) + "|" + instance.transitionId;
    unsigned char digest[32] = {};
    sha256(reinterpret_cast<const unsigned char*>(payload.data()),
           payload.size(), digest);
    std::ostringstream out;
    out << std::hex << std::setfill('0');
    for (unsigned char byte : digest) {
        out << std::setw(2) << static_cast<unsigned int>(byte);
    }
    return out.str();
}

bool Fn03CodeAllowsOpen(fn03::Code code)
{
    return code == fn03::Code::kAccepted ||
           code == fn03::Code::kPending ||
           code == fn03::Code::kDuplicate;
}

int Fn03OpenForeground(uint64_t rawOhToken, const std::string& owner,
                       uint32_t androidTokenIdentity,
                       uint64_t windowGeneration,
                       const std::string& transitionId)
{
    if (rawOhToken == 0 || owner.empty() || androidTokenIdentity == 0 ||
        windowGeneration == 0 || transitionId.empty()) {
        return -1;
    }

    std::lock_guard<std::mutex> lock(g_fn03ForegroundMutex);
    auto found = g_fn03ForegroundByToken.find(rawOhToken);
    if (found == g_fn03ForegroundByToken.end()) {
        const uint64_t generation = g_fn03NextActivityGeneration++;
        fn03::TokenRegistryRequest request;
        request.op = fn03::RegistryOp::kRegister;
        request.owner = owner;
        request.processEpoch = Fn03ProcessEpoch();
        request.generation = generation;
        request.nonce = "activity-" + std::to_string(generation);
        request.ohToken = "oh:" + Fn03Hex(rawOhToken);
        request.androidToken =
            "android:" + std::to_string(androidTokenIdentity);
        const fn03::TokenRegistryReceipt registered =
            g_fn03TokenRegistry.Apply(request);
        if (registered.code != fn03::Code::kAccepted ||
            registered.capabilityHandle == 0) {
            LOGE("[Fn03.A08] token registration rejected reason=%s",
                 registered.reason.c_str());
            return -2;
        }
        Fn03ForegroundInstance instance;
        instance.key = fn03::ActivityKey{
            owner, request.processEpoch, generation,
            registered.capabilityHandle};
        instance.rawOhToken = rawOhToken;
        found = g_fn03ForegroundByToken
                    .emplace(rawOhToken, std::move(instance))
                    .first;
        LOGI("[Fn03.A08] registered opaque activity capability=%llu "
             "owner=%s generation=%llu",
             static_cast<unsigned long long>(found->second.key.tokenHandle),
             owner.c_str(),
             static_cast<unsigned long long>(generation));
    } else if (found->second.key.owner != owner) {
        LOGE("[Fn03.A08] owner mismatch for existing activity capability");
        return -3;
    }

    Fn03ForegroundInstance& instance = found->second;
    if (instance.windowGeneration != 0 &&
        instance.windowGeneration != windowGeneration) {
        (void)g_fn03FirstFrameGate.Supersede(
            instance.key, instance.windowGeneration, "NEW_FOREGROUND_GENERATION");
    }
    const fn03::Result created = g_fn03FirstFrameGate.Create(
        instance.key, windowGeneration, transitionId, true, Fn03NowMs());
    if (!Fn03CodeAllowsOpen(created.code)) {
        LOGE("[Fn03.A10] create rejected reason=%s transition=%s",
             created.reason.c_str(), transitionId.c_str());
        return -4;
    }
    const fn03::Result resumed = g_fn03FirstFrameGate.Resume(
        instance.key, windowGeneration, transitionId);
    if (!Fn03CodeAllowsOpen(resumed.code)) {
        LOGE("[Fn03.A10] resume receipt rejected reason=%s transition=%s",
             resumed.reason.c_str(), transitionId.c_str());
        return -5;
    }
    const fn03::Result ackOpen = g_fn03AckReducer.Open(
        instance.key, transitionId,
        {"RESUME_TERMINAL", "FOREGROUND_READY"}, Fn03NowMs());
    if (!Fn03CodeAllowsOpen(ackOpen.code)) {
        LOGE("[Fn03.A07] ACK reducer open rejected reason=%s transition=%s",
             ackOpen.reason.c_str(), transitionId.c_str());
        return -6;
    }
    const fn03::Result resumeReceipt = g_fn03AckReducer.Receipt(
        instance.key, transitionId, "RESUME_TERMINAL", Fn03NowMs());
    if (!Fn03CodeAllowsOpen(resumeReceipt.code)) {
        LOGE("[Fn03.A07] resume terminal rejected reason=%s transition=%s",
             resumeReceipt.reason.c_str(), transitionId.c_str());
        return -7;
    }
    instance.windowGeneration = windowGeneration;
    instance.transitionId = transitionId;
    LOGI("[Fn03.A10] join open capability=%llu windowGeneration=%llu "
         "transition=%s",
         static_cast<unsigned long long>(instance.key.tokenHandle),
         static_cast<unsigned long long>(windowGeneration),
         transitionId.c_str());
    return 0;
}

bool Fn03AcceptAppContentPresent(uint64_t rawOhToken, uint64_t frameId,
                                fn03::ActivityKey* key,
                                std::string* transitionId)
{
    if (rawOhToken == 0 || frameId == 0 || key == nullptr ||
        transitionId == nullptr) {
        return false;
    }
    std::lock_guard<std::mutex> lock(g_fn03ForegroundMutex);
    const auto found = g_fn03ForegroundByToken.find(rawOhToken);
    if (found == g_fn03ForegroundByToken.end() ||
        found->second.windowGeneration == 0 ||
        found->second.transitionId.empty()) {
        LOGW("[Fn03.A10] Fn04.A02 receipt has no open foreground join");
        return false;
    }
    const Fn03ForegroundInstance& instance = found->second;
    fn03::FirstFrameReceipt receipt;
    receipt.key = instance.key;
    receipt.windowGeneration = instance.windowGeneration;
    receipt.frameId = frameId;
    receipt.presented = true;
    receipt.contentOrigin = fn03::ContentOrigin::kAppContent;
    receipt.producerActionId = "Fn04.A02";
    receipt.evidenceRunSha256 = Fn03ReceiptSha256(instance, frameId);
    const fn03::Result presented = g_fn03FirstFrameGate.Present(receipt);
    if (presented.code != fn03::Code::kReady) {
        if (presented.code != fn03::Code::kDuplicate) {
            LOGE("[Fn03.A10] APP_CONTENT receipt rejected reason=%s",
                 presented.reason.c_str());
        }
        return false;
    }
    const fn03::Result foregroundReady = g_fn03AckReducer.Receipt(
        instance.key, instance.transitionId, "FOREGROUND_READY", Fn03NowMs());
    if (!foregroundReady.emitted) {
        LOGE("[Fn03.A07] foreground-ready did not emit ACK reason=%s",
             foregroundReady.reason.c_str());
        return false;
    }
    *key = instance.key;
    *transitionId = instance.transitionId;
    std::ostringstream publicReceipt;
    publicReceipt
        << "FN03_A10_TYPED_RECEIPT_V1"
        << " producer_action_id=Fn04.A02"
        << " content_origin=APP_CONTENT"
        << " present_outcome=SUCCESS"
        << " capability=" << instance.key.tokenHandle
        << " window_generation=" << instance.windowGeneration
        << " frame_id=" << frameId
        << " transition_id=" << instance.transitionId
        << " producer_receipt_sha256=" << receipt.evidenceRunSha256;
    HiLogPrint(3, 4, 0xD000F00u, "OH_Fn03Receipt", "%{public}s",
               publicReceipt.str().c_str());
    LOGI("[Fn03.A10] typed APP_CONTENT ready capability=%llu frame=%llu "
         "receipt_sha256=%s",
         static_cast<unsigned long long>(instance.key.tokenHandle),
         static_cast<unsigned long long>(frameId),
         receipt.evidenceRunSha256.c_str());
    return true;
}

void Fn03RecordHostResult(const fn03::ActivityKey& key,
                          const std::string& transitionId, int rc)
{
    std::lock_guard<std::mutex> lock(g_fn03ForegroundMutex);
    const fn03::Result result = g_fn03AckReducer.HostResult(
        key, transitionId, std::optional<int>(rc));
    std::ostringstream publicResult;
    publicResult
        << "FN03_A07_ACK_RESULT_V1"
        << " rc=" << rc
        << " capability=" << key.tokenHandle
        << " transition_id=" << transitionId
        << " reducer_reason=" << result.reason;
    HiLogPrint(3, rc == 0 ? 4 : 6, 0xD000F00u, "OH_Fn03Receipt",
               "%{public}s", publicResult.str().c_str());
    LOGI("[Fn03.A07] OH ACK host result rc=%d reason=%s transition=%s",
         rc, result.reason.c_str(), transitionId.c_str());
}

}  // namespace

OHAbilityManagerClient& OHAbilityManagerClient::getInstance() {
    static OHAbilityManagerClient instance;
    return instance;
}

bool OHAbilityManagerClient::connect() {
    LOGI("Connecting to OH AbilityManagerService...");

    auto samgr = OHOS::SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgr == nullptr) {
        LOGE("Failed to get SystemAbilityManager");
        return false;
    }

    auto remoteObject = samgr->GetSystemAbility(ABILITY_MGR_SERVICE_ID);
    if (remoteObject == nullptr) {
        LOGE("Failed to get AbilityManagerService remote object (SA ID=%d)", ABILITY_MGR_SERVICE_ID);
        return false;
    }

    proxy_ = OHOS::iface_cast<OHOS::AAFwk::IAbilityManager>(remoteObject);
    if (proxy_ == nullptr) {
        LOGE("Failed to cast remote object to IAbilityManager");
        return false;
    }

    connected_ = true;
    LOGI("Connected to OH AbilityManagerService successfully");
    return true;
}

void OHAbilityManagerClient::disconnect() {
    LOGI("Disconnecting from OH AbilityManagerService");
    proxy_ = nullptr;
    connected_ = false;
}

int32_t OHAbilityManagerClient::getMissionIdByTokenAddr(jlong ohTokenAddr) {
    if (!connected_ || proxy_ == nullptr || ohTokenAddr == 0) {
        LOGE("GetMissionIdByToken: unavailable connected=%d token=0x%llx",
             connected_, static_cast<unsigned long long>(ohTokenAddr));
        return -1;
    }

    OHOS::IRemoteObject* raw =
        reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr);
    OHOS::sptr<OHOS::IRemoteObject> token(raw);
    int32_t missionId = proxy_->GetMissionIdByToken(token);
    LOGI("GetMissionIdByToken: token=0x%llx missionId=%d",
         static_cast<unsigned long long>(ohTokenAddr), missionId);
    return missionId > 0 ? missionId : -1;
}

int OHAbilityManagerClient::startAbility(const WantParams& want) {
    // Legacy entry: no caller token.  Kept for callers that genuinely lack
    // one (e.g., system-initiated cold-start paths).  For App-initiated
    // startActivity() — which is the helloworld user button case — use
    // startAbilityWithCaller() so OH AMS [ABMS1361]caller-invalid check
    // passes.  See 2026-05-19 doc/build_patch_log.html "Start SecondActivity"
    // entry for the full diagnosis.
    return startAbilityWithCaller(want, /*callerOhTokenAddr=*/0);
}

int OHAbilityManagerClient::startAbilityWithCaller(const WantParams& want,
                                                    jlong callerOhTokenAddr) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("StartAbility: bundle=%s, ability=%s, action=%s, callerOhTokenAddr=0x%llx",
         want.bundleName.c_str(), want.abilityName.c_str(), want.action.c_str(),
         static_cast<unsigned long long>(callerOhTokenAddr));

    // Construct OH Want object
    OHOS::AAFwk::Want ohWant;
    OHOS::AppExecFwk::ElementName element("", want.bundleName, want.abilityName);
    ohWant.SetElement(element);

    if (!want.action.empty()) {
        ohWant.SetAction(want.action);
    }
    if (!want.uri.empty()) {
        ohWant.SetUri(want.uri);
    }
    if (!want.parametersJson.empty()) {
        // Pass extras as a string parameter for Java-side parsing
        ohWant.SetParam("android_extras_json", want.parametersJson);
    }

    // 2026-05-25 1D: mark this as an Android adapter app + carry the Android
    // Intent launch flags so OH MissionListManager::StartAbility performs
    // server-side task grouping (caller's-task primary / bundle-affinity
    // fallback), mirroring AOSP ATMS ActivityStarter.  OH-native callers never
    // set these markers, so their mission behavior is unchanged.
    ohWant.SetParam("__android_adapter_app", true);
    ohWant.SetParam("__android_launch_flags", want.androidLaunchFlags);

    // Call AbilityManager.StartAbility via IPC.  Two overloads:
    //   - StartAbility(want, userId, requestCode, ...) — system caller path,
    //     rejected by OH AMS for normal-apl App callers with [ABMS1361]
    //     caller invalid.
    //   - StartAbility(want, callerToken, userId, requestCode, ...) —
    //     App-caller path, validates callerToken against existing ability
    //     nodes server-side.
    // We pick based on callerOhTokenAddr non-zero (App caller path).
    int result;
    if (callerOhTokenAddr != 0) {
        OHOS::IRemoteObject* raw =
            reinterpret_cast<OHOS::IRemoteObject*>(callerOhTokenAddr);
        OHOS::sptr<OHOS::IRemoteObject> callerToken(raw);
        result = proxy_->StartAbility(ohWant, callerToken);
    } else {
        result = proxy_->StartAbility(ohWant);
    }

    LOGI("StartAbility returned %d (0=success)", result);
    return result;
}

int OHAbilityManagerClient::connectAbility(const WantParams& want, int connectionId) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("ConnectAbility: bundle=%s, ability=%s, connId=%d",
         want.bundleName.c_str(), want.abilityName.c_str(), connectionId);

    // Construct OH Want
    OHOS::AAFwk::Want ohWant;
    OHOS::AppExecFwk::ElementName element("", want.bundleName, want.abilityName);
    ohWant.SetElement(element);

    // Get per-connection AbilityConnection stub from OHCallbackHandler
    auto connection = OHCallbackHandler::getInstance().getAbilityConnection(connectionId);
    if (connection == nullptr) {
        LOGE("Failed to create AbilityConnection for connId=%d", connectionId);
        return -1;
    }

    // V7 ConnectAbility(want, connect, callerToken, userId). We have no
    // meaningful caller token from the Android side; pass nullptr.
    int result = proxy_->ConnectAbility(ohWant, connection, nullptr, -1);
    if (result != 0) {
        // Fn07.A01：OH 仅以 ERR_OK(0) 表示同步受理成功。正值同样是失败，
        // 必须释放本次调用前创建的 callback adapter，避免孤儿记录。
        OHCallbackHandler::getInstance().removeAbilityConnection(connectionId);
    }
    LOGI("ConnectAbility returned %d", result);
    return result;
}

int OHAbilityManagerClient::disconnectAbility(int connectionId) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("DisconnectAbility: connectionId=%d", connectionId);

    auto connection = OHCallbackHandler::getInstance().getAbilityConnection(connectionId);
    if (connection == nullptr) {
        LOGE("AbilityConnection not found for connId=%d", connectionId);
        return -1;
    }

    int result = proxy_->DisconnectAbility(connection);
    // Clean up the connection adapter
    OHCallbackHandler::getInstance().removeAbilityConnection(connectionId);
    LOGI("DisconnectAbility returned %d", result);
    return result;
}

int OHAbilityManagerClient::stopServiceAbility(const WantParams& want) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("StopServiceAbility: bundle=%s, ability=%s",
         want.bundleName.c_str(), want.abilityName.c_str());

    OHOS::AAFwk::Want ohWant;
    OHOS::AppExecFwk::ElementName element("", want.bundleName, want.abilityName);
    ohWant.SetElement(element);

    int result = proxy_->StopServiceAbility(ohWant);

    LOGI("StopServiceAbility returned %d (0=success)", result);
    return result;
}

int OHAbilityManagerClient::startAbilityInMission(const WantParams& want, int32_t missionId) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("StartAbilityInMission: bundle=%s, ability=%s, missionId=%d",
         want.bundleName.c_str(), want.abilityName.c_str(), missionId);

    OHOS::AAFwk::Want ohWant;
    OHOS::AppExecFwk::ElementName element("", want.bundleName, want.abilityName);
    ohWant.SetElement(element);

    if (!want.action.empty()) {
        ohWant.SetAction(want.action);
    }
    if (!want.uri.empty()) {
        ohWant.SetUri(want.uri);
    }
    if (!want.parametersJson.empty()) {
        ohWant.SetParam("android_extras_json", want.parametersJson);
    }

    // ABI-safe routing: use standard IAbilityManager::StartAbility IPC with a
    // marker parameter. AMS-side patch (mission_list_manager) reads the marker
    // and routes to MissionListManager::StartAbilityInMission internally.
    // Never modifies IAbilityManager vtable.
    ohWant.SetParam("__android_in_mission_id", missionId);
    int result = proxy_->StartAbility(ohWant);

    LOGI("StartAbilityInMission returned %d (0=success)", result);
    return result;
}

int OHAbilityManagerClient::cleanMission(int32_t missionId) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("CleanMission: missionId=%d", missionId);
    int result = proxy_->CleanMission(missionId);
    LOGI("CleanMission returned %d", result);
    return result;
}

int OHAbilityManagerClient::moveMissionToFront(int32_t missionId) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("MoveMissionToFront: missionId=%d", missionId);
    int result = proxy_->MoveMissionToFront(missionId);
    LOGI("MoveMissionToFront returned %d", result);
    return result;
}

int OHAbilityManagerClient::setMultiAbilityMode(int32_t missionId, bool enabled) {
    // This is set on the Mission object via the StartAbility return path.
    // The adapter stores the mapping locally; the actual flag is set
    // via a custom parameter in the StartAbility Want.
    LOGI("setMultiAbilityMode: missionId=%d, enabled=%d", missionId, enabled);
    // The flag is set on the OH side during Mission creation when
    // the Want contains the android adapter marker.
    return 0;
}

bool OHAbilityManagerClient::isTopAbility(int32_t missionId, const std::string& abilityName) {
    if (!connected_ || proxy_ == nullptr) {
        return false;
    }

    // Query the Mission's top Ability via GetMissionInfo
    OHOS::AAFwk::MissionInfo missionInfo;
    int result = proxy_->GetMissionInfo("", missionId, missionInfo);
    if (result != 0) {
        return false;
    }

    auto element = missionInfo.want.GetElement();
    return element.GetAbilityName() == abilityName;
}

int OHAbilityManagerClient::clearAbilitiesAbove(int32_t missionId, const std::string& abilityName) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("ClearAbilitiesAbove: missionId=%d, abilityName=%s", missionId, abilityName.c_str());

    // This operation is handled within OH MissionListManager via a custom IPC call.
    // The adapter sets a Want parameter that triggers stack clearing in the patched
    // TerminateAbilityLocked / StartAbilityInMission path.
    //
    // Approach: start the target ability with a CLEAR_TOP marker in the Want.
    // The patched MissionListManager.StartAbilityInMission checks this marker
    // and calls Mission::PopAbilitiesAbove before pushing.
    OHOS::AAFwk::Want ohWant;
    // Use existing mission's bundle from MissionInfo
    OHOS::AAFwk::MissionInfo missionInfo;
    int result = proxy_->GetMissionInfo("", missionId, missionInfo);
    if (result != 0) {
        LOGE("ClearAbilitiesAbove: failed to get MissionInfo for %d", missionId);
        return -1;
    }

    auto element = missionInfo.want.GetElement();
    OHOS::AppExecFwk::ElementName newElement("", element.GetBundleName(), abilityName);
    ohWant.SetElement(newElement);
    ohWant.SetParam("android_clear_top", true);
    // ABI-safe routing: marker param read by patched MissionListManager.
    ohWant.SetParam("__android_in_mission_id", missionId);

    result = proxy_->StartAbility(ohWant);
    LOGI("ClearAbilitiesAbove returned %d", result);
    return result;
}

int32_t OHAbilityManagerClient::getMissionIdForBundle(const std::string& bundleName) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("Not connected to AbilityManagerService");
        return -1;
    }

    LOGI("GetMissionIdForBundle: bundle=%s", bundleName.c_str());

    // Query recent missions and find one matching the bundle name
    std::vector<OHOS::AAFwk::MissionInfo> missionInfos;
    int result = proxy_->GetMissionInfos("", 100, missionInfos);
    if (result != 0) {
        LOGE("GetMissionIdForBundle: GetMissionInfos failed with %d", result);
        return -1;
    }

    // Search for a mission whose Want element matches the bundle name
    for (const auto& info : missionInfos) {
        auto element = info.want.GetElement();
        if (element.GetBundleName() == bundleName) {
            LOGI("GetMissionIdForBundle: found missionId=%d for bundle=%s",
                 info.id, bundleName.c_str());
            return info.id;
        }
    }

    LOGW("GetMissionIdForBundle: no mission found for bundle=%s", bundleName.c_str());
    return -1;
}

// 2026-04-30 (B.48 §1.2.4.3 P2): TerminateAbility for App finish() reverse callback.
// AppSchedulerBridge OhTokenRegistry stores OH IRemoteObject addr at launch;
// when ActivityClientControllerAdapter.finishActivity gets Android IBinder, it
// looks up the OH token addr and calls this entry to drive OH AbilityMS::TerminateAbility.
int32_t OHAbilityManagerClient::terminateAbilityByTokenAddr(jlong ohTokenAddr, int32_t resultCode) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("terminateAbility: Not connected to AbilityManagerService");
        return -1;
    }
    if (ohTokenAddr == 0) {
        LOGE("terminateAbility: null token addr");
        return -2;
    }
    // Reconstruct sptr<IRemoteObject> from raw ptr that we stored at launch.
    // Safety: Java side MUST hold the original OH ScheduleLaunchAbility token via
    // OhTokenRegistry; the IRemoteObject stays alive at least until OH itself
    // releases it via OnProcessDied/OnAbilityDied. After TerminateAbility OH side
    // will release; subsequent finish() calls with same addr are no-ops.
    OHOS::IRemoteObject* raw = reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr);
    OHOS::sptr<OHOS::IRemoteObject> token(raw);
    int result = proxy_->TerminateAbility(token, resultCode, nullptr);
    LOGI("TerminateAbility(token=0x%llx, code=%d) returned %d",
         static_cast<unsigned long long>(ohTokenAddr), resultCode, result);
    return result;
}

// 2026-06-01 (back-key blocker fix, option B): MinimizeAbility for the
// IActivityClientController.onBackPressed reverse callback.  AOSP routes a
// root-activity back press through ATMS, which (for a task root that is not
// finishing) moves the task to the background.  On legacy OH WindowManager the
// equivalent is AbilityMS::MinimizeAbility(token, fromUser=true): the ability's
// window is hidden and the home/launcher comes forward, WITHOUT killing the
// process (distinct from TerminateAbility, which destroys the ability).
int32_t OHAbilityManagerClient::minimizeAbilityByTokenAddr(jlong ohTokenAddr) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("MinimizeAbility: Not connected to AbilityManagerService");
        return -1;
    }
    if (ohTokenAddr == 0) {
        LOGE("MinimizeAbility: null token addr");
        return -2;
    }
    OHOS::IRemoteObject* raw = reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr);
    OHOS::sptr<OHOS::IRemoteObject> token(raw);
    int result = proxy_->MinimizeAbility(token, /*fromUser=*/true);
    LOGI("MinimizeAbility(token=0x%llx, fromUser=true) returned %d",
         static_cast<unsigned long long>(ohTokenAddr), result);
    return result;
}

// 2026-06-01 (back-key fix, native-semantic redesign): the Android back press is
// routed to OH TerminateAbility -- the OH-native back method (Ability::OnBackPressed
// -> TerminateAbility), distinct from recents/multitask which uses MinimizeAbility.
// A marker Want ("ohAdapter.androidBack") tags this as an Android back so OH can
// apply the Android-specific root-Activity semantic (single-stack root back ->
// moveTaskToBack / minimize keep-alive instead of destroy). For a non-root Activity
// (multi-Ability stack) OH pops the top. The whole root/non-root decision lives in
// OH MissionListManager::TerminateAbility; the adapter just makes one call.
int32_t OHAbilityManagerClient::backPressedByTokenAddr(jlong ohTokenAddr) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("backPressed: Not connected to AbilityManagerService");
        return -1;
    }
    if (ohTokenAddr == 0) {
        LOGE("backPressed: null token addr");
        return -2;
    }
    OHOS::IRemoteObject* raw = reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr);
    OHOS::sptr<OHOS::IRemoteObject> token(raw);
    OHOS::AAFwk::Want backWant;
    backWant.SetParam("ohAdapter.androidBack", true);
    int result = proxy_->TerminateAbility(token, -1 /*resultCode*/, &backWant);
    LOGI("backPressed -> TerminateAbility(token=0x%llx, marker=androidBack) returned %d",
         static_cast<unsigned long long>(ohTokenAddr), result);
    return result;
}

// 2026-04-30 (G2.1 LIFECYCLE_HALF_TIMEOUT fix):
// After Android lifecycle transitions complete (onCreate/onResume/onPause/...)
// AOSP framework calls IActivityClientController.activityResumed(token,...).
// We need to forward this to OH IAbilityManager::AbilityTransitionDone(token,
// state, saveData) so OH AMS knows the app finished the transition; otherwise
// OH AMS triggers LIFECYCLE_HALF_TIMEOUT (~1s) and kills the app.
// Spec: doc/ability_manager_ipc_adapter_design.html (planned §3.x reverse).
int32_t OHAbilityManagerClient::abilityTransitionDoneByTokenAddr(jlong ohTokenAddr, int32_t ohState) {
    if (!connected_ || proxy_ == nullptr) {
        LOGE("AbilityTransitionDone: Not connected to AbilityManagerService");
        return -1;
    }
    if (ohTokenAddr == 0) {
        LOGE("AbilityTransitionDone: null token addr");
        return -2;
    }
    OHOS::IRemoteObject* raw = reinterpret_cast<OHOS::IRemoteObject*>(ohTokenAddr);
    OHOS::sptr<OHOS::IRemoteObject> token(raw);
    OHOS::AAFwk::PacMap saveData;  // empty — Android lifecycle doesn't carry OH PacMap
    int result = proxy_->AbilityTransitionDone(token, ohState, saveData);
    LOGI("AbilityTransitionDone(token=0x%llx, ohState=%d) returned %d",
         static_cast<unsigned long long>(ohTokenAddr), ohState, result);
    return result;
}

}  // namespace oh_adapter

extern "C" {

// JNI entry for ActivityClientControllerAdapter.finishActivity reverse callback.
// adapter.activity.ActivityClientControllerAdapter -> nativeTerminateAbilityByTokenAddr
JNIEXPORT jint JNICALL
Java_adapter_activity_ActivityClientControllerAdapter_nativeTerminateAbilityByTokenAddr(
        JNIEnv* /*env*/, jclass /*clazz*/, jlong ohTokenAddr, jint resultCode) {
    return oh_adapter::OHAbilityManagerClient::getInstance()
        .terminateAbilityByTokenAddr(ohTokenAddr, resultCode);
}

// 2026-06-01 (back-key blocker fix, option B): JNI entry for
// ActivityClientControllerAdapter.onBackPressed reverse callback (task-root
// minimize / back-to-home path).
JNIEXPORT jint JNICALL
Java_adapter_activity_ActivityClientControllerAdapter_nativeMinimizeAbilityByTokenAddr(
        JNIEnv* /*env*/, jclass /*clazz*/, jlong ohTokenAddr) {
    return oh_adapter::OHAbilityManagerClient::getInstance()
        .minimizeAbilityByTokenAddr(ohTokenAddr);
}

// 2026-06-01 (back-key fix): JNI entry for ActivityClientControllerAdapter.onBackPressed.
// Routes the Android back press to OH TerminateAbility (with androidBack marker);
// OH decides root (minimize keep-alive) vs non-root (pop) by mission stack size.
JNIEXPORT jint JNICALL
Java_adapter_activity_ActivityClientControllerAdapter_nativeBackPressedByTokenAddr(
        JNIEnv* /*env*/, jclass /*clazz*/, jlong ohTokenAddr) {
    return oh_adapter::OHAbilityManagerClient::getInstance()
        .backPressedByTokenAddr(ohTokenAddr);
}

// 2026-04-30 (G2.1): JNI for ActivityClientControllerAdapter.activityResumed
// reverse callback.  Forwards to OH AbilityMS::AbilityTransitionDone.
//
// G2.14j (2026-05-01): translate AbilityState (internal AMS enum, what the Java
// caller passes) → AbilityLifeCycleState (IPC wire enum the AMS server expects).
// AMS calls StateUtils::ConvertStateMap(AbilityLifeCycleState) → AbilityState
// internally before dispatch. Sending FOREGROUND(9) directly is interpreted as
// AbilityLifeCycleState::ABILITY_STATE_BACKGROUND_FAILED(=9) → DispatchBackground
// → expects BACKGROUNDING → fails with rc=22. Correct value is
// ABILITY_STATE_FOREGROUND_NEW(=5).
//
// AbilityState (input from Java)         | AbilityLifeCycleState (IPC wire)
//   INACTIVE=1                           | ABILITY_STATE_INACTIVE=1     (same)
//   FOREGROUND=9                         | ABILITY_STATE_FOREGROUND_NEW=5
//   BACKGROUND=10                        | ABILITY_STATE_BACKGROUND_NEW=6
JNIEXPORT jint JNICALL
Java_adapter_activity_ActivityClientControllerAdapter_nativeAbilityTransitionDone(
        JNIEnv* /*env*/, jclass /*clazz*/, jlong ohTokenAddr, jint ohState) {
    int wireState = ohState;
    switch (ohState) {
        case 9:  wireState = 5; break;   // FOREGROUND -> ABILITY_STATE_FOREGROUND_NEW
        case 10: wireState = 6; break;   // BACKGROUND -> ABILITY_STATE_BACKGROUND_NEW
        case 1:  wireState = 1; break;   // INACTIVE   -> ABILITY_STATE_INACTIVE (identity)
        default:
            // pass through unknown values; OH ConvertStateMap returns DEFAULT_INVAL_VALUE
            // for unrecognized values, AMS will reject explicitly.
            break;
    }
    __android_log_print(ANDROID_LOG_INFO, "OH_AbilityMgrClient",
        "[G2.14j] nativeAbilityTransitionDone: ohState=%d -> wireState=%d", ohState, wireState);
    return oh_adapter::OHAbilityManagerClient::getInstance()
        .abilityTransitionDoneByTokenAddr(ohTokenAddr, wireState);
}

JNIEXPORT jint JNICALL
Java_adapter_activity_ActivityClientControllerAdapter_nativeOpenForegroundTransition(
        JNIEnv* env, jclass /*clazz*/, jlong ohTokenAddr, jstring owner,
        jint androidTokenIdentity, jlong windowGeneration,
        jstring transitionId) {
    if (owner == nullptr || transitionId == nullptr) {
        return -1;
    }
    const char* ownerChars = env->GetStringUTFChars(owner, nullptr);
    const char* transitionChars =
        env->GetStringUTFChars(transitionId, nullptr);
    if (ownerChars == nullptr || transitionChars == nullptr) {
        if (ownerChars != nullptr) {
            env->ReleaseStringUTFChars(owner, ownerChars);
        }
        if (transitionChars != nullptr) {
            env->ReleaseStringUTFChars(transitionId, transitionChars);
        }
        return -1;
    }
    const int rc = oh_adapter::Fn03OpenForeground(
        static_cast<uint64_t>(ohTokenAddr), ownerChars,
        static_cast<uint32_t>(androidTokenIdentity),
        static_cast<uint64_t>(windowGeneration), transitionChars);
    env->ReleaseStringUTFChars(owner, ownerChars);
    env->ReleaseStringUTFChars(transitionId, transitionChars);
    return rc;
}

// Alias for AppSchedulerBridge usage (PathClassLoader scope, RegisterNatives).
JNIEXPORT jint JNICALL
Java_adapter_activity_AppSchedulerBridge_nativeTerminateAbility(
        JNIEnv* env, jclass clazz, jlong ohTokenAddr, jint resultCode) {
    return Java_adapter_activity_ActivityClientControllerAdapter_nativeTerminateAbilityByTokenAddr(
        env, clazz, ohTokenAddr, resultCode);
}

// G2.14i (2026-05-01): JNI for AppSchedulerBridge.notifyForegroundDeferred main-looper
// callback. Routes ApplicationForegrounded reverse IPC to OH AppMS. Called from
// Java main-looper Runnable that was posted by AppSchedulerAdapter::ScheduleForegroundApplication.
// By the time this fires, AppMS::AbilityForeground has already finished
// foregroundingAbilityTokens_.insert(token), so PopForegroundingAbilityTokens →
// OnAbilityRequestDone → AMS::ForegroundLifecycle works.
JNIEXPORT void JNICALL
Java_adapter_activity_AppSchedulerBridge_nativeNotifyApplicationForegrounded(
        JNIEnv* /*env*/, jclass /*clazz*/, jint recordId) {
    // Update the cached recordId so subsequent calls also use the latest.
    if (recordId >= 0) {
        oh_adapter::OHAppMgrClient::getInstance().setRecordId(recordId);
    }
    oh_adapter::OHAppMgrClient::getInstance().notifyAppState(
        static_cast<int>(oh_adapter::AppState::STATE_FOREGROUND));
}

// 2026-04-30 (B.48): stub for AOSP ActivityThread.nInitZygoteChildHeapProfiling.
// handleBindApplication line ~6856 calls this when isAppDebuggable || Build.IS_DEBUGGABLE.
// AOSP impl reads SystemProperties to enable malloc heap profiling — OH has no
// equivalent infrastructure. Stub return is safe (no caller relies on side effect).
// Registered via RegisterNatives from appspawnx_runtime.cpp (BCP class).
JNIEXPORT void JNICALL
Java_android_app_ActivityThread_nInitZygoteChildHeapProfiling(
        JNIEnv* /*env*/, jclass /*clazz*/) {
    // no-op
}

// AOSP implements nPurgePendingResources with bionic mallopt(M_PURGE, 0).
// OpenHarmony's musl allocator has no M_PURGE ABI.  The operation is only a
// best-effort idle-time allocator hint and its return value is intentionally
// ignored by ActivityThread, so the boundary-equivalent implementation is a
// no-op rather than allowing an UnsatisfiedLinkError to escape after destroy.
JNIEXPORT void JNICALL
Java_android_app_ActivityThread_nPurgePendingResources(
        JNIEnv* /*env*/, jobject /*activityThread*/) {
    // no-op: no OpenHarmony allocator purge primitive with matching semantics
}

}  // extern "C"

extern "C" __attribute__((visibility("default")))
void fn03_on_app_content_present(uint64_t ohTokenAddr, uint64_t frameId)
{
    oh_adapter::fn03::ActivityKey key;
    std::string transitionId;
    if (!oh_adapter::Fn03AcceptAppContentPresent(
            ohTokenAddr, frameId, &key, &transitionId)) {
        return;
    }
    const int rc = oh_adapter::OHAbilityManagerClient::getInstance()
                       .abilityTransitionDoneByTokenAddr(
                           static_cast<jlong>(ohTokenAddr), 5);
    oh_adapter::Fn03RecordHostResult(key, transitionId, rc);
}
