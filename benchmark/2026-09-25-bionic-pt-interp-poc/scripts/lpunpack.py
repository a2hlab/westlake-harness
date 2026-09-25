#!/usr/bin/env python3
"""Minimal liblp reader: list logical partitions of a super image and optionally dump one.
usage: lpunpack.py <disk.img> <super_byte_offset> [name out]"""
import struct, sys
img, base = sys.argv[1], int(sys.argv[2])
f = open(img, 'rb')
f.seek(base + 4096); g = f.read(52)
magic, _, _, max_size, slots, lbs = struct.unpack_from('<II32sIII', g)
assert magic == 0x616c4467, hex(magic)
f.seek(base + 4096 + 2 * 4096); h = f.read(256)
hmagic, major, minor, hsize = struct.unpack_from('<IHHI', h)
assert hmagic == 0x414c5030, hex(hmagic)
tables = [struct.unpack_from('<III', h, 80 + 12 * i) for i in range(4)]
f.seek(base + 4096 + 2 * 4096 + hsize); t = f.read(struct.unpack_from('<I', h, 44)[0])
po, pn, ps = tables[0]; eo, en, es = tables[1]
exts = [struct.unpack_from('<QIQI', t, eo + i * es) for i in range(en)]
parts = {}
for i in range(pn):
    name, attr, fe, ne, grp = struct.unpack_from('<36sIIII', t, po + i * ps)
    name = name.rstrip(b'\0').decode()
    parts[name] = exts[fe:fe + ne]
    print(name, 'attr', attr, 'extents', [(n * 512, d * 512) for n, ty, d, s in exts[fe:fe + ne]])
if len(sys.argv) > 4:
    out = open(sys.argv[4], 'wb')
    for n, ty, d, s in parts[sys.argv[3]]:
        assert ty == 0
        f.seek(base + d * 512); left = n * 512
        while left:
            b = f.read(min(left, 1 << 24)); out.write(b); left -= len(b)
    out.close()
