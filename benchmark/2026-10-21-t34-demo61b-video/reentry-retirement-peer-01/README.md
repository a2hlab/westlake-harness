# T34 confirmed-child retirement: independent host peer

The deployed R2 guardian retained an active child identity after a strict exit. Both actual `monitor_child` exit branches then caused a later same-PID/new-birth sample to fail `rc_gates_ok`. The R2 replay preserves that failure; it does not identify the historical uptime 7024 process.

R3 source `8bf74a08b71474e39e90fcdb012eed5e420f7352fa131cef2aa63b9c5bd80ef9` passes **13 core + 8 loop/lifecycle cases** independently. Acceptance is **offline source scope only**. R2 has 13 baseline cases. No device operation, deployment, feed, video, or historical crash-cause claim is made.

The tests extract actual source functions. OH/process observations are host seams; production monitor, retirement mutation, gate, WMS parser, reentry loop, spawn result classification, child/birth/sequence assignments, and main adoption branch execute unchanged. A successful spawn is not replaced with a fake `rc_do_spawn` result. The test observes real assignments of child 8080, birth 222, and sequence 2 in the caller shell.

Checks preserve parent/boot/lock rejection, unretired identity rejection, tuple mismatch, unknown exit, STOP/poll-limit semantics, old/other/unknown windows, pre-spawn refusal retaining the retirement key, one spawn per qualified edge, unknown-spawn hold, and active-child guards after spawn/adopt. The diff adds no signal or lock deletion. Current `AWAITING_REENTRY` file content alone does not prove a living guardian: the fresh read shows guardian absent.

## Reproduce offline

From this directory, use exact pinned source inputs in an existing checkout:

```sh
python3 replay.py --source snapshot-r3-01.sh --out NEW-core-output --expect r3
python3 replay_edges.py --source snapshot-r3-01.sh --common "$MAIN/benchmark/2026-10-19-toutiao-icon-reentry/src/reentry-common.sh" --parser "$MAIN/benchmark/2026-10-19-toutiao-icon-reentry/src/reentry-seams.sh" --out NEW-edge-output
```

Set `MAIN` to the checkout holding the pinned common/parser files. Each output directory must be new. The R2 comparison uses its original watchdog source and `--expect r2`. Receipts preserve actual `sh` argv, stdout, stderr, rc, generated script hashes, and source pins. Full generated scripts remain in the peer worktree run directories; the generator and frozen source reproduce them. The early local R2 argv-alias attempt is excluded, explicitly recorded in results, and not overwritten.

Source contract: `specs/demo61b-video-delivery/t3-confirmed-child-retirement.spec.md`, commit `115ad5931c`. Baseline source and deployed SHA agree. R3 source hash was checked again after both independent runs; source-directory WIP status is not promoted to an author freeze.
