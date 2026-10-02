#!/usr/bin/env python3
"""Who finishes an Activity while OH still has its foreground pending, and is that Activity the top one?

    closes.py [--out closes.csv]

Per U10.1T8 signing run (white-vs-lit population.groups(), window launch-3 s .. min(t20, hilog end)):
  requested   SceneBoard OnRequestSceneSession abilities of the app, in order (the last one = top)
  closes      AMS `CloseUIAbility call: <bundle>/<ability>`, each followed (same ms) by `pending state dropped CLOSE: N`
              when OH still had a pending state -> the close is NOT executed (ui_ability_lifecycle_manager.cpp:
              CloseUIAbility sets pending BACKGROUND and returns; termination then needs the app's BACKGROUND and
              INITIAL acknowledgements, which route-A never sends)
  foreground  AMS ForegroundLifecycle order; an ability foregrounded AFTER the dropped close covers it
Classes:
  top_dropped     the dropped close is the top (last requested) ability and nothing was foregrounded after it
                  -> its windowless scene stays on top, the caller stays backgrounded (M6 white)
  under_dropped   a dropped close of an ability that something else later covered (harmless leak: antennapod Splash)
  no_dropped      no dropped close
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
import templates  # noqa: E402

REQ = re.compile(r'OnRequestSceneSession: \[([^,\]]+), ([^,\]]+), ([^\]]+)\]')
CLOSE = re.compile(r'CloseUIAbility call: ([^/\s]+)/(\S+)')
DROP = re.compile(r'pending state dropped CLOSE: (\d+)')
FG = re.compile(r'ForegroundLifecycle (\S+)')


def scan(run):
    t = templates.extract(run)
    pkg = t['pkg']
    ev = []
    for line in open(Path(run) / 'hilog.txt', errors='replace'):
        if 'OnRequestSceneSession' not in line and 'CloseUIAbility' not in line and 'pending state dropped' not in line \
                and 'ForegroundLifecycle' not in line:
            continue
        m = templates.LINE.match(line)
        if not m:
            continue
        ts = templates.epoch(m.groups(), 2026)
        if t['start'] is None or ts < t['start'] or ts > t['cutoff']:
            continue
        msg = m.group(11)
        if (r := REQ.search(msg)) and r.group(1).strip() == pkg:
            ev.append(('req', r.group(3).strip().split('.')[-1]))
        elif (c := CLOSE.search(msg)) and c.group(1) == pkg:
            ev.append(('close', c.group(2).split('.')[-1]))
        elif DROP.search(msg) and ev and ev[-1][0] == 'close':
            ev[-1] = ('dropped', ev[-1][1])
        elif (f := FG.search(msg)) and pkg in f.group(1):
            ev.append(('fg', f.group(1).split('/')[-1].split('.')[-1]))
    requested = [a for k, a in ev if k == 'req']
    top = requested[-1] if requested else None
    cls = 'no_dropped'
    detail = []
    for i, (k, a) in enumerate(ev):
        if k != 'dropped':
            continue
        covered = any(k2 == 'fg' and a2 != a for k2, a2 in ev[i + 1:])
        if a == top and not covered:
            cls = 'top_dropped'
        elif cls != 'top_dropped':
            cls = 'under_dropped'
        detail.append(f'{a}{"(top)" if a == top else ""}{"+covered" if covered else ""}')
    return {'requested': requested, 'top': top, 'class': cls, 'dropped': detail,
            'events': ' > '.join(f'{k}:{a}' for k, a in ev)}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'closes.csv'))
    a = ap.parse_args()
    rows, c = [], collections.Counter()
    for k, g, v, run in population.groups():
        s = scan(run)
        c[(g, s['class'])] += 1
        rows.append({'key': k, 'group': g, 'verdict': v, 'class': s['class'], 'top': s['top'],
                     'dropped': ' '.join(s['dropped']), 'events': s['events'][:400]})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r['class'], r['group'], r['key'])))
    for g in ('WHITE', 'LIT'):
        n = sum(v for (gg, _), v in c.items() if gg == g)
        print(g, n, {cls: c[(g, cls)] for cls in ('top_dropped', 'under_dropped', 'no_dropped')})
    for r in rows:
        if r['class'] == 'top_dropped':
            print('  top_dropped:', r['group'], r['verdict'], r['key'], r['dropped'], '|', r['events'][:160])
    return 0


if __name__ == '__main__':
    sys.exit(main())
