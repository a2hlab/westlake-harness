"""Offline N8: remove only N7's root zlib alias; preserve all retained bytes."""
import hashlib,json,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
base=R.parent/'westlake-generation-n7-fa9ec3c6';out=R.parent/'westlake-generation-n8-private-zlib'
assert sha(base/'package.json')=='a77c7c6cfdc1c0f78a9f32dad2c184dabe049afedc9674774bd578fab1ab67ff'
assert not out.exists();subprocess.run(['/bin/cp','-Rc',str(base),str(out)],check=True)
m=json.loads((out/'package.json').read_text());remove='payload/android/lib64/libz.so'
(out/remove).unlink();del m['files'][remove];del m['live_hashes']['/system/android/lib64/libz.so']
m.update(rollout_ready=False,rollout_blocker='N8 offline; fresh exceptions and board acceptance pending')
save(out/'package.json',m);identity=sha(out/'package.json');c=out/'native-checks';sm=json.loads((c/'scan-manifest.json').read_text())
# Correct N7's profile metadata: its prepare.py reused the zlib loop variable
# when naming the EGL artifact. This changes no binary or source payload.
corrections=[]
for p in sm['profiles']:
 if p['name']=='egl-facade':
  corrections.append(dict(profile=p['name'],before=p['identity']['artifact'],after='payload/android/lib64/westlake_flutter/libEGL.so'))
  p['identity']['artifact']='payload/android/lib64/westlake_flutter/libEGL.so'
 p['identity'].update(package=out.name,manifest_sha256=identity,artifact_sha256=m['files'][p['identity']['artifact']])
save(c/'scan-manifest.json',sm)
g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=identity;g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');save(c/'native-gates.json',g)
save(c/'n8-source-binding.json',dict(parent_manifest=sha(base/'package.json'),removed=[remove],retained_payloads='byte identical to N7',metadata_corrections=corrections,prepare_source_sha256=sha(Path(__file__))))
load_package(out);validate_upgrade(load_package(R.parent/'westlake-generation-n4-order-216b68fb'),load_package(out))
save(H/'package.json',dict(package=out.name,manifest_sha256=identity,parent_manifest=sha(base/'package.json'),removed=[remove],metadata_corrections=corrections,board_writes=False))
print(out,identity)
