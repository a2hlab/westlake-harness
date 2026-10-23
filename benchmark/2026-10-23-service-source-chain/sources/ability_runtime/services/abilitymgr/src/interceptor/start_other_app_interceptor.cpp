/*
 * Copyright (c) 2024 Huawei Device Co., Ltd.
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

#include "interceptor/start_other_app_interceptor.h"

#include "ability_record.h"
#include "hilog_tag_wrapper.h"
#include "parameters.h"
#include "permission_verification.h"
#include "start_ability_utils.h"
#include "tokenid_kit.h"

namespace OHOS {
namespace AAFwk {
namespace {
const uint32_t API_VERSION_MOD = 100;
const uint32_t API_SINCE_VISION = 12;
constexpr const char* ABILITY_SUPPORT_START_OTHER_APP = "persist.sys.abilityms.support.start_other_app";
constexpr const char* IS_DELEGATOR_CALL = "isDelegatorCall";
constexpr const char* OPEN_LINK_SCENE_IDENTIFICATION = "appLinkingOnly";
}

ErrCode StartOtherAppInterceptor::DoProcess(AbilityInterceptorParam param)
{
    if (StartAbilityUtils::skipStartOther) {
        StartAbilityUtils::skipStartOther = false;
        return ERR_OK;
    }
    std::string supportStart = OHOS::system::GetParameter(ABILITY_SUPPORT_START_OTHER_APP, "true");
    if (supportStart == "true") {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Abilityms support start other app.");
        return ERR_OK;
    }

    if (!param.isWithUI || param.isStartAsCaller) {
        return ERR_OK;
    }
    if (CheckNativeCall() || CheckCallerIsSystemApp() ||
        (param.abilityInfo != nullptr && CheckTargetIsSystemApp(param.abilityInfo->applicationInfo))) {
        return ERR_OK;
    }

    if (!CheckStartOtherApp(param.want)) {
        return ERR_OK;
    }

    if (param.abilityInfo != nullptr && CheckAncoShellCall(param.abilityInfo->applicationInfo, param.want)) {
        return ERR_OK;
    }

    if (param.want.HasParameter(OPEN_LINK_SCENE_IDENTIFICATION)) {
        return ERR_OK;
    }

    AppExecFwk::ApplicationInfo callerApplicationInfo;
    if (!GetApplicationInfo(param.callerToken, callerApplicationInfo)) {
        if (IsDelegatorCall(param.want)) {
            return ERR_OK;
        }
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not find callerInfo");
        return ERR_INVALID_CALLER;
    }

    if (CheckCallerApiBelow12(callerApplicationInfo)) {
        return ERR_OK;
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "not call others api above 11");
    return ERR_START_OTHER_APP_FAILED;
}

bool StartOtherAppInterceptor::CheckNativeCall()
{
    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    if (isSaCall || isShellCall) {
        return true;
    }
    return false;
}

bool StartOtherAppInterceptor::CheckCallerIsSystemApp()
{
    auto callerToken = IPCSkeleton::GetCallingFullTokenID();
    if (!Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(callerToken)) {
        return false;
    }
    return true;
}

bool StartOtherAppInterceptor::CheckTargetIsSystemApp(const AppExecFwk::ApplicationInfo &applicationInfo)
{
    return applicationInfo.isSystemApp;
}

bool StartOtherAppInterceptor::GetApplicationInfo(const sptr<IRemoteObject> &callerToken,
    AppExecFwk::ApplicationInfo &applicationInfo)
{
    if (callerToken == nullptr) {
        int32_t callerPid = IPCSkeleton::GetCallingPid();
        auto appScheduler = DelayedSingleton<AppScheduler>::GetInstance();
        bool debug;
        if (appScheduler != nullptr &&
            appScheduler->GetApplicationInfoByProcessID(callerPid, applicationInfo, debug) == ERR_OK) {
            return true;
        }
        return false;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord == nullptr) {
        return false;
    }
    applicationInfo = abilityRecord->GetApplicationInfo();
    return true;
}

bool StartOtherAppInterceptor::CheckAncoShellCall(const AppExecFwk::ApplicationInfo &applicationInfo,
    const Want want)
{
    return (applicationInfo.codePath == std::to_string(CollaboratorType::RESERVE_TYPE) ||
        applicationInfo.codePath == std::to_string(CollaboratorType::OTHERS_TYPE));
}

bool StartOtherAppInterceptor::CheckStartOtherApp(const Want want)
{
    return want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME) != want.GetElement().GetBundleName();
}

bool StartOtherAppInterceptor::CheckCallerApiBelow12(const AppExecFwk::ApplicationInfo &applicationInfo)
{
    return (applicationInfo.apiTargetVersion % API_VERSION_MOD < API_SINCE_VISION);
}

bool StartOtherAppInterceptor::IsDelegatorCall(const Want want)
{
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->
        GetRunningProcessInfoByPid(IPCSkeleton::GetCallingPid(), processInfo);
    if (processInfo.isTestProcess && want.GetBoolParam(IS_DELEGATOR_CALL, false)) {
        return true;
    }
    return false;
}
}
}