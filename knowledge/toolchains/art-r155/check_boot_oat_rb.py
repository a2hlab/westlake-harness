#!/usr/bin/env python3
"""Offline read-barrier gate for a generated boot.oat (T5b / T7 pre-board check).

WHY: the board route-A R155 ART is built ART_USE_READ_BARRIER=false, so its boot.oat
OatHeader key-value store has concurrent-copying=false. A boot image compiled read-barrier-ON
(concurrent-copying=true) is NOT usable on it — proven on 5cd 2026-09-30 (T6 discriminative:
zygote children SIGILL/signal4, HelloWorld blank; benchmark/2026-09-30-dex2oat-l2/t6-rb-discriminative/).
Run this on any regenerated boot.oat BEFORE requesting a board window, so a still-RB-on rebuild
is caught offline instead of burning the short 5cd window.

Usage:
  check_boot_oat_rb.py <boot.oat>                        # kv dump + assert concurrent-copying=false, oat v230
  check_boot_oat_rb.py --image <boot.art> <boot.oat>     # also assert image v108
Exit 0 iff RB-off (concurrent-copying=false) AND oat version 230 (AND image 108 if --image given).
"""
import sys

KV_KEYS = ['apex-versions', 'bootclasspath', 'compiler-filter', 'concurrent-copying',
           'debuggable', 'dex2oat-cmdline', 'native-debuggable', 'requires-image']

def read_kv(oat_path):
    b = open(oat_path, 'rb').read(400000)   # OatHeader + kv store live at the top of the .oat
    ver = None
    m = b.find(b'oat\n')
    if m >= 0:
        ver = b[m + 4:m + 8].split(b'\x00', 1)[0].decode('latin1')
    kv = {}
    for k in KV_KEYS:
        i = b.find(k.encode() + b'\x00')
        if i < 0:
            continue
        kv[k] = b[i + len(k) + 1:].split(b'\x00', 1)[0].decode('latin1')
    return ver, kv

def image_version(art_path):
    b = open(art_path, 'rb').read(64)
    m = b.find(b'art\n')
    return b[m + 4:m + 8].split(b'\x00', 1)[0].decode('latin1') if m >= 0 else None

def main(argv):
    art = None
    args = []
    it = iter(argv)
    for a in it:
        if a == '--image':
            art = next(it)
        else:
            args.append(a)
    if not args:
        print(__doc__)
        return 2
    oat = args[0]
    ver, kv = read_kv(oat)
    print(f"oat = {oat}")
    print(f"oat version = {ver!r} (want '230')")
    for k in KV_KEYS:
        print(f"  {k} = {kv.get(k, '<MISSING>')!r}")
    ok = True
    cc = kv.get('concurrent-copying')
    if cc != 'false':
        print(f"FAIL: concurrent-copying={cc!r} (want 'false' = read barrier OFF; an RB-on image SIGILLs on board R155)")
        ok = False
    else:
        print("OK: concurrent-copying=false (read barrier OFF, matches board R155)")
    if ver != '230':
        print(f"FAIL: oat version {ver!r} != 230")
        ok = False
    if art:
        iv = image_version(art)
        print(f"image version = {iv!r} (want '108')")
        if iv != '108':
            print(f"FAIL: image version {iv!r} != 108")
            ok = False
    print("VERDICT:", "PASS (RB-off + versions ok) -> safe to board" if ok else "FAIL -> do NOT board; regenerate with the RB-off (T3b) dex2oat")
    return 0 if ok else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
