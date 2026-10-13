# R6 follow-up: fresh origin and independent reset-baseline evidence

Original R6 is partial, not accepted: geometry/HUD passed; acceleration reached sand, left/right stayed at the same location, LAP remained0/3, and reset returned to water. Its evidence and freeze40f0 are unchanged. Root completed the original window and restored947 on boot `a75c3bdd-a300-4f10-9747-4baee78330f3`; full319/seven binds/three sources and HW/ZZ passed, then the window unlocked.

`rebind.py` takes root's NEW read-only capture. It validates the actual four control bytes/metadata, runtime947 source and target, new source inode, probe receipt hash/rc/serial, and matching probe-start/control-metadata-end boot. It mechanically derives four parameters in the SHA-pinned40f0 successor: origin boot, actual inode evidence, control capture path, probe path. Hook, preparation algorithm, atomic preimage/CAS, source-only failure rollback and final live recovery gates are inherited without edits. No old35da boot or old inode is reused. No new runtime build occurs.

`prepare_behavior.py` amends only a fresh unapproved disabled output. It retains the original strict launch/APK/UID/PPID/birth/seven child pins/geometry gates and original TOUCHES loop byte-for-byte. After ready it adds one independent reset `1584,1074`, a `reset-baseline.jpeg`, and a root visual confirmation tied to that image SHA, current boot and exact child identity. Immediately after confirmation the original five operations run; there is no second3+6+6+15 cadence. Human confirmation has a45-second bound inside the original240-second interaction budget. No confirmation or a bad baseline fails closed and the normal hook restores947.

Source basis: existing `r4-knowledge-closure/sources/Boat.cs:203–214` resets to the nearest waypoint and clears velocity/angularVelocity plus orientation. `sources/Engine.cs:81–86` gates steering on `_yHeight > -0.1`. This supports normalizing the initial state, not claiming the unobserved LAP/turn result. LAP0→1/3 and visible left/right heading response remain required; reset is not a new hard acceptance gate for the original spec.

## Actual offline preparation

The local example `derived-a75c/` and `window-a75c-disabled/` were generated from main `outer/r6-followup-readonly`, not synthetic input. Five real BMS input resolves and the original62-target snapshot validator passed. Root should regenerate after landing:

```sh
export WORKSPACES="$(dirname "$PWD")" MAC_HOME="$HOME"
V2=benchmark/2026-10-09-demo-boatattack/v2-20261013
F="$V2/integration/runtime-successor-r6-followup"
python3 "$F/rebind.py" \
  --capture-root "$V2/outer/r6-followup-readonly" \
  --out "$V2/outer/r6-followup-main-derived" \
  --prepare-out "$V2/outer/r6-followup-main"
python3 "$F/prepare_behavior.py" --window "$V2/outer/r6-followup-main"
```

Root independently reviews/pins the new request, fills the generated authorization, sets execution_enabled in a separate board-run copy and uses the unchanged entry:

```sh
export R6_AUTH="<actual authorization>" R6_AUTH_SHA="<its SHA>"
python3 scripts/lab/board_run.py "$V2/outer/r6-followup-main/board-run.enabled.json" --detach
```

The root observer watches `run/boat/reset-baseline.jpeg` and `record.json` status `WAITING_FOR_BASELINE_REVIEW`. Only after personally confirming water/course orientation, write `run/boat/reset-baseline.approval.json` atomically with these fields (do not pre-create it):

```json
{"approved_by":"outer(codex)","verdict":"WATER_FACING_COURSE","boot_id":"ACTUAL_CANDIDATE_BOOT","child":{"pid":0,"birth":0,"ppid":0,"parent_birth":0,"uid":20011062},"image_sha256":"ACTUAL_RESET_BASELINE_JPEG_SHA"}
```

The child object must be copied exactly from that live record. Placeholder zeros above are not executable approval. The five input commands follow immediately after validation. Output belongs to a new supplemental group; original R6 never becomes original-cadence PASS by substitution.

The window still always rolls back: three source preimages→snapshot/policy→cold boot947→319/seven bind bytes+metadata+owner inodes/three sources/HWZZ→unlock. Boot-before-bind or partial-bind failures restore only this transaction's sources first; they cannot satisfy the final947 gates. No-intent cleanup remains read-only and does not boot. No61b or5cd operation is introduced.

## Subsequent full128 (not enabled)

T0's independent `r6-full128-5ea` freeze4b207c supplies the new337 identity and full128 adaptation; this package does not recreate that work. Only after root accepts the new behavior and popup evidence can the same f28 be placed again using a NEW post-rollback capture. That placement requires separate authority to retain the temporary candidate baseline, then T0's ten-control and full eight-window driver with fresh admission. Do not reuse this automatically-rolling-back experiment window as a persistent full128 baseline, or reuse a75c after its next reboot. Original45-minute/35-minute cutoff and all128 membership/records/collect/special-slot guards remain in T0's driver.

`capture_readonly.py` is an optional replay of root's original read commands for the NEXT cycle, default preview. It does not run as part of prepare or tests. All work here is local; no HDC/VM/SSH call was made by t4.
