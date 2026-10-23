/*
 * Copyright (c) 2022-2025 Huawei Device Co., Ltd.
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

#ifndef OHOS_ABILITY_RUNTIME_ABILITY_BUSINESS_ERROR_H
#define OHOS_ABILITY_RUNTIME_ABILITY_BUSINESS_ERROR_H

#include <string>

namespace OHOS {
namespace AbilityRuntime {
enum class AbilityErrorCode {
    // success
    ERROR_OK = 0,

    // no such permission.
    ERROR_CODE_PERMISSION_DENIED = 201,

    // non-system-app use system-api.
    ERROR_CODE_NOT_SYSTEM_APP = 202,

    // invalid param.
    ERROR_CODE_INVALID_PARAM = 401,

    // capability not support.
    ERROR_CODE_CAPABILITY_NOT_SUPPORT = 801,

    // common inner error.
    ERROR_CODE_INNER = 16000050,

    // can not find target ability.
    ERROR_CODE_RESOLVE_ABILITY = 16000001,

    // ability type is wrong.
    ERROR_CODE_INVALID_ABILITY_TYPE = 16000002,

    // id does not exist.
    ERROR_CODE_INVALID_ID = 16000003,

    // no start invisible ability permission.
    ERROR_CODE_NO_INVISIBLE_PERMISSION = 16000004,

    // check static permission failed.
    ERROR_CODE_STATIC_CFG_PERMISSION = 16000005,

    // no permission to cross user.
    ERROR_CODE_CROSS_USER = 16000006,

    // Service busy.Try again later.
    ERROR_CODE_SERVICE_BUSY = 16000007,

    // crowdtest app expiration.
    ERROR_CODE_CROWDTEST_EXPIRED = 16000008,

    // wukong mode.
    ERROR_CODE_WUKONG_MODE = 16000009,

    // not allowed for continuation flag.
    ERROR_CODE_CONTINUATION_FLAG = 16000010,

    // context is invalid.
    ERROR_CODE_INVALID_CONTEXT = 16000011,

    // application is controlled.
    ERROR_CODE_CONTROLLED = 16000012,

    // edm application is controlled.
    ERROR_CODE_EDM_CONTROLLED = 16000013,

    // ability wait start.
    ERROR_START_ABILITY_WAITTING = 16000017,

    // jump to other applicaiton is not enable after API12.
    ERROR_CODE_NOT_SUPPORT_CROSS_APP_START = 16000018,

    // implicit start can not match any component.
    ERROR_CODE_CANNOT_MATCH_ANY_COMPONENT = 16000019,
    
    // the context is not ability context.
    ERR_ABILITY_RUNTIME_EXTERNAL_NOT_ABILITY_CONTEXT = 16000020,

    // free install network abnormal.
    ERROR_CODE_NETWORK_ABNORMAL = 16000051,

    // not support free install.
    ERROR_CODE_NOT_SUPPORT_FREE_INSTALL = 16000052,

    // not top ability, not enable to free install.
    ERROR_CODE_NOT_TOP_ABILITY = 16000053,

    // too busy for free install.
    ERROR_CODE_FREE_INSTALL_TOO_BUSY = 16000054,

    // free install timeout.
    ERROR_CODE_FREE_INSTALL_TIMEOUT = 16000055,

    // free install other ability.
    ERROR_CODE_FREE_INSTALL_OTHERS = 16000056,

    // Cross-device installation-free is not supported.
    ERROR_CODE_FREE_INSTALL_CROSS_DEVICE = 16000057,

    // Uri flag invalid.
    ERROR_CODE_INVALID_URI_FLAG = 16000058,

    // Uri type invalid, only support file uri currently.
    ERROR_CODE_INVALID_URI_TYPE = 16000059,

    // Sandbox application can not grant URI permission.
    ERROR_CODE_GRANT_URI_PERMISSION = 16000060,

    // Operation not supported.
    ERROR_CODE_OPERATION_NOT_SUPPORTED = 16000061,

    // The number of child process exceeds upper bound.
    ERROR_CODE_CHILD_PROCESS_NUMBER_EXCEEDS_UPPER_BOUND = 16000062,

    // The target to restart does not belong to the current app or is not a UIAbility.
    ERROR_CODE_RESTART_APP_INCORRECT_ABILITY = 16000063,

    // Restart too frequently. Try again at least 3s later.
    ERROR_CODE_RESTART_APP_FREQUENT = 16000064,

    // ability not foreground.
    ERROR_CODE_ABILITY_NOT_FOREGROUND = 16000065,

    // wukong mode, can not move to foreground or background.
    ERROR_CODE_WUKONG_MODE_CANT_MOVE_STATE = 16000066,

    // Start options check failed.
    ERROR_START_OPTIONS_CHECK_FAILED = 16000067,

    // Ability already running.
    ERROR_ABILITY_ALREADY_RUNNING = 16000068,

    // extension start third party app has been controlled.
    ERROR_CODE_EXTENSION_START_THIRD_PARTY_APP_CONTROLLED = 16000069,

    // extension start service has been controlled.
    ERROR_CODE_EXTENSION_START_SERVICE_CONTROLLED = 16000070,

    // app is not Clone.
    ERROR_NOT_APP_CLONE = 16000071,

    // not support Clone app.
    ERROR_CODE_MULTI_APP_NOT_SUPPORTED = 16000072,

    // app clone index does not exist.
    ERROR_APP_CLONE_INDEX_INVALID = 16000073,

    // Caller does not exists.
    ERROR_CODE_CALLER_NOT_EXIST = 16000074,

    // Not support back to caller.
    ERROR_CODE_NOT_SUPPROT_BACK_TO_CALLER = 16000075,

    // invalid app instance key.
    ERROR_CODE_INVALID_APP_INSTANCE_KEY = 16000076,

    // upper limit.
    ERROR_CODE_UPPER_LIMIT = 16000077,

    // The multi-instance is not supported.
    ERROR_MULTI_INSTANCE_NOT_SUPPORTED = 16000078,

    // APP_INSTANCE_KEY cannot be specified.
    ERROR_CODE_APP_INSTANCE_KEY_NOT_SUPPORT = 16000079,

    // Not support to create a new instance.
    ERROR_CODE_CREATE_NEW_INSTANCE_NOT_SUPPORT = 16000080,

    // Target application not found.
    ERROR_CODE_GET_APPLICATION_INFO_FAILED = 16000081,

    // UIAbility is in starting state.
    ERROR_CODE_UI_ABILITY_IS_STARTING = 16000082,

    // extension can not start the ability due to extension control.
    ERROR_CODE_EXTENSION_START_ABILITY_CONTROLLED = 16000083,

    // Only allow DelegatorAbility to call the method once.
    ERROR_CODE_NOT_HOOK = 16000084,

    // The interaction process between Ability and the Window encountered an error.
    ERROR_CODE_FROM_WINDOW = 16000085,

    ERR_CODE_GET_FILE_URIS_BY_KEY_FAILED = 16000091,

    ERR_CODE_NO_PERMISSION_GRANT_URI = 16000092,

    ERR_CODE_INVALID_CALLER_TOKENID = 16000093,

    ERR_CODE_INVALID_TARGET_TOKENID = 16000094,

    // the target not in app identifier allow list.
    ERROR_CODE_TARGET_NOT_IN_APP_IDENTIFIER_ALLOW_LIST = 16000200,

    // the target has not been started yet.
    ERROR_CODE_TARGET_NOT_STARTED = 16000201,

    // The context is not UIAbilityContext.
    ERROR_CODE_NOT_UI_ABILITY_CONTEXT = 16000086,

    // The caller is not an atomic service.
    ERROR_CODE_CALLER_NOT_ATOMIC_SERVICE = 16000090,

    // invalid caller.
    ERROR_CODE_INVALID_CALLER = 16200001,

    // The caller is not main thread
    ERROR_CODE_MAIN_THREAD = 16000205,

    // Setting permissions for resident processes
    ERROR_CODE_NO_RESIDENT_PERMISSION = 16200006,

    // no such mission id.
    ERROR_CODE_NO_MISSION_ID = 16300001,

    // no such mission listener.
    ERROR_CODE_NO_MISSION_LISTENER = 16300002,

    // not self application.
    ERROR_NOT_SELF_APPLICATION = 16300003,

    // observer not found.
    ERROR_CODE_OBSERVER_NOT_FOUND = 16300004,

    // target bundle not exist.
    ERROR_CODE_TARGET_BUNDLE_NOT_EXIST = 16300005,

    // target free install task does not exist.
    ERROR_CODE_FREE_INSTALL_TASK_NOT_EXIST = 16300007,

    // target bundle has no main ability.
    ERROR_CODE_NO_MAIN_ABILITY = 16300008,

    // target application has no status-bar ability.
    ERROR_CODE_NO_STATUS_BAR_ABILITY = 16300009,

    // target application is not attached to a status bar.
    ERROR_CODE_NOT_ATTACHED_TO_STATUS_BAR = 16300010,

    // invalid main element type
    ERROR_CODE_INVALID_MAIN_ELEMENT_TYPE = 16000202,

    // can not change keep alive status
    ERROR_CODE_CHANGE_KEEP_ALIVE = 16000203,

    ERROR_CODE_KIOSK_MODE_NOT_IN_WHITELIST = 16000110,

    ERROR_CODE_ALREADY_IN_KIOSK_MODE = 16000111,

    ERROR_CODE_NOT_IN_KIOSK_MODE = 16000112,

    ERROR_CODE_APP_NOT_IN_FOCUS = 16000113,
    
    ERROR_CODE_NOT_ISOLATION_PROCESS = 16000115,

    ERROR_CODE_ALREADY_MASTER_PROCESS = 16000116,

    ERROR_CODE_NOT_CANDIDATE_MASTER_PROCESS = 16000117,

    ERROR_CODE_NOT_MASTER_PROCESS = 16000118,

    ERROR_CODE_NOT_ON_NEW_PROCESS_REQUEST_DONE = 16000119,

    ERROR_CODE_EXCEEDS_WANT_LIST_MAXIMUM_SIZE = 16000120,

    ERROR_CODE_TARGET_TYPE_NOT_UI_ABILITY = 16000121,

    ERROR_CODE_TARGET_BLOCKED_BY_SYSTEM_MODULE = 16000122,

    ERROR_CODE_NOT_SUPPORT_IMPLICIT_START = 16000123,

    ERROR_CODE_NOT_SUPPORT_START_REMOTE_UI_ABILITY = 16000124,

    ERROR_CODE_NOT_SUPPORT_START_PLUGIN_UI_ABILITY = 16000125,

    ERROR_CODE_NOT_SUPPORT_START_DLP_FILES = 16000126,

    ERROR_CODE_UIABILITY_NOT_BELONG_TO_CALLER = 16000130,

    ERROR_CODE_UIABILITY_IS_ALREADY_EXIST = 16000131,

    ERROR_CODE_MAIN_WINDOW_NOT_EXIST = 16000135,

    ERROR_CODE_SELF_REDIRECTION_DISALLOWED = 16000136,

    // target bundle is not in u1
    ERROR_CODE_NO_U1 = 16000204,

    ERROR_CODE_BUNDLE_NAME_INVALID = 18500001,
};

std::string GetErrorMsg(const AbilityErrorCode& errCode);
std::string GetNoPermissionErrorMsg(const std::string& permission);
AbilityErrorCode GetJsErrorCodeByNativeError(int32_t errCode);
}  // namespace AbilityRuntime
}  // namespace OHOS
#endif
