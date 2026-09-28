"""Read-only views of an OLP campaign board; the Markdown board stays the only source of truth.

Writes go through olp-board-append.sh (flock, append-only) -- line-start notes through board_note.sh.
Parsed from the board:
  entries    `### N. title` up to the next heading (any unnumbered heading ends it). Lane = `[lane]` in the title; boards = connect-keys on the
             line naming 独占板/独占设备; spec = first `specs/...spec.md` path. `改判(作废 #N)` makes an entry
             supersede N (inheriting N's spec and boards when it names none); `与 #N 同时执行` attaches it to N.
  ACKs       a bare `ACK(` anywhere -- `ACK(51 done: …)`, `ACK(done: …)`, `ACK(done)`; not one quoted in
             backticks, not the `ACK(N done|blocked|wontdo)` template, not a line signed 外环(…).
  notes      line-start only:  PROGRESS(<N>): <iso-time> <lane> <text>
                               LOCK(<serial>) <lane> <iso-time> <why>      UNLOCK(<serial>) <lane> <iso-time>
Also read: task specs `<repo>/specs/<campaign>/t*.spec.md` (their `depends:`), connect-keys in project.spec.md
(the device pool), and live lock holders in ~/.octos/board-locks/*.holder (written by board_note.sh).

usage: board_status.py [board.md] [--lane NAME] [--open] [--id N]
       board_status.py <board.md> --schedule [--text] [--stale-min 30] [--specs DIR]
       board_status.py <board.md> --watch [--interval 60] [--stale-min 30]   # exits with events for the outer
"""
import datetime as dt
import json
import os
import pathlib
import re
import sys
import time

BOARD = "/Users/zhaoyue/orca/workspaces/westlake-harness/.octos/OUTER_LOOP_REVIEW.md"
LOCKS = pathlib.Path(os.environ.get("BOARD_LOCK_DIR", pathlib.Path.home() / ".octos/board-locks"))
HEAD = re.compile(r"^###\s+(\d+[a-z0-9-]*)\.\s*(.*)$")
ACK = re.compile(r"ACK\((?:(\d+[a-z0-9-]*)\s+)?(done|blocked|wontdo)\b(?!\|)")
KEY = re.compile(r"\b[0-9a-f]{8}0{12,}[0-9a-f]{4,}\b|\b[A-Z0-9]{19}\b")
PROGRESS = re.compile(r"^PROGRESS\((\d+[a-z0-9-]*)\):\s*(\S+)\s+(\S+)\s*(.*)$")
LOCKLINE = re.compile(r"^(LOCK|UNLOCK)\(([^)]+)\)\s+(\S+)\s+(\S+)\s*(.*)$")
TS = "%Y-%m-%dT%H:%M:%S%z"


def when(s):
    try:
        return dt.datetime.strptime(s, TS)
    except ValueError:
        return None


def parse(path):
    entries, order, cur, notes = {}, [], None, []
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        line = line.rstrip("\n")
        m = HEAD.match(line)
        if m:
            eid, title = m.group(1), m.group(2).strip()
            lane = re.search(r"\[([\w-]+)\]", title)
            cur = entries.setdefault(eid, {"id": eid, "title": title, "line": n,
                                           "lane": lane.group(1) if lane else None, "boards": [],
                                           "spec": None, "acks": [], "progress": [], "supersedes": [],
                                           "attached_to": None, "body": []})
            if eid not in order:
                order.append(eid)
            continue
        if re.match(r"^#{1,6}\s", line):
            cur = None  # an unnumbered heading (####/## section) ends the entry
            continue
        p = PROGRESS.match(line)
        if p:
            notes.append(("progress", n, p.groups()))
        k = LOCKLINE.match(line)
        if k:
            notes.append(("lock", n, k.groups()))
        if cur is None:
            continue
        cur["body"].append(line)
        if not cur["boards"] and ("独占板" in line or "独占设备" in line):
            cur["boards"] = KEY.findall(line)
        if cur["spec"] is None:
            s = re.search(r"specs/[\w./-]+\.spec\.md", line)
            cur["spec"] = s.group(0) if s else None
        for s in re.findall(r"改判\(作废 #(\d+)\)", line):
            if s not in cur["supersedes"]:
                cur["supersedes"].append(s)
        a = re.search(r"与 #(\d+) 同时执行", line)
        if a and cur["attached_to"] is None:
            cur["attached_to"] = a.group(1)
        if re.search(r"外环\([^)]*\)", line[:60]):
            continue
        for hit in ACK.finditer(line):
            if hit.start() > 0 and line[hit.start() - 1] == "`":
                continue  # quoted in `code` by a task body, e.g. "先 `ACK(4 blocked)`"
            target = entries.get(hit.group(1), cur) if hit.group(1) else cur
            target["acks"].append({"line": n, "status": hit.group(2), "text": line.strip()[:200]})
    locks = []
    for kind, n, g in notes:
        if kind == "progress":
            eid, t, lane, text = g
            if eid in entries:
                entries[eid]["progress"].append({"line": n, "time": t, "lane": lane, "text": text})
        else:
            op, serial, lane, t, why = g
            locks.append({"line": n, "op": op, "serial": serial, "lane": lane, "time": t, "why": why})
    out = []
    for eid in order:
        e = entries[eid]
        e["state"] = e["acks"][-1]["status"] if e["acks"] else "open"
    for eid in order:
        e = entries[eid]
        if e["attached_to"] in entries and not e["acks"]:
            e["state"] = entries[e["attached_to"]]["state"]  # answered in the parent's ACK
        for old in e["supersedes"]:
            if old in entries:
                entries[old]["superseded_by"] = eid
                e["spec"] = e["spec"] or entries[old]["spec"]
                e["boards"] = e["boards"] or entries[old]["boards"]
        out.append(e)
    return out, locks


def live_holders():
    held = {}
    for f in LOCKS.glob("*.holder"):
        try:
            pid, lane, t = f.read_text().split()[:3]
            os.kill(int(pid), 0)
        except (ValueError, OSError):
            continue
        held[f.name[:-len(".holder")]] = {"lane": lane, "pid": int(pid), "since": t}
    return held


def read_specs(spec_dir):
    tasks, pool = {}, []
    for f in sorted(spec_dir.glob("*.spec.md")):
        text = f.read_text(encoding="utf-8", errors="replace")
        head = text.split("\n---", 1)[0]
        name = f.name[:-len(".spec.md")]
        if name == "project":
            pool = KEY.findall(text)
            continue
        dep = re.search(r"^depends:\s*\[([^\]]*)\]", head, re.M)
        title = re.search(r'^name:\s*"?([^"\n]+)"?', head, re.M)
        tasks[name] = {"task": name, "name": title.group(1) if title else name,
                       "depends": [d.strip() for d in dep.group(1).split(",") if d.strip()] if dep else [],
                       "spec": str(f)}
    return tasks, pool


def schedule(board, stale_min=30, spec_dir=None, now=None):
    now = now or dt.datetime.now(dt.timezone.utc).astimezone()
    entries, locks = parse(board)
    byid = {e["id"]: e for e in entries}
    repo = pathlib.Path(board).resolve().parents[2]
    if spec_dir is None:
        specs = {e["spec"] for e in entries if e["spec"]}
        spec_dir = repo / pathlib.Path(sorted(specs)[0]).parent if specs else None
    tasks, pool = read_specs(pathlib.Path(spec_dir)) if spec_dir else ({}, [])

    # an attached entry reports under its parent; a superseded entry is history
    def root(e):
        return byid.get(e["attached_to"], e) if e["attached_to"] else e
    active = [e for e in entries if not e.get("superseded_by") and not e["attached_to"] and e["lane"]]
    for e in entries:
        if e["attached_to"] and e["attached_to"] in byid:
            byid[e["attached_to"]].setdefault("attached", []).append(e["id"])
    progress = {}
    for e in entries:
        for p in e["progress"]:
            progress.setdefault(root(e)["id"], []).append(p)

    def task_of(e):
        return pathlib.Path(e["spec"]).name[:-len(".spec.md")] if e["spec"] else None

    # tasks: done if some live entry for it ACKed done
    for t in tasks.values():
        live = [e for e in active if task_of(e) == t["task"]]
        states = [e["state"] for e in live]
        t["entries"] = [e["id"] for e in live]
        t["state"] = ("done" if "done" in states else "blocked" if "blocked" in states
                      else "running" if "open" in states else "wontdo" if "wontdo" in states else "pending")
    for t in tasks.values():
        t["deps_done"] = all(tasks.get(d, {}).get("state") == "done" for d in t["depends"])
    dispatchable = [t["task"] for t in tasks.values() if t["state"] == "pending" and t["deps_done"]]

    lanes = {}
    for e in active:
        if e["state"] in ("done", "wontdo"):
            continue
        ps = sorted(progress.get(e["id"], []), key=lambda p: p["time"])
        last = ps[-1] if ps else None
        age = None
        if last and when(last["time"]):
            age = round((now - when(last["time"])).total_seconds() / 60, 1)
        lane = lanes.setdefault(e["lane"], {"lane": e["lane"], "entries": []})
        lane["entries"].append({"id": e["id"], "task": task_of(e), "state": e["state"],
                                "attached": e.get("attached", []), "boards": e["boards"],
                                "last_progress": last, "minutes_since_progress": age,
                                "stale": (age is None) or age > stale_min})

    held = live_holders()
    last_lock = {}
    for l in locks:
        last_lock[l["serial"]] = l
    owned = {}
    for e in active:
        if e["state"] in ("open", "blocked"):
            for b in e["boards"]:
                owned.setdefault(b, []).append(e["lane"])
    devices = sorted(set(pool) | {b for e in active for b in e["boards"]})
    dev = []
    anomalies = []
    for d in devices:
        h = held.get(d)
        ll = last_lock.get(d)
        dev.append({"serial": d, "owned_by": owned.get(d, []), "lock": h,
                    "free": not owned.get(d) and not h})
        if len(owned.get(d, [])) > 1:
            anomalies.append(f"{d} owned by several lanes {owned[d]}")
        if h and h["lane"] not in owned.get(d, []):
            anomalies.append(f"{d} locked by {h['lane']} which does not own it")
        if ll and ll["op"] == "LOCK" and not h:
            anomalies.append(f"{d} LOCK by {ll['lane']} at line {ll['line']} has no live holder (stale lock)")
    for h_serial, h in held.items():
        if h_serial not in devices:
            anomalies.append(f"{h_serial} locked by {h['lane']} but not in the device pool")
    return {"board": str(board), "now": now.strftime(TS), "stale_min": stale_min,
            "lanes": list(lanes.values()), "tasks": list(tasks.values()), "dispatchable": dispatchable,
            "devices": dev, "free_devices": [d["serial"] for d in dev if d["free"]], "anomalies": anomalies}


def short(serial):
    return serial[:8] if len(serial) > 12 else serial


def render(s):
    out = [f"== {s['board']}  @ {s['now']}  (stale > {s['stale_min']} min)"]
    out.append("-- lanes")
    for lane in s["lanes"]:
        for e in lane["entries"]:
            lp = e["last_progress"]
            prog = f"{e['minutes_since_progress']} min ago: {lp['text'][:70]}" if lp else "no PROGRESS yet"
            flag = "  STALE" if e["stale"] else ""
            extra = f" (+#{',#'.join(e['attached'])})" if e["attached"] else ""
            out.append(f"  {lane['lane']:<8} #{e['id']}{extra:<8} {e['state']:<8} {str(e['task']):<24} "
                       f"[{','.join(short(b) for b in e['boards']) or '-'}]  {prog}{flag}")
    out.append("-- tasks")
    for t in s["tasks"]:
        deps = ",".join(t["depends"]) or "-"
        out.append(f"  {t['task']:<24} {t['state']:<8} entries={','.join('#' + i for i in t['entries']) or '-':<8} "
                   f"depends={deps}{'  <- DISPATCHABLE' if t['task'] in s['dispatchable'] else ''}")
    out.append("-- devices")
    for d in s["devices"]:
        lock = f"lock={d['lock']['lane']}" if d["lock"] else "lock=-"
        out.append(f"  {short(d['serial']):<20} owner={','.join(d['owned_by']) or '-':<8} {lock:<14}"
                   f"{'FREE' if d['free'] else ''}")
    if s["anomalies"]:
        out.append("-- anomalies")
        out += [f"  ! {a}" for a in s["anomalies"]]
    return "\n".join(out)


def events(prev, cur):
    """What the outer loop must act on between two schedule snapshots."""
    ev = []
    ps = {e["id"]: e["state"] for l in prev["lanes"] for e in l["entries"]}
    cs = {e["id"]: e["state"] for l in cur["lanes"] for e in l["entries"]}
    for eid, st in ps.items():
        if eid not in cs:
            ev.append(f"entry #{eid} left the active set (ACK done/wontdo)")
        elif cs[eid] != st:
            ev.append(f"entry #{eid} {st} -> {cs[eid]}")
    for t in set(cur["dispatchable"]) - set(prev["dispatchable"]):
        ev.append(f"task {t} is dispatchable (dependencies done)")
    pst = {e["id"] for l in prev["lanes"] for e in l["entries"] if e["stale"]}
    for l in cur["lanes"]:
        for e in l["entries"]:
            if e["stale"] and e["id"] not in pst:
                ev.append(f"lane {l['lane']} entry #{e['id']} stale: no PROGRESS for > {cur['stale_min']} min")
    for a in set(cur["anomalies"]) - set(prev["anomalies"]):
        ev.append(f"anomaly: {a}")
    return ev


def main(argv):
    args = list(argv)

    def opt(name, default=None, cast=str):
        if name in args:
            i = args.index(name); v = cast(args[i + 1]); del args[i:i + 2]; return v
        return default

    def flag(name):
        if name in args:
            args.remove(name); return True
        return False
    lane, one = opt("--lane"), opt("--id")
    stale, interval, spec_dir = opt("--stale-min", 30, float), opt("--interval", 60, float), opt("--specs")
    only_open, sched, text, watch = flag("--open"), flag("--schedule"), flag("--text"), flag("--watch")
    board = args[0] if args else BOARD
    if watch:
        base = schedule(board, stale, spec_dir)
        started, silent_reported = time.time(), set()
        while True:
            time.sleep(interval)
            cur = schedule(board, stale, spec_dir)
            ev = events(base, cur)
            # a lane that never wrote PROGRESS is stale in the baseline too; time it from the watch start
            if (time.time() - started) / 60 > stale:
                for l in cur["lanes"]:
                    for e in l["entries"]:
                        if e["last_progress"] is None and e["id"] not in silent_reported:
                            silent_reported.add(e["id"])
                            ev.append(f"lane {l['lane']} entry #{e['id']} silent: no PROGRESS since the watch "
                                      f"started {stale:g} min ago")
            if ev:
                print("SCHEDULE-SIGNAL")
                print("\n".join(ev))
                print(render(cur))
                return
            base = cur
    if sched:
        s = schedule(board, stale, spec_dir)
        print(render(s) if text else json.dumps(s, ensure_ascii=False, indent=1))
        return
    entries, _ = parse(board)
    if lane:
        entries = [e for e in entries if e["lane"] == lane]
    if only_open:
        entries = [e for e in entries if e["state"] == "open" and not e.get("superseded_by")]
    if one:
        entries = [e for e in entries if e["id"] == one]
    for e in entries:
        if not one:
            del e["body"]
        else:
            e["body"] = "\n".join(e["body"]).strip()
    json.dump(entries, sys.stdout, ensure_ascii=False, indent=1)
    print()


if __name__ == "__main__":
    main(sys.argv[1:])
