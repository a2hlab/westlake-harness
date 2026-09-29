#!/usr/bin/env bash
set -euo pipefail
SERIAL=61b0657200000000000000000324012c
TOOLS=/Users/zhaoyue/orca/workspaces/westlake-inputs/tools
MASTER=/Users/zhaoyue/orca/workspaces/westlake-harness
OUT=/home/zhaoyue/a2hlab/board/b79-install-walls-r3-61b
mkdir -p "$OUT"
mac "$TOOLS/board_note.sh" held "$SERIAL" | grep '^cx-t0 ' >/dev/null
"$TOOLS/hdc_mac.sh" -t "$SERIAL" shell 'hilog -r' > "$OUT/hilog-clear.txt"
"$TOOLS/hdc_mac.sh" -t "$SERIAL" shell hilog > "$OUT/install-and-launch-hilog.txt" 2>&1 &
CAPTURE_PID=$!
cleanup() { kill "$CAPTURE_PID" 2>/dev/null || true; wait "$CAPTURE_PID" 2>/dev/null || true; }
trap cleanup EXIT
python3 "$MASTER/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py" --execute --serial "$SERIAL" --lane cx-t0 --keys x,toutiao,fd-seal --hdc-cmd "$TOOLS/hdc_mac.sh" --lock-cmd "mac $TOOLS/board_note.sh" --out "$OUT" --run-id b79-install-walls-r3-61b --reinstall --hilog 20 --wait 20
