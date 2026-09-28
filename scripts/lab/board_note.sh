#!/bin/bash
# Structured line-start notes on an OLP campaign board (the Markdown board stays the only source of truth).
# Every note goes through olp-board-append.sh (flock, append-only) and carries its own timestamp, so
# board_status.py --schedule can tell how fresh a lane is.
#
#   board_note.sh progress <board> <entry> <lane> <text...>
#       -> PROGRESS(<entry>): <iso-time> <lane> <text>
#   board_note.sh lock <board> <serial> <lane> [why...]
#       Takes ~/.octos/board-locks/<serial>.lock (non-blocking flock) in a holder that detaches into its own
#       session, then writes
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
    # The holder keeps the flock for as long as it lives. It double-forks into its own session, because
    # some agent harnesses (codex) kill a command's whole process group when the command returns.
    t=$(now)
    python3 - "$LOCKS/$serial.lock" "$LOCKS/$serial.holder" "$lane" "$t" <<'PY' || { echo "BUSY: $serial flock held outside board_note.sh" >&2; exit 75; }
import fcntl, os, sys, time
lock, holder, lane, t = sys.argv[1:5]
fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o644)
try:
    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(75)
r, w = os.pipe()
if os.fork():                      # caller: wait until the holder has recorded itself
    os.close(w); os.read(r, 1); os._exit(0)
os.setsid()
if os.fork():
    os._exit(0)
devnull = os.open(os.devnull, os.O_RDWR)
for n in (0, 1, 2):
    os.dup2(devnull, n)
with open(holder, "w") as f:
    f.write(f"{os.getpid()} {lane} {t}\n")
os.write(w, b"x"); os.close(w)
time.sleep(86400)
PY
    printf 'LOCK(%s) %s %s %s\n' "$serial" "$lane" "$t" "$*" | "$APPEND" "$board" ;;
  unlock)
    [ $# -eq 3 ] || { echo "usage: board_note.sh unlock <board> <serial> <lane>" >&2; exit 2; }
    board=$1 serial=$2 lane=$3
    if h=$(holder "$serial"); then
      set -- $h
      [ "$1" = "$lane" ] || { echo "REFUSE: $serial is held by $1, not $lane" >&2; exit 1; }
      pkill -P "$2" 2>/dev/null || true; kill "$2" 2>/dev/null || true
    fi
    # Anything of ours still holding the lock file goes too -- e.g. the `sleep` child of an old-style
    # `flock -n … sleep` holder, which survives when only its flock parent is killed.
    for p in $(lsof -t "$LOCKS/$serial.lock" 2>/dev/null); do
      case "$(ps -o command= -p "$p" 2>/dev/null)" in
        "sleep 86400"|flock\ -n\ *|*python3*) kill "$p" 2>/dev/null || true ;;
      esac
    done
    rm -f "$LOCKS/$serial.holder"
    printf 'UNLOCK(%s) %s %s\n' "$serial" "$lane" "$(now)" | "$APPEND" "$board" ;;
  held)
    [ $# -eq 1 ] || { echo "usage: board_note.sh held <serial>" >&2; exit 2; }
    holder "$1" ;;
  *)
    sed -n '2,19p' "$0"; exit 2 ;;
esac
