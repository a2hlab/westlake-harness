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

#include "ability_runtime/js_ability_context.h"

#include <chrono>
#include <cstdint>
#include <cstdlib>
#include <mutex>
#include <regex>

#include "ability_manager_client.h"
#include "ability_manager_errors.h"
#include "app_utils.h"
#include "event_handler.h"
#include "hilog_tag_wrapper.h"
#include "hitrace_meter.h"
#include "ipc_skeleton.h"
#include "ability_runtime/js_caller_complex.h"
#include "js_context_utils.h"
#include "js_data_struct_converter.h"
#include "js_error_utils.h"
#include "js_runtime_utils.h"
#include "js_uiservice_ability_connection.h"
#include "js_ui_extension_callback.h"
#include "js_ui_service_proxy.h"
#include "json_utils.h"
#include "mission_info.h"
#include "napi_common_ability.h"
#include "napi_common_start_options.h"
#include "napi_common_util.h"
#include "napi_common_want.h"
#include "napi_remote_object.h"
#include "open_link_options.h"
#include "open_link/napi_common_open_link_options.h"
#include "start_options.h"
#include "tokenid_kit.h"
#include "ui_ability_servicehost_stub_impl.h"
#include "ui_service_extension_connection_constants.h"
#include "uri.h"
#include "want.h"

#ifdef SUPPORT_GRAPHICS
#include "pixel_map_napi.h"
#endif

namespace OHOS {
namespace AbilityRuntime {
constexpr int32_t INDEX_ZERO = 0;
constexpr int32_t INDEX_ONE = 1;
constexpr int32_t INDEX_TWO = 2;
constexpr int32_t INDEX_THREE = 3;
constexpr size_t ARGC_ZERO = 0;
constexpr size_t ARGC_ONE = 1;
constexpr size_t ARGC_TWO = 2;
constexpr size_t ARGC_THREE = 3;
constexpr int32_t TRACE_ATOMIC_SERVICE_ID = 201;
const std::string KEY_REQUEST_ID = "com.ohos.param.requestId";
const std::string TRACE_ATOMIC_SERVICE = "StartAtomicService";
constexpr int32_t CALLER_TIME_OUT = 10; // 10s
const std::string JSON_KEY_ERR_MSG = "errMsg";

namespace {
static std::map<ConnectionKey, sptr<JSAbilityConnection>, KeyCompare> g_connects;
std::recursive_mutex gConnectsLock_;
int64_t g_serialNumber = 0;
const std::string ATOMIC_SERVICE_PREFIX = "com.atomicservice.";
std::atomic<bool> g_hasSetContinueState = false;
// max request code is (1 << 49) - 1
constexpr int64_t MAX_REQUEST_CODE = 562949953421311;
constexpr size_t MAX_REQUEST_CODE_LENGTH = 15;
constexpr int32_t BASE_REQUEST_CODE_NUM = 10;
constexpr const char* FUNC_NAME_ON_REQUEST_SUCCESS = "onRequestSuccess";
constexpr const char* FUNC_NAME_ON_REQUEST_FAILURE = "onRequestFailure";

void* DetachNewAbilityContext(napi_env, void* nativeObject, void*)
{
    auto* origContext = static_cast<std::weak_ptr<AbilityContext> *>(nativeObject);
    if (origContext == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "origContext is null");
        return nullptr;
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "New detached ability context");
    auto* detachNewContext = new (std::nothrow) std::weak_ptr<AbilityContext>(*origContext);
    return detachNewContext;
}

void DetachFinalizeAbilityContext(void* detachedObject, void*)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "Finalizer detached ability context");
    delete static_cast<std::weak_ptr<AbilityContext> *>(detachedObject);
}

int64_t RequestCodeFromStringToInt64(const std::string &requestCode)
{
    if (requestCode.size() > MAX_REQUEST_CODE_LENGTH) {
        TAG_LOGW(AAFwkTag::CONTEXT, "requestCode too long: %{public}s", requestCode.c_str());
        return 0;
    }
    std::regex formatRegex("^[1-9]\\d*|0$");
    std::smatch sm;
    if (!std::regex_match(requestCode, sm, formatRegex)) {
        TAG_LOGW(AAFwkTag::CONTEXT, "requestCode match failed: %{public}s", requestCode.c_str());
        return 0;
    }
    int64_t parsedRequestCode = 0;
    parsedRequestCode = strtoll(requestCode.c_str(), nullptr, BASE_REQUEST_CODE_NUM);
    if (parsedRequestCode > MAX_REQUEST_CODE) {
        TAG_LOGW(AAFwkTag::CONTEXT, "requestCode too large: %{public}s", requestCode.c_str());
        return 0;
    }
    return parsedRequestCode;
}

// This function has to be called from engine thread
void RemoveConnection(int64_t connectId)
{
    std::lock_guard<std::recursive_mutex> lock(gConnectsLock_);
    auto item = std::find_if(g_connects.begin(), g_connects.end(),
    [&connectId](const auto &obj) {
        return connectId == obj.first.id;
    });
    if (item != g_connects.end()) {
        TAG_LOGD(AAFwkTag::CONTEXT, "remove connection ability exist");
        if (item->second) {
            item->second->RemoveConnectionObject();
        }
        g_connects.erase(item);
    } else {
        TAG_LOGD(AAFwkTag::CONTEXT, "remove connection ability not exist");
    }
}

int64_t InsertConnection(sptr<JSAbilityConnection> connection, const AAFwk::Want &want, int32_t accountId = -1)
{
    std::lock_guard<std::recursive_mutex> lock(gConnectsLock_);
    if (connection == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null connection");
        return -1;
    }
    int64_t connectId = g_serialNumber;
    ConnectionKey key;
    key.id = g_serialNumber;
    key.want = want;
    key.accountId = accountId;
    connection->SetConnectionId(key.id);
    g_connects.emplace(key, connection);
    if (g_serialNumber < INT32_MAX) {
        g_serialNumber++;
    } else {
        g_serialNumber = 0;
    }
    return connectId;
}

class StartAbilityByCallParameters {
public:
    int err = 0;
    sptr<IRemoteObject> remoteCallee = nullptr;
    std::shared_ptr<CallerCallBack> callerCallBack = nullptr;
    std::mutex mutexlock;
    std::condition_variable condition;
};

void GenerateCallerCallBack(std::shared_ptr<StartAbilityByCallParameters> calls,
    std::shared_ptr<CallerCallBack> callerCallBack)
{
    if (calls == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null calls");
        return;
    }
    if (callerCallBack == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null callerCallBack");
        return;
    }
    auto callBackDone = [calldata = calls] (const sptr<IRemoteObject> &obj) {
        TAG_LOGD(AAFwkTag::CONTEXT, "callBackDone called start");
        std::unique_lock<std::mutex> lock(calldata->mutexlock);
        calldata->remoteCallee = obj;
        calldata->condition.notify_all();
        TAG_LOGD(AAFwkTag::CONTEXT, "callBackDone called end");
    };

    auto releaseListen = [](const std::string &str) {
        TAG_LOGI(AAFwkTag::CONTEXT, "releaseListen is called %{public}s", str.c_str());
    };

    callerCallBack->SetCallBack(callBackDone);
    callerCallBack->SetOnRelease(releaseListen);
}

void StartAbilityByCallExecuteDone(StartAbilityByCallParameters &callData,
    std::shared_ptr<CallerCallBack> callerCallback, const AAFwk::Want &want,
    std::weak_ptr<AbilityContext> wContext, int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::CONTEXT, "StartAbilityByCallExecuteDone begin");
    auto context = wContext.lock();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        callData.err = AAFwk::ERR_INVALID_CONTEXT;
        return;
    }
    auto ret = context->StartAbilityByCall(want, callerCallback, userId);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::CONTEXT, "startAbility failed");
        callData.err = ret;
        return;
    }
    std::unique_lock<std::mutex> lock(callData.mutexlock);
    if (callData.remoteCallee != nullptr) {
        TAG_LOGI(AAFwkTag::CONTEXT, "not null callExecute callee");
        return;
    }

    if (callData.condition.wait_for(lock, std::chrono::seconds(CALLER_TIME_OUT)) == std::cv_status::timeout) {
        TAG_LOGE(AAFwkTag::CONTEXT, "callExecute waiting callee timeout");
        callData.err = ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "StartAbilityByCallExecuteDone end");
}

void StartAbilityByCallComplete(napi_env env, NapiAsyncTask& task, std::weak_ptr<AbilityContext> abilityContext,
    std::shared_ptr<StartAbilityByCallParameters> calldata, std::shared_ptr<CallerCallBack> callerCallBack)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (calldata == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null calldata");
        return;
    }
    if (calldata->err != 0) {
        TAG_LOGE(AAFwkTag::CONTEXT, "StartAbilityByCall err: %{public}d", calldata->err);
        task.Reject(env, CreateJsErrorByNativeErr(env, calldata->err));
        auto context = abilityContext.lock();
        if (context == nullptr || callerCallBack == nullptr) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null context or callBack");
            return;
        }
        context->ClearFailedCallConnection(callerCallBack);
        return;
    }
    auto context = abilityContext.lock();
    if (context == nullptr || callerCallBack == nullptr || calldata->remoteCallee == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null callComplete params error %{public}s",
            context == nullptr ? "context" : (calldata->remoteCallee == nullptr ? "remoteCallee" : "callerCallBack"));
        task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
        TAG_LOGD(AAFwkTag::CONTEXT, "callComplete end");
        return;
    }
    auto releaseCallAbilityFunc = [abilityContext] (std::shared_ptr<CallerCallBack> callback) -> ErrCode {
        auto contextForRelease = abilityContext.lock();
        if (contextForRelease == nullptr) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null releaseCallAbilityFunction");
            return -1;
        }
        return contextForRelease->ReleaseCall(callback);
    };
    task.Resolve(env, CreateJsCallerComplex(env, releaseCallAbilityFunc, calldata->remoteCallee, callerCallBack));
    TAG_LOGD(AAFwkTag::CONTEXT, "StartAbilityByCallComplete end");
}
}

void JsAbilityContext::Finalizer(napi_env env, void* data, void* hint)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    std::unique_ptr<JsAbilityContext>(static_cast<JsAbilityContext*>(data));
}

napi_value JsAbilityContext::StartAbility(napi_env env, napi_callback_info info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbility);
}

napi_value JsAbilityContext::OpenLink(napi_env env, napi_callback_info info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnOpenLink);
}

napi_value JsAbilityContext::StartAbilityAsCaller(napi_env env, napi_callback_info info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityAsCaller);
}

napi_value JsAbilityContext::StartRecentAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartRecentAbility);
}

napi_value JsAbilityContext::StartAbilityWithAccount(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityWithAccount);
}

napi_value JsAbilityContext::StartAbilityByCall(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityByCall);
}

napi_value JsAbilityContext::StartAbilityForResult(napi_env env, napi_callback_info info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityForResult);
}

napi_value JsAbilityContext::StartAbilityForResultWithAccount(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityForResultWithAccount);
}

napi_value JsAbilityContext::StartServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartExtensionAbility);
}

napi_value JsAbilityContext::StartServiceExtensionAbilityWithAccount(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartExtensionAbilityWithAccount);
}

napi_value JsAbilityContext::StopServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStopExtensionAbility);
}

napi_value JsAbilityContext::StopServiceExtensionAbilityWithAccount(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStopExtensionAbilityWithAccount);
}

napi_value JsAbilityContext::ConnectAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnConnectAbility);
}

napi_value JsAbilityContext::ConnectAbilityWithAccount(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnConnectAbilityWithAccount);
}

napi_value JsAbilityContext::DisconnectAbility(napi_env env, napi_callback_info info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnDisconnectAbility);
}

napi_value JsAbilityContext::TerminateSelf(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnTerminateSelf);
}

napi_value JsAbilityContext::TerminateSelfWithResult(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnTerminateSelfWithResult);
}

napi_value JsAbilityContext::BackToCallerAbilityWithResult(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnBackToCallerAbilityWithResult);
}

napi_value JsAbilityContext::RestoreWindowStage(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnRestoreWindowStage);
}

napi_value JsAbilityContext::RequestDialogService(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnRequestDialogService);
}

napi_value JsAbilityContext::ReportDrawnCompleted(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnReportDrawnCompleted);
}

napi_value JsAbilityContext::IsTerminating(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnIsTerminating);
}

napi_value JsAbilityContext::StartAbilityByType(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAbilityByType);
}

napi_value JsAbilityContext::RequestModalUIExtension(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnRequestModalUIExtension);
}

napi_value JsAbilityContext::ShowAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnShowAbility);
}

napi_value JsAbilityContext::HideAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnHideAbility);
}

napi_value JsAbilityContext::MoveAbilityToBackground(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnMoveAbilityToBackground);
}

napi_value JsAbilityContext::OpenAtomicService(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnOpenAtomicService);
}

napi_value JsAbilityContext::StartUIServiceExtension(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartUIServiceExtension);
}

napi_value JsAbilityContext::ConnectUIServiceExtension(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnConnectUIServiceExtension);
}

napi_value JsAbilityContext::DisconnectUIServiceExtension(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnDisconnectUIServiceExtension);
}

napi_value JsAbilityContext::SetRestoreEnabled(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetRestoreEnabled);
}

napi_value JsAbilityContext::SetColorMode(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetColorMode);
}

napi_value JsAbilityContext::StartAppServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartAppServiceExtensionAbility);
}

napi_value JsAbilityContext::StopAppServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStopAppServiceExtensionAbility);
}

napi_value JsAbilityContext::ConnectAppServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnConnectAppServiceExtensionAbility);
}

napi_value JsAbilityContext::DisconnectAppServiceExtensionAbility(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnDisconnectAbility);
}

napi_value JsAbilityContext::RevokeDelegator(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnRevokeDelegator);
}

napi_value JsAbilityContext::SetOnNewWantSkipScenarios(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetOnNewWantSkipScenarios);
}

napi_value JsAbilityContext::StartSelfUIAbilityInCurrentProcess(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnStartSelfUIAbilityInCurrentProcess);
}

napi_value JsAbilityContext::RestartAppWithWindow(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnRestartAppWithWindow);
}

napi_value JsAbilityContext::SetMissionWindowIcon(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetMissionWindowIcon);
}

void JsAbilityContext::ClearFailedCallConnection(
    const std::weak_ptr<AbilityContext>& abilityContext, const std::shared_ptr<CallerCallBack> &callback)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    auto context = abilityContext.lock();
    if (context == nullptr || callback == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context or callback");
        return;
    }

    context->ClearFailedCallConnection(callback);
}

OnRequestResult JsAbilityContext::UnwrapCompletionHandlerOnRequestResult(napi_env env,
    const char *funcName, std::shared_ptr<NativeReference> ref)
{
    if (ref == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null ref");
        return nullptr;
    }
    return [env, ref, funcName](const AppExecFwk::ElementName &element, const std::string &message) {
        napi_value completionHandler = ref->GetNapiValue();
        AbilityRuntime::HandleScope handleScope(env);
        napi_value onRequestResultObj = AppExecFwk::GetPropertyValueByPropertyName(env, completionHandler,
            funcName, napi_function);
        size_t argc = ARGC_TWO;
        napi_value argv[ARGC_TWO] = { AppExecFwk::WrapElementName(env, element), CreateJsValue(env, message) };
        napi_status status = napi_call_function(env, completionHandler, onRequestResultObj, argc, argv, nullptr);
        if (status != napi_ok) {
            TAG_LOGE(AAFwkTag::CONTEXT, "call %{public}s, failed: %{public}d", funcName, status);
        }
    };
}

void JsAbilityContext::UnwrapCompletionHandlerInStartOptions(napi_env env, napi_value param,
    AAFwk::StartOptions &options)
{
    AbilityRuntime::HandleScope handleScope(env);
    napi_value completionHandler = AppExecFwk::GetPropertyValueByPropertyName(env, param,
        "completionHandler", napi_object);
    if (completionHandler == nullptr) {
        TAG_LOGD(AAFwkTag::CONTEXT, "null completionHandler");
        return;
    }
    TAG_LOGI(AAFwkTag::CONTEXT, "completionHandler exists");
    napi_ref ref = nullptr;
    if (napi_create_reference(env, completionHandler, 1, &ref) != napi_ok || ref == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "failed to create ref");
        return;
    }
    auto completionHandlerRef = std::shared_ptr<NativeReference>(reinterpret_cast<NativeReference *>(ref));
    OnRequestResult onRequestSucc = UnwrapCompletionHandlerOnRequestResult(env, FUNC_NAME_ON_REQUEST_SUCCESS,
        completionHandlerRef);
    OnRequestResult onRequestFail = UnwrapCompletionHandlerOnRequestResult(env, FUNC_NAME_ON_REQUEST_FAILURE,
        completionHandlerRef);
    auto context = context_.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        return;
    }
    std::string requestId = std::to_string(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::high_resolution_clock::now().time_since_epoch()).count()));
    if (context->AddCompletionHandler(requestId, onRequestSucc, onRequestFail) != ERR_OK) {
        TAG_LOGE(AAFwkTag::CONTEXT, "add completionHandler failed");
        return;
    }
    options.requestId_ = requestId;
}

std::pair<OnAtomicRequestSuccess, OnAtomicRequestFailure> JsAbilityContext::CreateAtomicServiceCallBack(
    napi_env env,
    const std::shared_ptr<NativeReference>& atomicServiceRef,
    const std::shared_ptr<NativeReference>& onRequestSuccRef,
    const std::shared_ptr<NativeReference>& onRequestFailRef)
{
    OnAtomicRequestSuccess onRequestSucc = [env, atomicServiceRef, onRequestSuccRef](const std::string &appId) {
        HandleScope handleScope(env);
        napi_value argv[ARGC_ONE] = { CreateJsValue(env, appId) };
        napi_value completionHandlerForAtomicService = atomicServiceRef->GetNapiValue();
        napi_value onRequestSuccFunc = onRequestSuccRef->GetNapiValue();
        napi_valuetype type = napi_undefined;
        if (napi_typeof(env, onRequestSuccFunc, &type) != napi_ok || type != napi_function) {
            TAG_LOGE(AAFwkTag::CONTEXT, "onRequestSuccFunc is not function");
            return;
        }
        if (napi_typeof(env, completionHandlerForAtomicService, &type) != napi_ok || type != napi_object) {
            TAG_LOGE(AAFwkTag::CONTEXT, "completionHandlerForAtomicService is not napi_object");
            return;
        }
        napi_status status = napi_call_function(
            env, completionHandlerForAtomicService, onRequestSuccFunc, ARGC_ONE, argv, nullptr);
        if (status != napi_ok) {
            TAG_LOGE(AAFwkTag::UI_EXT, "call onRequestSuccess, failed: %{public}d", status);
        }
    };
    OnAtomicRequestFailure onRequestFail = [env, atomicServiceRef, onRequestFailRef](
        const std::string &appId, int32_t failureCode, const std::string &message) {
        HandleScope handleScope(env);
        napi_value argv[ARGC_THREE] = { CreateJsValue(env, appId), CreateJsValue(env, failureCode),
            CreateJsValue(env, message) };
        napi_value completionHandlerForAtomicService = atomicServiceRef->GetNapiValue();
        napi_value onRequestFailFunc = onRequestFailRef->GetNapiValue();
        napi_valuetype type = napi_undefined;
        if (napi_typeof(env, onRequestFailFunc, &type) != napi_ok || type != napi_function) {
            TAG_LOGE(AAFwkTag::CONTEXT, "onRequestFailFunc is not function");
            return;
        }
        if (napi_typeof(env, completionHandlerForAtomicService, &type) != napi_ok || type != napi_object) {
            TAG_LOGE(AAFwkTag::CONTEXT, "completionHandlerForAtomicService is not napi_object");
            return;
        }
        napi_status status = napi_call_function(
            env, completionHandlerForAtomicService, onRequestFailFunc, ARGC_THREE, argv, nullptr);
        if (status != napi_ok) {
            TAG_LOGE(AAFwkTag::UI_EXT, "call onRequestFailure, failed: %{public}d", status);
        }
    };
    return std::make_pair(onRequestSucc, onRequestFail);
}

void JsAbilityContext::UnWrapCompletionHandlerForAtomicService(
    napi_env env, napi_value param, AAFwk::StartOptions &options, const std::string &appId)
{
    std::shared_ptr<NativeReference> atomicServiceRef = AppExecFwk::CreateNativeRef(env, param,
        "completionHandlerForAtomicService", napi_object);
    if (atomicServiceRef == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "create reference failed");
        return;
    }
    TAG_LOGI(AAFwkTag::UI_EXT, "completionHandlerForAtomicService exists");
    std::shared_ptr<NativeReference> onRequestSuccRef = AppExecFwk::CreateNativeRef(
        env, atomicServiceRef->GetNapiValue(), "onAtomicServiceRequestSuccess", napi_function);
    std::shared_ptr<NativeReference> onRequestFailRef = AppExecFwk::CreateNativeRef(
        env, atomicServiceRef->GetNapiValue(), "onAtomicServiceRequestFailure", napi_function);
    if (onRequestSuccRef == nullptr || onRequestFailRef == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "create onRequestSuccRef or onRequestFailRef failed");
        return;
    }
    auto atomicRequestCallback = CreateAtomicServiceCallBack(
        env, atomicServiceRef, onRequestSuccRef, onRequestFailRef);
    auto context = context_.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        return;
    }
    std::string requestId = std::to_string(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::high_resolution_clock::now().time_since_epoch()).count()));
    if (context->AddCompletionHandlerForAtomicService(
        requestId, atomicRequestCallback.first, atomicRequestCallback.second, appId) != ERR_OK) {
        TAG_LOGE(AAFwkTag::CONTEXT, "add completionHandler failed");
        return;
    }
    options.requestId_ = requestId;
}

void JsAbilityContext::AddCompletionHandlerForOpenLink(AAFwk::Want &want, OnRequestResult &onRequestSucc,
    OnRequestResult &onRequestFail)
{
    auto context = context_.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        return;
    }
    std::string requestId = std::to_string(static_cast<uint64_t>(std::chrono::duration_cast<std::chrono::nanoseconds>(
        std::chrono::high_resolution_clock::now().time_since_epoch()).count()));
    if (context->AddCompletionHandlerForOpenLink(requestId, onRequestSucc, onRequestFail) != ERR_OK) {
        TAG_LOGE(AAFwkTag::CONTEXT, "add completionHandler failed");
        return;
    }
    want.RemoveParam(KEY_REQUEST_ID);
    want.SetParam(KEY_REQUEST_ID, requestId);
}

napi_value JsAbilityContext::OnStartAbility(napi_env env, NapiCallbackInfo& info, bool isStartRecent)
{
    StartAsyncTrace(HITRACE_TAG_ABILITY_MANAGER, TRACE_ATOMIC_SERVICE, TRACE_ATOMIC_SERVICE_ID);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);

    if (info.argc == ARGC_ZERO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid arg");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    InheritWindowMode(want);
    decltype(info.argc) unwrapArgc = ARGC_ONE;
    TAG_LOGD(AAFwkTag::CONTEXT, "ability:%{public}s", want.GetElement().GetAbilityName().c_str());
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_ONE && CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start options is used");
        if (!AppExecFwk::UnwrapStartOptionsWithProcessOption(env, info.argv[INDEX_ONE], startOptions)) {
            ThrowInvalidParamError(env, "Parse param startOptions failed, startOptions must be StartOptions.");
            TAG_LOGE(AAFwkTag::CONTEXT, "invalid options");
            return CreateJsUndefined(env);
        }
        UnwrapCompletionHandlerInStartOptions(env, info.argv[INDEX_ONE], startOptions);
        unwrapArgc++;
    }

    if (isStartRecent) {
        TAG_LOGD(AAFwkTag::CONTEXT, "startRecentAbility");
        want.SetParam(Want::PARAM_RESV_START_RECENT, true);
    }

    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
            system_clock::now().time_since_epoch()).count());
        want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
    }

    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, want, startOptions, unwrapArgc,
        &observer = freeInstallObserver_, innerErrCode]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }

        *innerErrCode = (unwrapArgc == ARGC_ONE) ?
            context->StartAbility(want, -1) : context->StartAbility(want, startOptions, -1);
        if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND &&
            *innerErrCode != 0 && observer != nullptr) {
            std::string bundleName = want.GetElement().GetBundleName();
            std::string abilityName = want.GetElement().GetAbilityName();
            std::string startTime = want.GetStringParam(Want::PARAM_RESV_START_TIME);
            observer->OnInstallFinished(bundleName, abilityName, startTime, *innerErrCode);
        }
    };

    NapiAsyncTask::CompleteCallback complete = [innerErrCode, weak = context_, want, startOptions, unwrapArgc](
        napi_env env, NapiAsyncTask& task, int32_t status) {
        HandleScope handleScope(env);
        if (*innerErrCode == ERR_OK) {
            TAG_LOGD(AAFwkTag::CONTEXT, "startAbility success");
            task.Resolve(env, CreateJsUndefined(env));
            return;
        }
        task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
        auto context = weak.lock();
        if (context == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            return;
        }
        if (!startOptions.requestId_.empty()) {
            std::string errMsg = want.GetBoolParam(Want::PARAM_RESV_START_RECENT, false) ?
                "Failed to call startRecentAbility" : "Failed to call startAbility";
            nlohmann::json jsonObject = nlohmann::json { { JSON_KEY_ERR_MSG, errMsg } };
            context->OnRequestFailure(startOptions.requestId_, want.GetElement(), jsonObject.dump());
        }
    };

    napi_value lastParam = (info.argc > unwrapArgc) ? info.argv[unwrapArgc] : nullptr;
    napi_value result = nullptr;
    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        AddFreeInstallObserver(env, want, lastParam, &result);
        NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbility", env,
            CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), nullptr, nullptr));
    } else {
        NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbility", env,
            CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    }
    return result;
}

napi_value JsAbilityContext::OnStartUIServiceExtension(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid want");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->StartUIServiceExtensionAbility(want);
        };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartUIServiceExtension",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

bool JsAbilityContext::UnwrapConnectUIServiceExtensionParam(napi_env env, NapiCallbackInfo& info, AAFwk::Want& want)
{
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "invalid argc");
        ThrowTooFewParametersError(env);
        return false;
    }
    bool unwrapResult = OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    if (!unwrapResult) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "UnwrapWant failed");
        ThrowInvalidParamError(env, "parse want error");
        return false;
    }
    TAG_LOGI(AAFwkTag::UISERVC_EXT, "callee:%{public}s.%{public}s", want.GetBundle().c_str(),
        want.GetElement().GetAbilityName().c_str());
    if (!CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "callback type incorrect");
        ThrowInvalidParamError(env, "Incorrect parameter types");
        return false;
    }
    return true;
}

bool JsAbilityContext::CheckConnectAlreadyExist(napi_env env,
    AAFwk::Want& want, napi_value callback, napi_value& result)
{
    TAG_LOGD(AAFwkTag::UISERVC_EXT, "called");
    sptr<JSUIServiceExtAbilityConnection> connection = nullptr;
    UIServiceConnection::FindUIServiceAbilityConnection(env, want, callback, connection);
    if (connection == nullptr) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "null connection");
        return false;
    }

    std::unique_ptr<NapiAsyncTask> uasyncTask = CreateAsyncTaskWithLastParam(env, nullptr, nullptr, nullptr, &result);
    napi_value proxy = connection->GetProxyObject();
    if (proxy == nullptr) {
        TAG_LOGW(AAFwkTag::UISERVC_EXT, "null proxy");
        connection->AddDuplicatedPendingTask(uasyncTask);
    } else {
        TAG_LOGD(AAFwkTag::UISERVC_EXT, "resolve, got proxy object");
        uasyncTask->ResolveWithNoError(env, proxy);
    }
    return true;
}

napi_value JsAbilityContext::OnConnectUIServiceExtension(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::UISERVC_EXT, "called");
    AAFwk::Want want;
    bool unwrapResult = UnwrapConnectUIServiceExtensionParam(env, info, want);
    if (!unwrapResult) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "unwrap params failed");
        return CreateJsUndefined(env);
    }
    napi_value callbackObject = nullptr;
    if (info.argc > ARGC_ONE) {
        callbackObject = info.argv[INDEX_ONE];
    }
    napi_value result = nullptr;
    bool duplicated = CheckConnectAlreadyExist(env, want, callbackObject, result);
    if (duplicated) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "duplicated");
        return result;
    }

    sptr<JSUIServiceExtAbilityConnection> connection = sptr<JSUIServiceExtAbilityConnection>::MakeSptr(env);
    sptr<UIAbilityServiceHostStubImpl> stub = connection->GetServiceHostStub();
    want.SetParam(UISERVICEHOSTPROXY_KEY, stub->AsObject());

    result = nullptr;
    std::unique_ptr<NapiAsyncTask> uasyncTask = CreateAsyncTaskWithLastParam(env, nullptr, nullptr, nullptr, &result);
    std::shared_ptr<NapiAsyncTask> uasyncTaskShared = std::move(uasyncTask);
    if (info.argc > ARGC_ONE) {
        connection->SetJsConnectionObject(callbackObject);
    }
    connection->SetNapiAsyncTask(uasyncTaskShared);
    UIServiceConnection::InsertUIServiceAbilityConnection(connection, want);
    std::unique_ptr<NapiAsyncTask::CompleteCallback> complete = std::make_unique<NapiAsyncTask::CompleteCallback>(
        [weak = context_, want, uasyncTaskShared, connection](
            napi_env env, NapiAsyncTask& taskUseless, int32_t status) {
            DoConnectUIServiceExtension(env, weak, connection, uasyncTaskShared, want);
        });
    napi_ref callback = nullptr;
    std::unique_ptr<NapiAsyncTask::ExecuteCallback> execute = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnConnectUIServiceExtension",
        env, std::make_unique<NapiAsyncTask>(callback, std::move(execute), std::move(complete)));
    return result;
}

void JsAbilityContext::DoConnectUIServiceExtension(napi_env env,
    std::weak_ptr<AbilityContext> weakContext, sptr<JSUIServiceExtAbilityConnection> connection,
    std::shared_ptr<NapiAsyncTask> uasyncTaskShared, const AAFwk::Want& want)
{
    if (uasyncTaskShared == nullptr) {
        return;
    }

    int64_t connectId = connection->GetConnectionId();
    auto context = weakContext.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        uasyncTaskShared->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
        UIServiceConnection::RemoveUIServiceAbilityConnection(connectId);
        return;
    }

    auto innerErrCode = context->ConnectUIServiceExtensionAbility(want, connection);
    AbilityErrorCode errcode = AbilityRuntime::GetJsErrorCodeByNativeError(innerErrCode);
    if (errcode != AbilityErrorCode::ERROR_OK) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "errcode %{public}d.", errcode);
        uasyncTaskShared->Reject(env, CreateJsError(env, errcode));
        UIServiceConnection::RemoveUIServiceAbilityConnection(connectId);
    }
}

napi_value JsAbilityContext::OnDisconnectUIServiceExtension(napi_env env, NapiCallbackInfo& info)
{
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "invalid argc");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::JsUIServiceProxy* proxy = nullptr;
    napi_status status = napi_unwrap(env, info.argv[INDEX_ZERO], reinterpret_cast<void**>(&proxy));
    if (status != napi_ok || proxy == nullptr) {
        TAG_LOGE(AAFwkTag::UISERVC_EXT, "napi_unwrap err or null proxy");
        ThrowInvalidParamError(env, "Parameter verification failed");
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    int64_t connectId = proxy->GetConnectionId();
    sptr<JSUIServiceExtAbilityConnection> connection = nullptr;
    TAG_LOGI(AAFwkTag::UISERVC_EXT, "connectionId: %{public}d.", static_cast<int32_t>(connectId));
    UIServiceConnection::FindUIServiceAbilityConnection(connectId, want, connection);
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, want, connection, innerErrCode]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::UISERVC_EXT, "onDisconnectUIServiceExtension context is released");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }
        if (!connection) {
            TAG_LOGW(AAFwkTag::UISERVC_EXT, "onDisconnectUIServiceExtension connection nullptr");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INNER);
            return;
        }
        TAG_LOGI(AAFwkTag::UISERVC_EXT, "context->DisconnectAbility");
        context->DisconnectAbility(want, connection);
    };
    NapiAsyncTask::CompleteCallback complete = [connectId, innerErrCode](
            napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                UIServiceConnection::RemoveUIServiceAbilityConnection(connectId);
            } else {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
                UIServiceConnection::RemoveUIServiceAbilityConnection(connectId);
            }
        };

    napi_value result = nullptr;
    NapiAsyncTask::Schedule("JsAbilityContext::OnDisconnectUIServiceExtension",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

static bool CheckUrl(std::string &urlValue)
{
    if (urlValue.empty()) {
        return false;
    }
    Uri uri = Uri(urlValue);
    if (uri.GetScheme().empty()) {
        return false;
    }

    return true;
}

bool JsAbilityContext::CreateOpenLinkTask(const napi_env &env, const napi_value &lastParam,
    AAFwk::Want &want, int &requestCode)
{
    want.SetParam(Want::PARAM_RESV_FOR_RESULT, true);
    napi_value result = nullptr;
    std::unique_ptr<NapiAsyncTask> uasyncTask =
    CreateAsyncTaskWithLastParam(env, lastParam, nullptr, nullptr, &result);
    std::shared_ptr<NapiAsyncTask> asyncTask = std::move(uasyncTask);
    RuntimeTask task = [env, asyncTask](int resultCode, const AAFwk::Want& want, bool isInner) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start onOpenLink async callback");
        HandleScope handleScope(env);
        napi_value abilityResult = AppExecFwk::WrapAbilityResult(env, resultCode, want);
        if (abilityResult == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null abilityResult");
            asyncTask->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
            return;
        }
        isInner ? asyncTask->Reject(env, CreateJsErrorByNativeErr(env, resultCode)) :
            asyncTask->ResolveWithNoError(env, abilityResult);
    };
    requestCode = GenerateRequestCode();
    auto context = context_.lock();
    if (!context) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null context");
        return false;
    }
    context->InsertResultCallbackTask(requestCode, std::move(task));
    return true;
}

static bool ParseOpenLinkParams(const napi_env &env, const NapiCallbackInfo &info, std::string &linkValue,
    AAFwk::OpenLinkOptions &openLinkOptions, AAFwk::Want &want)
{
    if (info.argc != ARGC_THREE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "wrong arguments num");
        return false;
    }

    if (!CheckTypeForNapiValue(env, info.argv[ARGC_ZERO], napi_string)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "link must be string");
        return false;
    }
    if (!ConvertFromJsValue(env, info.argv[ARGC_ZERO], linkValue) || !CheckUrl(linkValue)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid link params");
        return false;
    }

    if (CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "openLinkOptions is used");
        if (!AppExecFwk::UnwrapOpenLinkOptions(env, info.argv[INDEX_ONE], openLinkOptions, want)) {
            TAG_LOGE(AAFwkTag::CONTEXT, "openLinkOptions parse failed");
            return false;
        }
    }

    return true;
}

napi_value JsAbilityContext::OnOpenLink(napi_env env, NapiCallbackInfo& info)
{
    StartAsyncTrace(HITRACE_TAG_ABILITY_MANAGER, TRACE_ATOMIC_SERVICE, TRACE_ATOMIC_SERVICE_ID);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::CONTEXT, "called");

    std::string linkValue("");
    AAFwk::OpenLinkOptions openLinkOptions;
    AAFwk::Want want;
    want.SetParam(AppExecFwk::APP_LINKING_ONLY, false);

    if (!ParseOpenLinkParams(env, info, linkValue, openLinkOptions, want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse openLink arguments failed");
        ThrowInvalidParamError(env,
            "Parse param link or openLinkOptions failed, link must be string, openLinkOptions must be options.");
        return CreateJsUndefined(env);
    }
    OnRequestResult onRequestSucc;
    OnRequestResult onRequestFail;
    if (CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object) &&
        AppExecFwk::UnwrapCommonCompletionHandler(env, info.argv[INDEX_ONE], onRequestSucc, onRequestFail)) {
        AddCompletionHandlerForOpenLink(want, onRequestSucc, onRequestFail);
    }

    want.SetUri(linkValue);
    std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
        system_clock::now().time_since_epoch()).count());
    want.SetParam(Want::PARAM_RESV_START_TIME, startTime);

    int requestCode = -1;
    if (CheckTypeForNapiValue(env, info.argv[INDEX_TWO], napi_function)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "async callback is used");
        CreateOpenLinkTask(env, info.argv[INDEX_TWO], want, requestCode);
    }
    return OnOpenLinkInner(env, want, requestCode, startTime, linkValue, openLinkOptions.GetHideFailureTipDialog());
}

napi_value JsAbilityContext::OnOpenLinkInner(napi_env env, const AAFwk::Want &want, int requestCode,
    const std::string &startTime, const std::string &url, bool hideFailureTipDialog)
{
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, innerErrCode, requestCode, hideFailureTipDialog]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->OpenLink(want, requestCode, hideFailureTipDialog);
        };
    napi_value result = nullptr;
    AddFreeInstallObserver(env, want, nullptr, &result, false, true);
    NapiAsyncTask::CompleteCallback complete = [want, innerErrCode, requestCode, startTime, url, weak = context_,
        observer = freeInstallObserver_](napi_env env, NapiAsyncTask& task, int32_t status) {
        if (*innerErrCode == 0) {
            TAG_LOGI(AAFwkTag::CONTEXT, "openLink succeeded");
            return;
        }
        auto context = weak.lock();
        if (context == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            return;
        }
        if (observer != nullptr) {
            if (*innerErrCode == AAFwk::ERR_OPEN_LINK_START_ABILITY_DEFAULT_OK) {
                TAG_LOGI(AAFwkTag::CONTEXT, "start ability by default succeeded");
                observer->OnInstallFinishedByUrl(startTime, url, ERR_OK);
                return;
            }
            observer->OnInstallFinishedByUrl(startTime, url, *innerErrCode);
            nlohmann::json jsonObject = nlohmann::json {
                { JSON_KEY_ERR_MSG, "Failed to call openLink" },
            };
            std::string requestId = want.GetStringParam(KEY_REQUEST_ID);
            context->OnOpenLinkRequestFailure(requestId, want.GetElement(), jsonObject.dump());
        }
        context->RemoveResultCallbackTask(requestCode);
    };

    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnOpenLink", env,
        CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), nullptr));

    return result;
}

napi_value JsAbilityContext::OnStartAbilityAsCallerInner(napi_env env, NapiCallbackInfo& info,
    const AAFwk::Want &want, size_t unwrapArgc, const AAFwk::StartOptions &startOptions)
{
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, want, startOptions, unwrapArgc, innerErrCode]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "context is released");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }
        *innerErrCode = (unwrapArgc == ARGC_ONE) ?
            context->StartAbilityAsCaller(want, -1) : context->StartAbilityAsCaller(want, startOptions, -1);
    };
    NapiAsyncTask::CompleteCallback complete =
        [weak = context_, innerErrCode, want, startOptions](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
                return;
            }
            if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
            auto context = weak.lock();
            if (context == nullptr) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                return;
            }
            if (!startOptions.requestId_.empty()) {
                nlohmann::json jsonObject = nlohmann::json {
                    { JSON_KEY_ERR_MSG, "Failed to call startAbilityAsCaller" }
                };
                context->OnRequestFailure(startOptions.requestId_, want.GetElement(), jsonObject.dump());
            }
        };

    napi_value lastParam = (info.argc > unwrapArgc) ? info.argv[unwrapArgc] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbilityAsCaller",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStartAbilityAsCaller(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);

    if (info.argc == ARGC_ZERO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    bool unWrapWantFlag = OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    if (!unWrapWantFlag) {
        ThrowInvalidParamError(env, "Parameter error: Parse want failed! Want must be a Want.");
        return CreateJsUndefined(env);
    }
    InheritWindowMode(want);
    decltype(info.argc) unwrapArgc = ARGC_ONE;
    TAG_LOGI(AAFwkTag::CONTEXT, "ability:%{public}s",
        want.GetElement().GetAbilityName().c_str());
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_ONE && CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start, options is used");
        AppExecFwk::UnwrapStartOptions(env, info.argv[INDEX_ONE], startOptions);
        UnwrapCompletionHandlerInStartOptions(env, info.argv[INDEX_ONE], startOptions);
        unwrapArgc++;
    }
    return OnStartAbilityAsCallerInner(env, info, want, unwrapArgc, startOptions);
}

napi_value JsAbilityContext::OnStartRecentAbility(napi_env env, NapiCallbackInfo& info)
{
    return OnStartAbility(env, info, true);
}

napi_value JsAbilityContext::OnStartAbilityWithAccount(napi_env env, NapiCallbackInfo& info)
{
    if (info.argc < ARGC_TWO) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::Want want;
    OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    InheritWindowMode(want);
    decltype(info.argc) unwrapArgc = ARGC_ONE;
    TAG_LOGI(AAFwkTag::CONTEXT, "ability:%{public}s",
        want.GetElement().GetAbilityName().c_str());
    int32_t accountId = 0;
    if (!OHOS::AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ONE], accountId)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "invalid second params");
        ThrowInvalidParamError(env, "Parse param accountId failed, accountId must be number.");
        return CreateJsUndefined(env);
    }
    unwrapArgc++;
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_TWO && CheckTypeForNapiValue(env, info.argv[INDEX_TWO], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start options is used");
        AppExecFwk::UnwrapStartOptions(env, info.argv[INDEX_TWO], startOptions);
        UnwrapCompletionHandlerInStartOptions(env, info.argv[INDEX_TWO], startOptions);
        unwrapArgc++;
    }

    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
            system_clock::now().time_since_epoch()).count());
        want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
    }

    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, accountId, startOptions, unwrapArgc, innerErrCode,
            &observer = freeInstallObserver_]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }

        *innerErrCode = (unwrapArgc == INDEX_TWO) ?
            context->StartAbilityWithAccount(want, accountId, -1) : context->StartAbilityWithAccount(
                want, accountId, startOptions, -1);
        if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND &&
            *innerErrCode != 0 && observer != nullptr) {
            std::string bundleName = want.GetElement().GetBundleName();
            std::string abilityName = want.GetElement().GetAbilityName();
            std::string startTime = want.GetStringParam(Want::PARAM_RESV_START_TIME);
            observer->OnInstallFinished(bundleName, abilityName, startTime, *innerErrCode);
        }
    };

    NapiAsyncTask::CompleteCallback complete = [weak = context_, innerErrCode, want, startOptions](
        napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == 0) {
                task.Resolve(env, CreateJsUndefined(env));
                return;
            }
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            auto context = weak.lock();
            if (context == nullptr) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                return;
            }
            if (!startOptions.requestId_.empty()) {
                nlohmann::json jsonObject = nlohmann::json {
                    { JSON_KEY_ERR_MSG, "Failed to call startAbilityWithAccount" }
                };
                context->OnRequestFailure(startOptions.requestId_, want.GetElement(), jsonObject.dump());
            }
    };
    napi_value lastParam = (info.argc > unwrapArgc) ? info.argv[unwrapArgc] : nullptr;
    napi_value result = nullptr;
    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        AddFreeInstallObserver(env, want, lastParam, &result);
        NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbilityWithAccount", env,
            CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), nullptr, nullptr));
    } else {
        NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbilityWithAccount", env,
            CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    }
    return result;
}

bool JsAbilityContext::CheckStartAbilityByCallParams(napi_env env, NapiCallbackInfo& info,
    AAFwk::Want &want, int32_t &userId, napi_value &lastParam)
{
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return false;
    }

    if (!CheckTypeForNapiValue(env, info.argv[INDEX_ZERO], napi_object) ||
        !AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return false;
    }

    InheritWindowMode(want);

    if (info.argc == ARGC_ONE) {
        return true;
    }
    bool paramOneIsNumber = CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_number);
    bool paramOneIsFunction = CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_function);
    if (!paramOneIsNumber && !paramOneIsFunction) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid input params");
        ThrowInvalidParamError(env, "Parse second param failed, second param must be callback or number.");
        return false;
    }
    if (paramOneIsNumber && !ConvertFromJsValue(env, info.argv[INDEX_ONE], userId)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse accountId failed");
        ThrowInvalidParamError(env, "Parse param accountId failed, accountId must be number.");
        return false;
    }
    if (paramOneIsFunction) {
        lastParam = info.argv[INDEX_ONE];
    }

    if (info.argc > ARGC_TWO && CheckTypeForNapiValue(env, info.argv[INDEX_TWO], napi_function)) {
        lastParam = info.argv[INDEX_TWO];
    }
    return true;
}

napi_value JsAbilityContext::OnStartAbilityByCall(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "OnStartAbilityByCall called");
    // 1. check params
    napi_value lastParam = nullptr;
    int32_t userId = DEFAULT_INVAL_VALUE;
    AAFwk::Want want;
    if (!CheckStartAbilityByCallParams(env, info, want, userId, lastParam)) {
        return CreateJsUndefined(env);
    }

    // 2. create CallBack function
    auto calls = std::make_shared<StartAbilityByCallParameters>();
    auto callerCallBack = std::make_shared<CallerCallBack>();
    GenerateCallerCallBack(calls, callerCallBack);
    auto callExecute = [calls, callerCallBack, want, weak = context_, userId] () {
        StartAbilityByCallExecuteDone(*calls, callerCallBack, want, weak, userId);
    };
    auto callComplete = [weak = context_, calldata = calls, callerCallBack] (
        napi_env env, NapiAsyncTask& task, int32_t status) {
        StartAbilityByCallComplete(env, task, weak, calldata, callerCallBack);
    };

    // 3. StartAbilityByCall
    napi_value retsult = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbilityByCall", env,
        CreateAsyncTaskWithLastParam(env, lastParam, std::move(callExecute), std::move(callComplete), &retsult));

    TAG_LOGD(AAFwkTag::CONTEXT, "OnStartAbilityByCall end");
    return retsult;
}

napi_value JsAbilityContext::OnStartAbilityForResult(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");

    if (info.argc == ARGC_ZERO) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    InheritWindowMode(want);
    decltype(info.argc) unwrapArgc = ARGC_ONE;
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_ONE && CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start, options is used");
        AppExecFwk::UnwrapStartOptions(env, info.argv[INDEX_ONE], startOptions);
        UnwrapCompletionHandlerInStartOptions(env, info.argv[INDEX_ONE], startOptions);
        unwrapArgc++;
    }

    napi_value lastParam = info.argc > unwrapArgc ? info.argv[unwrapArgc] : nullptr;
    napi_value result = nullptr;
    std::unique_ptr<NapiAsyncTask> uasyncTask;
    std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
        system_clock::now().time_since_epoch()).count());
    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
        AddFreeInstallObserver(env, want, lastParam, &result, true);
        uasyncTask = CreateAsyncTaskWithLastParam(env, nullptr, nullptr, nullptr, nullptr);
    } else {
        uasyncTask = CreateAsyncTaskWithLastParam(env, lastParam, nullptr, nullptr, &result);
    }
    std::shared_ptr<NapiAsyncTask> asyncTask = std::move(uasyncTask);
    RuntimeTask task = [env, asyncTask, element = want.GetElement(), flags = want.GetFlags(), startTime,
        &observer = freeInstallObserver_]
        (int resultCode, const AAFwk::Want& want, bool isInner) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start async callback");
        HandleScope handleScope(env);
        std::string bundleName = element.GetBundleName();
        std::string abilityName = element.GetAbilityName();
        napi_value abilityResult = AppExecFwk::WrapAbilityResult(env, resultCode, want);
        if (abilityResult == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null abilityResult");
            isInner = true;
            resultCode = ERR_INVALID_VALUE;
        }
        bool freeInstallEnable = (flags & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND &&
            observer != nullptr;
        if (freeInstallEnable) {
            isInner ? observer->OnInstallFinished(bundleName, abilityName, startTime, resultCode) :
                observer->OnInstallFinished(bundleName, abilityName, startTime, abilityResult);
        } else {
            isInner ? asyncTask->Reject(env, CreateJsErrorByNativeErr(env, resultCode)) :
                asyncTask->Resolve(env, abilityResult);
        }
    };
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null context");
        asyncTask->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
    } else {
        want.SetParam(Want::PARAM_RESV_FOR_RESULT, true);
        auto requestCode = GenerateRequestCode();
        (unwrapArgc == ARGC_ONE) ? context->StartAbilityForResult(want, requestCode, std::move(task)) :
            context->StartAbilityForResult(want, startOptions, requestCode, std::move(task));
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::OnStartAbilityForResultWithAccount(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    auto selfToken = IPCSkeleton::GetSelfTokenID();
    if (!Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(selfToken)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "non system app forbidden to call");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_NOT_SYSTEM_APP);
        return CreateJsUndefined(env);
    }
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    InheritWindowMode(want);
    decltype(info.argc) unwrapArgc = ARGC_ONE;
    int32_t accountId = 0;
    if (!OHOS::AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ONE], accountId)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid second params");
        ThrowInvalidParamError(env, "Parse param accountId failed, accountId must be number.");
        return CreateJsUndefined(env);
    }
    unwrapArgc++;
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_TWO && CheckTypeForNapiValue(env, info.argv[INDEX_TWO], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start options is used");
        AppExecFwk::UnwrapStartOptions(env, info.argv[INDEX_TWO], startOptions);
        UnwrapCompletionHandlerInStartOptions(env, info.argv[INDEX_TWO], startOptions);
        unwrapArgc++;
    }
    napi_value lastParam = info.argc > unwrapArgc ? info.argv[unwrapArgc] : nullptr;
    napi_value result = nullptr;
    std::unique_ptr<NapiAsyncTask> uasyncTask;
    std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
        system_clock::now().time_since_epoch()).count());
    if ((want.GetFlags() & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND) {
        want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
        AddFreeInstallObserver(env, want, lastParam, &result, true);
        uasyncTask = CreateAsyncTaskWithLastParam(env, lastParam, nullptr, nullptr, nullptr);
    } else {
        uasyncTask = CreateAsyncTaskWithLastParam(env, lastParam, nullptr, nullptr, &result);
    }
    std::shared_ptr<NapiAsyncTask> asyncTask = std::move(uasyncTask);
    RuntimeTask task = [env, asyncTask, element = want.GetElement(), flags = want.GetFlags(), startTime,
        &observer = freeInstallObserver_]
        (int resultCode, const AAFwk::Want& want, bool isInner) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start async callback");
        std::string bundleName = element.GetBundleName();
        std::string abilityName = element.GetAbilityName();
        HandleScope handleScope(env);
        napi_value abilityResult = AppExecFwk::WrapAbilityResult(env, resultCode, want);
        if (abilityResult == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null abilityResult");
            isInner = true;
            resultCode = ERR_INVALID_VALUE;
        }
        bool freeInstallEnable = (flags & Want::FLAG_INSTALL_ON_DEMAND) == Want::FLAG_INSTALL_ON_DEMAND &&
            observer != nullptr;
        if (freeInstallEnable) {
            isInner ? observer->OnInstallFinished(bundleName, abilityName, startTime, resultCode) :
                observer->OnInstallFinished(bundleName, abilityName, startTime, abilityResult);
        } else {
            isInner ? asyncTask->Reject(env, CreateJsErrorByNativeErr(env, resultCode)) :
                asyncTask->Resolve(env, abilityResult);
        }
        TAG_LOGD(AAFwkTag::CONTEXT, "finish async callback");
    };
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null context");
        asyncTask->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
    } else {
        auto requestCode = GenerateRequestCode();
        (unwrapArgc == INDEX_TWO) ? context->StartAbilityForResultWithAccount(
            want, accountId, requestCode, std::move(task)) : context->StartAbilityForResultWithAccount(
                want, accountId, startOptions, requestCode, std::move(task));
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::OnStartExtensionAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return StartExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::SERVICE);
}

napi_value JsAbilityContext::StartExtensionAbilityCommon(napi_env env, NapiCallbackInfo& info,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, innerErrCode, extensionType]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->StartExtensionAbilityWithExtensionType(want, extensionType);
    };

    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::StartExtensionAbilityCommon",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStartExtensionAbilityWithAccount(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "param too few");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    int32_t accountId = -1;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want) ||
        !OHOS::AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ONE], accountId)) {
        ThrowInvalidParamError(env, "Parse param accountId failed, accountId must be number.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, accountId, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->StartServiceExtensionAbility(want, accountId);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_TWO) ? info.argv[INDEX_TWO] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartExtensionAbilityWithAccount",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStopExtensionAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return StopExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::SERVICE);
}

napi_value JsAbilityContext::StopExtensionAbilityCommon(napi_env env, NapiCallbackInfo& info,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "param too few");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, innerErrCode, extensionType]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->StopExtensionAbilityWithExtensionType(want, extensionType);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::Schedule("JsAbilityContext::StopExtensionAbilityCommon",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStopExtensionAbilityWithAccount(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "param too few");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    int32_t accountId = -1;
    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want) ||
        !AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ONE], accountId)) {
        ThrowInvalidParamError(env,
            "Parse param want or accountId failed, want must be Want and accountId must be number.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, accountId, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->StopServiceExtensionAbility(want, accountId);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_TWO) ? info.argv[INDEX_TWO] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::Schedule("JsAbilityContext::OnStopExtensionAbilityWithAccount",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnTerminateSelfWithResult(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");

    if (info.argc == ARGC_ZERO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    int resultCode = 0;
    AAFwk::Want want;
    if (!AppExecFwk::UnWrapAbilityResult(env, info.argv[INDEX_ZERO], resultCode, want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse ability result failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }

    auto abilityContext = context_.lock();
    if (abilityContext != nullptr) {
        abilityContext->SetTerminating(true);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, resultCode, innerErrCode]() {
            TAG_LOGD(AAFwkTag::CONTEXT, "async terminateSelfWithResult ");
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->TerminateAbilityWithResult(want, resultCode);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnTerminateSelfWithResult",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::OnBackToCallerAbilityWithResult(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "start");
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid argc");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    int32_t resultCode = 0;
    AAFwk::Want want;
    if (!AppExecFwk::UnWrapAbilityResult(env, info.argv[INDEX_ZERO], resultCode, want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse ability result failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }

    std::string requestCodeStr;
    if (!OHOS::AppExecFwk::UnwrapStringFromJS2(env, info.argv[INDEX_ONE], requestCodeStr)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid requestCode");
        ThrowInvalidParamError(env, "Parse param requestCode failed, requestCode must be string.");
        return CreateJsUndefined(env);
    }
    auto requestCode = RequestCodeFromStringToInt64(requestCodeStr);
    TAG_LOGD(AAFwkTag::CONTEXT, "requestCode: %{public}s", requestCodeStr.c_str());

    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, want, resultCode, requestCode, innerErrCode]() {
        TAG_LOGI(AAFwkTag::CONTEXT, "async execute");
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }

        *innerErrCode = context->BackToCallerAbilityWithResult(want, resultCode, requestCode);
    };

    NapiAsyncTask::CompleteCallback complete = [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
        HandleScope handleScope(env);
        (*innerErrCode == ERR_OK) ? task.ResolveWithNoError(env, CreateJsUndefined(env)) :
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
    };
    // only support promise method
    napi_value lastParam = nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnBackToCallerAbilityWithResult",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnConnectAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return ConnectExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::SERVICE);
}

napi_value JsAbilityContext::ConnectExtensionAbilityCommon(napi_env env, NapiCallbackInfo& info,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    // only support two params
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid argc");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    
    std::string proNameNotFilter = "";
    auto selfToken = IPCSkeleton::GetSelfTokenID();
    if (Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(selfToken) &&
        extensionType == AppExecFwk::ExtensionAbilityType::SERVICE) {
        proNameNotFilter = Want::PARAM_RESV_DISPLAY_ID;
        TAG_LOGI(AAFwkTag::CONTEXT, "don't filter displayId");
    }
    // unwrap want
    AAFwk::Want want;
    OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want, proNameNotFilter);
    TAG_LOGD(AAFwkTag::CONTEXT, "callee:%{public}s.%{public}s",
        want.GetBundle().c_str(),
        want.GetElement().GetAbilityName().c_str());

    // unwarp connection
    sptr<JSAbilityConnection> connection = new JSAbilityConnection(env);
    connection->SetJsConnectionObject(info.argv[INDEX_ONE]);
    int64_t connectId = InsertConnection(connection, want);
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, connection, connectId, innerErrCode, extensionType]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGE(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            TAG_LOGD(AAFwkTag::CONTEXT, "connectAbility: %{public}d, extensionType: type: %{public}d",
                static_cast<int32_t>(connectId), static_cast<int32_t>(extensionType));
            *innerErrCode = context->ConnectExtensionAbilityWithExtensionType(want, connection, extensionType);
    };
    NapiAsyncTask::CompleteCallback complete =
        [connection, connectId, innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                RemoveConnection(connectId);
            } else {
                int32_t errcode = static_cast<int32_t>(AbilityRuntime::GetJsErrorCodeByNativeError(*innerErrCode));
                if (errcode) {
                    connection->CallJsFailed(errcode);
                    RemoveConnection(connectId);
                }
                task.Resolve(env, CreateJsUndefined(env));
            }
        };
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::ConnectExtensionAbilityCommon",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return CreateJsValue(env, connectId);
}

napi_value JsAbilityContext::OnConnectAbilityWithAccount(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    // only support three params
    if (info.argc < ARGC_THREE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    auto selfToken = IPCSkeleton::GetSelfTokenID();
    if (!Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(selfToken)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "non system app forbidden to call");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_NOT_SYSTEM_APP);
        return CreateJsUndefined(env);
    }
    // unwrap want
    AAFwk::Want want;
    OHOS::AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    TAG_LOGI(AAFwkTag::CONTEXT, "bundleName:%{public}s abilityName:%{public}s",
        want.GetBundle().c_str(), want.GetElement().GetAbilityName().c_str());

    int32_t accountId = 0;
    if (!OHOS::AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ONE], accountId)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid second params");
        ThrowInvalidParamError(env, "Parse param accountId failed, accountId must be number.");
        return CreateJsUndefined(env);
    }

    // unwarp connection
    sptr<JSAbilityConnection> connection = new JSAbilityConnection(env);
    connection->SetJsConnectionObject(info.argv[INDEX_TWO]);
    int64_t connectId = InsertConnection(connection, want, accountId);
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, accountId, connection, connectId, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGE(AAFwkTag::CONTEXT, "context is released");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            TAG_LOGI(AAFwkTag::CONTEXT, "context->ConnectAbilityWithAccount connection:%{public}d",
                static_cast<int32_t>(connectId));
            *innerErrCode = context->ConnectAbilityWithAccount(want, accountId, connection);
    };
    NapiAsyncTask::CompleteCallback complete =
        [connectId, connection, innerErrCode](
            napi_env env, NapiAsyncTask& task, int32_t status) {
                HandleScope handleScope(env);
                if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                    task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                    RemoveConnection(connectId);
                } else {
                    int32_t errcode = static_cast<int32_t>(AbilityRuntime::GetJsErrorCodeByNativeError(*innerErrCode));
                    if (errcode) {
                        connection->CallJsFailed(errcode);
                        RemoveConnection(connectId);
                    }
                    task.Resolve(env, CreateJsUndefined(env));
                }
        };
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnConnectAbilityWithAccount",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return CreateJsValue(env, connectId);
}

napi_value JsAbilityContext::OnDisconnectAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    std::lock_guard<std::recursive_mutex> lock(gConnectsLock_);
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    // unwrap want and connectId
    AAFwk::Want want;
    int64_t connectId = -1;
    sptr<JSAbilityConnection> connection = nullptr;
    int32_t accountId = -1;
    napi_get_value_int64(env, info.argv[INDEX_ZERO], &connectId);
    TAG_LOGI(AAFwkTag::CONTEXT, "connection:%{public}d", static_cast<int32_t>(connectId));
    auto item = std::find_if(g_connects.begin(),
        g_connects.end(),
        [&connectId](const auto &obj) {
            return connectId == obj.first.id;
        });
    if (item != g_connects.end()) {
        // match id
        want = item->first.want;
        connection = item->second;
        accountId = item->first.accountId;
    } else {
        TAG_LOGI(AAFwkTag::CONTEXT, "not find conn exist");
    }
    // begin disconnect
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, want, connection, accountId, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            if (!connection) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null connection");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INNER);
                return;
            }
            TAG_LOGD(AAFwkTag::CONTEXT, "context->DisconnectAbility");
            context->DisconnectAbility(want, connection, accountId);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                return;
            }
            if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INNER)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
                return;
            }
            task.Resolve(env, CreateJsUndefined(env));
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::Schedule("JsAbilityContext::OnDisconnectAbility",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnTerminateSelf(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    auto abilityContext = context_.lock();
    if (abilityContext != nullptr) {
        abilityContext->SetTerminating(true);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, innerErrCode]() {
            TAG_LOGI(AAFwkTag::CONTEXT, "async terminate self");
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }

            *innerErrCode = context->TerminateSelf();
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ZERO) ? info.argv[INDEX_ZERO] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnTerminateSelf",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnRestoreWindowStage(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called, info.argc = %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "need one params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    auto context = context_.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
        return CreateJsUndefined(env);
    }
    auto errcode = context->RestoreWindowStage(env, info.argv[INDEX_ZERO]);
    if (errcode != 0) {
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INNER);
        return CreateJsError(env, errcode, "restoreWindowStage failed");
    }
    return CreateJsUndefined(env);
}

napi_value JsAbilityContext::OnRequestDialogService(napi_env env, NapiCallbackInfo& info)
{
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::Want want;
    AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want);
    TAG_LOGD(AAFwkTag::CONTEXT, "target:%{public}s.%{public}s", want.GetBundle().c_str(),
        want.GetElement().GetAbilityName().c_str());

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    auto uasyncTask = CreateAsyncTaskWithLastParam(env, lastParam, nullptr, nullptr, &result);
    std::shared_ptr<NapiAsyncTask> asyncTask = std::move(uasyncTask);
    RequestDialogResultTask task =
        [env, asyncTask](int32_t resultCode, const AAFwk::Want &resultWant) {
        HandleScope handleScope(env);
        napi_value requestResult = JsAbilityContext::WrapRequestDialogResult(env, resultCode, resultWant);
        if (requestResult == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null requestResult");
            asyncTask->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
        } else {
            asyncTask->Resolve(env, requestResult);
        }
        TAG_LOGD(AAFwkTag::CONTEXT, "end async callback");
    };
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null context");
        asyncTask->Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
    } else {
        auto errCode = context->RequestDialogService(env, want, std::move(task));
        if (errCode != ERR_OK) {
            asyncTask->Reject(env, CreateJsError(env, GetJsErrorCodeByNativeError(errCode)));
        }
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::OnIsTerminating(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
        return CreateJsUndefined(env);
    }
    return CreateJsValue(env, context->IsTerminating());
}

napi_value JsAbilityContext::OnReportDrawnCompleted(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, innerErrCode]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }

        *innerErrCode = context->ReportDrawnCompleted();
    };

    NapiAsyncTask::CompleteCallback complete = [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
        HandleScope handleScope(env);
        (*innerErrCode == ERR_OK) ? task.Resolve(env, CreateJsUndefined(env)) :
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
    };

    napi_value lastParam = info.argv[INDEX_ZERO];
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnReportDrawnCompleted",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStartSelfUIAbilityInCurrentProcess(napi_env env, NapiCallbackInfo &info)
{
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }

    std::string specifiedFlag;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ONE], specifiedFlag)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse specifiedFlag failed");
        ThrowInvalidParamError(env, "Parse param specifiedFlag failed, specifiedFlag must be string.");
        return CreateJsUndefined(env);
    }

    size_t unwrapArgc = ARGC_TWO;
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_TWO && CheckTypeForNapiValue(env, info.argv[INDEX_TWO], napi_object)) {
        if (!AppExecFwk::UnwrapStartOptionsWithProcessOption(env, info.argv[INDEX_TWO], startOptions)) {
            TAG_LOGE(AAFwkTag::CONTEXT, "invalid startOptions");
            ThrowInvalidParamError(env, "Parse param startOptions failed, startOptions must be StartOption.");
            return CreateJsUndefined(env);
        }
        unwrapArgc++;
    }

    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, want, specifiedFlag, unwrapArgc,
        startOptions, innerErrCode]() {
        TAG_LOGI(AAFwkTag::CONTEXT, "async execute");
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int32_t>(AAFwk::ERR_INVALID_CONTEXT);
            return;
        }

        *innerErrCode = (unwrapArgc == ARGC_TWO) ? context->StartSelfUIAbilityInCurrentProcess(want, specifiedFlag,
            startOptions, false) : context->StartSelfUIAbilityInCurrentProcess(want, specifiedFlag, startOptions, true);
    };

    NapiAsyncTask::CompleteCallback complete = [innerErrCode](napi_env env, NapiAsyncTask &task, int32_t status) {
        HandleScope handleScope(env);
        (*innerErrCode == ERR_OK) ? task.ResolveWithNoError(env, CreateJsUndefined(env)) :
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
    };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartSelfUIAbilityInCurrentProcess",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::WrapRequestDialogResult(napi_env env,
    int32_t resultCode, const AAFwk::Want &want)
{
    napi_value object = nullptr;
    napi_create_object(env, &object);
    if (!CheckTypeForNapiValue(env, object, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "get object failed");
        return nullptr;
    }

    napi_set_named_property(env, object, "result", CreateJsValue(env, resultCode));
    napi_set_named_property(env, object, "want", AppExecFwk::WrapWant(env, want));
    return object;
}

void JsAbilityContext::InheritWindowMode(AAFwk::Want &want)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
#ifdef SUPPORT_SCREEN
    // only split mode need inherit
    auto context = context_.lock();
    if (!context) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        return;
    }
    auto windowMode = context->GetCurrentWindowMode();
    if (AAFwk::AppUtils::GetInstance().IsInheritWindowSplitScreenMode() &&
        (windowMode == AAFwk::AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_PRIMARY ||
        windowMode == AAFwk::AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_SECONDARY)) {
        want.SetParam(Want::PARAM_RESV_WINDOW_MODE, windowMode);
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "window mode is %{public}d", windowMode);
#endif
}

void JsAbilityContext::ConfigurationUpdated(napi_env env, napi_value object,
    const std::shared_ptr<AppExecFwk::Configuration> &config)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    if (object == nullptr || config == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null jsContext");
        return;
    }

    if (!CheckTypeForNapiValue(env, object, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "get object failed");
        return;
    }

    napi_value method = nullptr;
    napi_get_named_property(env, object, "onUpdateConfiguration", &method);
    if (method == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null method");
        return;
    }

    napi_value argv[] = {CreateJsConfiguration(env, *config)};
    napi_call_function(env, object, method, ARGC_ONE, argv, nullptr);
}

void JsAbilityContext::AddFreeInstallObserver(napi_env env, const AAFwk::Want &want, napi_value callback,
    napi_value *result, bool isAbilityResult, bool isOpenLink)
{
    // adapter free install async return install and start result
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    int ret = 0;
    if (freeInstallObserver_ == nullptr) {
        freeInstallObserver_ = new JsFreeInstallObserver(env);
        auto context = context_.lock();
        if (!context) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null context");
            return;
        }
        ret = context->AddFreeInstallObserver(freeInstallObserver_);
    }

    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::CONTEXT, "addFreeInstallObserver error");
    }
    std::string startTime = want.GetStringParam(Want::PARAM_RESV_START_TIME);
    if (!isOpenLink) {
        TAG_LOGI(AAFwkTag::CONTEXT, "addJsObserver");
        std::string bundleName = want.GetElement().GetBundleName();
        std::string abilityName = want.GetElement().GetAbilityName();
        freeInstallObserver_->AddJsObserverObject(
            bundleName, abilityName, startTime, callback, result, isAbilityResult);
        return;
    }
    std::string url = want.GetUriString();
    freeInstallObserver_->AddJsObserverObject(startTime, url, callback, result, isAbilityResult);
}

napi_value CreateJsAbilityContext(napi_env env, std::shared_ptr<AbilityContext> context)
{
    napi_value object = CreateJsBaseContext(env, context);

    std::unique_ptr<JsAbilityContext> jsContext = std::make_unique<JsAbilityContext>(context);
    napi_wrap(env, object, jsContext.release(), JsAbilityContext::Finalizer, nullptr, nullptr);

    auto abilityInfo = context->GetAbilityInfo();
    if (abilityInfo != nullptr) {
        napi_set_named_property(env, object, "abilityInfo", CreateJsAbilityInfo(env, *abilityInfo));
    }

    auto configuration = context->GetConfiguration();
    if (configuration != nullptr) {
        napi_set_named_property(env, object, "config", CreateJsConfiguration(env, *configuration));
    }

    std::string type = "UIAbilityContext";
    napi_set_named_property(env, object, "contextType", CreateJsValue(env, type));

    const char *moduleName = "JsAbilityContext";
    BindNativeFunction(env, object, "startAbility", moduleName, JsAbilityContext::StartAbility);
    BindNativeFunction(env, object, "openLink", moduleName, JsAbilityContext::OpenLink);
    BindNativeFunction(env, object, "startAbilityAsCaller", moduleName, JsAbilityContext::StartAbilityAsCaller);
    BindNativeFunction(env, object, "startAbilityWithAccount", moduleName,
        JsAbilityContext::StartAbilityWithAccount);
    BindNativeFunction(env, object, "startAbilityByCall", moduleName, JsAbilityContext::StartAbilityByCall);
    BindNativeFunction(env, object, "startAbilityForResult", moduleName, JsAbilityContext::StartAbilityForResult);
    BindNativeFunction(env, object, "startAbilityForResultWithAccount", moduleName,
        JsAbilityContext::StartAbilityForResultWithAccount);
    BindNativeFunction(env, object, "startServiceExtensionAbility", moduleName,
        JsAbilityContext::StartServiceExtensionAbility);
    BindNativeFunction(env, object, "startServiceExtensionAbilityWithAccount", moduleName,
        JsAbilityContext::StartServiceExtensionAbilityWithAccount);
    BindNativeFunction(env, object, "stopServiceExtensionAbility", moduleName,
        JsAbilityContext::StopServiceExtensionAbility);
    BindNativeFunction(env, object, "stopServiceExtensionAbilityWithAccount", moduleName,
        JsAbilityContext::StopServiceExtensionAbilityWithAccount);
    BindNativeFunction(env, object, "connectServiceExtensionAbility", moduleName, JsAbilityContext::ConnectAbility);
    BindNativeFunction(env, object, "connectAbilityWithAccount", moduleName,
        JsAbilityContext::ConnectAbilityWithAccount);
    BindNativeFunction(env, object, "connectServiceExtensionAbilityWithAccount", moduleName,
        JsAbilityContext::ConnectAbilityWithAccount);
    BindNativeFunction(env, object, "disconnectAbility", moduleName, JsAbilityContext::DisconnectAbility);
    BindNativeFunction(
        env, object, "disconnectServiceExtensionAbility", moduleName, JsAbilityContext::DisconnectAbility);
    BindNativeFunction(env, object, "terminateSelf", moduleName, JsAbilityContext::TerminateSelf);
    BindNativeFunction(env, object, "terminateSelfWithResult", moduleName,
        JsAbilityContext::TerminateSelfWithResult);
    BindNativeFunction(env, object, "backToCallerAbilityWithResult", moduleName,
        JsAbilityContext::BackToCallerAbilityWithResult);
    BindNativeFunction(env, object, "restoreWindowStage", moduleName, JsAbilityContext::RestoreWindowStage);
    BindNativeFunction(env, object, "isTerminating", moduleName, JsAbilityContext::IsTerminating);
    BindNativeFunction(env, object, "startRecentAbility", moduleName,
        JsAbilityContext::StartRecentAbility);
    BindNativeFunction(env, object, "requestDialogService", moduleName,
        JsAbilityContext::RequestDialogService);
    BindNativeFunction(env, object, "reportDrawnCompleted", moduleName,
        JsAbilityContext::ReportDrawnCompleted);
    BindNativeFunction(env, object, "setMissionContinueState", moduleName,
        JsAbilityContext::SetMissionContinueState);
    BindNativeFunction(env, object, "startAbilityByType", moduleName,
        JsAbilityContext::StartAbilityByType);
    BindNativeFunction(env, object, "requestModalUIExtension", moduleName,
        JsAbilityContext::RequestModalUIExtension);
    BindNativeFunction(env, object, "showAbility", moduleName,
        JsAbilityContext::ShowAbility);
    BindNativeFunction(env, object, "hideAbility", moduleName,
        JsAbilityContext::HideAbility);
    BindNativeFunction(env, object, "moveAbilityToBackground", moduleName, JsAbilityContext::MoveAbilityToBackground);
    BindNativeFunction(env, object, "openAtomicService", moduleName, JsAbilityContext::OpenAtomicService);
    BindNativeFunction(env, object, "startUIServiceExtensionAbility", moduleName,
        JsAbilityContext::StartUIServiceExtension);
    BindNativeFunction(env, object, "connectUIServiceExtensionAbility", moduleName,
        JsAbilityContext::ConnectUIServiceExtension);
    BindNativeFunction(env, object, "disconnectUIServiceExtensionAbility", moduleName,
        JsAbilityContext::DisconnectUIServiceExtension);
    BindNativeFunction(env, object, "setRestoreEnabled", moduleName, JsAbilityContext::SetRestoreEnabled);
    BindNativeFunction(env, object, "setColorMode", moduleName, JsAbilityContext::SetColorMode);
    BindNativeFunction(env, object, "revokeDelegator", moduleName, JsAbilityContext::RevokeDelegator);

#ifdef SUPPORT_GRAPHICS
    BindNativeFunction(env, object, "setMissionLabel", moduleName, JsAbilityContext::SetMissionLabel);
    BindNativeFunction(env, object, "setMissionIcon", moduleName, JsAbilityContext::SetMissionIcon);
    BindNativeFunction(env, object, "setAbilityInstanceInfo", moduleName, JsAbilityContext::SetAbilityInstanceInfo);
#endif
    BindNativeFunction(env, object, "startAppServiceExtensionAbility", moduleName,
        JsAbilityContext::StartAppServiceExtensionAbility);
    BindNativeFunction(env, object, "stopAppServiceExtensionAbility", moduleName,
        JsAbilityContext::StopAppServiceExtensionAbility);
    BindNativeFunction(env, object, "connectAppServiceExtensionAbility", moduleName,
        JsAbilityContext::ConnectAppServiceExtensionAbility);
    BindNativeFunction(env, object, "disconnectAppServiceExtensionAbility", moduleName,
        JsAbilityContext::DisconnectAppServiceExtensionAbility);
    BindNativeFunction(env, object, "setOnNewWantSkipScenarios", moduleName,
        JsAbilityContext::SetOnNewWantSkipScenarios);
    BindNativeFunction(env, object, "startSelfUIAbilityInCurrentProcess", moduleName,
        JsAbilityContext::StartSelfUIAbilityInCurrentProcess);
    BindNativeFunction(env, object, "restartApp", moduleName,
        JsAbilityContext::RestartAppWithWindow);
    BindNativeFunction(env, object, "setMissionWindowIcon", moduleName, JsAbilityContext::SetMissionWindowIcon);
    return object;
}

napi_value AttachJsUIAbilityContext(napi_env env, void *value, void *hint)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "attach uiability context");
    if (env == nullptr || value == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "invalid params");
        return nullptr;
    }
    auto ptr = reinterpret_cast<std::weak_ptr<AbilityContext> *>(value)->lock();
    if (ptr == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null ptr");
        return nullptr;
    }

    auto object = CreateJsAbilityContext(env, ptr);
    if (object == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null object");
        return nullptr;
    }
    auto systemModule = JsRuntime::LoadSystemModuleByEngine(env, "application.AbilityContext", &object, 1);
    if (systemModule == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null systemModule");
        return nullptr;
    }
    auto contextObj = systemModule->GetNapiValue();
    if (!CheckTypeForNapiValue(env, contextObj, napi_object)) {
        TAG_LOGW(AAFwkTag::CONTEXT, "not napi object");
        return nullptr;
    }

    auto workContext = new (std::nothrow) std::weak_ptr<AbilityContext>(ptr);
    auto status = napi_coerce_to_native_binding_object(
        env, contextObj, DetachNewAbilityContext, AttachJsUIAbilityContext, workContext, nullptr);
    if (status != napi_ok) {
        TAG_LOGW(AAFwkTag::CONTEXT, "coerce ability context failed: %{public}d", status);
        delete workContext;
        return nullptr;
    }
    napi_add_detached_finalizer(env, contextObj, DetachFinalizeAbilityContext, nullptr);
    status = napi_wrap(env, contextObj, workContext,
        [](napi_env, void *data, void*) {
            TAG_LOGD(AAFwkTag::CONTEXT, "finalizer for weak_ptr ui ability context");
            delete static_cast<std::weak_ptr<AbilityContext> *>(data);
        },
        nullptr, nullptr);
    if (status != napi_ok) {
        TAG_LOGW(AAFwkTag::CONTEXT, "wrap ability context failed: %{public}d", status);
        delete workContext;
        return nullptr;
    }

    return contextObj;
}

JSAbilityConnection::JSAbilityConnection(napi_env env) : env_(env) {}

JSAbilityConnection::~JSAbilityConnection()
{
    ReleaseNativeReference(jsConnectionObject_.release());
}

void JSAbilityConnection::ReleaseNativeReference(NativeReference* ref)
{
    if (ref == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null ref");
        return;
    }
    uv_loop_t *loop = nullptr;
    napi_get_uv_event_loop(env_, &loop);
    if (loop == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null loop");
        delete ref;
        return;
    }
    uv_work_t *work = new (std::nothrow) uv_work_t;
    if (work == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null work");
        delete ref;
        return;
    }
    work->data = reinterpret_cast<void *>(ref);
    int ret = uv_queue_work(loop, work, [](uv_work_t *work) {},
        [](uv_work_t *work, int status) {
        if (work == nullptr) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null work");
            return;
        }
        if (work->data == nullptr) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null data");
            delete work;
            work = nullptr;
            return;
        }
        NativeReference *refPtr = reinterpret_cast<NativeReference *>(work->data);
        delete refPtr;
        refPtr = nullptr;
        delete work;
        work = nullptr;
    });
    if (ret != 0) {
        delete ref;
        if (work != nullptr) {
            delete work;
            work = nullptr;
        }
    }
}

void JSAbilityConnection::SetConnectionId(int64_t id)
{
    connectionId_ = id;
}

void JSAbilityConnection::OnAbilityConnectDone(const AppExecFwk::ElementName &element,
    const sptr<IRemoteObject> &remoteObject, int resultCode)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "resultCode:%{public}d", resultCode);
    wptr<JSAbilityConnection> connection = this;
    std::unique_ptr<NapiAsyncTask::CompleteCallback> complete = std::make_unique<NapiAsyncTask::CompleteCallback>
        ([connection, element, remoteObject, resultCode](napi_env env, NapiAsyncTask &task, int32_t status) {
            sptr<JSAbilityConnection> connectionSptr = connection.promote();
            if (!connectionSptr) {
                TAG_LOGE(AAFwkTag::CONTEXT, "null connectionSptr");
                return;
            }
            connectionSptr->HandleOnAbilityConnectDone(element, remoteObject, resultCode);
        });

    napi_ref callback = nullptr;
    std::unique_ptr<NapiAsyncTask::ExecuteCallback> execute = nullptr;
    NapiAsyncTask::Schedule("JSAbilityConnection::OnAbilityConnectDone",
        env_, std::make_unique<NapiAsyncTask>(callback, std::move(execute), std::move(complete)));
}

void JSAbilityConnection::HandleOnAbilityConnectDone(const AppExecFwk::ElementName &element,
    const sptr<IRemoteObject> &remoteObject, int resultCode)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "resultCode:%{public}d", resultCode);
    if (jsConnectionObject_ == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null jsConnectionObject_");
        return;
    }
    napi_value obj = jsConnectionObject_->GetNapiValue();
    if (!CheckTypeForNapiValue(env_, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "get object failed");
        return;
    }
    napi_value methodOnConnect = nullptr;
    napi_get_named_property(env_, obj, "onConnect", &methodOnConnect);
    if (methodOnConnect == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null methodOnConnect");
        return;
    }

    // wrap RemoteObject
    napi_value napiRemoteObject = NAPI_ohos_rpc_CreateJsRemoteObject(env_, remoteObject);
    napi_value argv[] = { ConvertElement(element), napiRemoteObject };
    TAG_LOGI(AAFwkTag::CONTEXT, "Call onConnect");
    napi_status status = napi_call_function(env_, obj, methodOnConnect, ARGC_TWO, argv, nullptr);
    if (status != napi_ok) {
        TAG_LOGE(AAFwkTag::CONTEXT, "call js func failed %{public}d", status);
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
}

void JSAbilityConnection::OnAbilityDisconnectDone(const AppExecFwk::ElementName &element, int resultCode)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "resultCode:%{public}d", resultCode);
    wptr<JSAbilityConnection> connection = this;
    std::unique_ptr<NapiAsyncTask::CompleteCallback> complete = std::make_unique<NapiAsyncTask::CompleteCallback>
        ([connection, element, resultCode](napi_env env, NapiAsyncTask &task, int32_t status) {
            sptr<JSAbilityConnection> connectionSptr = connection.promote();
            if (!connectionSptr) {
                TAG_LOGI(AAFwkTag::CONTEXT, "null connectionSptr");
                return;
            }
            connectionSptr->HandleOnAbilityDisconnectDone(element, resultCode);
        });
    napi_ref callback = nullptr;
    std::unique_ptr<NapiAsyncTask::ExecuteCallback> execute = nullptr;
    NapiAsyncTask::Schedule("JSAbilityConnection::OnAbilityDisconnectDone",
        env_, std::make_unique<NapiAsyncTask>(callback, std::move(execute), std::move(complete)));
}

void JSAbilityConnection::HandleOnAbilityDisconnectDone(const AppExecFwk::ElementName &element,
    int resultCode)
{
    std::lock_guard<std::recursive_mutex> lock(gConnectsLock_);
    TAG_LOGD(AAFwkTag::CONTEXT, "resultCode:%{public}d", resultCode);
    if (jsConnectionObject_ == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null jsConnectionObject_");
        return;
    }

    napi_value obj = jsConnectionObject_->GetNapiValue();
    if (!CheckTypeForNapiValue(env_, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "get object failed");
        return;
    }

    napi_value method = nullptr;
    napi_get_named_property(env_, obj, "onDisconnect", &method);
    if (method == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null method");
        return;
    }

    // release connect
    TAG_LOGD(AAFwkTag::CONTEXT, "start, g_connects.size:%{public}zu", g_connects.size());
    std::string bundleName = element.GetBundleName();
    std::string abilityName = element.GetAbilityName();
    auto item = std::find_if(g_connects.begin(), g_connects.end(),
        [bundleName, abilityName, connectionId = connectionId_] (
            const auto &obj) {
                return (bundleName == obj.first.want.GetBundle()) &&
                    (abilityName == obj.first.want.GetElement().GetAbilityName()) &&
                    connectionId == obj.first.id;
        });
    if (item != g_connects.end()) {
        // match bundlename && abilityname
        g_connects.erase(item);
        TAG_LOGD(AAFwkTag::CONTEXT, "end release connect, erase g_connects.size:%{public}zu", g_connects.size());
    }

    napi_value argv[] = { ConvertElement(element) };
    TAG_LOGI(AAFwkTag::CONTEXT, "Call onDisconnect");
    napi_status status = napi_call_function(env_, obj, method, ARGC_ONE, argv, nullptr);
    if (status != napi_ok) {
        TAG_LOGE(AAFwkTag::CONTEXT, "call js func failed %{public}d", status);
    }
}

void JSAbilityConnection::CallJsFailed(int32_t errorCode)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    if (jsConnectionObject_ == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null jsConnectionObject_");
        return;
    }
    napi_value obj = jsConnectionObject_->GetNapiValue();
    if (!CheckTypeForNapiValue(env_, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "get object failed");
        return;
    }

    napi_value method = nullptr;
    napi_get_named_property(env_, obj, "onFailed", &method);
    if (method == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null method");
        return;
    }

    napi_value argv[] = {CreateJsValue(env_, errorCode)};
    napi_call_function(env_, obj, method, ARGC_ONE, argv, nullptr);
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
}

napi_value JSAbilityConnection::CallObjectMethod(const char* name, napi_value const *argv, size_t argc)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "name:%{public}s", name);
    if (!jsConnectionObject_) {
        TAG_LOGW(AAFwkTag::CONTEXT, "not found jsConnectionObject_");
        return nullptr;
    }

    HandleScope handleScope(env_);
    napi_value obj = jsConnectionObject_->GetNapiValue();
    if (!CheckTypeForNapiValue(env_, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "type error: connection napi value");
        return nullptr;
    }

    napi_value method = nullptr;
    napi_get_named_property(env_, obj, name, &method);
    if (!CheckTypeForNapiValue(env_, method, napi_function)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "type error, method: '%{public}s'", name);
        return nullptr;
    }
    napi_value result = nullptr;
    napi_call_function(env_, obj, method, argc, argv, &result);
    TAG_LOGD(AAFwkTag::CONTEXT, "callFunction(%{public}s) ok", name);
    return result;
}

napi_value JSAbilityConnection::ConvertElement(const AppExecFwk::ElementName &element)
{
    return AppExecFwk::WrapElementName(env_, element);
}

void JSAbilityConnection::SetJsConnectionObject(napi_value jsConnectionObject)
{
    napi_ref ref = nullptr;
    napi_create_reference(env_, jsConnectionObject, 1, &ref);
    jsConnectionObject_ = std::unique_ptr<NativeReference>(reinterpret_cast<NativeReference*>(ref));
}

void JSAbilityConnection::RemoveConnectionObject()
{
    jsConnectionObject_.reset();
}

napi_value JsAbilityContext::SetMissionContinueState(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetMissionContinueState);
}

napi_value JsAbilityContext::OnSetMissionContinueState(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    AAFwk::ContinueState state;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], state)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse state failed");
        ThrowInvalidParamError(env, "Parse param state failed, state must be State.");
        return CreateJsUndefined(env);
    }

    if (state <= AAFwk::ContinueState::CONTINUESTATE_UNKNOWN || state >= AAFwk::ContinueState::CONTINUESTATE_MAX) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid params, state: %{public}d", state);
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_PARAM);
        return CreateJsUndefined(env);
    }

    if (!g_hasSetContinueState) {
        g_hasSetContinueState = true;
        return SyncSetMissionContinueState(env, info, state);
    }

    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [weak = context_, state, innerErrCode]() {
        auto context = weak.lock();
        if (!context) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
            return;
        }
        *innerErrCode = context->SetMissionContinueState(state);
    };
    NapiAsyncTask::CompleteCallback complete = [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
        HandleScope handleScope(env);
        if (*innerErrCode == ERR_OK) {
            task.Resolve(env, CreateJsUndefined(env));
        } else {
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
        }
    };
    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetMissionContinueState",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    TAG_LOGI(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::SyncSetMissionContinueState(napi_env env, NapiCallbackInfo& info,
    const AAFwk::ContinueState& state)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "called");
    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, &state, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->SetMissionContinueState(state);
        };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };
    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetMissionContinueState",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    TAG_LOGI(AAFwkTag::CONTEXT, "end");
    return result;
}
#ifdef SUPPORT_SCREEN
napi_value JsAbilityContext::SetMissionLabel(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetMissionLabel);
}

napi_value JsAbilityContext::SetMissionIcon(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetMissionIcon);
}

napi_value JsAbilityContext::SetAbilityInstanceInfo(napi_env env, napi_callback_info info)
{
    GET_NAPI_INFO_AND_CALL(env, info, JsAbilityContext, OnSetAbilityInstanceInfo);
}

napi_value JsAbilityContext::OnSetMissionLabel(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    std::string label;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], label)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse label failed");
        ThrowInvalidParamError(env, "Parse param label failed, label must be string.");
        return CreateJsUndefined(env);
    }
    NapiAsyncTask::CompleteCallback complete =
        [weak = context_, label](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                return;
            }
            auto errCode = context->SetMissionLabel(label);
            if (errCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, errCode));
            }
    };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetMissionLabel",
        env, CreateAsyncTaskWithLastParam(env, lastParam, nullptr, std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnSetMissionIcon(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    auto icon = OHOS::Media::PixelMapNapi::GetPixelMap(env, info.argv[INDEX_ZERO]);
    if (!icon) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse icon failed");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_PARAM);
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, icon, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->SetMissionIcon(icon);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[INDEX_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetMissionIcon",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnSetAbilityInstanceInfo(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_TWO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    std::string label;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], label) || label.empty()) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse label failed");
        ThrowInvalidParamError(env, "Invalid label.");
        return CreateJsUndefined(env);
    }
    auto icon = OHOS::Media::PixelMapNapi::GetPixelMap(env, info.argv[INDEX_ONE]);
    if (icon == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse icon failed");
        ThrowInvalidParamError(env, "Parse icon failed.");
        return CreateJsUndefined(env);
    }
    NapiAsyncTask::CompleteCallback complete =
        [weak = context_, label, icon](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                return;
            }
            auto errCode = context->SetAbilityInstanceInfo(label, icon);
            if (errCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, errCode));
            }
    };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetAbilityInstanceInfo",
        env, CreateAsyncTaskWithLastParam(env, nullptr, nullptr, std::move(complete), &result));
    return result;
}
#endif

napi_value JsAbilityContext::OnStartAbilityByType(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGI(AAFwkTag::CONTEXT, "call");
    if (info.argc < ARGC_THREE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    std::string type;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], type)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse type failed");
        ThrowInvalidParamError(env, "Parse param type failed, type must be string.");
        return CreateJsUndefined(env);
    }

    AAFwk::WantParams wantParam;
    if (!AppExecFwk::UnwrapWantParams(env, info.argv[INDEX_ONE], wantParam)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse wantParam failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    std::shared_ptr<JsUIExtensionCallback> callback = std::make_shared<JsUIExtensionCallback>(env);
    callback->SetJsCallbackObject(info.argv[INDEX_TWO]);
    napi_value completionHandler = AppExecFwk::GetPropertyValueByPropertyName(
        env, info.argv[INDEX_TWO], "completionHandler", napi_object);
    if (completionHandler != nullptr) {
        callback->SetCompletionHandler(env, completionHandler);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, type, wantParam, callback, innerErrCode]() mutable {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
#ifdef SUPPORT_SCREEN
            *innerErrCode = context->StartAbilityByType(type, wantParam, callback);
#endif
        };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };
    napi_value lastParam = (info.argc > ARGC_THREE) ? info.argv[INDEX_THREE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnStartAbilityByType",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnRequestModalUIExtension(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[0], want)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute = [abilityContext = context_, want, innerErrCode]() {
        auto context = abilityContext.lock();
        if (!context) {
            TAG_LOGE(AAFwkTag::CONTEXT, "null context");
            *innerErrCode = static_cast<int>(AbilityErrorCode::ERROR_CODE_INNER);
            return;
        }
        *innerErrCode = AAFwk::AbilityManagerClient::GetInstance()->RequestModalUIExtension(want);
    };
    NapiAsyncTask::CompleteCallback complete = [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
        HandleScope handleScope(env);
        if (*innerErrCode == ERR_OK) {
            task.Resolve(env, CreateJsUndefined(env));
        } else {
            TAG_LOGE(AAFwkTag::CONTEXT, "complete failed %{public}d", *innerErrCode);
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
        }
    };
    napi_value lastParam = (info.argc > ARGC_ONE) ? info.argv[ARGC_ONE] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnRequestModalUIExtension",
        env, CreateAsyncTaskWithLastParam(env, lastParam, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnShowAbility(napi_env env, NapiCallbackInfo& info)
{
    return ChangeAbilityVisibility(env, info, true);
}

napi_value JsAbilityContext::OnHideAbility(napi_env env, NapiCallbackInfo& info)
{
    return ChangeAbilityVisibility(env, info, false);
}

napi_value JsAbilityContext::ChangeAbilityVisibility(napi_env env, NapiCallbackInfo& info, bool isShow)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, isShow, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->ChangeAbilityVisibility(isShow);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else if (*innerErrCode == static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT)) {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::ChangeAbilityVisibility",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnMoveAbilityToBackground(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "start");
    auto abilityContext = context_.lock();

    NapiAsyncTask::CompleteCallback complete =
        [weak = context_](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            TAG_LOGD(AAFwkTag::CONTEXT, "start task");
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT));
                return;
            }

            auto errcode = context->MoveUIAbilityToBackground();
            if (errcode == 0) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, errcode));
            }
        };

    napi_value lastParam = (info.argc > ARGC_ZERO) ? info.argv[INDEX_ZERO] : nullptr;
    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnMoveAbilityToBackground",
        env, CreateAsyncTaskWithLastParam(env, lastParam, nullptr, std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnOpenAtomicService(napi_env env, NapiCallbackInfo& info)
{
    if (info.argc == ARGC_ZERO) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    std::string appId;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], appId)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse appId failed");
        ThrowInvalidParamError(env, "Parse param appId failed, appId must be string.");
        return CreateJsUndefined(env);
    }

    Want want;
    AAFwk::StartOptions startOptions;
    if (info.argc > ARGC_ONE && CheckTypeForNapiValue(env, info.argv[INDEX_ONE], napi_object)) {
        TAG_LOGD(AAFwkTag::CONTEXT, "atomic service options is used");
        if (!AppExecFwk::UnwrapStartOptionsAndWant(env, info.argv[INDEX_ONE], startOptions, want)) {
            TAG_LOGE(AAFwkTag::CONTEXT, "invalid atomic service options");
            ThrowInvalidParamError(env, "Parse param startOptions failed, startOptions must be StartOption.");
            return CreateJsUndefined(env);
        }
        UnWrapCompletionHandlerForAtomicService(env, info.argv[INDEX_ONE], startOptions, appId);
    }

    std::string bundleName = ATOMIC_SERVICE_PREFIX + appId;
    TAG_LOGD(AAFwkTag::CONTEXT, "bundleName: %{public}s", bundleName.c_str());
    want.SetBundle(bundleName);
    return OpenAtomicServiceInner(env, info, want, startOptions);
}

napi_value JsAbilityContext::OpenAtomicServiceInner(napi_env env, NapiCallbackInfo& info, Want &want,
    AAFwk::StartOptions &options)
{
    InheritWindowMode(want);
    want.AddFlags(Want::FLAG_INSTALL_ON_DEMAND);
    std::string startTime = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::
        system_clock::now().time_since_epoch()).count());
    want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
    napi_value result = nullptr;
    AddFreeInstallObserver(env, want, nullptr, &result, true);
    RuntimeTask task = [env, element = want.GetElement(), startTime, &observer = freeInstallObserver_](
        int resultCode, const AAFwk::Want& want, bool isInner) {
        TAG_LOGD(AAFwkTag::CONTEXT, "start async callback");
        if (observer == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null observer");
            return;
        }
        HandleScope handleScope(env);
        std::string bundleName = element.GetBundleName();
        std::string abilityName = element.GetAbilityName();
        napi_value abilityResult = AppExecFwk::WrapAbilityResult(env, resultCode, want);
        if (abilityResult == nullptr) {
            TAG_LOGW(AAFwkTag::CONTEXT, "null abilityResult");
            isInner = true;
            resultCode = ERR_INVALID_VALUE;
        }
        isInner ? observer->OnInstallFinished(bundleName, abilityName, startTime, resultCode) :
            observer->OnInstallFinished(bundleName, abilityName, startTime, abilityResult);
    };
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::CONTEXT, "null context");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
        return CreateJsUndefined(env);
    } else {
        want.SetParam(Want::PARAM_RESV_FOR_RESULT, true);
        auto requestCode = GenerateRequestCode();
        context->OpenAtomicService(want, options, requestCode, std::move(task));
    }
    TAG_LOGD(AAFwkTag::CONTEXT, "end");
    return result;
}

napi_value JsAbilityContext::OnSetRestoreEnabled(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::CONTEXT, "called");
    if (info.argc == ARGC_ZERO) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    auto abilityContext = context_.lock();
    if (abilityContext == nullptr) {
        TAG_LOGW(AAFwkTag::CONTEXT, "null abilityContext");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
        return CreateJsUndefined(env);
    }

    bool enabled = true;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], enabled)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse param failed");
        ThrowInvalidParamError(env, "Parse param enabled failed.");
        return CreateJsUndefined(env);
    }

    abilityContext->SetRestoreEnabled(enabled);
    return CreateJsUndefined(env);
}

napi_value JsAbilityContext::OnSetColorMode(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::APPKIT, "OnSetColorMode called");
    // only support one params
    if (info.argc == ARGC_ZERO) {
        TAG_LOGE(AAFwkTag::APPKIT, "Not enough params");
        ThrowInvalidParamError(env, "Not enough params.");
        return CreateJsUndefined(env);
    }
    auto context = context_.lock();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::APPKIT, "context is already released");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
        return CreateJsUndefined(env);
    }

    int32_t colorMode = -1;
    if (!ConvertFromJsValue(env, info.argv[INDEX_ZERO], colorMode)) {
        TAG_LOGE(AAFwkTag::APPKIT, "Parse colorMode failed");
        ThrowInvalidParamError(env, "Parse param colorMode failed, colorMode must be number.");
        return CreateJsUndefined(env);
    }
    context->SetAbilityColorMode(colorMode);
    return CreateJsUndefined(env);
}

napi_value JsAbilityContext::OnRevokeDelegator(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::APPKIT, "OnRevokeDelegator called");
    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, innerErrCode] {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "released context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->RevokeDelegator();
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnRevokeDelegator",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnSetOnNewWantSkipScenarios(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::APPKIT, "OnSetOnNewWantSkipScenarios called");
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    int32_t scenarios = 0;
    if (!OHOS::AppExecFwk::UnwrapInt32FromJS2(env, info.argv[INDEX_ZERO], scenarios)) {
        TAG_LOGE(AAFwkTag::CONTEXT, "invalid first params");
        ThrowInvalidParamError(env, "Failed to parse scenarios. Scenarios must be a number.");
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, innerErrCode, scenarios] {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "released context");
                *innerErrCode = static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->SetOnNewWantSkipScenarios(scenarios);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsError(env, AbilityErrorCode::ERROR_CODE_INNER));
            }
        };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnSetOnNewWantSkipScenarios",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnStartAppServiceExtensionAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return StartExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::APP_SERVICE);
}

napi_value JsAbilityContext::OnStopAppServiceExtensionAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return StopExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::APP_SERVICE);
}

napi_value JsAbilityContext::OnConnectAppServiceExtensionAbility(napi_env env, NapiCallbackInfo& info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    return ConnectExtensionAbilityCommon(env, info, AppExecFwk::ExtensionAbilityType::APP_SERVICE);
}

napi_value JsAbilityContext::OnRestartAppWithWindow(napi_env env, NapiCallbackInfo& info)
{
    TAG_LOGD(AAFwkTag::APPKIT, "OnRestartAppWithWindow called");
    if (info.argc < ARGC_ONE) {
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }
    AAFwk::Want want;
    if (!AppExecFwk::UnwrapWant(env, info.argv[INDEX_ZERO], want)) {
        TAG_LOGE(AAFwkTag::APPKIT, "Parse want failed");
        ThrowInvalidParamError(env, "Parse param want failed, want must be Want.");
        return CreateJsUndefined(env);
    }
    InheritWindowMode(want);
    auto innerErrCode = std::make_shared<int32_t>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, innerErrCode, want] {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "released context");
                *innerErrCode = static_cast<int32_t>(AAFwk::ERR_INVALID_CONTEXT);
                return;
            }
            *innerErrCode = context->RestartAppWithWindow(want);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.ResolveWithNoError(env, CreateJsUndefined(env));
            } else {
                task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
            }
        };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::OnRestartAppWithWindow",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
}

napi_value JsAbilityContext::OnSetMissionWindowIcon(napi_env env, NapiCallbackInfo& info)
{
#ifdef SUPPORT_SCREEN
    TAG_LOGD(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(info.argc));
    if (info.argc < ARGC_ONE) {
        TAG_LOGE(AAFwkTag::CONTEXT, "not enough params");
        ThrowTooFewParametersError(env);
        return CreateJsUndefined(env);
    }

    auto windowIcon = OHOS::Media::PixelMapNapi::GetPixelMap(env, info.argv[INDEX_ZERO]);
    if (!windowIcon) {
        TAG_LOGE(AAFwkTag::CONTEXT, "parse windowIcon failed");
        ThrowError(env, AbilityErrorCode::ERROR_CODE_INVALID_PARAM);
        return CreateJsUndefined(env);
    }
    auto innerErrCode = std::make_shared<ErrCode>(ERR_OK);
    NapiAsyncTask::ExecuteCallback execute =
        [weak = context_, windowIcon, innerErrCode]() {
            auto context = weak.lock();
            if (!context) {
                TAG_LOGW(AAFwkTag::CONTEXT, "null context");
                *innerErrCode = AAFwk::ERR_INVALID_CONTEXT;
                return;
            }
            TAG_LOGI(AAFwkTag::CONTEXT, "info.argc: %{public}d", static_cast<int>(windowIcon->GetWidth()));
            *innerErrCode = context->SetMissionWindowIcon(windowIcon);
    };
    NapiAsyncTask::CompleteCallback complete =
        [innerErrCode](napi_env env, NapiAsyncTask& task, int32_t status) {
            HandleScope handleScope(env);
            if (*innerErrCode == ERR_OK) {
                task.Resolve(env, CreateJsUndefined(env));
                return;
            }
            task.Reject(env, CreateJsErrorByNativeErr(env, *innerErrCode));
        };

    napi_value result = nullptr;
    NapiAsyncTask::ScheduleHighQos("JsAbilityContext::SetMissionWindowIcon",
        env, CreateAsyncTaskWithLastParam(env, nullptr, std::move(execute), std::move(complete), &result));
    return result;
#else
    return CreateJsUndefined(env);
#endif
}

int32_t JsAbilityContext::GenerateRequestCode()
{
    std::lock_guard lock(requestCodeMutex_);
    curRequestCode_ = (curRequestCode_ == INT_MAX) ? 0 : (curRequestCode_ + 1);
    return curRequestCode_;
}

int32_t JsAbilityContext::curRequestCode_ = 0;
std::mutex JsAbilityContext::requestCodeMutex_;
}  // namespace AbilityRuntime
}  // namespace OHOS
