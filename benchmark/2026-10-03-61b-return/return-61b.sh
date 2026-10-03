#!/usr/bin/env bash
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
export WORKSPACES=${WORKSPACES:-$(cd "$HERE/../../.." && pwd)}
exec python3 "$HERE/return_61b.py" "$@"
