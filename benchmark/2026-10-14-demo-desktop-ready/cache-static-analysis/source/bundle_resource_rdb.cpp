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

#include "bundle_resource_rdb.h"

#include "app_log_wrapper.h"
#include "bundle_resource_constants.h"
#include "bundle_util.h"
#include "hitrace_meter.h"
#include "scope_guard.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
constexpr const char* SYSTEM_RESOURCES_APP = "ohos.global.systemres";
}

BundleResourceRdb::BundleResourceRdb()
{
    APP_LOGI_NOFUNC("BundleResourceRdb create");
    BmsRdbConfig bmsRdbConfig;
    bmsRdbConfig.dbName = BundleResourceConstants::BUNDLE_RESOURCE_RDB_NAME;
    bmsRdbConfig.dbPath = BundleResourceConstants::BUNDLE_RESOURCE_RDB_PATH;
    bmsRdbConfig.tableName = BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME;
    bmsRdbConfig.createTableSql = std::string(
        "CREATE TABLE IF NOT EXISTS "
        + std::string(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME)
        + "(NAME TEXT NOT NULL, UPDATE_TIME INTEGER, LABEL TEXT, ICON TEXT, "
        + "SYSTEM_STATE TEXT NOT NULL, PRIMARY KEY (NAME));");
    bmsRdbConfig.insertColumnSql.push_back(std::string("ALTER TABLE " +
        std::string(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME) +
        " ADD FOREGROUND BLOB;"));
    bmsRdbConfig.insertColumnSql.push_back(std::string("ALTER TABLE " +
        std::string(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME) +
        " ADD BACKGROUND BLOB;"));
    rdbDataManager_ = std::make_shared<RdbDataManager>(bmsRdbConfig);
    rdbDataManager_->CreateTable();
}

BundleResourceRdb::~BundleResourceRdb()
{
}

bool BundleResourceRdb::AddResourceInfo(const ResourceInfo &resourceInfo)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (resourceInfo.bundleName_.empty()) {
        APP_LOGE("failed, bundleName is empty");
        return false;
    }
    APP_LOGD("insert resource key:%{public}s", resourceInfo.GetKey().c_str());
    int64_t timeStamp = BundleUtil::GetCurrentTimeMs();
    NativeRdb::ValuesBucket valuesBucket;
    valuesBucket.PutString(BundleResourceConstants::NAME, resourceInfo.GetKey());
    valuesBucket.PutLong(BundleResourceConstants::UPDATE_TIME, timeStamp);
    valuesBucket.PutString(BundleResourceConstants::LABEL, resourceInfo.label_);
    valuesBucket.PutString(BundleResourceConstants::ICON, resourceInfo.icon_);
    valuesBucket.PutString(BundleResourceConstants::SYSTEM_STATE, BundleSystemState::GetInstance().ToString());
    // used for layered icons
    valuesBucket.PutBlob(BundleResourceConstants::FOREGROUND, resourceInfo.foreground_);
    valuesBucket.PutBlob(BundleResourceConstants::BACKGROUND, resourceInfo.background_);
    APP_LOGD("key:%{public}s foreground: %{public}zu, background: %{public}zu", resourceInfo.GetKey().c_str(),
        resourceInfo.foreground_.size(), resourceInfo.background_.size());

    return rdbDataManager_->InsertData(valuesBucket);
}

bool BundleResourceRdb::AddResourceInfos(const std::vector<ResourceInfo> &resourceInfos)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (resourceInfos.empty()) {
        APP_LOGE("failed, resourceInfos is empty");
        return false;
    }
    int64_t timeStamp = BundleUtil::GetCurrentTimeMs();
    bool ret = true;
    std::vector<NativeRdb::ValuesBucket> valuesBuckets;
    for (const auto &info : resourceInfos) {
        if (info.bundleName_.empty()) {
            APP_LOGE("failed, bundleName is empty");
            ret = false;
            continue;
        }
        NativeRdb::ValuesBucket valuesBucket;
        valuesBucket.PutString(BundleResourceConstants::NAME, info.GetKey());
        valuesBucket.PutLong(BundleResourceConstants::UPDATE_TIME, timeStamp);
        valuesBucket.PutString(BundleResourceConstants::SYSTEM_STATE, BundleSystemState::GetInstance().ToString());

        if (!info.label_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::LABEL, info.label_);
        } else {
            valuesBucket.PutString(BundleResourceConstants::LABEL, resourceInfos[0].label_);
        }

        if (!info.icon_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::ICON, info.icon_);
            // used for layered icons
            valuesBucket.PutBlob(BundleResourceConstants::FOREGROUND, info.foreground_);
            valuesBucket.PutBlob(BundleResourceConstants::BACKGROUND, info.background_);
        } else {
            valuesBucket.PutString(BundleResourceConstants::ICON, resourceInfos[0].icon_);
            // used for layered icons
            valuesBucket.PutBlob(BundleResourceConstants::FOREGROUND, resourceInfos[0].foreground_);
            valuesBucket.PutBlob(BundleResourceConstants::BACKGROUND, resourceInfos[0].background_);
        }
        APP_LOGD("key:%{public}s foreground: %{public}zu, background: %{public}zu", info.GetKey().c_str(),
            info.foreground_.size(), info.background_.size());
        valuesBuckets.emplace_back(valuesBucket);
    }
    int64_t insertNum = 0;
    bool insertRet = rdbDataManager_->BatchInsert(insertNum, valuesBuckets);
    if (!insertRet) {
        APP_LOGE("BatchInsert failed");
        return false;
    }
    if (valuesBuckets.size() != static_cast<uint64_t>(insertNum)) {
        APP_LOGE("BatchInsert size not expected");
        return false;
    }
    return ret;
}

bool BundleResourceRdb::DeleteResourceInfo(const std::string &key)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (key.empty()) {
        APP_LOGE("failed, key is empty");
        return false;
    }
    APP_LOGD("need delete resource info, key: %{public}s", key.c_str());
    /**
     * begin with bundle name, like:
     * 1. bundleName
     * 2. bundleName/moduleName/abilityName
     */
    if (key.find(ServiceConstants::PATH_SEPARATOR) == std::string::npos) {
        NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
        // need delete both bundle resource and launcher ability resource
        absRdbPredicates.BeginsWith(BundleResourceConstants::NAME, key + ServiceConstants::PATH_SEPARATOR);
        if (!rdbDataManager_->DeleteData(absRdbPredicates)) {
            APP_LOGW("delete key:%{public}s failed", key.c_str());
        }
    }
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.EqualTo(BundleResourceConstants::NAME, key);
    return rdbDataManager_->DeleteData(absRdbPredicates);
}

bool BundleResourceRdb::GetAllResourceName(std::vector<std::string> &keyNames)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    std::string systemState = BundleSystemState::GetInstance().ToString();
    APP_LOGI("start get all resource name:%{public}s", systemState.c_str());
    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("QueryByStep failed, systemState:%{public}s", systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });

    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("GoToFirstRow failed, ret %{public}d, systemState %{public}s", ret, systemState.c_str());
        return false;
    }
    do {
        std::string name;
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_NAME, name);
        if (ret != NativeRdb::E_OK) {
            APP_LOGE("GetString name failed, ret %{public}d, systemState %{public}s", ret, systemState.c_str());
            return false;
        }
        if (name.find("/") != std::string::npos) {
            continue;
        }
        // icon is invalid, need add again
        std::vector<uint8_t> foreground;
        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_FOREGROUND, foreground);
        if (ret != NativeRdb::E_OK) {
            APP_LOGE("GetString foreground failed, ret %{public}d, systemState %{public}s", ret, systemState.c_str());
            return false;
        }
        if (foreground.empty()) {
            APP_LOGW("keyName %{public}s foreground invalid", name.c_str());
            continue;
        }
        // label is invalid, need add again
        std::string label;
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_LABEL, label);
        if (ret != NativeRdb::E_OK) {
            APP_LOGE("GetString label failed, ret %{public}d, systemState:%{public}s", ret, systemState.c_str());
            return false;
        }
        if ((label.find('$') == 0) || (label == name) || label.empty()) {
            APP_LOGW("keyName %{public}s label invalid", name.c_str());
            continue;
        }
        keyNames.push_back(name);
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);
    APP_LOGI_NOFUNC("end");
    return true;
}

bool BundleResourceRdb::GetResourceNameByBundleName(
    const std::string &bundleName,
    const int32_t appIndex,
    std::vector<std::string> &keyName)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGI_NOFUNC("GetResourceName -n %{public}s -i %{public}d", bundleName.c_str(), appIndex);
    if (bundleName.empty()) {
        APP_LOGE("bundleName is empty");
        return false;
    }
    ResourceInfo resourceInfo;
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.BeginsWith(BundleResourceConstants::NAME, resourceInfo.GetKey() +
        BundleResourceConstants::SEPARATOR);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("bundleName:%{public}s failed due rdb QueryByStep failed, systemState:%{public}s",
            bundleName.c_str(), systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGD("bundleName:%{public}s not exist, ret: %{public}d, systemState:%{public}s",
            bundleName.c_str(), ret, systemState.c_str());
        return false;
    }

    do {
        std::string key;
        auto ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_NAME, key);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString name failed, ret: %{public}d");
        keyName.emplace_back(key);
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);
    APP_LOGI_NOFUNC("end");
    return true;
}

bool BundleResourceRdb::DeleteAllResourceInfo()
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    // delete all resource info
    return rdbDataManager_->DeleteData(absRdbPredicates);
}

bool BundleResourceRdb::GetBundleResourceInfo(
    const std::string &bundleName,
    const uint32_t flags,
    BundleResourceInfo &bundleResourceInfo,
    int32_t appIndex)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGD("rdb -n %{public}s -i %{public}d", bundleName.c_str(), appIndex);
    if (bundleName.empty()) {
        APP_LOGE("bundleName is empty");
        return false;
    }
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    ResourceInfo resourceInfo;
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    absRdbPredicates.EqualTo(BundleResourceConstants::NAME, resourceInfo.GetKey());
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("rdb QueryByStep failed, bundleName %{public}s appIndex %{public}d, %{public}s",
            bundleName.c_str(), appIndex, systemState.c_str());
        return false;
    }

    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE_NOFUNC("rdb GetBundleResourceInfo -n %{public}s failed:%{public}d systemState:%{public}s",
            bundleName.c_str(), ret, systemState.c_str());
        return false;
    }
    APP_LOGD("rdb end");
    return ConvertToBundleResourceInfo(absSharedResultSet, flags, bundleResourceInfo);
}

bool BundleResourceRdb::GetLauncherAbilityResourceInfo(
    const std::string &bundleName,
    const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfos,
    const int32_t appIndex)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGI_NOFUNC("rdb GetLauncherAbilityResourceInfo -n %{public}s -i %{public}d", bundleName.c_str(), appIndex);
    if (bundleName.empty()) {
        APP_LOGE("bundleName is empty");
        return false;
    }
    ResourceInfo resourceInfo;
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.BeginsWith(BundleResourceConstants::NAME, resourceInfo.GetKey() +
        BundleResourceConstants::SEPARATOR);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("QueryByStep failed bundleName %{public}s failed, systemState %{public}s",
            bundleName.c_str(), systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("bundleName %{public}s GoToFirstRow failed, ret %{public}d, systemState:%{public}s",
            bundleName.c_str(), ret, systemState.c_str());
        return false;
    }

    do {
        LauncherAbilityResourceInfo resourceInfo;
        if (ConvertToLauncherAbilityResourceInfo(absSharedResultSet, flags, resourceInfo)) {
            launcherAbilityResourceInfos.push_back(resourceInfo);
        }
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);

    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) {
        APP_LOGD("need sort by label");
        std::sort(launcherAbilityResourceInfos.begin(), launcherAbilityResourceInfos.end(),
            [](const LauncherAbilityResourceInfo &resourceA, const LauncherAbilityResourceInfo &resourceB) {
                return resourceA.label < resourceB.label;
            });
    }
    APP_LOGI_NOFUNC("end");
    return !launcherAbilityResourceInfos.empty();
}

bool BundleResourceRdb::GetAllBundleResourceInfo(const uint32_t flags,
    std::vector<BundleResourceInfo> &bundleResourceInfos)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGI("start get all bundle resource");
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet nullptr, systemState %{public}s", systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("GoToFirstRow failed, ret %{public}d, systemState %{public}s", ret, systemState.c_str());
        return false;
    }

    do {
        BundleResourceInfo resourceInfo;
        if (ConvertToBundleResourceInfo(absSharedResultSet, flags, resourceInfo)) {
            bundleResourceInfos.push_back(resourceInfo);
        }
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);

    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) {
        APP_LOGD("need sort by label");
        std::sort(bundleResourceInfos.begin(), bundleResourceInfos.end(),
            [](const BundleResourceInfo &resourceA, const BundleResourceInfo &resourceB) {
                return resourceA.label < resourceB.label;
            });
    }
    APP_LOGI_NOFUNC("end");
    return !bundleResourceInfos.empty();
}

bool BundleResourceRdb::GetAllLauncherAbilityResourceInfo(const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &launcherAbilityResourceInfos)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    APP_LOGI("start get all launcher resource");
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.Contains(BundleResourceConstants::NAME, BundleResourceConstants::SEPARATOR);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet nullptr, systemState %{public}s", systemState.c_str());
        return false;
    }

    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("GoToFirstRow failed, ret %{public}d, systemState %{public}s", ret, systemState.c_str());
        return false;
    }

    do {
        LauncherAbilityResourceInfo resourceInfo;
        if (ConvertToLauncherAbilityResourceInfo(absSharedResultSet, flags, resourceInfo)) {
            launcherAbilityResourceInfos.push_back(resourceInfo);
        }
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);

    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) {
        std::sort(launcherAbilityResourceInfos.begin(), launcherAbilityResourceInfos.end(),
            [](const LauncherAbilityResourceInfo &resourceA, const LauncherAbilityResourceInfo &resourceB) {
                return resourceA.label < resourceB.label;
            });
    }
    APP_LOGI_NOFUNC("end");
    return !launcherAbilityResourceInfos.empty();
}

bool BundleResourceRdb::ConvertToBundleResourceInfo(
    const std::shared_ptr<NativeRdb::ResultSet> &absSharedResultSet,
    const uint32_t flags,
    BundleResourceInfo &bundleResourceInfo)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet is nullptr");
        return false;
    }
    auto ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_NAME, bundleResourceInfo.bundleName);
    CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString name failed, ret: %{public}d");
    if (bundleResourceInfo.bundleName.find_first_of(BundleResourceConstants::SEPARATOR) != std::string::npos) {
        APP_LOGD("key:%{public}s not bundle resource info, continue", bundleResourceInfo.bundleName.c_str());
        return false;
    }
    ParseKey(bundleResourceInfo.bundleName, bundleResourceInfo);

    bool getAll = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL);

    bool getLabel = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL);
    if (getAll || getLabel) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_LABEL, bundleResourceInfo.label);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label failed, ret: %{public}d");
    }

    bool getIcon = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON);
    if (getAll || getIcon) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_ICON, bundleResourceInfo.icon);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label icon, ret: %{public}d");
    }

    bool getDrawable = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR);
    if (getDrawable) {
        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_FOREGROUND, bundleResourceInfo.foreground);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob foreground, ret: %{public}d");

        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_BACKGROUND, bundleResourceInfo.background);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob background, ret: %{public}d");
    }
    return true;
}

bool BundleResourceRdb::ConvertToLauncherAbilityResourceInfo(
    const std::shared_ptr<NativeRdb::ResultSet> &absSharedResultSet,
    const uint32_t flags,
    LauncherAbilityResourceInfo &launcherAbilityResourceInfo)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet is nullptr");
        return false;
    }
    std::string key;
    auto ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_NAME, key);
    CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString name failed, ret: %{public}d");
    ParseKey(key, launcherAbilityResourceInfo);
    if (launcherAbilityResourceInfo.extensionAbilityType != -1) {
        return false;
    }
    if (launcherAbilityResourceInfo.moduleName.empty() || launcherAbilityResourceInfo.abilityName.empty()) {
        APP_LOGW("key:%{public}s not launcher ability resource info", key.c_str());
        return false;
    }
    bool getAll = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL);
    bool getLabel = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL);
    if (getAll || getLabel) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_LABEL, launcherAbilityResourceInfo.label);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label failed, ret: %{public}d");
    }

    bool getIcon = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON);
    if (getAll || getIcon) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_ICON, launcherAbilityResourceInfo.icon);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label icon, ret: %{public}d");
    }

    bool getDrawable = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR);
    if (getDrawable) {
        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_FOREGROUND,
            launcherAbilityResourceInfo.foreground);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob foreground, ret: %{public}d");

        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_BACKGROUND,
            launcherAbilityResourceInfo.background);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob background, ret: %{public}d");
    }
    return true;
}

bool BundleResourceRdb::ConvertToExtensionAbilityResourceInfo(
    const std::shared_ptr<NativeRdb::ResultSet> &absSharedResultSet,
    const uint32_t flags,
    LauncherAbilityResourceInfo &launcherAbilityResourceInfo)
{
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet is nullptr");
        return false;
    }
    std::string key;
    auto ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_NAME, key);
    CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString name failed, ret: %{public}d");
    ParseKey(key, launcherAbilityResourceInfo);
    if (launcherAbilityResourceInfo.moduleName.empty() || launcherAbilityResourceInfo.abilityName.empty()) {
        APP_LOGW("key:%{public}s not launcher ability resource info", key.c_str());
        return false;
    }
    bool getAll = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_ALL);
    bool getLabel = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_LABEL);
    if (getAll || getLabel) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_LABEL, launcherAbilityResourceInfo.label);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label failed, ret: %{public}d");
    }

    bool getIcon = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_ICON);
    if (getAll || getIcon) {
        ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_ICON, launcherAbilityResourceInfo.icon);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString label icon, ret: %{public}d");
    }

    bool getDrawable = (flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_DRAWABLE_DESCRIPTOR);
    if (getDrawable) {
        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_FOREGROUND,
            launcherAbilityResourceInfo.foreground);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob foreground, ret: %{public}d");

        ret = absSharedResultSet->GetBlob(BundleResourceConstants::INDEX_BACKGROUND,
            launcherAbilityResourceInfo.background);
        CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetBlob background, ret: %{public}d");
    }
    return true;
}

bool BundleResourceRdb::UpdateResourceForSystemStateChanged(const std::vector<ResourceInfo> &resourceInfos)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    if (resourceInfos.empty()) {
        APP_LOGE("resourceInfos is empty");
        return false;
    }
    std::string systemState = BundleSystemState::GetInstance().ToString();
    int64_t timeStamp = BundleUtil::GetCurrentTimeMs();
    bool ret = true;
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    for (const auto &resourceInfo : resourceInfos) {
        NativeRdb::ValuesBucket valuesBucket;
        valuesBucket.PutString(BundleResourceConstants::NAME, resourceInfo.GetKey());
        valuesBucket.PutString(BundleResourceConstants::SYSTEM_STATE, systemState);
        // process label
        if (!resourceInfo.label_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::LABEL, resourceInfo.label_);
        } else if (!resourceInfos[0].label_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::LABEL, resourceInfos[0].label_);
        }
        // process icon
        if (!resourceInfo.icon_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::ICON, resourceInfo.icon_);
            valuesBucket.PutBlob(BundleResourceConstants::FOREGROUND, resourceInfo.foreground_);
            valuesBucket.PutBlob(BundleResourceConstants::BACKGROUND, resourceInfo.background_);
        } else if (!resourceInfos[0].icon_.empty()) {
            valuesBucket.PutString(BundleResourceConstants::ICON, resourceInfos[0].icon_);
            valuesBucket.PutBlob(BundleResourceConstants::FOREGROUND, resourceInfos[0].foreground_);
            valuesBucket.PutBlob(BundleResourceConstants::BACKGROUND, resourceInfos[0].background_);
        }
        valuesBucket.PutLong(BundleResourceConstants::UPDATE_TIME, timeStamp);
        absRdbPredicates.EqualTo(BundleResourceConstants::NAME, resourceInfo.GetKey());
        if (!rdbDataManager_->UpdateOrInsertData(valuesBucket, absRdbPredicates)) {
            APP_LOGE("bundleName: %{public}s UpdateData failed", resourceInfo.GetKey().c_str());
            ret = false;
        }
        absRdbPredicates.Clear();
    }
    return ret;
}

bool BundleResourceRdb::GetCurrentSystemState(std::string &systemState)
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.EqualTo(BundleResourceConstants::NAME, SYSTEM_RESOURCES_APP);
    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGW("bundleName:%{public}s failed due rdb QueryByStep failed", SYSTEM_RESOURCES_APP);
        return false;
    }

    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGW("bundleName:%{public}s GoToFirstRow failed, ret: %{public}d", SYSTEM_RESOURCES_APP, ret);
        return false;
    }
    ret = absSharedResultSet->GetString(BundleResourceConstants::INDEX_SYSTEM_STATE, systemState);
    CHECK_RDB_RESULT_RETURN_IF_FAIL(ret, "GetString name failed, ret: %{public}d");
    APP_LOGI("current resource rdb systemState:%{public}s", systemState.c_str());
    return true;
}

bool BundleResourceRdb::DeleteNotExistResourceInfo()
{
    HITRACE_METER_NAME_EX(HITRACE_LEVEL_INFO, HITRACE_TAG_APP, __PRETTY_FUNCTION__, nullptr);
    // need delete not current systemState resource
    std::string systemState = BundleSystemState::GetInstance().ToString();
    APP_LOGI_NOFUNC("current systemState:%{public}s", systemState.c_str());
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.NotEqualTo(BundleResourceConstants::SYSTEM_STATE, systemState);
    return rdbDataManager_->DeleteData(absRdbPredicates);
}

bool BundleResourceRdb::GetExtensionAbilityResourceInfo(const std::string &bundleName,
    const ExtensionAbilityType extensionAbilityType, const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &extensionAbilityResourceInfo, const int32_t appIndex)
{
    ResourceInfo resourceInfo;
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.BeginsWith(BundleResourceConstants::NAME, resourceInfo.GetKey() +
        BundleResourceConstants::SEPARATOR);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("QueryByStep failed bundleName %{public}s failed, systemState %{public}s",
            bundleName.c_str(), systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("bundleName %{public}s GoToFirstRow failed, ret %{public}d, systemState:%{public}s",
            bundleName.c_str(), ret, systemState.c_str());
        return false;
    }

    do {
        LauncherAbilityResourceInfo resourceInfo;
        if (ConvertToExtensionAbilityResourceInfo(absSharedResultSet, flags, resourceInfo)) {
            if (resourceInfo.extensionAbilityType == static_cast<int32_t>(extensionAbilityType)) {
                extensionAbilityResourceInfo.push_back(resourceInfo);
            }
        }
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);

    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) {
        std::sort(extensionAbilityResourceInfo.begin(), extensionAbilityResourceInfo.end(),
            [](LauncherAbilityResourceInfo &resourceA, LauncherAbilityResourceInfo &resourceB) {
                return resourceA.label < resourceB.label;
            });
    }
    return !extensionAbilityResourceInfo.empty();
}

bool BundleResourceRdb::GetAllExtensionAbilityResourceInfo(const std::string &bundleName, const uint32_t flags,
    std::vector<LauncherAbilityResourceInfo> &extensionAbilityResourceInfo, const int32_t appIndex)
{
    ResourceInfo resourceInfo;
    resourceInfo.bundleName_ = bundleName;
    resourceInfo.appIndex_ = appIndex;
    NativeRdb::AbsRdbPredicates absRdbPredicates(BundleResourceConstants::BUNDLE_RESOURCE_RDB_TABLE_NAME);
    absRdbPredicates.BeginsWith(BundleResourceConstants::NAME, resourceInfo.GetKey() +
        BundleResourceConstants::SEPARATOR);
    std::string systemState = BundleSystemState::GetInstance().ToString();

    auto absSharedResultSet = rdbDataManager_->QueryByStep(absRdbPredicates);
    if (absSharedResultSet == nullptr) {
        APP_LOGE("QueryByStep failed bundleName %{public}s failed, systemState %{public}s",
            bundleName.c_str(), systemState.c_str());
        return false;
    }
    ScopeGuard stateGuard([absSharedResultSet] { absSharedResultSet->Close(); });
    auto ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("bundleName %{public}s GoToFirstRow failed, ret %{public}d, systemState:%{public}s",
            bundleName.c_str(), ret, systemState.c_str());
        return false;
    }

    do {
        LauncherAbilityResourceInfo resourceInfo;
        if (ConvertToExtensionAbilityResourceInfo(absSharedResultSet, flags, resourceInfo)) {
            if (resourceInfo.extensionAbilityType >= 0) {
                extensionAbilityResourceInfo.push_back(resourceInfo);
            }
        }
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);

    if ((flags & static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) ==
        static_cast<uint32_t>(ResourceFlag::GET_RESOURCE_INFO_WITH_SORTED_BY_LABEL)) {
        std::sort(extensionAbilityResourceInfo.begin(), extensionAbilityResourceInfo.end(),
            [](LauncherAbilityResourceInfo &resourceA, LauncherAbilityResourceInfo &resourceB) {
                return resourceA.label < resourceB.label;
            });
    }
    return !extensionAbilityResourceInfo.empty();
}

void BundleResourceRdb::ParseKey(const std::string &key,
    LauncherAbilityResourceInfo &launcherAbilityResourceInfo)
{
    ResourceInfo info;
    info.ParseKey(key);
    launcherAbilityResourceInfo.bundleName = info.bundleName_;
    launcherAbilityResourceInfo.moduleName = info.moduleName_;
    launcherAbilityResourceInfo.abilityName = info.abilityName_;
    launcherAbilityResourceInfo.appIndex = info.appIndex_;
    launcherAbilityResourceInfo.extensionAbilityType = info.extensionAbilityType_;
}

void BundleResourceRdb::ParseKey(const std::string &key,
    BundleResourceInfo &bundleResourceInfo)
{
    ResourceInfo info;
    info.ParseKey(key);
    bundleResourceInfo.bundleName = info.bundleName_;
    bundleResourceInfo.appIndex = info.appIndex_;
}
} // AppExecFwk
} // OHOS
