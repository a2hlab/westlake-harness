/*
 * Copyright (c) 2021-2023 Huawei Device Co., Ltd.
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
#ifndef HIVIEW_FAULT_LOG_INFO_H
#define HIVIEW_FAULT_LOG_INFO_H
#include <cinttypes>
#include <list>
#include <map>
#include <string>

namespace OHOS {
namespace HiviewDFX {
struct FaultLogInfo {
    int64_t time {0};
    int32_t id {0};
    int32_t pid {0};
    std::shared_ptr<int32_t> pipeFd;
    int32_t faultLogType {0};
    int32_t fd = {-1};
    uint32_t logFileCutoffSizeBytes {0};
    std::string module;
    std::string reason;
    std::string summary;
    std::string logPath;
    std::string registers;
    std::string otherThreadInfo;
    std::string sanitizerType;
    std::map<std::string, std::string> sectionMap;
    std::list<std::string> additionalLogs;
    std::map<std::string, std::string> parsedLogInfo;
    bool dumpLogToFaultlogger {true};
    bool reportToAppEvent {true};
};

enum FaultLogType {
    ALL = 0,
    CPP_CRASH = 2,
    JS_CRASH = 3,
    APP_FREEZE = 4,
    SYS_FREEZE = 5,
    SYS_WARNING = 6,
    APPFREEZE_WARNING = 7,
    RUST_PANIC = 8,
    CJ_ERROR = 9,
    ADDR_SANITIZER = 10,
    PROCESS_PAGE_INFO = 11,
    MAX_TYPE,
};
}  // namespace HiviewDFX
}  // namespace OHOS
#endif  // HIVIEW_FAULT_LOG_INFO_H
