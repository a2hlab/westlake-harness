"""List every ACK on the OLP board under the entry it answers, so no reply is missed.

Earlier scans anchored on `^ACK(` and missed replies whose ACK did not start the line. This matches `ACK(`
anywhere, attributes each hit to the nearest preceding `### N.` heading, and reports entries that have no ACK.
usage: board_acks.py [board.md] [--since-line N]
"""
import re
import sys

args = sys.argv[1:]
since = 0
if "--since-line" in args:
    i = args.index("--since-line")
    since = int(args[i + 1])
    del args[i:i + 2]
board = args[0] if args else "/Users/zhaoyue/orca/workspaces/westlake-harness/.octos/OUTER_LOOP_REVIEW.md"

entry, acks, entries = None, {}, []
for n, line in enumerate(open(board, encoding="utf-8", errors="replace"), 1):
    m = re.match(r"^###\s+(\d+)\.", line)
    if m:
        entry = int(m.group(1))
        if entry not in entries:
            entries.append(entry)
        continue
    for hit in re.finditer(r"ACK\((done|blocked|wontdo)\)", line):
        if n >= since and "外环(claude)" not in line[:40]:
            acks.setdefault(entry, []).append((n, hit.group(1), line.strip()[:110]))

for e in entries:
    rows = acks.get(e, [])
    if rows:
        for n, kind, text in rows:
            print(f"#{e:<3} L{n:<5} {kind:<8} {text}")
    elif since == 0:
        print(f"#{e:<3} {'-':<6} (no ACK)")
