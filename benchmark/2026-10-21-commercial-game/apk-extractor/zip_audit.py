#!/usr/bin/env python3
"""Read-only ZIP layout audit. Does not validate signatures or extract/execute entries."""
import argparse
import hashlib
import json
from pathlib import Path
import struct

FIELDS = ['signature', 'numDisk', 'startDiskOfCentralDir', 'entriesDisk',
          'entriesTotal', 'centralSize', 'centralOffset', 'commentLength']

def enddir(b):
    return dict(zip(FIELDS, struct.unpack('<I4H2IH', b)))

def extras(b):
    ids = []
    while b:
        if len(b) < 4:
            return ids, len(b)
        ident, n = struct.unpack('<HH', b[:4])
        if n > len(b)-4:
            return ids, len(b)
        ids.append(ident); b = b[4+n:]
    return ids, 0

def audit(path):
    size = path.stat().st_size
    with path.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
        f.seek(max(0, size-65557)); start = f.tell(); tail = f.read()
        candidates = []
        for i in range(len(tail)-22, -1, -1):
            if tail[i:i+4] == b'PK\x05\x06':
                e = enddir(tail[i:i+22])
                if start+i+22+e['commentLength'] == size:
                    candidates.append((start+i, e))
        assert len(candidates) == 1, 'ambiguous or missing EOF-bound EOCD'
        off, e = candidates[0]
        assert e['numDisk'] == e['startDiskOfCentralDir'] == 0
        assert e['entriesDisk'] == e['entriesTotal']
        assert e['centralOffset']+e['centralSize'] == off
        pos = e['centralOffset']; entries = []; names = set()
        for _ in range(e['entriesTotal']):
            f.seek(pos); b = f.read(46)
            assert b[:4] == b'PK\x01\x02', 'central header signature'
            v = struct.unpack('<I6H3I5H2I', b)
            _, made, need, flags, method, tm, dt, crc, compressed, raw, nl, xl, cl, disk, ia, ea, local = v
            name = f.read(nl); extra = f.read(xl); comment = f.read(cl)
            assert name not in names; names.add(name)
            assert disk == 0 and 0xffffffff not in (compressed, raw, local)
            f.seek(local); lh = f.read(30)
            lv = struct.unpack('<I5H3I2H', lh)
            assert lh[:4] == b'PK\x03\x04' and lv[2] == flags and lv[3] == method
            lname = f.read(lv[-2]); lextra = f.read(lv[-1]); assert lname == name
            if not flags & 8:
                assert tuple(lv[6:9]) == (crc, compressed, raw)
            end = local+30+len(lname)+len(lextra)+compressed
            assert 0 <= local < end <= e['centralOffset']
            ce, ct = extras(extra); le, lt = extras(lextra)
            entries.append({'local': local, 'end': end, 'flags': flags, 'method': method,
                            'name_bytes': len(name), 'zip64_extra': 1 in ce+le,
                            'extra_unparsed_bytes': ct+lt,
                            'native_so': name.startswith(b'lib/') and name.endswith(b'.so')})
            pos += 46+nl+xl+cl
        assert pos == off
        spans = sorted((x['local'], x['end']) for x in entries)
        assert all(a[1] <= b[0] for a,b in zip(spans, spans[1:])), 'overlapping entry data'
        f.seek(e['centralOffset']-24); footer = f.read(24)
        signing = {'magic_present': footer[8:] == b'APK Sig Block 42', 'cryptographic_verification': 'NOT_PERFORMED'}
        if signing['magic_present']:
            n = struct.unpack('<Q', footer[:8])[0]; block_start = e['centralOffset']-n-8
            assert 0 <= block_start < e['centralOffset']-24
            f.seek(block_start); leading = struct.unpack('<Q', f.read(8))[0]; assert leading == n
            signing.update(start=block_start, footer_size=n, leading_size=leading,
                           entries_end_before_block=all(x['end'] <= block_start for x in entries))
        return {'sha256': digest, 'bytes': size, 'eocd_offset': off, 'eocd': e,
                'legacy_read_offset': size-22, 'legacy_read_hex': tail[-22:].hex(),
                'legacy_fields': enddir(tail[-22:]), 'central_and_local_checked': len(entries),
                'methods': sorted({x['method'] for x in entries}), 'flags': sorted({x['flags'] for x in entries}),
                'zip64_extra_entries': sum(x['zip64_extra'] for x in entries),
                'extra_unparsed_entries': sum(x['extra_unparsed_bytes'] > 0 for x in entries),
                'extra_unparsed_bytes': sum(x['extra_unparsed_bytes'] for x in entries),
                'extra_limit': 'Extra-field remainder is counted, not treated as a parser rejection or proof of absence of hidden fields.',
                'native_so_entries': sum(x['native_so'] for x in entries),
                'max_name_bytes': max(x['name_bytes'] for x in entries), 'signing_block': signing}

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('apk', type=Path)
    print(json.dumps(audit(p.parse_args().apk), indent=2))
