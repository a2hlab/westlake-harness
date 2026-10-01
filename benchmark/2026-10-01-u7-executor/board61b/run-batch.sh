#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
. "$repo/scripts/lab/lab_paths.sh"
serial=61b0657200000000000000000324012c
name=$1
shift
export MAC_HOME="${MAC_HOME:-$(mac sh -c 'echo "$HOME"')}"
python3 "$WORKSPACES/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py" \
 --execute --serial "$serial" --lane cx-t0 \
 --hdc-cmd "$WORKSPACES/westlake-inputs/tools/hdc_mac.sh" \
 --lock-cmd "mac $WORKSPACES/westlake-inputs/tools/board_note.sh" \
 --run-id "u7-executor-61b-$name" --out "$repo/benchmark/2026-10-01-u7-executor/board61b/runs/$name" \
 --hilog 20 --shots 5,20 --focus-check "$@"
