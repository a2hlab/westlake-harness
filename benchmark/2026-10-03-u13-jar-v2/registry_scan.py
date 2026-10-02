#!/usr/bin/env python3
"""Which runs ask for "telephony.registry", and which die on the null ITelephonyRegistry?

    registry_scan.py [--out registry-scan.csv]

Runs: the U10.1T8 signing population (white-vs-lit population.groups()) and every U12 window 1-4 run
(westlake-harness-u7-executor/.../2026-10-02-u12-final-assembly, smoke excluded). Per run, in hilog:
  asked   `[OHServiceManager] getService("telephony.registry")` (-> null on route A)
  npe     an NPE naming ITelephonyRegistry (listen*/addOnSubscriptionsChangedListener/...)
"""
import argparse
import csv
import glob
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-white-vs-lit'))
import lab_paths  # noqa: E402
import population  # noqa: E402

U12 = lab_paths.workspaces() / 'westlake-harness-u7-executor/benchmark/2026-10-02-u12-final-assembly'


def scan(run):
    asked = npe = 0
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'getService("telephony.registry")' in line:
            asked += 1
        if 'NullPointerException' in line and 'ITelephonyRegistry' in line:
            npe += 1
    return asked, npe


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'registry-scan.csv'))
    a = ap.parse_args()
    rows = []
    for k, g, v, run in population.groups():
        asked, npe = scan(run)
        rows.append({'source': 'u10.1t8', 'key': k, 'group': g, 'asked': asked, 'npe': npe})
    for rec in sorted(glob.glob(str(U12 / 'window*/**/runner/*/*/*/*/record.json'), recursive=True)):
        if '/smoke/' in rec:
            continue
        d = Path(rec).parent
        if not (d / 'hilog.txt').exists():
            continue
        asked, npe = scan(d)
        w = next(p for p in d.parts if p.startswith('window'))
        rows.append({'source': 'u12-' + w, 'key': d.name, 'group': d.parent.parent.parent.name, 'asked': asked, 'npe': npe})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for src in ('u10.1t8', 'u12'):
        rs = [r for r in rows if r['source'].startswith(src)]
        print(f'{src}: runs {len(rs)}, ask telephony.registry {sum(1 for r in rs if r["asked"])}, '
              f'die on null ITelephonyRegistry {sum(1 for r in rs if r["npe"])}')
        for r in rs:
            if r['asked']:
                print(f"   {r['source']} {r['group']} {r['key']} asked={r['asked']} npe={r['npe']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
