#!/usr/bin/env python3
"""Per-section size + sha256 of two ELF64 files (raw section bytes from the section headers); prints SAME/DIFF.
    elf_sections.py <a.so> <b.so>"""
import hashlib
import struct
import sys


def sections(path):
    d = open(path, 'rb').read()
    shoff, = struct.unpack_from('<Q', d, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x3A)
    hdrs = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    stroff, strsize = hdrs[shstrndx][4], hdrs[shstrndx][5]
    out = {}
    for h in hdrs:
        name = d[stroff + h[0]:d.index(b'\0', stroff + h[0])].decode()
        data = b'' if h[1] == 8 else d[h[4]:h[4] + h[5]]   # SHT_NOBITS has no file bytes
        out[name or '<null>'] = (h[5], hashlib.sha256(data).hexdigest()[:12])
    return out


a, b = sections(sys.argv[1]), sections(sys.argv[2])
for n in sorted(set(a) | set(b)):
    print(f"{n:22s} {str(a.get(n)):26s} {str(b.get(n)):26s} {'SAME' if a.get(n) == b.get(n) else 'DIFF'}")
