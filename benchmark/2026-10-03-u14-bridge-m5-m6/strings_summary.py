#!/usr/bin/env python3
"""Classify deployed_strings_diff output: text strings vs non-text layout bytes (a printable run that is mostly '.',
i.e. code/rodata bytes that happen to pass the strings filter). Against 84695d62 the baseline candidate's own diff
(../2026-10-02-u14-bridge-r1r3/diff-candidate/strings-846-vs-u14.txt) is subtracted first.   -> diffs/strings-summary.txt"""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BASE = HERE.parent / '2026-10-02-u14-bridge-r1r3' / 'diff-candidate' / 'strings-846-vs-u14.txt'
ENT = re.compile(r"^(DROPPED|ADDED)\s+'(.*)'$")


def entries(p):
    return {(m.group(1), m.group(2)) for m in map(ENT.match, Path(p).read_text().splitlines()) if m}


def text(s):
    return s.count('.') * 3 < len(s) and re.search(r'[A-Za-z]{3}', s) is not None


base = entries(BASE)
out = []
for ref in ('e34de8ab', '84695d62'):
    for v in ('m5', 'm6', 'm5m6', 'm1m5m6'):
        e = entries(HERE / 'diffs' / f'strings-{ref}-vs-{v}.txt')
        if ref == '84695d62':
            e -= base
        t = sorted(x for x in e if text(x[1]))
        n = len(e) - len(t)
        out.append(f'== {v} vs {ref}' + (' (minus the baseline candidate diff vs 846)' if ref == '84695d62' else '')
                   + f': text {len(t)}, non-text layout bytes {n}')
        out += [f'   {k:7s} {s}' for k, s in t]
Path(HERE / 'diffs' / 'strings-summary.txt').write_text('\n'.join(out) + '\n')
print('\n'.join(out))
