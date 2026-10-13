#!/usr/bin/env python3
"""Read-only verification of the fixed W3 inventory; emit an outer-owned tar list."""
import argparse
import hashlib
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--out-list', type=Path, required=True)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent / 'archive'
    index = json.loads((base / 'index.json').read_text())
    root = args.root.resolve()
    destination = args.out_list.resolve()
    if destination.is_relative_to(root):
        raise ValueError('output list must be outside evidence root')
    names = []
    total = 0
    for part in index['parts']:
        manifest, paths = base / part['manifest'], base / part['paths']
        if digest(manifest) != part['sha256'] or digest(paths) != part['paths_sha256']:
            raise ValueError('inventory part drift: ' + part['manifest'])
        part_names = []
        for line in manifest.read_text().splitlines():
            expected, size, name = line.split('\t', 2)
            relative = Path(name)
            path = root / relative
            if relative.is_absolute() or '..' in relative.parts or path.is_symlink():
                raise ValueError('unsafe member: ' + name)
            if not path.resolve().is_relative_to(root):
                raise ValueError('member escapes root: ' + name)
            if path.stat().st_size != int(size) or digest(path) != expected:
                raise ValueError('evidence drift: ' + name)
            part_names.append(name)
            total += int(size)
        if paths.read_text().splitlines() != part_names:
            raise ValueError('tar list differs from manifest')
        names.extend(part_names)
    if len(set(names)) != len(names) or len(names) != index['files'] or total != index['bytes']:
        raise ValueError('inventory totals/uniqueness mismatch')
    actual = {str(p.relative_to(root)) for p in root.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    with destination.open('x') as output:
        output.write(''.join(name + '\n' for name in names))
    print(json.dumps({'status': 'PASS_DECLARED_BYTES', 'files': len(names), 'bytes': total,
                      'later_additions_not_in_archive': sorted(actual - set(names)),
                      'remote_archive_verified': False}))


if __name__ == '__main__':
    main()
