# T37 independent host reentry review

**Latest: r4c `c73dadb3` passes 18/18 independent safety assertions; full offline package passes 165/165 pin checks.** Five replayed production sources equal their packaged counterparts. See `REVIEW-r4c.md`, `latest-review.json`, `r4c-c73dadb3-01/` and `assembly-r4c-02/`. The package is intentionally UNAPPROVED/disabled and retains the r3 ROOT, so this is an offline review handoff, not deployment approval. Earlier request-changes evidence below remains historical.

**Request changes.** The old assumption that child retirement alone covers host recreation is false in the production r3 path. Twelve r3 replay cases reproduce three baseline gaps and nine controls. Sixteen independent cases on the first T36 work-in-progress snapshot reproduce eight adverse observations and eight controls. Reproduction success is not candidate acceptance. No device access, REA, real signal, real socket removal or author-code modification occurred.

## Evidence and exact object

- Base: `47bdf7c706`; T35 evidence: `../whitescreen-01/README.md` and `results.json`.
- Production donor: `benchmark/2026-10-21-t34-demo61b-video/reentry-retirement-01/deploy-package-r3-root/payload`. The 20 available text payload files match the 22-member original manifest; `screen-gate` and `decoder-probe.jpeg` are absent in this checkout (see `r3-assembly.json`), so no full package execution is claimed. Available file SHA values are in `baseline-02/results.json` (actual count is the manifest length).
- T36 source snapshots, time, author HEAD and SHA: `candidate-01/pins.json`. These are uncommitted source snapshots, not an approved deployment or final author candidate. Full entry/payload assembly was not present at snapshot time.
- Raw generated scripts, stdout, stderr, rc, expected observations and script SHA are in `baseline-02/` and `candidate-replay-02/`. OS/process/transport seams are synthetic. Production functions and WMS parser execute; device entry does not execute.
- The first baseline harness attempt omitted a subshell-form parser function. `baseline-01/` preserves that failed attempt. `baseline-02/` includes the complete production parser and has no stderr. No baseline result from the broken harness is used.
- Live parent environment remains **unknown**. T35's tool failure and rejected follow-up were not retried, bypassed or replaced with historical environment as live evidence. The live cause remains inferred.

## Production assembly and counterexamples

`boot-entry.sh -> entry.sh -> watchdog.sh main -> start-parent.sh -> real-start-parent-bounded.sh -> monitor_child -> rc_reentry_loop -> do_one_launch -> spawn.sh -> real-spawn.sh`.

`entry.sh` pins the watchdog and ownership helper and exports the immutable authority. `start-parent.sh` refuses an existing socket and persists `parent-identity`. Its real helper rewrites `WL_PARENT_ID` with `sed -i` before launching the initial parent. Both watchdog focus and `spawn.sh` verify the parent's bound WID. `real-spawn.sh` only sends a fixed request. Removing the first WID guard alone cannot update the parent or pass the second guard.

Baseline watchdog SHA: `8bf74a08b71474e39e90fcdb012eed5e420f7352fa131cef2aa63b9c5bd80ef9`.

| Case | Actual production observation | Required behavior |
|---|---|---|
| `new_host_binding` | Verified host WID30, parent bound WID29 yields `other` | Explicit qualified reentry or refusal reason |
| `enumeration_failure_window` | `rb_owned_pids` rc7 becomes `owned=no` | Unknown, no destructive transition |
| `enumeration_failure_launch` | Same rc7 enters spawn helper, `calls=1` | Refuse before spawn |

## T36 snapshot blockers

References below are to immutable `candidate-01/watchdog-reentry-r4.sh`, not the moving author file. Each named case has a raw receipt in `candidate-replay-02/`.

1. **Exit is not proven.** `rc_parent_epoch_switch` (lines 334–375; exit check 351–352) compares `rb_birth` output with old birth; any read failure makes the strings differ. `birth_read_failure_after_term` proceeds to one unlink and one start. It needs a strict exited/unknown/reused distinction before any socket or run-inode change. `pid_reuse_after_term` also proceeds, preserving no explicit replacement-identity classification; this is an adverse identity-policy observation, not proof that the old process is still alive.
2. **Enumeration can manufacture emptiness.** `rc_direct_children` (306–316) accepts malformed stat text and a nonexistent proc root; `rc_fd_holders` (324–333) skips missing fd directories and ignores failed readlink. `malformed_proc_stat` reaches TERM/unlink/start. The standalone primitive cases return rc0/empty on incomplete data. A PID disappearing can be benign only with explicit proof; an unreadable or malformed existing object is unknown.
3. **Socket ownership is incomplete.** `rc_socket_inode_of` (317–323) matches a path and numeric inode without checking listening flags/state/type. `nonlistener_socket_row` accepts a connected row. Existing fd ownership alone does not establish who created the fixed pathname or exclude an init-provided endpoint. Post-stop holder scan only concerns the old inode; require a fresh complete listener/path ownership observation before unlink. Missing-fd/readlink failures above undermine that scan too.
4. **Signal authority must be narrower than read-only matching.** `parent_owned` (90–107) permits any matching private namespace and matching current physical/private run inode; it does not itself store and compare the guardian's previously recorded namespace or establish socket creation authority. Keep it read-only. Before TERM, validate the exact recorded epoch and complete direct-child absence, including unknown and malformed entries. A newly appearing child between enumeration and signal must also have an explicit exclusion argument.
5. **Baseline enumeration gaps remain in this snapshot.** Existing `rc_owned_window_present` and `do_one_launch` are unchanged. The new direct-child check does not repair ordinary same-host spawn's rc7-as-empty path. `newhost_owned_enum_failure` additionally reproduces TERM/unlink/start/spawn in the actual newhost loop after owned enumeration rc7. `newhost_two_edges_one_epoch_spawn` controls the two-click path: one TERM/start/spawn, parent9090 and child8080/seq2 persist.

Positive controls: live child/new host causes zero TERM/unlink/start; explicit direct child, explicit enumeration rc failure and stranger holder refuse; stop timeout holds without unlink/start; failed start holds against a second call. Successful synthetic transition updates parent in the current shell. These limited controls do not establish production assembly, actual exit, real socket safety or visual success.

## Acceptance and replay

`acceptance-matrix.json` separates warm return, cold child reentry and host recreation. Real user acceptance remains pending for **two cycles**: normal close -> real icon -> feed -> actual video card -> at least 20 seconds of changing video-content frames -> 3 seconds pause -> 10 seconds resumed dynamic content -> exit and reenter. Record monotonic times, screenshot SHA and identities. Progress bar/subtitle/overlay motion alone is insufficient. Agent-injected clicks and human observations have separate fields. Historical sound acceptance is preserved and will not be asked again.

```sh
python3 benchmark/2026-10-21-manual-video-regression/host-reentry-peer/test_peer.py
cargo test --manifest-path tools/spec-checks/Cargo.toml --test toutiao_host_reentry_peer
```

The test checks reproducibility of both positive and negative observations and honest scope. It must not be read as a safety PASS for T36. Candidate repair/replay and full payload pin/assembly review remain outstanding. Deployment and human video acceptance belong to the outer lane.

## Handoff status

Strict lifecycle: 3/3 scenarios plus boundary PASS; fresh explain: 3/3. These verify review evidence, not T36 acceptance. Landing preflight passed. Git staging was denied by the workspace sandbox (`index.lock`, rc128); no commit or push occurred. `ACK.md` is prepared for outer posting; the canonical board is absent here and outside the card paths. Structured lifecycle log is a path-normalized copy with raw SHA in `lifecycle-normalization.json`.

## Adaptive replay of author revision

At the second snapshot, author watchdog SHA became `9072bbfb032afc217ed01e369f3ce859b2c63e310e42815158780973f71391bc` (common unchanged). `candidate-02/pins.json` records it. The diff adds exact new-parent WID verification and explicit focus refusal reasons. The synthetic successful start now provides that requested WID, so the new production check executes. `candidate-replay-03/` reproduces all 16 observations again: eight controls and eight adverse observations. The blockers above remain; latest verdict is **request_changes**. Snapshot 01 and replay 01/02 remain historical evidence. Tests rehash and replay both snapshots.
