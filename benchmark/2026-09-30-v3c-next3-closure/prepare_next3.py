#!/usr/bin/env python3
"""Update the two declared ANL aliases in one complete upgrade package."""
import hashlib,json,shutil,subprocess,sys
from pathlib import Path
R=Path(__file__).resolve().parent
repo=R.parents[1]
sys.path.insert(0,str(repo/'scripts/lab'))
from deploy_generation import load_package
base=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next2-audio-anl')
out=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-v3c-next3-audio-anl')
artifact=repo/'bms/src/.work/v3c-next3-native/anl-build/pass1/app-loader/libapp_native_loader.so'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old=load_package(base);new=json.loads(json.dumps(old));digest=sha(artifact)
if out.exists():raise RuntimeError('output already exists')
subprocess.run(['cp','-Rc',str(base),str(out)],check=True)
changed=[]
for member in new['files']:
 if member.endswith('/libapp_native_loader.so'):
  shutil.copyfile(artifact,out/member);new['files'][member]=digest;changed.append(member)
assert set(changed)=={'payload/route/libapp_native_loader.so','payload/android/lib64/libapp_native_loader.so'}
for target in new['live_hashes']:
 if target.endswith('/libapp_native_loader.so'):new['live_hashes'][target]=digest
(out/'package.json').write_text(json.dumps(new,indent=2)+'\n');load_package(out)
(R/'package-changes.json').write_text(json.dumps({'base':str(base),'out':str(out),'changed_members':changed,'anl_sha256':digest,'package_sha256':sha(out/'package.json')},indent=2)+'\n')
(R/'package.json').write_bytes((out/'package.json').read_bytes())
# Reject next2 against the complete generated OH set, rather than only NDK names.
c=json.loads((R/'closure.json').read_text())
def coverage(path):
 data=path.read_bytes();strings=[s.decode('ascii',errors='ignore') for s in data.split(b'\0')]
 shared=set()
 for s in strings:
  if 'libc++.so' in s and ':' in s:shared.update(s.split(':'))
 missing=sorted(set(c['shared_names'])-shared)
 roots=':'.join(c['dependency_roots'])
 return {'sha256':sha(path),'missing_names':missing,'roots_present':roots.encode() in data,'passed':not missing and roots.encode() in data}
control=coverage(base/'payload/route/libapp_native_loader.so');candidate=coverage(artifact)
assert candidate['passed'] and not control['passed']
(R/'coverage.json').write_text(json.dumps({'candidate':candidate,'next2_negative':control},indent=2)+'\n')
print(json.dumps({'anl':digest,'package':sha(out/'package.json'),'negative_missing_count':len(control['missing_names'])}))
