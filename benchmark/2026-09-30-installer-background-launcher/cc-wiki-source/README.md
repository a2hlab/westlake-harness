# B11: grant START_ABILITIES_FROM_BACKGROUND to synthesized Android bundles

Installer source patch so every BMS-synthesized Android bundle declares and is
granted `ohos.permission.START_ABILITIES_FROM_BACKGROUND`. Same shape as #89's
INTERNET grant. Compile + host-test + `.so` build are cx-t0's (isolated dir
`bms/src/.work/installer-background-launcher`, batched with SelectLauncherActivity);
device verification on 5ea is cc-wiki's.

## Why (what was wrong)

B11 needs Wikipedia's welcome page. Static hilog proof (5ea r17c, run
`20260930T014739-ca7c9702`, both r17c versions identical):

1. Launcher enters `org.wikipedia.DefaultIcon -> org.wikipedia.main.MainActivity`
   (feed shell, the t5 screen).
2. `MainActivity.onCreate` requests the welcome page:
   `OH_ATMJNI nativeStartAbility ability=org.wikipedia.onboarding.InitialOnboardingActivity`.
3. Same millisecond it is denied:
   `AAFwk permission_verification: ohos.permission.START_ABILITIES_FROM_BACKGROUND: PERMISSION_DENIED`
   + `WMSLife scene_session.cpp DisallowActivationFromPendingBackground: session state:0 ...
   no permission to start ability from Background`.
4. Result: the onboarding activity never launches; the feed remains.

cx-t0 confirmed the wall is horizontal: Gallery / VLC hit the same denial after
their Subscribe/Publish CE. So granting this permission to all synthesized bundles
is a horizontal fix (Wikipedia welcome page, binaryeye/Splash->Main, Gallery, VLC).

## Mechanism (why ACL + pre-auth, not apl bump)

Authoritative permission definition, `/system/etc/access_token/permission_definitions.json`
on 5ea (generation 74d1d6d48210):

```
grantMode=system_grant  availableLevel=system_basic  availableType=SYSTEM  provisionEnable=true
```

The synthesized bundle is `APL_NORMAL` (#89, unchanged). `system_basic` exceeds
`NORMAL`, so the permission cannot be held by plain declaration. Chosen path,
justified from source:

- `provisionEnable=true` lets a NORMAL-apl app hold it via **ACL**
  (`HapPolicyParams.aclRequestedList`, from `hap_token_info.h`).
- `HapPolicyParams.preAuthorizationInfo` (`PreAuthorizationInfo{permissionName,
  userCancelable=false}`) install-time pre-grants it — exactly how OH itself lists
  it in `/system/etc/app/install_list_permissions.json` (`userCancellable:false`).
- `grantMode=system_grant` => `InitHapToken` grants it by policy, no user prompt.

This keeps `apl=NORMAL` (avoids relabeling the app data dirs, which follow
`createDirParam.apl = info.GetAppPrivilegeLevel()`) and does not set
`isSystemApp` (avoids over-privileging a third-party app). Fallback if the ACL is
rejected on host test (availableType=SYSTEM stricter than provisionEnable implies):
raise `hapPolicy.apl = APL_SYSTEM_BASIC` for the token — documented in the delta,
not applied by default.

## Files (deltas only; no shared OH kit header changed)

| File | Change |
|---|---|
| `apk_network_permissions.h` | add `oh_adapter::AdapterBackgroundLaunchPermissions()` returning the one OH permission (sibling of `MapApkNetworkPermissions`; already `#include`d in base_bundle_installer.cpp) |
| `base_bundle_installer.delta.md` | the 3 injection points against `base_bundle_installer.before.cpp` |
| `base_bundle_installer.cpp` | the fully patched file (before + the 3 edits; `/usr/bin/diff` = +23 lines, additions only) |

Patch base: `bms/src/.work/installer-background-launcher/base_bundle_installer.before.cpp`
(signed #89 + SelectLauncherActivity). Edits live only in the APK special-case
fresh-install branch: ACL+preAuth+permState after the network permStateList loop,
a `BGLAUNCH` log after the InitHapToken log, and the permission in
`moduleInfo.requestPermissions`.

## cc-wiki self-check (host-equivalent, no OH toolchain here)

- Anchors A/B/C each unique in before.cpp; patch applies with additions only
  (`/usr/bin/diff` verified, 9546 -> 9569 lines).
- Types resolved from the kit headers actually on disk
  (`oh61-bms-kit-background-launcher/.../hap_token_info.h`): `PermissionStateFull`,
  `PreAuthorizationInfo{permissionName,userCancelable}`,
  `HapPolicyParams{aclRequestedList, preAuthorizationInfo}`, `RequestPermission`.
- Grant is unconditional (all bundles), independent of the Android manifest.

## Device verification plan (cc-wiki, 5ea, after cx-t0's .so)

Clean reinstall required (fresh-install branch allocates the token; `bm install -r`
reuses the old token — same rule #89 documents). Uninstall+install, then:

1. `bm dump -n org.wikipedia` requestPermissions includes
   `ohos.permission.START_ABILITIES_FROM_BACKGROUND`.
2. install hilog: `BGLAUNCH: InitHapToken org.wikipedia acl=1 ret=0`.
3. launch Wikipedia: no `DisallowActivationFromPendingBackground` /
   `START_ABILITIES_FROM_BACKGROUND: PERMISSION_DENIED`; `InitialOnboardingActivity`
   reaches the foreground. Screenshot = welcome page ("All the world's knowledge").
4. control: binaryeye Splash->Main reaches Main; Gallery/VLC no longer denied.
5. facts.txt verbatim + screenshots for outer review; screen is ground truth.
