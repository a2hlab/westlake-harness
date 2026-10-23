/*
 * Copyright (c) 2024-2025 Huawei Device Co., Ltd.
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

#include "start_ability_utils.h"

#include "ability_record.h"
#include "ability_util.h"
#include "app_scheduler.h"
#include "app_utils.h"
#include "global_constant.h"
#include "hitrace_meter.h"
#include "startup_util.h"

namespace OHOS {
namespace AAFwk {
namespace {
constexpr int32_t ERMS_ISALLOW_RESULTCODE = 10;
constexpr const char* PARAM_RESV_ANCO_CALLER_UID = "ohos.anco.param.callerUid";
constexpr const char* PARAM_RESV_ANCO_CALLER_BUNDLENAME = "ohos.anco.param.callerBundleName";
}
thread_local std::shared_ptr<StartAbilityInfo> StartAbilityUtils::startAbilityInfo;
thread_local std::shared_ptr<StartAbilityInfo> StartAbilityUtils::callerAbilityInfo;
thread_local bool StartAbilityUtils::skipCrowTest = false;
thread_local bool StartAbilityUtils::skipStartOther = false;
thread_local bool StartAbilityUtils::skipErms = false;
thread_local int32_t StartAbilityUtils::ermsResultCode = ERMS_ISALLOW_RESULTCODE;
thread_local bool StartAbilityUtils::isWantWithAppCloneIndex = false;
thread_local bool StartAbilityUtils::ermsSupportBackToCallerFlag = false;
thread_local bool StartAbilityUtils::startSpecifiedBySCB = false;

bool StartAbilityUtils::GetAppIndex(const Want &want, sptr<IRemoteObject> callerToken, int32_t &appIndex)
{
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord && abilityRecord->GetApplicationInfo().bundleName == want.GetElement().GetBundleName() &&
        abilityRecord->GetAppIndex() > AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        appIndex = abilityRecord->GetAppIndex();
        return true;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "appIndex:%{public}d", want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, -1));
    return AbilityRuntime::StartupUtil::GetAppIndex(want, appIndex);
}

bool StartAbilityUtils::GetApplicationInfo(const std::string &bundleName, int32_t userId,
    AppExecFwk::ApplicationInfo &appInfo)
{
    if (StartAbilityUtils::startAbilityInfo &&
        StartAbilityUtils::startAbilityInfo->GetAppBundleName() == bundleName) {
        appInfo = StartAbilityUtils::startAbilityInfo->abilityInfo.applicationInfo;
        return true;
    }
    if (bundleName.empty()) {
        return false;
    }
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, false);
    bool result = IN_PROCESS_CALL(
        bms->GetApplicationInfo(bundleName, AppExecFwk::ApplicationFlag::GET_BASIC_APPLICATION_INFO,
            userId, appInfo)
    );
    if (!result) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "failed: %{public}s", bundleName.c_str());
        return false;
    }
    return true;
}

bool StartAbilityUtils::GetCallerAbilityInfo(const sptr<IRemoteObject> &callerToken,
    AppExecFwk::AbilityInfo &abilityInfo)
{
    if (StartAbilityUtils::callerAbilityInfo) {
        abilityInfo = StartAbilityUtils::callerAbilityInfo->abilityInfo;
    } else {
        if (callerToken == nullptr) {
            return false;
        }
        auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
        if (abilityRecord == nullptr) {
            return false;
        }
        abilityInfo = abilityRecord->GetAbilityInfo();
    }
    return true;
}

std::vector<int32_t> StartAbilityUtils::GetCloneAppIndexes(const std::string &bundleName, int32_t userId)
{
    std::vector<int32_t> appIndexes;
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, appIndexes);
    IN_PROCESS_CALL_WITHOUT_RET(bms->GetCloneAppIndexes(bundleName, appIndexes, userId));
    return appIndexes;
}

int32_t StartAbilityUtils::CheckAppProvisionMode(const Want& want, int32_t userId, sptr<IRemoteObject> callerToken)
{
    auto abilityInfo = StartAbilityUtils::startAbilityInfo;
    if (!abilityInfo || abilityInfo->GetAppBundleName() != want.GetElement().GetBundleName()) {
        int32_t appIndex = 0;
        if (!GetAppIndex(want, callerToken, appIndex)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid app clone index");
            return ERR_APP_CLONE_INDEX_INVALID;
        }
        abilityInfo = StartAbilityInfo::CreateStartAbilityInfo(want, userId, appIndex, nullptr);
    }
    CHECK_POINTER_AND_RETURN(abilityInfo, GET_ABILITY_SERVICE_FAILED);
    if (abilityInfo->status != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "unexpected abilityInfo status: %{public}d", abilityInfo->status);
        return abilityInfo->status;
    }
    if ((abilityInfo->abilityInfo).applicationInfo.appProvisionType !=
        AppExecFwk::Constants::APP_PROVISION_TYPE_DEBUG) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "window options invalid");
        return ERR_NOT_IN_APP_PROVISION_MODE;
    }
    return ERR_OK;
}

StartAbilityInfoWrap::StartAbilityInfoWrap(const Want &want, int32_t validUserId, int32_t appIndex,
    const sptr<IRemoteObject> &callerToken, bool isExtension)
{
    if (StartAbilityUtils::startAbilityInfo != nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "startAbilityInfo created");
    }
    Want localWant = want;
    if (!StartAbilityUtils::IsCallFromAncoShellOrBroker(callerToken)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "not call from anco or broker.");
        localWant.RemoveParam(PARAM_RESV_ANCO_CALLER_UID);
        localWant.RemoveParam(PARAM_RESV_ANCO_CALLER_BUNDLENAME);
        localWant.RemoveParam(Want::PARAM_RESV_CALLER_TOKEN);
        localWant.RemoveParam(Want::PARAM_RESV_CALLER_UID);
        localWant.RemoveParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME);
        localWant.SetParam(Want::PARAM_RESV_CALLER_TOKEN, static_cast<int32_t>(IPCSkeleton::GetCallingTokenID()));
        localWant.SetParam(Want::PARAM_RESV_CALLER_UID, IPCSkeleton::GetCallingUid());
    }
    if (isExtension) {
        StartAbilityUtils::startAbilityInfo = StartAbilityInfo::CreateStartExtensionInfo(localWant,
            validUserId, appIndex);
    } else {
        StartAbilityUtils::startAbilityInfo = StartAbilityInfo::CreateStartAbilityInfo(localWant,
            validUserId, appIndex, callerToken);
    }
    if (StartAbilityUtils::startAbilityInfo != nullptr &&
        StartAbilityUtils::startAbilityInfo->abilityInfo.type == AppExecFwk::AbilityType::EXTENSION) {
        StartAbilityUtils::skipCrowTest = true;
        StartAbilityUtils::skipStartOther = true;
    }

    if (StartAbilityUtils::callerAbilityInfo != nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "callerAbilityInfo created");
    }
    StartAbilityUtils::callerAbilityInfo = StartAbilityInfo::CreateCallerAbilityInfo(callerToken);

    StartAbilityUtils::ermsResultCode = ERMS_ISALLOW_RESULTCODE;
    StartAbilityUtils::ermsSupportBackToCallerFlag = false;
    StartAbilityUtils::isWantWithAppCloneIndex = false;
    if ((want.HasParameter(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY) && appIndex >= 0 &&
        appIndex < AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) || StartAbilityUtils::startSpecifiedBySCB) {
        StartAbilityUtils::isWantWithAppCloneIndex = true;
    }
}
StartAbilityInfoWrap::StartAbilityInfoWrap()
{
    StartAbilityUtils::startAbilityInfo.reset();
    StartAbilityUtils::callerAbilityInfo.reset();
    StartAbilityUtils::skipCrowTest = false;
    StartAbilityUtils::skipStartOther = false;
    StartAbilityUtils::skipErms = false;
    StartAbilityUtils::ermsResultCode = ERMS_ISALLOW_RESULTCODE;
    StartAbilityUtils::isWantWithAppCloneIndex = false;
    StartAbilityUtils::ermsSupportBackToCallerFlag = false;
}

StartAbilityInfoWrap::~StartAbilityInfoWrap()
{
    StartAbilityUtils::startAbilityInfo.reset();
    StartAbilityUtils::callerAbilityInfo.reset();
    StartAbilityUtils::skipCrowTest = false;
    StartAbilityUtils::skipStartOther = false;
    StartAbilityUtils::skipErms = false;
    StartAbilityUtils::ermsResultCode = ERMS_ISALLOW_RESULTCODE;
    StartAbilityUtils::isWantWithAppCloneIndex = false;
    StartAbilityUtils::ermsSupportBackToCallerFlag = false;
}

void StartAbilityInfoWrap::SetStartAbilityInfo(const AppExecFwk::AbilityInfo& abilityInfo)
{
    if (StartAbilityUtils::startAbilityInfo != nullptr) {
        return;
    }
    StartAbilityUtils::startAbilityInfo = std::make_shared<StartAbilityInfo>();
    StartAbilityUtils::startAbilityInfo->abilityInfo = abilityInfo;
}

namespace {
std::shared_ptr<StartAbilityInfo> QueryAbilityInfo(const Want &want, int32_t userId, int32_t abilityInfoFlag,
    int32_t appIndex, sptr<IRemoteObject> callerToken)
{
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, nullptr);
    auto request = std::make_shared<StartAbilityInfo>();
    if (appIndex > 0 && appIndex <= AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        IN_PROCESS_CALL_WITHOUT_RET(bms->QueryCloneAbilityInfo(want.GetElement(), abilityInfoFlag, appIndex,
            request->abilityInfo, userId));
        if (appIndex != request->abilityInfo.applicationInfo.appIndex) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "query appIndex no equal: want_%{public}d, bundle_%{public}d",
                appIndex, request->abilityInfo.applicationInfo.appIndex);
        }
        return request;
    }
    if (appIndex == 0) {
        if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
            auto caller = Token::GetAbilityRecordByToken(callerToken);
            if (caller == nullptr) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "caller is nullptr");
                request->status = RESOLVE_ABILITY_ERR;
                return request;
            }
            std::string hostBundleName = caller->GetAbilityInfo().bundleName;
            TAG_LOGI(AAFwkTag::ABILITYMGR, "hostBundleName: %{public}s", hostBundleName.c_str());
            auto element = want.GetElement();
            auto pluginRet = IN_PROCESS_CALL(bms->GetPluginAbilityInfo(hostBundleName, element.GetBundleName(),
                element.GetModuleName(), element.GetAbilityName(), userId, request->abilityInfo));
            if (pluginRet != ERR_OK) {
                TAG_LOGW(AAFwkTag::ABILITYMGR, "GetPluginAbilityInfo failed %{public}d", pluginRet);
                request->status = RESOLVE_ABILITY_ERR;
            }
            request->isTargetPlugin = true;
        } else {
            IN_PROCESS_CALL_WITHOUT_RET(bms->QueryAbilityInfo(want, abilityInfoFlag, userId, request->abilityInfo));
        }
    } else {
        IN_PROCESS_CALL_WITHOUT_RET(bms->GetSandboxAbilityInfo(want, appIndex,
            abilityInfoFlag, userId, request->abilityInfo));
    }
    return request;
}
}
std::shared_ptr<StartAbilityInfo> StartAbilityInfo::CreateStartAbilityInfo(const Want &want, int32_t userId,
    int32_t appIndex, sptr<IRemoteObject> callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, nullptr);
    auto abilityInfoFlag = static_cast<uint32_t>(AbilityRuntime::StartupUtil::BuildAbilityInfoFlag()) |
        static_cast<uint32_t>(AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_WITH_SKILL);
    auto request = QueryAbilityInfo(want, userId, abilityInfoFlag, appIndex, callerToken);
    if (request == nullptr || request->status != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "QueryAbilityInfo error");
        return request;
    }
    request->customProcess = request->abilityInfo.process;
    if (appIndex > 0 && appIndex <= AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        if (request->abilityInfo.name.empty() || request->abilityInfo.bundleName.empty()) {
            std::string hostBundleName = "";
            auto caller = Token::GetAbilityRecordByToken(callerToken);
            if (caller) {
                hostBundleName = caller->GetAbilityInfo().bundleName;
            }
            FindExtensionInfo(want, abilityInfoFlag, userId, appIndex, request, hostBundleName);
        }
        return request;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "abilityInfo customProcess: %{public}s", request->customProcess.c_str());
    if (request->abilityInfo.name.empty() || request->abilityInfo.bundleName.empty()) {
        // try to find extension
        std::vector<AppExecFwk::ExtensionAbilityInfo> extensionInfos;
        if (appIndex == 0) {
            IN_PROCESS_CALL_WITHOUT_RET(bms->QueryExtensionAbilityInfos(want, abilityInfoFlag,
                userId, extensionInfos));
        } else {
            IN_PROCESS_CALL_WITHOUT_RET(bms->GetSandboxExtAbilityInfos(want, appIndex,
                abilityInfoFlag, userId, extensionInfos));
        }
        if (extensionInfos.size() <= 0) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "extensionInfo empty");
            request->status = RESOLVE_ABILITY_ERR;
            return request;
        }

        AppExecFwk::ExtensionAbilityInfo extensionInfo = extensionInfos.front();
        if (extensionInfo.bundleName.empty() || extensionInfo.name.empty()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "extensionInfo empty.");
            request->status = RESOLVE_ABILITY_ERR;
            return request;
        }
        request->extensionProcessMode = extensionInfo.extensionProcessMode;
        // For compatibility translates to AbilityInfo
        AbilityRuntime::StartupUtil::InitAbilityInfoFromExtension(extensionInfo, request->abilityInfo);
    }
    return request;
}

std::shared_ptr<StartAbilityInfo> StartAbilityInfo::CreateStartExtensionInfo(const Want &want, int32_t userId,
    int32_t appIndex, const std::string &hostBundleName)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, nullptr);
    auto abilityInfoFlag = static_cast<uint32_t>(AbilityRuntime::StartupUtil::BuildAbilityInfoFlag()) |
        static_cast<uint32_t>(AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_WITH_SKILL);
    auto abilityInfo = std::make_shared<StartAbilityInfo>();
    if (appIndex > 0 && appIndex <= AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        FindExtensionInfo(want, abilityInfoFlag, userId, appIndex, abilityInfo, hostBundleName);
        return abilityInfo;
    }

    std::vector<AppExecFwk::ExtensionAbilityInfo> extensionInfos;
    if (appIndex == 0) {
        if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
            AppExecFwk::ExtensionAbilityInfo pluginExtensionInfo;
            IN_PROCESS_CALL_WITHOUT_RET(bms->GetPluginExtensionInfo(hostBundleName, want, userId, pluginExtensionInfo));
            extensionInfos.push_back(pluginExtensionInfo);
        } else {
            IN_PROCESS_CALL_WITHOUT_RET(bms->QueryExtensionAbilityInfos(want, abilityInfoFlag, userId, extensionInfos));
        }
    } else {
        IN_PROCESS_CALL_WITHOUT_RET(bms->GetSandboxExtAbilityInfos(want, appIndex,
            abilityInfoFlag, userId, extensionInfos));
    }
    if (extensionInfos.size() <= 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "extensionInfo empty");
        abilityInfo->status = RESOLVE_ABILITY_ERR;
        return abilityInfo;
    }

    AppExecFwk::ExtensionAbilityInfo extensionInfo = extensionInfos.front();
    if (extensionInfo.bundleName.empty() || extensionInfo.name.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "extensionInfo empty");
        abilityInfo->status = RESOLVE_ABILITY_ERR;
        return abilityInfo;
    }
    abilityInfo->extensionProcessMode = extensionInfo.extensionProcessMode;
    abilityInfo->customProcess = extensionInfo.customProcess;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "extensionInfo customProcess: %{public}s", abilityInfo->customProcess.c_str());
    // For compatibility translates to AbilityInfo
    AbilityRuntime::StartupUtil::InitAbilityInfoFromExtension(extensionInfo, abilityInfo->abilityInfo);

    return abilityInfo;
}

void StartAbilityInfo::FindExtensionInfo(const Want &want, int32_t flags, int32_t userId,
    int32_t appIndex, std::shared_ptr<StartAbilityInfo> abilityInfo, const std::string &hostBundleName)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER_LOG(abilityInfo, "abilityInfo is invalid.");
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_LOG(bms, "bms is invalid.");
    AppExecFwk::ExtensionAbilityInfo extensionInfo;
    if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
        IN_PROCESS_CALL_WITHOUT_RET(bms->GetPluginExtensionInfo(hostBundleName, want, userId, extensionInfo));
    } else {
        IN_PROCESS_CALL_WITHOUT_RET(bms->QueryCloneExtensionAbilityInfoWithAppIndex(want.GetElement(),
            flags, appIndex, extensionInfo, userId));
    }
    if (extensionInfo.bundleName.empty() || extensionInfo.name.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "extensionInfo empty");
        abilityInfo->status = RESOLVE_ABILITY_ERR;
        return;
    }
    abilityInfo->customProcess = extensionInfo.customProcess;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "extensionInfo customProcess: %{public}s", abilityInfo->customProcess.c_str());
    if (AbilityRuntime::StartupUtil::IsSupportAppClone(extensionInfo.type)) {
        abilityInfo->extensionProcessMode = extensionInfo.extensionProcessMode;
        // For compatibility translates to AbilityInfo
        AbilityRuntime::StartupUtil::InitAbilityInfoFromExtension(extensionInfo, abilityInfo->abilityInfo);
    } else {
        abilityInfo->status = ERR_APP_CLONE_INDEX_INVALID;
    }
}

std::shared_ptr<StartAbilityInfo> StartAbilityInfo::CreateCallerAbilityInfo(const sptr<IRemoteObject> &callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (callerToken == nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "not call from context.");
        return nullptr;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord empty");
        return nullptr;
    }
    auto request = std::make_shared<StartAbilityInfo>();
    request->abilityInfo = abilityRecord->GetAbilityInfo();
    return request;
}

bool StartAbilityUtils::IsCallFromAncoShellOrBroker(const sptr<IRemoteObject> &callerToken)
{
    auto callingUid = IPCSkeleton::GetCallingUid();
    if (callingUid == AppUtils::GetInstance().GetCollaboratorBrokerUID()) {
        return true;
    }
    AppExecFwk::AbilityInfo callerAbilityInfo;
    if (GetCallerAbilityInfo(callerToken, callerAbilityInfo)) {
        return callerAbilityInfo.bundleName == AppUtils::GetInstance().GetBrokerDelegateBundleName();
    }
    return false;
}

void StartAbilityUtils::SetTargetCloneIndexInSameBundle(const Want &want, sptr<IRemoteObject> callerToken)
{
    auto callerRecord = Token::GetAbilityRecordByToken(callerToken);
    CHECK_POINTER(callerRecord);
    if (callerRecord->GetAbilityInfo().bundleName != want.GetElement().GetBundleName()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "not the same bundle");
        return;
    }
    if (want.HasParameter(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "want with app clone index.");
        return;
    }
    int32_t appIndex = callerRecord->GetApplicationInfo().appIndex;
    if (appIndex >= 0 && appIndex < AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        (const_cast<Want &>(want)).SetParam(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY, appIndex);
    }
}

int32_t StartAbilityUtils::StartUIAbilitiesProcessAppIndex(Want &want,
    sptr<IRemoteObject> callerToken, int32_t &appIndex)
{
    SetTargetCloneIndexInSameBundle(want, callerToken);
    if (!want.HasParameter(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY)) {
        want.SetParam(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY, 0);
    }
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities GetAppIndex failed.");
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    return ERR_OK;
}

int32_t StartAbilityUtils::HandleSelfRedirection(bool isFromOpenLink,
    const std::vector<AppExecFwk::AbilityInfo> &abilityInfos)
{
    if (!isFromOpenLink || abilityInfos.empty() || abilityInfos.size() > 1) {
        return ERR_OK;
    }
    const AppExecFwk::AbilityInfo &abilityInfo = abilityInfos[0];
    if (abilityInfo.allowSelfRedirect || abilityInfo.linkType != AppExecFwk::LinkType::APP_LINK) {
        return ERR_OK;
    }
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(
        IPCSkeleton::GetCallingPid(), processInfo);
    if (processInfo.uid_ != abilityInfo.applicationInfo.uid) {
        return ERR_OK;
    }
    return ERR_SELF_REDIRECTION_DISALLOWED;
}
}
}