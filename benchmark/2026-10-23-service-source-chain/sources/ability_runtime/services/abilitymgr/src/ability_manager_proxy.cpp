/*
 * Copyright (c) 2023-2026 Huawei Device Co., Ltd.
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

#include "ability_manager_proxy.h"

#include "ability_scheduler_stub.h"
#include "ability_util.h"
#include "app_utils.h"
#include "freeze_util.h"
#include "hitrace_chain_utils.h"
#include "hitrace_meter.h"
#include "ipc_capacity_wrap.h"
#include "server_constant.h"
#include "status_bar_delegate_interface.h"
#include "mission_listener_interface.h"
#include "mission_snapshot.h"
#include "snapshot.h"
#ifdef SUPPORT_SCREEN
#include "pixel_map.h"
#endif //SUPPORT_SCREEN

namespace OHOS {
namespace AAFwk {
namespace {
#define PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(messageParcel, type, value) \
    do {                                                                  \
        if (!(messageParcel).Write##type(value)) {                        \
            TAG_LOGE(AAFwkTag::ABILITYMGR,                                \
            "failed write %{public}s", #value);                        \
            return INNER_ERR;                                             \
        }                                                                 \
    } while (0)
}
using AutoStartupInfo = AbilityRuntime::AutoStartupInfo;
constexpr int32_t CYCLE_LIMIT = 1000;
constexpr int32_t INDEX_ONE = 1;
constexpr int32_t MAX_AUTO_STARTUP_COUNT = 100;
constexpr int32_t MAX_UPDATE_CONFIG_SIZE = 100;
constexpr int32_t MAX_WANT_LIST_SIZE = 4;
constexpr int32_t MAX_IPC_CAPACITY_FOR_WANT_LIST = 4 * 216 * 1024;
constexpr int32_t MAX_DUMP_STATE_SIZE = 10000;
constexpr int32_t MAX_INTENT_SIZE = 10000;
bool AbilityManagerProxy::WriteInterfaceToken(MessageParcel &data)
{
    if (!data.WriteInterfaceToken(AbilityManagerProxy::GetDescriptor())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return false;
    }
    return true;
}

bool AbilityManagerProxy::ExtendMaxIpcCapacityForWant(const Want &want, MessageParcel &data)
{
    auto isCallBySCB = want.GetBoolParam(AbilityRuntime::ServerConstant::IS_CALL_BY_SCB, true);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "isCallBySCB:%{public}d", isCallBySCB);
    if (!isCallBySCB) {
        AAFwk::ExtendMaxIpcCapacityForInnerWant(data);
        return true;
    }
    return false;
}

int AbilityManagerProxy::StartAbility(const Want &want, int32_t userId, int requestCode, uint64_t specifiedFullTokenId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    Ability_MANAGER_HITRACE_CHAIN_NAME("StartAbility", HITRACE_FLAG_INCLUDE_ASYNC);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }

    if (!data.WriteUint64(specifiedFullTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "specifiedFullTokenId write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

AppExecFwk::ElementName AbilityManagerProxy::GetTopAbility(bool isNeedLocalDeviceId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return {};
    }
    if (!data.WriteBool(isNeedLocalDeviceId)) {
        return {};
    }

    int error = SendRequest(AbilityManagerInterfaceCode::GET_TOP_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return {};
    }
    std::unique_ptr<AppExecFwk::ElementName> name(reply.ReadParcelable<AppExecFwk::ElementName>());
    if (!name) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read info fail");
        return {};
    }
    AppExecFwk::ElementName result = *name;
    return result;
}

AppExecFwk::ElementName AbilityManagerProxy::GetElementNameByToken(sptr<IRemoteObject> token,
    bool isNeedLocalDeviceId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return {};
    }
    if (!data.WriteRemoteObject(token)) {
        return {};
    }
    if (!data.WriteBool(isNeedLocalDeviceId)) {
        return {};
    }
    int error = SendRequest(AbilityManagerInterfaceCode::GET_ELEMENT_NAME_BY_TOKEN, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return {};
    }
    std::unique_ptr<AppExecFwk::ElementName> name(reply.ReadParcelable<AppExecFwk::ElementName>());
    if (!name) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read info fail");
        return {};
    }
    AppExecFwk::ElementName result = *name;
    return result;
}

int AbilityManagerProxy::StartAbility(const Want &want, const AbilityStartSetting &abilityStartSetting,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    Ability_MANAGER_HITRACE_CHAIN_NAME("StartAbility", HITRACE_FLAG_INCLUDE_ASYNC);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&abilityStartSetting)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityStartSetting write fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and callerToken write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_FOR_SETTINGS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbility(
    const Want &want, const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode,
    uint64_t specifiedFullTokenId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    Ability_MANAGER_HITRACE_CHAIN_NAME("StartAbility", HITRACE_FLAG_INCLUDE_ASYNC);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    if (!data.WriteUint64(specifiedFullTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "specifiedFullTokenId write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_ADD_CALLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityWithSpecifyTokenId(
    const Want &want, const sptr<IRemoteObject> &callerToken, uint32_t specifyTokenId, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(specifyTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "specifyTokenId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_WITH_SPECIFY_TOKENID, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartAbilityByInsightIntent(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint64_t intentId, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid callertoken");
        return INNER_ERR;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
        return INNER_ERR;
    }

    if (!data.WriteUint64(intentId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "intentId write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    int32_t error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_BY_INSIGHT_INTENT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "start err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbility(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    Ability_MANAGER_HITRACE_CHAIN_NAME("StartAbility", HITRACE_FLAG_INCLUDE_ASYNC);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&startOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeParcelable fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and callerToken write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_FOR_OPTIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityAsCaller(const Want &want, const sptr<IRemoteObject> &callerToken,
    sptr<IRemoteObject> asCallerSourceToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    if (callerToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    if (asCallerSourceToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, asCallerSourceToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestCode);
    int error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_AS_CALLER_BY_TOKEN, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityAsCaller(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, sptr<IRemoteObject> asCallerSourceToken,
    int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &startOptions);
    if (callerToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    if (asCallerSourceToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, asCallerSourceToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestCode);

    error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_AS_CALLER_FOR_OPTIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityForResultAsCaller(
    const Want &want, const sptr<IRemoteObject> &callerToken, int requestCode, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token failed");
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    if (callerToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestCode);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    MessageParcel reply;
    MessageOption option;
    int error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_FOR_RESULT_AS_CALLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityForResultAsCaller(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, int requestCode, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token failed");
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &startOptions);
    if (callerToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestCode);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    MessageParcel reply;
    MessageOption option;
    int error =
        SendRequest(AbilityManagerInterfaceCode::START_ABILITY_FOR_RESULT_AS_CALLER_FOR_OPTIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

ErrCode AbilityManagerProxy::StartUIAbilitiesInSplitWindowMode(int32_t primaryWindowId,
    const AAFwk::Want &secondaryWant, sptr<IRemoteObject> callerToken)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start abilities");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INVALID_CALLER_TOKEN;
    }
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    if (!data.WriteInt32(primaryWindowId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write sourceWindowId fail");
        return ERR_WRITE_INT32_FAILED;
    }
    if (!data.WriteParcelable(&secondaryWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return ERR_WRITE_WANT;
    }
    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return ERR_WRITE_CALLER_TOKEN_FAILED;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::START_UI_ABILITIES_IN_SPLIT_WINDOW_MODE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

ErrCode AbilityManagerProxy::StartUIAbilities(const std::vector<AAFwk::Want> &wantList,
    const std::string &requestKey, sptr<IRemoteObject> callerToken)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start abilities");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INVALID_CALLER_TOKEN;
    }
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    int32_t size = static_cast<int32_t>(wantList.size());
    if (size < INDEX_ONE || size > MAX_WANT_LIST_SIZE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "vector size error");
        return START_UI_ABILITIES_WANT_LIST_SIZE_ERROR;
    }

    (data).SetMaxCapacity(MAX_IPC_CAPACITY_FOR_WANT_LIST);

    if (!data.WriteInt32(size)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write size fail");
        return ERR_WRITE_INT32_FAILED;
    }
    for (const Want &item : wantList) {
        if (!data.WriteParcelable(&item)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
            return ERR_WRITE_WANT;
        }
    }

    if (!data.WriteString(requestKey)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write requestKey fail");
        return ERR_WRITE_STRING_FAILED;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return ERR_WRITE_CALLER_TOKEN_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_UI_ABILITIES, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::CheckUISessionParams(MessageParcel &data, const sptr<IRemoteObject> &callerToken,
    const sptr<SessionInfo> &sessionInfo, int32_t userId, int requestCode)
{
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (sessionInfo) {
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    return ERR_OK;
}

int AbilityManagerProxy::StartAbilityByUIContentSession(const Want &want,
    const sptr<IRemoteObject> &callerToken, const sptr<SessionInfo> &sessionInfo,
    int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (CheckUISessionParams(data, callerToken, sessionInfo, userId, requestCode) == INNER_ERR) {
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_UI_SESSION_ABILITY_ADD_CALLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityByUIContentSession(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, const sptr<SessionInfo> &sessionInfo,
    int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&startOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeParcelable fail");
        return INNER_ERR;
    }
    if (CheckUISessionParams(data, callerToken, sessionInfo, userId, requestCode) == INNER_ERR) {
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_UI_SESSION_ABILITY_FOR_OPTIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityOnlyUIAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint32_t specifyTokenId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid callertoken");
        return INNER_ERR;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
        return INNER_ERR;
    }

    if (!data.WriteUint32(specifyTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "specifyTokenId write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    int32_t error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_ONLY_UI_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartExtensionAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "want write fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "flag and callerToken write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "userId write failed");
        return INNER_ERR;
    }
    if (!data.WriteInt32(static_cast<int32_t>(extensionType))) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "extensionType write failed");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::START_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RequestModalUIExtension(const Want &want)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    int error;
    MessageParcel reply;
    MessageOption option;
    error = SendRequest(AbilityManagerInterfaceCode::REQUEST_MODAL_UIEXTENSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::PreloadUIExtensionAbility(
    const Want &want, std::string &hostBundleName, int32_t userId, int32_t hostPid, int32_t requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);

    if (!data.WriteString16(Str8ToStr16(hostBundleName))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "hostBundleName write fail");
        return ERR_INVALID_VALUE;
    }

    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, hostPid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestCode);
    int error;
    MessageParcel reply;
    MessageOption option;
    error = SendRequest(AbilityManagerInterfaceCode::PRELOAD_UIEXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ChangeAbilityVisibility(sptr<IRemoteObject> token, bool isShow)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteBool(isShow)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write isShow fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::CHANGE_ABILITY_VISIBILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ChangeUIAbilityVisibilityBySCB(sptr<SessionInfo> sessionInfo, bool isShow)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteParcelable(sessionInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write sessionInfo fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteBool(isShow)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write isShow fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::CHANGE_UI_ABILITY_VISIBILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start uiext");
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    CHECK_POINTER_AND_RETURN_LOG(extensionSessionInfo, ERR_INVALID_VALUE,
        "connect fail, null extensionSessionInfo");
    if (extensionSessionInfo) {
        if (!data.WriteBool(true) || !data.WriteParcelable(extensionSessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and extensionSessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write failed");
        return INNER_ERR;
    }

    if (extensionSessionInfo->uiExtensionUsage == UIExtensionUsage::EMBEDDED) {
        error = SendRequest(AbilityManagerInterfaceCode::START_UI_EXTENSION_ABILITY_EMBEDDED, data, reply, option);
    } else if (extensionSessionInfo->uiExtensionUsage == UIExtensionUsage::MODAL) {
        error = SendRequest(AbilityManagerInterfaceCode::START_UI_EXTENSION_ABILITY, data, reply, option);
    } else if (extensionSessionInfo->uiExtensionUsage == UIExtensionUsage::PRE_VIEW_EMBEDDED) {
        error = SendRequest(AbilityManagerInterfaceCode::START_UI_EXTENSION_PRE_VIEW_EMBEDDED, data, reply, option);
    } else {
        error = SendRequest(AbilityManagerInterfaceCode::START_UI_EXTENSION_CONSTRAINED_EMBEDDED, data, reply, option);
    }

    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartUIAbilityBySCB(sptr<SessionInfo> sessionInfo, AbilityRuntime::StartParamsBySCB &params,
    bool &isColdStart)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start by scb");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteParcelable(&params)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "params write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::START_UI_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    isColdStart = reply.ReadBool();
    return reply.ReadInt32();
}

int AbilityManagerProxy::StopExtensionAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "want write fail");
        return INNER_ERR;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "flag and callerToken write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(static_cast<int32_t>(extensionType))) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "writeInt32 fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::STOP_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::TerminateAbility(const sptr<IRemoteObject> &token, int resultCode, const Want *resultWant)
{
    return TerminateAbility(token, resultCode, resultWant, true);
}

int AbilityManagerProxy::TerminateAbility(const sptr<IRemoteObject> &token,
    int resultCode, const Want *resultWant, bool flag)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and token write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(resultCode) || !data.WriteParcelable(resultWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write flag fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::TERMINATE_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::BackToCallerAbilityWithResult(const sptr<IRemoteObject> &token, int resultCode,
    const Want *resultWant, int64_t callerRequestCode)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    CHECK_POINTER_AND_RETURN_LOG(token, ERR_INVALID_VALUE, "null token");

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "token write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(resultCode) || !data.WriteParcelable(resultWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write resultCode fail");
        return INNER_ERR;
    }
    if (!data.WriteInt64(callerRequestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write requestCode fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::BACK_TO_CALLER_UIABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::TerminateUIServiceExtensionAbility(const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and token write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }

    error = SendRequest(AbilityManagerInterfaceCode::TERMINATE_UI_SERVICE_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::TerminateUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo, int resultCode,
    const Want *resultWant)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    CHECK_POINTER_AND_RETURN_LOG(extensionSessionInfo, ERR_INVALID_VALUE,
        "connect fail, null extensionSessionInfo");
    if (extensionSessionInfo) {
        if (!data.WriteBool(true) || !data.WriteParcelable(extensionSessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and extensionSessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }

    if (!data.WriteInt32(resultCode) || !data.WriteParcelable(resultWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::TERMINATE_UI_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::CloseUIExtensionAbilityBySCB(const sptr<IRemoteObject> token)
{
    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "input invalid");
        return ERR_INVALID_VALUE;
    }

    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and token fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::CLOSE_UI_EXTENSION_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::CloseUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool isUserRequestedExit,
    uint32_t sceneFlag)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteBool(isUserRequestedExit)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isUserRequestedExit write fail");
        return ERR_IPC_PROXY_WRITE_FAILED;
    }
    if (!data.WriteUint32(sceneFlag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sceneFlag write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::CLOSE_UI_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::SendResultToAbility(int32_t requestCode, int32_t resultCode, Want& resultWant)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(resultCode) || !data.WriteParcelable(&resultWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::SEND_RESULT_TO_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MoveAbilityToBackground(const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and token write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    error = SendRequest(AbilityManagerInterfaceCode::MOVE_ABILITY_TO_BACKGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::MoveUIAbilityToBackground(const sptr<IRemoteObject> token)
{
    CHECK_POINTER_AND_RETURN_LOG(token, ERR_INVALID_VALUE, "move fail, null token");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write Token fail");
        return IPC_PROXY_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, token);
    int32_t error = SendRequest(AbilityManagerInterfaceCode::MOVE_UI_ABILITY_TO_BACKGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::CloseAbility(const sptr<IRemoteObject> &token, int resultCode, const Want *resultWant)
{
    return TerminateAbility(token, resultCode, resultWant, false);
}

int AbilityManagerProxy::ConnectAbility(
    const Want &want, const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken, int32_t userId)
{
    return ConnectAbilityCommon(want, connect, callerToken, AppExecFwk::ExtensionAbilityType::SERVICE, userId);
}

int AbilityManagerProxy::ConnectAbilityCommon(
    const Want &want, const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken,
    AppExecFwk::ExtensionAbilityType extensionType, int32_t userId, bool isQueryExtensionOnly,
    uint64_t specifiedFullTokenId, int32_t loadTimeout)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    Ability_MANAGER_HITRACE_CHAIN_NAME("ConnectAbilityCommon", HITRACE_FLAG_INCLUDE_ASYNC);
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    CHECK_POINTER_AND_RETURN_LOG(connect, ERR_INVALID_VALUE, "fail, null connect");
    if (connect->AsObject()) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, connect->AsObject());
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    if (callerToken) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, static_cast<int32_t>(extensionType));
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, isQueryExtensionOnly);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Uint64, specifiedFullTokenId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, loadTimeout);
    int error = SendRequest(AbilityManagerInterfaceCode::CONNECT_ABILITY_WITH_TYPE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s, request error:%{public}d", __func__, error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ConnectUIExtensionAbility(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<SessionInfo> &sessionInfo, int32_t userId, sptr<UIExtensionAbilityConnectInfo> connectInfo)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    CHECK_POINTER_AND_RETURN_LOG(connect, ERR_INVALID_VALUE, "connect fail, null connect");
    if (connect->AsObject()) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, connect->AsObject());
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    CHECK_POINTER_AND_RETURN_LOG(sessionInfo, ERR_INVALID_VALUE, "connect fail, null sessionInfo");
    if (sessionInfo) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, sessionInfo);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    if (connectInfo != nullptr) {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, true);
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, connectInfo);
    } else {
        PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Bool, false);
    }

    int error = SendRequest(AbilityManagerInterfaceCode::CONNECT_UI_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    if (connectInfo != nullptr) {
        sptr<UIExtensionAbilityConnectInfo> replyInfo = reply.ReadParcelable<UIExtensionAbilityConnectInfo>();
        if (replyInfo != nullptr) {
            connectInfo->uiExtensionAbilityId = replyInfo->uiExtensionAbilityId;
            TAG_LOGD(AAFwkTag::ABILITYMGR, "UIExtensionAbilityId is %{public}d.", connectInfo->uiExtensionAbilityId);
        }
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::DisconnectAbility(sptr<IAbilityConnection> connect)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "fail, connect null");
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(connect->AsObject())) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connect write failed");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::DISCONNECT_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

sptr<IAbilityScheduler> AbilityManagerProxy::AcquireDataAbility(
    const Uri &uri, bool tryBind, const sptr<IRemoteObject> &callerToken)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start acquire data");
        return nullptr;
    }
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!callerToken) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid parameters");
        return nullptr;
    }
    if (!WriteInterfaceToken(data)) {
        return nullptr;
    }
    if (!data.WriteString(uri.ToString()) || !data.WriteBool(tryBind) || !data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return nullptr;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ACQUIRE_DATA_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return nullptr;
    }

    return iface_cast<IAbilityScheduler>(reply.ReadRemoteObject());
}

int AbilityManagerProxy::ReleaseDataAbility(
    sptr<IAbilityScheduler> dataAbilityScheduler, const sptr<IRemoteObject> &callerToken)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!dataAbilityScheduler || !callerToken) {
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(dataAbilityScheduler->AsObject()) || !data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::RELEASE_DATA_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::AttachAbilityThread(const sptr<IAbilityScheduler> &scheduler, const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (scheduler == nullptr) {
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(scheduler->AsObject()) || !data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ATTACH_ABILITY_THREAD, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        AbilityRuntime::FreezeUtil::GetInstance().AppendLifecycleEvent(token,
            std::string("AttachAbilityThread; ipc error ") + std::to_string(error));
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::AbilityTransitionDone(const sptr<IRemoteObject> &token, int state, const PacMap &saveData)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token) || !data.WriteInt32(state)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token or state write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(&saveData)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "saveData write fail");
        AbilityRuntime::FreezeUtil::GetInstance().AppendLifecycleEvent(token,
            "AbilityTransitionDone; write saveData failed");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ABILITY_TRANSITION_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        AbilityRuntime::FreezeUtil::GetInstance().AppendLifecycleEvent(token,
            std::string("AbilityTransitionDone; ipc error ") + std::to_string(error));
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::AbilityWindowConfigTransitionDone(
    const sptr<IRemoteObject> &token, const WindowConfig &windowConfig)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token or state write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(&windowConfig)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "saveData write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ABILITY_WINDOW_CONFIG_TRANSITION_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ScheduleConnectAbilityDone(
    const sptr<IRemoteObject> &token, const sptr<IRemoteObject> &remoteObject)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "write flag and token fail");
            return ERR_INVALID_VALUE;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "write flag fail");
            return ERR_INVALID_VALUE;
        }
    }

    if (remoteObject) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(remoteObject)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "write flag and remoteObject fail");
            return ERR_INVALID_VALUE;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "write flag fail");
            return ERR_INVALID_VALUE;
        }
    }

    error = SendRequest(AbilityManagerInterfaceCode::CONNECT_ABILITY_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        AbilityRuntime::FreezeUtil::GetInstance().AppendLifecycleEvent(token,
            std::string("AbilityManagerProxy::ScheduleConnectAbilityDone; ipc error ") + std::to_string(error));
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ScheduleDisconnectAbilityDone(const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "token write failed.");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::DISCONNECT_ABILITY_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ScheduleCommandAbilityDone(const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "token write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::COMMAND_ABILITY_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ScheduleCommandAbilityWindowDone(
    const sptr<IRemoteObject> &token,
    const sptr<SessionInfo> &sessionInfo,
    WindowCommand winCmd,
    AbilityCommand abilityCmd)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(sessionInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(winCmd)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "winCmd write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(abilityCmd)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityCmd write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::COMMAND_ABILITY_WINDOW_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::DumpSysState(
    const std::string& args, std::vector<std::string>& state, bool isClient, bool isUserId, int UserId)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return;
    }
    data.WriteString16(Str8ToStr16(args));

    if (!data.WriteBool(isClient)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ;
    }
    if (!data.WriteBool(isUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ;
    }
    if (!data.WriteInt32(UserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ;
    }

    error = SendRequest(AbilityManagerInterfaceCode::DUMPSYS_STATE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    int32_t stackNum = reply.ReadInt32();
    if (stackNum > MAX_DUMP_STATE_SIZE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "config stackNum error");
        return;
    }
    for (int i = 0; i < stackNum; i++) {
        std::string stac = Str16ToStr8(reply.ReadString16());
        state.emplace_back(stac);
    }
}

void AbilityManagerProxy::DumpState(const std::string &args, std::vector<std::string> &state)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return;
    }
    data.WriteString16(Str8ToStr16(args));

    error = SendRequest(AbilityManagerInterfaceCode::DUMP_STATE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    int32_t stackNum = reply.ReadInt32();
    if (stackNum > MAX_DUMP_STATE_SIZE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "config stackNum error");
        return;
    }
    for (int i = 0; i < stackNum; i++) {
        std::string stac = Str16ToStr8(reply.ReadString16());
        state.emplace_back(stac);
    }
}

int AbilityManagerProxy::MinimizeAbility(const sptr<IRemoteObject> &token, bool fromUser)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteBool(fromUser)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::MINIMIZE_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MinimizeUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo,
    bool fromUser)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    CHECK_POINTER_AND_RETURN_LOG(extensionSessionInfo, ERR_INVALID_VALUE,
        "connect fail, null extensionSessionInfo");
    if (extensionSessionInfo) {
        if (!data.WriteBool(true) || !data.WriteParcelable(extensionSessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and extensionSessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteBool(fromUser)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::MINIMIZE_UI_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MinimizeUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool fromUser, uint32_t sceneFlag)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteBool(fromUser)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "fromUser write fail");
        return INNER_ERR;
    }
    if (!data.WriteUint32(sceneFlag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sceneFlag write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::MINIMIZE_UI_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StopServiceAbility(const Want &want, int32_t userId, const sptr<IRemoteObject> &token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "failedwrite flag and token fail");
            return ERR_INVALID_VALUE;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
            return ERR_INVALID_VALUE;
        }
    }
    error = SendRequest(AbilityManagerInterfaceCode::STOP_SERVICE_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

template <typename T>
int AbilityManagerProxy::GetParcelableInfos(MessageParcel &reply, std::vector<T> &parcelableInfos)
{
    int32_t infoSize = reply.ReadInt32();
    if (infoSize > CYCLE_LIMIT) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "infoSize large");
        return ERR_INVALID_VALUE;
    }

    for (int32_t i = 0; i < infoSize; i++) {
        std::unique_ptr<T> info(reply.ReadParcelable<T>());
        if (!info) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "readParcelableInfos fail");
            return ERR_INVALID_VALUE;
        }
        parcelableInfos.emplace_back(*info);
    }
    return NO_ERROR;
}

int AbilityManagerProxy::GetMissionSnapshot(const std::string& deviceId, int32_t missionId,
    MissionSnapshot& snapshot, bool isLowResolution)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(deviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteBool(isLowResolution)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isLowResolution write fail");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::GET_MISSION_SNAPSHOT_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    std::unique_ptr<MissionSnapshot> info(reply.ReadParcelable<MissionSnapshot>());
    if (!info) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "readParcelableInfo fail");
        auto errorCode = reply.ReadInt32();
        return errorCode ? errorCode : ERR_UNKNOWN_OBJECT;
    }
    snapshot = *info;
    return reply.ReadInt32();
}
#ifdef SUPPORT_SCREEN
void AbilityManagerProxy::UpdateMissionSnapShot(const sptr<IRemoteObject> &token,
    const std::shared_ptr<Media::PixelMap> &pixelMap)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return;
    }
    if (!data.WriteParcelable(pixelMap.get())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write pixelMap fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::UPDATE_MISSION_SNAPSHOT_FROM_WMS,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }
}
#endif // SUPPORT_SCREEN
void AbilityManagerProxy::EnableRecoverAbility(const sptr<IRemoteObject>& token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeRemoteObject fail");
        return;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ABILITY_RECOVERY_ENABLE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    return;
}

void AbilityManagerProxy::ScheduleRecoverAbility(const sptr<IRemoteObject>& token, int32_t reason, const Want *want)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeRemoteObject fail");
        return;
    }

    data.WriteInt32(reason);

    if (!data.WriteParcelable(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ABILITY_RECOVERY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    return;
}

void AbilityManagerProxy::SubmitSaveRecoveryInfo(const sptr<IRemoteObject>& token)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeRemoteObject fail");
        return;
    }

    error = SendRequest(AbilityManagerInterfaceCode::ABILITY_RECOVERY_SUBMITINFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    return;
}

int AbilityManagerProxy::KillProcess(const std::string &bundleName, bool clearPageStack, int32_t appIndex,
    const std::string& reason)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString16(Str8ToStr16(bundleName))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "bundleName write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteBool(clearPageStack)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "clearPageStack write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appIndex write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString16(Str8ToStr16(reason))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "reason write fail");
        return ERR_INVALID_VALUE;
    }
    int error = SendRequest(AbilityManagerInterfaceCode::KILL_PROCESS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::ScheduleClearRecoveryPageStack()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return;
    }

    int error = SendRequest(AbilityManagerInterfaceCode::CLEAR_RECOVERY_PAGE_STACK, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    return;
}

#ifdef ABILITY_COMMAND_FOR_TEST
int AbilityManagerProxy::ForceTimeoutForTest(const std::string &abilityName, const std::string &state)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString16(Str8ToStr16(abilityName))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityName write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString16(Str8ToStr16(state))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityName write fail");
        return ERR_INVALID_VALUE;
    }
    int error = SendRequest(AbilityManagerInterfaceCode::FORCE_TIMEOUT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}
#endif

int AbilityManagerProxy::UninstallApp(const std::string &bundleName, int32_t uid)
{
    return UninstallApp(bundleName, uid, 0);
}

int32_t AbilityManagerProxy::UninstallApp(const std::string &bundleName, int32_t uid, int32_t appIndex)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString16(Str8ToStr16(bundleName))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "bundleName write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(uid)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uid write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appIndex write fail");
        return ERR_INVALID_VALUE;
    }
    int error = SendRequest(AbilityManagerInterfaceCode::UNINSTALL_APP, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UpgradeApp(const std::string &bundleName, const int32_t uid, const std::string &exitMsg,
    int32_t appIndex)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, String16, Str8ToStr16(bundleName));
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, uid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, String16, Str8ToStr16(exitMsg));
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, appIndex);
    int error = SendRequest(AbilityManagerInterfaceCode::UPGRADE_APP, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sendRequest error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

sptr<IWantSender> AbilityManagerProxy::GetWantSender(
    const WantSenderInfo &wantSenderInfo, const sptr<IRemoteObject> &callerToken, int32_t uid)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return nullptr;
    }
    if (!data.WriteParcelable(&wantSenderInfo)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "writeParcelable fail");
        return nullptr;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::WANTAGENT, "flag and callerToken write fail");
            return nullptr;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::WANTAGENT, "flag write fail");
            return nullptr;
        }
    }

    if (!data.WriteInt32(uid)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "uid write fail");
        return nullptr;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_SENDER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return nullptr;
    }
    sptr<IWantSender> wantSender = iface_cast<IWantSender>(reply.ReadRemoteObject());
    if (!wantSender) {
        return nullptr;
    }
    return wantSender;
}

int AbilityManagerProxy::SendWantSender(sptr<IWantSender> target, SenderInfo &senderInfo)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&senderInfo)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "senderInfo write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SEND_PENDING_WANT_SENDER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return error;
    }
    std::unique_ptr<SenderInfo> completedDataReply(reply.ReadParcelable<SenderInfo>());
    if (!completedDataReply) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "readParcelableInfo fail");
        return INNER_ERR;
    }
    senderInfo = *completedDataReply;
    return reply.ReadInt32();
}

int AbilityManagerProxy::SendLocalWantSender(const SenderInfo &senderInfo)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&senderInfo)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "senderInfo write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SEND_LOCAL_PENDING_WANT_SENDER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::CancelWantSender(const sptr<IWantSender> &sender)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (sender == nullptr || !data.WriteRemoteObject(sender->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "sender write fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::CANCEL_PENDING_WANT_SENDER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return;
    }
}

int AbilityManagerProxy::GetPendingWantUid(const sptr<IWantSender> &target)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_UID, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return INNER_ERR;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetPendingWantUserId(const sptr<IWantSender> &target)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_USERID, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return INNER_ERR;
    }
    return reply.ReadInt32();
}

std::string AbilityManagerProxy::GetPendingWantBundleName(const sptr<IWantSender> &target)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return "";
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return "";
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_BUNDLENAME, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return "";
    }
    return Str16ToStr8(reply.ReadString16());
}

int AbilityManagerProxy::GetPendingWantCode(const sptr<IWantSender> &target)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_CODE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return INNER_ERR;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetPendingWantType(const sptr<IWantSender> &target)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_TYPE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return INNER_ERR;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::RegisterCancelListener(const sptr<IWantSender> &sender, const sptr<IWantReceiver> &receiver)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (sender == nullptr || !data.WriteRemoteObject(sender->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "sender write fail");
        return;
    }
    if (receiver == nullptr || !data.WriteRemoteObject(receiver->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "receiver write fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_CANCEL_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return;
    }
}

void AbilityManagerProxy::UnregisterCancelListener(const sptr<IWantSender> &sender, const sptr<IWantReceiver> &receiver)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (sender == nullptr || !data.WriteRemoteObject(sender->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "sender write fail");
        return;
    }
    if (receiver == nullptr || !data.WriteRemoteObject(receiver->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "receiver write fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_CANCEL_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return;
    }
}

int AbilityManagerProxy::GetPendingRequestWant(const sptr<IWantSender> &target, std::shared_ptr<Want> &want)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return INNER_ERR;
    }
    if (want == nullptr || !data.WriteParcelable(want.get())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "want write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_REQUEST_WANT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return error;
    }
    std::unique_ptr<Want> wantInfo(reply.ReadParcelable<Want>());
    if (!wantInfo) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "readParcelableInfo fail");
        return INNER_ERR;
    }
    want = std::move(wantInfo);

    return NO_ERROR;
}

int AbilityManagerProxy::GetWantSenderInfo(const sptr<IWantSender> &target, std::shared_ptr<WantSenderInfo> &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (target == nullptr || !data.WriteRemoteObject(target->AsObject())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "target write fail");
        return INNER_ERR;
    }
    if (info == nullptr || !data.WriteParcelable(info.get())) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "info write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PENDING_WANT_SENDER_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "request error:%{public}d", error);
        return error;
    }
    std::unique_ptr<WantSenderInfo> wantSenderInfo(reply.ReadParcelable<WantSenderInfo>());
    if (!wantSenderInfo) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "readParcelable Info fail");
        return INNER_ERR;
    }
    info = std::move(wantSenderInfo);

    return NO_ERROR;
}

int AbilityManagerProxy::GetAppMemorySize()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write Token fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_APP_MEMORY_SIZE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

bool AbilityManagerProxy::IsRamConstrainedDevice()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write Token faile");
        return false;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::IS_RAM_CONSTRAINED_DEVICE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return false;
    }
    return reply.ReadBool();
}

int AbilityManagerProxy::ContinueMission(const std::string &srcDeviceId, const std::string &dstDeviceId,
    int32_t missionId, const sptr<IRemoteObject> &callBack, AAFwk::WantParams &wantParams)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(srcDeviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "srcDeviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(dstDeviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "dstDeviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callBack)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callBack write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&wantParams)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "wantParams write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::CONTINUE_MISSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sendRequest error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ContinueMission(AAFwk::ContinueMissionInfo continueMissionInfo,
    const sptr<IRemoteObject> &callback)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(continueMissionInfo.srcDeviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "srcDeviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(continueMissionInfo.dstDeviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "dstDeviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(continueMissionInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callback)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callBack write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&continueMissionInfo.wantParams)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "wantParams write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(continueMissionInfo.srcBundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "srcBundleName write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(continueMissionInfo.continueType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "continueType write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::CONTINUE_MISSION_OF_BUNDLENAME, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::ContinueAbility(const std::string &deviceId, int32_t missionId, uint32_t versionCode)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(deviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return INNER_ERR;
    }
    if (!data.WriteUint32(versionCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "versionCode write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::CONTINUE_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartContinuation(const Want &want, const sptr<IRemoteObject> &abilityToken, int32_t status)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option = {MessageOption::TF_ASYNC};
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(abilityToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityToken write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(status)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "status write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_CONTINUATION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::NotifyCompleteContinuation(const std::string &deviceId, int32_t sessionId, bool isSuccess)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option = {MessageOption::TF_ASYNC};
    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (!data.WriteString(deviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId write fail");
        return;
    }
    if (!data.WriteInt32(sessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionId write fail");
        return;
    }
    if (!data.WriteBool(isSuccess)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "result write fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::NOTIFY_COMPLETE_CONTINUATION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
}

int AbilityManagerProxy::NotifyContinuationResult(int32_t missionId, int32_t result)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(result)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "result write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::NOTIFY_CONTINUATION_RESULT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::LockMissionForCleanup(int32_t missionId)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::LOCK_MISSION_FOR_CLEANUP, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::UnlockMissionForCleanup(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::UNLOCK_MISSION_FOR_CLEANUP, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "unlock mission,error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::SetLockedState(int32_t sessionId, bool lockedState)
{
    MessageParcel data;

    if (!WriteInterfaceToken(data)) {
        return;
    }

    if (!data.WriteInt32(sessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return;
    }

    if (!data.WriteBool(lockedState)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeBool fail");
        return;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);
    auto error = SendRequest(AbilityManagerInterfaceCode::SET_SESSION_LOCKED_STATE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "error: %{public}d", error);
        return;
    }
    return;
}

int AbilityManagerProxy::RegisterMissionListener(const sptr<IMissionListener> &listener)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!listener) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener null");
        return ERR_INVALID_VALUE;
    }

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write missionListener fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::REGISTER_MISSION_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RegisterSessionHandler(const sptr<IRemoteObject> &object)
{
    if (!object) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "handler null");
        return ERR_INVALID_VALUE;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(object)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write sessionHandler fail");
        return ERR_INVALID_VALUE;
    }
    int error = SendRequest(AbilityManagerInterfaceCode::REGISTER_SESSION_HANDLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RegisterMissionListener(const std::string &deviceId,
    const sptr<IRemoteMissionListener> &listener)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(deviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_REMOTE_MISSION_LISTENER,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RegisterOnListener(const std::string &type,
    const sptr<IRemoteOnListener> &listener)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_REMOTE_ON_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RegisterOffListener(const std::string &type,
    const sptr<IRemoteOnListener> &listener)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_REMOTE_OFF_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::UnRegisterMissionListener(const sptr<IMissionListener> &listener)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!listener) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener null");
        return ERR_INVALID_VALUE;
    }

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write missionListener fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_MISSION_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetMissionInfos(const std::string& deviceId, int32_t numMax,
    std::vector<MissionInfo> &missionInfos)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString16(Str8ToStr16(deviceId))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write deviceId fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(numMax)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::GET_MISSION_INFOS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, " request error:%{public}d", error);
        return error;
    }
    error = GetParcelableInfos<MissionInfo>(reply, missionInfos);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getMissionInfos error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetMissionInfo(const std::string& deviceId, int32_t missionId,
    MissionInfo &missionInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString16(Str8ToStr16(deviceId))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write deviceId failed");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 failed");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::GET_MISSION_INFO_BY_ID, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    std::unique_ptr<MissionInfo> info(reply.ReadParcelable<MissionInfo>());
    if (!info) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read missioninfo fail");
        return ERR_UNKNOWN_OBJECT;
    }
    missionInfo = *info;
    return reply.ReadInt32();
}

int AbilityManagerProxy::CleanMission(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::CLEAN_MISSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "clean mission, error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::CleanAllMissions()
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::CLEAN_ALL_MISSIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MoveMissionToFront(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return ERR_INVALID_VALUE;
    }
    error = SendRequest(AbilityManagerInterfaceCode::MOVE_MISSION_TO_FRONT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MoveMissionToFront(int32_t missionId, const StartOptions &startOptions)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt32 fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(&startOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startOptions write fail");
        return INNER_ERR;
    }
    error = SendRequest(AbilityManagerInterfaceCode::MOVE_MISSION_TO_FRONT_BY_OPTIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::MoveMissionsToForeground(const std::vector<int32_t>& missionIds, int32_t topMissionId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteInt32Vector(missionIds)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionIds write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(topMissionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "topMissionId write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::MOVE_MISSIONS_TO_FOREGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::MoveMissionsToBackground(const std::vector<int32_t>& missionIds, std::vector<int32_t>& result)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteInt32Vector(missionIds)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "mission id write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::MOVE_MISSIONS_TO_BACKGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    if (!reply.ReadInt32Vector(&result)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read result fail");
        return INNER_ERR;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartUser(int userId, uint64_t displayId, sptr<IUserCallback> callback, bool isAppRecovery)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteUint64(displayId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write displayId failed");
        return IPC_PROXY_ERR;
    }
    if (!callback) {
        data.WriteBool(false);
    } else {
        data.WriteBool(true);
        if (!data.WriteRemoteObject(callback->AsObject())) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write IUserCallback fail");
            return ERR_INVALID_VALUE;
        }
    }
    if (!data.WriteBool(isAppRecovery)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write isAppRecovery fail");
        return IPC_PROXY_ERR;
    }
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);
    auto error = SendRequest(AbilityManagerInterfaceCode::START_USER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::SetMissionContinueState(const sptr<IRemoteObject> &token, const AAFwk::ContinueState &state)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(static_cast<int32_t>(state))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write state fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SET_MISSION_CONTINUE_STATE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StopUser(int userId, const sptr<IUserCallback> &callback)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "fail");
        return ERR_INVALID_VALUE;
    }

    if (!callback) {
        data.WriteBool(false);
    } else {
        data.WriteBool(true);
        if (!data.WriteRemoteObject(callback->AsObject())) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write IUserCallback fail");
            return ERR_INVALID_VALUE;
        }
    }
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);
    auto error = SendRequest(AbilityManagerInterfaceCode::STOP_USER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::LogoutUser(int32_t userId, sptr<IUserCallback> callback)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "fail");
        return ERR_INVALID_VALUE;
    }
    if (callback == nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "callback is nullptr");
        data.WriteBool(false);
    } else {
        data.WriteBool(true);
        if (!data.WriteRemoteObject(callback->AsObject())) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write IUserCallback fail");
            return ERR_INVALID_VALUE;
        }
    }
    int error = SendRequest(AbilityManagerInterfaceCode::LOGOUT_USER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

#ifdef SUPPORT_SCREEN
int AbilityManagerProxy::SetMissionLabel(const sptr<IRemoteObject> &token, const std::string &label)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString16(Str8ToStr16(label))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write label fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SET_MISSION_LABEL, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::SetMissionIcon(const sptr<IRemoteObject> &token,
    const std::shared_ptr<OHOS::Media::PixelMap> &icon)
{
    if (!token || !icon) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilitytoken or icon invalid");
        return ERR_INVALID_VALUE;
    }

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteParcelable(icon.get())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write icon fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::SET_MISSION_ICON, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::RegisterWindowManagerServiceHandler(const sptr<IWindowManagerServiceHandler>& handler,
    bool animationEnabled)
{
    if (!handler) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: handler null", __func__);
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: writeInterfaceToken failed", __func__);
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(handler->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: handler write fail", __func__);
        return INNER_ERR;
    }
    if (!data.WriteBool(animationEnabled)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write animationEnabled fail");
        return ERR_INVALID_VALUE;
    }
    MessageOption option;
    MessageParcel reply;
    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_WMS_HANDLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s:request error:%{public}d", __func__, error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::CompleteFirstFrameDrawing(const sptr<IRemoteObject> &abilityToken)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: writeInterfaceToken fail", __func__);
        return;
    }
    if (!data.WriteRemoteObject(abilityToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: abilityToken write fail", __func__);
        return;
    }
    MessageOption option;
    MessageParcel reply;
    auto error = SendRequest(AbilityManagerInterfaceCode::COMPLETEFIRSTFRAMEDRAWING, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: request error:%{public}d", __func__, error);
    }
}

int AbilityManagerProxy::PrepareTerminateAbility(const sptr<IRemoteObject> &token,
    sptr<IPrepareTerminateCallback> &callback)
{
    if (!callback) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callback null");
        return INNER_ERR;
    }
    int error = 0;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteRemoteObject(callback->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite callback fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::PREPARE_TERMINATE_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::GetDialogSessionInfo(const std::string &dialogSessionId, sptr<DialogSessionInfo> &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write interface fail");
        return INNER_ERR;
    }
    if (!data.WriteString(dialogSessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write dialogSessionId fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_DIALOG_SESSION_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    info = reply.ReadParcelable<DialogSessionInfo>();
    if (!info) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "readParcelable fail");
        return ERR_UNKNOWN_OBJECT;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::SendDialogResult(const Want &want, const std::string &dialogSessionId, const bool isAllow)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString(dialogSessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write dialogSessionId fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteBool(isAllow)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write dialogSessionId fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SEND_DIALOG_RESULT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RegisterAbilityFirstFrameStateObserver(
    const sptr<IAbilityFirstFrameStateObserver> &observer, const std::string &targetBundleName)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (observer == nullptr || !data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer null or write remote fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString(targetBundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write target bundleName fail");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::REGISTER_ABILITY_FIRST_FRAME_STATE_OBSERVER,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UnregisterAbilityFirstFrameStateObserver(
    const sptr<IAbilityFirstFrameStateObserver> &observer)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write Token fail");
        return INNER_ERR;
    }
    if (observer == nullptr || !data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer null or write remote fail");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret =
        SendRequest(AbilityManagerInterfaceCode::UNREGISTER_ABILITY_FIRST_FRAME_STATE_OBSERVER, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::CompleteFirstFrameDrawing(int32_t sessionId)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return;
    }
    if (!data.WriteInt32(sessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionId write failed");
        return;
    }
    MessageOption option;
    MessageParcel reply;
    auto error = SendRequest(AbilityManagerInterfaceCode::COMPLETE_FIRST_FRAME_DRAWING_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }
}
#endif

int AbilityManagerProxy::GetAbilityRunningInfos(std::vector<AbilityRunningInfo> &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_ABILITY_RUNNING_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    error = GetParcelableInfos<AbilityRunningInfo>(reply, info);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getParcelableInfos fail, error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetExtensionRunningInfos(int upperLimit, std::vector<ExtensionRunningInfo> &info)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start GetExtensionRunningInfos");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteInt32(upperLimit)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "upperLimit write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_EXTENSION_RUNNING_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    error = GetParcelableInfos<ExtensionRunningInfo>(reply, info);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getParcelableInfos fail, error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetProcessRunningInfos(std::vector<AppExecFwk::RunningProcessInfo> &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_PROCESS_RUNNING_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request, error:%{public}d", error);
        return error;
    }
    error = GetParcelableInfos<AppExecFwk::RunningProcessInfo>(reply, info);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getParcelable error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetAllIntentExemptionInfo(std::vector<AppExecFwk::IntentExemptionInfo> &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_INTENT_EXEMPTION_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request, error:%{public}d", error);
        return error;
    }
    error = GetParcelableInfos<AppExecFwk::IntentExemptionInfo>(reply, info);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getParcelable error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartSyncRemoteMissions(const std::string& devId, bool fixConflict, int64_t tag)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString(devId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write deviceId fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(fixConflict)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeBool fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt64(tag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInt64 fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_SYNC_MISSIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StopSyncRemoteMissions(const std::string& devId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString(devId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write deviceId fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::STOP_SYNC_MISSIONS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::UnRegisterMissionListener(const std::string &deviceId,
    const sptr<IRemoteMissionListener> &listener)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(deviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "listener write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_REMOTE_MISSION_LISTENER,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityByCall(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<IRemoteObject> &callerToken, int32_t accountId, bool isSilent, bool promotePriority, bool isVisible)
{
    std::string errMsg;
    return StartAbilityByCallWithErrMsg(want, connect, callerToken, accountId, errMsg, isSilent, promotePriority,
        isVisible);
}

int AbilityManagerProxy::StartAbilityByCallWithErrMsg(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<IRemoteObject> &callerToken, int32_t accountId, std::string &errMsg, bool isSilent,
    bool promotePriority, bool isVisible)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "AbilityManagerProxy::StartAbilityByCall begin.");
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        errMsg = "WriteInterfaceToken error";
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        errMsg = "want write fail";
        return ERR_INVALID_VALUE;
    }
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "resolve fail, null connect");
        errMsg = "null connect";
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteRemoteObject(connect->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "resolve write fail");
        errMsg = "resolve write fail";
        return ERR_INVALID_VALUE;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and callerToken failed");
            errMsg = "callerToken write fail";
            return ERR_INVALID_VALUE;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag failed");
            errMsg = "write flag failed";
            return ERR_INVALID_VALUE;
        }
    }
    if (!data.WriteInt32(accountId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "accountId write fail");
        errMsg = "accountId write fail";
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(isSilent)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isSilent write fail");
        errMsg = "isSilent write fail";
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(promotePriority)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "promotePriority write fail");
        errMsg = "promotePriority write fail";
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(isVisible)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isVisible write fail");
        errMsg = "isVisible write fail";
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::START_CALL_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "AbilityManagerProxy::StartAbilityByCall end.");
    errMsg = reply.ReadString();
    return reply.ReadInt32();
}

int AbilityManagerProxy::StartAbilityForPrelaunch(const Want &want, const int32_t frameNum)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "AbilityManagerProxy::StartAbilityForPrelaunch begin.");
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "WriteInterfaceToken error");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt32(frameNum)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "frameNum write fail");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::START_PRELAUNCH_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "AbilityManagerProxy::StartAbilityForPrelaunch end.");
    return reply.ReadInt32();
}

void AbilityManagerProxy::CallRequestDone(const sptr<IRemoteObject> &token, const sptr<IRemoteObject> &callStub)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail, null token ");
        return;
    }
    if (callStub == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail, null callStub");
        return;
    }

    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail, write token fail");
        return;
    }
    if (!data.WriteRemoteObject(callStub)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail, write callStub fail");
        return;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::CALL_REQUEST_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
}

int AbilityManagerProxy::ReleaseCall(
    const sptr<IAbilityConnection> &connect, const AppExecFwk::ElementName &element)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "release fail, null connect");
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(connect->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "release connect write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(&element)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "element error");
        return ERR_INVALID_VALUE;
    }

    error = SendRequest(AbilityManagerInterfaceCode::RELEASE_CALL_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::GetAbilityTokenByCalleeObj(const sptr<IRemoteObject> &callStub, sptr<IRemoteObject> &token)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return;
    }
    if (!data.WriteRemoteObject(callStub)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeRemoteObject fail, write callStub fail");
        return;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_ABILITY_TOKEN, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    token = sptr<IRemoteObject>(reply.ReadRemoteObject());
}

int AbilityManagerProxy::RegisterSnapshotHandler(const sptr<ISnapshotHandler>& handler)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(handler->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "handler write failed");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_SNAPSHOT_HANDLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::SetAbilityController(const sptr<AppExecFwk::IAbilityController> &abilityController,
    bool imAStabilityTest)
{
    if (!abilityController) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null abilityController");
        return ERR_INVALID_VALUE;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(abilityController->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityController write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteBool(imAStabilityTest)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "imAStabilityTest write fail");
        return ERR_INVALID_VALUE;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::SET_ABILITY_CONTROLLER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

bool AbilityManagerProxy::IsRunningInStabilityTest()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return false;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::IS_USER_A_STABILITY_TEST, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return false;
    }
    return reply.ReadBool();
}

int AbilityManagerProxy::StartUserTest(const Want &want, const sptr<IRemoteObject> &observer)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(observer)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::START_USER_TEST, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::FinishUserTest(
    const std::string &msg, const int64_t &resultCode, const std::string &bundleName)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteString(msg)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "msg write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteInt64(resultCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "resultCode write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "bundleName write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::FINISH_USER_TEST, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::GetTopAbility(sptr<IRemoteObject> &token)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_TOP_ABILITY_TOKEN, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    token = sptr<IRemoteObject>(reply.ReadRemoteObject());
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read IRemoteObject fail");
        return ERR_UNKNOWN_OBJECT;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::CheckUIExtensionIsFocused(uint32_t uiExtensionTokenId, bool& isFocused, uint64_t displayId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteUint32(uiExtensionTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uiExtensionTokenId write fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteUint64(displayId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "displayId write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::CHECK_UI_EXTENSION_IS_FOCUSED, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    isFocused = reply.ReadBool();
    return NO_ERROR;
}

int AbilityManagerProxy::DelegatorDoAbilityForeground(const sptr<IRemoteObject> &token)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::DELEGATOR_DO_ABILITY_FOREGROUND,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::DelegatorDoAbilityBackground(const sptr<IRemoteObject> &token)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::DELEGATOR_DO_ABILITY_BACKGROUND,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::DoAbilityForeground(const sptr<IRemoteObject> &token, uint32_t flag)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteUint32(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::DO_ABILITY_FOREGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::DoAbilityBackground(const sptr<IRemoteObject> &token, uint32_t flag)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteUint32(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
        return ERR_INVALID_VALUE;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::DO_ABILITY_BACKGROUND, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetMissionIdByToken(const sptr<IRemoteObject> &token)
{
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return -1;
    }

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return -1;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "data write fail");
        return -1;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_MISSION_ID_BY_ABILITY_TOKEN,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return -1;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::FreeInstallAbilityFromRemote(const Want &want, const sptr<IRemoteObject> &callback,
    int32_t userId, int requestCode)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callback)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callback write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::FREE_INSTALL_ABILITY_FROM_REMOTE,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int AbilityManagerProxy::AddFreeInstallObserver(const sptr<IRemoteObject> &callerToken,
    const sptr<AbilityRuntime::IFreeInstallObserver> &observer)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (observer == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null observer");
        return INNER_ERR;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and callerToken fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
            return INNER_ERR;
        }
    }

    if (!data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::ADD_FREE_INSTALL_OBSERVER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::DumpAbilityInfoDone(std::vector<std::string> &infos, const sptr<IRemoteObject> &callerToken)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteStringVector(infos)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "infos write fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "infos write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::DUMP_ABILITY_INFO_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::IsValidMissionIds(
    const std::vector<int32_t> &missionIds, std::vector<MissionValidResult> &results)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call, quert size:%{public}zu", missionIds.size());
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    constexpr int32_t MAX_COUNT = 20;
    int32_t num = static_cast<int32_t>(missionIds.size() > MAX_COUNT ? MAX_COUNT : missionIds.size());
    if (!data.WriteInt32(num)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write num fail");
        return INNER_ERR;
    }
    for (auto i = 0; i < num; ++i) {
        if (!data.WriteInt32(missionIds.at(i))) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write missionId fail");
            return INNER_ERR;
        }
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::QUERY_MISSION_VAILD, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    auto resultCode = reply.ReadInt32();
    if (resultCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", resultCode);
        return resultCode;
    }

    auto infoSize = reply.ReadInt32();
    for (auto i = 0; i < infoSize && i < MAX_COUNT; ++i) {
        std::unique_ptr<MissionValidResult> info(reply.ReadParcelable<MissionValidResult>());
        if (!info) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "read result fail");
            return INNER_ERR;
        }
        results.emplace_back(*info);
    }

    return resultCode;
}

int AbilityManagerProxy::VerifyPermission(const std::string &permission, int pid, int uid)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteString(permission)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(pid)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pid write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(uid)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uid write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::VERIFY_PERMISSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RequestDialogService(const Want &want, const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
    if (!callerToken) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken invalid");
        return ERR_INVALID_CALLER;
    }

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "infos write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REQUEST_DIALOG_SERVICE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ReportDrawnCompleted(const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INNER_ERR;
    }

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REPORT_DRAWN_COMPLETED, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::AcquireShareData(
    const int32_t &missionId, const sptr<IAcquireShareDataCallback> &shareData)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId write fail");
        return INNER_ERR;
    }

    if (shareData == nullptr || !data.WriteRemoteObject(shareData->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "shareData write fail");
        return INNER_ERR;
    }

    int32_t error = SendRequest(AbilityManagerInterfaceCode::ACQUIRE_SHARE_DATA, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", error);
        return INNER_ERR;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "end");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ShareDataDone(
    const sptr<IRemoteObject> &token, const int32_t &resultCode, const int32_t &uniqueId, WantParams &wantParam)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(resultCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(uniqueId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uniqueId write fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&wantParam)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "wantParam write fail");
        return INNER_ERR;
    }

    int32_t error = SendRequest(AbilityManagerInterfaceCode::SHARE_DATA_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err: %{public}d", error);
        return error;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "end");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ForceExitApp(const int32_t pid, const ExitReason &exitReason)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start.");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, pid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &exitReason);

    int32_t error = SendRequest(AbilityManagerInterfaceCode::FORCE_EXIT_APP, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "end.");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RecordAppExitReason(const ExitReason &exitReason)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start.");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write interface token fail");
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &exitReason);

    int32_t error = SendRequest(AbilityManagerInterfaceCode::RECORD_APP_EXIT_REASON, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "end.");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RecordProcessExitReason(const int32_t pid, const ExitReason &exitReason)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start.");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, pid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &exitReason);

    int32_t error = SendRequest(AbilityManagerInterfaceCode::RECORD_PROCESS_EXIT_REASON, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "end.");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RecordProcessExitReason(int32_t pid, int32_t uid, const ExitReason &exitReason)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start.");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, pid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, uid);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &exitReason);

    int32_t error = SendRequest(AbilityManagerInterfaceCode::RECORD_PROCESS_EXIT_REASON_PLUS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "end.");
    return reply.ReadInt32();
}

void AbilityManagerProxy::SetRootSceneSession(const sptr<IRemoteObject> &rootSceneSession)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return;
    }
    if (!data.WriteRemoteObject(rootSceneSession)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail");
        return;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);
    auto error = SendRequest(AbilityManagerInterfaceCode::SET_ROOT_SCENE_SESSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }
}

void AbilityManagerProxy::CallUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo,
    AbilityRuntime::StartParamsBySCB &params, bool &isColdStart)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return;
    }
    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return;
        }
    }
    if (!data.WriteParcelable(&params)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "params write fail");
        return;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::CALL_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return;
    }
    isColdStart = reply.ReadBool();
}

int32_t AbilityManagerProxy::StartSpecifiedAbilityBySCB(const Want &want, const StartSpecifiedAbilityParams &params)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }

    if (!data.WriteParcelable(&params)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "params write fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    auto error = SendRequest(AbilityManagerInterfaceCode::START_SPECIFIED_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::NotifySaveAsResult(const Want &want, int resultCode, int requestCode)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeWantObject fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(resultCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "resultCode write fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::NOTIFY_SAVE_AS_RESULT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetSessionManagerService(const sptr<IRemoteObject> &sessionManagerService)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(sessionManagerService)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token write fail");
        return INNER_ERR;
    }

    int32_t error = SendRequest(AbilityManagerInterfaceCode::SET_SESSIONMANAGERSERVICE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "end");
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RegisterIAbilityManagerCollaborator(
    int32_t type, const sptr<IAbilityManagerCollaborator> &impl)
{
    if (!impl) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null impl");
        return ERR_INVALID_VALUE;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(impl->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "impl write fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::REGISTER_COLLABORATOR, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UnregisterIAbilityManagerCollaborator(int32_t type)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type write fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_COLLABORATOR, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

sptr<IAbilityManagerCollaborator> AbilityManagerProxy::GetAbilityManagerCollaborator()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return nullptr;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::GET_ABILITY_MANAGER_COLLABORATOR, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return nullptr;
    }
    auto remoteObj = reply.ReadRemoteObject();
    if (!remoteObj) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "remote object null");
        return nullptr;
    }
    sptr<IAbilityManagerCollaborator> collaborator = iface_cast<IAbilityManagerCollaborator>(remoteObj);
    return collaborator;
}

int32_t AbilityManagerProxy::RegisterStatusBarDelegate(sptr<AbilityRuntime::IStatusBarDelegate> delegate)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (delegate == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null delegate");
        return ERR_NULL_OBJECT;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteRemoteObject(delegate->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write delegate fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::REGISTER_STATUS_BAR_DELEGATE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::KillProcessWithPrepareTerminate(const std::vector<int32_t> &pids, bool clear)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteUint32(pids.size())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write size fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    for (const auto &pid : pids) {
        if (!data.WriteInt32(pid)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write pid fail");
            return ERR_NATIVE_IPC_PARCEL_FAILED;
        }
    }
    if (!data.WriteBool(clear)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write clear fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::KILL_PROCESS_WITH_PREPARE_TERMINATE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
    }
    return ret;
}

int32_t AbilityManagerProxy::KillProcessWithReason(int32_t pid, const ExitReason &reason)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::APPMGR, "Write token failed");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteInt32(pid)) {
        TAG_LOGE(AAFwkTag::APPMGR, "parcel pid failed");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteParcelable(&reason)) {
        TAG_LOGE(AAFwkTag::APPMGR, "Write reason failed");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    int32_t ret =
        SendRequest(AbilityManagerInterfaceCode::KILL_PROCESS_WITH_REASON, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGW(AAFwkTag::APPMGR, "SendRequest err: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RegisterAutoStartupSystemCallback(const sptr<IRemoteObject> &callback)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callback)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callback write fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::REGISTER_AUTO_STARTUP_SYSTEM_CALLBACK, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UnregisterAutoStartupSystemCallback(const sptr<IRemoteObject> &callback)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callback)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callback write fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_AUTO_STARTUP_SYSTEM_CALLBACK, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetApplicationAutoStartup(const AutoStartupInfo &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&info)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write autoStartupInfo fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_APPLICATION_AUTO_STARTUP, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::CancelApplicationAutoStartup(const AutoStartupInfo &info)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&info)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write autoStartupInfo fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::CANCEL_APPLICATION_AUTO_STARTUP, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryAllAutoStartupApplications(std::vector<AutoStartupInfo> &infoList)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::QUERY_ALL_AUTO_STARTUP_APPLICATION, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send request error:%{public}d", ret);
        return ret;
    }

    auto resultCode = reply.ReadInt32();
    if (resultCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "reply error:%{public}d", resultCode);
        return resultCode;
    }

    auto infoSize = reply.ReadInt32();
    for (auto i = 0; i < infoSize && i < MAX_AUTO_STARTUP_COUNT; ++i) {
        std::unique_ptr<AutoStartupInfo> info(reply.ReadParcelable<AutoStartupInfo>());
        if (!info) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "read result fail");
            return INNER_ERR;
        }
        infoList.emplace_back(*info);
    }
    return ERR_OK;
}

int32_t AbilityManagerProxy::GetAutoStartupStatusForSelf(bool &isAutoStartEnabled)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::GET_AUTO_STARTUP_STATUS_FOR_SELF, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send request error:%{public}d", ret);
        return ret;
    }
    isAutoStartEnabled = reply.ReadBool();
    return NO_ERROR;
}

int32_t AbilityManagerProxy::ManualStartAutoStartupApps(int32_t userId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userId fail");
        return ERR_WRITE_INT32_FAILED;
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::MANUAL_START_AUTO_STARTUP_APPS, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int AbilityManagerProxy::PrepareTerminateAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool &isPrepareTerminate)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and sessionInfo write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::PREPARE_TERMINATE_ABILITY_BY_SCB,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    isPrepareTerminate = reply.ReadBool();
    return NO_ERROR;
}

int32_t AbilityManagerProxy::RegisterAppDebugListener(sptr<AppExecFwk::IAppDebugListener> listener)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (listener == nullptr || !data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write listener fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    int32_t error = SendRequest(AbilityManagerInterfaceCode::REGISTER_APP_DEBUG_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UnregisterAppDebugListener(sptr<AppExecFwk::IAppDebugListener> listener)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (listener == nullptr || !data.WriteRemoteObject(listener->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write listener fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    int32_t error = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_APP_DEBUG_LISTENER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::AttachAppDebug(const std::string &bundleName, bool isDebugFromLocal)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "bundleName write fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(isDebugFromLocal)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isDebugFromLocal write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    int32_t error = SendRequest(AbilityManagerInterfaceCode::ATTACH_APP_DEBUG, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::DetachAppDebug(const std::string &bundleName, bool isDebugFromLocal)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write bundleName fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(isDebugFromLocal)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isDebugFromLocal write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    int32_t error = SendRequest(AbilityManagerInterfaceCode::DETACH_APP_DEBUG, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ExecuteIntent(uint64_t key,  const sptr<IRemoteObject> &callerToken,
    const InsightIntentExecuteParam &param)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteUint64(key)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write key fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken failed.");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&param)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write param fail");
        return INNER_ERR;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "send execute intent.");
    int32_t error = SendRequest(AbilityManagerInterfaceCode::EXECUTE_INTENT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

bool AbilityManagerProxy::IsAbilityControllerStart(const Want &want)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return true;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeWantObject fail");
        return true;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::IS_ABILITY_CONTROLLER_START,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return true;
    }
    return reply.ReadBool();
}

int32_t AbilityManagerProxy::ExecuteInsightIntentDone(const sptr<IRemoteObject> &token, uint64_t intentId,
    const InsightIntentExecuteResult &result)
{
    TAG_LOGI(AAFwkTag::INTENT, "execute insight intent done proxy, intentId:%{public}" PRIu64"", intentId);
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteInt64(intentId) || !data.WriteParcelable(&result)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write params fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);
    auto ret = SendRequest(AbilityManagerInterfaceCode::EXECUTE_INSIGHT_INTENT_DONE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetForegroundUIAbilities(std::vector<AppExecFwk::AbilityStateData> &list)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return ERR_FLATTEN_OBJECT;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_FOREGROUND_UI_ABILITIES, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    auto errorCode = GetParcelableInfos<AppExecFwk::AbilityStateData>(reply, list);
    if (errorCode != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get abilities error:%{public}d", errorCode);
        return errorCode;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::OpenFile(const Uri& uri, uint32_t flag)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return false;
    }
    if (!data.WriteParcelable(&uri)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write uri fail");
        return false;
    }
    if (!data.WriteInt32(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
        return false;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::OPEN_FILE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail:%{public}d", ret);
        return ret;
    }
    return reply.ReadFileDescriptor();
}

int32_t AbilityManagerProxy::RequestAssertFaultDialog(
    const sptr<IRemoteObject> &callback, const AAFwk::WantParams &wantParams)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Request to display assert fault dialog.");
    if (callback == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callback");
        return INNER_ERR;
    }

    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callback)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callback fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&wantParams)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "wantParams write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::REQUEST_ASSERT_FAULT_DIALOG, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail:%{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::NotifyDebugAssertResult(uint64_t assertFaultSessionId, AAFwk::UserStatus userStatus)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Notify user action result to assert fault callback.");
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteUint64(assertFaultSessionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write assertFaultSessionId fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(static_cast<int32_t>(userStatus))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userStatus fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::NOTIFY_DEBUG_ASSERT_RESULT, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail:%{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UpdateSessionInfoBySCB(std::list<SessionInfo> &sessionInfos, int32_t userId,
    std::vector<int32_t> &sessionIds)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    auto size = static_cast<int32_t>(sessionInfos.size());
    int32_t threshold = 512;
    if (size > threshold) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "vector too large");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    if (!data.WriteInt32(size)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write size fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    for (const auto &info : sessionInfos) {
        if (!data.WriteParcelable(&info)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write sessionInfo fail");
            return ERR_NATIVE_IPC_PARCEL_FAILED;
        }
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userId fail");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::UPDATE_SESSION_INFO, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request fail:%{public}d", ret);
        return ret;
    }
    size = reply.ReadInt32();
    if (size > threshold) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "vector too large");
        return ERR_NATIVE_IPC_PARCEL_FAILED;
    }
    sessionIds.clear();
    for (auto index = 0; index < size; index++) {
        sessionIds.emplace_back(reply.ReadInt32());
    }
    return NO_ERROR;
}

ErrCode AbilityManagerProxy::SendRequest(AbilityManagerInterfaceCode code, MessageParcel &data, MessageParcel &reply,
    MessageOption& option)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    sptr<IRemoteObject> remote = Remote();
    if (remote == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null remote");
        return INNER_ERR;
    }

    return remote->SendRequest(static_cast<uint32_t>(code), data, reply, option);
}

int32_t AbilityManagerProxy::SetApplicationAutoStartupByEDM(const AutoStartupInfo &info, bool flag)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&info)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write AutoStartupInfo fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_APPLICATION_AUTO_STARTUP_BY_EDM, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::CancelApplicationAutoStartupByEDM(const AutoStartupInfo &info, bool flag)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&info)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write info fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::CANCEL_APPLICATION_AUTO_STARTUP_BY_EDM, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RestartApp(const AAFwk::Want &want, bool isAppRecovery)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return IPC_PROXY_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return IPC_PROXY_ERR;
    }
    if (!data.WriteBool(isAppRecovery)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write isAppRecovery fail");
        return IPC_PROXY_ERR;
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::RESTART_APP, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetUIExtensionRootHostInfo(const sptr<IRemoteObject> token,
    UIExtensionHostInfo &hostInfo, int32_t userId)
{
    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "input invalid");
        return ERR_INVALID_VALUE;
    }

    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and token fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userId fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_UI_EXTENSION_ROOT_HOST_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    std::unique_ptr<UIExtensionHostInfo> info(reply.ReadParcelable<UIExtensionHostInfo>());
    if (info == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get host fail");
        return INNER_ERR;
    }
    hostInfo = *info;
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetUIExtensionSessionInfo(const sptr<IRemoteObject> token,
    UIExtensionSessionInfo &uiExtensionSessionInfo, int32_t userId)
{
    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "input invalid");
        return ERR_INVALID_VALUE;
    }

    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write object fail");
        return INNER_ERR;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and token fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userId fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_UI_EXTENSION_SESSION_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    std::unique_ptr<UIExtensionSessionInfo> info(reply.ReadParcelable<UIExtensionSessionInfo>());
    if (info == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get host info fail");
        return INNER_ERR;
    }
    uiExtensionSessionInfo = *info;
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::OpenAtomicService(Want& want, const StartOptions &options,
    sptr<IRemoteObject> callerToken, int32_t requestCode, int32_t userId)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&options)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "options write fail");
        return INNER_ERR;
    }
    if (callerToken != nullptr) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag and callerToken write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::OPEN_ATOMIC_SERVICE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetResidentProcessEnabled(const std::string &bundleName, bool enable)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write bundleName fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(enable)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write enable fail");
        return INNER_ERR;
    }
    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_RESIDENT_PROCESS_ENABLE, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

bool AbilityManagerProxy::IsEmbeddedOpenAllowed(sptr<IRemoteObject> callerToken, const std::string &appId)
{
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "input invalid");
        return false;
    }

    MessageParcel data;
    if (!WriteInterfaceToken (data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write remote object fail");
        return false;
    }

    if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag and callerToken fail");
        return false;
    }

    if (!data.WriteString(appId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write userId fail");
        return false;
    }

    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::IS_EMBEDDED_OPEN_ALLOWED, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return false;
    }
    return reply.ReadBool();
}

int32_t AbilityManagerProxy::StartShortcut(const Want &want, const StartOptions &startOptions)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&startOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startOptions write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_SHORTCUT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetAbilityStateByPersistentId(int32_t persistentId, bool &state)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteInt32(persistentId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write failed");
        return IPC_PROXY_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::GET_ABILITY_STATE_BY_PERSISTENT_ID, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    state = reply.ReadBool();
    return NO_ERROR;
}


int32_t AbilityManagerProxy::TransferAbilityResultForExtension(const sptr<IRemoteObject> &callerToken,
    int32_t resultCode, const Want &want)
{
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteRemoteObject(callerToken) || !data.WriteInt32(resultCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken or resultCode write fail");
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::TRANSFER_ABILITY_RESULT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return NO_ERROR;
}

void AbilityManagerProxy::NotifyFrozenProcessByRSS(const std::vector<int32_t> &pidList, int32_t uid)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start NotifyFrozenProcessByRSS");
        return;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_ASYNC);

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return;
    }
    if (!data.WriteInt32Vector(pidList)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "list write fail");
        return;
    }
    if (!data.WriteInt32(uid)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uid write fail");
        return;
    }

    int error = SendRequest(AbilityManagerInterfaceCode::NOTIFY_FROZEN_PROCESS_BY_RSS, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request err %{public}d", error);
    }
}

int AbilityManagerProxy::CleanUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool isUserRequestedExit,
    uint32_t sceneFlag)
{
    int error;
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }

    if (sessionInfo) {
        ExtendMaxIpcCapacityForWant(sessionInfo->want, data);
        if (!data.WriteBool(true) || !data.WriteParcelable(sessionInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag or sessionInfo fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteBool(isUserRequestedExit)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write isUserRequestedExit fail");
        return ERR_IPC_PROXY_WRITE_FAILED;
    }
    if (!data.WriteUint32(sceneFlag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sceneFlag write fail");
        return INNER_ERR;
    }

    error = SendRequest(AbilityManagerInterfaceCode::CLEAN_UI_ABILITY_BY_SCB, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::PreStartMission(const std::string& bundleName, const std::string& moduleName,
    const std::string& abilityName, const std::string& startTime)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write bundleName fail");
        return INNER_ERR;
    }
    if (!data.WriteString(moduleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write moduleName fail");
        return INNER_ERR;
    }
    if (!data.WriteString(abilityName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write abilityName fail");
        return INNER_ERR;
    }
    if (!data.WriteString(startTime)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write startTime fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::PRE_START_MISSION, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

ErrCode AbilityManagerProxy::OpenLink(const Want &want, sptr<IRemoteObject> callerToken,
    int32_t userId, int requestCode, bool hideFailureTipDialog)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "userId write fail");
        return INNER_ERR;
    }
    if (!data.WriteInt32(requestCode)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestCode write fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(hideFailureTipDialog)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "hideFailureTipDialog write failed.");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::OPEN_LINK, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::TerminateMission(int32_t missionId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteInt32(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appCloneIndex write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::TERMINATE_MISSION,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::BlockAllAppStart(bool flag)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }
    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag failed.");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::BLOCK_ALL_APP_START,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Send request error: %{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UpdateAssociateConfigList(const std::map<std::string, std::list<std::string>>& configs,
    const std::list<std::string>& exportConfigs, int32_t flag)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return IPC_PROXY_ERR;
    }

    if (!UpdateAssociateConfigInner(configs, data)) {
        return INNER_ERR;
    }

    int32_t size = static_cast<int32_t>(exportConfigs.size());
    if (size > MAX_UPDATE_CONFIG_SIZE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "export configs size too large");
        return INNER_ERR;
    }
    if (!data.WriteInt32(size)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write export configs size fail");
        return INNER_ERR;
    }
    for (const auto& config : exportConfigs) {
        if (!data.WriteString(config)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write export config item fail");
            return INNER_ERR;
        }
    }
    if (!data.WriteInt32(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write flag fail");
        return INNER_ERR;
    }
    auto error = SendRequest(AbilityManagerInterfaceCode::UPDATE_ASSOCIATE_CONFIG_LIST, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

bool AbilityManagerProxy::UpdateAssociateConfigInner(const std::map<std::string, std::list<std::string>>& configs,
    MessageParcel& data)
{
    int32_t size = static_cast<int32_t>(configs.size());
    if (size > MAX_UPDATE_CONFIG_SIZE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "configs size too large");
        return false;
    }
    if (!data.WriteInt32(size)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write configs size fail");
        return false;
    }
    for (const auto& config : configs) {
        if (!data.WriteString(config.first)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write config key fail");
            return false;
        }
        size = static_cast<int32_t>(config.second.size());
        if (size > MAX_UPDATE_CONFIG_SIZE) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "config size too large");
            return false;
        }
        if (!data.WriteInt32(size)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write config item size fail");
            return false;
        }
        for (const auto& item : config.second) {
            if (!data.WriteString(item)) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "write config item fail");
                return false;
            }
        }
    }
    return true;
}

int32_t AbilityManagerProxy::SetApplicationKeepAlive(const std::string &bundleName, int32_t userId, bool flag)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write bundleName");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write userID");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write flag");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_APPLICATION_KEEP_ALLIVE,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryKeepAliveApplications(int32_t appType, int32_t userId,
    std::vector<KeepAliveInfo> &list)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(appType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write appType");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write userID");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::GET_APPLICATIONS_KEEP_ALIVE,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }

    ret = GetParcelableInfos<KeepAliveInfo>(reply, list);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "GetParcelableInfos error: %{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetApplicationKeepAliveByEDM(const std::string &bundleName, int32_t userId,
    bool flag, bool isAllowUserToCancel)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write bundleName");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write userID");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write flag");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(isAllowUserToCancel)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write isAllowUserToCancel");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_APPLICATION_KEEP_ALLIVE_BY_EDM,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryKeepAliveApplicationsByEDM(int32_t appType, int32_t userId,
    std::vector<KeepAliveInfo> &list)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(appType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write appType");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write userID");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::GET_APPLICATIONS_KEEP_ALIVE_BY_EDM,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }

    ret = GetParcelableInfos<KeepAliveInfo>(reply, list);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "GetParcelableInfos error: %{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::AddQueryERMSObserver(sptr<IRemoteObject> callerToken,
    sptr<AbilityRuntime::IQueryERMSObserver> observer)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return ERR_INVALID_VALUE;
    }

    if (observer == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null observer");
        return ERR_INVALID_VALUE;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer write fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::ADD_QUERY_ERMS_OBSERVER, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryAtomicServiceStartupRule(sptr<IRemoteObject> callerToken,
    const std::string &appId, const std::string &startTime, AtomicServiceStartupRule &rule)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return ERR_INVALID_VALUE;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return INNER_ERR;
    }

    if (!data.WriteString(appId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write appId fail");
        return INNER_ERR;
    }

    if (!data.WriteString(startTime)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write startTime fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::QUERY_ATOMIC_SERVICE_STARTUP_RULE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    rule.isOpenAllowed = reply.ReadBool();
    rule.isEmbeddedAllowed = reply.ReadBool();
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartSelfUIAbility(const Want &want)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return INNER_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::NDK_START_SELF_UI_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartSelfUIAbilityWithStartOptions(const Want &want, const StartOptions &options)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_CODE;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return ERR_WRITE_WANT;
    }

    if (!data.WriteParcelable(&options)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write startOptions fail");
        return ERR_WRITE_START_OPTIONS;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_SELF_UI_ABILITY_WITH_START_OPTIONS,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartSelfUIAbilityWithPidResult(const Want &want, StartOptions &options,
    uint64_t callbackId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_CODE;
    }

    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write want fail");
        return ERR_WRITE_WANT;
    }

    if (!data.WriteParcelable(&options)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write startOptions fail");
        return ERR_WRITE_START_OPTIONS;
    }

    if (!data.WriteUint64(callbackId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callbackId fail");
        return ERR_WRITE_INT_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::START_SELF_UI_ABILITY_WITH_PID_RESULT,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

void AbilityManagerProxy::PrepareTerminateAbilityDone(const sptr<IRemoteObject> &token, bool isTerminate)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write interface token fail");
        return;
    }
    if (token) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(token)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
            return;
        }
    } else {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "write fail");
            return;
        }
    }
    if (!data.WriteBool(isTerminate)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite isTerminate fail");
        return;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::PREPARE_TERMINATE_ABILITY_DONE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }
}

void AbilityManagerProxy::KillProcessWithPrepareTerminateDone(const std::string &moduleName,
    int32_t prepareTermination, bool isExist)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option(MessageOption::TF_SYNC);
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write interface token fail");
        return;
    }
    if (!data.WriteString(moduleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite moduleName fail");
        return;
    }
    if (!data.WriteInt32(prepareTermination)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite prepareTermination fail");
        return;
    }
    if (!data.WriteBool(isExist)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite isExist fail");
        return;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::KILL_PROCESS_WITH_PREPARE_TERMINATE_DONE,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
    }
}

int32_t AbilityManagerProxy::KillProcessForPermissionUpdate(uint32_t accessTokenId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write interface token fail");
        return ERR_FLATTEN_OBJECT;
    }
    if (!data.WriteUint32(accessTokenId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "weite accessTokenId fail");
        return IPC_PROXY_WRITE_PARCEL_ERR;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::KILL_PROCESS_FOR_PERMISSION_UPDATE,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return IPC_PROXY_ERR;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RegisterHiddenStartObserver(const sptr<IHiddenStartObserver> &observer)
{
    if (!observer) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer null");
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "RegisterHiddenStartObserver start");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return ERR_FLATTEN_OBJECT;
    }
    if (!data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer write failed.");
        return ERR_FLATTEN_OBJECT;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_HIDDEN_START_OBSERVER,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Send request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UnregisterHiddenStartObserver(const sptr<IHiddenStartObserver> &observer)
{
    if (!observer) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer null");
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "UnregisterHiddenStartObserver start");
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return ERR_FLATTEN_OBJECT;
    }
    if (!data.WriteRemoteObject(observer->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer write failed.");
        return ERR_FLATTEN_OBJECT;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::UNREGISTER_HIDDEN_START_OBSERVER,
        data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Send request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryPreLoadUIExtensionRecord(const AppExecFwk::ElementName &element,
                                                           const std::string &moduleName,
                                                           const int32_t hostPid,
                                                           int32_t &recordNum,
                                                           int32_t userId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "write token fail");
        return INNER_ERR;
    }

    if (!data.WriteParcelable(&element)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "write element fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteString(moduleName)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "write moduleName fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(hostPid)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "write hostPid fail");
        return INNER_ERR;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "write userId fail");
        return INNER_ERR;
    }

    auto error =
        SendRequest(AbilityManagerInterfaceCode::QUERY_PRELOAD_UIEXTENSION_RECORD,
                    data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::UI_EXT, "request error:%{public}d", error);
        return error;
    }
    recordNum = reply.ReadInt32();
    return NO_ERROR;
}

int32_t AbilityManagerProxy::RevokeDelegator(sptr<IRemoteObject> token)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        return ERR_INVALID_CONTEXT;
    }
    
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return INNER_ERR;
    }
    
    if (!data.WriteRemoteObject(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_INVALID_VALUE;
    }
    
    int error = SendRequest(AbilityManagerInterfaceCode::REVOKE_DELEGATOR, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetAllInsightIntentInfo(
    AbilityRuntime::GetInsightIntentFlag flag,
    std::vector<InsightIntentInfoForQuery> &infos,
    int32_t userId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    TAG_LOGI(AAFwkTag::INTENT, "GetAllInsightIntentInfo");
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::INTENT, "writeInterfaceToken failed");
        return INNER_ERR;
    }

    if (!data.WriteUint32(static_cast<uint32_t>(flag))) {
        TAG_LOGE(AAFwkTag::INTENT, "write flag fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::INTENT, "write userId fail");
        return ERR_INVALID_VALUE;
    }

    int error = SendRequest(
        AbilityManagerInterfaceCode::GET_ALL_INSIGHT_INTENT_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::INTENT, "request error:%{public}d", error);
        return error;
    }
    int32_t infoSize = reply.ReadInt32();
    if (infoSize < 0 || infoSize >= MAX_INTENT_SIZE) {
        TAG_LOGE(AAFwkTag::INTENT, "The number of intents exceeds the limit.");
        return ERR_INVALID_VALUE;
    }

    infos.clear();
    for (int32_t i = 0; i < infoSize; i++) {
        std::unique_ptr<InsightIntentInfoForQuery> info(reply.ReadParcelable<InsightIntentInfoForQuery>());
        if (info == nullptr) {
            return false;
        }
        infos.emplace_back(*info);
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetInsightIntentInfoByBundleName(
    AbilityRuntime::GetInsightIntentFlag flag,
    const std::string &bundleName,
    std::vector<InsightIntentInfoForQuery> &infos,
    int32_t userId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::INTENT, "writeInterfaceToken failed");
        return INNER_ERR;
    }

    if (!data.WriteUint32(static_cast<uint32_t>(flag))) {
        TAG_LOGE(AAFwkTag::INTENT, "write flag fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::INTENT, "write bundleName fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::INTENT, "write userId fail");
        return ERR_INVALID_VALUE;
    }

    int error = SendRequest(
        AbilityManagerInterfaceCode::GET_INSIGHT_INTENT_INFO_BY_BUNDLE_NAME, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::INTENT, "request error:%{public}d", error);
        return error;
    }
    int32_t infoSize = reply.ReadInt32();
    if (infoSize < 0 || infoSize >= MAX_INTENT_SIZE) {
        TAG_LOGE(AAFwkTag::INTENT, "The number of intents exceeds the limit.");
        return ERR_INVALID_VALUE;
    }

    infos.clear();
    for (int32_t i = 0; i < infoSize; i++) {
        std::unique_ptr<InsightIntentInfoForQuery> info(reply.ReadParcelable<InsightIntentInfoForQuery>());
        if (info == nullptr) {
            return false;
        }
        infos.emplace_back(*info);
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetInsightIntentInfoByIntentName(
    AbilityRuntime::GetInsightIntentFlag flag,
    const std::string &bundleName,
    const std::string &moduleName,
    const std::string &intentName,
    InsightIntentInfoForQuery &info,
    int32_t userId)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::INTENT, "writeInterfaceToken failed");
        return INNER_ERR;
    }

    if (!data.WriteUint32(static_cast<uint32_t>(flag))) {
        TAG_LOGE(AAFwkTag::INTENT, "write flag fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::INTENT, "write bundleName fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteString(moduleName)) {
        TAG_LOGE(AAFwkTag::INTENT, "write moduleName fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteString(intentName)) {
        TAG_LOGE(AAFwkTag::INTENT, "write intentName fail");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::INTENT, "write userId fail");
        return ERR_INVALID_VALUE;
    }

    int error = SendRequest(
        AbilityManagerInterfaceCode::GET_INSIGHT_INTENT_INFO_BY_INTENT_NAME, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::INTENT, "request error:%{public}d", error);
        return error;
    }
    std::unique_ptr<InsightIntentInfoForQuery> intentInfo(reply.ReadParcelable<InsightIntentInfoForQuery>());
    if (intentInfo == nullptr) {
        return false;
    }
    info = *intentInfo;
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartAbilityWithWait(Want &want, sptr<IAbilityStartWithWaitObserver> &observer)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    CHECK_POINTER_AND_RETURN_LOG(observer, ERR_NULL_OBJECT, "null observer");

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return INNER_ERR;
    }

    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Parcelable, &want);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, observer->AsObject());
    int32_t error = SendRequest(AbilityManagerInterfaceCode::START_ABILITY_WITH_WAIT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send err:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SuspendExtensionAbility(sptr<IAbilityConnection> connect)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "fail, connect null");
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(connect->AsObject())) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connect write failed");
        return ERR_INVALID_VALUE;
    }

    int32_t error = SendRequest(AbilityManagerInterfaceCode::SUSPEND_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ResumeExtensionAbility(sptr<IAbilityConnection> connect)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "fail, connect null");
        return ERR_INVALID_VALUE;
    }
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(connect->AsObject())) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connect write failed");
        return ERR_INVALID_VALUE;
    }

    int32_t error = SendRequest(AbilityManagerInterfaceCode::RESUME_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::RestartSelfAtomicService(sptr<IRemoteObject> callerToken)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null callerToken");
        return INVALID_CALLER_TOKEN;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return ERR_WRITE_CALLER_TOKEN_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::RESTART_SELF_ATOMIC_SERVICE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetAppServiceExtensionKeepAlive(const std::string &bundleName, bool flag)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write bundleName");
        return ERR_INVALID_VALUE;
    }

    if (!data.WriteBool(flag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write flag");
        return ERR_INVALID_VALUE;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_APP_SERVICE_EXTENSION_KEEP_ALIVE,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::UpdateKioskApplicationList(const std::vector<std::string> &appList)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    if (!data.WriteStringVector(appList)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appList write fail");
        return ERR_WRITE_KIOSK_UPDATE_APP_LIST_FAILED;
    }

    auto error =
        SendRequest(AbilityManagerInterfaceCode::UPDATE_KIOSK_APP_LIST, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::EnterKioskMode(sptr<IRemoteObject> callerToken)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        return ERR_INVALID_CONTEXT;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return ERR_WRITE_CALLER_TOKEN_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::ENTER_KIOSK_MODE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::ExitKioskMode(sptr<IRemoteObject> callerToken)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        return ERR_INVALID_CONTEXT;
    }

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken fail");
        return ERR_WRITE_CALLER_TOKEN_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::EXIT_KIOSK_MODE, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::GetKioskStatus(KioskStatus &kioskStatus)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::GET_KIOSK_INFO, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }

    std::unique_ptr<KioskStatus> info(reply.ReadParcelable<KioskStatus>());
    if (!info) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "read KioskStatus fail");
        return ERR_READ_RESULT_PARCEL_FAILED;
    }
    kioskStatus = *info;
    sptr<IRemoteObject> token = reply.ReadRemoteObject();
    if (token != nullptr) {
        kioskStatus.kioskToken_ = token;
    }
    return reply.ReadInt32();
}

ErrCode AbilityManagerProxy::RegisterSAInterceptor(sptr<AbilityRuntime::ISAInterceptor> interceptor)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call RegisterSAInterceptor");
    if (!interceptor) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptor null");
        return ERR_NULL_SA_INTERCEPTOR_EXECUTER;
    }

    MessageParcel data;
    MessageParcel reply;
    MessageOption option;

    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    if (!data.WriteRemoteObject(interceptor->AsObject())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptor write failed.");
        return ERR_WRITE_SA_INTERCEPTOR_FAILED;
    }

    auto error = SendRequest(AbilityManagerInterfaceCode::REGISTER_SA_INTERCEPTOR, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Send request error: %{public}d", error);
        return error;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::QueryKeepAliveAppServiceExtensions(std::vector<KeepAliveInfo> &list)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return INNER_ERR;
    }

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::GET_APP_SERVICE_EXTENSIONS_KEEP_ALIVE,
        data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }

    ret = GetParcelableInfos<KeepAliveInfo>(reply, list);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "GetParcelableInfos error: %{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::SetOnNewWantSkipScenarios(sptr<IRemoteObject> callerToken, int32_t scenarios)
{
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        return ERR_INVALID_CONTEXT;
    }

    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, RemoteObject, callerToken);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, scenarios);

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::SET_ON_NEW_WANT_SKIP_SCENARIOS, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::NotifyStartupExceptionBySCB(int32_t requestId)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken failed");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, requestId);

    MessageParcel reply;
    MessageOption option;
    auto ret = SendRequest(AbilityManagerInterfaceCode::NOTIFY_STARTUP_EXCEPTION_BY_SCB, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::PreloadApplication(const std::string &bundleName, int32_t userId, int32_t appIndex)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", bundleName.c_str());
        return INNER_ERR;
    }
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "writeInterfaceToken fail");
        return ERR_WRITE_INTERFACE_TOKEN_FAILED;
    }

    MessageParcel reply;
    MessageOption option;

    if (!data.WriteString(bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write bundleName");
        return ERR_WRITE_STRING_FAILED;
    }

    if (!data.WriteInt32(userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write userId");
        return ERR_WRITE_INT_FAILED;
    }

    if (!data.WriteInt32(appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to write appIndex");
        return ERR_WRITE_INT_FAILED;
    }

    auto ret = SendRequest(AbilityManagerInterfaceCode::PRELOAD_APPLICATION, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return ret;
    }

    return reply.ReadInt32();
}

int32_t AbilityManagerProxy::StartSelfUIAbilityInCurrentProcess(const Want &want, const std::string &specifiedFlag,
    const AAFwk::StartOptions &startOptions, bool hasOptions, sptr<IRemoteObject> callerToken)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    if (!data.WriteParcelable(&want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "want write fail");
        return INNER_ERR;
    }
    if (!data.WriteString(specifiedFlag)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "specifiedFlag write fail");
        return ERR_INVALID_VALUE;
    }
    if (!data.WriteParcelable(&startOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startOptions fail");
        return INNER_ERR;
    }
    if (!data.WriteBool(hasOptions)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "hasOptions write fail");
        return ERR_INVALID_VALUE;
    }
    if (callerToken) {
        if (!data.WriteBool(true) || !data.WriteRemoteObject(callerToken)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken and flag write fail");
            return INNER_ERR;
        }
    } else {
        if (!data.WriteBool(false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "flag write fail");
            return INNER_ERR;
        }
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::START_SELF_UI_ABILITY_IN_CURRENT_PROCESS, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "send request error: %{public}d", ret);
        return ret;
    }
    return reply.ReadInt32();
}

bool AbilityManagerProxy::IsRestartAppLimit()
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    if (!WriteInterfaceToken(data)) {
        return false;
    }
    auto ret = SendRequest(AbilityManagerInterfaceCode::IS_RESTART_APP_LIMIT, data, reply, option);
    if (ret != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error: %{public}d", ret);
        return false;
    }

    return reply.ReadBool();
}

int32_t AbilityManagerProxy::ClearPreloadedUIExtensionAbility(int32_t extensionAbilityId, int32_t userId)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, extensionAbilityId);
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::UN_PRELOAD_UI_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    int32_t result = reply.ReadInt32();
    return result;
}

int32_t AbilityManagerProxy::ClearPreloadedUIExtensionAbilities(int32_t userId)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        return INNER_ERR;
    }
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, userId);
    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(AbilityManagerInterfaceCode::CLEAR_ALL_PRELOAD_UI_EXTENSION_ABILITY, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    int32_t result = reply.ReadInt32();
    return result;
}

int32_t AbilityManagerProxy::RegisterPreloadUIExtensionHostClient(const sptr<IRemoteObject> &callerToken)
{
    MessageParcel data;
    if (!WriteInterfaceToken(data)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write token fail");
        return INNER_ERR;
    }
    if (!data.WriteRemoteObject(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "write callerToken failed.");
        return INNER_ERR;
    }
    MessageParcel reply;
    MessageOption option;
    auto error = SendRequest(
        AbilityManagerInterfaceCode::REGISTER_PRELOAD_UI_EXTENSION_HOST_CLIENT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    int32_t result = reply.ReadInt32();
    return result;
}

int32_t AbilityManagerProxy::UnRegisterPreloadUIExtensionHostClient(int32_t callerPid)
{
    MessageParcel data;
    MessageParcel reply;
    MessageOption option;
    PROXY_WRITE_PARCEL_AND_RETURN_IF_FAIL(data, Int32, callerPid);
    auto error =
        SendRequest(AbilityManagerInterfaceCode::UNREGISTER_PRELOAD_UI_EXTENSION_HOST_CLIENT, data, reply, option);
    if (error != NO_ERROR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "request error:%{public}d", error);
        return error;
    }
    int32_t result = reply.ReadInt32();
    return result;
}
} // namespace AAFwk
} // namespace OHOS
