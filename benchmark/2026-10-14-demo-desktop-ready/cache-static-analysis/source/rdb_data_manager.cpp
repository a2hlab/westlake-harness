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
#include <atomic>
#include <cstdlib>
#include "bundle_service_constants.h"
#include "rdb_data_manager.h"

#include "app_log_wrapper.h"
#include "bundle_util.h"
#include "event_report.h"
#include "installd_client.h"
#include "scope_guard.h"

namespace OHOS {
namespace AppExecFwk {
namespace {
constexpr const char* BMS_KEY = "KEY";
constexpr const char* BMS_VALUE = "VALUE";
constexpr int8_t BMS_KEY_INDEX = 0;
constexpr int8_t BMS_VALUE_INDEX = 1;
constexpr int16_t WRITE_TIMEOUT = 300; // 300s
constexpr int32_t CLOSE_TIME = 20 * 1000; // delay 20s stop rdbStore
constexpr int32_t OPERATION_TYPE_OF_INSUFFICIENT_DISK = 3;
static std::atomic<int64_t> g_lastReportTime = 0;
constexpr int64_t REPORTING_INTERVAL = 1000 * 60 * 30; // 30min
constexpr int32_t RETRY_TIMES = 3;
constexpr int32_t RETRY_INTERVAL = 500; // 500ms
constexpr const char* INTEGRITY_CHECK = "PRAGMA integrity_check";
constexpr const char* CHECK_OK = "ok";
const std::unordered_map<int32_t, int32_t> RDB_ERR_MAP = {
    {NativeRdb::E_OK, ERR_OK},
    {NativeRdb::E_NOT_SELECT, ERR_APPEXECFWK_DB_SQL_MUST_BE_QUERY_STATEMENT},
    {NativeRdb::E_COLUMN_OUT_RANGE, ERR_APPEXECFWK_DB_COLUMN_OUT_OF_BOUNDS},
    {NativeRdb::E_INVALID_FILE_PATH, ERR_APPEXECFWK_DB_INVALID_DATABASE_PATH},
    {NativeRdb::E_ROW_OUT_RANGE, ERR_APPEXECFWK_DB_ROW_OUT_OF_BOUNDS},
    {NativeRdb::E_NO_ROW_IN_QUERY, ERR_APPEXECFWK_DB_NO_DATA_MEETS_CONDITION},
    {NativeRdb::E_ALREADY_CLOSED, ERR_APPEXECFWK_DB_ALREADY_CLOSED},
    {NativeRdb::E_DATABASE_BUSY, ERR_APPEXECFWK_DB_DO_NOT_RESPOND},
    {NativeRdb::E_WAL_SIZE_OVER_LIMIT, ERR_APPEXECFWK_DB_THE_WAL_FILE_SIZE_OVER_DEFAULT_LIMIT},
    {NativeRdb::E_GET_DATAOBSMGRCLIENT_FAIL, ERR_APPEXECFWK_DB_FAILED_TO_GET_DATA_OBS_MGR_CLIENT},
    {NativeRdb::E_TYPE_MISMATCH, ERR_APPEXECFWK_DB_THE_TYPE_OF_DISTRIBUTED_TABLE_NOT_MATCH},
    {NativeRdb::E_SQLITE_FULL, ERR_APPEXECFWK_DB_IS_FULL},
    {NativeRdb::E_NOT_SUPPORT_THE_SQL, ERR_APPEXECFWK_DB_NOT_SUPPORT_THS_SQL},
    {NativeRdb::E_ATTACHED_DATABASE_EXIST, ERR_APPEXECFWK_DB_IS_ALREADY_ATTACHED},
    {NativeRdb::E_SQLITE_ERROR, ERR_APPEXECFWK_DB_SQL_GENERIC_ERROR},
    {NativeRdb::E_SQLITE_CORRUPT, ERR_APPEXECFWK_DB_SQL_CORRUPTED},
    {NativeRdb::E_SQLITE_ABORT, ERR_APPEXECFWK_DB_SQL_CALLBACK_ROUTINE_REQUESTED_AN_ABORT},
    {NativeRdb::E_SQLITE_PERM, ERR_APPEXECFWK_DB_SQL_ACCESS_PERMISSION_DENIED},
    {NativeRdb::E_SQLITE_BUSY, ERR_APPEXECFWK_DB_SQL_FILE_IS_LOCKED},
    {NativeRdb::E_SQLITE_LOCKED, ERR_APPEXECFWK_DB_SQL_TABLE_IS_LOCKED},
    {NativeRdb::E_SQLITE_NOMEM, ERR_APPEXECFWK_DB_SQL_DB_IS_OUT_OF_MEMORY},
    {NativeRdb::E_SQLITE_READONLY, ERR_APPEXECFWK_DB_SQL_ATTEMPT_WRITE_READONLY_DB},
    {NativeRdb::E_SQLITE_IOERR, ERR_APPEXECFWK_DB_SQL_SOME_KIND_OF_DISK_IO_ERROR},
    {NativeRdb::E_SQLITE_CANTOPEN, ERR_APPEXECFWK_DB_SQL_UNABLE_OPEN_DB_FILE},
    {NativeRdb::E_SQLITE_TOOBIG, ERR_APPEXECFWK_DB_SQL_TEXT_OR_BLOB_EXCEED_SIZE_LIMIT},
    {NativeRdb::E_SQLITE_CONSTRAINT, ERR_APPEXECFWK_DB_SQL_ABORT_DUE_TO_CONSTRAINT_VIOLATION},
    {NativeRdb::E_SQLITE_MISMATCH, ERR_APPEXECFWK_DB_SQL_DATA_TYPE_MISMATCH},
    {NativeRdb::E_SQLITE_MISUSE, ERR_APPEXECFWK_DB_SQL_LIBRARY_USED_INCORRECTLY},
    {NativeRdb::E_CONFIG_INVALID_CHANGE, ERR_APPEXECFWK_DB_CONFIG_CHANGED},
    {NativeRdb::E_NOT_SUPPORT, ERR_APPEXECFWK_DB_CAPABILITY_NOT_SUPPORT},
};
}

std::mutex RdbDataManager::restoreRdbMapMutex_;
std::unordered_map<std::string, std::mutex> RdbDataManager::restoreRdbMap_;

RdbDataManager::RdbDataManager(const BmsRdbConfig &bmsRdbConfig)
    : bmsRdbConfig_(bmsRdbConfig)
{
    delayedTaskMgr_ = std::make_shared<SingleDelayedTaskMgr>(bmsRdbConfig.tableName, CLOSE_TIME);
}

RdbDataManager::~RdbDataManager()
{
    rdbStore_ = nullptr;
}

void RdbDataManager::ClearCache()
{
    NativeRdb::RdbHelper::ClearCache();
}

std::mutex &RdbDataManager::GetRdbRestoreMutex(const std::string &dbName)
{
    std::lock_guard<std::mutex> restoreLock(restoreRdbMapMutex_);
    if (!isInitial_) {
        isInitial_ = restoreRdbMap_.find(dbName) != restoreRdbMap_.end();
    }
    return restoreRdbMap_[dbName];
}

ErrCode RdbDataManager::GetRdbStoreFromNative()
{
    auto &mutex = GetRdbRestoreMutex(bmsRdbConfig_.dbName);
    std::lock_guard<std::mutex> restoreLock(mutex);
    NativeRdb::RdbStoreConfig rdbStoreConfig(bmsRdbConfig_.dbPath + bmsRdbConfig_.dbName);
    rdbStoreConfig.SetSecurityLevel(NativeRdb::SecurityLevel::S1);
    rdbStoreConfig.SetWriteTime(WRITE_TIMEOUT);
    rdbStoreConfig.SetAllowRebuild(true);
    rdbStoreConfig.SetHaMode(NativeRdb::HAMode::MAIN_REPLICA);
    // for check db exist or not
    bool isNewDb = false;
    if (access(rdbStoreConfig.GetPath().c_str(), F_OK) != 0) {
        APP_LOGW_NOFUNC("bms db :%{public}s is not exist, need to create. errno:%{public}d",
            rdbStoreConfig.GetPath().c_str(), errno);
        isNewDb = true;
    }
    int32_t errCode = NativeRdb::E_OK;
    BmsRdbOpenCallback bmsRdbOpenCallback(bmsRdbConfig_);
    rdbStore_ = NativeRdb::RdbHelper::GetRdbStore(
        rdbStoreConfig,
        bmsRdbConfig_.version,
        bmsRdbOpenCallback, errCode);
    if (rdbStore_ == nullptr) {
        APP_LOGE("GetRdbStore failed, errCode:%{public}d", errCode);
        SendDbErrorEvent(bmsRdbConfig_.dbName, static_cast<int32_t>(DB_OPERATION_TYPE::OPEN), errCode);
        return errCode;
    }
    CheckSystemSizeAndHisysEvent(bmsRdbConfig_.dbPath, bmsRdbConfig_.dbName);
    bool isNeedRebuildDb = false;
    if (!isInitial_) {
        isNeedRebuildDb = RdbIntegrityCheckNeedRestore();
        isInitial_ = true;
    }
    NativeRdb::RebuiltType rebuildType = NativeRdb::RebuiltType::NONE;
    int32_t rebuildCode = rdbStore_->GetRebuilt(rebuildType);
    if (isNewDb || rebuildType == NativeRdb::RebuiltType::REPAIRED) {
        APP_LOGI("rdb repaired, reset rdb file");
        InstalldClient::GetInstance()->ResetBmsDBSecurity();
    }
    if (rebuildType == NativeRdb::RebuiltType::REBUILT || isNeedRebuildDb) {
        APP_LOGI("start %{public}s restore ret %{public}d, type:%{public}d", bmsRdbConfig_.dbName.c_str(),
            rebuildCode, static_cast<int32_t>(rebuildType));
        int32_t restoreRet = rdbStore_->Restore("");
        if (restoreRet != NativeRdb::E_OK) {
            APP_LOGE("rdb restore failed ret:%{public}d", restoreRet);
        } else {
            APP_LOGI("rdb rebuilt, reset rdb file");
            InstalldClient::GetInstance()->ResetBmsDBSecurity();
        }
        SendDbErrorEvent(bmsRdbConfig_.dbName, static_cast<int32_t>(DB_OPERATION_TYPE::REBUILD), rebuildCode);
        return restoreRet;
    }
    return ERR_OK;
}

std::shared_ptr<NativeRdb::RdbStore> RdbDataManager::GetRdbStore(ErrCode &result)
{
    std::lock_guard<std::mutex> lock(rdbMutex_);
    if (rdbStore_ == nullptr) {
        result = GetRdbStoreFromNative();
    }
    auto it = RDB_ERR_MAP.find(result);
    if (it != RDB_ERR_MAP.end()) {
        result = it->second;
    } else {
        result = ERR_APPEXECFWK_INSTALL_INTERNAL_ERROR;
    }

    if (rdbStore_ != nullptr) {
        DelayCloseRdbStore();
    }
    return rdbStore_;
}

void RdbDataManager::CheckSystemSizeAndHisysEvent(const std::string &path, const std::string &fileName)
{
    if (!CheckIsSatisfyTime()) {
        APP_LOGD("not satisfy time");
        return;
    }
    bool isInsufficientSpace = BundleUtil::CheckSystemSizeAndHisysEvent(path, fileName);
    if (isInsufficientSpace) {
        APP_LOGW("space not enough %{public}s", fileName.c_str());
        EventReport::SendDiskSpaceEvent(fileName, 0, OPERATION_TYPE_OF_INSUFFICIENT_DISK);
    }
}

bool RdbDataManager::CheckIsSatisfyTime()
{
    int64_t now = BundleUtil::GetCurrentTimeMs();
    if (abs(now - g_lastReportTime) < REPORTING_INTERVAL) {
        APP_LOGD("time is not up yet");
        return false;
    }
    g_lastReportTime = now;
    return true;
}

void RdbDataManager::SendDbErrorEvent(const std::string &dbName, int32_t operationType, int32_t errorCode)
{
    EventReport::SendDbErrorEvent(dbName, operationType, errorCode);
}

bool RdbDataManager::InsertData(const std::string &key, const std::string &value)
{
    APP_LOGD("InsertData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    int64_t rowId = -1;
    NativeRdb::ValuesBucket valuesBucket;
    valuesBucket.PutString(BMS_KEY, key);
    valuesBucket.PutString(BMS_VALUE, value);
    ret = InsertWithRetry(rdbStore, rowId, valuesBucket);
    return ret == NativeRdb::E_OK;
}

ErrCode RdbDataManager::InsertDataWithCode(const std::string &key, const std::string &value)
{
    APP_LOGD("InsertData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return ret;
    }

    int64_t rowId = -1;
    NativeRdb::ValuesBucket valuesBucket;
    valuesBucket.PutString(BMS_KEY, key);
    valuesBucket.PutString(BMS_VALUE, value);
    return InsertWithRetry(rdbStore, rowId, valuesBucket);
}

bool RdbDataManager::InsertData(const NativeRdb::ValuesBucket &valuesBucket)
{
    APP_LOGD("InsertData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    int64_t rowId = -1;
    ret = InsertWithRetry(rdbStore, rowId, valuesBucket);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::BatchInsert(int64_t &outInsertNum, const std::vector<NativeRdb::ValuesBucket> &valuesBuckets)
{
    APP_LOGD("BatchInsert start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    ret = rdbStore->BatchInsert(outInsertNum, bmsRdbConfig_.tableName, valuesBuckets);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::UpdateData(const std::string &key, const std::string &value)
{
    APP_LOGD("UpdateData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    int32_t rowId = -1;
    NativeRdb::AbsRdbPredicates absRdbPredicates(bmsRdbConfig_.tableName);
    absRdbPredicates.EqualTo(BMS_KEY, key);
    NativeRdb::ValuesBucket valuesBucket;
    valuesBucket.PutString(BMS_KEY, key);
    valuesBucket.PutString(BMS_VALUE, value);
    ret = rdbStore->Update(rowId, valuesBucket, absRdbPredicates);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::UpdateData(
    const NativeRdb::ValuesBucket &valuesBucket, const NativeRdb::AbsRdbPredicates &absRdbPredicates)
{
    APP_LOGD("UpdateData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    if (absRdbPredicates.GetTableName() != bmsRdbConfig_.tableName) {
        APP_LOGE("RdbStore table is invalid");
        return false;
    }
    int32_t rowId = -1;
    ret = rdbStore->Update(rowId, valuesBucket, absRdbPredicates);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::UpdateOrInsertData(
    const NativeRdb::ValuesBucket &valuesBucket, const NativeRdb::AbsRdbPredicates &absRdbPredicates)
{
    APP_LOGD("UpdateOrInsertData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    if (absRdbPredicates.GetTableName() != bmsRdbConfig_.tableName) {
        APP_LOGE("RdbStore table is invalid");
        return false;
    }
    int32_t rowId = -1;
    ret = rdbStore->Update(rowId, valuesBucket, absRdbPredicates);
    if ((ret == NativeRdb::E_OK) && (rowId == 0)) {
        APP_LOGI_NOFUNC("data not exist, need insert data");
        int64_t rowIdInsert = -1;
        ret = rdbStore->InsertWithConflictResolution(
            rowIdInsert, bmsRdbConfig_.tableName, valuesBucket, NativeRdb::ConflictResolution::ON_CONFLICT_REPLACE);
    }
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::DeleteData(const std::string &key)
{
    APP_LOGD("DeleteData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    int32_t rowId = -1;
    NativeRdb::AbsRdbPredicates absRdbPredicates(bmsRdbConfig_.tableName);
    absRdbPredicates.EqualTo(BMS_KEY, key);
    ret = rdbStore->Delete(rowId, absRdbPredicates);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::DeleteData(const NativeRdb::AbsRdbPredicates &absRdbPredicates)
{
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    if (absRdbPredicates.GetTableName() != bmsRdbConfig_.tableName) {
        APP_LOGE("RdbStore table is invalid");
        return false;
    }
    int32_t rowId = -1;
    ret = rdbStore->Delete(rowId, absRdbPredicates);
    return ret == NativeRdb::E_OK;
}

bool RdbDataManager::QueryData(const std::string &key, std::string &value)
{
    APP_LOGD("QueryData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    NativeRdb::AbsRdbPredicates absRdbPredicates(bmsRdbConfig_.tableName);
    absRdbPredicates.EqualTo(BMS_KEY, key);
    auto absSharedResultSet = rdbStore->QueryByStep(absRdbPredicates, std::vector<std::string>());
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet failed");
        return false;
    }
    ScopeGuard stateGuard([&] { absSharedResultSet->Close(); });
    ret = absSharedResultSet->GoToFirstRow();
    if (ret != NativeRdb::E_OK) {
        APP_LOGE_NOFUNC("GoToFirstRow failed, ret: %{public}d", ret);
        return false;
    }

    ret = absSharedResultSet->GetString(BMS_VALUE_INDEX, value);
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("QueryData failed, ret: %{public}d", ret);
        return false;
    }

    return true;
}

std::shared_ptr<NativeRdb::ResultSet> RdbDataManager::QueryData(
    const NativeRdb::AbsRdbPredicates &absRdbPredicates)
{
    APP_LOGD("QueryData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return nullptr;
    }
    if (absRdbPredicates.GetTableName() != bmsRdbConfig_.tableName) {
        APP_LOGE("RdbStore table is invalid");
        return nullptr;
    }
    auto absSharedResultSet = rdbStore->QueryByStep(absRdbPredicates, std::vector<std::string>());
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet failed");
        return nullptr;
    }
    return absSharedResultSet;
}

bool RdbDataManager::QueryAllData(std::map<std::string, std::string> &datas)
{
    APP_LOGD("QueryAllData start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }

    NativeRdb::AbsRdbPredicates absRdbPredicates(bmsRdbConfig_.tableName);
    auto absSharedResultSet = rdbStore->QueryByStep(absRdbPredicates, std::vector<std::string>());
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet failed");
        return false;
    }
    ScopeGuard stateGuard([&] { absSharedResultSet->Close(); });

    if (absSharedResultSet->GoToFirstRow() != NativeRdb::E_OK) {
        APP_LOGE("GoToFirstRow failed");
        return false;
    }

    do {
        std::string key;
        if (absSharedResultSet->GetString(BMS_KEY_INDEX, key) != NativeRdb::E_OK) {
            APP_LOGE("GetString key failed");
            return false;
        }

        std::string value;
        if (absSharedResultSet->GetString(BMS_VALUE_INDEX, value) != NativeRdb::E_OK) {
            APP_LOGE("GetString value failed");
            return false;
        }

        datas.emplace(key, value);
    } while (absSharedResultSet->GoToNextRow() == NativeRdb::E_OK);
    return !datas.empty();
}

bool RdbDataManager::CreateTable()
{
    std::string createTableSql;
    if (bmsRdbConfig_.createTableSql.empty()) {
        createTableSql = std::string(
            "CREATE TABLE IF NOT EXISTS "
            + bmsRdbConfig_.tableName
            + "(KEY TEXT NOT NULL PRIMARY KEY, VALUE TEXT NOT NULL);");
    } else {
        createTableSql = bmsRdbConfig_.createTableSql;
    }
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    ret = rdbStore->ExecuteSql(createTableSql);
    if (ret != NativeRdb::E_OK) {
        APP_LOGE("CreateTable %{public}s failed, ret: %{public}d", bmsRdbConfig_.tableName.c_str(), ret);
        return false;
    }
    for (const auto &sql : bmsRdbConfig_.insertColumnSql) {
        int32_t insertRet = rdbStore->ExecuteSql(sql);
        if (insertRet != NativeRdb::E_OK) {
            APP_LOGW_NOFUNC("ExecuteSql insertColumnSql failed ret: %{public}d", insertRet);
        }
    }
    return true;
}

bool RdbDataManager::ExecuteSql()
{
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    bool res = true;
    for (const auto &sql : bmsRdbConfig_.insertColumnSql) {
        int32_t insertRet = rdbStore->ExecuteSql(sql);
        if (insertRet != NativeRdb::E_OK) {
            res = false;
            APP_LOGW_NOFUNC("ExecuteSql failed ret: %{public}d", insertRet);
        }
    }
    return res;
}

void RdbDataManager::DelayCloseRdbStore()
{
    APP_LOGD("RdbDataManager DelayCloseRdbStore start");
    std::weak_ptr<RdbDataManager> weakPtr = shared_from_this();
    auto task = [weakPtr]() {
        APP_LOGD("DelayCloseRdbStore thread begin");
        auto sharedPtr = weakPtr.lock();
        if (sharedPtr == nullptr) {
            return;
        }
        std::lock_guard<std::mutex> lock(sharedPtr->rdbMutex_);
        sharedPtr->rdbStore_ = nullptr;
        APP_LOGD("DelayCloseRdbStore of %{public}s thread end", sharedPtr->bmsRdbConfig_.tableName.c_str());
    };
    delayedTaskMgr_->ScheduleDelayedTask(task);
}

bool RdbDataManager::RdbIntegrityCheckNeedRestore()
{
    APP_LOGI_NOFUNC("integrity check start db %{public}s", bmsRdbConfig_.dbName.c_str());
    if (rdbStore_ == nullptr) {
        APP_LOGE("RdbStore is null");
        return false;
    }
    auto [ret, outValue] = rdbStore_->Execute(INTEGRITY_CHECK);
    if (ret == NativeRdb::E_OK) {
        std::string outputResult;
        outValue.GetString(outputResult);
        if (outputResult != CHECK_OK) {
            APP_LOGW("rdb error need to restore");
            return true;
        }
        APP_LOGI_NOFUNC("integrity check succeed db %{public}s", bmsRdbConfig_.dbName.c_str());
    }
    return false;
}

std::shared_ptr<NativeRdb::ResultSet> RdbDataManager::QueryByStep(
    const NativeRdb::AbsRdbPredicates &absRdbPredicates)
{
    APP_LOGD("QueryByStep start");
    ErrCode ret = ERR_OK;
    auto rdbStore = GetRdbStore(ret);
    if (rdbStore == nullptr) {
        APP_LOGE("RdbStore is null");
        return nullptr;
    }
    if (absRdbPredicates.GetTableName() != bmsRdbConfig_.tableName) {
        APP_LOGE("RdbStore table is invalid");
        return nullptr;
    }
    auto absSharedResultSet = rdbStore->QueryByStep(absRdbPredicates, std::vector<std::string>());
    if (absSharedResultSet == nullptr) {
        APP_LOGE("absSharedResultSet failed");
        return nullptr;
    }
    return absSharedResultSet;
}

int32_t RdbDataManager::InsertWithRetry(std::shared_ptr<NativeRdb::RdbStore> rdbStore, int64_t &rowId,
    const NativeRdb::ValuesBucket &valuesBucket)
{
    int32_t retryCnt = 0;
    int32_t ret = 0;
    do {
        ret = rdbStore->InsertWithConflictResolution(rowId, bmsRdbConfig_.tableName,
            valuesBucket, NativeRdb::ConflictResolution::ON_CONFLICT_REPLACE);
        if (ret == NativeRdb::E_OK || !IsRetryErrCode(ret)) {
            break;
        }
        if (++retryCnt < RETRY_TIMES) {
            std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_INTERVAL));
        }
        APP_LOGW("rdb insert failed, retry count: %{public}d, ret: %{public}d", retryCnt, ret);
    } while (retryCnt < RETRY_TIMES);
    auto it = RDB_ERR_MAP.find(ret);
    if (it != RDB_ERR_MAP.end()) {
        ret = it->second;
        return ret;
    }
    return ERR_APPEXECFWK_INSTALL_INTERNAL_ERROR;
}

bool RdbDataManager::IsRetryErrCode(int32_t errCode)
{
    if (errCode == NativeRdb::E_DATABASE_BUSY ||
        errCode == NativeRdb::E_SQLITE_BUSY ||
        errCode == NativeRdb::E_SQLITE_LOCKED ||
        errCode == NativeRdb::E_SQLITE_NOMEM ||
        errCode == NativeRdb::E_SQLITE_IOERR) {
        return true;
    }
    return false;
}
}  // namespace AppExecFwk
}  // namespace OHOS
