#!/usr/bin/env python3
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
r=Path(__file__).resolve().parent;repo=r.parents[1];sys.path.insert(0,str(repo/'scripts/lab'))
from deploy_generation import load_package
base=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-candidate');out=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next4-audio-anl');w=repo/'bms/src/.work/v3c-next4-native'
artifacts={'appspawn-x':w/'host/appspawn-x-1','libapp_native_loader.so':w/'anl-build/pass1/app-loader/libapp_native_loader.so','liboh_android_runtime.so':w/'runtime-out/liboh_android_runtime.so'}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=json.loads(json.dumps(load_package(base)));assert not out.exists();subprocess.run(['cp','-Rc',str(base),str(out)],check=True)
changes=[]
for member in d['files']:
 name=Path(member).name
 if name in artifacts:
  shutil.copyfile(artifacts[name],out/member);d['files'][member]=sha(artifacts[name]);changes.append(member)
for target in d['live_hashes']:
 name=Path(target).name
 if name in artifacts:d['live_hashes'][target]=sha(artifacts[name])
assert len(changes)==4,changes
d['variant']='v3c-next4-direct-oh-owner';d['manifest_route']='v3c plus direct OH owner host/ANL and AudioSystem.newAudioSessionId; device pending'
(out/'package.json').write_text(json.dumps(d,indent=2)+'\n');load_package(out)
(r/'package.json').write_bytes((out/'package.json').read_bytes());(r/'package-changes.json').write_text(json.dumps({'base':str(base),'out':str(out),'changed_members':changes,'sha256':{k:sha(v) for k,v in artifacts.items()},'package_sha256':sha(out/'package.json')},indent=2)+'\n')
print(sha(out/'package.json'))
