# T38 independent migration and rollback review — initial slice

Status: **execution admission pending; do not treat the package audit as approval**. This appendix does not alter any of the 427 accepted T37 files or their pins. T36 landed as `db5ebfa0c1`, T37 as `53e5c670aa`. The later native peer regression receipts are for outer review; no regression replay is performed here.

## Objects and reproduced paths

Observed at `2026-10-21T09:24:55Z`; work in the author tree was still in progress. The disabled package root is `/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r4c`. Watchdog SHA is `c73dadb3c0d6ba082c030d7c1096810129b5afec7e3aced4d896dce86e59f0e5`. The exact captured package and source hashes are in `initial-01/pins.json` and `initial-01/observation.json`.

- Full payload consistency: **165/165** checks pass, including entry's literal watchdog/ownership pins. The package remains disabled and unapproved.
- Four new path probes reproduce actual production entry/main behavior; these are integration observations, not another run of the old 18-case suite. The unchanged entry is run only against local synthetic config/decoder/foreground seams. Main's process/start/spawn/monitor dependencies are doubles. No actual process is signalled, no device call occurs.
- A new guardian's own bootstrap records the epoch before first spawn. A supplied old parent skips that call. A missing binding records `phase=unbound` **and still permits the first spawn**. Subsequent host reentry then refuses `epoch_not_bound`. The probes preserve these observations, rather than calling first-spawn success a repaired reentry.
- The unchanged entry refuses an existing socket with `EXISTING_SOCKET_NO_TAKEOVER` before exec of the guardian. It also clears inherited parent/child identifiers. Supplying an old r3 parent to `main` does not solve migration: no epoch is recorded and switching refuses `epoch_record_missing`.

Receipts: `initial-01/path-replay.json`, per-case `.json`/`.sh`, and `review_t38.py`.

## Required connections before the window

| ID | Finding / required connection | Evidence and disposition |
|---|---|---|
| M1 | The live old r3 parent cannot be adopted into signal authority. Placement must lead to a newly proved boot, a new guardian-owned parent and a bound epoch. Never synthesize an epoch for the old parent or unlink its fixed socket. | Fresh boot `be4badc3-5a79-4fa8-8758-e6aacc0ca05f` shows r3 guardian `4016:3869`, parent `5089:5573`, state `AWAITING_REENTRY`; these are observations, not future authority. `entry_existing_r3_socket` and `main_adopt_r3_no_epoch` receipts. Placement code returns `PLACED_REQUIRES_NEW_BOOT`; no completed T38 boot/orchestration/recovery binding was present in this captured slice. |
| M2 | Before claiming reentry readiness, read back `parent-epoch` as bound to the newly started exact parent, namespace, listening socket, socket file and run inode. An unbound first launch must be a failed window with recovery, not successful readiness. | `main_bootstrap_unknown_still_spawns.json`: main rc0, one start/one spawn, unbound epoch, switch refused. This is an operational acceptance gap unless the window driver checks it. |
| E1 | Use the actual init service path, not the generator's similarly named recovery.cfg. | Fresh cfg SHA `7b9f2c0e6431a486f3138f8fca04e3c5aea2c21f4f8acb6f83e815735d998e4b` starts `westlake-u13-toutiao-overlay` on `sys.westlake.demo.u13.ready=true`. Generated recovery.cfg instead names `westlake-icon-manual-20261019`. Captured `after-sed.cfg` correctly changes only the root in the real service; reverse substitution reproduces the fresh original hash. Actual deploy plan/CHAIN still need binding to these bytes. |
| R1 | cfg restored is not runtime restored. After a new r4c parent has run, restoring the old cfg alone leaves that process/socket and loaded code alive. Recovery must bind the original cfg, a subsequent fresh boot, the r3 loaded guardian/root and actual video/runtime observations. Same-boot boot-entry reuse can also refuse its existing attempt directory. | Captured `deploy.execute(...rollback...)` restores only CFG; `CFG_RESTORED` is a placement result. It does not stop a guardian, reboot or inspect loaded processes. This is acceptable only with a separately reviewed caller completing recovery. |
| R2 | Preserve the video-installed state, not the pre-video T34 donor. T38 should not blindly invoke the W05 video rollback executor. Also account for `real-start-parent-bounded.sh` changing runtime/run.sh via sed, despite placement's `runtime_changed=false`. | W05 executor rollback restores older player/ffmpeg/bridge/shim and removes the compatibility DSO. T38 placement itself writes controls and CFG only; first launch subsequently rewrites WL_PARENT_ID and the run inode. The fresh slice captures control hashes but lacks the T38 runtime/video SHA+metadata+settings before-image needed to verify preservation/recovery. |

## Concrete placement validator findings

Captured deployment source: `deploy.py` SHA `6a7f73959bc4d2d191427cb1f610b7fece999148e3938679968506a7cd4feaf9`; `prepare.py` SHA `6063daf7b2d4ed23f6060b222247d68c75db6741523dc2729a67caf9dd46e977`.

1. **Disabled-plan preparation fails before writing plan.json** with `startup authority`. `prepare()` calls the same validator that requires enabled/outer approval. T38's first phase requires a concrete reviewable disabled plan. Separate preparation/pin validation from execution authority checking, or provide another exact disabled-plan artifact; do not manufacture outer approval to get a plan.
2. **Missing bounded-start leaf check in execution validator.** With a synthetic local package only, change `STARTUP_START_PARENT_SHA` to 64 zeroes and consistently update startup.expected and plan file hashes: `validate()` accepts it. The real start-parent wrapper later refuses `START_PARENT_SHA_CHANGED`. The present actual package passes the independent 165 checks, so this is a validator coverage gap, not a claim that its current leaf is bad. Add this leaf check to the actual admission path or bind an independently checked complete leaf report.

`initial-01/placement-validator.json` records both. All mutations were temporary review fixtures; author files and devices were untouched.

## Recovery matrix for the final plan

| Failure phase | Required evidence/action in the reviewed caller |
|---|---|
| Before cfg replacement | Verify old cfg still exact; preserve partial new-root evidence. Avoid restarting old same-boot guardian or changing runtime. |
| After replacement, before new boot | Restore exact captured cfg (including mode/uid/gid/label), verify root mount ro; record whether no new parent was started. |
| After new boot/start or unbound epoch | Preserve first refusal/event/proc/epoch evidence. Restore exact old cfg, complete a new boot, prove the actual r3-loaded entry/guardian and video-preserving runtime. Unknown parent/socket never authorizes cleanup by generic kill/unlink. |
| Runtime run.sh WID changed by launch | Explicitly bind the allowed WID normalization and other-byte preservation, or restore an admitted exact before-image with process ordering and a fresh boot. Never overwrite an inode still bound by an old live parent. |
| Timeout or partial placement / remount failure | Use original transaction/session binding and exact before/after cfg CAS, preserve raw command rc/stdout/stderr, reseal ro and independently verify the recovery outcome and settings. |

No live parent environment read was retried. Device/manual-video acceptance remains pending; dynamic content frames and the existing audio acceptance retain their T37 definitions. Review findings are only in this appendix for outer relay; no direct CC/bus communication was attempted.
