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

#include "ability_connect_manager.h"

#include <regex>

#include "ability_manager_service.h"
#include "ability_manager_constants.h"
#include "ability_permission_util.h"
#include "ability_resident_process_rdb.h"
#include "ability_util.h"
#include "appfreeze_manager.h"
#include "app_exit_reason_data_manager.h"
#include "assert_fault_callback_death_mgr.h"
#include "extension_ability_info.h"
#include "foreground_app_connection_manager.h"
#include "global_constant.h"
#include "hitrace_meter.h"
#include "int_wrapper.h"
#include "multi_instance_utils.h"
#include "param.h"
#include "request_id_util.h"
#include "res_sched_util.h"
#include "session/host/include/zidl/session_interface.h"
#include "startup_util.h"
#include "timeout_state_utils.h"
#include "ui_service_extension_connection_constants.h"
#include "uri_utils.h"
#include "ui_extension_wrapper.h"
#include "cache_extension_utils.h"
#include "datetime_ex.h"
#include "init_reboot.h"
#include "string_wrapper.h"
#include "user_controller/user_controller.h"

namespace OHOS {
namespace AAFwk {
namespace {
constexpr char EVENT_KEY_UID[] = "UID";
constexpr char EVENT_KEY_PID[] = "PID";
constexpr char EVENT_KEY_MESSAGE[] = "MSG";
constexpr char EVENT_KEY_PACKAGE_NAME[] = "PACKAGE_NAME";
constexpr char EVENT_KEY_PROCESS_NAME[] = "PROCESS_NAME";
const std::string DEBUG_APP = "debugApp";
const std::string FRS_APP_INDEX = "ohos.extra.param.key.frs_index";
const std::string FRS_BUNDLE_NAME = "com.ohos.formrenderservice";
const std::string MAX_UINT64_VALUE = "18446744073709551615";
#ifdef SUPPORT_ASAN
const int LOAD_TIMEOUT_MULTIPLE = 150;
const int CONNECT_TIMEOUT_MULTIPLE = 45;
const int COMMAND_TIMEOUT_MULTIPLE = 75;
const int COMMAND_TIMEOUT_MULTIPLE_NEW = 75;
const int COMMAND_WINDOW_TIMEOUT_MULTIPLE = 75;
#else
const int LOAD_TIMEOUT_MULTIPLE = 10;
const int CONNECT_TIMEOUT_MULTIPLE = 10;
const int COMMAND_TIMEOUT_MULTIPLE = 5;
const int COMMAND_TIMEOUT_MULTIPLE_NEW = 21;
const int COMMAND_WINDOW_TIMEOUT_MULTIPLE = 5;
#endif
constexpr const int32_t LOAD_TIMEOUT_MAX = 30;
const int32_t AUTO_DISCONNECT_INFINITY = -1;
constexpr const char* FROZEN_WHITE_DIALOG = "com.hmos.cast";
constexpr char BUNDLE_NAME_DIALOG[] = "com.ohos.amsdialog";
constexpr char ABILITY_NAME_ASSERT_FAULT_DIALOG[] = "AssertFaultDialog";
constexpr const char* WANT_PARAMS_APP_RESTART_FLAG = "ohos.aafwk.app.restart";
constexpr const char* PARAM_SPECIFIED_PROCESS_FLAG = "ohoSpecifiedProcessFlag";
constexpr int32_t HALF_TIMEOUT = 2;
const std::string IS_PRELOAD_UIEXTENSION_ABILITY = "ability.want.params.is_preload_uiextension_ability";

constexpr uint32_t PROCESS_MODE_RUN_WITH_MAIN_PROCESS =
    1 << static_cast<uint32_t>(AppExecFwk::ExtensionProcessMode::RUN_WITH_MAIN_PROCESS);

const std::string XIAOYI_BUNDLE_NAME = "com.hmos.vassistant";

}

AbilityConnectManager::AbilityConnectManager(int userId) : userId_(userId)
{}

AbilityConnectManager::~AbilityConnectManager()
{}

int AbilityConnectManager::StartAbility(const AbilityRequest &abilityRequest)
{
#ifdef SUPPORT_UPMS
    // grant uri permission to service extension and ui extension, must call out of serialMutext_.
    UriUtils::GetInstance().GrantUriPermissionForUIOrServiceExtension(abilityRequest);
#endif // SUPPORT_UPMS
    std::lock_guard guard(serialMutex_);
    return StartAbilityLocked(abilityRequest);
}

int AbilityConnectManager::TerminateAbility(const sptr<IRemoteObject> &token)
{
    std::lock_guard guard(serialMutex_);
    return TerminateAbilityInner(token);
}

int AbilityConnectManager::TerminateAbilityInner(const sptr<IRemoteObject> &token)
{
    auto abilityRecord = GetExtensionByTokenFromServiceMap(token);
    if (abilityRecord == nullptr) {
        abilityRecord = AbilityCacheManager::GetInstance().FindRecordByToken(token);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_CONNECT_MANAGER_NULL_ABILITY_RECORD);
    std::string element = abilityRecord->GetURI();
    TAG_LOGD(AAFwkTag::EXT, "terminate ability, ability is %{public}s", element.c_str());
    MoveToTerminatingMap(abilityRecord);
    return TerminateAbilityLocked(token);
}

int AbilityConnectManager::StopServiceAbility(const AbilityRequest &abilityRequest)
{
    TAG_LOGD(AAFwkTag::EXT, "call");
    std::lock_guard guard(serialMutex_);
    return StopServiceAbilityLocked(abilityRequest);
}

int AbilityConnectManager::StartAbilityLocked(const AbilityRequest &abilityRequest)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::EXT, "forbid start: %{public}s", abilityRequest.want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::EXT, "bundle/ability:%{public}s/%{public}s",
        abilityRequest.want.GetElement().GetBundleName().c_str(),
        abilityRequest.want.GetElement().GetAbilityName().c_str());

    int32_t ret = AbilityPermissionUtil::GetInstance().CheckMultiInstanceKeyForExtension(abilityRequest);
    if (ret != ERR_OK) {
        //  Do not distinguishing specific error codes
        return ERR_INVALID_VALUE;
    }

    std::shared_ptr<BaseExtensionRecord> targetService;
    bool isLoadedAbility = false;
    std::string hostBundleName;
    GetOrCreateServiceRecord(abilityRequest, false, targetService, isLoadedAbility);
    CHECK_POINTER_AND_RETURN(targetService, ERR_INVALID_VALUE);
    TAG_LOGI(AAFwkTag::EXT, "%{public}s/%{public}s",
        targetService->GetElementName().GetBundleName().c_str(),
        targetService->GetElementName().GetAbilityName().c_str());

    targetService->AddCallerRecord(abilityRequest.callerToken, abilityRequest.requestCode, abilityRequest.want);

    targetService->SetLaunchReason(LaunchReason::LAUNCHREASON_START_EXTENSION);

    targetService->DoBackgroundAbilityWindowDelayed(false);

    targetService->SetSessionInfo(abilityRequest.sessionInfo);

    ret = ReportXiaoYiToRSSIfNeeded(abilityRequest.abilityInfo);
    if (ret != ERR_OK) {
        return ret;
    }

    ReportEventToRSS(abilityRequest.abilityInfo, targetService, abilityRequest.callerToken);
    if (!isLoadedAbility) {
        TAG_LOGD(AAFwkTag::EXT, "targetService has not been loaded");
        LoadAbility(targetService);
    } else if (targetService->IsAbilityState(AbilityState::ACTIVE)) {
        // It may have been started through connect
        targetService->SetWant(abilityRequest.want);
        CommandAbility(targetService);
    } else {
        TAG_LOGI(AAFwkTag::EXT, "TargetService not active, state: %{public}d",
            targetService->GetAbilityState());
        EnqueueStartServiceReq(abilityRequest);
        return ERR_OK;
    }
    return ERR_OK;
}

void AbilityConnectManager::EnqueueStartServiceReq(const AbilityRequest &abilityRequest, const std::string &serviceUri)
{
    std::lock_guard guard(startServiceReqListLock_);
    auto abilityUri = abilityRequest.want.GetElement().GetURI();
    if (!serviceUri.empty()) {
        abilityUri = serviceUri;
    }
    TAG_LOGI(AAFwkTag::EXT, "abilityUri: %{public}s/%{public}s",
        abilityRequest.want.GetElement().GetBundleName().c_str(),
        abilityRequest.want.GetElement().GetAbilityName().c_str());
    auto reqListIt = startServiceReqList_.find(abilityUri);
    if (reqListIt != startServiceReqList_.end()) {
        reqListIt->second->push_back(abilityRequest);
    } else {
        auto reqList = std::make_shared<std::list<AbilityRequest>>();
        reqList->push_back(abilityRequest);
        startServiceReqList_.emplace(abilityUri, reqList);

        CHECK_POINTER(taskHandler_);
        auto callback = [abilityUri, connectManagerWeak = weak_from_this()]() {
            auto connectManager = connectManagerWeak.lock();
            CHECK_POINTER(connectManager);
            std::lock_guard guard{connectManager->startServiceReqListLock_};
            auto exist = connectManager->startServiceReqList_.erase(abilityUri);
            if (exist) {
                TAG_LOGE(AAFwkTag::EXT, "Target service %{public}s start timeout", abilityUri.c_str());
            }
        };

        int connectTimeout =
            AmsConfigurationParameter::GetInstance().GetAppStartTimeoutTime() * CONNECT_TIMEOUT_MULTIPLE;
        taskHandler_->SubmitTask(callback, std::string("start_service_timeout:") + abilityUri,
            connectTimeout);
    }
}

int AbilityConnectManager::TerminateAbilityLocked(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::EXT, "called");
    auto abilityRecord = GetExtensionByTokenFromTerminatingMap(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_CONNECT_MANAGER_NULL_ABILITY_RECORD);

    if (abilityRecord->IsTerminating()) {
        TAG_LOGD(AAFwkTag::EXT, "Ability is on terminating.");
        return ERR_OK;
    }

    if (!abilityRecord->GetConnectRecordList().empty()) {
        TAG_LOGI(AAFwkTag::EXT, "target service connected");
        auto connectRecordList = abilityRecord->GetConnectRecordList();
        HandleTerminateDisconnectTask(connectRecordList);
    }

    auto timeoutTask = [abilityRecord, connectManagerWeak = weak_from_this()]() {
        auto connectManager = connectManagerWeak.lock();
        CHECK_POINTER(connectManager);
        TAG_LOGW(AAFwkTag::EXT, "disconnect timeout");
        connectManager->HandleStopTimeoutTask(abilityRecord);
    };
    abilityRecord->Terminate(timeoutTask);
    return ERR_OK;
}

int AbilityConnectManager::StopServiceAbilityLocked(const AbilityRequest &abilityRequest)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::EXT, "call");
    AppExecFwk::ElementName element(abilityRequest.abilityInfo.deviceId, GenerateBundleName(abilityRequest),
        abilityRequest.abilityInfo.name, abilityRequest.abilityInfo.moduleName);
    std::string serviceKey = element.GetURI();
    if (FRS_BUNDLE_NAME == abilityRequest.abilityInfo.bundleName) {
        serviceKey = serviceKey + std::to_string(abilityRequest.want.GetIntParam(FRS_APP_INDEX, 0));
    }
    auto abilityRecord = GetServiceRecordByElementName(serviceKey);
    if (abilityRecord == nullptr) {
        abilityRecord = AbilityCacheManager::GetInstance().Get(abilityRequest);
        AddToServiceMap(serviceKey, abilityRecord);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    if (abilityRecord->IsTerminating()) {
        TAG_LOGI(AAFwkTag::EXT, "ability terminating");
        return ERR_OK;
    }

    if (!abilityRecord->GetConnectRecordList().empty()) {
        TAG_LOGI(AAFwkTag::EXT, "post disconnect task");
        auto connectRecordList = abilityRecord->GetConnectRecordList();
        HandleTerminateDisconnectTask(connectRecordList);
    }

    TerminateRecord(abilityRecord);
    EventInfo eventInfo = BuildEventInfo(abilityRecord);
    EventReport::SendStopServiceEvent(EventName::STOP_SERVICE, eventInfo);
    return ERR_OK;
}

void AbilityConnectManager::RemoveServiceFromMapSafe(const std::string &serviceKey)
{
    std::lock_guard lock(serviceMapMutex_);
    serviceMap_.erase(serviceKey);
    TAG_LOGD(AAFwkTag::EXT, "ServiceMap remove, size:%{public}zu", serviceMap_.size());
}

void AbilityConnectManager::GetConnectRecordListFromMap(
    const sptr<IAbilityConnection> &connect, std::list<std::shared_ptr<ConnectionRecord>> &connectRecordList)
{
    std::lock_guard lock(connectMapMutex_);
    CHECK_POINTER(connect);
    auto connectMapIter = connectMap_.find(connect->AsObject());
    if (connectMapIter != connectMap_.end()) {
        connectRecordList = connectMapIter->second;
    }
}

void AbilityConnectManager::ReportEventToRSS(const AppExecFwk::AbilityInfo &abilityInfo,
    const std::shared_ptr<BaseExtensionRecord> abilityRecord, sptr<IRemoteObject> callerToken)
{
    if (taskHandler_ == nullptr || abilityRecord == nullptr || abilityRecord->GetPid() <= 0) {
        return;
    }

    std::string reason = ResSchedUtil::GetInstance().GetThawReasonByAbilityType(abilityInfo);
    const int32_t uid = abilityInfo.applicationInfo.uid;
    const std::string bundleName = abilityInfo.applicationInfo.bundleName;
    const int32_t pid = abilityRecord->GetPid();
    auto callerAbility = Token::GetAbilityRecordByToken(callerToken);
    const int32_t callerPid = (callerAbility != nullptr) ? callerAbility->GetPid() : IPCSkeleton::GetCallingPid();
    TAG_LOGD(AAFwkTag::EXT, "%{public}d_%{public}s_%{public}d reason=%{public}s callerPid=%{public}d", uid,
        bundleName.c_str(), pid, reason.c_str(), callerPid);
    ffrt::submit([uid, bundleName, reason, pid, callerPid]() {
        ResSchedUtil::GetInstance().ReportEventToRSS(uid, bundleName, reason, pid, callerPid);
        }, ffrt::task_attr().timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));
}

int AbilityConnectManager::ConnectAbilityLocked(const AbilityRequest &abilityRequest,
    const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken, sptr<SessionInfo> sessionInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    auto connectObject = connect->AsObject();
#ifdef SUPPORT_UPMS
    // grant uri to service extension by connect, must call out of serialMutex_
    int32_t callerUser = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    if (userId_ == U0_USER_ID || callerUser == U0_USER_ID || callerUser == U1_USER_ID ||
        userId_ == AbilityRuntime::UserController::GetInstance().GetCallerUserId()) {
        UriUtils::GetInstance().GrantUriPermissionForServiceExtension(abilityRequest);
    } else {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "cross user, without grantUriPermission");
    }
#endif // SUPPORT_UPMS
    std::lock_guard guard(serialMutex_);

    // 1. get target service ability record, and check whether it has been loaded.
    int32_t ret = AbilityPermissionUtil::GetInstance().CheckMultiInstanceKeyForExtension(abilityRequest);
    if (ret != ERR_OK) {
        //  Do not distinguishing specific error codes
        return ERR_INVALID_VALUE;
    }
    std::shared_ptr<BaseExtensionRecord> targetService;
    bool isLoadedAbility = false;
    if (UIExtensionWrapper::IsUIExtension(abilityRequest.abilityInfo.extensionAbilityType) &&
        abilityRequest.uiExtensionAbilityConnectInfo != nullptr) {
        ret = GetOrCreateExtensionRecord(abilityRequest, targetService, isLoadedAbility);
    } else {
        GetOrCreateServiceRecord(abilityRequest, true, targetService, isLoadedAbility);
        CHECK_POINTER_AND_RETURN(targetService, ERR_INVALID_VALUE);
        ret = ERR_OK;
    }
    if (ret != ERR_OK) {
        return ret;
    }

    ReportEventToRSS(abilityRequest.abilityInfo, targetService, callerToken);
    // 2. get target connectRecordList, and check whether this callback has been connected.
    ConnectListType connectRecordList;
    GetConnectRecordListFromMap(connect, connectRecordList);
    bool isCallbackConnected = !connectRecordList.empty();
    auto connectedRecord = GetAbilityConnectedRecordFromRecordList(targetService, connectRecordList);
    // 3. If this service ability and callback has been connected, There is no need to connect repeatedly
    if (isLoadedAbility && (isCallbackConnected) && (connectedRecord != nullptr)) {
        TAG_LOGI(AAFwkTag::EXT, "service/callback connected");
        connectedRecord->CompleteConnectAndOnlyCallConnectDone();
        return ERR_OK;
    }

    // 4. Other cases , need to connect the service ability
    auto connectRecord = ConnectionRecord::CreateConnectionRecord(
        callerToken, targetService, connect, shared_from_this());
    CHECK_POINTER_AND_RETURN(connectRecord, ERR_INVALID_VALUE);
    connectRecord->AttachCallerInfo();
    connectRecord->SetConnectState(ConnectionState::CONNECTING);
    if (targetService->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        connectRecord->SetConnectWant(abilityRequest.want);
    }
    targetService->AddConnectRecordToList(connectRecord);
    targetService->SetSessionInfo(sessionInfo);
    connectRecordList.push_back(connectRecord);
    AddConnectObjectToMap(connectObject, connectRecordList, isCallbackConnected);
    HandleConnectionCountIncrement(connectRecord->GetCallerPid(), connectRecord->GetCallerName(),
        abilityRequest.abilityInfo.bundleName + "/" + abilityRequest.abilityInfo.name);
    targetService->SetLaunchReason(LaunchReason::LAUNCHREASON_CONNECT_EXTENSION);

    if (UIExtensionWrapper::IsWindowExtension(targetService->GetAbilityInfo().extensionAbilityType)
        && abilityRequest.sessionInfo) {
        std::lock_guard guard(windowExtensionMapMutex_);
        windowExtensionMap_.emplace(connectObject,
            WindowExtMapValType(targetService->GetApplicationInfo().accessTokenId, abilityRequest.sessionInfo));
    }

    auto &abilityInfo = abilityRequest.abilityInfo;
    ret = ReportXiaoYiToRSSIfNeeded(abilityInfo);
    if (ret != ERR_OK) {
        return ret;
    }
    ConnectAbilityLockedInner(isLoadedAbility, targetService, abilityRequest, connectRecord);
    return ret;
}

int AbilityConnectManager::ConnectAbilityLockedInner(bool isLoadedAbility,
    std::shared_ptr<BaseExtensionRecord>& targetService, const AbilityRequest& abilityRequest,
    std::shared_ptr<ConnectionRecord>& connectRecord)
{
    if (!isLoadedAbility) {
        TAG_LOGI(AAFwkTag::EXT, "load");
        LoadAbility(targetService, nullptr, false, abilityRequest.loadExtensionTimeout);
    } else if (targetService->IsAbilityState(AbilityState::ACTIVE)) {
        targetService->SetWant(abilityRequest.want);
        HandleActiveAbility(targetService, connectRecord);
    } else {
        TAG_LOGI(AAFwkTag::EXT, "targetService activing");
        targetService->SaveConnectWant(abilityRequest.want);
    }
    return ERR_OK;
}

void AbilityConnectManager::HandleConnectionCountIncrement(int32_t pid, const std::string &callerBundleName,
    const std::string &targetName)
{
    std::lock_guard<std::mutex> guard(callerPidConnectionCountMapMutex_);
    callerPidConnectionCountMap_[pid]++;
    for (const auto& threshold : thresholds_) {
        if (callerPidConnectionCountMap_[pid] == threshold) {
            EventInfo eventInfo;
            eventInfo.abilityName = targetName;
            eventInfo.callerBundleName = callerBundleName;
            eventInfo.moduleName = "ConnectionCountLimit";
            eventInfo.extensionType = threshold;
            TAG_LOGD(AAFwkTag::ABILITYMGR, "sendEventReport, pid: %{public}d, threshold: %{public}d", pid, threshold);
            EventReport::SendStartAbilityOtherExtensionEvent(EventName::START_ABILITY_OTHER_EXTENSION, eventInfo);
            break;
        }
    }
}

void AbilityConnectManager::DecrementConnectionCountAndCleanup(int32_t pid)
{
    std::lock_guard<std::mutex> guard(callerPidConnectionCountMapMutex_);
    auto it = callerPidConnectionCountMap_.find(pid);
    if (it == callerPidConnectionCountMap_.end()) {
        return;
    }
    int32_t &currentCount = it->second;
    currentCount--;
    if (currentCount == 0) {
        callerPidConnectionCountMap_.erase(it);
    }
}

void AbilityConnectManager::HandleActiveAbility(std::shared_ptr<BaseExtensionRecord> &targetService,
    std::shared_ptr<ConnectionRecord> &connectRecord)
{
    TAG_LOGI(AAFwkTag::EXT, "Active");
    if (targetService == nullptr) {
        TAG_LOGW(AAFwkTag::EXT, "null targetService");
        return;
    }
    AppExecFwk::ExtensionAbilityType extType = targetService->GetAbilityInfo().extensionAbilityType;
    bool isAbilityUIServiceExt = (extType == AppExecFwk::ExtensionAbilityType::UI_SERVICE);
    if (isAbilityUIServiceExt) {
        if (connectRecord != nullptr) {
            Want want = connectRecord->GetConnectWant();
            int connectRecordId = connectRecord->GetRecordId();
            ConnectUIServiceExtAbility(targetService, connectRecordId, want);
        }
        targetService->RemoveSignatureInfo();
        return;
    }

    if (targetService->GetConnectedListSize() >= 1) {
        TAG_LOGI(AAFwkTag::EXT, "connected");
        targetService->RemoveSignatureInfo();
        CHECK_POINTER(connectRecord);
        connectRecord->CompleteConnect();
    } else if (targetService->GetConnectingListSize() <= 1) {
        ConnectAbility(targetService);
    } else {
        TAG_LOGI(AAFwkTag::EXT, "connecting");
    }
}

std::shared_ptr<ConnectionRecord> AbilityConnectManager::GetAbilityConnectedRecordFromRecordList(
    const std::shared_ptr<BaseExtensionRecord> &targetService,
    std::list<std::shared_ptr<ConnectionRecord>> &connectRecordList)
{
    auto isMatch = [targetService](auto connectRecord) -> bool {
        if (targetService == nullptr || connectRecord == nullptr) {
            return false;
        }
        if (targetService != connectRecord->GetAbilityRecord()) {
            return false;
        }
        return true;
    };
    auto connectRecord = std::find_if(connectRecordList.begin(), connectRecordList.end(), isMatch);
    if (connectRecord != connectRecordList.end()) {
        return *connectRecord;
    }
    return nullptr;
}

int AbilityConnectManager::DisconnectAbilityLocked(const sptr<IAbilityConnection> &connect)
{
    std::lock_guard guard(serialMutex_);
    return DisconnectAbilityLocked(connect, false);
}

int AbilityConnectManager::DisconnectAbilityLocked(const sptr<IAbilityConnection> &connect, bool callerDied)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::EXT, "call");

    // 1. check whether callback was connected.
    ConnectListType connectRecordList;
    GetConnectRecordListFromMap(connect, connectRecordList);
    if (connectRecordList.empty()) {
        TAG_LOGW(AAFwkTag::EXT, "empty");
        return CONNECTION_NOT_EXIST;
    }

    // 2. schedule disconnect to target service
    int result = ERR_OK;
    ConnectListType list;
    for (auto &connectRecord : connectRecordList) {
        if (connectRecord) {
            auto abilityRecord = connectRecord->GetAbilityRecord();
            CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
            TAG_LOGD(AAFwkTag::EXT, "abilityName: %{public}s, bundleName: %{public}s",
                abilityRecord->GetAbilityInfo().name.c_str(), abilityRecord->GetAbilityInfo().bundleName.c_str());
            if (abilityRecord->GetAbilityInfo().type == AbilityType::EXTENSION) {
                RemoveExtensionDelayDisconnectTask(connectRecord);
            }
            if (connectRecord->GetCallerTokenId() != IPCSkeleton::GetCallingTokenID() &&
                static_cast<uint32_t>(IPCSkeleton::GetSelfTokenID() != IPCSkeleton::GetCallingTokenID())) {
                TAG_LOGW(AAFwkTag::EXT, "inconsistent caller");
                continue;
            }

            result = DisconnectRecordNormal(list, connectRecord, callerDied);
            if (result != ERR_OK && callerDied) {
                DisconnectRecordForce(list, connectRecord);
                result = ERR_OK;
            }

            if (result != ERR_OK) {
                TAG_LOGE(AAFwkTag::EXT, "fail: %{public}d", result);
                break;
            }
        }
    }
    for (auto&& connectRecord : list) {
        RemoveConnectionRecordFromMap(connectRecord);
    }

    return result;
}

int32_t AbilityConnectManager::SuspendExtensionAbilityLocked(const sptr<IAbilityConnection> &connect)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    TAG_LOGD(AAFwkTag::EXT, "call");

    // 1. check whether callback was connected.
    ConnectListType connectRecordList;
    GetConnectRecordListFromMap(connect, connectRecordList);
    if (connectRecordList.empty()) {
        TAG_LOGE(AAFwkTag::EXT, "empty");
        return CONNECTION_NOT_EXIST;
    }

    // 2. schedule suspend to target service
    int result = ERR_OK;
    for (auto &connectRecord : connectRecordList) {
        if (connectRecord) {
            if (connectRecord->GetCallerTokenId() != IPCSkeleton::GetCallingTokenID() &&
                static_cast<uint32_t>(IPCSkeleton::GetSelfTokenID() != IPCSkeleton::GetCallingTokenID())) {
                TAG_LOGW(AAFwkTag::EXT, "inconsistent caller");
                continue;
            }

            result = connectRecord->SuspendExtensionAbility();
            if (result != ERR_OK) {
                TAG_LOGE(AAFwkTag::EXT, "fail , ret = %{public}d", result);
                break;
            }
        }
    }
    return result;
}

int32_t AbilityConnectManager::ResumeExtensionAbilityLocked(const sptr<IAbilityConnection> &connect)
{
    std::lock_guard guard(serialMutex_);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::EXT, "call");

    // 1. check whether callback was connected.
    ConnectListType connectRecordList;
    GetConnectRecordListFromMap(connect, connectRecordList);
    if (connectRecordList.empty()) {
        TAG_LOGE(AAFwkTag::EXT, "empty");
        return CONNECTION_NOT_EXIST;
    }

    // 2. schedule suspend to target service
    int result = ERR_OK;
    for (auto &connectRecord : connectRecordList) {
        if (connectRecord) {
            if (connectRecord->GetCallerTokenId() != IPCSkeleton::GetCallingTokenID() &&
                static_cast<uint32_t>(IPCSkeleton::GetSelfTokenID() != IPCSkeleton::GetCallingTokenID())) {
                TAG_LOGW(AAFwkTag::EXT, "inconsistent caller");
                continue;
            }

            result = connectRecord->ResumeExtensionAbility();
            if (result != ERR_OK) {
                TAG_LOGE(AAFwkTag::EXT, "fail , ret = %{public}d", result);
                break;
            }
        }
    }
    return result;
}

void AbilityConnectManager::TerminateRecord(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "call");
    if (!GetExtensionByIdFromServiceMap(abilityRecord->GetRecordId()) &&
        !AbilityCacheManager::GetInstance().FindRecordByToken(abilityRecord->GetToken())) {
        return;
    }
    auto timeoutTask = [abilityRecord, connectManagerWeak = weak_from_this()]() {
        auto connectManager = connectManagerWeak.lock();
        CHECK_POINTER(connectManager);
        TAG_LOGW(AAFwkTag::EXT, "disconnect timeout");
        connectManager->HandleStopTimeoutTask(abilityRecord);
    };

    MoveToTerminatingMap(abilityRecord);
    abilityRecord->Terminate(timeoutTask);
}

int AbilityConnectManager::DisconnectRecordNormal(ConnectListType &list,
    std::shared_ptr<ConnectionRecord> connectRecord, bool callerDied) const
{
    auto result = connectRecord->DisconnectAbility();
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::EXT, "fail:%{public}d", result);
        return result;
    }

    if (connectRecord->GetConnectState() == ConnectionState::DISCONNECTED) {
        TAG_LOGW(AAFwkTag::EXT, "normal:%{public}d", connectRecord->GetRecordId());
        connectRecord->CompleteDisconnect(ERR_OK, callerDied);
        list.emplace_back(connectRecord);
    }
    return ERR_OK;
}

void AbilityConnectManager::DisconnectRecordForce(ConnectListType &list,
    std::shared_ptr<ConnectionRecord> connectRecord)
{
    auto abilityRecord = connectRecord->GetAbilityRecord();
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "null abilityRecord");
        return;
    }
    abilityRecord->RemoveConnectRecordFromList(connectRecord);
    connectRecord->CompleteDisconnect(ERR_OK, true);
    list.emplace_back(connectRecord);
    bool isUIService = (abilityRecord->GetAbilityInfo().extensionAbilityType ==
        AppExecFwk::ExtensionAbilityType::UI_SERVICE);
    if (abilityRecord->IsConnectListEmpty() && !isUIService) {
        if (abilityRecord->IsNeverStarted()) {
            TAG_LOGW(AAFwkTag::EXT, "force terminate ability record state: %{public}d",
                abilityRecord->GetAbilityState());
            TerminateRecord(abilityRecord);
        } else if (abilityRecord->IsAbilityState(AbilityState::ACTIVE)) {
            TAG_LOGW(AAFwkTag::EXT, "force disconnect ability record state: %{public}d",
                abilityRecord->GetAbilityState());
            connectRecord->CancelConnectTimeoutTask();
            abilityRecord->DisconnectAbility();
        }
    }
}

int AbilityConnectManager::AttachAbilityThreadLocked(
    const sptr<IAbilityScheduler> &scheduler, const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    return AttachAbilityThreadInner(scheduler, token);
}

void AbilityConnectManager::OnAppStateChanged(const AppInfo &info)
{
    auto serviceMap = GetServiceMap();
    std::for_each(serviceMap.begin(), serviceMap.end(), [&info](ServiceMapType::reference service) {
        if (service.second && info.bundleName == service.second->GetApplicationInfo().bundleName &&
            info.appIndex == service.second->GetAppIndex() && info.instanceKey == service.second->GetInstanceKey() &&
            info.pid == service.second->GetPid()) {
            auto appName = service.second->GetApplicationInfo().name;
            auto uid = service.second->GetAbilityInfo().applicationInfo.uid;
            auto isExist = [&appName, &uid](
                               const AppData &appData) { return appData.appName == appName && appData.uid == uid; };
            auto iter = std::find_if(info.appData.begin(), info.appData.end(), isExist);
            if (iter != info.appData.end()) {
                service.second->SetAppState(info.state);
            }
        }
    });

    auto cacheAbilityList = AbilityCacheManager::GetInstance().GetAbilityList();
    std::for_each(cacheAbilityList.begin(), cacheAbilityList.end(), [&info](
        std::shared_ptr<BaseExtensionRecord> &service) {
        if (service && info.bundleName == service->GetApplicationInfo().bundleName &&
            info.appIndex == service->GetAppIndex() && info.instanceKey == service->GetInstanceKey()) {
            auto appName = service->GetApplicationInfo().name;
            auto uid = service->GetAbilityInfo().applicationInfo.uid;
            auto isExist = [&appName, &uid](const AppData &appData) {
                return appData.appName == appName && appData.uid == uid;
            };
            auto iter = std::find_if(info.appData.begin(), info.appData.end(), isExist);
            if (iter != info.appData.end()) {
                service->SetAppState(info.state);
            }
        }
    });
    if (info.state == AppState::TERMINATED) {
        UnRegisterPreloadUIExtensionHostClient(info.pid);
    }
}

int AbilityConnectManager::AbilityTransitionDone(const sptr<IRemoteObject> &token, int state)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    int targetState = AbilityRecord::ConvertLifeCycleToAbilityState(static_cast<AbilityLifeCycleState>(state));
    std::string abilityState = AbilityRecord::ConvertAbilityState(static_cast<AbilityState>(targetState));
    std::shared_ptr<BaseExtensionRecord> abilityRecord;
    if (targetState == AbilityState::INACTIVE) {
        abilityRecord = GetExtensionByTokenFromServiceMap(token);
        CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    } else if (targetState == AbilityState::FOREGROUND || targetState == AbilityState::BACKGROUND) {
        abilityRecord = GetExtensionByTokenFromServiceMap(token);
        if (abilityRecord == nullptr) {
            abilityRecord = GetExtensionByTokenFromTerminatingMap(token);
        }
    } else if (targetState == AbilityState::INITIAL) {
        abilityRecord = GetExtensionByTokenFromTerminatingMap(token);
    }

    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    TAG_LOGI(AAFwkTag::EXT, "%{public}s/%{public}s, %{public}s",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(), abilityState.c_str());

    switch (targetState) {
        case AbilityState::INACTIVE: {
            return DispatchInactive(abilityRecord, state, token);
        }
        case AbilityState::FOREGROUND: {
            return DispatchForeground(abilityRecord, token);
        }
        case AbilityState::BACKGROUND: {
            return DispatchBackground(abilityRecord, token);
        }
        case AbilityState::INITIAL: {
            return DispatchTerminate(abilityRecord, token);
        }
        default: {
            TAG_LOGW(AAFwkTag::EXT, "not support transiting state: %{public}d", state);
            return ERR_INVALID_VALUE;
        }
    }
}

int AbilityConnectManager::AbilityWindowConfigTransactionDone(const sptr<IRemoteObject> &token,
    const WindowConfig &windowConfig)
{
    std::lock_guard<ffrt::mutex> guard(serialMutex_);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    abilityRecord->SaveAbilityWindowConfig(windowConfig);
    return ERR_OK;
}

void AbilityConnectManager::ProcessPreload(const std::shared_ptr<BaseExtensionRecord> &record) const
{
    auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER(record);
    CHECK_POINTER(bundleMgrHelper);
    auto abilityInfo = record->GetAbilityInfo();
    Want want;
    want.SetElementName(abilityInfo.deviceId, abilityInfo.bundleName, abilityInfo.name, abilityInfo.moduleName);
    auto uid = record->GetUid();
    want.SetParam("uid", uid);
    bundleMgrHelper->ProcessPreload(want);
}

int AbilityConnectManager::ScheduleConnectAbilityDoneLocked(
    const sptr<IRemoteObject> &token, const sptr<IRemoteObject> &remoteObject)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    auto abilityRecord = BaseExtensionRecord::TransferToExtensionRecordBase(Token::GetAbilityRecordByToken(token));
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    TAG_LOGI(AAFwkTag::EXT, "%{public}s/%{public}s", abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());

    if ((!abilityRecord->IsAbilityState(AbilityState::INACTIVE)) &&
        (!abilityRecord->IsAbilityState(AbilityState::ACTIVE))) {
        TAG_LOGE(AAFwkTag::EXT, "ability not inactive, state: %{public}d",
            abilityRecord->GetAbilityState());
        return INVALID_CONNECTION_STATE;
    }
    abilityRecord->RemoveConnectWant();
    abilityRecord->RemoveSignatureInfo();

    if (abilityRecord->GetAbilityInfo().type == AbilityType::SERVICE) {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateAbilityState(
            token, AppExecFwk::AbilityState::ABILITY_STATE_CONNECTED);
    } else {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateExtensionState(
            token, AppExecFwk::ExtensionState::EXTENSION_STATE_CONNECTED);
    }
    EventInfo eventInfo = BuildEventInfo(abilityRecord);
    eventInfo.userId = userId_;
    eventInfo.bundleName = abilityRecord->GetAbilityInfo().bundleName;
    eventInfo.moduleName = abilityRecord->GetAbilityInfo().moduleName;
    eventInfo.abilityName = abilityRecord->GetAbilityInfo().name;
    EventReport::SendConnectServiceEvent(EventName::CONNECT_SERVICE, eventInfo);

    abilityRecord->SetConnRemoteObject(remoteObject);
    // There may be multiple callers waiting for the connection result
    auto connectRecordList = abilityRecord->GetConnectRecordList();
    for (auto &connectRecord : connectRecordList) {
        CHECK_POINTER_CONTINUE(connectRecord);
        connectRecord->ScheduleConnectAbilityDone();
        if (abilityRecord->GetAbilityInfo().type == AbilityType::EXTENSION &&
            abilityRecord->GetAbilityInfo().extensionAbilityType != AppExecFwk::ExtensionAbilityType::SERVICE) {
            PostExtensionDelayDisconnectTask(connectRecord);
        }
    }
    CompleteStartServiceReq(abilityRecord->GetURI());
    ResSchedUtil::GetInstance().ReportLoadingEventToRss(LoadingStage::CONNECT_END, abilityRecord->GetPid(),
        abilityRecord->GetUid(), 0, abilityRecord->GetAbilityRecordId());
    return ERR_OK;
}

void AbilityConnectManager::ProcessEliminateAbilityRecord(std::shared_ptr<BaseExtensionRecord> eliminateRecord)
{
    CHECK_POINTER(eliminateRecord);
    std::string eliminateKey = eliminateRecord->GetURI();
    if (FRS_BUNDLE_NAME == eliminateRecord->GetAbilityInfo().bundleName) {
        eliminateKey = eliminateKey +
            std::to_string(eliminateRecord->GetWant().GetIntParam(FRS_APP_INDEX, 0));
    }
    AddToServiceMap(eliminateKey, eliminateRecord);
    TerminateRecord(eliminateRecord);
}

void AbilityConnectManager::TerminateOrCacheAbility(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    if (abilityRecord->IsSceneBoard()) {
        return;
    }
    if (IsCacheExtensionAbility(abilityRecord)) {
        std::string serviceKey = abilityRecord->GetURI();
        auto abilityInfo = abilityRecord->GetAbilityInfo();
        TAG_LOGD(AAFwkTag::EXT, "Cache the ability, service:%{public}s, extension type %{public}d",
            serviceKey.c_str(), abilityInfo.extensionAbilityType);
        if (FRS_BUNDLE_NAME == abilityInfo.bundleName) {
            AppExecFwk::ElementName elementName(abilityInfo.deviceId, abilityInfo.bundleName, abilityInfo.name,
                abilityInfo.moduleName);
            serviceKey = elementName.GetURI() +
                std::to_string(abilityRecord->GetWant().GetIntParam(FRS_APP_INDEX, 0));
        }
        RemoveServiceFromMapSafe(serviceKey);
        auto eliminateRecord = AbilityCacheManager::GetInstance().Put(abilityRecord);
        if (eliminateRecord != nullptr) {
            TAG_LOGD(AAFwkTag::EXT, "Terminate the eliminated ability, service:%{public}s.",
                eliminateRecord->GetURI().c_str());
            ProcessEliminateAbilityRecord(eliminateRecord);
        }
        return;
    }
    TAG_LOGD(AAFwkTag::EXT, "Terminate the ability, service:%{public}s, extension type %{public}d",
        abilityRecord->GetURI().c_str(), abilityRecord->GetAbilityInfo().extensionAbilityType);
    TerminateRecord(abilityRecord);
}

int AbilityConnectManager::ScheduleDisconnectAbilityDoneLocked(const sptr<IRemoteObject> &token)
{
    if (AAFwk::AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: ScheduleDisconnectAbilityDoneLocked");
        return AAFwk::INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    auto abilityRecord = GetExtensionByTokenFromServiceMap(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, CONNECTION_NOT_EXIST);

    auto connect = abilityRecord->GetDisconnectingRecord();
    CHECK_POINTER_AND_RETURN(connect, CONNECTION_NOT_EXIST);

    int ret = CheckAbilityStateForDisconnect(abilityRecord);
    if (ret != ERR_OK) {
        return ret;
    }

    UpdateStateAndCompleteDisconnect(abilityRecord, connect, token);

    CleanupConnectionAndTerminateIfNeeded(abilityRecord);

    RemoveConnectionRecordFromMap(connect);

    EventInfo eventInfo = BuildEventInfo(abilityRecord);
    EventReport::SendDisconnectServiceEvent(EventName::DISCONNECT_SERVICE, eventInfo);
    return ERR_OK;
}

int AbilityConnectManager::CheckAbilityStateForDisconnect(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    if (!abilityRecord->IsAbilityState(AbilityState::ACTIVE)) {
        TAG_LOGE(AAFwkTag::EXT, "ability not active, state: %{public}d",
            abilityRecord->GetAbilityState());
        return INVALID_CONNECTION_STATE;
    }
    return ERR_OK;
}

int AbilityConnectManager::UpdateStateAndCompleteDisconnect(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const std::shared_ptr<ConnectionRecord> &connect, const sptr<IRemoteObject> &token)
{
    if (abilityRecord->GetAbilityInfo().type == AbilityType::SERVICE) {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateAbilityState(
            token, AppExecFwk::AbilityState::ABILITY_STATE_DISCONNECTED);
    } else {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateExtensionState(
            token, AppExecFwk::ExtensionState::EXTENSION_STATE_DISCONNECTED);
    }

    TAG_LOGI(AAFwkTag::EXT, "schedule disconnect %{public}s/%{public}s",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());

    // complete disconnect and remove record from conn map
    connect->ScheduleDisconnectAbilityDone();
    abilityRecord->RemoveConnectRecordFromList(connect);
    return ERR_OK;
}

int AbilityConnectManager::CleanupConnectionAndTerminateIfNeeded(std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    if (abilityRecord->IsConnectListEmpty() && abilityRecord->GetStartId() == 0) {
        if (abilityRecord->GetAbilityInfo().extensionAbilityType ==
            AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "don't terminate uiservice");
        } else {
            TAG_LOGI(AAFwkTag::EXT, "terminate or cache");
            TerminateOrCacheAbility(abilityRecord);
        }
    }
    return ERR_OK;
}

int AbilityConnectManager::ScheduleCommandAbilityDoneLocked(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);
    auto abilityRecord = BaseExtensionRecord::TransferToExtensionRecordBase(Token::GetAbilityRecordByToken(token));
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    std::string element = abilityRecord->GetURI();
    TAG_LOGD(AAFwkTag::EXT, "Ability: %{public}s", element.c_str());

    if ((!abilityRecord->IsAbilityState(AbilityState::INACTIVE)) &&
        (!abilityRecord->IsAbilityState(AbilityState::ACTIVE))) {
        TAG_LOGE(AAFwkTag::EXT, "ability not inactive, state: %{public}d",
            abilityRecord->GetAbilityState());
        return INVALID_CONNECTION_STATE;
    }
    EventInfo eventInfo = BuildEventInfo(abilityRecord);
    EventReport::SendStartServiceEvent(EventName::START_SERVICE, eventInfo);
    abilityRecord->RemoveSignatureInfo();
    // complete command and pop waiting start ability from queue.
    CompleteCommandAbility(abilityRecord);

    return ERR_OK;
}

int AbilityConnectManager::ScheduleCommandAbilityWindowDone(
    const sptr<IRemoteObject> &token,
    const sptr<SessionInfo> &sessionInfo,
    WindowCommand winCmd,
    AbilityCommand abilityCmd)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    std::string element = abilityRecord->GetURI();
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "%{public}s/%{public}s, persistentId:%{private}d, winCmd:%{public}d, abilityCmd:%{public}d",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(),
        sessionInfo->persistentId, winCmd, abilityCmd);

    // Only foreground mode need cancel, cause only foreground CommandAbilityWindow post timeout task.
    if (taskHandler_ && winCmd == WIN_CMD_FOREGROUND) {
        int recordId = abilityRecord->GetRecordId();
        std::string taskName = std::string("CommandWindowTimeout_") + std::to_string(recordId) + std::string("_") +
                               std::to_string(sessionInfo->persistentId) + std::string("_") + std::to_string(winCmd);
        taskHandler_->CancelTask(taskName);
    }

    if (winCmd == WIN_CMD_DESTROY) {
        HandleCommandDestroy(sessionInfo);
    }

    abilityRecord->SetAbilityWindowState(sessionInfo, winCmd, true);

    CompleteStartServiceReq(element);
    return ERR_OK;
}

void AbilityConnectManager::HandleCommandDestroy(const sptr<SessionInfo> &sessionInfo)
{
    if (sessionInfo == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "null sessionInfo");
        return;
    }
    if (sessionInfo->sessionToken) {
        std::lock_guard guard(windowExtensionMapMutex_);
        for (auto& item : windowExtensionMap_) {
            auto sessionInfoVal = item.second.second;
            if (sessionInfoVal && sessionInfoVal->callerToken == sessionInfo->sessionToken) {
                windowExtensionMap_.erase(item.first);
                break;
            }
        }
    }
}

void AbilityConnectManager::CompleteCommandAbility(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    if (taskHandler_) {
        int recordId = abilityRecord->GetRecordId();
        std::string taskName = std::string("CommandTimeout_") + std::to_string(recordId) + std::string("_") +
                               std::to_string(abilityRecord->GetStartId());
        taskHandler_->CancelTask(taskName);
    }

    abilityRecord->SetAbilityState(AbilityState::ACTIVE);

    // manage queued request
    CompleteStartServiceReq(abilityRecord->GetURI());
    if (abilityRecord->NeedConnectAfterCommand()) {
        abilityRecord->UpdateConnectWant();
        ConnectAbility(abilityRecord);
    }
}

void AbilityConnectManager::CompleteStartServiceReq(const std::string &serviceUri)
{
    std::shared_ptr<std::list<OHOS::AAFwk::AbilityRequest>> reqList;
    {
        std::lock_guard guard(startServiceReqListLock_);
        auto it = startServiceReqList_.find(serviceUri);
        if (it != startServiceReqList_.end()) {
            reqList = it->second;
            startServiceReqList_.erase(it);
            if (taskHandler_) {
                taskHandler_->CancelTask(std::string("start_service_timeout:") + serviceUri);
            }
        }
    }

    if (reqList) {
        TAG_LOGI(AAFwkTag::EXT, "target service activating: %{public}zu, uri: %{public}s", reqList->size(),
            serviceUri.c_str());
        for (const auto &req: *reqList) {
            StartAbilityLocked(req);
        }
    }
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetServiceRecordByAbilityRequest(
    const AbilityRequest &abilityRequest)
{
    AppExecFwk::ElementName element(abilityRequest.abilityInfo.deviceId, GenerateBundleName(abilityRequest),
        abilityRequest.abilityInfo.name, abilityRequest.abilityInfo.moduleName);
    std::string serviceKey = element.GetURI();
    return GetServiceRecordByElementName(serviceKey);
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetServiceRecordByElementName(const std::string &element)
{
    std::lock_guard guard(serviceMapMutex_);
    auto mapIter = serviceMap_.find(element);
    if (mapIter != serviceMap_.end()) {
        return mapIter->second;
    }
    return nullptr;
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetExtensionByTokenFromServiceMap(
    const sptr<IRemoteObject> &token)
{
    auto IsMatch = [token](auto service) {
        if (!service.second) {
            return false;
        }
        sptr<IRemoteObject> srcToken = service.second->GetToken();
        return srcToken == token;
    };
    std::lock_guard lock(serviceMapMutex_);
    auto serviceRecord = std::find_if(serviceMap_.begin(), serviceMap_.end(), IsMatch);
    if (serviceRecord != serviceMap_.end()) {
        return serviceRecord->second;
    }
    return nullptr;
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetExtensionByIdFromServiceMap(
    const int64_t &abilityRecordId)
{
    auto IsMatch = [abilityRecordId](auto &service) {
        if (!service.second) {
            return false;
        }
        return service.second->GetAbilityRecordId() == abilityRecordId;
    };

    std::lock_guard lock(serviceMapMutex_);
    auto serviceRecord = std::find_if(serviceMap_.begin(), serviceMap_.end(), IsMatch);
    if (serviceRecord != serviceMap_.end()) {
        return serviceRecord->second;
    }
    return nullptr;
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetExtensionByIdFromTerminatingMap(
    const int64_t &abilityRecordId)
{
    auto IsMatch = [abilityRecordId](auto &extensionRecord) {
        if (extensionRecord == nullptr) {
            return false;
        }
        return extensionRecord->GetAbilityRecordId() == abilityRecordId;
    };

    std::lock_guard lock(serviceMapMutex_);
    auto extensionRecord = std::find_if(terminatingExtensionList_.begin(), terminatingExtensionList_.end(), IsMatch);
    if (extensionRecord != terminatingExtensionList_.end()) {
        return *extensionRecord;
    }
    return nullptr;
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetExtensionByTokenFromTerminatingMap(
    const sptr<IRemoteObject> &token)
{
    auto IsMatch = [token](auto& extensionRecord) {
        if (extensionRecord == nullptr) {
            return false;
        }
        auto terminatingToken = extensionRecord->GetToken();
        if (terminatingToken != nullptr) {
            return terminatingToken->AsObject() == token;
        }
        return false;
    };

    std::lock_guard lock(serviceMapMutex_);
    auto terminatingExtensionRecord =
        std::find_if(terminatingExtensionList_.begin(), terminatingExtensionList_.end(), IsMatch);
    if (terminatingExtensionRecord != terminatingExtensionList_.end()) {
        return *terminatingExtensionRecord;
    }
    return nullptr;
}

std::list<std::shared_ptr<ConnectionRecord>> AbilityConnectManager::GetConnectRecordListByCallback(
    sptr<IAbilityConnection> callback)
{
    std::lock_guard guard(connectMapMutex_);
    std::list<std::shared_ptr<ConnectionRecord>> connectList;
    CHECK_POINTER_AND_RETURN(callback, connectList);
    auto connectMapIter = connectMap_.find(callback->AsObject());
    if (connectMapIter != connectMap_.end()) {
        connectList = connectMapIter->second;
    }
    return connectList;
}

void AbilityConnectManager::LoadAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    std::function<void(const std::shared_ptr<BaseExtensionRecord>&)> updateRecordCallback, bool isPreloadUIExtension,
    int32_t loadTimeout)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    abilityRecord->SetStartTime();

    if (!abilityRecord->CanRestartRootLauncher()) {
        TAG_LOGE(AAFwkTag::EXT, "CanRestartRootLauncher fail");
        RemoveServiceAbility(abilityRecord);
        return;
    }
    int32_t loadTimeoutFinal =
        AmsConfigurationParameter::GetInstance().GetAppStartTimeoutTime() * GetLoadTimeout(loadTimeout);
    if (!abilityRecord->IsDebugApp()) {
        TAG_LOGD(AAFwkTag::EXT, "IsDebug is false, here is not debug app");
        PostLoadTimeoutTask(abilityRecord, loadTimeoutFinal);
    }
    sptr<Token> token = abilityRecord->GetToken();
    sptr<Token> perToken = nullptr;
    if (abilityRecord->IsCreateByConnect()) {
        auto connectingRecord = abilityRecord->GetConnectingRecord();
        CHECK_POINTER(connectingRecord);
        perToken = static_cast<Token*>(connectingRecord->GetToken().GetRefPtr());
    } else {
        auto callerList = abilityRecord->GetCallerRecordList();
        if (!callerList.empty() && callerList.back()) {
            auto caller = callerList.back()->GetCaller();
            if (caller) {
                perToken = caller->GetToken();
            }
        }
    }
    if (updateRecordCallback != nullptr) {
        updateRecordCallback(abilityRecord);
    }
    AbilityRuntime::LoadParam loadParam;
    loadParam.abilityRecordId = abilityRecord->GetRecordId();
    loadParam.isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    loadParam.token = token;
    loadParam.preToken = perToken;
    loadParam.instanceKey = abilityRecord->GetInstanceKey();
    loadParam.isCallerSetProcess = abilityRecord->IsCallerSetProcess();
    loadParam.customProcessFlag = abilityRecord->GetCustomProcessFlag();
    loadParam.extensionProcessMode = abilityRecord->GetExtensionProcessMode();
    loadParam.isPreloadUIExtension = isPreloadUIExtension;
    loadParam.loadTimeout = loadTimeoutFinal;
    SetExtensionLoadParam(loadParam, abilityRecord);
    AbilityRuntime::FreezeUtil::GetInstance().AddLifecycleEvent(loadParam.token, "AbilityConnectManager::LoadAbility");
    HandleLoadAbilityOrStartSpecifiedProcess(loadParam, abilityRecord);
}

void AbilityConnectManager::HandleLoadAbilityOrStartSpecifiedProcess(
    const AbilityRuntime::LoadParam &loadParam, const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "LoadAbility");
    DelayedSingleton<AppScheduler>::GetInstance()->LoadAbility(
        loadParam, abilityRecord->GetAbilityInfo(), abilityRecord->GetApplicationInfo(), abilityRecord->GetWant());
}

void AbilityConnectManager::StartSpecifiedProcess(
    const LoadAbilityContext &context, const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    std::lock_guard<std::mutex> guard(loadAbilityQueueLock_);
    auto requestId = RequestIdUtil::GetRequestId();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartSpecifiedProcess, requestId: %{public}d,", requestId);
    std::map<int32_t, LoadAbilityContext> mapContext_ = { { requestId, context } };
    loadAbilityQueue_.push_back(mapContext_);
    if (loadAbilityQueue_.size() > 1) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "loadAbilityQueue_ size > 1, requestId: %{public}d", requestId);
        return;
    }
    DelayedSingleton<AppScheduler>::GetInstance()->StartSpecifiedProcess(
        *context.want, *context.abilityInfo, requestId, context.loadParam->customProcessFlag);
}

void AbilityConnectManager::OnStartSpecifiedProcessResponse(const std::string &flag, int32_t requestId)
{
    std::lock_guard<std::mutex> guard(loadAbilityQueueLock_);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "OnStartSpecifiedProcessResponse, requestId: %{public}d, flag: %{public}s",
        requestId, flag.c_str());
    if (!loadAbilityQueue_.empty()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "OnStartSpecifiedProcessResponse LoadAbility");
        auto &front = loadAbilityQueue_.front();
        front[requestId].want->SetParam(PARAM_SPECIFIED_PROCESS_FLAG, flag);
        DelayedSingleton<AppScheduler>::GetInstance()->LoadAbility(*front[requestId].loadParam,
            *(front[requestId].abilityInfo), *(front[requestId].appInfo), *(front[requestId].want));
        loadAbilityQueue_.pop_front();
    }
}

void AbilityConnectManager::OnStartSpecifiedProcessTimeoutResponse(int32_t requestId)
{
    std::lock_guard<std::mutex> guard(loadAbilityQueueLock_);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "OnStartSpecifiedProcessTimeoutResponse requestId: %{public}d", requestId);

    if (!loadAbilityQueue_.empty()) {
        auto &front = loadAbilityQueue_.front();
        DelayedSingleton<AppScheduler>::GetInstance()->LoadAbility(*(front[requestId].loadParam),
            *(front[requestId].abilityInfo), *(front[requestId].appInfo), *(front[requestId].want));
        loadAbilityQueue_.pop_front();
    }
}

bool AbilityConnectManager::HasRequestIdInLoadAbilityQueue(int32_t requestId)
{
    std::lock_guard<std::mutex> guard(loadAbilityQueueLock_);
    for (const auto &map : loadAbilityQueue_) {
        if (map.find(requestId) != map.end()) {
            return true;
        }
    }
    return false;
}

void AbilityConnectManager::SetExtensionLoadParam(AbilityRuntime::LoadParam &loadParam,
    std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    if (!IsStrictMode(abilityRecord)) {
        TAG_LOGD(AAFwkTag::EXT, "SetExtensionLoadParam, strictMode:false");
        return;
    }
    auto &extensionParam = loadParam.extensionLoadParam;
    extensionParam.strictMode = true;
    extensionParam.networkEnableFlags = DelayedSingleton<ExtensionConfig>::GetInstance()->IsExtensionNetworkEnable(
        abilityRecord->GetAbilityInfo().extensionTypeName);
    extensionParam.saEnableFlags = DelayedSingleton<ExtensionConfig>::GetInstance()->IsExtensionSAEnable(
        abilityRecord->GetAbilityInfo().extensionTypeName);
    TAG_LOGD(AAFwkTag::EXT,
        "SetExtensionLoadParam, networkEnableFlags:%{public}d, saEnableFlags:%{public}d, strictMode:%{public}d",
        extensionParam.networkEnableFlags, extensionParam.saEnableFlags, extensionParam.strictMode);
}

bool AbilityConnectManager::IsStrictMode(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, false);
    const auto &want = abilityRecord->GetWant();
    bool strictMode = want.GetBoolParam(OHOS::AAFwk::STRICT_MODE, false);
    if (abilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::INPUTMETHOD) {
        return strictMode;
    }
    if (!NeedExtensionControl(abilityRecord)) {
        return false;
    }
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGD(AAFwkTag::EXT, "SetExtensionLoadParam, not SACall, force enable strictMode");
        return true;
    }
    if (!want.HasParameter(OHOS::AAFwk::STRICT_MODE)) {
        TAG_LOGD(AAFwkTag::EXT, "SetExtensionLoadParam, no striteMode param, force enable strictMode");
        return true;
    }
    return strictMode;
}

bool AbilityConnectManager::NeedExtensionControl(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, false);
    auto extensionType = abilityRecord->GetAbilityInfo().extensionAbilityType;
    if (extensionType == AppExecFwk::ExtensionAbilityType::SERVICE ||
        extensionType == AppExecFwk::ExtensionAbilityType::DATASHARE) {
        return false;
    }
    if (!abilityRecord->GetCustomProcessFlag().empty()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "SetExtensionLoadParam, customProces not empty");
        return false;
    }
    if (abilityRecord->GetExtensionProcessMode() == PROCESS_MODE_RUN_WITH_MAIN_PROCESS) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "SetExtensionLoadParam, extensionProcesMode:runWithMain");
        return false;
    }
    if (abilityRecord->GetAbilityInfo().applicationInfo.allowMultiProcess) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "SetExtensionLoadParam, allowMultiProcess:1");
        return false;
    }
    return true;
}

void AbilityConnectManager::PostRestartResidentTask(const AbilityRequest &abilityRequest)
{
    TAG_LOGI(AAFwkTag::EXT, "PostRestartResidentTask start");
    CHECK_POINTER(taskHandler_);
    std::string taskName = std::string("RestartResident_") + std::string(abilityRequest.abilityInfo.name);
    auto task = [abilityRequest, connectManagerWeak = weak_from_this()]() {
        auto connectManager = connectManagerWeak.lock();
        CHECK_POINTER(connectManager);
        connectManager->HandleRestartResidentTask(abilityRequest);
    };
    int restartIntervalTime = 0;
    auto abilityMgr = DelayedSingleton<AbilityManagerService>::GetInstance();
    if (abilityMgr) {
        restartIntervalTime = AmsConfigurationParameter::GetInstance().GetRestartIntervalTime();
    }
    TAG_LOGD(AAFwkTag::EXT, "PostRestartResidentTask, time:%{public}d", restartIntervalTime);
    taskHandler_->SubmitTask(task, taskName, restartIntervalTime);
    TAG_LOGI(AAFwkTag::EXT, "end");
}

void AbilityConnectManager::HandleRestartResidentTask(const AbilityRequest &abilityRequest)
{
    TAG_LOGI(AAFwkTag::EXT, "HandleRestartResidentTask start");
    std::lock_guard guard(serialMutex_);
    auto findRestartResidentTask = [abilityRequest](const AbilityRequest &requestInfo) {
        return (requestInfo.want.GetElement().GetBundleName() == abilityRequest.want.GetElement().GetBundleName() &&
            requestInfo.want.GetElement().GetModuleName() == abilityRequest.want.GetElement().GetModuleName() &&
            requestInfo.want.GetElement().GetAbilityName() == abilityRequest.want.GetElement().GetAbilityName());
    };
    auto findIter = find_if(restartResidentTaskList_.begin(), restartResidentTaskList_.end(), findRestartResidentTask);
    if (findIter != restartResidentTaskList_.end()) {
        restartResidentTaskList_.erase(findIter);
    }
    StartAbilityLocked(abilityRequest);
}

void AbilityConnectManager::PostTimeOutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    uint32_t messageId)
{
    CHECK_POINTER(abilityRecord);
    int connectRecordId = 0;
    if (messageId == AbilityManagerService::CONNECT_TIMEOUT_MSG) {
        auto connectRecord = abilityRecord->GetConnectingRecord();
        CHECK_POINTER(connectRecord);
        connectRecordId = connectRecord->GetRecordId();
    }
    PostTimeOutTask(abilityRecord, connectRecordId, messageId);
}

void AbilityConnectManager::PostTimeOutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    int connectRecordId, uint32_t messageId)
{
    CHECK_POINTER(abilityRecord);
    CHECK_POINTER(taskHandler_);

    std::string taskName;
    auto recordId = abilityRecord->GetAbilityRecordId();
    TAG_LOGD(AAFwkTag::EXT, "task: %{public}s/%{public}s, %{public}d, %{public}" PRId64,
        abilityRecord->GetAbilityInfo().bundleName.c_str(), abilityRecord->GetAbilityInfo().name.c_str(),
        connectRecordId, recordId);
    if (messageId == AbilityManagerService::CONNECT_TIMEOUT_MSG) {
        HandlePostConnectTimeout(abilityRecord, connectRecordId, recordId);
    } else {
        TAG_LOGE(AAFwkTag::EXT, "messageId error");
        return;
    }
}

void AbilityConnectManager::PostLoadTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    int32_t loadTimeout)
{
    CHECK_POINTER(abilityRecord);
    auto recordId = abilityRecord->GetAbilityRecordId();
    TAG_LOGD(AAFwkTag::EXT, "task: %{public}s/%{public}s, %{public}" PRId64,
        abilityRecord->GetAbilityInfo().bundleName.c_str(), abilityRecord->GetAbilityInfo().name.c_str(), recordId);
    abilityRecord->SendEvent(AbilityManagerService::LOAD_HALF_TIMEOUT_MSG, loadTimeout / HALF_TIMEOUT,
        recordId, true);
    abilityRecord->SendEvent(AbilityManagerService::LOAD_TIMEOUT_MSG, loadTimeout, recordId, true);
}

void AbilityConnectManager::HandlePostConnectTimeout(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    int connectRecordId, int64_t recordId)
{
    std::string taskName = std::to_string(connectRecordId);
    int32_t delayTime = AmsConfigurationParameter::GetInstance().GetAppStartTimeoutTime() * CONNECT_TIMEOUT_MULTIPLE;
    
    abilityRecord->SendEvent(AbilityManagerService::CONNECT_HALF_TIMEOUT_MSG, delayTime / HALF_TIMEOUT, recordId,
        true, taskName);
    abilityRecord->SendEvent(AbilityManagerService::CONNECT_TIMEOUT_MSG, delayTime, recordId, true, taskName);
    
    ResSchedUtil::GetInstance().ReportLoadingEventToRss(LoadingStage::CONNECT_BEGIN, abilityRecord->GetPid(),
        abilityRecord->GetUid(), delayTime, recordId);
}

int32_t AbilityConnectManager::GetLoadTimeout(int32_t loadTimeout)
{
#ifdef SUPPORT_ASAN
    return LOAD_TIMEOUT_MULTIPLE;
#else
    if (loadTimeout == 0) {
        TAG_LOGD(AAFwkTag::EXT, "loadTimeout 0, reset to default");
        return LOAD_TIMEOUT_MULTIPLE;
    }
    if (loadTimeout < 0 || loadTimeout > LOAD_TIMEOUT_MAX) {
        TAG_LOGW(AAFwkTag::EXT, "loadTimeout %{public}d invalid, reset to default", loadTimeout);
        return LOAD_TIMEOUT_MULTIPLE;
    }
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGW(AAFwkTag::EXT, "not sa call");
        return LOAD_TIMEOUT_MULTIPLE;
    }
    return loadTimeout;
#endif
}

void AbilityConnectManager::HandleStartTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGW(AAFwkTag::EXT, "load timeout");
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER(abilityRecord);
    HandleStartTimeoutTaskInner(abilityRecord);
}

void AbilityConnectManager::HandleStartTimeoutTaskInner(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    auto connectingList = abilityRecord->GetConnectingRecordList();
    for (auto &connectRecord : connectingList) {
        if (connectRecord == nullptr) {
            TAG_LOGW(AAFwkTag::EXT, "connectRecord null");
            continue;
        }
        connectRecord->CompleteDisconnect(ERR_OK, false, true);
        abilityRecord->RemoveConnectRecordFromList(connectRecord);
        RemoveConnectionRecordFromMap(connectRecord);
    }

    if (GetExtensionByTokenFromServiceMap(abilityRecord->GetToken()) == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "timeout ability record not exist");
        return;
    }
    TAG_LOGW(AAFwkTag::EXT, "AbilityUri:%{public}s/%{public}s,user:%{public}d",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(), userId_);
    MoveToTerminatingMap(abilityRecord);
    RemoveServiceAbility(abilityRecord);
    DelayedSingleton<AppScheduler>::GetInstance()->AttachTimeOut(abilityRecord->GetToken());
    if (abilityRecord->IsSceneBoard()) {
        if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId_)) {
            RestartAbility(abilityRecord, userId_);
        }
        return;
    }
    if (IsAbilityNeedKeepAlive(abilityRecord)) {
        TAG_LOGW(AAFwkTag::EXT, "load timeout");
        RestartAbility(abilityRecord, userId_);
    }
}

void AbilityConnectManager::HandleCommandTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGI(AAFwkTag::EXT, "HandleCommandTimeoutTask start");
    CHECK_POINTER(abilityRecord);
    if (abilityRecord->GetAbilityInfo().name == AbilityConfig::LAUNCHER_ABILITY_NAME) {
        TAG_LOGD(AAFwkTag::EXT, "Handle root launcher command timeout.");
        // terminate the timeout root launcher.
        DelayedSingleton<AppScheduler>::GetInstance()->AttachTimeOut(abilityRecord->GetToken());
        return;
    }
    CleanActivatingTimeoutAbility(abilityRecord);
    TAG_LOGI(AAFwkTag::EXT, "HandleCommandTimeoutTask end");
}

void AbilityConnectManager::HandleConnectTimeoutTask(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    TAG_LOGW(AAFwkTag::EXT, "connect timeout");
    CHECK_POINTER(abilityRecord);
    auto connectList = abilityRecord->GetConnectRecordList();
    std::lock_guard guard(serialMutex_);
    for (const auto &connectRecord : connectList) {
        RemoveExtensionDelayDisconnectTask(connectRecord);
        connectRecord->CancelConnectTimeoutTask();
        connectRecord->CompleteDisconnect(ERR_OK, false, true);
        abilityRecord->RemoveConnectRecordFromList(connectRecord);
        RemoveConnectionRecordFromMap(connectRecord);
    }

    if (IsSpecialAbility(abilityRecord->GetAbilityInfo()) || abilityRecord->GetStartId() != 0) {
        TAG_LOGI(AAFwkTag::EXT, "no need terminate");
        return;
    }

    TerminateRecord(abilityRecord);
}

void AbilityConnectManager::HandleCommandWindowTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<SessionInfo> &sessionInfo, WindowCommand winCmd)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start");
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER(abilityRecord);
    abilityRecord->SetAbilityWindowState(sessionInfo, winCmd, true);
    // manage queued request
    CompleteStartServiceReq(abilityRecord->GetURI());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "end");
}

void AbilityConnectManager::HandleStopTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "Complete stop ability timeout start.");
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER(abilityRecord);
    HandleStopTimeoutTaskInner(abilityRecord);
}

void AbilityConnectManager::HandleStopTimeoutTaskInner(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TerminateDone(abilityRecord);
}

void AbilityConnectManager::HandleTerminateDisconnectTask(const ConnectListType& connectlist)
{
    TAG_LOGD(AAFwkTag::EXT, "Disconnect ability when terminate.");
    for (auto& connectRecord : connectlist) {
        if (!connectRecord) {
            continue;
        }
        auto targetService = connectRecord->GetAbilityRecord();
        if (targetService) {
            TAG_LOGW(AAFwkTag::EXT, "record complete disconnect. recordId:%{public}d",
                connectRecord->GetRecordId());
            connectRecord->CompleteDisconnect(ERR_OK, false, true);
            targetService->RemoveConnectRecordFromList(connectRecord);
            RemoveConnectionRecordFromMap(connectRecord);
        };
    }
}

int AbilityConnectManager::DispatchInactive(const std::shared_ptr<BaseExtensionRecord> &abilityRecord, int state,
    const sptr<IRemoteObject> &token)
{
    TAG_LOGD(AAFwkTag::EXT, "DispatchInactive call");
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (abilityRecord->GetAbilityInfo().type == AbilityType::SERVICE) {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateAbilityState(
            token, AppExecFwk::AbilityState::ABILITY_STATE_CREATE);
    } else {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateExtensionState(
            token, AppExecFwk::ExtensionState::EXTENSION_STATE_CREATE);
        auto preloadTask = [owner = weak_from_this(), abilityRecord] {
            auto acm = owner.lock();
            if (acm == nullptr) {
                TAG_LOGE(AAFwkTag::EXT, "null AbilityConnectManager");
                return;
            }
            acm->ProcessPreload(abilityRecord);
        };
        if (taskHandler_ != nullptr) {
            taskHandler_->SubmitTask(preloadTask);
        }
    }

    CHECK_POINTER_AND_RETURN(eventHandler_, ERR_INVALID_VALUE);
    if (!abilityRecord->IsAbilityState(AbilityState::INACTIVATING)) {
        TAG_LOGE(AAFwkTag::EXT,
            "error. expect %{public}d, actual %{public}d callback %{public}d",
            AbilityState::INACTIVATING, abilityRecord->GetAbilityState(), state);
        return ERR_INVALID_VALUE;
    }
    eventHandler_->RemoveEvent(AbilityManagerService::INACTIVE_TIMEOUT_MSG, abilityRecord->GetAbilityRecordId());
    if (abilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE) {
        ResSchedUtil::GetInstance().ReportLoadingEventToRss(LoadingStage::LOAD_END,
            abilityRecord->GetPid(), abilityRecord->GetUid(), 0, abilityRecord->GetAbilityRecordId());
    }

    // complete inactive
    abilityRecord->SetAbilityState(AbilityState::INACTIVE);
    if (abilityRecord->IsCreateByConnect()) {
        ConnectAbility(abilityRecord);
    } else {
        CommandAbility(abilityRecord);
        if (abilityRecord->GetConnectRecordList().size() > 0) {
            // It means someone called connectAbility when service was loading
            abilityRecord->UpdateConnectWant();
            ConnectAbility(abilityRecord);
        }
    }

    return ERR_OK;
}

int AbilityConnectManager::DispatchForeground(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    abilityRecord->RemoveSignatureInfo();

    CHECK_POINTER_AND_RETURN(taskHandler_, ERR_INVALID_VALUE);
    // remove foreground timeout task.
    abilityRecord->RemoveForegroundTimeoutTask();
    auto task = [self = weak_from_this(), abilityRecord]() {
        auto selfObj = self.lock();
        CHECK_POINTER(selfObj);
        selfObj->CompleteForeground(abilityRecord);
    };
    taskHandler_->SubmitTask(task, TaskQoS::USER_INTERACTIVE);

    return ERR_OK;
}

int AbilityConnectManager::DispatchBackground(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(taskHandler_, ERR_INVALID_VALUE);
    // remove background timeout task.
    taskHandler_->CancelTask("background_" + std::to_string(abilityRecord->GetAbilityRecordId()));

    auto task = [self = weak_from_this(), abilityRecord]() {
        auto selfObj = self.lock();
        CHECK_POINTER(selfObj);
        selfObj->CompleteBackground(abilityRecord);
    };
    taskHandler_->SubmitTask(task, TaskQoS::USER_INTERACTIVE);

    return ERR_OK;
}

int AbilityConnectManager::DispatchTerminate(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (abilityRecord->GetAbilityInfo().type == AbilityType::SERVICE) {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateAbilityState(
            token, AppExecFwk::AbilityState::ABILITY_STATE_TERMINATED);
    } else {
        DelayedSingleton<AppScheduler>::GetInstance()->UpdateExtensionState(
            token, AppExecFwk::ExtensionState::EXTENSION_STATE_TERMINATED);
    }
    // remove terminate timeout task
    if (taskHandler_ != nullptr) {
        taskHandler_->CancelTask("terminate_" + std::to_string(abilityRecord->GetAbilityRecordId()));
    }
    ResSchedUtil::GetInstance().ReportLoadingEventToRss(LoadingStage::DESTROY_END, abilityRecord->GetPid(),
        abilityRecord->GetUid(), 0, abilityRecord->GetRecordId());
    // complete terminate
    TerminateDone(abilityRecord);
    return ERR_OK;
}

void AbilityConnectManager::ConnectAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    AppExecFwk::ExtensionAbilityType extType = abilityRecord->GetAbilityInfo().extensionAbilityType;
    if (extType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        ResumeConnectAbility(abilityRecord);
    } else {
        PostTimeOutTask(abilityRecord, AbilityManagerService::CONNECT_TIMEOUT_MSG);
        if (abilityRecord->GetToken()) {
            AbilityRuntime::FreezeUtil::GetInstance().AddLifecycleEvent(abilityRecord->GetToken()->AsObject(),
                "AbilityConnectManager::ConnectAbility");
        }
        abilityRecord->ConnectAbility();
    }
}

void AbilityConnectManager::ConnectUIServiceExtAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    int connectRecordId, const Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    PostTimeOutTask(abilityRecord, connectRecordId, AbilityManagerService::CONNECT_TIMEOUT_MSG);
    abilityRecord->ConnectAbilityWithWant(want);
}

void AbilityConnectManager::ResumeConnectAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGI(AAFwkTag::EXT, "ResumeConnectAbility");
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    std::list<std::shared_ptr<ConnectionRecord>> connectingList = abilityRecord->GetConnectingRecordList();
    for (auto &connectRecord : connectingList) {
        if (connectRecord == nullptr) {
            TAG_LOGW(AAFwkTag::EXT, "connectRecord null");
            continue;
        }
        int connectRecordId = connectRecord->GetRecordId();
        PostTimeOutTask(abilityRecord, connectRecordId, AbilityManagerService::CONNECT_TIMEOUT_MSG);
        abilityRecord->ConnectAbilityWithWant(connectRecord->GetConnectWant());
    }
}

void AbilityConnectManager::CommandAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    if (taskHandler_ != nullptr) {
        // first connect ability, There is at most one connect record.
        int recordId = abilityRecord->GetRecordId();
        abilityRecord->AddStartId();
        std::string taskName = std::string("CommandTimeout_") + std::to_string(recordId) + std::string("_") +
                               std::to_string(abilityRecord->GetStartId());
        auto timeoutTask = [abilityRecord, connectManagerWeak = weak_from_this()]() {
            auto connectManager = connectManagerWeak.lock();
            CHECK_POINTER(connectManager);
            TAG_LOGE(AAFwkTag::EXT, "command ability timeout. %{public}s",
                abilityRecord->GetAbilityInfo().name.c_str());
            connectManager->HandleCommandTimeoutTask(abilityRecord);
        };
        bool useOldMultiple = abilityRecord->GetAbilityInfo().name == AbilityConfig::LAUNCHER_ABILITY_NAME ||
            abilityRecord->GetAbilityInfo().name == AbilityConfig::CALLUI_ABILITY_NAME;
        auto timeoutMultiple = useOldMultiple ? COMMAND_TIMEOUT_MULTIPLE : COMMAND_TIMEOUT_MULTIPLE_NEW;
        auto commandTimeout =
            AmsConfigurationParameter::GetInstance().GetAppStartTimeoutTime() * timeoutMultiple;
        taskHandler_->SubmitTask(timeoutTask, taskName, commandTimeout);
        // scheduling command ability
        abilityRecord->CommandAbility();
    }
}

void AbilityConnectManager::CommandAbilityWindow(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<SessionInfo> &sessionInfo, WindowCommand winCmd)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    CHECK_POINTER(sessionInfo);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "ability: %{public}s, persistentId: %{private}d, wincmd: %{public}d",
        abilityRecord->GetURI().c_str(), sessionInfo->persistentId, winCmd);
    abilityRecord->SetAbilityWindowState(sessionInfo, winCmd, false);
    if (taskHandler_ != nullptr) {
        int recordId = abilityRecord->GetRecordId();
        std::string taskName = std::string("CommandWindowTimeout_") + std::to_string(recordId) + std::string("_") +
            std::to_string(sessionInfo->persistentId) + std::string("_") + std::to_string(winCmd);
        auto timeoutTask = [abilityRecord, sessionInfo, winCmd, connectManagerWeak = weak_from_this()]() {
            auto connectManager = connectManagerWeak.lock();
            CHECK_POINTER(connectManager);
            TAG_LOGE(AAFwkTag::ABILITYMGR, "command window timeout. %{public}s",
                abilityRecord->GetAbilityInfo().name.c_str());
            connectManager->HandleCommandWindowTimeoutTask(abilityRecord, sessionInfo, winCmd);
        };
        int commandWindowTimeout =
            AmsConfigurationParameter::GetInstance().GetAppStartTimeoutTime() * COMMAND_WINDOW_TIMEOUT_MULTIPLE;
        taskHandler_->SubmitTask(timeoutTask, taskName, commandWindowTimeout);
        // scheduling command ability
        abilityRecord->CommandAbilityWindow(sessionInfo, winCmd);
    }
}

void AbilityConnectManager::TerminateAbilityWindowLocked(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const sptr<SessionInfo> &sessionInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    CHECK_POINTER(sessionInfo);
    auto abilitystateStr = abilityRecord->ConvertAbilityState(abilityRecord->GetAbilityState());
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "ability:%{public}s/%{public}s, persistentId:%{public}d, abilityState:%{public}s",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(),
        sessionInfo->persistentId, abilitystateStr.c_str());
    EventInfo eventInfo;
    eventInfo.bundleName = abilityRecord->GetAbilityInfo().bundleName;
    eventInfo.abilityName = abilityRecord->GetAbilityInfo().name;
    EventReport::SendAbilityEvent(EventName::TERMINATE_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    std::lock_guard guard(serialMutex_);
    eventInfo.errCode = TerminateAbilityInner(abilityRecord->GetToken());
    if (eventInfo.errCode != ERR_OK) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "terminate ability window locked failed: %{public}d", eventInfo.errCode);
        EventReport::SendAbilityEvent(EventName::TERMINATE_ABILITY_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
}

void AbilityConnectManager::TerminateDone(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER(abilityRecord);
    if (!abilityRecord->IsAbilityState(AbilityState::TERMINATING)) {
        std::string expect = AbilityRecord::ConvertAbilityState(AbilityState::TERMINATING);
        std::string actual = AbilityRecord::ConvertAbilityState(abilityRecord->GetAbilityState());
        TAG_LOGE(AAFwkTag::EXT,
            "error. expect %{public}s, actual %{public}s", expect.c_str(), actual.c_str());
        return;
    }
    abilityRecord->RemoveAbilityDeathRecipient();
    if (abilityRecord->IsSceneBoard()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "scb exit, kill processes");
        KillProcessesByUserId();
    }
    DelayedSingleton<AppScheduler>::GetInstance()->TerminateAbility(abilityRecord->GetToken(), false);
    RemoveServiceAbility(abilityRecord);
}

void AbilityConnectManager::RemoveConnectionRecordFromMap(std::shared_ptr<ConnectionRecord> connection)
{
    std::lock_guard lock(connectMapMutex_);
    for (auto &connectCallback : connectMap_) {
        auto &connectList = connectCallback.second;
        auto connectRecord = std::find(connectList.begin(), connectList.end(), connection);
        if (connectRecord != connectList.end()) {
            CHECK_POINTER(*connectRecord);
            TAG_LOGD(AAFwkTag::EXT, "connrecord(%{public}d)", (*connectRecord)->GetRecordId());
            connectList.remove(connection);
            if (connection != nullptr) {
                DecrementConnectionCountAndCleanup(connection->GetCallerPid());
            }
            if (connectList.empty()) {
                RemoveConnectDeathRecipient(connectCallback.first);
                connectMap_.erase(connectCallback.first);
            }
            return;
        }
    }
}

void AbilityConnectManager::RemoveServiceAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    TAG_LOGD(AAFwkTag::EXT, "Remove service(%{public}s) from terminating map.",
        abilityRecord->GetURI().c_str());
    std::lock_guard lock(serviceMapMutex_);
    terminatingExtensionList_.remove(abilityRecord);
}

void AbilityConnectManager::AddConnectDeathRecipient(sptr<IRemoteObject> connectObject)
{
    CHECK_POINTER(connectObject);
    {
        std::lock_guard guard(recipientMapMutex_);
        auto it = recipientMap_.find(connectObject);
        if (it != recipientMap_.end()) {
            TAG_LOGE(AAFwkTag::EXT, "recipient added before");
            return;
        }
    }

    std::weak_ptr<AbilityConnectManager> thisWeakPtr(shared_from_this());
    sptr<IRemoteObject::DeathRecipient> deathRecipient =
        new AbilityConnectCallbackRecipient([thisWeakPtr](const wptr<IRemoteObject> &remote) {
            auto abilityConnectManager = thisWeakPtr.lock();
            if (abilityConnectManager) {
                abilityConnectManager->OnCallBackDied(remote);
            }
        });
    if (!connectObject->AddDeathRecipient(deathRecipient)) {
        TAG_LOGW(AAFwkTag::EXT, "fail");
    }
    std::lock_guard guard(recipientMapMutex_);
    recipientMap_.emplace(connectObject, deathRecipient);
}

void AbilityConnectManager::RemoveConnectDeathRecipient(sptr<IRemoteObject> connectObject)
{
    CHECK_POINTER(connectObject);
    sptr<IRemoteObject::DeathRecipient> deathRecipient;
    {
        std::lock_guard guard(recipientMapMutex_);
        auto it = recipientMap_.find(connectObject);
        if (it == recipientMap_.end()) {
            return;
        }
        deathRecipient = it->second;
        recipientMap_.erase(it);
    }

    connectObject->RemoveDeathRecipient(deathRecipient);
}

void AbilityConnectManager::OnCallBackDied(const wptr<IRemoteObject> &remote)
{
    auto object = remote.promote();
    CHECK_POINTER(object);
    if (taskHandler_) {
        auto task = [object, connectManagerWeak = weak_from_this()]() {
            auto connectManager = connectManagerWeak.lock();
            CHECK_POINTER(connectManager);
            connectManager->HandleCallBackDiedTask(object);
        };
        taskHandler_->SubmitTask(task, TASK_ON_CALLBACK_DIED);
    }
}

void AbilityConnectManager::HandleCallBackDiedTask(const sptr<IRemoteObject> &connect)
{
    TAG_LOGD(AAFwkTag::EXT, "called");
    CHECK_POINTER(connect);
    {
        std::lock_guard guard(windowExtensionMapMutex_);
        auto item = windowExtensionMap_.find(connect);
        if (item != windowExtensionMap_.end()) {
            windowExtensionMap_.erase(item);
        }
    }

    {
        std::lock_guard guard(connectMapMutex_);
        auto it = connectMap_.find(connect);
        if (it != connectMap_.end()) {
            ConnectListType connectRecordList = it->second;
            for (auto &connRecord : connectRecordList) {
                CHECK_POINTER_CONTINUE(connRecord);
                connRecord->ClearConnCallBack();
            }
        } else {
            TAG_LOGI(AAFwkTag::EXT, "not find");
            return;
        }
    }

    sptr<IAbilityConnection> object = iface_cast<IAbilityConnection>(connect);
    std::lock_guard guard(serialMutex_);
    DisconnectAbilityLocked(object, true);
}

void AbilityConnectManager::OnLoadAbilityFailed(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    abilityRecord->RemoveLoadTimeoutTask();
    HandleStartTimeoutTask(abilityRecord);
}

void AbilityConnectManager::OnAbilityDied(const std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    TAG_LOGI(AAFwkTag::EXT, "%{public}s/%{public}s", abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());
    if (abilityRecord->GetAbilityInfo().type != AbilityType::SERVICE &&
        abilityRecord->GetAbilityInfo().type != AbilityType::EXTENSION) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "type not service");
        return;
    }
    if (eventHandler_ && abilityRecord->GetAbilityState() == AbilityState::INITIAL) {
        abilityRecord->RemoveLoadTimeoutTask();
    }
    if (eventHandler_ && abilityRecord->GetAbilityState() == AbilityState::FOREGROUNDING) {
        abilityRecord->RemoveForegroundTimeoutTask();
    }
    if (taskHandler_ && abilityRecord->GetAbilityState() == AbilityState::BACKGROUNDING) {
        taskHandler_->CancelTask("background_" + std::to_string(abilityRecord->GetAbilityRecordId()));
    }
    if (taskHandler_ && abilityRecord->GetAbilityState() == AbilityState::TERMINATING) {
        taskHandler_->CancelTask("terminate_" + std::to_string(abilityRecord->GetAbilityRecordId()));
    }
    if (taskHandler_) {
        auto task = [abilityRecord, connectManagerWeak = weak_from_this()]() {
            auto connectManager = connectManagerWeak.lock();
            CHECK_POINTER(connectManager);
            connectManager->HandleAbilityDiedTask(abilityRecord);
        };
        taskHandler_->SubmitTask(task, TASK_ON_ABILITY_DIED);
    }
}

void AbilityConnectManager::OnTimeOut(uint32_t msgId, int64_t abilityRecordId, bool isHalf)
{
    auto abilityRecord = GetExtensionByIdFromServiceMap(abilityRecordId);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "null abilityRecord");
        return;
    }
    PrintTimeOutLog(abilityRecord, msgId, isHalf);
    if (isHalf) {
        return;
    }
    switch (msgId) {
        case AbilityManagerService::LOAD_TIMEOUT_MSG:
            HandleStartTimeoutTask(abilityRecord);
            break;
        case AbilityManagerService::INACTIVE_TIMEOUT_MSG:
            HandleInactiveTimeout(abilityRecord);
            break;
        case AbilityManagerService::FOREGROUND_TIMEOUT_MSG:
            HandleForegroundTimeoutTask(abilityRecord);
            break;
        case AbilityManagerService::CONNECT_TIMEOUT_MSG:
            HandleConnectTimeoutTask(abilityRecord);
            break;
        default:
            break;
    }
}

void AbilityConnectManager::HandleInactiveTimeout(const std::shared_ptr<BaseExtensionRecord> &ability)
{
    TAG_LOGI(AAFwkTag::EXT, "HandleInactiveTimeout start");
    CHECK_POINTER(ability);
    if (ability->GetAbilityInfo().name == AbilityConfig::LAUNCHER_ABILITY_NAME) {
        TAG_LOGD(AAFwkTag::EXT, "Handle root launcher inactive timeout.");
        // terminate the timeout root launcher.
        DelayedSingleton<AppScheduler>::GetInstance()->AttachTimeOut(ability->GetToken());
        return;
    }
    CleanActivatingTimeoutAbility(ability);
    TAG_LOGI(AAFwkTag::EXT, "HandleInactiveTimeout end");
}

void AbilityConnectManager::CleanActivatingTimeoutAbility(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    if (abilityRecord->IsAbilityState(AbilityState::ACTIVE)) {
        TAG_LOGI(AAFwkTag::EXT, "ability is active, no need handle.");
        return;
    }
    CleanActivatingTimeoutAbilityInner(abilityRecord);
}

void AbilityConnectManager::CleanActivatingTimeoutAbilityInner(std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    auto connectList = abilityRecord->GetConnectRecordList();
    std::lock_guard guard(serialMutex_);
    for (const auto &connectRecord : connectList) {
        CHECK_POINTER_CONTINUE(connectRecord);
        connectRecord->CompleteDisconnect(ERR_OK, false, true);
        abilityRecord->RemoveConnectRecordFromList(connectRecord);
        RemoveConnectionRecordFromMap(connectRecord);
    }

    TerminateRecord(abilityRecord);
    if (!IsAbilityNeedKeepAlive(abilityRecord)) {
        return;
    }
    if (!abilityRecord->IsSceneBoard() || AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId_)) {
        RestartAbility(abilityRecord, userId_);
    }
}

bool AbilityConnectManager::IsAbilityNeedKeepAlive(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER_AND_RETURN(abilityRecord, false);
    const auto &abilityInfo = abilityRecord->GetAbilityInfo();
    if (IsSpecialAbility(abilityInfo)) {
        return true;
    }

    return abilityRecord->IsKeepAliveBundle();
}

void AbilityConnectManager::KeepAbilityAlive(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    auto abilityInfo = abilityRecord->GetAbilityInfo();
    TAG_LOGI(AAFwkTag::EXT, "restart ability, bundleName: %{public}s, abilityName: %{public}s",
        abilityInfo.bundleName.c_str(), abilityInfo.name.c_str());
    auto token = abilityRecord->GetToken();
    if ((IsLauncher(abilityRecord) || abilityRecord->IsSceneBoard()) && token != nullptr) {
        IN_PROCESS_CALL_WITHOUT_RET(DelayedSingleton<AppScheduler>::GetInstance()->ClearProcessByToken(
            token->AsObject()));
        if (abilityRecord->IsSceneBoard() && !AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId_)) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "not current user's SCB, clear user and not restart");
            KillProcessesByUserId();
            return;
        }
    }

    if (userId_ != U0_USER_ID && userId_ != U1_USER_ID &&
        !AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId_)) {
        TAG_LOGI(AAFwkTag::EXT, "Not current user's ability");
        return;
    }

    int32_t restart = OHOS::system::GetIntParameter<int32_t>("persist.sceneboard.restart", 0);
    if (restart <= 0 && abilityRecord->IsSceneBoard() &&
        AmsConfigurationParameter::GetInstance().IsSupportSCBCrashReboot()) {
        static int sceneBoardCrashCount = 0;
        static int64_t tickCount = GetTickCount();
        int64_t tickNow = GetTickCount();
        const int64_t maxTime = 240000; // 240000 4min
        const int maxCount = 4; // 4: crash happened 4 times during 4 mins
        if (tickNow - tickCount > maxTime) {
            sceneBoardCrashCount = 0;
            tickCount = tickNow;
        }
        if ((++sceneBoardCrashCount) >= maxCount) {
            std::string reason = "SceneBoard exits " + std::to_string(sceneBoardCrashCount) +
                "times in " + std::to_string(maxTime) + "ms";
            DoRebootExt("panic", reason.c_str());
        }
    }
    if (DelayedSingleton<AppScheduler>::GetInstance()->IsKilledForUpgradeWeb(abilityInfo.bundleName)) {
        TAG_LOGI(AAFwkTag::EXT, "bundle killed");
        return;
    }
    if (IsNeedToRestart(abilityRecord, abilityInfo.bundleName, abilityInfo.name)) {
        RestartAbility(abilityRecord, userId_);
    }
}

bool AbilityConnectManager::IsNeedToRestart(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const std::string &bundleName, const std::string &abilityName)
{
    if (IsLauncher(abilityRecord) || abilityRecord->IsSceneBoard()) {
        return true;
    }

    if (DelayedSingleton<AppScheduler>::GetInstance()->IsMemorySizeSufficient()) {
        if (DelayedSingleton<AppScheduler>::GetInstance()->IsNoRequireBigMemory() ||
        !AppUtils::GetInstance().IsBigMemoryUnrelatedKeepAliveProc(bundleName)) {
            TAG_LOGD(AAFwkTag::EXT, "restart keep alive ability");
            return true;
        }
    } else if (AppUtils::GetInstance().IsAllowResidentInExtremeMemory(bundleName, abilityName)) {
        TAG_LOGD(AAFwkTag::EXT, "restart keep alive ability");
        return true;
    }
    TAG_LOGD(AAFwkTag::EXT, "not restart keep alive ability");
    return false;
}

void AbilityConnectManager::DisconnectBeforeCleanup()
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::EXT, "called");
    std::lock_guard<ffrt::mutex> guard(serialMutex_);
    auto serviceMap = GetServiceMap();
    for (auto it = serviceMap.begin(); it != serviceMap.end(); ++it) {
        auto abilityRecord = it->second;
        CHECK_POINTER(abilityRecord);
        TAG_LOGI(AAFwkTag::EXT, "ability will died: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
        if (abilityRecord->GetAbilityInfo().type != AbilityType::SERVICE &&
            abilityRecord->GetAbilityInfo().type != AbilityType::EXTENSION) {
            TAG_LOGW(AAFwkTag::EXT, "type not service");
            continue;
        }
        ConnectListType connlist = abilityRecord->GetConnectRecordList();
        for (auto &connectRecord : connlist) {
            CHECK_POINTER_CONTINUE(connectRecord);
            // just notify no same userId
            if (connectRecord->GetCallerUid() / BASE_USER_RANGE == userId_) {
                continue;
            }
            RemoveExtensionDelayDisconnectTask(connectRecord);
            connectRecord->CompleteDisconnect(ERR_OK, false, true);
            abilityRecord->RemoveConnectRecordFromList(connectRecord);
            RemoveConnectionRecordFromMap(connectRecord);
        }
    }
    TAG_LOGI(AAFwkTag::EXT, "cleanup end");
}

void AbilityConnectManager::HandleAbilityDiedTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "called");
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER(abilityRecord);
    TAG_LOGD(AAFwkTag::EXT, "ability died: %{public}s", abilityRecord->GetURI().c_str());
    HandleAbilityDiedTaskInner(abilityRecord);
}

void AbilityConnectManager::HandleAbilityDiedTaskInner(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    TAG_LOGD(AAFwkTag::EXT, "ability died: %{public}s", abilityRecord->GetURI().c_str());
    HandleConnectRecordOnAbilityDied(abilityRecord);
    bool isRemove = HandleExtensionAbilityRemove(abilityRecord);
    HandleAfterServiceRemoved(abilityRecord, isRemove);
}

bool AbilityConnectManager::HandleExtensionAbilityRemove(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    bool isRemove = false;
    if (IsCacheExtensionAbility(abilityRecord) &&
        AbilityCacheManager::GetInstance().FindRecordByToken(abilityRecord->GetToken()) != nullptr) {
        AbilityCacheManager::GetInstance().Remove(abilityRecord);
        MoveToTerminatingMap(abilityRecord);
        RemoveServiceAbility(abilityRecord);
        isRemove = true;
    } else if (GetExtensionByIdFromServiceMap(abilityRecord->GetAbilityRecordId()) != nullptr) {
        MoveToTerminatingMap(abilityRecord);
        RemoveServiceAbility(abilityRecord);
        isRemove = true;
    }
    return isRemove;
}

void AbilityConnectManager::HandleAfterServiceRemoved(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    bool isRemove)
{
    std::string serviceKey = GetServiceKey(abilityRecord);
    if (!isRemove) {
        TAG_LOGE(AAFwkTag::EXT, "%{public}s ability not in service map or cache.", serviceKey.c_str());
        return;
    }

    if (IsAbilityNeedKeepAlive(abilityRecord)) {
        KeepAbilityAlive(abilityRecord);
    } else {
        HandleNotifyAssertFaultDialogDied(abilityRecord);
    }
    TAG_LOGI(AAFwkTag::EXT, "HandleAbilityDiedTask end");
}

void AbilityConnectManager::HandleConnectRecordOnAbilityDied(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    abilityRecord->SetConnRemoteObject(nullptr);
    ConnectListType connlist = abilityRecord->GetConnectRecordList();
    for (auto &connectRecord : connlist) {
        CHECK_POINTER_CONTINUE(connectRecord);
        TAG_LOGW(AAFwkTag::EXT, "record complete disconnect. recordId:%{public}d",
            connectRecord->GetRecordId());
        RemoveExtensionDelayDisconnectTask(connectRecord);
        connectRecord->CompleteDisconnect(ERR_OK, false, true);
        abilityRecord->RemoveConnectRecordFromList(connectRecord);
        RemoveConnectionRecordFromMap(connectRecord);
    }
}

static bool CheckIsNumString(const std::string &numStr)
{
    const std::regex regexJsperf(R"(^\d*)");
    std::match_results<std::string::const_iterator> matchResults;
    if (numStr.empty() || !std::regex_match(numStr, matchResults, regexJsperf)) {
        TAG_LOGE(AAFwkTag::EXT, "error, %{public}s", numStr.c_str());
        return false;
    }
    if (MAX_UINT64_VALUE.length() < numStr.length() ||
        (MAX_UINT64_VALUE.length() == numStr.length() && MAX_UINT64_VALUE.compare(numStr) < 0)) {
        TAG_LOGE(AAFwkTag::EXT, "error, %{public}s", numStr.c_str());
        return false;
    }

    return true;
}

void AbilityConnectManager::HandleNotifyAssertFaultDialogDied(
    const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "called");
    CHECK_POINTER(abilityRecord);
    if (abilityRecord->GetAbilityInfo().name != ABILITY_NAME_ASSERT_FAULT_DIALOG ||
        abilityRecord->GetAbilityInfo().bundleName != BUNDLE_NAME_DIALOG) {
        TAG_LOGE(AAFwkTag::EXT, "fail");
        return;
    }

    auto want = abilityRecord->GetWant();
    auto assertSessionStr = want.GetStringParam(Want::PARAM_ASSERT_FAULT_SESSION_ID);
    if (!CheckIsNumString(assertSessionStr)) {
        TAG_LOGE(AAFwkTag::EXT, "assertSessionStr not number");
        return;
    }

    auto callbackDeathMgr = DelayedSingleton<AbilityRuntime::AssertFaultCallbackDeathMgr>::GetInstance();
    if (callbackDeathMgr == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "null callbackDeathMgr");
        return;
    }
    callbackDeathMgr->CallAssertFaultCallback(std::stoull(assertSessionStr));
}

void AbilityConnectManager::CloseAssertDialog(const std::string &assertSessionId)
{
    TAG_LOGD(AAFwkTag::EXT, "Called");
    std::shared_ptr<BaseExtensionRecord> abilityRecord = nullptr;
    {
        std::lock_guard lock(serviceMapMutex_);
        for (const auto &item : serviceMap_) {
            if (item.second == nullptr) {
                continue;
            }

            auto assertSessionStr = item.second->GetWant().GetStringParam(Want::PARAM_ASSERT_FAULT_SESSION_ID);
            if (assertSessionStr == assertSessionId) {
                abilityRecord = item.second;
                serviceMap_.erase(item.first);
                TAG_LOGD(AAFwkTag::EXT, "ServiceMap remove, size:%{public}zu", serviceMap_.size());
                break;
            }
        }
    }
    if (abilityRecord == nullptr) {
        abilityRecord = AbilityCacheManager::GetInstance().FindRecordBySessionId(assertSessionId);
        AbilityCacheManager::GetInstance().Remove(abilityRecord);
    }
    if (abilityRecord == nullptr) {
        return;
    }
    TAG_LOGD(AAFwkTag::EXT, "Terminate assert fault dialog");
    terminatingExtensionList_.push_back(abilityRecord);
    sptr<IRemoteObject> token = abilityRecord->GetToken();
    if (token != nullptr) {
        std::lock_guard lock(serialMutex_);
        TerminateAbilityLocked(token);
    }
}

void AbilityConnectManager::RestartAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    int32_t currentUserId)
{
    TAG_LOGI(AAFwkTag::EXT, "restart ability: %{public}s/%{public}s",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());
    AbilityRequest requestInfo;
    requestInfo.want = abilityRecord->GetWant();
    requestInfo.abilityInfo = abilityRecord->GetAbilityInfo();
    requestInfo.appInfo = abilityRecord->GetApplicationInfo();
    requestInfo.restartTime = abilityRecord->GetRestartTime();
    requestInfo.restart = true;
    requestInfo.uid = abilityRecord->GetUid();
    abilityRecord->SetRestarting(true);
    ResidentAbilityInfoGuard residentAbilityInfoGuard;
    if (abilityRecord->IsKeepAliveBundle()) {
        residentAbilityInfoGuard.SetResidentAbilityInfo(requestInfo.abilityInfo.bundleName,
            requestInfo.abilityInfo.name, userId_);
    }

    if (AppUtils::GetInstance().IsLauncherAbility(abilityRecord->GetAbilityInfo().name)) {
        if (currentUserId != userId_) {
            TAG_LOGW(AAFwkTag::EXT, "delay restart root launcher until switch user");
            return;
        }
        if (abilityRecord->IsSceneBoard()) {
            requestInfo.want.SetParam("ohos.app.recovery", true);
            uint64_t displayId = 0;
            if (AbilityRuntime::UserController::GetInstance().GetDisplayIdByForegroundUserId(userId_, displayId)) {
                requestInfo.want.SetParam(Want::PARAM_RESV_DISPLAY_ID, static_cast<int32_t>(displayId));
            }
            DelayedSingleton<AbilityManagerService>::GetInstance()->EnableListForSCBRecovery(userId_);
        }
        requestInfo.restartCount = abilityRecord->GetRestartCount();
        TAG_LOGD(AAFwkTag::EXT, "restart root launcher, number:%{public}d", requestInfo.restartCount);
        StartAbilityLocked(requestInfo);
        return;
    }

    requestInfo.want.SetParam(WANT_PARAMS_APP_RESTART_FLAG, true);

    // restart other resident ability
    if (abilityRecord->CanRestartResident()) {
        requestInfo.restartCount = abilityRecord->GetRestartCount();
        requestInfo.restartTime = AbilityUtil::SystemTimeMillis();
        StartAbilityLocked(requestInfo);
    } else {
        auto findRestartResidentTask = [requestInfo](const AbilityRequest &abilityRequest) {
            return (requestInfo.want.GetElement().GetBundleName() == abilityRequest.want.GetElement().GetBundleName() &&
                requestInfo.want.GetElement().GetModuleName() == abilityRequest.want.GetElement().GetModuleName() &&
                requestInfo.want.GetElement().GetAbilityName() == abilityRequest.want.GetElement().GetAbilityName());
        };
        auto findIter = find_if(restartResidentTaskList_.begin(), restartResidentTaskList_.end(),
            findRestartResidentTask);
        if (findIter != restartResidentTaskList_.end()) {
            TAG_LOGW(AAFwkTag::EXT, "restart task registered");
            return;
        }
        restartResidentTaskList_.emplace_back(requestInfo);
        PostRestartResidentTask(requestInfo);
    }
}

std::string AbilityConnectManager::GetServiceKey(const std::shared_ptr<BaseExtensionRecord> &service)
{
    std::string serviceKey = service->GetURI();
    if (FRS_BUNDLE_NAME == service->GetAbilityInfo().bundleName) {
        serviceKey = serviceKey + std::to_string(service->GetWant().GetIntParam(FRS_APP_INDEX, 0));
    }
    return serviceKey;
}

void AbilityConnectManager::DumpState(ServiceMapType &serviceMapBack, std::vector<std::string> &info, bool isClient,
    const std::string &args)
{
    TAG_LOGI(AAFwkTag::EXT, "args:%{public}s", args.c_str());
    auto cacheList = AbilityCacheManager::GetInstance().GetAbilityList();
    if (!args.empty()) {
        auto it = std::find_if(serviceMapBack.begin(), serviceMapBack.end(), [&args](const auto &service) {
            return service.first.compare(args) == 0;
        });
        if (it != serviceMapBack.end()) {
            info.emplace_back("uri [ " + it->first + " ]");
            if (it->second != nullptr) {
                it->second->DumpService(info, isClient);
            }
        } else {
            info.emplace_back(args + ": Nothing to dump from serviceMap.");
        }

        std::string serviceKey;
        auto iter = std::find_if(cacheList.begin(), cacheList.end(), [&args, &serviceKey](const auto &service) {
            serviceKey = GetServiceKey(service);
            return serviceKey.compare(args) == 0;
        });
        if (iter != cacheList.end()) {
            info.emplace_back("uri [ " + serviceKey + " ]");
            if (*iter != nullptr) {
                (*iter)->DumpService(info, isClient);
            }
        } else {
            info.emplace_back(args + ": Nothing to dump from lru cache.");
        }
    } else {
        info.emplace_back("  ExtensionRecords:");
        for (auto &&service : serviceMapBack) {
            info.emplace_back("    uri [" + service.first + "]");
            if (service.second != nullptr) {
                service.second->DumpService(info, isClient);
            }
        }
        for (auto &&service : cacheList) {
            std::string serviceKey = GetServiceKey(service);
            info.emplace_back("    uri [" + serviceKey + "]");
            if (service != nullptr) {
                service->DumpService(info, isClient);
            }
        }
    }
}

void AbilityConnectManager::DumpStateByUri(ServiceMapType &serviceMapBack, std::vector<std::string> &info,
    bool isClient, const std::string &args, std::vector<std::string> &params)
{
    TAG_LOGI(AAFwkTag::EXT, "args:%{public}s, params size: %{public}zu", args.c_str(), params.size());
    std::shared_ptr<BaseExtensionRecord> extensionAbilityRecord = nullptr;
    auto it = std::find_if(serviceMapBack.begin(), serviceMapBack.end(), [&args](const auto &service) {
        return service.first.compare(args) == 0;
    });
    if (it != serviceMapBack.end()) {
        info.emplace_back("uri [ " + it->first + " ]");
        extensionAbilityRecord = it->second;
    } else {
        info.emplace_back(args + ": Nothing to dump from serviceMap.");
    }

    if (extensionAbilityRecord != nullptr) {
        extensionAbilityRecord->DumpService(info, params, isClient);
        return;
    }
    extensionAbilityRecord = AbilityCacheManager::GetInstance().FindRecordByServiceKey(args);
    if (extensionAbilityRecord != nullptr) {
        info.emplace_back("uri [ " + args + " ]");
        extensionAbilityRecord->DumpService(info, params, isClient);
    } else {
        info.emplace_back(args + ": Nothing to dump from lru cache.");
    }
}

void AbilityConnectManager::GetExtensionRunningInfos(ServiceMapType &serviceMapBack, int upperLimit,
    std::vector<ExtensionRunningInfo> &info, const int32_t userId, bool isPerm)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto queryInfo = [&](ServiceMapType::reference service) {
        if (static_cast<int>(info.size()) >= upperLimit) {
            return;
        }
        auto abilityRecord = service.second;
        CHECK_POINTER(abilityRecord);

        if (isPerm) {
            GetExtensionRunningInfo(abilityRecord, userId, info);
        } else {
            auto callingTokenId = IPCSkeleton::GetCallingTokenID();
            auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
            if (callingTokenId == tokenID) {
                GetExtensionRunningInfo(abilityRecord, userId, info);
            }
        }
    };
    std::for_each(serviceMapBack.begin(), serviceMapBack.end(), queryInfo);

    auto cacheAbilityList = AbilityCacheManager::GetInstance().GetAbilityList();
    auto queryInfoForCache = [&](std::shared_ptr<BaseExtensionRecord> &service) {
        if (static_cast<int>(info.size()) >= upperLimit) {
            return;
        }
        CHECK_POINTER(service);

        if (isPerm) {
            GetExtensionRunningInfo(service, userId, info);
        } else {
            auto callingTokenId = IPCSkeleton::GetCallingTokenID();
            auto tokenID = service->GetApplicationInfo().accessTokenId;
            if (callingTokenId == tokenID) {
                GetExtensionRunningInfo(service, userId, info);
            }
        }
    };
    std::for_each(cacheAbilityList.begin(), cacheAbilityList.end(), queryInfoForCache);
}

void AbilityConnectManager::GetExtensionRunningInfo(std::shared_ptr<BaseExtensionRecord> &abilityRecord,
    const int32_t userId, std::vector<ExtensionRunningInfo> &info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    ExtensionRunningInfo extensionInfo;
    AppExecFwk::RunningProcessInfo processInfo;
    CHECK_POINTER(abilityRecord);
    extensionInfo.extension = abilityRecord->GetElementName();
    extensionInfo.type = abilityRecord->GetAbilityInfo().extensionAbilityType;
    DelayedSingleton<AppScheduler>::GetInstance()->
        GetRunningProcessInfoByToken(abilityRecord->GetToken(), processInfo);
    extensionInfo.pid = processInfo.pid_;
    extensionInfo.uid = processInfo.uid_;
    extensionInfo.processName = processInfo.processName_;
    extensionInfo.startTime = abilityRecord->GetStartTime();
    ConnectListType connectRecordList = abilityRecord->GetConnectRecordList();
    for (auto &connectRecord : connectRecordList) {
        if (connectRecord == nullptr) {
            TAG_LOGD(AAFwkTag::EXT, "connectRecord is nullptr.");
            continue;
        }
        auto callerAbilityRecord = Token::GetAbilityRecordByToken(connectRecord->GetToken());
        if (callerAbilityRecord == nullptr) {
            TAG_LOGD(AAFwkTag::EXT, "callerAbilityRecord is nullptr.");
            continue;
        }
        std::string package = callerAbilityRecord->GetAbilityInfo().bundleName;
        extensionInfo.clientPackage.emplace_back(package);
    }
    info.emplace_back(extensionInfo);
}

void AbilityConnectManager::PauseExtensions()
{
    TAG_LOGD(AAFwkTag::EXT, "begin.");
    std::vector<sptr<IRemoteObject>> needTerminatedTokens;
    {
        std::lock_guard lock(serviceMapMutex_);
        for (auto it = serviceMap_.begin(); it != serviceMap_.end();) {
            auto targetExtension = it->second;
            if (targetExtension != nullptr && targetExtension->GetAbilityInfo().type == AbilityType::EXTENSION &&
                (IsLauncher(targetExtension) || targetExtension->IsSceneBoard() ||
                (targetExtension->GetKeepAlive() && userId_ != U0_USER_ID))) {
                terminatingExtensionList_.push_back(it->second);
                it = serviceMap_.erase(it);
                TAG_LOGI(AAFwkTag::EXT, "terminate ability:%{public}s, serviceMap size:%{public}zu",
                    targetExtension->GetAbilityInfo().name.c_str(), serviceMap_.size());
                needTerminatedTokens.push_back(targetExtension->GetToken());
            } else {
                ++it;
            }
        }
    }

    for (const auto &token : needTerminatedTokens) {
        std::lock_guard lock(serialMutex_);
        TerminateAbilityLocked(token);
    }
}

void AbilityConnectManager::RemoveLauncherDeathRecipient()
{
    TAG_LOGI(AAFwkTag::EXT, "call");
    {
        std::lock_guard lock(serviceMapMutex_);
        for (auto it = serviceMap_.begin(); it != serviceMap_.end(); ++it) {
            auto targetExtension = it->second;
            if (targetExtension != nullptr && targetExtension->GetAbilityInfo().type == AbilityType::EXTENSION &&
                (IsLauncher(targetExtension) || targetExtension->IsSceneBoard())) {
                targetExtension->RemoveAbilityDeathRecipient();
                return;
            }
        }
    }
    AbilityCacheManager::GetInstance().RemoveLauncherDeathRecipient();
}

bool AbilityConnectManager::IsLauncher(std::shared_ptr<BaseExtensionRecord> serviceExtension) const
{
    if (serviceExtension == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "param null");
        return false;
    }
    return serviceExtension->GetAbilityInfo().name == AbilityConfig::LAUNCHER_ABILITY_NAME &&
        serviceExtension->GetAbilityInfo().bundleName == AbilityConfig::LAUNCHER_BUNDLE_NAME;
}

void AbilityConnectManager::KillProcessesByUserId() const
{
    auto appScheduler = DelayedSingleton<AppScheduler>::GetInstance();
    if (appScheduler == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "appScheduler null");
        return;
    }
    IN_PROCESS_CALL_WITHOUT_RET(appScheduler->KillProcessesByUserId(userId_));
}

void AbilityConnectManager::CompleteForeground(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    std::lock_guard guard(serialMutex_);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return;
    }
    if (abilityRecord->GetAbilityState() != AbilityState::FOREGROUNDING) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability state: %{public}d, not complete foreground",
            abilityRecord->GetAbilityState());
        return;
    }
    abilityRecord->SetAbilityState(AbilityState::FOREGROUND);
    CompleteForegroundInner(abilityRecord);
}

void AbilityConnectManager::CompleteForegroundInner(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    CompleteStartServiceReq(abilityRecord->GetURI());
}

void AbilityConnectManager::HandleForegroundTimeoutTask(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    std::lock_guard guard(serialMutex_);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return;
    }
    HandleForegroundTimeoutTaskInner(abilityRecord);
}

void AbilityConnectManager::HandleForegroundTimeoutTaskInner(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    abilityRecord->SetAbilityState(AbilityState::BACKGROUND);
    abilityRecord->DoBackgroundAbilityWindowDelayed(false);
    CompleteStartServiceReq(abilityRecord->GetURI());
}

void AbilityConnectManager::CompleteBackground(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    std::lock_guard lock(serialMutex_);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return;
    }
    if (abilityRecord->GetAbilityState() != AbilityState::BACKGROUNDING) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability state: %{public}d, not complete background.",
            abilityRecord->GetAbilityState());
        return;
    }
    abilityRecord->SetAbilityState(AbilityState::BACKGROUND);
    // send application state to AppMS.
    // notify AppMS to update application state.
    DelayedSingleton<AppScheduler>::GetInstance()->MoveToBackground(abilityRecord->GetToken());
    CompleteStartServiceReq(abilityRecord->GetURI());
    // Abilities ahead of the one started were put in terminate list, we need to terminate them.
    TerminateAbilityLocked(abilityRecord->GetToken());
}

void AbilityConnectManager::PrintTimeOutLog(const std::shared_ptr<BaseExtensionRecord> &ability, uint32_t msgId,
    bool isHalf)
{
    CHECK_POINTER(ability);
    AppExecFwk::RunningProcessInfo processInfo = {};
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByToken(ability->GetToken(), processInfo);
    if (processInfo.pid_ == 0) {
        TAG_LOGE(AAFwkTag::EXT, "ability %{public}s/%{public}s pid invalid",
            ability->GetElementName().GetBundleName().c_str(),
            ability->GetElementName().GetAbilityName().c_str());
        return;
    }
    int typeId = AppExecFwk::AppfreezeManager::TypeAttribute::NORMAL_TIMEOUT;
    std::string msgContent = "ability:" + ability->GetAbilityInfo().name + " ";
    if (!GetTimeoutMsgContent(msgId, msgContent, typeId)) {
        return;
    }
    if (ability->GetWant().GetBoolParam(IS_PRELOAD_UIEXTENSION_ABILITY, false)) {
        msgContent += "\nabilityLoadType: PreloadUIExtension\n";
    }

    std::string eventName = isHalf ?
        AppExecFwk::AppFreezeType::LIFECYCLE_HALF_TIMEOUT : AppExecFwk::AppFreezeType::LIFECYCLE_TIMEOUT;
    AppExecFwk::AppfreezeManager::ParamInfo info = {
        .typeId = typeId,
        .pid = processInfo.pid_,
        .eventName = eventName,
        .bundleName = ability->GetAbilityInfo().bundleName,
        .msg = msgContent
    };
    if (!UIExtensionWrapper::IsUIExtension(ability->GetAbilityInfo().extensionAbilityType) &&
        !ability->IsSceneBoard()) {
        info.needKillProcess = false;
        info.eventName = isHalf ? AppExecFwk::AppFreezeType::LIFECYCLE_HALF_TIMEOUT_WARNING :
            AppExecFwk::AppFreezeType::LIFECYCLE_TIMEOUT_WARNING;
    }
    TAG_LOGW(AAFwkTag::EXT,
        "%{public}s: uid: %{public}d, pid: %{public}d, bundleName: %{public}s, abilityName: %{public}s,"
        "msg: %{public}s", info.eventName.c_str(), processInfo.uid_, processInfo.pid_,
        ability->GetAbilityInfo().bundleName.c_str(), ability->GetAbilityInfo().name.c_str(), msgContent.c_str());
    FreezeUtil::TimeoutState state = TimeoutStateUtils::MsgId2FreezeTimeOutState(msgId);
    FreezeUtil::LifecycleFlow flow;
    if (state != FreezeUtil::TimeoutState::UNKNOWN) {
        if (ability->GetToken() != nullptr) {
            flow.token = ability->GetToken()->AsObject();
            flow.state = state;
        }
        info.msg = msgContent + "\nserver actions for ability:\n" +
            FreezeUtil::GetInstance().GetLifecycleEvent(flow.token)
            + "\nserver actions for app:\n" + FreezeUtil::GetInstance().GetAppLifecycleEvent(processInfo.pid_);
        if (!isHalf) {
            FreezeUtil::GetInstance().DeleteLifecycleEvent(flow.token);
            FreezeUtil::GetInstance().DeleteAppLifecycleEvent(processInfo.pid_);
        }
    } else {
        info.msg = msgContent;
    }
    AppExecFwk::AppfreezeManager::GetInstance()->LifecycleTimeoutHandle(info, flow);
}

bool AbilityConnectManager::GetTimeoutMsgContent(uint32_t msgId, std::string &msgContent, int &typeId)
{
    switch (msgId) {
        case AbilityManagerService::LOAD_TIMEOUT_MSG:
            msgContent += "load timeout";
            typeId = AppExecFwk::AppfreezeManager::TypeAttribute::CRITICAL_TIMEOUT;
            return true;
        case AbilityManagerService::ACTIVE_TIMEOUT_MSG:
            msgContent += "active timeout";
            return true;
        case AbilityManagerService::INACTIVE_TIMEOUT_MSG:
            msgContent += "inactive timeout";
            return true;
        case AbilityManagerService::FOREGROUND_TIMEOUT_MSG:
            msgContent += "foreground timeout";
            typeId = AppExecFwk::AppfreezeManager::TypeAttribute::CRITICAL_TIMEOUT;
            return true;
        case AbilityManagerService::BACKGROUND_TIMEOUT_MSG:
            msgContent += "background timeout";
            return true;
        case AbilityManagerService::TERMINATE_TIMEOUT_MSG:
            msgContent += "terminate timeout";
            return true;
        case AbilityManagerService::CONNECT_TIMEOUT_MSG:
            msgContent += "connect timeout";
            typeId = AppExecFwk::AppfreezeManager::TypeAttribute::CRITICAL_TIMEOUT;
            return true;
        default:
            return false;
    }
}

void AbilityConnectManager::MoveToTerminatingMap(const std::shared_ptr<BaseExtensionRecord>& abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    auto& abilityInfo = abilityRecord->GetAbilityInfo();
    std::lock_guard lock(serviceMapMutex_);
    terminatingExtensionList_.push_back(abilityRecord);
    std::string serviceKey = abilityRecord->GetURI();
    if (FRS_BUNDLE_NAME == abilityInfo.bundleName) {
        AppExecFwk::ElementName element(abilityInfo.deviceId, abilityInfo.bundleName, abilityInfo.name,
            abilityInfo.moduleName);
        serviceKey = element.GetURI() + std::to_string(abilityRecord->GetWant().GetIntParam(FRS_APP_INDEX, 0));
    }
    if (serviceMap_.erase(serviceKey) == 0) {
        TAG_LOGW(AAFwkTag::EXT, "Unknown: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
    }
    TAG_LOGD(AAFwkTag::EXT, "ServiceMap remove, size:%{public}zu", serviceMap_.size());
    AbilityCacheManager::GetInstance().Remove(abilityRecord);
    if (IsSpecialAbility(abilityRecord->GetAbilityInfo())) {
        TAG_LOGI(AAFwkTag::EXT, "moving ability: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
    }
}

bool AbilityConnectManager::IsWindowExtensionFocused(uint32_t extensionTokenId, const sptr<IRemoteObject>& focusToken)
{
    std::lock_guard guard(windowExtensionMapMutex_);
    for (auto& item: windowExtensionMap_) {
        uint32_t windowExtTokenId = item.second.first;
        auto sessionInfo = item.second.second;
        if (windowExtTokenId == extensionTokenId && sessionInfo && sessionInfo->callerToken == focusToken) {
            return true;
        }
    }
    return false;
}

void AbilityConnectManager::HandleProcessFrozen(const std::vector<int32_t> &pidList, int32_t uid)
{
    TAG_LOGD(AAFwkTag::EXT, "uid:%{public}d", uid);
    std::unordered_set<int32_t> pidSet(pidList.begin(), pidList.end());
    std::lock_guard lock(serviceMapMutex_);
    auto weakThis = weak_from_this();
    for (auto [key, abilityRecord] : serviceMap_) {
        if (abilityRecord && abilityRecord->GetUid() == uid &&
            abilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE &&
            pidSet.count(abilityRecord->GetPid()) > 0 &&
            abilityRecord->GetAbilityInfo().bundleName != FROZEN_WHITE_DIALOG &&
            abilityRecord->IsConnectListEmpty() &&
            !abilityRecord->GetKeepAlive()) {
            ffrt::submit([weakThis, record = abilityRecord]() {
                    auto connectManager = weakThis.lock();
                    if (record && connectManager) {
                        TAG_LOGI(AAFwkTag::EXT, "terminateRecord:%{public}s",
                            record->GetAbilityInfo().bundleName.c_str());
                        connectManager->TerminateRecord(record);
                    } else {
                        TAG_LOGE(AAFwkTag::EXT, "connectManager null");
                    }
                }, ffrt::task_attr().timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));
        }
    }
}

void AbilityConnectManager::PostExtensionDelayDisconnectTask(const std::shared_ptr<ConnectionRecord> &connectRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "call");
    CHECK_POINTER(taskHandler_);
    CHECK_POINTER(connectRecord);
    int32_t recordId = connectRecord->GetRecordId();
    std::string taskName = std::string("DelayDisconnectTask_") + std::to_string(recordId);

    auto abilityRecord = connectRecord->GetAbilityRecord();
    CHECK_POINTER(abilityRecord);
    auto typeName = abilityRecord->GetAbilityInfo().extensionTypeName;
    int32_t delayTime = DelayedSingleton<ExtensionConfig>::GetInstance()->GetExtensionAutoDisconnectTime(typeName);
    if (delayTime == AUTO_DISCONNECT_INFINITY) {
        TAG_LOGD(AAFwkTag::EXT, "This extension needn't auto disconnect.");
        return;
    }

    auto task = [connectRecord, self = weak_from_this()]() {
        auto selfObj = self.lock();
        if (selfObj == nullptr) {
            TAG_LOGW(AAFwkTag::EXT, "mgr invalid");
            return;
        }
        TAG_LOGW(AAFwkTag::EXT, "auto disconnect the Extension's connection");
        selfObj->HandleExtensionDisconnectTask(connectRecord);
    };
    taskHandler_->SubmitTask(task, taskName, delayTime);
}

void AbilityConnectManager::RemoveExtensionDelayDisconnectTask(const std::shared_ptr<ConnectionRecord> &connectRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "call");
    CHECK_POINTER(taskHandler_);
    CHECK_POINTER(connectRecord);
    int32_t recordId = connectRecord->GetRecordId();
    std::string taskName = std::string("DelayDisconnectTask_") + std::to_string(recordId);
    taskHandler_->CancelTask(taskName);
}

void AbilityConnectManager::HandleExtensionDisconnectTask(const std::shared_ptr<ConnectionRecord> &connectRecord)
{
    TAG_LOGD(AAFwkTag::EXT, "call");
    std::lock_guard guard(serialMutex_);
    CHECK_POINTER(connectRecord);
    int result = connectRecord->DisconnectAbility();
    if (result != ERR_OK) {
        TAG_LOGW(AAFwkTag::EXT, "error, ret: %{public}d", result);
    }
    if (connectRecord->GetConnectState() == ConnectionState::DISCONNECTED) {
        connectRecord->CompleteDisconnect(ERR_OK, false);
        RemoveConnectionRecordFromMap(connectRecord);
    }
}

bool AbilityConnectManager::IsCacheExtensionAbilityByInfo(const AppExecFwk::AbilityInfo &abilityInfo)
{
    return (CacheExtensionUtils::IsCacheExtensionType(abilityInfo.extensionAbilityType) ||
        AppUtils::GetInstance().IsCacheExtensionAbilityByList(abilityInfo.bundleName,
        abilityInfo.name));
}

bool AbilityConnectManager::IsCacheExtensionAbility(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    CHECK_POINTER_AND_RETURN(abilityRecord, false);
    return IsCacheExtensionAbilityByInfo(abilityRecord->GetAbilityInfo());
}

void AbilityConnectManager::SignRestartAppFlag(int32_t uid, const std::string &instanceKey)
{
    {
        std::lock_guard lock(serviceMapMutex_);
        for (auto &[key, abilityRecord] : serviceMap_) {
            if (abilityRecord == nullptr || abilityRecord->GetUid() != uid ||
                abilityRecord->GetInstanceKey() != instanceKey) {
                continue;
            }
            abilityRecord->SetRestartAppFlag(true);
        }
    }
    AbilityCacheManager::GetInstance().SignRestartAppFlag(uid, instanceKey);
}

void AbilityConnectManager::SignRestartProcess(int32_t pid)
{
    {
        std::lock_guard lock(serviceMapMutex_);
        for (auto &[key, abilityRecord] : serviceMap_) {
            if (abilityRecord == nullptr || abilityRecord->GetPid() != pid) {
                continue;
            }
            abilityRecord->SetRestartAppFlag(true);
        }
    }
    AbilityCacheManager::GetInstance().SignRestartProcess(pid);
}

bool AbilityConnectManager::AddToServiceMap(const std::string &key, std::shared_ptr<BaseExtensionRecord> abilityRecord)
{
    std::lock_guard lock(serviceMapMutex_);
    if (abilityRecord == nullptr) {
        return false;
    }
    auto insert = serviceMap_.emplace(key, abilityRecord);
    TAG_LOGD(AAFwkTag::EXT, "ServiceMap add, size:%{public}zu", serviceMap_.size());
    if (!insert.second) {
        TAG_LOGW(AAFwkTag::EXT, "record exist: %{public}s", key.c_str());
    }
    return insert.second;
}

AbilityConnectManager::ServiceMapType AbilityConnectManager::GetServiceMap()
{
    std::lock_guard lock(serviceMapMutex_);
    return serviceMap_;
}

void AbilityConnectManager::AddConnectObjectToMap(sptr<IRemoteObject> connectObject,
    const ConnectListType &connectRecordList, bool updateOnly)
{
    if (!updateOnly) {
        AddConnectDeathRecipient(connectObject);
    }
    std::lock_guard guard(connectMapMutex_);
    connectMap_[connectObject] = connectRecordList;
}

EventInfo AbilityConnectManager::BuildEventInfo(const std::shared_ptr<BaseExtensionRecord> &abilityRecord)
{
    EventInfo eventInfo;
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::EXT, "abilityRecord null");
        return eventInfo;
    }
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByToken(abilityRecord->GetToken(), processInfo);
    eventInfo.pid = processInfo.pid_;
    eventInfo.processName = processInfo.processName_;
    eventInfo.time = std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count();
    auto callerPid = abilityRecord->GetWant().GetIntParam(Want::PARAM_RESV_CALLER_PID, -1);
    eventInfo.callerPid = callerPid == -1 ? IPCSkeleton::GetCallingPid() : callerPid;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(eventInfo.callerPid, processInfo);
    eventInfo.callerPid = processInfo.pid_;
    eventInfo.callerProcessName = processInfo.processName_;
    if (!abilityRecord->IsCreateByConnect()) {
        auto abilityInfo = abilityRecord->GetAbilityInfo();
        eventInfo.extensionType = static_cast<int32_t>(abilityInfo.extensionAbilityType);
        eventInfo.userId = userId_;
        eventInfo.bundleName = abilityInfo.bundleName;
        eventInfo.moduleName = abilityInfo.moduleName;
        eventInfo.abilityName = abilityInfo.name;
    }
    return eventInfo;
}

std::string AbilityConnectManager::GenerateBundleName(const AbilityRequest &abilityRequest) const
{
    auto bundleName = abilityRequest.abilityInfo.bundleName;
    if (MultiInstanceUtils::IsMultiInstanceApp(abilityRequest.appInfo)) {
        bundleName = bundleName + '-' + MultiInstanceUtils::GetValidExtensionInstanceKey(abilityRequest);
        return bundleName;
    }
    if (AbilityRuntime::StartupUtil::IsSupportAppClone(abilityRequest.abilityInfo.extensionAbilityType)) {
        auto appCloneIndex = abilityRequest.want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, 0);
        if (appCloneIndex > 0) {
            bundleName = std::to_string(appCloneIndex) + bundleName;
        }
    }
    return bundleName;
}

int32_t AbilityConnectManager::ReportXiaoYiToRSSIfNeeded(const AppExecFwk::AbilityInfo &abilityInfo)
{
    if (abilityInfo.type != AppExecFwk::AbilityType::EXTENSION ||
        abilityInfo.extensionAbilityType != AppExecFwk::ExtensionAbilityType::SERVICE ||
        abilityInfo.bundleName != XIAOYI_BUNDLE_NAME) {
        return ERR_OK;
    }
    TAG_LOGI(AAFwkTag::EXT,
        "bundleName is extension, abilityName:%{public}s",
        abilityInfo.name.c_str());
    auto ret = ReportAbilityStartInfoToRSS(abilityInfo);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::EXT, "fail, ret:%{public}d", ret);
        return ret;
    }
    return ERR_OK;
}

int32_t AbilityConnectManager::ReportAbilityStartInfoToRSS(const AppExecFwk::AbilityInfo &abilityInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::vector<AppExecFwk::RunningProcessInfo> runningProcessInfos;
    auto ret = IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->GetProcessRunningInfos(
        runningProcessInfos));
    if (ret != ERR_OK) {
        return ret;
    }
    bool isColdStart = true;
    int32_t pid = 0;
    int32_t preloadMode = -1;
    for (auto const &info : runningProcessInfos) {
        if (info.uid_ == abilityInfo.applicationInfo.uid) {
            isColdStart = false;
            pid = info.pid_;
            preloadMode = static_cast<int32_t>(info.preloadMode_);
            break;
        }
    }
    TAG_LOGI(AAFwkTag::EXT, "ReportAbilityStartInfoToRSS, abilityName:%{public}s", abilityInfo.name.c_str());
    ResSchedUtil::GetInstance().ReportAbilityStartInfoToRSS(abilityInfo, pid, isColdStart, false, preloadMode);
    return ERR_OK;
}

void AbilityConnectManager::UninstallApp(const std::string &bundleName, int32_t uid)
{
    std::lock_guard lock(serviceMapMutex_);
    for (const auto &[key, abilityRecord]: serviceMap_) {
        if (abilityRecord && abilityRecord->GetAbilityInfo().bundleName == bundleName &&
            abilityRecord->GetUid() == uid) {
            abilityRecord->SetKeepAliveBundle(false);
        }
    }
}

int32_t AbilityConnectManager::UpdateKeepAliveEnableState(const std::string &bundleName,
    const std::string &moduleName, const std::string &mainElement, bool updateEnable)
{
    std::lock_guard lock(serviceMapMutex_);
    for (const auto &[key, abilityRecord]: serviceMap_) {
        CHECK_POINTER_AND_RETURN(abilityRecord, ERR_NULL_OBJECT);
        if (abilityRecord->GetAbilityInfo().bundleName == bundleName &&
            abilityRecord->GetAbilityInfo().name == mainElement &&
            abilityRecord->GetAbilityInfo().moduleName == moduleName) {
            TAG_LOGI(AAFwkTag::EXT,
                "update keepAlive,bundle:%{public}s,module:%{public}s,ability:%{public}s,enable:%{public}d",
                bundleName.c_str(), moduleName.c_str(), mainElement.c_str(), updateEnable);
            abilityRecord->SetKeepAliveBundle(updateEnable);
            return ERR_OK;
        }
    }
    return ERR_OK;
}

std::shared_ptr<BaseExtensionRecord> AbilityConnectManager::GetUIExtensionBySessionFromServiceMap(
    const sptr<SessionInfo> &sessionInfo)
{
    int32_t persistentId = sessionInfo->persistentId;
    auto IsMatch = [persistentId](auto service) {
        if (!service.second) {
            return false;
        }
        auto sessionInfoPtr = service.second->GetSessionInfo();
        if (!sessionInfoPtr) {
            return false;
        }
        int32_t srcPersistentId = sessionInfoPtr->persistentId;
        return srcPersistentId == persistentId;
    };
    std::lock_guard lock(serviceMapMutex_);
    auto serviceRecord = std::find_if(serviceMap_.begin(), serviceMap_.end(), IsMatch);
    if (serviceRecord != serviceMap_.end()) {
        TAG_LOGW(AAFwkTag::UI_EXT, "abilityRecord still exists");
        return serviceRecord->second;
    }
    return nullptr;
}

bool AbilityConnectManager::IsSpecialAbility(const AppExecFwk::AbilityInfo &abilityInfo)
{
    std::vector<std::pair<std::string, std::string>> trustAbilities{
        { AbilityConfig::SCENEBOARD_BUNDLE_NAME, AbilityConfig::SCENEBOARD_ABILITY_NAME },
        { AbilityConfig::SYSTEM_UI_BUNDLE_NAME, AbilityConfig::SYSTEM_UI_ABILITY_NAME },
        { AbilityConfig::LAUNCHER_BUNDLE_NAME, AbilityConfig::LAUNCHER_ABILITY_NAME }
    };
    for (const auto &pair : trustAbilities) {
        if (pair.first == abilityInfo.bundleName && pair.second == abilityInfo.name) {
            return true;
        }
    }
    return false;
}

void AbilityConnectManager::GetOrCreateServiceRecord(const AbilityRequest &abilityRequest,
    const bool isCreatedByConnect, std::shared_ptr<BaseExtensionRecord> &targetService, bool &isLoadedAbility)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    // lifecycle is not complete when window extension is reused
    bool noReuse = UIExtensionWrapper::IsWindowExtension(abilityRequest.abilityInfo.extensionAbilityType);
    AppExecFwk::ElementName element(abilityRequest.abilityInfo.deviceId, GenerateBundleName(abilityRequest),
        abilityRequest.abilityInfo.name, abilityRequest.abilityInfo.moduleName);
    std::string serviceKey = element.GetURI();
    if (FRS_BUNDLE_NAME == abilityRequest.abilityInfo.bundleName) {
        serviceKey = element.GetURI() + std::to_string(abilityRequest.want.GetIntParam(FRS_APP_INDEX, 0));
    }
    {
        std::lock_guard lock(serviceMapMutex_);
        auto serviceMapIter = serviceMap_.find(serviceKey);
        targetService = serviceMapIter == serviceMap_.end() ? nullptr : serviceMapIter->second;
    }
    if (targetService == nullptr &&
        IsCacheExtensionAbilityByInfo(abilityRequest.abilityInfo)) {
        targetService = AbilityCacheManager::GetInstance().Get(abilityRequest);
        if (targetService != nullptr) {
            AddToServiceMap(serviceKey, targetService);
        }
    }
    if (noReuse && targetService) {
        if (IsSpecialAbility(abilityRequest.abilityInfo)) {
            TAG_LOGI(AAFwkTag::EXT, "removing ability: %{public}s/%{public}s",
                element.GetBundleName().c_str(),
                element.GetAbilityName().c_str());
        }
        RemoveServiceFromMapSafe(serviceKey);
    }
    isLoadedAbility = true;
    if (noReuse || targetService == nullptr) {
        targetService = BaseExtensionRecord::CreateBaseExtensionRecord(abilityRequest);
        CHECK_POINTER(targetService);
        targetService->SetOwnerMissionUserId(userId_);
        if (isCreatedByConnect) {
            targetService->SetCreateByConnectMode();
        }
        SetServiceAfterNewCreate(abilityRequest, *targetService);
        AddToServiceMap(serviceKey, targetService);
        isLoadedAbility = false;
    }
    TAG_LOGD(AAFwkTag::EXT, "service map add, serviceKey: %{public}s", serviceKey.c_str());
}

void AbilityConnectManager::SetServiceAfterNewCreate(const AbilityRequest &abilityRequest,
    BaseExtensionRecord &targetService)
{
    if (abilityRequest.abilityInfo.name == AbilityConfig::LAUNCHER_ABILITY_NAME) {
        targetService.SetLauncherRoot();
        if (abilityRequest.restart) {
            targetService.SetRestartTime(abilityRequest.restartTime);
            targetService.SetRestartCount(abilityRequest.restartCount);
        }
    } else if (IsAbilityNeedKeepAlive(BaseExtensionRecord::TransferToExtensionRecordBase(
        targetService.shared_from_this())) && abilityRequest.restart) {
        targetService.SetRestartTime(abilityRequest.restartTime);
        targetService.SetRestartCount(abilityRequest.restartCount);
    }
    if (MultiInstanceUtils::IsMultiInstanceApp(abilityRequest.appInfo)) {
        targetService.SetInstanceKey(MultiInstanceUtils::GetValidExtensionInstanceKey(abilityRequest));
    }
    if (targetService.IsSceneBoard()) {
        TAG_LOGI(AAFwkTag::EXT, "create sceneboard");
        sceneBoardTokenId_ = abilityRequest.appInfo.accessTokenId;
    }
}
}  // namespace AAFwk
}  // namespace OHOS
