# T34: cc-video execution card (offline package; approval still required)

Only `inner(cc-video)` may issue device operations. Run commands with `cwd=$MAIN`.
`MAIN` is the reviewed main repository; `D=$MAIN/benchmark/2026-10-21-t34-demo61b-video/deployment`.
`W` is a new persistent T34 window directory. `INPUTS` is the verified
`t30-candidate-inputs` directory. Never reuse a historical holder/start.
No command below has been executed against a device by this lane.

## Bind input bytes before locking

The additional read-only shell is generated locally; cc-video executes it once with its
existing read-only transport and preserves script/argv/stdout/stderr/rc:

```sh
python3 "$D/render_supplement.py" --boot "$FRESH_BOOT" \
  --parent "$PARENT" --birth "$PARENT_BIRTH" --host "$HOST" --hostbirth "$HOST_BIRTH" \
  > "$INTAKE/supplement.sh"
```

The supplement must finish with matching `T34_BOOT_BEFORE/T34_BOOT_AFTER`.
The accepted intake is assembled into `fresh.json` using the exact fields consumed by
`prepare_data.validate`: source references include raw SHA and no invented missing values.
The original `before-image/run.sh` is read as bytes, not shell command substitution.

```sh
python3 "$D/prepare_data.py" --repo "$MAIN" --fresh "$INTAKE/fresh.json" \
  --run "$INTAKE/before-image/run.sh" --out "$W/data"
```

This creates **unsigned** `admission.template.json`. The status is
`FRESH_DATA_BOUND_NOT_AUTHORIZED`; it does not authorize device writes.
The complete data directory, executor diff and original/candidate hashes go to outer/peer.

## New window, scoped approval, preflight, apply

Only after outer/peer accept this source and bound data:

```sh
bash "$MAIN/scripts/lab/board_note.sh" lock \
  "$MAIN/.octos/boards/app-lighting.md" \
  61b0657200000000000000000324012c 'inner(cc-video)' 'T34 reviewed migration'
bash "$MAIN/scripts/lab/board_note.sh" held \
  61b0657200000000000000000324012c > "$W/holder.txt"
```

Record actual holder, its ISO timestamp epoch as `START`, actual boot, parent PID/birth/mnt
and host PID/birth/UID. Recheck them before admission. Fill a copy of the template:
`holder`, `window_start`, `boot`, `parent`, `parent_mnt`, `host`, `physical_only:false`.
Parent UID is **0**, host UID **20011206**. `wid` must equal this intake's raw run,
parent environment and WMS host row. Only outer supplies `approved_by:"outer(codex)"`
and real signing time. Do not modify source/data pins after approval.

```sh
python3 "$D/executor61b.py" preflight --execute \
  --repo "$MAIN" --data "$W/data" --inputs "$INPUTS" --hdc "$HDC" \
  --boot "$BOOT" --parent "$PARENT" --birth "$PARENT_BIRTH" \
  --holder "$HOLDER" --start "$START" --admission "$W/admission.json" \
  --out "$W/preflight"
python3 "$D/executor61b.py" apply --execute \
  --repo "$MAIN" --data "$W/data" --inputs "$INPUTS" --hdc "$HDC" \
  --boot "$BOOT" --parent "$PARENT" --birth "$PARENT_BIRTH" \
  --holder "$HOLDER" --start "$START" --admission "$W/admission.json" \
  --out "$W/apply"
```

Retain `apply/plan.json`, original `admission.json`, all command receipts and all five
on-device `.t34-61b-before-<original boot8>` backups plus the compat absence marker.
All backups are created/verified before the first swap. No `cp` writes an existing
runtime target; the swap uses a new same-directory file, metadata verification,
exact preimage CAS, then rename.

Use the existing cc-video reboot/wait/normal-icon/screenshot channel, bound to the
new boot and identities. Do not import 5cd helpers' serial, UID, WID, power or
guardian ROOT. This card does not authorize another runtime or alternate source.

## Same-window rollback, including no-parent physical recovery

Stop experiments by `START+1200`; restore and close by `START+1800`.
Do not wait for analysis/signoff beyond the recovery reserve.

Create `rollback-admission.json` from the original **actual** admission. Preserve all
source/data hashes, holder and start; bind:

- current real boot;
- `origin_apply_plan_sha256` = actual `apply/plan.json` SHA;
- current captured physical run bytes' exact `recovery_run_sha256` and `recovery_wid`;
- current live parent/host identities for normal rollback; **or** `parent:null`,
  `host:null`, `parent_mnt:null`, `physical_only:true` for no-parent recovery.

The only permitted run drift is one numeric `WL_PARENT_ID` line. The exact captured
run hash is admitted, then normalized only for comparison to the original two templates.
Recovery restores the **original backup bytes**, including its original WID, before
fresh boot. Foreign bytes outside that line refuse. Missing any backup after any
mutation refuses. No-parent recovery still requires current boot, exact physical
runtime paths/directories, cfg, guardian controls, HAP, providers, original plan/admission,
all exact pre/post file states and verified backups. It is not arbitrary-board rescue.

```sh
python3 "$D/executor61b.py" rollback --execute --recovery-no-parent \
  --repo "$MAIN" --data "$W/data" --inputs "$INPUTS" --hdc "$HDC" \
  --boot "$CURRENT_BOOT" --holder "$HOLDER" --start "$START" \
  --apply-plan "$W/apply/plan.json" --origin-admission "$W/admission.json" \
  --admission "$W/rollback-admission.json" --out "$W/rollback-01"
```

For a live-parent rollback, omit `--recovery-no-parent`, pass the fresh
`--parent/--birth`, and set `physical_only:false` with exact current host/parent.
After partial failure, preserve that output and use a fresh output directory;
retain the same original apply plan and original backup names.

After rollback: normal fresh boot, before/after same-plan snapshot and supplement,
physical/private original hashes, compat absent, host/HAP/UID/token/controls preserved,
power **30000/86400000**, debug absent106. Capture the actual final UI; host-only is
not feed recovery. Outer decides retention or recovery acceptance, then cc-video:

```sh
bash "$MAIN/scripts/lab/board_note.sh" unlock \
  "$MAIN/.octos/boards/app-lighting.md" \
  61b0657200000000000000000324012c 'inner(cc-video)'
```

No 5cd writes, 5ea operations, source rebuild, data clearing or new audio confirmation.
