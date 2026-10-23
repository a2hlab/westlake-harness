/*
 * Copyright (c) 2021-2024 Huawei Device Co., Ltd.
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

#include "js_service_extension.h"

#include "ability_business_error.h"
#include "ability_handler.h"
#include "ability_info.h"
#include "ability_manager_client.h"
#include "configuration_utils.h"
#include "display_util.h"
#include "freeze_util.h"
#include "hitrace_meter.h"
#include "hilog_tag_wrapper.h"
#include "insight_intent_execute_param.h"
#include "insight_intent_execute_result.h"
#include "insight_intent_executor_info.h"
#include "insight_intent_executor_mgr.h"
#include "js_extension_common.h"
#include "js_extension_context.h"
#include "js_runtime.h"
#include "js_runtime_utils.h"
#include "js_service_extension_context.h"
#include "napi/native_api.h"
#include "napi/native_node_api.h"
#include "napi_common_configuration.h"
#include "napi_common_want.h"
#include "napi_remote_object.h"
#ifdef SUPPORT_GRAPHICS
#include "iservice_registry.h"
#include "system_ability_definition.h"
#include "window_scene.h"
#endif

namespace OHOS {
namespace AbilityRuntime {
namespace {
constexpr size_t ARGC_ONE = 1;
constexpr size_t ARGC_TWO = 2;
}

namespace {
sptr<IRemoteObject> GetNativeRemoteObject(napi_env env, napi_value obj)
{
    if (env == nullptr || obj == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null obj");
        return nullptr;
    }
    napi_valuetype type;
    napi_typeof(env, obj, &type);
    if (type == napi_undefined || type == napi_null) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "obj type invalid");
        return nullptr;
    }
    if (type != napi_object) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "obj not object");
        return nullptr;
    }
    return NAPI_ohos_rpc_getNativeRemoteObject(env, obj);
}

napi_value PromiseCallback(napi_env env, napi_callback_info info)
{
    void *data = nullptr;
    NAPI_CALL_NO_THROW(napi_get_cb_info(env, info, nullptr, nullptr, nullptr, &data), nullptr);
    auto *callbackInfo = static_cast<AppExecFwk::AbilityTransactionCallbackInfo<> *>(data);
    callbackInfo->Call();
    AppExecFwk::AbilityTransactionCallbackInfo<>::Destroy(callbackInfo);
    data = nullptr;
    return nullptr;
}

napi_value OnConnectPromiseCallback(napi_env env, napi_callback_info info)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "enter");
    void *data = nullptr;
    size_t argc = ARGC_MAX_COUNT;
    napi_value argv[ARGC_MAX_COUNT] = {nullptr};
    NAPI_CALL_NO_THROW(napi_get_cb_info(env, info, &argc, argv, nullptr, &data), nullptr);
    auto *callbackInfo = static_cast<AppExecFwk::AbilityTransactionCallbackInfo<sptr<IRemoteObject>> *>(data);
    sptr<IRemoteObject> service = nullptr;
    if (argc > 0) {
        service = GetNativeRemoteObject(env, argv[0]);
    }
    callbackInfo->Call(service);
    AppExecFwk::AbilityTransactionCallbackInfo<sptr<IRemoteObject>>::Destroy(callbackInfo);
    data = nullptr;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "end");
    return nullptr;
}
}

using namespace OHOS::AppExecFwk;

napi_value AttachServiceExtensionContext(napi_env env, void *value, void *)
{
    HandleEscape handleEscape(env);
    if (value == nullptr) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "null value");
        return nullptr;
    }
    auto ptr = reinterpret_cast<std::weak_ptr<ServiceExtensionContext> *>(value)->lock();
    if (ptr == nullptr) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "null ptr");
        return nullptr;
    }
    napi_value object = CreateJsServiceExtensionContext(env, ptr);
    auto sysModule = JsRuntime::LoadSystemModuleByEngine(env,
        "application.ServiceExtensionContext", &object, 1);
    if (sysModule == nullptr) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "null sysModule");
        return nullptr;
    }
    auto contextObj = sysModule->GetNapiValue();
    napi_coerce_to_native_binding_object(
        env, contextObj, DetachCallbackFunc, AttachServiceExtensionContext, value, nullptr);
    auto workContext = new (std::nothrow) std::weak_ptr<ServiceExtensionContext>(ptr);
    auto res = napi_wrap(env, contextObj, workContext,
        [](napi_env, void *data, void *) {
            TAG_LOGD(AAFwkTag::SERVICE_EXT, "Finalizer for weak_ptr service extension context is called");
            delete static_cast<std::weak_ptr<ServiceExtensionContext> *>(data);
        },
        nullptr, nullptr);
    if (res != napi_ok && workContext != nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "napi_wrap failed:%{public}d", res);
        delete workContext;
        return nullptr;
    }
    return handleEscape.Escape(contextObj);
}

JsServiceExtension* JsServiceExtension::Create(const std::unique_ptr<Runtime>& runtime)
{
    return new JsServiceExtension(static_cast<JsRuntime&>(*runtime));
}

JsServiceExtension::JsServiceExtension(JsRuntime& jsRuntime) : jsRuntime_(jsRuntime) {}
JsServiceExtension::~JsServiceExtension()
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    auto context = GetContext();
    if (context) {
        context->Unbind();
    }

    jsRuntime_.FreeNativeReference(std::move(jsObj_));
    jsRuntime_.FreeNativeReference(std::move(shellContextRef_));
}

void JsServiceExtension::Init(const std::shared_ptr<AbilityLocalRecord> &record,
    const std::shared_ptr<OHOSApplication> &application, std::shared_ptr<AbilityHandler> &handler,
    const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    FreezeUtil::GetInstance().AddLifecycleEvent(token, "JsServiceExtension::Init");
    ServiceExtension::Init(record, application, handler, token);
    std::string srcPath = "";
    GetSrcPath(srcPath);
    if (srcPath.empty()) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get srcPath failed");
        return;
    }

    std::string moduleName(Extension::abilityInfo_->moduleName);
    moduleName.append("::").append(abilityInfo_->name);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called, moduleName:%{public}s,srcPath:%{public}s",
        moduleName.c_str(), srcPath.c_str());
    HandleScope handleScope(jsRuntime_);
    auto env = jsRuntime_.GetNapiEnv();

    FreezeUtil::GetInstance().AddLifecycleEvent(token, "JsServiceExtension::Init LoadModule");
    jsObj_ = jsRuntime_.LoadModule(
        moduleName, srcPath, abilityInfo_->hapPath, abilityInfo_->compileMode == CompileMode::ES_MODULE,
        false, abilityInfo_->srcEntrance);
    if (jsObj_ == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null jsObj_");
        return;
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "ConvertNativeValueTo");
    napi_value obj = jsObj_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get JsServiceExtension obj failed");
        return;
    }

    BindContext(env, obj);

    SetExtensionCommon(JsExtensionCommon::Create(jsRuntime_, static_cast<NativeReference&>(*jsObj_), shellContextRef_));

    handler_ = handler;
    auto context = GetContext();
    auto appContext = Context::GetApplicationContext();
    if (context != nullptr && appContext != nullptr) {
        auto appConfig = appContext->GetConfiguration();
        if (appConfig != nullptr) {
            TAG_LOGD(AAFwkTag::SERVICE_EXT, "Original config dump: %{public}s", appConfig->GetName().c_str());
            context->SetConfiguration(std::make_shared<Configuration>(*appConfig));
        }
    }
    ListenWMS();
}

void JsServiceExtension::ListenWMS()
{
#ifdef SUPPORT_GRAPHICS
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "RegisterDisplayListener");
    auto abilityManager = SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (abilityManager == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null SaMgr");
        return;
    }

    auto jsServiceExtension = std::static_pointer_cast<JsServiceExtension>(shared_from_this());
    displayListener_ = sptr<JsServiceExtensionDisplayListener>::MakeSptr(jsServiceExtension);
    if (displayListener_ == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null displayListener");
        return;
    }

    auto context = GetContext();
    if (context == nullptr || context->GetToken() == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null context");
        return;
    }

    saStatusChangeListener_ =
        sptr<SystemAbilityStatusChangeListener>::MakeSptr(displayListener_, context->GetToken());
    if (saStatusChangeListener_ == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null saStatusChangeListener");
        return;
    }

    auto ret = abilityManager->SubscribeSystemAbility(WINDOW_MANAGER_SERVICE_ID, saStatusChangeListener_);
    if (ret != 0) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "subscribe system ability error:%{public}d.", ret);
    }
#endif
}
#ifdef SUPPORT_GRAPHICS
void JsServiceExtension::SystemAbilityStatusChangeListener::OnAddSystemAbility(int32_t systemAbilityId,
    const std::string& deviceId)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "systemAbilityId: %{public}d add", systemAbilityId);
    if (systemAbilityId == WINDOW_MANAGER_SERVICE_ID) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "RegisterDisplayInfoChangedListener");
        Rosen::WindowManager::GetInstance().RegisterDisplayInfoChangedListener(token_, tmpDisplayListener_);
    }
}
#endif //SUPPORT_GRAPHICS
void JsServiceExtension::BindContext(napi_env env, napi_value obj)
{
    HandleScope handleScope(env);
    auto context = GetContext();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null context");
        return;
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    napi_value contextObj = CreateJsServiceExtensionContext(env, context);
    shellContextRef_ = JsRuntime::LoadSystemModuleByEngine(env, "application.ServiceExtensionContext",
        &contextObj, ARGC_ONE);
    if (shellContextRef_ == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null shellContextRef");
        return;
    }
    contextObj = shellContextRef_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, contextObj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get context native obj failed");
        return;
    }
    auto workContext = new (std::nothrow) std::weak_ptr<ServiceExtensionContext>(context);
    napi_coerce_to_native_binding_object(
        env, contextObj, DetachCallbackFunc, AttachServiceExtensionContext, workContext, nullptr);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Bind");
    context->Bind(jsRuntime_, shellContextRef_.get());
    napi_set_named_property(env, obj, "context", contextObj);

    auto res = napi_wrap(env, contextObj, workContext,
        [](napi_env, void* data, void*) {
            delete static_cast<std::weak_ptr<ServiceExtensionContext>*>(data);
        },
        nullptr, nullptr);
    if (res != napi_ok && workContext != nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "napi_wrap failed:%{public}d", res);
        delete workContext;
        return;
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "end");
}

bool JsServiceExtension::HasScreenDensityBeenSet(std::shared_ptr<Global::Resource::ResourceManager> resourceManager)
{
    TAG_LOGD(AAFwkTag::ABILITY, "call HasScreenDensityBeenSet");
    std::unique_ptr<Global::Resource::ResConfig> resConfig(Global::Resource::CreateResConfig());
    if (resConfig == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITY, "null resConfig");
        return false;
    }
    if (resourceManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITY, "null resourceManager");
        return false;
    }
    resourceManager->GetResConfig(*resConfig);
    return resConfig->GetScreenDensityDpi() != Global::Resource::ScreenDensity::SCREEN_DENSITY_NOT_SET;
}

void JsServiceExtension::OnStart(const AAFwk::Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    Extension::OnStart(want);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");

    auto context = GetContext();
    if (context != nullptr) {
#ifdef SUPPORT_GRAPHICS
        int32_t displayId = AAFwk::DisplayUtil::GetDefaultDisplayId();
        displayId = want.GetIntParam(Want::PARAM_RESV_DISPLAY_ID, displayId);
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "displayId %{public}d", displayId);
        auto configUtils = std::make_shared<ConfigurationUtils>();
        if (!HasScreenDensityBeenSet(context->GetResourceManager())) {
            TAG_LOGD(AAFwkTag::ABILITY, "call InitDisplayConfig");
            configUtils->InitDisplayConfig(displayId, context->GetConfiguration(), context->GetResourceManager());
        }
#endif //SUPPORT_GRAPHICS
    }

    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();

    // display config has changed, need update context.config
    if (context != nullptr) {
        JsExtensionContext::ConfigurationUpdated(env, shellContextRef_, context->GetConfiguration());
    }

    napi_value napiWant = OHOS::AppExecFwk::WrapWant(env, want);
    napi_value argv[] = {napiWant};
    CallObjectMethod("onCreate", argv, ARGC_ONE);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "ok");
}

void JsServiceExtension::OnStop()
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    ServiceExtension::OnStop();
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    CallObjectMethod("onDestroy");
    bool ret = ConnectionManager::GetInstance().DisconnectCaller(GetContext()->GetToken());
    if (ret) {
        ConnectionManager::GetInstance().ReportConnectionLeakEvent(getpid(), gettid());
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "service extension connection not disconnected");
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "UnregisterDisplayInfoChangedListener");
    auto context = GetContext();
    if (context == nullptr || context->GetToken() == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null context");
        return;
    }
#ifdef SUPPORT_GRAPHICS
    Rosen::WindowManager::GetInstance()
        .UnregisterDisplayInfoChangedListener(context->GetToken(), displayListener_);
    if (saStatusChangeListener_) {
        auto saMgr = SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
        if (saMgr) {
            saMgr->UnSubscribeSystemAbility(WINDOW_MANAGER_SERVICE_ID, saStatusChangeListener_);
        } else {
            TAG_LOGW(AAFwkTag::SERVICE_EXT, "OnStop SaMgr null");
        }
    }
#endif //SUPPORT_GRAPHICS
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "ok");
}

sptr<IRemoteObject> JsServiceExtension::OnConnect(const AAFwk::Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    HandleScope handleScope(jsRuntime_);
    napi_value result = CallOnConnect(want);
    napi_env env = jsRuntime_.GetNapiEnv();
    auto remoteObj = GetNativeRemoteObject(env, result);
    if (remoteObj == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null remoteObj");
    }
    return remoteObj;
}

void JsServiceExtension::AddLifecycleEventForJSCall(const std::string &eventStr)
{
    auto entry = std::string("JsServiceExtension::") + eventStr;
    auto context = GetContext();
    if (context) {
        FreezeUtil::GetInstance().AddLifecycleEvent(context->GetToken(), entry);
    }
}

sptr<IRemoteObject> JsServiceExtension::OnConnect(const AAFwk::Want &want,
    AppExecFwk::AbilityTransactionCallbackInfo<sptr<IRemoteObject>> *callbackInfo, bool &isAsyncCallback)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    HandleScope handleScope(jsRuntime_);
    AddLifecycleEventForJSCall("OnConnect begin");
    napi_env env = jsRuntime_.GetNapiEnv();
    napi_value result = CallOnConnect(want);
    bool isPromise = CheckPromise(result);
    AddLifecycleEventForJSCall("OnConnect end");
    if (!isPromise) {
        isAsyncCallback = false;
        sptr<IRemoteObject> remoteObj = GetNativeRemoteObject(env, result);
        if (remoteObj == nullptr) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "null remoteObj");
        }
        return remoteObj;
    }

    bool callResult = false;
    do {
        if (!CheckTypeForNapiValue(env, result, napi_object)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "convert value error");
            break;
        }
        napi_value then = nullptr;
        napi_get_named_property(env, result, "then", &then);
        if (then == nullptr) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "null then");
            break;
        }
        bool isCallable = false;
        napi_is_callable(env, then, &isCallable);
        if (!isCallable) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "not callable property then");
            break;
        }
        napi_value promiseCallback = nullptr;
        napi_create_function(env, "promiseCallback", strlen("promiseCallback"),
            OnConnectPromiseCallback, callbackInfo, &promiseCallback);
        napi_value argv[1] = { promiseCallback };
        napi_call_function(env, result, then, 1, argv, nullptr);
        callResult = true;
    } while (false);

    isAsyncCallback = true;
    if (!callResult) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "call promise error");
        isAsyncCallback = false;
    }
    return nullptr;
}

void JsServiceExtension::OnDisconnect(const AAFwk::Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    HandleScope handleScope(jsRuntime_);
    Extension::OnDisconnect(want);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    CallOnDisconnect(want, false);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "end");
}

void JsServiceExtension::OnDisconnect(const AAFwk::Want &want,
    AppExecFwk::AbilityTransactionCallbackInfo<> *callbackInfo, bool &isAsyncCallback)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    HandleScope handleScope(jsRuntime_);
    Extension::OnDisconnect(want);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    napi_value result = CallOnDisconnect(want, true);
    bool isPromise = CheckPromise(result);
    if (!isPromise) {
        isAsyncCallback = false;
        return;
    }
    bool callResult = CallPromise(result, callbackInfo);
    if (!callResult) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "call promise error");
        isAsyncCallback = false;
    } else {
        isAsyncCallback = true;
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "end");
}

void JsServiceExtension::OnCommand(const AAFwk::Want &want, bool restart, int startId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    Extension::OnCommand(want, restart, startId);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "restart=%{public}s,startId=%{public}d",
        restart ? "true" : "false",
        startId);
    // wrap want
    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();
    napi_value napiWant = OHOS::AppExecFwk::WrapWant(env, want);
    // wrap startId
    napi_value napiStartId = nullptr;
    napi_create_int32(env, startId, &napiStartId);
    napi_value argv[] = {napiWant, napiStartId};
    CallObjectMethod("onRequest", argv, ARGC_TWO);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "ok");
}

bool JsServiceExtension::HandleInsightIntent(const AAFwk::Want &want)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    auto callback = std::make_unique<InsightIntentExecutorAsyncCallback>();
    callback.reset(InsightIntentExecutorAsyncCallback::Create());
    if (callback == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null callback");
        return false;
    }
    auto executeParam = std::make_shared<AppExecFwk::InsightIntentExecuteParam>();
    bool ret = AppExecFwk::InsightIntentExecuteParam::GenerateFromWant(want, *executeParam);
    if (!ret) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "Generate execute param failed");
        InsightIntentExecutorMgr::TriggerCallbackInner(std::move(callback),
            static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_PARAM));
        return false;
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Insight bundleName: %{public}s, moduleName: %{public}s, abilityName: %{public}s"
        "insightIntentName: %{public}s, executeMode: %{public}d, intentId: %{public}" PRIu64 "",
        executeParam->bundleName_.c_str(), executeParam->moduleName_.c_str(), executeParam->abilityName_.c_str(),
        executeParam->insightIntentName_.c_str(), executeParam->executeMode_, executeParam->insightIntentId_);
    auto asyncCallback = [weak = weak_from_this(), intentId = executeParam->insightIntentId_]
        (AppExecFwk::InsightIntentExecuteResult result) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "intentId %{public}" PRIu64"", intentId);
        auto extension = weak.lock();
        if (extension == nullptr) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "null extension");
            return;
        }
        auto ret = extension->OnInsightIntentExecuteDone(intentId, result);
        if (!ret) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "OnInsightIntentExecuteDone failed");
        }
    };
    callback->Push(asyncCallback);
    InsightIntentExecutorInfo executorInfo;
    ret = GetInsightIntentExecutorInfo(want, executeParam, executorInfo);
    if (!ret) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "Get Intent executor failed");
        InsightIntentExecutorMgr::TriggerCallbackInner(std::move(callback),
            static_cast<int32_t>(AbilityErrorCode::ERROR_CODE_INVALID_PARAM));
        return false;
    }
    ret = DelayedSingleton<InsightIntentExecutorMgr>::GetInstance()->ExecuteInsightIntent(
        jsRuntime_, executorInfo, std::move(callback));
    if (!ret) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "Execute insight intent failed");
        return false;
    }
    return true;
}

napi_value JsServiceExtension::CallObjectMethod(const char* name, napi_value const* argv, size_t argc)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, std::string("CallObjectMethod:") + name);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "name:%{public}s", name);

    if (!jsObj_) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "Not found ServiceExtension.js");
        return nullptr;
    }

    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();

    napi_value obj = jsObj_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get ServiceExtension obj failed");
        return nullptr;
    }

    napi_value method = nullptr;
    napi_get_named_property(env, obj, name, &method);
    if (!CheckTypeForNapiValue(env, method, napi_function)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get '%{public}s' from ServiceExtension obj failed", name);
        return nullptr;
    }
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "CallFunc(%{public}s)", name);
    napi_value result = nullptr;
    napi_status status = napi_call_function(env, obj, method, argc, argv, &result);
    if (status != napi_ok) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "call js func failed: %{public}d", status);
    }
    return result;
}

void JsServiceExtension::GetSrcPath(std::string &srcPath)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    if (!Extension::abilityInfo_->isModuleJson) {
        /* temporary compatibility api8 + config.json */
        srcPath.append(Extension::abilityInfo_->package);
        srcPath.append("/assets/js/");
        if (!Extension::abilityInfo_->srcPath.empty()) {
            srcPath.append(Extension::abilityInfo_->srcPath);
        }
        srcPath.append("/").append(Extension::abilityInfo_->name).append(".abc");
        return;
    }

    if (!Extension::abilityInfo_->srcEntrance.empty()) {
        srcPath.append(Extension::abilityInfo_->moduleName + "/");
        srcPath.append(Extension::abilityInfo_->srcEntrance);
        srcPath.erase(srcPath.rfind('.'));
        srcPath.append(".abc");
    }
}

napi_value JsServiceExtension::CallOnConnect(const AAFwk::Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    Extension::OnConnect(want);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    HandleEscape handleEscape(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();
    napi_value napiWant = OHOS::AppExecFwk::WrapWant(env, want);
    napi_value argv[] = {napiWant};
    if (!jsObj_) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "Not found ServiceExtension.js");
        return nullptr;
    }

    napi_value obj = jsObj_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get ServiceExtension obj failed");
        return nullptr;
    }

    napi_value method = nullptr;
    napi_get_named_property(env, obj, "onConnect", &method);
    if (method == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null method");
        return nullptr;
    }
    napi_value remoteNative = nullptr;
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "Call onConnect");
    napi_status status = napi_call_function(env, obj, method, ARGC_ONE, argv, &remoteNative);
    if (status != napi_ok) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "call js func failed %{public}d", status);
    }
    if (remoteNative == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null remoteNative");
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "ok");
    return handleEscape.Escape(remoteNative);
}

napi_value JsServiceExtension::CallOnDisconnect(const AAFwk::Want &want, bool withResult)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    HandleEscape handleEscape(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();
    napi_value napiWant = OHOS::AppExecFwk::WrapWant(env, want);
    napi_value argv[] = { napiWant };
    if (!jsObj_) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "Not found ServiceExtension.js");
        return nullptr;
    }

    napi_value obj = jsObj_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get ServiceExtension obj failed");
        return nullptr;
    }

    napi_value method = nullptr;
    napi_get_named_property(env, obj, "onDisconnect", &method);
    if (method == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null method");
        return nullptr;
    }
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "Call onDisconnect");
    if (withResult) {
        napi_value result = nullptr;
        napi_status status = napi_call_function(env, obj, method, ARGC_ONE, argv, &result);
        if (status != napi_ok) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "call js func failed %{public}d", status);
        }
        return handleEscape.Escape(result);
    } else {
        napi_status status = napi_call_function(env, obj, method, ARGC_ONE, argv, nullptr);
        if (status != napi_ok) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "call js func failed %{public}d", status);
        }
        return nullptr;
    }
}

bool JsServiceExtension::CheckPromise(napi_value result)
{
    if (result == nullptr) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "null result");
        return false;
    }
    napi_env env = jsRuntime_.GetNapiEnv();
    bool isPromise = false;
    napi_is_promise(env, result, &isPromise);
    if (!isPromise) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "result not promise");
        return false;
    }
    return true;
}

bool JsServiceExtension::CallPromise(napi_value result, AppExecFwk::AbilityTransactionCallbackInfo<> *callbackInfo)
{
    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();
    if (!CheckTypeForNapiValue(env, result, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "convert value error");
        return false;
    }
    napi_value then = nullptr;
    napi_get_named_property(env, result, "then", &then);
    if (then == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null then");
        return false;
    }
    bool isCallable = false;
    napi_is_callable(env, then, &isCallable);
    if (!isCallable) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "not callable property then");
        return false;
    }
    napi_value promiseCallback = nullptr;
    napi_create_function(env, "promiseCallback", strlen("promiseCallback"), PromiseCallback,
        callbackInfo, &promiseCallback);
    napi_value argv[1] = { promiseCallback };
    napi_call_function(env, result, then, 1, argv, nullptr);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "end");
    return true;
}

void JsServiceExtension::OnConfigurationUpdated(const AppExecFwk::Configuration& configuration)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    ServiceExtension::OnConfigurationUpdated(configuration);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    ConfigurationUpdated();
}

void JsServiceExtension::ConfigurationUpdated()
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();

    // Notify extension context
    auto fullConfig = GetContext()->GetConfiguration();
    if (!fullConfig) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null configuration");
        return;
    }

    napi_value napiConfiguration = OHOS::AppExecFwk::WrapConfiguration(env, *fullConfig);
    CallObjectMethod("onConfigurationUpdated", &napiConfiguration, ARGC_ONE);
    CallObjectMethod("onConfigurationUpdate", &napiConfiguration, ARGC_ONE);
    JsExtensionContext::ConfigurationUpdated(env, shellContextRef_, fullConfig);
}

void JsServiceExtension::Dump(const std::vector<std::string> &params, std::vector<std::string> &info)
{
    Extension::Dump(params, info);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    HandleScope handleScope(jsRuntime_);
    napi_env env = jsRuntime_.GetNapiEnv();
    // create js array object of params
    napi_value argv[] = { CreateNativeArray(env, params) };

    if (!jsObj_) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "Not found ServiceExtension.js");
        return;
    }

    napi_value obj = jsObj_->GetNapiValue();
    if (!CheckTypeForNapiValue(env, obj, napi_object)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "get ServiceExtension obj failed");
        return;
    }

    napi_value method = nullptr;
    napi_get_named_property(env, obj, "onDump", &method);
    if (!CheckTypeForNapiValue(env, method, napi_function)) {
        method = nullptr;
        napi_get_named_property(env, obj, "dump", &method);
        if (!CheckTypeForNapiValue(env, method, napi_function)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "get onConnect from ServiceExtension obj failed");
            return;
        }
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "success");
    napi_value dumpInfo = nullptr;
    napi_call_function(env, obj, method, ARGC_ONE, argv, &dumpInfo);
    if (dumpInfo == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null dumpInfo");
        return;
    }
    uint32_t len = 0;
    napi_get_array_length(env, dumpInfo, &len);
    for (uint32_t i = 0; i < len; i++) {
        std::string dumpInfoStr;
        napi_value element = nullptr;
        napi_get_element(env, dumpInfo, i, &element);
        if (!ConvertFromJsValue(env, element, dumpInfoStr)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "Parse dumpInfoStr failed");
            return;
        }
        info.push_back(dumpInfoStr);
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Dump info size: %{public}zu", info.size());
}

#ifdef SUPPORT_GRAPHICS
void JsServiceExtension::OnCreate(Rosen::DisplayId displayId)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "enter");
}

void JsServiceExtension::OnDestroy(Rosen::DisplayId displayId)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "exit");
}

void JsServiceExtension::OnDisplayInfoChange(const sptr<IRemoteObject>& token, Rosen::DisplayId displayId,
    float density, Rosen::DisplayOrientation orientation)
{
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "displayId: %{public}" PRIu64, displayId);
    auto context = GetContext();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null context");
        return;
    }

    auto contextConfig = context->GetConfiguration();
    if (contextConfig == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null contextConfig");
        return;
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Config dump: %{public}s", contextConfig->GetName().c_str());
    bool configChanged = false;
    auto configUtils = std::make_shared<ConfigurationUtils>();
    configUtils->UpdateDisplayConfig(displayId, contextConfig, context->GetResourceManager(), configChanged);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Config dump after update: %{public}s", contextConfig->GetName().c_str());

    if (configChanged) {
        auto jsServiceExtension = std::static_pointer_cast<JsServiceExtension>(shared_from_this());
        auto task = [jsServiceExtension]() {
            if (jsServiceExtension) {
                jsServiceExtension->ConfigurationUpdated();
            }
        };
        if (handler_ != nullptr) {
            handler_->PostTask(task, "JsServiceExtension:OnChange");
        }
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "finished");
}

void JsServiceExtension::OnChange(Rosen::DisplayId displayId)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "displayId: %{public}" PRIu64"", displayId);
    auto context = GetContext();
    if (context == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null context");
        return;
    }

    auto contextConfig = context->GetConfiguration();
    if (contextConfig == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "null contextConfig");
        return;
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Config dump: %{public}s", contextConfig->GetName().c_str());
    bool configChanged = false;
    auto configUtils = std::make_shared<ConfigurationUtils>();
    configUtils->UpdateDisplayConfig(displayId, contextConfig, context->GetResourceManager(), configChanged);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Config dump after update: %{public}s", contextConfig->GetName().c_str());

    if (configChanged) {
        auto jsServiceExtension = std::static_pointer_cast<JsServiceExtension>(shared_from_this());
        auto task = [jsServiceExtension]() {
            if (jsServiceExtension) {
                jsServiceExtension->ConfigurationUpdated();
            }
        };
        if (handler_ != nullptr) {
            handler_->PostTask(task, "JsServiceExtension:OnChange");
        }
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "finished");
}
#endif
} // AbilityRuntime
} // OHOS
