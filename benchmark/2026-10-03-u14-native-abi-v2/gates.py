#!/usr/bin/env python3
"""Structural gates of native_abi v2 against 7605812c, and of its `_ctype_` data against U13 compat b8a87f6f.

    gates.py <7605812c.so> <v2.so> <compat-b8a87f6f.so>

1 exports: versioned dynamic definitions, v2 minus base must be exactly {_ctype_@@LIBC}, base minus v2 empty.
2 `_ctype_`: an 8-byte GLOBAL OBJECT whose R_AARCH64_RELATIVE addend points at a 257-byte LOCAL `_C_ctype_`; the 257
  bytes must equal compat b8a87f6f's `_C_ctype_` bytes (found the same way) and the AOSP table parsed from ctype_.c.
3 imports and NEEDED unchanged; 4 strings: only additions; open sites: the dlopen-family call sites (equiv covers code).
"""
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def tool(n):
    return subprocess.run(['xcrun', '-f', n], capture_output=True, text=True).stdout.strip() or n


def run(*a):
    return subprocess.run([str(x) for x in a], capture_output=True, text=True).stdout


def defs(so):
    out = set()
    for l in run(tool('llvm-readelf'), '--dyn-syms', '-W', so).splitlines():
        p = l.split()
        if len(p) >= 8 and p[6] != 'UND' and p[0].endswith(':') and p[7] != '':
            out.add(p[7])
    return out


def imports(so):
    return {l.split()[7] for l in run(tool('llvm-readelf'), '--dyn-syms', '-W', so).splitlines()
            if len(l.split()) >= 8 and l.split()[6] == 'UND' and l.split()[7]}


def needed(so):
    return re.findall(r'\(NEEDED\)\s+Shared library: \[(.+?)\]', run(tool('llvm-readelf'), '-d', so))


def sections(so):
    s = {}
    for l in run(tool('llvm-readelf'), '-S', '-W', so).splitlines():
        m = re.match(r'\s*\[\s*\d+\]\s+(\S+)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)', l)
        if m:
            s[m.group(1)] = (int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16))
    return s


def vaddr_to_off(so, va):
    for name, (addr, off, size) in sections(so).items():
        if addr and addr <= va < addr + size and name != '.bss':
            return off + (va - addr)
    raise ValueError(hex(va))


def ctype_table(so):
    """Address of _ctype_, the RELATIVE addend stored for it, and the 257 bytes it points at."""
    sym = [l.split() for l in run(tool('llvm-readelf'), '--dyn-syms', '-W', so).splitlines() if '_ctype_' in l]
    sym = [p for p in sym if p[7].split('@')[0] == '_ctype_' and p[6] != 'UND'][0]
    addr, size, typ, bind = int(sym[1], 16), int(sym[2]), sym[3], sym[4]
    target = None
    for l in run(tool('llvm-readelf'), '-r', '-W', so).splitlines():
        p = l.split()
        if p and re.match(r'^[0-9a-f]{8,}$', p[0]) and int(p[0], 16) == addr:
            target = int(p[-1], 16) if 'RELATIVE' in l else None
            kind = p[2]
    data = Path(so).read_bytes()
    table = data[vaddr_to_off(so, target):vaddr_to_off(so, target) + 257]
    local = [l.split() for l in run(tool('llvm-readelf'), '-s', '-W', so).splitlines() if '_C_ctype_' in l]
    return dict(addr=addr, size=size, type=typ, bind=bind, reloc=kind, target=target, table=table,
                c_ctype=[(p[1], p[2], p[4]) for p in local])


def strings(so):
    return set(run('strings', '-a', '-n', '6', so).splitlines())


def aosp_table():
    src = (HERE / 'src/inputs/aosp/libc/upstream-openbsd/lib/libc/gen/ctype_.c').read_text()
    body = src[src.index('_C_ctype_[1 + CTYPE_NUM_CHARS] = {') + 34:src.index('};')]
    body = re.sub(r'/\*.*?\*/', '', body, flags=re.S)
    v = dict(_U=0x01, _L=0x02, _N=0x04, _S=0x08, _P=0x10, _C=0x20, _X=0x40, _B=0x80)
    vals = []
    for tok in [t.strip() for t in body.split(',') if t.strip()]:
        tok = tok.replace('(char)', '')
        vals.append(eval(tok, {}, v) & 0xff)
    return bytes(vals)


def main():
    base, v2, compat = sys.argv[1:4]
    ok = True
    bd, vd = defs(base), defs(v2)
    print(f'1 exports: base {len(bd)}, v2 {len(vd)}; added {sorted(vd - bd)}; removed {sorted(bd - vd)}')
    ok &= (vd - bd) == {'_ctype_@@LIBC'} and not (bd - vd)
    t, c = ctype_table(v2), ctype_table(compat)
    aosp = aosp_table()
    print(f'2 _ctype_ v2: size {t["size"]} {t["type"]} {t["bind"]}, reloc {t["reloc"]} -> {t["target"]:#x}; '
          f'_C_ctype_ symtab {t["c_ctype"]}')
    print(f'  compat b8a87f6f: size {c["size"]} {c["type"]} {c["bind"]}, reloc {c["reloc"]} -> {c["target"]:#x}')
    print(f'  table v2 == compat: {t["table"] == c["table"]}; v2 == AOSP ctype_.c parsed ({len(aosp)} bytes): '
          f'{t["table"] == aosp}; first 16 {t["table"][:16].hex()}')
    ok &= t['size'] == 8 and t['type'] == 'OBJECT' and t['bind'] == 'GLOBAL' and 'RELATIVE' in t['reloc']
    ok &= t['table'] == c['table'] == aosp and len(aosp) == 257
    ok &= all(b == 'LOCAL' for (_, _, b) in t['c_ctype']) and all(s == '257' for (_, s, _) in t['c_ctype'])
    bi, vi = imports(base), imports(v2)
    print(f'3 imports added {sorted(vi - bi)} removed {sorted(bi - vi)}; NEEDED base {needed(base)} v2 {needed(v2)}')
    ok &= bi == vi and needed(base) == needed(v2)
    bs, vs = strings(base), strings(v2)
    print(f'4 strings removed {len(bs - vs)}: {sorted(bs - vs)[:10]}; added {len(vs - bs)}: {sorted(vs - bs)[:12]}')
    print('GATES', 'PASS' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
