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
NS_SUFFIX = re.compile(r'\.\d+\.\d+$')


def ns_base(ns):
    """Strip the trailing .<pid>.<n> suffix from a namespace string."""
    return NS_SUFFIX.sub('', ns)


def scan(dirs):
    """Aggregate dlopen failure lines across run directories. Returns list of dicts per lib."""
    agg = defaultdict(lambda: {'ns': set(), 'errno': set(), 'keys': set()})
    for d in dirs:
        for hilog in Path(d).rglob('hilog.txt'):
            key = hilog.parent.name
            try:
                for line in hilog.open(encoding='utf-8', errors='replace'):
                    m = LINE.search(line)
                    if m:
                        lib, ns, errno = m.groups()
                        a = agg[lib]
                        a['ns'].add(ns_base(ns))
                        a['errno'].add(errno)
                        a['keys'].add(key)
            except OSError:
                continue
    rows = []
    for lib, a in agg.items():
        rows.append({'lib': lib, 'ns': sorted(a['ns']), 'errno': sorted(a['errno'], key=int),
                     'key_count': len(a['keys']), 'keys': sorted(a['keys'])[:8]})
    rows.sort(key=lambda r: -r['key_count'])
    return rows


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dirs', nargs='+', type=Path)
    ap.add_argument('--json', action='store_true')
    a = ap.parse_args(argv)
    rows = scan(a.dirs)
    if a.json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    else:
        for r in rows:
            print(f"{r['lib']}  {','.join(r['ns'])}  errno={','.join(r['errno'])}  keys={r['key_count']}  {','.join(r['keys'])}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
