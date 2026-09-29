#!/usr/bin/env python3
"""Count the facts an ACK may state about a bms_batch.py run, straight from its files.

    run_facts.py <run-dir> [--json]

<run-dir> is a bms_batch run directory (<run>/<serial>/<key>/record.json, or <run>/<key>/record.json).
For every key it prints: screenshots captured / slots (record.json `screenshots[].captured`), whether a
process with the app's BMS uid is in processes-t5.txt / processes-t20.txt (UID column), how many hilog
lines the child process wrote (by the uid's PIDs), and the record status. The last line is the totals.

ACKs quote this output verbatim for screenshot and liveness counts (AGENTS.md 判定), so they are counted,
not taken from the plan. Unknown (file missing) is printed as `?`, never as a guess.
"""
import json
import pathlib
import re
import sys


def keys(run):
    run = pathlib.Path(run)
    subs = [d for d in run.iterdir() if d.is_dir() and re.search(r"0{7}", d.name)]
    base = subs[0] if len(subs) == 1 else run
    return sorted(d for d in base.iterdir() if (d / "record.json").is_file())


def pids_for_uid(path, uid):
    """PIDs whose UID column equals uid in a `ps -eo pid,ppid,uid,name` style table; None if unreadable."""
    try:
        lines = path.read_text(errors="replace").splitlines()
    except OSError:
        return None
    head = lines[0].split() if lines else []
    if "UID" not in head or "PID" not in head:
        return None
    ui, pi = head.index("UID"), head.index("PID")
    out = []
    for line in lines[1:]:
        f = line.split()
        if len(f) > max(ui, pi) and f[ui] == str(uid):
            out.append(f[pi])
    return out


def hilog_lines(path, pids):
    if not pids:
        return 0
    try:
        text = path.read_text(errors="replace")
    except OSError:
        return None
    pat = re.compile(r"^\S+ \S+\s+(%s)\s" % "|".join(map(re.escape, pids)), re.M)
    return len(pat.findall(text))


def facts(d):
    r = json.loads((d / "record.json").read_text())
    uid = (r.get("bms") or {}).get("uid")
    shots = r.get("screenshots") or []
    alive = {}
    pids = set()
    for t in ("t5", "t20"):
        p = pids_for_uid(d / f"processes-{t}.txt", uid) if uid is not None else None
        alive[t] = None if p is None else bool(p)
        pids.update(p or [])
    return {
        "key": d.name, "uid": uid, "status": r.get("status"),
        "captured": sum(1 for s in shots if s.get("captured")), "slots": len(shots),
        "not_captured_reasons": sorted({s.get("reason") for s in shots if not s.get("captured") and s.get("reason")}),
        "alive_t5": alive["t5"], "alive_t20": alive["t20"],
        "child_hilog_lines": hilog_lines(d / "hilog.txt", sorted(pids)),
    }


def mark(v):
    return "?" if v is None else ("yes" if v is True else "no" if v is False else str(v))


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    rows = [facts(d) for d in keys(argv[1])]
    if "--json" in argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for f in rows:
        why = ";".join(f["not_captured_reasons"])
        print(f"{f['key']:<20} shots {f['captured']}/{f['slots']}  alive t5={mark(f['alive_t5'])} "
              f"t20={mark(f['alive_t20'])}  child_hilog={mark(f['child_hilog_lines'])}  {f['status']}"
              + (f"  [{why}]" if why else ""))
    cap, slots = sum(f["captured"] for f in rows), sum(f["slots"] for f in rows)
    a5 = sum(1 for f in rows if f["alive_t5"]); a20 = sum(1 for f in rows if f["alive_t20"])
    unk = sum(1 for f in rows if f["alive_t20"] is None)
    print(f"TOTAL keys={len(rows)} screenshots_captured={cap}/{slots} alive_t5={a5} alive_t20={a20}"
          + (f" alive_unknown={unk}" if unk else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
