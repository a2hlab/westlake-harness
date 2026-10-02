#!/usr/bin/env python3
"""Did U12's JAR predictions move the first fatal? The six predicted keys, U12 windows 1-4 vs U10.1T8 window 5.

    u12_check.py [--out u12-check.json]

For each of notepad, fd-client, x, clipboardeditor, packlist, moodcairns:
  U12 runs     every record.json under westlake-harness-u7-executor/.../2026-10-02-u12-final-assembly/window{1..4}
               (smoke excluded); the board's runtime-fingerprint.txt must show runtime jar 0482c9b1 (U12 r2)
  U10.1T8 run  the key's source in 2026-10-02-candidate-first-fatal-clusters/sources.json
scripts/lab/first_fatal.py on each run directory, scripts/lab/cluster_first_cause.py over the combined result
(keys suffixed @u10.1t8 / @u12w<N>). A key without a U12 run is reported as not-run, not as unmoved.
"""
import argparse
import glob
import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
KEYS = ['cv2-com-nononsenseapps-notepad', 'fd-client', 'x', 'cv2-com-trianguloy-clipboardeditor',
        'cv2-com-nbossard-packlist', 'cv2-com-lcdcode-moodcairns']
U12 = WS / 'westlake-harness-u7-executor/benchmark/2026-10-02-u12-final-assembly'
SOURCES = REPO / 'benchmark/2026-10-02-candidate-first-fatal-clusters/sources.json'


def first_fatal(d):
    r = subprocess.run([sys.executable, str(REPO / 'scripts/lab/first_fatal.py'), str(d)], capture_output=True,
                       text=True, timeout=600)
    try:
        return json.loads(r.stdout)
    except Exception:
        return {'status': 'unknown', 'error': (r.stderr or r.stdout)[-300:]}


def summary(ff):
    t = (ff.get('terminal') or {}).get('event') or {}
    root = (ff.get('root') or {}).get('event') or {}
    frames = [f['message'].removeprefix('[stderr] ').strip() for f in (ff.get('root') or {}).get('frames', [])[:3]]
    return {'status': ff.get('status'), 'terminal_kind': (ff.get('terminal') or {}).get('kind'),
            'terminal_line': t.get('line'), 'terminal': (t.get('message') or '')[:220],
            'root': (root.get('message') or '')[:220], 'frames': frames}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'u12-check.json'))
    a = ap.parse_args()
    src = json.loads(SOURCES.read_text())
    combined, report = {}, {}
    for k in KEYS:
        entry = {'u10.1t8': None, 'u12': []}
        s = src.get(k)
        if s:
            d = Path(s.replace('$WORKSPACES', str(WS)))
            ff = first_fatal(d)
            combined[f'{k}@u10.1t8'] = ff
            entry['u10.1t8'] = {'run': s, **summary(ff)}
        for rec in sorted(glob.glob(str(U12 / 'window*/**/runner/*/*/*/' / k / 'record.json'), recursive=True)):
            d = Path(rec).parent
            if '/smoke/' in rec:
                continue
            fp = (d.parent / 'runtime-fingerprint.txt')
            jar = ''
            if fp.exists():
                for line in fp.read_text().splitlines():
                    if line.endswith('/oh-adapter-runtime.jar'):
                        jar = line.split()[0][:8]
            w = next(p for p in d.parts if p.startswith('window'))
            ff = first_fatal(d)
            combined[f'{k}@u12{w}'] = ff
            entry['u12'].append({'run': str(d).replace(str(WS), '$WORKSPACES'), 'window': w, 'runtime_jar': jar,
                                 **summary(ff)})
        report[k] = entry
    (HERE / 'u12-check-first-fatal.json').write_text(json.dumps(combined, indent=1, ensure_ascii=False))
    c = subprocess.run([sys.executable, str(REPO / 'scripts/lab/cluster_first_cause.py'),
                        str(HERE / 'u12-check-first-fatal.json')], capture_output=True, text=True)
    (HERE / 'u12-check-clusters.json').write_text(c.stdout)
    Path(a.out).write_text(json.dumps(report, indent=1, ensure_ascii=False))
    for k, e in report.items():
        old = e['u10.1t8']
        print(f'== {k}')
        print('   U10.1T8:', (old or {}).get('terminal_kind'), '|', ((old or {}).get('root') or (old or {}).get('terminal') or '')[:160])
        if not e['u12']:
            print('   U12: NOT RUN in windows 1-4')
        for r in e['u12']:
            print(f"   U12 {r['window']} jar={r['runtime_jar']}:",
                  r['terminal_kind'], '|', (r['root'] or r['terminal'])[:160])
    return 0


if __name__ == '__main__':
    sys.exit(main())
