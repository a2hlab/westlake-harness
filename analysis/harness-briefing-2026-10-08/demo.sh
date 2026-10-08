#!/bin/bash
# Three-minute offline demo for the harness briefing: read-only, no board, no VM.
#   bash demo.sh [<westlake-harness checkout>]      (default: $WORKSPACES/westlake-harness)
# Each step prints the command, then its real output on retained U14 stage-A evidence.
set -uo pipefail
REPO=${1:-}
if [ -z "$REPO" ]; then
  [ -n "${WORKSPACES:-}" ] || { echo "set WORKSPACES or pass the westlake-harness path" >&2; exit 2; }
  REPO=$WORKSPACES/westlake-harness
fi
. "$REPO/scripts/lab/lab_paths.sh" || exit 1
X=$WORKSPACES/westlake-harness-u7-executor/benchmark/2026-10-03-u14-stage-a-plan
ANKI=$X/window2/u14-A2-20261003T131427/5cd/runner/lit-regression-anki-1/20261003T140002-d08c1fa1
OM=$X/window6/u14-A6-20261003T182310/5cd
CONTROL=$OM/control-r2/runner/organicmaps/trial-1/batch/u13-5cd1e3dd-organicmaps-1791024470930018000
CANDIDATE=$OM/candidate/runner/organicmaps/trial-1/batch/u14-5cd1e3dd-organicmaps-1791026160404844000
cd "$REPO" || exit 1

step() { printf '\n\033[1m== %s\033[0m\n$ %s\n' "$1" "${*:2}"; "${@:2}"; }

step "1  An ACK may only quote this: counted from record.json, not from the plan" \
  python3 scripts/lab/run_facts.py "$ANKI"
step "2  Count the variables before naming a cause: U13 same-board control vs U14 candidate (OrganicMaps, 5cd)" \
  python3 scripts/lab/compare_runs.py "$CONTROL" "$CANDIDATE"
step "3  Frozen ratchet: every frozen source vs its git blob, every frozen artifact vs a run's deployed fingerprint" \
  python3 scripts/lab/check_frozen.py --git --fingerprint "$ANKI/5cd1e3dd00000000000000000923012c/runtime-fingerprint.txt"
