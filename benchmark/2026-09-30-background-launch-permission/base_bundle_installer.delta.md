# base_bundle_installer.cpp delta — START_ABILITIES_FROM_BACKGROUND grant

Base: `bms/src/.work/installer-background-launcher/base_bundle_installer.before.cpp`
(the signed #89 + SelectLauncherActivity before-source; APK special-case grant block
at 1808 `hapPolicy.apl=NORMAL`, 1812 permStateList loop, 1822 InitHapToken,
1861 moduleInfo.requestPermissions loop).

Requires `oh_adapter::AdapterBackgroundLaunchPermissions()` from the sibling
`apk_network_permissions.h` (already `#include`d — line 1547 uses
`oh_adapter::MapApkNetworkPermissions` from it). No shared OH kit header changes.

All three edits are inside the **fresh-install** branch (`else` of `adapterIsUpdate`,
lines ~1797-1866). Existing apps must be clean-reinstalled (uninstall+install) for
the grant to apply — same rule #89 already documents for network permissions
(`bm install -r` reuses the old token). Verification uses `--reinstall`.

---

## Edit 1 — ACL + pre-authorization for the background-launch permission

After the network `permStateList` loop (ends at the line
`    hapPolicy.permStateList.emplace_back(state);` / closing `}`, ~line 1820),
BEFORE `Security::AccessToken::HapInfoCheckResult permissionCheck;` (~1821):

```cpp
                        for (const auto &name : requestedNetworkPermissions) {
                            Security::AccessToken::PermissionStateFull state;
                            state.permissionName = name;
                            state.isGeneral = true;
                            state.resDeviceID.emplace_back(appInfo.deviceId);
                            state.grantStatus.emplace_back(Security::AccessToken::PermissionState::PERMISSION_DENIED);
                            state.grantFlags.emplace_back(Security::AccessToken::PermissionFlag::PERMISSION_DEFAULT_FLAG);
                            hapPolicy.permStateList.emplace_back(state);
                        }
+                       // B-BACKGROUND-LAUNCH: grant system_basic START_ABILITIES_FROM_BACKGROUND to
+                       // every synthesized bundle so in-app startAbility (Wikipedia onboarding /
+                       // Splash->Main) is not blocked by WMSLife DisallowActivationFromPendingBackground.
+                       // apl stays NORMAL; availableLevel=system_basic is carried by ACL
+                       // (provisionEnable=true) + preAuthorizationInfo, exactly as OH's own
+                       // install_list_permissions.json pre-grants it (userCancellable:false).
+                       // grantMode=system_grant => InitHapToken grants it by policy, no user prompt.
+                       for (const auto &name : oh_adapter::AdapterBackgroundLaunchPermissions()) {
+                           Security::AccessToken::PermissionStateFull bgState;
+                           bgState.permissionName = name;
+                           bgState.isGeneral = true;
+                           bgState.resDeviceID.emplace_back(appInfo.deviceId);
+                           bgState.grantStatus.emplace_back(Security::AccessToken::PermissionState::PERMISSION_DENIED);
+                           bgState.grantFlags.emplace_back(Security::AccessToken::PermissionFlag::PERMISSION_DEFAULT_FLAG);
+                           hapPolicy.permStateList.emplace_back(bgState);
+                           hapPolicy.aclRequestedList.emplace_back(name);
+                           Security::AccessToken::PreAuthorizationInfo bgPreAuth;
+                           bgPreAuth.permissionName = name;
+                           bgPreAuth.userCancelable = false;
+                           hapPolicy.preAuthorizationInfo.emplace_back(bgPreAuth);
+                       }
                        Security::AccessToken::HapInfoCheckResult permissionCheck;
```

## Edit 2 — verification log after InitHapToken

Immediately after the existing `APKNET: InitHapToken ... ret=%d` LOG_I (~1824-1825),
BEFORE `if (permissionRet != 0) {`:

```cpp
                        LOG_I(BMS_TAG_INSTALLER, "APKNET: InitHapToken %{public}s requests=%{public}zu ret=%{public}d",
                            pkg.c_str(), requestedNetworkPermissions.size(), permissionRet);
+                       LOG_I(BMS_TAG_INSTALLER,
+                           "BGLAUNCH: InitHapToken %{public}s acl=%{public}zu ret=%{public}d",
+                           pkg.c_str(), oh_adapter::AdapterBackgroundLaunchPermissions().size(), permissionRet);
+                       // On ACL/pre-auth rejection InitHapToken returns non-zero and permissionCheck
+                       // names the offending permission; the existing permissionRet!=0 guard below
+                       // fails the install so a rejected grant never ships silently.
                        if (permissionRet != 0) {
```

## Edit 3 — declare the permission in the module (bm dump visibility)

After the network `requestPermissions` loop (~1861-1866):

```cpp
                    for (const auto &name : requestedNetworkPermissions) {
                        RequestPermission request;
                        request.name = name;
                        request.moduleName = "entry";
                        moduleInfo.requestPermissions.emplace_back(request);
                    }
+                   for (const auto &name : oh_adapter::AdapterBackgroundLaunchPermissions()) {
+                       RequestPermission bgRequest;
+                       bgRequest.name = name;
+                       bgRequest.moduleName = "entry";
+                       moduleInfo.requestPermissions.emplace_back(bgRequest);
+                   }
```

---

## Notes for cx-t0

- `PreAuthorizationInfo` / `HapPolicyParams.aclRequestedList` /
  `HapPolicyParams.preAuthorizationInfo` are declared in
  `base/security/access_token/interfaces/innerkits/accesstoken/include/hap_token_info.h`
  (already transitively included via the existing `HapPolicyParams` use). No new include.
- `userCancelable` (not `userCancellable`) is the C++ field name in
  `PreAuthorizationInfo`; the JSON allowlist key is `userCancellable`. Watch the spelling.
- If InitHapToken rejects the ACL for a NORMAL non-system app (i.e. availableType=SYSTEM
  turns out stricter than provisionEnable=true implies), the fallback is to raise
  `hapPolicy.apl = APL_SYSTEM_BASIC` for the token only — but that also relabels the
  data dirs via `createDirParam.apl = info.GetAppPrivilegeLevel()`, so prefer the ACL
  path and only fall back if the BGLAUNCH ret is non-zero on host test.
