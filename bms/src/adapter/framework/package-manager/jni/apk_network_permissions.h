#ifndef OH_ADAPTER_APK_NETWORK_PERMISSIONS_H
#define OH_ADAPTER_APK_NETWORK_PERMISSIONS_H

#include <algorithm>
#include <string>
#include <vector>

namespace oh_adapter {
// Exact mappings already present in PermissionMapper::MapToOH. Keep the
// install-time system-grant projection limited to these two network requests.
inline std::vector<std::string> MapApkNetworkPermissions(
    const std::vector<std::string>& requested)
{
    std::vector<std::string> result;
    for (const auto& name : requested) {
        const char* mapped = nullptr;
        if (name == "android.permission.INTERNET") {
            mapped = "ohos.permission.INTERNET";
        } else if (name == "android.permission.ACCESS_NETWORK_STATE") {
            mapped = "ohos.permission.GET_NETWORK_INFO";
        }
        if (mapped && std::find(result.begin(), result.end(), mapped) == result.end()) {
            result.emplace_back(mapped);
        }
    }
    return result;
}
} // namespace oh_adapter
#endif
