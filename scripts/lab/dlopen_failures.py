#!/usr/bin/env python3
"""Aggregate 'MUSL-LDSO: load <lib> failed' lines from hilog.txt files in run directories.

    dlopen_failures.py <run-dir> [<run-dir> ...] [--json]

For each line 'MUSL-LDSO: load <lib> failed, namespace=<ns>, errno=<n>' (the namespace suffix
'.<pid>.<n>' is stripped, e.g. westlake.anl.app.29496.2 -> westlake.anl.app), group by library
and print: lib  ns  errno-set  key-count  first-8-keys (key = hilog.txt's parent directory).
Sorted by key count, descending.
"""
import argparse, json, re, sys
from pathlib import Path
from collections import defaultdict

LINE = re.compile(r'MUSL-LDSO: load (\S+) failed, namespace=(\S+), errno=(\d+)')
FATAL = re.compile(r'(?:DfxFaultLogger: Pid:(\d+)|JniAbort|exit with signal)')
NS_SUFFIX = re.compile(r'\.\d+\.\d+$')
TS = re.compile(r'^(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d)\.(\d\d\d)')


def ns_base(ns):
    """Strip the trailing .<pid>.<n> suffix from a namespace string."""
    return NS_SUFFIX.sub('', ns)


def _ts_ms(line):
    m = TS.match(line)
    if not m:
        return None
    mo, d, h, mi, s, ms = (int(x) for x in m.groups())
    return (((mo * 30 + d) * 24 + h) * 60 + mi) * 60000 + s * 1000 + ms


def fatal_line(lines):
    """First fatal line (DfxFaultLogger: Pid:N / JniAbort / exit with signal) and its timestamp."""
    for line in lines:
        if FATAL.search(line):
            pid = None
            m = re.search(r'DfxFaultLogger: Pid:(\d+)', line)
            if m:
                pid = int(m.group(1))
            return line, _ts_ms(line), pid
    return None, None, None


def scan(dirs, near_fatal_seconds=None):
    """Aggregate dlopen failure lines across run directories. Returns list of dicts per lib."""
    agg = defaultdict(lambda: {'ns': set(), 'errno': set(), 'keys': set(), 'near_fatal_keys': set()})
    for d in dirs:
        for hilog in Path(d).rglob('hilog.txt'):
            key = hilog.parent.name
            try:
                lines = hilog.read_text(encoding='utf-8', errors='replace').splitlines()
            except OSError:
                continue
            fatal_ts = None
            fatal_pid = None
            if near_fatal_seconds is not None:
                _, fatal_ts, fatal_pid = fatal_line(lines)
            for line in lines:
                m = LINE.search(line)
                if not m:
                    continue
                lib, ns, errno = m.groups()
                a = agg[lib]
                a['ns'].add(ns_base(ns))
                a['errno'].add(errno)
                a['keys'].add(key)
                if near_fatal_seconds is not None and fatal_ts is not None:
                    ts = _ts_ms(line)
                    if ts is not None and fatal_ts - ts <= near_fatal_seconds * 1000 and ts < fatal_ts:
                        parts = line.split()
                        pid = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else None
                        if fatal_pid is None or pid == fatal_pid:
                            a['near_fatal_keys'].add(key)
    rows = []
    for lib, a in agg.items():
        row = {'lib': lib, 'ns': sorted(a['ns']), 'errno': sorted(a['errno'], key=int),
               'key_count': len(a['keys']), 'keys': sorted(a['keys'])[:8]}
        if near_fatal_seconds is not None:
            row['near_fatal_keys'] = len(a['near_fatal_keys'])
        rows.append(row)
    rows.sort(key=lambda r: -r['key_count'])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dirs', nargs='+', type=Path)
    ap.add_argument('--json', action='store_true')
    ap.add_argument('--near-fatal', type=float, default=None, metavar='SECONDS',
                    help='keep only failures within SECONDS before the first fatal line')
    a = ap.parse_args(argv)
    rows = scan(a.dirs, near_fatal_seconds=a.near_fatal)
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            nf = f" near_fatal_keys={r['near_fatal_keys']}" if a.near_fatal is not None else ''
            print(f"{r['lib']}  {','.join(r['ns'])}  errno={','.join(r['errno'])}  keys={r['key_count']}  {','.join(r['keys'])}{nf}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
