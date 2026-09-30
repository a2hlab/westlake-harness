#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
python3 /Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py --execute --serial 61b0657200000000000000000324012c --lane cx-t0 --hdc-cmd /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh --lock-cmd "mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh" --manifest "$HERE/../controls.json" --input-root /Users/zhaoyue/orca/workspaces/westlake-b90-controls-inputs --out "$HERE/runs" --run-id "$1" --launch-only --hilog 20 --shots 5,20 --focus-check
