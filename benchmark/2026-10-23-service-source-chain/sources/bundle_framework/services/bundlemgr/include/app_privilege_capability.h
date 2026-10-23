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

#ifndef FOUNDATION_APPEXECFWK_SERVICES_BUNDLEMGR_INCLUDE_APP_PRIVILEGE_CAPABILITY_H
#define FOUNDATION_APPEXECFWK_SERVICES_BUNDLEMGR_INCLUDE_APP_PRIVILEGE_CAPABILITY_H

#include "bundle_util.h"

namespace OHOS {
namespace AppExecFwk {
struct AppPrivilegeCapability {
    bool allowMultiProcess = false;
    bool allowQueryPriority = false;
    bool allowExcludeFromMissions = false;
    bool allowMissionNotCleared = false;
    bool allowUsePrivilegeExtension = false;
    bool userDataClearable = true;
    bool hideDesktopIcon = false;
    bool formVisibleNotify = false;
    bool appShareLibrary = false;
    bool allowEnableNotification = false;
    bool allowArkTsLargeHeap = false;

    std::string ToString()
    {
        return "[ allowMultiProcess = " + BundleUtil::GetBoolStrVal(allowMultiProcess)
            + ", allowQueryPriority = " + BundleUtil::GetBoolStrVal(allowQueryPriority)
            + ", allowExcludeFromMissions = " + BundleUtil::GetBoolStrVal(allowExcludeFromMissions)
            + ", allowMissionNotCleared = " + BundleUtil::GetBoolStrVal(allowMissionNotCleared)
            + ", allowUsePrivilegeExtension = " + BundleUtil::GetBoolStrVal(allowUsePrivilegeExtension)
            + ", userDataClearable = " + BundleUtil::GetBoolStrVal(userDataClearable)
            + ", hideDesktopIcon = " + BundleUtil::GetBoolStrVal(hideDesktopIcon)
            + ", formVisibleNotify = " + BundleUtil::GetBoolStrVal(formVisibleNotify)
            + ", appShareLibrary = " + BundleUtil::GetBoolStrVal(appShareLibrary)
            + ", allowEnableNotification = " + BundleUtil::GetBoolStrVal(allowEnableNotification)
            + ", allowArkTsLargeHeap = " + BundleUtil::GetBoolStrVal(allowArkTsLargeHeap) + "]";
    }
};
}  // namespace AppExecFwk
}  // namespace OHOS
#endif  // FOUNDATION_APPEXECFWK_SERVICES_BUNDLEMGR_INCLUDE_APP_PRIVILEGE_CAPABILITY_H
