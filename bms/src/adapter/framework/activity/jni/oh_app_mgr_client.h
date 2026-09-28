/*
 * oh_app_mgr_client.h
 *
 * OpenHarmony AppMgr IPC client.
 * Wraps remote calls to OH AppMgrService (application process management).
 */
#ifndef OH_APP_MGR_CLIENT_H
#define OH_APP_MGR_CLIENT_H

#include <jni.h>
#include <string>
#include "iremote_object.h"
#include "app_mgr_interface.h"

namespace oh_adapter {

class AppSchedulerAdapter;

// App state constants (maps to OH ApplicationState)
enum class AppState : int {
    STATE_FOREGROUND = 2,
    STATE_BACKGROUND = 4,
    STATE_TERMINATED = 5,
};

class OHAppMgrClient {
public:
    static OHAppMgrClient& getInstance();

    /**
     * Connect to OH AppMgrService.
     */
    bool connect();

    /**
     * Disconnect from service.
     */
    void disconnect();

    /**
     * Register current App process with OH AppMgr.
     * Creates an AppSchedulerAdapter (OH IAppScheduler stub) and passes it
     * to AppMgr via AttachApplication. The stub receives lifecycle callbacks
     * from OH system and bridges them to Android IApplicationThread via JNI.
     *
     * @param jvm           JavaVM pointer for JNI in callback threads.
     * @param appThread     Java IApplicationThread instance (local ref).
     * @param pid           Process ID.
     * @param uid           User ID.
     * @param bundleName    OH bundle name / Android package name.
     */
    bool attachApplication(JNIEnv* env, JavaVM* jvm, jobject appThread,
                           int pid, int uid, const std::string& bundleName);

    /**
     * Legacy overload (no JNI context). Used when JVM/appThread are set separately.
     */
    bool attachApplication(int pid, int uid, const std::string& bundleName);

    /**
     * Notify App state change.
     * Corresponds to OH IAppMgr.ApplicationForegrounded/Backgrounded/Terminated().
     */
    void notifyAppState(int state);

    /**
     * [S19 LIFECYCLE-FIX] Complete the OH AbilityStage handshake.
     *
     * After ScheduleLaunchApplication (bindApplication), OH AppMgrService calls
     * AppScheduler->ScheduleAbilityStage(hapModuleInfo) and then BLOCKS waiting
     * for the app to reply IAppMgr::AddAbilityStageDone(recordId). Only after
     * that does AMS proceed to ScheduleLaunchAbility -> handleLaunchActivity.
     * If we never reply, AMS raises "Add Ability Stage TimeOut!" ->
     * LIFECYCLE_HALF_TIMEOUT / APP_FREEZE (handleLaunchActivity never fires).
     *
     * The deployed monolithic bridge 048b7576 sends this reply from
     * ScheduleAbilityStage; the split current tree dropped it (ScheduleAbilityStage
     * became a no-op) -> the LIFECYCLE wall. This restores parity. Called on the
     * OH binder thread (a direct reverse IPC, mirrors notifyAppState / 048b7576).
     */
    void addAbilityStageDone();

    /**
     * [S19 LIFECYCLE-FIX #2] Complete the OH specified-ability handshake.
     *
     * After AddAbilityStageDone, OH AMS calls AppScheduler->ScheduleAcceptWant(
     * want, moduleName) and BLOCKS on IAppMgr::ScheduleAcceptWantDone(recordId,
     * want, flag) before it will dispatch ScheduleLaunchAbility. Without the
     * reply, AMS raises "Start Specified Ability TimeOut!" -> LIFECYCLE_HALF_TIMEOUT
     * (ScheduleLaunchAbility / handleLaunchActivity never fire).
     *
     * The deployed monolithic bridge 048b7576 replies with flag=moduleName (the
     * default AbilityStage.onAcceptWant would return; AOSP has no AbilityStage so
     * moduleName is a stable process key). The split current tree dropped this
     * (ScheduleAcceptWant became a no-op). This restores parity. Called on the OH
     * binder thread (direct reverse IPC, mirrors addAbilityStageDone / 048b7576).
     */
    void scheduleAcceptWantDone(const OHOS::AAFwk::Want& want, const std::string& flag);

    /**
     * G2.14i: cache the recordId received via ScheduleLaunchApplication.AppLaunchData
     * so subsequent ApplicationForegrounded/Backgrounded calls reach the right
     * AppRunningRecord on the OH AppMS side. Default -1 hits "get appRecord fail".
     */
    void setRecordId(int32_t recordId) { recordId_ = recordId; }
    int32_t getRecordId() const { return recordId_; }

    /**
     * Get the AppScheduler adapter (for external use / testing).
     */
    OHOS::sptr<AppSchedulerAdapter> getAppSchedulerAdapter() const { return appScheduler_; }

    bool isConnected() const { return connected_; }

private:
    OHAppMgrClient() = default;
    ~OHAppMgrClient() = default;

    bool connected_ = false;
    int pid_ = 0;
    int uid_ = 0;
    int32_t recordId_ = -1;
    std::string bundleName_;
    OHOS::sptr<OHOS::AppExecFwk::IAppMgr> proxy_ = nullptr;
    OHOS::sptr<AppSchedulerAdapter> appScheduler_ = nullptr;
};

}  // namespace oh_adapter

#endif  // OH_APP_MGR_CLIENT_H
