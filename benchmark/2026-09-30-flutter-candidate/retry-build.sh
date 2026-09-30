#!/usr/bin/env bash
# Prepared command only: the authorized two attempts are exhausted.
# Run only after outer grants another build window.
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
REPO=$(cd "$HERE/../.." && pwd)
PACKAGE=$(cd "$REPO/../westlake-generation-v3c-candidate" && pwd)
cd "$REPO"
export DOCKBUILD_MOUNTS="$REPO:$PACKAGE"
exec /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/dockbuild.sh run \
  -n flutter-candidate-expanded-retry -- bash "$HERE/build.sh"
