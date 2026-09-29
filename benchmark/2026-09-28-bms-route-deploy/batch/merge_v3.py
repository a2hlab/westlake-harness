#!/usr/bin/env python3
"""#48: fold classify-22 into b4-final-61b-v2.json -> v3 with new histograms."""
import json, collections, sys

BASE = "/home/zhaoyue/a2hlab/board/b4-36-faultlog/b4-final-v2.json"
CLASS = "/home/zhaoyue/a2hlab/board/b4-48-faultlog/classify-22.json"

def main(out):
    final = json.load(open(BASE))
    recs = {r["key"]: r for r in final["records"]}
    cls = json.load(open(CLASS))["keys"]
    for k, v in cls.items():
        r = recs[k]
        r["category"] = v["category"]
        r["category_reason"] = "#48 unknown22 probe: %s" % ("alive at t+15" if v["category"] == "alive-at-sample" else "early exit, first fatal line classified")
        r["first_blocker"] = v["first_blocker"] if v["first_blocker"] else None
        r["blocker_evidence"] = v["evidence"]
        if v.get("faultlog_file"):
            r["faultlog_file"] = v["faultlog_file"]
        r["p48_probe"] = {"pids_at_15s": v["pids_at_15s"], "source": v.get("source", "faultlog")}
    final["task"] += " + #48 unknown22 probe (22 keys re-classified, 0 unknowns remain)"
    final["category_histogram"] = dict(collections.Counter(r["category"] for r in final["records"]))
    final["exited_early_first_blocker"] = dict(collections.Counter(
        r["first_blocker"] for r in final["records"]
        if r["category"] == "exited-early" and r["first_blocker"]))
    final["unknown_keys_remaining"] = [r["key"] for r in final["records"]
                                       if r["category"] == "exited-early" and r["first_blocker"] == "unknown"]
    json.dump(final, open(out, "w"), indent=1, ensure_ascii=False)
    print(json.dumps({"cats": final["category_histogram"],
                      "early": final["exited_early_first_blocker"],
                      "unknowns_left": final["unknown_keys_remaining"]}, indent=1))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/v3.json")
