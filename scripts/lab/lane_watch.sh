#!/usr/bin/env python3
"""Negative-signal sentinel for inner-loop panes (the name keeps the .sh the outer loop already calls).

Exit as soon as any watched herdr pane has been idle/blocked/done -- or lost its agent -- on two consecutive
polls, printing which one and its screen tail. Two polls filter the momentary idle between turns.
herdr reports an octoscode pane as done while it still runs a background task, so a stop also needs the
pane's own status line to say it is not working.
  lane_watch.sh [--interval S] <pane-id>...
"""
import json, re, subprocess, sys, time

# status lines of a pane that is still busy: octoscode "state ✧ Working|Orchestrating|Thinking", codex "• Working (",
# claude between turns while its own background job runs "· 1 shell still running" (it resumes when the job ends)
BUSY = re.compile(r"^\s*state\s+\S+\s+(Working|Orchestrating|Thinking)|^\s*• Working \(|\d+ shells? still running", re.M)

# octoscode's own status line when its octos serve session broke (connection_closed, cursor_expired,
# session_open_rejected): herdr may still report the pane idle or working, so it is checked separately
ERRORED = re.compile(r"^\s*state\s+x\s+Error", re.M)

# a pane that stopped because its model/API connection broke looks "done"/"idle" to herdr but did not finish its
# task: claude "API Error: Connection dropped|lost", codex "Error running remote compact task: Connection failed",
# octoscode "Turn error runtime_error". Reported as "interrupted" so the outer loop resumes it instead of waiting
# for an ACK that will never come (2026-09-30: five such stops in one night, each found only by reading the pane).
INTERRUPTED = re.compile(r"API Error: Connection|Connection lost mid-response|Error running remote .{0,40}Connection"
                         r"|Turn error runtime_error|failed to send streaming")


def classify(status, tail):
    """herdr status + screen tail -> one of working/idle/blocked/done/gone/session-error/interrupted."""
    if status == "gone":
        return "gone"
    if ERRORED.search(tail):
        return "session-error"
    if status in ("idle", "done") and BUSY.search(tail):
        return "working"
    if status in ("idle", "done") and INTERRUPTED.search(tail):
        return "interrupted"
    return status


def tail_of(pane):
    out = subprocess.run(["herdr", "pane", "read", pane], capture_output=True, text=True).stdout
    return "\n".join(out.splitlines()[-12:])

def busy(pane):
    return bool(BUSY.search(tail_of(pane)))

def main(args):
    interval = 20
    if args[:1] == ["--interval"]:
        interval, args = float(args[1]), args[2:]
    seen = set()
    while True:
        try:
            out = subprocess.run(["herdr", "agent", "list"], capture_output=True, text=True, timeout=30).stdout
            agents = {a["pane_id"]: a.get("status") or a.get("agent_status") for a in json.loads(out)["result"]["agents"]}
        except Exception:
            time.sleep(interval)
            continue
        for pane in args:
            st = agents.get(pane, "gone")
            st = classify(st, tail_of(pane)) if st != "gone" else st
            if st in ("idle", "blocked", "done", "gone", "session-error", "interrupted"):
                if pane in seen:
                    print(f"LANE-STOPPED {pane} {st} {time.strftime('%H:%M:%S')}", flush=True)
                    tail = subprocess.run(["herdr", "pane", "read", pane], capture_output=True, text=True).stdout
                    print("\n".join(tail.splitlines()[-25:]))
                    sys.exit(0)
                seen.add(pane)
            else:
                seen.discard(pane)
        time.sleep(interval)


if __name__ == "__main__":
    main(sys.argv[1:])
