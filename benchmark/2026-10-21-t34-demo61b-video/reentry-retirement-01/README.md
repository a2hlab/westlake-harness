# T34-RETIRE r3 — retire a strictly exited child (offline, NOT deployed)

Contract: `specs/demo61b-video-delivery/t3-confirmed-child-retirement.spec.md` @ `115ad5931c`.
Status: offline source ready; no device command, deployment, restart, lock or signal.

## What was wrong (r2, watchdog `41f1bf65`)

After `monitor_child` proved the child exited (`first_read_exited`), the reentry loop kept
re-validating that dead child's numeric PID on every gate check (`rc_gates_ok` →
`rc_child_state`). If that PID later shows a different birth, r2 returns `invalid` and the
guardian ends with `OWNER_REFUSED gate=child_identity_no_signal_no_stop_delete`. The
negative control below reproduces exactly this on r2. The fresh 61b intake shows that event
at uptime 7024 with the guardian (owner pid 4074) and child 7172 later absent; **which value
actually triggered it on the board stays UNKNOWN** — the mechanism test is not root-cause
evidence for that run.

## r3 change (`src/watchdog-reentry-r3.sh` `8bf74a08…`, diff `r2-to-r3.diff`, 22 lines)

- Both strict `child_exit_verdict=exited` branches of `monitor_child` record the retirement
  key `(boot, seq, pid, birth)` and append one `child_retired` event. Observation limit,
  stop, unknown verdict, reuse and capture failure never retire.
- `rc_child_state` returns `gone` only when the current instance equals that exact key; any
  other child (or key mismatch in any field) keeps the full r2 identity check.
- `rc_owned_window_present`: the retired PID stays in the owned set; a window matched only
  through it becomes `unknown` (not `owned`, never `no`) → no spawn.
- Retirement is cleared when `spawn.sh` is entered (`spawn_started`) and on adopt; a spawn
  with unknown outcome keeps r2's sticky hold. Boot / lock / parent gates, STOP, desktop→host
  arming (one spawn per edge) are unchanged. `instance.txt` and earlier events are not
  rewritten.

## Tests (raw argv/stdout/stderr/rc in `$T34_RETIRE_PRIVATE/raw`, indexed in `results.json`)

| Run | Result |
|---|---|
| t01 `tests/run-retirement-tests.sh` (sources the whole r3 file; 6 classes) | 71 passed, 0 failed |
| t02 same tests with `RETIRE_UNDER_TEST=` r2 (negative control) | 17 failed, rc 1 — r2 refuses on PID reuse |
| t03 old `run-all.sh` in a persistent scratch copy, r2 | PASS |
| t04 old `run-all.sh` in a persistent scratch copy with r3 swapped in | PASS (parser 21, reentry 29, race 116, cascade) |
| t05/t06 generator → r3 cascade (t06 uses the r2 root; t05 default-root output kept unused) | rc 0 |
| t07 `cargo test --test demo61b_child_retirement` | rc 0 |

Limits: the old race suite extracts only four functions, so it covers r3 bodies on the
non-retired path; retirement paths are covered by t01. In t01, `child_owned`, `parent_owned`,
`rb_owned_pids` and WMS capture/focus are stubbed seams; the parser, exit verdict, `rb_birth`
and event/state/instance writers are real.

## Pinned cascade (`candidate-payload-r3/`, root = existing `icon-manual-20261019-r2`)

Versus the repo r2 payload only `watchdog.sh`, `entry.sh`, `members.tsv`, `startup.env`,
`startup.expected.sha256` differ (SHAs in `results.json`). `screen-gate` / `decoder-probe.jpeg`
are not committed (identical to base, reproduced by the generator). The cascade is the
disabled-by-default repo form; the deployed 61b control files, backup and rollback are the
separate deployment window's job. Old r2 files are not modified.

## Deploy-only package (`deploy-package-r3-root/`, prepared, NOT admitted)

Generated (receipt t08, rc 0) from r3 source `8bf74a08` with
`--root /data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3 --enable --approved-by 'outer(codex)'`.
`STARTUP_ENABLED=1` only authorizes candidate content, not a device write. The new root was
read-only confirmed absent on boot 80b23c89. `deploy-cfg/` holds the exact live
`01_westlake_u13_toutiao.cfg` bytes and the r3 version that changes only the line-19 exec
path (the same single-line method the r2 deployment used: r2 `before.cfg`→`after.cfg`).
The generator's `payload/recovery.cfg` uses a different service name and must not replace the
live cfg. Full chain, live r2 control SHAs and fresh read-only receipts: `CHAIN.json`.
