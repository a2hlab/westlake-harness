#!/bin/bash
# Outer-loop read cursor for a lane board, so no lane entry is skipped between two sentinels.
#
#   board_cursor.sh <absolute board.md> show      # lane entries after the cursor (cursor unchanged)
#   board_cursor.sh <absolute board.md> wait      # block until there is at least one, then print them
#   board_cursor.sh <absolute board.md> advance   # mark everything up to the current last line as read
#
# 2026-10-01 night: the outer loop re-armed a "new lines since now" sentinel after each notification, so entries
# written between the old sentinel firing and the new one starting were never shown; a lane's FZ-005 draft waited
# 75 minutes and two cx-bms deliveries (04:39, 05:02) were missed. The cursor only moves on `advance`, which the
# outer loop runs after it has read what `show`/`wait` printed. Lane entries = lines starting PROGRESS/ACK/LOCK/UNLOCK
# that are not the outer loop's own ("外环(claude)"). Cursor file: $OUTER_CURSOR_DIR (default ~/.octos/outer)/board-cursor-<hash>.
set -euo pipefail
BOARD=${1:?usage: board_cursor.sh <absolute board.md> show|wait|advance}; CMD=${2:?usage: board_cursor.sh <board> show|wait|advance}
case $BOARD in /*) ;; *) echo "board path must be absolute" >&2; exit 2;; esac
DIR=${OUTER_CURSOR_DIR:-$HOME/.octos/outer}; mkdir -p "$DIR"
CUR="$DIR/board-cursor-$(printf '%s' "$BOARD" | shasum -a 256 | cut -c1-12)"
[ -f "$CUR" ] || wc -l < "$BOARD" | tr -d ' ' > "$CUR"
# `advance` moves only to the last line that show/wait actually looked at (recorded in $CUR.seen), not to the end
# of the file: 05:26 an entry written between `wait` returning and `advance` running was skipped.
entries() {
  local end; end=$(wc -l < "$BOARD" | tr -d ' ')
  echo "$end" > "$CUR.seen"
  sed -n "$(( $(cat "$CUR") + 1 )),${end}p" "$BOARD" | grep -E '^(PROGRESS|ACK\(|LOCK|UNLOCK)' | grep -v '外环(claude)' || true
}
case $CMD in
  show) entries ;;
  wait) while :; do out=$(entries); [ -n "$out" ] && { printf '%s\n' "$out"; exit 0; }; sleep "${OUTER_CURSOR_POLL:-30}"; done ;;
  # advance names what it marks as read (06:56 an entry was skipped by `show >/dev/null; advance` inside a sentinel).
  advance) [ -f "$CUR.seen" ] || { echo "run show or wait first" >&2; exit 2; }
           n=$(sed -n "$(( $(cat "$CUR") + 1 )),$(cat "$CUR.seen")p" "$BOARD" | grep -E '^(PROGRESS|ACK\(|LOCK|UNLOCK)' | grep -vc '外环(claude)' || true)
           cp "$CUR.seen" "$CUR"; echo "cursor at line $(cat "$CUR") (marked $n lane entries read)" ;;
  *) echo "unknown command: $CMD" >&2; exit 2 ;;
esac
