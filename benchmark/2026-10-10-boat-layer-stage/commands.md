# 5cd full-128 WITH the Boat layer — execution checklist (cc-t3 #91)

**Do not run any step until the on-board preconditions below hold.** This is the plan for the LATER on-board phase; the outer re-dispatches it after cx-t0 posts the 5cd full-128 facts and UNLOCKs 5cd. Every step lists its PASS criterion and a failure fallback. The whole run is reversible: `boat_layer_stage.sh --reverse --execute` + reboot returns 5cd to pure base; `seq1` is never touched.

## Preconditions (gate — do not start otherwise)
- cx-t0 has posted the **5cd clean-U13 full-128 signoff baseline** facts on the blackboard (this is the `--signoff` input for step 9) and **UNLOCKed 5cd**.
- 5cd is already **v2** (recover cfg carries the `westlake-u13-boat-overlay` job) and **128-complete, same fingerprint as 61b** (per outer).
- The **signed Boat artifacts dir** `<SRC>` is confirmed to hold the 6 files whose SHAs match `frozen-entry-draft.json` (`boat_layer_stage.sh` re-verifies, but confirm the dir first).
- `WORKSPACES=/Users/<...>/orca/workspaces` exported; `HDC` = the DevEco hdc; `SN=5cd1e3dd00000000000000000923012c`.
- Announce + **LOCK 5cd** (`board_note.sh lock`), window ≤45min.

## Steps

### 1. Pre snapshot (read-only baseline of the board before any change)
`python3 scripts/lab/board_state_snapshot.py $SN --hdc "$HDC" --out <OUT>/pre-snapshot --label cc-t3-5cd-boat-pre`
- **PASS**: `snapshot.json` written, `boot_stable=true`, Enforcing, boat NOT yet applied (runtime=18763dd4 base).
- **FAIL → STOP**: board unreachable / not v2 / already boat-applied unexpectedly → report, do not stage.

### 2. Stage the Boat layer (installer-free; dry-run first, then execute)
`bash scripts/lab/boat_layer_stage.sh --serial $SN --src <SRC>` *(dry-run: review the plan)*
`bash scripts/lab/boat_layer_stage.sh --serial $SN --src <SRC> --execute`
- **PASS**: 6 files staged into `/data/westlake-demo/u13/sources-boat`, each `STAGED_SHA` verified, single-recipe labels applied; script prints "seq1 untouched, installer not called, /system not remounted".
- **FAIL → STOP**: any `BOAT_ARTIFACT_SHA` / `STAGED_SHA` / `BOAT_JOB NOT present` → report; nothing to roll back (no reboot yet). If boat job absent, 5cd is not a valid v2 target — stop.

### 3. SELinux policy gate (static, before reboot)
`python3 scripts/lab/sepolicy_gate.py --recipe scripts/lab/selinux_label_recipe.sh --evidence <OUT>/sepolicy.json`
- **PASS**: gate returns 0; staged sources-boat labels match the single recipe (`.so`→system_lib_file, jar→system_file, private→data_app_el1_file).
- **FAIL → STOP + ROLLBACK**: `boat_layer_stage.sh --serial $SN --reverse --execute` → do NOT reboot into a mislabeled layer; report.

### 4. Reboot simulation (advisory offline pre-check) — REFERENCE STEP, skippable if inputs incomplete
`reboot_sim.py --inputs` takes a SHA-pinned **eight-input manifest JSON** (schema_version 1, inputs =
`plan, snapshot, inventory, autostart, closure, recipe, queries, policy` + `raw_inputs` for every snapshot
item) — NOT a snapshot directory. Build the manifest first from the pre snapshot + plan (+ the aux inputs if
available), then run the sim:
```
python3 scripts/lab/reboot_sim_inputs.py --snapshot <OUT>/pre-snapshot --plan <deploy-plan.json> \
    [--inventory P --autostart P --closure P --recipe knowledge/gates/selinux-label-recipe.json \
     --queries P --policy P] --out <OUT>/reboot-inputs.json
python3 scripts/lab/reboot_sim.py --inputs <OUT>/reboot-inputs.json --out <OUT>/prediction
```
- **If the exporter prints `MISSING aux inputs`** (inventory/autostart/closure/queries/policy not available in
  this window): this is a **reference step only** — SKIP the sim and RECORD "reboot_sim skipped: missing <names>"
  in the window notes. It is advisory; a missing input is not a safety failure and must not block the run.
- **PASS** (when all eight inputs are present): advisory prediction written; exit 0/1 is recorded, rc1 is
  FAIL/UNKNOWN (not a safety PASS), rc2 stops.
- **FAIL/anomaly with full inputs → STOP + ROLLBACK** (`boat_layer_stage.sh --reverse --execute`); report the finding.
- The real reboot-safety gate remains the post-reboot read-only checks (step 6), not this advisory sim.

### 5. Apply (real reboot — NOT `shell reboot`)
`"$HDC" -t $SN target boot` ; then wait for the device; read back `boot_id`.
- **PASS**: `boot_id` CHANGED vs step 1.
- **FAIL → STOP**: no boot_id change → `target boot` again once; if still stuck, report (possible hub re-plug per RUNBOOK). Do not touch the Mac.

### 6. Post-boot read-only health (DO NOT touch the Mac)
- `getenforce` → **Enforcing**.
- appspawn-x parent = init: `ps -A -o PPID,USER,NAME | grep -cE "^ *1 +root +appspawn-x$"` → **1** (after a first app launch; ondemand).
- AppSpawnX socket perms: `ls -lZ /dev/unix/socket/AppSpawnX` → **0660**, `u:object_r:appspawn_socket:s0`.
- boat applied: runtime=adc125f4 / adapter=8ab85446 / jar=6333bcab; `data_local_tmp` readback under /system/android = **0**; `dmesg | grep -ic invalid` = **0**.
- **PASS**: all above.
- **FAIL → STOP + ROLLBACK** (`--reverse --execute` + `target boot`); report which invariant failed.

### 7. Boat t2b five-touch playability (ground truth = screenshots)
Launch BoatAttack (proper staging; it is BMS-installed), then replay the **five scripted touches** (per specs t2b `2cbc57ab98`; uinput syntax in `benchmark/2026-10-10-boat-single-variable/README.md`): accelerate `uinput -T -d 1740 1100 -i 9000 -u 1740 1100`, steer `uinput -T -m 220 1000 70/370 1000 -k 5000 700`, reset `uinput -T -c 1440 1100 200`. Capture `touch-1..5` via `snapshot_display`.
- **PASS** (t2b 2cbc57ab98): boat **moves** after touch, steering **changes heading**, **lap counter advances**. (KPH-two-digit is NOT required — dropped in 2cbc57ab98.)
- **FAIL → record screenshots + STOP**: boat renders but is not playable → report (render-vs-playability split); rollback optional per outer.

### 8. Full-128 WITH the Boat layer
`python3 scripts/lab/board_run.py <PLAN.json>` *(PLAN pins serial 5cd, full-128 keys, boat state, `--hilog --shots 5,20`; `--dispatch` to preview)*; then `python3 scripts/lab/run_facts.py <run-dir>`.
- **PASS**: run completes; `run_facts` facts.txt captured verbatim → `5cd-boat-128/facts.txt`.
- **FAIL → STOP**: runner error (not app failures) → fix env, re-run (env failures don't count); genuine app regressions are judged in step 9.

### 9. Regression vs the 5cd clean-U13 signoff baseline (the registration gate)
`python3 benchmark/2026-10-09-demo-baseline/t4/regress_vs_signoff.py --signoff <cx-t0 5cd signoff facts> --out <OUT>/5cd-boat-128/regress-vs-signoff.json`
- **PASS (the floor, user 2026-10-10)**: **NO regression** — every app lit in the 5cd clean-U13 baseline stays lit with the Boat shared files; no first-fatal moves backward. These are SHARED files, so this is mandatory.
- **FAIL → the Boat layer regresses ≥1 app**: STOP, do NOT propose registration; rollback 5cd (`--reverse --execute` + `target boot`); report the regressing keys. The frozen entry stays DRAFT.

## On completion
- Fill the `EVIDENCE_SLOTS_TO_FILL_before_registration` in `frozen-entry-draft.json` with: `5cd-boat-128/facts.txt`, `regress-vs-signoff.json`, `boat-t2b/{touch-1..5}.png + verdict.json`, and the post-reboot proof.
- UNLOCK 5cd; PROGRESS(91) with file paths + commit. Registration into `knowledge/frozen/frozen.json` is the **outer's** step, not this lane's.
