#!/usr/bin/env python3
"""Verify packaged static claims, not proposed counterexamples or runtime success."""
from pathlib import Path
import json,hashlib
D=Path(__file__).resolve().parent
r=json.loads((D/'results.json').read_text());o=json.loads((D/'objects.json').read_text())
assert r['loader_sha256']==o['loader']['sha256']=='878c7019b1b78c8affbf9808d69fdc8478554273fe5d06d499b6775b7d004f23'
assert r['bootstrap_flags']==2 and r['actual_bootstrap_winner']=='UNKNOWN_STATE_DEPENDENT'
t=(D/'exact-pc-excerpts.txt').read_text()
for needle in ['5b80:','65a8:','35dc:','ceac:','cefc:','cfec:','d0fc:','d130:','d190:','d5bc:']:
 assert any(l.strip().startswith(needle) for l in t.splitlines()),needle
assert 'mov\tw2, #0x2 ' in t and 'mov\tw2, #0x102 ' in t
p=json.loads((D/'provider-build-chain.json').read_text())
assert p['native_abi_original']['sha256']=='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
c=json.loads((D/'counterexamples.json').read_text());assert c['status']=='DESIGN_ONLY_NOT_EXECUTED' and len(c['cases'])==9
assert not r['implementation'] and not r['counterexamples_executed'] and r['device_calls']==0
if (D/'manifest.json').exists():
 for x in json.loads((D/'manifest.json').read_text())['files']:
  p=D/x['path'];assert p.stat().st_size==x['bytes'] and hashlib.sha256(p.read_bytes()).hexdigest()==x['sha256'],p
print(json.dumps({'status':'PASS','exact_PC_anchors':10,'proposal_cases':9,'proposal_cases_executed':0,'actual_bootstrap_winner':'UNKNOWN','devices':0,'production_builds':0}))
