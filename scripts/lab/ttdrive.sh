#!/bin/bash
# Drive and observe the app of one launcher run through the bridge's in-process tap channel
# (/data/local/tmp/noice_tap, which probe_source_app.py points at the latest child on that board).
# usage: ttdrive.sh <serial> <run dir in VM, holding device-report.json> <command> [args]
#   front            bring the host (and so the app's sub-windows) back to the foreground
#   vt               dump the view tree (rect/id/text/clickable) and print it
#   tap X Y          inject one click at window coordinates
#   consent          find the first-run consent dialog in the view tree and tap its agree button
#   shot NAME        screenshot to ~/.octos/outer/board/drive/NAME.jpeg
#   alive            child state and any faultlog for it
#   log [N]          last N lines of the child's log (default 40)
S=$1; RUN=$2; cmd=$3; shift 3
H=/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc
dev() { "$H" -t "$S" shell "$1" | LC_ALL=C tr -d '\r'; }
read -r child runtime < <(orb -m a2hlab bash -lc "python3 -c \"import json;r=json.load(open('$RUN/device-report.json'));print(r['child'],r['runtime'])\"")
LOG=$runtime/private-tmp/adapter_child_$child.stderr

case $cmd in
  front) dev 'power-shell wakeup >/dev/null; aa start -b org.westlake.imehost -a EntryAbility >/dev/null' ;;
  vt)
    n=$(dev "wc -l < $LOG")
    dev "echo v > /data/local/tmp/noice_tap"; sleep "${VT_WAIT:-6}"
    dev "tail -n +$((n + 1)) $LOG" | grep -E '^VT( |$)|OH_InputBridge. VT' ;;
  tap) dev "echo '$1 $2' > /data/local/tmp/noice_tap" ;;
  consent)
    # Every launch gets fresh app data, so the first-run consent dialog is back each time. Tap its agree
    # button inside the root that holds it (explicit rN: automatic root choice misses dialogs, see board #8).
    for round in 1 2; do
      pick=$("$0" "$S" "$RUN" vt | python3 -c '
import re, sys
sys.stdin.reconfigure(errors="replace")  # VT truncates long text mid-character
root = None
for line in sys.stdin:
    m = re.search(r"root\[(\d+)\]", line)
    if m: root = int(m.group(1)); continue
    t = re.search(r"rect=\[(\d+),(\d+) (\d+)x(\d+)\].*\"(同意|同意并继续)\"\s*$", line)
    if t and root is not None:
        x, y, w, h = map(int, t.groups()[:4]); print(root, x + w // 2, y + h // 2); break')
      [ -z "$pick" ] && { echo "consent: no agree button (round $round)"; break; }
      read -r r x y <<<"$pick"; echo "consent: root[$r] tap ($x,$y)"
      dev "echo r$r > /data/local/tmp/noice_tap; sleep 1; echo '$x $y' > /data/local/tmp/noice_tap; sleep 1; echo r-1 > /data/local/tmp/noice_tap"
      sleep 3
    done ;;
  shot)
    mkdir -p ~/.octos/outer/board/drive
    dev "snapshot_display -f /data/local/tmp/drive.jpeg >/dev/null"
    "$H" -t "$S" file recv /data/local/tmp/drive.jpeg ~/.octos/outer/board/drive/"$1".jpeg >/dev/null
    echo ~/.octos/outer/board/drive/"$1".jpeg ;;
  alive) dev "[ -d /proc/$child ] && echo 'alive $child' || echo 'dead $child'; ls /data/log/faultlog/temp/ | grep -- '-$child-'" ;;
  log) dev "tail -n ${1:-40} $LOG" ;;
  *) echo "unknown command $cmd" >&2; exit 2 ;;
esac
