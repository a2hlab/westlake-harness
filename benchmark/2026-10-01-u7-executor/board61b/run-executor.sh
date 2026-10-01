#!/usr/bin/env bash
set -euo pipefail
repo=$(cd "$(dirname "$0")/../../.." && pwd)
cd "$repo"
export PATH="$repo/benchmark/2026-10-01-u7-executor/.vm-tools:$PATH"
export TMPDIR="$repo/benchmark/2026-10-01-u7-executor/.vm-tmp"
export LAB_HOME="${LAB_HOME:?set remote lab home}"
export NATIVE_READELF=/usr/bin/readelf
export MAC_HOME="${MAC_HOME:-$(mac sh -c 'echo "$HOME"')}"
exec python3 scripts/lab/u7_executor.py "$@"
