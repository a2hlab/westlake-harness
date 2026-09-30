#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
cd "$ROOT"
python3 "$HERE/jar.py" expose > "$HERE/rollback-expose.log" 2>&1
trap 'python3 "$HERE/jar.py" restore >> "$HERE/rollback-restore-on-failure.log" 2>&1 || true' EXIT
scripts/lab/deploy_generation.sh 61b0657200000000000000000324012c "$ROOT/../westlake-generation-n7-fa9ec3c6" --rollback --rollback-state "$(cat "$HERE/state-path.txt")" --native-experiment "$HERE/window.json" --lane cx-t0 > "$HERE/rollback.log" 2>&1
python3 "$HERE/jar.py" restore > "$HERE/rollback-restore.log" 2>&1
trap - EXIT
python3 "$HERE/jar.py" final > "$HERE/final.log" 2>&1
