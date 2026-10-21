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
#ifndef FAULTLOG_MANAGER_H
#define FAULTLOG_MANAGER_H
#include <cstdint>
#include <ctime>
#include <list>
#include <memory>
#include <string>

#include "log_store_ex.h"
#include "faultlog_info_inner.h"
#include "faultlog_database.h"

namespace OHOS {
namespace HiviewDFX {
class FaultLogManager {
public:
    // use rawdb manage fault log infos
    void Init();
    bool GetFaultLogContent(const std::string& name, std::string& content) const;
    int32_t CreateTempFaultLogFile(time_t time, int32_t id, int32_t faultType, const std::string& module) const;
    std::list<std::string> GetFaultLogFileList(const std::string& module, time_t time, int32_t id, int32_t faultType,
                                               int32_t maxNum) const;
    std::string SaveFaultLogToFile(FaultLogInfo& info) const;
    void RemoveOldFile(FaultLogInfo& info) const;

private:
    void InitWarningLogStore();
    std::string GetFaultLogFilePath(int32_t faultLogType, const std::string& fileName) const;
    int GetFaultLogFileFd(int32_t faultLogType, const std::string& fileName) const;
    void ReduceLogFileListSize(std::list<std::string>& infoVec, int32_t maxNum) const;
    std::unique_ptr<LogStoreEx> store_;
    std::unique_ptr<LogStoreEx> warningLogStore_;
};
}  // namespace HiviewDFX
}  // namespace OHOS
#endif
