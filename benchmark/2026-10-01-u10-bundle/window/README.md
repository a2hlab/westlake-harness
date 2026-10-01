# U10 three-board window proposal

APPROVED: outer ACK(90) 2026-10-01T22:52:00 authorized three parallel windows after native admission `eea0e3acc`.

Promoted bundle SHA `11adfff7fef79c9a52c60bacdcb5464718ca9992296ccf75829b5dcb605fc31c` (prior candidate `15b1f2a47425`); native manifest `3f5bee161d31`; JAR `37465d6d`. The approved promotion changes only rollout metadata, not payload, native manifest, sources or either expected fingerprint. The hook rejects a non-ready or drifted bundle. Production admission is rerun before execution.

## Per-board plans

- `plan-5ea.json`: 55 keys = original 21 + cv2 34, expected runtime `fe5d9e139746`.
- `plan-5cd.json`: 55 = 22 + 33, runtime `fe5d9e139746`.
- `plan-61b.json`: 56 = 23 + 33, runtime `519148f0f41a`.

The assignment is exactly cc-t3's accepted 55/55/56; all 166 unique keys match the original+cv2 manifest union. Each key retains its U9 board for comparison. Per-board predictions CSVs are exact subsets of `benchmark/2026-10-01-u10-prediction/predictions-v4.csv`. In each board one batch runs at a time; the three boards can run concurrently. Use the master runner with `--detach` and a new `U10_RUN_ID` for every attempt. `LAB_HOME` must name the existing remote tool location; it is not written into the scripts.

```sh
export U10_RUN_ID=<new-id>
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_run.py"   "$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-01-u10-bundle/window/plan-5ea.json" --detach
```

## Gates and restoration

`after_lock` requires the immutable approved bundle and rollout-ready flag, verifies signed U9's 318 assertions before writing, then uses `u7_executor`'s stopped-parent transaction. Smoke pins the actual host, U9 child, both aliases of compat/policy, retained runtime/bridge and JAR/stubs. NativeLoader policy is compiled into `libnativeloader.so`; no policy JSON exists in this payload, so no fictional JSON target is added. Marker `[U10-COMPAT-VISIBLE] inherit_requested` proves the optional host site executed; it does not claim application symbol resolution. ART/JVM require one mapping; bridge/runtime retain U9's two existing mappings.

`before_unlock` retains U10 when activation smoke passed and no regression was confirmed. Retention requires 318 identity assertions, the exact candidate fingerprints and the parent view/executable. This is pending full-sweep outer review, not a final UI verdict. A confirmed regression is recorded in the board window `confirmed-regression.json` as `confirmed:true`. Smoke FAIL, confirmed regression or a final identity gate failure instead rolls back U9. A verified automatic rollback is not run twice. Then require 318 identity assertions, per-board U9 fingerprints (`565fc6fdc116` for 5ea/5cd, `a2919b793eb6` for 61b, boot `4db882a81732`), restored HW/ZZ live t20 and screenshots, followed by one more byte-identity verification. Nonzero hook status leaves the lock held for recovery. Every recovery/rollback attempt gets a new output directory. Three offline hook tests verify recovery ordering, failure fencing and no duplicate rollback.

## Time budget for outer review

Each lock window is limited to 45 minutes, including recovery. The master deadline patch `d614c7d0a` enforces the minute-35 new-key cutoff across both shards: it passes one absolute epoch based on lock time; batch checks only at key boundaries, finishes the in-flight key, and records unrun keys as `not_run`/unknown. No interrupted APK installation is used to enforce this cutoff. Ten minutes remain for final verification or recovery. Unrun keys use follow-up windows without redeploying retained U10. No extension is implied.

Compare actual first walls/screenshots with predictions-v4 and U9 same-board records using the current `compare_runs.py`; an isolated flaky failure needs repeated samples, not an immediate regression claim. Quote facts verbatim; outer reads screenshots. Activation mismatch stops that board before shards and triggers the same strict restoration.
