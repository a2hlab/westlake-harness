#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
source "$ROOT/scripts/lab/lab_paths.sh"
cd "$ROOT"
python3 "$HERE/jar.py" expose > "$HERE/expose.log" 2>&1
# Shell trap restores J6 if activation fails before the planned restore.
trap 'python3 "$HERE/jar.py" restore >> "$HERE/restore-on-failure.log" 2>&1 || true' EXIT
scripts/lab/deploy_generation.sh 61b0657200000000000000000324012c "$ROOT/../westlake-generation-n8-private-zlib" --upgrade --native-experiment "$HERE/window.json" --lane cx-t0 > "$HERE/deploy.log" 2>&1
python3 "$HERE/jar.py" restore > "$HERE/restore.log" 2>&1
trap - EXIT
