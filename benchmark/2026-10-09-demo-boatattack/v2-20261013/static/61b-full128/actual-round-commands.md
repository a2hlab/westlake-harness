# Actual 61b full128 observation handoff

Preparation only: eight window plans select exactly 128 unique reference keys; nine existing reference/tool SHA pins match. No runner directories existed at preparation. Wait for the outer start message, then observe only these canonical shards. Existing collector/index remain unchanged. No device calls or human admission signatures.

## Per-window file-only command

```sh
export WORKSPACES="${WORKSPACES:-$HOME/orca/workspaces}"
OBSERVER="$WORKSPACES/westlake-harness-bms/benchmark/2026-10-09-demo-boatattack/v2-20261013/static/61b-full128"
ROUND="$WORKSPACES/westlake-harness-t0/benchmark/2026-10-14-final61b-next-binding/actual-running-086db6c7/identity128/round"
WINDOW=window-01
python3 "$OBSERVER/collect_window.py" --plan "$ROUND/$WINDOW/plan.json" --runner "$ROUND/$WINDOW/runner" --out "$OBSERVER/.artifacts/packets/$WINDOW"
```

Before running, check that each finished canonical record has its sibling serial-level facts.txt. Missing facts means pending output arrival, not an app regression; defer that collection. Smoke controls and unrelated install/Boat/Toutiao evidence never enter the 128 count. Plan hashes in actual-round-ready.json are preparation snapshots, not proof that execution has started; record the actual plan SHA from each packet.

Personally inspect actual t5/t10/t20 images against the index's signed, R4 and R6 references. Preserve loading, NOT_LIT, empty-content and foreground_unconfirmed independently of process survival. Verify first-fatal ownership against the actual record PID. On the first definite old-lit regression, send the key, actual image path/SHA, reference image path/SHA and own-PID fatal or unknown cause immediately, without waiting for all windows. Snotz/Toodoo's earlier scoped startup disposition is not a new content-function guarantee.

Keep packets and incremental visual reviews under this directory's .artifacts; do not overwrite old image verdicts or sign for the outer reviewer. No HDC/VM/SSH or changes to drivers, runtime, apps or data. Root alone owns device operation.
