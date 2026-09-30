#!/usr/bin/env python3
"""Copy N5, replace the Flutter-only ABI, and rebind existing gate evidence."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,d): p.write_text(json.dumps(d,indent=2)+'\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('base',type=Path);p.add_argument('out',type=Path);a=p.parse_args()
 assert sha(a.base/'package.json')=='b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7'
 assert not a.out.exists()
 old=load_package(a.base);subprocess.run(['/bin/cp','-Rc',str(a.base),str(a.out)],check=True)
 manifest=json.loads((a.out/'package.json').read_text());rel='payload/android/lib64/westlake_flutter/libwestlake_native_abi.so'
 source=ROOT/'bms/src/.work/n6-native/abi/libwestlake_native_abi.so';digest=sha(source)
 dest=a.out/rel;dest.chmod(dest.stat().st_mode|0o200);dest.write_bytes(source.read_bytes());manifest['files'][rel]=digest
 live='/system/android/lib64/westlake_flutter/libwestlake_native_abi.so';assert live in manifest['live_hashes'];manifest['live_hashes'][live]=digest
 manifest['rollout_ready']=False;manifest['rollout_blocker']='N6 private EGL candidate; candidate-bound exceptions and device review required'
 write(a.out/'package.json',manifest);identity=sha(a.out/'package.json');validate_upgrade(old,load_package(a.out))
 checks=a.out/'native-checks'
 p=checks/'scan-manifest.json';d=json.loads(p.read_text())
 for profile in d['profiles']:
  profile['identity']['package']=a.out.name;profile['identity']['manifest_sha256']=identity
 write(p,d)
 p=checks/'native-gates.json';d=json.loads(p.read_text());d['package_manifest_sha256']=identity;d['initialization']['manifest']['sha256']=sha(checks/'scan-manifest.json');write(p,d)
 write(checks/'n6-source-binding.json',{'artifact':rel,'sha256':digest,'sources':{str(p.relative_to(ROOT)):sha(p) for p in sorted((HERE/'src').glob('*'))}})
 result={'base_manifest':sha(a.base/'package.json'),'manifest_sha256':identity,'package':a.out.name,'changes':[{'file':rel,'before':old['files'][rel],'after':digest}],'board_writes':False}
 write(HERE/'package.json',result);print(json.dumps(result,indent=2))
 subprocess.run([sys.executable,str(ROOT/'scripts/lab/check_frozen.py'),'--package',str(a.out)],check=True)
if __name__=='__main__': main()
