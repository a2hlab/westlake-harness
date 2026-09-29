"""Prepare an isolated-input generation using R155 bytes and the original entry sources."""
from pathlib import Path
import hashlib,json,re,shutil,subprocess
r=Path.cwd();rw=r/'bms/src/.work/b6-real-work';w=r/'bms/src/.work/b6-task47';t=r/'benchmark/2026-09-28-bms-route-deploy/latest-source-generation/task47'
p=rw/'adapter/framework/appspawn-x/security_specialization/stock_child_plugin';g=p/'out/route-a-generation';live=r/'bms/src/.work/b6-r155/live/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d';orig=r.parent/'01.OH61AOSP16/real-work/src/adapter/framework/appspawn-x'
sha=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
# End the superseded no-image experiment by restoring its two source inputs.
for s in ['src/appspawnx_runtime.cpp','security_specialization/stock_child_plugin/src/westlake_android_runtime_provider.cpp']:
 shutil.copy2(orig/s,rw/'adapter/framework/appspawn-x'/s)
# Keep old round directories for investigation; rebuild into empty output trees.
for path in [g,p/'out/target']:
 backup=w/(path.name+'-before47')
 assert not backup.exists()
 path.rename(backup);path.mkdir()
for d in ['providers','pass1/registry','pass2/registry','logs']:(g/d).mkdir(parents=True,exist_ok=True)
for f in live.glob('*.so'):
 if f.name!='libwestlake_android_runtime_provider.so':shutil.copy2(f,g/'providers'/f.name)
shutil.copy2(r/'bms/src/.work/b6-task45/providers/libsigchain.so',g/'providers/libsigchain.so')
shutil.copy2(w/'bridge/libwestlake_art_abort_bridge.so',g/'providers/libwestlake_art_abort_bridge.so')
for name in ['libwestlake_thread_guard_registry.so']:
 for pas in ['pass1','pass2']:shutil.copy2(live/name,g/pas/'registry'/name)
# Provider link search directory uses the same preserved bytes as the manifest.
base=rw/'rebuilt-provider-base/providers'
for f in base.glob('*.so'):f.unlink()
for f in (g/'providers').glob('*.so'):shutil.copy2(f,base/f.name)
(rw/'retained-providers.sha256').write_text(''.join(f'{sha(f)}  {f.name}\n' for f in sorted((g/'providers').glob('*.so'))))
# Pin baseline native roots, fetched read-only from the signed B5 device.
expected={'liboh_adapter_bridge.so':'84695d62f515cfec6bb317c959ec55b1d5085bf82303f792a764cf549a22267a','liboh_android_runtime.so':'9ccf64f8d1f6e1748665057273eaa4c2770098934d39afa160f2c6b4c18b06db'}
env=(p/'r45_adapter_identity.env').read_text()
for name,sh in expected.items():
 f=w/'baseline-native'/name;assert sha(f)==sh
 shutil.copy2(f,rw/'adapter/frozen/r45-dynamic-roots'/name)
 prefix='WLAR_ADAPTER_BRIDGE' if 'adapter_bridge' in name else 'WLAR_ANDROID_RUNTIME'
 notes=subprocess.check_output(['/opt/homebrew/opt/llvm/bin/llvm-readelf','-n',str(f)],text=True)
 bid=re.search(r'Build ID: ([0-9a-f]+)',notes).group(1)
 env=re.sub(prefix+'_SHA256_HEX=.*',prefix+'_SHA256_HEX='+sh,env)
 env=re.sub(prefix+'_BUILD_ID_HEX=.*',prefix+'_BUILD_ID_HEX='+bid,env)
(p/'r45_adapter_identity.env').write_text(env)
(rw/'adapter/frozen/r45-dynamic-roots/SHA256SUMS').write_text(''.join(f'{sh}  {n}\n' for n,sh in expected.items()))
inner=(t.parent/'task45/recipes/build-retained-generation-inner.sh').read_text()
inner=inner.replace('-lhilog -lnativehelper -llog -lbionic_compat -lart -lbase -lnativeloader -lc++','-lhilog -lnativehelper -llog -lbionic_compat -lwestlake_art_abort_bridge -lart -lbase -lnativeloader -lc++')
(rw/'build-retained-generation-inner.sh').write_text(inner)
shutil.copy2(rw/'build-retained-generation-inner.sh',t/'recipes/build-retained-generation-inner.sh')
shutil.copy2(t.parent/'task45/recipes/build-retained-generation.sh',rw/'build-retained-generation.sh')
shutil.copy2(rw/'build-retained-generation.sh',t/'recipes/build-retained-generation.sh')
rows=[{'name':f.name,'r155_sha256':sha(f),'candidate_sha256':sha(g/'providers'/f.name),'same_bytes':f.read_bytes()==(g/'providers'/f.name).read_bytes()} for f in sorted(live.glob('*.so')) if f.name!='libwestlake_android_runtime_provider.so']
assert [x['name'] for x in rows if not x['same_bytes']]==['libsigchain.so']
(t/'preserved-provider-inputs.json').write_text(json.dumps({'preserved_count':26,'changed':['libsigchain.so','libwestlake_android_runtime_provider.so'],'added':['libwestlake_art_abort_bridge.so'],'runtime_provider_rebuild_authorized':True,'rows':rows},indent=2)+'\n')
print('PASS 26 original providers preserved; sigchain + runtime-provider + bridge differ')
