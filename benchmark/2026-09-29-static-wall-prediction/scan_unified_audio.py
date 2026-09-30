#!/usr/bin/env python3
"""Budget scan: exact-APK external DEX method references, NOT startup reachability."""
import hashlib
import json
import re
import struct
import zipfile
from pathlib import Path
from rules_unified_r17r import FAMILY, requirement

HERE = Path(__file__).resolve().parent
FREEZE = HERE.parent/'2026-09-30-r17op-prospective/freezes/v3'
CACHE = HERE.parent/'2026-09-30-background-start-prospective/evidence'
OUT = HERE/'unified-r17r-feedback'


def dex_references(data):
    if data[:4] != b'dex\n' or data[40:44] != b'\x78\x56\x34\x12':
        raise ValueError('unsupported DEX format')
    def u32(off):
        return struct.unpack_from('<I', data, off)[0]
    strings = []
    for i in range(u32(56)):
        offset = u32(u32(60)+4*i)
        while data[offset] & 128:
            offset += 1
        offset += 1
        strings.append(data[offset:data.index(b'\0', offset)].decode('utf-8', errors='replace'))
    types = [strings[u32(u32(68)+4*i)] for i in range(u32(64))]
    defined = {u32(u32(100)+32*i) for i in range(u32(96))}
    for i in range(u32(88)):
        offset = u32(92)+8*i
        owner, proto, name = struct.unpack_from('<HHI', data, offset)
        if owner in defined:
            continue  # APK-local lookalike definitions are not framework requirements.
        owner_name = types[owner][1:-1]
        if not owner_name.startswith('android/media/'):
            continue
        proto_offset = u32(76)+12*proto
        ret, params = u32(proto_offset+4), u32(proto_offset+8)
        args = ''.join(types[struct.unpack_from('<H', data, params+4+2*j)[0]]
                       for j in range(u32(params))) if params else ''
        yield dict(owner=owner_name, name=strings[name], signature='('+args+')'+types[ret],
                   method_id=i, method_id_offset=offset)


def scan(entry):
    result = dict(key=entry['key'], apk_sha256=entry['apk_sha256'], family=FAMILY,
                  status='unknown-input', witnesses=[], startup_reachable='unknown',
                  missing_implementation='unknown', active_wall='unknown')
    try:
        old = json.loads((CACHE/(entry['key']+'.json')).read_text())
        apk = Path(old['apk'])
        with apk.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if digest != entry['apk_sha256']:
            raise ValueError('base APK SHA mismatch')
        result.update(apk=str(apk), apk_sha256_verified=True)
        with zipfile.ZipFile(apk) as archive:
            for dex in sorted(n for n in archive.namelist() if re.fullmatch(r'classes\d*\.dex', n)):
                raw = archive.read(dex)
                dex_sha = hashlib.sha256(raw).hexdigest()
                for ref in dex_references(raw):
                    sub = requirement(ref['owner'], ref['name'], ref['signature'])
                    if sub:
                        result['witnesses'].append(dict(ref, dex=dex, dex_sha256=dex_sha, submechanism=sub))
        result['status'] = 'conditional-reference' if result['witnesses'] else 'no-reference-in-base-dex'
    except (OSError, KeyError, ValueError, struct.error, zipfile.BadZipFile) as exc:
        result['error'] = str(exc)
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = [scan(e) for e in json.loads((FREEZE/'predictions.json').read_text())]
    (OUT/'audio-static.json').write_text(json.dumps(rows, indent=2)+'\n')
    print(json.dumps({s: sum(r['status']==s for r in rows) for s in sorted({r['status'] for r in rows})}))


if __name__ == '__main__':
    main()
