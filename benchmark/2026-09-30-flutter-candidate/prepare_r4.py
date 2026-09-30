#!/usr/bin/env python3
"""Clone resident generation; atomically declared Flutter directory + ANL aliases."""
import argparse,hashlib,json,shutil,subprocess,sys
from pathlib import Path
P=argparse.ArgumentParser();P.add_argument('base',type=Path);P.add_argument('out',type=Path);a=P.parse_args()
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade
m=load_package(a.base);r3=json.loads((Path(__file__).parent/'evidence-r3/artifacts.json').read_text())
if a.out.exists():raise ValueError('output already exists')
subprocess.run(['/bin/cp','-Rc',str(a.base),str(a.out)],check=True)
changes=[]
def put(source,relative,target):
 data=source.read_bytes();sha=hashlib.sha256(data).hexdigest();f=a.out/relative;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data);m['files'][relative]=sha;m['live_hashes'][target]=sha;changes.append({'source':str(source),'file':relative,'target':target,'sha256':sha})
for src,dest in [('libwestlake_flutter_android.so','libandroid.so'),('libwestlake_flutter_gles2.so','libGLESv2.so'),('libwestlake_flutter_jnigraphics.so','libjnigraphics.so')]:
 f=repo/'bms/src/.work/flutter-candidate'/src
 assert hashlib.sha256(f.read_bytes()).hexdigest()==r3[src]['sha256']
 put(f,'payload/android/lib64/westlake_flutter/'+dest,'/system/android/lib64/westlake_flutter/'+dest)
for relative,target in [('payload/android/lib64/libapp_native_loader.so','/system/android/lib64/libapp_native_loader.so'),('payload/route/libapp_native_loader.so','/system/lib64/westlake/route-a/'+m['generation']+'/libapp_native_loader.so')]:
 put(repo/'bms/src/.work/flutter-r4/libapp_native_loader.so',relative,target)
m['rollout_ready']=False;m['rollout_blocker']='pending controlled 61b validation'
(a.out/'package.json').write_text(json.dumps(m,indent=2)+'\n')
new=load_package(a.out);validate_upgrade(load_package(a.base),new)
(a.out/'flutter-changes.json').write_text(json.dumps(changes,indent=2)+'\n');print(json.dumps(changes,indent=2))
