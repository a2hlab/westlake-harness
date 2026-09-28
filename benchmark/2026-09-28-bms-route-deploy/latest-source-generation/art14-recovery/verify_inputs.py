"""Compare every selected frozen source input, retaining each mismatch/missing path."""
import argparse
import hashlib
import json
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--manifest', type=Path, required=True)
p.add_argument('--root', type=Path, required=True)
p.add_argument('--prefix', default='./aosp/art/')
p.add_argument('--out', type=Path, required=True)
a = p.parse_args()
entries = []
for line in a.manifest.read_text().splitlines():
    digest, name = line.split(maxsplit=1)
    if name.startswith(a.prefix):
        relative = name[len(a.prefix):]
        assert relative and '..' not in Path(relative).parts
        entries.append((digest, relative))
assert entries, 'empty selected manifest'
assert len(set(name for _, name in entries)) == len(entries), 'duplicate paths'
missing = []; mismatches = []; matched = 0
for expected, name in entries:
    f = a.root / name
    if not f.is_file():
        missing.append({'path': name, 'expected': expected})
        continue
    actual = hashlib.sha256(f.read_bytes()).hexdigest()
    if actual == expected:
        matched += 1
    else:
        mismatches.append({'path': name, 'expected': expected, 'actual': actual})
r = {'manifest_sha256': hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
     'root': str(a.root.resolve()), 'prefix': a.prefix, 'expected_count': len(entries),
     'matched': matched, 'missing': missing, 'mismatches': mismatches,
     'passed': matched == len(entries)}
a.out.write_text(json.dumps(r, indent=2) + '\n')
print(json.dumps({k: v for k,v in r.items() if k not in ('missing', 'mismatches')}, indent=2))
print('missing',len(missing),'mismatched',len(mismatches))
raise SystemExit(0 if r['passed'] else 1)
