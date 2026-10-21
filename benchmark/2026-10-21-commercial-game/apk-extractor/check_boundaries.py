#!/usr/bin/env python3
"""Exercise actual compiled ZipFile::Open with exact peer and generated boundary inputs."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import struct
import subprocess
import zipfile

D = Path(__file__).resolve().parent

def check(original, candidate, out):
    out.mkdir(parents=True, exist_ok=False)
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as z:
        z.writestr(zipfile.ZipInfo('a', (2020, 1, 1, 0, 0, 0)), b'x')
    zero = data.getvalue(); e = zero.rfind(b'PK\x05\x06')
    def comment(b):
        return zero[:e+20]+struct.pack('<H', len(b))+b
    cases = {'zero': (zero, 0), 'comment19': (comment(b'x'*19), 0),
             'maxcomment': (comment(b'x'*65535), 0), 'truncated': (zero[:20], 2),
             'short-comment': (comment(b'x'*19)[:-1], 2)}
    # Exact two independent peer counterexamples, preserved byte-for-byte as hex.
    peers = json.loads((D/'evidence/peer-fixtures.json').read_text())
    for name, expected in [('central-in-comment-padded.zip', 2), ('valid-comment-fake-eocd.zip', 0)]:
        b = bytes.fromhex(peers[name]['hex'])
        assert hashlib.sha256(b).hexdigest() == peers[name]['sha256']
        cases[name[:-4]] = (b, expected)
    # The wide sum must reject wraparound rather than point into the file.
    bad = bytearray(zero); struct.pack_into('<II', bad, e+12, 0x400, 0xfffffff0)
    cases['central-overflow'] = (bytes(bad), 2)
    records = []
    for name, (b, expected) in cases.items():
        fixture = out/(name+'.zip'); fixture.write_bytes(b)
        for variant, binary in [('original', original), ('candidate', candidate)]:
            tag = variant+'-'+name; argv = [str(binary.resolve()), str(fixture.resolve())]
            r = subprocess.run(argv, capture_output=True)
            for suffix, content in [('argv.json', (json.dumps(argv, indent=2)+'\n').encode()),
                                    ('stdout', r.stdout), ('stderr', r.stderr), ('rc', str(r.returncode).encode())]:
                (out/(tag+'.'+suffix)).write_bytes(content)
            rec = {'tag': tag, 'rc': r.returncode, 'fixture_sha256': hashlib.sha256(b).hexdigest(),
                   'stdout': r.stdout.decode(), 'candidate_expected_rc': expected}
            records.append(rec)
            (out/'results.json').write_text(json.dumps(records, indent=2)+'\n')
            if variant == 'candidate':
                assert r.returncode == expected, rec
                assert json.loads(r.stdout)['open'] is (expected == 0)
    print(json.dumps({'candidate_cases': len(cases), 'calls': len(records), 'status': 'PASS'}))

if __name__ == '__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['original','candidate','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();check(a.original,a.candidate,a.out)
