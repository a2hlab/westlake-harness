#!/usr/bin/env python3
"""Check and stage the original interpreted Boat overlay sources without device access."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

HERE = Path(__file__).resolve().parent

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    lock = json.loads((HERE / 'source.lock.json').read_text())
    for entry in lock['files']:
        actual = hashlib.sha256((HERE / entry['path']).read_bytes()).hexdigest()
        if actual != entry['sha256']:
            raise SystemExit('source SHA mismatch: ' + entry['path'])
    if args.out:
        if args.out.exists():
            raise SystemExit('--out must be a new directory')
        shutil.copytree(HERE / 'payload', args.out)
    print('PASS 5 original source pins; interpreted scripts/config only; no binary build or deployment')

if __name__ == '__main__':
    main()
