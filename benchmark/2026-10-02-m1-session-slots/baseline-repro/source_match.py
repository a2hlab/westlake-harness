#!/usr/bin/env python3
"""Can the deployed bridge 84695d62 be rebuilt byte-identically from any source we have? Static answer, before a build.

    source_match.py [--out source-match.txt]

1) Window client version: every local copy of oh_window_manager_client.cpp (found by `grep -rl 'refusing orphan
   child'` under $WORKSPACES, plus this repo's bms/src and real-work's oh61-v7 snapshot) is compared two ways with the
   deployed bridge's strings: its window-client string literals (adjacent literals joined) missing from the binary,
   and the binary's window-client strings (createSession / getOhNativeWindow / destroySession / WMClient. /
   getRSSurfaceNode prefixes) missing from the source.
2) Per translation unit of the hardened compile_oh_adapter_bridge_arm64.sh source set (window/ and fn03 from the
   closest oh61-v7 snapshot, the rest from bms/src): how many of its >= 16-char literals are in the binary; a TU with
   >= 3 literals and none in the binary was not part of the deployed build.
3) OHCanvasRenderer member functions in the binary's dynamic symbols.
"""
import argparse
import glob
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO / 'scripts/lab'))
import lab_paths  # noqa: E402

W = lab_paths.workspaces()
BRIDGE = lab_paths.inputs() / 'generations/u10.1-t8-rerun-j5ae3dd29-s2f365a75-v3/bundle/native/payload/android/lib64/liboh_adapter_bridge.so'
A = REPO / 'bms/src/adapter'
OH61 = W / '01.OH61AOSP16/real-work/src/adapter/sources/oh61-v7-b2133b5b'
STR = re.compile(r'"((?:[^"\\]|\\.)*)"')
WC = re.compile(r'^(createSession|getOhNativeWindow|destroySession|WMClient\.|getRSSurfaceNode)')


def literals(path):
    raw = re.sub(r'"\s*\n\s*"', '', open(path, errors='replace').read())
    raw = re.sub(r'"\s+"', '', raw)
    return [m.group(1) for m in STR.finditer(raw)]


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'source-match.txt'))
    a = ap.parse_args()
    out = []
    sha = hashlib.sha256(BRIDGE.read_bytes()).hexdigest()
    assert sha.startswith('84695d62'), sha
    strs = subprocess.run(['strings', '-a', '-n', '6', str(BRIDGE)], capture_output=True, text=True).stdout
    dep = [s for s in strs.splitlines() if WC.match(s)]
    out.append(f'# deployed bridge {sha}; window-client strings in binary: {len(dep)}')
    cands = subprocess.run(['grep', '-rl', '--include=oh_window_manager_client.cpp', 'refusing orphan child', str(W)],
                           capture_output=True, text=True).stdout.split()
    cands += [str(A / 'framework/window/jni/oh_window_manager_client.cpp'),
              str(OH61 / 'framework/window/jni/oh_window_manager_client.cpp')]
    seen = {}
    for c in cands:
        if not os.path.isfile(c):
            continue
        h = hashlib.sha256(Path(c).read_bytes()).hexdigest()[:12]
        if h in seen:
            seen[h][0] += 1
            continue
        lits = literals(c)
        joined = '\n'.join(lits).replace('%{public}', '%')
        src_wc = [x for x in lits if WC.match(x)]
        miss_bin = [x for x in src_wc if x not in strs]
        miss_src = [s for s in dep if s.replace('%{public}', '%') not in joined]
        seen[h] = [1, c.replace(str(W), '$WORKSPACES'), miss_bin, miss_src]
    out.append('## 1) window client versions (source-not-in-binary / binary-not-in-source)')
    for h, (n, c, mb, ms) in sorted(seen.items(), key=lambda x: len(x[1][2]) + len(x[1][3])):
        out.append(f'{h} copies={n} src-not-in-bin={len(mb)} bin-not-in-src={len(ms)} {c}')
        out += [f'    src-only: {x[:110]}' for x in mb] + [f'    bin-only: {x[:110]}' for x in ms]
    out.append('## 2) hardened source set, per TU: literals (>=16 chars) found in the binary')
    srcs = []
    for d in 'core activity window surface broadcast contentprovider'.split():
        sd = OH61 / 'framework/window/jni' if d == 'window' else A / f'framework/{d}/jni'
        for s in sorted(glob.glob(str(sd / '*.cpp'))):
            b = os.path.basename(s)
            if '-untested-on-' in b or b == 'display_manager_adapter_jni.cpp':
                continue
            srcs.append(s)
    srcs += [str(A / 'framework/window/jni/display_manager_adapter_jni.cpp'),
             str(OH61 / 'framework/window/jni/display_manager_adapter_jni.cpp') + '  (oh61 copy, excluded by the script)',
             str(OH61 / 'framework/activity/core/fn03_lifecycle_core.cpp')]
    for s in srcs:
        path = s.split('  (')[0]
        lits = {re.split(r'%|\\', x)[0].strip() for x in literals(path)}
        lits = {x for x in lits if len(x) >= 16}
        hit = sum(x in strs for x in lits)
        tag = 'NONE-IN-BINARY' if len(lits) >= 3 and hit == 0 else ''
        out.append(f'{hit:4}/{len(lits):<4} {tag:15} {s.replace(str(W), "$WORKSPACES").replace(str(REPO) + "/", "")}')
    out.append('## 3) OHCanvasRenderer members in the binary dynamic symbols')
    nm = subprocess.run(['xcrun', '-f', 'llvm-nm'], capture_output=True, text=True).stdout.strip() or 'nm'
    syms = subprocess.run([nm, '-D', '-C', str(BRIDGE)], capture_output=True, text=True).stdout
    for fn in ('drawRect', 'drawText', 'drawPath', 'drawBitmap', 'clipRect', 'clipPath', 'drawColor'):
        out.append(f'OHCanvasRenderer::{fn}: {sum(1 for l in syms.splitlines() if "OHCanvasRenderer::" + fn in l)}')
    Path(a.out).write_text('\n'.join(out) + '\n')
    print('\n'.join(out))
    return 0


if __name__ == '__main__':
    sys.exit(main())
