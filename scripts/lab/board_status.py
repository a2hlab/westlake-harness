"""Read-only JSON view of the OLP board, so an agent can find its own entries without reading 4000 lines.

Writes still go to the Markdown board through olp-board-append.sh (flock, append-only); this only parses it.
An entry is a `### N. title` heading up to the next heading. Its lane is the `[lane]` tag in the title, its
boards are the connect-keys on the line naming 独占板/独占设备, its spec the first `specs/...spec.md` path.
An ACK is `ACK(` anywhere on a line -- `ACK(51 done: …)`, `ACK(done: …)` and `ACK(done)` all count, while the
template `ACK(51 done|blocked|wontdo)` quoted in a task body does not. One carrying a number is credited to
that entry, otherwise to the entry it sits under. Lines signed 外环(…) are reviewer notes, not ACKs.

usage: board_status.py [board.md] [--lane NAME] [--open] [--id N]
  --lane cc-t0   only entries tagged [cc-t0]      --open   only entries without an ACK
  --id 51        one entry, including its full body
"""
import json
import re
import sys

BOARD = "/Users/zhaoyue/orca/workspaces/westlake-harness/.octos/OUTER_LOOP_REVIEW.md"
HEAD = re.compile(r"^###\s+(\d+[a-z0-9-]*)\.\s*(.*)$")
ACK = re.compile(r"ACK\((?:(\d+[a-z0-9-]*)\s+)?(done|blocked|wontdo)\b(?!\|)")
KEY = re.compile(r"\b[0-9a-f]{8}0{12,}[0-9a-f]{4,}\b|\b[A-Z0-9]{19}\b")


def parse(path):
    entries, order, cur = {}, [], None
    for n, line in enumerate(open(path, encoding="utf-8", errors="replace"), 1):
        line = line.rstrip("\n")
        m = HEAD.match(line)
        if m:
            eid, title = m.group(1), m.group(2).strip()
            lane = re.search(r"\[([\w-]+)\]", title)
            cur = entries.setdefault(eid, {"id": eid, "title": title, "line": n,
                                           "lane": lane.group(1) if lane else None,
                                           "boards": [], "spec": None, "acks": [], "body": []})
            if eid not in order:
                order.append(eid)
            continue
        if cur is None:
            continue
        cur["body"].append(line)
        if not cur["boards"] and ("独占板" in line or "独占设备" in line):
            cur["boards"] = KEY.findall(line)
        if cur["spec"] is None:
            s = re.search(r"specs/[\w./-]+\.spec\.md", line)
            cur["spec"] = s.group(0) if s else None
        if re.search(r"外环\([^)]*\)", line[:60]):
            continue
        for hit in ACK.finditer(line):
            target = entries.get(hit.group(1), cur) if hit.group(1) else cur
            target["acks"].append({"line": n, "status": hit.group(2), "text": line.strip()[:200]})
    out = []
    for eid in order:
        e = entries[eid]
        e["state"] = e["acks"][-1]["status"] if e["acks"] else "open"
        out.append(e)
    return out


def main(argv):
    args, lane, only_open, one = list(argv), None, False, None
    if "--lane" in args:
        i = args.index("--lane"); lane = args[i + 1]; del args[i:i + 2]
    if "--id" in args:
        i = args.index("--id"); one = args[i + 1]; del args[i:i + 2]
    if "--open" in args:
        args.remove("--open"); only_open = True
    entries = parse(args[0] if args else BOARD)
    if lane:
        entries = [e for e in entries if e["lane"] == lane]
    if only_open:
        entries = [e for e in entries if e["state"] == "open"]
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
