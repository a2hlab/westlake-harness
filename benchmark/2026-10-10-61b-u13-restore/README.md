# 61b U13 restoration: files restored, daemon unavailable

A 319-file identity match does **not** mean a usable runtime. On 2026-10-10 the already-replayed 61b U13 layers matched every signed file, but the existing `Deployment.start` could not create the appspawn-x parent. The recovery is **blocked**, not a screenshot PASS.

## Evidence

`blocked-status.json`: 319 paths, `diff={}`, `absent=[]`; runtime `452447a4a0ba`, boot `ee927db88a67`; boot `ee198be6-a9f1-4ce0-ac2c-6a7cca1fc105`; no appspawn-x process. `before-identity.json` records the identical pre-write answer.

The original source journal is the U14 window2 double-transaction journal, SHA `f24718730ccd4165d876a411daf0d717630311de0ac2a1c5b1c20923c8ebde67`. Only `plan.native_tickets[1]` was refreshed using the production native gate; signed baseline bytes were unchanged. No native/JAR/image payload was replaced.

Read-only mountinfo had **112** `/westlake-demo/u13/sources/` entries, covering the 56 required targets twice. The autonomous recovery had already replayed them. The host-side recovery therefore added **zero binds**. First `Deployment.start` failed; the existing replay service transition `Deployment.stop` → `Deployment.start` also failed with `RuntimeError: parent failed to start`. No daemon was signaled directly.

The outer located the real definition at `/system/etc/init/appspawn_x.cfg` (underscore). It defines `appspawn-x`, `ondemand=true`, `secon=u:r:appspawn:s0` and preloads `/system/android/lib64/liblzma.so`. The earlier grep-empty result was not a valid service-inventory answer and is superseded by `service-config-correct-name.txt`.

The outer then authorized a ≤15-minute label experiment. `label-sources.json` binds the **56 unique top sources**; `labels-before.txt` / `labels-after.txt` record labels. We applied exactly the production deployer's recursive `u:object_r:system_file:s0` label and `0755` on the host source, without adding binds. All56 top labels read back as system_file; a subsequent319 snapshot remained byte-identical. **Deployment.start still failed**, recorded in `label-experiment.json` and the original traceback in `label-experiment.log`. Label repair alone is therefore insufficient in this observed service state; the remaining init/ondemand cause is not established.

Before the subsequent explicit reboot authorization, autostart `DISABLED` stayed present. No init configuration edit, reboot, new bind, package replacement or other-board action occurred. The authorized label/mode experiment is the only subsequent change. HelloWorld/ZigZag captures were not attempted after the parent gate refused; screenshot and child-ART verification are **not available**, not PASS. The cx-t0 lock was retained as required by the refusal boundary. Raw output is persisted in this directory in the lane worktree: `start-r2.log`, `stop-start.log`, `failure-hilog.txt`, `before-mountinfo.txt`, `failure-*.txt`, plus `device-*` command logs. These large transport logs remain outside Git.

## Next authorized boundary

An outer-approved init-service recovery path is needed before screenshots or UNLOCK. Re-running a bind replay cannot fix an absent daemon and would stack additional overlays. This report does not enable or repair autostart.

## Superseding outer decision: one reboot, then USB disconnect

The outer subsequently established `SERVICE_ATTR_INVALID` (init_common_service.c:675–687) as the permanent current-boot refusal and authorized one reboot; this is outer source/dmesg evidence, not a cause inferred from the earlier grep. `pre-reboot-disabled.txt` confirmed DISABLED. The single reboot call lost its remote status marker, and the next HDC target-list read contained only5ea/5cd. No further reboot, shared HDC/VM reset or hub action was attempted. **Current boot and post-reboot identity are unknown pending user reconnection** (`waiting-usb.json`). The lock remains held.

After physical reconnection, the already-authorized sequence starts with read-only physical host/child file stat, AppSpawnX socket and invalid-related dmesg **before any Android launch**, then a fresh baseline-native ticket and the existing new-boot baseline replay. No post-reboot replay or app launch has occurred yet.
