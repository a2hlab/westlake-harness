#!/usr/bin/env python3
"""List GPT partitions of a raw disk image (512-byte sectors)."""
import struct, sys
f = open(sys.argv[1], 'rb')
f.seek(512); h = f.read(92)
assert h[:8] == b'EFI PART', h[:8]
lba, n, sz = struct.unpack_from('<QII', h, 72)
f.seek(lba * 512)
for i in range(n):
    e = f.read(sz)
    first, last = struct.unpack_from('<QQ', e, 32)
    if first == 0:
        continue
    name = e[56:128].decode('utf-16le').rstrip('\0')
    f2 = open(sys.argv[1], 'rb'); f2.seek(first * 512); head = f2.read(8192); f2.close()
    magic = 'ext4' if head[1024 + 56:1024 + 58] == b'\x53\xef' else 'erofs' if head[1024:1028] == b'\xe2\xe1\xf5\xe0' else 'lp' if head[4096:4100] == b'gDla' else head[:4].hex()
    print(i, name, first, last, (last - first + 1) * 512, magic)
