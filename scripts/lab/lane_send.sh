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
  # 05:16) while boards stood idle. Say so, so an urgent dispatch can interrupt (Escape) and resend. A queued
  # message is delivered but shown only partly, so it is not probed (06:57 the probe resent a queued dispatch).
  # Claude shows "queued messages"; codex shows "Messages to be submitted after next tool call" / "Queued follow-up
  # inputs" with the text cut short (07:35 the probe missed that and a codex dispatch went in twice).
  if herdr pane read "$PANE" 2>/dev/null | grep -qE 'queued messages|Messages to be submitted after next tool call|Queued follow-up inputs'; then
    echo "lane_send: $PANE is busy; the dispatch is QUEUED behind the running turn (Escape + resend if urgent)"
    exit 0
  fi
  # 2026-10-01 06:50: a dispatch to a codex pane that was just finishing its turn never reached the session
  # (the pane showed only its idle prompt). Check that the text is on screen; resend once if not.
  # Compare the LAST 12 non-space characters (dispatches share their opening words) with all whitespace
  # removed from the screen: the TUI wraps and indents long input. herdr keeps only about a screen of history, so
  # this runs 3 s after sending, while the typed text is still above the composer.
  # 2026-10-02 10:51 / 11:01: a just-restarted Claude lane took the dispatch, collapsed it to "[Pasted text #1 +N
  # lines]" and started working; the tail probe found nothing and resent (exit 2, "no pickup") although the session
  # transcript held exactly one copy. A Claude/codex agent that left idle for "working" has picked it up: ask herdr
  # before resending.
  on_screen() { herdr pane read "$PANE" 2>/dev/null | python3 -c '
import sys; probe = "".join(sys.argv[1].split())[-12:]; screen = sys.stdin.read()
sys.exit(0 if probe in "".join(screen.split()) or "[Pasted text" in screen else 1)' "$TEXT"; }
  working() { herdr agent list 2>/dev/null | python3 -c '
import json, sys
agents = json.load(sys.stdin)["result"]["agents"]
sys.exit(0 if any(a.get("pane_id") == sys.argv[1] and a.get("agent_status") == "working" for a in agents) else 1)' "$PANE"; }
  if ! on_screen && working; then
    echo "lane_send: $PANE picked up the dispatch (agent working; text collapsed or scrolled)"
    exit 0
  fi
  if ! on_screen; then
    herdr pane run "$PANE" "$TEXT" >/dev/null
    sleep 3
    on_screen || { echo "lane_send: $PANE does not show the dispatch after two sends" >&2; exit 2; }
    echo "lane_send: $PANE needed a resend"
    exit 0
  fi
  echo "lane_send: $PANE is not an octoscode pane; sent"
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
