#!/usr/bin/env python3
"""#36 ①: corrected 61b aggregate (supersedes #32's b4-aggregate-61b.json).

Fixes vs the voided version (outer-loop re-review findings):
- liveness read from observed_pids (bms_batch.py field), not pids_after;
- install success judged from install.txt TEXT ("failed to install bundle"
  = failure with its code), not the bm process return code alone;
- first_blocker joined from crash-map.json (raw faultlogger files);
  late-crash survivors (alive at 16 s sample, crashed after) keep their
  crash recorded but are NOT counted as exited;
- firefox (batch_interrupted) and subwaysurfers (hash-refused, no
  install.txt) are listed as their own statuses, not lumped into early-exit.

Categories per key:
- alive-at-sample: observed_pids non-empty
- install-failed-9568260: install.txt contains the failure text
- interrupted: status batch_interrupted
- input-refused: no install.txt at all (hash mismatch refusal)
- exited-early: no observed_pids and install ok
  -> first_blocker from crash-map: b6-activity-attach / other-native;
     absent crash file => unknown (recorded explicitly)
"""
import collections, hashlib, json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "scripts", "lab"))
import lab_paths  # <repo>/scripts/lab

RUNS = [
    os.path.expanduser("~/a2hlab/board/bms-61b-20260928T195314/61b0657200000000000000000324012c"),
    os.path.expanduser("~/a2hlab/board/bms-61b-resume-20260928T2040/61b0657200000000000000000324012c"),
]
MANIFEST = str(lab_paths.workspaces() / "westlake-harness-b4/benchmark/2026-09-28-bms-route-deploy/batch/apps.json")
CRASHMAP = os.path.expanduser("~/a2hlab/board/b4-36-faultlog/crash-map.json")

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def main(out):
    recs = {}
    for r in RUNS:
        for x in json.load(open(os.path.join(r, "summary.json")))["records"]:
            recs[x["key"]] = (x, r)   # resume run wins for its 6 keys
    manifest = json.load(open(MANIFEST))["apps"]
    assert len(recs) == len(manifest) == 66
    crashes = {c["key"]: c for c in json.load(open(CRASHMAP))}
    out_recs = []
    for a in manifest:
        k = a["key"]
        rec, r = recs[k]
        d = os.path.join(r, k)
        ip = os.path.join(d, "install.txt")
        itxt = open(ip, errors="replace").read() if os.path.isfile(ip) else None
        status = rec.get("status")
        alive = bool(rec.get("observed_pids"))
        # classification
        if itxt is None and status == "app_failed":
            cat, why = "input-refused", "no install.txt; status app_failed (input hash drift refusal)"
        elif itxt is not None and "failed to install bundle" in itxt:
            import re
            code = re.search(r"code:(\d+)", itxt)
            cat = "install-failed-%s" % (code.group(1) if code else "unknown")
            why = itxt.strip().replace("\n", " / ")[:200]
        elif status == "batch_interrupted":
            cat, why = "interrupted", "install ok; batch interrupted before launch"
        elif alive:
            cat, why = "alive-at-sample", "observed_pids=%s" % rec.get("observed_pids")
        else:
            cat, why = "exited-early", "install ok; no target pid at 16 s sample"
        # first blocker for exited-early comes from the crash map
        blk, ev = None, None
        cr = crashes.get(k)
        if cat == "exited-early":
            if cr and cr.get("first_blocker"):
                blk, ev = cr["first_blocker"], cr.get("blocker_frame", "")
            else:
                blk, ev = "unknown", "no faultlogger file in window matches this key"
        elif cr:
            blk, ev = "late-crash:" + cr["first_blocker"], cr.get("blocker_frame", "")
        shots = []
        for s in (rec.get("screenshots") or []):
            shots.append({"path": s["path"], "sha256": s["sha256"], "visual_verdict": s.get("visual_verdict", "pending_review")})
        out_recs.append({
            "key": k, "phase": a["phase"], "package": a["package"],
            "apk_sha256": a["apk_sha256"], "record_status": status,
            "observed_pids": rec.get("observed_pids"),
            "foreground_confirmed": (rec.get("foreground") or {}).get("confirmed")
                if isinstance(rec.get("foreground"), dict) else rec.get("foreground"),
            "category": cat, "category_reason": why,
            "first_blocker": blk, "blocker_evidence": ev,
            "screenshots": shots,
        })
    hist = collections.Counter(r["category"] for r in out_recs)
    blk_hist = collections.Counter(r["first_blocker"].split(":")[-1] for r in out_recs if r["first_blocker"] and r["category"] == "exited-early")
    res = {
        "task": "b4-bms-sweep 61b corrected (#36; supersedes #32 aggregate)",
        "date": "2026-09-28", "serial": "61b0657200000000000000000324012c",
        "runs": RUNS, "crash_map": CRASHMAP, "total": len(out_recs),
        "category_histogram": dict(hist),
        "exited_early_first_blocker": dict(blk_hist),
        "records": out_recs,
    }
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"categories": dict(hist), "early_blockers": dict(blk_hist)}, indent=1))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b4-aggregate-corrected.json")
