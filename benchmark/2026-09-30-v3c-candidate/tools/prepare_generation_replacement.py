#!/usr/bin/env python3
"""Create a separate, hashed package for deploy_generation.sh --replace TARGET."""
import argparse,json,shutil
from pathlib import Path
from deploy_generation import load_package,replacement_source,sha,save,validate_replacement

def prepare(package,target,replacement,expected,out,adding=False):
    old=load_package(package)
    if adding:
        if not target.startswith('/system/android/lib64/'):
            raise ValueError('addition target must be an Android native library')
        source='payload/android/lib64/'+Path(target).name
    else:
        source=replacement_source(old,target)
    if sha(replacement)!=expected: raise ValueError('replacement SHA differs from requested build: '+str(replacement))
    if out.exists(): raise ValueError('output package already exists: '+str(out))
    new=json.loads(json.dumps(old))
    new['files'][source]=expected;new['live_hashes'][target]=expected
    if target=='/system/android/lib64/liboh_adapter_bridge.so':new['bridge_sha256']=expected
    validate_replacement(old,new,target,adding=adding)
    shutil.copytree(package,out)
    shutil.copyfile(replacement,out/source)
    save(out/'package.json',new)
    load_package(out)
    return out

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('package',type=Path);p.add_argument('target');p.add_argument('replacement',type=Path)
    p.add_argument('--sha256',required=True);p.add_argument('--out',required=True,type=Path)
    p.add_argument('--add',action='store_true')
    a=p.parse_args();print(prepare(a.package.resolve(),a.target,a.replacement.resolve(),a.sha256,a.out.resolve(),adding=a.add))
if __name__=='__main__':main()
