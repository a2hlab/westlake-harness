#!/usr/bin/env python3
"""android.bluetooth / android.bluetooth.le: the public AOSP 14 API (android-34 SDK android.jar, the same toolchain
android.jar build_u12.py compiles against) vs what the deployed boot class path defines.

    bt_inventory.py [--json bt-inventory.json]

BCP jars (local copies matched by sha256 to the deployed ones): framework.jar 3e106350, adapter-mainline-stubs.jar
2f365a75 (U10.1T8) and 615b8bbe (U12/U13), oh-adapter-framework.jar 2257b835. core-oj/core-libart/okhttp/
bouncycastle/apache-xml/core-icu4j define no android.bluetooth classes."""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-02-u12-jar-plan'))
sys.path.insert(0, str(HERE.parents[1] / 'scripts/lab'))
import build_u12 as r1  # noqa: E402
import lab_paths  # noqa: E402

G = lab_paths.inputs() / 'generations'
JARS = {
    'framework 3e106350': G / 't8-rebake-effective/ref-jars9/framework.jar',
    'stubs 2f365a75 (U10.1T8)': G / 't8-rebake-effective/jars9/adapter-mainline-stubs.jar',
    'stubs 615b8bbe (U12/U13)': G / 'u12-final-j0482c9b1-s615b8bbe-icu-media-zlib-v2/bundle/framework/adapter-mainline-stubs.jar',
    'oh-adapter-framework 2257b835': G / 't8-rebake-effective/jars9/oh-adapter-framework.jar',
}
PKG = re.compile(r'^android/bluetooth/(le/)?[^/]+$')


def dex_classes(jar):
    out = set()
    with zipfile.ZipFile(jar) as z:
        for n in z.namelist():
            if re.match(r'classes\d*\.dex$', n):
                data = z.read(n)
                # type_ids -> string_ids: parse the header directly
                import struct
                string_ids_size, string_ids_off, type_ids_size, type_ids_off = struct.unpack_from('<4I', data, 56)
                def s(i):
                    off = struct.unpack_from('<I', data, string_ids_off + 4 * i)[0]
                    while data[off] & 0x80:
                        off += 1
                    off += 1
                    end = data.index(b'\0', off)
                    return data[off:end].decode('utf-8', 'replace')
                class_defs_size, class_defs_off = struct.unpack_from('<2I', data, 96)
                for c in range(class_defs_size):
                    tidx = struct.unpack_from('<I', data, class_defs_off + 32 * c)[0]
                    sidx = struct.unpack_from('<I', data, type_ids_off + 4 * tidx)[0]
                    d = s(sidx)
                    out.add(d[1:-1])
    return out


def sdk_public():
    with zipfile.ZipFile(r1.AJ) as z:
        return {n[:-6] for n in z.namelist() if n.endswith('.class') and PKG.match(n[:-6]) and '$' not in n[:-6]} | \
               {n[:-6] for n in z.namelist() if n.endswith('.class') and PKG.match(n[:-6].split('$')[0])}


def main():
    sdk = sdk_public()
    bcp = {k: {c for c in dex_classes(v) if PKG.match(c.split('$')[0])} for k, v in JARS.items()}
    have = set().union(*bcp.values())
    res = {'sdk_android_jar': str(r1.AJ.name), 'sdk_classes': len(sdk), 'per_jar': {k: sorted(v) for k, v in bcp.items()}}
    for pkg in ('android/bluetooth/le/', 'android/bluetooth/'):
        top = lambda c: c.startswith(pkg) and (pkg.endswith('le/') or '/le/' not in c)
        s = sorted(c for c in sdk if top(c))
        res[pkg] = {'sdk': s, 'missing': [c for c in s if c not in have], 'present': [c for c in s if c in have]}
        print(f'{pkg}: SDK public {len(s)}, present in BCP {len(res[pkg]["present"])}, missing {len(res[pkg]["missing"])}')
    for k, v in bcp.items():
        print(f'  {k}: {len(v)} android.bluetooth classes: ' + ', '.join(c.split("/")[-1] for c in sorted(v))[:400])
    if '--json' in sys.argv:
        Path(sys.argv[sys.argv.index('--json') + 1]).write_text(json.dumps(res, indent=1) + '\n')


if __name__ == '__main__':
    main()
