# 5ea installer handoff: background launch + own-package launcher

Candidate pair (replace together before foundation restart):
- `libbms.z.so`: `6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9`
- `libapk_installer.so`: `7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18`

Preserves #89 INTERNET/GET_NETWORK_INFO. Adds one unconditional OH background
launch request through module.json, BMS metadata, and fresh-token ACL/preauth;
APL remains NORMAL and isSystemApp remains false. Old tokens missing the
new permission require uninstall/install. Anki mainAbility chooses
com.ichi2.anki.IntentHandler rather than LeakCanary. APK bytes unchanged.

Run **on Mac**, only with cc-wiki's 5ea lock, using the direct DevEco HDC.
Before apply write “将重启 5ea” on the board and archive current runtime replay
package / JAR SHA: foundation restart can reboot the device and clear mounts.

```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py dry-run
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py apply
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py restart
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py verify
```

`apply` requires both aliases of baseline 6f94d4f4 / eb6824b4, saves four exact
files and hashes, then replaces the pair. Partial apply failure restores them.
`verify` checks root + foundation-root SHA and a non-stale libbms mapping;
inspect its desktop screenshot. If rebooted, replay the approved resident
runtime/JAR before app tests; do not assume mounts survived.

Clean-reinstall Wikipedia (batch --reinstall), then binaryeye/Gallery/VLC and
Anki as installed/available. Check bm dump includes the new request,
BGLAUNCH InitHapToken ret=0, actual background activation no longer denied,
and screenshots show intended activity. Declaration/ret=0 alone are not
proof of a grant. HW/ZigZag regressions and facts.txt verbatim are required.

Rollback:
```sh
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py rollback
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py restart
python3 /Users/zhaoyue/orca/workspaces/westlake-installer-background-launcher-6aadb8b4/swap_services.py verify
```
Rollback restores the original libraries, not installed-package/token state.
The backup state is under westlake-generation-state/5ea34a4500000000000000001123012c/installer-background-launcher/.

Host validation: installer 31/31; both strict links pass; ELF NEEDED/order,
SONAME, flags, import sets unchanged and no removed exports; Wikipedia/Noice
real HAP tests pass with exactly three permissions; old-code negative control
fails expected actual==expected; four deployment/rollback tests pass.
Board results and grant acceptance remain unverified until cc-wiki's run.
