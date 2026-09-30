#!/usr/bin/env bash
# Run via dockbuild, or the same frozen scripts in VM only if outer authorizes.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
python3 "$REPO/scripts/lab/check_frozen.py" --source-root "$REPO"
bash "$HERE/build-flutter.sh" --anl-only
python3 "$HERE/build-host.py"
bash "$HERE/build-runtime.sh"
