import hashlib,json,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'))
import deployment_native_gate as gate
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
base=R.parent/'westlake-generation-n7-fa9ec3c6';new=R.parent/'westlake-generation-n8-private-zlib'
a=json.loads((base/'package.json').read_text());b=json.loads((new/'package.json').read_text());removed='payload/android/lib64/libz.so'
assert set(a['files'])-set(b['files'])=={removed} and not set(b['files'])-set(a['files'])
assert not (new/removed).exists() and '/system/android/lib64/libz.so' not in b['live_hashes']
assert all(a['files'][p]==v==sha(new/p) for p,v in b['files'].items())
assert b['files']['payload/android/lib64/westlake_native/libz.so']==a['files'][removed]
identity=sha(new/'package.json');side=json.loads((new/'native-checks/native-gates.json').read_text());assert side['package_manifest_sha256']==identity
for p in json.loads((new/'native-checks/scan-manifest.json').read_text())['profiles']:
 assert p['identity']['manifest_sha256']==identity and p['identity']['artifact_sha256']==b['files'][p['identity']['artifact']]
 if p['name']=='egl-facade':assert p['identity']['artifact'].endswith('westlake_flutter/libEGL.so')
gate.configure_experiment(R/'benchmark/2026-10-01-n7-window/window.json','61b0657200000000000000000324012c');assert gate.experiment_entries(identity)==([],None);gate.configure_experiment(None,None)
r=json.loads((H/'native-gate.json').read_text());assert r['package_manifest_sha256']==identity and r['status']=='REJECT' and not r['errors'];assert sum(g['rejected'] for g in r['gates'].values())==185
print('PASS removal-only payload, corrected sidecar binding, no inherited N7 authorization, strict rejection')
