#!/usr/bin/env python3
"""Per-function size comparison of two bridge builds (llvm-nm -S -C, text symbols incl. local): the cheapest
whole-binary check that the rebuilt code is the deployed code, function by function.

    fnsize.py <deployed .so> <rebuilt .so>
"""
import subprocess
import sys


def sizes(path, nm):
    out = subprocess.run([nm, '-S', '--defined-only', '-C', path], capture_output=True, text=True).stdout
    d = {}
    for line in out.splitlines():
        f = line.split(' ', 3)
        if len(f) == 4 and f[2] in 'tTwW':
            d[f[3]] = int(f[1], 16)
    return d


def main():
    old, new = sys.argv[1:3]
    nm = subprocess.run(['xcrun', '-f', 'llvm-nm'], capture_output=True, text=True).stdout.strip() or 'llvm-nm'
    a, b = sizes(old, nm), sizes(new, nm)
    common = set(a) & set(b)
    diff = sorted(k for k in common if a[k] != b[k])
    print(f'functions (incl. local, demangled): deployed {len(a)}, rebuilt {len(b)}, common {len(common)}, '
          f'same size {len(common) - len(diff)}, size differs {len(diff)}, only deployed {len(set(a) - set(b))}, '
          f'only rebuilt {len(set(b) - set(a))}')
    for k in diff:
        print('  SIZE', a[k], '->', b[k], k[:160])
    for k in sorted(set(a) - set(b)):
        print('  ONLY-DEPLOYED', a[k], k[:160])
    for k in sorted(set(b) - set(a)):
        print('  ONLY-REBUILT', b[k], k[:160])
    for ns in ('fn03::', 'SessionStageAdapter::', 'OHWindowManagerClient::', 'AbilitySchedulerAdapter::'):
        ka, kb = {k for k in a if ns in k}, {k for k in b if ns in k}
        c = ka & kb
        print(f'  [{ns[:-2]}] deployed {len(ka)} rebuilt {len(kb)} common {len(c)} '
              f'same-size {sum(1 for k in c if a[k] == b[k])} only-deployed {len(ka - kb)} only-rebuilt {len(kb - ka)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
