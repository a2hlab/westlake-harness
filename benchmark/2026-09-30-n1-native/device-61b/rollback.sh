#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../../.." && pwd)
SERIAL=61b0657200000000000000000324012c
python3 "$HERE/stop_test_apps.py"
python3 "$HERE/jar_overlay.py" expose
if [[ ${1:-} == full ]]; then
  "$REPO/scripts/lab/deploy_generation.sh" "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-generation-n1-aa57845c --rollback --lane cx-t0
elif [[ ${1:-} != runtime ]]; then
  echo 'Specify full or runtime based on the live deployment ledger' >&2
  exit 2
fi
"$REPO/scripts/lab/deploy_generation.sh" "$SERIAL" /Users/zhaoyue/orca/workspaces/westlake-n1-runtime-d40ae63f --replace /system/android/lib64/liboh_android_runtime.so --rollback --lane cx-t0
python3 "$HERE/jar_overlay.py" restore
