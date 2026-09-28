"""Describe provider ABI deltas; byte equality is informational, not equivalence."""
import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path


def inspect(path, readelf):
    data = path.read_bytes()
    assert data[:6] == b'\x7fELF\x02\x01', path
    offset = struct.unpack_from('<Q', data, 40)[0]
    size, count, names_index = struct.unpack_from('<HHH', data, 58)
    headers = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size)
               for i in range(count)]
    names_header = headers[names_index]
    names = data[names_header[4]:names_header[4] + names_header[5]]
    sections = {}
    for h in headers:
        name = names[h[0]:].split(b'\0')[0].decode()
        if not name:
            continue
        sections[name] = {'size': h[5], 'type': h[1], 'flags': h[2]}
        if h[1] != 8:  # SHT_NOBITS has size but no file bytes.
            sections[name]['sha256'] = hashlib.sha256(data[h[4]:h[4] + h[5]]).hexdigest()
    output = subprocess.check_output(
        [readelf, '-W', '-d', '--dyn-syms', str(path)], text=True)
    exports, imports = set(), set()
    for line in output.splitlines():
        fields = line.split()
        if len(fields) < 8 or not re.fullmatch(r'\d+:', fields[0]):
            continue
        if fields[4] not in ('GLOBAL', 'WEAK'):
            continue
        if fields[6] == 'UND':
            imports.add(fields[7])
        elif fields[5] in ('DEFAULT', 'PROTECTED'):
            exports.add(fields[7])
    return {'sha256': hashlib.sha256(data).hexdigest(),
            'soname': re.findall(r'Library soname: \[(.*?)\]', output),
            'needed': sorted(re.findall(r'Shared library: \[(.*?)\]', output)),
            'exports': sorted(exports), 'imports': sorted(imports),
            'sections': sections}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--candidate', type=Path, required=True)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--readelf', required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    rows = []
    for path in sorted(a.candidate.glob('*.so')):
        c = inspect(path, a.readelf)
        baseline = a.baseline / path.name
        b = inspect(baseline, a.readelf) if baseline.is_file() else None
        rows.append({'name': path.name, 'candidate': c, 'baseline': b,
                     'byte_identical': b is not None and c['sha256'] == b['sha256'],
                     'exports_removed': sorted(set(b['exports']) - set(c['exports'])) if b else [],
                     'exports_added': sorted(set(c['exports']) - set(b['exports'])) if b else [],
                     'soname_equal': b is not None and c['soname'] == b['soname'],
                     'needed_equal': b is not None and c['needed'] == b['needed']})
    a.out.write_text(json.dumps({'scope': 'ABI inventory, not runtime equivalence proof',
                                'providers': rows}, indent=2) + '\n')
    print(f'Compared {len(rows)} candidates; {sum(x["baseline"] is None for x in rows)} lack a baseline')
