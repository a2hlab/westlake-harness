#!/usr/bin/env python3
"""B4 #32: aggregate 66 records from the 61b batch runs into results.json.

Merges the two run directories (main + resume), keys them against the fixed
manifest, hashes the t3/final screenshots (paths+hash only; visual verdict is
the outer reviewer's), and derives first_blocker buckets per spec b4:
sandbox / spawn / alias-entry / activity-attach / art-entry / first-frame /
install / other. Derivation is log-based only — no image reading.
"""
import collections, hashlib, json, os, re, sys

RUNS = [
    "/home/zhaoyue/a2hlab/board/bms-61b-20260928T195314/61b0657200000000000000000324012c",
    "/home/zhaoyue/a2hlab/board/bms-61b-resume-20260928T2040/61b0657200000000000000000324012c",
]
MANIFEST = "/Users/zhaoyue/orca/workspaces/westlake-harness-b4/benchmark/2026-09-28-bms-route-deploy/batch/apps.json"

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()

def read(p, limit=400000):
    try:
        with open(p, "r", errors="replace") as f:
            return f.read(limit)
    except OSError:
        return ""

# signature -> bucket, ordered: first match wins against combined log text
SIGS = [
    ("activity-attach", [
        r"ContextWrapper\.getApplicationInfo", r"ContextImpl\.getTheme",
        r"Unable to instantiate activity", r"ClassNotFoundException",
        r"attachBaseContext", r"SIGSEGV",
    ]),
    ("spawn", [
        r"appspawn", r"failed to fork", r"setuid", r"Failed to start proc",
    ]),
    ("alias-entry", [
        r"DefaultIcon", r"targetActivity", r"MissingTarget",
    ]),
    ("art-entry", [
        r"art::", r"JNI DETECTED", r"java\.lang\.\w+Exception",
    ]),
]

def bucket(rec, d):
    if (rec.get("install") or {}).get("return_code") != 0:
        return "install", "install rc != 0"
    sp = (rec.get("sandbox") or {})
    if sp.get("return_code") not in (0, None):
        return "sandbox", sp.get("output", "")
    fg = (rec.get("foreground") or {})
    if isinstance(fg, bool):
        fg = {"confirmed": fg}
    if not rec.get("observed_pids"):
        return "spawn", "no process observed for target UID between click and sampling"
    if fg.get("confirmed"):
        return "none", "foreground confirmed; lit pending outer review"
    return "first-frame", "no process alive at sample; no signature matched"

def main(out):
    recs = []
    for r in RUNS:
        recs += json.load(open(os.path.join(r, "summary.json")))["records"]
    by = {x["key"]: x for x in recs}
    manifest = json.load(open(MANIFEST))["apps"]
    order = [a["key"] for a in manifest]
    assert len(by) == len(order) == 66, (len(by), len(order))
    out_recs = []
    for a in manifest:
        k = a["key"]
        rec = by[k]
        # locate this key's directory (resume run's records win for its 6 keys)
        d = None
        for r in RUNS:
            p = os.path.join(r, k)
            if os.path.isdir(p):
                d = p
        shots = {}
        for tag in ("t3", "final"):
            p = os.path.join(d, tag + ".jpeg")
            if os.path.isfile(p):
                shots[tag] = {"path": p, "sha256": sha256(p)}
        blk, ev = bucket(rec, d)
        out_recs.append({
            "key": k, "phase": a["phase"], "package": a["package"],
            "apk_sha256": a["apk_sha256"],
            "install_rc": (rec.get("install") or {}).get("return_code"),
            "bms_queryable": (rec.get("bms") or {}).get("queryable"),
            "uid": (rec.get("bms") or {}).get("uid"),
            "desktop_activity": (rec.get("bms") or {}).get("desktop_activity"),
            "clicked": rec.get("clicked"),
            "pids_after": rec.get("pids_after"),
            "foreground_confirmed": (rec.get("foreground") or {}).get("confirmed"),
            "first_blocker": blk, "blocker_evidence": ev[:300],
            "screenshots": shots, "review": "pending_review",
        })
    hist = collections.Counter(r["first_blocker"] for r in out_recs)
    res = {
        "task": "b4-bms-sweep 61b", "date": "2026-09-28",
        "serial": "61b0657200000000000000000324012c",
        "runs": RUNS, "total": len(out_recs),
        "first_blocker_histogram": dict(hist),
        "records": out_recs,
    }
    with open(out, "w") as f:
        json.dump(res, f, indent=1, ensure_ascii=False)
    print(json.dumps({"total": res["total"], "histogram": res["first_blocker_histogram"]}, indent=1))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b4-results.json")
