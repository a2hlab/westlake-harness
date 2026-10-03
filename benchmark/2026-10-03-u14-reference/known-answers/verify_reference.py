#!/usr/bin/env python3
"""U14 reference known answers: lit count == 126, every t20 exists, SHA matches sources.json."""
import hashlib, json, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WS = HERE.parents[3]   # known-answers/ is one level deeper than the script dir

src = json.loads((HERE.parent / 'sources.json').read_text())
lit = sum(1 for e in src['keys'].values() if e['verdict'] == 'lit')
print(f'lit count: {lit} (want 126)')
assert lit == 126

bad = 0
nonlit_missing = 0
for key, e in sorted(src['keys'].items()):
    t20 = e.get('t20')
    if not t20:
        if e['verdict'] == 'lit':
            print(f'{key}: LIT but t20 is None')
            bad += 1
        else:
            nonlit_missing += 1   # inherited from the base grid; a non-lit key never had a t20
        continue
    p = Path(str(t20).replace('$WORKSPACES', str(WS)))
    if not p.is_file():
        print(f'{key}: t20 file does not exist: {p}')
        bad += 1
        continue
    got = hashlib.sha256(p.read_bytes()).hexdigest()
    want = e.get('t20_sha256')
    if want and got != want:
        print(f'{key}: sha mismatch recorded={want[:12]} actual={got[:12]}')
        bad += 1
print(f'checked {len(src["keys"])} keys; lit problems: {bad}; non-lit without t20 (info): {nonlit_missing}')
sys.exit(1 if bad else 0)
