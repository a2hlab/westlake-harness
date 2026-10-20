# T30 root-channel command card

Actual production intake:38 output SHA/size verified,7 commands rc0; shim7f8d75bb/107544B; bridgeb0e5602a unchanged. New shim exports lock72c8/unlock72dc/geometryf8bc. The five-slot reader pins its own new repository path/SHA. Executor remains693448c2. This is a candidate window, not playback/seal approval.

Run helpers with **cwd=MAIN** after this exact listing lands. No device call was executed by the lane. Pending data at the deployment root remain unchanged; actual data are in `final-01`. All commands below using T30_EXECUTE are for the root's existing transport channel only.

```sh
cd "$WORKSPACES/westlake-harness"
export T30_BASE="$HOME/.local/share/westlake/toutiao-resume-20261020"
export T30_DEPLOY="$PWD/benchmark/2026-10-20-t30-request-recovery/deployment/final-01"
H="$PWD/benchmark/2026-10-20-t30-request-recovery/deployment/helpers"
W="$T30_BASE/t30-5cd-window-01"
PROD="$HOME/.local/share/westlake/t30-production/production-01"
python3 "$H/prepare_inputs.py" --t29-inputs "$T30_BASE/t29-candidate-inputs" --production "$PROD" --out "$T30_BASE/t30-candidate-inputs"
export T30_EXECUTE=1
python3 "$H/t30_outer.py" acquire
```

`acquire` persists actual holder/start and final-data pins. All subsequent helpers require that exact context. Do not acquire twice. The current reported boot/PIDs are deliberately absent from executable defaults. Let `B/P/PB/HOST/HB` denote values root has just read: boot, parentPID/birth, hostPID/birth. Initial WID29 remains required by inherited fresh-fill logic; another WID needs separately reviewed run data, not a substituted stale identity.

```sh
python3 "$H/t30_outer.py" shell candidate "$B" 'ps -A -o PID,PPID,UID,NAME; hidumper -s WindowManagerService -a "-a"; power-shell dump -s; param get debug.ttplayer.log.enable || true'
python3 "$H/fresh_read.py" apply "$P" "$HOST" fresh-read
python3 "$H/fill_admission.py" fill --repo "$PWD" --context "$W/context.json" \
  --held-stdout "$W/fresh-read/held.stdout" --held-stderr "$W/fresh-read/held.stderr" --held-rc "$W/fresh-read/held.rc" \
  --read-stdout "$W/fresh-read/read.stdout" --read-stderr "$W/fresh-read/read.stderr" --read-rc "$W/fresh-read/read.rc" --out "$W/fresh-admission"
python3 "$H/t30_baseline_collect.py"
python3 "$H/t30_exec.py" preflight "$B" "$P" "$PB" fresh-admission/admission.json preflight
python3 "$H/t30_exec.py" apply "$B" "$P" "$PB" fresh-admission/admission.json apply
python3 "$H/t30_outer.py" reboot candidate "$B"
python3 "$H/t30_wait_boot.py" candidate "$B" candidate
```

Fill validates the raw boot/UID/exe/parent-private/WMS/physical-private metadata bookends; `fresh-admission/identity.json` is authoritative for B/P/PB/HOST/HB. Never continue on nonzero preflight/apply or incomplete before snapshot/supplement. Preserve partial apply and use its original plan for recovery. The power/parameter diagnostic line above is evidence collection; root must inspect its actual values, not infer success from the shell marker.

Read new boot from `candidate-boot.json`, then read its new parent/host identity through the existing guarded shell. Exactly one normal launch per authorized attempt:

```sh
python3 "$H/t30_launch.py" candidate "$BNEW" candidate-icon
python3 "$H/t30_outer.py" capture candidate "$BNEW"
# Inspect actual screen before choosing any click. No coordinates are prefilled.
python3 "$H/t30_frames.py" observation-01 "$BNEW"
python3 "$H/read_slots.py" --execute --repo "$PWD" --out "$W/five-slots" --hdc "$HDC" \
  --boot "$BNEW" --holder "$HOLDER" --parent "$PNEW" --parent-birth "$PBNEW" --child "$CHILD" --child-birth "$CBIRTH" \
  --player-elf "$T30_BASE/t30-candidate-inputs/libttmplayer.so" --bridge-elf "$PROD/bridge.so" --shim-elf "$PROD/shim.so" \
  --surface-elf "$T30_BASE/provider-surface-readonly/libsurface.z.so"
python3 "$H/collect_prefix.py" --execute --context "$W/context.json" --boot "$BNEW" \
  --parent "$PNEW" --parent-birth "$PBNEW" --host "$HNEW" --host-birth "$HBNEW" \
  --child "$CHILD" --child-birth "$CBIRTH" --out "$W/candidate-log"
```

HDC/HOLDER come from the actual context; CHILD/CBIRTH and all postboot identities must be freshly read, not inherited. `frames` takes0/5/10/20-second captures without clicks. Slot reader retains the original behavior: inspect `status` and all five matches, not rc alone. Prefix collector is bounded to250MB and1200-second experiment cutoff; partial evidence is never described as global absence. Screenshots require visual review; user audio is independent.

**At1200s, or earlier on failure, stop experiments. Recovery has until1800s.** Keep the same holder/start and original `apply/plan.json`. Read current parent/host first; rollback fill accepts exact known before/after bridge/shim states only and verifies the original plan metadata.

```sh
python3 "$H/fresh_read.py" rollback "$PCUR" "$HCUR" rollback-read
python3 "$H/rollback_admission.py" fill --repo "$PWD" --context "$W/context.json" \
  --apply-plan "$W/apply/plan.json" --apply-admission "$W/fresh-admission/admission.json" \
  --held-stdout "$W/rollback-read/held.stdout" --held-stderr "$W/rollback-read/held.stderr" --held-rc "$W/rollback-read/held.rc" \
  --read-stdout "$W/rollback-read/read.stdout" --read-stderr "$W/rollback-read/read.stderr" --read-rc "$W/rollback-read/read.rc" --out "$W/rollback-admission"
python3 "$H/t30_exec.py" rollback "$BCUR" "$PCUR" "$PBCUR" rollback-admission/admission.json rollback
python3 "$H/t30_outer.py" reboot restored "$BCUR"
python3 "$H/t30_wait_boot.py" restored "$BCUR" restored
python3 "$H/t30_restore_collect.py"
python3 "$H/t30_launch.py" restored "$BRESTORED" restored-icon
python3 "$H/t30_outer.py" capture restored "$BRESTORED"
python3 "$H/t30_outer.py" shell restored "$BRESTORED" 'power-shell timeout -o 10000; power-shell dump -s; param get debug.ttplayer.log.enable || true'
```

Use `rollback-admission/identity.json` for BCUR/PCUR/PBCUR. The helper always passes this window's original apply-plan; no T29 plan is reused. If a parent is absent, this normal helper must refuse: use only the original executor's separately reviewed physical-recovery route, not fabricated PIDs. If apply timed out without a plan, inspect persisted evidence before any retry; do not rerun mutation blindly.

Root finishes physical/private original hashes and compat absence,518-target eight-field equality plus26supplement (boot excluded only where specified), original power10000/10000 and parameter106, actual final UI, then explicit unlock/held-after receipts using MAIN board_note. Fresh boot changes PID/mount text; do not demand raw proc/mount equality. Final UI may be host-only and must remain so in the result. Unlock is deliberately not automated by these helpers.
