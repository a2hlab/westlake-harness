/*
 * Copyright (c) 2021-2022 Huawei Device Co., Ltd.
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

#include "connection_manager.h"
#include "ability_connection.h"
#include "ability_context.h"
#include "ability_manager_client.h"
#include "dfx_dump_catcher.h"
#include "hichecker.h"
#include "hilog_tag_wrapper.h"
#include "ui_service_extension_connection_constants.h"

namespace OHOS {
namespace AbilityRuntime {
using namespace OHOS::HiviewDFX;
namespace {
constexpr const int64_t CONNECTING_TIMEOUT = 30000;
}
ConnectionManager& ConnectionManager::GetInstance()
{
    static ConnectionManager connectionManager;
    return connectionManager;
}

ErrCode ConnectionManager::ConnectAbility(const sptr<IRemoteObject>& connectCaller,
    const AAFwk::Want& want, const sptr<AbilityConnectCallback>& connectCallback)
{
    return ConnectAbilityInner(connectCaller, want, AAFwk::DEFAULT_INVAL_VALUE, connectCallback);
}

ErrCode ConnectionManager::ConnectAbilityWithAccount(const sptr<IRemoteObject>& connectCaller,
    const AAFwk::Want& want, int accountId, const sptr<AbilityConnectCallback>& connectCallback)
{
    return ConnectAbilityInner(connectCaller, want, accountId, connectCallback);
}

ErrCode ConnectionManager::ConnectUIServiceExtensionAbility(const sptr<IRemoteObject>& connectCaller,
    const AAFwk::Want& want, const sptr<AbilityConnectCallback>& connectCallback)
{
    return ConnectAbilityInner(connectCaller, want, AAFwk::DEFAULT_INVAL_VALUE, connectCallback,
        AppExecFwk::ExtensionAbilityType::UI_SERVICE);
}

ErrCode ConnectionManager::ConnectExtensionAbilityWithExtensionType(const sptr<IRemoteObject>& connectCaller,
    const AAFwk::Want& want, const sptr<AbilityConnectCallback>& connectCallback,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    return ConnectAbilityInner(connectCaller, want, AAFwk::DEFAULT_INVAL_VALUE, connectCallback, extensionType);
}

ErrCode ConnectionManager::ConnectAbilityInner(const sptr<IRemoteObject>& connectCaller, const AAFwk::Want& want,
    int accountId, const sptr<AbilityConnectCallback>& connectCallback, AppExecFwk::ExtensionAbilityType extensionType)
{
    if (connectCaller == nullptr || connectCallback == nullptr) {
        TAG_LOGE(AAFwkTag::CONNECTION, "null connectCaller or connectCallback");
        return AAFwk::ERR_INVALID_CALLER;
    }

    AppExecFwk::ElementName connectReceiver = want.GetElement();
    TAG_LOGD(AAFwkTag::CONNECTION, "connectReceiver: %{public}s",
        (connectReceiver.GetBundleName() + ":" + connectReceiver.GetAbilityName()).c_str());

    sptr<AbilityConnection> abilityConnection;
    std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
    auto connectionIter = abilityConnections_.begin();
    for (; connectionIter != abilityConnections_.end(); ++connectionIter) {
        if (MatchConnection(connectCaller, want, accountId, *connectionIter) &&
            !IsConnectingTimeout(connectionIter->first)) {
            break;
        }
    }
    if (connectionIter != abilityConnections_.end()) {
        std::vector<sptr<AbilityConnectCallback>>& callbacks = connectionIter->second;
        callbacks.push_back(connectCallback);
        abilityConnection = connectionIter->first.abilityConnection;
        if (!abilityConnection) {
            TAG_LOGE(AAFwkTag::CONNECTION, "AbilityConnection not exist");
            return AAFwk::ERR_INVALID_CALLER;
        }
        TAG_LOGI(AAFwkTag::CONNECTION, "abilityConnectionsSize: %{public}zu, ConnectionState: %{public}d",
            abilityConnections_.size(), abilityConnection->GetConnectionState());
        abilityConnection->AddConnectCallback(connectCallback);
        TAG_LOGD(AAFwkTag::CONNECTION, "abilityConnection exist, callbackSize:%{public}zu", callbacks.size());
        if (abilityConnection->GetConnectionState() == CONNECTION_STATE_CONNECTED) {
            connectCallback->OnAbilityConnectDone(connectReceiver, abilityConnection->GetRemoteObject(),
                abilityConnection->GetResultCode());
            return ERR_OK;
        } else if (abilityConnection->GetConnectionState() == CONNECTION_STATE_CONNECTING) {
            return ERR_OK;
        } else {
            TAG_LOGE(AAFwkTag::CONNECTION, "abilityConnection disconnected");
            abilityConnections_.erase(connectionIter);
            return CreateConnection(connectCaller, want, accountId, connectCallback, extensionType);
        }
    } else {
        return CreateConnection(connectCaller, want, accountId, connectCallback, extensionType);
    }
}

void* ConnectionManager::GetUIServiceExtProxyPtr(const AAFwk::Want& want)
{
    sptr<IRemoteObject> uiServiceExtProxySptr = want.GetRemoteObject(UISERVICEHOSTPROXY_KEY);
    void* uiServiceExtProxy = nullptr;
    if (uiServiceExtProxySptr != nullptr) {
        uiServiceExtProxy = uiServiceExtProxySptr.GetRefPtr();
    }
    return uiServiceExtProxy;
}

bool ConnectionManager::MatchConnection(
    const sptr<IRemoteObject>& connectCaller, const AAFwk::Want& connectReceiver, int32_t accountId,
    const std::map<ConnectionInfo, std::vector<sptr<AbilityConnectCallback>>>::value_type& connection)
{
    void* uiServiceExtProxy = GetUIServiceExtProxyPtr(connectReceiver);
    if (uiServiceExtProxy != connection.first.uiServiceExtProxy) {
        return false;
    }

    if (accountId != connection.first.userid) {
        return false;
    }
    if (!connectReceiver.GetElement().GetAbilityName().empty()) {
        return connectCaller == connection.first.connectCaller &&
            connectReceiver.GetElement().GetBundleName() == connection.first.connectReceiver.GetBundleName() &&
            connectReceiver.GetElement().GetModuleName() == connection.first.connectReceiver.GetModuleName() &&
            connectReceiver.GetElement().GetAbilityName() == connection.first.connectReceiver.GetAbilityName();
    } else {
        // ImplicitConnect
        return connectCaller == connection.first.connectCaller &&
            connectReceiver.GetElement().GetBundleName() == connection.first.connectReceiver.GetBundleName() &&
            connectReceiver.GetOperation() == connection.first.connectReceiver;
    }
}

ErrCode ConnectionManager::CreateConnection(const sptr<IRemoteObject>& connectCaller, const AAFwk::Want& want,
    int accountId, const sptr<AbilityConnectCallback>& connectCallback, AppExecFwk::ExtensionAbilityType extensionType)
{
    TAG_LOGD(AAFwkTag::CONNECTION, "called");
    sptr<AbilityConnection> abilityConnection = new AbilityConnection();
    if (abilityConnection == nullptr) {
        TAG_LOGE(AAFwkTag::CONNECTION, "null abilityConnection");
        return AAFwk::ERR_INVALID_CALLER;
    }
    abilityConnection->AddConnectCallback(connectCallback);
    abilityConnection->SetConnectionState(CONNECTION_STATE_CONNECTING);
    ErrCode ret = ERR_OK;
    ret = AAFwk::AbilityManagerClient::GetInstance()->ConnectAbilityWithExtensionType(
        want, abilityConnection, connectCaller, accountId, extensionType);
    std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
    if (ret == ERR_OK) {
        ConnectionInfo connectionInfo(connectCaller, want.GetOperation(), abilityConnection, accountId);
        connectionInfo.RecordConnectingTime();
        void* uiServiceExtProxy = GetUIServiceExtProxyPtr(want);
        connectionInfo.SetUIServiceExtProxyPtr(uiServiceExtProxy);
        std::vector<sptr<AbilityConnectCallback>> callbacks;
        callbacks.push_back(connectCallback);
        abilityConnections_[connectionInfo] = callbacks;
    } else {
        TAG_LOGE(AAFwkTag::CONNECTION, "error:%{public}d", ret);
    }
    return ret;
}

ErrCode ConnectionManager::DisconnectAbility(const sptr<IRemoteObject>& connectCaller,
    const AppExecFwk::ElementName& connectReceiver, const sptr<AbilityConnectCallback>& connectCallback)
{
    AAFwk::Want wantReceiver;
    wantReceiver.SetElement(connectReceiver);
    return DisconnectAbility(connectCaller, wantReceiver, connectCallback);
}

ErrCode ConnectionManager::DisconnectAbility(const sptr<IRemoteObject>& connectCaller,
    const AAFwk::Want& connectReceiver, const sptr<AbilityConnectCallback>& connectCallback,
    int32_t accountId)
{
    if (connectCaller == nullptr || connectCallback == nullptr) {
        TAG_LOGE(AAFwkTag::CONNECTION, "null connectCaller or connectCallback");
        return AAFwk::ERR_INVALID_CALLER;
    }
    auto element = connectReceiver.GetElement();
    TAG_LOGD(AAFwkTag::CONNECTION, "connectReceiver: %{public}s",
        (element.GetBundleName() + ":" + element.GetAbilityName()).c_str());
    std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
    bool found = false;
    auto item = abilityConnections_.begin();
    if (!abilityConnections_.empty()) {
        TAG_LOGI(AAFwkTag::CONNECTION, "Connection size:%{public}zu", abilityConnections_.size());
    }
    while (item != abilityConnections_.end()) {
        if (!MatchConnection(connectCaller, connectReceiver, accountId, *item) ||
            std::find(item->second.begin(), item->second.end(), connectCallback) == item->second.end()) {
            item++;
            continue;
        }
        found = true;
        TAG_LOGD(AAFwkTag::CONNECTION, "callback size: %{public}zu", item->second.size());
        auto iter = item->second.begin();
        while (iter != item->second.end()) {
            if (*iter == connectCallback) {
                iter = item->second.erase(iter);
            } else {
                iter++;
            }
        }
        sptr<AbilityConnection> abilityConnection = item->first.abilityConnection;
        if (item->second.empty()) {
            item = abilityConnections_.erase(item);
            TAG_LOGI(AAFwkTag::CONNECTION, "no callback left, disconnectAbility");
            auto ret = AAFwk::AbilityManagerClient::GetInstance()->DisconnectAbility(abilityConnection);
            if (ret != ERR_OK) {
                TAG_LOGE(AAFwkTag::CONNECTION, "disconnect err:%{public}d", ret);
                return ret;
            }
        } else {
            connectCallback->OnAbilityDisconnectDone(element, ERR_OK);
            abilityConnection->RemoveConnectCallback(connectCallback);
            TAG_LOGD(AAFwkTag::CONNECTION, "callbacks not empty, no need disconnectAbility");
            item++;
        }
    }
    if (!found) {
        TAG_LOGE(AAFwkTag::CONNECTION, "not find conn");
        return AAFwk::CONNECTION_NOT_EXIST;
    }
    return ERR_OK;
}

bool ConnectionManager::DisconnectCaller(const sptr<IRemoteObject>& connectCaller)
{
    TAG_LOGD(AAFwkTag::CONNECTION, "call");
    if (connectCaller == nullptr) {
        TAG_LOGE(AAFwkTag::CONNECTION, "null connectCaller");
        return false;
    }
    std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
    TAG_LOGD(AAFwkTag::CONNECTION, "abilityConnectionsSize:%{public}zu", abilityConnections_.size());

    bool isDisconnect = false;
    auto iter = abilityConnections_.begin();
    while (iter != abilityConnections_.end()) {
        ConnectionInfo connectionInfo = iter->first;
        if (IsConnectCallerEqual(connectionInfo.connectCaller, connectCaller)) {
            TAG_LOGD(AAFwkTag::CONNECTION, "DisconnectAbility");
            ErrCode ret =
                AAFwk::AbilityManagerClient::GetInstance()->DisconnectAbility(connectionInfo.abilityConnection);
            if (ret != ERR_OK) {
                TAG_LOGE(AAFwkTag::CONNECTION, "error:%{public}d", ret);
            }
            iter = abilityConnections_.erase(iter);
            isDisconnect = true;
        } else {
            ++iter;
        }
    }

    TAG_LOGD(AAFwkTag::CONNECTION, "abilityConnectionsSize:%{public}zu", abilityConnections_.size());
    return isDisconnect;
}

bool ConnectionManager::RemoveConnection(const sptr<AbilityConnection> connection)
{
    std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
    TAG_LOGD(AAFwkTag::CONNECTION, "abilityConnectionsSize: %{public}zu", abilityConnections_.size());

    bool isDisconnect = false;
    auto iter = abilityConnections_.begin();
    while (iter != abilityConnections_.end()) {
        ConnectionInfo connectionInfo = iter->first;
        if (connectionInfo.abilityConnection == connection) {
            TAG_LOGD(AAFwkTag::CONNECTION, "Remove connection");
            iter = abilityConnections_.erase(iter);
            isDisconnect = true;
        } else {
            ++iter;
        }
    }
    return isDisconnect;
}

bool ConnectionManager::DisconnectNonexistentService(
    const AppExecFwk::ElementName& element, const sptr<AbilityConnection> connection)
{
    bool exit = false;
    std::map<ConnectionInfo, std::vector<sptr<AbilityConnectCallback>>> abilityConnections;
    {
        std::lock_guard<std::recursive_mutex> lock(connectionsLock_);
        abilityConnections = abilityConnections_;
    }
    TAG_LOGD(AAFwkTag::CONNECTION, "abilityConnectionsSize: %{public}zu", abilityConnections.size());

    for (auto &&abilityConnection : abilityConnections) {
        ConnectionInfo connectionInfo = abilityConnection.first;
        if (connectionInfo.abilityConnection == connection &&
            connectionInfo.connectReceiver.GetBundleName() == element.GetBundleName()) {
            TAG_LOGD(AAFwkTag::CONNECTION, "find connection");
            exit = true;
            break;
        }
    }
    if (!exit) {
        TAG_LOGE(AAFwkTag::CONNECTION, "service need disconnect");
        AAFwk::AbilityManagerClient::GetInstance()->DisconnectAbility(connection);
        return true;
    }
    return false;
}

void ConnectionManager::ReportConnectionLeakEvent(const int pid, const int tid)
{
    TAG_LOGD(AAFwkTag::CONNECTION, "pid:%{public}d, tid:%{public}d", pid, tid);
    if (HiChecker::Contains(HiviewDFX::Rule::RULE_CHECK_ABILITY_CONNECTION_LEAK)) {
        DfxDumpCatcher dumpLog;
        std::string stackTrace;
        bool ret = dumpLog.DumpCatch(pid, tid, stackTrace);
        if (ret) {
            std::string cautionMsg = "TriggerRule:RULE_CHECK_ABILITY_CONNECTION_LEAK-pid=" +
                std::to_string(pid) + "-tid=" + std::to_string(tid) + ", has leaked connection" +
                ", Are you missing a call to DisconnectAbility()";
            TAG_LOGD(AAFwkTag::CONNECTION, "cautionMsg:%{public}s", cautionMsg.c_str());
            Caution caution(HiviewDFX::Rule::RULE_CHECK_ABILITY_CONNECTION_LEAK, cautionMsg, stackTrace);
            HiChecker::NotifyAbilityConnectionLeak(caution);
        } else {
            TAG_LOGE(AAFwkTag::CONNECTION, "dumpCatch stackTrace failed");
        }
    }
}

bool ConnectionManager::IsConnectCallerEqual(const sptr<IRemoteObject>& connectCaller,
    const sptr<IRemoteObject>& connectCallerOther)
{
    return connectCaller == connectCallerOther;
}

bool ConnectionManager::IsConnectReceiverEqual(AAFwk::Operation& connectReceiver,
    const AppExecFwk::ElementName& connectReceiverOther)
{
    return connectReceiver.GetBundleName() == connectReceiverOther.GetBundleName() &&
        connectReceiver.GetAbilityName() == connectReceiverOther.GetAbilityName();
}

bool ConnectionManager::IsConnectingTimeout(const ConnectionInfo& info)
{
    if (info.connectingTime == 0) {
        return false;
    }
    if (!info.abilityConnection || info.abilityConnection->GetConnectionState() != CONNECTION_STATE_CONNECTING) {
        return false;
    }
    auto now = std::chrono::steady_clock::now().time_since_epoch();
    auto duration = std::chrono::duration_cast<std::chrono::milliseconds>(now).count() - info.connectingTime;
    if (duration >= CONNECTING_TIMEOUT) {
        TAG_LOGW(AAFwkTag::CONNECTION, "connecting timeout, no reuse");
        return true;
    }
    return false;
}
} // namespace AbilityRuntime
} // namespace OHOS
