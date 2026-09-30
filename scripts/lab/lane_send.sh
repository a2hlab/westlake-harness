#!/bin/bash
# Send a dispatch to a lane pane and make sure the lane actually picked it up.
#
#   lane_send.sh [--wait-max S] <pane-id> <text>
#
# octoscode drops text sent while a turn is running (RUNBOOK; 2026-10-01 oc-t4 lost two dispatches in one
# night: the outer loop sent, saw no error, and the lane later reported "no remaining work"). For an
# octoscode pane this waits until the status line shows Idle/Done (up to --wait-max seconds, default 900),
# sends, then checks within 20 s that the lane left Idle; if it did not, it sends once more. Leaving Idle only
# proves a turn started (2026-10-01 04:24 a lane opened a turn and only summarised its previous task): name the
# expected output file in the dispatch and check that it appears.
# Codex and Claude panes queue input while busy, so they are sent to directly.
# Exit 0 = sent and picked up (or sent to a queueing pane); 1 = never became idle; 2 = sent twice, no pickup.
set -euo pipefail
WAIT_MAX=900
[ "${1:-}" = --wait-max ] && { WAIT_MAX=$2; shift 2; }
PANE=${1:?usage: lane_send.sh [--wait-max S] <pane-id> <text>}; shift
TEXT=${*:?usage: lane_send.sh [--wait-max S] <pane-id> <text>}

status() { herdr pane read "$PANE" 2>/dev/null | grep -E 'state [^|]*\|' | tail -1; }
is_octos() { herdr pane read "$PANE" 2>/dev/null | grep -q 'Ask Octos'; }
idle() { status | grep -qE 'state (· Idle|✓ Done)'; }

if ! is_octos; then
  herdr pane run "$PANE" "$TEXT" >/dev/null
  sleep 3
  # 2026-10-01: dispatches to busy Claude lanes sat queued for 10-20 min behind a long turn (cc-t3 03:14, cc-wiki
  # 05:16) while boards stood idle. Say so, so an urgent dispatch can interrupt (Escape) and resend.
  if herdr pane read "$PANE" 2>/dev/null | grep -q 'queued messages'; then
    echo "lane_send: $PANE is busy; the dispatch is QUEUED behind the running turn (Escape + resend if urgent)"
  else
    echo "lane_send: $PANE is not an octoscode pane; sent"
  fi
  exit 0
fi
waited=0
until idle; do
  [ "$waited" -ge "$WAIT_MAX" ] && { echo "lane_send: $PANE not idle after ${WAIT_MAX}s: $(status)" >&2; exit 1; }
  sleep 15; waited=$((waited + 15))
done
for attempt in 1 2; do
  herdr pane run "$PANE" "$TEXT" >/dev/null
  for _ in 1 2 3 4; do
    sleep 5
    idle || { echo "lane_send: $PANE picked up the dispatch (attempt $attempt, waited ${waited}s): $(status)"; exit 0; }
  done
done
echo "lane_send: $PANE still idle after two sends: $(status)" >&2
exit 2
