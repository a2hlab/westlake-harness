# 5cd Boat overlay and permissive demo regression

The earlier checklist assumed a completed clean-5cd baseline and treated reboot simulation as a hard gate. The user's 18:55 instruction superseded the former: retain the A/B lock, stage the signed Boat layer, reboot, validate playability, then use runtime Permissive for the 128-app icon-click comparison against the signed 61b t3 reference. Outer subsequently clarified the latter: `t2e-reboot-sim-min.spec.md` explicitly forbids making the advisory simulation a seal prerequisite. No complete Boat-layer eight-input exporter exists in the four searched worktrees; record that as **advisory skipped**, not as PASS.

`artifact-receipt.json` binds the six original source files by full SHA. The signed candidate stores the `adc125f4` bytes under `libandroid.so`; copying those unchanged bytes into the required `liboh_android_runtime.so` filename is declared in the receipt. No binary patch or rebuild occurs. Large files are retained in `signed-artifacts/`, not committed.

`steps.py stage` uses the current master tools: recursive declared-scope snapshot, original APK SHA and existing B1 sandbox setup if needed, installer-free `boat_layer_stage.sh` dry-run/execute, and real sepolicy gate. The recipe argument is the canonical JSON consumed by the CLI; the checklist's shell-recipe argument was a type mismatch. All 32 sepolicy proofs passed in the preliminary run. `steps.py boot` uses only `target boot`, then reads back a new boot ID. It does not restart HDC/VM or power-cycle the hub.

The baseline `sources/seq1`, installer and runtime recovery cfg remain unchanged. Rollback uses the master `boat_layer_stage.sh --reverse --execute` plus a real reboot. Any failed hard gate stops at the exact boundary and retains the lock for recovery. Post-reboot health, five-touch screenshots, permissive readback and the actual 128 regression evidence must be added before claiming completion or registering a frozen version.

## Actual stop boundary

The complete pre-snapshot is stable and Enforcing. The actual `/system/etc/init/00_westlake_u13_recover.cfg` contains only `post-fs-data -> westlake-u13-recover`; it explicitly describes a U13-only variant and has **no Boat overlay job**. `commands.md` preconditions and step 2 explicitly require STOP here. `steps.py stage` stopped before APK installation, sandbox preparation, staging or reboot. Zero Boat mutations occurred. The six source bytes and preliminary static policy checks do not satisfy the missing on-board job. No installer/config workaround was attempted.

`results.json` pins the original cfg, complete snapshot, failure log and shared baseline hashes. The board remains pure U13, restored Enforcing, with the user-retained cx-t0 lock. Completion requires an outer disposition for this missing job; changing the advisory reboot simulator cannot clear this separate hard precondition.

## Superseding safe-prefix authorization

Outer explained WITH_BOAT=0 as the missing-job cause, and authorized the existing seal sequence with a 60-minute cap. The full128 capture cannot fit that cap; its explicit fallback was to stop after `assert_bare_base`, before installing/enabling. `safe_bare_prepare.py` executed exactly that prefix: complete fresh snapshot, existing DISABLED marker sequence, one `target boot`, then unmodified `Workflow.assert_no_binds` and `Workflow.assert_bare_base` from master `scripts/lab/demo_seal_61b.py` (SHA `516250c01b2070472a298855cba0738d8e17f2b9f087ea6904d65631bd617d99`). Its transport adds remote status sentinels and checks the Mac lock on every call.

The new boot is `426dfbbb-1da3-4a5b-824a-7dde7e426dd9`. Shell and init views have no recover binds; all 246 signed seq1 members and SHA values match, physical `/system/android` has zero files, and Enforcing is read back. The exact raw result is `BARE_BASE: seq1_files=246 sha_diff={} physical_files=0 decision=REUSE`. The board is now **bare with recovery DISABLED**, not the earlier mounted U13 state. No installer, ENABLE, app launch or Boat staging followed. The lock remains held for outer disposition. `safe-prefix-receipt.json` pins the raw log, reads and snapshot; this successful prefix does not claim Boat playability or full128 regression.

## Approved continuation refused by original installer gate

Outer separately authorized the remaining sequence because the bare board must not be parked indefinitely. Before any archive/placement, `installer_guard_probe.py` executed the **exact master installer step-1 prefix** with `WITH_BOAT=1`, default v2 and the current preserved archive as DEPLOY. Its source SHA is recorded in `installer-guard-probe/result.json`; no parent override or guard edit was supplied. Remote status was 1: `install-u13: FAIL APPSPAWN_NOT_RUNNING`. Both recovered-board checks precede this original parent gate. No ARCHIVE, placement, ENABLE, Boat install/stage or second reboot followed.

Current status is `results.json`: new boot `426dfbbb`, bare, DISABLED, Enforcing, cx-t0 lock retained. This is an actual read-only precondition refusal, not an inferred permission refusal. Further recovery requires outer disposition; the previous 319 restored mounted-U13 receipt belongs to the completed A/B boot, not this new bare boot.

## Additional read-only archive hazard before continuing

The bare host target SHA is EMPTY (`e3b0c442...`), so the unchanged installer SHA gate would refuse even with ALLOW_NO_PARENT. A readonly scan of all **53 file layers** also found all physical targets differ from their pinned SHA, while all 53 `sources/seqN` archive members match. The three directory layers are excluded from that count. The master installer protects directory REUSE, but its file branch copies the physical target **over the archive before checking SHA**; relaxing only the parent gate would not make that sequence safe. No copy/archive was run. The exact per-layer comparison and raw remote-exit-bound reads are in `bare-file-layer-readonly/`. Outer and cc-t3 were notified; no unpublished installer patch is used.

## Master 5808dfd699 continuation precondition result

The outer-approved installer SHA `e0e3f1ffb6805fcea08288ae416153cab2b6d7671a26e256543b3fed2e2dba52` was verified locally. Its exact step-1 prefix, stopping before the first mutation, was executed on bare 5cd with WITH_BOAT=1 and ALLOW_NO_PARENT=1. The original gate logged the opt-in, then returned remote status1: `install-u13: FAIL APPSPAWN_SHA_MISMATCH`. This independently confirms the previously recorded EMPTY physical host target. No SHA gate was relaxed, and no installer archive/placement/ENABLE or second reboot occurred. Current state remains bare boot426dfbbb, DISABLED, Enforcing, lock retained. Evidence: `installer-e0e3f1ff-guard/result.json` plus exact source prefix and raw status-bound stdout/stderr.

## 2026-10-10 19:48 v2 recovery after the rejected installer

The first receipt read was too early: boot-completed became true before recover replaced the previous boot's READY receipt. That read is preserved in `restore-v2-enabled/result.json`; it is not a recovery failure. Only a receipt bound to the current boot may pass, with READY and all 56 layers. `wait_ready` now polls for at most 120 seconds, refuses a current-boot FAILED receipt immediately, and never accepts a wrong layer count. Four known answers pass on Mac and a2hlab.

Using the unchanged enable script (SHA `6e4517b460664dbaf257e474da42c94588a414650735ca2deafde051c6643bfb`) and exactly one target boot restored boot `567ee543-00b3-4eb8-839f-6dce8b8552e7`. Readback: READY/56, Enforcing, 319 identities with empty diff, runtime `452447a4a0ba`, boot-image `ee927db88a67`, init-owned appspawn-x PID 4445. No archive, installer, Boat, config edit, or additional reboot occurred. The original BMS HelloWorld capture produced one t20 screenshot and alive_t20=yes; its `foreground_unconfirmed` rc1 is retained, not rewritten. The screenshot is supplied for outer review; no lit count is asserted. The cx-t0 lock remains held awaiting the landed place-only installer.

Small handoff: `landing-paths-v2-recovery.txt`. Large launch logs and records remain at the paths and hashes in `restore-v2-evidence-index.json`. `restore-v2-enabled-complete/run-facts-raw.txt` is the unmodified output of run_facts on the serial run directory.
