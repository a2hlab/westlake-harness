/*
 * Copyright (c) 2021 Huawei Device Co., Ltd.
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
#ifndef HIVIEWDFX_HIVIEW_FAULTLOGGER_UTIL_H
#define HIVIEWDFX_HIVIEW_FAULTLOGGER_UTIL_H

#include <cstdint>
#include <ctime>
#include <string>
#include <string_view>
#include <map>

#include "faultlog_info_inner.h"
#include "json/json.h"

namespace OHOS {
namespace HiviewDFX {
std::string GetFormatedTime(uint64_t target);
std::string GetFormatedTimeWithMillsec(uint64_t time);
std::string GetFaultNameByType(int32_t faultType, bool asFileName);
std::string GetFaultLogName(const FaultLogInfo& info);
int32_t GetLogTypeByName(const std::string& type);
FaultLogInfo ExtractInfoFromFileName(const std::string& fileName);
FaultLogInfo ExtractInfoFromTempFile(const std::string& fileName);
int32_t GetRawEventIdByType(int32_t logType);
std::string RegulateModuleNameIfNeed(const std::string& name);
time_t GetFileLastAccessTimeStamp(const std::string& fileName);
std::string GetCppCrashTempLogName(const FaultLogInfo& info);
std::string GetDebugSignalTempLogName(const FaultLogInfo& info);
std::string GetSanitizerTempLogName(int32_t pid, const std::string& happenTime);
std::string GetThreadStack(const std::string& path, int32_t threadId);
bool IsValidPath(const std::string& path);
bool ExtractSubMoudleName(std::string &module);
bool IsSystemProcess(std::string_view processName, int32_t uid);
std::string GetStrValFromMap(const std::map<std::string, std::string>& map, const std::string& key);
FaultLogType GetLogTypeByEventName(const std::string& type);
uint64_t GetProcessInfo(const std::map<std::string, std::string>& sectionMap, const std::string &key);
Json::Value GetMemoryJsonValue(const std::map<std::string, std::string>& sectionMap);
std::string GetSummaryFromSectionMap(int32_t type, const std::map<std::string, std::string>& maps);
void AddBundleInfo(FaultLogInfo& info);
void AddForegroundInfo(FaultLogInfo& info);
std::list<std::string> GetDigtStrArr(const std::string &target);
void AddPagesHistory(FaultLogInfo& info, bool onlyReportApp);
void GetProcMemInfo(FaultLogInfo& info);
}  // namespace HiviewDFX
}  // namespace OHOS
#endif  // HIVIEWDFX_HIVIEW_FAULTLOGGER_UTIL_H
