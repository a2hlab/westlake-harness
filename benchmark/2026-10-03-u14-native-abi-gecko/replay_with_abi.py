#!/usr/bin/env python3
"""musl-order replay of the Gecko libraries against a REAL native_abi build (not a hypothetical --extra list), plus a
version check: every strong @LIBC import the replay sends to native_abi must be defined there at version LIBC
(vna_hash 0x50d63 = elf_hash("LIBC")).

    replay_with_abi.py <libwestlake_native_abi.so> <apk-libs-dir> [...]

Provider model and order are ../2026-10-03-gecko-fatal-before-bind/reloc_order.py (musl + RTLD_GLOBAL native_abi + the
app's own libraries + NDK API symbols; JMPREL, then REL, then RELA; WEAK never fails)."""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / '2026-10-03-gecko-fatal-before-bind'))
import gecko_imports as gi  # noqa: E402
import reloc_order as ro  # noqa: E402


def elf_hash(s):
    h = 0
    for c in s.encode():
        h = (h << 4) + c
        g = h & 0xF0000000
        if g:
            h ^= g >> 24
        h &= ~g & 0xFFFFFFFF
    return h


def versioned_defs(lib):
    out = subprocess.run([ro.tool('llvm-readelf'), '--dyn-syms', '-W', str(lib)], capture_output=True, text=True).stdout
    defs = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) >= 8 and p[6] != 'UND' and '@' in p[7]:
            name, ver = p[7].split('@', 1)
            defs[name] = ver.lstrip('@')
    return defs


def main():
    abi = Path(sys.argv[1])
    gi.PROVIDERS['libwestlake_native_abi.so(d2053066)'] = abi      # reloc_order reads the native_abi path from here
    defs = versioned_defs(abi)
    print(f'native_abi {abi.name}: version LIBC hash {elf_hash("LIBC"):#x} (libmozglue vna_hash 0x50d63)')
    for d in sys.argv[2:]:
        for lib in sorted(Path(d).glob('*.so')):
            sys.argv = ['reloc_order.py', str(lib)]
            ro.main()
            und = subprocess.run([ro.tool('llvm-readelf'), '--dyn-syms', '-W', str(lib)], capture_output=True, text=True).stdout
            wanted = {p[7].split('@')[0] for p in (l.split() for l in und.splitlines())
                      if len(p) >= 8 and p[6] == 'UND' and p[7].endswith('@LIBC')}
            bad = sorted(s for s in wanted if s in defs and defs[s] != 'LIBC')
            if bad:
                print(f'   VERSION MISMATCH {lib.name}: {bad}')


if __name__ == '__main__':
    main()
