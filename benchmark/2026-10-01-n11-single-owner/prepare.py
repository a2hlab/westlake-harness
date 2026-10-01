"""N10b plus N11 native over U8; preserve Java/boot/frozen objects."""
import hashlib,json,os,shutil,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];WS=R.parent
sys.path.insert(0,str(R/'scripts/lab'));import generation_bundle as gb
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();save=lambda p,j:p.write_text(json.dumps(j,indent=2)+'\n')
source=WS/'westlake-generation-n10b-batch-bundle-u8-ac59dec0';base=WS/'westlake-generation-u8-j9-t7e';_,old,baseline=gb.validate(base)
host=WS/'westlake-n11-build/host/candidate/appspawn-x';runtime=WS/'westlake-n11-build/runtime/candidate/runtime-out/liboh_android_runtime.so'
tag=sha(runtime)[:8];bundle=WS/('westlake-generation-n11-u8-'+tag);assert not bundle.exists();shutil.copytree(source,bundle);native=bundle/'native';m=load_package(native)
for key,file in {'payload/runtime/appspawn-x':host,'payload/android/lib64/liboh_android_runtime.so':runtime}.items():
 before=m['files'][key];after=sha(file);shutil.copy2(file,native/key);m['files'][key]=after
 for p,v in m['live_hashes'].items():
  if v==before:m['live_hashes'][p]=after
save(native/'package.json',m);validate_upgrade(old,load_package(native));manifest=sha(native/'package.json');c=native/'native-checks';scan=json.loads((c/'scan-manifest.json').read_text())
for name,file in {'n4-host.c':H/'src/host.c','n11-compat.cpp':H/'src/android_graphics_compat_shim.cpp'}.items():
 shutil.copy2(file,c/name);scan['sources'][name]={'path':name,'sha256':sha(file),'origin':str(file.relative_to(R)),'source_sha256':sha(file),'first_line':1}
scan['profiles'].append({'name':'n11-compat-owner','rule':'jni-order','sources':['n11-compat.cpp'],'entry_source':'n11-compat.cpp','entry_function':'resolve_oh_wm_funcs','identity':{'artifact':'payload/android/lib64/liboh_android_runtime.so'}})
for p in scan['profiles']:p['identity'].update(package=bundle.name,manifest_sha256=manifest,artifact_sha256=m['files'][p['identity']['artifact']])
save(c/'scan-manifest.json',scan);g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=manifest;g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
b=json.loads((bundle/'bundle.json').read_text());b['native']['manifest']['sha256']=manifest;b['rollout_ready']=False;b['rollout_blocker']='N11 exact gate exceptions pending outer approval; U8 only short window'
save(bundle/'bundle.json',b);_,_,expected=gb.validate(bundle);changed={p:[baseline[p],expected[p]] for p in baseline if baseline[p]!=expected[p]}
assert set(changed)=={'/system/bin/appspawn-x','/system/lib64/appspawn/libwestlake_android_child.z.so','/system/android/lib64/liboh_android_runtime.so'}
record={'bundle':bundle.name,'native_manifest_sha256':manifest,'bundle_sha256':sha(bundle/'bundle.json'),'changed':changed,'identity_count':len(expected),'baseline':'U8','device_io':False,'provider_unchanged':True}
save(H/'package.json',record);print(json.dumps(record,indent=2))
