#!/usr/bin/env python3
"""How many keys exercise each class-b (846-only) bridge path at runtime? Counts the 846-only log lines in the U10.1T8
signing runs (white-vs-lit population.groups(), whole hilog; these strings exist only in 84695d62, so a hit means the
key ran that 846-only code). R1 (focus bridge) logs only on error, and the R2 EnableRootBlast success line is an
ALOGI that does not reach hilog: 0 lines there means "never failed", not "never ran". R2 ran in every key that logged
"bound Android top-level content" (it sits after the EnableRootBlast check in createSession; a failure would refuse).

    usage_b.py [--out usage-b.csv]
"""
import argparse
import collections
import csv
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-white-vs-lit'))
import population  # noqa: E402

PATHS = {
    'R2_root_blast_on': 'EnableRootBlast: mUseBLASTAdapter',
    'R2_root_blast_refused': 'failed to enable root BLAST',
    'R2_bound_to_mainsession': 'bound Android top-level content to OH MainSession',
    'R3_rs_node_acquired_cross_ns': 'acquired process-published cross-namespace surface',
    'R3_rs_node_none': 'no local or process-published RSSurfaceNode',
    'R1_focus_bridge_err': 'callFocusBridgeVoidMethod(',
    'R1_focus_bridge_ctor_err': 'WindowCallbackBridge',
}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'usage-b.csv'))
    a = ap.parse_args()
    rows = []
    keys = collections.defaultdict(lambda: collections.Counter())
    for k, g, v, run in population.groups():
        c = collections.Counter()
        for line in open(Path(run) / 'hilog.txt', errors='replace'):
            for name, needle in PATHS.items():
                if needle in line:
                    c[name] += 1
        rows.append({'key': k, 'group': g, **{n: c[n] for n in PATHS}})
        for n in PATHS:
            if c[n]:
                keys[n][g] += 1
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print('runs', len(rows), dict(collections.Counter(r['group'] for r in rows)))
    for n in PATHS:
        print(f'{n:32s} keys with >=1 line: {dict(keys[n]) or 0}  lines: {sum(r[n] for r in rows)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
