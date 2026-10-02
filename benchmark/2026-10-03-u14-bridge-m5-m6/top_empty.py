#!/usr/bin/env python3
"""Population check: in which U10.1T8 signing runs is the app's TOP window (highest SceneBoard zOrder among its
sessions still present at t20) one whose cross-copy lookups were all empty (no Surface), and what did the signed t20
verdict say? Tells how an on-top window without a Surface renders.  -> top-empty.txt"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import dialog_surfaces as ds  # noqa: E402

rows = []
for key, group, verdict, run in ds.population.groups():
    pids = set(ds.templates.extract(run)['app_pids'])
    ss = ds.sessions(run, pids)
    lk = ds.static_proof.replay(run)['lookups']
    win = ds.t20_windows(run, pids) or {}
    live = [s for s in ss if s['session'] in win and s['zOrder'] is not None]
    if not live:
        continue
    top = max(live, key=lambda s: s['zOrder'])
    got = [x['outcome'] for x in lk if x['session'] == top['session']]
    if got and all(g == 'empty' for g in got):
        rows.append(f"{key:40s} {group:6s} top={top['session']} type={top['androidType']} "
                    f"rect={'x'.join(map(str, win[top['session']]['rect'][2:]))} below="
                    + ','.join(f"{s['session']}t{s['androidType']}" for s in live if s is not top))
print(f'runs whose top live window has no Surface: {len(rows)}')
print('\n'.join(rows))
