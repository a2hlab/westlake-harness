#!/usr/bin/env python3
"""Offline real-callback tests plus source/patch regeneration and rejection."""
import hashlib, subprocess, sys, tempfile
from pathlib import Path
sys.dont_write_bytecode = True
from generate import BASELINE, D, generate
baseline = D/'sources/baseline/EntryAbility.js'
original = baseline.read_bytes()
candidate, patch = generate(baseline)
assert (D/'sources/candidate/EntryAbility.js').read_bytes() == candidate.encode()
assert (D/'candidate.patch').read_bytes() == patch.encode()
with tempfile.TemporaryDirectory(prefix='t39-') as tmp:
    wrong = Path(tmp)/'EntryAbility.js';wrong.write_bytes(original+b'\n')
    try: generate(wrong)
    except ValueError as e: assert str(e)=='baseline SHA mismatch'
    else: raise AssertionError('changed baseline accepted')
    # Apply the delivered patch with the ordinary local patch tool.
    wrong.write_bytes(original)
    r=subprocess.run(['patch','--batch','-p1','-i',str(D/'candidate.patch')],cwd=tmp,capture_output=True,text=True)
    assert r.returncode == 0, (r.stdout,r.stderr)
    assert wrong.read_bytes() == candidate.encode()
assert baseline.read_bytes() == original
assert hashlib.sha256(original).hexdigest() == BASELINE
print('PASS deterministic regeneration, real patch application and altered-baseline rejection',flush=True)
r=subprocess.run(['node',str(D/'test_callbacks.cjs')])
raise SystemExit(r.returncode)
