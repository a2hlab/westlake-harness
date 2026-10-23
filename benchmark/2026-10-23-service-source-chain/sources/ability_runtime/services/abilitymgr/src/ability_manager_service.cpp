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

#include "ability_manager_service.h"

#include <sys/epoll.h>

#include "ability_background_connection.h"
#include "ability_business_error.h"
#include "ability_connect_manager.h"
#include "ability_errors_util.h"
#include "ability_manager_radar.h"
#include "ability_manager_xcollie.h"
#include "ability_start_by_call_helper.h"
#include "ability_start_with_wait_observer_utils.h"
#include "ability_start_with_wait_observer_manager.h"
#include "accesstoken_kit.h"
#include "app_utils.h"
#include "app_exit_reason_data_manager.h"
#include "app_mgr_constants.h"
#include "app_mgr_util.h"
#include "application_util.h"
#include "assert_fault_callback_death_mgr.h"
#include "collaborator_util.h"
#include "concurrent_task_client.h"
#include "config_policy_utils.h"
#include "connection_state_manager.h"
#include "c/executor_task.h"
#include "display_manager.h"
#include "display_util.h"
#include "distributed_client.h"
#include "dlp_utils.h"
#include "exit_info_data_manager.h"
#include "ffrt.h"
#include "ffrt_inner.h"
#include "foreground_app_connection_manager.h"
#include "freeze_util.h"
#include "global_constant.h"
#include "hidden_start_observer_manager.h"
#include "hitrace_meter.h"
#include "hisysevent_report.h"
#include "insight_intent_execute_manager.h"
#include "insight_intent_db_cache.h"
#include "insight_intent_utils.h"
#include "interceptor/ability_jump_interceptor.h"
#include "interceptor/block_all_app_start_interceptor.h"
#include "interceptor/control_interceptor.h"
#include "interceptor/crowd_test_interceptor.h"
#include "interceptor/disposed_rule_interceptor.h"
#include "interceptor/ecological_rule_interceptor.h"
#include "interceptor/extension_control_interceptor.h"
#include "interceptor/kiosk_interceptor.h"
#include "interceptor/screen_unlock_interceptor.h"
#include "interceptor/start_other_app_interceptor.h"
#include "int_wrapper.h"
#include "ipc_skeleton.h"
#include "iservice_registry.h"
#include "keep_alive_process_manager.h"
#include "keep_alive_utils.h"
#include "main_element_utils.h"
#ifdef MEMMGR_OVERRIDE_ENABLE
#include "mem_mgr_client.h"
#include "mem_mgr_process_state_info.h"
#endif
#include "mock_session_manager_service.h"
#include "modal_system_dialog/modal_system_dialog_ui_extension.h"
#include "modal_system_ui_extension.h"
#include "multi_app_utils.h"
#include "os_account_manager_wrapper.h"
#include "permission_constants.h"
#include "preload_manager_service.h"
#include "process_options.h"
#include "rate_limiter.h"
#include "recovery_info_timer.h"
#include "recovery_param.h"
#include "report_data_partition_usage_manager.h"
#include "res_sched_util.h"
#include "restart_app_manager.h"
#include "sa_interceptor_manager.h"
#include "scene_board_judgement.h"
#include "server_constant.h"
#ifdef SUPPORT_RECORDER_DSOFTBUS
#include "softbus_bus_center.h"
#endif
#include "start_ability_handler/start_ability_sandbox_savefile.h"
#include "start_ability_utils.h"
#include "start_options_utils.h"
#include "startup_util.h"
#include "status_bar_delegate_interface.h"
#include "string_wrapper.h"
#include "support_system_ability_permission.h"
#include "time_util.h"
#include "tokenid_kit.h"
#include "ui_extension_wrapper.h"
#include "ui_service_extension_connection_constants.h"
#include "unlock_screen_manager.h"
#ifdef SUPPORT_UPMS
#include "uri_permission_manager_client.h"
#endif // SUPPORT_UPMS
#include "uri_utils.h"
#include "user_controller/user_controller.h"
#include "utils/ability_permission_util.h"
#include "utils/dump_utils.h"
#include "utils/exit_reason_util.h"
#include "utils/extension_permissions_util.h"
#include "utils/modal_system_dialog_util.h"
#include "utils/update_caller_info_util.h"
#include "utils/want_utils.h"
#include "utils/window_options_utils.h"
#include "utils/udmf_utils.h"
#include "view_data.h"
#ifdef SUPPORT_GRAPHICS
#include "ability_first_frame_state_observer_manager.h"
#include "application_anr_listener.h"
#include "dialog_session_manager.h"
#include "input_manager.h"
#include "session_manager_lite.h"
#include "session/host/include/zidl/session_interface.h"
#include "window_focus_changed_listener.h"
#include "wm_common.h"
#endif
#include "query_erms_manager.h"
#include "window_visibility_changed_listener.h"
#ifdef SUPPORT_SCREEN
#include "utils/dms_util.h"
#endif
#ifdef RESOURCE_SCHEDULE_SERVICE_ENABLE
#include "res_sched_client.h"
#endif
#include "xcollie/watchdog.h"

using OHOS::AppExecFwk::ElementName;
using OHOS::Security::AccessToken::AccessTokenKit;

namespace OHOS {
using AbilityRuntime::FreezeUtil;
using namespace AbilityRuntime::ServerConstant;
namespace AAFwk {
using AutoStartupInfo = AbilityRuntime::AutoStartupInfo;
using GetExtensionAbilityInfoFlag = AppExecFwk::GetExtensionAbilityInfoFlag;
namespace {
#define CHECK_CALLER_IS_SYSTEM_APP                                                             \
    if (!AAFwk::PermissionVerification::GetInstance()->JudgeCallerIsAllowedToUseSystemAPI()) { \
        TAG_LOGE(AAFwkTag::ABILITYMGR,                                                         \
        "caller no system-app, can not use system-api");                               \
        return ERR_NOT_SYSTEM_APP;                                                             \
    }

#define OPEN_LINK_START_ABILITY(WANT, TOKEN, USER, CODE, REMOVE_INSIGHT, HIDE_FAILURE, FROM_OPEN_LINK)  \
    do {                                                                                                \
        StartAbilityWrapParam PARAM = {                                                                 \
            .want = WANT,                                                                               \
            .callerToken = TOKEN,                                                                       \
            .requestCode = CODE,                                                                        \
            .userId = USER,                                                                             \
            .hideFailureTipDialog = HIDE_FAILURE,                                                       \
            .removeInsightIntentFlag = REMOVE_INSIGHT,                                                  \
            .isFromOpenLink = FROM_OPEN_LINK,                                                           \
        };                                                                                              \
        int retCode = StartAbilityWithRemoveIntentFlag(PARAM);                                          \
        CHECK_RET_RETURN_RET(retCode, "startAbility failed");                                           \
        return ERR_OPEN_LINK_START_ABILITY_DEFAULT_OK;                                                  \
    } while (0)

#define IS_FOUNDATION_CALL  \
    PermissionVerification::GetInstance()->CheckSpecificSystemAbilityAccessPermission(FOUNDATION_PROCESS_NAME)

constexpr const char* ARGS_USER_ID = "-u";
constexpr const char* ARGS_CLIENT = "-c";
constexpr const char* ILLEGAL_INFOMATION = "The arguments are illegal and you can enter '-h' for help.";

constexpr int32_t NEW_RULE_VALUE_SIZE = 6;
constexpr int32_t APP_ALIVE_TIME_MS = 1000;  // Allow background startup within 1 second after application startup
constexpr int32_t REGISTER_FOCUS_DELAY = 5000;
constexpr size_t OFFSET = 32;
constexpr int32_t PENG_LAI_UID = 7655;
constexpr int32_t RSS_UID = 1096;
constexpr const char* IS_DELEGATOR_CALL = "isDelegatorCall";

constexpr int32_t SHORT_REPOLL_TIME_MICRO_SECONDS = 200000;

// Startup rule switch
constexpr const char* COMPONENT_STARTUP_NEW_RULES = "component.startup.newRules";
constexpr const char* BACKGROUND_JUDGE_FLAG = "component.startup.backgroundJudge.flag";
constexpr const char* WHITE_LIST_ASS_WAKEUP_FLAG = "component.startup.whitelist.associatedWakeUp";

// White list app
constexpr const char* BUNDLE_NAME_SETTINGSDATA = "com.ohos.settingsdata";
// UIExtension type
constexpr const char* UIEXTENSION_TYPE_KEY = "ability.want.params.uiExtensionType";
constexpr const char* UIEXTENSION_TARGET_TYPE_KEY = "ability.want.params.uiExtensionTargetType";
// Share picker params
constexpr char SHARE_PICKER_DIALOG_BUNDLE_NAME_KEY[] = "const.system.sharePicker.bundleName";
constexpr char SHARE_PICKER_DIALOG_ABILITY_NAME_KEY[] = "const.system.sharePicker.abilityName";
constexpr char SHARE_PICKER_DIALOG_DEFAULY_BUNDLE_NAME[] = "com.ohos.sharepickerdialog";
constexpr char SHARE_PICKER_DIALOG_DEFAULY_ABILITY_NAME[] = "PickerDialog";
constexpr char TOKEN_KEY[] = "ohos.ability.params.token";
// Developer mode param
constexpr char DEVELOPER_MODE_STATE[] = "const.security.developermode.state";
// Broker params key
constexpr const char* KEY_VISIBLE_ID = "ohos.anco.param.visible";
constexpr const char* START_ABILITY_TYPE = "ABILITY_INNER_START_WITH_ACCOUNT";
constexpr const char* BUNDLE_NAME_DIALOG = "com.ohos.amsdialog";
constexpr const char* STR_PHONE = "phone";
constexpr const char* PARAM_RESV_ANCO_CALLER_UID = "ohos.anco.param.callerUid";
constexpr const char* PARAM_RESV_ANCO_CALLER_BUNDLENAME = "ohos.anco.param.callerBundleName";
constexpr const char* PARAM_RESV_ANCO_IS_NEED_UPDATE_NAME = "ohos.anco.param.isNeedUpdateName";
// Distributed continued session Id
constexpr const char* DMS_CONTINUED_SESSION_ID = "ohos.dms.continueSessionId";
constexpr const char* DMS_PERSISTENT_ID = "ohos.dms.persistentId";
constexpr const char* DMS_CALLING_UID = "ohos.dms.callingUid";
constexpr const char* DEBUG_FROM = "ohos.param.debugFrom";
constexpr const char* AUTO_FILL_PASSWORD_TYPE = "autoFill/password";
constexpr const char* AUTO_FILL_SMART_TYPE = "autoFill/smart";
constexpr size_t INDEX_ZERO = 0;
constexpr size_t INDEX_ONE = 1;
constexpr size_t INDEX_TWO = 2;
constexpr size_t ARGC_THREE = 3;
constexpr size_t INDEX_FOUR = 4;
constexpr static char WANT_PARAMS_VIEW_DATA_KEY[] = "ohos.ability.params.viewData";
constexpr const char* WANT_PARAMS_HOST_WINDOW_ID_KEY = "ohos.extra.param.key.hostwindowid";

constexpr int32_t FOUNDATION_UID = 5523;
constexpr const char* FRS_BUNDLE_NAME = "com.ohos.formrenderservice";
constexpr const char* FOUNDATION_PROCESS_NAME = "foundation";
constexpr const char* RSS_PROCESS_NAME = "resource_schedule_service";
constexpr const char* IS_PRELOAD_UIEXTENSION_ABILITY = "ability.want.params.is_preload_uiextension_ability";
constexpr const char* IS_PRELOADED_UI_EXTENSION_SUCCESS = "ability.want.params.is_preload_ui_extension_ability_success";
constexpr const char* UIEXTENSION_MODAL_TYPE = "ability.want.params.modalType";
constexpr const char* SUPPORT_CLOSE_ON_BLUR = "supportCloseOnBlur";
constexpr const char* ATOMIC_SERVICE_PREFIX = "com.atomicservice.";
constexpr const char* PARAM_SPECIFIED_PROCESS_FLAG = "ohosSpecifiedProcessFlag";
#ifdef MEMMGR_OVERRIDE_ENABLE
constexpr const char* EXPECT_WINDOW_MODE = "expectWindowMode";
#endif
constexpr const char* AUTO_STARTUP_READY = "persist.sys.abilityms.if_startup_ready";

constexpr char ASSERT_FAULT_DETAIL[] = "assertFaultDialogDetail";
constexpr char PRODUCT_ASSERT_FAULT_DIALOG_ENABLED[] = "persisit.sys.abilityms.support_assert_fault_dialog";
constexpr const char* ABILITYMS_ENABLE_UISERVICE = "const.abilityms.enable_uiservice";

constexpr const char* DLP_PARAMS_SECURITY_FLAG = "ohos.dlp.params.securityFlag";

constexpr char PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED[] = "const.product.enterprisefeature.setting.enabled";

constexpr int32_t RESOURCE_SCHEDULE_UID = 1096;
constexpr int32_t HIVIEW_UID = 1201;
constexpr int32_t MEMMGR_UID = 1111;
constexpr int32_t UPDATE_CONFIG_FLAG_COVER = 1;
constexpr int32_t UPDATE_CONFIG_FLAG_APPEND = 2;
constexpr int32_t START_AUTO_START_APP_DELAY_TIME = 200;
constexpr int32_t START_AUTO_START_APP_RETRY_MAX_TIMES = 5;
constexpr int32_t RETRY_COUNT = 20;

const std::unordered_set<std::string> COMMON_PICKER_TYPE = {
    "share", "action", "navigation", "mail", "finance", "flight", "express", "photoEditor"
};
std::atomic<bool> g_isDmsAlive = false;
constexpr const char* APPSPAWN_STARTED = "startup.service.ctl.appspawn.pid";
constexpr const char* APP_LINKING_ONLY = "appLinkingOnly";
constexpr const char* SCREENCONFIG_SCREENMODE = "ohos.verticalpanel.screenconfig.screenmode";
constexpr const char* UD_KEY = "ability.want.params.udKey";
constexpr int32_t INSTALL_TYPE_UPGRADE = 2;

void SendAbilityEvent(const EventName &eventName, HiSysEventEventType type, const EventInfo &eventInfo)
{
    ffrt::submit([eventName, type, eventInfo]() {
        EventReport::SendAbilityEvent(eventName, type, eventInfo);
        }, ffrt::task_attr().timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));
}

bool IsEmbeddableStart(int32_t screenMode)
{
    return screenMode == AAFwk::EMBEDDED_FULL_SCREEN_MODE ||
        screenMode == AAFwk::EMBEDDED_HALF_SCREEN_MODE;
}
} // namespace

using namespace std::chrono;
using namespace std::chrono_literals;
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
using namespace BackgroundTaskMgr;
#endif
const bool CONCURRENCY_MODE_FALSE = false;
constexpr int32_t MAIN_USER_ID = 100;
constexpr auto DATA_ABILITY_START_TIMEOUT = 5s;
constexpr int32_t NON_ANONYMIZE_LENGTH = 6;
constexpr uint32_t SCENE_FLAG_NORMAL = 0;
constexpr int32_t MAX_NUMBER_OF_DISTRIBUTED_MISSIONS = 20;
constexpr int32_t SWITCH_ACCOUNT_TRY = 3;
constexpr const char* EMPTY_DEVICE_ID = "";
constexpr int32_t APP_MEMORY_SIZE = 512;
constexpr int32_t GET_PARAMETER_INCORRECT = -9;
constexpr int32_t GET_PARAMETER_OTHER = -1;
constexpr int32_t SIZE_10 = 10;
constexpr int32_t HIDUMPER_SERVICE_UID = 1212;
constexpr int32_t ACCOUNT_MGR_SERVICE_UID = 3058;
constexpr int32_t DMS_UID = 5522;
constexpr int32_t SAMGR_UID = 5555;
constexpr int32_t BOOTEVENT_COMPLETED_DELAY_TIME = 1000;
constexpr int32_t BOOTEVENT_BOOT_ANIMATION_READY_SIZE = 6;
constexpr const char* BUNDLE_NAME_KEY = "bundleName";
constexpr const char* DM_PKG_NAME = "ohos.distributedhardware.devicemanager";
constexpr const char* ACTION_CHOOSE = "ohos.want.action.select";
constexpr const char* HIGHEST_PRIORITY_ABILITY_ENTITY = "flag.home.intent.from.system";
constexpr const char* DMS_API_VERSION = "dmsApiVersion";
constexpr const char* DMS_IS_CALLER_BACKGROUND = "dmsIsCallerBackGround";
constexpr const char* DMS_PROCESS_NAME = "distributedsched";
constexpr const char* DMS_MISSION_ID = "dmsMissionId";
constexpr const char* BOOTEVENT_APPFWK_READY = "bootevent.appfwk.ready";
constexpr const char* BOOTEVENT_BOOT_COMPLETED = "bootevent.boot.completed";
constexpr const char* BOOTEVENT_BOOT_ANIMATION_STARTED = "bootevent.bootanimation.started";
constexpr const char* BOOTEVENT_BOOT_ANIMATION_READY = "bootevent.bootanimation.ready";
constexpr const char* NEED_STARTINGWINDOW = "ohos.ability.NeedStartingWindow";
constexpr const char* PERMISSIONMGR_BUNDLE_NAME = "com.ohos.permissionmanager";
constexpr const char* PERMISSIONMGR_ABILITY_NAME = "com.ohos.permissionmanager.GrantAbility";
constexpr const char* SCENEBOARD_BUNDLE_NAME = "com.ohos.sceneboard";
constexpr const char* SPECIFY_TOKEN_ID = "specifyTokenId";
constexpr const char* PROCESS_SUFFIX = "embeddable";
constexpr int32_t DEFAULT_DMS_MISSION_ID = -1;
constexpr const char* PARAM_PREVENT_STARTABILITY = "persist.sys.abilityms.prevent_startability";
constexpr const char* SUSPEND_SERVICE_CONFIG_FILE = "/etc/efficiency_manager/prevent_startability_whitelist.json";
constexpr const char* VPN_ALLOWLIST_CONFIG_FILE = "/etc/ability_runtime/vpn_startability_allowlist.json";
constexpr const char* DEFAULT_VPN_ALLOWLIST_CONFIG_FILE = "/system/etc/vpn_startability_allowlist.json";
constexpr const char* VPN_ALLOW_BUNDLENAMES = "bundleNames";
constexpr int32_t MAX_BUFFER = 2048;
constexpr int32_t API12 = 12;
constexpr int32_t API_VERSION_MOD = 100;
constexpr const char* WHITE_LIST = "white_list";
constexpr const char* SUPPORT_COLLABORATE_INDEX = "ohos.extra.param.key.supportCollaborateIndex";
constexpr const char* COLLABORATE_KEY = "ohos.dms.collabToken";
constexpr const char* IS_CALLING_FROM_DMS = "supportCollaborativeCallingFromDmsInAAFwk";
constexpr int32_t CLEAR_REASON_DELAY_TIME = 3000000;  // 3s
constexpr const char* LIFE_CYCLE_START = "start";
constexpr const char* LIFE_CYCLE_CONNECT = "connect";
constexpr const char* LIFE_CYCLE_MINIMIZE = "minimize";
constexpr const char* LIFE_CYCLE_TERMINATE = "terminate";
constexpr const char* LIFE_CYCLE_PRELOAD = "preload";
constexpr uint32_t TARGET_TYPE_INIT = 100;
constexpr int64_t USER_SWITCH_TIMEOUT = 3 * 1000; // 3s
constexpr const char* SUPPORT_LINKAGE_SCENE = "const.window.supportLinkageScene";
constexpr const char* KEY_SPECIFIED_FLAG = "com.ohos.param.specifiedFlag";

const bool REGISTER_RESULT =
    SystemAbility::MakeAndRegisterAbility(DelayedSingleton<AbilityManagerService>::GetInstance().get());
sptr<AbilityManagerService> AbilityManagerService::instance_;

AbilityManagerService::AbilityManagerService()
    : SystemAbility(ABILITY_MGR_SERVICE_ID, true),
      state_(ServiceRunningState::STATE_NOT_START)
{}

AbilityManagerService::~AbilityManagerService()
{}

std::shared_ptr<AbilityManagerService> AbilityManagerService::GetPubInstance()
{
    return DelayedSingleton<AbilityManagerService>::GetInstance();
}

void AbilityManagerService::OnStart()
{
    if (state_ == ServiceRunningState::STATE_RUNNING) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "started");
        return;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "starting");
    if (!Init()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed  init");
        return;
    }
    state_ = ServiceRunningState::STATE_RUNNING;
    /* Publish service maybe failed, so we need call this function at the last,
     * so it can't affect the TDD test program */
    instance_ = DelayedSingleton<AbilityManagerService>::GetInstance().get();
    if (instance_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "instance_ null");
        return;
    }
    auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
    if (bundleMgrHelper) {
        bundleMgrHelper->SetBmsReady(false);
    }
    bool ret = Publish(instance_);
    if (!ret) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "publish failed");
        return;
    }

    SetParameter(BOOTEVENT_APPFWK_READY, "true");
    bool bgTaskMgr = AddSystemAbilityListener(BACKGROUND_TASK_MANAGER_SERVICE_ID);
    bool distributedMgr = AddSystemAbilityListener(DISTRIBUTED_SCHED_SA_ID);
    bool bundleMgr = AddSystemAbilityListener(BUNDLE_MGR_SERVICE_SYS_ABILITY_ID);
#ifdef SUPPORT_SCREEN
    if (!AddSystemAbilityListener(MULTIMODAL_INPUT_SERVICE_ID)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "OnStart, add listener err");
    }
#endif
    bool windowMgr = AddSystemAbilityListener(WINDOW_MANAGER_SERVICE_ID);
    if (!bgTaskMgr || !distributedMgr || !bundleMgr || !windowMgr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "OnStart, add listeners err");
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "onStart success");
    auto pid = getpid();
    std::unordered_map<std::string, std::string> payload;
    payload["pid"] = std::to_string(pid);
    OHOS::ConcurrentTask::ConcurrentTaskClient::GetInstance().RequestAuth(payload);
}

bool AbilityManagerService::Init()
{
    HiviewDFX::Watchdog::GetInstance().InitFfrtWatchdog(); // For ffrt watchdog available in foundation
    taskHandler_ = TaskHandlerWrap::CreateQueueHandler(AbilityConfig::NAME_ABILITY_MGR_SERVICE);
    eventHandler_ = std::make_shared<AbilityEventHandler>(taskHandler_, weak_from_this());
    freeInstallManager_ = std::make_shared<FreeInstallManager>();
    CHECK_POINTER_RETURN_BOOL(freeInstallManager_);

    AmsConfigurationParameter::GetInstance().Parse();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "config parse");
    subManagersHelper_ = std::make_shared<SubManagersHelper>(taskHandler_, eventHandler_);
    subManagersHelper_->InitSubManagers(MAIN_USER_ID, true);
    SwitchManagers(U0_USER_ID, false);
#ifdef SUPPORT_SCREEN
    implicitStartProcessor_ = std::make_shared<ImplicitStartProcessor>();
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        InitFocusListener();
    }
    AppExecFwk::AbilityFirstFrameStateObserverManager::GetInstance().Init();
#endif

    DelayedSingleton<ConnectionStateManager>::GetInstance()->Init(taskHandler_);

    InitInterceptor();
    InitDeepLinkReserve();

    abilityAutoStartupService_ = std::make_shared<AbilityRuntime::AbilityAutoStartupService>();
    InitPushTask();
    AbilityCacheManager::GetInstance().Init(AppUtils::GetInstance().GetLimitMaximumExtensionsPerDevice(),
        AppUtils::GetInstance().GetLimitMaximumExtensionsPerProc());

    SubscribeScreenUnlockedEvent();
    SubscribeUserUnlockedEvent();
    AddWatchParameters();
    appExitReasonHelper_ = std::make_shared<AppExitReasonHelper>(subManagersHelper_);
    InitAppSpawnMsgPipe();
    insightIntentEventMgr_ = std::make_shared<AbilityRuntime::InsightIntentEventMgr>();
    insightIntentEventMgr_->SubscribeSysEventReceiver();
    ReportDataPartitionUsageManager::SendReportDataPartitionUsageEvent();
#ifdef RESOURCE_SCHEDULE_SERVICE_ENABLE
    ResourceSchedule::ResSchedClient::GetInstance().InitKillReasonListener();
#endif
    TAG_LOGI(AAFwkTag::ABILITYMGR, "init success");
    return true;
}

void AbilityManagerService::InitDeepLinkReserve()
{
    if (!DeepLinkReserveConfig::GetInstance().LoadConfiguration()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "initDeepLinkReserve failed");
    }
}

void AbilityManagerService::InitInterceptor()
{
    interceptorExecuter_ = std::make_shared<AbilityInterceptorExecuter>();
    interceptorExecuter_->AddInterceptor("ScreenUnlock", std::make_shared<ScreenUnlockInterceptor>());
    interceptorExecuter_->AddInterceptor("CrowdTest", std::make_shared<CrowdTestInterceptor>());
    interceptorExecuter_->AddInterceptor("Control", std::make_shared<ControlInterceptor>());
    afterCheckExecuter_ = std::make_shared<AbilityInterceptorExecuter>();
    afterCheckExecuter_->AddInterceptor("ExtensionControl", std::make_shared<ExtensionControlInterceptor>());
    afterCheckExecuter_->AddInterceptor("StartOtherApp", std::make_shared<StartOtherAppInterceptor>());
    afterCheckExecuter_->AddInterceptor("DisposedRule", std::make_shared<DisposedRuleInterceptor>());
    afterCheckExecuter_->AddInterceptor("EcologicalRule", std::make_shared<EcologicalRuleInterceptor>());
    afterCheckExecuter_->SetTaskHandler(taskHandler_);
    bool isAppJumpEnabled = OHOS::system::GetBoolParameter(
        OHOS::AppExecFwk::PARAMETER_APP_JUMP_INTERCEPTOR_ENABLE, false);
    if (isAppJumpEnabled) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "app jump enabled, add abilityJumpInterceptor");
        interceptorExecuter_->AddInterceptor("AbilityJump", std::make_shared<AbilityJumpInterceptor>());
    }
    if (AppUtils::GetInstance().IsStartOptionsWithAnimation()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "add BlockAllAppStartInterceptor");
        interceptorExecuter_->AddInterceptor("BlockAllAppStart", std::make_shared<BlockAllAppStartInterceptor>());
    }
}

 void AbilityManagerService::InitAppSpawnMsgPipe()
 {
     int32_t pipeFd[2];
     if (pipe(pipeFd) != 0) {
         TAG_LOGE(AAFwkTag::ABILITYMGR, "create pipe failed");
         return;
     }
     rFd_ = pipeFd[0];
     wFd_ = pipeFd[1];
     fdsan_exchange_owner_tag(rFd_, 0, static_cast<uint32_t>(AAFwkTag::ABILITYMGR));
     fdsan_exchange_owner_tag(wFd_, 0, static_cast<uint32_t>(AAFwkTag::ABILITYMGR));
     *ptrRFd_ = rFd_;
     auto context = new (std::nothrow) std::weak_ptr<AbilityManagerService>(shared_from_this());
     if (context == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "context null");
        return;
     }
     int32_t ret = WatchParameter(APPSPAWN_STARTED, ExitReasonUtil::AppSpawnStartCallback, context);
     if (ret != 0) {
         TAG_LOGE(AAFwkTag::ABILITYMGR, "watch parameter ret: %{public}d", ret);
         return;
     }
     ffrt_qos_t taskQos = 0;
     ret = ffrt_epoll_ctl(taskQos, EPOLL_CTL_ADD, rFd_, EPOLLIN, static_cast<void*>(ptrRFd_.get()),
        ExitReasonUtil::ProcessSignalData);
     if (ret != 0) {
         TAG_LOGE(AAFwkTag::ABILITYMGR, "ffrt_epoll_ctl failed, ret: %{public}d", ret);
         fdsan_close_with_tag(rFd_, static_cast<uint32_t>(AAFwkTag::ABILITYMGR));
         return;
     }
     TAG_LOGI(AAFwkTag::ABILITYMGR, "Listen signal msg ...");
 }

void AbilityManagerService::InitInterceptorForScreenUnlock()
{
    if (interceptorExecuter_) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "SU life, begin");
        interceptorExecuter_->AddInterceptor("ScreenUnlock", std::make_shared<ScreenUnlockInterceptor>());
    }
}

void AbilityManagerService::InitPushTask()
{
    if (taskHandler_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "taskHandler_ null");
        return;
    }

    auto initStartupFlagTask = [aams = shared_from_this()]() { aams->InitStartupFlag(); };
    taskHandler_->SubmitTask(initStartupFlagTask, "InitStartupFlag");

    auto initExtensionConfigTask = [aams = shared_from_this()]() {
        DelayedSingleton<ExtensionConfig>::GetInstance()->LoadExtensionConfiguration();
        if (aams) {
            aams->ParseVpnAllowListJson(VPN_ALLOWLIST_CONFIG_FILE, VPN_ALLOW_BUNDLENAMES);
        }
    };

    taskHandler_->SubmitTask(initExtensionConfigTask, "InitExtensionConfigTask");

    auto bootCompletedTask = [handler = taskHandler_]() {
        if (ApplicationUtil::IsBootCompleted()) {
            auto task = []() {
                ApplicationUtil::AppFwkBootEventCallback(BOOTEVENT_BOOT_COMPLETED, "true", nullptr);
            };
            CHECK_POINTER(handler);
            handler->SubmitTaskJust(task, "BootCompletedDelayTask", BOOTEVENT_COMPLETED_DELAY_TIME);
        } else {
            WatchParameter(BOOTEVENT_BOOT_COMPLETED, ApplicationUtil::AppFwkBootEventCallback, nullptr);
            TAG_LOGI(AAFwkTag::ABILITYMGR, "init call, InitPushTask suc");
        }
    };
    if (!ParseJsonFromBoot(SUSPEND_SERVICE_CONFIG_FILE)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "parse json fail");
    }
    isParamStartAbilityEnable_ = system::GetBoolParameter(PARAM_PREVENT_STARTABILITY, false);
    taskHandler_->SubmitTask(bootCompletedTask, "BootCompletedTask");
}

void AbilityManagerService::InitStartupFlag()
{
    startUpNewRule_ = CheckNewRuleSwitchState(COMPONENT_STARTUP_NEW_RULES);
    backgroundJudgeFlag_ = CheckNewRuleSwitchState(BACKGROUND_JUDGE_FLAG);
    whiteListassociatedWakeUpFlag_ = CheckNewRuleSwitchState(WHITE_LIST_ASS_WAKEUP_FLAG);
}

void AbilityManagerService::OnStop()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "stop");
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
    std::unique_lock<ffrt::mutex> lock(bgtaskObserverMutex_);
    if (bgtaskObserver_) {
        int ret = BackgroundTaskMgrHelper::UnsubscribeBackgroundTask(*bgtaskObserver_);
        if (ret != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "unsubscribe bgtask failed, err:%{public}d", ret);
        }
    }
#endif
    if (abilityBundleEventCallback_) {
        auto bms = AbilityUtil::GetBundleManagerHelper();
        if (bms) {
            if (!IN_PROCESS_CALL(bms->UnregisterBundleEventCallback(abilityBundleEventCallback_))) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "unsubscribe bundle event failed");
            }
            auto pluginRet = IN_PROCESS_CALL(bms->UnregisterPluginEventCallback(abilityBundleEventCallback_));
            if (pluginRet != ERR_OK) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "UnregisterPluginEventCallback failed: %{public}d", pluginRet);
            }
        }
    }
    eventHandler_.reset();
    taskHandler_.reset();
    state_ = ServiceRunningState::STATE_NOT_START;
}

ServiceRunningState AbilityManagerService::QueryServiceState() const
{
    return state_;
}

void AbilityManagerService::AddWatchParameters()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call AddWatchParameters");
    int32_t ret = WatchParameter(AUTO_STARTUP_READY, AbilityManagerService::HandleAutoStartupReadyCallback, nullptr);
    if (ret != 0) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "watch parameter %{public}s fail with %{public}d",
            AUTO_STARTUP_READY, ret);
    }
}

void AbilityManagerService::HandleAutoStartupReadyCallback(const char *key, const char *value, void *context)
{
    bool changed = system::GetBoolParameter(AUTO_STARTUP_READY, true);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "HandleAutoStartupReadyCallback key %{public}s, value %{public}d", key, changed);
    if (strcmp(key, AUTO_STARTUP_READY) != 0 || !changed) {
        return;
    }
    auto abilityMgr = DelayedSingleton<AbilityManagerService>::GetInstance();
    if (abilityMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityMgr is nullptr.");
        return;
    }
    int32_t userId = abilityMgr->GetValidUserId(DEFAULT_INVAL_VALUE);
    abilityMgr->StartAutoStartupApps(userId);
}

int AbilityManagerService::StartAbility(const Want &want, int32_t userId, int requestCode,
    uint64_t specifiedFullTokenId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    if (specifiedFullTokenId != 0 && IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "specifiedFullTokenId only support for DMS");
        specifiedFullTokenId = 0;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    bool isDebugApp = want.GetBoolParam(AbilityConfig::DEBUG_APP, false);
    bool isNativeDebugApp = want.GetBoolParam(AbilityConfig::NATIVE_DEBUG, false);
    bool hasWindowOptions = (want.HasParameter(Want::PARAM_RESV_WINDOW_LEFT) ||
        want.HasParameter(Want::PARAM_RESV_WINDOW_TOP) ||
        want.HasParameter(Want::PARAM_RESV_WINDOW_HEIGHT) ||
        want.HasParameter(Want::PARAM_RESV_WINDOW_WIDTH));
    bool isDebugFromLocal = want.GetBoolParam(DEBUG_FROM, false);
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "isDebugApp=%{public}d, hasWindowOptions=%{public}d, isNativeDebugApp=%{public}d, isDebugFromLocal=%{public}d",
        static_cast<int>(isDebugApp), static_cast<int>(hasWindowOptions), static_cast<int>(isNativeDebugApp),
        isDebugFromLocal);
    bool checkDeveloperModeFlag = (isDebugApp || hasWindowOptions || isNativeDebugApp || isDebugFromLocal);
    if (checkDeveloperModeFlag) {
        if (isDebugFromLocal &&
            !AAFwk::PermissionVerification::GetInstance()->VerifyStartLocalDebug(IPCSkeleton::GetCallingTokenID())) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "local debugging, permission denied");
            return CHECK_PERMISSION_FAILED;
        } else if (!isDebugFromLocal && !system::GetBoolParameter(DEVELOPER_MODE_STATE, false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer Mode");
            return ERR_NOT_DEVELOPER_MODE;
        }
        int32_t err = ERR_OK;
        if (userId == DEFAULT_INVAL_VALUE) {
            userId = GetValidUserId(userId);
        }
        if ((err = StartAbilityUtils::CheckAppProvisionMode(want, userId, nullptr)) != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "checkAppProvisionMode returns errcode=%{public}d", err);
            return err;
        }
    }
    if (!UnlockScreenManager::GetInstance().UnlockScreen()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "need passord to unlock");
        return ERR_UNLOCK_SCREEN_FAILED_IN_DEVELOPER_MODE;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "coldStart:%{public}d", want.GetBoolParam("coldStart", false));
    bool startWithAccount = want.GetBoolParam(START_ABILITY_TYPE, false);
    if (startWithAccount || IsCrossUserCall(userId)) {
        (const_cast<Want &>(want)).RemoveParam(START_ABILITY_TYPE);
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    if (hasWindowOptions && !AppUtils::GetInstance().IsStartOptionsWithAnimation()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "window options not supported");
        return ERR_NOT_SUPPORTED_PRODUCT_TYPE;
    }
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    EventInfo eventInfo = BuildEventInfo(want, userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(want);
#endif
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .requestCode = requestCode,
        .userId = userId,
        .specifiedFullTokenId = specifiedFullTokenId,
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    AAFWK::ContinueRadar::GetInstance().ClickIconStartAbility("StartAbilityWrap", want.GetFlags(), ret);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityError:%{public}d", eventInfo.errCode);
    }
    return ret;
}

int AbilityManagerService::StartAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, int requestCode, uint64_t specifiedFullTokenId)
{
    if (specifiedFullTokenId != 0 && IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "specifiedFullTokenId only support for DMS");
        specifiedFullTokenId = 0;
    }
    StartAbilityWrapParam param = {
        .want = want,
        .callerToken = callerToken,
        .requestCode = requestCode,
        .userId = userId,
        .specifiedFullTokenId = specifiedFullTokenId,
        .removeInsightIntentFlag = true,
    };
    return StartAbilityWithRemoveIntentFlag(param);
}

int AbilityManagerService::StartAbilityWithRemoveIntentFlag(const StartAbilityWrapParam &param)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", param.want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !param.want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start ability with caller");
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(param.want));
    //intent openlink do not RemoveInsightIntent
    if (param.removeInsightIntentFlag) {
        InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(param.want));
    }
#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(param.want);
#endif
    return StartAbilityByFreeInstall(param);
}

int32_t AbilityManagerService::StartAbilityByFreeInstall(const StartAbilityWrapParam &param)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    bool startWithAccount = param.want.GetBoolParam(START_ABILITY_TYPE, false);
    if (startWithAccount || IsCrossUserCall(param.userId)) {
        (const_cast<Want &>(param.want)).RemoveParam(START_ABILITY_TYPE);
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    auto flags = param.want.GetFlags();
    EventInfo eventInfo = BuildEventInfo(param.want, param.userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if ((flags & Want::FLAG_ABILITY_CONTINUATION) == Want::FLAG_ABILITY_CONTINUATION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not allow startAbility with continuation flags:%{public}d",
            ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG,
            "continuation flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start ability come, ability is %{public}s, userId is %{public}d",
        param.want.GetElement().GetAbilityName().c_str(), param.userId);
    int32_t ret = StartAbilityWrap(param);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityByFreeInstall error:%{public}d", ret);
    }
    return ret;
}

int AbilityManagerService::StartAbilityWithSpecifyTokenId(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint32_t specifyTokenId, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    if (IPCSkeleton::GetCallingUid() != FOUNDATION_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility with specialId, current process not foundation process");
        return CHECK_PERMISSION_FAILED;
    }
    return StartAbilityWithSpecifyTokenIdInner(want, callerToken, specifyTokenId, false, userId, requestCode);
}

int AbilityManagerService::StartAbilityWithSpecifyTokenIdInner(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint32_t specifyTokenId, bool isPendingWantCaller, int32_t userId, int requestCode)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    auto flags = want.GetFlags();
    EventInfo eventInfo = BuildEventInfo(want, userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if ((flags & Want::FLAG_ABILITY_CONTINUATION) == Want::FLAG_ABILITY_CONTINUATION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility with continuation flags not allowed:%{public}d",
            ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG,
            "continuation flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "start ability come, ability:%{public}s, userId:%{public}d, "
        "specifyTokenId:%{public}u, appIndex:%{public}d", want.GetElement().GetAbilityName().c_str(), userId,
        specifyTokenId, want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, -1));
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .callerToken = callerToken,
        .requestCode = requestCode,
        .isPendingWantCaller = isPendingWantCaller,
        .userId = userId,
        .specifyTokenId = specifyTokenId,
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility with specified token error:%{public}d", ret);
    }
    return ret;
}

int AbilityManagerService::StartAbilityWithSpecifyTokenIdInner(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, bool isPendingWantCaller,
    int32_t userId, int requestCode, uint32_t callerTokenId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start ability with startOptions by trigger.");
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    return StartUIAbilityForOptionWrap(
        want, startOptions, callerToken, isPendingWantCaller, userId, requestCode, callerTokenId);
}

int32_t AbilityManagerService::StartAbilityByInsightIntent(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint64_t intentId, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    std::string bundleNameFromWant = want.GetElement().GetBundleName();
    std::string bundleNameFromIntentMgr = "";
    if (DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->
        GetBundleName(intentId, bundleNameFromIntentMgr) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no such bundle matched intentId");
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no such bundle matched token");
        return ERR_INVALID_VALUE;
    }
    std::string bundleNameFromAbilityRecord = abilityRecord->GetAbilityInfo().bundleName;
    if (!bundleNameFromWant.empty() && bundleNameFromWant == bundleNameFromIntentMgr &&
        bundleNameFromWant == bundleNameFromAbilityRecord) {
        AbilityUtil::RemoveInstanceKey(const_cast<Want &>(want));
        TAG_LOGI(AAFwkTag::ABILITYMGR, "bundleName match");
        return StartAbility(want, callerToken, userId, -1);
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "bundleName not match");
    return ERR_INSIGHT_INTENT_START_INVALID_COMPONENT;
}

int AbilityManagerService::StartAbilityByUIContentSession(const Want &want, const sptr<IRemoteObject> &callerToken,
    const sptr<SessionInfo> &sessionInfo, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    if (!callerToken || !sessionInfo) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken or sessionInfo null");
        return ERR_INVALID_VALUE;
    }
    sptr<IRemoteObject> token;
#ifdef SUPPORT_SCREEN
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        Rosen::FocusChangeInfo focusChangeInfo;
        Rosen::WindowManager::GetInstance().GetFocusWindowInfo(focusChangeInfo);
        token = focusChangeInfo.abilityToken_;
    } else {
        if (!GetWMSHandler()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "wmsHandler_ null");
            return ERR_INVALID_VALUE;
        }
        GetWMSHandler()->GetFocusWindow(token);
    }
#endif // SUPPORT_SCREEN
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return ERR_INVALID_VALUE;
    }

    if (token != sessionInfo->callerToken) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken unequal to top ability token");
        return NOT_TOP_ABILITY;
    }
    AbilityUtil::RemoveInstanceKey(const_cast<Want &>(want));
    return StartAbility(want, callerToken, userId, requestCode);
}

int AbilityManagerService::StartAbilityByUIContentSession(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, const sptr<SessionInfo> &sessionInfo, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    if (!callerToken || !sessionInfo) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken or sessionInfo null");
        return ERR_INVALID_VALUE;
    }
    sptr<IRemoteObject> token;
#ifdef SUPPORT_SCREEN
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        Rosen::FocusChangeInfo focusChangeInfo;
        Rosen::WindowManager::GetInstance().GetFocusWindowInfo(focusChangeInfo);
        token = focusChangeInfo.abilityToken_;
    } else {
        if (!GetWMSHandler()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "wmsHandler_ null");
            return ERR_INVALID_VALUE;
        }
        GetWMSHandler()->GetFocusWindow(token);
    }
#endif // SUPPORT_SCREEN

    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return ERR_INVALID_VALUE;
    }

    if (token != sessionInfo->callerToken) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken unequal to top ability token");
        return NOT_TOP_ABILITY;
    }
    return StartAbility(want, startOptions, callerToken, userId, requestCode);
}

int AbilityManagerService::StartAbilityOnlyUIAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    uint32_t specifyTokenId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    if (IPCSkeleton::GetCallingUid() != FOUNDATION_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbility with specialId, process not foundation process");
        return CHECK_PERMISSION_FAILED;
    }

    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    auto flags = want.GetFlags();
    EventInfo eventInfo = BuildEventInfo(want, DEFAULT_INVAL_VALUE);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if ((flags & Want::FLAG_ABILITY_CONTINUATION) == Want::FLAG_ABILITY_CONTINUATION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbility not allowed:%{public}d", ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG, "not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "start, ability: %{public}s, userId: %{public}d, specifyTokenId: %{public}u",
        want.GetElement().GetAbilityName().c_str(), DEFAULT_INVAL_VALUE, specifyTokenId);
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .callerToken = callerToken,
        .specifyTokenId = specifyTokenId,
        .isUIAbilityOnly = true,
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityOnlyUIAbility error:%{public}d", ret);
    }
    return ret;
}

int AbilityManagerService::StartAbilityAsCaller(const Want &want, const sptr<IRemoteObject> &callerToken,
    sptr<IRemoteObject> asCallerSourceToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    return StartAbilityAsCallerDetails(want, callerToken, asCallerSourceToken, userId, requestCode);
}

int AbilityManagerService::ImplicitStartAbilityAsCaller(const Want &want, const sptr<IRemoteObject> &callerToken,
    sptr<IRemoteObject> asCallerSourceToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    return StartAbilityAsCallerDetails(want, callerToken, asCallerSourceToken, userId,
        requestCode, true);
}

int AbilityManagerService::StartAbilityAsCallerDetails(const Want &want, const sptr<IRemoteObject> &callerToken,
    sptr<IRemoteObject> asCallerSourceToken, int32_t userId, int requestCode, bool isImplicit, bool isAppCloneSelector,
    uint32_t callerAccessTokenId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_CALLER_IS_SYSTEM_APP;
    auto flags = want.GetFlags();
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    EventInfo eventInfo = BuildEventInfo(want, userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if ((flags & Want::FLAG_ABILITY_CONTINUATION) == Want::FLAG_ABILITY_CONTINUATION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility with continuation flags not allowed:%{public}d",
            ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG,
            "continuation flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    AAFwk::Want newWant = want;
    UpdateCallerInfoUtil::GetInstance().UpdateAsCallerSourceInfo(newWant, asCallerSourceToken, callerToken);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start ability come, ability:%{public}s, userId:%{public}d",
        want.GetElement().GetAbilityName().c_str(), userId);
    std::string callerPkg;
    std::string targetPkg;
    if (AbilityUtil::CheckJumpInterceptorWant(newWant, callerPkg, targetPkg)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR,
            "call from interceptor dialog, callerPkg:%{public}s, targetPkg:%{public}s",
            callerPkg.c_str(), targetPkg.c_str());
        AbilityUtil::AddAbilityJumpRuleToBms(callerPkg, targetPkg, GetValidUserId(userId));
    }
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = newWant,
        .callerToken = callerToken,
        .requestCode = requestCode,
        .userId = userId,
        .isStartAsCaller = true,
        .specifyTokenId = callerAccessTokenId,
        .isImplicit = isImplicit,
        .isAppCloneSelector = isAppCloneSelector,
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "start ability as caller failed:%{public}d", ret);
    }
    return ret;
}

int AbilityManagerService::StartAbilityPublicPrechainCheck(StartAbilityParams &params)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    // 1. CheckCallerToken
    if (params.callerToken != nullptr && !VerificationAllToken(params.callerToken)) {
        auto isSpecificSA = AAFwk::PermissionVerification::GetInstance()->
            CheckSpecificSystemAbilityAccessPermission(DMS_PROCESS_NAME);
        if (!isSpecificSA) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "verificationAllToken failed");
            return ERR_INVALID_CALLER;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "caller specific system ability");
    }

    // 2. validUserId, multi-user
    if (!JudgeMultiUserConcurrency(params.GetValidUserId())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    return ERR_OK;
}

int AbilityManagerService::StartAbilityPrechainInterceptor(StartAbilityParams &params)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(params.want, params.requestCode,
        params.GetValidUserId(), true, nullptr, shouldBlockFunc);
    auto interceptorResult = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (interceptorResult != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error");
        return interceptorResult;
    }

    return ERR_OK;
}

bool AbilityManagerService::StartAbilityInChain(StartAbilityParams &params, int &result)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!StartAbilitySandboxSavefile::GetInstance().MatchStartRequest(params)) {
        return false;
    }

    result = StartAbilityPublicPrechainCheck(params);
    if (result != ERR_OK) {
        return true;
    }
    result = StartAbilityPrechainInterceptor(params);
    if (result != ERR_OK) {
        return true;
    }
    result = StartAbilitySandboxSavefile::GetInstance().HandleStartRequest(params);
    return true;
}

int AbilityManagerService::StartAbilityWrap(const StartAbilityWrapParam &startAbilityWrapParam)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    StartAbilityParams startParams(const_cast<Want &>(startAbilityWrapParam.want));
    startParams.callerToken = startAbilityWrapParam.callerToken;
    startParams.userId = startAbilityWrapParam.userId;
    startParams.requestCode = startAbilityWrapParam.requestCode;
    startParams.isStartAsCaller = startAbilityWrapParam.isStartAsCaller;
    startParams.SetValidUserId(GetValidUserId(startAbilityWrapParam.userId));

    int result = ERR_OK;
    if (StartAbilityInChain(startParams, result)) {
        return result;
    }

    return StartAbilityInner(const_cast<StartAbilityWrapParam &>(startAbilityWrapParam));
}

void AbilityManagerService::SetReserveInfo(const std::string &linkString, AbilityRequest& abilityRequest)
{
    if (!linkString.size()) {
        return;
    }

#ifdef SUPPORT_SCREEN
    abilityRequest.uriReservedFlag =
        DeepLinkReserveConfig::GetInstance().IsLinkReserved(linkString, abilityRequest.reservedBundleName);
#endif // SUPPORT_SCREEN
}

int AbilityManagerService::CheckExtensionCallPermission(const Want& want, const AbilityRequest& abilityRequest,
    uint32_t specifyTokenId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, "startExtensionCheck");
    auto isSACall = AAFwk::PermissionVerification::GetInstance()->IsSACallByTokenId(specifyTokenId);
    bool isSystemAppCall = false;
    if (abilityRequest.specifiedFullTokenId != 0) {
        isSystemAppCall = Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(
            abilityRequest.specifiedFullTokenId);
    } else {
        isSystemAppCall = AAFwk::PermissionVerification::GetInstance()->IsSystemAppCallByTokenId(specifyTokenId);
    }
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCallByTokenId(specifyTokenId);
    auto isToPermissionMgr = IsTargetPermission(want);
    if (!isSACall && !isSystemAppCall && !isShellCall && !isToPermissionMgr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "cannot start, use startServiceExtensionAbility");
        return ERR_WRONG_INTERFACE_CALL;
    }
    int result = CheckCallServicePermission(abilityRequest);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check permission failed");
    }
    return result;
}

int AbilityManagerService::CheckServiceCallPermission(const AbilityRequest& abilityRequest,
    const AppExecFwk::AbilityInfo& abilityInfo)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "Check call service or extension permission, name is %{public}s.", abilityInfo.name.c_str());
    int result = CheckCallServicePermission(abilityRequest);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check permission failed");
    }
    return result;
}

int AbilityManagerService::CheckBrokerCallPermission(const AbilityRequest& abilityRequest,
    const AppExecFwk::AbilityInfo& abilityInfo)
{
    // temp add for broker, remove when delete issacall
    if (abilityRequest.collaboratorType != CollaboratorType::RESERVE_TYPE && !abilityInfo.visible) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Check permission failed");
        return CHECK_PERMISSION_FAILED;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "Check call service or extension permission, name is %{public}s.", abilityInfo.name.c_str());
    auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
    if (collaborator == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "collaborator null");
        return CHECK_PERMISSION_FAILED;
    }
    int result = collaborator->CheckCallAbilityPermission(abilityRequest.want);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check broker permission failed");
        return CHECK_PERMISSION_FAILED;
    }
    return result;
}

int AbilityManagerService::CheckAbilityCallPermission(const AbilityRequest& abilityRequest,
    const AppExecFwk::AbilityInfo& abilityInfo, uint32_t specifyTokenId,
    bool isSelector, bool isFreeInstallFromService)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Check call ability permission, name is %{public}s.", abilityInfo.name.c_str());
    if (AbilityPermissionUtil::GetInstance().IsStartSelfUIAbility()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "call from capi, already checked");
        return ERR_OK;
    }
    int result = CheckCallAbilityPermission(abilityRequest, isSelector, specifyTokenId, false, isFreeInstallFromService);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check permission failed");
    }
    return AbilityErrorUtil::ConvertToOriginErrorCode(result);
}

int AbilityManagerService::CheckCallPermission(const Want& want, const AppExecFwk::AbilityInfo& abilityInfo,
    const AbilityRequest& abilityRequest, bool isForegroundToRestartApp,
    bool isSendDialogResult, uint32_t specifyTokenId,
    const std::string& callerBundleName, bool isSelector, bool isFreeInstallFromService)
{
    auto type = abilityInfo.type;
    if (type == AppExecFwk::AbilityType::DATA) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot start data ability by start ability");
        return ERR_WRONG_INTERFACE_CALL;
    }
    if (abilityRequest.specifiedFullTokenId != 0) {
        specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    }
    if (type == AppExecFwk::AbilityType::EXTENSION) {
        return CheckExtensionCallPermission(want, abilityRequest, specifyTokenId);
    }
    if (type == AppExecFwk::AbilityType::SERVICE) {
        return CheckServiceCallPermission(abilityRequest, abilityInfo);
    }
    if ((callerBundleName == AppUtils::GetInstance().GetBrokerDelegateBundleName() &&
        AppUtils::GetInstance().IsSupportAncoApp()) ||
        IPCSkeleton::GetCallingUid() == AppUtils::GetInstance().GetCollaboratorBrokerUID()) {
        return CheckBrokerCallPermission(abilityRequest, abilityInfo);
    }
    if (!isForegroundToRestartApp && (!isSendDialogResult || want.GetBoolParam("isSelector", false))) {
        return CheckAbilityCallPermission(abilityRequest, abilityInfo, specifyTokenId, isSelector, isFreeInstallFromService);
    }
    return ERR_OK;
}

void AbilityManagerService::CheckExtensionRateLimit(const Want &want)
{
    if (AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        return;
    }
    auto uid = IPCSkeleton::GetCallingUid();
    auto limitResult = RateLimiter::GetInstance().CheckExtensionLimit(uid);
    if (!limitResult.limited) {
        return;
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Rate limited triggered, limit:%{public}d, uid:%{public}d",
        limitResult.triggeredLimit, uid);
    if (RateLimiter::GetInstance().CheckReportLimit(uid, limitResult.triggeredLimit)) {
        return;
    }
    std::string callerBundleName;
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER(bms)
    IN_PROCESS_CALL(bms->GetNameForUid(uid, callerBundleName));
    if (callerBundleName.empty()) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "callerBundleName empty, uid:%{public}d", uid);
        return;
    }
    EventInfo eventInfo;
    eventInfo.abilityName = want.GetElement().GetBundleName() + "/" + want.GetElement().GetAbilityName();
    eventInfo.callerBundleName = callerBundleName;
    eventInfo.moduleName = "ReachLimit";
    eventInfo.extensionType = limitResult.triggeredLimit;
    EventReport::SendStartAbilityOtherExtensionEvent(EventName::START_ABILITY_OTHER_EXTENSION, eventInfo);
}

int AbilityManagerService::StartAbilityInner(StartAbilityWrapParam &param)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!param.isStartAsCaller || param.isImplicit) {
        param.want.RemoveParam("ability.params.picker.erms.policy");
    }
    std::string dialogSessionId = param.want.GetStringParam("dialogSessionId");
    bool isSendDialogResult = false;
    AAFwk::SelectorType selectorType = AAFwk::SelectorType::WITHOUT_SELECTOR;
#ifdef SUPPORT_SCREEN
    auto dialogCallerInfo = DialogSessionManager::GetInstance().GetDialogCallerInfo(dialogSessionId);
    if (!dialogSessionId.empty() && dialogCallerInfo != nullptr) {
        isSendDialogResult = true;
        selectorType = dialogCallerInfo->type;
    }
#endif // SUPPORT_SCREEN

    EventInfo eventInfo = BuildEventInfo(param.want, param.userId);
    int result = ERR_OK;
    // prevent the app from dominating the screen
    if (param.callerToken == nullptr && !IsCallerSceneBoard() && !isSendDialogResult &&
        !param.isForegroundToRestartApp && !param.isServiceMatch &&
        AbilityPermissionUtil::GetInstance().IsDominateScreen(param.want, param.isPendingWantCaller)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller invalid");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CALLER, "caller invalid");
        return ERR_INVALID_CALLER;
    }

    if (!DlpUtils::AccessCheck(param.callerToken, param.want) ||
        VerifyAccountPermission(param.userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityInner permission verification failed");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, CHECK_PERMISSION_FAILED,
            "dlp permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (AbilityUtil::HandleDlpApp(param.want)) {
        InsightIntentExecuteParam::RemoveInsightIntent(param.want);
        result = StartExtensionAbilityInner(param.want, param.callerToken, param.userId,
            AppExecFwk::ExtensionAbilityType::SERVICE, false, false, true, param.isStartAsCaller);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartExtensionAbilityInner failed");
        return result;
    }
    bool isTargetPlugin = false;
    if (auto pluginRet = CheckStartPlugin(param.want, param.callerToken, isTargetPlugin); pluginRet != ERR_OK) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, pluginRet, "CheckStartPlugin failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(pluginRet);
    }

    AbilityUtil::RemoveWindowModeKey(param.want);
    if (param.callerToken != nullptr && !param.isFreeInstallFromService &&
        !VerificationAllToken(param.callerToken) && !isSendDialogResult) {
        auto isSpecificSA = AAFwk::PermissionVerification::GetInstance()->
            CheckSpecificSystemAbilityAccessPermission(DMS_PROCESS_NAME) ||
            (param.want.GetBoolParam(PARAM_RESV_ANCO_IS_NEED_UPDATE_NAME, false) &&
            AAFwk::PermissionVerification::GetInstance()->VerifyFusionAccessPermission());
        if (!isSpecificSA) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s verificationAllToken failed", __func__);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_IS_NOT_SPECIFIED_SA, "verification token fail");
            return ERR_INVALID_CALLER;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s:caller specific system ability", __func__);
    }

    int32_t oriValidUserId = GetValidUserId(param.userId);
    int32_t validUserId = oriValidUserId;
    StartAbilityUtils::SetTargetCloneIndexInSameBundle(param.want, param.callerToken);
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(param.want, param.callerToken, appIndex)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_APP_CLONE_INDEX_INVALID, "GetAppIndex failed");
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    if (!param.isForegroundToRestartApp) {
        auto checkRet = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(param.want,
            validUserId, appIndex, param.callerToken, param.isBySCB);
        if (checkRet != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "CheckMultiInstanceAndAppClone failed: %{public}d", checkRet);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkRet, "CheckMultiInstanceAndAppClone failed");
            return checkRet;
        }
    }
    StartAbilityInfoWrap threadLocalInfo(param.want, validUserId, appIndex, param.callerToken);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(param.want, param.requestCode, validUserId,
        true, nullptr, shouldBlockFunc);
    result = interceptorExecuter_ == nullptr ? ERR_NULL_INTERCEPTOR_EXECUTER :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or DoProcess error");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "DoProcess error");
        return result;
    }

    if ((param.want.GetFlags() & Want::FLAG_ABILITY_PREPARE_CONTINUATION) == Want::FLAG_ABILITY_PREPARE_CONTINUATION &&
        IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "flag only support DMS, flag:%{public}d", param.want.GetFlags());
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG, "flag only support DMS");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    if (param.callerToken != nullptr && CheckIfOperateRemote(param.want)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "try to StartRemoteAbility");
        result = StartRemoteAbility(param.want, param.requestCode, validUserId, param.callerToken,
            param.specifyTokenId);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartRemoteAbility failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "non-concurrent unsatisfied");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_CROSS_USER, "non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
    abilityRequest.hideFailureTipDialog = param.hideFailureTipDialog;
    abilityRequest.startSpecifiedParams = param.startSpecifiedParams;
    abilityRequest.isFromOpenLink = param.isFromOpenLink;
#ifdef SUPPORT_SCREEN
    if (ImplicitStartProcessor::IsImplicitStartAction(param.want)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "is implicit start action");
        auto checkResult = AbilityUtil::CheckInstanceKey(param.want);
        if (checkResult != ERR_OK) {
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkResult, "CheckInstanceKey failed");
            return checkResult;
        }
        abilityRequest.Voluation(param.want, param.requestCode, param.callerToken);
        if (param.specifyTokenId > 0 && param.callerToken != nullptr) { // for sa specify tokenId and caller token
            UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, param.callerToken);
        } else if (!param.isStartAsCaller) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
            UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, param.callerToken);
        } else {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "start as caller, skip UpdateCallerInfo!");
        }
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        SetReserveInfo(param.want.GetUriString(), abilityRequest);
        result = implicitStartProcessor_->ImplicitStartAbility(abilityRequest, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "implicit start ability error:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "implicit start error");
        }
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    if (param.want.GetAction().compare(ACTION_CHOOSE) == 0) {
        result = ShowPickerDialog(param.want, validUserId, param.callerToken);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "ShowPickerDialog failed");
        return result;
    }
#endif
    auto abilityRecord = Token::GetAbilityRecordByToken(param.callerToken);
    std::string callerBundleName = abilityRecord ? abilityRecord->GetAbilityInfo().bundleName : "";
    auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
    CollaboratorUtil::UpdateTargetIfNeed(collaborator, param.want, callerBundleName);
    result = GenerateAbilityRequest(param.want, param.requestCode, abilityRequest, param.callerToken, validUserId);
    bool selfFreeInstallEnable = (result == RESOLVE_ABILITY_ERR && param.want.GetElement().GetModuleName() != "" &&
                                  param.want.GetElement().GetBundleName() == callerBundleName);
    bool isStartFreeInstallByWant = AbilityUtil::IsStartFreeInstall(param.want);
    if (isStartFreeInstallByWant || selfFreeInstallEnable) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "selfFreeInstallEnable: %{public}d, isStartFreeInstallByWant: %{public}d",
            selfFreeInstallEnable, isStartFreeInstallByWant);
        Want localWant;
        auto freeInstallResult = PreStartFreeInstall(param.want, param.callerToken, param.specifyTokenId,
            param.isStartAsCaller, localWant);
        if (freeInstallResult != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "preStartFreeInstall failed");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, freeInstallResult, "preStartFreeInstall failed");
            return AbilityErrorUtil::ConvertToOriginErrorCode(freeInstallResult);
        }
        CHECK_POINTER_AND_RETURN(freeInstallManager_, ERR_INVALID_VALUE);

        if (isStartFreeInstallByWant) {
            auto freeInstallParam = std::make_shared<FreeInstallParams>();
            freeInstallParam->isAsync = true;
            freeInstallParam->specifyTokenId = param.specifyTokenId;
            result = freeInstallManager_->StartFreeInstall(localWant, validUserId, param.requestCode,
                param.callerToken, freeInstallParam);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartFreeInstall failed");
            return AbilityErrorUtil::ConvertToOriginErrorCode(result);
        }
        int32_t ret = freeInstallManager_->StartFreeInstall(localWant, validUserId, param.requestCode,
            param.callerToken);
        if (ret == ERR_OK) {
            result = GenerateAbilityRequest(param.want, param.requestCode, abilityRequest, param.callerToken,
                validUserId);
        }
    }

    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "GenerateAbilityRequest error");
        return result;
    }

    if (abilityRequest.requestCode != DEFAULT_REQUEST_CODE &&
        ForegroundAppConnectionManager::IsForegroundAppConnection(abilityRequest.abilityInfo, abilityRecord)) {
        DelayedSingleton<ForegroundAppConnectionManager>::GetInstance()->OnCallerStarted(IPCSkeleton::GetCallingPid(),
            IPCSkeleton::GetCallingUid(), param.want.GetBundle());
    }
    if (param.specifyTokenId > 0 && param.callerToken != nullptr) { // for sa specify tokenId and caller token
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, param.callerToken);
    } else if (!param.isStartAsCaller) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, param.callerToken);
    } else if (callerBundleName == BUNDLE_NAME_DIALOG ||
        (isSendDialogResult && param.want.GetBoolParam("isSelector", false))) {
#ifdef SUPPORT_SCREEN
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        int32_t flag = false;
        if (callerBundleName == BUNDLE_NAME_DIALOG) {
            flag = true;
        }
        implicitStartProcessor_->ResetCallingIdentityAsCaller(
            abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), flag);
#endif // SUPPORT_SCREEN
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    if (param.isUIAbilityOnly && abilityInfo.type != AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability type no UIAbility");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, RESOLVE_CALL_ABILITY_TYPE_ERR, "not UIAbility");
        return ERR_INVALID_VALUE;
    }
    if (abilityInfo.type != AbilityType::PAGE) {
        AbilityStartWithWaitObserverManager::GetInstance().NotifyAATerminateWait(
            param.want, TerminateReason::TERMINATE_FOR_NON_UI_ABILITY);
    }
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    if ((isSendDialogResult && param.want.GetBoolParam("isSelector", false))) {
        param.isImplicit = true;
    }
    abilityRequest.specifiedFullTokenId = param.specifiedFullTokenId;
    result = CheckStaticCfgPermission(abilityRequest, param.isStartAsCaller,
        abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), false, false, param.isImplicit);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_STATIC_CFG_PERMISSION,
            "checkStaticCfgPermission error");
        return ERR_STATIC_CFG_PERMISSION;
    }

    if (!param.isAppCloneSelector) {
        result = CheckCallPermission(param.want, abilityInfo, abilityRequest, param.isForegroundToRestartApp,
            isSendDialogResult, param.specifyTokenId, callerBundleName, param.isImplicit,
            param.isFreeInstallFromService);
        if (result != ERR_OK && !param.isServiceMatch) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "checkCallPermission error, result:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "checkCallPermission error");
            return result;
        }
        abilityRequest.userId = validUserId;
        bool interceptorSelectorFlag =
            isSendDialogResult ? selectorType == AAFwk::SelectorType::INTERCEPTOR_SELECTOR : false;
        if (!interceptorSelectorFlag &&
            !HandleExecuteSAInterceptor(param.want, param.callerToken, abilityRequest, result)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "checkCallPermission error, result:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "HandleExecuteSAInterceptor failed");
            return result;
        }
        Want newWant = abilityRequest.want;
        AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(newWant, param.requestCode, validUserId,
            true, param.callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), param.isStartAsCaller,
            appIndex);
        afterCheckParam.isTargetPlugin = isTargetPlugin;
        result = afterCheckExecuter_ == nullptr ? ERR_NULL_AFTER_CHECK_EXECUTER :
            afterCheckExecuter_->DoProcess(afterCheckParam);
        bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
        newWant.RemoveParam("queryWantFromErms");
        if (result != ERR_OK && isReplaceWantExist == false) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "doProcess failed or replaceWant absent");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "doProcess failed or replaceWant absent");
            return result;
        }
#ifdef SUPPORT_SCREEN
        if (result != ERR_OK && isReplaceWantExist && callerBundleName != BUNDLE_NAME_DIALOG) {
            result = DialogSessionManager::GetInstance().HandleErmsResult(abilityRequest, validUserId, newWant);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "HandleErmsResult failed");
            return result;
        }
        if (result == ERR_OK &&
            DialogSessionManager::GetInstance().IsCreateCloneSelectorDialog(abilityInfo.bundleName, validUserId)) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "create clone selector dialog");
            result = CreateCloneSelectorDialog(abilityRequest, validUserId);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "CreateCloneSelectorDialog failed");
            return result;
        }
#endif // SUPPORT_SCREEN
    }

    if (!AbilityUtil::IsSystemDialogAbility(abilityInfo.bundleName, abilityInfo.name)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "PreLoadAppDataAbilities:%{public}s.", abilityInfo.bundleName.c_str());
        result = PreLoadAppDataAbilities(abilityInfo.bundleName, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                "startAbility:app data ability preloading failed, '%{public}s', %{public}d",
                abilityInfo.bundleName.c_str(), result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_PRELOAD_APP_DATA_ABILITIES_FAILED,
                "app data ability preloading failed");
            return result;
        }
    }
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(param.want, abilityRequest, callerTokenId);
    if (abilityInfo.type == AppExecFwk::AbilityType::SERVICE ||
        abilityInfo.type == AppExecFwk::AbilityType::EXTENSION) {
        SendStartAbilityOtherExtensionEvent(abilityInfo, abilityRequest.want, param.specifyTokenId);
        result = StartAbilityByConnectManager(param.want, abilityRequest, abilityInfo, validUserId, param.callerToken);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartAbilityByConnectManager failed");
        return result;
    }

    if (!IsAbilityControllerStart(param.want, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart failed:%{public}s", abilityInfo.bundleName.c_str());
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WOULD_BLOCK, "isAbilityControllerStart failed");
        return ERR_WOULD_BLOCK;
    }

    auto backFlag = StartAbilityUtils::ermsSupportBackToCallerFlag;
    UpdateCallerInfoUtil::GetInstance().UpdateBackToCallerFlag(param.callerToken, abilityRequest.want,
        param.requestCode, backFlag);

    abilityRequest.want.RemoveParam(SPECIFY_TOKEN_ID);
    if (param.specifyTokenId > 0) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "set specifyTokenId, the specifyTokenId is %{public}d", param.specifyTokenId);
        abilityRequest.want.SetParam(SPECIFY_TOKEN_ID, static_cast<int32_t>(param.specifyTokenId));
        abilityRequest.specifyTokenId = param.specifyTokenId;
    }
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);
    // sceneboard
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        abilityRequest.userId = oriValidUserId;
        abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
        // other sa or shell can not use continueSessionId and persistentId
        auto abilityRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
        if (abilityRecord == nullptr &&
            !PermissionVerification::GetInstance()->CheckSpecificSystemAbilityAccessPermission(DMS_PROCESS_NAME)) {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "startAbilityInner, remove continueSessionId and persistentId");
            abilityRequest.want.RemoveParam(DMS_CONTINUED_SESSION_ID);
            abilityRequest.want.RemoveParam(DMS_PERSISTENT_ID);
        }
        if (abilityRequest.want.GetBoolParam(PARAM_RESV_ANCO_IS_NEED_UPDATE_NAME, false) &&
                PermissionVerification::GetInstance()->VerifyFusionAccessPermission()) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "startAbilityInner, update name for fusion");
            abilityRequest.want.SetParam(Want::PARAM_RESV_CALLER_ABILITY_NAME, std::string(""));
            abilityRequest.want.SetParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME, std::string(""));
        }
        CollaboratorUtil::HandleCallerIfNeed(param.callerToken, collaborator, abilityRequest.want, callerBundleName);
        auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        result = uiAbilityManager->NotifySCBToStartUIAbility(abilityRequest);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "NotifySCBToStartUIAbility failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    auto missionListManager = GetMissionListManagerByUserId(oriValidUserId);
    if (missionListManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId=%{public}d", validUserId);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_VALUE, "missionListManager null");
        return ERR_INVALID_VALUE;
    }

    ReportAbilityStartInfoToRSS(abilityInfo);
    ReportEventToRSS(abilityInfo, param.callerToken);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start ability, name is %{public}s", abilityInfo.name.c_str());
    result = missionListManager->StartAbility(abilityRequest);
    AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "missionListManager StartAbility failed");
    return result;
}

int AbilityManagerService::PreStartFreeInstall(const Want &want, sptr<IRemoteObject> callerToken,
    uint32_t specifyTokenId, bool isStartAsCaller, Want &localWant)
{
    if (freeInstallManager_ == nullptr) {
        return ERR_NULL_FREE_INSTALL_MANAGER;
    }
    (const_cast<Want &>(want)).RemoveParam("send_to_erms_embedded");
    localWant = want;
    if (!localWant.GetDeviceId().empty()) {
        localWant.SetDeviceId("");
    }
    if (specifyTokenId > 0 && callerToken != nullptr) { // for sa specify tokenId and caller token
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(localWant, callerToken);
    } else if (!isStartAsCaller) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(localWant, callerToken);
    } else {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "start as caller, skip UpdateCallerInfo!");
    }
    return ERR_OK;
}

int AbilityManagerService::StartAbilityByConnectManager(const Want& want, const AbilityRequest& abilityRequest,
    const AppExecFwk::AbilityInfo& abilityInfo, int validUserId, sptr<IRemoteObject> callerToken)
{
    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", validUserId);
        return CONNECT_MAMAGER_NOT_FIND_BY_USERID;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "start service or extension, name is %{public}s", abilityInfo.name.c_str());
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    return connectManager->StartAbility(abilityRequest);
}

int AbilityManagerService::StartAbility(const Want &want, const AbilityStartSetting &abilityStartSetting,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(want);
#endif
    return StartAbilityDetails(want, abilityStartSetting, callerToken, userId, requestCode);
}

int AbilityManagerService::ImplicitStartAbility(const Want &want, const AbilityStartSetting &abilityStartSetting,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    return StartAbilityDetails(want, abilityStartSetting, callerToken, userId, requestCode, true);
}

int AbilityManagerService::StartAbilityDetails(const Want &want, const AbilityStartSetting &abilityStartSetting,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode, bool isImplicit)
{
    EventInfo eventInfo = BuildEventInfo(want, userId);
    if (want.GetBoolParam(AbilityConfig::DEBUG_APP, false)) {
        if (!system::GetBoolParameter(DEVELOPER_MODE_STATE, false)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer Mode");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_NOT_DEVELOPER_MODE, "not developer Mode");
            return ERR_NOT_DEVELOPER_MODE;
        }
        int32_t err = ERR_OK;
        if (userId == DEFAULT_INVAL_VALUE) {
            userId = GetValidUserId(userId);
        }
        if ((err = StartAbilityUtils::CheckAppProvisionMode(want, userId, callerToken)) != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "checkAppProvisionMode returns errcode=%{public}d", err);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, err, "checkAppProvisionMode failed");
            return err;
        }
    }
    if (!UnlockScreenManager::GetInstance().UnlockScreen()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "screen need passord unlock");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_UNLOCK_SCREEN_FAILED_IN_DEVELOPER_MODE,
            "screen need passord unlock");
        return ERR_UNLOCK_SCREEN_FAILED_IN_DEVELOPER_MODE;
    }
    AbilityUtil::RemoveWantKey(const_cast<Want &>(want));
    StartAbilityParams startParams(const_cast<Want &>(want));
    startParams.callerToken = callerToken;
    startParams.userId = userId;
    startParams.requestCode = requestCode;
    startParams.SetValidUserId(GetValidUserId(userId));

    int result = ERR_OK;
    if (StartAbilityInChain(startParams, result)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartAbilityInChain failed");
        return result;
    }

    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start ability setting.");
    if (IsCrossUserCall(userId)) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);

    if (!DlpUtils::AccessCheck(callerToken, want) ||
        VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityDetails permission verification failed");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, CHECK_PERMISSION_FAILED,
            "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    bool isTargetPlugin = false;
    if (auto pluginRet = CheckStartPlugin(want, callerToken, isTargetPlugin); pluginRet != ERR_OK) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, pluginRet, "CheckStartPlugin failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(pluginRet);
    }

    if ((want.GetFlags() & Want::FLAG_ABILITY_PREPARE_CONTINUATION) == Want::FLAG_ABILITY_PREPARE_CONTINUATION &&
        IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "The flag only support for DMS, flag:%{public}d, error:%{public}d",
            want.GetFlags(), ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG, "flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verify callerToken failed:%{public}d", ERR_INVALID_CALLER);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CALLER, "verify callerToken failed");
        return ERR_INVALID_CALLER;
    }

    int32_t oriValidUserId = GetValidUserId(userId);
    int32_t validUserId = oriValidUserId;
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_APP_CLONE_INDEX_INVALID, "GetAppIndex failed");
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    auto checkRet = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(const_cast<Want &>(want),
        validUserId, appIndex, callerToken, false);
    if (checkRet != ERR_OK) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkRet, "CheckMultiInstanceAndAppClone failed");
        return checkRet;
    }
    StartAbilityInfoWrap threadLocalInfo(want, validUserId, appIndex, callerToken);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, requestCode, validUserId,
        true, nullptr, shouldBlockFunc);
    result = interceptorExecuter_ == nullptr ? ERR_NULL_INTERCEPTOR_EXECUTER :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "doProcess error");
        return result;
    }

    if (AbilityUtil::IsStartFreeInstall(want)) {
        if (CheckIfOperateRemote(want) || freeInstallManager_ == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "can not start remote free install");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_FREE_INSTALL_REMOTE_WANT,
                "can not start remote free install");
            return ERR_INVALID_VALUE;
        }
        (const_cast<Want &>(want)).RemoveParam("send_to_erms_embedded");
        Want localWant = want;
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(localWant, callerToken);
        auto param = std::make_shared<FreeInstallParams>();
        param->isAsync = true;
        result = freeInstallManager_->StartFreeInstall(localWant, validUserId, requestCode, callerToken, param);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartFreeInstall failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied:%{public}d", ERR_CROSS_USER);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_CROSS_USER, "non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
#ifdef SUPPORT_SCREEN
    if (ImplicitStartProcessor::IsImplicitStartAction(want)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "is implicit start action");
        auto checkResult = AbilityUtil::CheckInstanceKey(want);
        if (checkResult != ERR_OK) {
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkResult, "CheckInstanceKey failed");
            return checkResult;
        }
        abilityRequest.Voluation(
            want, requestCode, callerToken, std::make_shared<AbilityStartSetting>(abilityStartSetting));
        abilityRequest.callType = AbilityCallType::START_SETTINGS_TYPE;
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        result = implicitStartProcessor_->ImplicitStartAbility(abilityRequest, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "implicit start ability error:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "implicit start error");
        }
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    if (want.GetAction().compare(ACTION_CHOOSE) == 0) {
        result = ShowPickerDialog(want, validUserId, callerToken);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "ShowPickerDialog failed");
        return result;
    }
#endif
    result = GenerateAbilityRequest(want, requestCode, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "GenerateAbilityRequest error");
        return result;
    }
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);

    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.singleton ? U0_USER_ID : validUserId;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = CheckStaticCfgPermission(abilityRequest, false, -1, false, false, isImplicit);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "checkStaticCfgPermission error");
        return ERR_STATIC_CFG_PERMISSION;
    }
    result = CheckCallAbilityPermission(abilityRequest, false);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s checkCallAbilityPermission error:%{public}d",
            __func__, result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "checkCallAbilityPermission error");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    abilityRequest.startSetting = std::make_shared<AbilityStartSetting>(abilityStartSetting);

    if (abilityInfo.type == AppExecFwk::AbilityType::DATA) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot start data ability, use 'AcquireDataAbility()':%{public}d",
            ERR_WRONG_INTERFACE_CALL);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WRONG_INTERFACE_CALL,
            "cannot start data ability");
        return ERR_WRONG_INTERFACE_CALL;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, requestCode,
        validUserId, true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), false, appIndex);
    afterCheckParam.isTargetPlugin = isTargetPlugin;
    result = afterCheckExecuter_ == nullptr ? ERR_NULL_AFTER_CHECK_EXECUTER :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "afterCheckExecuter_ null or doProcess error");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "afterCheckExecuter_ null or doProcess error");
        return result;
    }

    if (!AbilityUtil::IsSystemDialogAbility(abilityInfo.bundleName, abilityInfo.name)) {
        result = PreLoadAppDataAbilities(abilityInfo.bundleName, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility:app data ability preloading failed, '%{public}s', %{public}d",
                abilityInfo.bundleName.c_str(), result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_PRELOAD_APP_DATA_ABILITIES_FAILED,
                "app data ability preloading failed");
            return result;
        }
    }
#ifdef SUPPORT_GRAPHICS
    if (abilityInfo.type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "only support page type ability:%{public}d", ERR_WRONG_INTERFACE_CALL);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WRONG_INTERFACE_CALL, "only support page ability");
        return ERR_WRONG_INTERFACE_CALL;
    }
#endif
    if (!IsAbilityControllerStart(want, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability controller start failed:%{public}d", ERR_WOULD_BLOCK);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WOULD_BLOCK, "ability controller start failed");
        return ERR_WOULD_BLOCK;
    }
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(want, abilityRequest, callerTokenId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
        abilityRequest.userId = oriValidUserId;
        abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
        auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        result = uiAbilityManager->NotifySCBToStartUIAbility(abilityRequest);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "NotifySCBToStartUIAbility failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    auto missionListManager = GetMissionListManagerByUserId(oriValidUserId);
    if (missionListManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId=%{public}d, error:%{public}d",
            validUserId, ERR_NULL_MISSION_LIST_MANAGER);
        return ERR_NULL_MISSION_LIST_MANAGER;
    }
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    return missionListManager->StartAbility(abilityRequest);
}

int AbilityManagerService::StartAbility(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start ability with startOptions.");
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(want);
#endif
    return StartUIAbilityForOptionWrap(want, startOptions, callerToken, false, userId, requestCode);
}

int AbilityManagerService::ImplicitStartAbility(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, int32_t userId, int requestCode)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Implicit Start ability with startOptions.");
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    return StartUIAbilityForOptionWrap(want, startOptions, callerToken, false, userId, requestCode, 0, true);
}

int AbilityManagerService::StartUIAbilityForOptionWrap(const Want &want, const StartOptions &options,
    sptr<IRemoteObject> callerToken, bool isPendingWantCaller, int32_t userId,
    int requestCode, uint32_t callerTokenId, bool isImplicit,
    bool isCallByShortcut)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    int32_t ret = ERR_OK;
    if ((ret = StartOptionsUtils::CheckProcessOptions(want, options, callerToken, userId)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check process oprions failed: %{public}d", ret);
        return ret;
    }
    return StartAbilityForOptionWrap(want, options, callerToken, isPendingWantCaller, userId, requestCode, false,
        callerTokenId, isImplicit, isCallByShortcut);
}

int AbilityManagerService::StartAbilityAsCaller(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, sptr<IRemoteObject> asCallerSourceToken,
    int32_t userId, int requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start ability as caller with startOptions.");
    CHECK_CALLER_IS_SYSTEM_APP;

    AbilityUtil::RemoveWantKey(const_cast<Want &>(want));
    AAFwk::Want newWant = want;
    UpdateCallerInfoUtil::GetInstance().UpdateAsCallerSourceInfo(newWant, asCallerSourceToken, callerToken);
    return StartAbilityForOptionWrap(newWant, startOptions, callerToken, false, userId, requestCode, true);
}

int AbilityManagerService::StartAbilityForResultAsCaller(
    const Want &want, const sptr<IRemoteObject> &callerToken, int requestCode, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    CHECK_CALLER_IS_SYSTEM_APP;

    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    AAFwk::Want newWant = want;
    auto validUserId = GetValidUserId(userId);
    if (validUserId == U0_USER_ID || validUserId == U1_USER_ID) {
        validUserId =
            AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
    }
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    CHECK_POINTER_AND_RETURN(connectManager, ERR_NO_INIT);
    auto asCallerSourceToken = connectManager->GetUIExtensionSourceToken(callerToken);
    UpdateCallerInfoUtil::GetInstance().UpdateAsCallerSourceInfo(newWant, asCallerSourceToken, callerToken);
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = newWant,
        .callerToken = callerToken,
        .requestCode = requestCode,
        .userId = userId,
        .isStartAsCaller = true,
    };
    return StartAbilityWrap(startAbilityWrapParam);
}

int AbilityManagerService::StartAbilityForResultAsCaller(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, int requestCode, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    CHECK_CALLER_IS_SYSTEM_APP;

    AAFwk::Want newWant = want;
    auto validUserId = GetValidUserId(userId);
    if (validUserId == U0_USER_ID || validUserId == U1_USER_ID) {
        validUserId =
            AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
    }
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    CHECK_POINTER_AND_RETURN(connectManager, ERR_NO_INIT);
    auto asCallerSourceToken = connectManager->GetUIExtensionSourceToken(callerToken);
    UpdateCallerInfoUtil::GetInstance().UpdateAsCallerSourceInfo(newWant, asCallerSourceToken, callerToken);
    return StartAbilityForOptionWrap(newWant, startOptions, callerToken, false, userId, requestCode, true);
}

int AbilityManagerService::StartAbilityForOptionWrap(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, bool isPendingWantCaller, int32_t userId, int requestCode,
    bool isStartAsCaller, uint32_t callerTokenId, bool isImplicit, bool isCallByShortcut)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    StartAbilityParams startParams(const_cast<Want &>(want));
    startParams.callerToken = callerToken;
    startParams.userId = userId;
    startParams.requestCode = requestCode;
    startParams.isStartAsCaller = isStartAsCaller;
    startParams.startOptions = &startOptions;
    startParams.SetValidUserId(GetValidUserId(userId));

    int result = ERR_OK;
    if (StartAbilityInChain(startParams, result)) {
        return result;
    }

    return StartAbilityForOptionInner(want, startOptions, callerToken, isPendingWantCaller, userId, requestCode,
        isStartAsCaller, callerTokenId, isImplicit, isCallByShortcut);
}

int AbilityManagerService::StartAbilityForOptionInner(const Want &want, const StartOptions &startOptions,
    const sptr<IRemoteObject> &callerToken, bool isPendingWantCaller, int32_t userId, int requestCode,
    bool isStartAsCaller, uint32_t specifyTokenId, bool isImplicit, bool isCallByShortcut)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    EventInfo eventInfo = BuildEventInfo(want, userId);
    // prevent the app from dominating the screen
    if (callerToken == nullptr && !IsCallerSceneBoard() && !isCallByShortcut &&
        AbilityPermissionUtil::GetInstance().IsDominateScreen(want, isPendingWantCaller)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller invalid");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CALLER, "caller invalid");
        return ERR_INVALID_CALLER;
    }

    bool startWithAccount = want.GetBoolParam(START_ABILITY_TYPE, false);
    if (startWithAccount || IsCrossUserCall(userId)) {
        (const_cast<Want &>(want)).RemoveParam(START_ABILITY_TYPE);
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if (!DlpUtils::AccessCheck(callerToken, want) ||
        VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, CHECK_PERMISSION_FAILED,
            "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (AbilityUtil::HandleDlpApp(const_cast<Want &>(want))) {
        auto result = StartExtensionAbilityInner(want, callerToken, userId,
            AppExecFwk::ExtensionAbilityType::SERVICE, false, false, true, isStartAsCaller);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartExtensionAbilityInner failed");
        return result;
    }
    bool isTargetPlugin = false;
    if (auto pluginRet = CheckStartPlugin(want, callerToken, isTargetPlugin); pluginRet != ERR_OK) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, pluginRet, "CheckStartPlugin failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(pluginRet);
    }

    if ((want.GetFlags() & Want::FLAG_ABILITY_PREPARE_CONTINUATION) == Want::FLAG_ABILITY_PREPARE_CONTINUATION &&
        IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "The flag only support for DMS, flag:%{public}d, error:%{publicd}d",
            want.GetFlags(), ERR_INVALID_CONTINUATION_FLAG);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CONTINUATION_FLAG, "flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verify callerToken failed:%{public}d", ERR_INVALID_CALLER);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CALLER, "verify callerToken failed");
        return ERR_INVALID_CALLER;
    }

    int32_t oriValidUserId = GetValidUserId(userId);
    int32_t validUserId = oriValidUserId;
    StartAbilityUtils::SetTargetCloneIndexInSameBundle(want, callerToken);
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_APP_CLONE_INDEX_INVALID, "GetAppIndex failed");
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    auto checkRet = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(const_cast<Want &>(want),
        validUserId, appIndex, callerToken, false);
    if (checkRet != ERR_OK) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkRet, "CheckMultiInstanceAndAppClone failed");
        return checkRet;
    }
    StartAbilityInfoWrap threadLocalInfo(want, validUserId, appIndex, callerToken);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, requestCode, validUserId,
        true, nullptr, shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_NULL_INTERCEPTOR_EXECUTER :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "doProcess error");
        return result;
    }

    if (AbilityUtil::IsStartFreeInstall(want)) {
        if (CheckIfOperateRemote(want) || freeInstallManager_ == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "not allow remote free install");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_VALUE, "not allow remote free install");
            return ERR_INVALID_VALUE;
        }
        (const_cast<Want &>(want)).RemoveParam("send_to_erms_embedded");
        Want localWant = want;
        if (!isStartAsCaller) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
            UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(localWant, callerToken);
        }
        TAG_LOGD(AAFwkTag::ABILITYMGR, "is start free install");
        auto param = std::make_shared<FreeInstallParams>();
        param->isAsync = true;
        param->specifyTokenId = specifyTokenId;
        param->startOptions = std::make_shared<AAFwk::StartOptions>(startOptions);
        result = freeInstallManager_->StartFreeInstall(localWant, validUserId, requestCode, callerToken, param);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "StartFreeInstall failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied:%{public}d", ERR_CROSS_USER);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_CROSS_USER, "non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
    abilityRequest.startOptions = startOptions;
#ifdef SUPPORT_SCREEN
    if (ImplicitStartProcessor::IsImplicitStartAction(want)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "is implicit start action");
        auto checkResult = AbilityUtil::CheckInstanceKey(want);
        if (checkResult != ERR_OK) {
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, checkResult, "CheckInstanceKey failed");
            return checkResult;
        }
        abilityRequest.Voluation(want, requestCode, callerToken);
        if (PermissionVerification::GetInstance()->IsSystemAppCall()) {
            bool windowFocused = startOptions.GetWindowFocused();
            abilityRequest.want.SetParam(Want::PARAM_RESV_WINDOW_FOCUSED, windowFocused);
        } else {
            abilityRequest.want.RemoveParam(Want::PARAM_RESV_WINDOW_FOCUSED);
        }
        if (startOptions.GetDisplayID() == 0) {
            abilityRequest.want.SetParam(Want::PARAM_RESV_DISPLAY_ID,
                DisplayUtil::GetDefaultDisplayId());
        } else {
            abilityRequest.want.SetParam(Want::PARAM_RESV_DISPLAY_ID, startOptions.GetDisplayID());
        }
        WindowOptionsUtils::SetWindowPositionAndSize(abilityRequest.want, callerToken, startOptions);
        abilityRequest.callType = AbilityCallType::START_OPTIONS_TYPE;
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        if (specifyTokenId > 0 && callerToken) { // for sa specify tokenId and caller token
            UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, callerToken);
        } else if (!isStartAsCaller) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
            UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
        }
        TAG_LOGD(AAFwkTag::ABILITYMGR, "implicit start ability");
        abilityRequest.want.RemoveParam(KEY_REQUEST_ID);
        if (!startOptions.requestId_.empty()) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "set implicit requestId:%{public}s", startOptions.requestId_.c_str());
            abilityRequest.want.SetParam(KEY_REQUEST_ID, startOptions.requestId_);
        }
        result = implicitStartProcessor_->ImplicitStartAbility(abilityRequest, validUserId,
            startOptions.GetWindowMode());
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "implicit start ability error:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "implicit start error");
        }
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    if (want.GetAction().compare(ACTION_CHOOSE) == 0) {
        result = ShowPickerDialog(want, validUserId, callerToken);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "ShowPickerDialog failed");
        return result;
    }
#endif
    result = GenerateAbilityRequest(want, requestCode, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "GenerateAbilityRequest error");
        return result;
    }

    auto callerRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRequest.requestCode != DEFAULT_REQUEST_CODE &&
        ForegroundAppConnectionManager::IsForegroundAppConnection(abilityRequest.abilityInfo, callerRecord)) {
        DelayedSingleton<ForegroundAppConnectionManager>::GetInstance()->OnCallerStarted(IPCSkeleton::GetCallingPid(),
            IPCSkeleton::GetCallingUid(), want.GetBundle());
    }
    std::string currentProcessName = startOptions.GetCurrentProcessName();
    if (!currentProcessName.empty()) {
        abilityRequest.specifiedFlag = want.GetStringParam(KEY_SPECIFIED_FLAG);
        abilityRequest.want.RemoveParam(KEY_SPECIFIED_FLAG);
        abilityRequest.abilityInfo.isolationProcess = false;
    }

    abilityRequest.userId = validUserId;
    if (!HandleExecuteSAInterceptor(want, callerToken, abilityRequest, result)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "HandleExecuteSAInterceptor failed");
        return result;
    }

    if (!isStartAsCaller) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    }
    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.singleton ? U0_USER_ID : validUserId;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    if (startOptions.processOptions != nullptr &&
        abilityRequest.abilityInfo.launchMode == AppExecFwk::LaunchMode::SPECIFIED) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        auto abilityRecords = uiAbilityManager->GetAbilityRecordsByName(want.GetElement(), appIndex);
        if (!abilityRecords.empty() && abilityRecords[0] &&
            !startOptions.processOptions->isRestartKeepAlive &&
            !ProcessOptions::IsAttachToStatusBarItemMode(startOptions.processOptions->processMode) &&
            !startOptions.processOptions->isStartFromNDK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "processMode is not attach to status bar item.");
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_ABILITY_ALREADY_RUNNING,
                "processMode is not attach to status bar item");
            return ERR_ABILITY_ALREADY_RUNNING;
        }
    }

    result = CheckStaticCfgPermission(abilityRequest, isStartAsCaller,
        abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), false, false, isImplicit);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result=%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "checkStaticCfgPermission error");
        return ERR_STATIC_CFG_PERMISSION;
    }
    result = StartAbilityUtils::IsCallFromAncoShellOrBroker(callerToken) ?
        CheckBrokerCallPermission(abilityRequest, abilityInfo) :
        CheckCallAbilityPermission(abilityRequest, false, 0, isCallByShortcut);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startoption permission error:%{public}d", result);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "CheckCallAbilityPermission error");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    if (abilityInfo.type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "only support page type ability:%{public}d", ERR_ABILITY_TYPE_INVALID);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_ABILITY_TYPE_INVALID, "only support page ability");
        return ERR_ABILITY_TYPE_INVALID;
    }

    if (!AbilityUtil::IsSystemDialogAbility(abilityInfo.bundleName, abilityInfo.name)) {
        result = PreLoadAppDataAbilities(abilityInfo.bundleName, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility:app data ability preloading failed, '%{public}s', %{public}d",
                abilityInfo.bundleName.c_str(), result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_PRELOAD_APP_DATA_ABILITIES_FAILED,
                "app data ability preloading failed");
            return result;
        }
    }

    if (!IsAbilityControllerStart(want, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability controller start failed:%{public}d", ERR_WOULD_BLOCK);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WOULD_BLOCK, "controller start failed");
        return ERR_WOULD_BLOCK;
    }
#ifdef SUPPORT_SCREEN
    if (abilityInfo.isStageBasedModel && !CheckWindowMode(startOptions.GetWindowMode(), abilityInfo.windowModes)) {
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_AAFWK_INVALID_WINDOW_MODE, "CheckWindowMode fail");
        return ERR_AAFWK_INVALID_WINDOW_MODE;
    }
#endif
    if (startOptions.GetDisplayID() == 0) {
        abilityRequest.want.SetParam(Want::PARAM_RESV_DISPLAY_ID,
            DisplayUtil::GetDefaultDisplayId());
    } else {
        abilityRequest.want.SetParam(Want::PARAM_RESV_DISPLAY_ID, startOptions.GetDisplayID());
    }
    abilityRequest.want.RemoveParam(KEY_REQUEST_ID);
    if (!startOptions.requestId_.empty()) {
        abilityRequest.want.SetParam(KEY_REQUEST_ID, startOptions.requestId_);
    }
    AbilityUtil::ProcessWindowMode(abilityRequest.want, abilityInfo.applicationInfo.accessTokenId,
        startOptions.GetWindowMode());

    WindowOptionsUtils::SetWindowPositionAndSize(abilityRequest.want, callerToken, startOptions);

    if (PermissionVerification::GetInstance()->IsSystemAppCall()) {
        bool focused = abilityRequest.want.GetBoolParam(Want::PARAM_RESV_WINDOW_FOCUSED, true);
        if (focused) {
            bool windowfocused = startOptions.GetWindowFocused();
            abilityRequest.want.SetParam(Want::PARAM_RESV_WINDOW_FOCUSED, windowfocused);
        }
    } else {
        abilityRequest.want.RemoveParam(Want::PARAM_RESV_WINDOW_FOCUSED);
    }

    Want newWant = abilityRequest.want;
    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(newWant, requestCode, validUserId,
        true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), isStartAsCaller, appIndex);
    afterCheckParam.isTargetPlugin = isTargetPlugin;
    result = afterCheckExecuter_ == nullptr ? ERR_NULL_AFTER_CHECK_EXECUTER :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
    newWant.RemoveParam("queryWantFromErms");
    if (result != ERR_OK && isReplaceWantExist == false) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "doProcess failed or replaceWant absent");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "doProcess failed or replaceWant absent");
        return result;
    }
#ifdef SUPPORT_SCREEN
    if (result != ERR_OK && isReplaceWantExist) {
        result = DialogSessionManager::GetInstance().HandleErmsResult(abilityRequest, validUserId, newWant);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "HandleErmsResult failed");
        return result;
    }
    if (result == ERR_OK &&
        DialogSessionManager::GetInstance().IsCreateCloneSelectorDialog(abilityInfo.bundleName, validUserId)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "create clone selector dialog");
        result = CreateCloneSelectorDialog(abilityRequest, validUserId);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "CreateCloneSelectorDialog failed");
        return result;
    }
#endif // SUPPORT_GRAPHICS
    auto backFlag = StartAbilityUtils::ermsSupportBackToCallerFlag;
    UpdateCallerInfoUtil::GetInstance().UpdateBackToCallerFlag(callerToken, abilityRequest.want, requestCode, backFlag);

    abilityRequest.want.RemoveParam(SPECIFY_TOKEN_ID);
    if (specifyTokenId > 0) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Set specifyTokenId, the specifyTokenId is %{public}d.", specifyTokenId);
        abilityRequest.want.SetParam(SPECIFY_TOKEN_ID, static_cast<int32_t>(specifyTokenId));
        abilityRequest.specifyTokenId = specifyTokenId;
    }
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(want, abilityRequest, callerTokenId);
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        abilityRequest.userId = oriValidUserId;
        abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
        abilityRequest.processOptions = startOptions.processOptions;
        if (IPCSkeleton::GetCallingTokenID() == abilityRequest.appInfo.accessTokenId ||
            AbilityPermissionUtil::GetInstance().IsStartSelfUIAbility()) {
            abilityRequest.startWindowOption = startOptions.startWindowOption;
        }
        abilityRequest.supportWindowModes = startOptions.supportWindowModes_;
        auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
        std::string callerBundleName = abilityRecord ? abilityRecord->GetAbilityInfo().bundleName : "";
        if (abilityRequest.want.GetElement().GetBundleName() == callerBundleName) {
            abilityRequest.hideStartWindow = startOptions.GetHideStartWindow();
        }
        auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_NULL_UI_ABILITY_MANAGER);
        result = uiAbilityManager->NotifySCBToStartUIAbility(abilityRequest);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "NotifySCBToStartUIAbility failed");
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
    auto missionListManager = GetMissionListManagerByUserId(oriValidUserId);
    if (missionListManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId=%{public}d, errror:%{public}d",
            oriValidUserId, ERR_NULL_MISSION_LIST_MANAGER);
        return ERR_NULL_MISSION_LIST_MANAGER;
    }
    if (startOptions.GetDisplayID() == -1) {
        abilityRequest.want.SetParam(Want::PARAM_RESV_DISPLAY_ID,
            DisplayUtil::GetDefaultDisplayId());
    }
    return missionListManager->StartAbility(abilityRequest);
}

int32_t AbilityManagerService::CheckWantForSplitMode(const AAFwk::Want &secondaryWant, sptr<IRemoteObject> callerToken,
    int32_t validUserId, int32_t appIndex)
{
    if (AbilityRuntime::StartupUtil::IsStartPlugin(secondaryWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode not support StartPlugin");
        return START_UI_ABILITIES_NOT_SUPPORT_START_PLUGIN;
    }
    AbilityUtil::RemoveWindowModeKey(const_cast<Want &>(secondaryWant));
    if (secondaryWant.GetBoolParam(Want::CREATE_APP_INSTANCE_KEY, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode not support CREATE_APP_INSTANCE_KEY");
        return START_UI_ABILITIES_NOT_SUPPORT_CREATE_APP_INSTANCE_KEY;
    }
    int32_t ret = StartUIAbilitiesCheckDlp(secondaryWant, callerToken, validUserId);
    if (ret != ERR_OK) {
        return ret;
    }
    ret = StartAbilityUtils::StartUIAbilitiesProcessAppIndex(const_cast<Want &>(secondaryWant), callerToken, appIndex);
    if (ret != ERR_OK) {
        return ret;
    }
    auto checkRet = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(const_cast<Want &>(secondaryWant),
        validUserId, appIndex, callerToken, false);
    if (checkRet != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "CheckMultiInstanceAndAppClone failed: %{public}d", checkRet);
        return checkRet;
    }
    StartAbilityInfoWrap threadLocalInfo(secondaryWant, validUserId, appIndex, callerToken);
    if (CheckIfOperateRemote(secondaryWant)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode not support StartRemoteAbility");
        return START_UI_ABILITIES_NOT_SUPPORT_OPERATE_REMOTE;
    }
    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }
    auto element = secondaryWant.GetElement();
    if (element.GetBundleName().empty() || element.GetAbilityName().empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode not support implicit start");
        return START_UI_ABILITIES_NOT_SUPPORT_IMPLICIT_START;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::StartUIAbilitiesInSplitWindowModeHandleWant(const AAFwk::Want &secondaryWant,
    sptr<IRemoteObject> callerToken, AbilityRequest &abilityRequest)
{
    int32_t userId = DEFAULT_INVAL_VALUE;
    int32_t validUserId = GetValidUserId(userId);
    uint32_t specifyTokenId = 0;
    int32_t requestCode = DEFAULT_INVAL_VALUE;
    int32_t appIndex = 0;
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(secondaryWant));
    auto result = CheckWantForSplitMode(secondaryWant, callerToken, validUserId, appIndex);
    if (result != ERR_OK) {
        return result;
    }
    result = GenerateAbilityForSplitMode(secondaryWant, abilityRequest, callerToken, requestCode, specifyTokenId,
        appIndex, validUserId);
    if (result != ERR_OK) {
        return result;
    }
    Want newWant = abilityRequest.want;
    bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
    newWant.RemoveParam("queryWantFromErms");
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    auto abilityInfo = abilityRequest.abilityInfo;
    RemoveUnauthorizedLaunchReasonMessage(secondaryWant, abilityRequest, callerTokenId);
    if (!IsAbilityControllerStart(secondaryWant, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilitiesInSplitWindowMode isAbilityControllerStart failed:%{public}s", abilityInfo.bundleName.c_str());
        return ERR_WOULD_BLOCK;
    }
    abilityRequest.want.RemoveParam(SPECIFY_TOKEN_ID);
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);
    return ERR_OK;
}

int32_t AbilityManagerService::GenerateAbilityForSplitMode(const AAFwk::Want &secondaryWant,
        AbilityRequest &abilityRequest, sptr<IRemoteObject> callerToken, int32_t requestCode, int32_t specifyTokenId,
        int32_t appIndex, int32_t validUserId)
{
    auto result = GenerateAbilityRequest(secondaryWant, requestCode, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode generate ability request local error");
        return result;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    std::string callerBundleName = abilityRecord ? abilityRecord->GetAbilityInfo().bundleName : "";
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, callerToken);
    auto abilityInfo = abilityRequest.abilityInfo;
    if (abilityInfo.type != AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode ability type no UIAbility");
        return RESOLVE_ABILITY_ERR;
    }
    result = CheckStaticCfgPermission(abilityRequest, false,
        abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), false, false, false);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilitiesInSplitWindowMode checkStaticCfgPermission error, result:%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }
    result = CheckCallPermission(secondaryWant, abilityInfo, abilityRequest, false,
        false, specifyTokenId, callerBundleName, false);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilitiesInSplitWindowMode checkCallPermission error, result:%{public}d", result);
        return result;
    }
    result = StartUIAbilitiesInterceptorCheck(secondaryWant, abilityRequest, callerToken, appIndex, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "InterceptorCheck error, result:%{public}d", result);
        return result;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::StartUIAbilitiesInSplitWindowMode(int32_t primaryWindowId,
    const AAFwk::Want &secondaryWant, sptr<IRemoteObject> callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!system::GetBoolParameter(SUPPORT_LINKAGE_SCENE, false) ||
        !Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "StartUIAbilitiesInSplitWindowMode capability not support");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }
    if (!AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode permission verification failed");
        return ERR_NOT_SYSTEM_APP;
    }
    if (callerToken == nullptr || !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilitiesInSplitWindowMode verificationAllToken failed");
        return ERR_INVALID_CALLER;
    }
    AbilityRequest abilityRequest;
    int32_t oriValidUserId = GetValidUserId(DEFAULT_INVAL_VALUE);
    auto result = StartUIAbilitiesInSplitWindowModeHandleWant(secondaryWant, callerToken, abilityRequest);
    if (result != ERR_OK) {
        return result;
    }
    abilityRequest.userId = oriValidUserId;
    abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
    auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    abilityRequest.primaryWindowId = primaryWindowId;
    abilityRequest.isStartInSplitMode = true;
    return uiAbilityManager->NotifySCBToStartUIAbility(abilityRequest);
}

ErrCode AbilityManagerService::StartUIAbilities(const std::vector<AAFwk::Want> &wantList,
    const std::string &requestKey, sptr<IRemoteObject> callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_DEFAULT(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call StartUIAbilities");
    std::vector<AbilityRequest> abilityRequestList;
    int32_t oriValidUserId = GetValidUserId(DEFAULT_INVAL_VALUE);

    if (!AppUtils::GetInstance().IsSupportStartAbilities() ||
        !Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities is not supported");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }

    if (wantList.size() < INDEX_ONE || wantList.size() > INDEX_FOUR) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities wantList size not support");
        return START_UI_ABILITIES_WANT_LIST_SIZE_ERROR;
    }

    if (callerToken == nullptr || !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities %{public}s verificationAllToken failed", __func__);
        return ERR_INVALID_CALLER;
    }

    for (const Want &want : wantList) {
        int32_t ret = StartUIAbilitiesHandleWant(want, callerToken, abilityRequestList);
        if (ret != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities want process block");
            return ret;
        }
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "StartUIAbilities ready to NotifySCBToStartUIAbilities");
    for (AbilityRequest &abilityRequest : abilityRequestList) {
        auto abilityInfo = abilityRequest.abilityInfo;
        ReportEventToRSS(abilityInfo, abilityRequest.callerToken);
        abilityRequest.userId = oriValidUserId;
        abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
    }
    auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->NotifySCBToStartUIAbilities(abilityRequestList, requestKey);
}

int32_t AbilityManagerService::StartUIAbilitiesHandleWant(const Want &want, sptr<IRemoteObject> callerToken,
    std::vector<AbilityRequest> &abilityRequestList)
{
    int32_t userId = DEFAULT_INVAL_VALUE;
    int32_t validUserId = GetValidUserId(userId);
    uint32_t specifyTokenId = 0;
    int32_t requestCode = DEFAULT_INVAL_VALUE;

    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));

    if (!want.HasParameter(AppExecFwk::INSIGHT_INTENT_EXECUTE_OPENLINK_FLAG)) {
        InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    }

#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(want);
#endif

    if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities not support StartPlugin");
        return START_UI_ABILITIES_NOT_SUPPORT_START_PLUGIN;
    }

    AbilityUtil::RemoveWindowModeKey(const_cast<Want &>(want));

    if (want.GetBoolParam(Want::CREATE_APP_INSTANCE_KEY, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities not support CREATE_APP_INSTANCE_KEY");
        return START_UI_ABILITIES_NOT_SUPPORT_CREATE_APP_INSTANCE_KEY;
    }

    int32_t ret = StartUIAbilitiesCheckDlp(want, callerToken, validUserId);
    if (ret != ERR_OK) {
        return ret;
    }

    int32_t appIndex = 0;
    ret = StartAbilityUtils::StartUIAbilitiesProcessAppIndex(const_cast<Want &>(want), callerToken, appIndex);
    if (ret != ERR_OK) {
        return ret;
    }
    ret = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(
        const_cast<Want &>(want), validUserId, appIndex, callerToken, false);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities CheckMultiInstanceAndAppClone failed");
        return ret;
    }

    StartAbilityInfoWrap threadLocalInfo(want, validUserId, appIndex, callerToken);

    if (CheckIfOperateRemote(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities not support StartRemoteAbility");
        return START_UI_ABILITIES_NOT_SUPPORT_OPERATE_REMOTE;
    }

    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities multi-user non-concurrent unsatisfied");
        return START_UI_ABILITIES_NOT_SUPPORT_CROSS_USER;
    }
#ifdef SUPPORT_SCREEN
    if (ImplicitStartProcessor::IsImplicitStartAction(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities not support implicit start");
        return START_UI_ABILITIES_NOT_SUPPORT_IMPLICIT_START;
    }
#endif
    AbilityRequest abilityRequest;
    auto result = GenerateAbilityRequest(want, requestCode, abilityRequest, callerToken, validUserId);
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    std::string callerBundleName = abilityRecord ? abilityRecord->GetAbilityInfo().bundleName : "";
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        return result;
    }

    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);

    auto abilityInfo = abilityRequest.abilityInfo;
    if (abilityInfo.type != AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities only support UIAbility");
        return START_UI_ABILITIES_ONLY_SUPPORT_UI_ABILITY;
    }

    result = CheckStaticCfgPermission(abilityRequest, false,
        abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), false, false, false);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilities checkStaticCfgPermission error, result:%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }
    result = CheckCallPermission(want, abilityInfo, abilityRequest, false,
        false, specifyTokenId, callerBundleName, false);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilities checkCallPermission error, result:%{public}d", result);
        return result;
    }

    result = StartUIAbilitiesInterceptorCheck(want, abilityRequest, callerToken, appIndex, validUserId);
    if (result != ERR_OK) {
        return result;
    }

    Want newWant = abilityRequest.want;
    bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
    newWant.RemoveParam("queryWantFromErms");

    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(want, abilityRequest, callerTokenId);

    if (!IsAbilityControllerStart(want, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilities isAbilityControllerStart failed:%{public}s", abilityInfo.bundleName.c_str());
        return ERR_WOULD_BLOCK;
    }
    abilityRequest.want.RemoveParam(SPECIFY_TOKEN_ID);
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);
    abilityRequestList.emplace_back(abilityRequest);
    return ERR_OK;
}

int32_t AbilityManagerService::StartUIAbilitiesCheckDlp(const Want &want, sptr<IRemoteObject> callerToken,
    int32_t userId)
{
    if (AbilityUtil::HandleDlpApp(const_cast<Want &>(want))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities not support Dlp");
        return START_UI_ABILITIES_NOT_SUPPORT_DLP;
    }
    if (!DlpUtils::AccessCheck(callerToken, want) ||
        VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "StartUIAbilities Dlp %{public}s: permission verification failed", __func__);
        return CHECK_PERMISSION_FAILED;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::StartUIAbilitiesInterceptorCheck(const Want &want, AbilityRequest &abilityRequest,
    sptr<IRemoteObject> callerToken, int32_t appIndex, int32_t userId)
{
    int32_t requestCode = DEFAULT_INVAL_VALUE;
    Want newWant = abilityRequest.want;
    auto abilityInfo = abilityRequest.abilityInfo;
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, requestCode, userId,
        true, nullptr, shouldBlockFunc);
    int32_t result = interceptorExecuter_ == nullptr ? ERR_NULL_INTERCEPTOR_EXECUTER :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result == ERR_CROWDTEST_EXPIRED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities ERR_CROWDTEST_EXPIRED");
        return result;
    }
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities interceptorExecuter_ null or DoProcess error");
        return START_UI_ABILITIES_INTERCEPTOR_CHECK_FAILED;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(newWant, requestCode, userId,
        true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), false, appIndex);
    result = afterCheckExecuter_ == nullptr ? ERR_NULL_AFTER_CHECK_EXECUTER :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result == ERR_CROWDTEST_EXPIRED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities ERR_CROWDTEST_EXPIRED");
        return result;
    }
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartUIAbilities afterCheckExecuter_ null or DoProcess error");
        return START_UI_ABILITIES_INTERCEPTOR_CHECK_FAILED;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::RequestDialogService(const Want &want, const sptr<IRemoteObject> &callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto flags = want.GetFlags();
    if ((flags & Want::FLAG_ABILITY_CONTINUATION) == Want::FLAG_ABILITY_CONTINUATION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestDialogService with continuation flags not allowed");
        return ERR_INVALID_CONTINUATION_FLAG;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "request dialog service, target:%{public}s/%{public}s",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str());
    return RequestDialogServiceInner(want, callerToken, -1, -1);
}

int32_t AbilityManagerService::ReportDrawnCompleted(const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken null");
        return INNER_ERR;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return INNER_ERR;
    }
    auto abilityInfo = abilityRecord->GetAbilityInfo();

    EventInfo eventInfo;
    eventInfo.userId = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    eventInfo.pid = IPCSkeleton::GetCallingPid();
    eventInfo.bundleName = abilityInfo.bundleName;
    eventInfo.moduleName = abilityInfo.moduleName;
    eventInfo.abilityName = abilityInfo.name;
    EventReport::SendAppEvent(EventName::DRAWN_COMPLETED, HISYSEVENT_BEHAVIOR, eventInfo);
    return ERR_OK;
}

int32_t AbilityManagerService::RequestDialogServiceInner(const Want &want, const sptr<IRemoteObject> &callerToken,
    int requestCode, int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (callerToken == nullptr || !VerificationAllToken(callerToken)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "caller invalid");
        return ERR_INVALID_CALLER;
    }

    if (!DlpUtils::AccessCheck(callerToken, want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "RequestDialogServiceInner permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (AbilityUtil::HandleDlpApp(const_cast<Want &>(want))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot handle dlp by requestDialogService");
        return ERR_WRONG_INTERFACE_CALL;
    }

    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    int32_t validUserId = GetValidUserId(userId);
    StartAbilityInfoWrap threadLocalInfo;
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, requestCode, validUserId,
        true, nullptr, shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or DoProcess error");
        return result;
    }

    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }
    AbilityRequest abilityRequest;
    result = GenerateExtensionAbilityRequest(want, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error when requestDialogService");
        return result;
    }
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);

    auto abilityInfo = abilityRequest.abilityInfo;
    threadLocalInfo.SetStartAbilityInfo(abilityInfo);
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = CheckStaticCfgPermission(abilityRequest, false, -1);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result:%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }

    auto type = abilityInfo.type;
    if (type == AppExecFwk::AbilityType::EXTENSION &&
        abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Check call ability permission, name is %{public}s.", abilityInfo.name.c_str());
        result = CheckCallServicePermission(abilityRequest);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "check permission failed");
            return result;
        }
    } else {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "requestDialogService no support other component");
        return ERR_WRONG_INTERFACE_CALL;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, requestCode,
        validUserId, true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo));
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "afterCheckExecuter_ null or DoProcess error");
        return result;
    }

    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", validUserId);
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "request dialog service, start service extension,name is %{public}s.", abilityInfo.name.c_str());
    return connectManager->StartAbility(abilityRequest);
}

int32_t AbilityManagerService::OpenAtomicService(AAFwk::Want& want, const StartOptions &options,
    sptr<IRemoteObject> callerToken, int32_t requestCode, int32_t userId)
{
    want.SetParam(AAFwk::SCREEN_MODE_KEY, AAFwk::ScreenMode::JUMP_SCREEN_MODE);
    return StartUIAbilityForOptionWrap(want, options, callerToken, false, userId, requestCode);
}

int AbilityManagerService::SetWantForSessionInfo(sptr<SessionInfo> sessionInfo)
{
    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);
    if (!(sessionInfo->want).GetElement().GetAbilityName().empty() &&
        !(sessionInfo->want).GetElement().GetModuleName().empty()) {
        return ERR_OK;
    }
    auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bundleMgrHelper, ERR_INVALID_VALUE);
    Want launchWant;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName:%{public}s, userId:%{public}d", sessionInfo->want.GetBundle().c_str(),
        GetValidUserId(sessionInfo->userId));
    auto errCode = IN_PROCESS_CALL(bundleMgrHelper->GetLaunchWantForBundle(
        (sessionInfo->want).GetBundle(), launchWant, GetValidUserId(sessionInfo->userId)));
    if (errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getLaunchWantForBundle returns %{public}d", errCode);
        return errCode;
    }
    (sessionInfo->want).SetElement(launchWant.GetElement());
    return ERR_OK;
}

int AbilityManagerService::StartUIAbilityBySCB(sptr<SessionInfo> sessionInfo, AbilityRuntime::StartParamsBySCB &params,
    bool &isColdStart)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call, sceneFlag:%{public}u, restart: %{public}d",
        params.sceneFlag, params.isRestart);
    if (sessionInfo == nullptr || sessionInfo->sessionToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return ERR_INVALID_VALUE;
    }
    sessionInfo->want.SetParam(AbilityRuntime::GlobalConstant::PAGE_CONFIG, params.pageConfig);
    EventInfo eventInfo = BuildEventInfo(sessionInfo->want, -1);
#ifdef MEMMGR_OVERRIDE_ENABLE
    WantParams wantParams = (sessionInfo->want).GetParams();
    std::string bundleName = (sessionInfo->want).GetElement().GetBundleName();
    int windowMode = wantParams.GetIntParam(EXPECT_WINDOW_MODE, 0);
    if (AppUtils::GetInstance().IsRequireBigMemoryProcess(bundleName) &&
        wantParams.HasParam(EXPECT_WINDOW_MODE) &&
        (windowMode == AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_FLOATING ||
        windowMode == AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_PRIMARY ||
        windowMode == AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_SECONDARY)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "App start ability from with no fullscreen.");
        Memory::MemMgrProcessStateInfo info;
        info.noFullScreenStart = 1;
        int32_t result = Memory::MemMgrClient::GetInstance().NotifyProcessStateChangedAsync(info);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "NotifyProcessStateChangedAsync error. result: %{public}d", result);
        }
    }
#endif
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_WRONG_INTERFACE_CALL,
            "not sceneboard", true);
        return ERR_WRONG_INTERFACE_CALL;
    }

    if (params.isRestart && !AppUtils::GetInstance().IsSupportRestartAppWithWindow()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not supported");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }

    if (!(sessionInfo->want).HasParameter(KEY_SESSION_ID)) {
        return StartUIAbilityBySCBDefault(sessionInfo, params, isColdStart);
    }

    std::string sessionId = (sessionInfo->want).GetStringParam(KEY_SESSION_ID);
    if (sessionId.empty()) {
        return StartUIAbilityBySCBDefault(sessionInfo, params, isColdStart);
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "sessionId=%{public}s", sessionId.c_str());

    if (freeInstallManager_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "freeInstallManager_ null");
        return ERR_INVALID_VALUE;
    }
    FreeInstallInfo taskInfo;
    if (!freeInstallManager_->GetFreeInstallTaskInfo(sessionId, taskInfo)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "failed find free install task");
        auto err = SetWantForSessionInfo(sessionInfo);
        if (err != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "SetWantForSessionInfo failed");
            return err;
        }
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        if (uiAbilityManager->GetUIAbilityRecordBySessionInfo(sessionInfo) == nullptr) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "first time open");
            return StartUIAbilityByPreInstallInner(sessionInfo, 0, params, isColdStart);
        }
        return StartUIAbilityBySCBDefault(sessionInfo, params, isColdStart);
    }

    if (taskInfo.isFreeInstallFinished) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install task finished");
        if (!taskInfo.isInstalled) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "free install task failed,resultCode=%{public}d",
                taskInfo.resultCode);
            return taskInfo.resultCode;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install succeeds");
        return StartUIAbilityByPreInstallInner(sessionInfo, taskInfo.specifyTokenId, params, isColdStart);
    }

    {
        std::lock_guard<ffrt::mutex> guard(preStartSessionMapLock_);
        preStartSessionMap_[sessionId] = sessionInfo;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "free install task in progress");
    const Want& want = sessionInfo->want;
    freeInstallManager_->SetSCBCallStatus(want.GetElement().GetBundleName(), want.GetElement().GetAbilityName(),
        want.GetStringParam(Want::PARAM_RESV_START_TIME), true);
    return ERR_OK;
}

int AbilityManagerService::StartUIAbilityBySCBDefault(sptr<SessionInfo> sessionInfo,
    AbilityRuntime::StartParamsBySCB &params, bool &isColdStart)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call.");

    auto currentUserId = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_NULL_SESSION_INFO);
    if (sessionInfo->userId == DEFAULT_INVAL_VALUE) {
        sessionInfo->userId = currentUserId;
    }

    (sessionInfo->want).RemoveParam(AAFwk::SCREEN_MODE_KEY);
    EventInfo eventInfo = BuildEventInfo(sessionInfo->want, currentUserId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);

    auto requestCode = sessionInfo->requestCode;
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(sessionInfo->want, sessionInfo->callerToken, appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get app index error");
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    StartAbilityInfoWrap threadLocalInfo(sessionInfo->want, currentUserId, appIndex, sessionInfo->callerToken);
    AbilityRequest abilityRequest;
    abilityRequest.processOptions = sessionInfo->processOptions;
    auto result = GenerateAbilityRequest(sessionInfo->want, requestCode, abilityRequest,
        sessionInfo->callerToken, currentUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result,
            "generate ability request local error", true);
        return result;
    }
    if (sessionInfo->want.GetBoolParam(ServerConstant::IS_CALL_BY_SCB, true)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "interceptorExecuter_ called");
        (sessionInfo->want).RemoveParam(IS_CALLING_FROM_DMS);
        auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
        AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(sessionInfo->want, requestCode,
            currentUserId, true, nullptr, shouldBlockFunc);
        auto result = interceptorExecuter_ == nullptr ? ERR_NULL_INTERCEPTOR_EXECUTER :
        interceptorExecuter_->DoProcess(interceptorParam);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or DoProcess error:%{public}d", result);
            AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result, "DoProcess error");
            return result;
        }
        abilityRequest.userId = currentUserId;
        if (!HandleExecuteSAInterceptor(sessionInfo->want, sessionInfo->callerToken, abilityRequest, result)) {
            return result;
        }
    }

    if (sessionInfo->want.GetBoolParam(ServerConstant::IS_CALL_BY_SCB, true)) {
        if (sessionInfo->startSetting != nullptr) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "Start by scb, last not.");
            sessionInfo->startSetting->AddProperty(AbilityStartSetting::IS_START_BY_SCB_KEY, "true");
        }

        if (abilityRequest.startSetting != nullptr) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "Start by scb.");
            abilityRequest.startSetting->AddProperty(AbilityStartSetting::IS_START_BY_SCB_KEY, "true");
        }
    }

    abilityRequest.collaboratorType = sessionInfo->collaboratorType;
    uint32_t specifyTokenId = static_cast<uint32_t>(sessionInfo->want.GetIntParam(SPECIFY_TOKEN_ID, 0));
    (sessionInfo->want).RemoveParam(SPECIFY_TOKEN_ID);
    abilityRequest.specifyTokenId = specifyTokenId;

    auto abilityInfo = abilityRequest.abilityInfo;
    if (!AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall() &&
        abilityInfo.type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "only support page type ability");
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_VALUE,
            "only support page type ability", true);
        return ERR_INVALID_VALUE;
    }

    if (sessionInfo->want.GetBoolParam(ServerConstant::IS_CALL_BY_SCB, true)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "afterCheckExecuter_ called");
        if (sessionInfo->want.GetBoolParam("ohos.ability.params.isSkipErmsFromSCB", false)) {
            abilityRequest.want.RemoveParam("ohos.ability.params.isSkipErmsFromSCB");
            StartAbilityUtils::skipErms = true;
        }
        Want newWant = abilityRequest.want;
        auto callerTokenId = IPCSkeleton::GetCallingTokenID();
        RemoveUnauthorizedLaunchReasonMessage(sessionInfo->want, abilityRequest, callerTokenId);
        AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(newWant, requestCode, currentUserId, true,
            sessionInfo->callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), false, appIndex);
        result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
            afterCheckExecuter_->DoProcess(afterCheckParam);
        bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
        newWant.RemoveParam("queryWantFromErms");
        if (result != ERR_OK) {
            if (isReplaceWantExist == false) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "doProcess failed or replaceWant absent");
                AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, result,
                    "doProcess failed or replaceWant absent", true);
                return result;
            }
            return DialogSessionManager::GetInstance().HandleErmsResultBySCB(abilityRequest, newWant);
        }
    }

    return StartUIAbilityBySCBDefaultCommon(abilityRequest, sessionInfo, params, isColdStart);
}

int32_t AbilityManagerService::StartUIAbilityBySCBDefaultCommon(AbilityRequest &abilityRequest,
    sptr<SessionInfo> sessionInfo, AbilityRuntime::StartParamsBySCB &params, bool &isColdStart)
{
    auto abilityInfo = abilityRequest.abilityInfo;
    if (!AbilityUtil::IsSystemDialogAbility(abilityInfo.bundleName, abilityInfo.name)) {
        int32_t result = PreLoadAppDataAbilities(abilityInfo.bundleName, IPCSkeleton::GetCallingUid() / BASE_USER_RANGE);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility: app data ability preloading failed, '%{public}s', %{public}d",
                abilityInfo.bundleName.c_str(), result);
            return result;
        }
    }

    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);
    ReportAbilityStartInfoToRSS(abilityInfo);
    ReportAbilityAssociatedStartInfoToRSS(abilityInfo, RES_TYPE_SCB_START_ABILITY, sessionInfo->callerToken);
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->StartUIAbility(abilityRequest, sessionInfo, params, isColdStart);
}

int32_t AbilityManagerService::NotifySCBToRecoveryAfterInterception(const AbilityRequest &abilityRequest)
{
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->NotifySCBToRecoveryAfterInterception(abilityRequest);
}

bool AbilityManagerService::CheckCallingTokenId(const std::string &bundleName, int32_t userId, int32_t appIndex)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto bundleMgrHelper = DelayedSingleton<AppExecFwk::BundleMgrHelper>::GetInstance();
    CHECK_POINTER_AND_RETURN(bundleMgrHelper, false);
    auto validUserId = GetValidUserId(userId);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName: %{public}s, userId: %{public}d, appIndex: %{public}d",
        bundleName.c_str(), validUserId, appIndex);
    AppExecFwk::ApplicationInfo appInfo;
    IN_PROCESS_CALL_WITHOUT_RET(bundleMgrHelper->GetApplicationInfoWithAppIndex(bundleName,
        appIndex, validUserId, appInfo));
    auto accessTokenId = IPCSkeleton::GetCallingTokenID();
    if (accessTokenId != appInfo.accessTokenId) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return false;
    }
    return true;
}

bool AbilityManagerService::IsCallerSceneBoard()
{
    int32_t userId = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    auto connectManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(connectManager, false);
    auto sceneBoardTokenId = connectManager->GetSceneBoardTokenId();
    return sceneBoardTokenId != 0 && IPCSkeleton::GetCallingTokenID() == sceneBoardTokenId;
}

bool AbilityManagerService::IsBackgroundTaskUid(const int uid)
{
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
    std::lock_guard<ffrt::mutex> lock(bgtaskObserverMutex_);
    if (bgtaskObserver_) {
        return bgtaskObserver_->IsBackgroundTaskUid(uid);
    }
    return false;
#else
    return false;
#endif
}

bool AbilityManagerService::IsDmsAlive() const
{
    return g_isDmsAlive.load();
}

void AbilityManagerService::AppUpgradeCompleted(int32_t uid, int32_t installType)
{
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sa call");
        return;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER(bms);
    auto userId = uid / BASE_USER_RANGE;
    if (userId != U0_USER_ID && userId != U1_USER_ID &&
        !AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "not current user");
        return;
    }

    AppExecFwk::BundleInfo bundleInfo;
    std::string bundleName;
    int32_t appIndex;
    if (IN_PROCESS_CALL(bms->GetNameAndIndexForUid(uid, bundleName, appIndex)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get appIndex for %{public}s", bundleName.c_str());
        return;
    }
    auto flags = static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_APPLICATION)
        | static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_HAP_MODULE)
        | static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_ABILITY)
        | static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_EXTENSION_ABILITY);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName: %{public}s, userId: %{public}d, appIndex: %{public}d",
        bundleName.c_str(), userId, appIndex);
    if (IN_PROCESS_CALL(bms->GetCloneBundleInfo(bundleName, flags, appIndex, bundleInfo, userId)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get bundle info for %{public}s", bundleName.c_str());
        return;
    }

    KeepAliveType type = KeepAliveType::UNSPECIFIED;
    if (!KeepAliveUtils::IsKeepAliveBundle(bundleInfo, userId, type)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "not keep-alive application");
        return;
    }

    std::vector<AppExecFwk::BundleInfo> bundleInfos = { bundleInfo };
    if (type == KeepAliveType::THIRD_PARTY && installType == INSTALL_TYPE_UPGRADE) {
        KeepAliveProcessManager::GetInstance().StartKeepAliveAfterAppUpgrade(bundleInfos, uid);
        if (IN_PROCESS_CALL(KeepAliveProcessManager::GetInstance().CheckNeedRestartAfterUpgrade(uid))) {
            IN_PROCESS_CALL_WITHOUT_RET(
                KeepAliveProcessManager::GetInstance().StartKeepAliveAppServiceExtension(bundleInfos));
        }
    } else if (type == KeepAliveType::RESIDENT_PROCESS) {
        auto residentProcessManager = DelayedSingleton<ResidentProcessManager>::GetInstance();
        CHECK_POINTER(residentProcessManager);
        residentProcessManager->StartResidentProcessWithMainElement(bundleInfos, userId);
        if (!bundleInfos.empty()) {
            residentProcessManager->StartResidentProcess(bundleInfos);
        }
    }
}

int32_t AbilityManagerService::RecordAppExitReason(const ExitReason &exitReason)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "recordAppExitReason reason:%{public}d, exitMsg:%{public}s", exitReason.reason,
        exitReason.exitMsg.c_str());

    CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
    return appExitReasonHelper_->RecordAppExitReason(exitReason);
}

int32_t AbilityManagerService::RecordProcessExitReason(const int32_t pid, const ExitReason &exitReason)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto callerPid = IPCSkeleton::GetCallingPid();
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "recordProcessExitReason pid:%{public}d, reason:%{public}d, exitMsg:%{public}s, callerPid:%{public}d",
        pid, exitReason.reason, exitReason.exitMsg.c_str(), callerPid);

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() &&
        !AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sa call");
        return ERR_PERMISSION_DENIED;
    }

    CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
    return appExitReasonHelper_->RecordProcessExitReason(pid, exitReason, false);
}

int32_t AbilityManagerService::RecordProcessExitReason(int32_t pid, int32_t uid, const ExitReason &exitReason)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (IPCSkeleton::GetCallingUid() != HIVIEW_UID && IPCSkeleton::GetCallingUid() != MEMMGR_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not expected caller");
        return ERR_NO_PERMISSION_CALLER;
    }

    auto callerPid = IPCSkeleton::GetCallingPid();
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "[EXIT_REASON_TAG] pid:%{public}d, reason:%{public}d, exitMsg:%{public}s, callerPid:%{public}d",
        pid, exitReason.reason, exitReason.exitMsg.c_str(), callerPid);

    CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_APP_EXIT_REASON_HELPER);
    return appExitReasonHelper_->RecordProcessExitReason(pid, uid, exitReason);
}

int32_t AbilityManagerService::ForceExitApp(const int32_t pid, const ExitReason &exitReason)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "forceExitApp pid:%{public}d, reason:%{public}d, exitMsg:%{public}s",
        pid, exitReason.reason, exitReason.exitMsg.c_str());

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() &&
        !AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sa or shell call");
        return ERR_PERMISSION_DENIED;
    }

    AppExecFwk::ApplicationInfo application;
    bool debug = false;
    auto ret = IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->GetApplicationInfoByProcessID(pid,
        application, debug));
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getApplicationInfoByProcessID failed");
        return ret;
    }

    std::string bundleName = application.bundleName;
    int32_t uid = application.uid;
    int32_t appIndex = application.appIndex;

    CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
    appExitReasonHelper_->RecordAppExitReason(bundleName, uid, appIndex, exitReason);

    return DelayedSingleton<AppScheduler>::GetInstance()->KillApplication(bundleName, false, appIndex);
}

int32_t AbilityManagerService::GetConfiguration(AppExecFwk::Configuration& config)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "AppMgrUtil::GetAppMgr failed");
        return -1;
    }

    return appMgr->GetConfiguration(config);
}

int32_t AbilityManagerService::GetConfiguration(AppExecFwk::Configuration& config, int32_t userId)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "AppMgrUtil::GetAppMgr failed");
        return -1;
    }

    return appMgr->GetConfiguration(config, userId);
}

int AbilityManagerService::CheckOptExtensionAbility(const Want &want, AbilityRequest &abilityRequest,
    int32_t validUserId, AppExecFwk::ExtensionAbilityType extensionType, bool isImplicit, bool isStartAsCaller)
{
    auto abilityInfo = abilityRequest.abilityInfo;
    auto type = abilityInfo.type;
    if (type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not extension ability");
        return ERR_WRONG_INTERFACE_CALL;
    }
    if (extensionType != AppExecFwk::ExtensionAbilityType::UNSPECIFIED &&
        extensionType != abilityInfo.extensionAbilityType) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "extension ability type not match, set type:%{public}d, real type: %{public}d",
            static_cast<int32_t>(extensionType), static_cast<int32_t>(abilityInfo.extensionAbilityType));
        return ERR_WRONG_INTERFACE_CALL;
    }

    auto result = CheckStaticCfgPermission(abilityRequest, false, -1, false, false, isImplicit);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result=%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }

    if (abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::DATASHARE ||
        abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE ||
        abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        result = CheckCallServiceExtensionPermission(abilityRequest);
    } else if (abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::APP_SERVICE) {
        result = CheckCallAppServiceExtensionPermission(abilityRequest, nullptr, false);
    } else {
        result = CheckCallOtherExtensionPermission(abilityRequest, validUserId);
    }
    if (result != ERR_OK) {
        return result;
    }
    if (!isStartAsCaller) {
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, abilityRequest.callerToken);
    }
    return ERR_OK;
}

void AbilityManagerService::OnAddSystemAbility(int32_t systemAbilityId, const std::string& deviceId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "systemAbilityId: %{public}d add", systemAbilityId);
    switch (systemAbilityId) {
        case BACKGROUND_TASK_MANAGER_SERVICE_ID: {
            SubscribeBackgroundTask();
            break;
        }
        case DISTRIBUTED_SCHED_SA_ID: {
            g_isDmsAlive.store(true);
            break;
        }
        case BUNDLE_MGR_SERVICE_SYS_ABILITY_ID: {
            auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
            if (bundleMgrHelper) {
                bundleMgrHelper->SetBmsReady(true);
            }
            SubscribeBundleEventCallback();
            break;
        }
#ifdef SUPPORT_SCREEN
        case MULTIMODAL_INPUT_SERVICE_ID: {
            auto anrListener = std::make_shared<ApplicationAnrListener>();
            MMI::InputManager::GetInstance()->SetAnrObserver(anrListener);
            break;
        }
#endif
        case WINDOW_MANAGER_SERVICE_ID: {
            InitWindowVisibilityChangedListener();
            break;
        }
        default:
            break;
    }
}

void AbilityManagerService::OnRemoveSystemAbility(int32_t systemAbilityId, const std::string& deviceId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "systemAbilityId: %{public}d remove", systemAbilityId);
    switch (systemAbilityId) {
        case BACKGROUND_TASK_MANAGER_SERVICE_ID: {
            UnSubscribeBackgroundTask();
            break;
        }
        case DISTRIBUTED_SCHED_SA_ID: {
            g_isDmsAlive.store(false);
            break;
        }
        case BUNDLE_MGR_SERVICE_SYS_ABILITY_ID: {
            UnsubscribeBundleEventCallback();
            break;
        }
        case WINDOW_MANAGER_SERVICE_ID: {
            FreeWindowVisibilityChangedListener();
            break;
        }
        default:
            break;
    }
}

void AbilityManagerService::SubscribeBackgroundTask()
{
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
    std::unique_lock<ffrt::mutex> lock(bgtaskObserverMutex_);
    if (!bgtaskObserver_) {
        bgtaskObserver_ = std::make_shared<BackgroundTaskObserver>();
    }
    int ret = BackgroundTaskMgrHelper::SubscribeBackgroundTask(*bgtaskObserver_);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s failed, err:%{public}d", __func__, ret);
        return;
    }
    bgtaskObserver_->GetContinuousTaskApps();
    bgtaskObserver_->GetEfficiencyResourcesTaskApps();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s success", __func__);
#endif
}

void AbilityManagerService::UnSubscribeBackgroundTask()
{
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
    std::unique_lock<ffrt::mutex> lock(bgtaskObserverMutex_);
    if (!bgtaskObserver_) {
        return;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s success", __func__);
#endif
}

void AbilityManagerService::SubscribeBundleEventCallback()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "subscribeBundleEventCallback begin");
    if (taskHandler_) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "submit startResidentApps task");
        auto startResidentAppsTask = [aams = shared_from_this()]() { aams->StartResidentApps(U0_USER_ID); };
        taskHandler_->SubmitTask(startResidentAppsTask, "StartResidentApps");
    }

    if (abilityBundleEventCallback_) {
        return;
    }

    // Register abilityBundleEventCallback to receive hap updates
    abilityBundleEventCallback_ =
        new (std::nothrow) AbilityBundleEventCallback(taskHandler_, abilityAutoStartupService_);
    auto bms = AbilityUtil::GetBundleManagerHelper();
    if (bms) {
        bool ret = IN_PROCESS_CALL(bms->RegisterBundleEventCallback(abilityBundleEventCallback_));
        if (!ret) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "registerBundleEventCallback failed");
        }
        auto pluginRet = IN_PROCESS_CALL(bms->RegisterPluginEventCallback(abilityBundleEventCallback_));
        if (pluginRet != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "RegisterPluginEventCallback failed %{public}d", pluginRet);
        }
    } else {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get bundleManager failed");
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "SubscribeBundleEventCallback success.");
}

void AbilityManagerService::UnsubscribeBundleEventCallback()
{
    if (!abilityBundleEventCallback_) {
        return;
    }
    abilityBundleEventCallback_ = nullptr;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "UnsubscribeBundleEventCallback success.");
}

void AbilityManagerService::ReportAbilityStartInfoToRSS(const AppExecFwk::AbilityInfo &abilityInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (abilityInfo.type == AppExecFwk::AbilityType::PAGE &&
        abilityInfo.launchMode != AppExecFwk::LaunchMode::SPECIFIED) {
        std::vector<AppExecFwk::RunningProcessInfo> runningProcessInfos;
        if (IN_PROCESS_CALL(GetProcessRunningInfos(runningProcessInfos)) != ERR_OK) {
            return;
        }
        bool isColdStart = true;
        int32_t pid = 0;
        bool supportWarmSmartGC = false;
        int32_t preloadMode = -1;
        for (auto const &info : runningProcessInfos) {
            if (info.uid_ == abilityInfo.applicationInfo.uid &&
                info.processType_ == AppExecFwk::ProcessType::NORMAL &&
                    std::find(info.bundleNames.begin(), info.bundleNames.end(),
                abilityInfo.applicationInfo.bundleName) != info.bundleNames.end()) {
                isColdStart = info.isExiting ? true : info.preloadMode_ == AppExecFwk::PreloadMode::PRESS_DOWN;
                pid = info.isExiting ? 0 : info.pid_;
                preloadMode = static_cast<int32_t>(info.preloadMode_);
                bool isSuggestCache = info.isCached;
                bool supportWarmSmartGC = (isSuggestCache ||
                    info.preloadMode_ == AppExecFwk::PreloadMode::PRE_MAKE ||
                    info.preloadMode_ == AppExecFwk::PreloadMode::PRELOAD_MODULE);
                TAG_LOGI(AAFwkTag::ABILITYMGR, "SmartGC: Process %{public}d report to RSS, start type: %{public}d, isCached: %{public}d, supportWarmGC: %{public}d",
                        pid, preloadMode, static_cast<int32_t>(isSuggestCache), static_cast<int32_t>(supportWarmSmartGC));
                break;
            }
        }
        ResSchedUtil::GetInstance().ReportAbilityStartInfoToRSS(abilityInfo, pid, isColdStart, supportWarmSmartGC, preloadMode);
    }
}

void AbilityManagerService::ReportAbilityAssociatedStartInfoToRSS(
    const AppExecFwk::AbilityInfo &abilityInfo, int64_t type, const sptr<IRemoteObject> &callerToken)
{
    if (!callerToken) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "null callerToken");
        return;
    }
    auto callerAbility = Token::GetAbilityRecordByToken(callerToken);
    CHECK_POINTER_LOG(callerAbility, "null callerAbility");
    int32_t callerUid = callerAbility->GetUid();
    int32_t callerPid = callerAbility->GetPid();
    ResSchedUtil::GetInstance().ReportAbilityAssociatedStartInfoToRSS(abilityInfo, type, callerUid, callerPid);
}

void AbilityManagerService::ReportEventToRSS(const AppExecFwk::AbilityInfo &abilityInfo,
    sptr<IRemoteObject> callerToken)
{
    CHECK_POINTER_LOG(taskHandler_, "taskhandler null");
    std::string reason = ResSchedUtil::GetInstance().GetThawReasonByAbilityType(abilityInfo);
    const auto uid = abilityInfo.applicationInfo.uid;
    const auto bundleName = abilityInfo.applicationInfo.bundleName;
    auto callerAbility = Token::GetAbilityRecordByToken(callerToken);
    const int32_t callerPid = (callerAbility != nullptr) ? callerAbility->GetPid() : IPCSkeleton::GetCallingPid();
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}d_%{public}s reason=%{public}s callerPid=%{public}d", uid,
        bundleName.c_str(), reason.c_str(), callerPid);
    taskHandler_->SubmitTask([reason, uid, bundleName, callerPid]() {
        ResSchedUtil::GetInstance().ReportEventToRSS(uid, bundleName, reason, -1, callerPid);
    });
}

void AbilityManagerService::ReportAppConnectOtherExtensionEvent(const AppExecFwk::AbilityInfo &abilityInfo,
    const Want &want)
{
    if (PermissionVerification::GetInstance()->IsSACall()) {
        return;
    }
    const std::unordered_set<AppExecFwk::ExtensionAbilityType> extensionSet {
        AppExecFwk::ExtensionAbilityType::FORM,
        AppExecFwk::ExtensionAbilityType::WORK_SCHEDULER,
        AppExecFwk::ExtensionAbilityType::INPUTMETHOD,
        AppExecFwk::ExtensionAbilityType::ACCESSIBILITY,
        AppExecFwk::ExtensionAbilityType::STATICSUBSCRIBER,
        AppExecFwk::ExtensionAbilityType::WALLPAPER,
        AppExecFwk::ExtensionAbilityType::BACKUP,
        AppExecFwk::ExtensionAbilityType::ENTERPRISE_ADMIN,
        AppExecFwk::ExtensionAbilityType::PRINT,
        AppExecFwk::ExtensionAbilityType::VPN,
        AppExecFwk::ExtensionAbilityType::FILEACCESS_EXTENSION,
        AppExecFwk::ExtensionAbilityType::REMOTE_NOTIFICATION,
        AppExecFwk::ExtensionAbilityType::REMOTE_LOCATION,
        AppExecFwk::ExtensionAbilityType::PUSH,
        AppExecFwk::ExtensionAbilityType::VOIP
    };
    if (extensionSet.find(abilityInfo.extensionAbilityType) != extensionSet.end()) {
        EventInfo eventInfo;
        eventInfo.bundleName = abilityInfo.bundleName;
        eventInfo.moduleName = abilityInfo.moduleName;
        eventInfo.abilityName = abilityInfo.name;
        eventInfo.extensionType = static_cast<int32_t>(abilityInfo.extensionAbilityType);
        eventInfo.callerBundleName = want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME);
        if (eventInfo.callerBundleName.empty()) {
            eventInfo.callerBundleName = want.GetStringParam(Want::PARAM_RESV_CALLER_NATIVE_NAME);
        }
        // Add prefix to distinguish reporting scenarios
        eventInfo.callerBundleName = "Connect:" + eventInfo.callerBundleName;
        EventReport::SendStartAbilityOtherExtensionEvent(EventName::START_ABILITY_OTHER_EXTENSION, eventInfo);
    }
}

int32_t AbilityManagerService::StartExtensionAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        if (!system::GetBoolParameter(ABILITYMS_ENABLE_UISERVICE, false)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "uiServiceExtensionAbility disable");
            return ERR_CAPABILITY_NOT_SUPPORT;
        }
    }
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    if (extensionType == AppExecFwk::ExtensionAbilityType::VPN ||
        extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE ||
        extensionType == AppExecFwk::ExtensionAbilityType::APP_SERVICE) {
        return StartExtensionAbilityInner(want, callerToken, userId, extensionType, false);
    }
    return StartExtensionAbilityInner(want, callerToken, userId, extensionType, true);
}

int AbilityManagerService::ImplicitStartExtensionAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    InsightIntentExecuteParam::RemoveInsightIntent(const_cast<Want &>(want));
    if (extensionType == AppExecFwk::ExtensionAbilityType::VPN) {
        return StartExtensionAbilityInner(want, callerToken, userId, extensionType, false, true);
    }
    return StartExtensionAbilityInner(want, callerToken, userId, extensionType, true, true);
}

int AbilityManagerService::PreloadUIExtensionAbility(const Want &want, std::string &bundleName,
    int32_t userId, int32_t hostPid, int32_t requestCode)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    TAG_LOGI(AAFwkTag::UI_EXT, "callerBundle: %{public}s", bundleName.c_str());
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    // check preload ui extension permission.
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
        return ERR_PERMISSION_DENIED;
    } 
    return PreloadUIExtensionAbilityInner(want, bundleName, userId, hostPid, requestCode);
}

int AbilityManagerService::PreloadUIExtensionAbilityInner(
    const Want &want, std::string &hostBundleName, int32_t userId, int32_t hostPid, int32_t requestCode)
{
    TAG_LOGD(AAFwkTag::UI_EXT, "PreloadUIExtension called, elementName: %{public}s/%{public}s",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str());
    int32_t validUserId = GetValidUserId(userId);
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, ERR_INVALID_VALUE);
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t callerAppIndex = 0;
    int32_t appIndex = 0;
    if (want.HasParameter(Want::PARAM_APP_CLONE_INDEX_KEY)) {
        appIndex = want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, 0);
    }

    if (IN_PROCESS_CALL(bms->GetNameAndIndexForUid(callerUid, hostBundleName, callerAppIndex)) == ERR_OK) {
        AppExecFwk::ExtensionAbilityInfo extensionInfo;
        IN_PROCESS_CALL_WITHOUT_RET(bms->QueryCloneExtensionAbilityInfoWithAppIndex(want.GetElement(),
            AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_DEFAULT, callerAppIndex, extensionInfo, validUserId));
        if (extensionInfo.type == AppExecFwk::ExtensionAbilityType::EMBEDDED_UI) {
            if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
                IN_PROCESS_CALL_WITHOUT_RET(bms->GetPluginExtensionInfo(hostBundleName, want, validUserId, extensionInfo));
            }
            if (hostBundleName == AbilityConfig::SCENEBOARD_BUNDLE_NAME) {
                (const_cast<Want &>(want)).SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, appIndex);
            } else {
                (const_cast<Want &>(want)).SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, callerAppIndex);
            }
        }
    }

    AbilityRequest abilityRequest;
    ErrCode result = ERR_OK;
    EventInfo eventInfo = BuildEventInfo(want, userId);
    eventInfo.lifeCycle = LIFE_CYCLE_PRELOAD;
    result = GenerateExtensionAbilityRequest(want, abilityRequest, nullptr, validUserId, hostBundleName);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "generate abilityReq error");
        return result;
    }
    abilityRequest.requestCode = requestCode;
    abilityRequest.extensionType = abilityRequest.abilityInfo.extensionAbilityType;
    abilityRequest.want.SetParam(IS_PRELOAD_UIEXTENSION_ABILITY, true);
    auto abilityInfo = abilityRequest.abilityInfo;
    abilityRequest.moduleProcess = "";
    AppExecFwk::HapModuleInfo hapModuleInfo;
    if (DelayedSingleton<AppExecFwk::BundleMgrHelper>::GetInstance()->GetHapModuleInfo(
        abilityRequest.abilityInfo, hapModuleInfo) &&
        abilityRequest.abilityInfo.process == hapModuleInfo.process) {
        TAG_LOGD(AAFwkTag::UI_EXT, "hapModule process: %{public}s", hapModuleInfo.process.c_str());
        abilityRequest.moduleProcess = hapModuleInfo.process;
    }
    auto res = JudgeAbilityVisibleControl(abilityInfo);
    if (res != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "target ability invisible");
        return res;
    }
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "connectManager null, userId:%{public}d", validUserId);
        eventInfo.errReason = "get connectManager by userId failed";
        SendExtensionReport(eventInfo, CONNECT_MAMAGER_NOT_FIND_BY_USERID);
        return ERR_INVALID_VALUE;
    }
    result = connectManager->PreloadUIExtensionAbilityLocked(abilityRequest, hostBundleName, hostPid);
    if (result != ERR_OK) {
        eventInfo.errReason = "PreloadUIExtensionAbilityLocked error";
        SendExtensionReport(eventInfo, result);
    }
    return result;
}

int AbilityManagerService::UnloadUIExtensionAbility(const std::shared_ptr<AAFwk::BaseExtensionRecord> &abilityRecord,
    pid_t &hostPid)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    auto connectManager = GetUIExtensionAbilityManagerByToken(abilityRecord->GetToken());
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null");
        return ERR_INVALID_VALUE;
    }
    return connectManager->UnloadUIExtensionAbility(abilityRecord, hostPid);
}

int AbilityManagerService::RequestModalUIExtension(const Want &want)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    return RequestModalUIExtensionInner(want);
}

int AbilityManagerService::RequestModalUIExtensionInner(Want want)
{
    sptr<IRemoteObject> token = nullptr;
    int ret = IN_PROCESS_CALL(GetTopAbility(token));
    if (ret == ERR_OK && token != nullptr) {
        // Gets the record corresponding to the current focus appliaction
        auto record = Token::GetAbilityRecordByToken(token);
        if (!record) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "record null");
            return ERR_INVALID_VALUE;
        }

        // Gets the bundleName corresponding to the
        // current focus appliaction
        std::string focusName = record->GetAbilityInfo().bundleName;

        // Gets the bundleName corresponding to the
        // current focus appliaction
        std::string callerName = want.GetParams().GetStringParam("bundleName");

        TAG_LOGI(AAFwkTag::ABILITYMGR,
               "focusbundlename: %{public}s, callerbundlename: %{public}s",
               focusName.c_str(), callerName.c_str());

        // Compare
        if (record->GetAbilityInfo().type == AppExecFwk::AbilityType::PAGE &&
            focusName == callerName) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "CreateModalUIExtension is called!");
            return record->CreateModalUIExtension(want);
        }
    } else {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "token null");
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "Window Modal System Create UIExtension is called!");
    want.SetParam(UIEXTENSION_MODAL_TYPE, 1);
    auto connection = std::make_shared<Rosen::ModalSystemUiExtension>();
    return connection->CreateModalUIExtension(want) ? ERR_OK : INNER_ERR;
}

int AbilityManagerService::ChangeAbilityVisibility(sptr<IRemoteObject> token, bool isShow)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    bool isEnable = AppUtils::GetInstance().IsStartOptionsWithProcessOptions();
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled() || !isEnable) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "capability not support");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->ChangeAbilityVisibility(token, isShow);
}

int AbilityManagerService::ChangeUIAbilityVisibilityBySCB(sptr<SessionInfo> sessionInfo, bool isShow)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->ChangeUIAbilityVisibilityBySCB(sessionInfo, isShow);
}

bool AbilityManagerService::CheckWorkSchedulerPermission(const sptr<IRemoteObject> &callerToken, const uint32_t uid)
{
#ifdef BGTASKMGR_CONTINUOUS_TASK_ENABLE
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    std::unique_lock<ffrt::mutex> lock(bgtaskObserverMutex_);
    if (bgtaskObserver_ && abilityRecord) {
        auto callerAbilityInfo = abilityRecord->GetAbilityInfo();
        if (callerAbilityInfo.extensionAbilityType != AppExecFwk::ExtensionAbilityType::WORK_SCHEDULER) {
            return true;
        }

        if (!bgtaskObserver_->IsEfficiencyResourcesTaskUid(uid)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "no permission to start extension by WorkScheduler");
            return false;
        }
    }
#endif
    return true;
}

int32_t AbilityManagerService::StartExtensionAbilityInner(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType, bool checkSystemCaller, bool isImplicit,
    bool isDlp, bool isStartAsCaller)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::SERVICE_EXT,
        "Start extension ability come, bundlename: %{public}s, ability is %{public}s, userId is %{public}d",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str(), userId);
    CheckExtensionRateLimit(want);
    if (checkSystemCaller) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    EventInfo eventInfo = BuildEventInfo(want, userId);
    eventInfo.extensionType = static_cast<int32_t>(extensionType);
    eventInfo.lifeCycle = LIFE_CYCLE_START;

    int result;
#ifdef WITH_DLP
    result = CheckDlpForExtension(want, callerToken, userId, eventInfo, EventName::START_EXTENSION_ERROR);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "CheckDlpForExtension error");
        return result;
    }
#endif // WITH_DLP

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "%{public}s verificationAllToken failed", __func__);
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "verificationAllToken error";
            SendExtensionReport(eventInfo, INVALID_CALLER_TOKEN, true);
        } else {
            eventInfo.errCode = ERR_INVALID_VALUE;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return ERR_INVALID_CALLER;
    }

    int32_t validUserId = GetValidUserId(userId);
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "GetAppIndex error";
            SendExtensionReport(eventInfo, ERR_APP_CLONE_INDEX_INVALID, true);
        } else {
            eventInfo.errCode = ERR_APP_CLONE_INDEX_INVALID;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    StartAbilityInfoWrap threadLocalInfo(want, validUserId, appIndex, callerToken, true);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, 0, validUserId, false, nullptr,
        shouldBlockFunc);
    result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "interceptorExecuter_ null or doProcess error");
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "interceptorExecuter_ null or doProcess error";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, result, true);
        } else {
            eventInfo.errCode = result;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }

    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "multi-user non-concurrent unsatisfied");
        eventInfo.errCode = ERR_CROSS_USER;
        EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
#ifdef SUPPORT_SCREEN
    if (ImplicitStartProcessor::IsImplicitStartAction(want)) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "is implicit start action");
        abilityRequest.Voluation(want, DEFAULT_INVAL_VALUE, callerToken);
        abilityRequest.callType = AbilityCallType::START_EXTENSION_TYPE;
        abilityRequest.extensionType = extensionType;
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        result = implicitStartProcessor_->ImplicitStartAbility(abilityRequest, validUserId);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "implicit start ability error:%{public}d", result);
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "implicit start ability error";
                eventInfo.appIndex = appIndex;
                SendExtensionReport(eventInfo, result, true);
            } else {
                eventInfo.errCode = result;
                EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
        }
        return AbilityErrorUtil::ConvertToOriginErrorCode(result);
    }
#endif
    result = GenerateExtensionAbilityRequest(want, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "generate ability request local error");
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "generate ability request local error";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, result, true);
        } else {
            eventInfo.errCode = result;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return result;
    }

    abilityRequest.userId = validUserId;
    if (!HandleExecuteSAInterceptor(want, callerToken, abilityRequest, result)) {
        return result;
    }

    if (!CheckWorkSchedulerPermission(callerToken, abilityRequest.abilityInfo.applicationInfo.uid)) {
        return CHECK_PERMISSION_FAILED;
    }
    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = isDlp ? IN_PROCESS_CALL(
        CheckOptExtensionAbility(want, abilityRequest, validUserId, extensionType, isImplicit, isStartAsCaller)) :
        CheckOptExtensionAbility(want, abilityRequest, validUserId, extensionType, isImplicit, isStartAsCaller);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "checkOptExtensionAbility error");
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "checkOptExtensionAbility error";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, result, true);
        } else {
            eventInfo.errCode = result;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return result;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, 0, validUserId,
        false, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), false, appIndex);
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "afterCheckExecuter_ null or doProcess error");
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "afterCheckExecuter_ null or doProcess error";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, result, true);
        } else {
            eventInfo.errCode = result;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return result;
    }

    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId=%{public}d", validUserId);
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "get connectManager by userId failed";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, CONNECT_MAMAGER_NOT_FIND_BY_USERID, true);
        } else {
            eventInfo.errCode = ERR_INVALID_VALUE;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return ERR_INVALID_VALUE;
    }
    if (!isStartAsCaller) {
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    }

    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Start extension begin, name is %{public}s.", abilityInfo.name.c_str());
    SetAbilityRequestSessionInfo(abilityRequest, extensionType);
    eventInfo.errCode = connectManager->StartAbility(abilityRequest);
    if (eventInfo.errCode != ERR_OK) {
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "StartAbility error";
            eventInfo.appIndex = appIndex;
            SendExtensionReport(eventInfo, eventInfo.errCode, true);
        } else {
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
    }
    ReportAbilityAssociatedStartInfoToRSS(abilityRequest.abilityInfo, RES_TYPE_EXTENSION_START_ABILITY, callerToken);
    return eventInfo.errCode;
}

bool AbilityManagerService::JudgeSystemParamsForPicker(const WantParams &parameters)
{
    auto systemParamsForPickerMap = parameters.GetParams();
    if (systemParamsForPickerMap.find(SCREENCONFIG_SCREENMODE) == systemParamsForPickerMap.end()) {
        return true;
    }

    if (AAFwk::PermissionVerification::GetInstance()->JudgeCallerIsAllowedToUseSystemAPI()) {
        return true;
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "caller no system-app, can not use system-api");
    return false;
}

void AbilityManagerService::SetPickerElementNameAndParams(const sptr<SessionInfo> &extensionSessionInfo, int32_t userId)
{
    CHECK_POINTER_IS_NULLPTR(extensionSessionInfo);
    std::string targetType = extensionSessionInfo->want.GetStringParam(UIEXTENSION_TARGET_TYPE_KEY);
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled() &&
        extensionSessionInfo->want.GetElement().GetBundleName().empty() &&
        extensionSessionInfo->want.GetElement().GetAbilityName().empty() &&
        COMMON_PICKER_TYPE.find(targetType) != COMMON_PICKER_TYPE.end()) {
        std::string abilityName = "CommonSelectPickerAbility";
        std::string bundleName = "com.ohos.amsdialog";
        extensionSessionInfo->want.SetElementName(bundleName, abilityName);
        WantParams &parameters = const_cast<WantParams &>(extensionSessionInfo->want.GetParams());
        parameters.SetParam(UIEXTENSION_TYPE_KEY, AAFwk::String::Box("sys/commonUI"));
        if (!JudgeSystemParamsForPicker(parameters)) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "parames include systemApi but not a systemAPP");
            extensionSessionInfo->want.RemoveParam(SCREENCONFIG_SCREENMODE);
        }
        extensionSessionInfo->want.SetParams(parameters);
        return;
    }
    if (extensionSessionInfo->want.GetElement().GetBundleName().empty() &&
        extensionSessionInfo->want.GetElement().GetAbilityName().empty() && !targetType.empty()) {
        std::string abilityName;
        std::string bundleName;
        std::string pickerType;
        std::vector<AppExecFwk::ExtensionAbilityInfo> extensionInfos;
        auto pickerMap = AmsConfigurationParameter::GetInstance().GetPickerMap();
        auto it = pickerMap.find(targetType);
        if (it == pickerMap.end()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "can not find targetType:%{public}s", targetType.c_str());
            return;
        }
        pickerType = it->second;
        auto bms = AbilityUtil::GetBundleManagerHelper();
        CHECK_POINTER(bms);
        int32_t validUserId = GetValidUserId(userId);
        TAG_LOGI(AAFwkTag::ABILITYMGR, "targetType: %{public}s, pickerType: %{public}s, userId: %{public}d",
            targetType.c_str(), pickerType.c_str(), validUserId);
        auto flags = static_cast<uint32_t>(GetExtensionAbilityInfoFlag::GET_EXTENSION_ABILITY_INFO_WITH_PERMISSION) |
            static_cast<uint32_t>(GetExtensionAbilityInfoFlag::GET_EXTENSION_ABILITY_INFO_BY_TYPE_NAME);
        auto ret = IN_PROCESS_CALL(bms->QueryExtensionAbilityInfosOnlyWithTypeName(pickerType,
            flags,
            validUserId,
            extensionInfos));
        if (ret != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "queryExtensionAbilityInfosOnlyWithTypeName failed");
            return;
        }
        abilityName = extensionInfos[0].name;
        bundleName = extensionInfos[0].bundleName;
        TAG_LOGI(AAFwkTag::ABILITYMGR,
            "abilityName: %{public}s, bundleName: %{public}s", abilityName.c_str(), bundleName.c_str());
        extensionSessionInfo->want.SetElementName(bundleName, abilityName);
        WantParams &parameters = const_cast<WantParams &>(extensionSessionInfo->want.GetParams());
        parameters.SetParam(UIEXTENSION_TYPE_KEY, AAFwk::String::Box(pickerType));

        if (!JudgeSystemParamsForPicker(parameters)) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "parames include systemApi but not a systemAPP");
            extensionSessionInfo->want.RemoveParam(SCREENCONFIG_SCREENMODE);
        }
        extensionSessionInfo->want.SetParams(parameters);
    }
}

void AbilityManagerService::SetAutoFillElementName(const sptr<SessionInfo> &extensionSessionInfo)
{
#ifdef SUPPORT_AUTO_FILL
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    CHECK_POINTER_IS_NULLPTR(extensionSessionInfo);
    std::vector<std::string> argList;
    if (extensionSessionInfo->want.GetStringParam(UIEXTENSION_TYPE_KEY) == AUTO_FILL_PASSWORD_TYPE) {
        SplitStr(KEY_AUTO_FILL_ABILITY, "/", argList);
    } else if (extensionSessionInfo->want.GetStringParam(UIEXTENSION_TYPE_KEY) == AUTO_FILL_SMART_TYPE) {
        SplitStr(KEY_SMART_AUTO_FILL_ABILITY, "/", argList);
    } else {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "not autofill");
        return;
    }

    if (argList.size() != ARGC_THREE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "parse extension element name failed");
        return;
    }
    extensionSessionInfo->want.SetElementName(argList[INDEX_ZERO], argList[INDEX_TWO]);
    extensionSessionInfo->want.SetModuleName(argList[INDEX_ONE]);
#endif // SUPPORT_AUTO_FILL
}

int AbilityManagerService::CheckUIExtensionUsage(AppExecFwk::UIExtensionUsage uiExtensionUsage,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    if (uiExtensionUsage == UIExtensionUsage::EMBEDDED &&
        !AAFwk::UIExtensionWrapper::IsPublicForEmbedded(extensionType)) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }

    if (uiExtensionUsage == UIExtensionUsage::CONSTRAINED_EMBEDDED &&
        !AAFwk::UIExtensionWrapper::IsPublicForConstrainedEmbedded(extensionType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "secureConstrainedEmbedded extension type error:%u.", extensionType);
        return ERR_INVALID_VALUE;
    }

    if (uiExtensionUsage == UIExtensionUsage::PRE_VIEW_EMBEDDED &&
        !AAFwk::UIExtensionWrapper::IsSystemUIExtension(extensionType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target not system app");
        return ERR_INVALID_VALUE;
    }

    return ERR_OK;
}

int AbilityManagerService::StartUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo, int32_t userId)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start uiext");
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::UI_EXT, "StartUIExtensionAbility begin");
    CHECK_POINTER_AND_RETURN(extensionSessionInfo, ERR_INVALID_VALUE);
    SetPickerElementNameAndParams(extensionSessionInfo, userId);
    SetAutoFillElementName(extensionSessionInfo);
    EventInfo eventInfo = BuildEventInfo(extensionSessionInfo->want, userId);
    eventInfo.persistentId = extensionSessionInfo->persistentId;
    eventInfo.lifeCycle = LIFE_CYCLE_START;
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);

    if (extensionSessionInfo->want.HasParameter(AAFwk::SCREEN_MODE_KEY)) {
        int32_t screenMode = extensionSessionInfo->want.GetIntParam(AAFwk::SCREEN_MODE_KEY, AAFwk::IDLE_SCREEN_MODE);
        if (!IsEmbeddableStart(screenMode)) {
            TAG_LOGE(AAFwkTag::UI_EXT, "only support embedded pull-ups");
            return ERR_INVALID_VALUE;
        }
        auto bms = AbilityUtil::GetBundleManagerHelper();
        CHECK_POINTER_AND_RETURN(bms, ERR_INVALID_VALUE);
        TAG_LOGD(AAFwkTag::UI_EXT, "bundleName: %{public}s, userId: %{public}d",
            extensionSessionInfo->want.GetBundle().c_str(), GetValidUserId(userId));
        AppExecFwk::BundleInfo bundleInfo;
        if (!IN_PROCESS_CALL(bms->GetBundleInfo(extensionSessionInfo->want.GetBundle(),
            AppExecFwk::BundleFlag::GET_BUNDLE_WITH_ABILITIES, bundleInfo, GetValidUserId(userId)))) {
            TAG_LOGE(AAFwkTag::UI_EXT, "verifyPermission failed get application info");
            return CHECK_PERMISSION_FAILED;
        }
        if (bundleInfo.applicationInfo.bundleType != AppExecFwk::BundleType::ATOMIC_SERVICE) {
            TAG_LOGE(AAFwkTag::UI_EXT, "only support atomicService");
            return ERR_INVALID_CALLER;
        }
        if (extensionSessionInfo->want.GetElement().GetAbilityName().empty()) {
            if (bundleInfo.abilityInfos.empty()) {
                TAG_LOGE(AAFwkTag::UI_EXT, "failed get abilityInfos");
                eventInfo.errReason = "failed get abilityInfos";
                SendExtensionReport(eventInfo, EXTENSION_ABILITY_NOT_EXIST);
                return ERR_INVALID_VALUE;
            }
            extensionSessionInfo->want.SetElementName(bundleInfo.name, bundleInfo.abilityInfos.begin()->name);
        }
        extensionSessionInfo->want.SetParam("send_to_erms_embedded", 1);
    }
    std::string extensionTypeStr = extensionSessionInfo->want.GetStringParam(UIEXTENSION_TYPE_KEY);
    AppExecFwk::ExtensionAbilityType extensionType = extensionTypeStr.empty() ?
        AppExecFwk::ExtensionAbilityType::UI : AppExecFwk::ConvertToExtensionAbilityType(extensionTypeStr);
    if (extensionType == AppExecFwk::ExtensionAbilityType::UNSPECIFIED) {
        TAG_LOGE(AAFwkTag::UI_EXT, "input extension ability type invalid");
        return ERR_INVALID_VALUE;
    }
    eventInfo.extensionType = static_cast<int32_t>(extensionType);

    auto ret = CheckUIExtensionUsage(extensionSessionInfo->uiExtensionUsage, extensionType);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "check usage failed");
        return ret;
    }

    if (InsightIntentExecuteParam::IsInsightIntentExecute(extensionSessionInfo->want)) {
        auto callerBundlename = InsightIntentGetcallerBundleName();
        if (callerBundlename.empty()) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "insightIntent get callerBundlename failed");
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "start uiExtension ability, bundlename: %{public}s", callerBundlename.c_str());
        int32_t result = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckAndUpdateWant(
            extensionSessionInfo->want, AppExecFwk::ExecuteMode::UI_EXTENSION_ABILITY,
            GetValidUserId(userId), callerBundlename);
        if (result != ERR_OK) {
            eventInfo.errReason = "CheckAndUpdateWant error";
            SendExtensionReport(eventInfo, result);
            return result;
        }
    }

    sptr<IRemoteObject> callerToken = extensionSessionInfo->callerToken;

    if (!DlpUtils::AccessCheck(callerToken, extensionSessionInfo->want) ||
        VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::UI_EXT, "startUIExtensionAbility: permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "startUIExtensionAbility verificationAllToken failed");
        eventInfo.errReason = "not containsAbility or not find abilityRecord by callerToken";
        SendExtensionReport(eventInfo, INVALID_CALLER_TOKEN);
        return ERR_INVALID_CALLER;
    }

    auto callerRecord = Token::GetAbilityRecordByToken(callerToken);
    if (callerRecord == nullptr || !JudgeSelfCalled(callerRecord)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "invalid callerToken");
        eventInfo.errReason = "get ability record by callerToken failed";
        SendExtensionReport(eventInfo, INVALID_CALLER_TOKEN);
        return ERR_INVALID_CALLER;
    }
    StartAbilityInfoWrap threadLocalInfo;

    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(extensionSessionInfo->want, 0,
        GetValidUserId(userId), true, nullptr, shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "interceptorExecuter_ null or doProcess error");
        eventInfo.errReason = "interceptorExecuter_ null or doProcess error";
        SendExtensionReport(eventInfo, result);
        return result;
    }

    int32_t validUserId = GetValidUserId(userId);
    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "multi-user non-concurrent unsatisfied");
        eventInfo.errReason = "multi-user non-concurrent unsatisfied";
        SendExtensionReport(eventInfo, ERR_CROSS_USER);
        return ERR_INVALID_VALUE;
    }
#ifdef SUPPORT_GRAPHICS
    if (ImplicitStartProcessor::IsImplicitStartAction(extensionSessionInfo->want)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "UI extension ability not support implicit start");
        return ERR_INVALID_VALUE;
    }
#endif // SUPPORT_GRAPHICS
    AbilityRequest abilityRequest;
    abilityRequest.Voluation(extensionSessionInfo->want, DEFAULT_INVAL_VALUE, callerToken);
    abilityRequest.callType = AbilityCallType::START_EXTENSION_TYPE;
    abilityRequest.sessionInfo = extensionSessionInfo;
    if (AbilityRuntime::StartupUtil::IsStartPlugin(extensionSessionInfo->want)) {
        abilityRequest.isTargetPlugin = true;
    }
    result = GenerateEmbeddableUIAbilityRequest(extensionSessionInfo->want, abilityRequest, callerToken, validUserId);
    CHECK_POINTER_AND_RETURN(abilityRequest.sessionInfo, ERR_INVALID_VALUE);
    abilityRequest.sessionInfo->uiExtensionComponentId = (
        static_cast<uint64_t>(callerRecord->GetRecordId()) << OFFSET) |
        static_cast<uint64_t>(abilityRequest.sessionInfo->persistentId);
    TAG_LOGI(AAFwkTag::UI_EXT, "StartUIExtension: persistentId: %{public}d, element: %{public}s/%{public}s",
        abilityRequest.sessionInfo->persistentId, extensionSessionInfo->want.GetElement().GetBundleName().c_str(),
        extensionSessionInfo->want.GetElement().GetAbilityName().c_str());
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "generate ability request local error");
        eventInfo.errReason = "generate ability request local error";
        SendExtensionReport(eventInfo, result);
        return result;
    }
    abilityRequest.extensionType = abilityRequest.abilityInfo.extensionAbilityType;

    abilityRequest.moduleProcess = "";
    AppExecFwk::HapModuleInfo hapModuleInfo;
    if (DelayedSingleton<AppExecFwk::BundleMgrHelper>::GetInstance()->GetHapModuleInfo(
        abilityRequest.abilityInfo, hapModuleInfo) &&
        abilityRequest.abilityInfo.process == hapModuleInfo.process) {
        TAG_LOGD(AAFwkTag::UI_EXT, "hapModule process: %{public}s", hapModuleInfo.process.c_str());
        abilityRequest.moduleProcess = hapModuleInfo.process;
    }

    abilityRequest.userId = validUserId;
    if (!HandleExecuteSAInterceptor(extensionSessionInfo->want, callerToken, abilityRequest, result)) {
        return result;
    }
    auto abilityInfo = abilityRequest.abilityInfo;
    threadLocalInfo.SetStartAbilityInfo(abilityInfo);
    validUserId = abilityInfo.applicationInfo.singleton ? U0_USER_ID : validUserId;
    TAG_LOGD(AAFwkTag::UI_EXT, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = ProcessUdmfKey(extensionSessionInfo->want, abilityInfo.applicationInfo.accessTokenId, extensionType);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "ProcessUdmfKey error");
        return result;
    }

    result = CheckOptExtensionAbility(extensionSessionInfo->want, abilityRequest, validUserId, extensionType);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "checkOptExtensionAbility error");
        eventInfo.errReason = "checkOptExtensionAbility error";
        SendExtensionReport(eventInfo, result);
        return result;
    }

    sptr<IRemoteObject> parentToken = extensionSessionInfo->parentToken;
    if (parentToken && parentToken != callerToken) {
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, parentToken);
    }

    result = JudgeAbilityVisibleControl(abilityInfo);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "judgeAbilityVisibleControl error");
        return result;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, 0, validUserId,
        true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo));
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "afterCheckExecuter_ null or doProcess error");
        eventInfo.errReason = "afterCheckExecuter_ null or doProcess error";
        SendExtensionReport(eventInfo, result);
        return result;
    }

    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::UI_EXT, "connectManager null userId=%{public}d", validUserId);
        eventInfo.errReason = "get connectManager by userId failed";
        SendExtensionReport(eventInfo, CONNECT_MAMAGER_NOT_FIND_BY_USERID);
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::UI_EXT, "name:%{public}s", abilityInfo.name.c_str());
#ifdef SUPPORT_GRAPHICS
    // for implicit system selector modal dialog
    bool isSCBCall = (callerRecord->GetApplicationInfo().bundleName == AbilityConfig::SCENEBOARD_BUNDLE_NAME);
    DialogSessionManager::GetInstance().UpdateExtensionWantWithDialogCallerInfo(abilityRequest, callerToken,
        isSCBCall);
#endif // SUPPORT_GRAPHICS
    eventInfo.errCode = connectManager->StartAbility(abilityRequest);
    if (eventInfo.errCode != ERR_OK) {
        eventInfo.errReason = "StartAbility error";
        SendExtensionReport(eventInfo, eventInfo.errCode);
    }
    return eventInfo.errCode;
}

int AbilityManagerService::StopExtensionAbility(const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    TAG_LOGI(AAFwkTag::SERVICE_EXT,
        "bundlename:%{public}s, ability:%{public}s, userId:%{public}d",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str(), userId);
    if (extensionType != AppExecFwk::ExtensionAbilityType::VPN &&
        extensionType != AppExecFwk::ExtensionAbilityType::APP_SERVICE) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    EventInfo eventInfo = BuildEventInfo(want, userId);
    eventInfo.extensionType = static_cast<int32_t>(extensionType);

    int result;
#ifdef WITH_DLP
    result = CheckDlpForExtension(want, callerToken, userId, eventInfo, EventName::STOP_EXTENSION_ERROR);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "CheckDlpForExtension error");
        return result;
    }
#endif // WITH_DLP

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "%{public}s verificationAllToken failed", __func__);
        if (!PermissionVerification::GetInstance()->CheckSpecificSystemAbilityAccessPermission(DMS_PROCESS_NAME)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "verificationAllToken failed");
            eventInfo.errCode = ERR_INVALID_VALUE;
            EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
            return ERR_INVALID_CALLER;
        }
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "Caller is specific system ability.");
    }

    int32_t validUserId = GetValidUserId(userId);
    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "multi-user non-concurrent unsatisfied");
        eventInfo.errCode = ERR_INVALID_VALUE;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return ERR_CROSS_USER;
    }

    if (callerToken != nullptr && CheckIfOperateRemote(want)) {
        auto callerUid = IPCSkeleton::GetCallingUid();
        uint32_t accessToken = IPCSkeleton::GetCallingTokenID();
        DistributedClient dmsClient;
        return dmsClient.StopRemoteExtensionAbility(want, callerUid, accessToken, eventInfo.extensionType);
    }

    AbilityRequest abilityRequest;
    result = GenerateExtensionAbilityRequest(want, abilityRequest, callerToken, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "generate ability request local error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return result;
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = CheckOptExtensionAbility(want, abilityRequest, validUserId, extensionType);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "checkOptExtensionAbility error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return result;
    }

    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId=%{public}d", validUserId);
        eventInfo.errCode = ERR_INVALID_VALUE;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Stop extension begin, name:%{public}s", abilityInfo.name.c_str());
    eventInfo.errCode = connectManager->StopServiceAbility(abilityRequest);
    if (eventInfo.errCode != ERR_OK) {
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
    return eventInfo.errCode;
}

void AbilityManagerService::StopSwitchUserDialog()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Stop switch user dialog extension ability come");
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "scene board enabled");
        return;
    }

    if (AbilityRuntime::UserController::GetInstance().GetFreezingNewUserId() == DEFAULT_INVAL_VALUE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get last userId error");
        return;
    }
#ifdef SUPPORT_GRAPHICS
    auto sysDialog = DelayedSingleton<SystemDialogScheduler>::GetInstance();
    if (sysDialog == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "system dialog scheduler instance null");
        return;
    }
    Want stopWant = sysDialog->GetSwitchUserDialogWant();
    StopSwitchUserDialogInner(stopWant, AbilityRuntime::UserController::GetInstance().GetFreezingNewUserId());
#endif // SUPPORT_GRAPHICS
    AbilityRuntime::UserController::GetInstance().SetFreezingNewUserId(DEFAULT_INVAL_VALUE);
    return;
}

void AbilityManagerService::StopSwitchUserDialogInner(const Want &want, const int32_t lastUserId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Stop switch user dialog inner come");
    EventInfo eventInfo = BuildEventInfo(want, lastUserId);
    eventInfo.extensionType = static_cast<int32_t>(AppExecFwk::ExtensionAbilityType::SERVICE);
    AbilityRequest abilityRequest;
    auto result =
        GenerateExtensionAbilityRequest(want, abilityRequest, nullptr, lastUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return;
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    auto stopUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    result = CheckOptExtensionAbility(want, abilityRequest, stopUserId, AppExecFwk::ExtensionAbilityType::SERVICE);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check extensionAbility type error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return;
    }

    auto connectManager = GetConnectManagerByUserId(stopUserId, abilityInfo.extensionAbilityType);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId:%{public}d", stopUserId);
        eventInfo.errCode = ERR_INVALID_VALUE;
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return;
    }

    eventInfo.errCode = connectManager->StopServiceAbility(abilityRequest);
    if (eventInfo.errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "eventInfo errCode=%{public}d", eventInfo.errCode);
        EventReport::SendExtensionEvent(EventName::STOP_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
}

int AbilityManagerService::MoveAbilityToBackground(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Move ability to background begin");
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        return ERR_WOULD_BLOCK;
    }

    auto ownerUserId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null ownerUserId=%{public}d", ownerUserId);
        return ERR_INVALID_VALUE;
    }
    return missionListManager->MoveAbilityToBackground(abilityRecord);
}

int32_t AbilityManagerService::MoveUIAbilityToBackground(const sptr<IRemoteObject> token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called");
    if (!AppUtils::GetInstance().EnableMoveUIAbilityToBackgroundApi()) {
        return ERR_OPERATION_NOT_SUPPORTED_ON_CURRENT_DEVICE;
    }
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!IsAppSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }
    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "move ability background failed in wukong mode");
        return ERR_WUKONG_MODE_CANT_MOVE_STATE;
    }
    if (!abilityRecord->IsAbilityState(FOREGROUND) && !abilityRecord->IsAbilityState(FOREGROUNDING)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability not foregorund state");
        return ERR_ABILITY_NOT_FOREGROUND;
    }
    if (abilityRecord->GetAbilityInfo().type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot background non UIAbility");
        return RESOLVE_CALL_ABILITY_TYPE_ERR;
    }
    auto ownerUserId = abilityRecord->GetOwnerMissionUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->NotifySCBToMinimizeUIAbility(token);
    }

    auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_INVALID_VALUE);
    return missionListManager->MoveAbilityToBackground(abilityRecord);
}

int AbilityManagerService::TerminateAbility(const sptr<IRemoteObject> &token, int resultCode, const Want *resultWant)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_INVALID_VALUE;
    }
    auto elementName = abilityRecord->GetWant().GetElement();
    if (AppUtils::GetInstance().IsLauncher(elementName.GetBundleName()) &&
        AppUtils::GetInstance().IsLauncherAbility(elementName.GetAbilityName())) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "cannot terminate launcher ability");
        return ERR_OK;
    }
    return TerminateAbilityWithFlag(token, resultCode, resultWant, true);
}

int32_t AbilityManagerService::TerminateUIServiceExtensionAbility(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (!VerificationAllToken(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s verificationAllToken failed", __func__);
        return ERR_INVALID_VALUE;
    }

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    auto type = abilityRecord->GetAbilityInfo().type;
    auto extensionAbilityType = abilityRecord->GetAbilityInfo().extensionAbilityType;

    if (type != AppExecFwk::AbilityType::EXTENSION  ||
        extensionAbilityType != AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            return ERR_INVALID_VALUE;
    }

    auto userId = GetValidUserId(DEFAULT_INVAL_VALUE);
    auto connectManager = GetCommonExtensionManagerByUserId(userId);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null. userId=%{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->TerminateAbility(token);
}

int AbilityManagerService::BackToCallerAbilityWithResult(const sptr<IRemoteObject> &token, int resultCode,
    const Want *resultWant, int64_t callerRequestCode)
{
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_INVALID_VALUE;
    }
    auto ownerUserId = abilityRecord->GetOwnerMissionUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->BackToCallerAbilityWithResult(abilityRecord, resultCode, resultWant,
            callerRequestCode);
    }
    auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_INVALID_VALUE);
    return missionListManager->BackToCallerAbilityWithResult(abilityRecord, resultCode, resultWant, callerRequestCode);
}

int AbilityManagerService::CloseAbility(const sptr<IRemoteObject> &token, int resultCode, const Want *resultWant)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    EventInfo eventInfo;
    SendAbilityEvent(EventName::CLOSE_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    return TerminateAbilityWithFlag(token, resultCode, resultWant, false);
}

int AbilityManagerService::TerminateAbilityWithFlag(const sptr<IRemoteObject> &token, int resultCode,
    const Want *resultWant, bool flag)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Terminate ability begin, flag:%{public}d.", flag);
    if (!VerificationAllToken(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s verificationAllToken failed", __func__);
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    if (IsSystemUiApp(abilityRecord->GetAbilityInfo())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "system ui not allow terminate");
        return ERR_INVALID_VALUE;
    }

    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto type = abilityRecord->GetAbilityInfo().type;
    if (type == AppExecFwk::AbilityType::SERVICE || type == AppExecFwk::AbilityType::EXTENSION) {
        auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
        if (!connectManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null. userId=%{public}d", userId);
            return ERR_INVALID_VALUE;
        }
        return connectManager->TerminateAbility(token);
    }

    if (type == AppExecFwk::AbilityType::DATA) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot terminate, use 'ReleaseDataAbility()'");
        return ERR_WRONG_INTERFACE_CALL;
    }

    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        return ERR_WOULD_BLOCK;
    }

    auto ownerUserId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
    if (missionListManager) {
        return missionListManager->TerminateAbility(abilityRecord, resultCode, resultWant, flag);
    }
    TAG_LOGW(AAFwkTag::ABILITYMGR, "missionListManager null ownerUserId=%{public}d", ownerUserId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->CloseUIAbility(std::static_pointer_cast<UIAbilityRecord>(abilityRecord),
            resultCode, resultWant, false, false);
    }
    return ERR_INVALID_VALUE;
}

int AbilityManagerService::TerminateUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo, int resultCode,
    const Want *resultWant)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Terminate ui extension ability begin.");
    CHECK_POINTER_AND_RETURN(extensionSessionInfo, ERR_INVALID_VALUE);
    auto abilityRecord = Token::GetAbilityRecordByToken(extensionSessionInfo->callerToken);
    std::shared_ptr<UIExtensionAbilityManager> connectManager;
    std::shared_ptr<BaseExtensionRecord> targetRecord;
    GetConnectManagerAndUIExtensionBySessionInfo(extensionSessionInfo, connectManager, targetRecord, true);
    CHECK_POINTER_AND_RETURN(targetRecord, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(connectManager, ERR_INVALID_VALUE);
    EventInfo eventInfo = BuildEventInfo(extensionSessionInfo->want, extensionSessionInfo->userId);
    eventInfo.lifeCycle = LIFE_CYCLE_TERMINATE;
    SendAbilityEvent(EventName::TERMINATE_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);

    // self terminate or caller terminate is allowed.
    if (!JudgeSelfCalled(targetRecord) && abilityRecord != nullptr && !JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto result = JudgeAbilityVisibleControl(targetRecord->GetAbilityInfo());
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "judgeAbilityVisibleControl error");
        return result;
    }

    if (!UIExtensionWrapper::IsUIExtension(targetRecord->GetAbilityInfo().extensionAbilityType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot terminate except ui extension ability");
        eventInfo.errReason = "cannot terminate except ui extension ability";
        SendExtensionReport(eventInfo, EXTENSION_TYPE_NOT_UI_EXTENSION);
        return ERR_WRONG_INTERFACE_CALL;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "UIExtension persistentId: %{public}d, element: %{public}s/%{public}s",
        extensionSessionInfo->persistentId, extensionSessionInfo->want.GetElement().GetBundleName().c_str(),
        extensionSessionInfo->want.GetElement().GetAbilityName().c_str());
    connectManager->TerminateAbilityWindowLocked(targetRecord, extensionSessionInfo);
    return ERR_OK;
}

int AbilityManagerService::CloseUIExtensionAbilityBySCB(const sptr<IRemoteObject> token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "close uiextensionability by scb");
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_PERMISSION_DENIED;
    }

    if (!VerificationAllToken(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verificationAllToken failed");
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!UIExtensionWrapper::IsUIExtension(abilityRecord->GetAbilityInfo().extensionAbilityType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability %{public}s/%{public}s not an uiextensionability",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
        return ERR_INVALID_VALUE;
    }

    auto sessionInfo = abilityRecord->GetSessionInfo();
    if (sessionInfo == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target session info is null, ability: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
        return ERR_INVALID_VALUE;
    }

    std::shared_ptr<UIExtensionAbilityManager> connectManager;
    std::shared_ptr<BaseExtensionRecord> targetRecord;
    GetConnectManagerAndUIExtensionBySessionInfo(sessionInfo, connectManager, targetRecord, true);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null, ability: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
        return ERR_INVALID_VALUE;
    }

    sptr<Rosen::ISession> sessionProxy = iface_cast<Rosen::ISession>(sessionInfo->sessionToken);
    if (sessionProxy == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Get session proxy failed, ability: %{public}s/%{public}s",
            abilityRecord->GetElementName().GetBundleName().c_str(),
            abilityRecord->GetElementName().GetAbilityName().c_str());
        return ERR_INVALID_VALUE;
    }

    // notify caller sync detach
    sessionProxy->NotifyExtensionDetachToDisplay();
    connectManager->TerminateAbilityWindowLocked(BaseExtensionRecord::TransferToExtensionRecordBase(abilityRecord),
        sessionInfo);
    return ERR_OK;
}

int AbilityManagerService::CloseUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool isUserRequestedExit,
    uint32_t sceneFlag)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (sessionInfo == nullptr || sessionInfo->sessionToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return ERR_INVALID_VALUE;
    }

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }

    SetMinimizedDuringFreeInstall(sessionInfo);

    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "close session: %{public}d, resultCode: %{public}d, isClearSession: %{public}d",
        sessionInfo->persistentId, sessionInfo->resultCode, sessionInfo->isClearSession);
    if (sessionInfo->isClearSession) {
        (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->
            DeleteAbilityRecoverInfoBySessionId(sessionInfo->persistentId);
    }
    auto abilityRecord = uiAbilityManager->GetUIAbilityRecordBySessionInfo(sessionInfo);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    abilityRecord->SetSceneFlag(sceneFlag);
    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        return ERR_WOULD_BLOCK;
    }

    EventInfo eventInfo;
    eventInfo.bundleName = abilityRecord->GetAbilityInfo().bundleName;
    eventInfo.abilityName = abilityRecord->GetAbilityInfo().name;
    SendAbilityEvent(EventName::CLOSE_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if (isUserRequestedExit) {
        CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
        AAFwk::ExitReason exitReason = { REASON_NORMAL, "User Request" };
        appExitReasonHelper_->RecordUIAbilityExitReason(abilityRecord->GetPid(), abilityRecord->GetAbilityInfo().name,
            exitReason);
    }
    eventInfo.errCode = uiAbilityManager->CloseUIAbility(abilityRecord, sessionInfo->resultCode,
        &(sessionInfo->want), sessionInfo->isClearSession, false);
    if (eventInfo.errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "close UIAbility by SCB failed: %{public}d", eventInfo.errCode);
        SendAbilityEvent(EventName::TERMINATE_ABILITY_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
    return AbilityErrorUtil::ConvertToOriginErrorCode(eventInfo.errCode);
}

int AbilityManagerService::SendResultToAbility(int32_t requestCode, int32_t resultCode, Want &resultWant)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    if (!CheckCallerIsDmsProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check processName failed");
        return ERR_INVALID_VALUE;
    }
    int missionId = resultWant.GetIntParam(DMS_MISSION_ID, DEFAULT_DMS_MISSION_ID);
    resultWant.RemoveParam(DMS_MISSION_ID);
    if (missionId == DEFAULT_DMS_MISSION_ID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionId empty");
        return ERR_INVALID_VALUE;
    }
    std::shared_ptr<AbilityRecord> abilityRecord = nullptr;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetCurrentUIAbilityManager();
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        abilityRecord = uiAbilityManager->GetAbilityRecordsById(missionId);
    } else {
        sptr<IRemoteObject> abilityToken = GetAbilityTokenByMissionId(missionId);
        CHECK_POINTER_AND_RETURN(abilityToken, ERR_INVALID_VALUE);
        abilityRecord = Token::GetAbilityRecordByToken(abilityToken);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    abilityRecord->SetResult(std::make_shared<AbilityResult>(requestCode, resultCode, resultWant));
    abilityRecord->SendResult(0, 0);
    return ERR_OK;
}

int AbilityManagerService::StartRemoteAbility(const Want &want, int requestCode, int32_t validUserId,
    const sptr<IRemoteObject> &callerToken, uint32_t specifyTokenId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    Want remoteWant = want;
    UpdateCallerInfoUtil::GetInstance().UpdateDmsCallerInfo(remoteWant, callerToken);
    if (AddStartControlParam(remoteWant, callerToken) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s addStartControlParam failed", __func__);
        return ERR_ADD_START_CONTROL_PARAM_FAILED;
    }
    if (AbilityUtil::IsStartFreeInstall(remoteWant)) {
        return freeInstallManager_ == nullptr ? ERR_NULL_FREE_INSTALL_MANAGER :
            freeInstallManager_->StartRemoteFreeInstall(remoteWant, requestCode, validUserId, callerToken);
    }
    if (remoteWant.GetBoolParam(Want::PARAM_RESV_FOR_RESULT, false)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "try startAbilityForResult");
        int32_t missionId = -1;
        if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
            missionId = GetMissionIdByAbilityTokenInner(callerToken);
            if (!missionId) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid missionId id");
                return ERR_GET_MISSION_ID_BY_ABILITY_TOKEN_FAILED;
            }
        } else {
            missionId = GetMissionIdByAbilityToken(callerToken);
        }
        if (missionId < 0) {
            return ERR_INVALID_MISSION_ID;
        }
        remoteWant.SetParam(DMS_MISSION_ID, missionId);
    }

    int32_t callerUid = IPCSkeleton::GetCallingUid();
    uint32_t accessToken = IPCSkeleton::GetCallingTokenID();
#ifdef SUPPORT_UPMS
    UriUtils::GetInstance().CheckUriPermission(accessToken, remoteWant);
#endif // SUPPORT_UPMS
    DistributedClient dmsClient;
    int result = dmsClient.StartRemoteAbility(remoteWant, callerUid, requestCode, accessToken, specifyTokenId);
    if (result != ERR_NONE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityManagerService::startRemoteAbility failed, result=%{public}d", result);
    }
    return result;
}

bool AbilityManagerService::CheckIsRemote(const std::string& deviceId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (deviceId.empty()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "checkIsRemote:deviceId empty");
        return false;
    }
    std::string localDeviceId;
    if (!GetLocalDeviceId(localDeviceId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkIsRemote:get local deviceId failed");
        return false;
    }
    if (localDeviceId == deviceId) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "checkIsRemote:deviceId local");
        return false;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "CheckIsRemote, deviceId = %{public}s", AnonymizeDeviceId(deviceId).c_str());
    return true;
}

bool AbilityManagerService::CheckIfOperateRemote(const Want &want)
{
    std::string deviceId = want.GetElement().GetDeviceID();
    if (deviceId.empty() || want.GetElement().GetBundleName().empty() ||
        want.GetElement().GetAbilityName().empty()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "CheckIfOperateRemote: DeviceId or BundleName or GetAbilityName empty");
        return false;
    }
    return CheckIsRemote(deviceId);
}

bool AbilityManagerService::GetLocalDeviceId(std::string& localDeviceId)
{
#ifdef SUPPORT_RECORDER_DSOFTBUS
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto localNode = std::make_unique<NodeBasicInfo>();
    int32_t errCode = GetLocalNodeDeviceInfo(DM_PKG_NAME, localNode.get());
    if (errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "err=%{public}d", errCode);
        return false;
    }
    if (localNode != nullptr) {
        localDeviceId = localNode->networkId;
        TAG_LOGD(AAFwkTag::ABILITYMGR, "get local deviceId, deviceId = %{public}s",
            AnonymizeDeviceId(localDeviceId).c_str());
        return true;
    }
#endif
    TAG_LOGE(AAFwkTag::ABILITYMGR, "localDeviceId null");
    return false;
}

std::string AbilityManagerService::AnonymizeDeviceId(const std::string& deviceId)
{
    if (deviceId.length() < NON_ANONYMIZE_LENGTH) {
        return EMPTY_DEVICE_ID;
    }
    std::string anonDeviceId = deviceId.substr(0, NON_ANONYMIZE_LENGTH);
    anonDeviceId.append("******");
    return anonDeviceId;
}

int AbilityManagerService::MinimizeAbility(const sptr<IRemoteObject> &token, bool fromUser)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "minimize ability, fromUser:%{public}d", fromUser);
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot minimize except page ability");
        return ERR_WRONG_INTERFACE_CALL;
    }

    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        return ERR_WOULD_BLOCK;
    }

    auto missionListManager = GetMissionListManagerByUserId(abilityRecord->GetOwnerMissionUserId());
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null");
        return ERR_INVALID_VALUE;
    }
    return missionListManager->MinimizeAbility(token, fromUser);
}

int AbilityManagerService::MinimizeUIExtensionAbility(const sptr<SessionInfo> &extensionSessionInfo,
    bool fromUser)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Minimize ui extension ability, fromUser:%{public}d.", fromUser);
    CHECK_POINTER_AND_RETURN(extensionSessionInfo, ERR_INVALID_VALUE);
    auto abilityRecord = Token::GetAbilityRecordByToken(extensionSessionInfo->callerToken);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    EventInfo eventInfo = BuildEventInfo(extensionSessionInfo->want, extensionSessionInfo->userId);
    eventInfo.lifeCycle = LIFE_CYCLE_MINIMIZE;
    SendAbilityEvent(EventName::ABILITY_ONBACKGROUND, HISYSEVENT_BEHAVIOR, eventInfo);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    std::shared_ptr<UIExtensionAbilityManager> connectManager;
    std::shared_ptr<BaseExtensionRecord> targetRecord;
    GetConnectManagerAndUIExtensionBySessionInfo(extensionSessionInfo, connectManager, targetRecord);
    CHECK_POINTER_AND_RETURN(targetRecord, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(connectManager, ERR_INVALID_VALUE);

    auto result = JudgeAbilityVisibleControl(targetRecord->GetAbilityInfo());
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "judgeAbilityVisibleControl error");
        return result;
    }

    if (!UIExtensionWrapper::IsUIExtension(targetRecord->GetAbilityInfo().extensionAbilityType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot minimize except ui extension ability");
        eventInfo.errReason = "cannot minimize except ui extension ability";
        SendExtensionReport(eventInfo, EXTENSION_TYPE_NOT_UI_EXTENSION);
        return ERR_WRONG_INTERFACE_CALL;
    }
    extensionSessionInfo->uiExtensionComponentId = (
        static_cast<uint64_t>(abilityRecord->GetRecordId()) << OFFSET) |
        static_cast<uint64_t>(extensionSessionInfo->persistentId);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "UIExtension component id: %{public}" PRId64 ", element: %{public}s/%{public}s",
        extensionSessionInfo->uiExtensionComponentId, extensionSessionInfo->want.GetElement().GetBundleName().c_str(),
        extensionSessionInfo->want.GetElement().GetAbilityName().c_str());
    connectManager->BackgroundAbilityWindowLocked(targetRecord, extensionSessionInfo);
    return ERR_OK;
}

void AbilityManagerService::SetMinimizedDuringFreeInstall(const sptr<SessionInfo> &sessionInfo)
{
    if (sessionInfo == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return;
    }

    if (!(sessionInfo->want).HasParameter(KEY_SESSION_ID)) {
        return;
    }

    std::string sessionId = (sessionInfo->want).GetStringParam(KEY_SESSION_ID);
    if (sessionId.empty()) {
        return;
    }

    if (freeInstallManager_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "freeInstallManager_ null");
        return;
    }
    FreeInstallInfo taskInfo;
    if (!freeInstallManager_->GetFreeInstallTaskInfo(sessionId, taskInfo)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install task with sessionId=%{public}s does not exist",
            sessionId.c_str());
        return;
    }

    if (taskInfo.isFreeInstallFinished) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install task finished");
        return;
    }

    {
        std::lock_guard<ffrt::mutex> guard(preStartSessionMapLock_);
        auto it = preStartSessionMap_.find(sessionId);
        if (it == preStartSessionMap_.end()) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "session info with sessionId=%{public}s does not exist",
                sessionId.c_str());
            return;
        }
        CHECK_POINTER(it->second);
        it->second->isMinimizedDuringFreeInstall = true;
    }
}

int AbilityManagerService::MinimizeUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool fromUser,
    uint32_t sceneFlag)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called, sceneFlag:%{public}u", sceneFlag);
    if (sessionInfo == nullptr || sessionInfo->sessionToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return ERR_INVALID_VALUE;
    }

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }

    SetMinimizedDuringFreeInstall(sessionInfo);

    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    auto abilityRecord = uiAbilityManager->GetUIAbilityRecordBySessionInfo(sessionInfo);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        return ERR_WOULD_BLOCK;
    }
    return uiAbilityManager->MinimizeUIAbility(abilityRecord, fromUser, sceneFlag);
}

int32_t AbilityManagerService::ConnectAbility(
    const Want &want, const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken, int32_t userId)
{
    return ConnectAbilityCommon(want, connect, callerToken, AppExecFwk::ExtensionAbilityType::SERVICE, userId);
}

int32_t AbilityManagerService::ConnectAbilityCommon(
    const Want &want, const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken,
    AppExecFwk::ExtensionAbilityType extensionType, int32_t userId, bool isQueryExtensionOnly,
    uint64_t specifiedFullTokenId, int32_t loadTimeout)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    if (specifiedFullTokenId != 0 && IPCSkeleton::GetCallingUid() != DMS_UID) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "specifiedFullTokenId only support for DMS");
        specifiedFullTokenId = 0;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "element: %{public}s/%{public}s",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str());
    CheckExtensionRateLimit(want);
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(connect->AsObject(), ERR_INVALID_VALUE);
    if (extensionType != AppExecFwk::ExtensionAbilityType::UI_SERVICE && want.HasParameter(UISERVICEHOSTPROXY_KEY)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "error to have UISERVICEHOSTPROXY_KEY");
        return ERR_WRONG_INTERFACE_CALL;
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::SERVICE && IsCrossUserCall(userId)) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    EventInfo eventInfo = BuildEventInfo(want, userId);
	eventInfo.lifeCycle = LIFE_CYCLE_CONNECT;

    int result;
#ifdef WITH_DLP
    result = CheckDlpForExtension(want, callerToken, userId, eventInfo, EventName::CONNECT_SERVICE_ERROR);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "checkDlpForExtension error");
        return result;
    }
#endif // WITH_DLP

    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, 0, GetValidUserId(userId), false, nullptr,
        shouldBlockFunc);
    result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "interceptorExecuter_ null or doProcess error");
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "interceptorExecuter_ null or doProcess error";
            SendExtensionReport(eventInfo, result, true);
        } else {
            eventInfo.errCode = result;
            EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
        return result;
    }

    int32_t validUserId = GetValidUserId(userId);

    if (AbilityUtil::IsStartFreeInstall(want)) {
        CHECK_POINTER_AND_RETURN(freeInstallManager_, ERR_INVALID_VALUE);
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "is start free install");
        std::string localDeviceId;
        if (!GetLocalDeviceId(localDeviceId)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "%{public}s:get Local deviceId failed", __func__);
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "get Local deviceId failed";
                SendExtensionReport(eventInfo, GET_LOCAL_DEVICE_ID_FAILED, true);
            } else {
                eventInfo.errCode = ERR_INVALID_VALUE;
                EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
            return ERR_INVALID_VALUE;
        }
        result = freeInstallManager_->ConnectFreeInstall(want, validUserId, callerToken, localDeviceId);
        if (result != ERR_OK) {
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "ConnectFreeInstall error";
                SendExtensionReport(eventInfo, result, true);
            } else {
                eventInfo.errCode = result;
                EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
            return result;
        }
    }

    Want abilityWant = want;
    AbilityRequest abilityRequest;
    std::string uri = abilityWant.GetUri().ToString();
    bool isFileUri = (abilityWant.GetUri().GetScheme() == "file");
    if (!uri.empty() && !isFileUri) {
        // if the want include uri, it may only has uri information. it is probably a datashare extension.
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "uri: %{public}s, userId: %{public}d", uri.c_str(), validUserId);
        AppExecFwk::ExtensionAbilityInfo extensionInfo;
        auto bms = AbilityUtil::GetBundleManagerHelper();
        CHECK_POINTER_AND_RETURN(bms, ERR_INVALID_VALUE);

        bool queryResult = IN_PROCESS_CALL(bms->QueryExtensionAbilityInfoByUri(uri, validUserId, extensionInfo));
        if (!queryResult || extensionInfo.name.empty() || extensionInfo.bundleName.empty()) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "invalid extension ability info");
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "invalid extension ability info";
                SendExtensionReport(eventInfo, EXTENSION_ABILITY_INFO_NOT_QUERY_BY_URI, true);
            } else {
                eventInfo.errCode = ERR_INVALID_VALUE;
                EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
            return ERR_INVALID_VALUE;
        }
        abilityWant.SetElementName(extensionInfo.bundleName, extensionInfo.name);
    }

    if (CheckIfOperateRemote(abilityWant)) {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "AbilityManagerService::ConnectAbility. try to ConnectRemoteAbility");
        eventInfo.errCode = ConnectRemoteAbility(abilityWant, callerToken, connect->AsObject());
        if (eventInfo.errCode != ERR_OK) {
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "ConnectRemoteAbility error";
                SendExtensionReport(eventInfo, eventInfo.errCode, true);
            } else {
                EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
        }
        return eventInfo.errCode;
    }
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityWant, callerToken);

    if (callerToken != nullptr && callerToken->GetObjectDescriptor() != u"ohos.aafwk.AbilityToken") {
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "invalid Token.");
        eventInfo.errCode = ConnectLocalAbility(abilityWant, validUserId, connect, nullptr, extensionType, nullptr,
            false, nullptr, specifiedFullTokenId, loadTimeout);
        if (eventInfo.errCode != ERR_OK) {
            if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
                eventInfo.errReason = "ConnectLocalAbility error";
                SendExtensionReport(eventInfo, eventInfo.errCode, true);
            } else {
                EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
            }
        }
        return eventInfo.errCode;
    }
    eventInfo.errCode = ConnectLocalAbility(abilityWant, validUserId, connect, callerToken, extensionType, nullptr,
        isQueryExtensionOnly, nullptr, specifiedFullTokenId, loadTimeout);
    if (eventInfo.errCode != ERR_OK) {
        if (extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            eventInfo.errReason = "ConnectLocalAbility error";
            SendExtensionReport(eventInfo, eventInfo.errCode, true);
        } else {
            EventReport::SendExtensionEvent(EventName::CONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
        }
    }
    return eventInfo.errCode;
}

int AbilityManagerService::ConnectUIExtensionAbility(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<SessionInfo> &sessionInfo, int32_t userId, sptr<UIExtensionAbilityConnectInfo> connectInfo)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::UI_EXT,
        "ConnectUIExtensionAbility bundlename: %{public}s, ability is %{public}s, userId is %{private}d",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str(), userId);
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(connect->AsObject(), ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);

    if (IsCrossUserCall(userId)) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }

    EventInfo eventInfo = BuildEventInfo(want, userId);
    eventInfo.lifeCycle = LIFE_CYCLE_CONNECT;
    sptr<IRemoteObject> callerToken = sessionInfo->callerToken;

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "connectUIExtensionAbility verificationAllToken failed");
        eventInfo.errReason = "not containsAbility or not find abilityRecord by callerToken";
        SendExtensionReport(eventInfo, INVALID_CALLER_TOKEN);
        return ERR_INVALID_CALLER;
    }

    int result;
#ifdef WITH_DLP
    result = CheckDlpForExtension(want, callerToken, userId, eventInfo, EventName::CONNECT_SERVICE_ERROR);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "checkDlpForExtension error");
        return result;
    }
#endif // WITH_DLP

    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, 0, GetValidUserId(userId), false, nullptr,
        shouldBlockFunc);
    result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "interceptorExecuter_ null or doProcess error");
        eventInfo.errReason = "interceptorExecuter_ null or doProcess error";
        SendExtensionReport(eventInfo, result);
        return result;
    }

    int32_t validUserId = GetValidUserId(userId);

    Want abilityWant = want;
    AbilityRequest abilityRequest;
    std::string uri = abilityWant.GetUri().ToString();
    if (!uri.empty()) {
        // if the want include uri, it may only has uri information.
        TAG_LOGI(AAFwkTag::UI_EXT, "called. uri:%{public}s/%{public}s, userId %{public}d",
            abilityWant.GetElement().GetBundleName().c_str(),
            abilityWant.GetElement().GetAbilityName().c_str(), validUserId);
        AppExecFwk::ExtensionAbilityInfo extensionInfo;
        auto bms = AbilityUtil::GetBundleManagerHelper();
        CHECK_POINTER_AND_RETURN(bms, ERR_INVALID_VALUE);

        bool queryResult = IN_PROCESS_CALL(bms->QueryExtensionAbilityInfoByUri(uri, validUserId, extensionInfo));
        if (!queryResult || extensionInfo.name.empty() || extensionInfo.bundleName.empty()) {
            TAG_LOGE(AAFwkTag::UI_EXT, "invalid extension ability info");
            eventInfo.errReason = "invalid extension ability info";
            SendExtensionReport(eventInfo, EXTENSION_ABILITY_INFO_NOT_QUERY_BY_URI);
            return ERR_INVALID_VALUE;
        }
        abilityWant.SetElementName(extensionInfo.bundleName, extensionInfo.name);
    }

    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityWant, callerToken);

    if (callerToken != nullptr && callerToken->GetObjectDescriptor() != u"ohos.aafwk.AbilityToken") {
        TAG_LOGI(AAFwkTag::UI_EXT, "invalid Token");
        eventInfo.errCode = ConnectLocalAbility(abilityWant, validUserId, connect, nullptr,
            AppExecFwk::ExtensionAbilityType::UI, sessionInfo, false, connectInfo);
        if (eventInfo.errCode != ERR_OK) {
            eventInfo.errReason = "ConnectLocalAbility error";
            SendExtensionReport(eventInfo, eventInfo.errCode);
        }
        return eventInfo.errCode;
    }
    eventInfo.errCode = ConnectLocalAbility(abilityWant, validUserId, connect, callerToken,
        AppExecFwk::ExtensionAbilityType::UI, sessionInfo, false, connectInfo);
    if (eventInfo.errCode != ERR_OK) {
        eventInfo.errReason = "ConnectLocalAbility error";
        SendExtensionReport(eventInfo, eventInfo.errCode);
    }
    return eventInfo.errCode;
}

EventInfo AbilityManagerService::BuildEventInfo(const Want &want, int32_t userId)
{
    EventInfo eventInfo;
    eventInfo.userId = userId;
    eventInfo.bundleName = want.GetElement().GetBundleName();
    eventInfo.moduleName = want.GetElement().GetModuleName();
    eventInfo.abilityName = want.GetElement().GetAbilityName();
    return eventInfo;
}

int AbilityManagerService::DisconnectAbility(sptr<IAbilityConnection> connect)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "Disconnect");
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    int err = DisconnectLocalAbility(connect);
    if (err == ERR_OK) {
        return ERR_OK;
    }
    CHECK_POINTER_AND_RETURN(connect->AsObject(), ERR_INVALID_VALUE);
    int remoteErr = DisconnectRemoteAbility(connect->AsObject());
    if (remoteErr == ERR_OK) {
        return ERR_OK;
    }
    if (remoteErr != INVALID_PARAMETERS_ERR &&
        remoteErr != CONNECTION_NOT_EXIST &&
        err == CONNECTION_NOT_EXIST) {
        err = remoteErr;
    }
    TAG_LOGE(AAFwkTag::SERVICE_EXT, "Disconnect error %{public}d", err);
    EventInfo eventInfo;
    eventInfo.errCode = err;
    EventReport::SendExtensionEvent(EventName::DISCONNECT_SERVICE_ERROR, HISYSEVENT_FAULT, eventInfo);
    return err;
}

bool AbilityManagerService::CheckSupportVpn(AppExecFwk::AbilityInfo abilityInfo)
{
    auto bundleName = abilityInfo.applicationInfo.bundleName;
    if (std::find(vpnAllowList_.begin(), vpnAllowList_.end(), bundleName) == vpnAllowList_.end()) {
        return false;
    }
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "allow bundleName: %{public}s",  bundleName.c_str());
    return true;
}

bool AbilityManagerService::ParseVpnAllowListJson(const std::string &relativePath, const std::string &jsonItemStr)
{
    nlohmann::json jsonObj;
    std::string absolutePath = GetConfigFileAbsolutePath(relativePath);
    if (absolutePath.length() == 0) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "ParseVpnAllowListJson absolutePath isEmpty");
        absolutePath = DEFAULT_VPN_ALLOWLIST_CONFIG_FILE;
    }
    if (ParseJsonValueFromFile(jsonObj, absolutePath) != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "ParseVpnAllowListJson parse file err");
        return false;
    }
    std::lock_guard<std::mutex> locker(allowListMutex_);
    if (!jsonObj.contains(jsonItemStr)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "ParseVpnAllowListJson not contains item");
        return false;
    }

    nlohmann::json vpnAllowJsonList = jsonObj[jsonItemStr.c_str()];
    if (!vpnAllowJsonList.is_array()) {
        TAG_LOGI(AAFwkTag::SERVICE_EXT, "ParseVpnAllowListJson: jsonItem is not array");
        return false;
    }

    for (const auto& it : vpnAllowJsonList) {
        if (it.is_string()) {
            TAG_LOGI(AAFwkTag::SERVICE_EXT, "ParseVpnAllowListJson: bundleName: %{public}s", 
                it.get<std::string>().c_str());
            vpnAllowList_.push_back(it.get<std::string>());
        }
    }
    return true;
}

int32_t AbilityManagerService::ConnectLocalAbility(const Want &want, const int32_t userId,
    const sptr<IAbilityConnection> &connect, const sptr<IRemoteObject> &callerToken,
    AppExecFwk::ExtensionAbilityType extensionType, const sptr<SessionInfo> &sessionInfo,
    bool isQueryExtensionOnly, sptr<UIExtensionAbilityConnectInfo> connectInfo, uint64_t specifiedFullTokenId,
    int32_t loadTimeout)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    StartAbilityInfoWrap threadLocalInfo;
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    if (!CheckCrossUser(userId, extensionType)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
    ErrCode result = ERR_OK;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "start generate ability request, isQueryExtensionOnly: %{public}d, type: %{public}d",
        isQueryExtensionOnly, static_cast<int32_t>(extensionType));
    if (isQueryExtensionOnly ||
        AAFwk::UIExtensionWrapper::IsUIExtension(extensionType)) {
        result = GenerateExtensionAbilityRequest(want, abilityRequest, callerToken, userId);
    } else {
        result = GenerateAbilityRequest(want, DEFAULT_INVAL_VALUE, abilityRequest, callerToken, userId);
    }
    abilityRequest.sessionInfo = sessionInfo;
    abilityRequest.loadExtensionTimeout = loadTimeout;

    Want requestWant = want;
    CHECK_POINTER_AND_RETURN_LOG(connect, ERR_INVALID_VALUE, "connect is nullptr");
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "requestWant SetParam success");

    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "generate request error");
        return result;
    }
    result = CheckPermissionForUIService(extensionType, want, abilityRequest);
    if (result != ERR_OK) {
        return result;
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    threadLocalInfo.SetStartAbilityInfo(abilityInfo);
    if (abilityInfo.isStageBasedModel) {
        bool isService = (abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE);
        if (isService && extensionType != AppExecFwk::ExtensionAbilityType::SERVICE) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "Service extension type, please use ConnectAbility");
            return ERR_WRONG_INTERFACE_CALL;
        }
        // not allow app to connect other extension by using connectServiceExtensionAbility
        bool isVpn = CheckSupportVpn(abilityInfo);
        if (callerToken && extensionType == AppExecFwk::ExtensionAbilityType::SERVICE && !isService && !isVpn) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "ability, type not service");
            return TARGET_ABILITY_NOT_SERVICE;
        }
    }
    int32_t validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "validUserId : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    abilityRequest.specifiedFullTokenId = specifiedFullTokenId;
    result = CheckStaticCfgPermission(abilityRequest, false, -1);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "checkStaticCfgPermission error, result=%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }

    uint32_t specifyTokenId = static_cast<uint32_t>(specifiedFullTokenId);
    AppExecFwk::ExtensionAbilityType targetExtensionType = abilityInfo.extensionAbilityType;
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "extension type %{public}d.", targetExtensionType);
    if (AAFwk::UIExtensionWrapper::IsUIExtension(extensionType)) {
        if (!AAFwk::UIExtensionWrapper::IsUIExtension(targetExtensionType)
            && targetExtensionType != AppExecFwk::ExtensionAbilityType::WINDOW) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "UI extension, target ability not UI extension");
            return ERR_WRONG_INTERFACE_CALL;
        }

        // Cause window has used this api, don't check it when type is window.
        if (targetExtensionType != AppExecFwk::ExtensionAbilityType::WINDOW &&
            !PermissionVerification::GetInstance()->VerifyCallingPermission(
                PermissionConstants::PERMISSION_CONNECT_UI_EXTENSION_ABILITY, specifyTokenId)) {
            TAG_LOGE(AAFwkTag::SERVICE_EXT, "permission %{public}s verification failed",
                PermissionConstants::PERMISSION_CONNECT_UI_EXTENSION_ABILITY);
            return ERR_PERMISSION_DENIED;
        }
    }

    auto type = abilityInfo.type;
    if (type != AppExecFwk::AbilityType::SERVICE && type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "ability failed, target ability not service");
        return TARGET_ABILITY_NOT_SERVICE;
    }

    abilityRequest.userId = validUserId;
    if (!HandleExecuteSAInterceptor(want, callerToken, abilityRequest, result)) {
        return result;
    }

    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, 0, validUserId,
        false, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo));
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "afterCheckExecuter_ null or doProcess error");
        return result;
    }

    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId=%{public}d", validUserId);
        return ERR_INVALID_VALUE;
    }

    if (extensionType == AppExecFwk::ExtensionAbilityType::APP_SERVICE) {
        auto targetService = connectManager->GetServiceRecordByAbilityRequest(abilityRequest);
        result = CheckCallAppServiceExtensionPermission(abilityRequest, targetService, true);
        TAG_LOGD(AAFwkTag::SERVICE_EXT, "CheckCallAppServiceExtensionPermission result: %{public}d", result);
    } else {
        result = CheckCallServicePermission(abilityRequest);
    }
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "%{public}s checkCallServicePermission error", __func__);
        return result;
    }

    ReportAppConnectOtherExtensionEvent(abilityInfo, want);

    if (!ExtensionPermissionsUtil::CheckSAPermission(targetExtensionType, specifyTokenId)) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "SA doesn't have target extension permission");
        return CHECK_PERMISSION_FAILED;
    }

    result = PreLoadAppDataAbilities(abilityInfo.bundleName, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectAbility: app data ability preloading failed, '%{public}s', %{public}d",
            abilityInfo.bundleName.c_str(),
            result);
        return result;
    }

    SetAbilityRequestSessionInfo(abilityRequest, targetExtensionType);
    int ret = ERR_OK;
    if(AAFwk::UIExtensionWrapper::IsUIExtension(abilityInfo.extensionAbilityType)) {
        abilityRequest.uiExtensionAbilityConnectInfo = connectInfo;
        auto uiExtensionManager = GetUIExtensionAbilityManagerByUserId(validUserId);
        ret = uiExtensionManager->ConnectAbilityLocked(abilityRequest, connect, callerToken, sessionInfo);
    }else{
        ret = connectManager->ConnectAbilityLocked(abilityRequest, connect, callerToken, sessionInfo);
    }
    return ret;
}

int AbilityManagerService::ConnectRemoteAbility(Want &want, const sptr<IRemoteObject> &callerToken,
    const sptr<IRemoteObject> &connect)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s begin", __func__);
    UpdateCallerInfoUtil::GetInstance().UpdateDmsCallerInfo(want, callerToken);
    if (AddStartControlParam(want, callerToken) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s addStartControlParam failed", __func__);
        return ERR_INVALID_VALUE;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName: %{public}s, abilityName: %{public}s",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str());
    DistributedClient dmsClient;
    return dmsClient.ConnectRemoteAbility(want, connect);
}

int AbilityManagerService::DisconnectLocalAbility(const sptr<IAbilityConnection> &connect)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    auto userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    auto func = [](std::shared_ptr<AbilityConnectManager> connectManager, sptr<IAbilityConnection> connect) {
        return connectManager->DisconnectAbilityLocked(connect);
    };
    auto ret = HandleExtensionConnectionByUserId(connect, userId, func);
    if (ret == ERR_OK || ret == ERR_NO_INIT) {
        return ret;
    }

    auto commonManagers = GetCommonExtensionManagers();
    for (auto &item : commonManagers) {
        auto userId = item.first;
        if (HandleExtensionConnectionByUserId(connect, userId, func) == ERR_OK) {
            return ERR_OK;
        }
    }
    return CONNECT_MAMAGER_NOT_FIND_BY_USERID;
}

int32_t AbilityManagerService::HandleExtensionConnectionByUserId(sptr<IAbilityConnection> connect, int32_t userId,
    std::function<int32_t(std::shared_ptr<AbilityConnectManager>, sptr<IAbilityConnection>)> func)
{
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    auto uiExtensionManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(commonExtensionManager, ERR_NO_INIT);
    CHECK_POINTER_AND_RETURN(uiExtensionManager, ERR_NO_INIT);

    auto retCommon = func(commonExtensionManager, connect);
    bool commonFailed = retCommon != ERR_OK && retCommon != CONNECTION_NOT_EXIST;
    if (commonFailed) {
        return retCommon;
    }
    auto retUI = func(uiExtensionManager, connect);
    bool uiFailed = retUI != ERR_OK && retUI != CONNECTION_NOT_EXIST;
    if (uiFailed) {
        return retUI;
    }
    if (retCommon == ERR_OK || retUI == ERR_OK) {
        return ERR_OK;
    }
    return CONNECTION_NOT_EXIST;
}

int AbilityManagerService::DisconnectRemoteAbility(const sptr<IRemoteObject> &connect)
{
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    uint32_t accessToken = IPCSkeleton::GetCallingTokenID();
    DistributedClient dmsClient;
    return dmsClient.DisconnectRemoteAbility(connect, callerUid, accessToken);
}

int AbilityManagerService::ContinueMission(const std::string &srcDeviceId, const std::string &dstDeviceId,
    int32_t missionId, const sptr<IRemoteObject> &callBack, AAFwk::WantParams &wantParams)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    TAG_LOGI(AAFwkTag::ABILITYMGR, "missionId: %{public}d", missionId);
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    wantParams.SetParam(DMS_CALLING_UID, AAFwk::Integer::Box(callingUid));
    return dmsClient.ContinueMission(srcDeviceId, dstDeviceId, missionId, callBack, wantParams);
}

int AbilityManagerService::ContinueMission(AAFwk::ContinueMissionInfo continueMissionInfo,
    const sptr<IRemoteObject> &callback)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    AAFWK::ContinueRadar::GetInstance().ClickIconContinue("ContinueMission");
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    continueMissionInfo.wantParams.SetParam(DMS_CALLING_UID, AAFwk::Integer::Box(callingUid));
    return dmsClient.ContinueMission(continueMissionInfo, callback);
}

int AbilityManagerService::ContinueAbility(const std::string &deviceId, int32_t missionId, uint32_t versionCode)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "ContinueAbility missionId = %{public}d, version = %{public}u.", missionId, versionCode);
    if (!CheckCallerIsDmsProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check processName failed");
        return ERR_INVALID_VALUE;
    }

    std::shared_ptr<AbilityRecord> abilityRecord = nullptr;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetCurrentUIAbilityManager();
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        abilityRecord = uiAbilityManager->GetAbilityRecordsById(missionId);
    } else {
        sptr<IRemoteObject> abilityToken = GetAbilityTokenByMissionId(missionId);
        CHECK_POINTER_AND_RETURN(abilityToken, ERR_INVALID_VALUE);
        abilityRecord = Token::GetAbilityRecordByToken(abilityToken);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    abilityRecord->ContinueAbility(deviceId, versionCode);
    return ERR_OK;
}

int AbilityManagerService::StartContinuation(const Want &want, const sptr<IRemoteObject> &abilityToken, int32_t status)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start continuation");
    if (!CheckIfOperateRemote(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "deviceId or bundleName or abilityName empty");
        return ERR_INVALID_VALUE;
    }
    CHECK_POINTER_AND_RETURN(abilityToken, ERR_INVALID_VALUE);

    int32_t appUid = IPCSkeleton::GetCallingUid();
    uint32_t accessToken = IPCSkeleton::GetCallingTokenID();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "try startContinuation");
    int32_t missionId = -1;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        missionId = GetMissionIdByAbilityTokenInner(abilityToken);
        if (!missionId) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid missionId id");
            return ERR_INVALID_VALUE;
        }
    } else {
        missionId = GetMissionIdByAbilityToken(abilityToken);
    }
    if (missionId < 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get missionId");
        return ERR_INVALID_VALUE;
    }
    AAFWK::ContinueRadar::GetInstance().SaveDataRemoteWant("StartContinuation");
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "bundleName: %{public}s, abilityName: %{public}s, missionId: %{public}d, status: %{public}d",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str(), missionId, status);
    DistributedClient dmsClient;
    auto result =  dmsClient.StartContinuation(want, missionId, appUid, status, accessToken);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startContinuation failed, result=%{public}d, notify caller", result);
        NotifyContinuationResult(missionId, result);
    }
    return result;
}

void AbilityManagerService::NotifyCompleteContinuation(const std::string &deviceId,
    int32_t sessionId, bool isSuccess)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "NotifyCompleteContinuation");
    AAFWK::ContinueRadar::GetInstance().ClickIconRecvOver("NotifyCompleteContinuation");
    sptr<ISystemAbilityManager> samgrProxy = SystemAbilityManagerClient::GetInstance().GetSystemAbilityManager();
    if (samgrProxy == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get samgrProxy");
        return;
    }
    sptr<IRemoteObject> bmsProxy = samgrProxy->GetSystemAbility(BUNDLE_MGR_SERVICE_SYS_ABILITY_ID);
    if (bmsProxy == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get bms from samgr");
        return;
    }
    auto bundleMgr = iface_cast<AppExecFwk::IBundleMgr>(bmsProxy);
    if (bundleMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get bms");
        return;
    }
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    std::string callerBundleName;
    // reset ipc identity
    auto identity = IPCSkeleton::ResetCallingIdentity();
    bool result = bundleMgr->GetBundleNameForUid(callerUid, callerBundleName);
    // set ipc identity to raw
    IPCSkeleton::SetCallingIdentity(identity);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "callerBundleName: %{public}s", callerBundleName.c_str());
    DistributedClient dmsClient;
    dmsClient.NotifyCompleteContinuation(Str8ToStr16(deviceId), sessionId, isSuccess, callerBundleName);
}

int AbilityManagerService::NotifyContinuationResult(int32_t missionId, int32_t result)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "result : %{public}d", result);
    std::shared_ptr<AbilityRecord> abilityRecord = nullptr;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetCurrentUIAbilityManager();
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        abilityRecord = uiAbilityManager->GetAbilityRecordsById(missionId);
    } else {
        sptr<IRemoteObject> abilityToken = GetAbilityTokenByMissionId(missionId);
        CHECK_POINTER_AND_RETURN(abilityToken, ERR_INVALID_VALUE);
        abilityRecord = Token::GetAbilityRecordByToken(abilityToken);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    if (!JudgeSelfCalled(abilityRecord) && !CheckCallerIsDmsProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_INVALID_VALUE;
    }
    abilityRecord->NotifyContinuationResult(result);
    return ERR_OK;
}

int AbilityManagerService::StartSyncRemoteMissions(const std::string& devId, bool fixConflict, int64_t tag)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    uint32_t callingTokenId = IPCSkeleton::GetCallingTokenID();
    TAG_LOGD(AAFwkTag::ABILITYMGR, "fixConflict: %{public}d, tag: %{public}" PRId64, fixConflict, tag);
    return dmsClient.StartSyncRemoteMissions(devId, fixConflict, tag, callingUid, callingTokenId);
}

int AbilityManagerService::StopSyncRemoteMissions(const std::string& devId)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    return dmsClient.StopSyncRemoteMissions(devId, callingUid);
}

int AbilityManagerService::RegisterObserver(const sptr<AbilityRuntime::IConnectionObserver> &observer)
{
    if (!PermissionVerification::GetInstance()->CheckObserverCallerPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<ConnectionStateManager>::GetInstance()->RegisterObserver(observer);
}

int AbilityManagerService::UnregisterObserver(const sptr<AbilityRuntime::IConnectionObserver> &observer)
{
    if (!PermissionVerification::GetInstance()->CheckObserverCallerPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<ConnectionStateManager>::GetInstance()->UnregisterObserver(observer);
}

int32_t AbilityManagerService::RegisterForegroundAppObserver(sptr<AbilityRuntime::IForegroundAppConnection> observer)
{
    if (!PermissionVerification::GetInstance()->CheckObserverCallerPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<ForegroundAppConnectionManager>::GetInstance()->RegisterObserver(observer);
}

int32_t AbilityManagerService::UnregisterForegroundAppObserver(sptr<AbilityRuntime::IForegroundAppConnection> observer)
{
    if (!PermissionVerification::GetInstance()->CheckObserverCallerPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<ForegroundAppConnectionManager>::GetInstance()->UnregisterObserver(observer);
}

#ifdef WITH_DLP
int AbilityManagerService::GetDlpConnectionInfos(std::vector<AbilityRuntime::DlpConnectionInfo> &infos)
{
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "can't get dlp connection infos if caller not sa");
        return CHECK_PERMISSION_FAILED;
    }
    DelayedSingleton<ConnectionStateManager>::GetInstance()->GetDlpConnectionInfos(infos);

    return ERR_OK;
}
#endif // WITH_DLP

int AbilityManagerService::GetConnectionData(std::vector<AbilityRuntime::ConnectionData> &connectionData)
{
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller no sa no connection data");
        return CHECK_PERMISSION_FAILED;
    }
    DelayedSingleton<ConnectionStateManager>::GetInstance()->GetConnectionData(connectionData);

    return ERR_OK;
}

int AbilityManagerService::RegisterMissionListener(const std::string &deviceId,
    const sptr<IRemoteMissionListener> &listener)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    std::string localDeviceId;
    if (!GetLocalDeviceId(localDeviceId) || localDeviceId == deviceId) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "registerMissionListener:check deviceId failed");
        return REGISTER_REMOTE_MISSION_LISTENER_FAIL;
    }
    CHECK_POINTER_AND_RETURN(listener, ERR_INVALID_VALUE);
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    return dmsClient.RegisterMissionListener(Str8ToStr16(deviceId), listener->AsObject(), callingUid);
}

int AbilityManagerService::RegisterOnListener(const std::string &type,
    const sptr<IRemoteOnListener> &listener)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    CHECK_POINTER_AND_RETURN(listener, ERR_INVALID_VALUE);
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    int32_t ret = dmsClient.RegisterOnListener(type, listener->AsObject(), callingUid);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed with code: %{public}d", ret);
        return INNER_ERR;
    }
    return ERR_OK;
}

int AbilityManagerService::RegisterOffListener(const std::string &type,
    const sptr<IRemoteOnListener> &listener)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    CHECK_POINTER_AND_RETURN(listener, ERR_INVALID_VALUE);
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    int32_t ret = dmsClient.RegisterOffListener(type, listener->AsObject(), callingUid);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed with code: %{public}d", ret);
        return INNER_ERR;
    }
    return ERR_OK;
}

int AbilityManagerService::UnRegisterMissionListener(const std::string &deviceId,
    const sptr<IRemoteMissionListener> &listener)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    std::string localDeviceId;
    if (!GetLocalDeviceId(localDeviceId) || localDeviceId == deviceId) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check deviceId failed");
        return REGISTER_REMOTE_MISSION_LISTENER_FAIL;
    }
    CHECK_POINTER_AND_RETURN(listener, ERR_INVALID_VALUE);
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    DistributedClient dmsClient;
    return dmsClient.UnRegisterMissionListener(Str8ToStr16(deviceId), listener->AsObject());
}

int32_t AbilityManagerService::GetUidByCloneBundleInfo(
    std::string &bundleName, int32_t callerUid, int32_t userId, int32_t &appIndex) const
{
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, -1);
    AppExecFwk::BundleInfo bundleInfo;
    MultiAppUtils::GetRunningMultiAppIndex(bundleName, callerUid, appIndex);
    if (IN_PROCESS_CALL(bms->GetCloneBundleInfo(
        bundleName, static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_APPLICATION),
        appIndex, bundleInfo, userId)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "failed get bundle info for %{public}s", bundleName.c_str());
        return -1;
    }
    return bundleInfo.uid;
}

sptr<IWantSender> AbilityManagerService::GetWantSenderByUserId(const WantSenderInfo &wantSenderInfo,
    const sptr<IRemoteObject> &callerToken, int32_t uid, int32_t callerUid, int32_t callerUserId)
{
    bool isSpecifyUserId = wantSenderInfo.userId >= 0;
    std::string bundleName = "";
    if (!wantSenderInfo.allWants.empty()) {
        bundleName = wantSenderInfo.allWants.back().want.GetElement().GetBundleName();
    }
    bool isSACall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    bool isSystemApp = AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall();

    int32_t userId = -1;
    int32_t appUid = -1;
    int32_t appIndex = 0;
    if (isSACall || callerUserId == U0_USER_ID) {
        if (isSpecifyUserId) {
            userId = wantSenderInfo.userId;
            appIndex = wantSenderInfo.appIndex;
            appUid = (uid >= 0) ? uid : GetUidByCloneBundleInfo(bundleName, callerUid, userId, appIndex);
        } else if (uid >= 0) {
            if (DelayedSingleton<AppExecFwk::OsAccountManagerWrapper>::GetInstance()->
                GetOsAccountLocalIdFromUid(callerUid, userId) != 0) {
                TAG_LOGE(AAFwkTag::WANTAGENT, "getOsAccountLocalIdFromUid failed uid=%{public}d", callerUid);
                return nullptr;
            }
            appUid = uid;
        } else {
            userId = callerUserId;
            appUid = GetUidByCloneBundleInfo(bundleName, callerUid, userId, appIndex);
        }
    } else if (isSystemApp) {
        userId = isSpecifyUserId ? wantSenderInfo.userId : callerUserId;
        appUid = GetUidByCloneBundleInfo(bundleName, callerUid, userId, appIndex);
    } else {
        userId = callerUserId;
        appUid = callerUid;
    }
    std::shared_ptr<PendingWantManager> pendingWantManager = GetPendingWantManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(pendingWantManager, nullptr);
    if (!CheckSenderWantInfo(appUid, wantSenderInfo)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "check bundleName failed for appUid: %{public}d", appUid);
        return nullptr;
    }
    const_cast<WantSenderInfo&>(wantSenderInfo).userId = userId;
    TAG_LOGI(AAFwkTag::WANTAGENT, "bundleName: %{public}s, appIndex: %{public}d, isSystemApp: %{public}d, "
        "isSACall: %{public}d, userId: %{public}d, appUid: %{public}d", bundleName.c_str(), appIndex, isSystemApp,
        isSACall, userId, appUid);

    return pendingWantManager->GetWantSender(callerUid, appUid, isSystemApp, wantSenderInfo, callerToken, appIndex);
}

sptr<IWantSender> AbilityManagerService::GetWantSender(
    const WantSenderInfo &wantSenderInfo, const sptr<IRemoteObject> &callerToken,
    int32_t uid)
{
    TAG_LOGD(AAFwkTag::WANTAGENT, "called");
    int32_t userId = wantSenderInfo.userId;
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t callerUserId = callerUid / BASE_USER_RANGE;
    if (userId >= 0 || callerUserId == U0_USER_ID) {
        return GetWantSenderByUserId(wantSenderInfo, callerToken, uid, callerUid, callerUserId);
    }
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER_AND_RETURN(pendingWantManager, nullptr);

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, nullptr);

    int32_t bundleMgrResult = 0;
    if (DelayedSingleton<AppExecFwk::OsAccountManagerWrapper>::GetInstance()->
        GetOsAccountLocalIdFromUid(callerUid, userId) != 0) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "getOsAccountLocalIdFromUid failed uid=%{public}d", callerUid);
        return nullptr;
    }
    TAG_LOGD(AAFwkTag::WANTAGENT, "getOsAccountLocalIdFromUid userId: %{public}d", userId);
    //sa caller and has uid，no need find from bms.
    bool isSpecifyUidBySa = (uid != -1) && (AAFwk::PermissionVerification::GetInstance()->IsSACall());

    int32_t appUid = -1;
    int32_t appIndex = 0;
    std::string bundleName = "";
    if (!wantSenderInfo.allWants.empty()) {
        bundleName = wantSenderInfo.allWants.back().want.GetElement().GetBundleName();
    }
    if (!bundleName.empty()) {
        if (!isSpecifyUidBySa) {
            AppExecFwk::BundleInfo bundleInfo;
            MultiAppUtils::GetRunningMultiAppIndex(bundleName, callerUid, appIndex);
            bundleMgrResult = IN_PROCESS_CALL(bms->GetCloneBundleInfo(bundleName,
                static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_APPLICATION),
                appIndex, bundleInfo, userId));
            if (bundleMgrResult == ERR_OK) {
                appUid = bundleInfo.uid;
            }
        } else {
            appIndex = wantSenderInfo.appIndex;
            appUid = uid;
        }
        TAG_LOGD(AAFwkTag::WANTAGENT,
            "bundleName: %{public}s, uid: %{public}d, userId: %{public}d, appIndex: %{public}d", bundleName.c_str(),
            appUid, userId, appIndex);
    }
    if (!CheckSenderWantInfo(callerUid, wantSenderInfo)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "check bundleName failed");
        return nullptr;
    }

    bool isSystemApp = AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall();

    TAG_LOGI(AAFwkTag::WANTAGENT, "%{public}s#%{public}d, isSystemApp: %{public}d, "
        "userId: %{public}d", wantSenderInfo.bundleName.c_str(), appIndex, isSystemApp, userId);
    return pendingWantManager->GetWantSender(callerUid, appUid, isSystemApp, wantSenderInfo, callerToken, appIndex);
}

int AbilityManagerService::SendWantSender(sptr<IWantSender> target, SenderInfo &senderInfo)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "call");
    CHECK_POINTER_AND_RETURN(target, ERR_INVALID_VALUE);
    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return ERR_INVALID_VALUE;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, ERR_INVALID_VALUE);
    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, ERR_INVALID_VALUE);
    return pendingWantManager->SendWantSender(target, senderInfo);
}

int AbilityManagerService::SendLocalWantSender(const SenderInfo &senderInfo)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "call");
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER_AND_RETURN(pendingWantManager, ERR_INVALID_VALUE);
    if (!PermissionVerification::GetInstance()->VerifyPermissionByTokenId(senderInfo.tokenId,
        PermissionConstants::PERMISSION_TRIGGER_LOCAL_WANTAGENT)) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "no permission to trigger local wantagent");
        return CHECK_PERMISSION_FAILED;
    }
    return pendingWantManager->SendLocalWantSender(senderInfo);
}

void AbilityManagerService::CancelWantSender(const sptr<IWantSender> &sender)
{
    TAG_LOGD(AAFwkTag::WANTAGENT, "called");
    CHECK_POINTER(sender);

    sptr<IRemoteObject> obj = sender->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(sender.GetRefPtr());
    CHECK_POINTER(record);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER(pendingWantManager);
    TAG_LOGD(AAFwkTag::WANTAGENT, "getOsAccountLocalIdFromUid userId: %{public}d", userId);
    bool isSystemAppCall = AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall();

    pendingWantManager->CancelWantSender(isSystemAppCall, sender);
}

void AbilityManagerService::CancelWantSenderByFlags(const sptr<IWantSender> &sender, uint32_t flags)
{
    TAG_LOGD(AAFwkTag::WANTAGENT, "called");
    CHECK_POINTER(sender);
    sptr<IRemoteObject> obj = sender->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(sender.GetRefPtr());
    CHECK_POINTER(record);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER(bms);
    if (flags != 0 && record->GetKey() != nullptr &&
        (static_cast<uint32_t>(record->GetKey()->GetFlags()) & flags) == 0) {
        TAG_LOGI(AAFwkTag::WANTAGENT, "flags=%{public}u not match wantAgent flags=%{public}d",
                flags, record->GetKey()->GetFlags());
        return;
    }

    TAG_LOGI(AAFwkTag::WANTAGENT, "code=%{public}d cancel by flags=%{public}u",
        record->GetKey() != nullptr ? record->GetKey()->GetCode() : -1, flags);
    bool isSystemAppCall = AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall();
    pendingWantManager->CancelWantSender(isSystemAppCall, sender);
}

int AbilityManagerService::GetPendingWantUid(const sptr<IWantSender> &target)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "%{public}s:begin", __func__);
    if (target == nullptr) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "%s, target null", __func__);
        return -1;
    }
    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return -1;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, -1);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, -1);
    return pendingWantManager->GetPendingWantUid(target);
}

int AbilityManagerService::GetPendingWantUserId(const sptr<IWantSender> &target)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "%{public}s:begin", __func__);
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER_AND_RETURN(pendingWantManager, -1);
    if (target == nullptr) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "%s, target null", __func__);
        return -1;
    }
    return pendingWantManager->GetPendingWantUserId(target);
}

std::string AbilityManagerService::GetPendingWantBundleName(const sptr<IWantSender> &target)
{
    TAG_LOGD(AAFwkTag::WANTAGENT, "call");
    XCOLLIE_TIMER_DEFAULT(__PRETTY_FUNCTION__);
    CHECK_POINTER_AND_RETURN(target, "");

    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return "";
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, "");

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, "");
    return pendingWantManager->GetPendingWantBundleName(target);
}

int AbilityManagerService::GetPendingWantCode(const sptr<IWantSender> &target)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "%{public}s:begin", __func__);
    if (target == nullptr) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "%s, target null", __func__);
        return -1;
    }
    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return -1;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, -1);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, -1);
    return pendingWantManager->GetPendingWantCode(target);
}

int AbilityManagerService::GetPendingWantType(const sptr<IWantSender> &target)
{
    TAG_LOGD(AAFwkTag::WANTAGENT, "call");
    XCOLLIE_TIMER_DEFAULT(__PRETTY_FUNCTION__);
    if (target == nullptr) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "%s, target null", __func__);
        return -1;
    }
    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return -1;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, -1);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, -1);
    return pendingWantManager->GetPendingWantType(target);
}

void AbilityManagerService::RegisterCancelListener(const sptr<IWantSender> &sender,
    const sptr<IWantReceiver> &receiver)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "register cancel listener");
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER(pendingWantManager);
    CHECK_POINTER(sender);
    CHECK_POINTER(receiver);
    pendingWantManager->RegisterCancelListener(sender, receiver);
}

void AbilityManagerService::UnregisterCancelListener(
    const sptr<IWantSender> &sender, const sptr<IWantReceiver> &receiver)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "unregister cancel listener");
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER(pendingWantManager);
    CHECK_POINTER(sender);
    CHECK_POINTER(receiver);
    pendingWantManager->UnregisterCancelListener(sender, receiver);
}

int AbilityManagerService::GetPendingRequestWant(const sptr<IWantSender> &target, std::shared_ptr<Want> &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::WANTAGENT, "Get pending request want.");
    XCOLLIE_TIMER_DEFAULT(__PRETTY_FUNCTION__);
    CHECK_POINTER_AND_RETURN(target, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(want, ERR_INVALID_VALUE);
    sptr<IRemoteObject> obj = target->AsObject();
    if (!obj || obj->IsProxyObject()) {
        TAG_LOGE(AAFwkTag::WANTAGENT, "obj null or proxy obj");
        return -1;
    }
    sptr<PendingWantRecord> record = static_cast<PendingWantRecord*>(target.GetRefPtr());
    CHECK_POINTER_AND_RETURN(record, -1);

    int32_t userId = -1;
    if (record->GetKey() != nullptr) {
        userId = record->GetKey()->GetUserId();
    }
    std::shared_ptr<PendingWantManager> pendingWantManager;
    if (userId >= 0) {
        pendingWantManager = GetPendingWantManagerByUserId(userId);
    } else {
        pendingWantManager = GetCurrentPendingWantManager();
    }
    CHECK_POINTER_AND_RETURN(pendingWantManager, ERR_INVALID_VALUE);
    CHECK_CALLER_IS_SYSTEM_APP;
    return pendingWantManager->GetPendingRequestWant(target, want);
}

int AbilityManagerService::LockMissionForCleanup(int32_t missionId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request unlock for clean all, id=%{public}d", missionId);
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    return missionListManager->SetMissionLockedState(missionId, true);
}

int AbilityManagerService::UnlockMissionForCleanup(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request unlock for clean all, id=%{public}d", missionId);
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    return missionListManager->SetMissionLockedState(missionId, false);
}

void AbilityManagerService::SetLockedState(int32_t sessionId, bool lockedState)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request lock abilityRecord, sessionId :%{public}d", sessionId);
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard, no allowed");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    auto abilityRecord = uiAbilityManager->GetAbilityRecordsById(sessionId);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return;
    }
    abilityRecord->SetLockedState(lockedState);
}

int AbilityManagerService::RegisterMissionListener(const sptr<IMissionListener> &listener)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request registerMissionListener");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    return missionListManager->RegisterMissionListener(listener);
}

int AbilityManagerService::UnRegisterMissionListener(const sptr<IMissionListener> &listener)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request RegisterMissionListener ");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
    return missionListManager->UnRegisterMissionListener(listener);
}

int AbilityManagerService::GetMissionInfos(const std::string& deviceId, int32_t numMax,
    std::vector<MissionInfo> &missionInfos)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request getMissionInfos");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (CheckIsRemote(deviceId)) {
        return GetRemoteMissionInfos(deviceId, numMax, missionInfos);
    }

    return missionListManager->GetMissionInfos(numMax, missionInfos);
}

int AbilityManagerService::GetRemoteMissionInfos(const std::string& deviceId, int32_t numMax,
    std::vector<MissionInfo> &missionInfos)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "getRemoteMissionInfos");
    DistributedClient dmsClient;
    int result = dmsClient.GetMissionInfos(deviceId, numMax, missionInfos);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getRemoteMissionInfos failed, result=%{public}d", result);
        return result;
    }
    return ERR_OK;
}

int AbilityManagerService::GetMissionInfo(const std::string& deviceId, int32_t missionId,
    MissionInfo &missionInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request getMissionInfo, missionId:%{public}d", missionId);
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (CheckIsRemote(deviceId)) {
        return GetRemoteMissionInfo(deviceId, missionId, missionInfo);
    }

    return missionListManager->GetMissionInfo(missionId, missionInfo);
}

int AbilityManagerService::GetRemoteMissionInfo(const std::string& deviceId, int32_t missionId,
    MissionInfo &missionInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "getMissionInfoFromDms");
    std::vector<MissionInfo> missionVector;
    int result = GetRemoteMissionInfos(deviceId, MAX_NUMBER_OF_DISTRIBUTED_MISSIONS, missionVector);
    if (result != ERR_OK) {
        return result;
    }
    for (auto iter = missionVector.begin(); iter != missionVector.end(); iter++) {
        if (iter->id == missionId) {
            missionInfo = *iter;
            return ERR_OK;
        }
    }
    TAG_LOGW(AAFwkTag::ABILITYMGR, "missionId not found");
    return ERR_INVALID_VALUE;
}

int AbilityManagerService::CleanMission(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request cleanMission, missionId:%{public}d", missionId);
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    return missionListManager->ClearMission(missionId);
}

int AbilityManagerService::CleanAllMissions()
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request cleanAllMissions");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    Want want;
    want.SetElementName(AbilityConfig::LAUNCHER_BUNDLE_NAME, AbilityConfig::LAUNCHER_ABILITY_NAME);
    if (!IsAbilityControllerStart(want, AbilityConfig::LAUNCHER_BUNDLE_NAME)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart failed:%{public}s", want.GetBundle().c_str());
        return ERR_WOULD_BLOCK;
    }

    return missionListManager->ClearAllMissions();
}

int AbilityManagerService::MoveMissionToFront(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request MoveMissionToFront, missionId:%{public}d", missionId);
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (!IsAbilityControllerStartById(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart false");
        return ERR_WOULD_BLOCK;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->MoveMissionToFront(missionId);
    }

    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    return missionListManager->MoveMissionToFront(missionId);
}

int AbilityManagerService::MoveMissionToFront(int32_t missionId, const StartOptions &startOptions)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "request MoveMissionToFront, missionId:%{public}d", missionId);
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    if (!IsAbilityControllerStartById(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart false");
        return ERR_WOULD_BLOCK;
    }

    auto options = std::make_shared<StartOptions>(startOptions);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->MoveMissionToFront(missionId, options);
    }

    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    return missionListManager->MoveMissionToFront(missionId, options);
}

int AbilityManagerService::MoveMissionsToForeground(const std::vector<int32_t>& missionIds, int32_t topMissionId)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
#ifdef SUPPORT_SCREEN
    if (GetWMSHandler()) {
        auto ret = GetWMSHandler()->MoveMissionsToForeground(missionIds, topMissionId);
        if (ret) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "moveMissionsToForeground failed, missiondIds may invalid");
            return ERR_INVALID_VALUE;
        } else {
            return NO_ERROR;
        }
    }
#endif // SUPPORT_SCREEN
    return ERR_NO_INIT;
}

int AbilityManagerService::MoveMissionsToBackground(const std::vector<int32_t>& missionIds,
    std::vector<int32_t>& result)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }
#ifdef SUPPORT_SCREEN
    if (GetWMSHandler()) {
        auto ret = GetWMSHandler()->MoveMissionsToBackground(missionIds, result);
        if (ret) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "moveMissionsToBackground failed, missiondIds may invalid");
            return ERR_INVALID_VALUE;
        } else {
            return NO_ERROR;
        }
    }
#endif // SUPPORT_SCREEN
    return ERR_NO_INIT;
}

int32_t AbilityManagerService::GetMissionIdByToken(const sptr<IRemoteObject> &token)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "request GetMissionIdByToken.");
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_INVALID_VALUE;
    }
    if (!JudgeSelfCalled(abilityRecord) && !CheckCallerIsDmsProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_INVALID_VALUE;
    }
    return GetMissionIdByAbilityTokenInner(token);
}

bool AbilityManagerService::IsAbilityControllerStartById(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto missionListWrap = GetMissionListWrap();
    if (missionListWrap == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "missionListWrap null");
        return true;
    }
    InnerMissionInfo innerMissionInfo;
    int getMission = missionListWrap->GetInnerMissionInfoById(missionId, innerMissionInfo);
    if (getMission != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "cannot find mission info:%{public}d", missionId);
        return true;
    }
    if (!IsAbilityControllerStart(innerMissionInfo.missionInfo.want, innerMissionInfo.missionInfo.want.GetBundle())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart failed:%{public}s",
            innerMissionInfo.missionInfo.want.GetBundle().c_str());
        return false;
    }
    return true;
}

bool AbilityManagerService::GenerateDataAbilityRequestByUri(const std::string& dataAbilityUri,
    AbilityRequest &abilityRequest, sptr<IRemoteObject> callerToken, int32_t userId)
{
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, false);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "dataAbilityUri: %{public}s, userId: %{public}d", dataAbilityUri.c_str(), userId);
    bool queryResult = IN_PROCESS_CALL(bms->QueryAbilityInfoByUri(dataAbilityUri, userId, abilityRequest.abilityInfo));
    if (!queryResult || abilityRequest.abilityInfo.name.empty() || abilityRequest.abilityInfo.bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid ability info acquiring");
        return false;
    }
    abilityRequest.callerToken = callerToken;
    return true;
}

sptr<IAbilityScheduler> AbilityManagerService::AcquireDataAbility(
    const Uri &uri, bool tryBind, const sptr<IRemoteObject> &callerToken)
{
    auto localUri(uri);
    if (localUri.GetScheme() != AbilityConfig::SCHEME_DATA_ABILITY) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "acquire data ability invalid uri scheme");
        return nullptr;
    }
    std::vector<std::string> pathSegments;
    localUri.GetPathSegments(pathSegments);
    if (pathSegments.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "acquire data ability invalid uri path");
        return nullptr;
    }

    auto userId = GetValidUserId(INVALID_USER_ID);
    AbilityRequest abilityRequest;
    if (!GenerateDataAbilityRequestByUri(localUri.ToString(), abilityRequest, callerToken, userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate data ability request failed");
        return nullptr;
    }

    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    if (!isSaCall && CheckCallDataAbilityPermission(abilityRequest, isShellCall, isSaCall) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid ability request info acquiring");
        return nullptr;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "Query data ability info: %{public}s|%{public}s|%{public}s",
        abilityRequest.appInfo.name.c_str(), abilityRequest.appInfo.bundleName.c_str(),
        abilityRequest.abilityInfo.name.c_str());

    if (CheckStaticCfgPermission(abilityRequest, false, -1, true, isSaCall) !=
        AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission fail");
        return nullptr;
    }

    if (!VerificationAllToken(callerToken)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "verificationAllToken fail");
        return nullptr;
    }

    if (abilityRequest.abilityInfo.applicationInfo.singleton) {
        userId = U0_USER_ID;
    }

    std::shared_ptr<DataAbilityManager> dataAbilityManager = GetDataAbilityManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(dataAbilityManager, nullptr);
    ReportEventToRSS(abilityRequest.abilityInfo, callerToken);
    bool isNotHap = isSaCall || isShellCall;
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    return dataAbilityManager->Acquire(abilityRequest, tryBind, callerToken, isNotHap);
}

int AbilityManagerService::ReleaseDataAbility(
    sptr<IAbilityScheduler> dataAbilityScheduler, const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called");
    if (!dataAbilityScheduler || !callerToken) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "dataAbilitySchedule or callerToken null");
        return ERR_INVALID_VALUE;
    }

    std::shared_ptr<DataAbilityManager> dataAbilityManager = GetDataAbilityManager(dataAbilityScheduler);
    if (!dataAbilityManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "dataAbilityScheduler absent");
        return ERR_INVALID_VALUE;
    }

    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    bool isNotHap = isSaCall || isShellCall;
    return dataAbilityManager->Release(dataAbilityScheduler, callerToken, isNotHap);
}

int AbilityManagerService::AttachAbilityThread(
    const sptr<IAbilityScheduler> &scheduler, const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "AttachAbilityThread");
    CHECK_POINTER_AND_RETURN(scheduler, ERR_INVALID_VALUE);
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled() && !VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto abilityInfo = abilityRecord->GetAbilityInfo();
    auto type = abilityInfo.type;
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s/%{public}s", abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());
    // force timeout ability for test
    if (IsNeedTimeoutForTest(abilityInfo.name, AbilityRecord::ConvertAbilityState(AbilityState::INITIAL))) {
        TAG_LOGW(AAFwkTag::ABILITYMGR,
            "force timeout ability, state:INITIAL, ability:%{public}s", abilityInfo.name.c_str());
        return ERR_OK;
    }
    if (type == AppExecFwk::AbilityType::SERVICE || type == AppExecFwk::AbilityType::EXTENSION) {
        auto connectManager = GetConnectManagerByUserId(userId, abilityInfo.extensionAbilityType);
        if (!connectManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", userId);
            return ERR_INVALID_VALUE;
        }
        return connectManager->AttachAbilityThreadLocked(scheduler, token);
    } else if (type == AppExecFwk::AbilityType::DATA) {
        auto dataAbilityManager = GetDataAbilityManagerByUserId(userId);
        if (!dataAbilityManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "dataAbilityManager null userId=%{public}d", userId);
            return ERR_INVALID_VALUE;
        }
        return dataAbilityManager->AttachAbilityThread(scheduler, token);
    } else {
        std::string entry = "AbilityManagerService::AttachAbilityThread; the end of load lifecycle.";
        FreezeUtil::GetInstance().AddLifecycleEvent(token, entry);
        int32_t ownerMissionUserId = abilityRecord->GetOwnerMissionUserId();
        if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
            auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerMissionUserId);
            CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
            return uiAbilityManager->AttachAbilityThread(scheduler, token);
        }
        auto missionListManager = GetMissionListManagerByUserId(ownerMissionUserId);
        CHECK_POINTER_AND_RETURN(missionListManager, ERR_INVALID_VALUE);
        return missionListManager->AttachAbilityThread(scheduler, token);
    }
}

void AbilityManagerService::DumpSysInner(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }

    DumpSysMissionListInner(args, info, isClient, isUserID, userId);
    DumpSysStateInner(args, info, isClient, isUserID, userId);
    DumpSysPendingInner(args, info, isClient, isUserID, userId);
    DumpSysProcess(args, info, isClient, isUserID, userId);
}

void AbilityManagerService::DumpSysMissionListInner(
    const std::string &args, std::vector<std::string> &info, bool isClient, bool isUserID, int userId)
{
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        DumpSysMissionListInnerBySCB(args, info, isClient, isUserID, userId);
        return;
    }
    std::shared_ptr<MissionListManagerInterface> targetManager;
    if (isUserID) {
        auto missionListManager = GetMissionListManagerByUserId(userId);
        if (missionListManager == nullptr) {
            info.push_back("error: No user found.");
            return;
        }
        targetManager = missionListManager;
    } else {
        targetManager = GetCurrentMissionListManager();
    }

    CHECK_POINTER(targetManager);

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }

    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        targetManager->DumpMissionList(info, isClient, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        targetManager->DumpMissionList(info, isClient);
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpSysMissionListInnerBySCB(
    const std::string &args, std::vector<std::string> &info, bool isClient, bool isUserID, int userId)
{
    if (!isUserID) {
        userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    }

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }

    auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
    CHECK_POINTER(uiAbilityManager);
    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        uiAbilityManager->DumpMissionList(info, isClient, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        uiAbilityManager->DumpMissionList(info, isClient);
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpSysAbilityInner(
    const std::string &args, std::vector<std::string> &info, bool isClient, bool isUserID, int userId)
{
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        DumpSysAbilityInnerBySCB(args, info, isClient, isUserID, userId);
        return;
    }
    std::shared_ptr<MissionListManagerInterface> targetManager;
    if (isUserID) {
        auto missionListManager = GetMissionListManagerByUserId(userId);
        if (missionListManager == nullptr) {
            info.push_back("error: No user found.");
            return;
        }
        targetManager = missionListManager;
    } else {
        targetManager = GetCurrentMissionListManager();
    }

    CHECK_POINTER(targetManager);

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() >= MIN_DUMP_ARGUMENT_NUM) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "argList=%{public}s", argList[1].c_str());
        std::vector<std::string> params(argList.begin() + MIN_DUMP_ARGUMENT_NUM, argList.end());
        try {
            auto abilityId = static_cast<int32_t>(std::stoi(argList[1]));
            targetManager->DumpMissionListByRecordId(info, isClient, abilityId, params);
        } catch (...) {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "stoi(%{public}s) failed", argList[1].c_str());
            info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
        }
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpSysAbilityInnerBySCB(
    const std::string &args, std::vector<std::string> &info, bool isClient, bool isUserID, int userId)
{
    if (!isUserID) {
        userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    }

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() >= MIN_DUMP_ARGUMENT_NUM) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "argList=%{public}s", argList[1].c_str());
        std::vector<std::string> params(argList.begin() + MIN_DUMP_ARGUMENT_NUM, argList.end());
        try {
            auto abilityId = static_cast<int32_t>(std::stoi(argList[1]));
            auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
            CHECK_POINTER(uiAbilityManager);
            uiAbilityManager->DumpMissionListByRecordId(info, isClient, abilityId, params);
        } catch (...) {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "stoi(%{public}s) failed", argList[1].c_str());
            info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
        }
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpSysStateInner(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "dumpSysStateInner begin:%{public}s", args.c_str());
    AbilityConnectManager::ServiceMapType serviceMap;
    auto dumpUserId = isUserID ? userId : AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    auto ret = GetServiceMapByUserId(serviceMap, dumpUserId);

    if (ret != ERR_OK) {
        if (isUserID) {
            info.push_back("error: No user found.");
        }
        return;
    }

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }

    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        AbilityConnectManager::DumpState(serviceMap, info, isClient, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        AbilityConnectManager::DumpState(serviceMap, info, isClient);
    } else {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "uri=%{public}s", argList[1].c_str());
        std::vector<std::string> params(argList.begin() + MIN_DUMP_ARGUMENT_NUM, argList.end());
        AbilityConnectManager::DumpStateByUri(serviceMap, info, isClient, argList[1], params);
    }
}

void AbilityManagerService::DumpSysPendingInner(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    std::shared_ptr<PendingWantManager> targetManager;
    if (isUserID) {
        auto pendingWantManager = GetPendingWantManagerByUserId(userId);
        if (pendingWantManager == nullptr) {
            info.push_back("error: No user found.");
            return;
        }
        targetManager = pendingWantManager;
    } else {
        targetManager = GetCurrentPendingWantManager();
    }

    CHECK_POINTER(targetManager);

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }

    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        targetManager->DumpByRecordId(info, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        targetManager->Dump(info);
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpSysProcess(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    std::vector<AppExecFwk::RunningProcessInfo> processInfos;
    int ret = 0;
    if (isUserID) {
        ret = GetProcessRunningInfosByUserId(processInfos, userId);
    } else {
        ret = GetProcessRunningInfos(processInfos);
    }

    if (ret != ERR_OK || processInfos.size() == 0) {
        return;
    }

    std::string dumpInfo = "  AppRunningRecords:";
    info.push_back(dumpInfo);
    auto processInfoID = 0;
    auto hasProcessName = (argList.size() == MIN_DUMP_ARGUMENT_NUM ? true : false);
    for (const auto& processInfo : processInfos) {
        if (hasProcessName && argList[1] != processInfo.processName_) {
            continue;
        }

        dumpInfo = "    AppRunningRecord ID #" + std::to_string(processInfoID);
        processInfoID++;
        info.push_back(dumpInfo);
        dumpInfo = "      process name [" + processInfo.processName_ + "]";
        info.push_back(dumpInfo);
        dumpInfo = "      pid #" + std::to_string(processInfo.pid_) +
            "  uid #" + std::to_string(processInfo.uid_);
        info.push_back(dumpInfo);
        auto appState = static_cast<AppState>(processInfo.state_);
        dumpInfo = "      state #" + DelayedSingleton<AppScheduler>::GetInstance()->ConvertAppState(appState);
        info.push_back(dumpInfo);
        DumpUIExtensionRootHostRunningInfos(processInfo.pid_, info);
        DumpUIExtensionProviderRunningInfos(processInfo.pid_, info);
    }
}

void AbilityManagerService::DumpUIExtensionRootHostRunningInfos(pid_t pid, std::vector<std::string> &info)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "get appMgr failed");
        return;
    }

    std::vector<pid_t> hostPids;
    auto ret = IN_PROCESS_CALL(appMgr->GetAllUIExtensionRootHostPid(pid, hostPids));
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get root host process info faild");
        return;
    }

    if (hostPids.size() == 0) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "There's no ui extenson root host of pid %{public}d.", pid);
        return;
    }

    std::string temp;
    for (size_t i = 0; i < hostPids.size(); i++) {
        temp = "      root caller #" + std::to_string(i);
        info.push_back(temp);
        temp = "        pid #" + std::to_string(hostPids[i]);
        info.push_back(temp);
    }
}

void AbilityManagerService::DumpUIExtensionProviderRunningInfos(pid_t hostPid, std::vector<std::string> &info)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "get appMgr failed");
        return;
    }

    std::vector<pid_t> providerPids;
    auto ret = IN_PROCESS_CALL(appMgr->GetAllUIExtensionProviderPid(hostPid, providerPids));
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get process info failed");
        return;
    }

    if (providerPids.size() == 0) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "There's no ui extension provider of pid %{public}d.", hostPid);
        return;
    }

    std::string temp;
    for (size_t i = 0; i < providerPids.size(); i++) {
        temp = "      uiextension provider #" + std::to_string(i);
        info.push_back(temp);
        temp = "        pid #" + std::to_string(providerPids[i]);
        info.push_back(temp);
    }
}

void AbilityManagerService::DataDumpSysStateInner(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    std::shared_ptr<DataAbilityManager> targetManager;
    if (isUserID) {
        auto dataAbilityManager = GetDataAbilityManagerByUserId(userId);
        if (dataAbilityManager == nullptr) {
            info.push_back("error: No user found.");
            return;
        }
        targetManager = dataAbilityManager;
    } else {
        targetManager = GetCurrentDataAbilityManager();
    }

    CHECK_POINTER(targetManager);

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        targetManager->DumpSysState(info, isClient, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        targetManager->DumpSysState(info, isClient);
    } else {
        info.emplace_back("error: invalid argument, please see 'hidumper -s AbilityManagerService -a '-h''.");
    }
}

void AbilityManagerService::DumpInner(const std::string &args, std::vector<std::string> &info)
{
    auto userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->Dump(info);
        return;
    }

    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (missionListManager) {
        missionListManager->Dump(info);
    }
}

void AbilityManagerService::DumpMissionListInner(const std::string &args, std::vector<std::string> &info)
{
    auto userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->DumpMissionList(info, false, " ");
        return;
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (missionListManager) {
        missionListManager->DumpMissionList(info, false, "");
    }
}

void AbilityManagerService::DumpMissionInfosInner(const std::string &args, std::vector<std::string> &info)
{
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
#ifdef SUPPORT_GRAPHICS
        Rosen::WindowManager::GetInstance().DumpSessionAll(info);
#endif // SUPPORT_GRAPHICS
        return;
    }
    auto missionListManager = GetCurrentMissionListManager();
    if (missionListManager) {
        missionListManager->DumpMissionInfos(info);
    }
}

void AbilityManagerService::DumpMissionInner(const std::string &args, std::vector<std::string> &info)
{
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        info.push_back("error: invalid argument, please see 'ability dump -h'.");
        return;
    }
    int missionId = DEFAULT_INVAL_VALUE;
    (void)StrToInt(argList[1], missionId);

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
#ifdef SUPPORT_GRAPHICS
        Rosen::WindowManager::GetInstance().DumpSessionWithId(missionId, info);
#endif // SUPPORT_GRAPHICS
        return;
    }

    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_LOG(missionListManager, "Current mission manager not init.");
    missionListManager->DumpMission(missionId, info);
}

void AbilityManagerService::DumpStateInner(const std::string &args, std::vector<std::string> &info)
{
    auto userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    AbilityConnectManager::ServiceMapType serviceMap;
    auto ret = GetServiceMapByUserId(serviceMap, userId);
    if (ret != ERR_OK) {
        return;
    }

    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        AbilityConnectManager::DumpState(serviceMap, info, false, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        AbilityConnectManager::DumpState(serviceMap, info, false);
    } else {
        info.emplace_back("error: invalid argument, please see 'ability dump -h'.");
    }
}

void AbilityManagerService::DataDumpStateInner(const std::string &args, std::vector<std::string> &info)
{
    auto dataAbilityManager = GetCurrentDataAbilityManager();
    CHECK_POINTER(dataAbilityManager);
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    if (argList.size() == MIN_DUMP_ARGUMENT_NUM) {
        dataAbilityManager->DumpState(info, argList[1]);
    } else if (argList.size() < MIN_DUMP_ARGUMENT_NUM) {
        dataAbilityManager->DumpState(info);
    } else {
        info.emplace_back("error: invalid argument, please see 'ability dump -h'.");
    }
}

void AbilityManagerService::DumpState(const std::string &args, std::vector<std::string> &info)
{
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    auto isHidumperServiceCall = (IPCSkeleton::GetCallingUid() == HIDUMPER_SERVICE_UID);
    if (!isShellCall && !isHidumperServiceCall) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return;
    }
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    auto key = DumpUtils::DumpMap(argList[0]);
    if (!key.first) {
        return;
    }
    switch (key.second) {
        case DumpUtils::KEY_DUMP_SERVICE:
            DumpStateInner(args, info);
            break;
        case DumpUtils::KEY_DUMP_DATA:
            DataDumpStateInner(args, info);
            break;
        case DumpUtils::KEY_DUMP_ALL:
            DumpInner(args, info);
            break;
        case DumpUtils::KEY_DUMP_MISSION:
            DumpMissionInner(args, info);
            break;
        case DumpUtils::KEY_DUMP_MISSION_LIST:
            DumpMissionListInner(args, info);
            break;
        case DumpUtils::KEY_DUMP_MISSION_INFOS:
            DumpMissionInfosInner(args, info);
            break;
        default:
            info.push_back("error: invalid argument, please see 'ability dump -h'.");
            break;
    }
}

void AbilityManagerService::DumpSysState(
    const std::string& args, std::vector<std::string>& info, bool isClient, bool isUserID, int userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s begin", __func__);
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    auto isHidumperServiceCall = (IPCSkeleton::GetCallingUid() == HIDUMPER_SERVICE_UID);
    if (!isShellCall && !isHidumperServiceCall) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return;
    }
    std::vector<std::string> argList;
    SplitStr(args, " ", argList);
    if (argList.empty()) {
        return;
    }
    auto key = DumpUtils::DumpsysMap(argList[0]);
    if (!key.first) {
        return;
    }
    switch (key.second) {
        case DumpUtils::KEY_DUMP_SYS_ALL:
            DumpSysInner(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_SERVICE:
            DumpSysStateInner(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_PENDING:
            DumpSysPendingInner(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_PROCESS:
            DumpSysProcess(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_DATA:
            DataDumpSysStateInner(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_MISSION_LIST:
            DumpSysMissionListInner(args, info, isClient, isUserID, userId);
            break;
        case DumpUtils::KEY_DUMP_SYS_ABILITY:
            DumpSysAbilityInner(args, info, isClient, isUserID, userId);
            break;
        default:
            info.push_back("error: invalid argument, please see 'ability dump -h'.");
            break;
    }
}

int AbilityManagerService::AbilityTransitionDone(const sptr<IRemoteObject> &token, int state, const PacMap &saveData)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled() && !VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN_LOG(abilityRecord, ERR_INVALID_VALUE, "Ability record is nullptr.");
    auto callerPid = IPCSkeleton::GetCallingPid();
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "AbilityTransitionDone, ability:%{public}s/%{public}s, state:%{public}d, callerPid:%{public}d",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(), state, callerPid);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto abilityInfo = abilityRecord->GetAbilityInfo();
    auto type = abilityInfo.type;
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    // force timeout ability for test
    int targetState = AbilityRecord::ConvertLifeCycleToAbilityState(static_cast<AbilityLifeCycleState>(state));
    bool isTerminate = abilityRecord->IsAbilityState(AbilityState::TERMINATING) && targetState == AbilityState::INITIAL;
    std::string tempState = isTerminate ? AbilityRecord::ConvertAbilityState(AbilityState::TERMINATING) :
        AbilityRecord::ConvertAbilityState(static_cast<AbilityState>(targetState));
    if (IsNeedTimeoutForTest(abilityInfo.name, tempState)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "force timeout ability, state:%{public}s, ability:%{public}s",
            tempState.c_str(),
            abilityInfo.name.c_str());
        return ERR_OK;
    }
    if (type == AppExecFwk::AbilityType::SERVICE || type == AppExecFwk::AbilityType::EXTENSION) {
        auto connectManager = GetConnectManagerByUserId(userId, abilityInfo.extensionAbilityType);
        if (!connectManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", userId);
            return ERR_INVALID_VALUE;
        }
        return connectManager->AbilityTransitionDone(token, state);
    }
    if (type == AppExecFwk::AbilityType::DATA) {
        auto dataAbilityManager = GetDataAbilityManagerByUserId(userId);
        if (!dataAbilityManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "dataAbilityManager null userId=%{public}d", userId);
            return ERR_INVALID_VALUE;
        }
        return dataAbilityManager->AbilityTransitionDone(token, state);
    }

    if (targetState == AbilityState::BACKGROUND) {
        std::string entry = "AbilityManagerService::AbilityTransitionDone; the end of background lifecycle.";
        FreezeUtil::GetInstance().AddLifecycleEvent(token, entry);
    } else if (targetState != AbilityState::INITIAL) {
        std::string entry = "AbilityManagerService::AbilityTransitionDone; the end of foreground lifecycle.";
        FreezeUtil::GetInstance().AddLifecycleEvent(token, entry);
    }

    int32_t ownerMissionUserId = abilityRecord->GetOwnerMissionUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerMissionUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->AbilityTransactionDone(token, state, saveData);
    } else {
        auto missionListManager = GetMissionListManagerByUserId(ownerMissionUserId);
        if (!missionListManager) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId=%{public}d", ownerMissionUserId);
            return ERR_INVALID_VALUE;
        }
        return missionListManager->AbilityTransactionDone(token, state, saveData);
    }
}

int AbilityManagerService::AbilityWindowConfigTransitionDone(
    const sptr<IRemoteObject> &token, const WindowConfig &windowConfig)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled() && !VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN_LOG(abilityRecord, ERR_INVALID_VALUE, "ability record null.");
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "ability:%{public}s/%{public}s",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());
    auto abilityInfo = abilityRecord->GetAbilityInfo();
    auto type = abilityInfo.extensionAbilityType;
    if (type != AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid type");
        return ERR_INVALID_VALUE;
    }
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto connectManager = GetCommonExtensionManagerByUserId(userId);
    if(!connectManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->AbilityWindowConfigTransactionDone(token, windowConfig);
}

int AbilityManagerService::ScheduleConnectAbilityDone(
    const sptr<IRemoteObject> &token, const sptr<IRemoteObject> &remoteObject)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "called");
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::SERVICE && type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "ability failed, target ability not service");
        return TARGET_ABILITY_NOT_SERVICE;
    }
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId=%{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->ScheduleConnectAbilityDoneLocked(token, remoteObject);
}

int AbilityManagerService::ScheduleDisconnectAbilityDone(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "call");
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::SERVICE && type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "ability failed, target ability not service");
        return TARGET_ABILITY_NOT_SERVICE;
    }
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId=%{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->ScheduleDisconnectAbilityDoneLocked(token);
}

int AbilityManagerService::ScheduleCommandAbilityDone(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::SERVICE_EXT, "Schedule command ability done.");
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }
    // force timeout ability for test
    if (IsNeedTimeoutForTest(abilityRecord->GetAbilityInfo().name, std::string("COMMAND"))) {
        TAG_LOGW(AAFwkTag::SERVICE_EXT, "force timeout ability, state:COMMAND, ability: %{public}s",
            abilityRecord->GetAbilityInfo().name.c_str());
        return ERR_OK;
    }
    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::SERVICE && type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "failed, target ability not service");
        return TARGET_ABILITY_NOT_SERVICE;
    }
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::SERVICE_EXT, "connectManager null userId = %{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->ScheduleCommandAbilityDoneLocked(token);
}

int AbilityManagerService::ScheduleCommandAbilityWindowDone(
    const sptr<IRemoteObject> &token,
    const sptr<SessionInfo> &sessionInfo,
    WindowCommand winCmd,
    AbilityCommand abilityCmd)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "enter.");
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    if (!UIExtensionWrapper::IsUIExtension(abilityRecord->GetAbilityInfo().extensionAbilityType)
        && !UIExtensionWrapper::IsWindowExtension(abilityRecord->GetAbilityInfo().extensionAbilityType)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability not ui or window extension");
        return ERR_INVALID_VALUE;
    }
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;
    auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
    if (!connectManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", userId);
        return ERR_INVALID_VALUE;
    }
    return connectManager->ScheduleCommandAbilityWindowDone(token, sessionInfo, winCmd, abilityCmd);
}

void AbilityManagerService::OnAbilityRequestDone(const sptr<IRemoteObject> &token, const int32_t state)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER(abilityRecord);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "OnAbilityRequestDone %{public}s-%{public}s state:%{public}d",
        abilityRecord->GetAbilityInfo().bundleName.c_str(), abilityRecord->GetAbilityInfo().name.c_str(), state);
    auto userId = abilityRecord->GetApplicationInfo().uid / BASE_USER_RANGE;

    auto type = abilityRecord->GetAbilityInfo().type;
    switch (type) {
        case AppExecFwk::AbilityType::DATA: {
            auto dataAbilityManager = GetDataAbilityManagerByUserId(userId);
            if (!dataAbilityManager) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "dataAbilityManager null userId=%{public}d", userId);
                return;
            }
            dataAbilityManager->OnAbilityRequestDone(token, state);
            break;
        }
        case AppExecFwk::AbilityType::SERVICE:
        case AppExecFwk::AbilityType::EXTENSION: {
            auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
            if (!connectManager) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", userId);
                return;
            }
            connectManager->OnAbilityRequestDone(token, state);
            break;
        }
        default: {
            int32_t ownerUserId = abilityRecord->GetOwnerMissionUserId();
            if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
                auto uiAbilityManager = GetUIAbilityManagerByUserId(ownerUserId);
                CHECK_POINTER(uiAbilityManager);
                uiAbilityManager->OnAbilityRequestDone(token, state);
            } else {
                auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
                if (!missionListManager) {
                    TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId=%{public}d", ownerUserId);
                    return;
                }
                missionListManager->OnAbilityRequestDone(token, state);
            }
            break;
        }
    }
}

void AbilityManagerService::OnAppStateChanged(const AppInfo &info)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    auto userId = info.userId;
    if (userId == U0_USER_ID || userId == U1_USER_ID) {
        userId = AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
    }
    if (info.state == AppState::TERMINATED) {
        DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->OnInsightAppDied(info.bundleName);
    }

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER_LOG(commonExtensionManager, "commonExtensionManager not init.");
    commonExtensionManager->OnAppStateChanged(info);
    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER_LOG(uiExtensionAbilityManager, "uiExtensionAbilityManager not init.");
    uiExtensionAbilityManager->OnAppStateChanged(info);

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnAppStateChanged(info);
    } else {
        auto missionListManager = GetMissionListManagerByUserId(userId);
        CHECK_POINTER_LOG(missionListManager, "Current mission list manager not init.");
        missionListManager->OnAppStateChanged(info);
    }
    auto dataAbilityManager = GetCurrentDataAbilityManager();
    CHECK_POINTER(dataAbilityManager);
    dataAbilityManager->OnAppStateChanged(info);

    auto residentProcessMgr = DelayedSingleton<ResidentProcessManager>::GetInstance();
    CHECK_POINTER(residentProcessMgr);
    residentProcessMgr->OnAppStateChanged(info);

    if (system::GetBoolParameter(PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED, false)) {
        KeepAliveProcessManager::GetInstance().OnAppStateChanged(info);
    }
    KioskManager::GetInstance().OnAppStop(info);
}

std::shared_ptr<AbilityEventHandler> AbilityManagerService::GetEventHandler()
{
    return eventHandler_;
}

#ifndef DISABLE_LAUNCHER
int AbilityManagerService::StartHighestPriorityAbility(int32_t userId, uint64_t displayId, bool isBoot,
    bool isAppRecovery)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, BMS_NOT_CONNECTED);

    /* Query the highest priority ability or extension ability, and start it. usually, it is OOBE or launcher */
    Want want;
    want.AddEntity(HIGHEST_PRIORITY_ABILITY_ENTITY);
    AppExecFwk::AbilityInfo abilityInfo;
    AppExecFwk::ExtensionAbilityInfo extensionAbilityInfo;
    int attemptNums = 0;
    int64_t startTime = AbilityRuntime::TimeUtil::CurrentTimeMillis();
    int64_t bmsCntTime = 0;
    int64_t queryTime = 0;
    while (true) {
        bms->PreConnect();
        bmsCntTime = AbilityRuntime::TimeUtil::CurrentTimeMillis();
        if (IN_PROCESS_CALL(bms->ImplicitQueryInfoByPriority(want,
            AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_DEFAULT, userId,
            abilityInfo, extensionAbilityInfo))) {
            break;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "waiting query highest priority ability info completed");
        ++attemptNums;
        if (!isBoot && attemptNums > SWITCH_ACCOUNT_TRY) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "query highest priority ability failed");
            return RESOLVE_ABILITY_ERR;
        }
        usleep(SHORT_REPOLL_TIME_MICRO_SECONDS);
    }
    queryTime = AbilityRuntime::TimeUtil::CurrentTimeMillis();

    if (abilityInfo.name.empty() && extensionAbilityInfo.name.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "query highest priority ability failed");
        return RESOLVE_ABILITY_ERR;
    }

    Want abilityWant; // donot use 'want' here, because the entity of 'want' is not empty
    if (!abilityInfo.name.empty()) {
        /* highest priority ability */
        TAG_LOGI(AAFwkTag::ABILITYMGR, "start highest priority ability bundleName:%{public}s, ability:%{public}s",
            abilityInfo.bundleName.c_str(), abilityInfo.name.c_str());
        abilityWant.SetElementName(abilityInfo.bundleName, abilityInfo.name);
    } else {
        /* highest priority extension ability */
        TAG_LOGI(AAFwkTag::ABILITYMGR,
            "start highest priority extension ability bundleName:%{public}s, ability:%{public}s,"
            "BMScntTime:%{public}" PRId64 " ms, queryTime:%{public}" PRId64 " ms",
            extensionAbilityInfo.bundleName.c_str(), extensionAbilityInfo.name.c_str(),
            bmsCntTime - startTime, queryTime - bmsCntTime);
        abilityWant.SetElementName(extensionAbilityInfo.bundleName, extensionAbilityInfo.name);
    }

#ifdef SUPPORT_GRAPHICS
    abilityWant.SetParam(NEED_STARTINGWINDOW, false);
    abilityWant.SetParam(Want::PARAM_RESV_DISPLAY_ID, static_cast<int32_t>(displayId));
    // wait BOOT_ANIMATION_STARTED to start LAUNCHER
    WaitBootAnimationStart();
#endif
    if (isAppRecovery) {
        abilityWant.SetParam("ohos.app.logout_recovery", true);
    }
    /* note: OOBE APP need disable itself, otherwise, it will be started when restart system everytime */
    return StartAbility(abilityWant, userId, DEFAULT_INVAL_VALUE);
}
#endif
int AbilityManagerService::GenerateAbilityRequest(const Want &want, int requestCode, AbilityRequest &request,
    const sptr<IRemoteObject> &callerToken, int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord != nullptr) {
        request.callerTokenRecordId = abilityRecord->GetRecordId();
    }
    if (abilityRecord && abilityRecord->GetAppIndex() > AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX &&
        abilityRecord->GetApplicationInfo().bundleName == want.GetElement().GetBundleName()) {
        (const_cast<Want &>(want)).SetParam(AbilityRuntime::ServerConstant::DLP_INDEX, abilityRecord->GetAppIndex());
        (const_cast<Want &>(want)).SetParam(DLP_PARAMS_SECURITY_FLAG, abilityRecord->GetSecurityFlag());
    }

    if (abilityRecord != nullptr &&
        abilityRecord->GetApplicationInfo().bundleName == want.GetElement().GetBundleName() &&
        (!want.HasParameter(Want::PARAM_APP_CLONE_INDEX_KEY) ||
        want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, 0) == abilityRecord->GetAppIndex())) {
        (const_cast<Want &>(want)).SetParam(AbilityConfig::DEBUG_APP, abilityRecord->IsDebugApp());
    }

    request.want = want;
    request.requestCode = requestCode;
    request.callerToken = callerToken;
    auto setting = AbilityStartSetting::GetEmptySetting();
    if (setting != nullptr) {
        setting->AddProperty(AbilityStartSetting::IS_START_BY_SCB_KEY, "false"); // default is false
        request.startSetting = std::make_shared<AbilityStartSetting>(*(setting.get()));
    }

    auto abilityInfo = StartAbilityUtils::startAbilityInfo;
    if (abilityInfo == nullptr || abilityInfo->GetAppBundleName() != want.GetElement().GetBundleName()) {
        int32_t appIndex = 0;
        if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
            return ERR_APP_CLONE_INDEX_INVALID;
        }
        Want localWant = want;
        if (!StartAbilityUtils::IsCallFromAncoShellOrBroker(callerToken)) {
            localWant.RemoveParam(PARAM_RESV_ANCO_CALLER_UID);
            localWant.RemoveParam(PARAM_RESV_ANCO_CALLER_BUNDLENAME);
            localWant.RemoveParam(PARAM_RESV_ANCO_IS_NEED_UPDATE_NAME);
            localWant.SetParam(Want::PARAM_RESV_CALLER_TOKEN, static_cast<int32_t>(IPCSkeleton::GetCallingTokenID()));
            localWant.SetParam(Want::PARAM_RESV_CALLER_UID, IPCSkeleton::GetCallingUid());
        }
        abilityInfo = StartAbilityInfo::CreateStartAbilityInfo(localWant, userId, appIndex, callerToken);
    }
    CHECK_POINTER_AND_RETURN(abilityInfo, GET_ABILITY_SERVICE_FAILED);
    if (abilityInfo->status != ERR_OK) {
        return abilityInfo->status;
    }
    request.abilityInfo = abilityInfo->abilityInfo;
    request.extensionProcessMode = abilityInfo->extensionProcessMode;
    request.customProcess = abilityInfo->customProcess;
    request.collaboratorType = GetCollaboratorType(request.abilityInfo.applicationInfo.codePath);
    request.isTargetPlugin = abilityInfo->isTargetPlugin;

    if (request.abilityInfo.type == AppExecFwk::AbilityType::SERVICE && request.abilityInfo.isStageBasedModel) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "stage mode, abilityInfo SERVICE type reset EXTENSION");
        request.abilityInfo.type = AppExecFwk::AbilityType::EXTENSION;
    }

    if (request.abilityInfo.applicationInfo.name.empty() || request.abilityInfo.applicationInfo.bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get app info failed");
        return RESOLVE_APP_ERR;
    }
    if (want.GetIntParam(AAFwk::SCREEN_MODE_KEY, ScreenMode::IDLE_SCREEN_MODE) == ScreenMode::JUMP_SCREEN_MODE &&
        (request.abilityInfo.applicationInfo.bundleType != AppExecFwk::BundleType::ATOMIC_SERVICE ||
        request.abilityInfo.launchMode != AppExecFwk::LaunchMode::SINGLETON)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interface of starting atomicService start only atomicService");
        return TARGET_ABILITY_NOT_SERVICE;
    }
    request.appInfo = request.abilityInfo.applicationInfo;
    request.uid = request.appInfo.uid;
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "GenerateAbilityRequest end, app name: %{public}s, moduleName name: %{public}s, uid: %{public}d.",
        request.appInfo.name.c_str(), request.abilityInfo.moduleName.c_str(), request.uid);

    request.want.SetModuleName(request.abilityInfo.moduleName);

    int32_t startRecent = AbilityPermissionUtil::GetInstance().CheckStartRecentAbility(want, request);
    if (startRecent != ERR_OK) {
        return startRecent;
    }

    if (ModalSystemDialogUtil::CheckDebugAppNotInDeveloperMode(request.abilityInfo.applicationInfo)) {
        // local debug do not show dialog.
        if (AAFwk::PermissionVerification::GetInstance()->VerifyStartLocalDebug(IPCSkeleton::GetCallingTokenID())) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "local debug");
            return ERR_OK;
        }
        if (AAFwk::PermissionVerification::GetInstance()->VerifyStartLocalDebug(
            request.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0))) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "real call is local debug");
            return ERR_OK;
        }
        if (abilityRecord != nullptr) {
            std::string targetBundleName = request.want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME);
            std::string callerBundleName = abilityRecord->GetApplicationInfo().bundleName;
            if (targetBundleName.compare(callerBundleName) ==0) {
                TAG_LOGD(AAFwkTag::ABILITYMGR, "same bundle");
                return ERR_OK;
            }
        }
        // service and extension do not show dialog.
        if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled() &&
            !(request.abilityInfo.type == AppExecFwk::AbilityType::SERVICE ||
                request.abilityInfo.type == AppExecFwk::AbilityType::EXTENSION)) {
            ModalSystemDialogUtil::ShowDeveloperModeDialog(
                request.abilityInfo.bundleName, request.abilityInfo.moduleName, request.abilityInfo.labelId, userId);
        }
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer mode");
        return ERR_NOT_DEVELOPER_MODE;
    }

    return ERR_OK;
}

int AbilityManagerService::GenerateExtensionAbilityRequest(const Want &want, AbilityRequest &request,
    const sptr<IRemoteObject> &callerToken, int32_t userId, const std::string hostBundleName)
{
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord != nullptr) {
        request.callerTokenRecordId = abilityRecord->GetRecordId();
        std::string extensionTypeStr = want.GetStringParam(UIEXTENSION_TYPE_KEY);
        int32_t appIndex = 0;
        if (want.HasParameter(Want::PARAM_APP_CLONE_INDEX_KEY)) {
            appIndex = want.GetIntParam(Want::PARAM_APP_CLONE_INDEX_KEY, 0);
        }

        if (AppExecFwk::ConvertToExtensionAbilityType(extensionTypeStr) ==
            AppExecFwk::ExtensionAbilityType::EMBEDDED_UI) {
            (const_cast<Want &>(want)).SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, abilityRecord->GetAppIndex());
            if (abilityRecord->GetApplicationInfo().bundleName == AbilityConfig::SCENEBOARD_BUNDLE_NAME) {
                (const_cast<Want &>(want)).SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, appIndex);
            }
        }
    }
    if (abilityRecord && abilityRecord->GetAppIndex() > AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX &&
        abilityRecord->GetApplicationInfo().bundleName == want.GetElement().GetBundleName()) {
        (const_cast<Want &>(want)).SetParam(AbilityRuntime::ServerConstant::DLP_INDEX, abilityRecord->GetAppIndex());
        (const_cast<Want &>(want)).SetParam(DLP_PARAMS_SECURITY_FLAG, abilityRecord->GetSecurityFlag());
    }
    request.want = want;
    request.callerToken = callerToken;
    request.startSetting = nullptr;
    if (AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
        request.isTargetPlugin = true;
    }

    auto abilityInfo = StartAbilityUtils::startAbilityInfo;
    if (abilityInfo == nullptr || abilityInfo->GetAppBundleName() != want.GetElement().GetBundleName()) {
        int32_t appIndex = 0;
        if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
            return ERR_APP_CLONE_INDEX_INVALID;
        }
        std::string nHostBundleName = GetHostBundleName(hostBundleName, callerToken);
        request.hostBundleName = nHostBundleName;
        abilityInfo = StartAbilityInfo::CreateStartExtensionInfo(want, userId, appIndex, nHostBundleName);
    }
    CHECK_POINTER_AND_RETURN(abilityInfo, GET_ABILITY_SERVICE_FAILED);
    if (abilityInfo->status != ERR_OK) {
        return abilityInfo->status;
    }
    if (ModalSystemDialogUtil::CheckDebugAppNotInDeveloperMode(abilityInfo->abilityInfo.applicationInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer mode");
        return ERR_NOT_DEVELOPER_MODE;
    }
    return InitialAbilityRequest(request, *abilityInfo);
}

std::string AbilityManagerService::GetHostBundleName(const std::string hostBundleName,
    const sptr<IRemoteObject> &callerToken)
{
    std::string result = hostBundleName;
    auto caller = Token::GetAbilityRecordByToken(callerToken);
    if (result.empty() && caller) {
        result = caller->GetAbilityInfo().bundleName;
    }

    return result;
}

int32_t AbilityManagerService::InitialAbilityRequest(AbilityRequest &request,
    const StartAbilityInfo &abilityInfo) const
{
    request.abilityInfo = abilityInfo.abilityInfo;
    request.extensionProcessMode = abilityInfo.extensionProcessMode;
    request.customProcess = abilityInfo.customProcess;
    if (request.abilityInfo.applicationInfo.name.empty() || request.abilityInfo.applicationInfo.bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get app info failed");
        return RESOLVE_APP_ERR;
    }
    request.appInfo = request.abilityInfo.applicationInfo;
    request.uid = request.appInfo.uid;
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "GenerateExtensionAbilityRequest end, app name:%{public}s, bundle name:%{public}s, uid:%{public}d, moduleName:%{public}s",
        request.appInfo.name.c_str(), request.appInfo.bundleName.c_str(), request.uid, request.abilityInfo.moduleName.c_str());

    request.want.SetModuleName(request.abilityInfo.moduleName);

    return ERR_OK;
}

int AbilityManagerService::StopServiceAbility(const Want &want, int32_t userId, const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call.");

    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    if (!isSaCall && !isShellCall) {
        auto abilityRecord = Token::GetAbilityRecordByToken(token);
        if (abilityRecord == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "callerRecord null");
            return ERR_INVALID_VALUE;
        }
    }

    int32_t validUserId = GetValidUserId(userId);
    if (!JudgeMultiUserConcurrency(validUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    AbilityRequest abilityRequest;
    auto result = GenerateAbilityRequest(want, DEFAULT_INVAL_VALUE, abilityRequest, nullptr, validUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        return result;
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "validUserId : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    auto type = abilityInfo.type;
    if (type != AppExecFwk::AbilityType::SERVICE && type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability not service type");
        return TARGET_ABILITY_NOT_SERVICE;
    }

    auto res = JudgeAbilityVisibleControl(abilityInfo);
    if (res != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability invisible");
        return res;
    }

    auto connectManager = GetConnectManagerByUserId(validUserId, abilityInfo.extensionAbilityType);
    if (connectManager == nullptr) {
        return ERR_INVALID_VALUE;
    }

    return connectManager->StopServiceAbility(abilityRequest);
}

void AbilityManagerService::OnAbilityDied(std::shared_ptr<AbilityRecord> abilityRecord)
{
    CHECK_POINTER(abilityRecord);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "On ability died: %{public}s/%{public}s, %{public}d, %{public}" PRId64,
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str(),
        abilityRecord->GetRecordId(),
        abilityRecord->GetAbilityRecordId());
    if (abilityRecord->GetToken()) {
        FreezeUtil::GetInstance().DeleteLifecycleEvent(abilityRecord->GetToken()->AsObject());
        if (KioskManager::GetInstance().IsInKioskMode() &&
            KioskManager::GetInstance().IsKioskBundleUid(abilityRecord->GetAbilityInfo().uid)) {
            KioskManager::GetInstance().ExitKioskMode(abilityRecord->GetToken()->AsObject(), true);
        }
    }
    FreezeUtil::GetInstance().DeleteAppLifecycleEvent(abilityRecord->GetPid());
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        if (abilityRecord->GetAbilityInfo().type == AbilityType::PAGE) {
            auto uiAbilityManager = GetUIAbilityManagerByUserId(abilityRecord->GetOwnerMissionUserId());
            CHECK_POINTER(uiAbilityManager);
            uiAbilityManager->OnAbilityDied(std::static_pointer_cast<UIAbilityRecord>(abilityRecord));
            return;
        }
    } else {
        auto manager = GetMissionListManagerByUserId(abilityRecord->GetOwnerMissionUserId());
        if (manager && abilityRecord->GetAbilityInfo().type == AbilityType::PAGE) {
            ReleaseAbilityTokenMap(abilityRecord->GetToken());
            manager->OnAbilityDied(abilityRecord, abilityRecord->GetOwnerMissionUserId());
            return;
        }
    }

    auto userId = abilityRecord->GetOwnerMissionUserId();
    auto connectManager = GetConnectManagerByUserId(userId, abilityRecord->GetAbilityInfo().extensionAbilityType);
    if (connectManager) {
        connectManager->OnAbilityDied(BaseExtensionRecord::TransferToExtensionRecordBase(abilityRecord));
        return;
    } else {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "no connectManager, type: %{public}d", abilityRecord->GetAbilityRecordType());
    }

    auto dataAbilityManager = GetDataAbilityManagerByToken(abilityRecord->GetToken());
    if (dataAbilityManager) {
        dataAbilityManager->OnAbilityDied(abilityRecord);
    }
}

void AbilityManagerService::OnCallConnectDied(std::shared_ptr<CallRecord> callRecord)
{
    CHECK_POINTER(callRecord);
    auto userId = callRecord->GetUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnCallConnectDied(callRecord);
        return;
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (missionListManager) {
        missionListManager->OnCallConnectDied(callRecord);
    }
}

void AbilityManagerService::ReleaseAbilityTokenMap(const sptr<IRemoteObject> &token)
{
    std::lock_guard<ffrt::mutex> autoLock(abilityTokenLock_);
    for (auto iter = callStubTokenMap_.begin(); iter != callStubTokenMap_.end(); iter++) {
        if (iter->second == token) {
            callStubTokenMap_.erase(iter);
            break;
        }
    }
}

bool AbilityManagerService::CheckPermissionForKillCollaborator()
{
    // check permission first
    auto isShellCall = PermissionVerification::GetInstance()->IsShellCall();
    auto isCallingPerm = PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_KILL_APP_PROCESSES);
    if (!isShellCall && !isCallingPerm) {
        return false;
    }
    return true;
}

int AbilityManagerService::KillProcess(const std::string &bundleName, bool clearPageStack, int32_t appIndex,
    const std::string& reason)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "Kill process, bundleName: %{public}s, clearPageStack: %{public}d",
        bundleName.c_str(), clearPageStack);
    // check permission first
    auto isAllowKillProcessForCollaborator = CheckPermissionForKillCollaborator();
    if (!isAllowKillProcessForCollaborator &&
        DelayedSingleton<AppScheduler>::GetInstance()->VerifyKillProcessPermission(bundleName) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "KillProcess permission verification fail");
        return ERR_PERMISSION_DENIED;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, KILL_PROCESS_FAILED);
    int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    AppExecFwk::BundleInfo bundleInfo;
    if (IN_PROCESS_CALL(bms->GetCloneBundleInfoExt(bundleName,
        static_cast<uint32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_APPLICATION),
        appIndex, userId, bundleInfo)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get bundle info when kill process failed");
        return GET_BUNDLE_INFO_FAILED;
    }

    int32_t collaboratorType = GetCollaboratorType(bundleInfo.applicationInfo.codePath);
    if (CheckCollaboratorType(collaboratorType)) {
        if (!isAllowKillProcessForCollaborator) {
            TAG_LOGE(AAFwkTag::APPMGR, "KillProcess permission verification fail");
            return ERR_PERMISSION_DENIED;
        }
        return KillProcessForCollaborator(collaboratorType, bundleName, userId);
    }

    KeepAliveType type;
    if (KeepAliveUtils::IsKeepAliveBundle(bundleInfo, userId, type)
        && DelayedSingleton<AppScheduler>::GetInstance()->IsMemorySizeSufficient()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no kill alive process");
        return KILL_PROCESS_KEEP_ALIVE;
    }

    int ret = DelayedSingleton<AppScheduler>::GetInstance()->KillApplication(bundleName, clearPageStack, appIndex, reason);
    return ret == ERR_OK ? ERR_OK : KILL_PROCESS_FAILED;
}

int32_t AbilityManagerService::KillProcessForCollaborator(int32_t collaboratorType,
    const std::string &bundleName, int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "Collaborator kill");
    auto collaborator = GetCollaborator(collaboratorType);
    if (collaborator == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Collaborator null");
        return KILL_PROCESS_FAILED;
    }
    if (collaborator->NotifyKillProcesses(bundleName, userId) != ERR_OK) {
        return KILL_PROCESS_FAILED;
    }
    return ERR_OK;
}

int AbilityManagerService::UninstallApp(const std::string &bundleName, int32_t uid)
{
    return UninstallApp(bundleName, uid, 0);
}

int32_t AbilityManagerService::UninstallApp(const std::string &bundleName, int32_t uid, int32_t appIndex)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "uninstall app, bundleName:%{public}s, uid=%{public}d, appIndex:%{public}d",
        bundleName.c_str(), uid, appIndex);
    return UninstallAppInner(bundleName, uid, appIndex, false, "");
}

int32_t AbilityManagerService::UpgradeApp(const std::string &bundleName, const int32_t uid, const std::string &exitMsg,
    int32_t appIndex)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "upgradeApp app, bundleName: %{public}s, uid=%{public}d, exitMsg:%{public}s, appIndex:%{public}d",
        bundleName.c_str(), uid, exitMsg.c_str(), appIndex);
    return UninstallAppInner(bundleName, uid, appIndex, true, exitMsg);
}

int32_t AbilityManagerService::UninstallAppInner(const std::string &bundleName, const int32_t uid, int32_t appIndex,
    const bool isUpgrade, const std::string &exitMsg)
{
    pid_t callingPid = IPCSkeleton::GetCallingPid();
    pid_t pid = getprocpid();
    if (callingPid != pid) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: not bundleMgr", __func__);
        return CHECK_PERMISSION_FAILED;
    }

    auto userId = uid / BASE_USER_RANGE;
    if (isUpgrade) {
        CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
        AAFwk::ExitReason exitReason = { REASON_UPGRADE, exitMsg };
        appExitReasonHelper_->RecordAppExitReason(bundleName, uid, appIndex, exitReason);
        IN_PROCESS_CALL_WITHOUT_RET(
            KeepAliveProcessManager::GetInstance().SaveKeepAliveAppRestartAfterUpgrade(bundleName, uid));
        IN_PROCESS_CALL_WITHOUT_RET(
            KeepAliveProcessManager::GetInstance().SaveAppSeriviceRestartAfterUpgrade(bundleName, uid));
    } else {
        IN_PROCESS_CALL_WITHOUT_RET(
            KeepAliveProcessManager::GetInstance().SetApplicationKeepAlive(bundleName, userId, false, true, false));
        if (userId == U1_USER_ID) {
            IN_PROCESS_CALL_WITHOUT_RET(KeepAliveProcessManager::GetInstance().SetAppServiceExtensionKeepAlive(
                bundleName, false, true, false));
        }
    }
    IN_PROCESS_CALL_WITHOUT_RET(DelayedSingleton<AppExecFwk::AppMgrClient>::
        GetInstance()->SetKeepAliveEnableState(bundleName, false, uid));

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    if (commonExtensionManager) {
        commonExtensionManager->UninstallApp(bundleName, uid);
    }
    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    if (uiExtensionAbilityManager) {
        uiExtensionAbilityManager->UninstallApp(bundleName, uid);
    }

    CHECK_POINTER_AND_RETURN(subManagersHelper_, ERR_NULL_OBJECT);
    subManagersHelper_->UninstallApp(bundleName, uid);
    int ret = IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->NotifyUninstallOrUpgradeApp(bundleName,
            uid, isUpgrade));
    if (ret != ERR_OK) {
        return UNINSTALL_APP_FAILED;
    }
    if (!isUpgrade) {
        DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->DeleteAppExitReason(bundleName, uid,
            appIndex);
    }
    return ERR_OK;
}

int AbilityManagerService::PreLoadAppDataAbilities(const std::string &bundleName, const int32_t userId)
{
    if (bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid bundle name preloading");
        return ERR_INVALID_VALUE;
    }

    ffrt::submit([weak = weak_from_this(), bundleName, userId]() {
        auto pthis = weak.lock();
        if (pthis == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "pthis null");
            return;
        }
        pthis->PreLoadAppDataAbilitiesTask(bundleName, userId);
        }, ffrt::task_attr().timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));

    return ERR_OK;
}

void AbilityManagerService::PreLoadAppDataAbilitiesTask(const std::string &bundleName, const int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    auto dataAbilityManager = GetDataAbilityManagerByUserId(userId);
    if (dataAbilityManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid data ability manager preloading");
        return;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER(bms);

    AppExecFwk::BundleInfo bundleInfo;
    bool ret = IN_PROCESS_CALL(
        bms->GetBundleInfo(bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_WITH_ABILITIES, bundleInfo, userId));
    if (!ret) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "get bundleInfo preloading failed, userId:%{public}d", userId);
        return;
    }

    auto begin = system_clock::now();
    AbilityRequest dataAbilityRequest;
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(dataAbilityRequest.want, nullptr);
    dataAbilityRequest.appInfo = bundleInfo.applicationInfo;
    for (auto it = bundleInfo.abilityInfos.begin(); it != bundleInfo.abilityInfos.end(); ++it) {
        if (it->type != AppExecFwk::AbilityType::DATA) {
            continue;
        }
        if ((system_clock::now() - begin) >= DATA_ABILITY_START_TIMEOUT) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "app data ability preloading '%{public}s' timeout", bundleName.c_str());
            return;
        }
        dataAbilityRequest.abilityInfo = *it;
        dataAbilityRequest.uid = bundleInfo.uid;
        TAG_LOGD(AAFwkTag::ABILITYMGR, "App data ability preloading: '%{public}s.%{public}s'...",
            it->bundleName.c_str(), it->name.c_str());

        auto dataAbility = dataAbilityManager->Acquire(dataAbilityRequest, false, nullptr, false);
        if (dataAbility == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                "preload data ability failed  '%{public}s.%{public}s'", it->bundleName.c_str(), it->name.c_str());
            return;
        }
    }
}

bool AbilityManagerService::IsSystemUiApp(const AppExecFwk::AbilityInfo &info) const
{
    if (info.bundleName != AbilityConfig::SYSTEM_UI_BUNDLE_NAME) {
        return false;
    }
    return (info.name == AbilityConfig::SYSTEM_UI_NAVIGATION_BAR ||
        info.name == AbilityConfig::SYSTEM_UI_STATUS_BAR ||
        info.name == AbilityConfig::SYSTEM_UI_ABILITY_NAME);
}

bool AbilityManagerService::IsSystemUI(const std::string &bundleName) const
{
    return bundleName == AbilityConfig::SYSTEM_UI_BUNDLE_NAME;
}

void AbilityManagerService::HandleLoadTimeOut(int64_t abilityRecordId, bool isHalf, bool isExtension)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "load timeout %{public}" PRId64, abilityRecordId);
    if (isExtension) {

        auto commonExtensionManager = GetCommonExtensionManagerByAbilityRecordId(abilityRecordId);
        if (commonExtensionManager != nullptr) {
            commonExtensionManager->OnTimeOut(AbilityManagerService::LOAD_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
        auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByAbilityRecordId(abilityRecordId);
        if (uiExtensionAbilityManager != nullptr) {
            uiExtensionAbilityManager->OnTimeOut(AbilityManagerService::LOAD_TIMEOUT_MSG, abilityRecordId, isHalf);
        }   
        return;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManagers = GetUIAbilityManagers();
        for (auto& item : uiAbilityManagers) {
            if (item.second) {
                item.second->OnTimeOut(AbilityManagerService::LOAD_TIMEOUT_MSG, abilityRecordId, isHalf);
            }
        }
        return;
    }
    auto missionListManagers = GetMissionListManagers();
    for (auto& item : missionListManagers) {
        if (item.second) {
            item.second->OnTimeOut(AbilityManagerService::LOAD_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
    }
}

void AbilityManagerService::HandleActiveTimeOut(int64_t abilityRecordId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Handle active timeout.");
    auto missionListManagers = GetMissionListManagers();
    for (auto& item : missionListManagers) {
        if (item.second) {
            item.second->OnTimeOut(AbilityManagerService::ACTIVE_TIMEOUT_MSG, abilityRecordId);
        }
    }
}

void AbilityManagerService::HandleInactiveTimeOut(int64_t abilityRecordId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Handle inactive timeout.");
    auto missionListManagers = GetMissionListManagers();
    for (auto& item : missionListManagers) {
        if (item.second) {
            item.second->OnTimeOut(AbilityManagerService::INACTIVE_TIMEOUT_MSG, abilityRecordId);
        }
    }
    auto connectManagers = GetConnectManagers();
    for (auto& item : connectManagers) {
        if (item) {
            item->OnTimeOut(AbilityManagerService::INACTIVE_TIMEOUT_MSG, abilityRecordId);
        }
    }
}

void AbilityManagerService::HandleConnectTimeOut(int64_t abilityRecordId, bool isHalf)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Handle connect timeout.");
    auto connectManagers = GetConnectManagers();
    for (auto& item : connectManagers) {
        if (item) {
            item->OnTimeOut(AbilityManagerService::CONNECT_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
    }
}

void AbilityManagerService::HandleForegroundTimeOut(int64_t abilityRecordId, bool isHalf, bool isExtension)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "foreground timeout %{public}" PRId64, abilityRecordId);
    if (isExtension) {

        auto commonExtensionManager = GetCommonExtensionManagerByAbilityRecordId(abilityRecordId);
        if (commonExtensionManager != nullptr) {
            commonExtensionManager->OnTimeOut(AbilityManagerService::FOREGROUND_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
        auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByAbilityRecordId(abilityRecordId);
        if (uiExtensionAbilityManager != nullptr) {
            uiExtensionAbilityManager->OnTimeOut(AbilityManagerService::FOREGROUND_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
        return;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManagers = GetUIAbilityManagers();
        for (auto& item : uiAbilityManagers) {
            if (item.second) {
                item.second->OnTimeOut(AbilityManagerService::FOREGROUND_TIMEOUT_MSG, abilityRecordId, isHalf);
            }
        }
        return;
    }
    auto missionListManagers = GetMissionListManagers();
    for (auto& item : missionListManagers) {
        if (item.second) {
            item.second->OnTimeOut(AbilityManagerService::FOREGROUND_TIMEOUT_MSG, abilityRecordId, isHalf);
        }
    }
}

void AbilityManagerService::HandleShareDataTimeOut(int64_t uniqueId)
{
    WantParams wantParam;
    int32_t ret = GetShareDataPairAndReturnData(nullptr, ERR_TIMED_OUT, uniqueId, wantParam);
    if (ret) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "acqurieShareData failed");
    }
}

int32_t AbilityManagerService::GetShareDataPairAndReturnData(std::shared_ptr<AbilityRecord> abilityRecord,
    const int32_t &resultCode, const int32_t &uniqueId, WantParams &wantParam)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "resultCode:%{public}d, uniqueId:%{public}d, wantParam size:%{public}d",
        resultCode, uniqueId, wantParam.Size());
    {
        std::lock_guard<ffrt::mutex> guard(iAcquireShareDataMapLock_);
        auto it = iAcquireShareDataMap_.find(uniqueId);
        if (it != iAcquireShareDataMap_.end()) {
            auto shareDataPair = it->second;
            if (abilityRecord && shareDataPair.first != abilityRecord->GetAbilityRecordId()) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord is not the abilityRecord from request");
                return ERR_INVALID_VALUE;
            }
            auto callback = shareDataPair.second;
            if (!callback) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "callback object null");
                return ERR_INVALID_VALUE;
            }
            auto ret = callback->AcquireShareDataDone(resultCode, wantParam);
            iAcquireShareDataMap_.erase(it);
            return ret;
        }
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "iAcquireShareData null");
    return ERR_INVALID_VALUE;
}

bool AbilityManagerService::VerificationAllToken(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_POINTER_AND_RETURN(subManagersHelper_, false);
    return subManagersHelper_->VerificationAllToken(token);
}

std::shared_ptr<DataAbilityManager> AbilityManagerService::GetCurrentDataAbilityManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentDataAbilityManager();
}

std::shared_ptr<DataAbilityManager> AbilityManagerService::GetDataAbilityManager(
    const sptr<IAbilityScheduler> &scheduler)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetDataAbilityManager(scheduler);
}

std::shared_ptr<DataAbilityManager> AbilityManagerService::GetDataAbilityManagerByUserId(int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetDataAbilityManagerByUserId(userId);
}

std::shared_ptr<DataAbilityManager> AbilityManagerService::GetDataAbilityManagerByToken(
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetDataAbilityManagerByToken(token);
}

std::vector<std::shared_ptr<AbilityConnectManager>> AbilityManagerService::GetConnectManagers()
{
    if (subManagersHelper_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pointer null");
        return std::vector<std::shared_ptr<AbilityConnectManager>>();
    }
    return subManagersHelper_->GetConnectManagers();
}

std::shared_ptr<AbilityConnectManager> AbilityManagerService::GetConnectManagerByUserId(int32_t userId, const AppExecFwk::ExtensionAbilityType type)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    std::shared_ptr<AbilityConnectManager> connectManager = nullptr;
    if(UIExtensionWrapper::IsUIExtension(type)){
        connectManager = GetUIExtensionAbilityManagerByUserId(userId);
    }else{
        connectManager = GetCommonExtensionManagerByUserId(userId);
    }
    return connectManager;
}

std::shared_ptr<AbilityConnectManager> AbilityManagerService::GetConnectManagerByToken(
    const sptr<IRemoteObject> &token, const AppExecFwk::ExtensionAbilityType type)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    std::shared_ptr<AbilityConnectManager> connectManager = nullptr;
    if(UIExtensionWrapper::IsUIExtension(type)){
        connectManager = GetUIExtensionAbilityManagerByToken(token);
    }else{
        connectManager = GetCommonExtensionManagerByToken(token);
    }
    return connectManager;
}

std::shared_ptr<PendingWantManager> AbilityManagerService::GetCurrentPendingWantManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentPendingWantManager();
}

int32_t AbilityManagerService::GetServiceMapByUserId(AbilityConnectManager::ServiceMapType &serviceMap, int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, ERR_INVALID_VALUE);
    auto commonExtensionManager = subManagersHelper_->GetCommonExtensionManagerByUserId(userId);
    auto uiExtensionManager = subManagersHelper_->GetUIExtensionAbilityManagerByUserId(userId);
    if (!commonExtensionManager || !uiExtensionManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "manager null");
        return ERR_INVALID_VALUE;
    }

    auto serviceMapCommon = commonExtensionManager->GetServiceMap();
    serviceMap.insert(serviceMapCommon.begin(), serviceMapCommon.end());
    auto serviceMapUI = uiExtensionManager->GetServiceMap();
    serviceMap.insert(serviceMapUI.begin(), serviceMapUI.end());
    return ERR_OK;
}

std::unordered_map<int, std::shared_ptr<UIExtensionAbilityManager>> AbilityManagerService::GetUIExtensionAbilityManagers()
{
    if (subManagersHelper_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pointer null");
        return std::unordered_map<int, std::shared_ptr<UIExtensionAbilityManager>>();
    }
    return subManagersHelper_->GetUIExtensionAbilityManagers();
}

std::shared_ptr<UIExtensionAbilityManager> AbilityManagerService::GetCurrentUIExtensionAbilityManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentUIExtensionAbilityManager();
}

std::shared_ptr<UIExtensionAbilityManager> AbilityManagerService::GetUIExtensionAbilityManagerByUserId(int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetUIExtensionAbilityManagerByUserId(userId);
}

std::shared_ptr<UIExtensionAbilityManager> AbilityManagerService::GetUIExtensionAbilityManagerByToken(
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetUIExtensionAbilityManagerByToken(token);
}

std::shared_ptr<UIExtensionAbilityManager> AbilityManagerService::GetUIExtensionAbilityManagerByAbilityRecordId(
    const int64_t &abilityRecordId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetUIExtensionAbilityManagerByAbilityRecordId(abilityRecordId);
}


std::unordered_map<int, std::shared_ptr<CommonExtensionManager>> AbilityManagerService::GetCommonExtensionManagers()
{
    if (subManagersHelper_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pointer null");
        return std::unordered_map<int, std::shared_ptr<CommonExtensionManager>>();
    }
    return subManagersHelper_->GetCommonExtensionManagers();
}

std::shared_ptr<CommonExtensionManager> AbilityManagerService::GetCurrentCommonExtensionManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentCommonExtensionManager();
}

std::shared_ptr<CommonExtensionManager> AbilityManagerService::GetCommonExtensionManagerByUserId(int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCommonExtensionManagerByUserId(userId);
}

std::shared_ptr<CommonExtensionManager> AbilityManagerService::GetCommonExtensionManagerByToken(
    const sptr<IRemoteObject> &token)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCommonExtensionManagerByToken(token);
}

std::shared_ptr<CommonExtensionManager> AbilityManagerService::GetCommonExtensionManagerByAbilityRecordId(
    const int64_t &abilityRecordId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCommonExtensionManagerByAbilityRecordId(abilityRecordId);
}

std::shared_ptr<PendingWantManager> AbilityManagerService::GetPendingWantManagerByUserId(int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetPendingWantManagerByUserId(userId);
}

std::unordered_map<int, std::shared_ptr<MissionListManagerInterface>> AbilityManagerService::GetMissionListManagers()
{
    if (subManagersHelper_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pointer null");
        return std::unordered_map<int, std::shared_ptr<MissionListManagerInterface>>();
    }
    return subManagersHelper_->GetMissionListManagers();
}

std::shared_ptr<MissionListManagerInterface> AbilityManagerService::GetCurrentMissionListManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentMissionListManager();
}

std::shared_ptr<MissionListManagerInterface> AbilityManagerService::GetMissionListManagerByUserId(int32_t userId)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetMissionListManagerByUserId(userId);
}

std::shared_ptr<MissionListWrap> AbilityManagerService::GetMissionListWrap()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetMissionListWrap();
}

std::unordered_map<int, std::shared_ptr<UIAbilityLifecycleManager>> AbilityManagerService::GetUIAbilityManagers()
{
    if (subManagersHelper_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "pointer null");
        return std::unordered_map<int, std::shared_ptr<UIAbilityLifecycleManager>>();
    }
    return subManagersHelper_->GetUIAbilityManagers();
}

std::shared_ptr<UIAbilityLifecycleManager> AbilityManagerService::GetCurrentUIAbilityManager()
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetCurrentUIAbilityManager();
}

std::shared_ptr<UIAbilityLifecycleManager> AbilityManagerService::GetUIAbilityManagerByUserId(int32_t userId) const
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetUIAbilityManagerByUserId(userId);
}

std::shared_ptr<UIAbilityLifecycleManager> AbilityManagerService::GetUIAbilityManagerByUid(int32_t uid)
{
    CHECK_POINTER_AND_RETURN(subManagersHelper_, nullptr);
    return subManagersHelper_->GetUIAbilityManagerByUid(uid);
}

void AbilityManagerService::StartResidentApps(int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartResidentApps %{public}d", userId);
    ConnectServices();
    auto residentProcessManager = DelayedSingleton<ResidentProcessManager>::GetInstance();
    CHECK_POINTER(residentProcessManager);
    std::vector<AppExecFwk::BundleInfo> bundleInfos;
    if (!residentProcessManager->GetResidentBundleInfosForUser(bundleInfos, userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get resident bundleinfos failed");
        return;
    }
    residentProcessManager->Init();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "startResidentApps getBundleInfos size:%{public}zu", bundleInfos.size());

    residentProcessManager->StartResidentProcessWithMainElement(bundleInfos, userId);
    if (!bundleInfos.empty()) {
#ifdef SUPPORT_GRAPHICS
        if (userId == U0_USER_ID) {
            WaitBootAnimationStart();
        }
#endif
        residentProcessManager->StartResidentProcess(bundleInfos);
    }
}

void AbilityManagerService::StartKeepAliveApps(int32_t userId)
{
    if (!system::GetBoolParameter(PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED, false)) {
        return;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartKeepAliveApps %{public}d", userId);
    ConnectServices();
    std::vector<AppExecFwk::BundleInfo> bundleInfos;
    if (!KeepAliveProcessManager::GetInstance().GetKeepAliveBundleInfosForUser(
        bundleInfos, userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get keep-alive bundle info failed");
        return;
    }
    KeepAliveProcessManager::GetInstance().FilterNeedRestartKeepAliveBundleInfos(bundleInfos);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartKeepAliveApps getBundleInfos size:%{public}zu", bundleInfos.size());

    KeepAliveProcessManager::GetInstance().StartKeepAliveProcessWithMainElement(bundleInfos, userId);
}

void AbilityManagerService::StartAutoStartupApps(int32_t userId, bool isManualStart)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "StartAutoStartupApps called");
    bool isAutoStartupReady = system::GetBoolParameter(AUTO_STARTUP_READY, true);
    bool hasScreenUnlockInterceptor = false;
    if (interceptorExecuter_ != nullptr) {
        hasScreenUnlockInterceptor = interceptorExecuter_->HasInterceptor("ScreenUnlock");
    }
    if (!isAutoStartupReady || hasScreenUnlockInterceptor) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "isReady %{public}d, hasInterceptor %{public}d",
            isAutoStartupReady, hasScreenUnlockInterceptor);
        return;
    }
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return;
    }
    std::vector<AutoStartupInfo> infoList;
    int32_t result = abilityAutoStartupService_->QueryAllAutoStartupApplicationsWithoutPermission(infoList, userId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed query data");
        return;
    }

    if (taskHandler_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "taskHandler null");
        return;
    }
    std::queue<AutoStartupInfo> infoQueue;
    for (auto &info : infoList) {
        info.retryCount = START_AUTO_START_APP_RETRY_MAX_TIMES;
        infoQueue.push(info);
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartAutoStartupApps userId:%{public}d", userId);
    StartAutoStartupApps(infoQueue, userId);
    if (!isManualStart) {
        abilityAutoStartupService_->AddHandledAutoStartupUsers(userId);
    }
    auto removeParameterWatcherTask = []() {
        int32_t ret = RemoveParameterWatcher(
            AUTO_STARTUP_READY, AbilityManagerService::HandleAutoStartupReadyCallback, nullptr);
        TAG_LOGD(AAFwkTag::ABILITYMGR, "RemoveParameterWatcher %{public}s with %{public}d",
                AUTO_STARTUP_READY, ret);
    };
    taskHandler_->SubmitTask(removeParameterWatcherTask, "removeParameterWatcherTask");
}

void AbilityManagerService::StartAutoStartupApps(std::queue<AutoStartupInfo> infoQueue, int32_t userId)
{
    if (infoQueue.empty()) {
        return;
    }
    if (taskHandler_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "taskHandler null");
        return;
    }
    auto info = infoQueue.front();
    infoQueue.pop();
    AppExecFwk::ElementName element;
    element.SetBundleName(info.bundleName);
    element.SetAbilityName(info.abilityName);
    element.SetModuleName(info.moduleName);
    Want want;
    want.SetElement(element);
    want.SetParam(Want::PARAM_APP_AUTO_STARTUP_LAUNCH_REASON, true);
    if (info.appCloneIndex >= 0 && info.appCloneIndex <= AbilityRuntime::GlobalConstant::MAX_APP_CLONE_INDEX) {
        want.SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, info.appCloneIndex);
    }
    int32_t result = ERR_OK;
    if (info.abilityTypeName == AbilityRuntime::EXTENSION_TYPE_APP_SERVICE) {
        result = StartExtensionAbility(
            want, nullptr, userId, AppExecFwk::ExtensionAbilityType::APP_SERVICE);
    } else {
        result = StartAbility(want, userId);
    }
    if ((result != ERR_OK) && (info.retryCount > 0)) {
        info.retryCount--;
        infoQueue.push(info);
    }
    auto nextStartAutoStartupAppsTask = [aams = weak_from_this(), infoQueue, userId]() {
        auto obj = aams.lock();
        if (obj == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "start auto startup app error, obj null");
            return;
        }
        obj->StartAutoStartupApps(infoQueue, userId);
    };
    taskHandler_->SubmitTask(nextStartAutoStartupAppsTask, "StartAutoStartupApps", START_AUTO_START_APP_DELAY_TIME);
}

void AbilityManagerService::SubscribeUserUnlockedEvent()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "SubscribeUserUnlockedEvent called");
    std::lock_guard<std::mutex> lock(subscribedMutex_);
    // add listen screen unlocked.
    EventFwk::MatchingSkills matchingSkills;
    matchingSkills.AddEvent(EventFwk::CommonEventSupport::COMMON_EVENT_USER_UNLOCKED);
    EventFwk::CommonEventSubscribeInfo subscribeInfo(matchingSkills);
    subscribeInfo.SetThreadMode(EventFwk::CommonEventSubscribeInfo::COMMON);
    userUnlockSubscriber_ = std::make_shared<AbilityRuntime::AbilityUserUnlockEventSubscriber>(subscribeInfo,
        GetScreenUnlockCallback(), GetUserScreenUnlockCallback());
    bool subResult = EventFwk::CommonEventManager::SubscribeCommonEvent(userUnlockSubscriber_);
    if (!subResult) {
        RetrySubscribeUnlockedEvent(RETRY_COUNT, userUnlockSubscriber_, true);
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "SU life, subscribe uu suc");
}

void AbilityManagerService::SubscribeScreenUnlockedEvent()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "SubscribeScreenUnlockedEvent called");
    std::lock_guard<std::mutex> lock(subscribedMutex_);
    if (isSubscribed_) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Screen unlocked event subscriber already exists");
        return;
    }
    // add listen screen unlocked.
    EventFwk::MatchingSkills matchingSkills;
    matchingSkills.AddEvent(EventFwk::CommonEventSupport::COMMON_EVENT_SCREEN_UNLOCKED);
    EventFwk::CommonEventSubscribeInfo subscribeInfo(matchingSkills);
    subscribeInfo.SetThreadMode(EventFwk::CommonEventSubscribeInfo::COMMON);
    screenSubscriber_ = std::make_shared<AbilityRuntime::AbilityScreenUnlockEventSubscriber>(subscribeInfo,
        GetScreenUnlockCallback());
    bool subResult = EventFwk::CommonEventManager::SubscribeCommonEvent(screenSubscriber_);
    if (!subResult) {
        RetrySubscribeUnlockedEvent(RETRY_COUNT, screenSubscriber_);
        return;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "SU life, subscribe su suc");
    isSubscribed_ = true;
}

std::function<void(int32_t)> AbilityManagerService::GetScreenUnlockCallback()
{
    auto screenUnlockCallback = [abilityManager = weak_from_this()](int32_t userId) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "on screen unlocked");
        auto abilityMgr = abilityManager.lock();
        if (abilityMgr == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid abilityMgr pointer");
            return;
        }
        auto taskHandler = abilityMgr->GetTaskHandler();
        if (taskHandler == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid taskHandler pointer");
            return;
        }
        auto screenUnlockTask = [abilityManager]() {
            auto abilityMgr = abilityManager.lock();
            if (abilityMgr == nullptr) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid abilityMgr pointer");
                return;
            }
            abilityMgr->RemoveScreenUnlockInterceptor();
            abilityMgr->UnSubscribeScreenUnlockedEvent();
            DelayedSingleton<ResidentProcessManager>::GetInstance()->StartFailedResidentAbilities();
        };
        taskHandler->SubmitTask(screenUnlockTask, "ScreenUnlockTask");
        auto delayStartAutoStartupAppTask = [abilityManager, userId]() {
            auto abilityMgr = abilityManager.lock();
            if (abilityMgr == nullptr) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid abilityMgr pointer");
                return;
            }
            abilityMgr->StartAutoStartupApps(userId);
        };
        taskHandler->SubmitTask(delayStartAutoStartupAppTask, "DelayStartAutoStartupApps",
            START_AUTO_START_APP_DELAY_TIME);
    };
    return screenUnlockCallback;
}

std::function<void()> AbilityManagerService::GetUserScreenUnlockCallback()
{
    auto userScreenUnlockCallback = [abilityManager = weak_from_this()]() {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "On user screen unlocked.");
        auto abilityMgr = abilityManager.lock();
        if (abilityMgr == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "Invalid abilityMgr pointer.");
            return;
        }
        abilityMgr->RemoveScreenUnlockInterceptor();
    };
    return userScreenUnlockCallback;
}

void AbilityManagerService::UnSubscribeScreenUnlockedEvent()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "UnSubscribeScreenUnlockedEvent called");
    std::lock_guard<std::mutex> lock(subscribedMutex_);
    bool subResult = EventFwk::CommonEventManager::UnSubscribeCommonEvent(screenSubscriber_);
    if (subResult) {
        isSubscribed_ = false;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Screen unlocked event subscriber unsubscribe result is %{public}d.", subResult);
}

void AbilityManagerService::RetrySubscribeUnlockedEvent(int32_t retryCount,
    std::shared_ptr<EventFwk::CommonEventSubscriber> subscriber, bool isUserUnlockSubscriber)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "RetryCount: %{public}d.", retryCount);
    CHECK_POINTER_LOG(subscriber, "subscriber nullptr");
    auto retrySubscribeScreenUnlockedEventTask = [aams = weak_from_this(), unlockedEventSubscriber = subscriber,
                                                     retryCount, isUserUnlock = isUserUnlockSubscriber]() {
        CHECK_POINTER_LOG(unlockedEventSubscriber, "unlockedEventSubscriber nullptr");
        auto obj = aams.lock();
        if (obj == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "retry subscribe screen unlocked event, obj null");
            return;
        }
        bool subResult = EventFwk::CommonEventManager::SubscribeCommonEvent(unlockedEventSubscriber);
        if (subResult) {
            if (!isUserUnlock) {
                obj->isSubscribed_ = true;
            }
            TAG_LOGI(AAFwkTag::ABILITYMGR, "SU life, subscribe suc:%{public}d", isUserUnlock);
            return;
        }
        if (retryCount > 0) {
            obj->RetrySubscribeUnlockedEvent(retryCount - 1, unlockedEventSubscriber, isUserUnlock);
            return;
        }
        TAG_LOGE(AAFwkTag::ABILITYMGR, "SU life, subscribe err:%{public}d", isUserUnlock);
    };
    constexpr int32_t delaytime = 200 * 1000; // us
    ffrt::submit(std::move(retrySubscribeScreenUnlockedEventTask),
        ffrt::task_attr().delay(delaytime).name("RetrySubscribeUnlockedEvent")
        .timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));
}

void AbilityManagerService::RemoveScreenUnlockInterceptor()
{
    if (interceptorExecuter_ != nullptr) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "SU life, end");
        interceptorExecuter_->RemoveInterceptor("ScreenUnlock");
    }
}

void AbilityManagerService::RemoveUnauthorizedLaunchReasonMessage(const Want &want, AbilityRequest &abilityRequest,
    uint32_t callerTokenId)
{
    std::string value = want.GetStringParam(Want::PARM_LAUNCH_REASON_MESSAGE);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "launchReasonMessage:%{public}s", value.c_str());
    if (!AppUtils::GetInstance().IsSystemReasonMessage(value)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "not allow, remove");
        (const_cast<Want &>(want)).RemoveParam(Want::PARM_LAUNCH_REASON_MESSAGE);
        abilityRequest.want.RemoveParam(Want::PARM_LAUNCH_REASON_MESSAGE);
        return;
    }
    if (!PermissionVerification::GetInstance()->VerifyPermissionByTokenId(callerTokenId,
        PermissionConstants::PERMISSION_SET_LAUNCH_REASON_MESSAGE) ||
        (!PermissionVerification::GetInstance()->IsSystemAppCall() &&
        !PermissionVerification::GetInstance()->IsSACall())) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "verifyPermission failed, remove launch reason message.");
        (const_cast<Want &>(want)).RemoveParam(Want::PARM_LAUNCH_REASON_MESSAGE);
        abilityRequest.want.RemoveParam(Want::PARM_LAUNCH_REASON_MESSAGE);
    }
}

void AbilityManagerService::ConnectServices()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "waiting appMgr service run completed");
    while (!DelayedSingleton<AppScheduler>::GetInstance()->Init(shared_from_this())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed init appScheduler");
        usleep(REPOLL_TIME_MICRO_SECONDS);
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "waiting bundleMgr service run completed");
    while (AbilityUtil::GetBundleManagerHelper() == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get bundle manager helper failed");
        usleep(REPOLL_TIME_MICRO_SECONDS);
    }
    AbilityUtil::GetBundleManagerHelper()->ConnectTillSuccess();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "bms success");
}

int AbilityManagerService::GetWantSenderInfo(const sptr<IWantSender> &target, std::shared_ptr<WantSenderInfo> &info)
{
    TAG_LOGI(AAFwkTag::WANTAGENT, "get pending request info");
    auto pendingWantManager = GetCurrentPendingWantManager();
    CHECK_POINTER_AND_RETURN(pendingWantManager, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(target, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(info, ERR_INVALID_VALUE);
    return pendingWantManager->GetWantSenderInfo(target, info);
}

int AbilityManagerService::GetAppMemorySize()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "service getAppMemorySize start");
    const char *key = "const.product.arkheaplimit";
    const char *def = "512m";
    char *valueGet = nullptr;
    unsigned int len = 128;
    int ret = GetParameter(key, def, valueGet, len);
    int resultInt = 0;
    if ((ret != GET_PARAMETER_OTHER) && (ret != GET_PARAMETER_INCORRECT)) {
        if (valueGet == nullptr) {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "%{public}s, valueGet null", __func__);
            return APP_MEMORY_SIZE;
        }
        int len = strlen(valueGet);
        for (int i = 0; i < len; i++) {
            if (valueGet[i] >= '0' && valueGet[i] <= '9') {
                resultInt *= SIZE_10;
                resultInt += valueGet[i] - '0';
            }
        }
        if (resultInt == 0) {
            return APP_MEMORY_SIZE;
        }
        return resultInt;
    }
    return APP_MEMORY_SIZE;
}

bool AbilityManagerService::IsRamConstrainedDevice()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "service IsRamConstrainedDevice start");
    const char *key = "const.product.islowram";
    const char *def = "0";
    char *valueGet = nullptr;
    unsigned int len = 128;
    int ret = GetParameter(key, def, valueGet, len);
    if ((ret != GET_PARAMETER_OTHER) && (ret != GET_PARAMETER_INCORRECT)) {
        int value = atoi(valueGet);
        if (value) {
            return true;
        }
        return false;
    }
    return false;
}

int32_t AbilityManagerService::GetMissionIdByAbilityToken(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return -1;
    }
    if (!JudgeSelfCalled(abilityRecord)) {
        return -1;
    }
    return GetMissionIdByAbilityTokenInner(token);
}

int32_t AbilityManagerService::GetMissionIdByAbilityTokenInner(const sptr<IRemoteObject> &token)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return -1;
    }
    auto userId = abilityRecord->GetOwnerMissionUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->GetSessionIdByAbilityToken(token);
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null mission userId=%{public}d", userId);
        return -1;
    }
    return missionListManager->GetMissionIdByAbilityToken(token);
}

sptr<IRemoteObject> AbilityManagerService::GetAbilityTokenByMissionId(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto missionListManager = GetCurrentMissionListManager();
    if (!missionListManager) {
        return nullptr;
    }
    return missionListManager->GetAbilityTokenByMissionId(missionId);
}

int AbilityManagerService::StartRemoteAbilityByCall(const Want &want, const sptr<IRemoteObject> &callerToken,
    const sptr<IRemoteObject> &connect)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s begin startRemoteAbilityByCall", __func__);
    Want remoteWant = want;
    UpdateCallerInfoUtil::GetInstance().UpdateDmsCallerInfo(remoteWant, callerToken);
    if (AddStartControlParam(remoteWant, callerToken) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s addStartControlParam failed", __func__);
        return ERR_INVALID_VALUE;
    }
    int32_t missionId = -1;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        missionId = GetMissionIdByAbilityTokenInner(callerToken);
        if (!missionId) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid missionId id");
            return ERR_INVALID_VALUE;
        }
    } else {
        missionId = GetMissionIdByAbilityToken(callerToken);
}
    if (missionId < 0) {
        return ERR_INVALID_VALUE;
    }
    remoteWant.SetParam(DMS_MISSION_ID, missionId);
    DistributedClient dmsClient;
    return dmsClient.StartRemoteAbilityByCall(remoteWant, connect);
}

int AbilityManagerService::ReleaseRemoteAbility(const sptr<IRemoteObject> &connect,
    const AppExecFwk::ElementName &element)
{
    DistributedClient dmsClient;
    return dmsClient.ReleaseRemoteAbility(connect, element);
}

int AbilityManagerService::StartAbilityByCall(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<IRemoteObject> &callerToken, int32_t accountId, bool isSilent, bool promotePriority,
    bool isVisible)
{
    std::string errMsg;
    return StartAbilityByCallWithErrMsg(want, connect, callerToken, accountId, errMsg, isSilent, promotePriority,
        isVisible);
}

int AbilityManagerService::StartAbilityByCallWithErrMsg(const Want &want, const sptr<IAbilityConnection> &connect,
    const sptr<IRemoteObject> &callerToken, int32_t accountId, std::string &errMsg, bool isSilent,
    bool promotePriority, bool isVisible)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS_IGNORE(__PRETTY_FUNCTION__, !want.GetElement().GetDeviceID().empty());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call");
    int paramCheckResult = AbilityStartByCallHelper::CheckParam(connect, errMsg);
    if (paramCheckResult != ERR_OK) {
        return paramCheckResult;
    }

    if (IsCrossUserCall(accountId)) {
        CHECK_CALLER_IS_SYSTEM_APP;
    }

    if (VerifyAccountPermission(accountId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: permission verification failed", __func__);
        errMsg = "verify account permission failed";
        return CHECK_PERMISSION_FAILED;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord && !JudgeSelfCalled(abilityRecord)) {
        errMsg = "verify account permission failed";
        return CHECK_PERMISSION_FAILED;
    }

    AbilityUtil::RemoveWantKey(const_cast<Want &>(want));
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        errMsg = "app index is error";
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    if (accountId == U0_USER_ID) {
        accountId = DEFAULT_INVAL_VALUE;
    }
    int32_t oriValidUserId = GetValidUserId(accountId);
    auto checkRet = AbilityPermissionUtil::GetInstance().CheckMultiInstanceAndAppClone(const_cast<Want &>(want),
        oriValidUserId, appIndex, callerToken, false);
    if (checkRet != ERR_OK) {
        return checkRet;
    }

#ifdef SUPPORT_SCREEN
    DmsUtil::GetInstance().UpdateFlagForCollaboration(want);
#endif

    StartAbilityInfoWrap threadLocalInfo(want, oriValidUserId, appIndex, callerToken);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    bool isWithUI = want.GetBoolParam(Want::PARAM_RESV_CALL_TO_FOREGROUND, false) ? true : !isSilent;
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, 0, oriValidUserId, isWithUI, nullptr,
        shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error");
        return result;
    }

    if (CheckIfOperateRemote(want)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "start remote ability by call");
        return StartRemoteAbilityByCall(want, callerToken, connect->AsObject());
    }

    if (!JudgeMultiUserConcurrency(oriValidUserId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied");
        return ERR_CROSS_USER;
    }

    AbilityRequest abilityRequest;
    abilityRequest.callType = AbilityCallType::CALL_REQUEST_TYPE;
    abilityRequest.callerUid = IPCSkeleton::GetCallingUid();
    abilityRequest.callerToken = callerToken;
    abilityRequest.want = want;
    abilityRequest.connect = connect;
    abilityRequest.promotePriority = PermissionVerification::GetInstance()->IsSACall() && promotePriority;
    result = GenerateAbilityRequest(want, -1, abilityRequest, callerToken, oriValidUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request error");
        return result;
    }

    abilityRequest.userId = oriValidUserId;
    if (!HandleExecuteSAInterceptor(want, callerToken, abilityRequest, result)) {
        return result;
    }

    if (!abilityRequest.abilityInfo.isStageBasedModel) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability not stage base model");
        return RESOLVE_CALL_ABILITY_VERSION_ERR;
    }

    result = CheckStartByCallPermission(abilityRequest);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStartByCallPermission fail, result:%{public}d", result);
        errMsg = "CheckStartByCallPermission failed";
        return result;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "abilityInfo.applicationInfo.singleton is %{public}s",
        abilityRequest.abilityInfo.applicationInfo.singleton ? "true" : "false");
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(abilityRequest.want, 0, oriValidUserId,
        isVisible, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityRequest.abilityInfo), false, appIndex);
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    if (result != ERR_OK) {
        errMsg = "afterCheckParam is nullptr";
        TAG_LOGE(AAFwkTag::ABILITYMGR, "afterCheckExecuter_ null or doProcess error");
        return result;
    }
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(want, abilityRequest, callerTokenId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
        auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
        if (uiAbilityManager == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "uiAbilityManager null, userId is invalid:%{public}d", oriValidUserId);
            errMsg = "uiAbilityManager null, userId is invalid";
            return ERR_INVALID_VALUE;
        }
        return uiAbilityManager->ResolveLocked(abilityRequest, errMsg);
    }

    auto missionListMgr = GetMissionListManagerByUserId(oriValidUserId);
    if (missionListMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListMgr null designated user id=%{public}d", oriValidUserId);
        errMsg = "userId is not invalid";
        return ERR_INVALID_VALUE;
    }
    ReportEventToRSS(abilityRequest.abilityInfo, callerToken);

    return missionListMgr->ResolveLocked(abilityRequest);
}

int AbilityManagerService::StartAbilityForPrelaunch(const Want &want, const int32_t frameNum)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call");
    if (IPCSkeleton::GetCallingUid() != RSS_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uid check fail");
        return RESOLVE_CALL_NO_PERMISSIONS;
    }
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "SceneBoard not Enabled");
        return ERR_INVALID_VALUE;
    }
    int32_t oriValidUserId = GetValidUserId(DEFAULT_INVAL_VALUE);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, 0, oriValidUserId, true, nullptr,
        shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error");
        return result;
    }
    AbilityRequest abilityRequest;
    abilityRequest.callType = AbilityCallType::CALL_REQUEST_TYPE;
    abilityRequest.callerUid = IPCSkeleton::GetCallingUid();
    abilityRequest.startSetting = nullptr;
    abilityRequest.want = want;
    result = GenerateAbilityRequest(want, -1, abilityRequest, nullptr, oriValidUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request error");
        return result;
    }

    abilityRequest.userId = oriValidUserId;
    if (!HandleExecuteSAInterceptor(want, nullptr, abilityRequest, result)) {
        return result;
    }

    if (!abilityRequest.abilityInfo.isStageBasedModel) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target ability not stage base model");
        return RESOLVE_CALL_ABILITY_VERSION_ERR;
    }
    if (abilityRequest.abilityInfo.type != AppExecFwk::AbilityType::PAGE ||
        abilityRequest.abilityInfo.launchMode == AppExecFwk::LaunchMode::SPECIFIED ||
        abilityRequest.abilityInfo.isolationProcess) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not support prelaunch");
        return RESOLVE_CALL_ABILITY_TYPE_ERR;
    }
    result = CheckStartByCallPermission(abilityRequest);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStartByCallPermission fail, result:%{public}d", result);
        return result;
    }
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, nullptr);

    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    RemoveUnauthorizedLaunchReasonMessage(want, abilityRequest, callerTokenId);
    abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
    auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
    if (uiAbilityManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uiAbilityManager null, userId is invalid:%{public}d", oriValidUserId);
        return ERR_INVALID_VALUE;
    }
    return uiAbilityManager->PrelaunchAbilityLocked(abilityRequest, frameNum);
}

int AbilityManagerService::StartAbilityJust(AbilityRequest &abilityRequest, int32_t validUserId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call");
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, abilityRequest.callerToken);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(validUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        std::string errMsg;
        return uiAbilityManager->ResolveLocked(abilityRequest, errMsg);
    }

    auto missionListMgr = GetMissionListManagerByUserId(validUserId);
    if (missionListMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListMgr null designated userId=%{public}d", validUserId);
        return ERR_INVALID_VALUE;
    }
    ReportEventToRSS(abilityRequest.abilityInfo, abilityRequest.callerToken);

    return missionListMgr->ResolveLocked(abilityRequest);
}

int AbilityManagerService::ReleaseCall(
    const sptr<IAbilityConnection> &connect, const AppExecFwk::ElementName &element)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Release called ability.");

    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    CHECK_POINTER_AND_RETURN(connect->AsObject(), ERR_INVALID_VALUE);

    std::string elementName = element.GetURI();
    TAG_LOGD(AAFwkTag::ABILITYMGR, "try to release called ability, name: %{public}s.", elementName.c_str());

    if (CheckIsRemote(element.GetDeviceID())) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "release remote ability");
        return ReleaseRemoteAbility(connect->AsObject(), element);
    }

    int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->ReleaseCallLocked(connect, element);
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    return missionListManager->ReleaseCallLocked(connect, element);
}

int AbilityManagerService::JudgeAbilityVisibleControl(const AppExecFwk::AbilityInfo &abilityInfo)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call.");
    if (abilityInfo.visible) {
        return ERR_OK;
    }
    auto callerTokenId = IPCSkeleton::GetCallingTokenID();
    if (callerTokenId == abilityInfo.applicationInfo.accessTokenId ||
        callerTokenId == static_cast<uint32_t>(IPCSkeleton::GetSelfTokenID())) {  // foundation call is allowed
        return ERR_OK;
    }
    if (AccessTokenKit::VerifyAccessToken(callerTokenId,
        PermissionConstants::PERMISSION_START_INVISIBLE_ABILITY, false) == AppExecFwk::Constants::PERMISSION_GRANTED) {
        return ERR_OK;
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken:%{private}u, targetToken:%{private}u, caller without permission",
        callerTokenId, abilityInfo.applicationInfo.accessTokenId);
    return ABILITY_VISIBLE_FALSE_DENY_REQUEST;
}

int AbilityManagerService::StartUser(int userId, uint64_t displayId, sptr<IUserCallback> callback, bool isAppRecovery)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "startUser in service:%{public}d, displayId:%{public}" PRIu64"", userId, displayId);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);

    CHECK_POINTER_AND_RETURN_LOG(callback, INVALID_PARAMETERS_ERR, "startUser callback is nullptr");
    auto checkRet = AbilityRuntime::UserController::GetInstance().CheckUserParam(userId);
    if (checkRet != ERR_OK) {
        callback->OnStartUserDone(userId, checkRet);
        return checkRet;
    }

    if (userId == U1_USER_ID) {
        UserStarted(userId);
        callback->OnStartUserDone(userId, ERR_OK);
        return ERR_OK;
    }
    if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId, displayId)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "StartUser current:%{public}d", userId);
        callback->OnStartUserDone(userId, ERR_OK);
        return ERR_OK;
    }

    if (ShouldBlockAllAppStart() && callback != nullptr) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "low-mem mode, disallow");
        callback->OnStartUserDone(userId, ERR_ALL_APP_START_BLOCKED);
        return ERR_ALL_APP_START_BLOCKED;
    }
    // Lister screen unlock for auto startup apps.
    if (AppUtils::GetInstance().IsProductAppbootSettingEnabled() && abilityAutoStartupService_ &&
        !abilityAutoStartupService_->FindHandledAutoStartupUsers(userId)) {
        InitInterceptorForScreenUnlock();
        SubscribeScreenUnlockedEvent();
    }

    DelayedSingleton<AppScheduler>::GetInstance()->SetEnableStartProcessFlagByUserId(userId, true);
    auto oldUserId = AbilityRuntime::UserController::GetInstance().GetForegroundUserId(displayId);
    // True indicates that a user has been created on this displayId, false indicates that no user has been created
    auto hasDisplayId = AbilityRuntime::UserController::GetInstance().IsExistDisplayId(displayId);
    if (oldUserId != U0_USER_ID && !Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        // start freezing screen
        AbilityRuntime::UserController::GetInstance().SetFreezingNewUserId(userId);
        StartFreezingScreen();
        auto stopFreezingScreenTask = [weak = weak_from_this()]() {
            auto abilityMgr = weak.lock();
            if (abilityMgr == nullptr) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "ability manager instance null");
                return;
            }
            abilityMgr->StopFreezingScreen();
        };
        if (taskHandler_) {
            taskHandler_->SubmitTask(stopFreezingScreenTask, "StopFreezingScreen", USER_SWITCH_TIMEOUT);
        }
    }

    AbilityRuntime::UserController::GetInstance().SetForegroundUserId(userId, displayId);
    auto ret = SwitchToUser(oldUserId, userId, displayId, callback, isAppRecovery);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "SwitchToUser filed, oldUserId:%{public}d, hasDisplayId:%{public}d", oldUserId, hasDisplayId);
        if (hasDisplayId) {
            AbilityRuntime::UserController::GetInstance().SetForegroundUserId(oldUserId, displayId);
        } else {
            AbilityRuntime::UserController::GetInstance().ClearDisplayId(displayId);
        }
    }
    return ret;
}

int AbilityManagerService::StopUser(int userId, const sptr<IUserCallback> &callback)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "stopUser in service:%{public}d", userId);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (callback == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "stopUser callback is nullptr");
        return INVALID_PARAMETERS_ERR;
    }

    auto checkRet = AbilityRuntime::UserController::GetInstance().CheckStopUserParam(userId);
    if (checkRet != ERR_OK) {
        callback->OnStopUserDone(userId, checkRet);
        return checkRet;
    }

    // clear userInfo for autoStartup
    if (AppUtils::GetInstance().IsProductAppbootSettingEnabled() && abilityAutoStartupService_) {
        abilityAutoStartupService_->RemoveHandledAutoStartupUsers(userId);
    }
    AbilityRuntime::AbilityEventMapManager::GetInstance().RemoveUser(userId);

    if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId)) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "user current:%{public}d", userId);
        callback->OnStopUserDone(userId, ERR_OK);
        return ERR_OK;
    }
    DelayedSingleton<AppScheduler>::GetInstance()->KillProcessesByUserId(userId);

    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto missionListWrap = GetMissionListWrap();
        if (!missionListWrap) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListWrap null");
            callback->OnStopUserDone(userId, -1);
            return -1;
        }
        missionListWrap->RemoveUserDir(userId);
    }
    ClearUserData(userId);
    AbilityRuntime::UserController::GetInstance().ClearUserId(userId);
    callback->OnStopUserDone(userId, ERR_OK);
    UpdateApplicationKeepAlive(userId);
    return ERR_OK;
}

int32_t AbilityManagerService::UpdateApplicationKeepAlive(int32_t userId) const
{
    if (!system::GetBoolParameter(PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED, false)) {
        return 0;
    }
    IN_PROCESS_CALL_WITHOUT_RET(KeepAliveProcessManager::GetInstance().ClearKeepAliveAppServiceExtension(userId));
    std::vector<AppExecFwk::BundleInfo> bundleInfos;
    if (!KeepAliveProcessManager::GetInstance().GetKeepAliveBundleInfosForUser(bundleInfos, userId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get keep-alive bundle info failed");
        return 0;
    }
    for (const auto &bundleInfo : bundleInfos) {
        IN_PROCESS_CALL_WITHOUT_RET(KeepAliveProcessManager::GetInstance().SetApplicationKeepAlive(
            bundleInfo.name, userId, false, true, false));
        if (userId == U1_USER_ID) {
            IN_PROCESS_CALL_WITHOUT_RET(KeepAliveProcessManager::GetInstance().SetAppServiceExtensionKeepAlive(
                bundleInfo.name, false, true, false));
        }
    }
    return ERR_OK;
}

int AbilityManagerService::LogoutUser(int32_t userId, sptr<IUserCallback> callback)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "LogoutUser in service:%{public}d", userId);
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (callback == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "logoutUser callback is nullptr");
        return INVALID_PARAMETERS_ERR;
    }
    auto checkRet = AbilityRuntime::UserController::GetInstance().CheckUserParam(userId);
    if (checkRet != ERR_OK) {
        callback->OnLogoutUserDone(userId, checkRet);
        return checkRet;
    }
    // clear userInfo for autoStartup
    if (AppUtils::GetInstance().IsProductAppbootSettingEnabled() && abilityAutoStartupService_) {
        InitInterceptorForScreenUnlock();
        abilityAutoStartupService_->RemoveHandledAutoStartupUsers(userId);
    }
    AbilityRuntime::AbilityEventMapManager::GetInstance().RemoveUser(userId);

    RemoveLauncherDeathRecipient(userId);
    ClearUserData(userId);
    DelayedSingleton<AppScheduler>::GetInstance()->SetEnableStartProcessFlagByUserId(userId, false);
    AbilityRuntime::UserController::GetInstance().ClearUserId(userId);
    DelayedSingleton<AppScheduler>::GetInstance()->KillProcessesByUserId(userId,
        system::GetBoolParameter(DEVELOPER_MODE_STATE, false), callback);
    return ERR_OK;
}

void AbilityManagerService::OnAcceptWantResponse(
    const AAFwk::Want &want, const std::string &flag, int32_t requestId, int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "OnAcceptWantResponse userId:%{public}d", userId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnAcceptWantResponse(want, flag, requestId);
        return;
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        return;
    }
    missionListManager->OnAcceptWantResponse(want, flag);
}

void AbilityManagerService::OnStartSpecifiedAbilityTimeoutResponse(int32_t requestId, int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "OnStartSpecifiedAbilityTimeoutResponse %{public}d, userId:%{public}d",
        requestId, userId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnStartSpecifiedAbilityTimeoutResponse(requestId);
        return;
    }
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        return;
    }
    missionListManager->OnStartSpecifiedAbilityTimeoutResponse();
}

void AbilityManagerService::OnStartSpecifiedProcessResponse(const std::string &flag, int32_t userId, int32_t requestId,
    const std::string &callerProcessName, int32_t recordId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "flag = %{public}s", flag.c_str());
    auto connectManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER(connectManager);
    if (connectManager->HasRequestIdInLoadAbilityQueue(requestId)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "uiextension StartSpecifiedProcessResponse, requestId = %{public}d", requestId);
        DelayedSingleton<AppScheduler>::GetInstance()->SetSpecifiedProcessRequestId(recordId, -1);
        connectManager->OnStartSpecifiedProcessResponse(flag, requestId);
        return;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnStartSpecifiedProcessResponse(flag, requestId, callerProcessName, recordId);
        return;
    }
}

void AbilityManagerService::OnStartSpecifiedProcessTimeoutResponse(int32_t requestId, int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "OnStartSpecifiedProcessTimeoutResponse %{public}d", requestId);
    auto connectManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER(connectManager);
    if (connectManager->HasRequestIdInLoadAbilityQueue(requestId)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "uiextension StartSpecifiedProcessTimeoutResponse");
        connectManager->OnStartSpecifiedProcessTimeoutResponse(requestId);
        return;
    }
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnStartSpecifiedProcessTimeoutResponse(requestId);
        return;
    }
}

void AbilityManagerService::OnStartSpecifiedFailed(int32_t requestId, int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "On accept want response");
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->OnStartSpecifiedFailed(requestId);
    }
}

int AbilityManagerService::GetAbilityRunningInfos(std::vector<AbilityRunningInfo> &info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Get running ability infos.");
    auto isPerm = AAFwk::PermissionVerification::GetInstance()->VerifyRunningInfoPerm();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        uiAbilityManager->GetAbilityRunningInfos(info, isPerm);
    } else {
        auto missionListManager = GetCurrentMissionListManager();
        CHECK_POINTER_AND_RETURN(missionListManager, ERR_INVALID_VALUE);
        missionListManager->GetAbilityRunningInfos(info, isPerm);
    }

    UpdateFocusState(info);

    return ERR_OK;
}

void AbilityManagerService::UpdateFocusState(std::vector<AbilityRunningInfo> &info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (info.empty()) {
        return;
    }

#ifdef SUPPORT_GRAPHICS
    sptr<IRemoteObject> token;
    int ret = IN_PROCESS_CALL(GetTopAbility(token));
    if (ret != ERR_OK || token == nullptr) {
        return;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (abilityRecord == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "%{public}s abilityRecord null", __func__);
        return;
    }

    for (auto &item : info) {
        if (item.uid == abilityRecord->GetUid() && item.pid == abilityRecord->GetPid() &&
            item.ability == abilityRecord->GetElementName()) {
            item.abilityState = static_cast<int>(AbilityState::ACTIVE);
            break;
        }
    }
#endif
}

int AbilityManagerService::GetExtensionRunningInfos(int upperLimit, std::vector<ExtensionRunningInfo> &info)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Get extension infos, upperLimit : %{public}d", upperLimit);
    CHECK_CALLER_IS_SYSTEM_APP;
    auto isPerm = AAFwk::PermissionVerification::GetInstance()->VerifyRunningInfoPerm();
    std::vector<int32_t> userIds;
    AbilityRuntime::UserController::GetInstance().GetAllForegroundUserId(userIds);
    auto iter = userIds.begin();
    while (iter != userIds.end()) {
        AbilityConnectManager::ServiceMapType serviceMap;
        auto ret = GetServiceMapByUserId(serviceMap, *iter);
        if (ret != ERR_OK) {
            return ret;
        }
        AbilityConnectManager::GetExtensionRunningInfos(serviceMap, upperLimit, info, *iter, isPerm);
        iter++;
    }
    return ERR_OK;
}

int AbilityManagerService::GetProcessRunningInfos(std::vector<AppExecFwk::RunningProcessInfo> &info)
{
    return DelayedSingleton<AppScheduler>::GetInstance()->GetProcessRunningInfos(info);
}

int32_t AbilityManagerService::GetAllIntentExemptionInfo(std::vector<AppExecFwk::IntentExemptionInfo> &info)
{
    const auto exemptionData =
        DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->GetAllIntentExemptionInfo();
    for (auto& data : exemptionData) {
        AppExecFwk::IntentExemptionInfo tmpInfo;
        tmpInfo.uid_ = data.first;
        tmpInfo.duration_ = INTENT_EXEMPTION_DURATION;
        info.push_back(tmpInfo);
    }
    return ERR_OK;
}

int AbilityManagerService::GetProcessRunningInfosByUserId(
    std::vector<AppExecFwk::RunningProcessInfo> &info, int32_t userId)
{
    return DelayedSingleton<AppScheduler>::GetInstance()->GetProcessRunningInfosByUserId(info, userId);
}

void AbilityManagerService::ClearUserData(int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    // notify disconnect done to callers before clear connectManager's user data
    DisconnectBeforeCleanupByUserId(userId);
    CHECK_POINTER(subManagersHelper_);
    subManagersHelper_->ClearSubManagers(userId);
}

void AbilityManagerService::DisconnectBeforeCleanupByUserId(int32_t userId) {
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s", __func__);

    TAG_LOGI(AAFwkTag::ABILITYMGR, "handle all abilities die before clear data, userId:%{public}d", userId);
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER(commonExtensionManager);
    commonExtensionManager->DisconnectBeforeCleanup();
    
    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER(uiExtensionAbilityManager);
    uiExtensionAbilityManager->DisconnectBeforeCleanup();
}

int AbilityManagerService::RegisterSnapshotHandler(const sptr<ISnapshotHandler>& handler)
{
    if (IPCSkeleton::GetCallingUid() != SAMGR_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "register snapshot handler permission fail:%{public}d",
            IPCSkeleton::GetCallingUid());
        return CHECK_PERMISSION_FAILED;
    }

    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, INNER_ERR);
    missionListManager->RegisterSnapshotHandler(handler);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "snapshot: abilityManagerService register snapshot handler success");
    return ERR_OK;
}

int32_t AbilityManagerService::GetMissionSnapshot(const std::string& deviceId, int32_t missionId,
    MissionSnapshot& missionSnapshot, bool isLowResolution)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyMissionPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s: permission verification failed", __func__);
        return CHECK_PERMISSION_FAILED;
    }

    if (CheckIsRemote(deviceId)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "get remote mission snapshot");
        return GetRemoteMissionSnapshotInfo(deviceId, missionId, missionSnapshot);
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "get local mission snapshot");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, INNER_ERR);
    bool result = missionListManager->GetMissionSnapshot(missionId, missionSnapshot, isLowResolution);
    if (!result) {
        return INNER_ERR;
    }
    return ERR_OK;
}
#ifdef SUPPORT_SCREEN
void AbilityManagerService::UpdateMissionSnapShot(const sptr<IRemoteObject> &token,
    const std::shared_ptr<Media::PixelMap> &pixelMap)
{
    if (!IS_FOUNDATION_CALL) {
        return;
    }
    auto missionListManager = GetCurrentMissionListManager();
    if (missionListManager) {
        missionListManager->UpdateSnapShot(token, pixelMap);
    }
}
#endif // SUPPORT_SCREEN
void AbilityManagerService::EnableRecoverAbility(const sptr<IRemoteObject>& token)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Enable recovery ability.");
    if (token == nullptr) {
        return;
    }
    auto record = Token::GetAbilityRecordByToken(token);
    if (record == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s appRecovery::failed find abilityRecord by token", __func__);
        return;
    }
    if (record->IsClearMissionFlag()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s appRecovery::not allow EnableRecoverAbility before clearMission",
            __func__);
        return;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = record->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appRecovery scheduleRecoverAbility not self, not enabled");
        return;
    }
    {
        std::lock_guard<ffrt::mutex> guard(globalLock_);
        auto it = appRecoveryHistory_.find(record->GetUid());
        if (it == appRecoveryHistory_.end()) {
            appRecoveryHistory_.emplace(record->GetUid(), 0);
        }
    }
    auto userId = record->GetOwnerMissionUserId();
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        const auto& abilityInfo = record->GetAbilityInfo();
        std::string abilityName = abilityInfo.name;
        auto sessionId = uiAbilityManager->GetSessionIdByAbilityToken(token);
        if (abilityInfo.launchMode == AppExecFwk::LaunchMode::STANDARD) {
            abilityName += std::to_string(sessionId);
        }
        (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->AddAbilityRecoverInfo(
            abilityInfo.applicationInfo.accessTokenId, abilityInfo.moduleName, abilityName, sessionId);
    } else {
        auto missionListMgr = GetMissionListManagerByUserId(userId);
        if (missionListMgr == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListMgr null");
            return;
        }
        missionListMgr->EnableRecoverAbility(record->GetMissionId());
    }
}

void AbilityManagerService::ScheduleClearRecoveryPageStack()
{
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    std::string bundleName;
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_IS_NULLPTR(bms);

    if (IN_PROCESS_CALL(bms->GetNameForUid(callerUid, bundleName)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "scheduleClearRecoveryPageStack get bundleName failed");
        return;
    }

    auto tokenId = IPCSkeleton::GetCallingTokenID();

    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "ScheduleClearRecoveryPageStack bundleName = %{public}s, callerUid = %{public}d, tokenId = %{public}d",
        bundleName.c_str(), callerUid, tokenId);
    (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->
        DeleteAppExitReason(bundleName, tokenId);
    (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->
        DeleteAllRecoverInfoByTokenId(tokenId);
}

void AbilityManagerService::ReportAppRecoverResult(const int32_t appId, const AppExecFwk::ApplicationInfo &appInfo,
    const std::string& abilityName, const std::string& result)
{
    auto hisyseventReport = std::make_shared<HisyseventReport>(6);
    hisyseventReport->InsertParam("APP_UID", appId);
    hisyseventReport->InsertParam("VERSION_CODE", std::to_string(appInfo.versionCode));
    hisyseventReport->InsertParam("VERSION_NAME", appInfo.versionName);
    hisyseventReport->InsertParam("BUNDLE_NAME", appInfo.bundleName);
    hisyseventReport->InsertParam("ABILITY_NAME", abilityName);
    hisyseventReport->InsertParam("RECOVERY_RESULT", result);
    int32_t ret = hisyseventReport->Report("AAFWK", "APP_RECOVERY", HISYSEVENT_BEHAVIOR);
}

void AbilityManagerService::SubmitSaveRecoveryInfo(const sptr<IRemoteObject>& token)
{
    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "submitInfo token null");
        return;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "submitInfo abilityRecord null");
        return;
    }
    auto abilityInfo = abilityRecord->GetAbilityInfo();
    auto userId = abilityRecord->GetOwnerMissionUserId();
    auto tokenId = abilityRecord->GetApplicationInfo().accessTokenId;
    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    if (callingTokenId != tokenId) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "SubmitSaveRecoveryInfo not self, not enabled");
        return;
    }
    std::string abilityName = abilityInfo.name;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER(uiAbilityManager);
        auto sessionId = uiAbilityManager->GetSessionIdByAbilityToken(token);
        if (abilityInfo.launchMode == AppExecFwk::LaunchMode::STANDARD) {
            abilityName += std::to_string(sessionId);
        }
    } else {
        auto missionListMgr = GetMissionListManagerByUserId(userId);
        if (missionListMgr == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListMgr null");
            return;
        }
        abilityName += std::to_string(abilityRecord->GetMissionId());
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "submitInfo bundleName = %{public}s, moduleName = %{public}s, abilityName = %{public}s, tokenId = %{public}d",
        abilityInfo.bundleName.c_str(),  abilityInfo.moduleName.c_str(), abilityName.c_str(), tokenId);
    RecoveryInfo recoveryInfo;
    recoveryInfo.bundleName = abilityInfo.bundleName;
    recoveryInfo.moduleName = abilityInfo.moduleName;
    recoveryInfo.abilityName = abilityName;
    recoveryInfo.time = time(nullptr);
    OHOS::AAFwk::RecoveryInfoTimer::GetInstance().SubmitSaveRecoveryInfo(recoveryInfo);
}

void AbilityManagerService::AppRecoverKill(pid_t pid, int32_t reason)
{
    AppExecFwk::AppFaultDataBySA faultDataSA;
    faultDataSA.errorObject.name = "appRecovery";
    switch (reason) {
        case AppExecFwk::StateReason::CPP_CRASH:
            faultDataSA.faultType = AppExecFwk::FaultDataType::CPP_CRASH;
            break;
        case AppExecFwk::StateReason::JS_ERROR:
            faultDataSA.faultType = AppExecFwk::FaultDataType::JS_ERROR;
            break;
        case AppExecFwk::StateReason::LIFECYCLE:
        case AppExecFwk::StateReason::APP_FREEZE:
            faultDataSA.faultType = AppExecFwk::FaultDataType::APP_FREEZE;
            break;
        default:
            faultDataSA.faultType = AppExecFwk::FaultDataType::UNKNOWN;
    }
    faultDataSA.pid = pid;
    IN_PROCESS_CALL(DelayedSingleton<AppExecFwk::AppMgrClient>::GetInstance()->NotifyAppFaultBySA(faultDataSA));
}

void AbilityManagerService::ScheduleRecoverAbility(const sptr<IRemoteObject>& token, int32_t reason, const Want *want)
{
    if (token == nullptr) {
        return;
    }
    auto record = Token::GetAbilityRecordByToken(token);
    if (record == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s appRecovery::failed find abilityRecord by token", __func__);
        return;
    }
    if (!record->IsForeground() && !record->GetAbilityForegroundingFlag()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s appRecovery::recoveryAbility failed"
            "due background", __func__);
        return;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = record->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appRecovery scheduleRecoverAbility no self, no enabled");
        return;
    }

    AAFwk::Want curWant;
    {
        std::lock_guard<ffrt::mutex> guard(globalLock_);
        auto type = record->GetAbilityInfo().type;
        if (type != AppExecFwk::AbilityType::PAGE) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s appRecovery::only recover for page ability", __func__);
            return;
        }

        constexpr int64_t MIN_RECOVERY_TIME = 60;
        int64_t now = time(nullptr);
        auto it = appRecoveryHistory_.find(record->GetUid());
        auto appInfo = record->GetApplicationInfo();
        auto abilityInfo = record->GetAbilityInfo();

        if ((it != appRecoveryHistory_.end()) &&
            (it->second + MIN_RECOVERY_TIME > now)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                "%{public}s appRecovery recover more once in one minute, kill app(%{public}d)",
                __func__, record->GetPid());
            ReportAppRecoverResult(record->GetUid(), appInfo, abilityInfo.name, "FAIL_WITHIN_ONE_MINUTE");
            AppRecoverKill(record->GetPid(), reason);
            return;
        }

        if (want != nullptr) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "BundleName:%{public}s targetBundleName:%{public}s.",
                appInfo.bundleName.c_str(), want->GetElement().GetBundleName().c_str());
            if (want->GetElement().GetBundleName().empty() ||
                (appInfo.bundleName.compare(want->GetElement().GetBundleName()) != 0)) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "appRecovery bundleName not match, not recovery ability");
                ReportAppRecoverResult(record->GetUid(), appInfo, abilityInfo.name, "FAIL_BUNDLE_NAME_NOT_MATCH");
                return;
            }
            if (want->GetElement().GetAbilityName().empty()) {
                TAG_LOGD(AAFwkTag::ABILITYMGR, "AppRecovery recovery target ability is empty");
                ReportAppRecoverResult(record->GetUid(), appInfo, abilityInfo.name, "FAIL_TARGET_ABILITY_EMPTY");
                return;
            }
            auto bms = AbilityUtil::GetBundleManagerHelper();
            CHECK_POINTER_IS_NULLPTR(bms);
            AppExecFwk::BundleInfo bundleInfo;
            auto bundleName = want->GetElement().GetBundleName();
            int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
            bool ret = IN_PROCESS_CALL(
                bms->GetBundleInfo(bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_WITH_ABILITIES, bundleInfo,
                userId));
            if (!ret) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "appRecovery get bundleInfo fail, not recovery");
                return;
            }
            bool isRestartPage = false;
            auto abilityName = want->GetElement().GetAbilityName();
            for (auto it = bundleInfo.abilityInfos.begin(); it != bundleInfo.abilityInfos.end(); ++it) {
                if ((abilityName.compare(it->name) == 0) && it->type == AppExecFwk::AbilityType::PAGE) {
                    isRestartPage = true;
                    break;
                }
            }
            if (!isRestartPage) {
                TAG_LOGI(AAFwkTag::ABILITYMGR, "appRecovery target ability type not PAGE");
                ReportAppRecoverResult(record->GetUid(), appInfo, abilityName, "FAIL_TARGET_ABILITY_NOT_PAGE");
                return;
            }
        }

        appRecoveryHistory_[record->GetUid()] = now;
        curWant = (want == nullptr) ? record->GetWant() : *want;
        if (curWant.GetBoolParam(AAFwk::Want::PARAM_ABILITY_RECOVERY_RESTART, true)) {
            curWant.SetParam(AAFwk::Want::PARAM_ABILITY_RECOVERY_RESTART, true);
        }

        ReportAppRecoverResult(record->GetUid(), appInfo, abilityInfo.name, "SUCCESS");
    }
    RestartApp(curWant, true);
}

int32_t AbilityManagerService::GetRemoteMissionSnapshotInfo(const std::string& deviceId, int32_t missionId,
    MissionSnapshot& missionSnapshot)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "getRemoteMissionSnapshotInfo");
    std::unique_ptr<MissionSnapshot> missionSnapshotPtr = std::make_unique<MissionSnapshot>();
    DistributedClient dmsClient;
    int result = dmsClient.GetRemoteMissionSnapshotInfo(deviceId, missionId, missionSnapshotPtr);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getRemoteMissionSnapshotInfo failed, result=%{public}d", result);
        return result;
    }
    missionSnapshot = *missionSnapshotPtr;
    return ERR_OK;
}

void AbilityManagerService::StartSwitchUserDialog()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start switch user dialog extension ability come");
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "scene board enabled, dialog not show");
        return;
    }

#ifdef SUPPORT_GRAPHICS
    auto sysDialog = DelayedSingleton<SystemDialogScheduler>::GetInstance();
    if (sysDialog == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "system dialog scheduler instance null");
        return;
    }

    Want dialogWant = sysDialog->GetSwitchUserDialogWant();
    StartSwitchUserDialogInner(dialogWant, AbilityRuntime::UserController::GetInstance().GetFreezingNewUserId());
#endif // SUPPORT_GRAPHICS
}


void AbilityManagerService::StartSwitchUserDialogInner(const Want &want, int32_t lastUserId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Start switch user dialog inner come");
    EventInfo eventInfo = BuildEventInfo(want, lastUserId);
    eventInfo.extensionType = static_cast<int32_t>(AppExecFwk::ExtensionAbilityType::SERVICE);
    AbilityRequest abilityRequest;
    auto result = GenerateExtensionAbilityRequest(want, abilityRequest, nullptr, lastUserId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return;
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    auto startUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    abilityRequest.userId = startUserId;
    result = CheckOptExtensionAbility(want, abilityRequest, startUserId, AppExecFwk::ExtensionAbilityType::SERVICE);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check extensionAbility type error");
        eventInfo.errCode = result;
        EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
        return;
    }

    auto connectManager = GetConnectManagerByUserId(startUserId, abilityInfo.extensionAbilityType);

    if (connectManager == nullptr) {
        CHECK_POINTER(subManagersHelper_);
        subManagersHelper_->InitUIExtensionAbilityManager(startUserId, false);
        subManagersHelper_->InitCommonExtensionManager(startUserId, false);
        connectManager = GetConnectManagerByUserId(startUserId, abilityInfo.extensionAbilityType);
        if (connectManager == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager null userId=%{public}d", startUserId);
            eventInfo.errCode = ERR_INVALID_VALUE;
            EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
            return;
        }
    }

    eventInfo.errCode = connectManager->StartAbility(abilityRequest);
    if (eventInfo.errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "eventInfo errCode:%{public}d", eventInfo.errCode);
        EventReport::SendExtensionEvent(EventName::START_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
}

void AbilityManagerService::StartFreezingScreen()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
#ifdef SUPPORT_GRAPHICS
    StartSwitchUserDialog();
    std::vector<Rosen::DisplayId> displayIds = Rosen::DisplayManager::GetInstance().GetAllDisplayIds();
    IN_PROCESS_CALL_WITHOUT_RET(Rosen::DisplayManager::GetInstance().Freeze(displayIds));
#endif
}

void AbilityManagerService::StopFreezingScreen()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
#ifdef SUPPORT_GRAPHICS
    std::vector<Rosen::DisplayId> displayIds = Rosen::DisplayManager::GetInstance().GetAllDisplayIds();
    IN_PROCESS_CALL_WITHOUT_RET(Rosen::DisplayManager::GetInstance().Unfreeze(displayIds));
    StopSwitchUserDialog();
#endif
}

void AbilityManagerService::UserStarted(int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    CHECK_POINTER(subManagersHelper_);
    subManagersHelper_->InitSubManagers(userId, false);
}

int AbilityManagerService::SwitchToUser(int32_t oldUserId, int32_t userId, uint64_t displayId,
    sptr<IUserCallback> callback, bool isAppRecovery)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "%{public}s, oldUserId:%{public}d, newUserId:%{public}d, isAppRecovery:%{public}d", __func__,
        oldUserId, userId, isAppRecovery);
    SwitchManagers(userId);
    int32_t ret = ERR_OK;
#ifndef DISABLE_LAUNCHER
    if (!StartUserApps(oldUserId)) {
        bool isBoot = oldUserId == U0_USER_ID ? true : false;
        ret = StartHighestPriorityAbility(userId, displayId, isBoot, isAppRecovery);
    }
#endif
    if (callback) {
        callback->OnStartUserDone(userId, ret);
    }
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartHighestPriorityAbility failed: %{public}d", ret);
        return ret;
    }
    if (taskHandler_) {
        taskHandler_->SubmitTask([abilityMs = shared_from_this(), userId]() {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "StartResidentApps userId:%{public}d", userId);
            abilityMs->StartResidentApps(userId);
        });
    }
    StartKeepAliveAppsInner(userId);
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled() &&
        AmsConfigurationParameter::GetInstance().MultiUserType() != 0) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "no need terminate old scb");
        return ret;
    }
    PauseOldConnectManager(oldUserId);
    return ret;
}

bool AbilityManagerService::IsSceneBoardReady(int32_t userId)
{
    auto connectManager = GetCommonExtensionManagerByUserId(userId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "connectManager is nullptr");
        return false;
    }
    if (connectManager->GetSceneBoardTokenId() == 0) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "SCB not ready");
        return false;
    }
    return true;
}

void AbilityManagerService::StartKeepAliveAppsInner(int32_t userId)
{
    if (!system::GetBoolParameter(PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not supported");
        return;
    }
    if (taskHandler_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "taskHandler nullptr");
        return;
    }
    taskHandler_->SubmitTask([abilityMs = shared_from_this(), userId] {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "StartKeepAliveApps userId:%{public}d", userId);
        abilityMs->StartKeepAliveApps(userId);
    });
}

void AbilityManagerService::SwitchManagers(int32_t userId, bool switchUser)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, SwitchManagers:%{public}d-----begin", __func__, userId);
    CHECK_POINTER(subManagersHelper_);
    subManagersHelper_->InitSubManagers(userId, switchUser);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, SwitchManagers:%{public}d-----end", __func__, userId);
}

void AbilityManagerService::PauseOldUser(int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldUser:%{public}d-----begin", __func__, userId);
    PauseOldMissionListManager(userId);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldUser:%{public}d-----end", __func__, userId);
}

void AbilityManagerService::PauseOldMissionListManager(int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldMissionListManager:%{public}d-----begin", __func__, userId);
    auto manager = GetMissionListManagerByUserId(userId);
    CHECK_POINTER(manager);
    manager->PauseManager();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldMissionListManager:%{public}d-----end", __func__, userId);
}

void AbilityManagerService::PauseOldConnectManager(int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldConnectManager:%{public}d-----begin", __func__, userId);
    if (userId == U0_USER_ID || userId == U1_USER_ID) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, u0 not stop, id:%{public}d-----null", __func__, userId);
        return;
    }

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER(commonExtensionManager);
    commonExtensionManager->PauseExtensions();

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER(uiExtensionAbilityManager);
    uiExtensionAbilityManager->PauseExtensions();
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, PauseOldConnectManager:%{public}d-----end", __func__, userId);
}

bool AbilityManagerService::StartUserApps(int32_t oldUserId)
{
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        PauseOldUser(oldUserId);
        ConnectServices();
        auto missionListManager = GetCurrentMissionListManager();
        if (missionListManager && missionListManager->IsStarted()) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "missionListManager ResumeManager");
            missionListManager->ResumeManager();
            return true;
        }
    }
    return false;
}

int32_t AbilityManagerService::GetValidUserId(int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId = %{public}d.", userId);
    return DEFAULT_INVAL_VALUE == userId ? AbilityRuntime::UserController::GetInstance().GetCallerUserId() : userId;
}

int AbilityManagerService::SetAbilityController(const sptr<IAbilityController> &abilityController,
    bool imAStabilityTest)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s, imAStabilityTest: %{public}d", __func__, imAStabilityTest);
    auto isPerm = AAFwk::PermissionVerification::GetInstance()->VerifyControllerPerm();
    if (!isPerm) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        return CHECK_PERMISSION_FAILED;
    }

    std::lock_guard<ffrt::mutex> guard(globalLock_);
    abilityController_ = abilityController;
    controllerIsAStabilityTest_ = imAStabilityTest;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s, end", __func__);
    return ERR_OK;
}

bool AbilityManagerService::IsRunningInStabilityTest()
{
    std::lock_guard<ffrt::mutex> guard(globalLock_);
    bool ret = abilityController_ != nullptr && controllerIsAStabilityTest_;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s, IsRunningInStabilityTest: %{public}d", __func__, ret);
    return ret;
}

bool AbilityManagerService::IsAbilityControllerStart(const Want &want, const std::string &bundleName)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "method call, controllerIsAStabilityTest_: %{public}d", controllerIsAStabilityTest_);
    if (abilityController_ == nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "abilityController_ is nullptr");
        return true;
    }

    if (controllerIsAStabilityTest_) {
        bool isStart = abilityController_->AllowAbilityStart(want, bundleName);
        if (!isStart) {
            TAG_LOGI(AAFwkTag::ABILITYMGR,
                "controller starting can't start ability:%{public}s", bundleName.c_str());
            return false;
        }
    }
    return true;
}

bool AbilityManagerService::IsAbilityControllerForeground(const std::string &bundleName)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "method call, controllerIsAStabilityTest_: %{public}d", controllerIsAStabilityTest_);
    if (abilityController_ == nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "abilityController_ is nullptr");
        return true;
    }

    if (controllerIsAStabilityTest_) {
        bool isResume = abilityController_->AllowAbilityBackground(bundleName);
        if (!isResume) {
            TAG_LOGI(AAFwkTag::ABILITYMGR,
                "controller resuming can't terminate ability:%{public}s", bundleName.c_str());
            return false;
        }
    }
    return true;
}

int AbilityManagerService::StartUserTest(const Want &want, const sptr<IRemoteObject> &observer)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "enter");
    if (observer == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "observer null");
        return ERR_INVALID_VALUE;
    }

    std::string bundleName = want.GetStringParam("-b");
    if (bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid bundle name");
        return ERR_INVALID_VALUE;
    }

    auto checkResult = AbilityUtil::CheckInstanceKey(want);
    if (checkResult != ERR_OK) {
        return checkResult;
    }
    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, nullptr, appIndex) || appIndex != 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Not support app clone");
        return ERR_NOT_SUPPORT_APP_CLONE;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, START_USER_TEST_FAIL);
    AppExecFwk::BundleInfo bundleInfo;
    int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    if (!IN_PROCESS_CALL(
        bms->GetBundleInfo(bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_DEFAULT, bundleInfo, U0_USER_ID))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get bundleInfo by U0_USER_ID %{public}d", U0_USER_ID);
        TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName: %{public}s, userId: %{public}d", bundleName.c_str(), userId);
        if (!IN_PROCESS_CALL(
            bms->GetBundleInfo(bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_DEFAULT, bundleInfo, userId))) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "failed get bundleInfo by userId %{public}d", userId);
            return GET_BUNDLE_INFO_FAILED;
        }
    }

    bool isDebugApp = want.GetBoolParam(AbilityConfig::DEBUG_APP, false);
    if (isDebugApp && bundleInfo.applicationInfo.appProvisionType != AppExecFwk::Constants::APP_PROVISION_TYPE_DEBUG) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "release app not support debug");
        return ERR_NOT_IN_APP_PROVISION_MODE;
    }

    return DelayedSingleton<AppScheduler>::GetInstance()->StartUserTest(want, observer, bundleInfo, userId);
}

int AbilityManagerService::FinishUserTest(
    const std::string &msg, const int64_t &resultCode, const std::string &bundleName)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "enter");
    if (bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid bundle name");
        return ERR_INVALID_VALUE;
    }

    return DelayedSingleton<AppScheduler>::GetInstance()->FinishUserTest(msg, resultCode, bundleName);
}

int AbilityManagerService::GetTopAbility(sptr<IRemoteObject> &token)
{
    return GetTopAbilityInner(token);
}

int AbilityManagerService::GetTopAbilityInner(sptr<IRemoteObject> &token, uint64_t displayId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    if (!isSaCall) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
#ifdef SUPPORT_SCREEN
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        Rosen::FocusChangeInfo focusChangeInfo;
        Rosen::WindowManager::GetInstance().GetFocusWindowInfo(focusChangeInfo, displayId);
        token = focusChangeInfo.abilityToken_;
    } else {
        if (!GetWMSHandler()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "wmsHandler_ null");
            return ERR_INVALID_VALUE;
        }
        GetWMSHandler()->GetFocusWindow(token);
    }

    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return ERR_INVALID_VALUE;
    }
#endif
    return ERR_OK;
}

int AbilityManagerService::DelegatorDoAbilityForeground(const sptr<IRemoteObject> &token)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "enter");
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);
    auto &&abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    int32_t callerPid = IPCSkeleton::GetCallingPid();
    int32_t appPid = abilityRecord->GetPid();
    TAG_LOGD(AAFwkTag::ABILITYMGR, "callerPid: %{public}d, appPid: %{public}d", callerPid, appPid);
    if (callerPid != appPid) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not application itself");
        return ERR_INVALID_VALUE;
    }
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto sessionId = GetMissionIdByAbilityTokenInner(token);
        if (!sessionId) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid session id");
            return ERR_INVALID_VALUE;
        }
        auto want = abilityRecord->GetWant();
        if (!IsAbilityControllerStart(want, want.GetBundle())) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                "sceneBoard IsAbilityControllerStart failed:%{public}s", want.GetBundle().c_str());
            return ERR_WOULD_BLOCK;
        }
        return ERR_OK;
    }
    auto missionId = GetMissionIdByAbilityToken(token);
    if (missionId < 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid mission id");
        return ERR_INVALID_VALUE;
    }
    return DelegatorMoveMissionToFront(missionId);
}

int AbilityManagerService::DelegatorDoAbilityBackground(const sptr<IRemoteObject> &token)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "enter");
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);
    auto &&abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    int32_t appPid = abilityRecord->GetPid();
    int32_t callerPid = IPCSkeleton::GetCallingPid();
    TAG_LOGD(AAFwkTag::ABILITYMGR, "callerPid: %{public}d, appPid: %{public}d", callerPid, appPid);
    if (callerPid != appPid) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not application itself");
        return ERR_INVALID_VALUE;
    }
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        return ERR_OK;
    }
    return MinimizeAbility(token, true);
}

int AbilityManagerService::DoAbilityForeground(const sptr<IRemoteObject> &token, uint32_t flag)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "DoAbilityForeground, sceneFlag:%{public}u", flag);
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);
    if (!VerificationAllToken(token)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s token error", __func__);
        return ERR_INVALID_VALUE;
    }

    std::lock_guard<ffrt::mutex> guard(globalLock_);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "cannot minimize except page ability");
        return ERR_WRONG_INTERFACE_CALL;
    }

    if (!IsAbilityControllerForeground(abilityRecord->GetAbilityInfo().bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerForeground false");
        return ERR_WOULD_BLOCK;
    }

    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    return missionListManager->DoAbilityForeground(abilityRecord, flag);
}

int AbilityManagerService::DoAbilityBackground(const sptr<IRemoteObject> &token, uint32_t flag)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "DoAbilityBackground, sceneFlag:%{public}u", flag);
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    abilityRecord->lifeCycleStateInfo_.sceneFlag = flag;
    int ret = MinimizeAbility(token);
    abilityRecord->lifeCycleStateInfo_.sceneFlag = SCENE_FLAG_NORMAL;
    return ret;
}

int AbilityManagerService::DelegatorMoveMissionToFront(int32_t missionId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "enter missionId:%{public}d", missionId);
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);

    if (!IsAbilityControllerStartById(missionId)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "IsAbilityControllerStart false");
        return ERR_WOULD_BLOCK;
    }

    return missionListManager->MoveMissionToFront(missionId);
}

bool AbilityManagerService::JudgeMultiUserConcurrency(int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (userId == U0_USER_ID || userId == U1_USER_ID) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s, userId is 0 or 1.", __func__);
        return true;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId : %{public}d", userId);
    if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(userId)) {
        return true;
    }
    return false;
}

void AbilityManagerService::SendExtensionReport(EventInfo &eventInfo, int32_t errCode, bool isService)
{
    eventInfo.errCode = errCode;
    eventInfo.callerBundleName = InsightIntentGetcallerBundleName();
    if (isService) {
        EventReport::SendExtensionEvent(EventName::UI_SERVICE_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
    } else {
        EventReport::SendExtensionEvent(EventName::UI_EXTENSION_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
}

void AbilityManagerService::SendIntentReport(EventInfo &eventInfo, int32_t errCode, const std::string &intentName)
{
    eventInfo.errCode = errCode;
    eventInfo.callerBundleName = InsightIntentGetcallerBundleName();
    eventInfo.intentName = intentName;
    EventReport::SendExecuteIntentEvent(EventName::EXECUTE_INSIGHT_INTENT_ERROR, HISYSEVENT_FAULT, eventInfo);
}

#ifdef ABILITY_COMMAND_FOR_TEST
int AbilityManagerService::ForceTimeoutForTest(const std::string &abilityName, const std::string &state)
{
    if (abilityName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityName empty");
        return INVALID_DATA;
    }
    std::lock_guard guard(timeoutMapLock_);
    if (abilityName == "clean") {
        timeoutMap_.clear();
        return ERR_OK;
    }
    if (state != AbilityRecord::ConvertAbilityState(AbilityState::INITIAL) &&
        state != AbilityRecord::ConvertAbilityState(AbilityState::INACTIVE) &&
        state != AbilityRecord::ConvertAbilityState(AbilityState::FOREGROUND) &&
        state != AbilityRecord::ConvertAbilityState(AbilityState::BACKGROUND) &&
        state != AbilityRecord::ConvertAbilityState(AbilityState::TERMINATING) &&
        state != std::string("COMMAND")) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "lifecycle state invalid");
        return INVALID_DATA;
    }
    timeoutMap_.insert(std::make_pair(state, abilityName));
    return ERR_OK;
}
#endif

int AbilityManagerService::CheckStaticCfgPermissionForAbility(const AppExecFwk::AbilityInfo &abilityInfo,
    uint32_t tokenId)
{
    if (abilityInfo.permissions.empty() || AccessTokenKit::VerifyAccessToken(tokenId,
        PermissionConstants::PERMISSION_START_INVISIBLE_ABILITY, false) == ERR_OK) {
        return AppExecFwk::Constants::PERMISSION_GRANTED;
    }

    for (const auto &permission : abilityInfo.permissions) {
        if (AccessTokenKit::VerifyAccessToken(tokenId, permission, false) !=
            AppExecFwk::Constants::PERMISSION_GRANTED) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "verify access token fail, permission:%{public}s",
                permission.c_str());
            return AppExecFwk::Constants::PERMISSION_NOT_GRANTED;
        }
    }

    return AppExecFwk::Constants::PERMISSION_GRANTED;
}

bool AbilityManagerService::CheckOneSkillPermission(const AppExecFwk::Skill &skill, uint32_t tokenId)
{
    for (auto permission : skill.permissions) {
        if (AccessTokenKit::VerifyAccessToken(tokenId, permission, false) !=
            AppExecFwk::Constants::PERMISSION_GRANTED) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "verify access token fail, permission:%{public}s",
                permission.c_str());
            return false;
        }
    }

    return true;
}

int AbilityManagerService::CheckStaticCfgPermissionForSkill(const AppExecFwk::AbilityRequest &abilityRequest,
    uint32_t tokenId)
{
    auto abilityInfo = abilityRequest.abilityInfo;
    auto resultAbilityPermission = CheckStaticCfgPermissionForAbility(abilityInfo, tokenId);
    if (resultAbilityPermission != AppExecFwk::Constants::PERMISSION_GRANTED) {
        return resultAbilityPermission;
    }

    if (abilityInfo.skills.empty()) {
        return AppExecFwk::Constants::PERMISSION_GRANTED;
    }
    int32_t result = AppExecFwk::Constants::PERMISSION_GRANTED;
    for (auto skill : abilityInfo.skills) {
        if (skill.Match(abilityRequest.want)) {
            if (CheckOneSkillPermission(skill, tokenId)) {
                return AppExecFwk::Constants::PERMISSION_GRANTED;
            } else {
                result = AppExecFwk::Constants::PERMISSION_NOT_GRANTED;
            }
        }
    }
    return result;
}

int AbilityManagerService::CheckStaticCfgPermission(const AppExecFwk::AbilityRequest &abilityRequest,
    bool isStartAsCaller, uint32_t callerTokenId, bool isData, bool isSaCall, bool isImplicit)
{
    auto abilityInfo = abilityRequest.abilityInfo;
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (AppUtils::GetInstance().IsSupportAncoApp() &&
        StartAbilityUtils::IsCallFromAncoShellOrBroker(abilityRequest.callerToken)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR,
            "Check static permission, name is %{public}s.", abilityInfo.name.c_str());
        auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
        if (collaborator == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "Collaborator null");
            return AppExecFwk::Constants::PERMISSION_NOT_GRANTED;
        }
        int result = collaborator->CheckStaticCfgPermission(abilityRequest.want, isImplicit);
        if (result != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "Check permission failed from broker");
            return AppExecFwk::Constants::PERMISSION_NOT_GRANTED;
        }
    }
    if (!isData) {
        isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    }
    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    if (specifyTokenId != 0) {
        isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACallByTokenId(specifyTokenId);
    }
    if (isSaCall) {
        // do not need check static config permission when start ability by SA
        return AppExecFwk::Constants::PERMISSION_GRANTED;
    }

    uint32_t tokenId;
    if (isStartAsCaller) {
        tokenId = callerTokenId;
    } else if (specifyTokenId != 0) {
        tokenId = specifyTokenId;
    } else {
        tokenId = IPCSkeleton::GetCallingTokenID();
    }

    if (abilityInfo.applicationInfo.accessTokenId == tokenId) {
        return AppExecFwk::Constants::PERMISSION_GRANTED;
    }

    if (abilityRequest.want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME) ==
        AppUtils::GetInstance().GetBrokerDelegateBundleName() &&
        abilityRequest.abilityInfo.applicationInfo.codePath == std::to_string(CollaboratorType::RESERVE_TYPE)) {
        return AppExecFwk::Constants::PERMISSION_GRANTED;
    }

    if ((abilityInfo.type == AppExecFwk::AbilityType::EXTENSION &&
        abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::DATASHARE) ||
        (abilityInfo.type == AppExecFwk::AbilityType::DATA)) {
        // just need check the read permission and write permission of extension ability or data ability
        if (!abilityInfo.readPermission.empty()) {
            int checkReadPermission = AccessTokenKit::VerifyAccessToken(tokenId, abilityInfo.readPermission, false);
            if (checkReadPermission == ERR_OK) {
                return AppExecFwk::Constants::PERMISSION_GRANTED;
            }
            TAG_LOGW(AAFwkTag::ABILITYMGR,
                "verify access token fail, read permission: %{public}s", abilityInfo.readPermission.c_str());
        }
        if (!abilityInfo.writePermission.empty()) {
            int checkWritePermission = AccessTokenKit::VerifyAccessToken(tokenId, abilityInfo.writePermission, false);
            if (checkWritePermission == ERR_OK) {
                return AppExecFwk::Constants::PERMISSION_GRANTED;
            }
            TAG_LOGW(AAFwkTag::ABILITYMGR,
                "verify access token fail, write permission: %{public}s", abilityInfo.writePermission.c_str());
        }

        if (!abilityInfo.readPermission.empty() || !abilityInfo.writePermission.empty()) {
            // 'readPermission' and 'writePermission' take precedence over 'permission'
            // when 'readPermission' or 'writePermission' is not empty, no need check 'permission'
            return AppExecFwk::Constants::PERMISSION_NOT_GRANTED;
        }
    }

    if (!isImplicit) {
        return CheckStaticCfgPermissionForAbility(abilityInfo, tokenId);
    }
    return CheckStaticCfgPermissionForSkill(abilityRequest, tokenId);
}

int AbilityManagerService::CheckPermissionForUIService(AppExecFwk::ExtensionAbilityType extensionType,
    const Want &want, const AbilityRequest &abilityRequest)
{
    AppExecFwk::ExtensionAbilityType targetExtType = abilityRequest.abilityInfo.extensionAbilityType;
    if (targetExtType != AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        return ERR_OK;
    }
    if (!want.HasParameter(UISERVICEHOSTPROXY_KEY)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "need UISERVICEHOSTPROXY_KEY connect UI_SERVICE");
        return ERR_WRONG_INTERFACE_CALL;
    }
    if (extensionType != AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interface not support connect UI_SERVICE");
        return ERR_WRONG_INTERFACE_CALL;
    }
    if (!system::GetBoolParameter(ABILITYMS_ENABLE_UISERVICE, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ABILITYMS_ENABLE_UISERVICE false");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }

    return ERR_OK;
}

bool AbilityManagerService::IsNeedTimeoutForTest(const std::string &abilityName, const std::string &state) const
{
    std::lock_guard guard(timeoutMapLock_);
    for (auto iter = timeoutMap_.begin(); iter != timeoutMap_.end(); iter++) {
        if (iter->first == state && iter->second == abilityName) {
            return true;
        }
    }
    return false;
}

bool AbilityManagerService::GetValidDataAbilityUri(const std::string &abilityInfoUri, std::string &adjustUri)
{
    // note: do not use abilityInfo.uri directly, need check uri first.
    size_t firstSeparator = abilityInfoUri.find_first_of('/');
    size_t lastSeparator = abilityInfoUri.find_last_of('/');
    if (lastSeparator - firstSeparator != 1) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability info uri error, uri: %{public}s", abilityInfoUri.c_str());
        return false;
    }

    adjustUri = abilityInfoUri;
    adjustUri.insert(lastSeparator, "/");
    return true;
}

bool AbilityManagerService::GetDataAbilityUri(const std::vector<AppExecFwk::AbilityInfo> &abilityInfos,
    const std::string &mainAbility, std::string &uri)
{
    if (abilityInfos.empty() || mainAbility.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "abilityInfos or mainAbility empty mainAbility:%{public}s", mainAbility.c_str());
        return false;
    }

    std::string dataAbilityUri;
    for (auto abilityInfo : abilityInfos) {
        if (abilityInfo.type == AppExecFwk::AbilityType::DATA &&
            abilityInfo.name == mainAbility) {
            dataAbilityUri = abilityInfo.uri;
            TAG_LOGI(AAFwkTag::ABILITYMGR, "get data ability uri:%{public}s", dataAbilityUri.c_str());
            break;
        }
    }

    return GetValidDataAbilityUri(dataAbilityUri, uri);
}

void AbilityManagerService::GetAbilityRunningInfo(std::vector<AbilityRunningInfo> &info,
    std::shared_ptr<AbilityRecord> abilityRecord)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    AbilityRunningInfo runningInfo;
    AppExecFwk::RunningProcessInfo processInfo;
    CHECK_POINTER(abilityRecord);
    runningInfo.ability = abilityRecord->GetElementName();
    runningInfo.startTime = abilityRecord->GetStartTime();
    runningInfo.abilityState = static_cast<int>(abilityRecord->GetAbilityState());

    DelayedSingleton<AppScheduler>::GetInstance()->
        GetRunningProcessInfoByToken(abilityRecord->GetToken(), processInfo);
    runningInfo.pid = processInfo.pid_;
    runningInfo.uid = processInfo.uid_;
    runningInfo.processName = processInfo.processName_;
    runningInfo.appCloneIndex = processInfo.appCloneIndex;
    runningInfo.firstCallerBundleName = abilityRecord->GetFirstCallerBundleName();
    info.emplace_back(runningInfo);
}

int AbilityManagerService::VerifyAccountPermission(int32_t userId)
{
    if (userId < 0) {
        return ERR_OK;
    }
    int32_t callerUser = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    if (((callerUser == U0_USER_ID || callerUser == U1_USER_ID) &&
        UserController::GetInstance().IsForegroundUser(userId)) || callerUser == userId) {
        return ERR_OK;
    }
    return AAFwk::PermissionVerification::GetInstance()->VerifyAccountPermission();
}

int AbilityManagerService::FreeInstallAbilityFromRemote(const Want &want, const sptr<IRemoteObject> &callback,
    int32_t userId, int requestCode)
{
    auto callingUid = IPCSkeleton::GetCallingUid();
    if (callingUid != DMS_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interface only support DMS");
        return CHECK_PERMISSION_FAILED;
    }
    int32_t validUserId = GetValidUserId(userId);
    if (freeInstallManager_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "freeInstallManager_ null");
        return ERR_INVALID_VALUE;
    }
    return freeInstallManager_->FreeInstallAbilityFromRemote(want, callback, validUserId, requestCode);
}

AppExecFwk::ElementName AbilityManagerService::GetTopAbility(bool isNeedLocalDeviceId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s start.", __func__);
    AppExecFwk::ElementName elementName = {};
    if (!PermissionVerification::GetInstance()->JudgeCallerIsAllowedToUseSystemAPI()) {
        auto callerPid = IPCSkeleton::GetCallingPid();
        AppExecFwk::RunningProcessInfo processInfo;
        DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(callerPid, processInfo);
        if (!processInfo.isTestProcess) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "can't use system-api or not test process");
            return elementName;
        }
    }
#ifdef SUPPORT_GRAPHICS
    sptr<IRemoteObject> token;
    int ret = IN_PROCESS_CALL(GetTopAbility(token));
    if (ret) {
        return elementName;
    }
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return elementName;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s abilityRecord null", __func__);
        return elementName;
    }
    elementName = abilityRecord->GetElementName();
    bool isDeviceEmpty = elementName.GetDeviceID().empty();
    std::string localDeviceId;
    if (isDeviceEmpty && isNeedLocalDeviceId && GetLocalDeviceId(localDeviceId)) {
        elementName.SetDeviceID(localDeviceId);
    }
#endif
    return elementName;
}

AppExecFwk::ElementName AbilityManagerService::GetElementNameByToken(sptr<IRemoteObject> token,
    bool isNeedLocalDeviceId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s start.", __func__);
    AppExecFwk::ElementName elementName = {};
#ifdef SUPPORT_GRAPHICS
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return elementName;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s abilityRecord null", __func__);
        return elementName;
    }
    elementName = abilityRecord->GetElementName();
    bool isDeviceEmpty = elementName.GetDeviceID().empty();
    std::string localDeviceId;
    if (isDeviceEmpty && isNeedLocalDeviceId && GetLocalDeviceId(localDeviceId)) {
        elementName.SetDeviceID(localDeviceId);
    }
#endif
    return elementName;
}

int AbilityManagerService::Dump(int fd, const std::vector<std::u16string>& args)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Dump begin fd: %{public}d", fd);
    std::string result;
    auto errCode = Dump(args, result);
    int ret = dprintf(fd, "%s\n", result.c_str());
    if (ret < 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "dprintf error");
        return ERR_AAFWK_HIDUMP_ERROR;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Dump end");
    return errCode;
}

int AbilityManagerService::Dump(const std::vector<std::u16string>& args, std::string& result)
{
    ErrCode errCode = ERR_OK;
    auto size = args.size();
    if (size == 0) {
        ShowHelp(result);
        return errCode;
    }

    std::vector<std::string> argsStr;
    for (auto arg : args) {
        argsStr.emplace_back(Str16ToStr8(arg));
    }

    if (argsStr[0] == "-h") {
        ShowHelp(result);
    } else {
        errCode = ProcessMultiParam(argsStr, result);
        if (errCode == ERR_AAFWK_HIDUMP_INVALID_ARGS) {
            ShowIllegalInfomation(result);
        }
    }
    return errCode;
}

ErrCode AbilityManagerService::ProcessMultiParam(std::vector<std::string>& argsStr, std::string& result)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s begin", __func__);
    bool isClient = false;
    bool isUser = false;
    int userID = DEFAULT_INVAL_VALUE;
    std::vector<std::string>::iterator it;
    for (it = argsStr.begin(); it != argsStr.end();) {
        if (*it == ARGS_CLIENT) {
            isClient = true;
            it = argsStr.erase(it);
            continue;
        }
        if (*it == ARGS_USER_ID) {
            it = argsStr.erase(it);
            if (it == argsStr.end()) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "ARGS_USER_ID id invalid");
                return ERR_AAFWK_HIDUMP_INVALID_ARGS;
            }
            (void)StrToInt(*it, userID);
            if (userID < 0) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "ARGS_USER_ID id invalid");
                return ERR_AAFWK_HIDUMP_INVALID_ARGS;
            }
            isUser = true;
            it = argsStr.erase(it);
            continue;
        }
        it++;
    }
    std::string cmd;
    for (unsigned int i = 0; i < argsStr.size(); i++) {
        cmd.append(argsStr[i]);
        if (i != argsStr.size() - 1) {
            cmd.append(" ");
        }
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s, isClient:%{public}d, userID:%{public}d, cmd:%{public}s",
        __func__, isClient, userID, cmd.c_str());

    std::vector<std::string> dumpResults;
    DumpSysState(cmd, dumpResults, isClient, isUser, userID);
    for (auto it : dumpResults) {
        result += it + "\n";
    }
    return ERR_OK;
}

void AbilityManagerService::ShowHelp(std::string& result)
{
    result.append("Usage:\n")
        .append("-h                          ")
        .append("help text for the tool\n")
        .append("-a [-c | -u {UserId}]       ")
        .append("dump all ability infomation in the system or all ability infomation of client/UserId\n")
        .append("-l                          ")
        .append("dump all mission list information in the system\n")
        .append("-i {AbilityRecordId}        ")
        .append("dump an ability infomation by ability record id\n")
        .append("-e                          ")
        .append("dump all extension infomation in the system(FA: ServiceAbilityRecords, Stage: ExtensionRecords)\n")
        .append("-p [PendingWantRecordId]    ")
        .append("dump all pendingwant record infomation in the system\n")
        .append("-r                          ")
        .append("dump all process in the system\n")
        .append("-d                          ")
        .append("dump all data ability infomation in the system");
}

void AbilityManagerService::ShowIllegalInfomation(std::string& result)
{
    result.append(ILLEGAL_INFOMATION);
}

int AbilityManagerService::DumpAbilityInfoDone(std::vector<std::string> &infos, const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "dumpAbilityInfoDone begin");
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (abilityRecord == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_INVALID_VALUE;
    }
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }
    abilityRecord->DumpAbilityInfoDone(infos);
    return ERR_OK;
}

int AbilityManagerService::SetMissionContinueState(const sptr<IRemoteObject> &token, const AAFwk::ContinueState &state)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "SetMissionContinueState begin. State: %{public}d", state);

    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    int32_t missionId = GetMissionIdByAbilityToken(token);
    if (missionId == -1) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed state:%{public}d", state);
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "no such ability record missionId:%{public}d, state:%{public}d",
            missionId, state);
        return -1;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "setMissionContinueState not self, not enabled. missionId:%{public}d, state:%{public}d",
            missionId, state);
        return -1;
    }

    auto userId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "find missionListManager failed missionId:%{public}d, state:%{public}d",
            missionId, state);
        return -1;
    }

    auto setResult = missionListManager->SetMissionContinueState(token, missionId, state);
    if (setResult != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "missionListManager set failed, result:%{public}d, missionId:%{public}d, state:%{public}d",
            setResult, missionId, state);
        return setResult;
    }

    DistributedClient dmsClient;
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    auto result =  dmsClient.SetMissionContinueState(missionId, state, callingUid);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "Notify DMS client failed, result: %{public}d. Mission id: %{public}d, state: %{public}d",
            result, missionId, state);
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "SetMissionContinueState end. Mission id: %{public}d, state: %{public}d", missionId, state);
    return ERR_OK;
}

#ifdef SUPPORT_SCREEN
int AbilityManagerService::SetMissionLabel(const sptr<IRemoteObject> &token, const std::string &label)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no such ability record");
        return -1;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "setMissionLabel not self, not enabled");
        return -1;
    }

    auto userId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager find failed when set mission label");
        return -1;
    }

    return missionListManager->SetMissionLabel(token, label);
}

int AbilityManagerService::SetMissionIcon(const sptr<IRemoteObject> &token,
    const std::shared_ptr<OHOS::Media::PixelMap> &icon)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "%{public}s", __func__);
    CHECK_CALLER_IS_SYSTEM_APP;
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no such ability record");
        return -1;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self, not enable set mission icon");
        return -1;
    }

    auto userId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(userId);
    if (!missionListManager) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "find missionListManager failed");
        return -1;
    }

    return missionListManager->SetMissionIcon(token, icon);
}

int AbilityManagerService::RegisterWindowManagerServiceHandler(const sptr<IWindowManagerServiceHandler> &handler,
    bool animationEnabled)
{
    if (IPCSkeleton::GetCallingUid() != SAMGR_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "register wms handler permission fail:%{public}d", IPCSkeleton::GetCallingUid());
        return CHECK_PERMISSION_FAILED;
    }
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "only support null scb device");
        return CHECK_PERMISSION_FAILED;
    }
    std::lock_guard<ffrt::mutex> guard(wmsHandlerLock_);
    wmsHandler_ = handler;
    isAnimationEnabled_ = animationEnabled;
    TAG_LOGI(AAFwkTag::ABILITYMGR, "WMS handler registered successfully.");
    return ERR_OK;
}

sptr<IWindowManagerServiceHandler> AbilityManagerService::GetWMSHandler()
{
    std::lock_guard<ffrt::mutex> guard(wmsHandlerLock_);
    return wmsHandler_;
}

void AbilityManagerService::CompleteFirstFrameDrawing(const sptr<IRemoteObject> &abilityToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (IPCSkeleton::GetCallingUid() != FOUNDATION_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not foundation call");
        return;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(abilityToken);
    CHECK_POINTER(abilityRecord);

    auto ownerUserId = abilityRecord->GetOwnerMissionUserId();
    auto missionListManager = GetMissionListManagerByUserId(ownerUserId);
    CHECK_POINTER(missionListManager);
    missionListManager->CompleteFirstFrameDrawing(abilityToken);
}

void AbilityManagerService::CompleteFirstFrameDrawing(int32_t sessionId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sceneboard called, not allowed");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    uiAbilityManager->CompleteFirstFrameDrawing(sessionId);
}

int32_t AbilityManagerService::ShowPickerDialog(
    const Want& want, int32_t userId, const sptr<IRemoteObject> &callerToken)
{
    AAFwk::Want newWant = want;
    std::string sharePickerBundleName =
        OHOS::system::GetParameter(SHARE_PICKER_DIALOG_BUNDLE_NAME_KEY, SHARE_PICKER_DIALOG_DEFAULY_BUNDLE_NAME);
    std::string sharePickerAbilityName =
        OHOS::system::GetParameter(SHARE_PICKER_DIALOG_ABILITY_NAME_KEY, SHARE_PICKER_DIALOG_DEFAULY_ABILITY_NAME);
    newWant.SetElementName(sharePickerBundleName, sharePickerAbilityName);
    newWant.SetParam(TOKEN_KEY, callerToken);
    // note: clear actions
    newWant.SetAction("");
    return IN_PROCESS_CALL(StartAbility(newWant, DEFAULT_INVAL_VALUE, userId));
}

bool AbilityManagerService::CheckWindowMode(int32_t windowMode,
    const std::vector<AppExecFwk::SupportWindowMode>& windowModes) const
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "window mode:%{public}d", windowMode);
    if (windowMode == AbilityWindowConfiguration::MULTI_WINDOW_DISPLAY_UNDEFINED) {
        return true;
    }

    auto bmsWindowMode = WindowOptionsUtils::WindowModeMap(windowMode);
    if (bmsWindowMode.first) {
        for (const auto& mode : windowModes) {
            if (mode == bmsWindowMode.second) {
                return true;
            }
        }
    }
    return false;
}

int AbilityManagerService::PrepareTerminateAbility(const sptr<IRemoteObject> &token,
    sptr<IPrepareTerminateCallback> &callback)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call PrepareTerminateAbility");
    if (callback == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callback null");
        return ERR_INVALID_VALUE;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    auto err = AbilityPermissionUtil::GetInstance().CheckPrepareTerminateEnable(abilityRecord);
    if (err != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "CheckPrepareTerminateEnable failed: %{public}d", err);
        callback->DoPrepareTerminate();
        return err;
    }

    if (!JudgeSelfCalled(abilityRecord)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self call");
        callback->DoPrepareTerminate();
        return CHECK_PERMISSION_FAILED;
    }

    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    bool res = uiAbilityManager->PrepareTerminateAbility(abilityRecord, false);
    if (!res) {
        callback->DoPrepareTerminate();
        return ERR_OK;
    }
    std::lock_guard<std::mutex> guard(prepareTermiationCallbackMutex_);
    auto abilityRecordId = std::to_string(abilityRecord->GetAbilityRecordId());
    if (prepareTermiationCallbacks_.find(abilityRecordId) != prepareTermiationCallbacks_.end()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "abilityRecordId=%{public}s already exists", abilityRecordId.c_str());
        return ERR_OK;
    }
    prepareTermiationCallbacks_[abilityRecordId] = callback;

    auto timeoutTask = [callback]() {
        if (callback != nullptr) {
            callback->DoPrepareTerminate();
        }
    };
    if (taskHandler_) {
        taskHandler_->SubmitTask(timeoutTask, "PrepareTerminate_" + abilityRecordId,
            GlobalConstant::PREPARE_TERMINATE_TIMEOUT_TIME);
    }
    return ERR_OK;
}

void AbilityManagerService::PrepareTerminateAbilityDone(const sptr<IRemoteObject> &token, bool isTerminate)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call PrepareTerminateAbilityDone, isTerminate=%{public}d", isTerminate);
    if (token == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null token");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER(abilityRecord);
    if (!JudgeSelfCalled(abilityRecord)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self caller");
        return;
    }
    auto abilityRecordId = std::to_string(abilityRecord->GetAbilityRecordId());
    std::lock_guard<std::mutex> guard(prepareTermiationCallbackMutex_);
    auto iter = prepareTermiationCallbacks_.find(abilityRecordId);
    if (iter == prepareTermiationCallbacks_.end()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "scb call, abilityRecordId=%{public}s not found", abilityRecordId.c_str());
        uiAbilityManager->PrepareTerminateAbilityDone(
            std::static_pointer_cast<UIAbilityRecord>(abilityRecord), isTerminate);
        return;
    }
    if (iter->second != nullptr && !isTerminate) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "abilityRecordId=%{public}s, calling callback", abilityRecordId.c_str());
        iter->second->DoPrepareTerminate();
    }
    prepareTermiationCallbacks_.erase(iter);
    if (taskHandler_) {
        taskHandler_->CancelTask("PrepareTerminate_" + abilityRecordId);
    }
}

void AbilityManagerService::KillProcessWithPrepareTerminateDone(const std::string &moduleName,
    int32_t prepareTermination, bool isExist)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call KillProcessWithPrepareTerminateDone, moduleName=%{public}s, "
        "prepareTermination=%{public}d, isExist=%{public}d", moduleName.c_str(), prepareTermination, isExist);
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    uiAbilityManager->TryPrepareTerminateByPidsDone(moduleName, prepareTermination, isExist);
}

void AbilityManagerService::HandleFocused(const sptr<OHOS::Rosen::FocusChangeInfo> &focusChangeInfo)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "handle focused event");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER(missionListManager);
    CHECK_POINTER(focusChangeInfo);
    int32_t missionId = GetMissionIdByAbilityToken(focusChangeInfo->abilityToken_);
    missionListManager->NotifyMissionFocused(missionId);
}

void AbilityManagerService::HandleUnfocused(const sptr<OHOS::Rosen::FocusChangeInfo> &focusChangeInfo)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "handle unfocused event");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER(missionListManager);
    CHECK_POINTER(focusChangeInfo);
    int32_t missionId = GetMissionIdByAbilityToken(focusChangeInfo->abilityToken_);
    missionListManager->NotifyMissionUnfocused(missionId);
}

void AbilityManagerService::InitFocusListener()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "init ability focus listener");
    if (focusListener_) {
        return;
    }

    focusListener_ = new WindowFocusChangedListener(shared_from_this(), taskHandler_);
    auto registerTask = [innerService = shared_from_this()]() {
        if (innerService) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "registerFocusListener task");
            innerService->RegisterFocusListener();
        }
    };
    if (taskHandler_) {
        taskHandler_->SubmitTaskJust(registerTask, "RegisterFocusListenerTask", REGISTER_FOCUS_DELAY);
    }
}

void AbilityManagerService::RegisterFocusListener()
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "register focus listener");
    if (!focusListener_) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no listener obj");
        return;
    }
    Rosen::WindowManager::GetInstance().RegisterFocusChangedListener(focusListener_);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "register focus listener success");
}

int AbilityManagerService::RegisterAbilityFirstFrameStateObserver(
    const sptr<IAbilityFirstFrameStateObserver> &observer, const std::string &targetBundleName)
{
    return AppExecFwk::AbilityFirstFrameStateObserverManager::GetInstance().
        RegisterAbilityFirstFrameStateObserver(observer, targetBundleName);
}

int AbilityManagerService::UnregisterAbilityFirstFrameStateObserver(
    const sptr<IAbilityFirstFrameStateObserver> &observer)
{
    return AppExecFwk::AbilityFirstFrameStateObserverManager::GetInstance().
        UnregisterAbilityFirstFrameStateObserver(observer);
}

bool AbilityManagerService::GetAnimationFlag()
{
    std::lock_guard<ffrt::mutex> guard(wmsHandlerLock_);
    return isAnimationEnabled_;
}

#endif

int AbilityManagerService::CheckCallServicePermission(const AbilityRequest &abilityRequest)
{
    if (abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_UID, IPCSkeleton::GetCallingUid()) ==
        AppUtils::GetInstance().GetCollaboratorBrokerUID() &&
        abilityRequest.want.GetElement().GetBundleName() == AppUtils::GetInstance().GetBrokerDelegateBundleName()) {
        auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
        if (collaborator != nullptr) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "Collaborator CheckCallAbilityPermission");
            return collaborator->CheckCallAbilityPermission(abilityRequest.want);
        }
    }
    if (abilityRequest.abilityInfo.isStageBasedModel) {
        auto extensionType = abilityRequest.abilityInfo.extensionAbilityType;
        TAG_LOGD(AAFwkTag::ABILITYMGR, "extensionType is %{public}d.", static_cast<int>(extensionType));
        if (extensionType == AppExecFwk::ExtensionAbilityType::SERVICE ||
            extensionType == AppExecFwk::ExtensionAbilityType::DATASHARE ||
            extensionType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
            return CheckCallServiceExtensionPermission(abilityRequest);
        } else {
            return CheckCallOtherExtensionPermission(abilityRequest);
        }
    } else {
        return CheckCallServiceAbilityPermission(abilityRequest);
    }
}

int AbilityManagerService::CheckCallDataAbilityPermission(AbilityRequest &abilityRequest, bool isShell, bool isSACall)
{
    abilityRequest.appInfo = abilityRequest.abilityInfo.applicationInfo;
    abilityRequest.uid = abilityRequest.appInfo.uid;
    if (abilityRequest.appInfo.name.empty() || abilityRequest.appInfo.bundleName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid app info acquiring");
        return ERR_INVALID_VALUE;
    }
    if (abilityRequest.abilityInfo.type != AppExecFwk::AbilityType::DATA) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "BMS query result not data ability");
        return ERR_WRONG_INTERFACE_CALL;
    }

    AAFwk::PermissionVerification::VerificationInfo verificationInfo = CreateVerificationInfo(abilityRequest,
        true, isShell, isSACall);
    if (isShell) {
        verificationInfo.isBackgroundCall = true;
    }
    if (!isShell && IsCallFromBackground(abilityRequest, verificationInfo.isBackgroundCall, false, 0, true) != ERR_OK) {
        return ERR_INVALID_VALUE;
    }
    int result = AAFwk::PermissionVerification::GetInstance()->CheckCallDataAbilityPermission(verificationInfo,
        isShell);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "without start DataAbility permission");
        return result;
    }

    return ERR_OK;
}

AAFwk::PermissionVerification::VerificationInfo AbilityManagerService::CreateVerificationInfo(
    const AbilityRequest &abilityRequest, bool isData, bool isShell, bool isSA)
{
    AAFwk::PermissionVerification::VerificationInfo verificationInfo;
    verificationInfo.accessTokenId = abilityRequest.appInfo.accessTokenId;
    verificationInfo.visible = abilityRequest.abilityInfo.visible;
    verificationInfo.withContinuousTask = IsBackgroundTaskUid(IPCSkeleton::GetCallingUid());
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call ServiceAbility or DataAbility, target bundleName: %{public}s.",
        abilityRequest.appInfo.bundleName.c_str());
    if (whiteListassociatedWakeUpFlag_ &&
        abilityRequest.appInfo.bundleName == BUNDLE_NAME_SETTINGSDATA) {
        TAG_LOGD(AAFwkTag::ABILITYMGR,
            "Call ServiceAbility or DataAbility, target bundle in white-list, allow associatedWakeUp.");
        verificationInfo.associatedWakeUp = true;
    } else {
        verificationInfo.associatedWakeUp = abilityRequest.appInfo.associatedWakeUp;
    }
    if (!isData) {
        isSA = AAFwk::PermissionVerification::GetInstance()->IsSACall();
        isShell = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    }
    if (isSA || isShell) {
        return verificationInfo;
    }
    std::shared_ptr<AbilityRecord> callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (callerAbility) {
        verificationInfo.apiTargetVersion = callerAbility->GetApplicationInfo().apiTargetVersion;
    }

    return verificationInfo;
}

int32_t AbilityManagerService::CheckCallAppServiceExtensionPermission(const AbilityRequest &abilityRequest,
    std::shared_ptr<BaseExtensionRecord> targetService, bool isFromConnect)
{
    int32_t result = CheckCallServiceExtensionPermission(abilityRequest);
    if (result != ERR_OK) {
        return result;
    }
    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    if (AAFwk::PermissionVerification::GetInstance()->IsSACallByTokenId(specifyTokenId)) {
        return ERR_OK;
    }
    if (!AppUtils::GetInstance().IsSupportAppServiceExtension()) {
        return ERR_CAPABILITY_NOT_SUPPORT;
    }
    bool isVerifyAppIdentifierAllowList = true;
    if (targetService != nullptr && targetService->IsAbilityState(AbilityState::ACTIVE)) {
        isVerifyAppIdentifierAllowList = false;
    }
    if (isVerifyAppIdentifierAllowList && !VerifySameAppOrAppIdentifierAllowListPermission(abilityRequest)) {
        if (isFromConnect) {
            return ERR_TARGET_NOT_STARTED;
        }
        return ERR_TARGET_NOT_IN_APP_IDENTIFIER_ALLOW_LIST;
    }
    if (!PermissionVerification::GetInstance()->VerifyPermissionByTokenId(abilityRequest.appInfo.accessTokenId,
        PermissionConstants::PERMISSION_SUPPORT_APP_SERVICE_EXTENSION)) {
        return TARGET_ABILITY_NOT_SERVICE;
    }
    return ERR_OK;
}

int AbilityManagerService::CheckCallServiceExtensionPermission(const AbilityRequest &abilityRequest)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "begin");

    AAFwk::PermissionVerification::VerificationInfo verificationInfo;
    verificationInfo.accessTokenId = abilityRequest.appInfo.accessTokenId;
    verificationInfo.visible = abilityRequest.abilityInfo.visible;
    verificationInfo.withContinuousTask = IsBackgroundTaskUid(IPCSkeleton::GetCallingUid());
    verificationInfo.isBackgroundCall = false;
    verificationInfo.specifyTokenId = static_cast<uint32_t>(abilityRequest.specifyTokenId);
    if (isParamStartAbilityEnable_) {
        bool stopContinuousTaskFlag = ShouldPreventStartAbility(abilityRequest);
        if (stopContinuousTaskFlag) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "no have permission to start ServiceExtension");
            return CHECK_PERMISSION_FAILED;
        }
    }

    if (abilityRequest.abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "background startup UI_SERVICE");
        verificationInfo.isBackgroundCall = true;
        std::shared_ptr<AbilityRecord> callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
        if (callerAbility) {
            verificationInfo.apiTargetVersion = callerAbility->GetApplicationInfo().apiTargetVersion;
        }
        if (IsCallFromBackground(abilityRequest, verificationInfo.isBackgroundCall, false) != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "not background startup UI_SERVICE");
            return ERR_INVALID_VALUE;
        }
    }

    int result = AAFwk::PermissionVerification::GetInstance()->CheckCallServiceExtensionPermission(verificationInfo);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "without start serviceExtension or sataShareExtension permission");
    }
    return result;
}

#ifdef SUPPORT_AUTO_FILL
int AbilityManagerService::CheckCallAutoFillExtensionPermission(const AbilityRequest &abilityRequest)
{
    if (!abilityRequest.appInfo.isSystemApp) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "application requesting call isn't system application");
        return CHECK_PERMISSION_FAILED;
    }
    std::string jsonDataStr = abilityRequest.want.GetStringParam(WANT_PARAMS_VIEW_DATA_KEY);
    AbilityBase::ViewData viewData;
    viewData.FromJsonString(jsonDataStr.c_str());
    std::string callerName;
    int32_t uid = 0;
    auto callerPid = IPCSkeleton::GetCallingPid();
    DelayedSingleton<AppScheduler>::GetInstance()->GetBundleNameByPid(callerPid, callerName, uid);
    if (viewData.bundleName != callerName) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Not %{public}s called, no allowed", viewData.bundleName.c_str());
        return ERR_WRONG_INTERFACE_CALL;
    }
    return ERR_OK;
}
#endif // SUPPORT_AUTO_FILL

int AbilityManagerService::CheckCallOtherExtensionPermission(const AbilityRequest &abilityRequest, int32_t validUserId)
{
    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    if (IPCSkeleton::GetCallingUid() != AppUtils::GetInstance().GetCollaboratorBrokerUID() &&
        AAFwk::PermissionVerification::GetInstance()->IsSACallByTokenId(specifyTokenId)) {
        return ERR_OK;
    }
    auto extensionType = abilityRequest.abilityInfo.extensionAbilityType;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "OtherExtension type: %{public}d.", static_cast<int32_t>(extensionType));
    if (system::GetBoolParameter(DEVELOPER_MODE_STATE, false) &&
        PermissionVerification::GetInstance()->VerifyShellStartExtensionType(
            static_cast<int32_t>(extensionType), specifyTokenId)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "CheckCallOtherExtensionPermission, allow aa start with debug mode.");
        return ERR_OK;
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::WINDOW) {
        if (!AAFwk::PermissionVerification::GetInstance()->JudgeCallerIsAllowedToUseSystemAPIByTokenId(
            abilityRequest.specifiedFullTokenId)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "caller no system-app, can not use system-api");
            return ERR_NOT_SYSTEM_APP;
        }
        return ERR_OK;
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::ADS_SERVICE) {
        if (!abilityRequest.appInfo.isSystemApp) {
            return CHECK_PERMISSION_FAILED;
        }
        return ERR_OK;
    }
#ifdef SUPPORT_AUTO_FILL
    if (extensionType == AppExecFwk::ExtensionAbilityType::AUTO_FILL_PASSWORD ||
        extensionType == AppExecFwk::ExtensionAbilityType::AUTO_FILL_SMART) {
        return CheckCallAutoFillExtensionPermission(abilityRequest);
    }
#endif // SUPPORT_AUTO_FILL
    if (AAFwk::UIExtensionWrapper::IsUIExtension(extensionType)) {
        return CheckUIExtensionPermission(abilityRequest, validUserId);
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::VPN) {
        return ERR_OK;
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::FILEACCESS_EXTENSION) {
        return CheckFileAccessExtensionPermission(abilityRequest);
    }
    if (extensionType == AppExecFwk::ExtensionAbilityType::CALLER_INFO_QUERY) {
        return CheckCallerInfoQueryExtensionPermission(abilityRequest);
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "not SA, can't start other extension");
    return CHECK_PERMISSION_FAILED;
}

int AbilityManagerService::CheckCallerInfoQueryExtensionPermission(const AbilityRequest &abilityRequest)
{
    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    auto ret = AAFwk::PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_GET_TELEPHONY_STATE, specifyTokenId);
    if (!ret) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny for callerInfoQueryExtension");
        return CHECK_PERMISSION_FAILED;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "check permission success");
    return ERR_OK;
}

int AbilityManagerService::CheckFileAccessExtensionPermission(const AbilityRequest &abilityRequest)
{
    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    auto ret = AAFwk::PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_FILE_ACCESS_MANAGER, specifyTokenId);
    if (!ret) {
        return CHECK_PERMISSION_FAILED;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Temporary, FILEACCESS_EXTENSION use serviceExtension start-up rule.");
    return CheckCallServiceExtensionPermission(abilityRequest);
}

int AbilityManagerService::CheckUIExtensionPermission(const AbilityRequest &abilityRequest, int32_t validUserId)
{
    if (abilityRequest.want.HasParameter(AAFwk::SCREEN_MODE_KEY)) {
        // If started by embedded atomic service, allow it.
        return ERR_OK;
    } 

    auto extensionType = abilityRequest.abilityInfo.extensionAbilityType;
    if (AAFwk::UIExtensionWrapper::IsSystemUIExtension(extensionType)) {
        auto callerRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
        if (callerRecord == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid caller");
            return NO_FOUND_ABILITY_BY_CALLER;
        }

        if (!abilityRequest.appInfo.isSystemApp) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "bundle %{public}s want start or caller bundle %{public}s "
                "isn't system app, type %{public}d not allowed", abilityRequest.appInfo.bundleName.c_str(),
                callerRecord->GetApplicationInfo().bundleName.c_str(), extensionType);
            return CHECK_PERMISSION_FAILED;
        }
    }

    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    if (AAFwk::UIExtensionWrapper::IsSystemCallerNeeded(extensionType)) {
        auto callerRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
        if (callerRecord == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid caller");
            return NO_FOUND_ABILITY_BY_CALLER;
        }

        if (!callerRecord->GetApplicationInfo().isSystemApp
            && !AAFwk::PermissionVerification::GetInstance()->IsSACallByTokenId(specifyTokenId)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                     "bundle %{public}s want start but caller bundle %{public}s "
                     "isn't system app, type %{public}d not allowed",
                     abilityRequest.appInfo.bundleName.c_str(), callerRecord->GetApplicationInfo().bundleName.c_str(),
                     extensionType);
            return CHECK_PERMISSION_FAILED;
        }
    }

    if (!CheckUIExtensionCallerIsForeground(abilityRequest)) {
        return CHECK_PERMISSION_FAILED;
    }

    if (!CheckUIExtensionCallerPidByHostWindowId(abilityRequest, validUserId)) {
        return ERR_INVALID_CALLER;
    }

    return ERR_OK;
}

bool AbilityManagerService::CheckUIExtensionCallerIsForeground(const AbilityRequest &abilityRequest)
{
    if (!CheckUIExtensionCallerIsUIAbility(abilityRequest)) {
        // Check only if the caller is uiability, if caller is not a uiability, don't check.
        return true;
    }

    bool isBackgroundCall = true;
    auto ret = IsCallFromBackground(abilityRequest, isBackgroundCall, false);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "start uea when background");
        return false;
    }

    if (!isBackgroundCall) {
        return true;
    }

    if (CheckStartCallHasFloatingWindowForUIExtension(abilityRequest.callerToken)) {
        return true;
    }

    auto callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (callerAbility != nullptr) {
        if (UIExtensionWrapper::IsUIExtension(callerAbility->GetAbilityInfo().extensionAbilityType)) {
            auto tokenId = callerAbility->GetApplicationInfo().accessTokenId;
            bool isFocused = false;
            if (CheckUIExtensionIsFocused(tokenId, isFocused) == ERR_OK && isFocused) {
                TAG_LOGD(AAFwkTag::ABILITYMGR, "Root caller is foreground");
                return true;
            }
        }

        if (callerAbility->IsSceneBoard()) {
            return true;
        }
    }

    uint32_t specifyTokenId = static_cast<uint32_t>(abilityRequest.specifiedFullTokenId);
    if (PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_START_ABILITIES_FROM_BACKGROUND, specifyTokenId)) {
        return true;
    }

    TAG_LOGE(AAFwkTag::ABILITYMGR, "caller app not foreground, can't start %{public}s/%{public}s",
        abilityRequest.want.GetElement().GetBundleName().c_str(),
        abilityRequest.want.GetElement().GetAbilityName().c_str());
    return false;
}

bool AbilityManagerService::CheckStartCallHasFloatingWindowForUIExtension(const sptr<IRemoteObject> &callerToken)
{
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto sceneSessionManager = Rosen::SessionManagerLite::GetInstance().GetSceneSessionManagerLiteProxy();
        CHECK_POINTER_AND_RETURN_LOG(sceneSessionManager, CHECK_PERMISSION_FAILED, "sceneSessionManager is nullptr");
        bool hasFloatingWindow = false;
        auto err = sceneSessionManager->HasFloatingWindowForeground(callerToken, hasFloatingWindow);
        TAG_LOGI(AAFwkTag::ABILITYMGR,
            "check floatingwindow permission. Ret: %{public}d, hasFloatingWindow: %{public}d",
            static_cast<int32_t>(err), hasFloatingWindow);
        if (err != Rosen::WMError::WM_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR,
                "checking floatingwindow err: %{public}d", static_cast<int32_t>(err));
        } else if (hasFloatingWindow) {
            return true;
        }
    }
    return false;
}

bool AbilityManagerService::CheckUIExtensionCallerIsUIAbility(const AbilityRequest &abilityRequest)
{
    auto callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (callerAbility == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "caller ability invalid");
        return false;
    }

    if (callerAbility->GetAbilityInfo().type == AppExecFwk::AbilityType::PAGE) {
        return true;
    }

    if (UIExtensionWrapper::IsUIExtension(callerAbility->GetAbilityInfo().extensionAbilityType)) {
        callerAbility = GetUIExtensionRootCaller(abilityRequest.callerToken, abilityRequest.userId);
        if (callerAbility != nullptr && callerAbility->GetAbilityInfo().type == AppExecFwk::AbilityType::PAGE) {
            return true;
        }
    }

    return false;
}

bool AbilityManagerService::CheckUIExtensionCallerPidByHostWindowId(const AbilityRequest &abilityRequest,
    int32_t validUserId)
{
#ifdef SUPPORT_SCREEN
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        return true;
    }

    auto sessionInfo = abilityRequest.sessionInfo;
    CHECK_POINTER_AND_RETURN(sessionInfo, false);
    auto hostWindowId = sessionInfo->hostWindowId;
    auto callerUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    auto sceneSessionManager = Rosen::MockSessionManagerService::GetInstance().GetSceneSessionManagerLiteBySA(callerUserId);
    CHECK_POINTER_AND_RETURN(sceneSessionManager, false);
    pid_t hostPid = 0;
    // If host window id is scb, it will return with error.
    auto tokenId = abilityRequest.appInfo.accessTokenId;
    auto element = abilityRequest.want.GetElement();
    auto extType = abilityRequest.abilityInfo.extensionAbilityType;
    {
        HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, "Rosen::SceneSessionManager::CheckUIExtensionCreation");
        auto ret = sceneSessionManager->CheckUIExtensionCreation(hostWindowId, tokenId, element, extType, hostPid);
        if (ret == Rosen::WMError::WM_ERROR_INVALID_PERMISSION) {
            // If check permission failed, means target ability can't show on lock screen.
            TAG_LOGE(AAFwkTag::UI_EXT,
                "Check fail, tokenId: %{public}d, element: %{public}s/%{public}s, ret: %{public}d",
                tokenId, element.GetBundleName().c_str(), element.GetAbilityName().c_str(), ret);
            return false;
        }
    }

    TAG_LOGD(AAFwkTag::UI_EXT, "get pid %{public}d by windowId %{public}d", hostPid, hostWindowId);
    auto callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    CHECK_POINTER_AND_RETURN(callerAbility, false);
    if (callerAbility->IsSceneBoard()) {
        return true;
    }
    if (hostPid != 0 && callerAbility->GetPid() == hostPid) {
        return true;
    }

    if (UIExtensionWrapper::IsUIExtension(callerAbility->GetAbilityInfo().extensionAbilityType)) {
        TAG_LOGD(AAFwkTag::UI_EXT, "caller is nested uiextability");
        if (validUserId == U0_USER_ID || validUserId == U1_USER_ID) {
            validUserId =
                AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
        }
        auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);

        CHECK_POINTER_AND_RETURN(connectManager, false);
        bool matched = false;
        std::list<sptr<IRemoteObject>> callerList;
        connectManager->GetUIExtensionCallerTokenList(BaseExtensionRecord::TransferToExtensionRecordBase(callerAbility), callerList);
        for (auto &item : callerList) {
            auto ability = AAFwk::Token::GetAbilityRecordByToken(item);
            if (ability == nullptr) {
                TAG_LOGW(AAFwkTag::UI_EXT, "wrong ability");
                continue;
            }

            if ((hostPid != 0 && ability->GetPid() == hostPid) || ability->IsSceneBoard()) {
                matched = true;
                return true;
            }
        }
        if (!matched) {
            TAG_LOGE(AAFwkTag::UI_EXT, "Check nested uiextability failed");
        }
    }

    TAG_LOGE(AAFwkTag::UI_EXT, "check pid %{public}d fail, got %{public}d actual %{public}d",
        hostWindowId, hostPid, callerAbility->GetPid());
    return false;
#else
    return true;
#endif // SUPPORT_SCREEN
}

int AbilityManagerService::CheckCallServiceAbilityPermission(const AbilityRequest &abilityRequest)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call");
    AAFwk::PermissionVerification::VerificationInfo verificationInfo = CreateVerificationInfo(abilityRequest);
    if (IsCallFromBackground(abilityRequest, verificationInfo.isBackgroundCall, false) != ERR_OK) {
        return ERR_INVALID_VALUE;
    }

    int result = AAFwk::PermissionVerification::GetInstance()->CheckCallServiceAbilityPermission(
        verificationInfo, static_cast<uint32_t>(abilityRequest.specifiedFullTokenId));
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "without start serviceAbility permission");
    }
    return result;
}

int AbilityManagerService::CheckCallAbilityPermission(const AbilityRequest &abilityRequest, bool isSelector,
    uint32_t specifyTokenId, bool isCallByShortcut, bool isFreeInstallFromService)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call CheckCallAbilityPermission");

    AAFwk::PermissionVerification::VerificationInfo verificationInfo;
    verificationInfo.accessTokenId = abilityRequest.appInfo.accessTokenId;
    verificationInfo.visible = abilityRequest.abilityInfo.visible;
    verificationInfo.withContinuousTask = IsBackgroundTaskUid(IPCSkeleton::GetCallingUid());
    verificationInfo.specifyTokenId = specifyTokenId;
    auto callerAbilityRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (callerAbilityRecord != nullptr &&
        AbilityPermissionUtil::GetInstance().NeedCheckStatusBar(callerAbilityRecord, abilityRequest)) {
        uint32_t accessTokenId = abilityRequest.appInfo.accessTokenId;
        int32_t callerUid = callerAbilityRecord->GetUid();
        bool isMultiInstance =
            abilityRequest.appInfo.multiAppMode.multiAppModeType == AppExecFwk::MultiAppModeType::MULTI_INSTANCE;
        if (IsInStatusBar(accessTokenId, callerUid, isMultiInstance)) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "process in statusbar, calling UIAbility");
            return ERR_OK;
        }
    }
    if (isFreeInstallFromService || (callerAbilityRecord != nullptr &&
        callerAbilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::APP_SERVICE)) {
        verificationInfo.isBackgroundCall = false;
    } else if (IsCallFromBackground(abilityRequest, verificationInfo.isBackgroundCall, isSelector,
            specifyTokenId) != ERR_OK) {
        return ERR_CHECK_CALL_FROM_BACKGROUND_FAILED;
    }

    int result = AAFwk::PermissionVerification::GetInstance()->CheckCallAbilityPermission(
        verificationInfo, isCallByShortcut);
    if (result != ERR_OK) {
        auto sessionInfo = callerAbilityRecord ? callerAbilityRecord->GetSessionInfo() : nullptr;
        int32_t persistentId = (sessionInfo == nullptr) ? -1 : sessionInfo->persistentId;
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "without start pageAbility(FA) or ability(Stage) permission, caller:%{public}s %{public}d",
            callerAbilityRecord ? callerAbilityRecord->GetAbilityInfo().name.c_str() : "null record", persistentId);
    }
    return result;
}

int AbilityManagerService::CheckStartByCallPermission(const AbilityRequest &abilityRequest)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call");
    // check whether the target ability is page type and not specified mode.
    if (abilityRequest.abilityInfo.type != AppExecFwk::AbilityType::PAGE ||
        abilityRequest.abilityInfo.launchMode == AppExecFwk::LaunchMode::SPECIFIED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "called ability not common ability");
        return RESOLVE_CALL_ABILITY_TYPE_ERR;
    }

    // plugin not supported.
    if (AbilityRuntime::StartupUtil::IsStartPlugin(abilityRequest.want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "called ability cannot be plugin");
        return RESOLVE_CALL_NO_PERMISSIONS;
    }

    AAFwk::PermissionVerification::VerificationInfo verificationInfo;
    verificationInfo.accessTokenId = abilityRequest.appInfo.accessTokenId;
    verificationInfo.visible = abilityRequest.abilityInfo.visible;
    verificationInfo.withContinuousTask = IsBackgroundTaskUid(IPCSkeleton::GetCallingUid());
    if (IsCallFromBackground(abilityRequest, verificationInfo.isBackgroundCall, false) != ERR_OK) {
        return ERR_INVALID_VALUE;
    }

    if (AAFwk::PermissionVerification::GetInstance()->CheckStartByCallPermission(verificationInfo) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "without startAbilityByCall permission");
        return RESOLVE_CALL_NO_PERMISSIONS;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "caller has permission to resolve the call proxy of common ability");
    return ERR_OK;
}

int AbilityManagerService::IsCallFromBackground(const AbilityRequest &abilityRequest, bool &isBackgroundCall,
    bool isSelector, uint32_t specifyTokenId, bool isData)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!isData && AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        isBackgroundCall = true;
        return ERR_OK;
    }

    if (!isData && (SupportSystemAbilityPermission::IsSupportSaCallPermission() ||
        AbilityUtil::IsStartFreeInstall(abilityRequest.want))) {
        isBackgroundCall = false;
        return ERR_OK;
    }

    AppExecFwk::RunningProcessInfo processInfo;
    std::shared_ptr<AbilityRecord> callerAbility = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (callerAbility && callerAbility->GetAbilityInfo().bundleName == BUNDLE_NAME_DIALOG) {
        callerAbility = callerAbility->GetCallerRecord();
    }
    if (callerAbility) {
        if (callerAbility->IsForeground() || callerAbility->GetAbilityForegroundingFlag()) {
            isBackgroundCall = false;
            return ERR_OK;
        }
        // CallerAbility is not foreground, so check process state
        DelayedSingleton<AppScheduler>::GetInstance()->
            GetRunningProcessInfoByToken(callerAbility->GetToken(), processInfo);
        if (IsDelegatorCall(processInfo, abilityRequest)) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "The call is from AbilityDelegator, allow background-call.");
            isBackgroundCall = false;
            return ERR_OK;
        }
#ifdef SUPPORT_SCREEN
        if (AppUtils::GetInstance().IsStartOptionsWithAnimation() &&
            callerAbility->GetAbilityInfo().type == AppExecFwk::AbilityType::PAGE &&
            AbilityPermissionUtil::GetInstance().CheckStartCallHasFloatingWindow(
            abilityRequest.callerToken) == ERR_OK) {
            isBackgroundCall = false;
            return ERR_OK;
        }
#endif // SUPPORT_SCREEN
        auto abilityState = callerAbility->GetAbilityState();
        if (abilityState == AbilityState::BACKGROUND || abilityState == AbilityState::BACKGROUNDING ||
            // If uiability or uiextensionability ability state is foreground when terminate,
            // it will move to background firstly. So if startAbility in onBackground() lifecycle,
            // the actual ability state may be had changed to terminating from background or backgrounding.
            abilityState == AbilityState::TERMINATING) {
            return ERR_OK;
        }
    } else if (AbilityPermissionUtil::GetInstance().IsStartSelfUIAbility()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "call from capi, already checked background call");
        isBackgroundCall = false;
        return ERR_OK;
    } else {
        auto callerPid = IPCSkeleton::GetCallingPid();
        DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(callerPid, processInfo);
        if (processInfo.processName_.empty()) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "Can not find caller application by callerPid: %{private}d.", callerPid);
            bool isPermisson = false;
            if (isSelector) {
                isPermisson = AAFwk::PermissionVerification::GetInstance()->VerifyCallingPermission(
                    PermissionConstants::PERMISSION_START_ABILITIES_FROM_BACKGROUND, specifyTokenId);
            } else {
                isPermisson = AAFwk::PermissionVerification::GetInstance()->VerifyCallingPermission(
                    PermissionConstants::PERMISSION_START_ABILITIES_FROM_BACKGROUND);
            }
            if (isPermisson) {
                TAG_LOGD(AAFwkTag::ABILITYMGR, "Caller has PERMISSION_START_ABILITIES_FROM_BACKGROUND, PASS.");
                isBackgroundCall = false;
                return ERR_OK;
            }
            TAG_LOGE(AAFwkTag::ABILITYMGR, "without PERMISSION_START_ABILITIES_FROM_BACKGROUND, REJECT");
            return ERR_INVALID_VALUE;
        }
    }
    return SetBackgroundCall(processInfo, abilityRequest, isBackgroundCall);
}

int32_t AbilityManagerService::SetBackgroundCall(const AppExecFwk::RunningProcessInfo &processInfo,
    const AbilityRequest &abilityRequest, bool &isBackgroundCall) const
{
    if (IsDelegatorCall(processInfo, abilityRequest)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "The call is from AbilityDelegator, allow background-call.");
        isBackgroundCall = false;
        return ERR_OK;
    }

    if (backgroundJudgeFlag_) {
        isBackgroundCall = processInfo.state_ != AppExecFwk::AppProcessState::APP_STATE_FOREGROUND &&
            !processInfo.isFocused && !processInfo.isAbilityForegrounding;
    } else {
        isBackgroundCall = !processInfo.isFocused;
        if (!processInfo.isFocused && processInfo.state_ == AppExecFwk::AppProcessState::APP_STATE_FOREGROUND) {
            // Allow background startup within 1 second after application startup if state is FOREGROUND
            int64_t aliveTime = AbilityUtil::SystemTimeMillis() - processInfo.startTimeMillis_;
            isBackgroundCall = aliveTime > APP_ALIVE_TIME_MS;
            TAG_LOGD(AAFwkTag::ABILITYMGR, "Process %{public}s is alive %{public}s ms.",
                processInfo.processName_.c_str(), std::to_string(aliveTime).c_str());
        }
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "backgroundJudgeFlag: %{public}d, isBackgroundCall: %{public}d, callerAppState: %{public}d.",
        static_cast<int32_t>(backgroundJudgeFlag_),
        static_cast<int32_t>(isBackgroundCall),
        static_cast<int32_t>(processInfo.state_));

    return ERR_OK;
}

bool AbilityManagerService::IsTargetPermission(const Want &want) const
{
    std::string bundleName = PERMISSIONMGR_BUNDLE_NAME;
    std::string abilityName = PERMISSIONMGR_ABILITY_NAME;
    Security::AccessToken::PermissionGrantInfo info;
    Security::AccessToken::AccessTokenKit::GetPermissionManagerInfo(info);
    if (!info.grantBundleName.empty() && !info.grantServiceAbilityName.empty()) {
        bundleName = info.grantBundleName;
        abilityName = info.grantServiceAbilityName;
    }
    if (want.GetElement().GetBundleName() == bundleName &&
        want.GetElement().GetAbilityName() == abilityName) {
        return true;
    }

    return false;
}

inline bool AbilityManagerService::IsDelegatorCall(
    const AppExecFwk::RunningProcessInfo &processInfo, const AbilityRequest &abilityRequest) const
{
    /*  To make sure the AbilityDelegator is not counterfeited
     *   1. The caller-process must be test-process
     *   2. The callerToken must be nullptr
     */
    if (processInfo.isTestProcess &&
        !abilityRequest.callerToken && abilityRequest.want.GetBoolParam(IS_DELEGATOR_CALL, false)) {
        return true;
    }
    return false;
}

bool AbilityManagerService::CheckNewRuleSwitchState(const std::string &param)
{
    char value[NEW_RULE_VALUE_SIZE] = "false";
    int retSysParam = GetParameter(param.c_str(), "false", value, NEW_RULE_VALUE_SIZE);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "checkNewRuleSwitchState, %{public}s value: %{public}s", param.c_str(), value);
    if (retSysParam > 0 && !std::strcmp(value, "true")) {
        return true;
    }
    return false;
}

bool AbilityManagerService::GetStartUpNewRuleFlag() const
{
    return startUpNewRule_;
}

void AbilityManagerService::CallRequestDone(const sptr<IRemoteObject> &token, const sptr<IRemoteObject> &callStub)
{
    FreezeUtil::GetInstance().AddLifecycleEvent(token, "AbilityManagerService::CallRequestDone");
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER(abilityRecord);
    if (!JudgeSelfCalled(abilityRecord)) {
        return;
    }

    {
        std::lock_guard<ffrt::mutex> autoLock(abilityTokenLock_);
        callStubTokenMap_[callStub] = token;
    }
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(abilityRecord->GetOwnerMissionUserId());
        CHECK_POINTER(uiAbilityManager);
        uiAbilityManager->CallRequestDone(std::static_pointer_cast<UIAbilityRecord>(abilityRecord), callStub);
        return;
    }

    auto missionListManager = GetMissionListManagerByUserId(abilityRecord->GetOwnerMissionUserId());
    CHECK_POINTER(missionListManager);
    missionListManager->CallRequestDone(abilityRecord, callStub);
}

void AbilityManagerService::GetAbilityTokenByCalleeObj(const sptr<IRemoteObject> &callStub, sptr<IRemoteObject> &token)
{
    std::lock_guard<ffrt::mutex> autoLock(abilityTokenLock_);
    auto it = callStubTokenMap_.find(callStub);
    if (it == callStubTokenMap_.end()) {
        token = nullptr;
        return;
    }
    token = callStubTokenMap_[callStub];
}

int AbilityManagerService::AddStartControlParam(Want &want, const sptr<IRemoteObject> &callerToken)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (AAFwk::PermissionVerification::GetInstance()->IsSACall() ||
        AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        return ERR_OK;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    int32_t apiVersion = abilityRecord->GetApplicationInfo().apiTargetVersion;
    want.SetParam(DMS_API_VERSION, apiVersion);
    bool isCallerBackground = true;
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->
        GetRunningProcessInfoByToken(abilityRecord->GetToken(), processInfo);
    if (backgroundJudgeFlag_) {
        isCallerBackground = processInfo.state_ != AppExecFwk::AppProcessState::APP_STATE_FOREGROUND;
    } else {
        isCallerBackground = !processInfo.isFocused;
    }
    want.SetParam(DMS_IS_CALLER_BACKGROUND, isCallerBackground);
    return ERR_OK;
}

#ifdef WITH_DLP
int AbilityManagerService::CheckDlpForExtension(
    const Want &want, const sptr<IRemoteObject> &callerToken,
    int32_t userId, EventInfo &eventInfo, const EventName &eventName)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    // check if form frs
    auto callingUid = IPCSkeleton::GetCallingUid();
    std::string bundleName = want.GetBundle();
    if (callingUid == FOUNDATION_UID && FRS_BUNDLE_NAME == bundleName) {
        return ERR_OK;
    }

    if (!DlpUtils::AccessCheck(callerToken, want) ||
        VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verify failed");
        eventInfo.errCode = CHECK_PERMISSION_FAILED;
        EventReport::SendExtensionEvent(eventName, HISYSEVENT_FAULT, eventInfo);
        return CHECK_PERMISSION_FAILED;
    }
    return ERR_OK;
}
#endif // WITH_DLP

bool AbilityManagerService::JudgeSelfCalled(const std::shared_ptr<AbilityRecord> &abilityRecord)
{
    if (IPCSkeleton::GetCallingPid() == getprocpid()) {
        return true;
    }

    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    CHECK_POINTER_RETURN_BOOL(abilityRecord);
    auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
    if (abilityRecord->IsPluginAbility()) {
        auto caller = abilityRecord->GetCallerRecord();
        if (caller) {
            tokenID = caller->GetApplicationInfo().accessTokenId;
        }
    }
    if (callingTokenId != tokenID && !(abilityRecord->IsPluginAbility() &&
        abilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::EMBEDDED_UI)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self, caller:%{public}u, tokenId:%{public}u", callingTokenId, tokenID);
        return false;
    }

    return true;
}

bool AbilityManagerService::IsAppSelfCalled(const std::shared_ptr<AbilityRecord> &abilityRecord)
{
    CHECK_POINTER_RETURN_BOOL(abilityRecord);
    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenID = abilityRecord->GetApplicationInfo().accessTokenId;
    if (callingTokenId != tokenID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not app self called");
        return false;
    }
    return true;
}

std::shared_ptr<AbilityRecord> AbilityManagerService::GetFocusAbility()
{
#ifdef SUPPORT_SCREEN
    sptr<IRemoteObject> token;
    if (!GetWMSHandler()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "wmsHandler_ null");
        return nullptr;
    }

    GetWMSHandler()->GetFocusWindow(token);
    if (!token) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "token null");
        return nullptr;
    }

    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
    }
    return abilityRecord;
#endif

    return nullptr;
}

int AbilityManagerService::CheckUIExtensionIsFocused(uint32_t uiExtensionTokenId, bool& isFocused, uint64_t displayId)
{
    sptr<IRemoteObject> token;
    auto ret = GetTopAbilityInner(token, displayId);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getTopAbility failed");
        return ret;
    }

    auto topAbility = Token::GetAbilityRecordByToken(token);
    if (topAbility != nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "top ability: %{public}s/%{public}s, pid: %{public}d, tokenId: %{public}d",
            topAbility->GetWant().GetElement().GetBundleName().c_str(),
            topAbility->GetWant().GetElement().GetAbilityName().c_str(), topAbility->GetPid(),
            topAbility->GetApplicationInfo().accessTokenId);
    }

    bool focused = false;
    int32_t userId = GetValidUserId(DEFAULT_INVAL_VALUE);
    auto connectManager = GetUIExtensionAbilityManagerByUserId(userId);
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    if (connectManager || commonExtensionManager) {
        if (connectManager) {
            focused = connectManager->IsUIExtensionFocused(uiExtensionTokenId, token);
        }
        if (!focused && commonExtensionManager) {
            focused = commonExtensionManager->IsWindowExtensionFocused(uiExtensionTokenId, token);
        }
    } else {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "connectManager null, userId:%{public}d", userId);
    }
    if (!focused && userId != U0_USER_ID) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Check connectManager in user0");
        auto connectManager = GetUIExtensionAbilityManagerByUserId(U0_USER_ID); 
        auto commonExtensionManager = GetCommonExtensionManagerByUserId(U0_USER_ID);  
        if (connectManager || commonExtensionManager) {
            if (connectManager) {
                focused = connectManager->IsUIExtensionFocused(uiExtensionTokenId, token);
            }
            if (!focused && commonExtensionManager) {
                focused = commonExtensionManager->IsWindowExtensionFocused(uiExtensionTokenId, token);
            }
        } else {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "connectManager null, userId: 0");
        }
    }
    isFocused = focused;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "isFocused: %{public}d", isFocused);
    return ERR_OK;
}

int AbilityManagerService::AddFreeInstallObserver(const sptr<IRemoteObject> &callerToken,
    const sptr<AbilityRuntime::IFreeInstallObserver> &observer)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (freeInstallManager_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "freeInstallManager_ null");
        return ERR_INVALID_VALUE;
    }
    return freeInstallManager_->AddFreeInstallObserver(callerToken, observer);
}

int32_t AbilityManagerService::IsValidMissionIds(
    const std::vector<int32_t> &missionIds, std::vector<MissionValidResult> &results)
{
    auto userId = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    auto missionlistMgr = GetMissionListManagerByUserId(userId);
    if (missionlistMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "missionlistMgr null");
        return ERR_INVALID_VALUE;
    }

    return missionlistMgr->IsValidMissionIds(missionIds, results);
}

int AbilityManagerService::VerifyPermission(const std::string &permission, int pid, int uid)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "permission=%{public}s, pid=%{public}d, uid=%{public}d",
        permission.c_str(), pid, uid);
    if (permission.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verifyPermission permission invalid");
        return CHECK_PERMISSION_FAILED;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, ERR_INVALID_VALUE);

    int32_t callerUid = IPCSkeleton::GetCallingUid();
    std::string callerBundleName;
    if (IN_PROCESS_CALL(bms->GetNameForUid(callerUid, callerBundleName)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get caller bundleName failed");
        return CHECK_PERMISSION_FAILED;
    }

    int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    AppExecFwk::BundleInfo bundleInfo;
    bool queryBundleInfoRet = IN_PROCESS_CALL(
        bms->GetBundleInfo(callerBundleName, AppExecFwk::BundleFlag::GET_BUNDLE_WITH_ABILITIES, bundleInfo, userId));
    if (!queryBundleInfoRet) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get caller bundleInfo failed, %{public}s", callerBundleName.c_str());
        return CHECK_PERMISSION_FAILED;
    }
    for (auto it = bundleInfo.abilityInfos.begin(); it != bundleInfo.abilityInfos.end(); ++it) {
        if (it->isStageBasedModel == true) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "only support fa mode");
            return CHECK_PERMISSION_FAILED;
        }
    }

    std::string bundleName;
    if (IN_PROCESS_CALL(bms->GetNameForUid(uid, bundleName)) != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verifyPermission get bundle name failed");
        return CHECK_PERMISSION_FAILED;
    }

    int account = -1;
    DelayedSingleton<AppExecFwk::OsAccountManagerWrapper>::GetInstance()->GetOsAccountLocalIdFromUid(uid, account);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "bundleName: %{public}s, account: %{private}d", bundleName.c_str(), account);
    AppExecFwk::ApplicationInfo appInfo;
    if (!IN_PROCESS_CALL(bms->GetApplicationInfo(bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_DEFAULT,
        account, appInfo))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verifyPermission get application info failed");
        return CHECK_PERMISSION_FAILED;
    }

    int32_t ret = Security::AccessToken::AccessTokenKit::VerifyAccessToken(appInfo.accessTokenId, permission, false);
    if (ret != Security::AccessToken::PermissionState::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "PERMISSION_DENIED");
        return CHECK_PERMISSION_FAILED;
    }

    return ERR_OK;
}

int32_t AbilityManagerService::AcquireShareData(
    const int32_t &missionId, const sptr<IAcquireShareDataCallback> &shareData)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "missionId is %{public}d.", missionId);
    CHECK_CALLER_IS_SYSTEM_APP;
    int32_t userId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    std::shared_ptr<AbilityRecord> abilityRecord = nullptr;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        abilityRecord = uiAbilityManager->GetAbilityRecordsById(missionId);
    } else {
        auto missionListManager = GetMissionListManagerByUserId(userId);
        CHECK_POINTER_AND_RETURN(missionListManager, ERR_INVALID_VALUE);
        abilityRecord = missionListManager->GetAbilityRecordByMissionId(missionId);
    }
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_INVALID_VALUE;
    }
    std::lock_guard<ffrt::mutex> guard(iAcquireShareDataMapLock_);
    uniqueId_ = (uniqueId_ == INT_MAX) ? 0 : (uniqueId_ + 1);
    std::pair<int64_t, const sptr<IAcquireShareDataCallback>> shareDataPair =
        std::make_pair(abilityRecord->GetAbilityRecordId(), shareData);
    iAcquireShareDataMap_.emplace(uniqueId_, shareDataPair);
    abilityRecord->ShareData(uniqueId_);
    return ERR_OK;
}

int32_t AbilityManagerService::ShareDataDone(
    const sptr<IRemoteObject> &token, const int32_t &resultCode, const int32_t &uniqueId, WantParams &wantParam)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "resultCode:%{public}d, uniqueId:%{public}d", resultCode, uniqueId);
    if (!VerificationAllToken(token)) {
        return ERR_INVALID_VALUE;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN_LOG(abilityRecord, ERR_INVALID_VALUE, "ability record is nullptr.");
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }
    CHECK_POINTER_AND_RETURN_LOG(eventHandler_, ERR_INVALID_VALUE, "fail to get abilityEventHandler.");
    eventHandler_->RemoveEvent(SHAREDATA_TIMEOUT_MSG, uniqueId);
    return GetShareDataPairAndReturnData(abilityRecord, resultCode, uniqueId, wantParam);
}

int32_t AbilityManagerService::NotifySaveAsResult(const Want &want, int resultCode, int requestCode)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "requestCode is %{public}d.", requestCode);
    CHECK_CALLER_IS_SYSTEM_APP;
#ifdef WITH_DLP
    //caller check
    if (!DlpUtils::CheckCallerIsDlpManager(AbilityUtil::GetBundleManagerHelper())) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "caller check failed");
        return CHECK_PERMISSION_FAILED;
    }
#endif // WITH_DLP
    auto checkResult = AbilityUtil::CheckInstanceKey(want);
    if (checkResult != ERR_OK) {
        return checkResult;
    }

    StartAbilitySandboxSavefile::GetInstance().HandleResult(want, resultCode, requestCode);
    return ERR_OK;
}

void AbilityManagerService::SetRootSceneSession(const sptr<IRemoteObject> &rootSceneSession)
{
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    uiAbilityManager->SetRootSceneSession(rootSceneSession);
}

void AbilityManagerService::CallUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo,
    AbilityRuntime::StartParamsBySCB &params, bool &isColdStart)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER(uiAbilityManager);
    uiAbilityManager->CallUIAbilityBySCB(sessionInfo, params, isColdStart);
}

int32_t AbilityManagerService::SetSessionManagerService(const sptr<IRemoteObject> &sessionManagerService)
{
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }

    TAG_LOGI(AAFwkTag::ABILITYMGR, "call setSessionManagerService of WMS");
    bool ret = Rosen::MockSessionManagerService::GetInstance().SetSessionManagerService(sessionManagerService);
    if (ret) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Call SetSessionManagerService of WMS.");
        return ERR_OK;
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "SMS setSessionManagerService return false");
    return SET_SMS_FAILED;
}

int32_t AbilityManagerService::StartSpecifiedAbilityBySCB(const Want &want, const StartSpecifiedAbilityParams &params)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartSpecifiedAbilityBySCB");
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return ERR_PERMISSION_DENIED;
    }
    StartAbilityUtils::startSpecifiedBySCB = true;
    StartAbilityWrapParam param = {
        .want = want,
        .isBySCB = true,
        .startSpecifiedParams = std::make_shared<StartSpecifiedAbilityParams>(params),
    };
    auto ret = StartAbilityInner(param);
    StartAbilityUtils::startSpecifiedBySCB = false;
    return ret;
}

int32_t AbilityManagerService::RegisterIAbilityManagerCollaborator(
    int32_t type, const sptr<IAbilityManagerCollaborator> &impl)
{
    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    auto callingUid = IPCSkeleton::GetCallingUid();
    if (!isSaCall || (callingUid != AppUtils::GetInstance().GetCollaboratorBrokerUID() &&
        callingUid != AppUtils::GetInstance().GetCollaboratorBrokerReserveUID())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interface only support broker");
        return CHECK_PERMISSION_FAILED;
    }
    if (!CheckCollaboratorType(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "collaborator register failed, invalid type");
        return ERR_INVALID_VALUE;
    }
    {
        std::lock_guard<ffrt::mutex> autoLock(collaboratorMapLock_);
        collaboratorMap_[type] = impl;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::UnregisterIAbilityManagerCollaborator(int32_t type)
{
    auto isSaCall = AAFwk::PermissionVerification::GetInstance()->IsSACall();
    auto callingUid = IPCSkeleton::GetCallingUid();
    if (!isSaCall || (callingUid != AppUtils::GetInstance().GetCollaboratorBrokerUID() &&
        callingUid != AppUtils::GetInstance().GetCollaboratorBrokerReserveUID())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interface only support broker");
        return CHECK_PERMISSION_FAILED;
    }
    if (!CheckCollaboratorType(type)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "collaborator unregister failed, invalid type");
        return ERR_INVALID_VALUE;
    }
    {
        std::lock_guard<ffrt::mutex> autoLock(collaboratorMapLock_);
        collaboratorMap_.erase(type);
    }
    return ERR_OK;
}

int32_t AbilityManagerService::GetCollaboratorType(const std::string &codePath) const
{
    if (codePath == std::to_string(CollaboratorType::RESERVE_TYPE)) {
        return CollaboratorType::RESERVE_TYPE;
    } else if (codePath == std::to_string(CollaboratorType::OTHERS_TYPE)) {
        return CollaboratorType::OTHERS_TYPE;
    }
    return 0;
}

sptr<IAbilityManagerCollaborator> AbilityManagerService::GetAbilityManagerCollaborator()
{
    if (IPCSkeleton::GetCallingUid() != FOUNDATION_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not foundation call");
        return nullptr;
    }
    return GetCollaborator(CollaboratorType::RESERVE_TYPE);
}

sptr<IAbilityManagerCollaborator> AbilityManagerService::GetCollaborator(int32_t type)
{
    if (!CheckCollaboratorType(type)) {
        return nullptr;
    }
    {
        std::lock_guard<ffrt::mutex> autoLock(collaboratorMapLock_);
        auto it = collaboratorMap_.find(type);
        if (it != collaboratorMap_.end()) {
            return it->second;
        }
    }
    return nullptr;
}

bool AbilityManagerService::CheckCollaboratorType(int32_t type)
{
    if (type != CollaboratorType::RESERVE_TYPE && type != CollaboratorType::OTHERS_TYPE) {
        return false;
    }
    return true;
}

void AbilityManagerService::GetConnectManagerAndUIExtensionBySessionInfo(const sptr<SessionInfo> &sessionInfo,
    std::shared_ptr<UIExtensionAbilityManager> &connectManager, std::shared_ptr<BaseExtensionRecord> &targetAbility,
    bool needCheck)
{
    targetAbility = nullptr;
    int32_t userId = GetValidUserId(DEFAULT_INVAL_VALUE);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId=%{public}d", userId);
    connectManager = GetUIExtensionAbilityManagerByUserId(userId);
    if (connectManager) {
        targetAbility = connectManager->GetUIExtensionBySessionInfo(sessionInfo);
        if (needCheck && targetAbility == nullptr) {
            targetAbility = connectManager->GetUIExtensionBySessionFromServiceMap(sessionInfo);
        }
    } else {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "connectManager null, userId:%{public}d", userId);
    }
    if (targetAbility == nullptr && userId != U0_USER_ID) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "try to find UIExtension in user0");
        connectManager = GetUIExtensionAbilityManagerByUserId(U0_USER_ID);
        if (connectManager) {
            targetAbility = connectManager->GetUIExtensionBySessionInfo(sessionInfo);
            if (needCheck && targetAbility == nullptr) {
                targetAbility = connectManager->GetUIExtensionBySessionFromServiceMap(sessionInfo);
            }
        } else {
            TAG_LOGW(AAFwkTag::ABILITYMGR, "connectManager null, userId:0");
        }
    }
}

int32_t AbilityManagerService::RegisterStatusBarDelegate(sptr<AbilityRuntime::IStatusBarDelegate> delegate)
{
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->RegisterStatusBarDelegate(delegate);
}

int32_t AbilityManagerService::KillProcessWithPrepareTerminate(const std::vector<int32_t> &pids, bool clear)
{
    if (!IsCallerSceneBoard() && !PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_KILL_APP_PROCESSES)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not scb called or has kill permission, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->TryPrepareTerminateByPids(pids, clear);
}

bool AbilityManagerService::ProcessLowMemoryKill(int32_t pid, const ExitReason &reason, bool isKillPrecedeStart)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!isKillPrecedeStart) {
        return false;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    if (uiAbilityManager == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "null uiAbilityManager");
        return false;
    }
    if (uiAbilityManager->IsBundleStarting(pid)) {
        return true;
    }
    // set ability record kill reason
    uiAbilityManager->RecordPidKilling(pid, reason.exitMsg, isKillPrecedeStart);
    return false;
}

int32_t AbilityManagerService::KillProcessWithReason(int32_t pid, const ExitReason &reason)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    bool isKillPrecedeStart =
        (reason.reason == Reason::REASON_RESOURCE_CONTROL && reason.exitMsg == GlobalConstant::LOW_MEMORY_KILL) ||
        reason.shouldSkipKillInStartup;
    EventInfo eventInfo;
    eventInfo.callerPid = IPCSkeleton::GetCallingPid();
    eventInfo.pid = pid;
    eventInfo.exitMsg = reason.exitMsg;
    eventInfo.shouldKillForeground = reason.shouldKillForeground;
#ifdef RESOURCE_SCHEDULE_SERVICE_ENABLE
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    if (!ResourceSchedule::ResSchedClient::GetInstance().IsAllowedKill(callerUid, reason.exitMsg)) {
        TAG_LOGE(AAFwkTag::APPMGR, "kill reason verification fail");
        return ERR_PERMISSION_DENIED;
    }
#endif
    auto ret = KillProcessWithReasonInner(pid, reason, isKillPrecedeStart);
    TAG_LOGE(AAFwkTag::ABILITYMGR, "KillProcessWithReason pid:%{public}d,ret:%{public}d,reason:%{public}s", pid, ret,
        reason.exitMsg.c_str());
    if (isKillPrecedeStart) {
        AbilityEventUtil::SendKillProcessWithReasonEvent(ret, "KillProcessWithReason", eventInfo);
    }
    return ret;
}

int32_t AbilityManagerService::KillProcessWithReasonInner(int32_t pid, const ExitReason &reason,
    bool isKillPrecedeStart)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    bool supportShell = AmsConfigurationParameter::GetInstance().IsSupportAAKillWithReason();
    auto isShellCall = PermissionVerification::GetInstance()->IsShellCall();
    auto isCallingPerm = PermissionVerification::GetInstance()->VerifyCallingPermission(
        AAFwk::PermissionConstants::PERMISSION_KILL_APP_PROCESSES);
    if (!isCallingPerm && !(supportShell && isShellCall)) {
        TAG_LOGE(AAFwkTag::APPMGR, "permission verification fail");
        return ERR_PERMISSION_DENIED;
    }

    if (!reason.shouldKillForeground) {
        AppExecFwk::RunningProcessInfo processInfo;
        DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(pid, processInfo);
        if (processInfo.isAbilityForegrounding || processInfo.isFocused) {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "do not kill foreground apps, pid = %{public}d", pid);
            return ERR_KILL_APP_WHILE_FOREGROUND;
        }
    }

    if (ProcessLowMemoryKill(pid, reason, isKillPrecedeStart)) {
        // if app is already starting, return
        TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}d is starting", pid);
        return ERR_KILL_APP_WHILE_STARTING;
    }
    CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
    auto ret = appExitReasonHelper_->RecordProcessExitReason(pid, reason, true);
    if (ret != ERR_OK) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "RecordAppExitReason failed, ret:%{public}d", ret);
    }
    std::vector<int32_t> pidToBeKilled = { pid };
    return IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->KillProcessesByPids(pidToBeKilled,
        reason.exitMsg, true, isKillPrecedeStart));
}

int32_t AbilityManagerService::RegisterAutoStartupSystemCallback(const sptr<IRemoteObject> &callback)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->RegisterAutoStartupSystemCallback(callback);
}

int32_t AbilityManagerService::UnregisterAutoStartupSystemCallback(const sptr<IRemoteObject> &callback)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->UnregisterAutoStartupSystemCallback(callback);
}

int32_t AbilityManagerService::SetApplicationAutoStartup(const AutoStartupInfo &info)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->SetApplicationAutoStartup(info);
}

int32_t AbilityManagerService::CancelApplicationAutoStartup(const AutoStartupInfo &info)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->CancelApplicationAutoStartup(info);
}

int32_t AbilityManagerService::QueryAllAutoStartupApplications(std::vector<AutoStartupInfo> &infoList)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    std::vector<int32_t> userIds;
    AbilityRuntime::UserController::GetInstance().GetAllForegroundUserId(userIds);
    int32_t result = ERR_OK;
    auto iter = userIds.begin();
    while (iter != userIds.end()) {
        result = abilityAutoStartupService_->QueryAllAutoStartupApplications(infoList, *iter);
        if (result != ERR_OK) {
            return result;
        }
        iter++;
    }
    return result;
}

int32_t AbilityManagerService::GetAutoStartupStatusForSelf(bool &isAutoStartEnabled)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->GetAutoStartupStatusForSelf(IPCSkeleton::GetCallingTokenID(),
        isAutoStartEnabled);
}

int32_t AbilityManagerService::ManualStartAutoStartupApps(int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "ManualStartAutoStartupApps userId: %{public}d", userId);
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_MANAGE_APP_BOOT_INTERNAL)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "verify PERMISSION_MANAGE_APP_BOOT_INTERNAL fail");
        return CHECK_PERMISSION_FAILED;
    }
    StartAutoStartupApps(userId, true);
    return ERR_OK;
}

int AbilityManagerService::PrepareTerminateAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool &isTerminate)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Call.");
    if (sessionInfo == nullptr || sessionInfo->sessionToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return ERR_INVALID_VALUE;
    }

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sceneboard called, not allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }

    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    auto abilityRecord = uiAbilityManager->GetUIAbilityRecordBySessionInfo(sessionInfo);
    isTerminate = uiAbilityManager->PrepareTerminateAbility(abilityRecord, true);

    return ERR_OK;
}

int AbilityManagerService::RegisterSessionHandler(const sptr<IRemoteObject> &object)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call");
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    sptr<ISessionHandler> handler = iface_cast<ISessionHandler>(object);
    uiAbilityManager->SetSessionHandler(handler);
    return ERR_OK;
}

int32_t AbilityManagerService::RegisterAppDebugListener(sptr<AppExecFwk::IAppDebugListener> listener)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<AppScheduler>::GetInstance()->RegisterAppDebugListener(listener);
}

int32_t AbilityManagerService::UnregisterAppDebugListener(sptr<AppExecFwk::IAppDebugListener> listener)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }
    return DelayedSingleton<AppScheduler>::GetInstance()->UnregisterAppDebugListener(listener);
}

std::shared_ptr<AbilityDebugDeal> AbilityManagerService::ConnectInitAbilityDebugDeal()
{
    if (abilityDebugDeal_ != nullptr) {
        return abilityDebugDeal_;
    }

    std::unique_lock<ffrt::mutex> lock(abilityDebugDealLock_);
    if (abilityDebugDeal_ != nullptr) {
        return abilityDebugDeal_;
    }

    TAG_LOGD(AAFwkTag::ABILITYMGR, "Creat ability debug deal object.");
    abilityDebugDeal_ = std::make_shared<AbilityDebugDeal>();
    if (abilityDebugDeal_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "creat ability debug deal object failed");
        return nullptr;
    }

    abilityDebugDeal_->RegisterAbilityDebugResponse();
    return abilityDebugDeal_;
}

int32_t AbilityManagerService::AttachAppDebug(const std::string &bundleName, bool isDebugFromLocal)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (isDebugFromLocal &&
        !AAFwk::PermissionVerification::GetInstance()->VerifyStartLocalDebug(IPCSkeleton::GetCallingTokenID())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "local debugging, permission denied");
        return CHECK_PERMISSION_FAILED;
    } else if (!isDebugFromLocal && !system::GetBoolParameter(DEVELOPER_MODE_STATE, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer Mode");
        return ERR_NOT_DEVELOPER_MODE;
    }

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() &&
        !AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    int32_t err = ERR_OK;
    int32_t userId = GetValidUserId(DEFAULT_INVAL_VALUE);
    AppExecFwk::ApplicationInfo appInfo;
    if (!StartAbilityUtils::GetApplicationInfo(bundleName, userId, appInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Get application info failed: %{public}s", bundleName.c_str());
        return ERR_INVALID_VALUE;
    }

    if (!IsAllowAttachOrDetachAppDebug(appInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "release application or check permission error");
        return ERR_NOT_IN_APP_PROVISION_MODE;
    }

    ConnectInitAbilityDebugDeal();
    return IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->AttachAppDebug(bundleName, isDebugFromLocal));
}

int32_t AbilityManagerService::DetachAppDebug(const std::string &bundleName, bool isDebugFromLocal)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (isDebugFromLocal &&
        !AAFwk::PermissionVerification::GetInstance()->VerifyStartLocalDebug(IPCSkeleton::GetCallingTokenID())) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "local debugging, permission denied");
        return CHECK_PERMISSION_FAILED;
    } else if (!isDebugFromLocal && !system::GetBoolParameter(DEVELOPER_MODE_STATE, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not developer Mode");
        return ERR_NOT_DEVELOPER_MODE;
    }

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() &&
        !AAFwk::PermissionVerification::GetInstance()->IsShellCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    int32_t err = ERR_OK;
    int32_t userId = GetValidUserId(DEFAULT_INVAL_VALUE);
    AppExecFwk::ApplicationInfo appInfo;
    if (!StartAbilityUtils::GetApplicationInfo(bundleName, userId, appInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Get application info failed: %{public}s", bundleName.c_str());
        return ERR_INVALID_VALUE;
    }

    if (!IsAllowAttachOrDetachAppDebug(appInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "release application or check permission error");
        return ERR_NOT_IN_APP_PROVISION_MODE;
    }

    return IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->DetachAppDebug(bundleName));
}

bool AbilityManagerService::IsAllowAttachOrDetachAppDebug(AppExecFwk::ApplicationInfo &appInfo)
{
    if (appInfo.appProvisionType == AppExecFwk::Constants::APP_PROVISION_TYPE_DEBUG) {
        return true;
    }
    bool isDebugEnabled = AppUtils::GetInstance().IsSupportAllowDebugPermission();
    if (isDebugEnabled && AccessTokenKit::VerifyAccessToken(appInfo.accessTokenId,
        PermissionConstants::PERMISSION_ALL_DEBUG , false) == AppExecFwk::Constants::PERMISSION_GRANTED) {
        return true;
    }
    return false;
}

std::string AbilityManagerService::InsightIntentGetcallerBundleName()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "InsightIntentGetcallerBundleName called");
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    auto bundleMgr = AbilityUtil::GetBundleManagerHelper();
    std::string callerBundlename;
    if (bundleMgr != nullptr) {
       IN_PROCESS_CALL(bundleMgr->GetNameForUid(callerUid, callerBundlename));
    }
    return callerBundlename;
}

int32_t AbilityManagerService::StartAbilityWithServiceMatch(const InsightIntentExecuteParam &param, int32_t userId, int requestCode)
{
    AAFwk::Want want;
    AppExecFwk::ElementName element("", param.bundleName_, param.abilityName_);
    want.SetElement(element);
    auto IParam = param.insightIntentParam_;
    if (IParam == nullptr) {
        return ERR_INVALID_VALUE;
    }
    want.SetParams(*IParam);
    want.SetUri(Uri(IParam->GetStringParam(static_cast<std::string>("uri"))));
    want.SetAction(IParam->GetStringParam(static_cast<std::string>("action")));

    EventInfo eventInfo = BuildEventInfo(want, userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .requestCode = requestCode,
        .userId = userId,
        .isServiceMatch = true,
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    AAFWK::ContinueRadar::GetInstance().ClickIconStartAbility("StartAbilityWrap", want.GetFlags(), ret);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityError:%{public}d", eventInfo.errCode);
    }
    return ret;

}

int32_t AbilityManagerService::ExecuteIntent(uint64_t key, const sptr<IRemoteObject> &callerToken,
    const InsightIntentExecuteParam &param)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (param.isServiceMatch_) {
        return StartAbilityWithServiceMatch(param);
    }
    auto callerBundlename = InsightIntentGetcallerBundleName();
    if (callerBundlename.empty()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "callerBundlename is null");
    }

    if(IsCrossUserCall(param.userId_)) {
        if (VerifyAccountPermission(param.userId_) != ERR_OK) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
            return CHECK_PERMISSION_FAILED;
        }
        if (!JudgeMultiUserConcurrency(param.userId_)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "multi-user non-concurrent unsatisfied");
            return ERR_CROSS_USER;
        }
    }

    AbilityRuntime::ExtractInsightIntentGenericInfo infos = GetInsightIntentGenericInfo(param);
    bool openLinkExecuteFlag = infos.decoratorType == AbilityRuntime::INSIGHT_INTENTS_DECORATOR_TYPE_LINK;
    bool ignoreAbilityName = openLinkExecuteFlag ||
        (infos.decoratorType == AbilityRuntime::INSIGHT_INTENTS_DECORATOR_TYPE_PAGE) ||
        (infos.decoratorType == AbilityRuntime::INSIGHT_INTENTS_DECORATOR_TYPE_FUNCTION);
    auto paramPtr = std::make_shared<InsightIntentExecuteParam>(param);
    int32_t ret = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckAndUpdateParam(key, callerToken,
        paramPtr, callerBundlename, ignoreAbilityName);
    if (ret != ERR_OK) {
        return ret;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "execute insight intent, bundleName: %{public}s, moduleName: %{public}s, "
        "intentName: %{public}s, intentId:%{public}" PRIu64", openLinkExecuteFlag: %{public}d, executeMode: %{public}d, "
        "userId: %{public}d",
        param.bundleName_.c_str(), param.moduleName_.c_str(), param.insightIntentName_.c_str(), param.insightIntentId_,
        openLinkExecuteFlag, param.executeMode_, param.userId_);

    if (openLinkExecuteFlag) {
        return IntentOpenLinkInner(paramPtr, infos, param.userId_);
    }

    Want want;
    ret = InsightIntentExecuteManager::GenerateWant(paramPtr, infos, want);
    if (ret != ERR_OK) {
        return ret;
    }
    int32_t callerUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    EventInfo eventInfo = BuildEventInfo(want, callerUserId);
    switch (param.executeMode_) {
        case AppExecFwk::ExecuteMode::UI_ABILITY_FOREGROUND:
            TAG_LOGD(AAFwkTag::ABILITYMGR, "ExecuteMode UI_ABILITY_FOREGROUND.");
            ret = StartAbilityWithInsightIntent(want, param.userId_);
            if (ret != ERR_OK) {
                eventInfo.errReason = "StartAbilityWithInsightIntent error";
                SendIntentReport(eventInfo, ret, param.insightIntentName_);
            }
            break;
        case AppExecFwk::ExecuteMode::UI_ABILITY_BACKGROUND: {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "ExecuteMode UI_ABILITY_BACKGROUND.");
            ret = StartAbilityByCallWithInsightIntent(want, callerToken, param, param.userId_);
            if (ret != ERR_OK) {
                eventInfo.errReason = "StartAbilityByCallWithInsightIntent error";
                SendIntentReport(eventInfo, ret, param.insightIntentName_);
            }
            break;
        }
        case AppExecFwk::ExecuteMode::UI_EXTENSION_ABILITY:
            TAG_LOGW(AAFwkTag::ABILITYMGR, "executeMode UI_EXTENSION_ABILITY not supported");
            ret = ERR_INVALID_OPERATION;
            break;
        case AppExecFwk::ExecuteMode::SERVICE_EXTENSION_ABILITY:
            TAG_LOGD(AAFwkTag::ABILITYMGR, "ExecuteMode SERVICE_EXTENSION_ABILITY.");
            ret = StartExtensionAbilityWithInsightIntent(want, AppExecFwk::ExtensionAbilityType::SERVICE, param.userId_);
            if (ret != ERR_OK) {
                eventInfo.errReason = "StartExtensionAbilityWithInsightIntent error";
                SendIntentReport(eventInfo, ret, param.insightIntentName_);
            }
            break;
        default:
            TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid executeMode");
            ret = ERR_INVALID_OPERATION;
            break;
    }
    if (ret == START_ABILITY_WAITING) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "Top ability is foregrounding. The intent will be queued for execution");
        ret = ERR_OK;
    }
    if (ret != ERR_OK) {
        DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->RemoveExecuteIntent(paramPtr->insightIntentId_);
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "ExecuteIntent done, ret: %{public}d.", ret);
    return ret;
}

bool AbilityManagerService::IsAbilityStarted(AbilityRequest &abilityRequest,
    std::shared_ptr<AbilityRecord> &targetRecord, const int32_t oriValidUserId)
{
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "scene board enable");
        auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, false);
        return uiAbilityManager->IsAbilityStarted(abilityRequest, targetRecord);
    }

    auto missionListMgr = GetMissionListManagerByUserId(oriValidUserId);
    if (missionListMgr == nullptr) {
        return false;
    }
    return missionListMgr->IsAbilityStarted(abilityRequest, targetRecord);
}

int32_t AbilityManagerService::OnExecuteIntent(AbilityRequest &abilityRequest,
    std::shared_ptr<AbilityRecord> &targetRecord)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "onExecuteIntent");
    if (targetRecord == nullptr || targetRecord->GetScheduler() == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "null scheduler");
        return ERR_INVALID_VALUE;
    }
    targetRecord->GetScheduler()->OnExecuteIntent(abilityRequest.want);

    return ERR_OK;
}

int32_t AbilityManagerService::StartAbilityWithInsightIntent(const Want &want, int32_t userId, int requestCode)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    bool startWithAccount = want.GetBoolParam(START_ABILITY_TYPE, false);
    if (startWithAccount || IsCrossUserCall(userId)) {
        (const_cast<Want &>(want)).RemoveParam(START_ABILITY_TYPE);
        CHECK_CALLER_IS_SYSTEM_APP;
    }
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    AbilityUtil::RemoveInstanceKey(const_cast<Want &>(want));
    EventInfo eventInfo = BuildEventInfo(want, userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .requestCode = requestCode,
        .userId = userId
    };
    int32_t ret = StartAbilityWrap(startAbilityWrapParam);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityError:%{public}d", ret);
    }
    return ret;
}

int32_t AbilityManagerService::StartExtensionAbilityWithInsightIntent(const Want &want,
    AppExecFwk::ExtensionAbilityType extensionType, int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    return StartExtensionAbilityInner(want, nullptr, userId, extensionType, true);
}

int32_t AbilityManagerService::StartAbilityByCallWithInsightIntent(const Want &want,
    const sptr<IRemoteObject> &callerToken, const InsightIntentExecuteParam &param, int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "called");
    sptr<IAbilityConnection> connect = sptr<AbilityBackgroundConnection>::MakeSptr();
    if (connect == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid connect");
        return ERR_INVALID_VALUE;
    }

    AbilityUtil::RemoveWantKey(const_cast<Want &>(want));
    AbilityUtil::RemoveInstanceKey(const_cast<Want &>(want));
    AbilityRequest abilityRequest;
    abilityRequest.callType = AbilityCallType::CALL_REQUEST_TYPE;
    abilityRequest.callerUid = IPCSkeleton::GetCallingUid();
    abilityRequest.callerToken = callerToken;
    abilityRequest.startSetting = nullptr;
    abilityRequest.want = want;
    abilityRequest.connect = connect;
    int32_t result = GenerateAbilityRequest(want, -1, abilityRequest, callerToken, GetValidUserId(userId));
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request error");
        return result;
    }
    std::shared_ptr<AbilityRecord> targetRecord;
    int32_t oriValidUserId = GetValidUserId(userId);
    auto missionListMgr = GetMissionListManagerByUserId(oriValidUserId);
    if (IsAbilityStarted(abilityRequest, targetRecord, oriValidUserId)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "ability has already started");
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
        result = OnExecuteIntent(abilityRequest, targetRecord);
    }  else {
        result = StartAbilityByCall(want, connect, callerToken, oriValidUserId);
    }
    ResSchedUtil::GetInstance().ReportAbilityIntentExemptionInfoToRSS(abilityRequest.uid, 0);
    DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->SetIntentExemptionInfo(
        abilityRequest.uid);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "startAbilityByCallWithInsightIntent %{public}d uid:%{public}d",
        result, abilityRequest.uid);
    return result;
}

bool AbilityManagerService::IsAbilityControllerStart(const Want &want)
{
    auto callingUid = IPCSkeleton::GetCallingUid();
    bool isBrokerCall = (callingUid == AppUtils::GetInstance().GetCollaboratorBrokerUID() ||
        callingUid == AppUtils::GetInstance().GetCollaboratorBrokerReserveUID());
    if (isBrokerCall) {
        return IsAbilityControllerStart(want, want.GetBundle());
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "interface only support broker");
    return true;
}

int32_t AbilityManagerService::ExecuteInsightIntentDone(const sptr<IRemoteObject> &token, uint64_t intentId,
    const InsightIntentExecuteResult &result)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(token);
    CHECK_POINTER_AND_RETURN_LOG(abilityRecord, ERR_INVALID_VALUE, "Ability record is nullptr.");
    if (!JudgeSelfCalled(abilityRecord)) {
        return CHECK_PERMISSION_FAILED;
    }

    Want want = abilityRecord->GetWant();
    if (InsightIntentExecuteParam::IsInsightIntentExecute(want)) {
        InsightIntentExecuteParam::RemoveInsightIntent(want);
        abilityRecord->SetWant(want);
    }
    // check send by same bundleName.
    std::string bundleNameStored = "";
    auto ret = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->GetBundleName(intentId, bundleNameStored);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "matched bundleName failed, intentId:%{public}" PRIu64"", intentId);
        return ERR_INVALID_VALUE;
    }

    std::string bundleName = abilityRecord->GetAbilityInfo().bundleName;
    if (bundleNameStored != bundleName) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "bundleName %{public}s and %{public}s mismatch", bundleName.c_str(), bundleNameStored.c_str());
        return ERR_INVALID_VALUE;
    }

    std::string callerBundleName;
    DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->GetCallerBundleName(intentId, callerBundleName);
    uint32_t initiatorTokenId = abilityRecord->GetApplicationInfo().accessTokenId;
#ifdef SUPPORT_UPMS
    if (!callerBundleName.empty()) {
        abilityRecord->GrantUriPermission(result.uris, result.flags, callerBundleName, initiatorTokenId);
    }
#endif // SUPPORT_UPMS

    return DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->ExecuteIntentDone(
        intentId, result.innerErr, result);
}

int32_t AbilityManagerService::SetApplicationAutoStartupByEDM(const AutoStartupInfo &info, bool flag)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->SetApplicationAutoStartupByEDM(info, flag);
}

int32_t AbilityManagerService::CancelApplicationAutoStartupByEDM(const AutoStartupInfo &info, bool flag)
{
    if (abilityAutoStartupService_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityAutoStartupService_ null");
        return ERR_NO_INIT;
    }
    return abilityAutoStartupService_->CancelApplicationAutoStartupByEDM(info, flag);
}

int32_t AbilityManagerService::GetForegroundUIAbilities(std::vector<AppExecFwk::AbilityStateData> &list)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    CHECK_CALLER_IS_SYSTEM_APP;
    auto isPerm = AAFwk::PermissionVerification::GetInstance()->VerifyRunningInfoPerm();
    if (!isPerm) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    std::vector<AbilityRunningInfo> abilityRunningInfos;
    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        uiAbilityManager->GetAbilityRunningInfos(abilityRunningInfos, isPerm);
    } else {
        auto missionListManager = GetCurrentMissionListManager();
        CHECK_POINTER_AND_RETURN(missionListManager, ERR_NULL_OBJECT);
        missionListManager->GetAbilityRunningInfos(abilityRunningInfos, isPerm);
    }

    for (auto &info : abilityRunningInfos) {
        if (info.abilityState != AbilityState::FOREGROUND) {
            continue;
        }

        AppExecFwk::AbilityStateData abilityData;
        abilityData.bundleName = info.ability.GetBundleName();
        abilityData.moduleName = info.ability.GetModuleName();
        abilityData.abilityName = info.ability.GetAbilityName();
        abilityData.abilityState = info.abilityState;
        abilityData.pid = info.pid;
        abilityData.uid = info.uid;
        abilityData.abilityType = static_cast<int32_t>(AppExecFwk::AbilityType::PAGE);
        abilityData.appCloneIndex = info.appCloneIndex;
        abilityData.callerBundleName = info.firstCallerBundleName;
        AppExecFwk::ApplicationInfo appInfo;
        int32_t userId = abilityData.uid / BASE_USER_RANGE;
        if (!StartAbilityUtils::GetApplicationInfo(abilityData.bundleName, userId, appInfo)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "can't get applicationInfo through bundleName");
        } else if (appInfo.bundleType == AppExecFwk::BundleType::ATOMIC_SERVICE) {
            abilityData.isAtomicService = true;
        }
        list.push_back(abilityData);
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Get foreground ui abilities end, list.size = %{public}zu.", list.size());
    return ERR_OK;
}

void AbilityManagerService::NotifyConfigurationChange(const AppExecFwk::Configuration &config, int32_t userId)
{
    auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
    if (collaborator == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "collaborator getCollaborator null");
        return;
    }
    collaborator->UpdateConfiguration(config, userId);
}

void AbilityManagerService::NotifyStartResidentProcess(std::vector<AppExecFwk::BundleInfo> &bundleInfos)
{
    int32_t callerUser =
        AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
    std::vector<AppExecFwk::BundleInfo> bundleInfosForU0;
    std::map<int32_t, std::vector<AppExecFwk::BundleInfo>> bundleInfosMap;
    for (const auto &item: bundleInfos) {
        auto user = item.uid / BASE_USER_RANGE;
        if (user == U0_USER_ID) {
            bundleInfosForU0.push_back(item);
        } else if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(user)) {
            auto search = bundleInfosMap.find(user);
            if (search != bundleInfosMap.end()) {
                search->second.push_back(item);
            } else {
                std::vector<AppExecFwk::BundleInfo> bundleInfosForcallerUser;
                bundleInfosForcallerUser.push_back(item);
                bundleInfosMap.emplace(user, bundleInfosForcallerUser);
            }
        }
    }

    auto residentProcessMgr = DelayedSingleton<ResidentProcessManager>::GetInstance();
    CHECK_POINTER(residentProcessMgr);

    residentProcessMgr->StartResidentProcessWithMainElement(
        bundleInfosForU0, U0_USER_ID);
    if (!bundleInfosForU0.empty()) {
        residentProcessMgr->StartResidentProcess(bundleInfosForU0);
    }

    for (auto search = bundleInfosMap.rbegin(); search != bundleInfosMap.rend(); ++search) {
        residentProcessMgr->StartResidentProcessWithMainElement(search->second, search->first);
        if (!search->second.empty()) {
            residentProcessMgr->StartResidentProcess(search->second);
        }
    }
}

void AbilityManagerService::NotifyStartKeepAliveProcess(std::vector<AppExecFwk::BundleInfo> &bundleInfos,
    pid_t diedPid)
{
    if (!system::GetBoolParameter(PRODUCT_ENTERPRISE_FEATURE_SETTING_ENABLED, false)) {
        return;
    }

    auto userId =
        AbilityRuntime::UserController::GetInstance().GetForegroundUserId(ServerConstant::DEFAULT_DISPLAY_ID);
    std::map<int32_t, std::vector<AppExecFwk::BundleInfo>> bundleInfosMap;
    std::vector<AppExecFwk::BundleInfo> bundleInfosForU1;
    for (const auto &item: bundleInfos) {
        if (KeepAliveProcessManager::GetInstance().KeepAliveIsRestartAfterUpdate(item.uid)) {
            TAG_LOGI(AAFwkTag::APPMGR, "KeepAliveIsRestartAfterUpdate uid: %{public}d", item.uid);
            return;
        }
        auto user = item.uid / BASE_USER_RANGE;
        if (user == U1_USER_ID) {
            bundleInfosForU1.push_back(item);
        } else if (AbilityRuntime::UserController::GetInstance().IsForegroundUser(user)) {
            auto search = bundleInfosMap.find(user);
            if (search != bundleInfosMap.end()) {
                search->second.push_back(item);
            } else {
                std::vector<AppExecFwk::BundleInfo> bundleInfosForCurrentUser;
                bundleInfosForCurrentUser.push_back(item);
                bundleInfosMap.emplace(user, bundleInfosForCurrentUser);
            }
        } else {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "keepAlive not U1 or current user.");
            KeepAliveProcessManager::GetInstance().AddNeedRestartKeepAliveUid(item.uid);
        }
    }
    if (diedPid != AppExecFwk::INVALID_DIED_PID) {
        TimeSequenceKeepAliveRestart(userId, diedPid, bundleInfosMap, bundleInfosForU1);
        return;
    }

    for (auto search = bundleInfosMap.rbegin(); search != bundleInfosMap.rend(); ++search) {
        KeepAliveProcessManager::GetInstance().StartKeepAliveProcessWithMainElement(search->second, search->first);
    }

    if (bundleInfosForU1.size() != 0) {
        KeepAliveProcessManager::GetInstance().StartKeepAliveAppServiceExtension(bundleInfosForU1);
    }
}

void AbilityManagerService::TimeSequenceKeepAliveRestart(int32_t userId, pid_t pid,
    std::map<int32_t, std::vector<AppExecFwk::BundleInfo>> &bundleInfosMap,
    std::vector<AppExecFwk::BundleInfo> &bundleInfosForU1)
{
    CHECK_POINTER_LOG(taskHandler_, "taskHandler nullptr");
    auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
    CHECK_POINTER_LOG(uiAbilityManager, "uiAbilityManager nullptr");
    uiAbilityManager->HandleUIAbilityDiedByPid(pid);
    auto bundleInfosMapPtr =
        std::make_shared<std::map<int32_t, std::vector<AppExecFwk::BundleInfo>>>(bundleInfosMap);
    auto bundleInfosForU1Ptr = std::make_shared<std::vector<AppExecFwk::BundleInfo>>(bundleInfosForU1);
    auto keepAliveRestartTask = [bundleInfosMapPtr, bundleInfosForU1Ptr]() {
        CHECK_POINTER_LOG(bundleInfosMapPtr, "bundleInfosMapPtr nullptr");
        CHECK_POINTER_LOG(bundleInfosForU1Ptr, "bundleInfosForU1Ptr nullptr");
        auto bundleInfosMap = *bundleInfosMapPtr;
        auto bundleInfosForU1 = *bundleInfosForU1Ptr;
        for (auto search = bundleInfosMap.rbegin(); search != bundleInfosMap.rend(); ++search) {
            KeepAliveProcessManager::GetInstance().StartKeepAliveProcessWithMainElement(search->second, search->first);
        }

        if (bundleInfosForU1.size() != 0) {
            KeepAliveProcessManager::GetInstance().StartKeepAliveAppServiceExtension(bundleInfosForU1);
        }
    };
    taskHandler_->SubmitTask(keepAliveRestartTask, "TimeSequenceKeepAliveRestartTask");
}

void AbilityManagerService::NotifyAppPreCache(int32_t pid, int32_t userId)
{
    ForceTerminateServiceExtensionByPid(pid, userId);
}

void AbilityManagerService::OnAppRemoteDied(const std::vector<sptr<IRemoteObject>> &abilityTokens)
{
    std::shared_ptr<AbilityRecord> abilityRecord;
    for (auto &token : abilityTokens) {
        abilityRecord = Token::GetAbilityRecordByToken(token);
        if (abilityRecord == nullptr) {
            continue;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "app onRemoteDied, ability:%{public}s, app:%{public}s",
            abilityRecord->GetAbilityInfo().name.c_str(), abilityRecord->GetAbilityInfo().bundleName.c_str());
        abilityRecord->OnProcessDied();
    }
}

void AbilityManagerService::OnStartProcessFailed(const std::vector<sptr<IRemoteObject>> &abilityTokens)
{
    std::shared_ptr<AbilityRecord> abilityRecord;
    for (auto &token : abilityTokens) {
        abilityRecord = Token::GetAbilityRecordByToken(token);
        if (abilityRecord == nullptr) {
            continue;
        }
        TAG_LOGW(AAFwkTag::ABILITYMGR, "NotifyStartProcessFailed, ability:%{public}s, bundle:%{public}s",
            abilityRecord->GetAbilityInfo().name.c_str(), abilityRecord->GetAbilityInfo().bundleName.c_str());
        if (abilityRecord->GetAbilityInfo().type == AppExecFwk::AbilityType::EXTENSION) {
            auto connectManager = GetConnectManagerByToken(token, abilityRecord->GetAbilityInfo().extensionAbilityType);
            if (connectManager == nullptr) {
                TAG_LOGE(AAFwkTag::ABILITYMGR, "null connectManager");
                continue;
            }
            connectManager->OnLoadAbilityFailed(BaseExtensionRecord::TransferToExtensionRecordBase(abilityRecord));
        }
    }
}

void AbilityManagerService::OnCacheExitInfo(uint32_t accessTokenId, const AppExecFwk::RunningProcessInfo &exitInfo,
    const std::string &bundleName, const std::vector<std::string> &abilityNames,
    const std::vector<std::string> &uiExtensionNames)
{
    ExitCacheInfo cacheInfo = {};
    cacheInfo.exitInfo = exitInfo;
    cacheInfo.bundleName = bundleName;
    cacheInfo.abilityNames = abilityNames;
    cacheInfo.uiExtensionNames = uiExtensionNames;
    if (!ExitInfoDataManager::GetInstance().AddExitInfo(accessTokenId, cacheInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "AddExitInfo failed");
        return;
    }
    auto delayClearReason = [ accessTokenId ]() {
        if (!ExitInfoDataManager::GetInstance().DeleteExitInfo(accessTokenId)) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "DeleteExitInfo failed");
            return;
        }
    };
    ffrt::submit(std::move(delayClearReason), ffrt::task_attr()
        .delay(CLEAR_REASON_DELAY_TIME).name("delayClearReason")
        .timeout(AbilityRuntime::GlobalConstant::DEFAULT_FFRT_TASK_TIMEOUT));
}

void AbilityManagerService::RecordAppExitSignalReason(int32_t pid, int32_t uid, int32_t signal,
    std::string &bundleName)
{
    if(DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->RecordSignalReason(
        pid, uid, signal, bundleName) != 0) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "RecordSignalReason failed");
    }
}

int32_t AbilityManagerService::OpenFile(const Uri& uri, uint32_t flag)
{
    auto accessTokenId = IPCSkeleton::GetCallingTokenID();
    auto collaborator = GetCollaborator(CollaboratorType::RESERVE_TYPE);
    if (collaborator == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "collaborator getCollaborator null");
        return -1;
    }
    return collaborator->OpenFile(uri, flag, accessTokenId);
}

#ifdef SUPPORT_SCREEN
int AbilityManagerService::GetDialogSessionInfo(const std::string &dialogSessionId,
    sptr<DialogSessionInfo> &dialogSessionInfo)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    dialogSessionInfo = DialogSessionManager::GetInstance().GetDialogSessionInfo(dialogSessionId);
    if (dialogSessionInfo) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "success");
        return ERR_OK;
    }
    TAG_LOGD(AAFwkTag::ABILITYMGR, "fail");
    return INNER_ERR;
}

int AbilityManagerService::SendDialogResult(const Want &want, const std::string &dialogSessionId, bool isAllowed)
{
    CHECK_CALLER_IS_SYSTEM_APP;
    return DialogSessionManager::GetInstance().SendDialogResult(want, dialogSessionId, isAllowed);
}

int AbilityManagerService::CreateCloneSelectorDialog(AbilityRequest &request, int32_t userId,
    const std::string &replaceWantString)
{
    CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
    auto ret = implicitStartProcessor_->ImplicitStartAbility(request, userId, 0, replaceWantString, true);
    return AbilityErrorUtil::ConvertToOriginErrorCode(ret);
}
#endif // SUPPORT_SCREEN
void AbilityManagerService::RemoveSelectorIdentity(int32_t tokenId)
{
    CHECK_POINTER(implicitStartProcessor_);
    implicitStartProcessor_->RemoveIdentity(tokenId);
}

void AbilityManagerService::RemoveLauncherDeathRecipient(int32_t userId)
{
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    if (commonExtensionManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "commonExtensionManager null userId=%{public}d", userId);
        return;
    }
    commonExtensionManager->RemoveLauncherDeathRecipient();

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    if (uiExtensionAbilityManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uiExtensionAbilityManager null userId=%{public}d", userId);
        return;
    }
    uiExtensionAbilityManager->RemoveLauncherDeathRecipient();
}

int32_t AbilityManagerService::GenerateEmbeddableUIAbilityRequest(
    const Want &want, AbilityRequest &request, const sptr<IRemoteObject> &callerToken, int32_t userId)
{
    int32_t screenMode = want.GetIntParam(AAFwk::SCREEN_MODE_KEY, AAFwk::IDLE_SCREEN_MODE);
    int32_t result = ERR_OK;
    if (IsEmbeddableStart(screenMode)) {
        result = GenerateAbilityRequest(want, -1, request, callerToken, userId);
        request.abilityInfo.isModuleJson = true;
        request.abilityInfo.isStageBasedModel = true;
        request.abilityInfo.type = AppExecFwk::AbilityType::EXTENSION;
        request.abilityInfo.extensionAbilityType = AppExecFwk::ExtensionAbilityType::UI;
        struct timespec time = {0, 0};
        clock_gettime(CLOCK_MONOTONIC, &time);
        int64_t times = static_cast<int64_t>(time.tv_sec);
        request.abilityInfo.process = request.abilityInfo.bundleName + PROCESS_SUFFIX + std::to_string(times);
    } else {
        result = GenerateExtensionAbilityRequest(want, request, callerToken, userId);
    }
    return result;
}

int32_t AbilityManagerService::CheckDebugAssertPermission()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!system::GetBoolParameter(PRODUCT_ASSERT_FAULT_DIALOG_ENABLED, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "assert fault product dialog not enabled");
        return ERR_NOT_SUPPORTED_PRODUCT_TYPE;
    }
    if (!system::GetBoolParameter(DEVELOPER_MODE_STATE, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "developer mode false");
        return ERR_NOT_SUPPORTED_PRODUCT_TYPE;
    }

    auto bundleMgr = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bundleMgr, ERR_INVALID_VALUE);
    int32_t flags = static_cast<int32_t>(AppExecFwk::GetBundleInfoFlag::GET_BUNDLE_INFO_WITH_APPLICATION);
    AppExecFwk::BundleInfo bundleInfo;
    auto ret = bundleMgr->GetBundleInfoForSelf(flags, bundleInfo);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get bundle info failed");
        return ret;
    }
    if (!bundleInfo.applicationInfo.debug) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "non-debug version app");
        return ERR_INVALID_VALUE;
    }
    return ERR_OK;
}

bool AbilityManagerService::VerifySameAppOrAppIdentifierAllowListPermission(const AbilityRequest &abilityRequest)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    std::string targetBundleName = abilityRequest.abilityInfo.bundleName;
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t targetUid = abilityRequest.uid;
    if (callerUid == targetUid) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "same app");
        return true;
    }
    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, false);
    AppExecFwk::BundleInfo targetBundleInfo;
    std::string callerAppIdentifier = abilityRequest.want.GetStringParam(Want::PARAM_RESV_CALLER_APP_IDENTIFIER);
    if (callerAppIdentifier.empty()) {
        AppExecFwk::SignatureInfo signatureInfo;
        auto abilityRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
        if (abilityRecord == nullptr) {
            return false;
        }
        std::string callerBundleName = abilityRecord->GetApplicationInfo().bundleName;
        if (IN_PROCESS_CALL(bms->GetSignatureInfoByBundleName(callerBundleName,
            signatureInfo)) != ERR_OK) {
                TAG_LOGE(AAFwkTag::ABILITYMGR,
                    "bms GetSignatureInfoByBundleName error, bundleName: %{public}s", callerBundleName.c_str());
                return false;
            };
        callerAppIdentifier = signatureInfo.appIdentifier;
    }
    if (!IN_PROCESS_CALL(bms->GetBundleInfo(targetBundleName, AppExecFwk::BundleFlag::GET_BUNDLE_WITH_EXTENSION_INFO,
        targetBundleInfo, targetUid / BASE_USER_RANGE))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "bms GetBundleInfo error, BundleFlag: GET_BUNDLE_WITH_EXTENSION_INFO");
        return false;
    }
    for (const AppExecFwk::ExtensionAbilityInfo& info: targetBundleInfo.extensionInfos) {
        if (info.type == AppExecFwk::ExtensionAbilityType::APP_SERVICE &&
            info.name == abilityRequest.abilityInfo.name) {
            if (std::find(info.appIdentifierAllowList.begin(), info.appIdentifierAllowList.end(),
                callerAppIdentifier) != info.appIdentifierAllowList.end()) {
                return true;
            }
            return false;
        }
    }
    return false;
}

void AbilityManagerService::CloseAssertDialog(const std::string &assertSessionId, int32_t userId)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Close assert fault dialog begin.");
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    if (commonExtensionManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "commonExtensionManager null userId=%{public}d", userId);
        return;
    }
    commonExtensionManager->CloseAssertDialog(assertSessionId);

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    if (uiExtensionAbilityManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "uiExtensionAbilityManager null userId=%{public}d", userId);
        return;
    }
    uiExtensionAbilityManager->CloseAssertDialog(assertSessionId);
}

int32_t AbilityManagerService::SetResidentProcessEnabled(const std::string &bundleName, bool enable)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (!AAFwk::PermissionVerification::GetInstance()->IsSystemAppCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return ERR_NOT_SYSTEM_APP;
    }

    auto residentProcessManager = DelayedSingleton<ResidentProcessManager>::GetInstance();
    CHECK_POINTER_AND_RETURN(residentProcessManager, INNER_ERR);

    std::string callerName;
    int32_t uid = 0;
    auto callerPid = IPCSkeleton::GetCallingPid();
    DelayedSingleton<AppScheduler>::GetInstance()->GetBundleNameByPid(callerPid, callerName, uid);
    if (callerName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "obtain caller name failed");
        return INNER_ERR;
    }

    return residentProcessManager->SetResidentProcessEnabled(bundleName, callerName, enable);
}

int32_t AbilityManagerService::RequestAssertFaultDialog(
    const sptr<IRemoteObject> &callback, const AAFwk::WantParams &wantParams)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Request to display assert fault dialog begin.");
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto checkRet = CheckDebugAssertPermission();
    if (checkRet != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "check debug assert permission error");
        return checkRet;
    }
    sptr<IRemoteObject> remoteCallback = callback;
    if (remoteCallback == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "params remote callback null");
        return ERR_INVALID_VALUE;
    }
    auto debugDeal = ConnectInitAbilityDebugDeal();
    Want want;
#ifdef SUPPORT_SCREEN
    auto sysDialog = DelayedSingleton<SystemDialogScheduler>::GetInstance();
    if (sysDialog == nullptr || debugDeal == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sysDialog or debugDeal null");
        return ERR_INVALID_VALUE;
    }
    if (!sysDialog->GetAssertFaultDialogWant(want)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get assert fault dialog want failed");
        return ERR_INVALID_VALUE;
    }
#endif // SUPPORT_SCREEN
    uint64_t assertFaultSessionId = reinterpret_cast<uint64_t>(remoteCallback.GetRefPtr());
    want.SetParam(Want::PARAM_ASSERT_FAULT_SESSION_ID, std::to_string(assertFaultSessionId));
    want.SetParam(ASSERT_FAULT_DETAIL, wantParams.GetStringParam(ASSERT_FAULT_DETAIL));
    auto &connection = AbilityRuntime::ModalSystemAssertUIExtension::GetInstance();
    want.SetParam(UIEXTENSION_MODAL_TYPE, 1);
    if (!IN_PROCESS_CALL(connection.CreateModalUIExtension(want))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "create modal ui extension failed");
        return ERR_INVALID_VALUE;
    }
    auto callbackDeathMgr = DelayedSingleton<AbilityRuntime::AssertFaultCallbackDeathMgr>::GetInstance();
    if (callbackDeathMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get callback death manager instance null");
        return ERR_INVALID_VALUE;
    }
    int32_t userId = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    auto callbackTask = [weak = weak_from_this(), userId] (const std::string &assertSessionId) {
        auto abilityMgr = weak.lock();
        if (abilityMgr == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "ability manager instance null");
            return;
        }
        abilityMgr->CloseAssertDialog(assertSessionId, userId);
    };
    callbackDeathMgr->AddAssertFaultCallback(remoteCallback, callbackTask);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Request to display assert fault dialog end.");
    return ERR_OK;
}

int32_t AbilityManagerService::NotifyDebugAssertResult(uint64_t assertFaultSessionId, AAFwk::UserStatus userStatus)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!system::GetBoolParameter(PRODUCT_ASSERT_FAULT_DIALOG_ENABLED, false)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "assert fault dialog product not enabled");
        return ERR_NOT_SUPPORTED_PRODUCT_TYPE;
    }

    CHECK_CALLER_IS_SYSTEM_APP;
    auto permissionSA = PermissionVerification::GetInstance();
    if (permissionSA == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification instance null");
        return ERR_INVALID_VALUE;
    }
    if (!permissionSA->VerifyCallingPermission(PermissionConstants::PERMISSION_NOTIFY_DEBUG_ASSERT_RESULT)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_NOTIFY_DEBUG_ASSERT_RESULT);
        return ERR_PERMISSION_DENIED;
    }

    auto callbackDeathMgr = DelayedSingleton<AbilityRuntime::AssertFaultCallbackDeathMgr>::GetInstance();
    if (callbackDeathMgr == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get callback death manager instance null");
        return ERR_INVALID_VALUE;
    }
    callbackDeathMgr->CallAssertFaultCallback(assertFaultSessionId, userStatus);
    return ERR_OK;
}

int32_t AbilityManagerService::UpdateSessionInfoBySCB(std::list<SessionInfo> &sessionInfos, int32_t userId,
    std::vector<int32_t> &sessionIds)
{
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no sceneboard called, no allowed");
        return ERR_WRONG_INTERFACE_CALL;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "sceneboard being restored");
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->UpdateSessionInfoBySCB(sessionInfos, sessionIds);
}

bool AbilityManagerService::CheckSenderWantInfo(int32_t callerUid, const WantSenderInfo &wantSenderInfo)
{
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        auto bms = AbilityUtil::GetBundleManagerHelper();
        CHECK_POINTER_AND_RETURN(bms, false);

        std::string bundleName;
        if (IN_PROCESS_CALL(bms->GetNameForUid(callerUid, bundleName)) != ERR_OK) {
            TAG_LOGE(AAFwkTag::WANTAGENT, "get bundle name failed");
            return false;
        }
        if (wantSenderInfo.bundleName != bundleName) {
            TAG_LOGE(AAFwkTag::WANTAGENT, "wantSender bundleName check failed");
            return false;
        }
    }
    return true;
}

bool AbilityManagerService::CheckCallerIsDmsProcess()
{
    Security::AccessToken::NativeTokenInfo nativeTokenInfo;
    uint32_t accessToken = IPCSkeleton::GetCallingTokenID();
    auto tokenType = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(accessToken);
    int32_t result = Security::AccessToken::AccessTokenKit::GetNativeTokenInfo(accessToken, nativeTokenInfo);
    if (tokenType != Security::AccessToken::ATokenTypeEnum::TOKEN_NATIVE ||
        result != ERR_OK || nativeTokenInfo.processName != DMS_PROCESS_NAME) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not dms");
        return false;
    }
    return true;
}

void AbilityManagerService::WaitBootAnimationStart()
{
    char value[BOOTEVENT_BOOT_ANIMATION_READY_SIZE] = "";
    int32_t ret = GetParameter(BOOTEVENT_BOOT_ANIMATION_READY, "", value,
        BOOTEVENT_BOOT_ANIMATION_READY_SIZE);
    if (ret > 0 && !std::strcmp(value, "false")) {
        // Get new param success and new param is not ready, wait the new param.
        WaitParameter(BOOTEVENT_BOOT_ANIMATION_READY, "true",
            AmsConfigurationParameter::GetInstance().GetBootAnimationTimeoutTime());
    } else if (ret <= 0 || !std::strcmp(value, "")) {
        // Get new param failed or new param is not set, wait the old param.
        WaitParameter(BOOTEVENT_BOOT_ANIMATION_STARTED, "true",
            AmsConfigurationParameter::GetInstance().GetBootAnimationTimeoutTime());
    }
    // other, the animation is ready, not wait.
}

int32_t AbilityManagerService::GetUIExtensionRootHostInfo(const sptr<IRemoteObject> token,
    UIExtensionHostInfo &hostInfo, int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Get ui extension host info.");
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() && !IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_PERMISSION_DENIED;
    }

    auto callerRecord = GetUIExtensionRootCaller(token, userId);
    if (callerRecord == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "get root host info failed");
        return ERR_INVALID_VALUE;
    }

    hostInfo.elementName_ = callerRecord->GetElementName();
    auto sessionInfo = callerRecord->GetSessionInfo();
    if (sessionInfo != nullptr) {
        hostInfo.sessionName = sessionInfo->sessionName;
    }
    TAG_LOGD(AAFwkTag::UI_EXT, "uri: %{public}s, sessionName: %{public}s.",
             hostInfo.elementName_.GetURI().c_str(), hostInfo.sessionName.c_str());
    return ERR_OK;
}

std::shared_ptr<AbilityRecord> AbilityManagerService::GetUIExtensionRootCaller(const sptr<IRemoteObject> token,
    int32_t userId)
{
    auto validUserId = GetValidUserId(userId);
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);    
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "manager null, userId:%{public}d", validUserId);
        return nullptr;
    }

    auto callerRecord = connectManager->GetUIExtensionRootHostInfo(token);
    if (callerRecord == nullptr && validUserId != U0_USER_ID) {
        auto connectManager = GetUIExtensionAbilityManagerByUserId(U0_USER_ID);
        if (connectManager == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "manager null, userId: %{public}d", U0_USER_ID);
            return nullptr;
        }
        callerRecord = connectManager->GetUIExtensionRootHostInfo(token);
    }

    return callerRecord;
}

int32_t AbilityManagerService::GetUIExtensionSessionInfo(const sptr<IRemoteObject> token,
    UIExtensionSessionInfo &uiExtensionSessionInfo, int32_t userId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "Get ui extension host info.");
    CHECK_POINTER_AND_RETURN(token, ERR_INVALID_VALUE);

    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall() && !IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_PERMISSION_DENIED;
    }

    auto validUserId = GetValidUserId(userId);
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "manager null, userId:%{public}d", validUserId);
        return ERR_INVALID_VALUE;
    }

    auto ret = connectManager->GetUIExtensionSessionInfo(token, uiExtensionSessionInfo);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get ui extension session info failed");
        return ret;
    }

    return ERR_OK;
}

int32_t AbilityManagerService::RestartApp(const AAFwk::Want &want, bool isAppRecovery)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "RestartApp, isAppRecovery: %{public}d", isAppRecovery);
    auto callerPid = IPCSkeleton::GetCallingPid();
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(callerPid, processInfo);
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t userId = callerUid / BASE_USER_RANGE;
    auto result = CheckRestartAppWant(want, processInfo.appCloneIndex, userId);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkRestartAppWant error");
        return result;
    }
    if (!processInfo.isFocused && !processInfo.isAbilityForegrounding) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "restartApp, is not foreground");
        return AAFwk::NOT_TOP_ABILITY;
    }

    RestartAppKeyType key(processInfo.instanceKey, callerUid);
    int64_t now = time(nullptr);
    if (!isAppRecovery && RestartAppManager::GetInstance().IsRestartAppFrequent(key, now)) {
        return AAFwk::ERR_RESTART_APP_FREQUENT;
    }

    SignRestartAppFlagParam param =
        { userId, callerUid, processInfo.instanceKey, processInfo.appMode, isAppRecovery, false };
    result = SignRestartAppFlag(param);
    if (!isAppRecovery && result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "signRestartAppFlag error");
        return result;
    }

    (const_cast<Want &>(want)).SetParam(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY, processInfo.appCloneIndex);
    (const_cast<Want &>(want)).SetParam(AAFwk::Want::APP_INSTANCE_KEY, processInfo.instanceKey);
    (const_cast<Want &>(want)).RemoveParam(Want::CREATE_APP_INSTANCE_KEY);
    StartAbilityWrapParam startAbilityWrapParam = {
        .want = want,
        .isForegroundToRestartApp = true,
    };
    result = StartAbilityWrap(startAbilityWrapParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startAbility error");
        return result;
    }
    if (!isAppRecovery) {
        RestartAppManager::GetInstance().AddRestartAppHistory(key, now);
    }
    return result;
}

bool AbilityManagerService::IsRestartAppLimit()
{
    auto callerPid = IPCSkeleton::GetCallingPid();
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(callerPid, processInfo);
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    RestartAppKeyType key(processInfo.instanceKey, callerUid);
    int64_t now = time(nullptr);
    return RestartAppManager::GetInstance().IsRestartAppFrequent(key, now);
}

int32_t AbilityManagerService::CheckRestartAppWant(const AAFwk::Want &want, int32_t appIndex, int32_t userId)
{
    std::string bundleName = want.GetElement().GetBundleName();
    if (!CheckCallingTokenId(bundleName, userId, appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no itself called, no allowed");
        return AAFwk::ERR_RESTART_APP_INCORRECT_ABILITY;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bms, GET_ABILITY_SERVICE_FAILED);
    auto abilityInfoFlag = AbilityRuntime::StartupUtil::BuildAbilityInfoFlag();

    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "bundleName: %{public}s, abilityName: %{public}s, appIndex: %{public}d, userId: %{public}d",
        want.GetElement().GetBundleName().c_str(), want.GetElement().GetAbilityName().c_str(), appIndex, userId);
    AppExecFwk::AbilityInfo abilityInfo;
    auto queryResult = IN_PROCESS_CALL(
        bms->QueryCloneAbilityInfo(want.GetElement(), abilityInfoFlag, appIndex, abilityInfo, userId));
    if (queryResult != ERR_OK || abilityInfo.name.empty() || abilityInfo.bundleName.empty() ||
        abilityInfo.type != AbilityType::PAGE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability invalid or not UIAbility");
        return AAFwk::ERR_RESTART_APP_INCORRECT_ABILITY;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::SignRestartAppFlag(const SignRestartAppFlagParam &param)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "AppMgrUtil::GetAppMgr failed");
        return ERR_INVALID_VALUE;
    }
    auto ret = IN_PROCESS_CALL(appMgr->SignRestartAppFlag(param.uid, param.instanceKey));
    if (!param.isAppRecovery && ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appMgr signRestartAppFlag error");
        return ret;
    }

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(param.userId);
    CHECK_POINTER_AND_RETURN(commonExtensionManager, ERR_INVALID_VALUE);
    commonExtensionManager->SignRestartAppFlag(param.uid, param.instanceKey);

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(param.userId);
    CHECK_POINTER_AND_RETURN(uiExtensionAbilityManager, ERR_INVALID_VALUE);
    uiExtensionAbilityManager->SignRestartAppFlag(param.uid, param.instanceKey);

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUserId(param.userId);
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        uiAbilityManager->SignRestartAppFlag(param.uid, param.instanceKey, param.isAppRecovery);
    } else {
        auto missionListManager = GetMissionListManagerByUserId(param.userId);
        if (missionListManager == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "missionListManager null userId:%{public}d", param.userId);
            return ERR_INVALID_VALUE;
        }
        missionListManager->SignRestartAppFlag(param.uid, param.instanceKey);
    }

    if (param.type == AppExecFwk::MultiAppModeType::MULTI_INSTANCE) {
        return appMgr->KillAppSelfWithInstanceKey(param.instanceKey, false, "RestartInstance");
    }
    if (param.isAtomicService) {
        return DelayedSingleton<AppExecFwk::AppMgrClient>::GetInstance()->KillApplicationSelf(false,
            "RestartSelfAtomicService");
    }
    return DelayedSingleton<AppExecFwk::AppMgrClient>::GetInstance()->KillApplicationSelf(false, "RestartApp");
}

int32_t AbilityManagerService::SignRestartProcess(int32_t pid, int32_t userId)
{
    auto appMgr = AppMgrUtil::GetAppMgr();
    if (appMgr == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "AppMgrUtil::GetAppMgr failed");
        return ERR_INVALID_VALUE;
    }
    auto ret = IN_PROCESS_CALL(appMgr->SignRestartProcess(pid));
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "appMgr SignRestartProcess error");
        return ret;
    }

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(commonExtensionManager, ERR_INVALID_VALUE);
    commonExtensionManager->SignRestartProcess(pid);

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(uiExtensionAbilityManager, ERR_INVALID_VALUE);
    uiExtensionAbilityManager->SignRestartProcess(pid);

    auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    uiAbilityManager->SignRestartProcess(pid);

    return IN_PROCESS_CALL(appMgr->KillProcessByPidForExit(pid, "RestartUIAbility"));
}

bool AbilityManagerService::IsEmbeddedOpenAllowed(sptr<IRemoteObject> callerToken, const std::string &appId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!AppUtils::GetInstance().IsLaunchEmbededUIAbility()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "device type not allowd");
        return false;
    }
    auto accessTokenId = IPCSkeleton::GetCallingTokenID();
    auto type = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(accessTokenId);
    if (type != Security::AccessToken::TypeATokenTypeEnum::TOKEN_HAP) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not hap");
        return false;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    auto callerAbility = uiAbilityManager->GetAbilityRecordByToken(callerToken);
    if (callerAbility == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller invalid");
        return false;
    }
    if (callerAbility->GetApplicationInfo().accessTokenId != accessTokenId) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "callerToken don't belong caller");
        return false;
    }
    if (!callerAbility->IsForeground() && !callerAbility->GetAbilityForegroundingFlag()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not foreground");
        return false;
    }
    CHECK_POINTER_AND_RETURN(freeInstallManager_, false);
    std::string bundleName = ATOMIC_SERVICE_PREFIX + appId;
    Want want;
    want.SetBundle(bundleName);
    want.SetParam("send_to_erms_embedded", 1);
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(want, callerToken);
    int32_t callerUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    int32_t ret = freeInstallManager_->StartFreeInstall(want, callerUserId, 0, callerToken);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "target not allowed free install");
        return false;
    }
    want.SetParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME, callerAbility->GetElementName().GetBundleName());
    auto erms = std::make_shared<EcologicalRuleInterceptor>();
    return erms->DoProcess(want, callerUserId);
}

int32_t AbilityManagerService::AddQueryERMSObserver(sptr<IRemoteObject> callerToken,
    sptr<AbilityRuntime::IQueryERMSObserver> observer)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (callerToken == nullptr || !JudgeSelfCalled(Token::GetAbilityRecordByToken(callerToken))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller invalid");
        return ERR_PERMISSION_DENIED;
    }
    return QueryERMSManager::GetInstance().AddQueryERMSObserver(callerToken, observer);
}

int32_t AbilityManagerService::QueryAtomicServiceStartupRule(sptr<IRemoteObject> callerToken,
    const std::string &appId, const std::string &startTime, AtomicServiceStartupRule &rule)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    CHECK_TRUE_RETURN_RET(!AppUtils::GetInstance().IsLaunchEmbededUIAbility(),
        ERR_CAPABILITY_NOT_SUPPORT, "device type not allowd");
    auto accessTokenId = IPCSkeleton::GetCallingTokenID();
    auto type = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(accessTokenId);
    CHECK_TRUE_RETURN_RET(type != Security::AccessToken::TypeATokenTypeEnum::TOKEN_HAP, INNER_ERR, "caller not hap");
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, INNER_ERR);
    auto callerAbility = uiAbilityManager->GetAbilityRecordByToken(callerToken);
    CHECK_POINTER_AND_RETURN(callerAbility, INNER_ERR);
    CHECK_TRUE_RETURN_RET(callerAbility->GetApplicationInfo().accessTokenId != accessTokenId,
        INNER_ERR, "callerToken don't belong caller");
    CHECK_TRUE_RETURN_RET(!callerAbility->IsForeground() && !callerAbility->GetAbilityForegroundingFlag(),
        INNER_ERR, "caller not foreground");

    Want want;
    want.SetBundle(ATOMIC_SERVICE_PREFIX + appId);
    want.SetParam("send_to_erms_embedded", 1);
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(want, callerToken);
    auto userId = callerAbility->GetOwnerMissionUserId();
    int32_t ret = freeInstallManager_->StartFreeInstall(want, userId, 0, callerToken);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "free install failed:%{public}d", ret);
        rule.isOpenAllowed = false;
        rule.isEmbeddedAllowed = false;
        return ERR_OK;
    }

    want.SetParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME, callerAbility->GetElementName().GetBundleName());
    auto erms = std::make_shared<EcologicalRuleInterceptor>();
    sptr<Want> replaceWant = nullptr;
    ret = erms->QueryAtomicServiceStartupRule(want, callerToken, userId, rule, replaceWant);
    if (ret == ERR_OK) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "QueryAtomicServiceStartupRule succeeded");
        return ERR_OK;
    }
    if (ret != ERR_ECOLOGICAL_CONTROL_STATUS) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "QueryAtomicServiceStartupRule failed:%{public}d", ret);
        if (ret == ERR_CAPABILITY_NOT_SUPPORT) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "not supported");
            return ret;
        }
        return INNER_ERR;
    }
    AbilityRequest abilityRequest;
    ret = GenerateAbilityRequest(want, -1, abilityRequest, callerToken, userId);
    CHECK_TRUE_RETURN_RET(ret != ERR_OK, INNER_ERR, "GenerateAbilityRequest failed");

    abilityRequest.isQueryERMS = true;
    abilityRequest.appId = appId;
    abilityRequest.startTime = startTime;
    abilityRequest.isEmbeddedAllowed = rule.isEmbeddedAllowed;
    ret = DialogSessionManager::GetInstance().HandleErmsResult(abilityRequest, userId, *replaceWant);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "HandleErmsResult: ret=%{public}d", ret);
    CHECK_TRUE_RETURN_RET(ret != ERR_OK, INNER_ERR, "HandleErmsResult failed");
    return ERR_ECOLOGICAL_CONTROL_STATUS;
}

bool AbilityManagerService::CheckProcessIsBackground(int32_t pid, AbilityState currentState)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "pid:%{public}d, currentState:%{public}d", pid, currentState);
    std::lock_guard<ffrt::mutex> myLockGuard(windowVisibleListLock_);
    if (currentState == AAFwk::AbilityState::BACKGROUND &&
        windowVisibleList_.find(pid) != windowVisibleList_.end()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process window is occluded");
        return false;
    }

    if (currentState != AAFwk::AbilityState::BACKGROUND) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process is not on background Pass");
        return false;
    }
    return true;
}

void AbilityManagerService::InitWindowVisibilityChangedListener()
{
    if (windowVisibilityChangedListener_ != nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "visibility already initiate");
        return;
    }

    windowVisibilityChangedListener_ =
        new (std::nothrow) WindowVisibilityChangedListener(weak_from_this(), taskHandler_);
    if (windowVisibilityChangedListener_ == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "window visibility changed listener null");
        return;
    }

    Rosen::WindowManager::GetInstance().RegisterVisibilityChangedListener(windowVisibilityChangedListener_);
}

void AbilityManagerService::FreeWindowVisibilityChangedListener()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (windowVisibilityChangedListener_ == nullptr) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "visibility listener already free");
        return;
    }
    Rosen::WindowManager::GetInstance().UnregisterVisibilityChangedListener(windowVisibilityChangedListener_);
    windowVisibilityChangedListener_ = nullptr;
}

void AbilityManagerService::HandleWindowVisibilityChanged(
    const std::vector<sptr<OHOS::Rosen::WindowVisibilityInfo>> &windowVisibilityInfos)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (windowVisibilityInfos.empty()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "window visibility info empty");
        return;
    }
    std::lock_guard<ffrt::mutex> myLockGuard(windowVisibleListLock_);
    for (const auto &info : windowVisibilityInfos) {
        if (info == nullptr) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "null info");
            continue;
        }
        int uid = 0;
        std::string bundleName;
        if (info->windowType_ == Rosen::WindowType::WINDOW_TYPE_DESKTOP &&
            info->visibilityState_ == Rosen::WINDOW_VISIBILITY_STATE_NO_OCCLUSION) {
            TAG_LOGD(AAFwkTag::ABILITYMGR, "desktop is visible clear windowVisibleList_");
            windowVisibleList_.clear();
            continue;
        }
        DelayedSingleton<AppScheduler>::GetInstance()->GetBundleNameByPid(info->pid_, bundleName, uid);
        if (info->visibilityState_ == Rosen::WINDOW_VISIBILITY_STATE_NO_OCCLUSION &&
            bundleName != SCENEBOARD_BUNDLE_NAME) {
            windowVisibleList_.insert(info->pid_);
        }
    }
}

bool AbilityManagerService::ShouldPreventStartAbility(const AbilityRequest &abilityRequest)
{
    std::shared_ptr<AbilityRecord> abilityRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    if (abilityRecord == nullptr) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "No matched token pass");
        return false;
    }
    auto abilityInfo = abilityRequest.abilityInfo;
    auto callerAbilityInfo = abilityRecord->GetAbilityInfo();
    PrintStartAbilityInfo(callerAbilityInfo, abilityInfo);
    if (abilityRecord->GetApplicationInfo().apiTargetVersion % API_VERSION_MOD < API12) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "API version %{public}d pass",
            abilityRecord->GetApplicationInfo().apiTargetVersion % API_VERSION_MOD);
        return false;
    }
    bool continuousFlag = IsBackgroundTaskUid(IPCSkeleton::GetCallingUid());
    if(!IN_PROCESS_CALL(DelayedSingleton<AppScheduler>::GetInstance()->
        IsProcessContainsOnlyUIAbility(abilityRecord->GetPid()))) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process has other extension except UIAbility, pass");
        return false;
    }
    if (abilityInfo.extensionAbilityType != AppExecFwk::ExtensionAbilityType::DATASHARE &&
        abilityInfo.extensionAbilityType != AppExecFwk::ExtensionAbilityType::SERVICE) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process did not call service or datashare extension Pass");
        return false;
    }
    if (abilityInfo.applicationInfo.uid == IPCSkeleton::GetCallingUid()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process is in same bundle Pass");
        return false;
    }
    if (callerAbilityInfo.type != AppExecFwk::AbilityType::PAGE) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Is not UI Ability Pass");
        return false;
    }
    if (DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckIntentIsExemption(
        abilityRecord->GetUid())) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Is Exemption Pass");
        return false;
    }
    if (!CheckProcessIsBackground(abilityRecord->GetPid(), abilityRecord->GetAbilityState())) {
        return false;
    }
    if (continuousFlag) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process has continuous task Pass");
        return false;
    }
    if (IsInWhiteList(callerAbilityInfo.bundleName, abilityInfo.bundleName, abilityInfo.name)) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "Process is in white list Pass");
        return false;
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "without start serviceExtension %{public}s/%{public}s permission",
        abilityRecord->GetElementName().GetBundleName().c_str(),
        abilityRecord->GetElementName().GetAbilityName().c_str());
    ReportPreventStartAbilityResult(callerAbilityInfo, abilityInfo);
    return true;
}

void AbilityManagerService::PrintStartAbilityInfo(AppExecFwk::AbilityInfo callerInfo, AppExecFwk::AbilityInfo calledInfo)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "calledAbilityInfo toString: "
        "calledUid is: %{public}d, "
        "name is: %{public}s, "
        "bundleName is: %{public}s, "
        "type is: %{public}d, "
        "extensionAbilityType is: %{public}d, "
        "moduleName is: %{public}s, "
        "applicationName is: %{public}s",
        calledInfo.applicationInfo.uid,
        calledInfo.name.c_str(),
        calledInfo.bundleName.c_str(),
        static_cast<int32_t>(calledInfo.type),
        static_cast<int32_t>(calledInfo.extensionAbilityType),
        calledInfo.moduleName.c_str(),
        calledInfo.applicationName.c_str());


    TAG_LOGD(AAFwkTag::ABILITYMGR, "callerAbilityInfo toString: "
        "callerUid is: %{public}d, "
        "callerPid is: %{public}d, "
        "name is: %{public}s, "
        "bundleName is: %{public}s, "
        "type is: %{public}d, "
        "extensionAbilityType is: %{public}d, "
        "moduleName is: %{public}s, "
        "applicationName is: %{public}s",
        IPCSkeleton::GetCallingUid(),
        IPCSkeleton::GetCallingPid(),
        callerInfo.name.c_str(),
        callerInfo.bundleName.c_str(),
        static_cast<int32_t>(callerInfo.type),
        static_cast<int32_t>(callerInfo.extensionAbilityType),
        callerInfo.moduleName.c_str(),
        callerInfo.applicationName.c_str());
}

void AbilityManagerService::ReportPreventStartAbilityResult(const AppExecFwk::AbilityInfo &callerAbilityInfo,
    const AppExecFwk::AbilityInfo &abilityInfo)
{
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t callerPid = IPCSkeleton::GetCallingPid();
    int32_t extensionAbilityType = static_cast<int32_t>(abilityInfo.extensionAbilityType);
    TAG_LOGD(AAFwkTag::ABILITYMGR,
        "Prevent start ability debug log CALLER_BUNDLE_NAME %{public}s CALLEE_BUNDLE_NAME"
        "%{public}s ABILITY_NAME %{public}s",
        callerAbilityInfo.bundleName.c_str(), abilityInfo.name.c_str(), abilityInfo.name.c_str());
    auto hisyseventReport = std::make_shared<HisyseventReport>(8);
    hisyseventReport->InsertParam("CALLER_UID", callerUid);
    hisyseventReport->InsertParam("CALLER_PID", callerPid);
    hisyseventReport->InsertParam("CALLER_PROCESS_NAME", callerAbilityInfo.process);
    hisyseventReport->InsertParam("CALLER_BUNDLE_NAME", callerAbilityInfo.bundleName);
    hisyseventReport->InsertParam("CALLEE_BUNDLE_NAME", abilityInfo.bundleName);
    hisyseventReport->InsertParam("CALLEE_PROCESS_NAME", abilityInfo.process);
    hisyseventReport->InsertParam("EXTENSION_ABILITY_TYPE", extensionAbilityType);
    hisyseventReport->InsertParam("ABILITY_NAME", abilityInfo.name);
    hisyseventReport->Report("AAFWK", "PREVENT_START_ABILITY", HISYSEVENT_BEHAVIOR);
}

bool AbilityManagerService::IsInWhiteList(const std::string &callerBundleName, const std::string &calleeBundleName,
    const std::string &calleeAbilityName)
{
    std::lock_guard<std::mutex> locker(whiteListMutex_);
    std::map<std::string, std::list<std::string>>::iterator iter = whiteListMap_.find(callerBundleName);
    std::string uri = calleeBundleName + "/" + calleeAbilityName;
    if (iter != whiteListMap_.end()) {
        if (std::find(std::begin(iter->second), std::end(iter->second), uri) != std::end(iter->second)) {
            return true;
        }
    }
    std::list<std::string>::iterator it = std::find(exportWhiteList_.begin(), exportWhiteList_.end(), uri);
    if (it != exportWhiteList_.end()) {
        return true;
    }
    return false;
}

bool AbilityManagerService::ParseJsonFromBoot(const std::string &relativePath)
{
    nlohmann::json jsonObj;
    std::string absolutePath = GetConfigFileAbsolutePath(relativePath);
    if (ParseJsonValueFromFile(jsonObj, absolutePath) != ERR_OK) {
        return false;
    }
    std::lock_guard<std::mutex> locker(whiteListMutex_);
    nlohmann::json whiteListJsonList = jsonObj[WHITE_LIST];
    for (const auto& [key, value] : whiteListJsonList.items()) {
        if (!value.is_array()) {
            continue;
        }
        whiteListMap_.emplace(key, std::list<std::string>());
        for (const auto& it : value) {
            if (it.is_string()) {
                whiteListMap_[key].push_back(it);
            }
        }
    }
    if (!jsonObj.contains("exposed_white_list")) {
        return false;
    }
    nlohmann::json exportWhiteJsonList = jsonObj["exposed_white_list"];
    for (const auto& it : exportWhiteJsonList) {
        if (it.is_string()) {
            exportWhiteList_.push_back(it);
        }
    }
    return true;
}

std::string AbilityManagerService::GetConfigFileAbsolutePath(const std::string &relativePath)
{
    if (relativePath.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "relativePath empty");
        return "";
    }
    char buf[PATH_MAX];
    char *tmpPath = GetOneCfgFile(relativePath.c_str(), buf, PATH_MAX);
    char absolutePath[PATH_MAX] = {0};
    if (!tmpPath || strlen(tmpPath) > PATH_MAX || !realpath(tmpPath, absolutePath)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get file fail");
        return "";
    }
    return std::string(absolutePath);
}

int32_t AbilityManagerService::ParseJsonValueFromFile(nlohmann::json &value, const std::string &filePath)
{
    std::ifstream fin;
    std::string realPath;
    if (!ConvertFullPath(filePath, realPath)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "get real path failed");
        return ERR_INVALID_VALUE;
    }
    fin.open(realPath, std::ios::in);
    if (!fin.is_open()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "can't open file %{private}s", realPath.c_str());
        return ERR_INVALID_VALUE;
    }
    char buffer[MAX_BUFFER];
    std::ostringstream os;
    while (fin.getline(buffer, MAX_BUFFER)) {
        os << buffer;
    }
    const std::string data = os.str();
    value = nlohmann::json::parse(data, nullptr, false);
    if (value.is_discarded()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed due data discarded");
        return ERR_INVALID_VALUE;
    }
    return ERR_OK;
}

bool AbilityManagerService::ConvertFullPath(const std::string& partialPath, std::string& fullPath)
{
    if (partialPath.empty() || partialPath.length() >= PATH_MAX) {
        return false;
    }
    char tmpPath[PATH_MAX] = {0};
    if (realpath(partialPath.c_str(), tmpPath) == nullptr) {
        return false;
    }
    fullPath = tmpPath;
    return true;
}

int32_t AbilityManagerService::StartShortcut(const Want &want, const StartOptions &startOptions)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!PermissionVerification::GetInstance()->IsSystemAppCall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "non-system app calling system api");
        return ERR_NOT_SYSTEM_APP;
    }
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_START_SHORTCUT)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_START_SHORTCUT);
        return ERR_PERMISSION_DENIED;
    }
    AbilityUtil::RemoveShowModeKey(const_cast<Want &>(want));
    return StartUIAbilityForOptionWrap(want, startOptions, nullptr, false, DEFAULT_INVAL_VALUE, DEFAULT_INVAL_VALUE,
        0, false, true);
}

int32_t AbilityManagerService::GetAbilityStateByPersistentId(int32_t persistentId, bool &state)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!CheckCallerIsDmsProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "getAbilityStateByPersistentId, caller not dms");
        return ERR_PERMISSION_DENIED;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
        CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
        return uiAbilityManager->GetAbilityStateByPersistentId(persistentId, state);
    }
    TAG_LOGE(AAFwkTag::ABILITYMGR, "getAbilityStateByPersistentId, mission without persistent id");
    return INNER_ERR;
}

int32_t AbilityManagerService::TransferAbilityResultForExtension(const sptr<IRemoteObject> &callerToken,
    int32_t resultCode, const Want &want)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    if (!JudgeSelfCalled(abilityRecord)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller mismatch");
        return ERR_INVALID_VALUE;
    }
    auto type = abilityRecord->GetAbilityInfo().type;
    if (type != AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type not uiextension");
        return ERR_INVALID_VALUE;
    }
    // save result to caller AbilityRecord.
    (const_cast<Want &>(want)).RemoveParam(Want::PARAM_RESV_CALLER_TOKEN);
    abilityRecord->SaveResultToCallers(resultCode, &want);
    abilityRecord->SendResultToCallers();
    return ERR_OK;
}

void AbilityManagerService::NotifyFrozenProcessByRSS(const std::vector<int32_t> &pidList, int32_t uid)
{
    if (!PermissionVerification::GetInstance()->CheckSpecificSystemAbilityAccessPermission(RSS_PROCESS_NAME)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "caller not RSS");
        return;
    }
    auto userId = uid / BASE_USER_RANGE;

    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER_LOG(commonExtensionManager, "can't find user connect manager");
    commonExtensionManager->HandleProcessFrozen(pidList, uid);

    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER_LOG(uiExtensionAbilityManager, "can't find user connect manager");
    uiExtensionAbilityManager->HandleProcessFrozen(pidList, uid);
}

void AbilityManagerService::HandleRestartResidentProcessDependedOnWeb()
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "call");
    auto appMgr = AppMgrUtil::GetAppMgr();
    CHECK_POINTER_LOG(appMgr, "get appMgr fail");
    appMgr->RestartResidentProcessDependedOnWeb();
}

int32_t AbilityManagerService::PreStartMission(const std::string& bundleName, const std::string& moduleName,
    const std::string& abilityName, const std::string& startTime)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "PreStartMission");
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyPreStartAtomicServicePermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "calling user not ag");
        return ERR_PERMISSION_DENIED;
    }

    if (!freeInstallManager_) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "freeInstallManager_ null");
        return ERR_INVALID_VALUE;
    }

    FreeInstallInfo taskInfo;
    if (!freeInstallManager_->GetFreeInstallTaskInfo(bundleName, abilityName, startTime, taskInfo)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR,
            "failed find free install task info:bundleName=%{public}s,abilityName=%{public}s,startTime=%{public}s",
            bundleName.c_str(), abilityName.c_str(), startTime.c_str());
        return ERR_FREE_INSTALL_TASK_NOT_EXIST;
    }

    if (taskInfo.isFreeInstallFinished) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install finished");
        if (!taskInfo.isInstalled) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "free install task failed,resultCode=%{public}d",
                taskInfo.resultCode);
        } else {
            TAG_LOGI(AAFwkTag::ABILITYMGR, "free install succeeded");
        }
        // if free install is already finished then either the window is opened (on success)
        // or the user is informed of the error (on failure).
        return taskInfo.resultCode;
    }

    return PreStartInner(taskInfo);
}

int32_t AbilityManagerService::PreStartInner(const FreeInstallInfo& taskInfo)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");

    const Want& want = taskInfo.want;
    sptr<IRemoteObject> callerToken = taskInfo.callerToken;

    EventInfo eventInfo = BuildEventInfo(want, taskInfo.userId);
    SendAbilityEvent(EventName::START_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "PreStartInner StartAbilityError:%{public}d", ERR_INVALID_CALLER);
        AbilityEventUtil::SendStartAbilityErrorEvent(eventInfo, ERR_INVALID_CALLER,
            "PreStartInner StartAbilityError");
        return ERR_INVALID_CALLER;
    }

    int32_t oriValidUserId = GetValidUserId(taskInfo.userId);

    int32_t appIndex = 0;
    StartAbilityInfoWrap threadLocalInfo(want, oriValidUserId,
        StartAbilityUtils::GetAppIndex(want, callerToken, appIndex), callerToken);

    AbilityRequest abilityRequest = {
        .requestCode = taskInfo.requestCode,
        .callerToken = callerToken,
        .startSetting = nullptr,
        .want = want
    };

    TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
    UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);

    // sceneboard
    abilityRequest.userId = oriValidUserId;
    abilityRequest.want.SetParam(ServerConstant::IS_CALL_BY_SCB, false);
    std::string sessionId = std::to_string(std::chrono::duration_cast<std::chrono::milliseconds>(
        std::chrono::system_clock::now().time_since_epoch()).count());
    abilityRequest.want.SetParam(KEY_SESSION_ID, sessionId);
    auto uiAbilityManager = GetUIAbilityManagerByUserId(oriValidUserId);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    sptr<SessionInfo> sessionInfo = nullptr;
    auto errCode = uiAbilityManager->NotifySCBToPreStartUIAbility(abilityRequest, sessionInfo);
    if (errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed notify sceneboard pre-start uiability");
        return errCode;
    }
    CHECK_POINTER_AND_RETURN(freeInstallManager_, ERR_INVALID_VALUE);
    freeInstallManager_->SetFreeInstallTaskSessionId(taskInfo.want.GetElement().GetBundleName(),
        taskInfo.want.GetElement().GetAbilityName(),
        taskInfo.want.GetStringParam(Want::PARAM_RESV_START_TIME), sessionId);

    freeInstallManager_->SetPreStartMissionCallStatus(taskInfo.want.GetElement().GetBundleName(),
        taskInfo.want.GetElement().GetAbilityName(),
        taskInfo.want.GetStringParam(Want::PARAM_RESV_START_TIME),
        true);
    return ERR_OK;
}

int32_t AbilityManagerService::StartUIAbilityByPreInstall(const FreeInstallInfo &taskInfo)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call StartUIAbilityByPreInstall");
    if (!taskInfo.isFreeInstallFinished || !taskInfo.isInstalled) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "free install not finished or failed");
        return ERR_INVALID_VALUE;
    }
    if (!taskInfo.isStartUIAbilityBySCBCalled) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "free install finished, startUIAbilityBySCB not called");
        return ERR_OK;
    }

    const auto& want = taskInfo.want;
    auto sessionId = want.GetStringParam(KEY_SESSION_ID);
    if (sessionId.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "session id empty");
        return ERR_INVALID_VALUE;
    }
    auto bundleName = want.GetElement().GetBundleName();
    auto abilityName = want.GetElement().GetAbilityName();
    auto startTime = want.GetStringParam(Want::PARAM_RESV_START_TIME);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call"
        "sessionId=%{public}s,bundleName=%{public}s,abilityName=%{public}s,startTime=%{public}s",
        sessionId.c_str(), bundleName.c_str(), abilityName.c_str(), startTime.c_str());
    sptr<SessionInfo> sessionInfo = nullptr;
    {
        std::lock_guard<ffrt::mutex> guard(preStartSessionMapLock_);
        auto it = preStartSessionMap_.find(sessionId);
        if (it == preStartSessionMap_.end()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "failed find session info with sessionId=%{public}s",
                sessionId.c_str());
            return ERR_INVALID_VALUE;
        }
        sessionInfo = it->second;
        CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);
        (sessionInfo->want).SetElement(want.GetElement());
    }

    if (sessionInfo->isMinimizedDuringFreeInstall) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "ability is already minimized");
        return ATOMIC_SERVICE_MINIMIZED;
    }

    bool isColdStart = true;
    AbilityRuntime::StartParamsBySCB params;
    int errCode = StartUIAbilityByPreInstallInner(sessionInfo, taskInfo.specifyTokenId, params, isColdStart);
    if (errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "startUIAbilityByPreInstallInner failed,errCode=%{public}d", errCode);
        return errCode;
    }
    RemovePreStartSession(sessionId);
    return errCode;
}

// StartUIAbilityByPreInstallInner is called when free install task is already finished
int AbilityManagerService::StartUIAbilityByPreInstallInner(sptr<SessionInfo> sessionInfo, uint32_t specifyTokenId,
    AbilityRuntime::StartParamsBySCB &params, bool &isColdStart)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call StartUIAbilityByPreInstallInner");
    CHECK_POINTER_AND_RETURN(sessionInfo, ERR_INVALID_VALUE);
    auto callerToken = sessionInfo->callerToken;
    const auto& want = sessionInfo->want;
    const auto userId = sessionInfo->userId;
    const auto requestCode = sessionInfo->requestCode;
    bool isStartAsCaller = false;

    if (callerToken != nullptr && !VerificationAllToken(callerToken)) {
        auto isSpecificSA = AAFwk::PermissionVerification::GetInstance()->
            CheckSpecificSystemAbilityAccessPermission(DMS_PROCESS_NAME);
        if (!isSpecificSA) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s verificationAllToken failed", __func__);
            return ERR_INVALID_CALLER;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "%{public}s: caller specific system ability", __func__);
    }

    int32_t oriValidUserId = GetValidUserId(userId);
    int32_t validUserId = oriValidUserId;

    int32_t appIndex = 0;
    if (!StartAbilityUtils::GetAppIndex(want, callerToken, appIndex)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "%{public}s GetAppIndex failed", __func__);
        return ERR_APP_CLONE_INDEX_INVALID;
    }
    StartAbilityInfoWrap threadLocalInfo(want, validUserId, appIndex, callerToken);
    auto shouldBlockFunc = [aams = shared_from_this()]() { return aams->ShouldBlockAllAppStart(); };
    AbilityInterceptorParam interceptorParam = AbilityInterceptorParam(want, requestCode, validUserId,
        true, nullptr, shouldBlockFunc);
    auto result = interceptorExecuter_ == nullptr ? ERR_INVALID_VALUE :
        interceptorExecuter_->DoProcess(interceptorParam);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "interceptorExecuter_ null or doProcess error");
        return result;
    }

    AbilityRequest abilityRequest;
    result = GenerateAbilityRequest(want, requestCode, abilityRequest, callerToken, validUserId);
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    std::string callerBundleName = abilityRecord ? abilityRecord->GetAbilityInfo().bundleName : "";

    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "generate ability request local error");
        return result;
    }

    abilityRequest.userId = validUserId;
    if (!HandleExecuteSAInterceptor(want, callerToken, abilityRequest, result)) {
        return result;
    }

    if (specifyTokenId > 0 && callerToken != nullptr) { // for sa specify tokenId and caller token
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfoFromToken(abilityRequest.want, callerToken);
    } else if (!isStartAsCaller) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "do not start as caller, UpdateCallerInfo");
        UpdateCallerInfoUtil::GetInstance().UpdateCallerInfo(abilityRequest.want, callerToken);
    } else if (callerBundleName == BUNDLE_NAME_DIALOG) {
#ifdef SUPPORT_SCREEN
        CHECK_POINTER_AND_RETURN(implicitStartProcessor_, ERR_IMPLICIT_START_ABILITY_FAIL);
        implicitStartProcessor_->ResetCallingIdentityAsCaller(
            abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), true);
#endif // SUPPORT_SCREEN
    }

    auto abilityInfo = abilityRequest.abilityInfo;
    validUserId = abilityInfo.applicationInfo.uid / BASE_USER_RANGE;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "userId is : %{public}d, singleton is : %{public}d",
        validUserId, static_cast<int>(abilityInfo.applicationInfo.singleton));

    result = CheckStaticCfgPermission(abilityRequest, isStartAsCaller,
        abilityRequest.want.GetIntParam(Want::PARAM_RESV_CALLER_TOKEN, 0), false, false, false);
    if (result != AppExecFwk::Constants::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkStaticCfgPermission error, result:%{public}d", result);
        return ERR_STATIC_CFG_PERMISSION;
    }

    result = CheckCallPermission(want, abilityInfo, abilityRequest, false,
        false, specifyTokenId, callerBundleName, false);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "checkCallPermission error, result:%{public}d", result);
        return result;
    }

    Want newWant = abilityRequest.want;
    AbilityInterceptorParam afterCheckParam = AbilityInterceptorParam(newWant, requestCode, validUserId,
        true, callerToken, std::make_shared<AppExecFwk::AbilityInfo>(abilityInfo), isStartAsCaller, appIndex);
    result = afterCheckExecuter_ == nullptr ? ERR_INVALID_VALUE :
        afterCheckExecuter_->DoProcess(afterCheckParam);
    bool isReplaceWantExist = newWant.GetBoolParam("queryWantFromErms", false);
    newWant.RemoveParam("queryWantFromErms");
    if (result != ERR_OK && isReplaceWantExist == false) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "doProcess failed or replaceWant absent");
        return result;
    }
#ifdef SUPPORT_SCREEN
    if (result != ERR_OK && isReplaceWantExist && callerBundleName != BUNDLE_NAME_DIALOG) {
        return DialogSessionManager::GetInstance().HandleErmsResult(abilityRequest, validUserId, newWant);
    }
    if (result == ERR_OK &&
        DialogSessionManager::GetInstance().IsCreateCloneSelectorDialog(abilityInfo.bundleName, validUserId)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "create clone selector dialog");
        return CreateCloneSelectorDialog(abilityRequest, validUserId);
    }
#endif // SUPPORT_SCREEN

    if (abilityInfo.type == AppExecFwk::AbilityType::SERVICE ||
        abilityInfo.type == AppExecFwk::AbilityType::EXTENSION) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "start ability by connectManager, type:%{public}d",
            static_cast<int32_t>(abilityInfo.type));
        return StartAbilityByConnectManager(want, abilityRequest, abilityInfo, validUserId, callerToken);
    }

    if (!IsAbilityControllerStart(want, abilityInfo.bundleName)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "isAbilityControllerStart failed:%{public}s", abilityInfo.bundleName.c_str());
        return ERR_WOULD_BLOCK;
    }

    abilityRequest.want.RemoveParam(SPECIFY_TOKEN_ID);
    if (specifyTokenId > 0) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "set specifyTokenId, the specifyTokenId is %{public}d", specifyTokenId);
        abilityRequest.want.SetParam(SPECIFY_TOKEN_ID, static_cast<int32_t>(specifyTokenId));
        abilityRequest.specifyTokenId = specifyTokenId;
    }
    abilityRequest.want.RemoveParam(PARAM_SPECIFIED_PROCESS_FLAG);

    auto uiAbilityManager = GetUIAbilityManagerByUserId(validUserId);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);

    return uiAbilityManager->StartUIAbility(abilityRequest, sessionInfo, params, isColdStart);
}

void AbilityManagerService::NotifySCBToHandleAtomicServiceException(const std::string& sessionId, int32_t errCode,
    const std::string& reason, int32_t userId)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call NotifySCBToHandleAtomicServiceException");
    sptr<SessionInfo> sessionInfo = nullptr;
    {
        std::lock_guard<ffrt::mutex> guard(preStartSessionMapLock_);
        auto it = preStartSessionMap_.find(sessionId);
        if (it == preStartSessionMap_.end()) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "failed find session info with sessionId=%{public}s",
                sessionId.c_str());
            return;
        }
        sessionInfo = it->second;
        preStartSessionMap_.erase(it);
    }
    if (sessionInfo == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo null");
        return;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
    CHECK_POINTER(uiAbilityManager);
    return uiAbilityManager->NotifySCBToHandleAtomicServiceException(sessionInfo, errCode, reason);
}

void AbilityManagerService::RemovePreStartSession(const std::string& sessionId)
{
    std::lock_guard<ffrt::mutex> guard(preStartSessionMapLock_);
    preStartSessionMap_.erase(sessionId);
}

AbilityRuntime::ExtractInsightIntentGenericInfo AbilityManagerService::GetInsightIntentGenericInfo(
    const InsightIntentExecuteParam &param)
{
    AbilityRuntime::ExtractInsightIntentGenericInfo infos;
    DelayedSingleton<AbilityRuntime::InsightIntentDbCache>::GetInstance()->GetInsightIntentGenericInfo(
        param.bundleName_, param.moduleName_, param.insightIntentName_, GetValidUserId(param.userId_), infos);
    TAG_LOGD(AAFwkTag::INTENT,
        "getLinkInfo:bundleName:%{public}s,moduleName:%{public}s,"
        "intentName:%{public}s,decoratorType:%{public}s",
        param.bundleName_.c_str(), param.moduleName_.c_str(), param.insightIntentName_.c_str(),
        infos.decoratorType.c_str());
    return infos;
}

void AbilityManagerService::CombinLinkInfo(
    const std::vector<AbilityRuntime::LinkIntentParamMapping> &paramMappings, std::string &uri, AAFwk::Want &want)
{
    bool linkQuestionChatFlag = true;
    if (uri.find('?') != std::string::npos) {
        linkQuestionChatFlag = false;
    }
    for (auto &mapInfo : paramMappings) {
        TAG_LOGD(AAFwkTag::INTENT,
            "paramMapping info paramName:%{public}s paramMappingName:%{public}s paramCategory:%{public}s",
            mapInfo.paramName.c_str(),
            mapInfo.paramMappingName.c_str(),
            mapInfo.paramCategory.c_str());
        if (!want.HasParameter(mapInfo.paramName)) {
            continue;
        }
        std::string value = want.GetStringParam(mapInfo.paramName);
        if (mapInfo.paramCategory == "link") {
            if (linkQuestionChatFlag) {
                uri += ("?" + mapInfo.paramMappingName + "=" + value);
                linkQuestionChatFlag = false;
            } else {
                uri += ("&" + mapInfo.paramMappingName + "=" + value);
            }
            TAG_LOGD(AAFwkTag::INTENT, "link uri=%{public}s", uri.c_str());
        } else {
            want.RemoveParam(mapInfo.paramName);
            want.SetParam(mapInfo.paramMappingName, value);
            TAG_LOGD(AAFwkTag::INTENT,
                "want setparam key:%{public}s value:%{public}s",
                mapInfo.paramMappingName.c_str(),
                value.c_str());
        }
    }
}

ErrCode AbilityManagerService::IntentOpenLinkInner(const std::shared_ptr<AppExecFwk::InsightIntentExecuteParam> &param,
    AbilityRuntime::ExtractInsightIntentGenericInfo &linkInfo, const int32_t userId)
{
    if (param->uris_.empty()) {
        TAG_LOGE(AAFwkTag::INTENT, "Intent OpenLink failed uris is empty");
        return INNER_ERR;
    }
    std::string linkUri = linkInfo.get<AbilityRuntime::InsightIntentLinkInfo>().uri;
    if (linkUri != param->uris_[0].substr(0, linkUri.size())) {
        TAG_LOGE(AAFwkTag::INTENT,
            "Intent OpenLink failed uris is mismatch,linkUri:%{public}s, param uris:%{public}s",
            linkUri.c_str(), param->uris_[0].c_str());
        return INNER_ERR;
    }

    AAFwk::Want want;
    want.SetParams(*param->insightIntentParam_);
    std::string openLinkUri = param->uris_[0];
    CombinLinkInfo(linkInfo.get<AbilityRuntime::InsightIntentLinkInfo>().paramMapping, openLinkUri, want);

    want.SetUri(openLinkUri);
    want.SetElementName("", param->bundleName_, "", param->moduleName_);
    TAG_LOGD(AAFwkTag::INTENT, "openLinkUri=%{public}s", openLinkUri.c_str());
    if (!want.HasParameter(APP_LINKING_ONLY)) {
        want.SetParam(APP_LINKING_ONLY, false);
    }
    want.SetParam(AppExecFwk::INSIGHT_INTENT_EXECUTE_PARAM_NAME, param->insightIntentName_);
    want.SetParam(AppExecFwk::INSIGHT_INTENT_EXECUTE_OPENLINK_FLAG, 1);
    if (!want.HasParameter(Want::PARAM_APP_CLONE_INDEX_KEY)) {
        want.SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, 0);
    }

    auto resultCode = OpenLinkInner(want, nullptr, userId, DEFAULT_INVAL_VALUE, false);
    if (resultCode == ERR_OK || resultCode == ERR_OPEN_LINK_START_ABILITY_DEFAULT_OK) {
        TAG_LOGD(AAFwkTag::INTENT, "Intent OpenLink success");
        InsightIntentExecuteResult result;
        DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->ExecuteIntentDone(
            param->insightIntentId_, result.innerErr, result);
        return ERR_OK;
    }
    //mapping error code 16000019->16000050
    if (resultCode == ERR_IMPLICIT_START_ABILITY_FAIL) {
        resultCode = INNER_ERR;
    }
    TAG_LOGD(AAFwkTag::INTENT, "Intent OpenLink failed:%{public}d", resultCode);
    return resultCode;
}

ErrCode AbilityManagerService::OpenLink(const Want& want, sptr<IRemoteObject> callerToken,
    int32_t userId, int32_t requestCode, bool hideFailureTipDialog)
{
    return OpenLinkInner(want, callerToken, userId, requestCode, true, hideFailureTipDialog);
}

ErrCode AbilityManagerService::OpenLinkInner(const Want& want, sptr<IRemoteObject> callerToken,
    int32_t userId, int32_t requestCode, bool removeInsightIntentFlag, bool hideFailureTipDialog)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call OpenLink, requestCode:%{public}d", requestCode);
    AbilityUtil::RemoveInstanceKey(const_cast<Want &>(want));
    std::string callerBundleName = want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME);
    Want convertedWant = want;
    TAG_LOGD(AAFwkTag::ABILITYMGR, "hideFailureTipDialog: %{public}d", hideFailureTipDialog);
    if (!WantUtils::IsShortUrl(want) || ((!IS_FOUNDATION_CALL || callerBundleName.empty()) &&
        WantUtils::GetCallerBundleName(callerBundleName) != ERR_OK)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "start ability by default");
        OPEN_LINK_START_ABILITY(want, callerToken, userId, requestCode, removeInsightIntentFlag,
            hideFailureTipDialog, true);
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "callerBundleName=%{public}s", callerBundleName.c_str());
    convertedWant.SetParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME, callerBundleName);
    uint32_t targetType = TARGET_TYPE_INIT;
    if (WantUtils::ConvertToExplicitWant(convertedWant, targetType) != ERR_OK) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "ConvertToExplicitWant fail. start ability by default");
        OPEN_LINK_START_ABILITY(want, callerToken, userId, requestCode, removeInsightIntentFlag,
            hideFailureTipDialog, true);
    }
    if (WantUtils::IsNormalApp(targetType)) {
        OPEN_LINK_START_ABILITY(convertedWant, callerToken, userId, requestCode, removeInsightIntentFlag,
            hideFailureTipDialog, true);
    }
    if (WantUtils::IsAtomicService(targetType)) {
        StartAbilityWrapParam param = {
            .want = convertedWant,
            .callerToken = callerToken,
            .requestCode = requestCode,
            .userId = userId,
            .hideFailureTipDialog = hideFailureTipDialog,
            .removeInsightIntentFlag = removeInsightIntentFlag,
            .isFromOpenLink = true,
        };
        return OpenLinkFreeInstallAtomicService(param, want);
    }
    bool curAppLinkingOnlyFlag = convertedWant.GetBoolParam(APP_LINKING_ONLY, false);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "openLink not specific app or atomicService. AppLinkingOnly: %{public}d",
        curAppLinkingOnlyFlag);
    if (curAppLinkingOnlyFlag) {
        return RESOLVE_ABILITY_ERR;
    }
    OPEN_LINK_START_ABILITY(convertedWant, callerToken, userId, requestCode, removeInsightIntentFlag,
        hideFailureTipDialog, true);
}

int32_t AbilityManagerService::OpenLinkFreeInstallAtomicService(StartAbilityWrapParam &param,
    const Want &originalWant)
{
    if (freeInstallManager_ == nullptr) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "freeInstallManager_ nullptr. start ability by default");
        OPEN_LINK_START_ABILITY(originalWant, param.callerToken, param.userId, param.requestCode,
            param.removeInsightIntentFlag, param.hideFailureTipDialog, param.isFromOpenLink);
    }
    param.want.AddFlags(Want::FLAG_INSTALL_ON_DEMAND);
    auto freeInstallParam = std::make_shared<FreeInstallParams>();
    freeInstallParam->isAsync = true;
    freeInstallParam->isOpenAtomicServiceShortUrl = true;
    freeInstallParam->originalWant = std::make_shared<Want>(originalWant);
    ErrCode retCode = freeInstallManager_->StartFreeInstall(param.want, GetValidUserId(param.userId),
        param.requestCode, param.callerToken, freeInstallParam);
    if (retCode != ERR_OK) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "startFreeInstall returns errCode=%{public}d", retCode);
        if (retCode == NOT_TOP_ABILITY) {
            TAG_LOGE(AAFwkTag::ABILITYMGR, "start from background not allowed");
            return retCode;
        }
        TAG_LOGI(AAFwkTag::ABILITYMGR, "start ability by default");
        OPEN_LINK_START_ABILITY(originalWant, param.callerToken, param.userId, param.requestCode,
            param.removeInsightIntentFlag, param.hideFailureTipDialog, param.isFromOpenLink);
    }
    return ERR_OK;
}

int32_t AbilityManagerService::CleanUIAbilityBySCB(const sptr<SessionInfo> &sessionInfo, bool isUserRequestedExit,
    uint32_t sceneFlag)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    if (sessionInfo == nullptr || sessionInfo->sessionToken == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sessionInfo invalid");
        return ERR_INVALID_VALUE;
    }

    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "only support sceneboard call");
        return ERR_WRONG_INTERFACE_CALL;
    }

    SetMinimizedDuringFreeInstall(sessionInfo);

    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "user request clean session: %{public}d", sessionInfo->persistentId);
    auto abilityRecord = uiAbilityManager->GetUIAbilityRecordBySessionInfo(sessionInfo);
    if(!abilityRecord){
        (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->
            DeleteAbilityRecoverInfoBySessionId(sessionInfo->persistentId);
    }
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);
    abilityRecord->SetSceneFlag(sceneFlag);
    if (isUserRequestedExit) {
        CHECK_POINTER_AND_RETURN(appExitReasonHelper_, ERR_NULL_OBJECT);
        AAFwk::ExitReason exitReason = { REASON_NORMAL, "User Request" };
        appExitReasonHelper_->RecordUIAbilityExitReason(abilityRecord->GetPid(), abilityRecord->GetAbilityInfo().name,
            exitReason);
    }
    int32_t errCode = uiAbilityManager->CleanUIAbility(abilityRecord);
    ReportCleanSession(sessionInfo, abilityRecord, errCode);
    return errCode;
}

void AbilityManagerService::ForceTerminateServiceExtensionByPid(int32_t pid, int32_t userId)
{
    std::vector<sptr<IRemoteObject>> tokens;
    IN_PROCESS_CALL_WITHOUT_RET(DelayedSingleton<AppScheduler>::GetInstance()->GetAbilityRecordsByProcessID(
        pid, tokens));
    auto connectManager = GetCommonExtensionManagerByUserId(userId);
    if (connectManager) {
        for (const auto& token : tokens) {
            auto abilityRecord = Token::GetAbilityRecordByToken(token);
            if (abilityRecord &&
                abilityRecord->GetAbilityInfo().extensionAbilityType ==
                AppExecFwk::ExtensionAbilityType::SERVICE) {
                TAG_LOGI(AAFwkTag::ABILITYMGR, "app ForceTerminateServiceExtensionByPid, pid is %{public}d", pid);
                connectManager->TerminateAbility(token);
            }
        }
    }
}

void AbilityManagerService::ReportCleanSession(const sptr<SessionInfo> &sessionInfo,
    const std::shared_ptr<AbilityRecord> &abilityRecord, int32_t errCode)
{
    if (!sessionInfo || !abilityRecord) {
        return;
    }

    const auto &abilityInfo = abilityRecord->GetAbilityInfo();
    std::string abilityName = abilityInfo.name;
    if (abilityInfo.launchMode == AppExecFwk::LaunchMode::STANDARD) {
        abilityName += std::to_string(sessionInfo->persistentId);
    }
    (void)DelayedSingleton<AbilityRuntime::AppExitReasonDataManager>::GetInstance()->
        DeleteAbilityRecoverInfo(abilityInfo.applicationInfo.accessTokenId, abilityInfo.moduleName, abilityName);

    EventInfo eventInfo;
    eventInfo.errCode = errCode;
    eventInfo.bundleName = abilityRecord->GetAbilityInfo().bundleName;
    eventInfo.abilityName = abilityRecord->GetAbilityInfo().name;
    SendAbilityEvent(EventName::CLOSE_ABILITY, HISYSEVENT_BEHAVIOR, eventInfo);
    if (eventInfo.errCode != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "failed to terminate ability: %{public}d", eventInfo.errCode);
        SendAbilityEvent(EventName::TERMINATE_ABILITY_ERROR, HISYSEVENT_FAULT, eventInfo);
    }
}

void AbilityManagerService::SendStartAbilityOtherExtensionEvent(const AppExecFwk::AbilityInfo& abilityInfo,
    const Want& want, uint32_t specifyTokenId)
{
    if (abilityInfo.type != AppExecFwk::AbilityType::EXTENSION ||
        abilityInfo.extensionAbilityType == AppExecFwk::ExtensionAbilityType::SERVICE) {
        return;
    }
    EventInfo eventInfo;
    eventInfo.bundleName = abilityInfo.bundleName;
    eventInfo.moduleName = abilityInfo.moduleName;
    eventInfo.abilityName = abilityInfo.name;
    eventInfo.extensionType = static_cast<int32_t>(abilityInfo.extensionAbilityType);
    if (specifyTokenId > 0) {
        // come from want agent or form
        Security::AccessToken::HapTokenInfo hapInfo;
        if (Security::AccessToken::AccessTokenKit::GetHapTokenInfo(specifyTokenId, hapInfo) == ERR_OK) {
            eventInfo.callerBundleName = hapInfo.bundleName;
        }
    } else {
        eventInfo.callerBundleName = want.GetStringParam(Want::PARAM_RESV_CALLER_BUNDLE_NAME);
        if (eventInfo.callerBundleName.empty()) {
            eventInfo.callerBundleName = want.GetStringParam(Want::PARAM_RESV_CALLER_NATIVE_NAME);
        }
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "SendStartAbilityOtherExtensionEvent, bundleName:%{public}s, extensionAbilityType:%{public}d",
        eventInfo.bundleName.c_str(), eventInfo.extensionType);
    EventReport::SendStartAbilityOtherExtensionEvent(EventName::START_ABILITY_OTHER_EXTENSION, eventInfo);
}

void AbilityManagerService::SetAbilityRequestSessionInfo(AbilityRequest &abilityRequest,
    AppExecFwk::ExtensionAbilityType extensionType)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");
    if (extensionType != AppExecFwk::ExtensionAbilityType::UI_SERVICE) {
        return;
    }

    abilityRequest.want.RemoveParam(WANT_PARAMS_HOST_WINDOW_ID_KEY);
    auto callerAbilityRecord = Token::GetAbilityRecordByToken(abilityRequest.callerToken);
    CHECK_POINTER_LOG(callerAbilityRecord, "callerAbilityRecord is nullptr");
    sptr<SessionInfo> callerSessionInfo = callerAbilityRecord->GetSessionInfo();
    CHECK_POINTER_LOG(callerSessionInfo, "callerSessionInfo is nullptr");

    if (callerAbilityRecord->GetAbilityInfo().type == AbilityType::PAGE) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "UIAbility Caller");
        abilityRequest.want.SetParam(WANT_PARAMS_HOST_WINDOW_ID_KEY, callerSessionInfo->persistentId);
    } else if (AAFwk::UIExtensionWrapper::IsUIExtension(callerAbilityRecord->GetAbilityInfo().extensionAbilityType)) {
        int32_t mainWindowId = -1;
        auto sceneSessionManager = Rosen::SessionManagerLite::GetInstance().
            GetSceneSessionManagerLiteProxy();
        CHECK_POINTER_LOG(sceneSessionManager, "sceneSessionManager is nullptr");
        auto err = sceneSessionManager->GetRootMainWindowId(static_cast<int32_t>(callerSessionInfo->hostWindowId),mainWindowId);
        TAG_LOGI(AAFwkTag::ABILITYMGR, "callerSessionInfo->hostWindowId = %{public}d, mainWindowId = %{public}d, err = %{public}d",
            callerSessionInfo->hostWindowId, mainWindowId, err);
        abilityRequest.want.SetParam(WANT_PARAMS_HOST_WINDOW_ID_KEY, mainWindowId);
    } else {
        abilityRequest.want.SetParam(WANT_PARAMS_HOST_WINDOW_ID_KEY, 0);
    }
}

int32_t AbilityManagerService::TerminateMission(int32_t missionId)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "TerminateMission");
    auto missionListManager = GetCurrentMissionListManager();
    CHECK_POINTER_AND_RETURN(missionListManager, ERR_NO_INIT);
    CHECK_CALLER_IS_SYSTEM_APP;

    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_KILL_APP_PROCESSES)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission verification failed");
        return CHECK_PERMISSION_FAILED;
    }

    return missionListManager->ClearMission(missionId);
}

int32_t AbilityManagerService::BlockAllAppStart(bool flag)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "called");

    if (!AppUtils::GetInstance().IsStartOptionsWithAnimation()) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "not supported device");
        return ERR_PERMISSION_DENIED;
    }

    if (!PermissionVerification::GetInstance()->VerifyBlockAllAppStartPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Permission verification failed");
        return ERR_PERMISSION_DENIED;
    }

    std::unique_lock<ffrt::mutex> lock(shouldBlockAllAppStartMutex_);
    shouldBlockAllAppStart_ = flag;
    return ERR_OK;
}

bool AbilityManagerService::ShouldBlockAllAppStart()
{
    if (!AppUtils::GetInstance().IsStartOptionsWithAnimation()) {
        return false;
    }

    std::unique_lock<ffrt::mutex> lock(shouldBlockAllAppStartMutex_);
    return shouldBlockAllAppStart_;
}

int32_t AbilityManagerService::UpdateAssociateConfigList(const std::map<std::string, std::list<std::string>>& configs,
    const std::list<std::string>& exportConfigs, int32_t flag)
{
    if (IPCSkeleton::GetCallingUid() != RESOURCE_SCHEDULE_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "Update associate config, current process not rss process");
        return CHECK_PERMISSION_FAILED;
    }
    std::lock_guard<std::mutex> locker(whiteListMutex_);
    if (flag == UPDATE_CONFIG_FLAG_COVER) {
        whiteListMap_ = configs;
        exportWhiteList_ = exportConfigs;
    } else if (flag == UPDATE_CONFIG_FLAG_APPEND) {
        for (const auto& config : configs) {
            for (const auto& item : config.second) {
                whiteListMap_[config.first].push_back(item);
            }
        }
        for (const auto& config : exportConfigs) {
            exportWhiteList_.push_back(config);
        }
    }
    return ERR_OK;
}

void AbilityManagerService::EnableListForSCBRecovery(int32_t userId) const
{
    auto uiAbilityManager = GetUIAbilityManagerByUserId(userId);
    CHECK_POINTER_LOG(uiAbilityManager, "UIAbilityMgr not exist.");
    uiAbilityManager->EnableListForSCBRecovery();
}

int32_t AbilityManagerService::UpdateKeepAliveEnableState(const std::string &bundleName,
    const std::string &moduleName, const std::string &mainElement, bool updateEnable, int32_t userId)
{
    auto commonExtensionManager = GetCommonExtensionManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(commonExtensionManager, ERR_NULL_OBJECT);
    int32_t retCommon = commonExtensionManager->UpdateKeepAliveEnableState(bundleName, moduleName, mainElement, updateEnable);
    if (retCommon != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "UpdateKeepAliveEnableState failed, err:%{public}d", retCommon);
    }
    
    auto uiExtensionAbilityManager = GetUIExtensionAbilityManagerByUserId(userId);
    CHECK_POINTER_AND_RETURN(uiExtensionAbilityManager, ERR_NULL_OBJECT);
    int32_t retUI = commonExtensionManager->UpdateKeepAliveEnableState(bundleName, moduleName, mainElement, updateEnable);
    if (retUI != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "UpdateKeepAliveEnableState failed, err:%{public}d", retUI);
    }
    if (retCommon != ERR_OK) {
        return retCommon;
    }
    return retUI;
}

bool AbilityManagerService::IsInStatusBar(uint32_t accessTokenId, int32_t uid, bool isMultiInstance)
{
    auto uiAbilityManager = GetUIAbilityManagerByUid(uid);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, false);

    return uiAbilityManager->IsInStatusBar(accessTokenId, isMultiInstance);
}

bool AbilityManagerService::IsSupportStatusBar(int32_t uid)
{
    auto uiAbilityManager = GetUIAbilityManagerByUid(uid);
    CHECK_POINTER_AND_RETURN(uiAbilityManager, false);

    return uiAbilityManager->IsSupportStatusBar();
}

int32_t AbilityManagerService::SetApplicationKeepAlive(const std::string &bundleName, int32_t userId, bool flag)
{
    return KeepAliveProcessManager::GetInstance().SetApplicationKeepAlive(
        bundleName, userId, flag, false, false);
}

int32_t AbilityManagerService::QueryKeepAliveApplications(int32_t appType, int32_t userId,
    std::vector<KeepAliveInfo> &list)
{
    return KeepAliveProcessManager::GetInstance().QueryKeepAliveApplications(
        appType, userId, list, false);
}

int32_t AbilityManagerService::SetApplicationKeepAliveByEDM(const std::string &bundleName, int32_t userId,
    bool flag, bool isAllowUserToCancel)
{
    if (userId != U1_USER_ID && isAllowUserToCancel) {
        return ERR_CAPABILITY_NOT_SUPPORT;
    }

    auto bms = AbilityUtil::GetBundleManagerHelper();
    AppExecFwk::BundleInfo bundleInfo;
    if (bms && userId == U1_USER_ID) {
        if (IN_PROCESS_CALL(bms->GetBundleInfo(
            bundleName, AppExecFwk::BundleFlag::GET_BUNDLE_DEFAULT, bundleInfo, userId))) {
            std::string mainElementName;
            if (MainElementUtils::CheckAppServiceExtension(bundleInfo, mainElementName)) {
                return KeepAliveProcessManager::GetInstance().SetAppServiceExtensionKeepAlive(
                    bundleName, flag, true, isAllowUserToCancel);
            }
        }
    }

    return KeepAliveProcessManager::GetInstance().SetApplicationKeepAlive(
        bundleName, userId, flag, true, false);
}

int32_t AbilityManagerService::QueryKeepAliveApplicationsByEDM(int32_t appType, int32_t userId,
    std::vector<KeepAliveInfo> &list)
{
    return KeepAliveProcessManager::GetInstance().QueryKeepAliveApplications(
        appType, userId, list, true);
}

int AbilityManagerService::StartSelfUIAbilityInner(StartSelfUIAbilityParam param)
{
    CHECK_TRUE_RETURN_RET(!AppUtils::GetInstance().IsStartOptionsWithAnimation(),
        ERR_CAPABILITY_NOT_SUPPORT, "not supported");
    auto targetBundleName = param.want.GetBundle();
    CHECK_TRUE_RETURN_RET(targetBundleName.empty(), ERR_NOT_ALLOW_IMPLICIT_START, "implicit start not allowed");

    auto callingPid = IPCSkeleton::GetCallingPid();
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByChildProcessPid(callingPid, processInfo);
    CHECK_TRUE_RETURN_RET(processInfo.bundleNames.empty(), INNER_ERR, "failed to get by child process pid");
    auto iter = std::find_if(processInfo.bundleNames.begin(), processInfo.bundleNames.end(),
        [targetBundleName](const std::string &bundleName) { return bundleName == targetBundleName; });
    CHECK_TRUE_RETURN_RET(iter == processInfo.bundleNames.end(), ERR_START_OTHER_APP_FAILED, "cannot start other app");

    auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bundleMgrHelper, INNER_ERR);
    AppExecFwk::AbilityInfo abilityInfo;
    auto callerUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    CHECK_TRUE_RETURN_RET(!IN_PROCESS_CALL(bundleMgrHelper->QueryAbilityInfo(param.want,
        AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_WITH_APPLICATION, callerUserId, abilityInfo)),
        TARGET_BUNDLE_NOT_EXIST, "bundle or ability not exist");

    CHECK_TRUE_RETURN_RET(abilityInfo.type != AppExecFwk::AbilityType::PAGE,
        RESOLVE_CALL_ABILITY_TYPE_ERR, "not UIAbility");

    param.want.RemoveParam(Want::PARAM_APP_CLONE_INDEX_KEY);
    if (processInfo.appMode == AppExecFwk::MultiAppModeType::APP_CLONE) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "set appIndex: %{public}d", processInfo.appCloneIndex);
        param.want.SetParam(Want::PARAM_APP_CLONE_INDEX_KEY, processInfo.appCloneIndex);
    }

    if (processInfo.appMode == AppExecFwk::MultiAppModeType::MULTI_INSTANCE &&
        !param.want.HasParameter(Want::APP_INSTANCE_KEY) &&
        !param.want.GetBoolParam(Want::CREATE_APP_INSTANCE_KEY, false)) {
        TAG_LOGI(AAFwkTag::ABILITYMGR, "set instanceKey: %{public}s", processInfo.instanceKey.c_str());
        param.want.SetParam(Want::APP_INSTANCE_KEY, processInfo.instanceKey);
    }

    auto tokenId = abilityInfo.applicationInfo.accessTokenId;
    StartSelfUIAbilityRecordGuard startSelfUIAbilityRecordGuard(callingPid, tokenId);
    CHECK_TRUE_RETURN_RET(!PermissionVerification::GetInstance()->VerifyStartSelfUIAbility(tokenId),
        CHECK_PERMISSION_FAILED, "permission denied");

    CHECK_TRUE_RETURN_RET(processInfo.state_ != AppExecFwk::AppProcessState::APP_STATE_FOREGROUND,
        NOT_TOP_ABILITY, "caller not foreground");

    if (!param.hasStartOptions) {
        return StartAbility(param.want);
    }
    return StartAbility(param.want, param.options, nullptr);
}

int AbilityManagerService::StartSelfUIAbility(const Want &want)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);

    StartSelfUIAbilityParam param;
    param.want = want;
    return StartSelfUIAbilityInner(param);
}

int AbilityManagerService::StartSelfUIAbilityWithStartOptions(const Want &want, const StartOptions &options)
{
    if (AppUtils::GetInstance().IsForbidStart()) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "forbid start: %{public}s", want.GetElement().GetBundleName().c_str());
        return INNER_ERR;
    }
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartSelfUIAbility with startOptions");

    if(options.processOptions != nullptr) {
       options.processOptions->isStartFromNDK = true;
    }

    StartSelfUIAbilityParam param = { want, options, true };
    return StartSelfUIAbilityInner(param);
}

int AbilityManagerService::StartSelfUIAbilityWithPidResult(const Want &want, StartOptions &options,
    uint64_t callbackId)
{
    XCOLLIE_TIMER_LESS(__PRETTY_FUNCTION__);
    TAG_LOGI(AAFwkTag::ABILITYMGR, "StartSelfUIAbilityWithPidResult");

    if (options.processOptions == nullptr) {
        options.processOptions = std::make_shared<ProcessOptions>();
    }
    options.processOptions->loadAbilityCallbackId = callbackId;
    options.processOptions->callingPid = IPCSkeleton::GetCallingPid();
    auto ret = StartSelfUIAbilityWithStartOptions(want, options);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartSelfUIAbilityWithStartOptions failed:%{public}d", ret);
        return ret;
    }
    return ERR_OK;
}

bool AbilityManagerService::CheckCrossUser(const int32_t userId, AppExecFwk::ExtensionAbilityType extensionType)
{
    if (AAFwk::UIExtensionWrapper::IsEnterpriseAdmin(extensionType) || JudgeMultiUserConcurrency(userId)) {
        return true;
    }
    if (AppUtils::GetInstance().IsConnectSupportCrossUser() && (extensionType == AppExecFwk::ExtensionAbilityType::DATASHARE
        || extensionType == AppExecFwk::ExtensionAbilityType::SERVICE)) {
        return true;
    }
    return false;
}

int32_t AbilityManagerService::KillProcessForPermissionUpdate(uint32_t accessTokenId)
{
    int32_t callingUid = IPCSkeleton::GetCallingUid();
    TAG_LOGI(AAFwkTag::ABILITYMGR,
        "Call KillProcessForPermissionUpdate. callingUid: %{public}d", callingUid);
    auto isCallingPerm = PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_KILL_APP_PROCESSES);
    if (!isCallingPerm) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no permission to kill processes.");
        return ERR_PERMISSION_DENIED;
    }

    if (Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        auto uiAbilityManager = GetUIAbilityManagerByUid(callingUid);
        CHECK_POINTER_AND_RETURN_LOG(uiAbilityManager, ERR_NULL_OBJECT, "uiAbilityLifecycleManager nullptr");
        uiAbilityManager->SetKillForPermissionUpdateFlag(accessTokenId);
    }

    int32_t ret =
        DelayedSingleton<AppScheduler>::GetInstance()->KillProcessesByAccessTokenId(accessTokenId);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "KillProcessesByAccessTokenId error");
        return ret;
    }

    return ERR_OK;
}

int32_t AbilityManagerService::RegisterHiddenStartObserver(const sptr<IHiddenStartObserver> &observer)
{
    if (!AAFwk::PermissionVerification::GetInstance()->VerifyStartUIAbilityToHiddenPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "RegisterHiddenStartObserver permission verification failed");
        return ERR_PERMISSION_DENIED;
    }
    return HiddenStartObserverManager::GetInstance().RegisterObserver(observer);
}

int32_t AbilityManagerService::UnregisterHiddenStartObserver(const sptr<IHiddenStartObserver> &observer)
{
    if (!AAFwk::PermissionVerification::GetInstance()->VerifyStartUIAbilityToHiddenPermission()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "UnregisterHiddenStartObserver permission verification failed");
        return ERR_PERMISSION_DENIED;
    }
    return HiddenStartObserverManager::GetInstance().UnregisterObserver(observer);
}

int32_t AbilityManagerService::QueryPreLoadUIExtensionRecord(const AppExecFwk::ElementName &element,
                                                             const std::string &moduleName,
                                                             const int32_t hostPid,
                                                             int32_t &recordNum,
                                                             int32_t userId)
{
  // check preload ui extension permission.
  CHECK_CALLER_IS_SYSTEM_APP;
  if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
          PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
      TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
               PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
      return ERR_PERMISSION_DENIED;
  }
  int32_t validUserId = GetValidUserId(userId);
  auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
  if (!connectManager) {
      TAG_LOGE(AAFwkTag::UI_EXT, "connectManager null. userId=%{public}d", userId);
      return ERR_INVALID_VALUE;
  }
  return connectManager->QueryPreLoadUIExtensionRecordInner(
      element, moduleName, hostPid, recordNum);
}

int32_t AbilityManagerService::RevokeDelegator(sptr<IRemoteObject> token)
{
    if (!Rosen::SceneBoardJudgement::IsSceneBoardEnabled()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "capability not support");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }
    auto callingTokenId = IPCSkeleton::GetCallingTokenID();
    auto tokenType = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(callingTokenId);
    if (tokenType != Security::AccessToken::ATokenTypeEnum::TOKEN_HAP) {
        TAG_LOGE(AAFwkTag::URIPERMMGR, "Not TOKEN_HAP");
        return ERR_NO_PERMISSION_CALLER;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->RevokeDelegator(token);
}

int32_t AbilityManagerService::StartAbilityWithWait(Want &want, sptr<IAbilityStartWithWaitObserver> &observer)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::ABILITYMGR, "AbilityManagerService::StartAbilityWithWait called");
    auto isShellCall = AAFwk::PermissionVerification::GetInstance()->IsShellCall();
    if (!isShellCall) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not shell call");
        return ERR_PERMISSION_DENIED;
    }
    // 1.regist observer
    int32_t result = AbilityStartWithWaitObserverManager::GetInstance().RegisterObserver(want, observer);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "register ability start with wait observer fail, result:%{public}d", result);
        return result;
    }
    // 2.start ability
    result = StartAbility(want, DEFAULT_INVAL_VALUE, DEFAULT_INVAL_VALUE);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "start ability wait fail, result:%{public}d", result);
        return result;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::CheckStartPlugin(const Want& want, sptr<IRemoteObject> callerToken, bool &isTargetPlugin)
{
    if (!AbilityRuntime::StartupUtil::IsStartPlugin(want)) {
        return ERR_OK;
    }
    TAG_LOGI(AAFwkTag::ABILITYMGR, "start plugin ability");
    // bundleName, abilityName, moduoleName not empty
    auto element = want.GetElement();
    if (element.GetBundleName().empty() || element.GetAbilityName().empty() || element.GetModuleName().empty()) {
        return INVALID_PARAMETERS_ERR;
    }
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    if (!abilityRecord) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "abilityRecord null");
        return ERR_CHECK_PLUGIN_NULL_RECORD;
    }
    if (!(abilityRecord->GetAbilityInfo().type == AppExecFwk::AbilityType::PAGE ||
        (abilityRecord->GetAbilityInfo().type == AppExecFwk::AbilityType::EXTENSION &&
        abilityRecord->GetAbilityInfo().extensionAbilityType == AppExecFwk::ExtensionAbilityType::EMBEDDED_UI))) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "type is not UIAbility or embedded_ui");
        return ERR_CHECK_PLUGIN_INVALID_TYPE;
    }
    if (abilityRecord->IsPluginAbility()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not host ability");
        return ERR_CALLER_IS_PLUGIN_ABILITY;
    }
    isTargetPlugin = true;
    return ERR_OK;
}

int32_t AbilityManagerService::GetAllInsightIntentInfo(
    AbilityRuntime::GetInsightIntentFlag flag,
    std::vector<InsightIntentInfoForQuery> &infos,
    int32_t userId)
{
    TAG_LOGI(AAFwkTag::INTENT, "GetAllInsightIntentInfo");
    int32_t ret = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckGetInsightIntenInfoPermission();
    if (ret != ERR_OK) {
        TAG_LOGD(AAFwkTag::INTENT, "not system app or permission denied");
        return ret;
    }

    if(IsCrossUserCall(userId)) {
        if (VerifyAccountPermission(userId) != ERR_OK) {
            TAG_LOGE(AAFwkTag::INTENT, "permission verification failed");
            return CHECK_PERMISSION_FAILED;
        }
        if (!JudgeMultiUserConcurrency(userId)) {
            TAG_LOGE(AAFwkTag::INTENT, "multi-user non-concurrent unsatisfied");
            return ERR_CROSS_USER;
        }
    }

    if (flag & AbilityRuntime::GetInsightIntentFlag::GET_FULL_INSIGHT_INTENT) {
        std::vector<ExtractInsightIntentInfo> intentInfos;
        std::vector<InsightIntentInfo> configInfos;
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetAllInsightIntentInfo(GetValidUserId(userId), intentInfos, configInfos);
        if (intentInfos.empty() && configInfos.empty()) {
            TAG_LOGD(AAFwkTag::INTENT, "extractInsightIntentInfos empty");
            return ERR_OK;
        }
        TAG_LOGD(AAFwkTag::INTENT, "intentInfos size: %{public}zu, configInfos size: %{public}zu",
            intentInfos.size(), configInfos.size());
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        for (auto &info : configInfos) {
             InsightIntentInfoForQuery intentInfoQuery;
             InsightIntentUtils::ConvertConfigInsightIntentInfo(info, intentInfoQuery, getEntity);
             infos.emplace_back(intentInfoQuery);
        }
        for (auto &info : intentInfos) {
            InsightIntentInfoForQuery intentInfoQuery;
            InsightIntentUtils::ConvertExtractInsightIntentInfo(info, intentInfoQuery, getEntity);
            infos.emplace_back(intentInfoQuery);
        }
    } else if (flag & AbilityRuntime::GetInsightIntentFlag::GET_SUMMARY_INSIGHT_INTENT) {
        std::vector<ExtractInsightIntentGenericInfo> genericInfos;
        std::vector<InsightIntentInfo> configInfos;
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetAllConfigInsightIntentInfo(GetValidUserId(userId), configInfos);
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetAllInsightIntentGenericInfo(GetValidUserId(userId), genericInfos);
        if (genericInfos.empty() && configInfos.empty()) {
            return ERR_OK;
        }
        TAG_LOGD(AAFwkTag::INTENT, "genericInfos size: %{public}zu", genericInfos.size());
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        for (auto &info : configInfos) {
             InsightIntentInfoForQuery intentInfoQuery;
             InsightIntentUtils::ConvertConfigInsightIntentInfo(info, intentInfoQuery, getEntity);
             infos.emplace_back(intentInfoQuery);
        }

        if (getEntity) {
            std::vector<ExtractInsightIntentInfo> intentInfos;
            std::vector<InsightIntentInfo> configInfosWithEntity;
            DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetAllInsightIntentInfo(GetValidUserId(userId), intentInfos, configInfosWithEntity);
            if (intentInfos.empty() && configInfosWithEntity.empty()) {
                TAG_LOGI(AAFwkTag::INTENT, "InsightIntentInfos empty");
                return ERR_OK;
            }
            for (auto &info : intentInfos) {
                InsightIntentInfoForQuery intentInfoQuery;
                InsightIntentUtils::ConvertExtractInsightIntentEntityInfo(info, intentInfoQuery);
                infos.emplace_back(intentInfoQuery);
            }
            return ERR_OK;
        }

        for (auto &info : genericInfos) {
            InsightIntentInfoForQuery intentInfoQuery;
            InsightIntentUtils::ConvertExtractInsightIntentGenericInfo(info, intentInfoQuery);
            infos.emplace_back(intentInfoQuery);
        }
    } else {
        TAG_LOGW(AAFwkTag::INTENT, "invalid flag: %{public}d", flag);
    }

    return ERR_OK;
}

int32_t AbilityManagerService::GetInsightIntentInfoByBundleName(
    AbilityRuntime::GetInsightIntentFlag flag,
    const std::string &bundleName,
    std::vector<InsightIntentInfoForQuery> &infos,
    int32_t userId)
{
    TAG_LOGI(AAFwkTag::INTENT, "GetInsightIntentInfoByBundleName");
    int32_t ret = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckGetInsightIntenInfoPermission();
    if (ret != ERR_OK) {
        TAG_LOGD(AAFwkTag::INTENT, "not system app or permission denied");
        return ret;
    }

    if(IsCrossUserCall(userId)) {
        if (VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
            TAG_LOGE(AAFwkTag::INTENT, "permission verification failed");
            return CHECK_PERMISSION_FAILED;
        }
        if (!JudgeMultiUserConcurrency(userId)) {
            TAG_LOGE(AAFwkTag::INTENT, "multi-user non-concurrent unsatisfied");
            return ERR_CROSS_USER;
        }
    }

    if (flag & AbilityRuntime::GetInsightIntentFlag::GET_FULL_INSIGHT_INTENT) {
        std::vector<ExtractInsightIntentInfo> intentInfos;
        std::vector<InsightIntentInfo> configInfos;
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentInfoByName(
            bundleName, GetValidUserId(userId), intentInfos);
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetConfigInsightIntentInfoByName(
            bundleName, GetValidUserId(userId), configInfos);
        if (intentInfos.empty() && configInfos.empty()) {
            TAG_LOGD(AAFwkTag::INTENT, "InsightIntentInfos and configInsightIntentInfos empty");
            return ERR_OK;
        }
        TAG_LOGD(AAFwkTag::INTENT, "intentInfos size: %{public}zu", intentInfos.size());
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        for (auto &info : configInfos) {
            InsightIntentInfoForQuery intentInfoQuery;
            InsightIntentUtils::ConvertConfigInsightIntentInfo(info, intentInfoQuery, getEntity);
            infos.emplace_back(intentInfoQuery);
        }
        for (auto &info : intentInfos) {
            InsightIntentInfoForQuery intentInfoQuery;
            InsightIntentUtils::ConvertExtractInsightIntentInfo(info, intentInfoQuery, getEntity);
            infos.emplace_back(intentInfoQuery);
        }
    } else if (flag & AbilityRuntime::GetInsightIntentFlag::GET_SUMMARY_INSIGHT_INTENT) {
        std::vector<ExtractInsightIntentGenericInfo> genericInfos;
        std::vector<InsightIntentInfo> configInfos;
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetConfigInsightIntentInfoByName(
            bundleName, GetValidUserId(userId), configInfos);
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentGenericInfoByName(
            bundleName, GetValidUserId(userId), genericInfos);
        if (genericInfos.empty() && configInfos.empty()) {
            return ERR_OK;
        }
        TAG_LOGD(AAFwkTag::INTENT, "genericInfos size: %{public}zu", genericInfos.size());
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        for (auto &info : configInfos) {
             InsightIntentInfoForQuery intentInfoQuery;
             InsightIntentUtils::ConvertConfigInsightIntentInfo(info, intentInfoQuery, getEntity);
             infos.emplace_back(intentInfoQuery);
        }

        if (getEntity) {
            std::vector<ExtractInsightIntentInfo> intentInfos;
            DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentInfoByName(
                bundleName, GetValidUserId(userId), intentInfos);
            if (intentInfos.empty()) {
                TAG_LOGI(AAFwkTag::INTENT, "extractInsightIntentInfos empty");
                return ERR_OK;
            }
            for (auto &info : intentInfos) {
                InsightIntentInfoForQuery intentInfoQuery;
                InsightIntentUtils::ConvertExtractInsightIntentEntityInfo(info, intentInfoQuery);
                infos.emplace_back(intentInfoQuery);
            }
            return ERR_OK;
        }
        for (auto &info : genericInfos) {
            InsightIntentInfoForQuery intentInfoQuery;
            InsightIntentUtils::ConvertExtractInsightIntentGenericInfo(info, intentInfoQuery);
            infos.emplace_back(intentInfoQuery);
        }
    } else {
        TAG_LOGW(AAFwkTag::INTENT, "invalid flag: %{public}d", flag);
    }
    return ERR_OK;
}

int32_t AbilityManagerService::GetInsightIntentInfoByIntentName(
    AbilityRuntime::GetInsightIntentFlag flag,
    const std::string &bundleName,
    const std::string &moduleName,
    const std::string &intentName,
    InsightIntentInfoForQuery &info,
    int32_t userId)
{
    TAG_LOGI(AAFwkTag::INTENT, "GetInsightIntentInfoByIntentName");
    int32_t ret = DelayedSingleton<InsightIntentExecuteManager>::GetInstance()->CheckGetInsightIntenInfoPermission();
    if (ret != ERR_OK) {
        TAG_LOGD(AAFwkTag::INTENT, "not system app or permission denied");
        return ret;
    }

    if(IsCrossUserCall(userId)) {
        if (VerifyAccountPermission(userId) == CHECK_PERMISSION_FAILED) {
            TAG_LOGE(AAFwkTag::INTENT, "permission verification failed");
            return CHECK_PERMISSION_FAILED;
        }
        if (!JudgeMultiUserConcurrency(userId)) {
            TAG_LOGE(AAFwkTag::INTENT, "multi-user non-concurrent unsatisfied");
            return ERR_CROSS_USER;
        }
    }

    if (flag & AbilityRuntime::GetInsightIntentFlag::GET_FULL_INSIGHT_INTENT) {
        ExtractInsightIntentInfo intentInfo;
        InsightIntentInfo configIntentInfo;
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetConfigInsightIntentInfo(
            bundleName, moduleName, intentName, GetValidUserId(userId), configIntentInfo);
        InsightIntentUtils::ConvertConfigInsightIntentInfo(configIntentInfo, info, getEntity);

        if (info.bundleName.empty()) {
            DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentInfo(
                bundleName, moduleName, intentName, GetValidUserId(userId), intentInfo);
            InsightIntentUtils::ConvertExtractInsightIntentInfo(intentInfo, info, getEntity);
        }
    } else if (flag & AbilityRuntime::GetInsightIntentFlag::GET_SUMMARY_INSIGHT_INTENT) {
        bool getEntity = (flag & AbilityRuntime::GetInsightIntentFlag::GET_ENTITY_INFO);
        InsightIntentInfo configIntentInfo;
        DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetConfigInsightIntentInfo(
            bundleName, moduleName, intentName, GetValidUserId(userId), configIntentInfo);
        InsightIntentUtils::ConvertConfigInsightIntentInfo(configIntentInfo, info, getEntity);
        if (info.bundleName.empty()) {
            if (getEntity) {
                ExtractInsightIntentInfo intentInfo;
                DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentInfo(
                    bundleName, moduleName, intentName, GetValidUserId(userId), intentInfo);
                InsightIntentUtils::ConvertExtractInsightIntentEntityInfo(intentInfo, info);

                return ERR_OK;
            }

            ExtractInsightIntentGenericInfo genericInfo;
            DelayedSingleton<InsightIntentDbCache>::GetInstance()->GetInsightIntentGenericInfo(
                bundleName, moduleName, intentName, GetValidUserId(userId), genericInfo);
            InsightIntentUtils::ConvertExtractInsightIntentGenericInfo(genericInfo, info);
        }

    } else {
        TAG_LOGW(AAFwkTag::INTENT, "invalid flag: %{public}d", flag);
    }
    return ERR_OK;
}

bool AbilityManagerService::IsCrossUserCall(int32_t userId) const
{
    if (userId == INVALID_USER_ID || userId == U0_USER_ID || userId == U1_USER_ID) {
        return false;
    }
    int32_t callerUser = IPCSkeleton::GetCallingUid() / BASE_USER_RANGE;
    if (((callerUser == U0_USER_ID || callerUser == U1_USER_ID) &&
        UserController::GetInstance().IsForegroundUser(userId)) || callerUser == userId) {
        return false;
    }
    return true;
}

int32_t AbilityManagerService::RestartSelfAtomicService(sptr<IRemoteObject> callerToken)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "RestartSelfAtomicService");
    auto abilityRecord = Token::GetAbilityRecordByToken(callerToken);
    CHECK_POINTER_AND_RETURN(abilityRecord, ERR_INVALID_VALUE);

    if (abilityRecord->GetApplicationInfo().bundleType != AppExecFwk::BundleType::ATOMIC_SERVICE) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not atomic service");
        return ERR_CALLER_NOT_ATOMIC_SERVICE;
    }

    auto callerPid = IPCSkeleton::GetCallingPid();
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByPid(callerPid, processInfo);
    int32_t callerUid = IPCSkeleton::GetCallingUid();
    int32_t userId = callerUid / BASE_USER_RANGE;
    if (!processInfo.isFocused && !processInfo.isAbilityForegrounding) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "restartApp, is not foreground");
        return AAFwk::NOT_TOP_ABILITY;
    }

    RestartAppKeyType key(processInfo.instanceKey, callerUid);
    int64_t now = time(nullptr);
    if (RestartAppManager::GetInstance().IsRestartAppFrequent(key, now)) {
        return AAFwk::ERR_RESTART_APP_FREQUENT;
    }

    SignRestartAppFlagParam param =
        { userId, callerUid, processInfo.instanceKey, processInfo.appMode, false, true };
    auto result = SignRestartAppFlag(param);
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "signRestartAppFlag error: %{public}d", result);
        return result;
    }

    auto want = abilityRecord->GetWant();
    std::string startTime = std::to_string(now);
    want.SetParam(Want::PARAM_RESV_START_TIME, startTime);
    want.AddFlags(Want::FLAG_INSTALL_ON_DEMAND);
    StartAbilityWrapParam startAbilityParam = {
        .want = want,
        .userId = userId,
    };
    result = IN_PROCESS_CALL(StartAbilityByFreeInstall(startAbilityParam));
    if (result != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "StartAbilityByFreeInstall failed:%{public}d", result);
        return result;
    }
    RestartAppManager::GetInstance().AddRestartAppHistory(key, now);
    return result;
}

int32_t AbilityManagerService::UpdateKioskApplicationList(const std::vector<std::string> &appList)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "request UpdateKioskApplicationList");
    return KioskManager::GetInstance().UpdateKioskApplicationList(appList);
}

int32_t AbilityManagerService::EnterKioskMode(sptr<IRemoteObject> callerToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "request EnterKioskMode");
    auto record = Token::GetAbilityRecordByToken(callerToken);
    if (!record) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "record null");
        return INVALID_PARAMETERS_ERR;
    }
    if (!JudgeSelfCalled(record)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self call");
        return CHECK_PERMISSION_FAILED;
    }
    return KioskManager::GetInstance().EnterKioskMode(callerToken);
}

int32_t AbilityManagerService::ExitKioskMode(sptr<IRemoteObject> callerToken)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "request ExitKioskMode");
    auto record = Token::GetAbilityRecordByToken(callerToken);
    if (!record) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "record null");
        return INVALID_PARAMETERS_ERR;
    }
    if (!JudgeSelfCalled(record)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self call");
        return CHECK_PERMISSION_FAILED;
    }
    return KioskManager::GetInstance().ExitKioskMode(callerToken, false);
}

int32_t AbilityManagerService::GetKioskStatus(KioskStatus &kioskStatus)
{
    TAG_LOGD(AAFwkTag::ABILITYMGR, "request GetKioskStatus");
    return KioskManager::GetInstance().GetKioskStatus(kioskStatus);
}

std::shared_ptr<AbilityInterceptorExecuter> AbilityManagerService::GetAbilityInterceptorExecuter()
{
    return interceptorExecuter_;
}

int32_t AbilityManagerService::RegisterSAInterceptor(sptr<AbilityRuntime::ISAInterceptor> interceptor)
{
    TAG_LOGI(AAFwkTag::ABILITYMGR, "call RegisterSaInterceptor, callingPid:%{public}d", IPCSkeleton::GetCallingPid());
    if (IPCSkeleton::GetCallingUid() != PENG_LAI_UID) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "no permission call");
        return CHECK_PERMISSION_FAILED;
    }

    return SAInterceptorManager::GetInstance().AddSAInterceptor(interceptor);
}

bool AbilityManagerService::HandleExecuteSAInterceptor(const Want &want, sptr<IRemoteObject> callerToken,
    AbilityRequest &abilityRequest, int32_t &result)
{
    if (SAInterceptorManager::GetInstance().SAInterceptorListIsEmpty()) {
        return true;
    }
    Rule rule;
    auto dialogSessionId = DialogSessionManager::GetInstance().GenerateDialogSessionId();
    auto params = SAInterceptorManager::GetInstance().GenerateSAInterceptorParams(want, callerToken,
        abilityRequest.abilityInfo, dialogSessionId);
    auto ret = SAInterceptorManager::GetInstance().ExecuteSAInterceptor(params, rule);

    if (ret != ERR_OK || rule.type == RuleType::NOT_ALLOW) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "sa interceptor OnCheckStarting failed");
        result = static_cast<int32_t>(ERROR_SA_INTERCEPTOR_START_FAILED);
        return false;
    }

    if (rule.type == RuleType::USER_SELECTION) {
        TAG_LOGW(AAFwkTag::ABILITYMGR, "sa interceptor OnCheckStarting failed, set dialog caller info");
        DialogSessionManager::GetInstance().OnlySetDialogCallerInfo(abilityRequest, abilityRequest.userId,
            SelectorType::INTERCEPTOR_SELECTOR, dialogSessionId, false);
        result = ERR_OK;
        return false;
    }

    return true;
}

int32_t AbilityManagerService::HandleExtensionAbility(sptr<IAbilityConnection> connect,
        std::function<int32_t(std::shared_ptr<AbilityConnectManager>, sptr<IAbilityConnection>)> func)
{
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    auto commonManagers = GetCommonExtensionManagers();
    for (auto &item : commonManagers) {
        auto userId = item.first;
        if (HandleExtensionConnectionByUserId(connect, userId, func) == ERR_OK) {
            return ERR_OK;
        }
    }
    return CONNECT_MAMAGER_NOT_FIND_BY_USERID;
}

int AbilityManagerService::SuspendExtensionAbility(sptr<IAbilityConnection> connect)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sa call");
        return CHECK_PERMISSION_FAILED;
    }
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "Suspend extension ability begin.");
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    auto err = HandleExtensionAbility(connect,
        [](std::shared_ptr<AbilityConnectManager> connectManager, sptr<IAbilityConnection> connect) {
            return connectManager->SuspendExtensionAbilityLocked(connect);
        });
    if (err == ERR_OK) {
        return ERR_OK;
    }

    TAG_LOGE(AAFwkTag::SERVICE_EXT, "Suspend extension ability error %{public}d", err);
    return err;
}

int AbilityManagerService::ResumeExtensionAbility(sptr<IAbilityConnection> connect)
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (!AAFwk::PermissionVerification::GetInstance()->IsSACall()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not sa call");
        return CHECK_PERMISSION_FAILED;
    }
    TAG_LOGI(AAFwkTag::SERVICE_EXT, "Resume extension ability begin.");
    CHECK_POINTER_AND_RETURN(connect, ERR_INVALID_VALUE);
    auto err = HandleExtensionAbility(connect,
        [](std::shared_ptr<AbilityConnectManager> connectManager, sptr<IAbilityConnection> connect) {
            return connectManager->ResumeExtensionAbilityLocked(connect);
        });
    if (err == ERR_OK) {
        return ERR_OK;
    }

    TAG_LOGE(AAFwkTag::SERVICE_EXT, "Resume extension ability error %{public}d", err);
    return err;
}

int32_t AbilityManagerService::SetAppServiceExtensionKeepAlive(const std::string &bundleName, bool flag)
{
    return KeepAliveProcessManager::GetInstance().SetAppServiceExtensionKeepAlive(
        bundleName, flag, false, false);
}

int32_t AbilityManagerService::QueryKeepAliveAppServiceExtensions(std::vector<KeepAliveInfo> &list)
{
    return KeepAliveProcessManager::GetInstance().QueryKeepAliveAppServiceExtensions(list, false);
}

int32_t AbilityManagerService::SetOnNewWantSkipScenarios(sptr<IRemoteObject> callerToken, int32_t scenarios)
{
    auto record = Token::GetAbilityRecordByToken(callerToken);
    if (record == nullptr) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "The toke from context is invalid");
        return ERR_INVALID_CONTEXT;
    }
    if (!JudgeSelfCalled(record)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "invalid callerToken");
        return ERR_INVALID_CALLER;
    }
    record->SetOnNewWantSkipScenarios(scenarios);
    return ERR_OK;
}

int32_t AbilityManagerService::NotifyStartupExceptionBySCB(int32_t requestId)
{
    if (!IsCallerSceneBoard()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "permission deny");
        return ERR_PERMISSION_DENIED;
    }
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN_LOG(uiAbilityManager, ERR_NULL_OBJECT, "uiAbilityLifecycleManager nullptr");
    std::string reason = "SCB intercepted this startup attempt";
    return uiAbilityManager->NotifyStartupExceptionBySCB(requestId, reason);
}

int32_t AbilityManagerService::PreloadApplication(const std::string &bundleName, int32_t userId, int32_t appIndex)
{
    return PreloadManagerService::GetInstance().PreloadApplication(bundleName, userId, appIndex);
}

int32_t AbilityManagerService::ProcessUdmfKey(
    const Want &want, uint32_t targetTokenId, AppExecFwk::ExtensionAbilityType extensionType)
{
    std::string key = want.GetStringParam(UD_KEY);
    if (UIExtensionWrapper::IsProcessUdkeyExtension(extensionType) && !key.empty()){
        return AbilityRuntime::UdmfUtils::ProcessUdmfKey(key, targetTokenId);
    }
    return ERR_OK;
}

ErrCode AbilityManagerService::IsUIAbilityAlreadyExist(const Want &want, const std::string &specifiedFlag,
    int32_t appIndex, const std::string &instanceKey, AppExecFwk::LaunchMode launchMode)
{
    auto uiAbilityManager = GetUIAbilityManagerByUid(IPCSkeleton::GetCallingUid());
    CHECK_POINTER_AND_RETURN(uiAbilityManager, ERR_INVALID_VALUE);
    return uiAbilityManager->IsUIAbilityAlreadyExist(want, specifiedFlag, appIndex, instanceKey, launchMode);
}

bool AbilityManagerService::IsAppCloneOrMultiInstance(const Want &want, const std::shared_ptr<AbilityRecord> callerRecord,
    int32_t &targetAppIndex, const std::string &callerInstanceKey)
{
    if (callerRecord == nullptr) {
        return false;
    }
    int32_t callerIndex = callerRecord->GetAppIndex();
    if (targetAppIndex == -1) {
        targetAppIndex = callerIndex;
    }
    if (callerIndex != targetAppIndex) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "app clone scene");
        return true;
    }
    auto instanceKey = want.GetStringParam(Want::APP_INSTANCE_KEY);
    auto isCreating = want.GetBoolParam(Want::CREATE_APP_INSTANCE_KEY, false);
    if ((!instanceKey.empty() && instanceKey != callerInstanceKey) || isCreating) {
        TAG_LOGD(AAFwkTag::ABILITYMGR, "multi instance scene");
        return true;
    }
    return false;
}

ErrCode AbilityManagerService::StartSelfUIAbilityInCurrentProcess(const Want &want, const std::string &specifiedFlag,
    const AAFwk::StartOptions &startOptions, bool hasOptions, sptr<IRemoteObject> callerToken)
{
    if (!AppUtils::GetInstance().IsStartUIAbilityInCurrentProcess()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "device not supported");
        return ERR_CAPABILITY_NOT_SUPPORT;
    }
    auto callerRecord = Token::GetAbilityRecordByToken(callerToken);
    if (callerRecord == nullptr || !JudgeSelfCalled(callerRecord)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not self call");
        return ERR_INVALID_VALUE;
    }

    std::string targetBundleName = want.GetBundle();
    std::string targetAbilityName = want.GetElement().GetAbilityName();
    if (targetBundleName.empty() || targetAbilityName.empty()) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "implicit start not allowed");
        return START_UI_ABILITIES_NOT_SUPPORT_IMPLICIT_START;
    }
    auto callingPid = IPCSkeleton::GetCallingPid();
    AppExecFwk::RunningProcessInfo processInfo;
    DelayedSingleton<AppScheduler>::GetInstance()->GetRunningProcessInfoByChildProcessPid(callingPid, processInfo);
    CHECK_TRUE_RETURN_RET(processInfo.bundleNames.empty(), INNER_ERR, "failed to get by child process pid");
    auto iter = std::find(processInfo.bundleNames.begin(), processInfo.bundleNames.end(), targetBundleName);
    CHECK_TRUE_RETURN_RET(iter == processInfo.bundleNames.end(), ERROR_UIABILITY_NOT_BELONG_TO_CALLER,
        "The UIAbility not belog to caller");
    int32_t appIndex = want.GetIntParam(AAFwk::Want::PARAM_APP_CLONE_INDEX_KEY, -1);
    if (IsAppCloneOrMultiInstance(want, callerRecord, appIndex, processInfo.instanceKey)) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "not support app clone and multi instance");
        return ERROR_UIABILITY_NOT_BELONG_TO_CALLER;
    }
    auto bundleMgrHelper = AbilityUtil::GetBundleManagerHelper();
    CHECK_POINTER_AND_RETURN(bundleMgrHelper, INNER_ERR);
    AppExecFwk::AbilityInfo abilityInfo;
    auto callerUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    CHECK_TRUE_RETURN_RET(IN_PROCESS_CALL(bundleMgrHelper->QueryCloneAbilityInfo(want.GetElement(),
        AppExecFwk::AbilityInfoFlag::GET_ABILITY_INFO_WITH_APPLICATION, appIndex, abilityInfo, callerUserId)) != ERR_OK,
        TARGET_BUNDLE_NOT_EXIST, "The specified ability not exist");

    CHECK_TRUE_RETURN_RET(abilityInfo.type != AppExecFwk::AbilityType::PAGE,
        TARGET_BUNDLE_NOT_EXIST, "not UIAbility");
    auto ret = IsUIAbilityAlreadyExist(want, specifiedFlag, appIndex, processInfo.instanceKey, abilityInfo.launchMode);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::ABILITYMGR, "UIAbility already exist");
        return ret;
    }

    CHECK_TRUE_RETURN_RET(processInfo.state_ != AppExecFwk::AppProcessState::APP_STATE_FOREGROUND,
        NOT_TOP_ABILITY, "caller not foreground");

    auto useStartOptions = startOptions;
    useStartOptions.SetCurrentProcessName(processInfo.processName_);
    if (useStartOptions.processOptions == nullptr) {
        useStartOptions.processOptions = std::make_shared<ProcessOptions>();
    }
    useStartOptions.processOptions->selfPid = callingPid;
    auto useWant = want;
    if (abilityInfo.launchMode == AppExecFwk::LaunchMode::SPECIFIED) {
        useWant.SetParam(KEY_SPECIFIED_FLAG, specifiedFlag);
    }
    return StartAbility(useWant, useStartOptions, callerToken);
}

int32_t AbilityManagerService::ClearPreloadedUIExtensionAbility(int32_t extensionAbilityId, int32_t userId)
{
    TAG_LOGD(AAFwkTag::UI_EXT, "ClearPreloadedUIExtensionAbility called, id: %{public}d, userId: %{public}d",
        extensionAbilityId, userId);
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
        return ERR_PERMISSION_DENIED;
    }
    int32_t validUserId = GetValidUserId(userId);
    AbilityRequest abilityRequest;
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);    
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "null connectManager");
        return ERR_INVALID_VALUE;
    }
    int32_t ret = connectManager->UnPreloadUIExtensionAbilityLocked(extensionAbilityId);
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT, "UnPreloadUIExtensionAbilityLocked failed, id: %{public}d, ret: %{public}d",
            extensionAbilityId, ret);
        return ret;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::ClearPreloadedUIExtensionAbilities(int32_t userId)
{
    TAG_LOGD(AAFwkTag::UI_EXT,
        "ClearPreloadedUIExtensionAbilities called, userId: %{public}d", userId);
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
        return ERR_PERMISSION_DENIED;
    }
    int32_t validUserId = GetValidUserId(userId);
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "null connectManager");
        return ERR_INVALID_VALUE;
    }
    int32_t ret = connectManager->ClearAllPreloadUIExtensionAbilityLocked();
    if (ret != ERR_OK) {
        TAG_LOGE(AAFwkTag::UI_EXT,
            "ClearAllPreloadUIExtensionAbilityLocked failed, ret: %{public}d", ret);
        return ret;
    }
    return ERR_OK;
}

int32_t AbilityManagerService::RegisterPreloadUIExtensionHostClient(const sptr<IRemoteObject> &callerToken)
{
    TAG_LOGD(AAFwkTag::UI_EXT, "RegisterPreloadUIExtensionHostClient called");
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
        return ERR_PERMISSION_DENIED;
    }
    if (callerToken == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "null callerToken");
        return ERR_INVALID_VALUE;
    }
    int32_t validUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "null connectManager");
        return ERR_INVALID_VALUE;
    }
    return connectManager->RegisterPreloadUIExtensionHostClient(callerToken);
}

int32_t AbilityManagerService::UnRegisterPreloadUIExtensionHostClient(int32_t callerPid)
{
    TAG_LOGD(AAFwkTag::UI_EXT, "UnRegisterPreloadUIExtensionHostClient called");
    CHECK_CALLER_IS_SYSTEM_APP;
    if (!PermissionVerification::GetInstance()->VerifyCallingPermission(
        PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY)) {
        TAG_LOGE(AAFwkTag::UI_EXT, "permission %{public}s verification failed",
            PermissionConstants::PERMISSION_PRELOAD_UI_EXTENSION_ABILITY);
        return ERR_PERMISSION_DENIED;
    }
    int32_t validUserId = AbilityRuntime::UserController::GetInstance().GetCallerUserId();
    auto connectManager = GetUIExtensionAbilityManagerByUserId(validUserId);
    if (connectManager == nullptr) {
        TAG_LOGE(AAFwkTag::UI_EXT, "null connectManager");
        return ERR_INVALID_VALUE;
    }
    return connectManager->UnRegisterPreloadUIExtensionHostClient(callerPid);
}
}  // namespace AAFwk
}  // namespace OHOS
