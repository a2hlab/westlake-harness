#!/usr/bin/env python3
"""Reject any ELF byte difference outside its nonallocated .comment section."""
import argparse
import hashlib
import json
from pathlib import Path
import struct


def comment_range(data):
    assert data[:7] == b'\x7fELF\x02\x01\x01'
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, strings_index = struct.unpack_from('<HHH', data, 58)
    assert size == 64 and 0 < strings_index < count
    rows = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
    strings = rows[strings_index]
    names = data[strings[4]:strings[4] + strings[5]]
    matches = [r for r in rows if names[r[0]:].split(b'\0', 1)[0] == b'.comment']
    assert len(matches) == 1
    row = matches[0]
    assert not row[2] & 2 and row[4] + row[5] <= len(data)
    return row[4], row[4] + row[5]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('historical', type=Path)
    parser.add_argument('rebuilt', type=Path)
    args = parser.parse_args()
    old, new = args.historical.read_bytes(), args.rebuilt.read_bytes()
    assert len(old) == len(new)
    a, b = comment_range(old), comment_range(new)
    assert a == b
    differences = [i for i, pair in enumerate(zip(old, new)) if pair[0] != pair[1]]
    assert all(a[0] <= i < a[1] for i in differences)
    print(json.dumps(dict(status='ENTIRE_ELF_EQUAL_EXCEPT_NONALLOC_COMMENT',
        old_sha256=hashlib.sha256(old).hexdigest(), new_sha256=hashlib.sha256(new).hexdigest(),
        different_bytes=len(differences), old_comment=old[a[0]:a[1]].decode(),
        new_comment=new[a[0]:a[1]].decode()), indent=2))

if __name__ == '__main__':
    main()
