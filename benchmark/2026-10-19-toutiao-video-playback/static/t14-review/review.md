# t14 5cd normal play-observation — actual-code narrow review (4 axes)

Reviewed real code (video-plan `benchmark/2026-10-20-t14-play-observation/`):
- `observe.py` sha `2b33711fb3b5b1af110228ef0e5279298b5756b70f30860f2ef42f2c93f2cbe0`
- `framing.py` sha `c90a65c0dc2b7836bc828383cc62559dd6bb48fe96a8f2bd34435e4b1ce2a7a2`
- spec `t14-normal-play-observation.spec.md` sha `5d522b33aec3372f7cb45d73ab0f62217518adf84678f81ab1bc273a88faa64e`
Scope = the 4 named axes only. NOT reviewed: player root cause, deploy, attach, REA (not redone). No device.

## Verdict: **NO BLOCKER.** All 4 axes sound in actual code. 2 runbook notes (non-blocking).

## Axis 1 — runtime identity / lock / 600s — SOUND
- Identity: `profile()` (18-29) pins serial/boot/run+sha/readonly-receipt + parent/child/host
  pid/ppid/birth/uid/exe-sha/mnt, child.ppid==parent.pid, child.uid==host.uid==20011300,
  parent.mnt==child.mnt≠init (private ns), display ≤8192; `receipt pin` (63) binds the outer read-only
  receipt; `source-pins.json` (65-66) verifies reused **bms_batch f41efa6a + delta 19656e17** before any
  device call. `guard()` (32-43) is a per-command bookend (`set -eu; guard; cmd; guard`, shell():100-102)
  re-verifying boot + all 3 processes (stat not Z/X, birth, ppid, Uid×4, TracerPid 0, ns/mnt, exe-sha) +
  run.sh sha + parent private-root inode. (restore runs guard='true' — recovery must survive drift.)
- Lock: `B.ready()` (98-99) re-checks `held==holder` on every command; holder↔ISO bound (68).
- 600s: `0<=age<600` (69); deadline no-extend via `min(…,state)` (78-79); **`B.command` reserves 60s for
  non-restore** (89) ⇒ UI/capture stop by 540s, last 60s restore-only; `flock LOCK_EX|NB` (74-75)
  serializes actions. ✓

## Axis 2 — per-screenshot coords / one tab + one play — SOUND
`ui_command` (51-55): `kind not in used` (each of unlock/front/tab/play **at most once**) AND
`reviewed==latest` screenshot sha (64-hex) — coords must target the **current** reviewed screenshot, no
stale/repeat; coord count (swipe 4 / click 2) + in-display-range; no coord guessing. `ui` action (124-130):
tab/play require `foreground([child,host])` confirmed; play requires a captured `log_before` baseline;
intent (`last_ui`) saved **before** execution; no auto-retry (a second same-kind fails `once`). ✓

## Axis 3 — original screen-parameter restore — SOUND
`begin` saves `power_original=(Timeout,Override)` before awake (121); `awake()` sets `-o 86400000` +
readback, re-applied after each UI (130)/capture (123); `restore()` (107-112) sets `-o original Override`
and `need(power(dump)==original)` (both fields); error path (142-147) marks stopped+recovery_required then
**auto-attempts restore**, keeping `recovery_required`/lock on restore failure; restore touches only power,
never signals an app. ✓

## Axis 4 — fd2 regular-file range + HDC merged framing — SOUND
`framing.script` redirects `dd` stderr (fd2) to a **scratch regular file** (`2>{err}`) so the merged HDC
stream's payload stays clean, bounded `0<=size<=65536`, unique 32-hex token, `BEGIN:size / END:rc / POST`
guard markers. `framing.decode` proves completeness by **marker position** (`END` must begin exactly at
`len(start)+size`) + `END:0` + host rc0 + no timeout ⇒ `BOUNDED_BYTES_COMPLETE`; else `PARTIAL_UNVERIFIED`
(bytes preserved, `player_verdict='unknown'`). Position-based ⇒ binary-safe and detects `dd` short-read at
EOF (where dd still returns 0). `observe.log-read` (135-141): one post-play read only; `logstat` verifies
`/proc/child/fd/2 == log` (fd2 target is that regular file); frame guard re-checks log `dev:inode==before`
+ `size>=after.size` (no rotation/truncation); reads the new-bytes range from `before.size`; PARTIAL ⇒
raise ⇒ restore. ✓

## Runbook notes (not blockers; consistent with T12/T13)
- **N1** — normal success does not auto-restore; the outer must call `restore` before releasing the lock
  (state `stopped`/`recovery_required` + the 540s/60s split guide it; a deadline-hit command raises ⇒
  auto-restore). Gate lock release on the restored state.
- **N2** — tab-before-play order is not tool-enforced (each kind once + foreground + screenshot-bound);
  the actual sequence + real load/dynamic playback are **human-reviewed** from screenshots + original log,
  not a script PASS. `playback`/`player_verdict` stay `unknown`; feed/video-cover ≠ playback.

token t14-review-ready
