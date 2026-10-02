#!/usr/bin/env python3
"""Where was each "no observed termination" key's main thread at t20 on the candidate base (window 5)?

    slow_or_dead.py [--out stages.csv]

Keys and runs: benchmark/2026-10-02-candidate-first-fatal-clusters (clusters.json group no-observed-termination,
sources.json run dirs, first-fatal.json target_pids). t20 = the board mtime of t20.jpeg (record.json remote_stat,
epoch) shown in board local time (UTC+8, the hilog clock). Main thread = the tid that logs
"[B43-BIND] ensureBindApplication start" (ActivityThread on its dedicated pthread). Stage markers, in order
(learned from a lit run, aegis window 2):
  bind_start   [B43-BIND] ensureBindApplication start
  app_done     [B43-BIND] handleBindApplication returned OK      (Application.attach + onCreate returned)
  window_add   [OH_WSA] ENTRY addToDisplayAsUser                  (Activity resumed, ViewRootImpl.setView)
  first_frame  activityResumed (first-frame)                      (first frame drawn, ability transition done)
The captured hilog ends ~5 s before t20 in every run, so each key is judged at cutoff = min(t20, hilog end)
(about t15). Verdict at the cutoff:
  drew               first frame before the cutoff: startup finished; a white t20 is content/render, not start speed
  slow-in-app-init   bind started, Application not returned, main thread logged within 3 s of the cutoff
  slow-in-activity   Application returned, no first frame, main thread logged within 3 s of the cutoff
  idle-before-frame  no first frame and the main thread silent > 3 s before the cutoff (waiting/stuck, not CPU)
  not-launched       no t20 screenshot / no target pid (the launcher never started the app)
main_lines_after_frame counts main-thread hilog lines between the first frame and the cutoff (a busy main thread
after the first frame would point to slow content work).
"""
import argparse
import csv
import datetime as dt
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
CL = WS / 'westlake-harness/benchmark/2026-10-02-candidate-first-fatal-clusters'
BOARD_TZ = dt.timezone(dt.timedelta(hours=8))
MARKS = [('bind_start', '[B43-BIND] ensureBindApplication start'),
         ('app_done', '[B43-BIND] handleBindApplication returned OK'),
         ('window_add', '[OH_WSA] ENTRY addToDisplayAsUser'),
         ('first_frame', 'activityResumed (first-frame)')]
TS = re.compile(r'^(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.(\d{3})\s+(\d+)\s+(\d+)\s')


def ts(line, year):
    m = TS.match(line)
    if not m:
        return None
    mo, d, h, mi, s, ms, pid, tid = m.groups()
    t = dt.datetime(year, int(mo), int(d), int(h), int(mi), int(s), int(ms) * 1000, tzinfo=BOARD_TZ).timestamp()
    return t, pid, tid


def analyse(key, run, pids):
    rec = json.loads((run / 'record.json').read_text())
    shots = {Path(s['path']).name: s for s in rec.get('screenshots', [])}
    t20 = shots.get('t20.jpeg', {})
    t20_epoch = int(t20['remote_stat'].split()[1]) if t20.get('remote_stat') else None
    year = dt.datetime.fromtimestamp(t20_epoch or 0, BOARD_TZ).year
    lines = (run / 'hilog.txt').read_text(errors='replace').split('\n')
    first = {}
    main_tid = None
    child_t0 = None
    last_any = None
    last_main = None
    main_lines = 0
    pidset = {str(p) for p in pids}
    for i, l in enumerate(lines):
        r = ts(l, year)
        if not r:
            continue
        t, pid, tid = r
        last_any = t if last_any is None or t > last_any else last_any
        if pid not in pidset:
            continue
        if child_t0 is None:
            child_t0 = t
        for name, needle in MARKS:
            if name not in first and needle in l:
                first[name] = (t, i + 1)
                if name == 'bind_start':
                    main_tid = tid
        if main_tid and tid == main_tid and (t20_epoch is None or t <= t20_epoch):
            last_main = (t, i + 1, l[31:170])
            if 'first_frame' in first:
                main_lines += 1
    if not t20_epoch or not pidset:
        return {'key': key, 'verdict': 'not-launched', 'run': str(run).replace(str(WS), '$WORKSPACES')}
    cutoff = min(t20_epoch, last_any)
    row = {'key': key, 'pid': ','.join(sorted(pidset)), 'main_tid': main_tid or '',
           't20_board': dt.datetime.fromtimestamp(t20_epoch, BOARD_TZ).strftime('%H:%M:%S') if t20_epoch else '',
           'child_start_to_t20_s': round(t20_epoch - child_t0, 1) if t20_epoch and child_t0 else '',
           'hilog_end_minus_t20_s': round(last_any - t20_epoch, 1) if last_any and t20_epoch else ''}
    for name, _ in MARKS:
        if name in first and first[name][0] <= cutoff:
            row[name + '_s'] = round(first[name][0] - child_t0, 2)
            row[name + '_line'] = first[name][1]
        else:
            row[name + '_s'] = ''
            row[name + '_line'] = first[name][1] if name in first else ''
    if last_main:
        row['main_last_log_before_cutoff_s'] = round(cutoff - last_main[0], 1)
        row['main_last_line'] = last_main[1]
        row['main_last_text'] = last_main[2].strip()
    else:
        row.update(main_last_log_before_cutoff_s='', main_last_line='', main_last_text='')
    row['cutoff_after_child_start_s'] = round(cutoff - child_t0, 1)
    row['main_lines_after_frame'] = main_lines
    quiet = row['main_last_log_before_cutoff_s'] if row['main_last_log_before_cutoff_s'] != '' else 99
    if row['first_frame_s'] != '':
        v = 'drew'
    elif row['bind_start_s'] == '':
        v = 'idle-before-frame' if quiet > 3 else 'slow-before-bind'
    elif quiet > 3:
        v = 'idle-before-frame'
    elif row['app_done_s'] == '':
        v = 'slow-in-app-init'
    else:
        v = 'slow-in-activity'
    row['verdict'] = v
    row['run'] = str(run).replace(str(WS), '$WORKSPACES')
    return row


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'stages.csv'))
    a = ap.parse_args()
    clusters = json.loads((CL / 'clusters.json').read_text())
    keys = next(c['keys'] for c in clusters if c['signature']['kind'] == 'no-observed-termination')
    src = json.loads((CL / 'sources.json').read_text())
    ff = json.loads((CL / 'first-fatal.json').read_text())
    rows = [analyse(k, Path(src[k].replace('$WORKSPACES', str(WS))), ff[k]['target_pids']) for k in keys]
    fields = list(max(rows, key=len))
    with open(a.out, 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, restval='')
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    print(len(rows), 'keys;', Counter(r['verdict'] for r in rows).most_common())
    for r in rows:
        print(f"{r['key']:44} {r['verdict']:18} " + ' '.join(f'{k}={r.get(k, "")}' for k in (
            'bind_start_s', 'app_done_s', 'window_add_s', 'first_frame_s', 'cutoff_after_child_start_s',
            'main_last_log_before_cutoff_s', 'main_lines_after_frame')))
    return 0


if __name__ == '__main__':
    sys.exit(main())
