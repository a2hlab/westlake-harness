#!/usr/bin/env python3
"""Negative-signal sentinel for inner-loop panes (the name keeps the .sh the outer loop already calls).

Exit as soon as any watched herdr pane has been idle/blocked/done -- or lost its agent -- on two consecutive
polls, printing which one and its screen tail. Two polls filter the momentary idle between turns.
  lane_watch.sh [--interval S] <pane-id>...
"""
import json, subprocess, sys, time

args = sys.argv[1:]
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
        if st in ("idle", "blocked", "done", "gone"):
            if pane in seen:
                print(f"LANE-STOPPED {pane} {st} {time.strftime('%H:%M:%S')}", flush=True)
                tail = subprocess.run(["herdr", "pane", "read", pane], capture_output=True, text=True).stdout
                print("\n".join(tail.splitlines()[-25:]))
                sys.exit(0)
            seen.add(pane)
        else:
            seen.discard(pane)
    time.sleep(interval)
