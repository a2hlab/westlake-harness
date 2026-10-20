# Exact candidate activation — root execution only

This card replaces only the repeat-playback/per-clip-audio acceptance steps for t4, under `acceptance-addendum.json`. Do not edit or reinterpret historical t2 results. Previous replay is unsigned and being restored; wait for outer baseline recovery/unlock before acquiring this new window. No pre-signed retention JSON is supplied.

## New output root and existing entrypoints

Set MAIN to landed main. Read fresh boot/parent/host before using B/P/PB/HOST; do not paste prior IDs. Confirm original power10000/10000 and debug absent106. All executable dependencies and data are pinned in dependencies.json. WID must be29.

```sh
cd "$MAIN"
T="$MAIN/benchmark/2026-10-20-t31-demo-retain"
H="$T/helpers"
D="$MAIN/benchmark/2026-10-20-t30-request-recovery/deployment/final-01"
BASE="$HOME/.local/share/westlake/toutiao-resume-20261020/t31-activation-01"
# This BASE must be NEW and this shell must be the only device executor.
test ! -e "$BASE" || exit 1
mkdir -p "$BASE"
W="$BASE/t31-5cd-window-01"
INPUTS="$HOME/.local/share/westlake/toutiao-resume-20261020/t30-candidate-inputs"
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
python3 "$H/t31_launch.py" candidate "$BNEW" activation-icon
python3 "$H/t31_outer.py" capture candidate "$BNEW"
```

No repeat two-cycle run and no repeat audio request. `T31_BASE` isolates this activation from replay/T30; WINDOW remains the original fixed t31-5cd-window-01 **under the new BASE**. The apply command uses scoped-admission.json, not the unscope filler output.

## Fresh child fallback / five slots / six states

If quick reports no unique child, retain that output. Read the same `activation-icon/ps.txt`, select only an exact com.ss.android.article.news row with UID20011300 and PPID=current verified parent. If none/ambiguous, capture a new complete ps as a new receipt; do not reuse stale PID. For its fresh C and P, use existing checked shell to record `/proc/$C/stat`, `/proc/$C/status`, `/proc/$C/exe` SHA and `/proc/$C/ns/mnt`, and the corresponding parent values, then stat again. Require non-Z/non-X, stable birth, child PPID=P, child UID20011300/parent UID0, TracerPid0, exact appspawn exe a7a358c6, same child/parent private namespace. Only those actual stat values supply PB/CB. This is a selector fallback, not a weakened identity gate.

```sh
# HDC/holder and all identities below are read from THIS context/current receipts.
# The original reader independently verifies full stat/UID/exe/mnt and all four ELF SHA.
python3 "$MAIN/benchmark/2026-10-20-t30-request-recovery/deployment/helpers/read_slots.py" --execute --repo "$MAIN" --hdc "$HDC" --holder "$HOLDER" --boot "$BNEW" --parent "$PNEW" --parent-birth "$PBNEW" --child "$CNEW" --child-birth "$CBNEW" --player-elf "$INPUTS/libttmplayer.so" --bridge-elf "$INPUTS/liboh_adapter_bridge.so" --shim-elf "$INPUTS/libwebview_bionic_shim.so" --surface-elf "$HOME/.local/share/westlake/toutiao-resume-20261020/provider-surface-readonly/libsurface.z.so" --out "$W/five-slots"
```

Require all five named matches, not rc alone. If player not yet mapped, enter a visible video once through normal UI to load it, then collect under a new tag; no repeat cycle/audio test. Return to feed and capture. Preserve any failed read. Do not replace a failed binding with an old-window result.

For six-state after verification, read the physical and parent-private paths named by final-01/parameters.json and THIS apply/plan.json (run, compat, media, player, bridge, shim), SHA and mode/uid/gid/label/dev:inode; compare against exact after hashes and fresh admission metadata, requiring physical/private inode equality. Existing root serial shell/metadata-read recipes suffice; no new executor. Also check unchanged cfg and live host WID29. For run, require actual 11d3d671... WID29 bytes, not normalization.

## Timely retain or rollback

Before1200s, outer signs an actual `retain-decision.json` after reviewing fresh six states/five slots, normal icon-to-feed, reused-evidence SHA, and original settings. Include real decision time/approved_by=outer(codex), current holder/start/boot/parent/host/child/birth, source/production refs, this W/apply/plan.json + scoped-admission hashes, all five backup paths/SHA/metadata + ABSENT marker SHA, recovery source hashes, named recovery owner and live-parent/WID29 limitation. These backup paths must use this activation origin boot8, not replay. Backups must persist and never be overwritten. No signature may be copied from old windows.

The latest user accepts manual audio globally for this scoped candidate and same-clip visual evidence; preserve prior cycle-title audio nulls. It does not authorize silently ignoring a new activation failure.

Every uitest click/keyEvent uses the existing serial shell followed by `power-shell timeout -o 86400000` then dump requiring OverrideTimeout86400000. Before retain decision restore `power-shell timeout -o 10000`, read actual Timeout10000/OverrideTimeout10000, and confirm debug absent106. Capture final feed and bind identity. The unchanged original card's **Retain decision and close** unlock commands are reused, but its old repeated-audio prerequisites are superseded for this t4 only. held-after expects rc1/empty.

If final proof/signature is incomplete at1200, follow exact original card **Same-window failure / no signature by1200s** using THIS W/context/scoped-admission/apply-plan and current identities; rollback→freshboot→same518+26/source-private/power/param/UI→close before1800. Do not wait for archive upload to decide.

Future recovery uses original card **Future durable recovery window** with new R/holder/start and ORIGIN=this activation W. Preserve its original apply backups and use `window_exec.py durable-recovery`; live parent/WID29 only. A dead parent, foreign byte, missing backup or other WID refuses and requires separate review; do not advertise unconditional rescue.

Record window decision before deadline, then archive E→A→R; final S separately binds R and the earlier decision. S does not go inside its own archive. No new build, helper edit, runtime edit, API freeze or general video guarantee.
