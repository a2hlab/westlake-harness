#!/usr/bin/env python3
"""Count the facts an ACK may state about a bms_batch.py run, straight from its files.

    run_facts.py <run-dir> [--json]

<run-dir> is a bms_batch run directory (<run>/<serial>/<key>/record.json, or <run>/<key>/record.json).
For every key it prints: screenshots captured / slots (record.json `screenshots[].captured`), whether a
process with the app's BMS uid is in processes-t5.txt and the final scheduled capture's process file
(e.g. processes-t10.txt or processes-t20.txt, UID column), how many hilog
lines the child process wrote (by the uid's PIDs), and the record status. The last line is the totals.
The first lines give the run's identity, in the same format bms_batch.py writes at the top of facts.txt:
RUNTIME / FROZEN / BOOTIMAGE fingerprints and the TOOL line. 2026-10-01 a lane regenerated facts.txt with this
script and the U7 5cd facts lost which runtime and boot image they were counted on.

ACKs quote this output verbatim for screenshot and liveness counts (AGENTS.md 判定), so they are counted,
not taken from the plan. Unknown (file missing) is printed as `?`, never as a guess.
"""
import hashlib
import json
import math
import pathlib
import re
import sys


def base_dir(run):
    run = pathlib.Path(run)
    subs = [d for d in run.iterdir() if d.is_dir() and re.search(r"0{7}", d.name)]
    return subs[0] if len(subs) == 1 else run


def keys(run):
    base = base_dir(run)
    return sorted(d for d in base.iterdir() if (d / "record.json").is_file())


def identity(run):
    """RUNTIME/FROZEN/BOOTIMAGE/TOOL lines as bms_batch.write_facts prints them; missing inputs are said, not skipped."""
    base, out = base_dir(run), []
    fp, bp = base / "runtime-fingerprint.txt", base / "boot-image-fingerprint.txt"
    for label, path, note in (("RUNTIME", fp, "compare before blaming the JAR across boards"),
                              ("BOOTIMAGE", bp, "not part of RUNTIME")):
        if not path.is_file():
            out.append(f"{label} fingerprint=unknown ({path.name} missing)")
            continue
        body = path.read_text().strip()
        short = hashlib.sha256(body.encode()).hexdigest()[:12] if body else "unknown"
        out.append(f"{label} fingerprint={short} files={len(body.splitlines()) if body else 0} ({path.name}; {note})")
        if label == "RUNTIME":
            try:
                sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
                import check_frozen
                checked, bad = check_frozen.check_artifacts(
                    check_frozen.active(check_frozen.load(check_frozen.REPO / "knowledge/frozen/frozen.json")),
                    check_frozen.fingerprint_hashes(fp), "board")
                out.append(f"FROZEN checked={len(checked)} violations={bad}"
                           + "".join(f"\n  {l}" for l in checked if l.startswith("FROZEN-VIOLATION")))
            except Exception as exc:
                out.append(f"FROZEN unavailable: {exc}")
    try:
        tool = json.loads((base / "plan.json").read_text()).get("tool") or {}
    except (OSError, ValueError):
        tool = {}
    out.append(f"TOOL bms_batch={tool.get('bms_batch_sha256', '?')[:8]} head={(tool.get('git_head') or '?')[:9]} "
               f"manifest={tool.get('manifest_sha256', '?')[:8]} (plan.json tool)" if tool
               else "TOOL unknown (plan.json has no tool identity)")
    return out


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
    timed = [s.get("scheduled_seconds") for s in shots
             if isinstance(s.get("scheduled_seconds"), (int, float))
             and math.isfinite(s["scheduled_seconds"]) and s["scheduled_seconds"] >= 0]
    last_tag = ('t' + str(float(max(timed))).removesuffix('.0')) if timed else None
    for t in dict.fromkeys(["t5", "t20"] + ([last_tag] if last_tag else [])):
        p = pids_for_uid(d / f"processes-{t}.txt", uid) if uid is not None else None
        alive[t] = None if p is None else bool(p)
        pids.update(p or [])
    return {
        "key": d.name, "uid": uid, "status": r.get("status"),
        "captured": sum(1 for s in shots if s.get("captured")), "slots": len(shots),
        "not_captured_reasons": sorted({s.get("reason") for s in shots if not s.get("captured") and s.get("reason")}),
        "alive_t5": alive["t5"], "alive_t20": alive["t20"],
        "last_shot_tag": last_tag,
        "alive_last": alive.get(last_tag),
        **({"alive_" + last_tag: alive[last_tag]} if last_tag else {}),
        "child_hilog_lines": hilog_lines(d / "hilog.txt", sorted(pids)),
    }


def mark(v):
    return "?" if v is None else ("yes" if v is True else "no" if v is False else str(v))


def format_rows(rows):
    """Same factual text for the CLI and bms_batch; liveness follows the recorded shot schedule."""
    lines = []
    for f in rows:
        tag = f['last_shot_tag'] or 'last'
        why = ';'.join(f['not_captured_reasons'])
        lines.append(f"{f['key']:<20} shots {f['captured']}/{f['slots']}  alive t5={mark(f['alive_t5'])} "
                     f"{tag}={mark(f['alive_last'])}  child_hilog={mark(f['child_hilog_lines'])}  {f['status']}"
                     + (f"  [{why}]" if why else ''))
    cap, slots = sum(f['captured'] for f in rows), sum(f['slots'] for f in rows)
    tags = sorted({f['last_shot_tag'] for f in rows if f['last_shot_tag']}, key=lambda t: float(t[1:]))
    counts = [f"alive_{tag}={sum(f['last_shot_tag'] == tag and f['alive_last'] is True for f in rows)}"
              for tag in tags if tag != 't5']
    if not tags: counts = ['alive_last=0']
    unknown = sum(f['alive_last'] is None for f in rows)
    total = f"TOTAL keys={len(rows)} screenshots_captured={cap}/{slots} alive_t5={sum(f['alive_t5'] is True for f in rows)}"
    total += (' ' + ' '.join(counts)) if counts else ''
    if unknown: total += f' alive_unknown={unknown}'
    return lines, total


def main(argv):
    if len(argv) < 2 or argv[1] in ("-h", "--help"):
        print(__doc__.strip(), file=sys.stderr)
        return 2
    rows = [facts(d) for d in keys(argv[1])]
    if "--json" in argv:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return 0
    for line in identity(argv[1]):
        print(line)
    lines, total = format_rows(rows)
    for line in lines: print(line)
    print(total)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
