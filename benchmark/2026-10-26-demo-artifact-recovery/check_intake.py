#!/usr/bin/env python3
"""Check the independently anchored runtime requirement set against the release manifest."""
import argparse
import hashlib
import json
from pathlib import Path


def compare(required, manifest):
    files = {row['path']: row for row in manifest['files']}
    missing, mismatched = [], []
    for row in required['files']:
        if not row.get('required', True):
            continue
        actual = files.get(row['stage_path'])
        if actual is None:
            missing.append(row['stage_path'])
        elif (actual['sha256'] != row['sha256'] or
              ('size' in row and actual['size'] != row['size'])):
            mismatched.append(row['stage_path'])
    return {'required': sum(r.get('required', True) for r in required['files']),
            'missing': missing, 'mismatched': mismatched,
            'complete_declared_runtime': not missing and not mismatched}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--intake', type=Path, default=Path(__file__).parent/'intake')
    ap.add_argument('--repo', type=Path, default=Path(__file__).resolve().parents[2])
    args = ap.parse_args()
    required = json.loads((args.intake/'required-runtime.json').read_text())
    manifest = json.loads((args.intake/'manifest.json').read_text())
    result = compare(required, manifest)
    result['anchor_mismatches'] = []
    for anchor in required['anchors']:
        p = args.repo/anchor['path']
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != anchor['sha256']:
            result['anchor_mismatches'].append(anchor['path'])
    print(json.dumps(result))
    return 0 if result['complete_declared_runtime'] and not result['anchor_mismatches'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
