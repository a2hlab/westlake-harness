#!/usr/bin/env python3
"""Static upper bound: which keys' APKs touch android.bluetooth classes our BCP does not define.

    bt_scan.py [--out bt-scan.csv]

For every key (B10 collect.inputs, the frozen APK per key) parse each classes*.dex: type_ids that name a MISSING
android.bluetooth(.le) class (from bt-inventory.json), and class_defs whose superclass or interfaces are a missing
class (those fail when the app class itself is loaded, the fd-plus shape: ExternalSensorsPlugin <init> -> a
ScanCallback subclass). A reference is only an upper bound: it fails only when executed/resolved."""
import argparse
import csv
import json
import re
import struct
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-10-01-b10-theme-graphics'))
import collect  # noqa: E402
import lab_paths  # noqa: E402

INV = json.loads((HERE / 'bt-inventory.json').read_text())
MISSING = {'L' + c + ';' for p in ('android/bluetooth/le/', 'android/bluetooth/') for c in INV[p]['missing']}


def dex_info(data):
    sz, soff, tsz, toff = struct.unpack_from('<4I', data, 56)

    def s(i):
        off = struct.unpack_from('<I', data, soff + 4 * i)[0]
        while data[off] & 0x80:
            off += 1
        off += 1
        return data[off:data.index(b'\0', off)].decode('utf-8', 'replace')
    types = [s(struct.unpack_from('<I', data, toff + 4 * t)[0]) for t in range(tsz)]
    cdsz, cdoff = struct.unpack_from('<2I', data, 96)
    subs = []
    for c in range(cdsz):
        cls, _, sup, ifoff = struct.unpack_from('<4I', data, cdoff + 32 * c)
        parents = [types[sup]] if sup != 0xFFFFFFFF else []
        if ifoff:
            n = struct.unpack_from('<I', data, ifoff)[0]
            parents += [types[struct.unpack_from('<H', data, ifoff + 4 + 2 * k)[0]] for k in range(n)]
        hit = [p for p in parents if p in MISSING]
        if hit:
            subs.append(f'{types[cls]}<{",".join(hit)}')
    return set(types), subs


def scan(apk):
    refs, subs = set(), []
    with zipfile.ZipFile(apk) as z:
        for n in z.namelist():
            if re.match(r'classes\d*\.dex$', n):
                t, sb = dex_info(z.read(n))
                refs |= {x for x in t if x in MISSING}
                subs += sb
    return refs, subs


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--out', default=str(HERE / 'bt-scan.csv'))
    a = ap.parse_args()
    rows = []
    for r in collect.inputs(lab_paths.workspaces()):
        try:
            refs, subs = scan(r['path'])
        except Exception as e:  # noqa: BLE001
            refs, subs = set(), [f'ERROR {e}']
        rows.append({'key': r['key'], 'missing_refs': len(refs),
                     'scancallback_ref': 'Landroid/bluetooth/le/ScanCallback;' in refs,
                     'subclasses_missing': len(subs), 'subclass_list': ' '.join(subs)[:600],
                     'refs': ' '.join(sorted(x[1:-1].split('/')[-1] for x in refs))})
    with open(a.out, 'w', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    any_ref = [r for r in rows if r['missing_refs']]
    sc = [r for r in rows if r['scancallback_ref']]
    sub = [r for r in rows if r['subclasses_missing']]
    print(f'keys {len(rows)}; reference a missing android.bluetooth class {len(any_ref)}; ScanCallback {len(sc)}; '
          f'define a subclass/implementor of a missing class {len(sub)}')
    for r in sub:
        print('  SUB', r['key'], r['subclass_list'][:300])


if __name__ == '__main__':
    main()
