#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def package():
 info=json.loads((H/'package.json').read_text());p=R.parent/info['package'];n5=R.parent/'westlake-generation-n5-6d001bb8'
 a=json.loads((p/'package.json').read_text());b=json.loads((n5/'package.json').read_text())
 assert sha(p/'package.json')==info['manifest_sha256']
 assert {k for k in a['files'] if a['files'][k]!=b['files'][k]}=={'payload/android/lib64/westlake_flutter/libwestlake_native_abi.so'}
 assert set(a['files'])==set(b['files'])
 for k,v in a['files'].items():assert sha(p/k)==v,k
 gate=json.loads((H/'native-gate.json').read_text());assert gate['status']=='REJECT' and not gate['errors']
 assert gate['gates']['N1']['rejected']==28 and gate['gates']['N2']['rejected']==156
 prop=json.loads((H/'exception-proposal.json').read_text());assert len(prop['entries'])==184
 assert all(e['package_manifest_sha256']==info['manifest_sha256'] for e in prop['entries'])
 assert 'native predeploy gate refused: REJECT' in (H/'dry-run.txt').read_text()
 for f in ['native_abi.c','bionic_stdio_compat.c']:assert (H/'src'/f).read_bytes()==(R/'benchmark/2026-09-30-n4-native/src'/f).read_bytes()
 print('PASS N6 private package, payload hashes, unchanged baseline C, strict rejection')
def handoff():
 for f in ['README.md','EXCEPTION-PROPOSAL.md','source-sha256.json','build-inputs.json','symbol-audit.json','results.json','source-evidence/n5-localsend-stack.txt']:assert (H/f).stat().st_size
 r=json.loads((H/'results.json').read_text());assert r['preserved_exports']==26 and r['added_exports']==4
 assert 'unverified' in (H/'README.md').read_text()
 print('PASS N6 offline handoff artifacts; human review required')
if __name__=='__main__': {'package':package,'handoff':handoff}[sys.argv[1]]()
