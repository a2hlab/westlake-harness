#!/bin/bash
# Structured line-start notes on an OLP campaign board (the Markdown board stays the only source of truth).
# Every note goes through olp-board-append.sh (flock, append-only) and carries its own timestamp, so
# board_status.py --schedule can tell how fresh a lane is.
#
#   board_note.sh progress <board> <entry> <lane> <text...>
#       -> PROGRESS(<entry>): <iso-time> <lane> <text>
#   board_note.sh lock <board> <serial> <lane> [why...]
#       Takes ~/.octos/board-locks/<serial>.lock with `flock -n` in a detached holder process, then writes
#       LOCK(<serial>) <lane> <iso-time> <why>. Exit 75 and no board line when another lane holds it.
#       The holder lives until unlock (or 24 h), so the lock outlasts any single shell command.
#   board_note.sh unlock <board> <serial> <lane>
#       Kills this lane's holder and writes UNLOCK(<serial>) <lane> <iso-time>. Refuses another lane's lock.
#   board_note.sh held <serial>
#       Prints "<lane> <pid> <iso-time>" of the live holder, or nothing (exit 1).
#
# Serials are full connect-keys (e.g. 5ea34a4500000000000000001123012c) or the Android serial.
set -euo pipefail
APPEND=${OLP_BOARD_APPEND:-$HOME/workspace/octoscode/scripts/olp-board-append.sh}
LOCKS=${BOARD_LOCK_DIR:-$HOME/.octos/board-locks}
now() { date +%Y-%m-%dT%H:%M:%S%z; }
mkdir -p "$LOCKS"

holder() {  # holder <serial> -> "lane pid time" if the recorded holder process is alive
  local f="$LOCKS/$1.holder"
  [ -f "$f" ] || return 1
  local pid lane t
  read -r pid lane t < "$f" || return 1
  kill -0 "$pid" 2>/dev/null || return 1
  echo "$lane $pid $t"
}

cmd=${1:-}; shift || true
case "$cmd" in
  progress)
    [ $# -ge 4 ] || { echo "usage: board_note.sh progress <board> <entry> <lane> <text...>" >&2; exit 2; }
    board=$1 entry=$2 lane=$3; shift 3
    printf 'PROGRESS(%s): %s %s %s\n' "$entry" "$(now)" "$lane" "$*" | "$APPEND" "$board" ;;
  lock)
    [ $# -ge 3 ] || { echo "usage: board_note.sh lock <board> <serial> <lane> [why...]" >&2; exit 2; }
    board=$1 serial=$2 lane=$3; shift 3
    if h=$(holder "$serial"); then
      set -- $h; [ "$1" = "$lane" ] && { echo "already held by $lane (pid $2)"; exit 0; }
      echo "BUSY: $serial held by $1 (pid $2 since $3)" >&2; exit 75
    fi
    # The holder keeps the flock for as long as it lives; `flock -n` makes a second taker fail at once.
    nohup flock -n "$LOCKS/$serial.lock" sleep 86400 >/dev/null 2>&1 &
    pid=$!
    sleep 0.3
    kill -0 "$pid" 2>/dev/null || { echo "BUSY: $serial flock held outside board_note.sh" >&2; exit 75; }
    t=$(now)
    echo "$pid $lane $t" > "$LOCKS/$serial.holder"
    printf 'LOCK(%s) %s %s %s\n' "$serial" "$lane" "$t" "$*" | "$APPEND" "$board" ;;
  unlock)
    [ $# -eq 3 ] || { echo "usage: board_note.sh unlock <board> <serial> <lane>" >&2; exit 2; }
    board=$1 serial=$2 lane=$3
    if h=$(holder "$serial"); then
      set -- $h
      [ "$1" = "$lane" ] || { echo "REFUSE: $serial is held by $1, not $lane" >&2; exit 1; }
      pkill -P "$2" 2>/dev/null || true; kill "$2" 2>/dev/null || true
    fi
    rm -f "$LOCKS/$serial.holder"
    printf 'UNLOCK(%s) %s %s\n' "$serial" "$lane" "$(now)" | "$APPEND" "$board" ;;
  held)
    [ $# -eq 1 ] || { echo "usage: board_note.sh held <serial>" >&2; exit 2; }
    holder "$1" ;;
  *)
    sed -n '2,19p' "$0"; exit 2 ;;
esac
