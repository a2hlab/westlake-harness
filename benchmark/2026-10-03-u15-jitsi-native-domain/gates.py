#!/usr/bin/env python3
"""Pairwise ELF gates for the jitsi native-domain change.

    gates.py <a.so> <b.so> [--label X]

dynsym (defined + UND, name@version), NEEDED/SONAME, open sites (scripts/lab/open_site_scan.py --json), dlopen/dlsym
call counts, strings -a -n 6 set difference (path-bearing strings listed separately), equiv.py function summary."""
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
EQUIV = REPO / 'benchmark/2026-10-02-u14-bridge-r1r3/equiv.py'
OSS = REPO / 'scripts/lab/open_site_scan.py'
PATHY = re.compile(r'/|\.c$|\.h$|\.inc$')


def run(*a):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True).stdout


def dynsym(f):
    out = set()
    for l in run('llvm-readelf', '--dyn-syms', '-W', f).splitlines()[3:]:
        p = l.split()
        if len(p) >= 8:
            out.add(('U ' if p[6] == 'UND' else 'D ') + p[7])
    return out


def needed(f):
    return re.findall(r'\((?:NEEDED|SONAME)\)\s+\S+ \S+: \[(.+?)\]', run('llvm-readelf', '-d', f))


def sites(f):
    with tempfile.TemporaryDirectory() as t:
        j = Path(t) / 'o.json'
        subprocess.run(['python3', str(OSS), str(f), '--json', str(j)], capture_output=True, text=True)
        d = json.loads(j.read_text()) if j.exists() else {}
    rows = d.get('findings') or []
    name = Path(f).name
    norm = sorted(re.sub(r'0x[0-9a-f]+', '0x#', json.dumps(r, sort_keys=True).replace(name + ':', ''))
                  for r in rows) if isinstance(rows, list) else []
    return norm


def calls(f, name):
    return len(re.findall(rf'\bb(?:l)?\s+0x[0-9a-f]+ <{name}@plt>', run('llvm-objdump', '-d', '--no-show-raw-insn', f)))


def main():
    a, b = sys.argv[1], sys.argv[2]
    da, db = dynsym(a), dynsym(b)
    print(f'dynsym: {len(da)} vs {len(db)}; only a {sorted(da - db)}; only b {sorted(db - da)}')
    print(f'NEEDED/SONAME equal: {needed(a) == needed(b)} {needed(b)}')
    sa, sb = sites(a), sites(b)
    print(f'open sites (open_site_scan, position-free): {len(sa)} vs {len(sb)}; equal: {sa == sb}')
    for n in ('dlopen', 'dlopen_ns', 'dlsym', 'android_dlopen_ext'):
        print(f'  calls to {n}: {calls(a, n)} vs {calls(b, n)}')
    ra = set(run('strings', '-a', '-n', '6', a).splitlines())
    rb = set(run('strings', '-a', '-n', '6', b).splitlines())
    add, rem = sorted(rb - ra), sorted(ra - rb)
    print('strings added (non-path):', [s for s in add if not PATHY.search(s)])
    print('strings added that name a package dir:', [s for s in add if re.fullmatch(r'/[a-z0-9_.]+/', s)])
    print('strings removed (non-path):', [s for s in rem if not PATHY.search(s)])
    print(f'strings added/removed with a path: {sum(bool(PATHY.search(s)) for s in add)}/{sum(bool(PATHY.search(s)) for s in rem)}')
    eq = run('python3', EQUIV, a, b).splitlines()
    print(eq[0] if eq else 'equiv: no output')
    for l in eq[1:]:
        if re.match(r'\s+(DIFF|ONLY)', l):
            print(l[:170])


if __name__ == '__main__':
    main()
