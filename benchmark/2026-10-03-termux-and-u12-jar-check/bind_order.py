#!/usr/bin/env python3
"""In which U10.1T8 runs is an in-process bound service connected BEFORE the binding Activity is started?

    bind_order.py [--out bind-order.csv]

Per signing run (white-vs-lit population.groups()), in the app process (the pid of the first [B47-SLA] ENTRY):
  posted      first `[B8-AMB] bindServiceInstance -> in-process in-app service` (bindService queues the in-process
              create+bind+onServiceConnected runnable on the main looper: ActivityManagerBindProxy.postInProcessBind)
  connected   first `[B8-AMB] connected <service>` (that runnable ran)
  resumed     first `ClientTransaction scheduled on main Looper (direct token): RESUMED` (onStart/onResume of the
              launched Activity run from that transaction on route A, not from the launch transaction)
  finish      first `finishActivity: OH TerminateAbility`
early = the bind runnable was queued BEFORE the RESUMED transaction was queued (hilog line order; both are main-looper
posts, so FIFO): the app's onServiceConnected runs while its Activity is created but not started. On
Android the launch transaction carries start+resume, so a connection posted from onCreate is always delivered after
onResume.
"""
import argparse
import collections
import csv
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'benchmark/2026-10-02-white-vs-lit'))
import population  # noqa: E402

TS = re.compile(r'^(\d\d-\d\d \d\d:\d\d:\d\d\.\d+)\s+(\d+)\s+')


def scan(run):
    pid, out = None, {'posted': '', 'connected': '', 'service': '', 'resumed': '', 'finish': ''}
    lines = {}
    for n, line in enumerate(open(Path(run) / 'hilog.txt', errors='replace')):
        m = TS.match(line)
        if not m:
            continue
        if pid is None:
            if '[B47-SLA] ENTRY bundle=' in line:
                pid = m.group(2)
            continue
        if m.group(2) != pid:
            continue
        t = m.group(1)
        if not out['posted'] and 'bindServiceInstance -> in-process in-app service' in line:
            out['posted'] = t
            lines['posted'] = n
        elif not out['connected'] and '[B8-AMB] connected ' in line:
            out['connected'] = t
            out['service'] = line.split('[B8-AMB] connected ', 1)[1].split(' binder=')[0].strip()
        elif not out['resumed'] and 'ClientTransaction scheduled on main Looper (direct token): RESUMED' in line:
            out['resumed'] = t
            lines['resumed'] = n
        elif not out['finish'] and 'finishActivity: OH TerminateAbility' in line:
            out['finish'] = t
    out['early'] = bool(out['connected'] and 'posted' in lines
                        and ('resumed' not in lines or lines['posted'] < lines['resumed']))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'bind-order.csv'))
    a = ap.parse_args()
    rows, c = [], collections.Counter()
    for k, g, v, run in population.groups():
        s = scan(run)
        rows.append({'key': k, 'group': g, **s})
        c[(g, 'any-connect')] += bool(s['connected'])
        c[(g, 'early')] += s['early']
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    for g in ('WHITE', 'LIT'):
        print(g, 'runs with an in-process connect', c[(g, 'any-connect')], '| connected before RESUMED', c[(g, 'early')])
    for r in rows:
        if r['early']:
            print('  early:', r['group'], r['key'], r['service'], 'posted', r['posted'], 'connected', r['connected'],
                  'resumed', r['resumed'] or '-',
                  'finish', r['finish'] or '-')
    return 0


if __name__ == '__main__':
    sys.exit(main())
