#!/usr/bin/env python3
"""Derive the observer from the exact T32 source; never edit that source."""
import argparse, difflib, hashlib
from pathlib import Path
D = Path(__file__).resolve().parent
BASELINE = '9dc302d9aa72eb1be8635d7bc4bc4306da76f0e45d2414d67bd96d024e2a24c6'
def generate(baseline):
    data = baseline.read_bytes()
    if hashlib.sha256(data).hexdigest() != BASELINE:
        raise ValueError('baseline SHA mismatch')
    source = data.decode()
    anchor = 'class EntryAbility extends UIAbility {\n'
    callback = "    onCreate() { this.record('created', {}); }"
    assert source.count(anchor) == source.count(callback) == 1
    result = source.replace(anchor, (D / 'observer.fragment.js').read_text() + '\n' + anchor)
    result = result.replace(callback, """    onCreate(want, launchParam) {
        observeLaunch(this, 'onCreate', want, launchParam);
        this.record('created', {});
    }
    onNewWant(want, launchParam) {
        observeLaunch(this, 'onNewWant', want, launchParam);
    }""")
    patch = ''.join(difflib.unified_diff(source.splitlines(True), result.splitlines(True),
        fromfile='a/EntryAbility.js', tofile='b/EntryAbility.js'))
    return result, patch
if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--baseline', type=Path, default=D/'sources/baseline/EntryAbility.js'); ap.add_argument('--check', action='store_true'); a = ap.parse_args()
    candidate, patch = generate(a.baseline)
    outputs = [(D/'sources/candidate/EntryAbility.js', candidate), (D/'candidate.patch', patch)]
    for p, text in outputs:
        if a.check:
            assert p.read_bytes() == text.encode(), 'regeneration differs: ' + p.name
        else: p.write_bytes(text.encode())
    print('exact baseline and deterministic candidate/patch verified' if a.check else 'candidate and patch generated')
