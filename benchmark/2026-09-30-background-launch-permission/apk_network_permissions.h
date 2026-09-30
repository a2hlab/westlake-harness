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

// System permissions granted to EVERY synthesized Android bundle, independent of
// its Android manifest (unlike MapApkNetworkPermissions, which is driven by
// usesPermissions). These cover OH-side capabilities that an Android app assumes
// implicitly.
//
// ohos.permission.START_ABILITIES_FROM_BACKGROUND lets an in-app startAbility
// proceed while the launched activity's session is still in the pending-foreground
// state. Android apps routinely call startActivity() from MainActivity.onCreate
// (e.g. Wikipedia -> org.wikipedia.onboarding.InitialOnboardingActivity welcome
// page; the binaryeye/Splash family -> Main). On OH the caller session is
// session_state=0 at that instant, so WMSLife::DisallowActivationFromPendingBackground
// blocks the nested start with "no permission to start ability from Background"
// unless the caller holds this permission (verified on 5ea, run
// 20260930T014739, hilog AAFwk permission_verification + WMSLife DisallowActivation).
//
// Permission properties (authoritative, /system/etc/access_token/permission_definitions.json
// on the 5ea DAYU600 generation 74d1d6d48210):
//   grantMode=system_grant, availableLevel=system_basic, availableType=SYSTEM,
//   provisionEnable=true.
// Because availableLevel(system_basic) exceeds the synthesized bundle's
// APL_NORMAL, it cannot be held by declaration alone. provisionEnable=true is the
// enabler: the caller adds it to HapPolicyParams.aclRequestedList (ACL to exceed
// apl) plus preAuthorizationInfo (install-time pre-grant, non-cancelable) — the
// same shape OH itself uses in /system/etc/app/install_list_permissions.json,
// where this permission already appears with userCancellable:false. grantMode=
// system_grant then makes InitHapToken grant it by policy without any user prompt.
// This avoids raising apl to system_basic (which would relabel the sandbox dirs)
// or marking the bundle isSystemApp (which would over-privilege a third-party app).
inline std::vector<std::string> AdapterBackgroundLaunchPermissions()
{
    return {
        "ohos.permission.START_ABILITIES_FROM_BACKGROUND",
    };
}
} // namespace oh_adapter
#endif
