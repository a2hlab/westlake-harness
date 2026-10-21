# Fixed W05 two-point input

Only the actual reviewed current-layout points (600,960) then (1120,1862), once each, via two original GuardedBoard.shell calls; one observation follows. No compound shell, no retries, no UI/runtime guard changes. All non-main functions are byte-identical to ui-01. Only action allowed is tap-pair; recovery mode rejects it. Coordinates are not configurable. Original session/pins/holder/boot/budget/power/receipts remain. No device operation. Three actual-main offline seam tests pass, including first failure preventing second action and observation. This does not prove live return success.

Command (fresh current W05 values only):
```sh
python3 "$REPO/benchmark/2026-10-21-t34-demo61b-video/tap-pair-01/ui.py" --repo "$REPO" --window "$W05_UI" --session "$FRESH_SESSION" --tag pair-return-01 --observe-seconds 0 tap-pair
```

Use a new unique tag, never retry an unknown attempt. Deadline uses the original holder start. Image review is required after the pair.
