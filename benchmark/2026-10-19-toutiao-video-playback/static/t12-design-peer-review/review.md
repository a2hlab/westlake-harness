# t12 5cd existing-parent icon-recovery — tool.py peer review (actual code)

Reviewed actual code: `../westlake-harness-video-plan/benchmark/2026-10-20-5cd-icon-recovery/{derive.py,
tool.py}` + generated payload. Role: design peer; my assigned focus = **tool.py apply/stop/restore
chain** (base5 owns the derivation/call-chain review, report
`../westlake-harness-api-progress-peer/benchmark/2026-10-20-t12-derived-review/`). No device, no deploy,
no board write, no push.

## Verdict: **NO CODE BLOCKER in tool.py apply/stop/restore — ADMITTED.**
Final reviewed SHA: tool.py = `ca8404bfa42db16b72f06dde97b35b10e3f6a443927b4fce8f38a071172d0d1a`
(video-plan commit `bcbb1f016`). Native derivation review + cx UI review passed (not re-reviewed here).

### Final additions (bcbb1f016) — verified correct
- **Holder+ISO binding** (35-36): `--holder` = 3 fields, `h[1]` digit, `h[2]` ISO; `window_start` must
  equal the lock ISO within 1s; every command re-checks `board_note held == holder` (57). Execution is
  bound to the exact live lock holder + window — a changed/expired lock refuses.
- **60s over-window recovery only** (38-39): forward actions refuse once `age>=600`; `stop`/`restore`
  still run past 600s with a fresh 60s deadline — recovery is always possible.
- **Receipt cannot extend the deadline** (43): `deadline=min(deadline,receipt['monotonic_deadline'])`
  for non-recovery; a stale receipt can only shorten.
- **Old 7-control + cfg/run close recheck** (98-100, 153-154): preflight SHA-captures the old attempt's
  7 controls {state, events.log, instance.txt, sequence, spawn.txt, parent-identity, parent-start.txt};
  `restore` re-verifies those + CFG(`19d0201b`) + run.sh(`5a3aef63`) **unchanged** (`close-unchanged`,
  parent=False) — mechanically proving the bounded attempt left the old attempt + cfg/run byte-identical;
  drift ⇒ RECOVERY_REQUIRED.

### Admission (tool.py scope sign-off)
Admit **preflight → (review receipt) → apply → stop → restore** for outer-executed, lock-held,
preflight-gated run. All guards hold: live-parent `shell_guard` bookend on every forward command
(incl. guardian-start); one-shot (`TT_MAX_ATTEMPTS=1` + `seq>=1` stop latch); keepalive `-o 86400000`
+ `refresh-awake` per UI action + `restore -o savedOverride` verified (never `-r`); live-WMS↔parent-env
WID cross-check (no stale 29); evidence-first + noclobber + SHA-readback placement; per-command
lock+600s+timeout bounds + guardian self-deadline; recovery `parent=False` TERMs only the exact
guardian pid/birth/cmdline (no child/parent/group signal); no reboot/data-cleanup fallback. Outer to
independently re-verify, then on-board.

## Derivation corroboration (base5 authoritative; I did NOT redo it)
Generated the payload via `derive.derive()` and diffed vs sources (`payload-compare.txt`): verbatim set
{route-b-owner, launch-common, real-spawn, readiness-probe, reentry-seams, exit-verdict} all identical;
`verify_parent_window` count src=2 == payload=2; `reentry-common.sh` differs by **only** `+rc_event
t12_desktop_seen`; `spawn.sh` differs by **only** two injected `t12_launch_guard` calls with
JIT→`parent_owned`→`verify_parent_window`→`host_spawn` order intact. Consistent with base5's finding
that the two STOP/deadline guards are the reviewed necessary change and the foreground guard/order is
preserved. Full byte-identity not required (per outer).

## tool.py apply/stop/restore — actual-chain findings
- **Live-parent gating closes the TOCTOU (B3).** `remote(...,parent=True)` wraps every forward command
  with `shell_guard()` (tool.py:58,60) as pre+post amble, re-verifying live parent `19163`/birth
  `7265322` (not Z/X, exe SHA `a7a358c6`, mnt-ns≠init, run.sh inode, TracerPid 0, UID) — including
  `processes()` (119) and `guardian-start` (120). A parent that died/changed between preflight and arm
  fails the command → `RECOVERY_REQUIRED`, never a false arm. (derive.py line-60's
  `[$parent:$parent_birth=19163:7265322]` is an **env config guard, not liveness**; liveness is tool.py
  `shell_guard` + the guardian's own `verify_parent_window`×2 — base5's seam.)
- **One spawn (B2).** `entry.sh` exports `TT_MAX_ATTEMPTS=1 TT_MAX_POLLS=0`; rewritten `rc_stop_present`
  writes `stop=single_launch_complete` once `seq>=1`. Double-enforced. (derive side; base5.)
- **Power P1 — restore is `-o savedOverride` + full verify, never `-r`.** apply sets `-o 86400000` +
  readback (110-111); `refresh-awake` re-sets `-o 86400000` + readback per UI action (uitest resets it,
  123-125); `restore` sets `-o original.override` and `need(read_power()==original)` on BOTH
  timeout+override (149). Power original pinned from `power-shell dump -s` (`Timeout 10000/Override
  10000`). Foreground guard is NOT weakened — keepalive only prevents screen sleep; the host-readiness
  guard (FOREGROUND_HOST_NOT_READY path) is untouched.
- **Power P2 — WID not defaulted to 29.** preflight reads the parent's live `WL_PARENT_ID` from
  `/proc/19163/environ` and **requires the live WMS host window field to equal it**
  (`host[0][3]==wid[0]`, 82-89); exactly 1 SCBDesktop + 1 imehost0; host/desktop identities bookended
  (stat/uid/exe/exe-sha/cmdline, drift-checked). Stale 29 cannot leak in.
- **Fail-safe ordering & bounds.** evidence `result.json` written before device mutation (108-109);
  override set before mkdir; root `umask 077`→verify `:0:0:700` (112-113); payload placed with `test
  !-e` + `set -C` noclobber + `chmod 500` + SHA readback (115-118); every command re-verifies the held
  5cd lock (`board_note.sh held`==holder, 57) + 600s window (38,50) + per-command `timeout`; the guardian
  carries its **own** `guardian_deadline_uptime` so it self-stops even if the outer dies (98 → derive
  `t12_deadline_stop`).
- **Recovery correctness.** `stop`/`restore` run `parent=False` deliberately — they must work even if
  the parent died (gating cleanup on parent liveness would strand an awake screen). `stop` TERMs **only**
  the recorded guardian pid+birth+cmdline (`/system/bin/sh\n<root>/watchdog.sh`), refuses a changed
  process, never a group/child/parent signal (135-144); bounded 5s confirm. `stop` status
  `GUARDIAN_STOPPED_RESTORE_REQUIRED` forces a following `restore`.

## Recommendations (executable scope; NOT blockers)
- **R1 — `stop` should collect on-device guardian artifacts into `out/` before/after TERM**
  (`<root>/state`, `/event`, `/spawn.txt`, `/wms-owned.txt`, `/guardian.log`) so the STOP receipt is
  self-contained (blueprint step 6 "collect originals"). Currently `stop` writes the stop marker + TERMs
  but does not `cat` those into `out/`; add a bounded read sub-step. Evidence completeness, not safety.
- **R2 — runbook ordering pin (no code change):** apply → (per UI action: outer acts, then
  `refresh-awake`) → `stop` → `restore` → verify `POWER_RESTORED_ONLY` → release lock. The status names
  encode the chain; the lock release must gate on `POWER_RESTORED_ONLY` (do not release on
  `GUARDIAN_STOPPED_RESTORE_REQUIRED`).

## Executable scope (safe to run under the outer's lock + preflight receipt)
`preflight` (read-only pins/processes/windows/power) → review receipt → `apply` (places payload under
`icon-manual-5cd-t12-*`, sets keepalive, arms one-shot guardian) → outer does ≤1 desktop→host icon +
optional one video click, `refresh-awake` after each UI action → `stop` → `restore`. All bounded by the
600s lock window and the guardian uptime deadline; no reboot/data-cleanup fallback; lost transport ⇒
`RECOVERY_REQUIRED`, not PASS. Fresh-boot remains a **backup** (10-19 transport proven on 61b only; a
5cd variant still needs its own derived deploy/restore — not zero new code).

token t12-design-peer-ready
