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

#include "permission_verification.h"

#include "ability_manager_errors.h"
#include "accesstoken_kit.h"
#include "hilog_tag_wrapper.h"
#include "permission_constants.h"
#include "server_constant.h"
#include "support_system_ability_permission.h"
#include "tokenid_kit.h"
#include "hitrace_meter.h"
#include "hilog_tag_wrapper.h"
#include "record_cost_time_util.h"

namespace OHOS {
namespace AAFwk {
const std::string DLP_PARAMS_SECURITY_FLAG = "ohos.dlp.params.securityFlag";
namespace {
const int32_t SHELL_START_EXTENSION_FLOOR = 0; // FORM
const int32_t SHELL_START_EXTENSION_CEIL = 21; // EMBEDDED_UI
const int32_t TOKEN_ID_BIT_SIZE = 32;
const std::string FOUNDATION_PROCESS_NAME = "foundation";
const std::set<std::string> OBSERVER_NATIVE_CALLER = {
    "memmgrservice",
    "resource_schedule_service",
};
}
bool PermissionVerification::VerifyPermissionByTokenId(const int &tokenId, const std::string &permissionName) const
{
    TAG_LOGD(AAFwkTag::DEFAULT, "permission %{public}s", permissionName.c_str());
    int32_t ret = Security::AccessToken::AccessTokenKit::VerifyAccessToken(tokenId, permissionName, false);
    if (ret != Security::AccessToken::PermissionState::PERMISSION_GRANTED) {
        TAG_LOGE(AAFwkTag::DEFAULT, "%{public}s: PERMISSION_DENIED", permissionName.c_str());
        return false;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "verify token success");
    return true;
}

bool PermissionVerification::VerifyCallingPermission(
    const std::string &permissionName, const uint32_t specifyTokenId) const
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    RecordCostTimeUtil timeRecord("VerifyCallingPermission");
    TAG_LOGD(AAFwkTag::DEFAULT, "permission %{public}s, specifyTokenId: %{public}u",
        permissionName.c_str(), specifyTokenId);
    auto callerToken = specifyTokenId == 0 ? GetCallingTokenID() : specifyTokenId;
    TAG_LOGD(AAFwkTag::DEFAULT, "Token: %{public}u", callerToken);
    int32_t ret = Security::AccessToken::AccessTokenKit::VerifyAccessToken(callerToken, permissionName, false);
    if (ret != Security::AccessToken::PermissionState::PERMISSION_GRANTED) {
        TAG_LOGW(AAFwkTag::DEFAULT, "%{public}s: PERMISSION_DENIED", permissionName.c_str());
        return false;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "verify Token success");
    return true;
}

bool PermissionVerification::IsSACall() const
{
    auto callerToken = GetCallingTokenID();
    return IsSACallByTokenId(callerToken);
}

bool PermissionVerification::IsSACallByTokenId(uint32_t callerTokenId) const
{
    TAG_LOGD(AAFwkTag::DEFAULT, "called");
    if (callerTokenId == 0) {
        callerTokenId = GetCallingTokenID();
    }
    auto tokenType = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(callerTokenId);
    if (tokenType == Security::AccessToken::ATokenTypeEnum::TOKEN_NATIVE) {
        TAG_LOGD(AAFwkTag::DEFAULT, "verify success");
        return true;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "Not SA called");
    return false;
}

bool PermissionVerification::IsShellCall() const
{
    auto callerToken = GetCallingTokenID();
    return IsShellCallByTokenId(callerToken);
}

bool PermissionVerification::IsShellCallByTokenId(uint32_t callerTokenId) const
{
    TAG_LOGD(AAFwkTag::DEFAULT, "called");
    if (callerTokenId == 0) {
        callerTokenId = GetCallingTokenID();
    }
    auto tokenType = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(callerTokenId);
    if (tokenType == Security::AccessToken::ATokenTypeEnum::TOKEN_SHELL) {
        TAG_LOGD(AAFwkTag::DEFAULT, "verify success");
        return true;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "Not shell called");
    return false;
}

bool PermissionVerification::CheckSpecificSystemAbilityAccessPermission(const std::string &processName) const
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    TAG_LOGD(AAFwkTag::DEFAULT, "called");
    if (!IsSACall()) {
        TAG_LOGE(AAFwkTag::DEFAULT, "verify fail");
        return false;
    }
    auto callerToken = GetCallingTokenID();
    Security::AccessToken::NativeTokenInfo nativeTokenInfo;
    int32_t result = Security::AccessToken::AccessTokenKit::GetNativeTokenInfo(callerToken, nativeTokenInfo);
    if (result != ERR_OK || nativeTokenInfo.processName != processName) {
        TAG_LOGE(AAFwkTag::DEFAULT, "check process fail");
        return false;
    }
    return true;
}

bool PermissionVerification::CheckObserverCallerPermission() const
{
    TAG_LOGD(AAFwkTag::DEFAULT, "called");
    if (!IsSACall()) {
        TAG_LOGE(AAFwkTag::DEFAULT, "tokenType not native");
        return false;
    }
    auto callerToken = GetCallingTokenID();
    Security::AccessToken::NativeTokenInfo nativeTokenInfo;
    int32_t result = Security::AccessToken::AccessTokenKit::GetNativeTokenInfo(callerToken, nativeTokenInfo);
    if (result != ERR_OK ||
        OBSERVER_NATIVE_CALLER.find(nativeTokenInfo.processName) == OBSERVER_NATIVE_CALLER.end()) {
        TAG_LOGE(AAFwkTag::DEFAULT, "check token fail");
        return false;
    }
    return true;
}

bool PermissionVerification::VerifyRunningInfoPerm() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_GET_RUNNING_INFO)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    return false;
}

bool PermissionVerification::VerifyCustomSandbox(uint32_t accessTokenId) const
{
    if (VerifyPermissionByTokenId(accessTokenId, PermissionConstants::PERMISSION_CUSTOM_SANDBOX)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    return false;
}

bool PermissionVerification::VerifyControllerPerm() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_SET_ABILITY_CONTROLLER)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    return false;
}

bool PermissionVerification::VerifyDlpPermission(Want &want) const
{
    if (want.GetIntParam(AbilityRuntime::ServerConstant::DLP_INDEX, 0) == 0) {
        want.RemoveParam(DLP_PARAMS_SECURITY_FLAG);
        return true;
    }

    if (VerifyCallingPermission(PermissionConstants::PERMISSION_ACCESS_DLP)) {
        return true;
    }
    return false;
}

int PermissionVerification::VerifyAccountPermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_INTERACT_ACROSS_LOCAL_ACCOUNTS)) {
        return ERR_OK;
    }
    return CHECK_PERMISSION_FAILED;
}

bool PermissionVerification::VerifyMissionPermission() const
{
    HITRACE_METER_NAME(HITRACE_TAG_ABILITY_MANAGER, __PRETTY_FUNCTION__);
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_MANAGE_MISSION)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    return false;
}

int PermissionVerification::VerifyAppStateObserverPermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_RUNNING_STATE_OBSERVER)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return ERR_OK;
    }
    return ERR_PERMISSION_DENIED;
}

int32_t PermissionVerification::VerifyUpdateConfigurationPerm() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_UPDATE_CONFIGURATION)) {
        TAG_LOGI(AAFwkTag::DEFAULT,
            "Permission %{public}s granted", PermissionConstants::PERMISSION_UPDATE_CONFIGURATION);
        return ERR_OK;
    }
    return ERR_PERMISSION_DENIED;
}

int32_t PermissionVerification::VerifyUpdateAPPConfigurationPerm() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_UPDATE_APP_CONFIGURATION)) {
        TAG_LOGI(AAFwkTag::DEFAULT,
            "Permission %{public}s granted", PermissionConstants::PERMISSION_UPDATE_APP_CONFIGURATION);
        return ERR_OK;
    }
    return ERR_PERMISSION_DENIED;
}

bool PermissionVerification::VerifyInstallBundlePermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_INSTALL_BUNDLE)) {
        TAG_LOGI(AAFwkTag::DEFAULT,
            "Permission %{public}s granted", PermissionConstants::PERMISSION_INSTALL_BUNDLE);
        return true;
    }
    return false;
}

bool PermissionVerification::VerifyGetBundleInfoPrivilegedPermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_GET_BUNDLE_INFO_PRIVILEGED)) {
        TAG_LOGI(AAFwkTag::DEFAULT,
            "Permission %{public}s granted", PermissionConstants::PERMISSION_GET_BUNDLE_INFO_PRIVILEGED);
        return true;
    }
    return false;
}

bool PermissionVerification::VerifyStartRecentAbilityPermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_START_RECENT_ABILITY)) {
        TAG_LOGI(AAFwkTag::DEFAULT,
            "Permission %{public}s granted", PermissionConstants::PERMISSION_START_RECENT_ABILITY);
        return true;
    }
    return VerifyMissionPermission();
}

int PermissionVerification::CheckCallDataAbilityPermission(const VerificationInfo &verificationInfo, bool isShell) const
{
    if ((verificationInfo.apiTargetVersion > API8 || isShell) &&
        !JudgeStartAbilityFromBackground(verificationInfo.isBackgroundCall)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller START_ABILITIES_FROM_BACKGROUND permission invalid");
        return CHECK_PERMISSION_FAILED;
    }
    if (!JudgeStartInvisibleAbility(verificationInfo.accessTokenId, verificationInfo.visible)) {
        TAG_LOGE(AAFwkTag::DEFAULT,
            "caller INVISIBLE permission invalid");
        return ABILITY_VISIBLE_FALSE_DENY_REQUEST;
    }
    if (!JudgeAssociatedWakeUp(verificationInfo.accessTokenId, verificationInfo.associatedWakeUp)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "associatedWakeUp false");
        return CHECK_PERMISSION_FAILED;
    }

    return ERR_OK;
}

int PermissionVerification::CheckCallServiceAbilityPermission(const VerificationInfo &verificationInfo,
    uint32_t specifyTokenId) const
{
    if (CheckSpecificSystemAbilityAccessPermission(FOUNDATION_PROCESS_NAME)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Allow fms to connect service ability");
        return ERR_OK;
    }
    if ((verificationInfo.apiTargetVersion > API8 || IsShellCallByTokenId(specifyTokenId)) &&
        !JudgeStartAbilityFromBackground(verificationInfo.isBackgroundCall)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller START_ABILITIES_FROM_BACKGROUND permission invalid");
        return CHECK_PERMISSION_FAILED;
    }
    if (!JudgeStartInvisibleAbility(verificationInfo.accessTokenId, verificationInfo.visible)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller INVISIBLE permission invalid");
        return ABILITY_VISIBLE_FALSE_DENY_REQUEST;
    }
    if (!JudgeAssociatedWakeUp(verificationInfo.accessTokenId, verificationInfo.associatedWakeUp)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "associatedWakeUp false");
        return CHECK_PERMISSION_FAILED;
    }

    return ERR_OK;
}

int PermissionVerification::CheckCallAbilityPermission(const VerificationInfo &verificationInfo,
    bool isCallByShortcut) const
{
    return JudgeInvisibleAndBackground(verificationInfo, isCallByShortcut);
}

int PermissionVerification::CheckCallServiceExtensionPermission(const VerificationInfo &verificationInfo) const
{
    return JudgeInvisibleAndBackground(verificationInfo);
}

int PermissionVerification::CheckStartByCallPermission(const VerificationInfo &verificationInfo) const
{
    if (IsCallFromSameAccessToken(verificationInfo.accessTokenId)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "StartAbilityByCall reject");
        return CHECK_PERMISSION_FAILED;
    }
    // Different APP call, check permissions
    if (!VerifyCallingPermission(PermissionConstants::PERMISSION_ABILITY_BACKGROUND_COMMUNICATION)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
        return CHECK_PERMISSION_FAILED;
    }
    if (!JudgeStartInvisibleAbility(verificationInfo.accessTokenId, verificationInfo.visible)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller INVISIBLE permission invalid");
        return ABILITY_VISIBLE_FALSE_DENY_REQUEST;
    }
    if (!JudgeStartAbilityFromBackground(verificationInfo.isBackgroundCall)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller START_ABILITIES_FROM_BACKGROUND permission invalid");
        return CHECK_PERMISSION_FAILED;
    }

    return ERR_OK;
}

unsigned int PermissionVerification::GetCallingTokenID() const
{
    auto callerToken = IPCSkeleton::GetCallingTokenID();
    TAG_LOGD(AAFwkTag::DEFAULT, "callerToken: %{private}u", callerToken);
    return callerToken;
}

bool PermissionVerification::JudgeStartInvisibleAbility(const uint32_t accessTokenId, const bool visible,
    const uint32_t specifyTokenId) const
{
    if (visible) {
        TAG_LOGD(AAFwkTag::DEFAULT, "visible:true");
        return true;
    }
    if (specifyTokenId > 0 && accessTokenId == specifyTokenId) {
        TAG_LOGD(AAFwkTag::DEFAULT, "accessTokenId equal specifyTokenId");
        return true;
    }
    if (IsCallFromSameAccessToken(accessTokenId)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "TargetAbility in same APP");
        return true;
    }
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_START_INVISIBLE_ABILITY, specifyTokenId)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Caller PASS");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "verification fail");
    return false;
}

bool PermissionVerification::JudgeStartAbilityFromBackground(const bool isBackgroundCall) const
{
    if (!isBackgroundCall) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Caller not background");
        return true;
    }

    // Temporarily supports permissions with two different spellings
    // PERMISSION_START_ABILIIES_FROM_BACKGROUND will be removed later due to misspelling
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_START_ABILITIES_FROM_BACKGROUND) ||
        VerifyCallingPermission(PermissionConstants::PERMISSION_START_ABILIIES_FROM_BACKGROUND)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Caller PASS");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "verification fail");
    return false;
}

bool PermissionVerification::JudgeAssociatedWakeUp(const uint32_t accessTokenId, const bool associatedWakeUp) const
{
    if (IsCallFromSameAccessToken(accessTokenId)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "TargetAbility in same APP");
        return true;
    }
    if (associatedWakeUp) {
        TAG_LOGD(AAFwkTag::DEFAULT, "associatedWakeUp: true");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "not allowed associatedWakeUp");
    return false;
}

int PermissionVerification::JudgeInvisibleAndBackground(const VerificationInfo &verificationInfo,
    bool isCallByShortcut) const
{
    uint32_t specifyTokenId = verificationInfo.specifyTokenId;
    TAG_LOGD(AAFwkTag::DEFAULT, "specifyTokenId: %{public}u, isCallByShortcut %{public}d",
        specifyTokenId, isCallByShortcut);
    if (specifyTokenId == 0 &&
        SupportSystemAbilityPermission::IsSupportSaCallPermission()) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Support SA call");
        return ERR_OK;
    }
    if (!isCallByShortcut &&
        !JudgeStartInvisibleAbility(verificationInfo.accessTokenId, verificationInfo.visible,
        specifyTokenId)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller INVISIBLE permission invalid");
        return ABILITY_VISIBLE_FALSE_DENY_REQUEST;
    }
    if (!JudgeStartAbilityFromBackground(verificationInfo.isBackgroundCall)) {
        TAG_LOGE(AAFwkTag::DEFAULT, "caller START_ABILITIES_FROM_BACKGROUND permission invalid");
        return CHECK_PERMISSION_FAILED;
    }

    return ERR_OK;
}

bool PermissionVerification::JudgeCallerIsAllowedToUseSystemAPI() const
{
    if (IsSACall() || IsShellCall()) {
        return true;
    }
    auto callerToken = IPCSkeleton::GetCallingFullTokenID();
    return Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(callerToken);
}

bool PermissionVerification::JudgeCallerIsAllowedToUseSystemAPIByTokenId(uint64_t specifiedFullTokenId) const
{
    uint32_t specifyTokenId = static_cast<uint32_t>(specifiedFullTokenId);
    if (IsSACallByTokenId(specifyTokenId) || IsShellCallByTokenId(specifyTokenId)) {
        return true;
    }
    if (specifiedFullTokenId == 0) {
        specifiedFullTokenId = IPCSkeleton::GetCallingFullTokenID();
    }
    return Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(specifiedFullTokenId);
}

bool PermissionVerification::IsSystemAppCall() const
{
    auto callerToken = IPCSkeleton::GetCallingFullTokenID();
    return Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(callerToken);
}

bool PermissionVerification::IsSystemAppCallByTokenId(uint32_t callerTokenId) const
{
    if (callerTokenId == 0) {
        return IsSystemAppCall();
    }
    auto tokenType = Security::AccessToken::AccessTokenKit::GetTokenTypeFlag(callerTokenId);
    if (tokenType != Security::AccessToken::ATokenTypeEnum::TOKEN_HAP) {
        TAG_LOGE(AAFwkTag::URIPERMMGR, "Not TOKEN_HAP.");
        return false;
    }
    Security::AccessToken::HapTokenInfo hapInfo;
    auto ret = Security::AccessToken::AccessTokenKit::GetHapTokenInfo(callerTokenId, hapInfo);
    if (ret != Security::AccessToken::AccessTokenKitRet::RET_SUCCESS) {
        TAG_LOGE(AAFwkTag::URIPERMMGR, "GetHapTokenInfo failed, ret:%{public}d", ret);
        return false;
    }
    uint64_t fullCallerTokenId = (static_cast<uint64_t>(hapInfo.tokenAttr) << TOKEN_ID_BIT_SIZE) + callerTokenId;
    return Security::AccessToken::TokenIdKit::IsSystemAppByFullTokenID(fullCallerTokenId);
}

bool PermissionVerification::VerifyBackgroundCallPermission(const bool isBackgroundCall) const
{
    return JudgeStartAbilityFromBackground(isBackgroundCall);
}

bool PermissionVerification::VerifyPrepareTerminatePermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_PREPARE_TERMINATE)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifyPrepareTerminatePermission(const int &tokenId) const
{
    int32_t ret = Security::AccessToken::AccessTokenKit::VerifyAccessToken(tokenId,
        PermissionConstants::PERMISSION_PREPARE_TERMINATE, false);
    if (ret != Security::AccessToken::PermissionState::PERMISSION_GRANTED) {
        TAG_LOGD(AAFwkTag::DEFAULT, "permission denied");
        return false;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "verify AccessToken success");
    return true;
}

bool PermissionVerification::VerifyShellStartExtensionType(int32_t type, uint32_t specifyTokenId) const
{
    if (IsShellCallByTokenId(specifyTokenId) && type >= SHELL_START_EXTENSION_FLOOR &&
        type <= SHELL_START_EXTENSION_CEIL) {
        return true;
    }
    TAG_LOGD(AAFwkTag::DEFAULT, "reject start");
    return false;
}

bool PermissionVerification::VerifyPreloadApplicationPermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_PRELOAD_APPLICATION)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission %{public}s granted",
            PermissionConstants::PERMISSION_PRELOAD_APPLICATION);
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission %{public}s denied",
        PermissionConstants::PERMISSION_PRELOAD_APPLICATION);
    return false;
}

bool PermissionVerification::VerifyPreStartAtomicServicePermission() const
{
    if (VerifyCallingPermission(PermissionConstants::PERMISSION_PRE_START_ATOMIC_SERVICE)) {
        TAG_LOGD(AAFwkTag::APPMGR, "Permission %{public}s granted",
            PermissionConstants::PERMISSION_PRE_START_ATOMIC_SERVICE);
        return true;
    }
    TAG_LOGW(AAFwkTag::APPMGR, "Permission %{public}s denied",
        PermissionConstants::PERMISSION_PRE_START_ATOMIC_SERVICE);
    return false;
}

bool PermissionVerification::VerifyKillProcessDependedOnWebPermission() const
{
    if (IsSACall() && VerifyCallingPermission(PermissionConstants::PERMISSION_KILL_PROCESS_DEPENDED_ON_WEB)) {
        TAG_LOGD(AAFwkTag::APPMGR, "Permission verification succeeded.");
        return true;
    }
    TAG_LOGW(AAFwkTag::APPMGR, "Permission verification failed");
    return false;
}

bool PermissionVerification::VerifyBlockAllAppStartPermission() const
{
    if (IsSACall() && VerifyCallingPermission(PermissionConstants::PERMISSION_BLOCK_ALL_APP_START)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifyStartUIAbilityToHiddenPermission() const
{
    if (IsSACall() && VerifyCallingPermission(PermissionConstants::PERMISSION_START_UIABILITY_TO_HIDDEN)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifySuperviseKiaServicePermission() const
{
    if (IsSACall() && VerifyCallingPermission(PermissionConstants::PERMISSION_SUPERVISE_KIA_SERVICE)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifyStartLocalDebug(int32_t tokenId) const
{
    if (VerifyPermissionByTokenId(tokenId, PermissionConstants::PERMISSION_PERFORM_LOCAL_DEBUG)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifyStartSelfUIAbility(int tokenId) const
{
    if (!IsSACall() && VerifyPermissionByTokenId(tokenId, PermissionConstants::PERMISSION_NDK_START_SELF_UI_ABILITY)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}

bool PermissionVerification::VerifyFusionAccessPermission() const
{
    auto callerToken = GetCallingTokenID();
    if (VerifyPermissionByTokenId(callerToken, PermissionConstants::PERMISSION_FUSION_ACCESS)) {
        TAG_LOGD(AAFwkTag::DEFAULT, "Permission granted");
        return true;
    }
    TAG_LOGE(AAFwkTag::DEFAULT, "Permission denied");
    return false;
}
}  // namespace AAFwk
}  // namespace OHOS
