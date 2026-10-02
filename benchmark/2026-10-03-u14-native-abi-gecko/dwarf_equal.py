#!/usr/bin/env python3
"""Prove that the remaining .debug_* differences between two builds are only path-induced string placement:
(1) the multiset of strings in .debug_str and .debug_line_str is equal once each file's build root is replaced by a
placeholder; (2) llvm-dwarfdump --debug-info --debug-line (strings resolved) is textually identical after the same
replacement with raw string-section offsets ([0x...] / .debug_*str[0x...]) stripped.

    dwarf_equal.py <a.so> <a-root> <b.so> <b-root>"""
import collections
import re
import struct
import subprocess
import sys


def section(path, want):
    d = open(path, 'rb').read()
    shoff, = struct.unpack_from('<Q', d, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x3A)
    sh = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    so = sh[shstrndx][4]
    for h in sh:
        if d[so + h[0]:d.index(b'\0', so + h[0])].decode() == want:
            return d[h[4]:h[4] + h[5]]
    return b''


def strings(path, root, sec):
    return collections.Counter(s.replace(root.encode(), b'<ROOT>') for s in section(path, sec).split(b'\0') if s)


def dump(path, root):
    tool = subprocess.run(['xcrun', '-f', 'llvm-dwarfdump'], capture_output=True, text=True).stdout.strip()
    out = subprocess.run([tool, '--debug-info', '--debug-line', path], capture_output=True, text=True).stdout
    out = out.replace(root, '<ROOT>').split('\n', 1)[1]          # drop the "file format" header line
    out = re.sub(r'\.debug_(line_)?str\[0x[0-9a-f]+\]', '.debug_str[]', out)
    out = re.sub(r'DW_AT_(name|comp_dir|producer|linkage_name)\s*\(0x[0-9a-f]+\)', r'DW_AT_\1()', out)
    return out


a, ra, b, rb = sys.argv[1:5]
for sec in ('.debug_str', '.debug_line_str'):
    ca, cb = strings(a, ra, sec), strings(b, rb, sec)
    print(f'{sec}: {sum(ca.values())} vs {sum(cb.values())} strings; multiset equal after root placeholder: {ca == cb}')
    if ca != cb:
        print('   only a:', list((ca - cb).items())[:5], '\n   only b:', list((cb - ca).items())[:5])
da, db = dump(a, ra), dump(b, rb)
la, lb = da.splitlines(), db.splitlines()
nd = [i for i, (x, y) in enumerate(zip(la, lb)) if x != y]
print(f'dwarfdump --debug-info --debug-line (strings resolved, root placeholder, string offsets stripped): '
      f'{len(la)} vs {len(lb)} lines, differing lines {len(nd)}')
for i in nd[:10]:
    print('   a:', la[i].strip()[:150], '\n   b:', lb[i].strip()[:150])
