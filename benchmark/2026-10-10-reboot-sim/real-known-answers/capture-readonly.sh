#!/bin/bash
set -eu
: "${WORKSPACES:=$HOME/orca/workspaces}"
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SERIAL=${1:?serial required}
case "$SERIAL" in
  5cd1e3dd00000000000000000923012c|5ea34a4500000000000000001123012c) ;;
  *) printf 'REFUSE: healthy spare-board serial required\n' >&2; exit 2 ;;
esac
OUT="$HOME/a2hlab-provision/t2e-inputs/$SERIAL/recursive-$(date +%Y%m%dT%H%M%S)-$$"
printf 'READONLY_OUT=%s\n' "$OUT"
python3 "$WORKSPACES/westlake-harness/scripts/lab/board_state_snapshot.py" "$SERIAL" \
  --plan "$HERE/capture-scope-plan.json" --label t2e-observed-label-scope --out "$OUT"
shasum -a 256 "$OUT/snapshot.json" "$HERE/capture-scope-plan.json"
printf 'This plan covers declared label scopes only; it is not a reboot recovery plan.\n'
