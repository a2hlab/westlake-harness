#!/bin/bash
# Dashboard for an OLP campaign board: the --schedule view (lanes, progress age, tasks, free devices,
# anomalies) plus the newest board lines. Read-only.
#   board_dash.sh [board.md] [--tail N] [--loop SECONDS] [--stale-min M]
# Default board: the app-lighting campaign board.
set -u
HERE=$(cd "$(dirname "$0")" && pwd)
. "$HERE/lab_paths.sh" || exit 1
BOARD=$WORKSPACES/westlake-harness/.octos/boards/app-lighting.md
TAIL=20 LOOP=0 STALE=30
while [ $# -gt 0 ]; do
  case "$1" in
    --tail) TAIL=$2; shift 2 ;;
    --loop) LOOP=$2; shift 2 ;;
    --stale-min) STALE=$2; shift 2 ;;
    *) BOARD=$1; shift ;;
  esac
done
show() {
  python3 "$HERE/board_status.py" "$BOARD" --schedule --text --stale-min "$STALE"
  echo "-- newest $TAIL board lines"
  tail -n "$TAIL" "$BOARD" | cut -c1-200
}
if [ "$LOOP" = 0 ]; then show; exit; fi
while true; do clear; show; sleep "$LOOP"; done
