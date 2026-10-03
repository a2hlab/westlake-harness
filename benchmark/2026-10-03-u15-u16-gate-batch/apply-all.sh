#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
WORKSPACES=${WORKSPACES:-$(cd "$HERE/../../.." && pwd)}
export WORKSPACES
exec python3 "$HERE/apply_batch.py" --repo "$WORKSPACES/westlake-harness" --expected-plan-sha 8cf14d568c7f8b52a13c9a5d11120f213a25386a2698bad0dff44a07441dcc2a "$@"
