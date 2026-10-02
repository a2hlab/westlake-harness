#!/usr/bin/env python3
"""Acceptance of the U13 runtime candidate, the same checks cc-wiki ran for aa149019 (getlongfield-null).

    acceptance.py [--out acceptance.txt]

Binaries: deployed ac59dec0 (U10.1T8 bundle), cc-wiki aa149019 (asset_manager only), this round's m1 and u13
(persisted generation u13-runtime-m1-v1/build). For u13 and m1 against ac59dec0 and aa149019:
  objects    per-object sha from runtime-build-receipt-u13.json (and cc-wiki's receipt)
  exports    llvm-nm -D --defined-only, names
  undefined  llvm-nm -D --undefined-only, names (expected: + dl_iterate_phdr, exported by board libc fd3c4701)
  strings    scripts/lab/deployed_strings_diff.py --deployed ac59dec0 (expected: + the [M1-COPY] marker only)
  open sites scripts/lab/open_site_scan.py --json, findings compared after dropping the library name and @0x address
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

WS = lab_paths.workspaces()
GEN = lab_paths.inputs() / 'generations'
DEPLOYED = GEN / 'u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64/liboh_android_runtime.so'
AA = WS / 'westlake-n10b-build/runtime-n11hr2/candidate/runtime-out/liboh_android_runtime.so'
BUILD = GEN / 'u13-runtime-m1-v1/build'
CAND = {'m1': BUILD / 'm1/runtime-out/liboh_android_runtime.so', 'u13': BUILD / 'u13/runtime-out/liboh_android_runtime.so'}


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    return r.returncode, (r.stdout + r.stderr).replace(str(WS), '$WORKSPACES')


def nm(path, which):
    tool = subprocess.run(['xcrun', '-f', 'llvm-nm'], capture_output=True, text=True).stdout.strip() or 'llvm-nm'
    out = subprocess.run([tool, '-D', which, str(path)], capture_output=True, text=True).stdout
    return {l.split()[-1] for l in out.splitlines() if l.strip()}


def open_sites(path, tmp):
    j = tmp / (path.parent.parent.name + '-sites.json')
    rc, _ = run([sys.executable, REPO / 'scripts/lab/open_site_scan.py', path, '--json', j])
    data = json.loads(j.read_text())
    rows = data if isinstance(data, list) else data.get('findings', data.get('sites', []))
    norm = sorted(re.sub(r'@0x[0-9a-f]+', '@', re.sub(r'^[^:]*:', '', json.dumps(r, sort_keys=True))) for r in rows)
    return len(rows), norm


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'acceptance.txt'))
    a = ap.parse_args()
    rec = json.loads((HERE / 'runtime-build-receipt-u13.json').read_text())['variants']
    cw = json.loads((REPO / 'benchmark/2026-10-02-getlongfield-null/build/runtime-build-receipt-N11HR2.json').read_text())['variants']['candidate']
    log, ok = [], True
    sha = lambda p: subprocess.run(['shasum', '-a', '256', str(p)], capture_output=True, text=True).stdout.split()[0]
    log.append(f'deployed {sha(DEPLOYED)}\naa149019 {sha(AA)}\nm1       {sha(CAND["m1"])}\nu13      {sha(CAND["u13"])}')
    d = lambda x, y: sorted(k for k in set(x) | set(y) if x.get(k) != y.get(k))
    log.append(f"## objects ({len(rec['control']['objects'])})")
    log.append(f"control == deployed ac59dec0: {rec['control']['sha256'] == sha(DEPLOYED)}")
    log.append(f"m1  vs control: {d(rec['m1']['objects'], rec['control']['objects'])}")
    log.append(f"u13 vs control: {d(rec['u13']['objects'], rec['control']['objects'])}")
    log.append(f"u13 vs aa149019: {d(rec['u13']['objects'], cw['objects'])}")
    ok &= d(rec['u13']['objects'], cw['objects']) == ['android_graphics_compat_shim.o']
    exp_d, exp_u = nm(DEPLOYED, '--defined-only'), nm(DEPLOYED, '--undefined-only')
    tmp = BUILD.parent / 'acceptance-tmp'
    tmp.mkdir(exist_ok=True)
    base_n, base_sites = open_sites(DEPLOYED, tmp)
    for name, path in CAND.items():
        cd, cu = nm(path, '--defined-only'), nm(path, '--undefined-only')
        log.append(f'## {name} vs deployed ac59dec0')
        log.append(f'exports: +{sorted(cd - exp_d)} -{sorted(exp_d - cd)}')
        log.append(f'undefined: +{sorted(cu - exp_u)} -{sorted(exp_u - cu)}')
        ok &= cd == exp_d and cu - exp_u == {'dl_iterate_phdr'} and not exp_u - cu
        rc, out = run([sys.executable, REPO / 'scripts/lab/deployed_strings_diff.py', path, '--deployed', DEPLOYED])
        log.append(f'deployed_strings_diff rc={rc}:\n' + out.rstrip())
        # Expected: the one new marker; every other ADDED has an equal-length DROPPED twin (bytes that only look like
        # text and move with the layout: .rodata jump-table offsets, or a readelf "[ offset]" label pushed by exactly
        # len(marker)+1 bytes).
        lit = lambda s: eval(s) if s[:1] in '\'"' else s
        added = [lit(l[8:]) for l in out.splitlines() if l.startswith('ADDED')]
        dropped = [lit(l[8:]) for l in out.splitlines() if l.startswith('DROPPED')]
        marker = [s for s in added if s.startswith('[M1-COPY]')]
        twins = sorted(len(s) for s in added if not s.startswith('[M1-COPY]')) == sorted(len(s) for s in dropped)
        labels = [(int(re.match(r'\[\s*([0-9a-f]+)\]', s).group(1), 16)) for s in added + dropped
                  if re.match(r'\[\s*[0-9a-f]+\] ', s)]
        shift = (max(labels) - min(labels)) if len(labels) == 2 else None
        explained = len(marker) == 1 and twins and (shift is None or shift == len(marker[0]) + 1)
        log.append(f'strings explained: marker added {len(marker)}, other added/dropped are equal-length twins: {twins}, '
                   f'readelf label shift {hex(shift) if shift is not None else "n/a"} == len(marker)+1 '
                   f'{hex(len(marker[0]) + 1) if marker else "n/a"}: {explained}')
        ok &= explained
        n, sites = open_sites(path, tmp)
        same = sites == base_sites
        log.append(f'open_site_scan: {n} vs {base_n}; normalized identical: {same}')
        ok &= same and n == base_n
    log.append(f'VERDICT: {"PASS" if ok else "CHECK"}')
    Path(a.out).write_text('\n'.join(log) + '\n')
    print('\n'.join(log))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
