#!/usr/bin/env python3
"""#46: RSS / VSZ / VMA / thread curve across the three video windows of four46-fresh2.
Fields per /proc/pid/stat (after comm): index 22 = vsize, 23 = rss pages.
usage: mem_curve.py <run-dir>
"""
import json
import os
import sys

B = sys.argv[1]
print("window   t+sec    VSZ(GiB)  RSS(MiB)  threads")
for v in ("video1", "video2", "video3"):
    path = os.path.join(B, f"{v}-task-stats.jsonl")
    if not os.path.exists(path):
        continue
    rows = []
    for line in open(path):
        d = json.loads(line)
        first = d.get("tasks", "").split("\n", 1)[0]
        if ")" not in first:
            continue
        f = first[first.rindex(")") + 2:].split()
        rows.append((d["epoch"], int(f[20]), int(f[21]) * 4096, d["tasks"].count("\n") + 1))
    if not rows:
        continue
    t0 = rows[0][0]
    step = max(1, len(rows) // 6)
    shown = rows[::step]
    if rows[-1] not in shown:
        shown.append(rows[-1])
    for e, vsz, rss, n in shown:
        print(f"{v:8} {e - t0:6.1f}  {vsz / 2**30:8.1f}  {rss / 2**20:8.0f}  {n:6}")
    d0, d1 = rows[0], rows[-1]
    dt = d1[0] - d0[0]
    print(f"  -> RSS {d0[2] / 2**20:.0f} -> {d1[2] / 2**20:.0f} MiB over {dt:.0f}s "
          f"({(d1[2] - d0[2]) / 2**20 / dt * 60:.0f} MiB/min)")
