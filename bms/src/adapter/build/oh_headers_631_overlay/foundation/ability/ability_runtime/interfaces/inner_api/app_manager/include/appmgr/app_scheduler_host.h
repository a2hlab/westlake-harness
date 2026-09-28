/*
 * Copyright (c) 2021-2023 Huawei Device Co., Ltd.
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

#ifndef OHOS_ABILITY_RUNTIME_APP_SCHEDULER_HOST_H
#define OHOS_ABILITY_RUNTIME_APP_SCHEDULER_HOST_H

#include <cstdint>
#include <map>

#include "iremote_object.h"
#include "iremote_stub.h"
#include "nocopyable.h"
#include "app_scheduler_interface.h"
#include "string_ex.h"

namespace OHOS {
namespace AppExecFwk {
class AppSchedulerHost : public IRemoteStub<IAppScheduler> {
public:
    AppSchedulerHost();
    virtual ~AppSchedulerHost();
    void InitMemberFuncMap();
    virtual int OnRemoteRequest(
        uint32_t code, MessageParcel &data, MessageParcel &reply, MessageOption &option) override;

private:
    int32_t HandleScheduleForegroundApplication(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleBackgroundApplication(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleTerminateApplication(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleLowMemory(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleShrinkMemory(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleMemoryLevel(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleLaunchAbility(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleCleanAbility(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleLaunchApplication(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleAbilityStage(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleProfileChanged(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleConfigurationUpdated(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleProcessSecurityExit(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleClearPageStack(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleAcceptWant(MessageParcel &data, MessageParcel &reply);
    int32_t HandleSchedulePrepareTerminate(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleNewProcessRequest(MessageParcel &data, MessageParcel &reply);
    int32_t HandleNotifyLoadRepairPatch(MessageParcel &data, MessageParcel &reply);
    int32_t HandleNotifyHotReloadPage(MessageParcel &data, MessageParcel &reply);
    int32_t HandleNotifyUnLoadRepairPatch(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleUpdateApplicationInfoInstalled(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleHeapMemory(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleJsHeapMemory(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleCjHeapMemory(MessageParcel &data, MessageParcel &reply);
    int32_t HandleNotifyAppFault(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleChangeAppGcState(MessageParcel &data, MessageParcel &reply);
    int32_t HandleAttachAppDebug(MessageParcel &data, MessageParcel &reply);
    int32_t HandleDetachAppDebug(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleDumpIpcStart(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleDumpIpcStop(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleDumpIpcStat(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleCacheProcess(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleDumpFfrt(MessageParcel &data, MessageParcel &reply);
    int32_t HandleScheduleDumpArkWeb(MessageParcel &data, MessageParcel &reply);
    int32_t HandleSetWatchdogBackgroundStatus(MessageParcel &data, MessageParcel &reply);
    int32_t HandleOnLoadAbilityFinished(MessageParcel &data, MessageParcel &reply);
    int32_t OnRemoteRequestInner(uint32_t code, MessageParcel &data,
        MessageParcel &reply, MessageOption &option);
    int32_t OnRemoteRequestInnerFirst(uint32_t code, MessageParcel &data,
        MessageParcel &reply, MessageOption &option);
    int32_t OnRemoteRequestInnerSecond(uint32_t code, MessageParcel &data,
        MessageParcel &reply, MessageOption &option);
    int32_t OnRemoteRequestInnerThird(uint32_t code, MessageParcel &data,
        MessageParcel &reply, MessageOption &option);
    DISALLOW_COPY_AND_MOVE(AppSchedulerHost);
};
}  // namespace AppExecFwk
}  // namespace OHOS
#endif  // OHOS_ABILITY_RUNTIME_APP_SCHEDULER_HOST_H
