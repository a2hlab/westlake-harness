#!/usr/bin/env python3
"""Compare what the loader maps (PT_LOAD file bytes, with .note.gnu.build-id's descriptor and the ELF header's e_shoff
(section-header offset, never used by the loader) masked) and list .symtab
entries that differ between two ELF64 files.   elf_load_and_symtab.py <a.so> <b.so>"""
import hashlib
import struct
import sys


def parse(path):
    d = bytearray(open(path, 'rb').read())
    phoff, shoff = struct.unpack_from('<QQ', d, 0x20)
    phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from('<HHHHH', d, 0x36)
    sh = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    stro = sh[shstrndx][4]
    name = lambda h: d[stro + h[0]:d.index(b'\0', stro + h[0])].decode()
    secs = {name(h): h for h in sh}
    bid = secs.get('.note.gnu.build-id')
    if bid:  # mask the 20-byte sha1 descriptor (namesz 4, descsz 20, type 3, "GNU\0")
        d[bid[4] + 16:bid[4] + 16 + 20] = b'\0' * 20
    d[0x28:0x30] = b'\0' * 8   # e_shoff (already read above)
    loads = []
    for i in range(phnum):
        ptype, flags, off, vaddr, paddr, filesz, memsz, align = struct.unpack_from('<IIQQQQQQ', d, phoff + i * phentsize)
        if ptype == 1:
            loads.append((vaddr, filesz, hashlib.sha256(bytes(d[off:off + filesz])).hexdigest()[:12]))
    st, ss = secs['.symtab'], secs['.strtab']
    syms = []
    for i in range(st[5] // 24):
        nm, info, other, shndx, val, size = struct.unpack_from('<IBBHQQ', d, st[4] + 24 * i)
        syms.append((d[ss[4] + nm:d.index(b'\0', ss[4] + nm)].decode(), info, other, shndx, val, size))
    return loads, syms


(la, sa), (lb, sb) = parse(sys.argv[1]), parse(sys.argv[2])
for x, y in zip(la, lb):
    print('PT_LOAD vaddr=%#x filesz=%d  a=%s b=%s %s' % (x[0], x[1], x[2], y[2], 'SAME' if x == y else 'DIFF'))
diff = [(x, y) for x, y in zip(sa, sb) if x != y]
print(f'.symtab entries {len(sa)} vs {len(sb)}; differing {len(diff)}')
for x, y in diff[:10]:
    print('  a', x, '\n  b', y)
