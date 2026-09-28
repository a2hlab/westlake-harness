#!/usr/bin/env python3
"""#36 finalize: fold reverify + firefox crash + aegis experiment into the
corrected aggregate. Every number traces to a raw file:
- base: b4-aggregate-corrected.json (aggregate_61b.py over the two run dirs)
- firefox: /home/zhaoyue/a2hlab/board/b4-36-diag/new/cppcrash-17133-40103657
  (Uid 20010125 == firefox, thread org.mozilla.fir, #05 ContextImpl.getTheme)
- reverify: b4-36-reverify-61b-20260928T2235/results.json (clicked/sandbox/
  pids/shots per key)
- aegis: b4-36-aegis-experiment/{uninstall,reinstall,dump-after}.txt
"""
import collections, json, re, sys

BASE = "/home/zhaoyue/a2hlab/board/b4-36-faultlog/b4-aggregate-corrected.json"
FF_CRASH = "/home/zhaoyue/a2hlab/board/b4-36-diag/new/cppcrash-17133-40103657"
REVERIFY = "/home/zhaoyue/a2hlab/board/b4-36-reverify-61b-20260928T2235/results.json"
AEGIS = "/home/zhaoyue/a2hlab/board/b4-36-aegis-experiment"

def main(out):
    res = json.load(open(BASE))
    recs = {r["key"]: r for r in res["records"]}

    # --- firefox: interrupted -> exited-early with B6 crash evidence ---
    ff = open(FF_CRASH, errors="replace").read()
    assert re.search(r"Uid:20010125", ff) and "org.mozilla.fir" in ff
    theme = next(l.strip() for l in ff.splitlines() if "ContextImpl.getTheme" in l)
    r = recs["firefox"]
    r["category"] = "exited-early"
    r["category_reason"] = ("reverify run2235: install ok, desktop icon clicked, "
                            "no target pid at 3 s/30 s; faultlogger cppcrash-17133-40103657")
    r["first_blocker"] = "b6-activity-attach"
    r["blocker_evidence"] = theme + "  [file: cppcrash-17133-40103657, Uid 20010125, thread org.mozilla.fir]"

    # --- reverify outcomes for the four keys ---
    rv = {t["key"]: t for t in json.load(open(REVERIFY))["trials"]}
    for k, t in rv.items():
        recs[k]["reverify_run2235"] = {
            "clicked": t.get("clicked"), "sandbox_prepared": t.get("sandbox_prepared"),
            "pids_at_3s": t.get("pids_at_3s"), "pids_at_30s": t.get("pids_at_30s"),
            "input_attempted": t.get("input_attempted"),
            "launch_error": t.get("launch_error"),
            "capture_errors": t.get("capture_errors"),
            "screenshots": [{"path": s["path"], "sha256": s["sha256"]} for s in t.get("screenshots", [])],
        }
    # fd-notes: input test could not run (process not alive) — state it plainly
    recs["fd-notes"]["reverify_run2235"]["input_test"] = (
        "not attempted: no target-uid pid at 3 s or 30 s after desktop click; "
        "no new faultlogger file (board temp count unchanged at 40)")

    # --- aegis 9568260 experiment ---
    un = open(AEGIS + "/uninstall.txt", errors="replace").read().strip()
    ri = open(AEGIS + "/reinstall.txt", errors="replace").read().strip()
    du = open(AEGIS + "/dump-after.txt", errors="replace").read().strip()
    res["aegis_9568260_experiment"] = {
        "uninstall": un, "reinstall_same_apk": ri, "bm_dump_after": du[:80],
        "verdict": ("9568260 = cover-install over an existing older install fails; "
                    "same APK installs successfully after bm uninstall (icon/resource "
                    "hypothesis excluded)"),
    }

    # --- recompute histograms ---
    res["category_histogram"] = dict(collections.Counter(r["category"] for r in res["records"]))
    res["exited_early_first_blocker"] = dict(collections.Counter(
        r["first_blocker"] for r in res["records"]
        if r["category"] == "exited-early" and r["first_blocker"]))
    res["task"] += " + finalize (reverify, firefox crash, aegis experiment)"
    json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"categories": res["category_histogram"],
                      "early_blockers": res["exited_early_first_blocker"]}, indent=1))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/b4-final.json")
