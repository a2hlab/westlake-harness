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

#include "bundle_resource_manager.h"

#include "account_helper.h"
#include "bms_extension_client.h"
#include "bundle_common_event_mgr.h"
#include "bundle_permission_mgr.h"
#include "bundle_util.h"
#include "bundle_resource_parser.h"
#include "bundle_resource_process.h"
#include "bundle_resource_theme_process.h"
#include "bundle_mgr_service.h"
#include "directory_ex.h"
#include "event_report.h"
#include "hitrace_meter.h"
#include "thread_pool.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
constexpr const char* GLOBAL_RESOURCE_BUNDLE_NAME = "ohos.global.systemres";
constexpr int8_t MAX_TASK_NUMBER = 2;
constexpr const char* THREAD_POOL_NAME = "BundleResourceThreadPool";
constexpr int8_t CHECK_INTERVAL = 30; // 30ms
constexpr const char* FOUNDATION_PROCESS_NAME = "foundation";
constexpr int8_t SCENE_ID_UPDATE_RESOURCE = 1 << 1;
constexpr const char* TASK_NAME = "ReleaseResourceTask";
constexpr uint64_t DELAY_TIME_MILLI_SECONDS = 3 * 60 * 1000; // 3mins
constexpr const char* CONTACTS_BUNDLE_NAME = "com.ohos.contacts";
using Want = OHOS::AAFwk::Want;
}
std::mutex BundleResourceManager::g_sysResMutex;
std::shared_ptr<Global::Resource::ResourceManager> BundleResourceManager::g_resMgr = nullptr;

BundleResourceManager::BundleResourceManager()
{
    bundleResourceRdb_ = std::make_shared<BundleResourceRdb>();
    bundleResourceIconRdb_ = std::make_shared<BundleResourceIconRdb>();
    uninstallBundleResourceRdb_ = std::make_shared<UninstallBundleResourceRdb>();
    delayedTaskMgr_ = std::make_shared<SingleDelayedTaskMgr>(TASK_NAME, DELAY_TIME_MILLI_SECONDS);
}

BundleResourceManager::~BundleResourceManager()
{
}

void BundleResourceManager::DeleteNotExistResourceInfo(
    const std::string &bundleName, const int32_t appIndex, const std::vector<ResourceInfo> &resourceInfos)
{
    // get current rdb resource
    std::vector<std::string> existResourceName;
    if (bundleResourceRdb_->GetResourceNameByBundleName(bundleName, appIndex, existResourceName) &&
        !existResourceName.empty()) {
        for (const auto &key : existResourceName) {
            auto it = std::find_if(resourceInfos.begin(), resourceInfos.end(),
                [&key](const ResourceInfo &info) {
                return info.GetKey() == key;
            });
            if (it == resourceInfos.end()) {
                bundleResourceRdb_->DeleteResourceInfo(key);
            }
        }
    }
}

bool BundleResourceManager::DeleteAllResourceInfo()
{
    return bundleResourceRdb_->DeleteAllResourceInfo();
}

void BundleResourceManager::InnerProcessResourceInfoBySystemLanguageChanged(
    std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap)
{
    for (auto iter = resourceInfosMap.begin(); iter != resourceInfosMap.end(); ++iter) {
        for (auto &resourceInfo : iter->second) {
            resourceInfo.iconNeedParse_ = false;
        }
    }
}

void BundleResourceManager::DeleteNotExistResourceInfo(
    const std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap,
    const std::vector<std::string> &existResourceNames)
{
    // delete not exist resource
    for (const auto &name : existResourceNames) {
        if (resourceInfosMap.find(name) == resourceInfosMap.end()) {
            ResourceInfo resourceInfo;
            resourceInfo.ParseKey(name);
            // main bundle not exist
            if (resourceInfo.appIndex_ == 0) {
                DeleteResourceInfo(name);
                continue;
            }
            auto iter = resourceInfosMap.find(resourceInfo.bundleName_);
            // main bundle not exist
            if ((iter == resourceInfosMap.end()) || (iter->second.empty())) {
                DeleteResourceInfo(name);
                continue;
            }
            // clone bundle appIndex not exist
            if (std::find(iter->second[0].appIndexes_.begin(), iter->second[0].appIndexes_.end(),
                resourceInfo.appIndex_) == iter->second[0].appIndexes_.end()) {
                DeleteResourceInfo(name);
            }
        }
    }
}

bool BundleResourceManager::DeleteResourceInfo(const std::string &key)
{
    return bundleResourceRdb_->DeleteResourceInfo(key);
}

bool BundleResourceManager::GetAllResourceName(std::vector<std::string> &keyNames)
{
    return bundleResourceRdb_->GetAllResourceName(keyNames);
}

bool BundleResourceManager::GetBundleResourceInfo(const std::string &bundleName, const uint32_t flags,
    BundleResourceInfo &bundleResourceInfo, int32_t appIndex)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGD("start, bundleName:%{public}s", bundleName.c_str());
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (bundleResourceRdb_->GetBundleResourceInfo(bundleName, resourceFlags, bundleResourceInfo, appIndex)) {
        APP_LOGD("success, bundleName:%{public}s", bundleName.c_str());
        if (IsNeedProcessResourceIconInfo(resourceFlags)) {
            int32_t userId = GetUserId();
            std::vector<LauncherAbilityResourceInfo> resourceIconInfos;
            if (!bundleResourceIconRdb_->GetResourceIconInfos(bundleName, userId, appIndex, resourceFlags,
                resourceIconInfos) || resourceIconInfos.empty()) {
                return true;
            }
            if (bundleName == CONTACTS_BUNDLE_NAME) {
                BundleResourceThemeProcess::ProcessSpecialBundleResource(resourceIconInfos, bundleResourceInfo);
                return true;
            }
            auto iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                [bundleName, appIndex](const auto &resourceIconInfo) {
                    return ((resourceIconInfo.bundleName == bundleName) &&
                        (resourceIconInfo.appIndex == appIndex));
                });
            if (iter != resourceIconInfos.end()) {
                bundleResourceInfo.icon = iter->icon;
                bundleResourceInfo.foreground = iter->foreground;
                bundleResourceInfo.background = iter->background;
            }
        }
        return true;
    }
    auto bmsExtensionClient = std::make_shared<BmsExtensionClient>();
    ErrCode ret = bmsExtensionClient->GetBundleResourceInfo(bundleName, resourceFlags, bundleResourceInfo, appIndex);
    if (ret == ERR_OK) {
        APP_LOGD("success, bundleName:%{public}s", bundleName.c_str());
        return true;
    }
    APP_LOGE_NOFUNC("%{public}s not exist in resource rdb", bundleName.c_str());
    return false;
}

bool BundleResourceManager::GetSingleLauncherAbilityResourceInfo(const std::string &bundleName, const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfo, const int32_t appIndex)
{
    APP_LOGD("start, bundleName:%{public}s", bundleName.c_str());
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (bundleResourceRdb_->GetLauncherAbilityResourceInfo(bundleName, flags,
        launcherAbilityResourceInfo, appIndex)) {
        if (IsNeedProcessResourceIconInfo(flags)) {
            int32_t userId = GetUserId();
            std::vector<LauncherAbilityResourceInfo> resourceIconInfos;
            if (!bundleResourceIconRdb_->GetResourceIconInfos(bundleName, userId, appIndex, flags,
                resourceIconInfos) || resourceIconInfos.empty()) {
                return true;
            }
            for (auto &resource : launcherAbilityResourceInfo) {
                auto iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                    [&resource](const auto &resourceIconInfo) {
                        return ((resource.bundleName == resourceIconInfo.bundleName) &&
                            (resource.moduleName == resourceIconInfo.moduleName) &&
                            (resource.abilityName == resourceIconInfo.abilityName) &&
                            (resource.appIndex == resourceIconInfo.appIndex));
                    });
                if (iter == resourceIconInfos.end()) {
                    iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                        [&resource](const auto &resourceIconInfo) {
                            return ((resource.bundleName == resourceIconInfo.bundleName) &&
                                (resource.appIndex == resourceIconInfo.appIndex));
                        });
                }
                if (iter != resourceIconInfos.end()) {
                    resource.icon = iter->icon;
                    resource.foreground = iter->foreground;
                    resource.background = iter->background;
                }
            }
        }
        return true;
    }
    return false;
}

bool BundleResourceManager::GetLauncherAbilityResourceInfo(const std::string &bundleName, const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfo, const int32_t appIndex)
{
    APP_LOGD("start, bundleName:%{public}s", bundleName.c_str());
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (GetSingleLauncherAbilityResourceInfo(bundleName, resourceFlags, launcherAbilityResourceInfo, appIndex)) {
        return true;
    }
    auto bmsExtensionClient = std::make_shared<BmsExtensionClient>();
    ErrCode ret = bmsExtensionClient->GetLauncherAbilityResourceInfo(bundleName, resourceFlags,
        launcherAbilityResourceInfo, appIndex);
    if (ret == ERR_OK) {
        APP_LOGD("success, bundleName:%{public}s", bundleName.c_str());
        return true;
    }
    APP_LOGE_NOFUNC("%{public}s not exist in resource rdb", bundleName.c_str());
    return false;
}

bool BundleResourceManager::GetAllBundleResourceInfo(const uint32_t flags,
    std::vector<BundleResourceInfo> &bundleResourceInfos)
{
    APP_LOGD("start");
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (bundleResourceRdb_->GetAllBundleResourceInfo(resourceFlags, bundleResourceInfos)) {
        if (IsNeedProcessResourceIconInfo(resourceFlags)) {
            int32_t userId = GetUserId();
            std::vector<LauncherAbilityResourceInfo> resourceIconInfos;
            if (!bundleResourceIconRdb_->GetAllResourceIconInfo(userId, resourceFlags, resourceIconInfos) ||
                resourceIconInfos.empty()) {
                return true;
            }
            for (auto &resource : bundleResourceInfos) {
                if (resource.bundleName == CONTACTS_BUNDLE_NAME) {
                    BundleResourceThemeProcess::ProcessSpecialBundleResource(resourceIconInfos, resource);
                    continue;
                }
                auto iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                    [&resource](const auto &resourceIconInfo) {
                        return ((resource.bundleName == resourceIconInfo.bundleName) &&
                            (resource.appIndex == resourceIconInfo.appIndex));
                    });
                if (iter != resourceIconInfos.end()) {
                    resource.icon = iter->icon;
                    resource.foreground = iter->foreground;
                    resource.background = iter->background;
                }
            }
        }
        return true;
    }
    return false;
}

bool BundleResourceManager::GetAllLauncherAbilityResourceInfo(const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfos)
{
    APP_LOGD("start");
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (bundleResourceRdb_->GetAllLauncherAbilityResourceInfo(resourceFlags, launcherAbilityResourceInfos)) {
        if (IsNeedProcessResourceIconInfo(resourceFlags)) {
            int32_t userId = GetUserId();
            std::vector<LauncherAbilityResourceInfo> resourceIconInfos;
            if (!bundleResourceIconRdb_->GetAllResourceIconInfo(userId, resourceFlags, resourceIconInfos) ||
                resourceIconInfos.empty()) {
                return true;
            }
            for (auto &resource : launcherAbilityResourceInfos) {
                auto iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                    [&resource](const auto &resourceIconInfo) {
                        return ((resource.bundleName == resourceIconInfo.bundleName) &&
                            (resource.moduleName == resourceIconInfo.moduleName) &&
                            (resource.abilityName == resourceIconInfo.abilityName) &&
                            (resource.appIndex == resourceIconInfo.appIndex));
                    });
                if (iter == resourceIconInfos.end()) {
                    iter = std::find_if(resourceIconInfos.begin(), resourceIconInfos.end(),
                        [&resource](const auto &resourceIconInfo) {
                            return ((resource.bundleName == resourceIconInfo.bundleName) &&
                                (resource.appIndex == resourceIconInfo.appIndex));
                        });
                }
                if (iter != resourceIconInfos.end()) {
                    resource.icon = iter->icon;
                    resource.foreground = iter->foreground;
                    resource.background = iter->background;
                }
            }
        }
        return true;
    }
    return false;
}

bool BundleResourceManager::FilterLauncherAbilityResourceInfoWithFlag(const uint32_t flags,
    const std::string &bundleName, std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfos)
{
    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ONLY_WITH_MAIN_ABILITY)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ONLY_WITH_MAIN_ABILITY)) {
        std::vector<AbilityInfo> abilityInfos;
        if (!GetLauncherAbilityInfos(bundleName, abilityInfos)) {
            launcherAbilityResourceInfos.clear();
            APP_LOGE("GetLauncherAbilityInfos failed");
            return false;
        }
        launcherAbilityResourceInfos.erase(
            std::remove_if(launcherAbilityResourceInfos.begin(), launcherAbilityResourceInfos.end(),
                [this, &abilityInfos](const LauncherAbilityResourceInfo& resource) {
                    return !this->IsLauncherAbility(resource, abilityInfos);
                }),
            launcherAbilityResourceInfos.end()
        );
    }
    return true;
}

bool BundleResourceManager::GetLauncherAbilityInfos(const std::string &bundleName,
    std::vector<AbilityInfo> &abilityInfos)
{
    int32_t userId = GetUserId();
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return false;
    }
    Want want;
    want.SetAction(Want::ACTION_HOME);
    want.AddEntity(Want::ENTITY_HOME);
    if (!bundleName.empty()) {
        ElementName elementName;
        elementName.SetBundleName(bundleName);
        want.SetElement(elementName);
    }
    ErrCode ret = dataMgr->QueryLauncherAbilityInfos(want, userId, abilityInfos);
    auto bmsExtensionClient = std::make_shared<BmsExtensionClient>();
    ErrCode ans = bmsExtensionClient->QueryLauncherAbility(want, userId, abilityInfos);
    if (ret != ERR_OK && ans != ERR_OK) {
        APP_LOGE("GetLauncherAbilityInfos failed, ret:%{public}d, ans:%{public}d", ret, ans);
        return false;
    }
    return true;
}

bool BundleResourceManager::IsLauncherAbility(const LauncherAbilityResourceInfo &resourceInfo,
    std::vector<AbilityInfo> &abilityInfos)
{
    for (const auto& abilityInfo : abilityInfos) {
        if (resourceInfo.bundleName == abilityInfo.bundleName &&
            resourceInfo.moduleName == abilityInfo.moduleName &&
            resourceInfo.abilityName == abilityInfo.name) {
            return true;
        }
    }
    return false;
}

uint32_t BundleResourceManager::CheckResourceFlags(const uint32_t flags)
{
    APP_LOGD("flags:%{public}u", flags);
    if (((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ||
        ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL)) ||
        ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ||
        ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ||
        ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ONLY_WITH_MAIN_ABILITY)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ONLY_WITH_MAIN_ABILITY))) {
        return flags;
    }
    APP_LOGD("illegal flags");
    return flags | static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL);
}

void BundleResourceManager::ProcessResourceInfoWhenParseFailed(ResourceInfo &resourceInfo)
{
    APP_LOGI("start, bundleName:%{public}s", resourceInfo.bundleName_.c_str());
    if (resourceInfo.label_.empty()) {
        resourceInfo.label_ = resourceInfo.bundleName_;
    }
    if (resourceInfo.bundleName_ == GLOBAL_RESOURCE_BUNDLE_NAME) {
        APP_LOGE("%{public}s default resource parse failed", resourceInfo.bundleName_.c_str());
        return;
    }
    if (resourceInfo.icon_.empty()) {
        GetDefaultIcon(resourceInfo);
    }
}

void BundleResourceManager::GetDefaultIcon(ResourceInfo &resourceInfo)
{
    BundleResourceInfo bundleResourceInfo;
    if (!GetBundleResourceInfo(GLOBAL_RESOURCE_BUNDLE_NAME,
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON) |
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR),
        bundleResourceInfo)) {
        APP_LOGE("get default icon failed");
        return;
    }
    resourceInfo.icon_ = bundleResourceInfo.icon;
    resourceInfo.foreground_ = bundleResourceInfo.foreground;
    resourceInfo.background_ = bundleResourceInfo.background;
}

void BundleResourceManager::SendBundleResourcesChangedEvent(const int32_t userId, const uint32_t type)
{
    APP_LOGI("send bundleResource event, userId:%{public}d type:%{public}u", userId, type);
    std::shared_ptr<BundleCommonEventMgr> commonEventMgr = std::make_shared<BundleCommonEventMgr>();
    commonEventMgr->NotifyBundleResourcesChanged(userId, type);
}

void BundleResourceManager::GetTargetBundleName(const std::string &bundleName, std::string &targetBundleName)
{
    APP_LOGD("start");
    BundleResourceProcess::GetTargetBundleName(bundleName, targetBundleName);
}

bool BundleResourceManager::GetBundleResourceInfoForCloneBundle(const std::string &bundleName,
    const int32_t appIndex, const uint32_t type, std::vector<ResourceInfo> &resourceInfos)
{
    uint32_t flags = 0;
    if ((type & static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_THEME_CHANGE)) ==
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_THEME_CHANGE)) {
        flags |= static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR) |
            static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON);
    }
    if ((type & static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE)) ==
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE)) {
        flags |= static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL);
    }
    // 1. get main bundle resource info
    BundleResourceInfo bundleResourceInfo;
    if (!bundleResourceRdb_->GetBundleResourceInfo(bundleName, flags, bundleResourceInfo)) {
        APP_LOGE("get resource failed %{public}s appIndex:%{public}d", bundleName.c_str(), appIndex);
        return false;
    }
    bundleResourceInfo.appIndex = appIndex;
    ResourceInfo bundleResource;
    bundleResource.ConvertFromBundleResourceInfo(bundleResourceInfo);
    resourceInfos.emplace_back(bundleResource);
    // 2. get main launcher ability resource info
    std::vector<LauncherAbilityResourceInfo> launcherAbilityResourceInfos;
    if (!bundleResourceRdb_->GetLauncherAbilityResourceInfo(bundleName, flags, launcherAbilityResourceInfos)) {
        APP_LOGW("get ability resource failed %{public}s appIndex:%{public}d",
            bundleName.c_str(), appIndex);
    }
    for (auto &launcherAbility : launcherAbilityResourceInfos) {
        launcherAbility.appIndex = appIndex;
        ResourceInfo launcherResource;
        launcherResource.ConvertFromLauncherAbilityResourceInfo(launcherAbility);
        resourceInfos.emplace_back(launcherResource);
    }
    // 3. get extension ability resource info
    std::vector<LauncherAbilityResourceInfo> extensionAbilityResourceInfos;
    bundleResourceRdb_->GetAllExtensionAbilityResourceInfo(bundleName, flags, extensionAbilityResourceInfos);
    for (auto &extensionAbility : extensionAbilityResourceInfos) {
        extensionAbility.appIndex = appIndex;
        ResourceInfo extensionResource;
        extensionResource.ConvertFromLauncherAbilityResourceInfo(extensionAbility);
        resourceInfos.emplace_back(extensionResource);
    }
    APP_LOGI("%{public}s appIndex:%{public}d add resource size:%{public}zu", bundleName.c_str(), appIndex,
        resourceInfos.size());
    return true;
}

bool BundleResourceManager::DeleteNotExistResourceInfo()
{
    APP_LOGD("start delete not exist resource");
    return bundleResourceRdb_->DeleteNotExistResourceInfo();
}

bool BundleResourceManager::GetExtensionAbilityResourceInfo(const std::string &bundleName,
    const ExtensionAbilityType extensionAbilityType, const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &extensionAbilityResourceInfo, const int32_t appIndex)
{
    APP_LOGD("start, bundleName:%{public}s", bundleName.c_str());
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (bundleResourceRdb_->GetExtensionAbilityResourceInfo(bundleName, extensionAbilityType, resourceFlags,
        extensionAbilityResourceInfo, appIndex)) {
        return true;
    }
    APP_LOGE_NOFUNC("%{public}s extension ability %{public}d not exist in resource rdb", bundleName.c_str(),
        extensionAbilityType);
    return false;
}

void BundleResourceManager::ProcessResourceInfoNoNeedToParseOtherIcon(std::vector<ResourceInfo> &resourceInfos)
{
    size_t size = resourceInfos.size();
    for (size_t index = 0; index < size; ++index) {
        // theme changed no need parse label
        resourceInfos[index].labelNeedParse_ = false;
        resourceInfos[index].label_ = Constants::EMPTY_STRING;
        if ((index > 0) && ServiceConstants::ALLOW_MULTI_ICON_BUNDLE.find(resourceInfos[0].bundleName_) ==
            ServiceConstants::ALLOW_MULTI_ICON_BUNDLE.end()) {
            // only need parse once
            resourceInfos[index].iconNeedParse_ = false;
        }
    }
}

void BundleResourceManager::PrepareSysRes()
{
    {
        std::lock_guard<std::mutex> guard(g_sysResMutex);
        if (!g_resMgr) {
            g_resMgr = std::shared_ptr<Global::Resource::ResourceManager>(
                Global::Resource::CreateResourceManager());
            APP_LOGI("get system resource");
        }
    }
    auto task = [] {
        std::lock_guard<std::mutex> guard(g_sysResMutex);
        g_resMgr = nullptr;
        APP_LOGI("release system resource");
    };
    delayedTaskMgr_->ScheduleDelayedTask(task);
}

bool BundleResourceManager::AddResourceInfoByBundleNameWhenInstall(
    const std::string &bundleName, const int32_t userId, const bool isBundleFirstInstall)
{
    // 1. get all resourceInfos by bundleName
    std::vector<ResourceInfo> resourceInfos;
    if (!BundleResourceProcess::GetResourceInfoByBundleName(bundleName, userId, resourceInfos, 0, false)) {
        APP_LOGE("get resource by -n %{public}s -u %{public}d failed", bundleName.c_str(), userId);
        return false;
    }
    // not first install need delete resource
    if (!isBundleFirstInstall) {
        DeleteNotExistResourceInfo(bundleName, 0, resourceInfos);
    }
    PrepareSysRes();
    // 2. parse icon and label resource with hap files
    BundleResourceParser parser;
    if (!parser.ParseResourceInfosNoTheme(userId, resourceInfos)) {
        APP_LOGW_NOFUNC("-n %{public}s Parse failed, need to modify label and icon", bundleName.c_str());
        ProcessResourceInfoWhenParseFailed(resourceInfos[0]);
    }
    // 3. add original resource information to bundleResourceRdb
    bool ret = bundleResourceRdb_->AddResourceInfos(resourceInfos);
    if (!ret) {
        APP_LOGE("add resource failed when install -n %{public}s -u %{public}d", bundleName.c_str(), userId);
    }
    // 4. if isBundleFirstInstall false, need to process clone bundle resource
    if (!isBundleFirstInstall && !resourceInfos.empty() && !resourceInfos[0].appIndexes_.empty()) {
        for (const int32_t appIndex : resourceInfos[0].appIndexes_) {
            DeleteNotExistResourceInfo(bundleName, appIndex, resourceInfos);
            // update clone bundle, label and icon
            (void)ProcessCloneBundleResourceInfo(resourceInfos[0].bundleName_, appIndex);
        }
    }
    // 5. if theme not exist, then return
    if (!BundleResourceThemeProcess::IsBundleThemeExist(bundleName, userId)) {
        return ret;
    }
    std::vector<ResourceInfo> themeResourceInfos;
    themeResourceInfos.emplace_back(resourceInfos[0]);
    // 5. traverse all resourceInfo to determine if ability theme exist
    for (const auto &resource : resourceInfos) {
        if (BundleResourceThemeProcess::IsAbilityThemeExist(resource.bundleName_, resource.moduleName_,
            resource.abilityName_, userId)) {
            themeResourceInfos.emplace_back(resource);
        }
    }
    // clear icon data
    for (auto resource : themeResourceInfos) {
        resource.icon_ = "";
        resource.foreground_.clear();
        resource.background_.clear();
    }
    // 6. parse resource with theme
    if (!parser.ParseIconResourceInfosWithTheme(userId, themeResourceInfos)) {
        APP_LOGE("parse theme resource failed -n %{public}s -u %{public}d", bundleName.c_str(), userId);
        return false;
    }
    // 7. add theme resource to bundleResourceIconRdb
    if (!bundleResourceIconRdb_->AddResourceIconInfos(userId, IconResourceType::THEME_ICON, themeResourceInfos)) {
        APP_LOGE("add theme resource failed -n %{public}s -u %{public}d", bundleName.c_str(), userId);
        return false;
    }
    return ret;
}

bool BundleResourceManager::AddResourceInfoByBundleNameWhenUpdate(
    const std::string &bundleName, const int32_t userId)
{
    // 1. get all resource
    std::vector<ResourceInfo> resourceInfos;
    if (!BundleResourceProcess::GetResourceInfoByBundleName(bundleName, userId, resourceInfos, 0, false) ||
        resourceInfos.empty()) {
        APP_LOGE("get resource bundleName %{public}s userId %{public}d failed",
            bundleName.c_str(), userId);
        return false;
    }
    // 2. delete ability resource when update, module or ability may changed
    DeleteNotExistResourceInfo(bundleName, 0, resourceInfos);
    PrepareSysRes();
    // 3. parse icon and label resource with hap files
    BundleResourceParser parser;
    if (!parser.ParseResourceInfosNoTheme(userId, resourceInfos)) {
        APP_LOGW_NOFUNC("key:%{public}s Parse failed, need to modify label and icon",
            resourceInfos[0].GetKey().c_str());
        ProcessResourceInfoWhenParseFailed(resourceInfos[0]);
    }
    // 4. add original resource information to bundleResourceRdb
    bool ret = bundleResourceRdb_->AddResourceInfos(resourceInfos);
    if (!ret) {
        APP_LOGE("add resource failed when update -n %{public}s -u %{public}d", bundleName.c_str(), userId);
    }
    /**
     * 5. no need to consider theme and dynamic icon when bundle update,
     * need to update clone bundle resource (original resource information) in bundleResourceRdb
     */
    if (!resourceInfos.empty() && !resourceInfos[0].appIndexes_.empty()) {
        for (const int32_t appIndex : resourceInfos[0].appIndexes_) {
            DeleteNotExistResourceInfo(bundleName, appIndex, resourceInfos);
            // 6. update clone bundle, label and icon
            if (!ProcessCloneBundleResourceInfo(resourceInfos[0].bundleName_, appIndex)) {
                APP_LOGW("-n %{public}s -i %{public}d add clone resource failed", bundleName.c_str(), appIndex);
            }
        }
    }
    return ret;
}

bool BundleResourceManager::ProcessCloneBundleResourceInfo(
    const std::string &bundleName, const int32_t appIndex)
{
    APP_LOGD("start update clone bundle resource info, bundleName:%{public}s appIndex:%{public}d",
        bundleName.c_str(), appIndex);
    uint32_t type = static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE) |
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_THEME_CHANGE);
    // 1. get main bundle resource info
    std::vector<ResourceInfo> resourceInfos;
    if (!GetBundleResourceInfoForCloneBundle(bundleName, appIndex, type, resourceInfos)) {
        APP_LOGE("add clone bundle resource failed, bundleName:%{public}s appIndex:%{public}d",
            bundleName.c_str(), appIndex);
        return false;
    }
    // 2. need to process base icon and badge icon
    BundleResourceParser parser;
    if (!parser.ParserCloneResourceInfo(appIndex, resourceInfos)) {
        APP_LOGE("bundleName:%{public}s appIndex:%{public}d parse clone resource failed",
            bundleName.c_str(), appIndex);
    }
    // 3. add clone bundle resource info
    if (!bundleResourceRdb_->AddResourceInfos(resourceInfos)) {
        APP_LOGE("add resource failed, bundleName:%{public}s appIndex:%{public}d", bundleName.c_str(), appIndex);
        return false;
    }
    APP_LOGD("end, add clone bundle resource succeed");
    return true;
}

bool BundleResourceManager::AddResourceInfoByBundleNameWhenCreateUser(
    const std::string &bundleName, const int32_t userId)
{
    // 1. if theme not exist, then return
    if (!BundleResourceThemeProcess::IsBundleThemeExist(bundleName, userId)) {
        return true;
    }
    // 2. get all resource
    std::vector<ResourceInfo> resourceInfos;
    if (!BundleResourceProcess::GetResourceInfoByBundleName(bundleName, userId, resourceInfos, 0, false) ||
        resourceInfos.empty()) {
        APP_LOGE("get all resource failed when create user -n %{public}s -u %{public}d",
            bundleName.c_str(), userId);
        return false;
    }
    PrepareSysRes();
    std::vector<ResourceInfo> themeResourceInfos;
    themeResourceInfos.emplace_back(resourceInfos[0]);
    // 3. traverse all resourceInfo to determine if ability theme exist
    for (const auto &resource : resourceInfos) {
        if (BundleResourceThemeProcess::IsAbilityThemeExist(resource.bundleName_, resource.moduleName_,
            resource.abilityName_, userId)) {
            themeResourceInfos.emplace_back(resource);
        }
    }
    // 4. parse theme icon, no need to add hapPath
    BundleResourceParser parser;
    if (!parser.ParseIconResourceInfosWithTheme(userId, themeResourceInfos)) {
        APP_LOGE("parse theme icon failed when create user -n %{public}s -u %{public}d", bundleName.c_str(), userId);
        return false;
    }
    // 5. add theme icon to bundleResourceIconRdb
    if (!bundleResourceIconRdb_->AddResourceIconInfos(userId, IconResourceType::THEME_ICON, themeResourceInfos)) {
        APP_LOGE("add theme icon failed when create user -n %{public}s -u %{public}d", bundleName.c_str(), userId);
        return false;
    }
    // 6. process bundle clone resource
    if (!resourceInfos.empty() && !resourceInfos[0].appIndexes_.empty()) {
        for (const int32_t appIndex : resourceInfos[0].appIndexes_) {
            // update clone bundle icon resource
            (void)ProcessCloneBundleResourceInfoWhenSystemThemeChanged(bundleName, userId, appIndex);
        }
    }
    return true;
}

bool BundleResourceManager::DeleteBundleResourceInfo(
    const std::string &bundleName,
    const int32_t userId,
    const bool isExistInOtherUser)
{
    /**
     * Delete bundle resource when uninstall, but bundle still exists in other users.
     * if isExistInOtherUser false, need to delete resource in bundleResourceIconRdb and bundleResourceRdb.
     * if isExistInOtherUser true, Only need to delete resource in bundleResourceIconRdb.
     */
    bool ret = true;
    if (!isExistInOtherUser) {
        ret = bundleResourceRdb_->DeleteResourceInfo(bundleName);
        if (!ret) {
            APP_LOGE("delete -n %{public}s -u %{public}d in bundleResourceRdb failed", bundleName.c_str(), userId);
        }
    }

    if (!bundleResourceIconRdb_->DeleteResourceIconInfos(bundleName, userId)) {
        APP_LOGE("delete -n %{public}s -u %{public}d in bundleResourceIconRdb failed", bundleName.c_str(), userId);
        return false;
    }
    return ret;
}

bool BundleResourceManager::AddDynamicIconResource(
    const std::string &bundleName, const int32_t userId, const int32_t appIndex, ResourceInfo &resourceInfo)
{
    // only need to process bundleResourceIconRdb
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    if (userId != Constants::UNSPECIFIED_USERID) {
        // process icon with badge
        BundleResourceParser parser;
        if ((appIndex > 0) && (!parser.ParserCloneResourceInfo(appIndex, resourceInfo))) {
            APP_LOGE("parse clone resource failed -n %{public}s -u %{public}d -a %{public}d",
                bundleName.c_str(), userId, appIndex);
        }
        if (!bundleResourceIconRdb_->AddResourceIconInfo(userId, IconResourceType::DYNAMIC_ICON, resourceInfo)) {
            APP_LOGE("add dynamic icon failed -n %{public}s -u %{public}d -a %{public}d",
                bundleName.c_str(), userId, appIndex);
            return false;
        }
        return true;
    }
    // if userId == -2, process all user and clone bundle
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return false;
    }
    bool ret = true;
    auto userIds = dataMgr->GetUserIds(bundleName);
    for (const auto &user : userIds) {
        resourceInfo.appIndex_ = 0;
        ret &= bundleResourceIconRdb_->AddResourceIconInfo(user, IconResourceType::DYNAMIC_ICON, resourceInfo);
        auto appIndexes = dataMgr->GetCloneAppIndexes(bundleName, user);
        // process icon with badge
        BundleResourceParser parser;
        for (const auto &index : appIndexes) {
            ResourceInfo newResourceInfo = resourceInfo;
            newResourceInfo.appIndex_ = index;
            if (!parser.ParserCloneResourceInfo(index, newResourceInfo)) {
                APP_LOGE("parse clone resource failed -n %{public}s -u %{public}d -a %{public}d",
                    bundleName.c_str(), user, index);
            }
            ret &= bundleResourceIconRdb_->AddResourceIconInfo(user, IconResourceType::DYNAMIC_ICON, newResourceInfo);
        }
    }
    if (!ret) {
        APP_LOGE("add all user dynamic icon failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
    }
    return ret;
}

bool BundleResourceManager::DeleteDynamicIconResource(
    const std::string &bundleName, const int32_t userId, const int32_t appIndex)
{
    if (userId != Constants::UNSPECIFIED_USERID) {
        if (!bundleResourceIconRdb_->DeleteResourceIconInfo(bundleName, userId, appIndex,
            IconResourceType::DYNAMIC_ICON)) {
            APP_LOGE("delete dynamic icon failed -n %{public}s -u %{public}d -a %{public}d",
                bundleName.c_str(), userId, appIndex);
            return false;
        }
        return true;
    }
    // if userId is -2, need delete all userId and appIndex dynamic icon
    if (!bundleResourceIconRdb_->DeleteResourceIconInfos(bundleName, IconResourceType::DYNAMIC_ICON)) {
        APP_LOGE("delete all user dynamic icon failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    return true;
}

bool BundleResourceManager::AddAllResourceInfo(
    const int32_t userId, const uint32_t type)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    EventReport::SendCpuSceneEvent(FOUNDATION_PROCESS_NAME, SCENE_ID_UPDATE_RESOURCE);
    ++currentTaskNum_;
    uint32_t tempTaskNum = currentTaskNum_;
    currentChangeType_ = type;
    std::lock_guard<std::mutex> guard(mutex_);
    APP_LOGI("bundle resource hold mutex");
    std::map<std::string, std::vector<ResourceInfo>> resourceInfosMap;
    if (!BundleResourceProcess::GetAllResourceInfo(userId, resourceInfosMap)) {
        APP_LOGE("GetAllResourceInfo failed userId %{public}d", userId);
        return false;
    }
    PrepareSysRes();
    if ((type & static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_THEME_CHANGE)) ==
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_THEME_CHANGE)) {
        if (!AddResourceInfosWhenSystemThemeChanged(resourceInfosMap, userId, tempTaskNum)) {
            APP_LOGE("add resource failed when theme changed -u %{public}d", userId);
            return false;
        }
    }
    if ((type & static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE)) ==
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE)) {
        if (!AddResourceInfosWhenSystemLanguageChanged(resourceInfosMap, userId, tempTaskNum)) {
            APP_LOGE("add resource failed when language changed -u %{public}d", userId);
            return false;
        }
    }
    SendBundleResourcesChangedEvent(userId, type);
    APP_LOGI_NOFUNC("add all resource end");
    return true;
}

bool BundleResourceManager::IsNeedInterrupted(const uint32_t tempTaskNumber, const BundleResourceChangeType type)
{
    if (tempTaskNumber == currentTaskNum_) {
        return false;
    }
    return static_cast<uint32_t>(currentChangeType_) == static_cast<uint32_t>(type);
}

bool BundleResourceManager::AddResourceInfosWhenSystemLanguageChanged(
    std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap,
    const int32_t userId, const uint32_t tempTaskNumber)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (resourceInfosMap.empty()) {
        APP_LOGE("resourceInfosMap is empty");
        return false;
    }
    InnerProcessResourceInfoBySystemLanguageChanged(resourceInfosMap);
    std::shared_ptr<ThreadPool> threadPool = std::make_shared<ThreadPool>(THREAD_POOL_NAME);
    threadPool->Start(MAX_TASK_NUMBER);
    threadPool->SetMaxTaskNum(MAX_TASK_NUMBER);
    for (const auto &item : resourceInfosMap) {
        if (IsNeedInterrupted(tempTaskNumber, BundleResourceChangeType::SYSTEM_LANGUE_CHANGE)) {
            APP_LOGI("need stop current task, new first");
            threadPool->Stop();
            return false;
        }
        std::string bundleName = item.first;
        auto task = [userId, bundleName, &resourceInfosMap, this]() {
            if (resourceInfosMap.find(bundleName) == resourceInfosMap.end()) {
                APP_LOGE("bundleName %{public}s not exist", bundleName.c_str());
                return;
            }
            std::vector<ResourceInfo> resourceInfos = resourceInfosMap[bundleName];
            BundleResourceParser parser;
            parser.ParseResourceInfos(userId, resourceInfos);
            bundleResourceRdb_->UpdateResourceForSystemStateChanged(resourceInfos);
        };
        threadPool->AddTask(task);
    }
    while (threadPool->GetCurTaskNum() > 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(CHECK_INTERVAL));
    }
    threadPool->Stop();
    // process clone bundle resource info, only flash label
    for (const auto &item : resourceInfosMap) {
        if (!item.second.empty() && !item.second[0].appIndexes_.empty()) {
            APP_LOGI("start process bundle:%{public}s clone resource info", item.first.c_str());
            for (const int32_t appIndex : item.second[0].appIndexes_) {
                ProcessCloneBundleResourceInfoWhenSystemLanguageChanged(item.first, userId, appIndex);
            }
        }
    }
    APP_LOGI("all task end resource size %{public}zu when language changed", resourceInfosMap.size());
    return true;
}

bool BundleResourceManager::ProcessCloneBundleResourceInfoWhenSystemLanguageChanged(
    const std::string &bundleName,
    const int32_t userId,
    const int32_t appIndex)
{
    if (appIndex <= 0) {
        APP_LOGE("prase clone bundle failed -n %{public}s -u %{public}d -a %{public}d", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    std::vector<ResourceInfo> resourceInfos;
    if (!GetBundleResourceInfoForCloneBundle(bundleName, appIndex,
        static_cast<uint32_t>(BundleResourceChangeType::SYSTEM_LANGUE_CHANGE), resourceInfos)) {
        APP_LOGE("get clone bundle resource failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    // update clone bundle label resource
    if (!bundleResourceRdb_->UpdateResourceForSystemStateChanged(resourceInfos)) {
        APP_LOGE("update clone resource failed -n %{public}s -u %{public}d -a %{public}d", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    return true;
}

void BundleResourceManager::DeleteNotExistThemeResource(
    const std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap,
    const std::set<std::string> &oldResourceNames,
    const int32_t userId)
{
    if (oldResourceNames.empty()) {
        return;
    }
    std::set<std::string> newBundleNames;
    for (const auto &item : resourceInfosMap) {
        for (const auto &resource : item.second) {
            newBundleNames.insert(resource.GetKey());
        }
    }
    for (const auto &name : oldResourceNames) {
        if (newBundleNames.find(name) == newBundleNames.end()) {
            // delete key bundleName and type, need delete  clone bundle
            (void)bundleResourceIconRdb_->DeleteResourceIconInfos(name, userId, IconResourceType::THEME_ICON);
        }
    }
}

bool BundleResourceManager::AddResourceInfosWhenSystemThemeChanged(
    std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap,
    const int32_t userId, const uint32_t tempTaskNumber)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (resourceInfosMap.empty()) {
        APP_LOGE("resourceInfosMap is empty");
        return false;
    }
    // 1. used to delete no exist in current theme bundle resource
    std::set<std::string> oldResourceNames;
    if (!bundleResourceIconRdb_->GetAllResourceIconName(userId, oldResourceNames, IconResourceType::THEME_ICON)) {
        APP_LOGW("get old bundle names failed");
    }
    // 2. judge whether the bundle theme exists
    InnerProcessResourceInfoBySystemThemeChanged(resourceInfosMap, userId);
    std::shared_ptr<ThreadPool> threadPool = std::make_shared<ThreadPool>(THREAD_POOL_NAME);
    threadPool->Start(MAX_TASK_NUMBER);
    threadPool->SetMaxTaskNum(MAX_TASK_NUMBER);
    for (const auto &item : resourceInfosMap) {
        if (IsNeedInterrupted(tempTaskNumber, BundleResourceChangeType::SYSTEM_THEME_CHANGE)) {
            APP_LOGI("need stop current task, new first");
            threadPool->Stop();
            return false;
        }
        std::string bundleName = item.first;
        auto task = [userId, bundleName, &resourceInfosMap, this]() {
            if (resourceInfosMap.find(bundleName) == resourceInfosMap.end()) {
                APP_LOGE("bundleName %{public}s not exist", bundleName.c_str());
                return;
            }
            std::vector<ResourceInfo> resourceInfos = resourceInfosMap[bundleName];
            BundleResourceParser parser;
            parser.ParseIconResourceInfosWithTheme(userId, resourceInfos);
            (void)bundleResourceIconRdb_->AddResourceIconInfos(userId, IconResourceType::THEME_ICON, resourceInfos);
        };
        threadPool->AddTask(task);
    }
    while (threadPool->GetCurTaskNum() > 0) {
        std::this_thread::sleep_for(std::chrono::milliseconds(CHECK_INTERVAL));
    }
    threadPool->Stop();
    // process clone bundle resource info
    for (const auto &item : resourceInfosMap) {
        if (!item.second.empty() && !item.second[0].appIndexes_.empty()) {
            APP_LOGI("start process bundle:%{public}s clone resource info", item.first.c_str());
            for (const int32_t appIndex : item.second[0].appIndexes_) {
                (void)ProcessCloneBundleResourceInfoWhenSystemThemeChanged(item.first, userId, appIndex);
            }
        }
    }
    DeleteNotExistThemeResource(resourceInfosMap, oldResourceNames, userId);
    // set is online theme
    SetIsOnlineTheme(userId);
    APP_LOGI("all task end resource size %{public}zu when theme changed", resourceInfosMap.size());
    return true;
}

bool BundleResourceManager::ProcessCloneBundleResourceInfoWhenSystemThemeChanged(
    const std::string &bundleName,
    const int32_t userId,
    const int32_t appIndex)
{
    // 1. query main bundle resource in bundleResourceIconRdb
    std::vector<LauncherAbilityResourceInfo> launcherAbilityResourceInfos;
    if (!bundleResourceIconRdb_->GetResourceIconInfos(bundleName, userId, 0,
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON) |
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR),
        launcherAbilityResourceInfos, IconResourceType::THEME_ICON)) {
        APP_LOGE("get resource failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    std::vector<ResourceInfo> resourceInfos;
    for (auto &info : launcherAbilityResourceInfos) {
        info.appIndex = appIndex;
        ResourceInfo bundleResource;
        bundleResource.ConvertFromLauncherAbilityResourceInfo(info);
        resourceInfos.emplace_back(bundleResource);
    }
    // 2. process icon with badge
    BundleResourceParser parser;
    if (!parser.ParserCloneResourceInfo(appIndex, resourceInfos)) {
        APP_LOGE("parse clone resource failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
    }
    // 3. save clone bundle resource info to bundleResourceIconRdb
    if (!bundleResourceIconRdb_->AddResourceIconInfos(userId, IconResourceType::THEME_ICON, resourceInfos)) {
        APP_LOGE("add resource failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    return true;
}

void BundleResourceManager::InnerProcessResourceInfoBySystemThemeChanged(
    std::map<std::string, std::vector<ResourceInfo>> &resourceInfosMap,
    const int32_t userId)
{
    for (auto iter = resourceInfosMap.begin(); iter != resourceInfosMap.end();) {
        if (iter->second.empty() || !BundleResourceThemeProcess::IsBundleThemeExist(iter->first, userId)) {
            iter = resourceInfosMap.erase(iter);
            continue;
        }
        std::vector<ResourceInfo> themeResourceInfos;
        themeResourceInfos.emplace_back(iter->second[0]);
        for (const auto &resource : iter->second) {
            if (BundleResourceThemeProcess::IsAbilityThemeExist(resource.bundleName_, resource.moduleName_,
                resource.abilityName_, userId)) {
                themeResourceInfos.emplace_back(resource);
            }
        }
        iter->second = themeResourceInfos;
        ++iter;
    }
    for (auto iter = resourceInfosMap.begin(); iter != resourceInfosMap.end(); ++iter) {
        ProcessResourceInfoNoNeedToParseOtherIcon(iter->second);
    }
}

bool BundleResourceManager::AddCloneBundleResourceInfoWhenInstall(
    const std::string &bundleName,
    const int32_t userId,
    const int32_t appIndex,
    const bool isExistInOtherUser)
{
    /**
     * Need to distinguish whether bundle and appIndex exist in other users.
     * if not exist, need to process both bundleResourceRdb and bundleResourceIconRdb;
     * if exist, only need to process bundleResourceIconRdb.
     */
    PrepareSysRes();
    bool ret = true;
    if (!isExistInOtherUser) {
        // 1. process clone resource icon and label in bundleResourceRdb, icon with badge, label with appIndex
        ret = ProcessCloneBundleResourceInfo(bundleName, appIndex);
        if (!ret) {
            APP_LOGE("-n %{public}s -u %{public}d -a %{public}d process clone resource failed",
                bundleName.c_str(), userId, appIndex);
        }
    }
    // 2. if theme not exist, then return
    if (!BundleResourceThemeProcess::IsBundleThemeExist(bundleName, userId)) {
        return ret;
    }
    // 3. process clone resource icon in bundleResourceIconRdb
    std::vector<LauncherAbilityResourceInfo> launcherAbilityResourceInfos;
    if (!bundleResourceIconRdb_->GetResourceIconInfos(bundleName, userId, 0,
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON) |
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR),
        launcherAbilityResourceInfos, IconResourceType::THEME_ICON)) {
        APP_LOGE("get resource failed -n %{public}s -u %{public}d -a %{public}d",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    // 4. process icon with badge
    std::vector<ResourceInfo> resourceInfos;
    for (auto &info : launcherAbilityResourceInfos) {
        info.appIndex = appIndex;
        ResourceInfo bundleResource;
        bundleResource.ConvertFromLauncherAbilityResourceInfo(info);
        resourceInfos.emplace_back(bundleResource);
    }
    BundleResourceParser parser;
    if (!parser.ParserCloneResourceInfo(appIndex, resourceInfos)) {
        APP_LOGE("-n %{public}s -u %{public}d -a %{public}d parse clone resource failed",
            bundleName.c_str(), userId, appIndex);
    }
    // 5. add theme icon to bundleResourceIconRdb
    if (!bundleResourceIconRdb_->AddResourceIconInfos(userId, IconResourceType::THEME_ICON, resourceInfos)) {
        APP_LOGE("-n %{public}s -u %{public}d -a %{public}d add clone resource failed",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    return ret;
}

bool BundleResourceManager::DeleteCloneBundleResourceInfoWhenUninstall(
    const std::string &bundleName,
    const int32_t userId,
    const int32_t appIndex,
    const bool isExistInOtherUser)
{
    /**
     * Need to distinguish whether bundle and appIndex exist in other users.
     * if not exist, need to delete both bundleResourceRdb and bundleResourceIconRdb;
     * if exist, only need to delete bundleResourceIconRdb.
     */
    bool ret = true;
    if (!isExistInOtherUser) {
        ResourceInfo resourceInfo;
        resourceInfo.bundleName_ = bundleName;
        resourceInfo.appIndex_ = appIndex;
        ret = bundleResourceRdb_->DeleteResourceInfo(resourceInfo.GetKey());
        if (!ret) {
            APP_LOGE("-n %{public}s -u %{public}d -a %{public}d delete resource failed",
                bundleName.c_str(), userId, appIndex);
        }
    }
    if (!bundleResourceIconRdb_->DeleteResourceIconInfo(bundleName, userId, appIndex)) {
        APP_LOGE("-n %{public}s -u %{public}d -a %{public}d delete resource failed",
            bundleName.c_str(), userId, appIndex);
        return false;
    }
    return ret;
}

bool BundleResourceManager::IsNeedProcessResourceIconInfo(const uint32_t resourceFlags)
{
    if (((resourceFlags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ||
        ((resourceFlags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ||
        ((resourceFlags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR))) {
        return true;
    }
    return false;
}

int32_t BundleResourceManager::GetUserId()
{
    int32_t userId = BundleUtil::GetUserIdByCallingUid();
    if (userId == Constants::DEFAULT_USERID) {
        // sa call or U0 app
        userId = AccountHelper::GetCurrentActiveUserId();
    }
    if (userId < Constants::DEFAULT_USERID) {
        APP_LOGE("userId %{public}d is invalid", userId);
    }
    return userId;
}

void BundleResourceManager::SetIsOnlineThemeWhenBoot()
{
    APP_LOGI("set online theme when boot start");
    // 1. get all user
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return;
    }
    auto userIds = dataMgr->GetAllUser();
    // 2. parse json file
    for (const auto &userId : userIds) {
        SetIsOnlineTheme(userId);
    }
    APP_LOGI("set online theme when boot end");
}

void BundleResourceManager::SetIsOnlineTheme(const int32_t userId)
{
    bool isOnlineTheme = false;
    if (!BundleResourceProcess::CheckThemeType("", userId, isOnlineTheme)) {
        APP_LOGE("userId %{public}d check online theme failed", userId);
    }
    APP_LOGI("userId %{public}d isOnlineTheme %{public}d", userId, isOnlineTheme);
    bundleResourceIconRdb_->SetIsOnlineTheme(userId, isOnlineTheme);
}

bool BundleResourceManager::InnerProcessThemeIconWhenOta(
    const std::string &bundleName, const std::set<int32_t> userIds, const bool hasBundleUpdated)
{
    // 1. theme whether exist in all user, no need to process
    std::vector<int32_t> existThemeUserIds;
    for (const auto user : userIds) {
        if (BundleResourceThemeProcess::IsBundleThemeExist(bundleName, user)) {
            existThemeUserIds.push_back(user);
        }
    }
    if (existThemeUserIds.empty()) {
        return true;
    }
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return false;
    }
    // 2. only process bundle resource rdb, like bundle update
    bool isUpdated = false;
    for (const auto userId : existThemeUserIds) {
        // bundle whether installed in user
        bool isInstalled = false;
        if ((dataMgr->IsBundleInstalled(bundleName, userId, 0, isInstalled) != ERR_OK) || !isInstalled) {
            continue;
        }
        if (!isUpdated && !hasBundleUpdated) {
            (void)AddResourceInfoByBundleNameWhenUpdate(bundleName, existThemeUserIds[0]);
            isUpdated = true;
        }
        (void)AddResourceInfoByBundleNameWhenCreateUser(bundleName, userId);
    }
    return true;
}

bool BundleResourceManager::InnerProcessDynamicIconWhenOta(const std::string &bundleName)
{
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return false;
    }
    // 1. check dynamic icon info, if not exist then return
    std::vector<DynamicIconInfo> dynamicIconInfos;
    if (dataMgr->GetDynamicIconInfo(bundleName, dynamicIconInfos) != ERR_OK) {
        APP_LOGE("get dynamic icon failed -n %{public}s", bundleName.c_str());
        return false;
    }
    if (dynamicIconInfos.empty()) {
        return true;
    }
    // 2. need parse dynamic icon, add to bundle resource icon rdb
    std::set<int32_t> userIds;
    for (const auto &dynamicIcon : dynamicIconInfos) {
        userIds.insert(dynamicIcon.userId);
        ResourceInfo resourceInfo;
        resourceInfo.bundleName_ = dynamicIcon.bundleName;
        resourceInfo.appIndex_ = dynamicIcon.appIndex;
        if (!BundleResourceProcess::GetDynamicIconResourceInfo(dynamicIcon.bundleName, dynamicIcon.moduleName,
            resourceInfo)) {
            APP_LOGE("get dynamic icon failed -n %{public}s", bundleName.c_str());
            continue;
        }
        // add bundle resource icon rdb
        if (!AddDynamicIconResource(bundleName, dynamicIcon.userId, dynamicIcon.appIndex, resourceInfo)) {
            APP_LOGE("add dynamic icon failed -n %{public}s", bundleName.c_str());
        }
    }
    // 3. update bundle resource rdb
    for (const auto userId : userIds) {
        if (BundleResourceThemeProcess::IsBundleThemeExist(bundleName, userId)) {
            if (AddResourceInfoByBundleNameWhenUpdate(bundleName, userId)) {
                APP_LOGE("add resource icon failed -n %{public}s -u %{public}d", bundleName.c_str(), userId);
            }
            break;
        }
    }
    return true;
}

bool BundleResourceManager::ProcessThemeAndDynamicIconWhenOta(
    const std::set<std::string> &updateBundleNames)
{
    APP_LOGI("ProcessThemeAndDynamicIconWhenOta start");
    std::shared_ptr<BundleDataMgr> dataMgr = DelayedSingleton<BundleMgrService>::GetInstance()->GetDataMgr();
    if (dataMgr == nullptr) {
        APP_LOGE("dataMgr is nullptr");
        return false;
    }
    PrepareSysRes();
    auto userIds = dataMgr->GetAllUser();
    // 1. get all bundle names
    std::vector<std::string> allBundleNames = dataMgr->GetAllBundleName();
    for (const auto &bundleName : allBundleNames) {
        // dynamic icon need all process
        InnerProcessDynamicIconWhenOta(bundleName);
        // theme icon already process when bundle update
        bool hasBundleUpdated = std::find(updateBundleNames.begin(), updateBundleNames.end(),
            bundleName) != updateBundleNames.end();
        InnerProcessThemeIconWhenOta(bundleName, userIds, hasBundleUpdated);
    }
    APP_LOGI("ProcessThemeAndDynamicIconWhenOta end");
    return true;
}

bool BundleResourceManager::AddUninstallBundleResource(const std::string &bundleName,
    const int32_t userId, const int32_t appIndex)
{
    APP_LOGI("-n %{public}s -u %{public}d -i %{public}d add uinstall bundle resource start", bundleName.c_str(),
        userId, appIndex);
    // 1. get resource info, labelId and iconId
    std::vector<ResourceInfo> resourceInfos;
    if (!BundleResourceProcess::GetResourceInfoByBundleName(bundleName, userId, resourceInfos, appIndex, false)) {
        APP_LOGE("-n %{public}s -u %{public}d -i %{public}d get bundle resourceInfo failed", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    ResourceInfo resourceInfo = resourceInfos[0]; // resourceInfos not empty
    resourceInfo.appIndex_ = appIndex;
    // 2. get bundle resource Info from bundleResourceRdb
    uint32_t flag = static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON) |
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR);
    BundleResourceInfo bundleResourceInfo;
    if (!bundleResourceRdb_->GetBundleResourceInfo(bundleName, flag, bundleResourceInfo, appIndex)) {
        APP_LOGW("-n %{public}s -i %{public}d resource not exist in db", bundleName.c_str(), appIndex);
        resourceInfo.iconNeedParse_ = true;
    } else {
        resourceInfo.iconNeedParse_ = false;
    }
    // 3. parse label and icon from hap
    std::map<std::string, std::string> labelMap;
    BundleResourceParser parser;
    if (!parser.ParseUninstallBundleResource(resourceInfo, labelMap)) {
        APP_LOGE("-n %{public}s -u %{public}d -i %{public}d parse uinstall bundle resource failed", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    if (resourceInfo.iconNeedParse_) {
        bundleResourceInfo.icon = resourceInfo.icon_;
        bundleResourceInfo.foreground = resourceInfo.foreground_;
        bundleResourceInfo.background = resourceInfo.background_;
    }
    if (!uninstallBundleResourceRdb_->AddUninstallBundleResource(bundleName, userId, appIndex,
        labelMap, bundleResourceInfo)) {
        APP_LOGE("-n %{public}s -u %{public}d -i %{public}d add uinstall bundle resource failed", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    APP_LOGI("-n %{public}s -u %{public}d -i %{public}d add uinstall bundle resource succeed", bundleName.c_str(),
        userId, appIndex);
    return true;
}

bool BundleResourceManager::DeleteUninstallBundleResource(const std::string &bundleName,
    const int32_t userId, const int32_t appIndex)
{
    APP_LOGI("-n %{public}s -u %{public}d -i %{public}d delete uinstall bundle resource start", bundleName.c_str(),
        userId, appIndex);
    return uninstallBundleResourceRdb_->DeleteUninstallBundleResource(bundleName, userId, appIndex);
}

bool BundleResourceManager::DeleteUninstallBundleResourceForUser(const int32_t userId)
{
    APP_LOGI("-u %{public}d delete uinstall bundle resource start", userId);
    return uninstallBundleResourceRdb_->DeleteUninstallBundleResourceForUser(userId);
}

bool BundleResourceManager::GetUninstallBundleResource(const std::string &bundleName,
    const int32_t userId, const int32_t appIndex, const uint32_t flags, BundleResourceInfo &bundleResourceInfo)
{
    uint32_t resourceFlags = CheckResourceFlags(flags);
    if (!uninstallBundleResourceRdb_->GetUninstallBundleResource(bundleName, userId, appIndex, resourceFlags,
        bundleResourceInfo)) {
        APP_LOGE("-n %{public}s -u %{public}d -i %{public}d get uinstall bundle resource failed", bundleName.c_str(),
            userId, appIndex);
        return false;
    }
    return true;
}

bool BundleResourceManager::GetAllUninstallBundleResourceInfo(const int32_t userId, const uint32_t flags,
    std::vector<BundleResourceInfo> &bundleResourceInfos)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGD("start, -u:%{public}d", userId);
    uint32_t resourceFlags = CheckResourceFlags(flags);
    int32_t newUserId = userId;
    if (newUserId == Constants::DEFAULT_USERID) {
        // sa call or U0 app
        newUserId = AccountHelper::GetCurrentActiveUserId();
    }
    if (!uninstallBundleResourceRdb_->GetAllUninstallBundleResource(newUserId, resourceFlags, bundleResourceInfos)) {
        APP_LOGE("-u %{public}d get all uinstall bundle resource failed", newUserId);
        return false;
    }
    return true;
}
} // AppExecFwk
} // OHOS
