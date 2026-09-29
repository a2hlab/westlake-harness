#!/usr/bin/env python3
"""#36 ②: map faultlogger temp crashes to the 38 exited apps.

Rules (raw-file backed, no rerun):
- crash file: cppcrash-<pid>-<unix_ms>; timestamp inside must be within
  19:53-21:05 local (the two batch runs' window).
- thread name "Tid: <pid>, Name:<x>" is the forked child's package name.
- first_blocker: first boot-framework.oat frame in the fault thread stack
  mapped to a bucket; B6 family = getTheme/getApplicationInfo during
  Activity.attach.
"""
import json, os, re, sys

TEMP = "/home/zhaoyue/a2hlab/board/b4-36-faultlog/temp"
RUNS = [
    "/home/zhaoyue/a2hlab/board/bms-61b-20260928T195314/61b0657200000000000000000324012c",
    "/home/zhaoyue/a2hlab/board/bms-61b-resume-20260928T2040/61b0657200000000000000000324012c",
]
MANIFEST = "/Users/zhaoyue/orca/workspaces/westlake-harness-b4/benchmark/2026-09-28-bms-route-deploy/batch/apps.json"
# batch window: 19:53:14 start .. 20:58:40 last crash observed; widen to 19:50-21:10
WINDOW = ("2026-09-28 19:50", "2026-09-28 21:10")

FRAME_BUCKETS = [
    ("b6-activity-attach", re.compile(r"ContextImpl\.getTheme|ContextWrapper\.getApplicationInfo")),
    ("activity-attach-other", re.compile(r"Activity\.attach|performLaunchActivity")),
    ("window-surface", re.compile(r"ANativeWindow|Surface|hwui|EGL")),
    ("art-entry", re.compile(r"art::|nterp_")),
]

def parse(fn):
    txt = open(fn, errors="replace").read()
    ts = re.search(r"Timestamp:([\d\- :.]+)", txt)
    pid = re.search(r"^Pid:(\d+)", txt, re.M)
    uid = re.search(r"^Uid:(\d+)", txt, re.M)
    name = re.search(r"Tid:\d+, Name:(\S+)", txt)
    raw = re.findall(r"#\d+ pc \S+ (\S+?)\(([^)]*)\)", txt)
    frames = [f"{lib}({sym})" for lib, sym in raw][:30]
    return {
        "file": os.path.basename(fn),
        "timestamp": ts.group(1).strip() if ts else None,
        "pid": pid.group(1) if pid else None,
        "uid": uid.group(1) if uid else None,
        "thread_name": name.group(1) if name else None,
        "frames": frames[:30],
    }

def main(out):
    crashes = []
    for fn in sorted(os.listdir(TEMP)):
        p = os.path.join(TEMP, fn)
        if not os.path.isfile(p):
            continue
        c = parse(p)
        # window filter on the in-file timestamp
        if not c["timestamp"] or not (WINDOW[0] <= c["timestamp"] <= WINDOW[1]):
            continue
        bucket, evidence = "unknown", ""
        for f in c["frames"]:
            if "boot-framework.oat" not in f and "boot.oat" not in f:
                continue
            for b, rx in FRAME_BUCKETS:
                if rx.search(f):
                    bucket, evidence = b, f
                    break
            if bucket != "unknown":
                break
        if bucket == "unknown" and c["frames"]:
            bucket, evidence = "other-native", c["frames"][0]
        c["first_blocker"], c["blocker_frame"] = bucket, evidence
        crashes.append(c)
    # load records -> uid map (apps that were actually launched)
    recs = []
    for r in RUNS:
        recs += json.load(open(os.path.join(r, "summary.json")))["records"]
    by_uid = {}
    for rec in recs:
        u = (rec.get("bms") or {}).get("uid")
        if u:
            by_uid[str(u)] = rec["key"]
    by_pkg = {a["package"]: a["key"] for a in json.load(open(MANIFEST))["apps"]}
    for c in crashes:
        k = by_uid.get(c["uid"]) or by_pkg.get(c["thread_name"])
        c["key"] = k or None
    with open(out, "w") as f:
        json.dump(crashes, f, indent=1, ensure_ascii=False)
    import collections
    print("crashes in window:", len(crashes))
    print("by blocker:", dict(collections.Counter(c["first_blocker"] for c in crashes)))
    print("mapped to key:", sum(1 for c in crashes if c["key"]))
    print("unmapped thread_names:", sorted({c["thread_name"] for c in crashes if not c["key"]}))

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "/tmp/crash-map.json")
