# T31 root-channel card — 5cd only

Status: offline implementation for peer review; **no board action or retention has happened**. Recovery sources d405e37d/dce32de0/5efdb869/ef4d51dc are unchanged from outer's snapshot02 acceptance. The original 42 T30 files remain unchanged. Fresh WID must still be29: otherwise stop; do not edit admission to make it fit. Owners already20011300. No candidate rebuild.

Set `MAIN` to the landed main repository. Root alone supplies its working HDC transport. All raw argv/stdout/stderr/rc must remain under the NEW window. Do not use any T30 `t30_outer/launch/frames` entry (their output root is historical).

```sh
cd "$MAIN"
T="$MAIN/benchmark/2026-10-20-t31-demo-retain"
H="$T/helpers"
D="$MAIN/benchmark/2026-10-20-t30-request-recovery/deployment/final-01"
BASE="$HOME/.local/share/westlake/toutiao-resume-20261020"
W="$BASE/t31-5cd-window-01"
INPUTS="$BASE/t30-candidate-inputs"
export T31_BASE="$BASE" T31_DEPLOY="$D" T31_EXECUTE=1
python3 "$T/preview.py" --repo "$MAIN"  # local only; all fresh fields null
# Root's existing transport does initial read-only boot/process/WMS/power inspection.
python3 "$H/t31_outer.py" acquire
# B/P/PB/HOST are ACTUAL current boot,parent,birth,host from the new read, never old T30 IDs.
python3 "$H/t31_outer.py" shell candidate "$B" 'ps -A -o PID,PPID,UID,NAME; hidumper -s WindowManagerService -a "-a"; power-shell dump -s; param get debug.ttplayer.log.enable || true'
python3 "$H/fresh_read.py" apply "$P" "$HOST" fresh-read
python3 "$H/fill_admission.py" fill --repo "$MAIN" --context "$W/context.json" --held-stdout "$W/fresh-read/held.stdout" --held-stderr "$W/fresh-read/held.stderr" --held-rc "$W/fresh-read/held.rc" --read-stdout "$W/fresh-read/read.stdout" --read-stderr "$W/fresh-read/read.stderr" --read-rc "$W/fresh-read/read.rc" --out "$W/fresh-admission"
python3 "$T/scope_apply.py" --context "$W/context.json" --fresh-admission "$W/fresh-admission/admission.json" --origin-data "$D" --out "$W/scoped-admission.json"
python3 "$H/t31_baseline_collect.py"
python3 "$T/window_exec.py" preflight --execute --context "$W/context.json" --admission "$W/scoped-admission.json" --identity "$W/fresh-admission/identity.json" --inputs "$INPUTS" --out "$W/preflight"
python3 "$T/window_exec.py" apply --execute --context "$W/context.json" --admission "$W/scoped-admission.json" --identity "$W/fresh-admission/identity.json" --inputs "$INPUTS" --out "$W/apply"
python3 "$H/t31_outer.py" reboot candidate "$B"
python3 "$H/t31_wait_boot.py" candidate "$B" candidate
# BNEW comes from candidate-boot.json; root checks fresh parent/host/private identity.
python3 "$H/t31_launch.py" candidate "$BNEW" cycle1-icon
python3 "$H/t31_outer.py" capture candidate "$BNEW"
```

**The scoped admission above is the one actually sent to executor693448.** Preserve `apply/plan.json`, `scoped-admission.json`, all five verified backup paths and the original ABSENT marker. A preflight/apply failure or incomplete518+26 requires recovery; never retry mutations blindly. Same candidate five-slot reader remains MAIN T30 `helpers/read_slots.py` with fresh identities and actual T30 artifact inputs; its code has no historical output root, and `--out` must be `$W/five-slots`. Inspect all five matches, not rc alone.

For each of TWO cycles, first inspect the new screen and select the visible video/control coordinates. Root uses `t31_outer.py shell candidate "$BNEW" 'uitest uiInput click X Y; power-shell timeout -o 86400000; pw=$(power-shell dump -s); printf "%s\n" "$pw"; printf "%s\n" "$pw" | grep -F "OverrideTimeout=86400000ms"'` with actual visually chosen X/Y. Every root-issued uitest click or keyEvent must use this SAME serial shell order: UI action → power-shell timeout -o86400000 → dump/readback requiring OverrideTimeout=86400000ms. A readback failure stops the next observation; do not retry an unknown UI action. This also applies to pause/play/back/fullscreen. No concurrent power changes. Final close restores10000/10000. No predetermined tap is embedded here. After selecting play / pause / resume respectively:

```sh
python3 "$H/cycle_frames.py" play cycle1-play "$BNEW"       # 0/5/10/20
python3 "$H/cycle_frames.py" pause cycle1-pause "$BNEW"     # 0/3
python3 "$H/cycle_frames.py" resume cycle1-resume "$BNEW"   # 0/5/10
# Root visually chooses exit/back; capture actual feed, then:
python3 "$H/t31_outer.py" capture candidate "$BNEW"
python3 "$H/t31_launch.py" candidate "$BNEW" cycle2-icon
# repeat the three phase commands using cycle2-* tags, then exit/feed/icon evidence.
```

The phase helper does NOT click for you. Each cycle requires its own content-linked human audio confirmation; one clip's confirmation cannot cover the other. Capture source paths/result timestamps are authoritative; no planned count is a fact. Keep controls/clock/subtitles outside the video-content ROI. Final repeated icon is a normal authorized reentry, not crash diagnosis. Do not wait past1200s for audio, a reviewer, or an upload.

## Same-window failure / no signature by1200s

Use fresh current parent/host; derive the admission from this T31 plan and its **scoped** admission. Original frozen local filler is reused without modification:

```sh
python3 "$H/fresh_read.py" rollback "$PCUR" "$HCUR" rollback-read
python3 "$H/rollback_admission.py" fill --repo "$MAIN" --context "$W/context.json" --apply-plan "$W/apply/plan.json" --apply-admission "$W/scoped-admission.json" --held-stdout "$W/rollback-read/held.stdout" --held-stderr "$W/rollback-read/held.stderr" --held-rc "$W/rollback-read/held.rc" --read-stdout "$W/rollback-read/read.stdout" --read-stderr "$W/rollback-read/read.stderr" --read-rc "$W/rollback-read/read.rc" --out "$W/rollback-admission"
python3 "$T/window_exec.py" same-window-rollback --execute --context "$W/context.json" --admission "$W/rollback-admission/admission.json" --identity "$W/rollback-admission/identity.json" --inputs "$INPUTS" --origin-plan "$W/apply/plan.json" --out "$W/rollback"
python3 "$H/t31_outer.py" reboot restored "$BCUR"
python3 "$H/t31_wait_boot.py" restored "$BCUR" restored
python3 "$H/t31_restore_collect.py"
python3 "$H/t31_launch.py" restored "$BRESTORED" restored-icon
python3 "$H/t31_outer.py" capture restored "$BRESTORED"
```

Root compares the same518-target eight fields and26supplement against THIS window's before, checks original physical/private six states and restores original power10000/10000/debug absent106. UI may fail and must be recorded as such. The helper's1800-second gate is not extended.

## Retain decision and close

Before1200s, root must explicitly approve a **5cd-only** retain decision referencing: two reviewed cycles/two corresponding audio receipts, actual candidate boot/identity/five slots/six file states, production/source commits, THIS T31 apply-plan+scoped admission hashes, backup SHA/meta+ABSENT SHA evidence, independently accepted recovery code/source pins and limitations (live parent/WID29 only), responsible operator, original power/parameter receipts. No script here fabricates a signature. Missing item means the rollback branch above. Do not promise rescue for dead parent or changed WID.

Restore temporary settings and capture final UI (candidate branch if retaining, restored branch if rollback). Use the same checked holder; root writes signed decision/close with actual timestamps. Then the existing close/unlock interface is:

```sh
python3 "$H/t31_outer.py" shell "$PHASE" "$BCURRENT" 'power-shell timeout -o 10000; power-shell dump -s; param get debug.ttplayer.log.enable || true'
python3 "$H/t31_outer.py" capture "$PHASE" "$BCURRENT"
bash "$MAIN/scripts/lab/board_note.sh" unlock "$MAIN/.octos/boards/app-lighting.md" 5cd1e3dd00000000000000000923012c 'inner(cx-seal)' > "$W/unlock.stdout" 2> "$W/unlock.stderr"
printf '%s\n' "$?" > "$W/unlock.rc"
bash "$MAIN/scripts/lab/board_note.sh" held 5cd1e3dd00000000000000000923012c > "$W/held-after.stdout" 2> "$W/held-after.stderr"
printf '%s\n' "$?" > "$W/held-after.rc"
```

For retain, PHASE=candidate and all decision/temporary-state checks finish by1200s. For rollback, PHASE=restored and close before1800s. held-after expectedrc1/empty, not rc0. Preserve errors and time overruns. Archive evidence first; final seal S is separately git-fixed after archive R, not inside its own hashed archive. The in-window retain decision and the later archival seal are separate records, neither may be retroactively invented.

## Future recovery of a retained T31 candidate (new lock, same original backups)

This entry is **rollback-only**, live parent/WID29 required; other cases refuse/need separate reviewed action. `ORIGIN` is the actual retained T31 window, never historical T30. Acquire a NEW root MAIN lock via board_note, record heldstdout/stderr/rc; set R to a fresh `t31-recovery-window-N` and use prepare_context with `--recovery`. Preserve the origin files unchanged.

```sh
python3 "$T/prepare_context.py" --recovery --repo "$MAIN" --origin-data "$D" --hdc "$HDC" --held-stdout "$HELD_STDOUT" --held-stderr "$HELD_STDERR" --held-rc "$HELD_RC" --out "$R"
python3 "$T/recovery/recovery_admission.py" read-script --parent "$PCUR" --host "$HCUR" > "$R/read.sh"
# Root transport executes that exact read.sh under NEW held/time budget and records read.stdout/stderr/rc.
python3 "$T/recovery/recovery_admission.py" fill --repo "$MAIN" --origin-data "$D" --context "$R/context.json" --apply-plan "$ORIGIN/apply/plan.json" --apply-admission "$ORIGIN/scoped-admission.json" --held-stdout "$HELD_STDOUT" --held-stderr "$HELD_STDERR" --held-rc "$HELD_RC" --read-stdout "$R/read.stdout" --read-stderr "$R/read.stderr" --read-rc "$R/read.rc" --out "$R/admission"
python3 "$T/window_exec.py" durable-recovery --execute --context "$R/context.json" --admission "$R/admission/admission.json" --identity "$R/admission/identity.json" --inputs "$INPUTS" --origin-plan "$ORIGIN/apply/plan.json" --origin-admission "$ORIGIN/scoped-admission.json" --out "$R/rollback"
```

Then root's existing freshboot/ready/same-plan518+26/source-private/power/param/UI/close steps use R and the NEW holder/start. Do not call T31 original-window helpers for this future R (their fixed WINDOW is intentional). No automatic reboot/unlock is hidden in recovery.py; `PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT` is not a full recovery verdict. Origin backup corruption/absence or foreign runtime blocks overwrite. The separate recovery window uses1800s; neither the old holder nor old start is forged.
