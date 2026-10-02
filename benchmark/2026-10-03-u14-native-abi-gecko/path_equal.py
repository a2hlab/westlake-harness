#!/usr/bin/env python3
"""Faithfulness check of a re-build against the deployed ELF, per the outer's criterion: replace each file's own build
root path string with a same-length placeholder, mask the .note.gnu.build-id descriptor, then compare byte by byte and
list every remaining differing offset with the section that holds it.

    path_equal.py <deployed.so> <deployed-root> <rebuilt.so> <rebuilt-root>"""
import struct
import sys


def load(path, root):
    d = bytearray(open(path, 'rb').read())
    r = root.encode()
    n = d.count(r)
    d = bytearray(bytes(d).replace(r, b'#' * len(r)))
    shoff, = struct.unpack_from('<Q', d, 0x28)
    shentsize, shnum, shstrndx = struct.unpack_from('<HHH', d, 0x3A)
    sh = [struct.unpack_from('<IIQQQQIIQQ', d, shoff + i * shentsize) for i in range(shnum)]
    so = sh[shstrndx][4]
    secs = [(d[so + h[0]:d.index(b'\0', so + h[0])].decode(), h[4], h[5]) for h in sh if h[1] != 8]  # skip NOBITS
    for name, off, size in secs:
        if name == '.note.gnu.build-id':
            d[off + 16:off + size] = b'\0' * (size - 16)
    return d, secs, n


a, sa, na = load(sys.argv[1], sys.argv[2])
b, sb, nb = load(sys.argv[3], sys.argv[4])
print(f'root occurrences replaced: deployed {na}, rebuilt {nb}; sizes {len(a)} / {len(b)}')
if len(a) != len(b):
    print('SIZE DIFFERS')
diff = [i for i in range(min(len(a), len(b))) if a[i] != b[i]]
where = lambda i: next((n for n, o, s in sa if o <= i < o + s), '<header/outside sections>')
print(f'differing bytes after path placeholder + build-id mask: {len(diff)}')
import collections
per = collections.Counter(where(i) for i in diff)
for name, n in sorted(per.items()):
    first = next(i for i in diff if where(i) == name)
    print(f'  {name:22s} {n:5d} bytes, first at {first:#08x}')
allowed = all(n.startswith('.debug_') or n in ('.comment', '.symtab', '.strtab') for n in per)
print('VERDICT byte-equal:', not diff and len(a) == len(b),
      '| every remaining difference is in .debug_*/.comment/.symtab (non-allocated):', allowed)
