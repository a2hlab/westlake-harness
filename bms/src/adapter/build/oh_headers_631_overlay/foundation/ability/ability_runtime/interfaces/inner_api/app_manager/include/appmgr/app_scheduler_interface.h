/*
 * Copyright (c) 2021-2025 Huawei Device Co., Ltd.
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

#ifndef OHOS_ABILITY_RUNTIME_APP_SCHEDULER_INTERFACE_H
#define OHOS_ABILITY_RUNTIME_APP_SCHEDULER_INTERFACE_H

#include "iremote_broker.h"
#include "ability_info.h"
#include "app_launch_data.h"
#include "configuration.h"
#include "fault_data.h"
#include "hap_module_info.h"
#include "iquick_fix_callback.h"
#include "want.h"
#include "app_malloc_info.h"
#include "app_jsheap_mem_info.h"
#include "app_cjheap_mem_info.h"

namespace OHOS {
namespace AppExecFwk {
class IAppScheduler : public IRemoteBroker {
public:
    DECLARE_INTERFACE_DESCRIPTOR(u"ohos.appexecfwk.AppScheduler");

    /**
     * ScheduleForegroundApplication, call ScheduleForegroundApplication() through proxy project,
     * Notify application to switch to foreground.
     *
     * @return
     */
    virtual bool ScheduleForegroundApplication() = 0;

    /**
     * ScheduleBackgroundApplication, call ScheduleBackgroundApplication() through proxy project,
     * Notify application to switch to background.
     *
     * @return
     */
    virtual void ScheduleBackgroundApplication() = 0;

    /**
     * ScheduleTerminateApplication, call ScheduleTerminateApplication() through proxy project,
     * Notify application to terminate.
     *
     * @param isLastProcess When it is the last application process, pass in true.
     */
    virtual void ScheduleTerminateApplication(bool isLastProcess = false) = 0;

    /**
     * ScheduleShrinkMemory, call ScheduleShrinkMemory() through proxy project,
     * Notifies the application of the memory seen.
     *
     * @param The memory value.
     *
     * @return
     */
    virtual void ScheduleShrinkMemory(const int) = 0;

    /**
     * ScheduleLowMemory, call ScheduleLowMemory() through proxy project,
     * Notify application to low memory.
     *
     * @return
     */
    virtual void ScheduleLowMemory() = 0;

    /**
     * ScheduleMemoryLevel, call ScheduleMemoryLevel() through proxy project,
     * Notify applications background the current memory level.
     *
     * @return
     */
    virtual void ScheduleMemoryLevel(int32_t level) = 0;

    /**
     * ScheduleHeapMemory, call ScheduleHeapMemory() through proxy project,
     * Get the application's memory allocation info.
     *
     * @param pid, pid input.
     * @param mallocInfo, dynamic storage information output.
     *
     * @return
     */
    virtual void ScheduleHeapMemory(const int32_t pid, OHOS::AppExecFwk::MallocInfo &mallocInfo) = 0;

    /**
     * ScheduleJsHeapMemory, call ScheduleJsHeapMemory() through proxy project,
     * triggerGC and dump the application's jsheap memory info.
     *
     * @param info, pid, tid, needGc, needSnapshot
     *
     * @return
     */
    virtual void ScheduleJsHeapMemory(OHOS::AppExecFwk::JsHeapDumpInfo &info) = 0;

    /**
     * ScheduleCjHeapMemory, call ScheduleCjHeapMemory() through proxy project,
     * triggerGC and dump the application's cjheap memory info.
     *
     * @param info, pid, needGc, needSnapshot
     *
     * @return
     */
    virtual void ScheduleCjHeapMemory(OHOS::AppExecFwk::CjHeapDumpInfo &info) = 0;

    /**
     * ScheduleLaunchApplication, call ScheduleLaunchApplication() through proxy project,
     * Notify application to launch application.
     *
     * @param The app data value.
     *
     * @return
     */
    virtual void ScheduleLaunchApplication(const AppLaunchData &, const Configuration &) = 0;

    /**
     * ScheduleUpdateApplicationInfoInstalled, call ScheduleUpdateApplicationInfoInstalled() through proxy object,
     * update the application info after new module installed.
     *
     * @param appInfo The latest application info obtained from bms for update abilityRuntimeContext.
     *
     * @return
     */
    virtual void ScheduleUpdateApplicationInfoInstalled(const ApplicationInfo &, const std::string &) = 0;

    /**
     * ScheduleAbilityStageInfo, call ScheduleAbilityStageInfo() through proxy project,
     * Notify application to launch application.
     *
     * @param The app data value.
     *
     * @return
     */
    virtual void ScheduleAbilityStage(const HapModuleInfo &) = 0;

    /**
     * Notify application to launch ability.
     *
     * @param ability The ability info.
     * @param token The ability token.
     * @param want The want to start the ability.
     * @param token The ability token.
     */
    virtual void ScheduleLaunchAbility(const AbilityInfo &, const sptr<IRemoteObject> &,
        const std::shared_ptr<AAFwk::Want> &want, int32_t abilityRecordId) = 0;

    /**
     * ScheduleCleanAbility, call ScheduleCleanAbility() through proxy project,
     * Notify application to clean ability.
     *
     * @param The ability token.
     * @return
     */
    virtual void ScheduleCleanAbility(const sptr<IRemoteObject> &, bool isCacheProcess = false) = 0;

    /**
     * ScheduleProfileChanged, call ScheduleProfileChanged() through proxy project,
     * Notify application to profile update.
     *
     * @param The profile data.
     * @return
     */
    virtual void ScheduleProfileChanged(const Profile &) = 0;

    /**
     * ScheduleConfigurationUpdated, call ScheduleConfigurationUpdated() through proxy project,
     * Notify application to configuration update.
     *
     * @param config, The configuration data.
     * @param reason, The configuration update scene flag.
     * @return
     */
    virtual void ScheduleConfigurationUpdated(const Configuration &config,
        ConfigUpdateReason reason = ConfigUpdateReason::CONFIG_UPDATE_REASON_DEFAULT) = 0;

    /**
     * ScheduleProcessSecurityExit, call ScheduleProcessSecurityExit() through proxy project,
     * Notify application process exit safely.
     *
     * @return
     */
    virtual void ScheduleProcessSecurityExit() = 0;

    /**
     * scheduleClearPageStack, call scheduleClearPageStack() through proxy project,
     * Notify application clear recovery page stack.
     *
     */
    virtual void ScheduleClearPageStack() = 0;

    /**
     * @brief Schedule the given module the onAcceptWant lifecycle call.
     *
     * @param want the param passed to onAcceptWant lifecycle.
     * @param want the moduleName of which being scheduled.
     */
    virtual void ScheduleAcceptWant(const AAFwk::Want &want, const std::string &moduleName) = 0;

    /**
     * @brief Schedule prepare terminate application
     *
     * @param moduleName module name
     */
    virtual void SchedulePrepareTerminate(const std::string &moduleName) = 0;

    virtual void ScheduleNewProcessRequest(const AAFwk::Want &want, const std::string &moduleName) = 0;

    /**
     * @brief Notify application load patch.
     *
     * @param bundleName Bundle name
     * @param callback called when LoadPatch finished.
     * @param recordId callback data
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleNotifyLoadRepairPatch(const std::string &bundleName,
        const sptr<IQuickFixCallback> &callback, const int32_t recordId) = 0;

    /**
     * @brief Notify application reload page.
     *
     * @param callback called when HotReload finished.
     * @param recordId callback data
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleNotifyHotReloadPage(const sptr<IQuickFixCallback> &callback, const int32_t recordId) = 0;

    /**
     * @brief Notify application unload patch.
     *
     * @param bundleName Bundle name
     * @param callback called when UnloadPatch finished.
     * @param recordId callback data
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleNotifyUnLoadRepairPatch(const std::string &bundleName,
        const sptr<IQuickFixCallback> &callback, const int32_t recordId) = 0;

    /**
     * @brief Schedule Notify App Fault Data.
     *
     * @param faultData fault data
     * @return Returns ERR_OK on success, error code on failure.
     */
    virtual int32_t ScheduleNotifyAppFault(const FaultData &faultData) = 0;

    /**
     * @brief Notify NativeEngine GC of status change.
     *
     * @param state GC state
     * @param pid pid
     *
     * @return Is the status change completed.
     */
    virtual int32_t ScheduleChangeAppGcState(int32_t state, uint64_t tid = 0) = 0;

    /**
     * @brief Attach app debug.
     */
    virtual void AttachAppDebug(bool isDebugFromLocal) = 0;

    /**
     * @brief Detach app debug.
     */
    virtual void DetachAppDebug() = 0;

    /**
     * ScheduleDumpIpcStart, call ScheduleDumpIpcStart(std::string& result) through proxy project,
     * Start querying the application's IPC payload info.
     *
     * @param result, start IPC dump result output.
     *
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleDumpIpcStart(std::string& result) = 0;

    /**
     * ScheduleDumpIpcStop, call ScheduleDumpIpcStop(std::string& result) through proxy project,
     * Stop querying the application's IPC payload info.
     *
     * @param result, stop IPC dump result output.
     *
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleDumpIpcStop(std::string& result) = 0;

    /**
     * ScheduleDumpIpcStat, call ScheduleDumpIpcStat(std::string& result) through proxy project,
     * Collect the application's IPC payload info.
     *
     * @param result, IPC payload result output.
     *
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleDumpIpcStat(std::string& result) = 0;

    /**
     *
     * @brief Notify application to prepare for process caching.
     *
     */
    virtual void ScheduleCacheProcess() = 0;

    /**
     * ScheduleDumpFfrt, call ScheduleDumpFfrt(std::string& result) through proxy project,
     * Start querying the application's ffrt usage.
     *
     * @param result, ffrt dump result output.
     *
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleDumpFfrt(std::string& result) = 0;

    /**
     * ScheduleDumpArkWeb, call ScheduleDumpArkWeb(std::string &customArgs, std::string& result) through proxy project,
     * Start querying the application's arkWeb usage.
     *
     * @param customArgs, customArgs for dump.
     * @param result, arkWeb dump result output.
     *
     * @return Returns 0 on success, error code on failure.
     */
    virtual int32_t ScheduleDumpArkWeb(const std::string &customArgs, std::string &result) = 0;

    /**
     * SetWatchdogBackgroundStatus, call SetWatchdogBackgroundStatus(bool status) through proxy project,
     * Notify application to set watchdog background status.
     *
     * @return
     */
    virtual void SetWatchdogBackgroundStatus(bool status) = 0;

    /**
     * Call the callback to send the pid of the started ability.
     * @param callbackId The id of the callback to send the pid.
     * @param pid The resultant process id of the started ability.
     */
    virtual void OnLoadAbilityFinished(uint64_t callbackId, int32_t pid) = 0;

    enum class Message {
        SCHEDULE_FOREGROUND_APPLICATION_TRANSACTION = 0,
        SCHEDULE_BACKGROUND_APPLICATION_TRANSACTION,
        SCHEDULE_TERMINATE_APPLICATION_TRANSACTION,
        SCHEDULE_LOWMEMORY_APPLICATION_TRANSACTION,
        SCHEDULE_SHRINK_MEMORY_APPLICATION_TRANSACTION,
        SCHEDULE_LAUNCH_ABILITY_TRANSACTION,
        SCHEDULE_CLEAN_ABILITY_TRANSACTION,
        SCHEDULE_LAUNCH_APPLICATION_TRANSACTION,
        SCHEDULE_PROFILE_CHANGED_TRANSACTION,
        SCHEDULE_CONFIGURATION_UPDATED,
        SCHEDULE_PROCESS_SECURITY_EXIT_TRANSACTION,
        SCHEDULE_ABILITY_STAGE_INFO,
        SCHEDULE_ACCEPT_WANT,
        SCHEDULE_MEMORYLEVEL_APPLICATION_TRANSACTION,
        SCHEDULE_NOTIFY_LOAD_REPAIR_PATCH,
        SCHEDULE_NOTIFY_HOT_RELOAD_PAGE,
        SCHEDULE_NOTIFY_UNLOAD_REPAIR_PATCH,
        SCHEDULE_UPDATE_APPLICATION_INFO_INSTALLED,
        SCHEDULE_HEAPMEMORY_APPLICATION_TRANSACTION,
        SCHEDULE_NOTIFY_FAULT,
        APP_GC_STATE_CHANGE,
        SCHEDULE_ATTACH_APP_DEBUG,
        SCHEDULE_DETACH_APP_DEBUG,
        SCHEDULE_NEW_PROCESS_REQUEST,
        SCHEDULE_JSHEAP_MEMORY_APPLICATION_TRANSACTION,
        SCHEDULE_DUMP_IPC_START,
        SCHEDULE_DUMP_IPC_STOP,
        SCHEDULE_DUMP_IPC_STAT,
        SCHEDULE_DUMP_FFRT,
        SCHEDULE_CACHE_PROCESS,
        SCHEDULE_CLEAR_PAGE_STACK,
        SCHEDULE_PREPARE_TERMINATE,
        WATCHDOG_BACKGROUND_STATUS_TRANSACTION,
        SCHEDULE_CJHEAP_MEMORY_APPLICATION_TRANSACTION,
        ON_LOAD_ABILITY_FINISHED,
        SCHEDULE_DUMP_ARKWEB,
    };
};
}  // namespace AppExecFwk
}  // namespace OHOS
#endif  // OHOS_ABILITY_RUNTIME_APP_SCHEDULER_INTERFACE_H
