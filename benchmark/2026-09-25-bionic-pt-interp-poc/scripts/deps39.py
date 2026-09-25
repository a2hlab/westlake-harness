#!/usr/bin/env python3
"""#39: dependency facts for rebuilding the 57 out-all0925 runtime libraries against Bionic.

For every library: producer build (from native-runtime/artifacts.json origins), DT_NEEDED split into
in-runtime / libc-family / external (OH), and a topological level. For the OH-facing ones, the number of
undefined symbols each external library actually satisfies (from the firmware stubs in native-imports).
Read only. Prints JSON."""
import json, re, subprocess
from collections import defaultdict
from pathlib import Path

A = Path('/home/dspfac/a2hlab/source-closure/verify')
R = A / 'out-all0925/native-runtime'
IMPORTS = A / 'out-all0925/native-imports'
RE = str(A / 'toolchains/clang-15/bin/llvm-readelf')
NM = str(A / 'toolchains/clang-15/bin/llvm-nm')
LIBC = {'libc.so', 'libm.so', 'libdl.so', 'libc++.so', 'libc++_shared.so', 'ld-musl-aarch64.so.1'}


def needed(p):
    out = subprocess.run([RE, '-d', str(p)], capture_output=True, text=True).stdout
    return re.findall(r'Shared library: \[(.*?)\]', out)


def undefined(p):
    out = subprocess.run([NM, '-D', '--undefined-only', str(p)], capture_output=True, text=True).stdout
    return {l.split()[-1].split('@')[0] for l in out.splitlines() if l.strip()}


def defined(p):
    out = subprocess.run([NM, '-D', '--defined-only', str(p)], capture_output=True, text=True).stdout
    return {l.split()[-1].split('@')[0] for l in out.splitlines() if l.strip()}


def main():
    report = json.loads((R / 'artifacts.json').read_text())
    origins = report.get('origins', {})
    libs = sorted(p.name for p in R.glob('*.so'))
    own = set(libs)
    info = {}
    for name in libs:
        deps = needed(R / name)
        info[name] = {
            'producer': str(Path(origins.get(name, '?')).parent).replace(str(A) + '/', ''),
            'bytes': (R / name).stat().st_size,
            'in_runtime': [d for d in deps if d in own],
            'libc': [d for d in deps if d in LIBC],
            'external': [d for d in deps if d not in own and d not in LIBC],
        }
    # topological levels over in-runtime edges
    level = {}
    def lv(n, stack=()):
        if n in level:
            return level[n]
        if n in stack:
            return 0
        level[n] = 1 + max([lv(d, stack + (n,)) for d in info[n]['in_runtime']] or [-1])
        return level[n]
    for n in libs:
        lv(n)
        info[n]['level'] = level[n]
    # symbol use per external provider for OH-facing libs
    stub_dirs = [d for d in IMPORTS.rglob('*') if d.is_dir()] + [IMPORTS,
                 A / 'toolchains/ohos-sdk/native/sysroot/usr/lib/aarch64-linux-ohos']
    providers = {}
    for d in stub_dirs:
        for f in d.glob('*.so'):
            providers.setdefault(f.name, f)
    for n in libs:
        ext = info[n]['external']
        if not ext:
            continue
        und = undefined(R / n)
        per = {}
        for e in ext:
            f = providers.get(e)
            per[e] = len(und & defined(f)) if f else None
        info[n]['external_symbols'] = per
    print(json.dumps({'libs': info, 'count': len(libs)}, indent=1))


if __name__ == '__main__':
    main()
