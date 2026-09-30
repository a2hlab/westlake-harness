#!/bin/bash
# Append one entry to an OLP board and prove it landed (EVO-0034).
#
#   board_append.sh <absolute board.md> [text...]      # body = the arguments, or stdin when there are none
#
# octoscode's olp-board-append.sh reads the body from stdin only: body text passed as arguments is
# ignored and it appends nothing with exit 0, which let the outer loop report a sign-off that was never
# written. This wrapper refuses an empty body or a relative board path, appends through
# olp-board-append.sh (same flock), then reads the board back and exits 1 unless the entry's first line
# is there.
set -euo pipefail
BOARD=${1:?usage: board_append.sh <absolute board.md> [text...]}; shift
APPEND=${OLP_BOARD_APPEND:-$HOME/workspace/octoscode/scripts/olp-board-append.sh}
case $BOARD in /*) ;; *) echo "REFUSE: board path must be absolute: $BOARD" >&2; exit 2;; esac
[ -f "$BOARD" ] || { echo "REFUSE: no board at $BOARD" >&2; exit 2; }
if [ $# -gt 0 ]; then BODY="$*"; else BODY=$(cat); fi
FIRST=$(printf '%s\n' "$BODY" | grep -m1 -v '^[[:space:]]*$' || true)
[ -n "$FIRST" ] || { echo "REFUSE: empty body, nothing appended" >&2; exit 2; }
printf '%s\n' "$BODY" | "$APPEND" "$BOARD"
if tail -n 400 "$BOARD" | grep -qF -- "$FIRST"; then
  echo "appended: ${FIRST:0:100}"
else
  echo "FAILED: entry not found on the board after append: ${FIRST:0:100}" >&2; exit 1
fi
