/*
 * oh_ability_manager_client.h
 *
 * OpenHarmony AbilityManager IPC client.
 * Wraps remote calls to OH AbilityManagerService.
 */
#ifndef OH_ABILITY_MANAGER_CLIENT_H
#define OH_ABILITY_MANAGER_CLIENT_H
#include <refbase.h>
#include <iremote_broker.h>

#include "intent_want_converter.h"
#include <jni.h>
#include <string>

// Pull in the full IAbilityManager definition so callers that destruct an
// OHAbilityManagerClient (which holds sptr<IAbilityManager> proxy_) don't hit
// "incomplete type" in refbase.h::sptr<T>::~sptr.
#include "ability_manager_interface.h"

// OH IPC types still forward-declared for callers that don't need full layout.
namespace OHOS {
    class IRemoteObject;
}

namespace oh_adapter {

// Forward declaration
class AbilitySchedulerAdapter;
class AppSchedulerAdapter;

class OHAbilityManagerClient {
public:
    static OHAbilityManagerClient& getInstance();

    /**
     * Connect to OH AbilityManagerService.
     * Obtains remote proxy via OH SystemAbilityManager.
     */
    bool connect();

    /**
     * Disconnect from service.
     */
    void disconnect();

    /**
     * Call OH AbilityManager.StartAbility(Want).
     * @param want Converted Want parameters
     * @return 0 on success, non-zero error code
     */
    int startAbility(const WantParams& want);
    // 2026-05-19: caller-aware overload — passes callerToken to OH AMS so
    // non-system app callers (apl=normal helloworld etc.) pass the
    // "[ABMS1361]caller invalid" check.  callerOhTokenAddr=0 falls back to
    // the no-caller form (system caller path).  Mirrors ArkUI UIAbility
    // .startAbility() which uses StartAbility(want, self.token, ...).
    int startAbilityWithCaller(const WantParams& want, jlong callerOhTokenAddr);

    /**
     * Resolve this application's SceneBoard mission/session identity from its
     * OH Ability token. In SceneBoard mode AMS maps this to the main
     * SceneSession persistentId.
     *
     * @return positive persistentId on success, negative value on failure
     */
    int32_t getMissionIdByTokenAddr(jlong ohTokenAddr);

    /**
     * Start an Ability within an existing Mission (push onto Ability stack).
     * @param want Converted Want parameters
     * @param missionId Target Mission ID to push into
     * @return 0 on success, non-zero error code
     */
    int startAbilityInMission(const WantParams& want, int32_t missionId);

    /**
     * Call OH AbilityManager.ConnectAbility(Want).
     * @param want Converted Want parameters
     * @param connectionId Local connection ID from ServiceConnectionRegistry
     * @return 0 on success, negative on error
     */
    int connectAbility(const WantParams& want, int connectionId);

    /**
     * Call OH AbilityManager.DisconnectAbility().
     */
    int disconnectAbility(int connectionId);

    /**
     * Call OH AbilityManager.StopServiceAbility(Want).
     * @param want Converted Want parameters (bundleName + abilityName)
     * @return 0 on success, non-zero error code
     */
    int stopServiceAbility(const WantParams& want);

    /**
     * Clean (remove) a Mission and all its stacked Abilities.
     * @param missionId Mission to clean
     * @return 0 on success
     */
    int cleanMission(int32_t missionId);

    /**
     * Move a Mission's top Ability to front.
     * @param missionId Mission to move
     * @return 0 on success
     */
    int moveMissionToFront(int32_t missionId);

    /**
     * Set multi-ability mode on a Mission (enable Ability stacking).
     * @param missionId Target Mission
     * @param enabled true to enable
     * @return 0 on success
     */
    int setMultiAbilityMode(int32_t missionId, bool enabled);

    /**
     * Check if the top Ability of a Mission matches the given name.
     * @param missionId Mission ID
     * @param abilityName Target ability name
     * @return true if top ability matches
     */
    bool isTopAbility(int32_t missionId, const std::string& abilityName);

    /**
     * Clear all Abilities above the named Ability in a Mission's stack.
     * Used for FLAG_ACTIVITY_CLEAR_TOP behavior.
     * @param missionId Target Mission
     * @param abilityName Ability to clear above
     * @return number of abilities cleared, or -1 on error
     */
    int clearAbilitiesAbove(int32_t missionId, const std::string& abilityName);

    /**
     * Find the Mission ID for an active Mission matching the given bundle name.
     * Queries GetMissionInfos and returns the first matching missionId.
     * @param bundleName Target bundle name
     * @return missionId if found, -1 if not found
     */
    int32_t getMissionIdForBundle(const std::string& bundleName);

    /**
     * 2026-04-30 (B.48 §1.2.4.3 P2 reverse callback):
     * Reconstruct sptr from raw OH IRemoteObject addr (saved at ScheduleLaunchAbility
     * via OhTokenRegistry) and call OH AbilityMS::TerminateAbility.
     * @param ohTokenAddr  raw pointer captured at SLA time (jlong cast)
     * @param resultCode   Activity result code (Android RESULT_OK=-1 / FIRST_USER=1...)
     * @return 0 on OH success, non-zero on error
     */
    int32_t terminateAbilityByTokenAddr(jlong ohTokenAddr, int32_t resultCode);

    /**
     * 2026-06-01 (back-key blocker fix, option B):
     * Reconstruct sptr from raw OH IRemoteObject addr and call OH
     * AbilityMS::MinimizeAbility — the legacy-WindowManager "back to home,
     * keep process alive" semantics for a task-root activity.  Invoked from
     * ActivityClientControllerAdapter.onBackPressed (which replaces AOSP ATMS's
     * IActivityClientController.onBackPressed; AOSP routes back through ATMS
     * which decides minimize-vs-finish — adapter must replicate that decision).
     * @param ohTokenAddr  raw pointer captured at SLA time (jlong cast)
     * @return 0 on OH success, non-zero on error
     */
    int32_t minimizeAbilityByTokenAddr(jlong ohTokenAddr);

    /**
     * 2026-06-01 (back-key fix, native-semantic redesign):
     * Route the Android back press to OH TerminateAbility (the OH-native back
     * method, distinct from recents' MinimizeAbility) with an "ohAdapter.androidBack"
     * marker Want.  OH MissionListManager::TerminateAbility decides root (single
     * stack -> minimize keep-alive) vs non-root (multi stack -> pop) — the whole
     * decision lives in OH.  Invoked from ActivityClientControllerAdapter.onBackPressed.
     * @param ohTokenAddr  raw pointer captured at SLA time (jlong cast)
     * @return 0 on OH success, non-zero on error
     */
    int32_t backPressedByTokenAddr(jlong ohTokenAddr);

    /**
     * 2026-04-30 (G2.1 LIFECYCLE_HALF_TIMEOUT fix):
     * Tell OH AbilityMS the lifecycle transition completed.  Without this
     * callback OH AMS treats the ability as "stuck loading" and triggers
     * LIFECYCLE_HALF_TIMEOUT (~1s after ScheduleLaunchAbility), then
     * killProcessByPid the app.  Called from
     * ActivityClientControllerAdapter.activityResumed (Android side reports
     * onResume done) → JNI → here → IAbilityManager.AbilityTransitionDone.
     * @param ohTokenAddr  raw pointer captured at SLA time (jlong cast)
     * @param ohState      OH AbilityState enum value: FOREGROUND=9 / BACKGROUND=10 / INITIAL=0 / INACTIVE=1
     * @return 0 on OH success, non-zero on error
     */
    int32_t abilityTransitionDoneByTokenAddr(jlong ohTokenAddr, int32_t ohState);

    /**
     * Get the IPC proxy for direct access (used by advanced operations).
     */
    OHOS::sptr<OHOS::AAFwk::IAbilityManager> getProxy() const { return proxy_; }

    bool isConnected() const { return connected_; }

private:
    OHAbilityManagerClient() = default;
    ~OHAbilityManagerClient() = default;

    bool connected_ = false;
    OHOS::sptr<OHOS::AAFwk::IAbilityManager> proxy_ = nullptr;
};

}  // namespace oh_adapter

#endif  // OH_ABILITY_MANAGER_CLIENT_H
