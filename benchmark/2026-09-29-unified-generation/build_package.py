#!/usr/bin/env python3
"""Copy the accepted generation bytes; never rebuild or modify sealed manifests."""
import hashlib,json,shutil,sys
from pathlib import Path
R=Path(__file__).resolve().parents[2]; E=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'scripts/lab'));from deploy_generation import GEN,sha,save
out=Path(sys.argv[1]).resolve();out.mkdir(parents=True,exist_ok=False)
P=R/'bms/src/.work/b6-real-work/adapter/framework/appspawn-x/security_specialization/stock_child_plugin'
T=R/'benchmark/2026-09-28-bms-route-deploy/latest-source-generation/task58-route'
rows=json.loads((E/'android-sources.local.json').read_text())
def cp(source,name):
 p=out/name;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,p)
for row in rows:
 assert sha(row['source'])==row['sha256'];cp(row['source'],'payload/android/'+row['target'].removeprefix('/system/android/'))
for f in (P/'out/route-a-generation/providers').glob('*.so'):cp(f,'payload/route/'+f.name)
cp(P/'out/route-a-generation/libwestlake_android_runtime_provider.so','payload/route/libwestlake_android_runtime_provider.so')
cp(P/'out/route-a-generation/appspawn-x-stock','payload/runtime/appspawn-x')
cp(P/'out/target/libwestlake_android_child.z.so','payload/runtime/libwestlake_android_child.z.so')
base=Path('/Users/zhaoyue/orca/.bridge-payload/pr03-74e6-portable')
cp(base/'runtime/appdata-sandbox.json','payload/runtime/appdata-sandbox.json')
zig=R.parent/'westlake-bms-suite/var/state/b6-quick/candidates/b5-alias-b6-context/files'
for name in ['libmediandk.so','libwestlake_bionic_signal_box.so','libmain.so','libil2cpp.so','libtuanjie.so']:cp(zig/name,'payload/zigzag/'+name)
for name in ['generation-verification.json','ROUTE_A_INPUTS.json','SOURCE_CLOSURE.json','closure.json','closure-negatives.json','static-dispositions.json','v1-host-tests.json','provider-comparison.json']:
 cp(T/name,'receipts/'+name)
cp(R/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py','tools/bms_batch.py')
cp(R/'scripts/lab/deploy_generation.py','tools/deploy_generation.py');cp(R/'scripts/lab/deploy_generation.sh','tools/deploy_generation.sh')
route='/system/lib64/westlake/route-a/'+GEN
mounts=[('payload/android','/system/android'),('payload/route',route)]
for name in ['libsigchain.so','libwestlake_android_runtime_provider.so','libwestlake_thread_guard_registry.so']:
 mounts.append(('payload/route/'+name,'/system/android/lib64/'+name))
mounts.append(('payload/route/libwestlake_thread_guard_registry.so','/system/lib64/libwestlake_thread_guard_registry.so'))
mounts += [('payload/runtime/appdata-sandbox.json','/system/etc/sandbox/appdata-sandbox.json'),('payload/runtime/libwestlake_android_child.z.so','/system/lib64/appspawn/libwestlake_android_child.z.so'),('payload/runtime/appspawn-x','/system/bin/appspawn-x')]
for p in sorted((out/'payload/zigzag').iterdir()):mounts.append(('payload/zigzag/'+p.name,'/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/'+p.name))
files={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
live={}
for source,target in mounts:
 if source in files:live[target]=files[source]
for name in ['libart.so','libopenjdkjvm.so','libwestlake_art_abort_bridge.so']:live[route+'/'+name]=files['payload/route/'+name]
for name in ['liboh_adapter_bridge.so','liboh_android_runtime.so']:live['/system/android/lib64/'+name]=files['payload/android/lib64/'+name]
for name in ['oh-adapter-runtime.jar','framework.jar','arm64/boot-framework.oat']:live['/system/android/framework/'+name]=files['payload/android/framework/'+name]
v=json.loads((T/'generation-verification.json').read_text())
assert live['/system/bin/appspawn-x']==v['stock_host_sha256']
assert live[route+'/libart.so']==v['libart_sha256']
assert files['payload/route/libsigchain.so']==v['libsigchain_sha256']
assert len(list((out/'payload/route').iterdir()))==29
m={'schema':1,'generation':GEN,'source_commit':'d1046892fe6f66456459acc630854b756040f954','source_boot':'e36781a9-2ba1-4804-b8e5-2a1125c39a47','files':files,'mounts':[{'source':s,'target':t} for s,t in mounts],'live_hashes':live,'prerequisites':{'/system/lib64/chipset-sdk-sp/libc++.so':'9466fb0d933689533bdf4b4962907f3e0c0970be278bd6ccf703ffa2aea838a6'}}
save(out/'package.json',m);save(E/'package-manifest.json',m)
print(json.dumps({'path':str(out),'files':len(files),'mounts':len(mounts),'bytes':sum(p.stat().st_size for p in out.rglob('*') if p.is_file()),'manifest_sha256':sha(out/'package.json')},indent=2))
