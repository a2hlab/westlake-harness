# T45 — existing owned bridge records aligned with the T44 clicks (5cd, read-only)

**What was open.** T44 saw onCreate → onNewWant on host 20722, a WMS focus on Toutiao child 22549 at 15:00:12, and a
host-only screenshot 33 s later (15:00:45). It was unclear whether those samples contradicted each other.

**Rule applied.** Device zero writes. The state directory is located from the init cfg → `boot-entry.sh` →
`config-common.sh` (`AUTH_STATE_ROOT=$ROOT/boots/<boot_id>`), not guessed. Each sample keeps its own instant:
event lines use their own uptime, process births use /proc ticks.

## Binding
- Same boot 8b64b087; no lock holder; 229 s collection, 573 KiB raw (limits 300 s / 32 MiB); files stable over the final 15:17:10–15:17:12 stat/SHA check only, not over the full collection.
- State dir `/data/westlake-demo/toutiao/recovery-attempts/restore-v1-5cd-20261012/boots/8b64b087-…`
  - `events.log` 66323f83, `instance.txt` 2e06096b, `spawn.txt` 4cd926db, `state` c0dcbc69 (`OWNER_REFUSED`), `sequence` 53c234e5 (`2`).
- Parent 20851 = `/data/local/tmp/asx/appspawn-x`, starttime 7773763 = events `parent_birth`.
- Executor shell 3978 (starttime 3844) is named in the capture path in `snapshot.log`.
- Byte-identical repo copies exist for every deployed script except `startup.env`. This is not a lineage claim; see
  `results.json` `script_binding`.
- Clock: wall = 1792574593.08 + uptime (±1 s). Ticks at 100 Hz; host birth is close to the click-1 uitest call; ±1 s uncertainty cannot place it inside the 0.37 s call.

## Timeline (all times approximate to ±1 s)
| time | source | fact |
|---|---|---|
| 14:58:48.4–48.8 | T44 | click 1; host 20722 born 48.8; onCreate seq1 |
| ~14:58:49 | events l1 | SUPERVISOR_STARTING seq0 |
| 14:58:50.7 | /proc | parent 20851 born |
| 14:59:04–05 | events l2 | child 22549 born, BOOTSTRAP seq1 |
| 14:59:08–15:00:29 | events l3–16 | 22549 UI_UNVERIFIED (label unknown/login), one first_feed_observation 14:59:27, never READY |
| 15:00:02.9 | T44 | click 2, onNewWant seq2 — **no events.log line at this time** |
| 15:00:12 | T44 WMS | focus WID55 owned by 22549 (alive) |
| ~15:00:32 | events l17–19 | 22549 process_exit → RECOVERING, backoff 5 s |
| 15:00:45 | T44 c2 screenshot | host layout: sampled between the recorded exit of 22549 and birth of 27648; not contemporaneous with WMS, not proof of a globally child-free interval or cause |
| 15:00:49–50 | events l20 | child 27648 born, BOOTSTRAP seq2 |
| 15:01:06 / 15:01:12 | events l23–24 | first_feed_observation → READY feed_confirmed_without_auto_consent; the bridge's own capture feed-2.jpeg (15:01:13) is private and is not an acceptance screenshot |
| 15:01:33 | T44 | b189 restore install |
| ~15:16:27 | events l25, state | OWNER_REFUSED child_identity_changed_no_signal for 27648; which sub-check failed is unknown |

## Unknown
- Full argv of 3978.
- Why 22549 exited.
- Which `child_owned` sub-check failed at 15:16:27. T45 did read-only reads at 15:16:19 and 15:16:47 in other
  directories; causation was not assessed.
- State after 15:17:11.
- Any bridge reaction to click 2.
- Source of `startup.env`.

## Not claimed
White-screen root cause, a fix, continuous PID history, a passive JSON treated as a bridge request, READY treated as
on-screen acceptance.

## Files
`results.json`, `timeline.json` (39 items, each with source path/SHA or T44 raw record), `SHA256SUMS`.
Private raw (argv/start/end/stdout/stderr/rc per command, bridge capture copies): `$HOME/.local/share/westlake/t45-existing-bridge-evidence-20261022/` with `MANIFEST.sha256`.

## Outer review
197 private manifest entries and 32 six-part command records were verified. A second reviewer independently checked 25 events and 33 source copies. The retained image SHA `0228c34d…` was visually inspected by the outer agent and shows the Toutiao feed at its historical capture time; it is neither a new capture nor close/reopen acceptance. T45 has no implemented Rust selector or passing lifecycle receipt: this is evidence archival, not contract completion or a fix.

The deployed owner helper writes rejection details to stderr; no persistent sink was proven. A birth mismatch short-circuits before that helper, so a detailed record may never have been emitted. No inference about third-party exit cause is made.

### T45-A bounded follow-up
At 15:35:48 on the same boot, `/proc/3978/stat` returned a missing-file body despite shell rc0. Collection stopped before cmdline/FD2, with no substitute PID. Four admission commands took 0.254 seconds; FD2 remains unknown. See `t45-a-guardian-absence.json`.
