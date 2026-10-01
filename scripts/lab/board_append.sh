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
# 2026-09-30, twice in one evening (oc-t4 22:10, the outer loop 22:08): an entry carried a hand-written time
# minutes in the future. Refuse a first-line ISO timestamp more than 60 s ahead of the clock; take it from date.
AHEAD=$(printf '%s' "$FIRST" | python3 -c '
import re, sys, time
from datetime import datetime
m = re.search(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2})?([+-]\d{2}:?\d{2})?", sys.stdin.read())
if m:
    s = m.group(0) if m.group(1) else m.group(0)[:16] + ":00" + m.group(0)[16:]
    t = datetime.fromisoformat(s)
    t = t.timestamp() if t.tzinfo else time.mktime(t.timetuple())
    print(int(t - time.time()))
else:
    print(0)')
[ "$AHEAD" -le 60 ] || { echo "REFUSE: entry time is ${AHEAD}s in the future; write it with \$(date +%Y-%m-%dT%H:%M:%S%z)" >&2; exit 2; }
# EVO-0033..0036 (same disease, 5th time on 2026-09-30): an adoption ("采认") restated a lane's inference without
# naming the object it was checked against. Warn when an adopting entry carries no evidence anchor (a hash of
# >= 7 hex digits or a file path); the entry is still appended. A rejection ("未采认"/"不采认") adopts nothing.
if printf '%s' "$BODY" | sed -E 's/(未|不)采认//g' | grep '采认' >/dev/null && ! printf '%s' "$BODY" | grep -E '[0-9a-f]{7,}|/[A-Za-z0-9._-]+/[A-Za-z0-9._/-]+' >/dev/null; then
  echo "WARN: 采认 without an evidence anchor (hash or path of the object it was checked against) -- EVO-0036" >&2
fi
# EVO-0049 (2026-10-01 06:25/06:31): two outer ACKs cited "外环 06:0x 5ea 签认", a sign-off that existed only in the
# outer loop's private notes; a lane then copied the wrong shard's sign-off. Warn on a wildcard time ("06:0x") and on
# a cited HH:MM:SS that no board line carries (typo'd or never published); hilog times (HH:MM:SS.mmm) are skipped.
# The entry is still appended.
printf '%s' "$BODY" | python3 -c '
import re, sys
body, board = sys.stdin.read(), open(sys.argv[1], errors="replace").read()
for w in sorted(set(re.findall(r"\b\d{2}:\d?x\b", body))):
    print(f"WARN: wildcard time {w} cited -- cite the board line with its exact timestamp (EVO-0049)", file=sys.stderr)
own = set(re.findall(r"T(\d{2}:\d{2}:\d{2})", body.splitlines()[0] if body else ""))
# only times cited as board entries (07:32: hilog times without milliseconds were flagged)
cited = {m.group(2) for m in re.finditer(r"(ACK|PROGRESS|签认|采认|黑板|那条|LOCK)[^\n]{0,24}?(?<![\d:T])(\d{2}:\d{2}:\d{2})(?![\d:.])", body)}
for t in sorted(cited - own):
    if "T" + t not in board:
        print(f"WARN: cited time {t} is not on the board (never published, or a typo) (EVO-0049)", file=sys.stderr)
' "$BOARD"
# EVO-0051 (2026-10-01 06:58): a hard spot-check gate included noice, a two-Activity race key that flips lit/white;
# it went white, the 61b persistence window rolled back. Warn when an entry that sets a gate (抽检/硬门/门槛/gate)
# names a key registered in knowledge/gates/flaky-keys.json; flaky keys get repeated runs and a rate, not a gate.
FLAKY="$(cd "$(dirname "$0")/../.." && pwd)/knowledge/gates/flaky-keys.json"
[ -f "$FLAKY" ] && printf '%s' "$BODY" | python3 -c '
import json, re, sys
body = sys.stdin.read()
if re.search(r"抽检|硬门|门槛|\bgate\b", body):
    keys = [k["key"] for k in json.load(open(sys.argv[1])).get("keys", [])]
    hit = [k for k in keys if re.search(r"(?<![\w-])" + re.escape(k) + r"(?![\w-])", body)]
    if hit:
        print("WARN: gate entry names flaky key(s) " + ", ".join(hit) + " (knowledge/gates/flaky-keys.json) -- use repeats and a rate, not a single-run gate (EVO-0051)", file=sys.stderr)
' "$FLAKY"
printf '%s\n' "$BODY" | "$APPEND" "$BOARD"
if tail -n 400 "$BOARD" | grep -F -- "$FIRST" >/dev/null; then  # no -q under pipefail (RUNBOOK)
  echo "appended: ${FIRST:0:100}"
else
  echo "FAILED: entry not found on the board after append: ${FIRST:0:100}" >&2; exit 1
fi
