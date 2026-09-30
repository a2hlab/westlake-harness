#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
python3 "$HERE/stop_test_apps.py"
python3 "$HERE/jar_overlay.py" expose
"$REPO/scripts/lab/deploy_generation.sh" 61b0657200000000000000000324012c /Users/zhaoyue/orca/workspaces/westlake-generation-flutter-r5 --rollback --lane cx-t0
python3 "$HERE/jar_overlay.py" restore
bash "$HERE/run_controls.sh" flutter-r5-rollback-61b
