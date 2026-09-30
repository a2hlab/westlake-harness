#!/usr/bin/env python3
"""Assemble one declared N3 upgrade from signed N2; preserve every unrelated byte."""
import argparse,json,hashlib,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parents[2];report=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('base',type=Path);ap.add_argument('out',type=Path);a=ap.parse_args()
sys.path.insert(0,str(r/'scripts/lab'));from deploy_generation import load_package,validate_upgrade
m=load_package(a.base)
if not a.out.exists():subprocess.run(['/bin/cp','-Rc',str(a.base),str(a.out)],check=True)
changes=[]
def put(src,rel,target):
 data=src.read_bytes();h=hashlib.sha256(data).hexdigest();f=a.out/rel;f.parent.mkdir(parents=True,exist_ok=True)
 if f.is_symlink():raise ValueError('replacement may not follow symlink: '+rel)
 if f.exists():f.chmod(f.stat().st_mode|0o200)
 f.write_bytes(data);m['files'][rel]=h;m['live_hashes'][target]=h
 changes.append({'source':str(src),'file':rel,'target':target,'sha256':h})
g=m['generation'];b=r/'bms/src/.work/n3-native'
put(b/'runtime-out/liboh_android_runtime.so','payload/android/lib64/liboh_android_runtime.so','/system/android/lib64/liboh_android_runtime.so')
for name,folder in [('libapp_native_loader.so','flutter')]:
 for rel,target in [('payload/android/lib64/'+name,'/system/android/lib64/'+name),('payload/route/'+name,'/system/lib64/westlake/route-a/'+g+'/'+name)]:put(b/folder/name,rel,target)
for rel,target in [('payload/android/lib64/libwestlake_native_abi.so','/system/android/lib64/libwestlake_native_abi.so'),('payload/android/lib64/westlake_flutter/libwestlake_native_abi.so','/system/android/lib64/westlake_flutter/libwestlake_native_abi.so'),('payload/android/lib64/westlake_native/libwestlake_native_abi.so','/system/android/lib64/westlake_native/libwestlake_native_abi.so')]:
 put(b/'flutter/libwestlake_native_abi.so',rel,target)
put(b/'host/appspawn-x-1','payload/runtime/appspawn-x','/system/bin/appspawn-x')
# Reuse byte-identical, previously published Westlake facade files.
for name in ['libandroid.so','libGLESv2.so','libjnigraphics.so']:
 put(a.base/'payload/android/lib64/westlake_flutter'/name,'payload/android/lib64/westlake_native/'+name,'/system/android/lib64/westlake_native/'+name)
put(a.base/'payload/android/lib64/libstdc++.so','payload/android/lib64/westlake_native/libstdc++.so','/system/android/lib64/westlake_native/libstdc++.so')
m['rollout_ready']=False;m['rollout_blocker']='N3 device review pending; baseline U2/N2 preserved elsewhere'
(a.out/'package.json').write_text(json.dumps(m,indent=2)+'\n');(report/'package-changes.json').write_text(json.dumps(changes,indent=2)+'\n')
validate_upgrade(load_package(a.base),load_package(a.out));print('N3 declared targets:',len(changes))
