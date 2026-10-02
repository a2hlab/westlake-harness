#!/usr/bin/env python3
"""Every 'relocating failed: symbol not found' line in every U12 stage-A and U13 stage-A run (all keys, lit or not),
grouped by key / domain / symbol, with whether that symbol is in the fd-meet gap set and whether the line is the key's
first-fatal wall (2026-10-03-u13-first-fatal-clusters per-run.json; lit runs are non-fatal by definition).

    scan_runs.py [--json out]
Domain: native (13-package native cluster, deployed libapp_native_loader eebd62f2), flutter (6 Flutter packages),
normal (everything else)."""
import argparse
import glob
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
EXE = WS / 'westlake-harness-u7-executor/benchmark'
RUNS = [EXE / '2026-10-02-u12-final-assembly', EXE / '2026-10-03-u13-stage-a-plan']
NATIVE = ['com.ichi2.anki', 'com.unciv.app', 'app.organicmaps', 'com.nextcloud.client', 'com.mcdonalds.app',
          'io.anuke.mindustry', 'com.emn8.mobilem8.nativeapp.bk', 'im.vector.app', 'org.mozilla.firefox',
          'org.mozilla.fennec_fdroid', 'org.videolan.vlc', 'org.ppsspp.ppsspp', 'com.shatteredpixel.shatteredpixeldungeon']
FLUTTER = ['org.localsend.localsend_app', 'com.example.kitchenowl', 'chat.fluffy.fluffychat', 'app.alextran.immich',
           'deckers.thibault.aves.libre', 'com.adilhanney.saber']
GAP = {'__register_atfork', 'android_set_abort_message', '__assert2', '__errno', 'strtoll_l', 'strtoull_l',
       '__system_property_get', '__sF', '__cmsg_nxthdr', '__FD_SET_chk', '__FD_ISSET_chk', '__FD_CLR_chk', '__open_2',
       '__gnu_strerror_r'}
LINE = re.compile(r'relocating failed: symbol not found\. dso=(\S+) s=(\S+) use_vna_hash=(\d) van_hash=(\w+)')


def domain(dso):
    if any(f'/{p}/' in dso for p in NATIVE):
        return 'native'
    if any(f'/{p}/' in dso for p in FLUTTER):
        return 'flutter'
    return 'normal'


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--json', type=Path)
    a = ap.parse_args()
    walls = {r['key']: r['wall'] for r in json.loads((REPO / 'benchmark/2026-10-03-u13-first-fatal-clusters/per-run.json').read_text())}
    agg = defaultdict(lambda: {'runs': set(), 'dsos': set(), 'domain': '', 'first_fatal': False})
    nruns = 0
    for root in RUNS:
        for h in glob.glob(str(root / '**/runner/*/*/*/*/hilog.txt'), recursive=True):
            if '/smoke/' in h:
                continue
            nruns += 1
            key = Path(h).parent.name
            gen = 'u13' if 'u13' in h else 'u12'
            for m in LINE.finditer(Path(h).read_text(errors='replace')):
                dso, sym = m.group(1), m.group(2)
                e = agg[(key, sym)]
                e['runs'].add(gen)
                e['dsos'].add(dso.rsplit('/', 1)[-1])
                e['domain'] = domain(dso)
                e['first_fatal'] |= sym in (walls.get(key) or '')
    rows = [{'key': k, 'symbol': s, 'in_meet_gap': s in GAP, 'domain': v['domain'], 'generations': sorted(v['runs']),
             'dsos': sorted(v['dsos']), 'first_fatal_wall': v['first_fatal']} for (k, s), v in sorted(agg.items())]
    print(f'runs scanned: {nruns}; (key, symbol) pairs: {len(rows)}')
    for r in rows:
        if r['domain'] == 'normal':
            print(f"NORMAL {r['key']:36s} {r['symbol']:28s} gap={r['in_meet_gap']!s:5s} fatal_wall={r['first_fatal_wall']!s:5s} {','.join(r['generations'])} {','.join(r['dsos'])[:80]}")
    other = defaultdict(set)
    for r in rows:
        if r['domain'] != 'normal':
            other[(r['domain'], r['key'])].add(r['symbol'])
    for (d, k), s in sorted(other.items()):
        print(f'{d.upper():7s} {k:36s} {sorted(s)}')
    if a.json:
        a.json.write_text(json.dumps({'runs_scanned': nruns, 'rows': rows}, indent=1) + '\n')


if __name__ == '__main__':
    main()
