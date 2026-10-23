/*
 * Copyright (c) 2022 Huawei Device Co., Ltd.
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

#include "bundle_install_checker.h"

#include "app_log_tag_wrapper.h"
#include "bms_extension_data_mgr.h"
#include "bundle_mgr_service.h"
#include "bundle_parser.h"
#include "bundle_permission_mgr.h"
#include "parameter.h"
#include "parameters.h"
#include "privilege_extension_ability_type.h"
#include "scope_guard.h"
#include "securec.h"
#include "systemcapability.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
constexpr const char* PRIVILEGE_ALLOW_APP_DATA_NOT_CLEARED = "AllowAppDataNotCleared";
constexpr const char* PRIVILEGE_ALLOW_APP_MULTI_PROCESS = "AllowAppMultiProcess";
constexpr const char* PRIVILEGE_ALLOW_APP_DESKTOP_ICON_HIDE = "AllowAppDesktopIconHide";
constexpr const char* PRIVILEGE_ALLOW_ABILITY_PRIORITY_QUERIED = "AllowAbilityPriorityQueried";
constexpr const char* PRIVILEGE_ALLOW_ABILITY_EXCLUDE_FROM_MISSIONS = "AllowAbilityExcludeFromMissions";
constexpr const char* PRIVILEGE_ALLOW_MISSION_NOT_CLEARED = "AllowMissionNotCleared";
constexpr const char* PRIVILEGE_ALLOW_APP_USE_PRIVILEGE_EXTENSION = "AllowAppUsePrivilegeExtension";
constexpr const char* PRIVILEGE_ALLOW_FORM_VISIBLE_NOTIFY = "AllowFormVisibleNotify";
constexpr const char* PRIVILEGE_ALLOW_APP_SHARE_LIBRARY = "AllowAppShareLibrary";
constexpr const char* PRIVILEGE_ALLOW_ENABLE_NOTIFICATION = "AllowEnableNotification";
constexpr const char* PRIVILEGE_ALLOW_ARK_TS_LARGE_HEAP = "AllowArkTsLargeHeap";
constexpr const char* ALLOW_APP_DATA_NOT_CLEARED = "allowAppDataNotCleared";
constexpr const char* ALLOW_APP_MULTI_PROCESS = "allowAppMultiProcess";
constexpr const char* ALLOW_APP_DESKTOP_ICON_HIDE = "allowAppDesktopIconHide";
constexpr const char* ALLOW_ABILITY_PRIORITY_QUERIED = "allowAbilityPriorityQueried";
constexpr const char* ALLOW_ABILITY_EXCLUDE_FROM_MISSIONS = "allowAbilityExcludeFromMissions";
constexpr const char* ALLOW_MISSION_NOT_CLEARED = "allowMissionNotCleared";
constexpr const char* ALLOW_APP_USE_PRIVILEGE_EXTENSION = "allowAppUsePrivilegeExtension";
constexpr const char* ALLOW_FORM_VISIBLE_NOTIFY = "allowFormVisibleNotify";
constexpr const char* ALLOW_APP_SHARE_LIBRARY = "allowAppShareLibrary";
constexpr const char* ALLOW_ENABLE_NOTIFICATION = "allowEnableNotification";
constexpr const char* APL_NORMAL = "normal";
constexpr const char* SLASH = "/";
constexpr const char* DOUBLE_SLASH = "//";
constexpr const char* SUPPORT_ISOLATION_MODE = "persist.bms.supportIsolationMode";
constexpr const char* VALUE_TRUE = "true";
constexpr const char* VALUE_TRUE_BOOL = "1";
constexpr const char* NONISOLATION_ONLY = "nonisolationOnly";
constexpr const char* ISOLATION_ONLY = "isolationOnly";
constexpr const char* SUPPORT_APP_TYPES = "const.bms.supportAppTypes";
constexpr const char* PROVIDED_DEVICE_FEATURES = "const.product.providedDeviceFeatures";
constexpr const char* SUPPORT_APP_TYPES_SEPARATOR = ",";
constexpr int8_t SLAH_OFFSET = 2;
constexpr int8_t THRESHOLD_VAL_LEN = 40;
constexpr const char* DEVICE_TYPE_OF_DEFAULT = "default";
constexpr const char* DEVICE_TYPE_OF_PHONE = "phone";
constexpr const char* APP_INSTALL_PATH = "/data/app/el1/bundle";
constexpr const char* IS_ROOT_MODE_PARAM = "const.debuggable";
const int32_t ROOT_MODE = 1;
const int32_t USER_MODE = 0;

const std::unordered_map<std::string, void (*)(AppPrivilegeCapability &appPrivilegeCapability)>
        PRIVILEGE_MAP = {
            { PRIVILEGE_ALLOW_APP_DATA_NOT_CLEARED,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.userDataClearable = false;
                } },
            { PRIVILEGE_ALLOW_APP_MULTI_PROCESS,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowMultiProcess = true;
                } },
            { PRIVILEGE_ALLOW_APP_DESKTOP_ICON_HIDE,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.hideDesktopIcon = true;
                } },
            { PRIVILEGE_ALLOW_ABILITY_PRIORITY_QUERIED,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowQueryPriority = true;
                } },
            { PRIVILEGE_ALLOW_ABILITY_EXCLUDE_FROM_MISSIONS,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowExcludeFromMissions = true;
                } },
            { PRIVILEGE_ALLOW_MISSION_NOT_CLEARED,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowMissionNotCleared = true;
                } },
            { PRIVILEGE_ALLOW_APP_USE_PRIVILEGE_EXTENSION,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowUsePrivilegeExtension = true;
                } },
            { PRIVILEGE_ALLOW_FORM_VISIBLE_NOTIFY,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.formVisibleNotify = true;
                } },
            { PRIVILEGE_ALLOW_APP_SHARE_LIBRARY,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.appShareLibrary = true;
                } },
            { PRIVILEGE_ALLOW_ENABLE_NOTIFICATION,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowEnableNotification = true;
                } },
            { PRIVILEGE_ALLOW_ARK_TS_LARGE_HEAP,
                [] (AppPrivilegeCapability &appPrivilegeCapability) {
                    appPrivilegeCapability.allowArkTsLargeHeap = true;
                } },
        };

static std::map<std::string, AppDistributionTypeEnum> AppDistributionTypeEnumMap = {
    { Constants::APP_DISTRIBUTION_TYPE_APP_GALLERY,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_APP_GALLERY },
    { Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_ENTERPRISE },
    { Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_NORMAL,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_ENTERPRISE_NORMAL },
    { Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_MDM,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_ENTERPRISE_MDM },
    { Constants::APP_DISTRIBUTION_TYPE_INTERNALTESTING,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_INTERNALTESTING },
    { Constants::APP_DISTRIBUTION_TYPE_CROWDTESTING,
        AppDistributionTypeEnum::APP_DISTRIBUTION_TYPE_CROWDTESTING },
};

std::string GetAppDistributionType(const Security::Verify::AppDistType &type)
{
    auto typeIter = APP_DISTRIBUTION_TYPE_MAPS.find(type);
    if (typeIter == APP_DISTRIBUTION_TYPE_MAPS.end()) {
        LOG_E(BMS_TAG_INSTALLER, "wrong AppDistType");
        return Constants::APP_DISTRIBUTION_TYPE_NONE;
    }

    return typeIter->second;
}

std::string GetAppProvisionType(const Security::Verify::ProvisionType &type)
{
    if (type == Security::Verify::ProvisionType::DEBUG) {
        return Constants::APP_PROVISION_TYPE_DEBUG;
    }

    return Constants::APP_PROVISION_TYPE_RELEASE;
}

bool IsPrivilegeExtensionAbilityType(ExtensionAbilityType type)
{
    return PRIVILEGE_EXTENSION_ABILITY_TYPE.find(type) != PRIVILEGE_EXTENSION_ABILITY_TYPE.end();
}

bool IsSystemExtensionAbilityType(ExtensionAbilityType type)
{
    return SYSTEM_EXTENSION_ABILITY_TYPE.find(type) != SYSTEM_EXTENSION_ABILITY_TYPE.end();
}
}

bool BundleInstallChecker::CheckSpaceIsolation(const int32_t userId, const InnerBundleInfo &info)
{
    bool isSpaceIsolation = OHOS::system::GetBoolParameter(ServiceConstants::ENTERPRISE_SPACE_ENABLE, false);
    if (!isSpaceIsolation) {
        return true;
    }

    if (userId < Constants::START_USERID) {
        return true;
    }

    if (info.IsSystemApp()) {
        return true;
    }

    BundleType bundleType = info.GetApplicationBundleType();
    if (bundleType != BundleType::APP && bundleType != BundleType::ATOMIC_SERVICE) {
        return true;
    }

    bool isDebugApp = info.GetAppProvisionType() == Constants::APP_PROVISION_TYPE_DEBUG ||
        info.GetBaseApplicationInfo().debug;
    std::string distributionType = info.GetAppDistributionType();
    bool isEnterpriseApp = distributionType == Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE ||
        distributionType == Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_NORMAL ||
        distributionType == Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_MDM;
    if (!isDebugApp && !isEnterpriseApp) {
        return true;
    }

    auto dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is null");
        return false;
    }

    std::string bundleName = info.GetBundleName();
    InnerBundleInfo installedInfo;
    bool isAppExist = dataMgr->FetchInnerBundleInfo(bundleName, installedInfo);
    if (!isAppExist) {
        return true;
    }

    PreInstallBundleInfo preInstallBundleInfo;
    if (dataMgr->GetPreInstallBundleInfo(bundleName, preInstallBundleInfo)) {
        return true;
    }

    return AccountHelper::CheckUserIsolation(userId, installedInfo.GetUsers());
}

ErrCode BundleInstallChecker::CheckSysCap(const std::vector<std::string> &bundlePaths)
{
    LOG_D(BMS_TAG_INSTALLER, "check hap syscaps start");
    if (bundlePaths.empty()) {
        LOG_NOFUNC_E(BMS_TAG_INSTALLER, "empty bundlePaths check hap syscaps fail");
        return ERR_APPEXECFWK_INSTALL_PARAM_ERROR;
    }

    ErrCode result = ERR_OK;
    BundleParser bundleParser;
    for (const auto &bundlePath : bundlePaths) {
        std::vector<std::string> bundleSysCaps;
        result = bundleParser.ParseSysCap(bundlePath, bundleSysCaps);
        if (result != ERR_OK) {
            LOG_D(BMS_TAG_INSTALLER, "parse bundle syscap failed, error: %{public}d", result);
            return result;
        }

        for (const auto &bundleSysCapItem : bundleSysCaps) {
            LOG_D(BMS_TAG_INSTALLER, "check syscap(%{public}s)", bundleSysCapItem.c_str());
            if (!HasSystemCapability(bundleSysCapItem.c_str())) {
                LOG_E(BMS_TAG_INSTALLER, "check syscap failed which %{public}s is not exsit",
                    bundleSysCapItem.c_str());
                return ERR_APPEXECFWK_INSTALL_CHECK_SYSCAP_FAILED;
            }
        }
    }

    LOG_D(BMS_TAG_INSTALLER, "finish check hap syscaps");
    return result;
}

ErrCode BundleInstallChecker::CheckMultipleHapsSignInfo(
    const std::vector<std::string> &bundlePaths,
    std::vector<Security::Verify::HapVerifyResult>& hapVerifyRes, bool readFile, int32_t userId)
{
    LOG_D(BMS_TAG_INSTALLER, "Check multiple haps signInfo");
    if (bundlePaths.empty()) {
        LOG_NOFUNC_E(BMS_TAG_INSTALLER, "check sign failed paths empty");
        return ERR_APPEXECFWK_INSTALL_PARAM_ERROR;
    }
    userId = userId < Constants::DEFAULT_USERID ? AccountHelper::GetUserIdByCallerType() : userId;
    for (const std::string &bundlePath : bundlePaths) {
        Security::Verify::HapVerifyResult hapVerifyResult;
        ErrCode verifyRes = ERR_OK;
        if (readFile) {
            std::string localCertDir = std::string(ServiceConstants::HAP_COPY_PATH) +
                ServiceConstants::ENTERPRISE_CERT_PATH + std::to_string(userId);
            if (userId < Constants::START_USERID || !BundleUtil::IsExistDir(localCertDir)) {
                localCertDir.clear();
            }
            verifyRes = Security::Verify::HapVerify(bundlePath, hapVerifyResult, true, localCertDir);
        } else {
            verifyRes = BundleVerifyMgr::HapVerify(bundlePath, hapVerifyResult, userId);
        }
#ifndef X86_EMULATOR_MODE
        if (verifyRes != ERR_OK) {
            LOG_E(BMS_TAG_INSTALLER, "hap file verify failed, bundlePath: %{public}s", bundlePath.c_str());
            return readFile ? ERR_APPEXECFWK_INSTALL_FAILED_BUNDLE_SIGNATURE_VERIFICATION_FAILURE : verifyRes;
        }
#endif
        hapVerifyRes.emplace_back(hapVerifyResult);
    }

    if (hapVerifyRes.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "no sign info in the all haps");
        return ERR_APPEXECFWK_INSTALL_FAILED_INCOMPATIBLE_SIGNATURE;
    }

    if (!CheckEnterpriseResign(hapVerifyRes[0].GetProvisionInfo(), userId)) {
        LOG_E(BMS_TAG_INSTALLER, "enterprise resign check failed");
        return ERR_APPEXECFWK_INSTALL_FAILED_APP_SOURCE_NOT_TRUESTED;
    }

    if (!CheckProvisionInfoIsValid(hapVerifyRes)) {
#ifndef X86_EMULATOR_MODE
        return ERR_APPEXECFWK_INSTALL_FAILED_INCOMPATIBLE_SIGNATURE;
#else
        // on emulator if check signature failed clear appid
        for (auto &verifyRes : hapVerifyRes) {
            Security::Verify::ProvisionInfo provisionInfo = verifyRes.GetProvisionInfo();
            provisionInfo.appId = Constants::EMPTY_STRING;
            verifyRes.SetProvisionInfo(provisionInfo);
        }
#endif
    }
    LOG_D(BMS_TAG_INSTALLER, "finish check multiple haps signInfo");
    return ERR_OK;
}

bool BundleInstallChecker::CheckEnterpriseResign(
    const Security::Verify::ProvisionInfo &provisionInfo, const int32_t userId)
{
    if (provisionInfo.distributionType != Security::Verify::AppDistType::ENTERPRISE &&
        provisionInfo.distributionType != Security::Verify::AppDistType::ENTERPRISE_NORMAL &&
        provisionInfo.distributionType != Security::Verify::AppDistType::ENTERPRISE_MDM) {
        return true;
    }
    if (provisionInfo.isEnterpriseResigned) {
        return true;
    }
    if (!OHOS::system::GetBoolParameter(ServiceConstants::IS_ENTERPRISE_DEVICE, false)) {
        return true;
    }
    std::vector<std::string> certificateAlias;
    if ((BundleUtil::GetEnterpriseReSignatureCert(userId, certificateAlias) == ERR_OK) && !certificateAlias.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "enterprise resign cert exist but hap not resigned");
        return false;
    }
    return true;
}

bool BundleInstallChecker::CheckProvisionInfoIsValid(
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes)
{
    auto appId = hapVerifyRes[0].GetProvisionInfo().appId;
    auto appIdentifier = hapVerifyRes[0].GetProvisionInfo().bundleInfo.appIdentifier;
    auto apl = hapVerifyRes[0].GetProvisionInfo().bundleInfo.apl;
    auto appDistributionType = hapVerifyRes[0].GetProvisionInfo().distributionType;
    auto appProvisionType = hapVerifyRes[0].GetProvisionInfo().type;
    bool isInvalid = std::any_of(hapVerifyRes.begin(), hapVerifyRes.end(),
        [appId, apl, appDistributionType, appProvisionType, appIdentifier](const auto &hapVerifyResult) {
            if (appId != hapVerifyResult.GetProvisionInfo().appId) {
                LOG_E(BMS_TAG_INSTALLER, "error: hap files have different appId");
                return true;
            }
            if (apl != hapVerifyResult.GetProvisionInfo().bundleInfo.apl) {
                LOG_E(BMS_TAG_INSTALLER, "error: hap files have different apl");
                return true;
            }
            if (appDistributionType != hapVerifyResult.GetProvisionInfo().distributionType) {
                LOG_E(BMS_TAG_INSTALLER, "error: hap files have different appDistributionType");
                return true;
            }
            if (appProvisionType != hapVerifyResult.GetProvisionInfo().type) {
                LOG_E(BMS_TAG_INSTALLER, "error: hap files have different appProvisionType");
                return true;
            }
            if (appIdentifier != hapVerifyResult.GetProvisionInfo().bundleInfo.appIdentifier) {
                LOG_E(BMS_TAG_INSTALLER, "error: hap files have different appIdentifier");
                return true;
            }
        return false;
    });
    return !isInvalid;
}

bool BundleInstallChecker::VaildInstallPermission(const InstallParam &installParam,
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes)
{
    PermissionStatus installBundleStatus = installParam.installBundlePermissionStatus;
    PermissionStatus installEnterpriseBundleStatus = installParam.installEnterpriseBundlePermissionStatus;
    PermissionStatus installEtpMdmBundleStatus = installParam.installEtpMdmBundlePermissionStatus;
    PermissionStatus installInternaltestingBundleStatus = installParam.installInternaltestingBundlePermissionStatus;
    bool isCallByShell = installParam.isCallByShell;
    if (!isCallByShell && installBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEnterpriseBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEtpMdmBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installInternaltestingBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS) {
        return true;
    }
    for (uint32_t i = 0; i < hapVerifyRes.size(); ++i) {
        Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes[i].GetProvisionInfo();
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE) {
            if (isCallByShell && provisionInfo.type != Security::Verify::ProvisionType::DEBUG) {
                LOG_E(BMS_TAG_INSTALLER, "enterprise bundle can not be installed by shell");
                return false;
            }
            if (!isCallByShell && installEnterpriseBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
                LOG_E(BMS_TAG_INSTALLER, "install enterprise bundle permission denied");
                return false;
            }
            continue;
        }
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL ||
            provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM) {
            bool result = VaildEnterpriseInstallPermission(installParam, provisionInfo);
            if (!result) {
                return false;
            }
            continue;
        }
        if (provisionInfo.distributionType == Security::Verify::AppDistType::INTERNALTESTING) {
            if (!isCallByShell && installInternaltestingBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
                LOG_E(BMS_TAG_INSTALLER, "install internaltesting bundle permission denied");
                return false;
            }
            continue;
        }
        if (installBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
            LOG_E(BMS_TAG_INSTALLER, "install permission denied");
            return false;
        }
    }
    return true;
}

bool BundleInstallChecker::VaildEnterpriseInstallPermission(const InstallParam &installParam,
    const Security::Verify::ProvisionInfo &provisionInfo)
{
    if (installParam.isSelfUpdate) {
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM) {
            LOG_I(BMS_TAG_INSTALLER, "Mdm self update");
            return true;
        }
        LOG_E(BMS_TAG_INSTALLER, "Self update not MDM");
        return false;
    }
    bool isCallByShell = installParam.isCallByShell;
    PermissionStatus installEtpNormalBundleStatus = installParam.installEtpNormalBundlePermissionStatus;
    PermissionStatus installEtpMdmBundleStatus = installParam.installEtpMdmBundlePermissionStatus;
    if (isCallByShell && provisionInfo.type != Security::Verify::ProvisionType::DEBUG) {
        LOG_E(BMS_TAG_INSTALLER, "enterprise normal/mdm bundle can not be installed by shell");
        return false;
    }
    if (!isCallByShell &&
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL &&
        installEtpNormalBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEtpMdmBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
        LOG_E(BMS_TAG_INSTALLER, "install enterprise normal bundle permission denied");
        return false;
    }
    if (!isCallByShell &&
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM &&
        installEtpMdmBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
        LOG_E(BMS_TAG_INSTALLER, "install enterprise mdm bundle permission denied");
        return false;
    }
    return true;
}

ErrCode BundleInstallChecker::ParseHapFiles(
    const std::vector<std::string> &bundlePaths,
    const InstallCheckParam &checkParam,
    std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes,
    std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    LOG_D(BMS_TAG_INSTALLER, "Parse hap file");
    ErrCode result = ERR_OK;
    for (uint32_t i = 0; i < bundlePaths.size(); ++i) {
        InnerBundleInfo newInfo;
        BundlePackInfo packInfo;
        Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes[i].GetProvisionInfo();
        if (provisionInfo.bundleInfo.appFeature == ServiceConstants::HOS_SYSTEM_APP) {
            newInfo.SetAppType(Constants::AppType::SYSTEM_APP);
        } else {
            newInfo.SetAppType(Constants::AppType::THIRD_PARTY_APP);
        }

        newInfo.SetIsPreInstallApp(checkParam.isPreInstallApp);
        result = ParseBundleInfo(bundlePaths[i], newInfo, packInfo);
        if (result != ERR_OK) {
            LOG_E(BMS_TAG_INSTALLER, "bundle parse failed %{public}d", result);
            return result;
        }
        newInfo.SetOrganization(provisionInfo.organization);
#ifndef X86_EMULATOR_MODE
        result = CheckBundleName(provisionInfo.bundleInfo.bundleName, newInfo.GetBundleName());
        if (result != ERR_OK) {
            LOG_E(BMS_TAG_INSTALLER, "check provision bundleName failed");
            return result;
        }
#endif
        if (newInfo.HasEntry()) {
            if (isContainEntry_) {
                LOG_E(BMS_TAG_INSTALLER, "more than one entry hap in the direction");
                return ERR_APPEXECFWK_INSTALL_INVALID_NUMBER_OF_ENTRY_HAP;
            }
            isContainEntry_ = true;
        }

        SetEntryInstallationFree(packInfo, newInfo);
        result = CheckMainElement(newInfo);
        if (result != ERR_OK) {
            return result;
        }
        AppPrivilegeCapability appPrivilegeCapability;
        // from provision file
        ParseAppPrivilegeCapability(provisionInfo, appPrivilegeCapability);
        // form install_list_capability.json, higher priority than provision file
        // allow appIdentifier/appId/fingerprint
        newInfo.SetProvisionId(provisionInfo.appId);
        std::vector<std::string> appSignatures;
        appSignatures.emplace_back(provisionInfo.bundleInfo.appIdentifier);
        appSignatures.emplace_back(newInfo.GetAppId());
        appSignatures.emplace_back(provisionInfo.fingerprint);
        FetchPrivilegeCapabilityFromPreConfig(
            newInfo.GetBundleName(), appSignatures, appPrivilegeCapability);
        // process bundleInfo by appPrivilegeCapability
        result = ProcessBundleInfoByPrivilegeCapability(appPrivilegeCapability, newInfo);
        if (result != ERR_OK) {
            return result;
        }
        CollectProvisionInfo(provisionInfo, appPrivilegeCapability, newInfo);
#ifdef USE_PRE_BUNDLE_PROFILE
        GetPrivilegeCapability(checkParam, newInfo);
#endif
        if ((provisionInfo.distributionType == Security::Verify::AppDistType::CROWDTESTING) ||
            (checkParam.specifiedDistributionType == Constants::APP_DISTRIBUTION_TYPE_CROWDTESTING)) {
            newInfo.SetAppCrowdtestDeadline((checkParam.crowdtestDeadline >= 0) ? checkParam.crowdtestDeadline :
                Constants::INHERIT_CROWDTEST_DEADLINE);
        } else {
            newInfo.SetAppCrowdtestDeadline(Constants::INVALID_CROWDTEST_DEADLINE);
        }
        if (!checkParam.isPreInstallApp) {
            if ((result = CheckSystemSize(bundlePaths[i], checkParam.appType)) != ERR_OK) {
                LOG_E(BMS_TAG_INSTALLER, "install failed due to insufficient disk memory");
                return result;
            }
        }
        if (provisionInfo.isEnterpriseResigned) {
            newInfo.SetAppSignType(Constants::APP_SIGN_TYPE_ENTERPRISE_RE_SIGN);
        }
        infos.emplace(bundlePaths[i], newInfo);
    }
    if (!infos.empty()) {
        result = CheckEnterpriseForAllUser(infos, checkParam, infos.begin()->second.GetAppDistributionType());
        if (result != ERR_OK) {
            return result;
        }
    }

    if ((result = CheckModuleNameForMulitHaps(infos)) != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "install failed due to duplicated moduleName");
        return result;
    }
    LOG_D(BMS_TAG_INSTALLER, "finish parse hap file");
    return result;
}

ErrCode BundleInstallChecker::CheckEnterpriseForAllUser(std::unordered_map<std::string, InnerBundleInfo> &infos,
    const InstallCheckParam &checkParam, const std::string &distributionType)
{
    if (!checkParam.isInstalledForAllUser) {
        return ERR_OK;
    }
    if (Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_NORMAL != distributionType &&
        Constants::APP_DISTRIBUTION_TYPE_ENTERPRISE_MDM != distributionType) {
        LOG_W(BMS_TAG_INSTALLER, "param is true, but not enterprise bundle");
        return ERR_OK;
    }
    if (!OHOS::system::GetBoolParameter(ServiceConstants::IS_ENTERPRISE_DEVICE, false)) {
        LOG_E(BMS_TAG_INSTALLER, "not enterprise device");
        return ERR_APPEXECFWK_INSTALL_ENTERPRISE_BUNDLE_NOT_ALLOWED;
    }
    for (auto &info : infos) {
        info.second.SetInstalledForAllUser(checkParam.isInstalledForAllUser);
    }
    LOG_I(BMS_TAG_INSTALLER, "install enterprise bundle for all user");
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckHspInstallCondition(
    std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes,
    const Security::AccessToken::AccessTokenID callerToken)
{
    ErrCode result = ERR_OK;
    if ((result = CheckDeveloperMode(hapVerifyRes, callerToken)) != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "install failed due to debug mode");
        return result;
    }
    if ((result = CheckAllowEnterpriseBundle(hapVerifyRes)) != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "install failed due to non-enterprise device");
        return result;
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckInstallPermission(const InstallCheckParam &checkParam,
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes)
{
    if ((checkParam.installBundlePermissionStatus != PermissionStatus::NOT_VERIFIED_PERMISSION_STATUS ||
        checkParam.installEnterpriseBundlePermissionStatus != PermissionStatus::NOT_VERIFIED_PERMISSION_STATUS ||
        checkParam.installEtpNormalBundlePermissionStatus != PermissionStatus::NOT_VERIFIED_PERMISSION_STATUS ||
        checkParam.installInternaltestingBundlePermissionStatus != PermissionStatus::NOT_VERIFIED_PERMISSION_STATUS ||
        checkParam.installEtpMdmBundlePermissionStatus != PermissionStatus::NOT_VERIFIED_PERMISSION_STATUS) &&
        !VaildInstallPermissionForShare(checkParam, hapVerifyRes)) {
        // need vaild permission
        LOG_E(BMS_TAG_INSTALLER, "install permission denied");
        return ERR_APPEXECFWK_INSTALL_PERMISSION_DENIED;
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckNoU1Enable(const std::unordered_map<std::string, InnerBundleInfo> &newInfos)
{
    for (auto &item : newInfos) {
        if (item.second.IsU1Enable()) {
            LOG_E(BMS_TAG_INSTALLER, "%{public}s: u1Enable in bundleinfos are not same",
                item.second.GetBundleName().c_str());
            return ERR_APPEXECFWK_INSTALL_U1_ENABLE_NOT_SUPPORT_APP_SERVICE_AND_SHARED_BUNDLE;
        }
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckU1EnableSameInHaps(const std::unordered_map<std::string, InnerBundleInfo> &infos,
    const std::string &bundleName, bool &u1Enable)
{
    if (infos.empty()) {
        return ERR_OK;
    }
    u1Enable = infos.begin()->second.IsU1Enable();
    for (auto &item : infos) {
        if (u1Enable != item.second.IsU1Enable()) {
            LOG_E(BMS_TAG_INSTALLER, "%{public}s: u1Enable in bundleinfos are not same",
                bundleName.c_str());
            return ERR_APPEXECFWK_INSTALL_U1_ENABLE_NOT_SAME_IN_ALL_BUNDLE_INFOS;
        }
    }
    return ERR_OK;
}

bool BundleInstallChecker::VaildInstallPermissionForShare(const InstallCheckParam &checkParam,
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes)
{
    PermissionStatus installBundleStatus = checkParam.installBundlePermissionStatus;
    PermissionStatus installEnterpriseBundleStatus = checkParam.installEnterpriseBundlePermissionStatus;
    PermissionStatus installEtpMdmBundleStatus = checkParam.installEtpMdmBundlePermissionStatus;
    PermissionStatus installInternaltestingBundleStatus = checkParam.installInternaltestingBundlePermissionStatus;
    bool isCallByShell = checkParam.isCallByShell;
    if (!isCallByShell && installBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEnterpriseBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEtpMdmBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS &&
        installInternaltestingBundleStatus == PermissionStatus::HAVE_PERMISSION_STATUS) {
        return true;
    }
    for (uint32_t i = 0; i < hapVerifyRes.size(); ++i) {
        Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes[i].GetProvisionInfo();
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE) {
            if (isCallByShell && provisionInfo.type != Security::Verify::ProvisionType::DEBUG) {
                LOG_E(BMS_TAG_INSTALLER, "enterprise bundle can not be installed by shell");
                return false;
            }
            if (!isCallByShell && installEnterpriseBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
                LOG_E(BMS_TAG_INSTALLER, "install enterprise bundle permission denied");
                return false;
            }
            continue;
        }
        if (provisionInfo.distributionType == Security::Verify::AppDistType::INTERNALTESTING) {
            if (!isCallByShell && installInternaltestingBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
                LOG_E(BMS_TAG_INSTALLER, "install internaltesting bundle permission denied");
                return false;
            }
            continue;
        }
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL ||
            provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM) {
            bool result = VaildEnterpriseInstallPermissionForShare(checkParam, provisionInfo);
            if (!result) {
                return false;
            }
            continue;
        }
        if (installBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
            LOG_E(BMS_TAG_INSTALLER, "install permission denied");
            return false;
        }
    }
    return true;
}

bool BundleInstallChecker::VaildEnterpriseInstallPermissionForShare(const InstallCheckParam &checkParam,
    const Security::Verify::ProvisionInfo &provisionInfo)
{
    bool isCallByShell = checkParam.isCallByShell;
    PermissionStatus installEtpNormalBundleStatus = checkParam.installEtpNormalBundlePermissionStatus;
    PermissionStatus installEtpMdmBundleStatus = checkParam.installEtpMdmBundlePermissionStatus;
    if (isCallByShell && provisionInfo.type != Security::Verify::ProvisionType::DEBUG) {
        LOG_E(BMS_TAG_INSTALLER, "enterprise normal/mdm bundle can not be installed by shell");
        return false;
    }
    if (!isCallByShell &&
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL &&
        installEtpNormalBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS &&
        installEtpMdmBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
        LOG_E(BMS_TAG_INSTALLER, "install enterprise normal bundle permission denied");
        return false;
    }
    if (!isCallByShell &&
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM &&
        installEtpMdmBundleStatus != PermissionStatus::HAVE_PERMISSION_STATUS) {
        LOG_E(BMS_TAG_INSTALLER, "install enterprise mdm bundle permission denied");
        return false;
    }
    return true;
}

ErrCode BundleInstallChecker::CheckDependency(std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    LOG_D(BMS_TAG_INSTALLER, "CheckDependency");
    auto hapVersionCode = GetVersionCode(infos);
    for (const auto &info : infos) {
        if (info.second.GetInnerModuleInfos().empty()) {
            LOG_D(BMS_TAG_INSTALLER, "GetInnerModuleInfos is empty");
            continue;
        }
        // There is only one innerModuleInfo when installing
        InnerModuleInfo moduleInfo = info.second.GetInnerModuleInfos().begin()->second;
        LOG_D(BMS_TAG_INSTALLER, "current module:%{public}s, dependencies = %{public}s", moduleInfo.moduleName.c_str(),
            GetJsonStrFromInfo(moduleInfo.dependencies).c_str());
        for (const auto &dependency : moduleInfo.dependencies) {
            if (!NeedCheckDependency(dependency, info.second)) {
                LOG_D(BMS_TAG_INSTALLER, "deliveryWithInstall is false, do not check whether the dependency exists");
                continue;
            }
            std::string bundleName =
                dependency.bundleName.empty() ? info.second.GetBundleName() : dependency.bundleName;
            if (FindModuleInInstallingPackage(dependency.moduleName, bundleName, infos)) {
                continue;
            }
            LOG_W(BMS_TAG_INSTALLER, "The depend module:%{public}s is not exist in installing package",
                dependency.moduleName.c_str());
            if (!FindModuleInInstalledPackage(dependency.moduleName, bundleName, hapVersionCode)) {
                LOG_E(BMS_TAG_INSTALLER, "The depend :%{public}s is not exist", dependency.moduleName.c_str());
                SetCheckResultMsg(
                    moduleInfo.moduleName + "'s dependent module: " + dependency.moduleName + " does not exist");
                return ERR_APPEXECFWK_INSTALL_DEPENDENT_MODULE_NOT_EXIST;
            }
        }
    }

    return ERR_OK;
}

bool BundleInstallChecker::NeedCheckDependency(const Dependency &dependency, const InnerBundleInfo &info)
{
    LOG_D(BMS_TAG_INSTALLER, "NeedCheckDependency the moduleName is %{public}s, the bundleName is %{public}s",
        dependency.moduleName.c_str(), dependency.bundleName.c_str());

    if (!dependency.bundleName.empty() && dependency.bundleName != info.GetBundleName()) {
        LOG_D(BMS_TAG_INSTALLER, "Cross-app dependencies, check dependency with shared bundle installer");
        return false;
    }
    std::vector<PackageModule> modules = info.GetBundlePackInfo().summary.modules;
    if (modules.empty()) {
        LOG_D(BMS_TAG_INSTALLER, "NeedCheckDependency modules is empty, need check dependency");
        return true;
    }
    for (const auto &module : modules) {
        if (module.distro.moduleName == dependency.moduleName) {
            return module.distro.deliveryWithInstall;
        }
    }

    LOG_D(BMS_TAG_INSTALLER, "NeedCheckDependency the module not found, need check dependency");
    return true;
}

bool BundleInstallChecker::FindModuleInInstallingPackage(
    const std::string &moduleName,
    const std::string &bundleName,
    const std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    LOG_D(BMS_TAG_INSTALLER, "moduleName is %{public}s, the bundleName is %{public}s",
        moduleName.c_str(), bundleName.c_str());
    for (const auto &info : infos) {
        if (info.second.GetBundleName() == bundleName) {
            if (info.second.GetInnerModuleInfos().empty()) {
                continue;
            }
            // There is only one innerModuleInfo when installing
            InnerModuleInfo moduleInfo = info.second.GetInnerModuleInfos().begin()->second;
            if (moduleInfo.moduleName == moduleName) {
                return true;
            }
        }
    }
    return false;
}

bool BundleInstallChecker::FindModuleInInstalledPackage(
    const std::string &moduleName,
    const std::string &bundleName,
    uint32_t versionCode)
{
    LOG_D(BMS_TAG_INSTALLER, "FindModuleInInstalledPackage the moduleName is %{public}s, the bundleName is %{public}s",
        moduleName.c_str(), bundleName.c_str());
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        LOG_E(BMS_TAG_INSTALLER, "Get dataMgr shared_ptr nullptr");
        return false;
    }

    ScopeGuard enableGuard([&dataMgr, &bundleName] { dataMgr->EnableBundle(bundleName); });
    InnerBundleInfo bundleInfo;
    bool isBundleExist = dataMgr->FetchInnerBundleInfo(bundleName, bundleInfo);
    if (!isBundleExist) {
        LOG_E(BMS_TAG_INSTALLER, "the bundle: %{public}s is not install", bundleName.c_str());
        return false;
    }
    if (!bundleInfo.FindModule(moduleName)) {
        LOG_E(BMS_TAG_INSTALLER, "the module: %{public}s is not install", moduleName.c_str());
        return false;
    }
    if (bundleInfo.GetVersionCode() != versionCode) {
        LOG_E(BMS_TAG_INSTALLER, "the versionCode %{public}d of dependency is not consistent with the installed module",
            bundleInfo.GetVersionCode());
        return false;
    }
    return true;
}

ErrCode BundleInstallChecker::CheckBundleName(const std::string &provisionBundleName, const std::string &bundleName)
{
    LOG_D(BMS_TAG_INSTALLER, "CheckBundleName provisionBundleName:%{public}s, bundleName:%{public}s",
        provisionBundleName.c_str(), bundleName.c_str());
    if (provisionBundleName.empty() || bundleName.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "CheckBundleName provisionBundleName:%{public}s, bundleName:%{public}s failed",
            provisionBundleName.c_str(), bundleName.c_str());
        return ERR_APPEXECFWK_INSTALL_FAILED_BUNDLE_SIGNATURE_VERIFICATION_FAILURE;
    }
    if (provisionBundleName == bundleName) {
        return ERR_OK;
    }
    LOG_E(BMS_TAG_INSTALLER, "CheckBundleName failed provisionBundleName:%{public}s, bundleName:%{public}s",
        provisionBundleName.c_str(), bundleName.c_str());
    return ERR_APPEXECFWK_INSTALL_FAILED_BUNDLE_SIGNATURE_VERIFICATION_FAILURE;
}

void BundleInstallChecker::CollectProvisionInfo(
    const Security::Verify::ProvisionInfo &provisionInfo,
    const AppPrivilegeCapability &appPrivilegeCapability,
    InnerBundleInfo &newInfo)
{
    newInfo.SetProvisionId(provisionInfo.appId);
    newInfo.SetAppFeature(provisionInfo.bundleInfo.appFeature);
    newInfo.SetAppPrivilegeLevel(provisionInfo.bundleInfo.apl);
    newInfo.SetAllowedAcls(provisionInfo.acls.allowedAcls);
    newInfo.SetCertificateFingerprint(provisionInfo.fingerprint);
    newInfo.SetAppDistributionType(GetAppDistributionType(provisionInfo.distributionType));
    newInfo.SetAppProvisionType(GetAppProvisionType(provisionInfo.type));
    SetAppProvisionMetadata(provisionInfo.metadatas, newInfo);
#ifdef USE_PRE_BUNDLE_PROFILE
    newInfo.SetUserDataClearable(appPrivilegeCapability.userDataClearable);
    newInfo.SetHideDesktopIcon(appPrivilegeCapability.hideDesktopIcon);
    newInfo.SetFormVisibleNotify(appPrivilegeCapability.formVisibleNotify);
    newInfo.SetAllowMultiProcess(appPrivilegeCapability.allowMultiProcess);
#endif
    newInfo.AddOldAppId(newInfo.GetAppId());
    newInfo.SetAppIdentifier(provisionInfo.bundleInfo.appIdentifier);
}

void BundleInstallChecker::SetAppProvisionMetadata(const std::vector<Security::Verify::Metadata> &provisionMetadatas,
    InnerBundleInfo &newInfo)
{
    if (provisionMetadatas.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "provisionMetadatas is empty");
        return;
    }
    std::vector<Metadata> metadatas;
    for (const auto &it : provisionMetadatas) {
        Metadata metadata;
        metadata.name = it.name;
        metadata.value = it.value;
        metadatas.emplace_back(metadata);
    }
    newInfo.SetAppProvisionMetadata(metadatas);
}

void BundleInstallChecker::GetPrivilegeCapability(
    const InstallCheckParam &checkParam, InnerBundleInfo &newInfo)
{
    // Reset privilege capability
    newInfo.SetKeepAlive(false);
    newInfo.SetSingleton(false);

    newInfo.SetRemovable(checkParam.removable);
    PreBundleConfigInfo preBundleConfigInfo;
    preBundleConfigInfo.bundleName = newInfo.GetBundleName();
    if (!BMSEventHandler::GetPreInstallCapability(preBundleConfigInfo)) {
        LOG_D(BMS_TAG_INSTALLER, "%{public}s not exist in preinstall capability list", newInfo.GetBundleName().c_str());
        return;
    }

    if (!MatchSignature(preBundleConfigInfo.appSignature, newInfo.GetCertificateFingerprint()) &&
        !MatchSignature(preBundleConfigInfo.appSignature, newInfo.GetAppId()) &&
        !MatchSignature(preBundleConfigInfo.appSignature, newInfo.GetAppIdentifier()) &&
        !MatchOldSignatures(newInfo.GetBundleName(), preBundleConfigInfo.appSignature)) {
        LOG_E(BMS_TAG_INSTALLER, "%{public}s signature not match the capability list", newInfo.GetBundleName().c_str());
        return;
    }

    newInfo.SetKeepAlive(preBundleConfigInfo.keepAlive);
    newInfo.SetSingleton(preBundleConfigInfo.singleton);
    newInfo.SetRunningResourcesApply(preBundleConfigInfo.runningResourcesApply);
    newInfo.SetAssociatedWakeUp(preBundleConfigInfo.associatedWakeUp);
    newInfo.SetAllowCommonEvent(preBundleConfigInfo.allowCommonEvent);
    newInfo.SetResourcesApply(preBundleConfigInfo.resourcesApply);
    newInfo.SetAllowAppRunWhenDeviceFirstLocked(preBundleConfigInfo.allowAppRunWhenDeviceFirstLocked);
    newInfo.SetAllowEnableNotification(preBundleConfigInfo.allowEnableNotification);
}

void BundleInstallChecker::SetPackInstallationFree(BundlePackInfo &bundlePackInfo,
    const InnerBundleInfo &innerBundleInfo) const
{
    if (innerBundleInfo.GetIsNewVersion()) {
        if (innerBundleInfo.GetApplicationBundleType() != BundleType::ATOMIC_SERVICE) {
            for (auto &item : bundlePackInfo.summary.modules) {
                item.distro.installationFree = false;
            }
            return;
        }
        for (auto &item : bundlePackInfo.summary.modules) {
            item.distro.installationFree = true;
        }
    }
}

ErrCode BundleInstallChecker::ParseBundleInfo(
    const std::string &bundleFilePath,
    InnerBundleInfo &info,
    BundlePackInfo &packInfo)
{
    BundleParser bundleParser;
    ErrCode result = bundleParser.Parse(bundleFilePath, info, isAbcCompressed_);
    if (result != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "parse bundle info failed, error: %{public}d", result);
        if (result == ERR_APPEXECFWK_PARSE_NATIVE_SO_FAILED) {
            std::string resultMsg = "In the module named " + info.GetCurrentModulePackage() +
                ", the Abi type supported by the device does not match the Abi type configured in the C++ project.";
            LOG_E(BMS_TAG_INSTALLER, "%{public}s", resultMsg.c_str());
            SetCheckResultMsg(resultMsg);
        }
        return result;
    }

    const auto extensions = info.GetInnerExtensionInfos();
    for (const auto &item : extensions) {
        if (item.second.type == ExtensionAbilityType::UNSPECIFIED &&
            !BMSEventHandler::CheckExtensionTypeInConfig(item.second.extensionTypeName)) {
            LOG_W(BMS_TAG_INSTALLER, "Parse error, There is no corresponding type in the configuration");
        }
    }

    if (!packInfo.GetValid()) {
        result = bundleParser.ParsePackInfo(bundleFilePath, packInfo);
        if (result != ERR_OK) {
            LOG_E(BMS_TAG_INSTALLER, "parse bundle pack info failed, error: %{public}d", result);
            return result;
        }

        SetPackInstallationFree(packInfo, info);
        info.SetBundlePackInfo(packInfo);
        packInfo.SetValid(true);
    }

    return ERR_OK;
}

void BundleInstallChecker::SetEntryInstallationFree(
    const BundlePackInfo &bundlePackInfo,
    InnerBundleInfo &innerBundleInfo)
{
    if (!bundlePackInfo.GetValid()) {
        LOG_W(BMS_TAG_INSTALLER, "no pack.info in the hap file");
        return;
    }

    auto packageModule = bundlePackInfo.summary.modules;
    auto installationFree = std::any_of(packageModule.begin(), packageModule.end(), [&](const auto &module) {
        return module.distro.moduleType == "entry" && module.distro.installationFree;
    });
    if (installationFree) {
        LOG_I(BMS_TAG_INSTALLER, "install or update hm service");
    }
    if (innerBundleInfo.GetIsNewVersion()) {
        installationFree = innerBundleInfo.GetApplicationBundleType() == BundleType::ATOMIC_SERVICE;
    }

    innerBundleInfo.SetEntryInstallationFree(installationFree);
    if (installationFree && !innerBundleInfo.GetIsNewVersion()) {
        innerBundleInfo.SetApplicationBundleType(BundleType::ATOMIC_SERVICE);
    }
}

ErrCode BundleInstallChecker::CheckSystemSize(
    const std::string &bundlePath,
    const Constants::AppType appType) const
{
    if ((appType == Constants::AppType::SYSTEM_APP) &&
        (BundleUtil::CheckSystemSize(bundlePath, APP_INSTALL_PATH))) {
        return ERR_OK;
    }

    if ((appType == Constants::AppType::THIRD_SYSTEM_APP) &&
        (BundleUtil::CheckSystemSize(bundlePath, APP_INSTALL_PATH))) {
        return ERR_OK;
    }

    if ((appType == Constants::AppType::THIRD_PARTY_APP) &&
        (BundleUtil::CheckSystemSize(bundlePath, APP_INSTALL_PATH))) {
        return ERR_OK;
    }

    LOG_E(BMS_TAG_INSTALLER, "install failed due to insufficient disk memory");
    return ERR_APPEXECFWK_INSTALL_DISK_MEM_INSUFFICIENT;
}

ErrCode BundleInstallChecker::CheckHapHashParams(
    std::unordered_map<std::string, InnerBundleInfo> &infos,
    std::map<std::string, std::string> hashParams)
{
    if (hashParams.empty()) {
        LOG_D(BMS_TAG_INSTALLER, "hashParams is empty");
        return ERR_OK;
    }

    std::vector<std::string> hapModuleNames;
    for (auto &info : infos) {
        std::vector<std::string> moduleNames;
        info.second.GetModuleNames(moduleNames);
        if (moduleNames.empty()) {
            LOG_E(BMS_TAG_INSTALLER, "hap(%{public}s) moduleName is empty", info.first.c_str());
            return ERR_APPEXECFWK_INSTALL_FAILED_MODULE_NAME_EMPTY;
        }

        if (std::find(hapModuleNames.begin(), hapModuleNames.end(), moduleNames[0]) != hapModuleNames.end()) {
            LOG_E(BMS_TAG_INSTALLER, "hap moduleName(%{public}s) duplicate", moduleNames[0].c_str());
            return ERR_APPEXECFWK_INSTALL_FAILED_MODULE_NAME_DUPLICATE;
        }

        hapModuleNames.emplace_back(moduleNames[0]);
        auto hashParamIter = hashParams.find(moduleNames[0]);
        if (hashParamIter != hashParams.end()) {
            info.second.SetModuleHashValue(hashParamIter->second);
            hashParams.erase(hashParamIter);
        }
    }

    if (!hashParams.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "Some hashParam moduleName is not exist in hap moduleNames");
        return ERR_APPEXECFWK_INSTALL_FAILED_CHECK_HAP_HASH_PARAM;
    }

    return ERR_OK;
}

std::tuple<bool, std::string, std::string> BundleInstallChecker::GetValidReleaseType(
    const std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    if (infos.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "infos is empty");
        return std::make_tuple(false, "", "");
    }
    for (const auto &info : infos) {
        if (!info.second.IsHsp()) {
            return std::make_tuple(false, info.second.GetCurModuleName(), info.second.GetReleaseType());
        }
    }
    return std::make_tuple(true, (infos.begin()->second).GetCurModuleName(),
        (infos.begin()->second).GetReleaseType());
}

uint32_t BundleInstallChecker::GetVersionCode(const std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    if (infos.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "infos is empty");
        return 0;
    }
    uint32_t version = (infos.begin()->second).GetVersionCode();
    for (const auto &info : infos) {
        if (info.second.HasEntry()) {
            return info.second.GetVersionCode();
        }
        version = version > info.second.GetVersionCode() ? version : info.second.GetVersionCode();
    }
    return version;
}

ErrCode BundleInstallChecker::CheckAppLabelInfo(
    const std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    LOG_D(BMS_TAG_INSTALLER, "Check APP label");
    ErrCode ret = ERR_OK;
    std::string bundleName = (infos.begin()->second).GetBundleName();
    uint32_t versionCode = GetVersionCode(infos);
    auto [isHsp, moduleName, releaseType] = GetValidReleaseType(infos);
    bool singleton = (infos.begin()->second).IsSingleton();
    Constants::AppType appType = (infos.begin()->second).GetAppType();
    bool isStage = (infos.begin()->second).GetIsNewVersion();
    const std::string targetBundleName = (infos.begin()->second).GetTargetBundleName();
    int32_t targetPriority = (infos.begin()->second).GetTargetPriority();
    BundleType bundleType = (infos.begin()->second).GetApplicationBundleType();
    bool isHmService = (infos.begin()->second).GetEntryInstallationFree();
    bool debug = (infos.begin()->second).GetBaseApplicationInfo().debug;
    bool hasEntry = (infos.begin()->second).HasEntry();
    bool isSameDebugType = true;
    bool entryDebug = hasEntry ? debug : false;
    auto dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    bool isPreInstallApp = false;
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is null");
    } else {
        PreInstallBundleInfo preInstallBundleInfo;
        isPreInstallApp = dataMgr->GetPreInstallBundleInfo(bundleName, preInstallBundleInfo);
    }

    for (const auto &info : infos) {
        // check bundleName
        if (bundleName != info.second.GetBundleName()) {
            LOG_E(BMS_TAG_INSTALLER, "bundleName not same");
            return ERR_APPEXECFWK_INSTALL_BUNDLENAME_NOT_SAME;
        }
        // check version
        if (bundleType != BundleType::SHARED) {
            if ((isPreInstallApp ? isPreInstallApp : info.second.IsPreInstallApp()) &&
                info.second.GetAppType() == Constants::AppType::SYSTEM_APP && info.second.IsHsp()) {
                if (versionCode < info.second.GetVersionCode()) {
                    LOG_E(BMS_TAG_INSTALLER, "hsp version higer than entry!");
                    return ERR_APPEXECFWK_INSTALL_VERSIONCODE_NOT_SAME;
                }
            } else {
                if (versionCode != info.second.GetVersionCode()) {
                    LOG_E(BMS_TAG_INSTALLER, "versionCode not same");
                    return ERR_APPEXECFWK_INSTALL_VERSIONCODE_NOT_SAME;
                }
            }
        }
        // check release type
        if (releaseType != info.second.GetReleaseType()) {
            LOG_W(BMS_TAG_INSTALLER, "releaseType not same: [%{public}s, %{public}s] vs [%{public}s, %{public}s]",
                moduleName.c_str(), releaseType.c_str(),
                info.second.GetCurModuleName().c_str(), info.second.GetReleaseType().c_str());
            if (!isHsp && !info.second.IsHsp()) {
                LOG_E(BMS_TAG_INSTALLER, "releaseType not same");
                return ERR_APPEXECFWK_INSTALL_RELEASETYPE_NOT_SAME;
            }
        }
        if (singleton != info.second.IsSingleton()) {
            LOG_E(BMS_TAG_INSTALLER, "singleton not same");
            return ERR_APPEXECFWK_INSTALL_SINGLETON_NOT_SAME;
        }
        if (appType != info.second.GetAppType()) {
            LOG_E(BMS_TAG_INSTALLER, "appType not same");
            return ERR_APPEXECFWK_INSTALL_APPTYPE_NOT_SAME;
        }
        // check model type(FA or stage)
        if (isStage != info.second.GetIsNewVersion()) {
            LOG_E(BMS_TAG_INSTALLER, "must be all FA model or all stage model");
            return ERR_APPEXECFWK_INSTALL_STATE_ERROR;
        }
        if (targetBundleName != info.second.GetTargetBundleName()) {
            LOG_E(BMS_TAG_INSTALLER, "targetBundleName not same");
            return ERR_BUNDLEMANAGER_OVERLAY_INSTALLATION_FAILED_TARGET_BUNDLE_NAME_NOT_SAME;
        }
        if (targetPriority != info.second.GetTargetPriority()) {
            LOG_E(BMS_TAG_INSTALLER, "targetPriority not same");
            return ERR_BUNDLEMANAGER_OVERLAY_INSTALLATION_FAILED_TARGET_PRIORITY_NOT_SAME;
        }
        if (bundleType != info.second.GetApplicationBundleType()) {
            LOG_E(BMS_TAG_INSTALLER, "bundleType not same");
            return ERR_APPEXECFWK_BUNDLE_TYPE_NOT_SAME;
        }
        if (isHmService != info.second.GetEntryInstallationFree()) {
            LOG_E(BMS_TAG_INSTALLER, "application and hm service are not allowed installed simultaneously");
            return ERR_APPEXECFWK_INSTALL_TYPE_ERROR;
        }
        if (debug != info.second.GetBaseApplicationInfo().debug) {
            LOG_E(BMS_TAG_INSTALLER, "debug not same");
            isSameDebugType = false;
        }
        if (!hasEntry) {
            hasEntry = info.second.HasEntry();
            entryDebug = info.second.GetBaseApplicationInfo().debug;
        }
    }

    if (hasEntry && !entryDebug && (debug || !isSameDebugType)) {
        LOG_E(BMS_TAG_INSTALLER, "debug type not same");
        return ERR_APPEXECFWK_INSTALL_DEBUG_NOT_SAME;
    }
    LOG_D(BMS_TAG_INSTALLER, "finish check APP label");
    return ret;
}

ErrCode BundleInstallChecker::CheckMultiNativeFile(
    std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    ErrCode result = CheckMultiNativeSo(infos);
    if (result != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "Check multi nativeSo failed, result: %{public}d", result);
        return result;
    }

    result = CheckMultiArkNativeFile(infos);
    if (result != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "Check multi arkNativeFile failed, result: %{public}d", result);
        return result;
    }

    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckMultiArkNativeFile(
    std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    std::string arkNativeFileAbi = (infos.begin()->second).GetArkNativeFileAbi();
    for (const auto &info : infos) {
        if (info.second.GetArkNativeFileAbi().empty()) {
            continue;
        }
        if (arkNativeFileAbi.empty()) {
            arkNativeFileAbi = info.second.GetArkNativeFileAbi();
            continue;
        }
    }

    // Ensure the an is consistent in multiple haps
    if (!arkNativeFileAbi.empty()) {
        for (auto &info : infos) {
            info.second.SetArkNativeFileAbi(arkNativeFileAbi);
        }
    }

    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckMultiNativeSo(
    std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    std::string nativeLibraryPath = (infos.begin()->second).GetNativeLibraryPath();
    std::string cpuAbi = (infos.begin()->second).GetCpuAbi();
    for (const auto &info : infos) {
        if (info.second.GetNativeLibraryPath().empty()) {
            continue;
        }
        if (nativeLibraryPath.empty()) {
            nativeLibraryPath = info.second.GetNativeLibraryPath();
            cpuAbi = info.second.GetCpuAbi();
            continue;
        }
    }

    // Ensure the so is consistent in multiple haps
    if (!nativeLibraryPath.empty()) {
        for (auto &info : infos) {
            info.second.SetNativeLibraryPath(nativeLibraryPath);
            info.second.SetCpuAbi(cpuAbi);
        }
    }

    return ERR_OK;
}

void BundleInstallChecker::ResetProperties()
{
    isContainEntry_ = false;
}

void BundleInstallChecker::ParseAppPrivilegeCapability(
    const Security::Verify::ProvisionInfo &provisionInfo,
    AppPrivilegeCapability &appPrivilegeCapability)
{
    for (const auto &appPrivilege : provisionInfo.appPrivilegeCapabilities) {
        auto iter = PRIVILEGE_MAP.find(appPrivilege);
        if (iter != PRIVILEGE_MAP.end()) {
            iter->second(appPrivilegeCapability);
        }
    }
    LOG_D(BMS_TAG_INSTALLER, "AppPrivilegeCapability %{public}s",
        appPrivilegeCapability.ToString().c_str());
#ifndef USE_PRE_BUNDLE_PROFILE
    appPrivilegeCapability.allowMultiProcess = true;
    appPrivilegeCapability.allowUsePrivilegeExtension = true;
#endif
}

ErrCode BundleInstallChecker::CheckModuleNameForMulitHaps(
    const std::unordered_map<std::string, InnerBundleInfo> &infos)
{
    std::set<std::string> moduleSet;
    for (const auto &info : infos) {
        std::vector<std::string> moduleVec = info.second.GetDistroModuleName();
        if (moduleVec.empty()) {
            LOG_E(BMS_TAG_INSTALLER, "moduleName vector is empty");
            return ERR_APPEXECFWK_INSTALL_INTERNAL_ERROR;
        }
        if (moduleSet.count(moduleVec[0])) {
            LOG_E(BMS_TAG_INSTALLER, "the moduleName: %{public}s is not unique in the haps", moduleVec[0].c_str());
            SetCheckResultMsg("the moduleName: " + moduleVec[0] + " is not unique in the haps");
            return ERR_APPEXECFWK_INSTALL_NOT_UNIQUE_DISTRO_MODULE_NAME;
        }
        moduleSet.insert(moduleVec[0]);
    }
    return ERR_OK;
}

bool BundleInstallChecker::IsExistedDistroModule(const InnerBundleInfo &newInfo, const InnerBundleInfo &info) const
{
    std::string moduleName = newInfo.GetCurModuleName();
    std::string packageName = newInfo.GetCurrentModulePackage();
    if (packageName.empty() || moduleName.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "IsExistedDistroModule failed due to invalid packageName or moduleName");
        return false;
    }
    std::string oldModuleName = info.GetModuleNameByPackage(packageName);
    // if FA update to Stage, allow module name inconsistent
    bool isFAToStage = !info.GetIsNewVersion() && newInfo.GetIsNewVersion();
    if (!isFAToStage) {
        // if not FA update to Stage, check consistency of module name
        if (moduleName.compare(oldModuleName) != 0) {
            LOG_E(BMS_TAG_INSTALLER, "no moduleName in the innerModuleInfo");
            return false;
        }
    }
    // check consistency of module type
    std::string newModuleType = newInfo.GetModuleTypeByPackage(packageName);
    std::string oldModuleType = info.GetModuleTypeByPackage(packageName);
    if (newModuleType.compare(oldModuleType) != 0) {
        LOG_E(BMS_TAG_INSTALLER, "moduleType is different between the new hap and the original hap");
        return false;
    }

    return true;
}

bool BundleInstallChecker::IsContainModuleName(const InnerBundleInfo &newInfo, const InnerBundleInfo &info) const
{
    std::string moduleName = newInfo.GetCurModuleName();
    std::vector<std::string> moduleVec = info.GetDistroModuleName();
    if (moduleName.empty() || moduleVec.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "IsContainModuleName failed due to invalid moduleName or modulevec");
        return false;
    }
    return (find(moduleVec.cbegin(), moduleVec.cend(), moduleName) == moduleVec.cend()) ? false : true;
}

ErrCode BundleInstallChecker::CheckMainElement(const InnerBundleInfo &info)
{
    const std::map<std::string, InnerModuleInfo> &innerModuleInfos = info.GetInnerModuleInfos();
    if (innerModuleInfos.empty()) {
        return ERR_OK;
    }
    if (innerModuleInfos.cbegin()->second.distro.moduleType == Profile::MODULE_TYPE_SHARED) {
        return ERR_OK;
    }
    if (info.GetEntryInstallationFree() && innerModuleInfos.cbegin()->second.mainAbility.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "atomic service's mainElement can't be empty");
        return ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR;
    }
    return ERR_OK;
}

bool BundleInstallChecker::GetPrivilegeCapabilityValue(
    const std::vector<std::string> &existInJson,
    const std::string &key,
    bool existInPreJson,
    bool existInProvision)
{
    if (find(existInJson.cbegin(), existInJson.cend(), key) != existInJson.cend()) {
        return existInPreJson;
    }
    return existInProvision;
}

void BundleInstallChecker::FetchPrivilegeCapabilityFromPreConfig(
    const std::string &bundleName,
    const std::vector<std::string> &appSignatures,
    AppPrivilegeCapability &appPrivilegeCapability)
{
#ifdef USE_PRE_BUNDLE_PROFILE
    LOG_D(BMS_TAG_INSTALLER, "bundleName: %{public}s, FetchPrivilegeCapabilityFromPreConfig start", bundleName.c_str());
    PreBundleConfigInfo configInfo;
    configInfo.bundleName = bundleName;
    if (!BMSEventHandler::GetPreInstallCapability(configInfo)) {
        LOG_D(BMS_TAG_INSTALLER, "bundleName: %{public}s is not exist in pre install capability list",
            bundleName.c_str());
        return;
    }
    bool match = false;
    for (const auto &signature : appSignatures) {
        if (MatchSignature(configInfo.appSignature, signature)) {
            match = true;
            break;
        }
    }
    if (!match && !MatchOldSignatures(bundleName, configInfo.appSignature)) {
        LOG_NOFUNC_E(BMS_TAG_INSTALLER, "bundleName: %{public}s signature verify failed in capability list",
            bundleName.c_str());
        return;
    }

    appPrivilegeCapability.allowUsePrivilegeExtension = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_APP_USE_PRIVILEGE_EXTENSION,
        configInfo.allowUsePrivilegeExtension, appPrivilegeCapability.allowUsePrivilegeExtension);

    appPrivilegeCapability.allowMultiProcess = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_APP_MULTI_PROCESS, configInfo.allowMultiProcess, appPrivilegeCapability.allowMultiProcess);

    appPrivilegeCapability.hideDesktopIcon = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_APP_DESKTOP_ICON_HIDE, configInfo.hideDesktopIcon, appPrivilegeCapability.hideDesktopIcon);

    appPrivilegeCapability.allowQueryPriority = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_ABILITY_PRIORITY_QUERIED, configInfo.allowQueryPriority, appPrivilegeCapability.allowQueryPriority);

    appPrivilegeCapability.allowExcludeFromMissions = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_ABILITY_EXCLUDE_FROM_MISSIONS,
        configInfo.allowExcludeFromMissions, appPrivilegeCapability.allowExcludeFromMissions);

    appPrivilegeCapability.allowMissionNotCleared = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_MISSION_NOT_CLEARED, configInfo.allowMissionNotCleared, appPrivilegeCapability.allowMissionNotCleared);

    appPrivilegeCapability.formVisibleNotify = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_FORM_VISIBLE_NOTIFY, configInfo.formVisibleNotify, appPrivilegeCapability.formVisibleNotify);

    appPrivilegeCapability.userDataClearable = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_APP_DATA_NOT_CLEARED, configInfo.userDataClearable, appPrivilegeCapability.userDataClearable);

    appPrivilegeCapability.appShareLibrary = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_APP_SHARE_LIBRARY, configInfo.appShareLibrary, appPrivilegeCapability.appShareLibrary);

    appPrivilegeCapability.allowEnableNotification = GetPrivilegeCapabilityValue(configInfo.existInJsonFile,
        ALLOW_ENABLE_NOTIFICATION, configInfo.allowEnableNotification, appPrivilegeCapability.allowEnableNotification);
    LOG_D(BMS_TAG_INSTALLER, "AppPrivilegeCapability %{public}s", appPrivilegeCapability.ToString().c_str());
#endif
}

bool CheckDriverNameAndType(const InnerBundleInfo &bundleInfo)
{
    for (const auto &extensionInfo: bundleInfo.GetInnerExtensionInfos()) {
        bool isDriverExtensionAbilityType = (extensionInfo.second.type == ExtensionAbilityType::DRIVER);
        if (!isDriverExtensionAbilityType) {
            continue;
        }

        for (const auto &meta : extensionInfo.second.metadata) {
            if (meta.name == "saneConfig" || meta.name == "saneBackend") {
                LOG_E(BMS_TAG_INSTALLER, "Bundle %{public}s is not allowed", bundleInfo.GetBundleName().c_str());
                return false;
            }
        }
    }

    return true;
}

bool BundleInstallChecker::CheckSaneDriverIsolation(const Security::Verify::HapVerifyResult &hapVerifyResult,
    const int32_t userId, const std::unordered_map<std::string, InnerBundleInfo> &newInfos)
{
    if (newInfos.empty()) {
        LOG_E(BMS_TAG_INSTALLER, "newInfos is empty");
        return false;
    }

    bool isSpaceIsolation = OHOS::system::GetBoolParameter(ServiceConstants::ENTERPRISE_SPACE_ENABLE, false);
    if (!isSpaceIsolation) {
        return true;
    }

    bool isDebugProvisionType = (hapVerifyResult.GetProvisionInfo().type == Security::Verify::ProvisionType::DEBUG);
    if (!isDebugProvisionType) {
        return true;
    }
    for (const auto &newInfo : newInfos) {
        const InnerBundleInfo &bundleInfo = newInfo.second;
        if (!CheckDriverNameAndType(bundleInfo)) {
            return false;
        }
    }

    return true;
}

bool BundleInstallChecker::MatchOldSignatures(const std::string &bundleName,
    const std::vector<std::string> &appSignatures)
{
    std::vector<std::string> oldAppIds;
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (!dataMgr->GetOldAppIds(bundleName, oldAppIds)) {
        LOG_D(BMS_TAG_INSTALLER, "Get OldAppIds failed");
        return false;
    }
    for (const auto &signature : appSignatures) {
        if (std::find(oldAppIds.begin(), oldAppIds.end(), signature) != oldAppIds.end()) {
            return true;
        }
    }

    return false;
}

bool BundleInstallChecker::MatchSignature(
    const std::vector<std::string> &appSignatures, const std::string &signature)
{
    if (appSignatures.empty() || signature.empty()) {
        LOG_NOFUNC_W(BMS_TAG_INSTALLER, "appSignature of signature is empty");
        return false;
    }

    return std::find(
        appSignatures.begin(), appSignatures.end(), signature) != appSignatures.end();
}

ErrCode BundleInstallChecker::ProcessBundleInfoByPrivilegeCapability(
    const AppPrivilegeCapability &appPrivilegeCapability,
    InnerBundleInfo &innerBundleInfo)
{
    // process application
    ApplicationInfo applicationInfo = innerBundleInfo.GetBaseApplicationInfo();
    if (!appPrivilegeCapability.allowMultiProcess || applicationInfo.process.empty()) {
        applicationInfo.process = applicationInfo.bundleName;
    }
    applicationInfo.allowEnableNotification = appPrivilegeCapability.allowEnableNotification;
    applicationInfo.allowArkTsLargeHeap = appPrivilegeCapability.allowArkTsLargeHeap;
    innerBundleInfo.SetBaseApplicationInfo(applicationInfo);
    BundleInfo bundleInfo = innerBundleInfo.GetBaseBundleInfo();
    // process allow app share library
    if (applicationInfo.bundleType == BundleType::SHARED && !appPrivilegeCapability.appShareLibrary) {
        LOG_E(BMS_TAG_INSTALLER, "not allow app share library");
        return ERR_APPEXECFWK_INSTALL_SHARE_APP_LIBRARY_NOT_ALLOWED;
    }
    // process ability
    auto &abilityInfos = innerBundleInfo.FetchAbilityInfos();
    for (auto iter = abilityInfos.begin(); iter != abilityInfos.end(); ++iter) {
#ifdef USE_PRE_BUNDLE_PROFILE
        if (!appPrivilegeCapability.allowQueryPriority) {
            iter->second.priority = 0;
        }
        if (!appPrivilegeCapability.allowExcludeFromMissions) {
            iter->second.excludeFromMissions = false;
        }
        if (!appPrivilegeCapability.allowMissionNotCleared) {
            iter->second.unclearableMission = false;
        }
#else
        if (!applicationInfo.isSystemApp || !bundleInfo.isPreInstallApp) {
            iter->second.priority = 0;
            iter->second.excludeFromMissions = false;
        }
#endif
    }
    // process ExtensionAbility
    auto &innerExtensionInfos = innerBundleInfo.FetchInnerExtensionInfos();
    for (auto iter = innerExtensionInfos.begin(); iter != innerExtensionInfos.end(); ++iter) {
        bool privilegeType = IsPrivilegeExtensionAbilityType(iter->second.type);
        if (privilegeType && !appPrivilegeCapability.allowUsePrivilegeExtension) {
            LOG_E(BMS_TAG_INSTALLER, "not allow use privilege extension");
            return ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR;
        }

        bool systemType = IsSystemExtensionAbilityType(iter->second.type);
        if (systemType && !applicationInfo.isSystemApp) {
            LOG_E(BMS_TAG_INSTALLER, "not allow use system extension");
            return ERR_APPEXECFWK_PARSE_PROFILE_PROP_CHECK_ERROR;
        }

#ifdef USE_PRE_BUNDLE_PROFILE
        if (!appPrivilegeCapability.allowQueryPriority) {
            iter->second.priority = 0;
        }
#else
        if (!applicationInfo.isSystemApp || !bundleInfo.isPreInstallApp) {
            iter->second.priority = 0;
        }
#endif
        if (appPrivilegeCapability.allowMultiProcess) {
            LOG_D(BMS_TAG_INSTALLER, "%{public}s support allowMultiProcess", iter->second.bundleName.c_str());
            auto hapModuleInfo = innerBundleInfo.GetInnerModuleInfoByModuleName(iter->second.moduleName);
            if (hapModuleInfo && !hapModuleInfo->process.empty()) {
                iter->second.process = hapModuleInfo->process;
            }
        }
    }
    // process InnerModuleInfo
    auto &innerModuleInfos = innerBundleInfo.FetchInnerModuleInfos();
    for (auto iter = innerModuleInfos.begin(); iter != innerModuleInfos.end(); ++iter) {
        if (iter->second.isModuleJson && (!appPrivilegeCapability.allowMultiProcess || iter->second.process.empty())) {
            iter->second.process = applicationInfo.bundleName;
        }
    }
    return ERR_OK;
}

bool BundleInstallChecker::CheckSupportAppTypes(
    const std::unordered_map<std::string, InnerBundleInfo> &infos, const std::string &supportAppTypes) const
{
    LOG_D(BMS_TAG_INSTALLER, "supportAppTypes: %{public}s", supportAppTypes.c_str());
    std::vector<std::string> appTypesVec;
    OHOS::SplitStr(supportAppTypes, SUPPORT_APP_TYPES_SEPARATOR, appTypesVec);
    if (find(appTypesVec.begin(), appTypesVec.end(), DEVICE_TYPE_OF_DEFAULT) != appTypesVec.end() &&
        find(appTypesVec.begin(), appTypesVec.end(), DEVICE_TYPE_OF_PHONE) == appTypesVec.end()) {
        appTypesVec.emplace_back(DEVICE_TYPE_OF_PHONE);
    }
    sort(appTypesVec.begin(), appTypesVec.end());
    for (const auto &info : infos) {
        std::vector<std::string> devVec = info.second.GetDeviceType(info.second.GetCurrentModulePackage());
        if (find(devVec.begin(), devVec.end(), DEVICE_TYPE_OF_DEFAULT) != devVec.end() &&
            find(devVec.begin(), devVec.end(), DEVICE_TYPE_OF_PHONE) == devVec.end()) {
            devVec.emplace_back(DEVICE_TYPE_OF_PHONE);
        }
        sort(devVec.begin(), devVec.end());
        std::vector<std::string> intersectionVec;
        set_intersection(appTypesVec.begin(), appTypesVec.end(),
            devVec.begin(), devVec.end(), back_inserter(intersectionVec));
        if (intersectionVec.empty()) {
            LOG_W(BMS_TAG_INSTALLER, "check supportAppTypes failed");
            return false;
        }
    }
    return true;
}

ErrCode BundleInstallChecker::CheckDeviceType(std::unordered_map<std::string, InnerBundleInfo> &infos,
    ErrCode checkSysCapRes) const
{
    std::string supportAppTypes = OHOS::system::GetParameter(SUPPORT_APP_TYPES, "");
    if (!supportAppTypes.empty() && CheckSupportAppTypes(infos, supportAppTypes)) {
        return ERR_OK;
    }
    std::string deviceType = GetDeviceType();
    LOG_D(BMS_TAG_INSTALLER, "deviceType is %{public}s", deviceType.c_str());
    for (const auto &info : infos) {
        std::vector<std::string> devVec = info.second.GetDeviceType(info.second.GetCurrentModulePackage());
        if (devVec.empty()) {
            if (checkSysCapRes == ERR_APPEXECFWK_INSTALL_CHECK_SYSCAP_FAILED &&
                GetIntParameter(IS_ROOT_MODE_PARAM, USER_MODE) == ROOT_MODE) {
                LOG_NOFUNC_E(BMS_TAG_INSTALLER, "deviceTypes is empty and in root mode and check syscap failed");
                return ERR_APPEXECFWK_INSTALL_DEVICE_TYPE_NOT_SUPPORTED;
            }
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "deviceTypes is empty");
            continue;
        }

        if ((deviceType == DEVICE_TYPE_OF_PHONE) &&
            (find(devVec.begin(), devVec.end(), DEVICE_TYPE_OF_DEFAULT) != devVec.end())) {
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "current deviceType is phone and bundle is matched with default");
            continue;
        }

        if ((deviceType == DEVICE_TYPE_OF_DEFAULT) &&
            (find(devVec.begin(), devVec.end(), DEVICE_TYPE_OF_PHONE) != devVec.end())) {
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "current deviceType is default and bundle is matched with phone");
            continue;
        }

        if (find(devVec.begin(), devVec.end(), deviceType) == devVec.end()) {
            LOG_NOFUNC_E(BMS_TAG_INSTALLER, "%{public}s is not supported", deviceType.c_str());
            return CheckRequiredDeviceFeatures(infos);
        }
    }
    return ERR_OK;
}

bool BundleInstallChecker::IsSubSet(
    const std::vector<std::string> &mainSet, const std::vector<std::string> &subSet) const
{
    for (std::string item : subSet) {
        if (std::find(mainSet.begin(), mainSet.end(), item) == mainSet.end()) {
            LOG_NOFUNC_D(BMS_TAG_INSTALLER, "not SubSet: %{public}s", item.c_str());
            return false;
        }
    }
    return true;
}

ErrCode BundleInstallChecker::CheckRequiredDeviceFeatures(
    std::unordered_map<std::string, InnerBundleInfo> &infos) const
{
    std::string providedDeviceFeaturesValue = OHOS::system::GetParameter(PROVIDED_DEVICE_FEATURES, "");
    LOG_NOFUNC_D(BMS_TAG_INSTALLER, "providedDeviceFeatures: %{public}s", providedDeviceFeaturesValue.c_str());
    if (providedDeviceFeaturesValue.empty()) {
        LOG_NOFUNC_W(BMS_TAG_INSTALLER, "providedDeviceFeatures empty");
        return ERR_APPEXECFWK_INSTALL_DEVICE_TYPE_NOT_SUPPORTED;
    }
    std::vector<std::string> providedDeviceFeatures;
    OHOS::SplitStr(providedDeviceFeaturesValue, SUPPORT_APP_TYPES_SEPARATOR, providedDeviceFeatures);

    std::string deviceType = GetDeviceType();
    LOG_D(BMS_TAG_INSTALLER, "deviceType is %{public}s", deviceType.c_str());
    for (const auto &info : infos) {
        auto requiredDeviceFeatures = info.second.GetRequiredDeviceFeatures(info.second.GetCurrentModulePackage());
        auto it = requiredDeviceFeatures.find(deviceType);
        if (it == requiredDeviceFeatures.end()) {
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "requiredDeviceFeatures not support: %{public}s", deviceType.c_str());
            return ERR_APPEXECFWK_INSTALL_DEVICE_TYPE_NOT_SUPPORTED;
        }
        if (!IsSubSet(providedDeviceFeatures, it->second)) {
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "requiredDeviceFeatures not in provided");
            return ERR_APPEXECFWK_INSTALL_DEVICE_TYPE_NOT_SUPPORTED;
        }
    }
    return ERR_OK;
}

AppProvisionInfo BundleInstallChecker::ConvertToAppProvisionInfo(
    const Security::Verify::ProvisionInfo &provisionInfo) const
{
    AppProvisionInfo appProvisionInfo;
    appProvisionInfo.versionCode = provisionInfo.versionCode;
    appProvisionInfo.versionName = provisionInfo.versionName;
    if (provisionInfo.type == Security::Verify::ProvisionType::DEBUG) {
        appProvisionInfo.type = Constants::APP_PROVISION_TYPE_DEBUG;
        appProvisionInfo.certificate = provisionInfo.bundleInfo.developmentCertificate;
    } else {
        appProvisionInfo.type = Constants::APP_PROVISION_TYPE_RELEASE;
        appProvisionInfo.certificate = provisionInfo.bundleInfo.distributionCertificate;
    }
    appProvisionInfo.appDistributionType = GetAppDistributionType(provisionInfo.distributionType);
    appProvisionInfo.apl = provisionInfo.bundleInfo.apl.empty() ? APL_NORMAL : provisionInfo.bundleInfo.apl;
    appProvisionInfo.developerId = provisionInfo.bundleInfo.developerId;
    appProvisionInfo.issuer = provisionInfo.issuer;
    appProvisionInfo.uuid = provisionInfo.uuid;
    appProvisionInfo.validity.notBefore = provisionInfo.validity.notBefore;
    appProvisionInfo.validity.notAfter = provisionInfo.validity.notAfter;
    appProvisionInfo.appIdentifier = provisionInfo.bundleInfo.appIdentifier;
    appProvisionInfo.appServiceCapabilities = provisionInfo.appServiceCapabilities;
    appProvisionInfo.organization = provisionInfo.organization;
    return appProvisionInfo;
}

std::string GetBundleNameFromUri(const std::string &uri)
{
    std::size_t firstSlashPos = uri.find(DOUBLE_SLASH);
    if (firstSlashPos == std::string::npos) {
        LOG_E(BMS_TAG_INSTALLER, "dataproxy uri is invalid");
        return Constants::EMPTY_STRING;
    }

    std::size_t secondSlashPos = uri.find(SLASH, firstSlashPos + SLAH_OFFSET);
    if (secondSlashPos == std::string::npos) {
        LOG_E(BMS_TAG_INSTALLER, "dataproxy uri is invalid");
        return Constants::EMPTY_STRING;
    }

    std::string bundleName = uri.substr(firstSlashPos + SLAH_OFFSET, secondSlashPos - firstSlashPos - SLAH_OFFSET);
    return bundleName;
}

bool BundleInstallChecker::CheckProxyPermissionLevel(const std::string &permissionName) const
{
    // no permission name, only for self usage
    if (permissionName.empty()) {
        return true;
    }
    PermissionDef permissionDef;
    ErrCode ret = BundlePermissionMgr::GetPermissionDef(permissionName, permissionDef);
    if (ret != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "getPermissionDef failed");
        return false;
    }
    if (permissionDef.availableLevel < Security::AccessToken::ATokenAplEnum::APL_SYSTEM_BASIC) {
        LOG_E(BMS_TAG_INSTALLER, "permission %{public}s level too low", permissionName.c_str());
        return false;
    }
    return true;
}

ErrCode BundleInstallChecker::CheckProxyDatas(const InnerBundleInfo &innerBundleInfo) const
{
    auto bundleName = innerBundleInfo.GetBundleName();
    auto moduleInfos = innerBundleInfo.GetInnerModuleInfos();
    if (moduleInfos.empty()) {
        return ERR_OK;
    }
    for (const auto &moduleInfo : moduleInfos) {
        for (const auto &proxyData : moduleInfo.second.proxyDatas) {
            auto name = GetBundleNameFromUri(proxyData.uri);
            if (bundleName != name) {
                LOG_E(BMS_TAG_INSTALLER, "bundleName from uri %{public}s different from origin bundleName %{public}s",
                    name.c_str(), bundleName.c_str());
                return ERR_APPEXECFWK_INSTALL_CHECK_PROXY_DATA_URI_FAILED;
            }
            if (innerBundleInfo.IsSystemApp()) {
                continue;
            }
            if (!CheckProxyPermissionLevel(proxyData.requiredReadPermission)
                    || !CheckProxyPermissionLevel(proxyData.requiredWritePermission)) {
                return ERR_APPEXECFWK_INSTALL_CHECK_PROXY_DATA_PERMISSION_FAILED;
            }
        }
    }
    return ERR_OK;
}

bool CheckSupportIsolation(const char *szIsolationModeThresholdMb, const std::string &isolationMode)
{
    if ((std::strcmp(szIsolationModeThresholdMb, VALUE_TRUE) == 0) ||
        (std::strcmp(szIsolationModeThresholdMb, VALUE_TRUE_BOOL) == 0)) {
        if (isolationMode == NONISOLATION_ONLY) {
            LOG_E(BMS_TAG_INSTALLER, "check isolation mode failed");
            return false;
        }
    } else {
        if (isolationMode == ISOLATION_ONLY) {
            LOG_E(BMS_TAG_INSTALLER, "check isolation mode failed");
            return false;
        }
    }
    return true;
}

ErrCode BundleInstallChecker::CheckIsolationMode(const std::unordered_map<std::string, InnerBundleInfo> &infos) const
{
    for (const auto &info : infos) {
        auto moduleInfos = info.second.GetInnerModuleInfos();
        for (const auto &moduleInfo : moduleInfos) {
            std::string isolationMode = moduleInfo.second.isolationMode;
            char szIsolationModeThresholdMb[THRESHOLD_VAL_LEN] = {0};
            int32_t ret = GetParameter(SUPPORT_ISOLATION_MODE, "",
                szIsolationModeThresholdMb, THRESHOLD_VAL_LEN);
            if (ret <= 0) {
                LOG_D(BMS_TAG_INSTALLER, "GetParameter failed");
            }
            if (!CheckSupportIsolation(szIsolationModeThresholdMb, isolationMode)) {
                LOG_E(BMS_TAG_INSTALLER, "check isolation mode failed");
                return ERR_APPEXECFWK_INSTALL_ISOLATION_MODE_FAILED;
            }
        }
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckSignatureFileDir(const std::string &signatureFileDir) const
{
    ErrCode ret = BundleUtil::CheckFileName(signatureFileDir);
    if (ret != ERR_OK) {
        LOG_E(BMS_TAG_INSTALLER, "code signature file dir is invalid");
        return ERR_BUNDLEMANAGER_INSTALL_CODE_SIGNATURE_FILE_IS_INVALID;
    }
    if (!BundleUtil::CheckFileType(signatureFileDir, ServiceConstants::CODE_SIGNATURE_FILE_SUFFIX)) {
        LOG_E(BMS_TAG_INSTALLER, "signatureFileDir is not suffixed with .sig");
        return ERR_BUNDLEMANAGER_INSTALL_CODE_SIGNATURE_FILE_IS_INVALID;
    }
    // signatureFileDir not support relevant dir
    if (signatureFileDir.find(ServiceConstants::RELATIVE_PATH) != std::string::npos) {
        LOG_E(BMS_TAG_INSTALLER, "signatureFileDir is invalid");
        return ERR_BUNDLEMANAGER_INSTALL_CODE_SIGNATURE_FILE_IS_INVALID;
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckDeveloperMode(
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes,
    const Security::AccessToken::AccessTokenID callerToken) const
{
    bool hasDebugBundle = false;
    for (uint32_t i = 0; i < hapVerifyRes.size(); ++i) {
        Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes[i].GetProvisionInfo();
        if (provisionInfo.type == Security::Verify::ProvisionType::DEBUG) {
            hasDebugBundle = true;
            break;
        }
    }
    if (!hasDebugBundle) {
        return ERR_OK;
    }
    if (system::GetBoolParameter(ServiceConstants::DEVELOPERMODE_STATE, true)) {
        return ERR_OK;
    }
    if (BundlePermissionMgr::VerifyPermissionByCallingTokenId(
        Constants::PERMISSION_PERFORM_LOCAL_DEBUG, callerToken)) {
        LOG_I(BMS_TAG_INSTALLER, "dev assistant is allowed to install debug bundle");
        return ERR_OK;
    }
    LOG_E(BMS_TAG_INSTALLER, "debug bundle can only be installed in developer mode");
    return ERR_APPEXECFWK_INSTALL_DEBUG_BUNDLE_NOT_ALLOWED;
}

ErrCode BundleInstallChecker::CheckAllowEnterpriseBundle(
    const std::vector<Security::Verify::HapVerifyResult> &hapVerifyRes) const
{
    if (system::GetBoolParameter(ServiceConstants::ALLOW_ENTERPRISE_BUNDLE, false) ||
        system::GetBoolParameter(ServiceConstants::IS_ENTERPRISE_DEVICE, false) ||
        system::GetBoolParameter(ServiceConstants::DEVELOPERMODE_STATE, false)) {
        return ERR_OK;
    }
    for (uint32_t i = 0; i < hapVerifyRes.size(); ++i) {
        Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes[i].GetProvisionInfo();
        if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL ||
            provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM) {
            LOG_E(BMS_TAG_INSTALLER, "enterprise normal/mdm bundle cannot be installed on non-enterprise device");
            return ERR_APPEXECFWK_INSTALL_ENTERPRISE_BUNDLE_NOT_ALLOWED;
        }
    }
    return ERR_OK;
}

ErrCode BundleInstallChecker::CheckAppDistributionType(const Security::Verify::AppDistType type)
{
    return CheckAppDistributionType(GetAppDistributionType(type));
}

ErrCode BundleInstallChecker::CheckAppDistributionType(const std::string distributionType)
{
    if (distributionType == Constants::APP_DISTRIBUTION_TYPE_OS_INTEGRATION) {
        APP_LOGD("os_integration is pass");
        return ERR_OK;
    }
    auto bmsPara = DelayedSingleton<BundleMgrService>::GetInstance()->GetBmsParam();
    if (bmsPara == nullptr) {
        APP_LOGW("bmsPara is nullptr");
        return ERR_OK;
    }
    std::string val;
    bmsPara->GetBmsParam(Constants::APP_DISTRIBUTION_TYPE_WHITE_LIST, val);
    if (val.length() <= 0) {
        APP_LOGE("GetBmsParam is null or exsit");
        return ERR_OK;
    }
    int32_t appDisnTypeEnum = GetAppDistributionTypeEnum(distributionType);
    std::vector<std::string> appDistributionTypeEnums;
    OHOS::SplitStr(val, Constants::SUPPORT_APP_TYPES_SEPARATOR, appDistributionTypeEnums);
    if (std::find(appDistributionTypeEnums.begin(), appDistributionTypeEnums.end(), std::to_string(appDisnTypeEnum))
        == appDistributionTypeEnums.end()) {
        APP_LOGE("bmsParam %{public}s not allow %{public}s install", val.c_str(), distributionType.c_str());
        return ERR_APP_DISTRIBUTION_TYPE_NOT_ALLOW_INSTALL;
    }
    return ERR_OK;
}

int32_t BundleInstallChecker::GetAppDistributionTypeEnum(const std::string distributionType) const
{
    if (AppDistributionTypeEnumMap.find(distributionType) != AppDistributionTypeEnumMap.end()) {
        return static_cast<int32_t>(AppDistributionTypeEnumMap[distributionType]);
    }
    return 0;
}

bool BundleInstallChecker::CheckEnterpriseBundle(Security::Verify::HapVerifyResult &hapVerifyRes) const
{
    Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes.GetProvisionInfo();
    if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL ||
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM ||
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE) {
        return true;
    }
    return false;
}

bool BundleInstallChecker::CheckInternaltestingBundle(Security::Verify::HapVerifyResult &hapVerifyRes) const
{
    Security::Verify::ProvisionInfo provisionInfo = hapVerifyRes.GetProvisionInfo();
    if (provisionInfo.distributionType == Security::Verify::AppDistType::INTERNALTESTING) {
        return true;
    }
    return false;
}

void BundleInstallChecker::ProcessCodeSignatureParam(
    const Security::Verify::HapVerifyResult &hapVerifyResult,
    CodeSignatureParam &codeSignatureParam)
{
    Security::Verify::ProvisionInfo provisionInfo = hapVerifyResult.GetProvisionInfo();
    if (provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE ||
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_NORMAL ||
        provisionInfo.distributionType == Security::Verify::AppDistType::ENTERPRISE_MDM ||
        provisionInfo.distributionType == Security::Verify::AppDistType::INTERNALTESTING) {
        unsigned char *originalProfile = provisionInfo.profileBlock.get();
        if (originalProfile == nullptr) {
            LOG_NOFUNC_E(BMS_TAG_INSTALLER, "invalid originalProfile");
            return;
        }
        auto tempProfilePtr = std::make_unique<unsigned char[]>(provisionInfo.profileBlockLength);
        unsigned char *tempProfileData = tempProfilePtr.get();
        if (tempProfileData == nullptr) {
            LOG_NOFUNC_E(BMS_TAG_INSTALLER, "invalid tempProfileData");
            return;
        }
        if (memcpy_s(tempProfileData, provisionInfo.profileBlockLength, originalProfile,
            provisionInfo.profileBlockLength) != 0) {
            LOG_NOFUNC_E(BMS_TAG_INSTALLER, "process CodeSignatureParam memcpy_s failed");
            return;
        }
        codeSignatureParam.profileBlockLength = provisionInfo.profileBlockLength;
        codeSignatureParam.profileBlock = std::move(tempProfilePtr);
    }
}

std::string BundleInstallChecker::GetCheckResultMsg() const
{
    return checkResultMsg_;
}

void BundleInstallChecker::SetCheckResultMsg(const std::string checkResultMsg)
{
    checkResultMsg_ = checkResultMsg;
}

bool BundleInstallChecker::DetermineCloneApp(InnerBundleInfo &innerBundleInfo)
{
    BmsExtensionDataMgr bmsExtensionDataMgr;
    int32_t cloneNum = 0;
    if (!bmsExtensionDataMgr.DetermineCloneNum(
        innerBundleInfo.GetBundleName(), innerBundleInfo.GetAppIdentifier(), cloneNum) ||
        cloneNum == 0) {
        LOG_NOFUNC_W(BMS_TAG_INSTALLER, "DetermineCloneNum failed");
        return false;
    }
    MultiAppModeType currentMode = innerBundleInfo.GetMultiAppModeType();
    if (currentMode != MultiAppModeType::UNSPECIFIED && currentMode != MultiAppModeType::APP_CLONE) {
        auto dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
        if (dataMgr == nullptr) {
            LOG_NOFUNC_W(BMS_TAG_INSTALLER, "DetermineCloneApp dataMgr is null");
            return false;
        }
        /**
         * 1. If an app installed for the first time is not in cloning mode, no action is required.
         * 2. Forced app cloning cannot be upgraded to multi-instance, keep cloning mode.
         */
        MultiAppModeType installedMode;
        if (!dataMgr->GetMultiAppModeTypeByBundleName(innerBundleInfo.GetBundleName(), installedMode) ||
            installedMode != MultiAppModeType::APP_CLONE) {
            LOG_NOFUNC_I(BMS_TAG_INSTALLER, "%{public}s not installed or not clone mode no action required",
                innerBundleInfo.GetBundleName().c_str());
            return false;
        }
    }
    if (currentMode == MultiAppModeType::APP_CLONE &&
        innerBundleInfo.GetMultiAppMaxCount() >= cloneNum) {
        LOG_NOFUNC_W(BMS_TAG_INSTALLER, "%{public}s cloneNum is smaller no need to refresh",
            innerBundleInfo.GetBundleName().c_str());
        return false;
    }
    MultiAppModeData multiAppMode;
    multiAppMode.multiAppModeType = MultiAppModeType::APP_CLONE;
    multiAppMode.maxCount = std::min(cloneNum, Constants::CLONE_APP_INDEX_MAX);
    innerBundleInfo.SetMultiAppMode(multiAppMode);
    LOG_NOFUNC_I(BMS_TAG_INSTALLER, "DetermineCloneNum -n %{public}s -c %{public}d",
        innerBundleInfo.GetBundleName().c_str(), cloneNum);
    return true;
}

bool BundleInstallChecker::GetIsAbcCompressed() const
{
    return isAbcCompressed_;
}

void BundleInstallChecker::SetIsAbcCompressed(const bool &isAbcCompressed)
{
    isAbcCompressed_ = isAbcCompressed;
}
}  // namespace AppExecFwk
}  // namespace OHOS