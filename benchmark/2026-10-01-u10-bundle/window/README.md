# U10 three-board window proposal

DRAFT: no board access is authorized by these files. Outer review requested this proposal after native admission `eea0e3acc`.

Candidate bundle SHA `15b1f2a474253bc4ef1e7933e75771538944e93d2bc10c61377db483097df597`; native manifest `3f5bee161d31`; JAR `37465d6d`. All production checks pass; bundle rollout-ready is deliberately false. Approval must promote the same payload and update `composition.json` to the resulting bundle SHA before executing; the hook rejects a non-ready or drifted bundle. No automatic promotion occurs here.

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

`before_unlock` always rolls back U9, even if every shard passes; no U10 retention. A verified automatic rollback is not run twice. Then require 318 identity assertions, per-board U9 fingerprints (`565fc6fdc116` for 5ea/5cd, `a2919b793eb6` for 61b, boot `4db882a81732`), restored HW/ZZ live t20 and screenshots, followed by one more byte-identity verification. Nonzero hook status leaves the lock held for recovery. Every recovery/rollback attempt gets a new output directory. Three offline hook tests verify recovery ordering, failure fencing and no duplicate rollback.

## Time budget for outer review

Each lock window is limited to 45 minutes, including rollback and recovery smoke. Stop adding tests by minute 35 and reserve ten minutes for restoration. The `window_limit_minutes`/`stop_new_tests_by_minute` fields are scheduling metadata, not enforced by current `board_run`; its runner has no deadline-aware per-key scheduler. The owner must monitor the detached logs against the lock timestamp and end testing before the reserve. The draft does not promise all 55/56 keys fit: any unrun keys are `unknown` and move to a later approved window. No extension or partial retention is implied. This limitation must be accounted for when approving the plans.

Compare actual first walls/screenshots with predictions-v4 and U9 same-board records using the current `compare_runs.py`; an isolated flaky failure needs repeated samples, not an immediate regression claim. Quote facts verbatim; outer reads screenshots. Activation mismatch stops that board before shards and triggers the same strict restoration.
