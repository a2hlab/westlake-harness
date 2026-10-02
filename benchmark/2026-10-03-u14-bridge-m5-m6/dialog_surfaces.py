#!/usr/bin/env python3
"""What M5 alone (no M1) raises for each dialog-first key: per window session of the signed run, its Android type, the
outcome of every cross-copy BBQ lookup (rescued = it got its Surface, empty = no Surface: the R3/V1 single slot already
points at a later session), and whether / where the window still exists in the t20 window dump.

    dialog_surfaces.py [--out dialog-surfaces.json]

Runs: the 13 keys of ../2026-10-03-u14-m5-watchlist (its signed lit runs, evidence/zorder-proof.txt) plus the two M5
movers dddmodel2 and fd-mobile (their U10.1T8 signing runs, ../2026-10-02-white-vs-lit population)."""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-white-vs-lit'))
sys.path.insert(0, str(HERE.parent / '2026-10-02-m1-session-slots'))
import population  # noqa: E402
import static_proof  # noqa: E402
import templates  # noqa: E402

CS = re.compile(r'createSession: bundle=\S+ ability=(\S+) name=\S+, androidType=(\d+) -> ohType=(\d+)')
OK = re.compile(r'createSession: success, sessionId=(\d+)')
ZO = re.compile(r'UpdateZOrderInner: id: (\d+), zOrder: \d+ -> (\d+)')
WIN = re.compile(r'^(\S+)\s+\d+\s+(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+(-?\d+)\s+\d+\s+\[\s*(-?\d+)\s+(-?\d+)\s+(\d+)\s+(\d+)\s*\]')
EXTRA = ['cv2-org-andresoviedo-dddmodel2', 'fd-mobile']


def runs():
    ws = str(templates.lab_paths.workspaces())
    proof = HERE.parent / '2026-10-03-u14-m5-watchlist' / 'evidence' / 'zorder-proof.txt'
    out = []
    for line in proof.read_text().splitlines():
        m = re.match(r'== (\S+)\s+run=(\S+)', line)
        if m:
            out.append((m.group(1), 'watchlist', f'{ws}/westlake-harness-u7-executor/benchmark/{m.group(2)}'))
    out += [(k, 'mover', run) for k, g, v, run in population.groups() if k in EXTRA]
    return out


def sessions(run, pids):
    order, pending = [], {}
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'createSession' not in line and 'UpdateZOrderInner' not in line:
            continue
        m = templates.LINE.match(line)
        if not m:
            continue
        msg, pid, tid = m.group(11), int(m.group(7)), m.group(8)
        c = CS.search(msg)
        if c and pid in pids:
            pending[tid] = int(c.group(2))
            continue
        o = OK.search(msg)
        if o and pid in pids and tid in pending:
            order.append({'session': int(o.group(1)), 'androidType': pending.pop(tid), 'zOrder': None})
            continue
        z = ZO.search(msg)
        if z:
            for s in order:
                if s['session'] == int(z.group(1)):
                    s['zOrder'] = int(z.group(2))
    return order


def t20_windows(run, pids):
    f = Path(run) / 'windows-t20.txt'
    if not f.exists():
        return None
    out = {}
    for line in f.read_text(errors='replace').splitlines():
        m = WIN.match(line)
        if m and int(m.group(2)) in pids:
            out[int(m.group(3))] = {'rect': [int(m.group(i)) for i in (6, 7, 8, 9)], 'zord': int(m.group(5))}
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'dialog-surfaces.json'))
    a = ap.parse_args()
    rows = []
    for key, src, run in runs():
        pids = set(templates.extract(run)['app_pids'])
        ss = sessions(run, pids)
        lk = static_proof.replay(run)['lookups']
        win = t20_windows(run, pids)
        for s in ss:
            got = [x['outcome'] for x in lk if x['session'] == s['session']]
            s['lookups'] = got
            s['surface'] = ('none' if got and all(g == 'empty' for g in got) else
                            'yes' if got else 'no-lookup')
            s['t20'] = None if win is None else win.get(s['session'])
        rows.append({'key': key, 'source': src, 'run': run.replace(str(templates.lab_paths.workspaces()), '$WORKSPACES'),
                     'sessions': ss})
        desc = '; '.join(f"{s['session']} t{s['androidType']} z{s['zOrder']} surface={s['surface']} "
                         f"t20={'gone' if s['t20'] is None else 'x'.join(map(str, s['t20']['rect'][2:]))}"
                         for s in ss)
        print(f'{key:42s} {desc}')
    Path(a.out).write_text(json.dumps(rows, indent=1) + '\n')


if __name__ == '__main__':
    main()
