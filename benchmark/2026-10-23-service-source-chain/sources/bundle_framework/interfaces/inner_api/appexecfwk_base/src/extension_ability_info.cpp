/*
 * Copyright (c) 2023-2025 Huawei Device Co., Ltd.
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

#include "extension_ability_info.h"

#include <fcntl.h>
#include <set>
#include <string>
#include <unistd.h>

#include "bundle_constants.h"
#include "common_json_converter.h"
#include "json_util.h"
#include "nlohmann/json.hpp"
#include "parcel_macro.h"
#include "string_ex.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
const uint32_t ABILITY_CAPACITY = 204800; // 200K

const std::unordered_map<std::string, ExtensionAbilityType> EXTENSION_TYPE_MAP = {
    { "form", ExtensionAbilityType::FORM },
    { "workScheduler", ExtensionAbilityType::WORK_SCHEDULER },
    { "inputMethod", ExtensionAbilityType::INPUTMETHOD },
    { "service", ExtensionAbilityType::SERVICE },
    { "accessibility", ExtensionAbilityType::ACCESSIBILITY },
    { "fence", ExtensionAbilityType::FENCE },
    { "dataShare", ExtensionAbilityType::DATASHARE },
    { "fileShare", ExtensionAbilityType::FILESHARE },
    { "staticSubscriber", ExtensionAbilityType::STATICSUBSCRIBER },
    { "wallpaper", ExtensionAbilityType::WALLPAPER },
    { "backup", ExtensionAbilityType::BACKUP },

    { "appService", ExtensionAbilityType::APP_SERVICE },
    { "distributed", ExtensionAbilityType::DISTRIBUTED },
    { "selection", ExtensionAbilityType::SELECTION },
    { "window", ExtensionAbilityType::WINDOW },
    { "enterpriseAdmin", ExtensionAbilityType::ENTERPRISE_ADMIN },
    { "fileAccess", ExtensionAbilityType::FILEACCESS_EXTENSION },
    { "thumbnail", ExtensionAbilityType::THUMBNAIL },
    { "preview", ExtensionAbilityType::PREVIEW },
    { "print", ExtensionAbilityType::PRINT },
    { "share", ExtensionAbilityType::SHARE },
    { "push", ExtensionAbilityType::PUSH },
    { "driver", ExtensionAbilityType::DRIVER },
    { "action", ExtensionAbilityType::ACTION },
    { "adsService", ExtensionAbilityType::ADS_SERVICE },
    { "embeddedUI", ExtensionAbilityType::EMBEDDED_UI },
    { "statusBarView", ExtensionAbilityType::STATUS_BAR_VIEW },
    { "insightIntentUI", ExtensionAbilityType::INSIGHT_INTENT_UI },
    { "autoFill/password", ExtensionAbilityType::AUTO_FILL_PASSWORD },
    { "appAccountAuthorization", ExtensionAbilityType::APP_ACCOUNT_AUTHORIZATION },
    { "ui", ExtensionAbilityType::UI },
    { "remoteNotification", ExtensionAbilityType::REMOTE_NOTIFICATION },
    { "remoteLocation", ExtensionAbilityType::REMOTE_LOCATION },
    { "voip", ExtensionAbilityType::VOIP },
    { "accountLogout", ExtensionAbilityType::ACCOUNTLOGOUT },
    { "sysDialog/userAuth", ExtensionAbilityType::SYSDIALOG_USERAUTH },
    { "sysDialog/common", ExtensionAbilityType::SYSDIALOG_COMMON },
    { "sysPicker/mediaControl", ExtensionAbilityType::SYSPICKER_MEDIACONTROL },
    { "sysDialog/atomicServicePanel", ExtensionAbilityType::SYSDIALOG_ATOMICSERVICEPANEL },
    { "sysDialog/power", ExtensionAbilityType::SYSDIALOG_POWER },
    { "sysPicker/share", ExtensionAbilityType::SYSPICKER_SHARE },
    { "hms/account", ExtensionAbilityType::HMS_ACCOUNT },
    { "ads", ExtensionAbilityType::ADS },
    { "sysDialog/meetimeCall", ExtensionAbilityType::SYSDIALOG_MEETIMECALL },
    { "sysDialog/meetimeContact", ExtensionAbilityType::SYSDIALOG_MEETIMECONTACT },
    { "sysDialog/meetimeMessage", ExtensionAbilityType::SYSDIALOG_MEETIMEMESSAGE },
    { "sysDialog/print", ExtensionAbilityType::SYSDIALOG_PRINT },
    { "sysPicker/meetimeContact", ExtensionAbilityType::SYSPICKER_MEETIMECONTACT },
    { "sysPicker/meetimeCallLog", ExtensionAbilityType::SYSPICKER_MEETIMECALLLOG },
    { "sysPicker/photoPicker", ExtensionAbilityType::SYSPICKER_PHOTOPICKER },
    { "sysPicker/navigation", ExtensionAbilityType::SYSPICKER_NAVIGATION },
    { "sysPicker/appSelector", ExtensionAbilityType::SYSPICKER_APPSELECTOR },
    { "sysPicker/camera", ExtensionAbilityType::SYSPICKER_CAMERA },
    { "sysPicker/filePicker", ExtensionAbilityType::SYSPICKER_FILEPICKER },
    { "sysPicker/audioPicker", ExtensionAbilityType::SYSPICKER_AUDIOPICKER },
    { "sys/commonUI", ExtensionAbilityType::SYS_COMMON_UI },
    { "vpn", ExtensionAbilityType::VPN },
    { "autoFill/smart", ExtensionAbilityType::AUTO_FILL_SMART },
    { "liveViewLockScreen", ExtensionAbilityType::LIVEVIEW_LOCKSCREEN },
    { "photoEditor", ExtensionAbilityType::PHOTO_EDITOR },
    { "callerInfoQuery", ExtensionAbilityType::CALLER_INFO_QUERY },
    { "sysPicker/photoEditor", ExtensionAbilityType::SYSPICKER_PHOTOEDITOR },
    { "sys/visualExtension", ExtensionAbilityType::SYS_VISUAL },

    { "recentPhoto", ExtensionAbilityType::RECENT_PHOTO },
    { "uiService", ExtensionAbilityType::UI_SERVICE },
    { "assetAcceleration", ExtensionAbilityType::ASSET_ACCELERATION },
    { "formEdit", ExtensionAbilityType::FORM_EDIT },
    { "liveForm", ExtensionAbilityType::LIVE_FORM },
    { "webNativeMessaging", ExtensionAbilityType::WEB_NATIVE_MESSAGING },
    { "faultLog", ExtensionAbilityType::FAULT_LOG },
    { "notificationSubscriber", ExtensionAbilityType::NOTIFICATION_SUBSCRIBER },
    { "crypto", ExtensionAbilityType::CRYPTO },
    { "awc/webpage", ExtensionAbilityType::AWC_WEBPAGE },
    { "awc/newsfeed", ExtensionAbilityType::AWC_NEWSFEED },
    { "contentEmbed", ExtensionAbilityType::CONTENT_EMBED },
    { "partnerAgent", ExtensionAbilityType::PARTNER_AGENT },
    { "embeddedCashier", ExtensionAbilityType::EMBEDDED_CASHIER }
};

// the new extension type does not need to be added here
const std::set<std::string> NOT_NEED_CREATE_SANBOX_MODE = {
    "form", "workScheduler", "service", "accessibility", "dataShare", "fileShare", "staticSubscriber", "wallpaper",
    "backup", "window", "enterpriseAdmin", "fileAccess", "thumbnail", "preview", "print", "share", "push", "driver",
    "action", "adsService", "embeddedUI", "insightIntentUI", "statusBarView", "autoFill/password",
    "appAccountAuthorization", "ui", "remoteNotification", "remoteLocation", "voip", "accountLogout",
    "sysDialog/userAuth", "sysDialog/common", "sysPicker/mediaControl", "sysDialog/atomicServicePanel",
    "sysDialog/power", "sysPicker/share", "hms/account", "ads", "sysDialog/meetimeCall",
    "sysDialog/meetimeContact", "sysDialog/meetimeMessage", "sysDialog/print", "sysPicker/meetimeContact",
    "sysPicker/meetimeCallLog", "sysPicker/photoPicker", "sysPicker/camera", "sysPicker/navigation",
    "sysPicker/appSelector", "sys/commonUI", "vpn", "autoFill/smart", "liveViewLockScreen","partnerAgent"
};

const std::unordered_map<std::string, ExtensionProcessMode> EXTENSION_PROCESS_MODE_MAP = {
    { "instance", ExtensionProcessMode::INSTANCE },
    { "type", ExtensionProcessMode::TYPE },
    { "bundle", ExtensionProcessMode::BUNDLE },
    { "runWithMainProcess", ExtensionProcessMode::RUN_WITH_MAIN_PROCESS }
};

bool ReadSkillInfoFromParcel(Parcel &parcel, std::vector<SkillUriForAbilityAndExtension> &skillUri)
{
    int32_t skillUriSize = 0;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, skillUriSize);
    CONTAINER_SECURITY_VERIFY(parcel, skillUriSize, &skillUri);
    for (auto i = 0; i < skillUriSize; i++) {
        SkillUriForAbilityAndExtension stctUri;
        stctUri.scheme = Str16ToStr8(parcel.ReadString16());
        stctUri.host = Str16ToStr8(parcel.ReadString16());
        stctUri.port = Str16ToStr8(parcel.ReadString16());
        stctUri.path = Str16ToStr8(parcel.ReadString16());
        stctUri.pathStartWith = Str16ToStr8(parcel.ReadString16());
        stctUri.pathRegex = Str16ToStr8(parcel.ReadString16());
        stctUri.type = Str16ToStr8(parcel.ReadString16());
        stctUri.utd = Str16ToStr8(parcel.ReadString16());
        stctUri.maxFileSupported = parcel.ReadInt32();
        stctUri.linkFeature = Str16ToStr8(parcel.ReadString16());
        stctUri.isMatch = parcel.ReadBool();
        skillUri.emplace_back(stctUri);
    }
    return true;
}

bool ReadMetadataFromParcel(Parcel &parcel, std::vector<Metadata> &metadata)
{
    int32_t metadataSize = 0;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, metadataSize);
    CONTAINER_SECURITY_VERIFY(parcel, metadataSize, &metadata);
    for (auto i = 0; i < metadataSize; i++) {
        std::unique_ptr<Metadata> meta(parcel.ReadParcelable<Metadata>());
        if (!meta) {
            APP_LOGE("ReadParcelable<Metadata> failed");
            return false;
        }
        metadata.emplace_back(*meta);
    }
    return true;
}
}; // namespace

bool ExtensionAbilityInfo::ReadFromParcel(Parcel &parcel)
{
    bundleName = Str16ToStr8(parcel.ReadString16());
    moduleName = Str16ToStr8(parcel.ReadString16());
    name = Str16ToStr8(parcel.ReadString16());
    srcEntrance = Str16ToStr8(parcel.ReadString16());
    icon = Str16ToStr8(parcel.ReadString16());
    iconId = parcel.ReadUint32();
    label = Str16ToStr8(parcel.ReadString16());
    labelId = parcel.ReadUint32();
    description = Str16ToStr8(parcel.ReadString16());
    descriptionId = parcel.ReadUint32();
    priority = parcel.ReadInt32();
    int32_t permissionsSize;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, permissionsSize);
    CONTAINER_SECURITY_VERIFY(parcel, permissionsSize, &permissions);
    for (auto i = 0; i < permissionsSize; i++) {
        permissions.emplace_back(Str16ToStr8(parcel.ReadString16()));
    }
    int32_t appIdentifierAllowListSize;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, appIdentifierAllowListSize);
    CONTAINER_SECURITY_VERIFY(parcel, appIdentifierAllowListSize, &appIdentifierAllowList);
    for (auto i = 0; i < appIdentifierAllowListSize; i++) {
        appIdentifierAllowList.emplace_back(Str16ToStr8(parcel.ReadString16()));
    }
    readPermission = Str16ToStr8(parcel.ReadString16());
    writePermission = Str16ToStr8(parcel.ReadString16());
    uri = Str16ToStr8(parcel.ReadString16());
    type = static_cast<ExtensionAbilityType>(parcel.ReadInt32());
    extensionTypeName = Str16ToStr8(parcel.ReadString16());
    visible = parcel.ReadBool();
    if (!ReadMetadataFromParcel(parcel, metadata)) {
        APP_LOGE("Read meta data failed");
        return false;
    }

    std::unique_ptr<ApplicationInfo> appInfo(parcel.ReadParcelable<ApplicationInfo>());
    if (!appInfo) {
        APP_LOGE("ReadParcelable<ApplicationInfo> failed");
        return false;
    }
    applicationInfo = *appInfo;

    resourcePath = Str16ToStr8(parcel.ReadString16());
    hapPath = Str16ToStr8(parcel.ReadString16());
    enabled = parcel.ReadBool();
    process = Str16ToStr8(parcel.ReadString16());
    compileMode = static_cast<CompileMode>(parcel.ReadInt32());
    uid = parcel.ReadInt32();
    appIndex = parcel.ReadInt32();
    if (!ReadSkillInfoFromParcel(parcel, skillUri)) {
        APP_LOGE("Read skill info failed");
        return false;
    }
    extensionProcessMode = static_cast<ExtensionProcessMode>(parcel.ReadInt32());
    int32_t skillsSize;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, skillsSize);
    CONTAINER_SECURITY_VERIFY(parcel, skillsSize, &skills);
    for (auto i = 0; i < skillsSize; i++) {
        std::unique_ptr<Skill> extensionSkillPtr(parcel.ReadParcelable<Skill>());
        if (!extensionSkillPtr) {
            APP_LOGE("ReadParcelable<SkillForExtension> failed");
            return false;
        }
        skills.emplace_back(*extensionSkillPtr);
    }

    needCreateSandbox = parcel.ReadBool();
    isolationProcess = parcel.ReadBool();
    int32_t dataGroupIdsSize;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, dataGroupIdsSize);
    CONTAINER_SECURITY_VERIFY(parcel, dataGroupIdsSize, &dataGroupIds);
    for (auto i = 0; i < dataGroupIdsSize; i++) {
        dataGroupIds.emplace_back(Str16ToStr8(parcel.ReadString16()));
    }
    int32_t validDataGroupIdsSize;
    READ_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, validDataGroupIdsSize);
    CONTAINER_SECURITY_VERIFY(parcel, validDataGroupIdsSize, &validDataGroupIds);
    for (auto i = 0; i < validDataGroupIdsSize; i++) {
        validDataGroupIds.emplace_back(Str16ToStr8(parcel.ReadString16()));
    }
    customProcess = Str16ToStr8(parcel.ReadString16());
    arkTSMode = parcel.ReadString();
    return true;
}

ExtensionAbilityInfo *ExtensionAbilityInfo::Unmarshalling(Parcel &parcel)
{
    ExtensionAbilityInfo *info = new (std::nothrow) ExtensionAbilityInfo();
    if (info && !info->ReadFromParcel(parcel)) {
        APP_LOGW("read from parcel failed");
        delete info;
        info = nullptr;
    }
    return info;
}

bool ExtensionAbilityInfo::MarshallingSkillUri(Parcel &parcel, SkillUriForAbilityAndExtension uri) const
{
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.scheme));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.host));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.port));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.path));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.pathStartWith));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.pathRegex));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.type));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.utd));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, uri.maxFileSupported);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri.linkFeature));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Bool, parcel, uri.isMatch);
    return true;
}

bool ExtensionAbilityInfo::Marshalling(Parcel &parcel) const
{
    CHECK_PARCEL_CAPACITY(parcel, ABILITY_CAPACITY);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(bundleName));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(moduleName));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(name));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(srcEntrance));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(icon));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Uint32, parcel, iconId);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(label));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Uint32, parcel, labelId);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(description));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Uint32, parcel, descriptionId);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, priority);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, permissions.size());
    for (auto &permission : permissions) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(permission));
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, appIdentifierAllowList.size());
    for (auto &appIdentifier : appIdentifierAllowList) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(appIdentifier));
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(readPermission));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(writePermission));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(uri));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, static_cast<int32_t>(type));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(extensionTypeName));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Bool, parcel, visible);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, metadata.size());
    for (auto &mete : metadata) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Parcelable, parcel, &mete);
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Parcelable, parcel, &applicationInfo);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(resourcePath));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(hapPath));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Bool, parcel, enabled);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(process));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, static_cast<int32_t>(compileMode));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, uid);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, appIndex);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, skillUri.size());
    for (auto &uri : skillUri) {
        MarshallingSkillUri(parcel, uri);
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, static_cast<int32_t>(extensionProcessMode));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, skills.size());
    for (auto &skill : skills) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Parcelable, parcel, &skill);
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Bool, parcel, needCreateSandbox);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Bool, parcel, isolationProcess);
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, dataGroupIds.size());
    for (auto &dataGroupId : dataGroupIds) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(dataGroupId));
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(Int32, parcel, validDataGroupIds.size());
    for (auto &dataGroupId : validDataGroupIds) {
        WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(dataGroupId));
    }
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String16, parcel, Str8ToStr16(customProcess));
    WRITE_PARCEL_AND_RETURN_FALSE_IF_FAIL(String, parcel, arkTSMode);
    return true;
}

void to_json(nlohmann::json &jsonObject, const ExtensionAbilityInfo &extensionInfo)
{
    APP_LOGD("ExtensionAbilityInfo to_json begin");
    ExtensionToJson(jsonObject, extensionInfo);
}

void from_json(const nlohmann::json &jsonObject, ExtensionAbilityInfo &extensionInfo)
{
    APP_LOGD("ExtensionAbilityInfo from_json begin");
    ExtensionFromJson(jsonObject, extensionInfo);
}

ExtensionAbilityType ConvertToExtensionAbilityType(const std::string &type)
{
    if (EXTENSION_TYPE_MAP.find(type) != EXTENSION_TYPE_MAP.end()) {
        return EXTENSION_TYPE_MAP.at(type);
    }

    return ExtensionAbilityType::UNSPECIFIED;
}

std::string ConvertToExtensionTypeName(ExtensionAbilityType type)
{
    for (const auto &[key, val] : EXTENSION_TYPE_MAP) {
        if (val == type) {
            return key;
        }
    }

    return "Unspecified";
}

ExtensionProcessMode ConvertToExtensionProcessMode(const std::string &extensionProcessMode)
{
    if (EXTENSION_PROCESS_MODE_MAP.find(extensionProcessMode) != EXTENSION_PROCESS_MODE_MAP.end()) {
        return EXTENSION_PROCESS_MODE_MAP.at(extensionProcessMode);
    }

    return ExtensionProcessMode::UNDEFINED;
}

void ExtensionAbilityInfo::UpdateNeedCreateSandbox()
{
    needCreateSandbox = false;
}
}  // namespace AppExecFwk
}  // namespace OHOS
