#!/usr/bin/env python3
"""Bind-status of each key from hilog.txt files in run directories.

    bind_status.py <run-dir> [<run-dir> ...] [--all] [--json]

Per hilog.txt (key = parent directory name; multiple runs of the same key all count):
  bound = contains '[B43-BIND] handleBindApplication returned OK'
  fatal = contains 'DfxFaultLogger: Pid:' or 'JniAbort' or 'exit with signal'
  status = bound | fatal_before_bind (fatal but not bound) | unbound_at_capture (neither)
Per key: runs, bound_runs, fatal_runs, key_status (any bound run -> bound; else any fatal run
-> fatal_before_bind; else unbound_at_capture). Default prints only non-bound keys; --all prints
every key; --json prints a list.
"""
import argparse, json, sys
from pathlib import Path
from collections import defaultdict

BOUND = '[B43-BIND] handleBindApplication returned OK'
FATALS = ('DfxFaultLogger: Pid:', 'JniAbort', 'exit with signal')


def scan(dirs):
    """Per-key bind status across run directories. Returns list of dicts per key."""
    agg = defaultdict(lambda: {'runs': 0, 'bound_runs': 0, 'fatal_runs': 0})
    for d in dirs:
        for hilog in Path(d).rglob('hilog.txt'):
            key = hilog.parent.name
            try:
                text = hilog.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            a = agg[key]
            a['runs'] += 1
            if BOUND in text:
                a['bound_runs'] += 1
            if any(f in text for f in FATALS):
                a['fatal_runs'] += 1
    rows = []
    for key, a in sorted(agg.items()):
        if a['bound_runs']:
            status = 'bound'
        elif a['fatal_runs']:
            status = 'fatal_before_bind'
        else:
            status = 'unbound_at_capture'
        rows.append({'key': key, 'runs': a['runs'], 'bound_runs': a['bound_runs'],
                     'fatal_runs': a['fatal_runs'], 'key_status': status})
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dirs', nargs='+', type=Path)
    ap.add_argument('--all', action='store_true')
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = scan(a.dirs)
    if not a.all:
        rows = [r for r in rows if r['key_status'] != 'bound']
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            print(f"{r['key']}  runs={r['runs']} bound_runs={r['bound_runs']} fatal_runs={r['fatal_runs']} {r['key_status']}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
