"""Compose U9/J10g and smoke inputs without approving deployment."""
import argparse,hashlib,json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[2]
sys.path.insert(0,str(R/'scripts/lab'))
import lab_paths,generation_bundle as gb,u7_executor as u,check_frozen as frozen
W=lab_paths.workspaces()
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
p=argparse.ArgumentParser()
p.add_argument('--jar',type=Path,default=W/'westlake-generation-j10g-staging/oh-adapter-runtime-j10g.jar')
p.add_argument('--jar-sha',default='238ffc148620ab5a1311c0cdb4fb7eddc50a9ae69a8465744c1824dcc8b01426')
p.add_argument('--out',type=Path,default=W/'westlake-generation-u9-j10g-238ffc14')
p.add_argument('--extra-smoke',type=Path,help='add markers/groups from the final JAR donor smoke spec')
a=p.parse_args()
base=W/'westlake-generation-u8-j9-t7e'
source=W/'westlake-generation-u9-native-33558acd'
jar=a.jar
assert len(a.jar_sha)==64 and sha(jar)==a.jar_sha
out=a.out
assert not out.exists();shutil.copytree(source,out)
d=json.loads((out/'bundle.json').read_text());_,_,resident=gb.validate(base)
shutil.copy2(jar,out/d['runtime_jar']['source']);d['runtime_jar']['sha256']=sha(jar)
for row in d['reference'].values():
 paths=gb.read_fingerprint(base/row['source'])
 (out/row['source']).write_text('\n'.join(sorted(f'{resident[p]}  {p}' for p in paths))+'\n')
 row['sha256']=sha(out/row['source'])
d['rollout_ready']=False
d['rollout_blocker']='Final J10g acceptance required; installer unchanged'
d.pop('service_group',None)
shutil.rmtree(out/'installer')
save(out/'bundle.json',d)
plan=u.prepare(out,base/'native')
assert plan['baseline']==u.prepare(base,base/'native')['expected']
fp=u.fingerprints(plan['expected'],plan['reference_paths'])
save(H/'package.json',{'bundle':out.name,'bundle_sha256':sha(out/'bundle.json'),'native_manifest_sha256':d['native']['manifest']['sha256'],'jar_sha256':sha(jar),'identities':len(plan['expected']),'fingerprints':fp,'rollout_ready':False,'device_io':False})
spec=json.loads((R/'knowledge/smoke/n10b.json').read_text())
spec['expect']={'runtime_fp':fp['runtime']['sha256_12'],'boot_fp':fp['boot']['sha256_12']}
corpus='$WORKSPACES/westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json'
inputs='$WORKSPACES/westlake-inputs/corpus-v2/app-inputs'
spec['groups'].append({'manifest':corpus,'input_root':inputs,'mode':'reinstall','keys':['cv2-com-deva-knot','cv2-com-caniwebview-android','cv2-com-degeder-yam']})
spec['fixes'] += [
 {'id':'J10d-THEME','key':'cv2-com-deva-knot','markers':[r'\[J10d-THEME\]']},
 {'id':'J10e-DELEGATE','key':'cv2-com-caniwebview-android','markers':[r'\[J10e-WEBVIEW\] delegate forwards setLayoutParams']},
 {'id':'J10e-COOKIE','key':'cv2-com-degeder-yam','markers':[r'\[J10e-WEBVIEW\] CookieManager stub installed']},
 {'id':'J10f-SETTINGS','key':'cv2-com-caniwebview-android','markers':[r'\[J10f-WEBVIEW\] settings stub installed']},
]
if a.extra_smoke:
 donor=json.loads(a.extra_smoke.read_text())
 ids={f['id'] for f in spec['fixes']}
 spec['fixes'] += [f for f in donor.get('fixes',[]) if f['id'] not in ids]
 for group in donor.get('groups',[]):
  if not group.get('controls'):
   portable=json.loads(json.dumps(group).replace(str(W),'$WORKSPACES'))
   spec['groups'].append(portable)
spec['probe']['single_copy']=['libart.so','libopenjdkjvm.so','liboh_adapter_bridge.so','liboh_android_runtime.so']
spec['probe']['expect_copies']={'liboh_adapter_bridge.so':2,'liboh_android_runtime.so':2}
spec['probe']['files'][d['runtime_jar']['target']]=sha(jar)
baseline_services={'libbms.z.so':'6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9','libapk_installer.so':'7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18'}
for name,value in baseline_services.items():
 for directory in ['/system/lib64','/system/lib64/platformsdk']:
  spec['probe']['files'][directory+'/'+name]=value
save(H/'smoke.json',spec)
services={p:v for p,v in spec['probe']['files'].items() if Path(p).name in baseline_services}
lines,bad=frozen.check_artifacts(frozen.active(frozen.load(R/'knowledge/frozen/frozen.json')),services,'unchanged U8 installer')
save(H/'service-frozen-precheck.json',{'violations':bad,'lines':lines,'registry_sha256':sha(R/'knowledge/frozen/frozen.json'),'device_io':False})
print(json.dumps({'package':out.name,'fingerprints':fp,'baseline_exact':True,'service_freeze_violations':bad,'device_io':False},indent=2))
