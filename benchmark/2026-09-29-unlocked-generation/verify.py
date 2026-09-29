#!/usr/bin/env python3
"""B9 evidence checks; a screenshot regression must remain a failing scenario."""
import hashlib,json,subprocess,sys
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[1]
d=json.loads((E/'results.json').read_text());key=sys.argv[1]
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def app(label):
 a=d['apps'][label]
 for s in a['screens'].values():assert sha(E/s['path'])==s['sha256']
 return a
if key=='swap':
 a=app('swap-helloworld');assert a['visual_inner']=='own UI' and not any(a['admission_errors'].values())
 proofs=list((E/'evidence/swap-helloworld').glob('child-proof-*.sha256'));assert proofs
 assert any('84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a  /proc/' in p.read_text() for p in proofs)
 assert any('/system/android/lib64/liboh_adapter_bridge.so' in p.read_text() for p in (E/'evidence/swap-helloworld').glob('*maps*'))
elif key=='exports':
 s=(E/('v3a-bridge-exports.txt' if 'v3a' in d else 'window-bridge-exports.txt')).read_text()
 for symbol in ['nativeParseManifestJson','nativeGetSysProp']:assert 'Java_adapter_activity_AppSchedulerBridge_'+symbol in s
 assert json.loads((E/'final-package-manifest.json').read_text())['bridge_sha256']==d['final_bridge']
elif key=='application':
 assert d['user_override'].startswith('fd-android substitutes fd-k9')
 if 'v3a' in d:
  for k in ['fd-android','ooniprobe']:
   a=d['v3a']['apps'][k];assert a['providers'] and min(map(int,a['providers']))>0
   assert not a['old_koin_wall'] and not a['application_cast_error']
 else:
  for k in ['final-fd-android','final-ooniprobe']:
   a=app(k);assert a['providers'] and min(a['providers'])>0
   assert not a['old_koin_wall'] and not a['application_cast_error']
elif key=='missing':
 subprocess.run([sys.executable,str(E/'test_host_gates.py'),'Gates.test_required_sources_and_zip'],check=True)
elif key=='regression':
 if 'v3a' in d:
  for k in ['helloworld','zigzag']:
   a=d['v3a'][k];assert sha(E/a['screen'])==a['sha256'];assert a['visual_inner']=='own UI'
 else:
  assert sha(E/d['final_helloworld']['screen'])==d['final_helloworld']['sha256']
  assert d['final_helloworld']['visual_inner']=='own UI'
  assert app('final-zigzag')['visual_inner']=='own UI','ZigZag rebuilt bridge screenshot is white'
elif key=='mismatch':
 n=d['negative_package'];assert n['returncode']!=0 and n['rejected_before_device_io'] and n['unchanged'] and n['before']==n['after']
 subprocess.run([sys.executable,str(E/'test_host_gates.py'),'Gates.test_double_art_gate','TransactionRollback.test_post_swap_maps_failure_restores_previous_file'],check=True)
elif key=='rollback':
 r=d['rollback'];assert r['status']=='rolled_back' and r['baseline_generation'].startswith('6cb40cd6')
 assert r['baseline_sha_match'] and r['baseline_gate']['passed']
else:raise ValueError(key)
print('PASS B9',key)
