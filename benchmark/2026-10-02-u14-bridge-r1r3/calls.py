#!/usr/bin/env python3
"""Ordered direct-call list (bl targets, demangled) and string references of named functions in a .so -- the
behaviour fingerprint used to port/rewrite 846-only functions and to prove the rewrite matches.

    calls.py <.so> <symbol-substring> [<symbol-substring> ...] [--strings]

A symbol-substring selects every defined text symbol whose demangled name contains it. For each: address, size, the
bl/b targets in program order (PLT stubs resolved to their import), and with --strings the C strings it loads via
adrp+add (resolved from .rodata).
"""
import re
import subprocess
import sys


def tool(name):
    return subprocess.run(['xcrun', '-f', name], capture_output=True, text=True).stdout.strip() or name


def symbols(so):
    out = subprocess.run([tool('llvm-nm'), '-S', '--defined-only', '-C', so], capture_output=True, text=True).stdout
    syms = []
    for line in out.splitlines():
        f = line.split(' ', 3)
        if len(f) == 4 and f[2] in 'tTwW':
            syms.append((int(f[0], 16), int(f[1], 16), f[3]))
    return syms


def rodata(so):
    """Map address -> C string for .rodata (readelf section headers + raw bytes)."""
    out = subprocess.run([tool('llvm-readelf'), '-S', '-W', so], capture_output=True, text=True).stdout
    secs = []
    for line in out.splitlines():
        m = re.search(r'\]\s+(\.rodata\S*|\.data\.rel\.ro)\s+\S+\s+([0-9a-f]+)\s+([0-9a-f]+)\s+([0-9a-f]+)', line)
        if m:
            secs.append((int(m.group(2), 16), int(m.group(3), 16), int(m.group(4), 16)))
    data = open(so, 'rb').read()
    return secs, data


def cstr(addr, secs, data):
    for va, off, size in secs:
        if va <= addr < va + size:
            o = off + (addr - va)
            end = data.find(b'\0', o, o + 400)
            s = data[o:end if end >= 0 else o + 400]
            try:
                t = s.decode()
            except UnicodeDecodeError:
                return None
            return t if t and all(31 < ord(c) < 127 or c in '\t\n' for c in t) else None
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    want_strings = '--strings' in sys.argv
    so, pats = args[0], args[1:]
    syms = symbols(so)
    secs, data = rodata(so)
    od = tool('llvm-objdump')
    for addr, size, name in sorted(syms):
        if not any(p in name for p in pats) or size == 0:
            continue
        print(f'== {name}  @0x{addr:x} size {size}')
        dis = subprocess.run([od, '-d', '-C', '--no-show-raw-insn', f'--start-address={addr}',
                              f'--stop-address={addr + size}', so], capture_output=True, text=True).stdout
        page = {}
        for line in dis.splitlines():
            m = re.match(r'\s*([0-9a-f]+):\s+(\S+)\s+(.*)$', line)
            if not m:
                continue
            op, rest = m.group(2), m.group(3)
            if op in ('bl', 'b') and '<' in rest:
                tgt = rest[rest.index('<') + 1:rest.rindex('>')]
                if op == 'b' and ('+' in tgt or tgt.startswith(name[:20])):
                    continue
                print(f'   {op:3s} {tgt.replace("@plt", "")}')
            elif op == 'blr':
                print('   blr (indirect)')
            if want_strings:
                if op == 'adrp':
                    mm = re.match(r'(x\d+),\s*0x([0-9a-f]+)', rest)
                    if mm:
                        page[mm.group(1)] = int(mm.group(2), 16)
                elif op == 'add':
                    mm = re.match(r'(x\d+),\s*(x\d+),\s*#0x([0-9a-f]+)', rest)
                    if mm and mm.group(2) in page:
                        s = cstr(page[mm.group(2)] + int(mm.group(3), 16), secs, data)
                        if s:
                            print(f'   str "{s[:110]}"')
    return 0


if __name__ == '__main__':
    sys.exit(main())
