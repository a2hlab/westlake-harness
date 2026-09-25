#!/usr/bin/env python3
"""#46: which targets actually keep the tt crypto pair out of the default namespace.

A library ends up in the isolated Android namespace iff it went through NativeLoader
(System.loadLibrary) AND is a target, OR it is a DT_NEEDED of an already-isolated
library. So the tt pair stays single iff every APK library that DIRECTLY DT_NEEDEDs it
is isolated. For each such direct dependant we find the NativeLoader-reachable roots
whose forward DT_NEEDED closure covers it; a direct dependant with no NativeLoader root
can only arrive via native dlopen and CANNOT be routed by targets -> needs the fallback.

usage: tt_cover.py <apk-lib-dir> <nativeloader-list-file> <current-targets-colon-list>
"""
import subprocess
import sys
from pathlib import Path

lib_dir = Path(sys.argv[1])
nl = {l.strip() for l in open(sys.argv[2]) if l.strip()}
current = set(filter(None, sys.argv[3].split(':')))
SEED = {'libttcrypto.so', 'libttboringssl.so'}


def needed(p):
    out = subprocess.run(['readelf', '-d', str(p)], capture_output=True, text=True).stdout
    return {l.split('[', 1)[1].split(']', 1)[0] for l in out.splitlines() if '(NEEDED)' in l}


libs = {p.name: needed(p) for p in lib_dir.glob('*.so')}

# direct dependants of the pair (first ring of the reverse closure)
direct = {n for n, d in libs.items() if d & SEED}

# forward DT_NEEDED closure of a set (only APK libs)
def fwd(roots):
    seen, stack = set(), list(roots)
    while stack:
        x = stack.pop()
        if x in seen or x not in libs:
            continue
        seen.add(x)
        stack += [d for d in libs[x] if d in libs]
    return seen

# reverse DT_NEEDED reach (who can pull x in), APK only
rev = {n: set() for n in libs}
for n, d in libs.items():
    for dep in d:
        if dep in rev:
            rev[dep].add(n)

def rev_roots(x):
    seen, stack, roots = set(), [x], set()
    while stack:
        y = stack.pop()
        if y in seen:
            continue
        seen.add(y)
        callers = rev[y]
        if not callers and y in nl:
            roots.add(y)
        for c in callers:
            stack.append(c)
        if y in nl:
            roots.add(y)
    return roots

print('# direct DT_NEEDED dependants of the tt crypto pair:', len(direct))
need_targets = set()
uncovered = []
for d in sorted(direct):
    roots = {r for r in rev_roots(d) if r in nl}
    tag = 'NativeLoader-root' if d in nl else ('via ' + ','.join(sorted(roots)) if roots else 'NO NativeLoader root')
    print(f'  {d:26} {tag}')
    if d in nl:
        need_targets.add(d)
    elif roots:
        need_targets |= roots
    else:
        uncovered.append(d)

print()
print('# minimal target set (NativeLoader roots that must be isolated):')
for t in sorted(need_targets):
    print(f'  {t:26}{"  (already target)" if t in current else "  ADD"}')
missing = sorted(need_targets - current)
print()
print('# libs to ADD to WESTLAKE_ANDROID_NATIVE_TARGETS:', ' '.join(missing) or '(none)')
print('# direct dependants with NO NativeLoader root (targets cannot route -> fallback):',
      ' '.join(uncovered) or '(none)')
print()
print('WESTLAKE_ANDROID_NATIVE_TARGETS=' + ':'.join(sorted(current | need_targets,
      key=lambda s: (s not in current, s))))
