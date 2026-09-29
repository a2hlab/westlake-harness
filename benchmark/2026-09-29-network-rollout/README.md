# Task 90: network host and installer rollout on 61b and 5cd

Foundation hot restart after the installer replacement left 61b's old SceneBoard session black. Shell and foundation library SHA checks passed, but the desktop launch precondition failed (`focus window missing; desktop state unknown`). That failed attempt is retained; it is not counted as a successful smoke. The established recovery—reboot, replay the same runtime files, then recheck the installer and controls—restored the screen. For 5cd we installed the two libraries and rebooted directly, avoiding a second known black-screen cycle.

Only the cx-t0 deployment subtask of the outer-owned #90 is reported here. The r16/full-66 sweep and prediction work belong to other lanes. No 5ea command was issued.

## Selected artifacts and preserved variants

Both boards receive these exact already-built files:

| Artifact | SHA256 |
|---|---|
| appspawn-x | d977bd15da1ad193990a7aeb841c93940c28462e66dce1ec5b6bd7b31d3a02e8 |
| libbms.z.so, both aliases | 6f94d4f4448aa881b9868c094347849c86d460fdd22977934ffd7dbfc66dc287 |
| libapk_installer.so, both aliases | eb6824b4db46c63267f447c8d12e7ce70dbab7677667a5b3bdab073387dd9524 |

61b retains the signed VelocityTracker runtime `c835a93e` and bionic-supply liblog `8c81a937`, JAR r8b `d5000c4e`. Its host-only replacement package is `/Users/zhaoyue/orca/workspaces/westlake-generation-b90-61b-inet-d977bd15`, derived from the resident `westlake-generation-b87-vt-c835a93e` by the existing replacement-package tool. No native rebuild occurred.

5cd retains the stock v3a native set. Its owner had advanced from r15c `be7731a4` to r16 `6a5d7fca` before releasing the board; we preserved **r16**, not the earlier read. The package replay is the already supplied `/Users/zhaoyue/orca/workspaces/westlake-generation-b80-inet-d977bd15`, followed by the exact r16 overlay from `vm-copies/r16-runtime-jar/oh-adapter-runtime.jar`. `restore_r16.py` copies the B11 deploy_jar bind pattern, with live cx-t0 lock checks, pinned local/remote/baseline SHA, parent-root verification and immediate unmount rollback on mismatch.

## Execution and evidence

All board operations use Mac's `/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc`. `deploy_host_mac.py` calls the existing `Deployment` implementation with only the transport/lock command changed. Package, prerequisite, mount, runtime SHA, child SHA, bridge identity and single-ART checks remain active. Replaying after reboot remounts existing artifacts; it is not a new generation build. Installer changes are made by the copied #89 transaction with board-specific serial/lane/baseline identities. Original four files are retained in each board's `/data/local/tmp/b90-network-permissions-6f94d4f4/backup` and state receipts under `westlake-generation-state/<serial>/b90-network-permissions/`.

The master `bms_batch.py` runs installed HelloWorld/ZigZag using 16 MiB/private-off/clock/screen preflight, `--launch-only --shots 5,20 --hilog 20 --focus-check`. Their immutable source APK identities are in `controls.json`. Source APKs were not reinstalled or changed by this smoke. Foreground acceptance may remain `foreground_unconfirmed`; screenshots, captured flags and the saved process snapshots are retained. Facts are copied verbatim to each `smoke/facts.txt`; counts are never inferred from the plan.

`generation-gate.json` and `generation-child-sha.json` come from the existing deployer. Final inventories include shell, foundation (service-library paths only), appspawn parent and available child views. Foundation may retain a mount namespace without `/system/android`; do not demand runtime files through its root or confuse their absence with an installer hash mismatch. Native runtime/JAR identities are checked in the appspawn parent/child namespace. `WLNET` lines prove the host requested gid 3003; old installed control tokens still show `internet_set=1 allow=0`, so these controls are **not** a fresh-install network-permission test. The next sweep must use `--reinstall` to create ATM permissions via the new installer.

## Rollback and continuation

Installer packages:

- `/Users/zhaoyue/orca/workspaces/westlake-b90-network-61b`
- `/Users/zhaoyue/orca/workspaces/westlake-b90-network-5cd`

With the corresponding board lock, run its `swap_services.py rollback`, announce and restart/reboot, then replay its prior runtime/JAR according to the saved receipt. The exact installer rollback identities are in each `manifest.json`: 61b `2220df48/675536e8`, 5cd `f8ef078d/1ebf78ab`. Do not delete backup or transaction state to force a retry. File rollback does not undo package/token database changes from future reinstalls.

For host-only rollback in the current boot, use the same verified replacement mechanism with the intact previous package: 61b `westlake-generation-b87-vt-c835a93e`; 5cd `westlake-generation-v3a-74d1d6d4-r8b`. On 5cd, first remove **only this task's recorded r16 overlay** if its top mount still matches `5cd/r16-replay/receipt.json`, restoring r8b for the package check, then restore the current owner's JAR after host rollback. If the owner has since added another overlay, coordinate its receipt rather than blindly unmounting. A reboot clears bind mounts, not installed system-library files.

Build/source provenance for the unchanged binaries remains in the #80 network-groups and #89 network-permissions reports and their persistent `/home/alvin/` archives. This task adds deployment recipes and evidence only. B8 lifecycle selectors still match zero tests; their six Skip verdicts are not a passing contract result. Known-answer tests and final facts are recorded separately in `results.json`.

Raw per-command traces and complete process maps are retained outside git at `/Users/zhaoyue/orca/workspaces/westlake-b90-evidence/`; this report commits relevant map excerpts, SHA/gate receipts, process snapshots, records and screenshots.
Committed text views trim trailing whitespace; original byte views remain in the raw-evidence directory. `facts.txt` is copied verbatim.
