#!/usr/bin/env python3
"""Assemble N7 without mutating U5/N5 or deploying it."""
import hashlib,json,subprocess,sys,shutil
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1]
sys.path.insert(0,str(R/'scripts/lab'))
from deploy_generation import load_package,validate_upgrade
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
base=R.parent/'westlake-generation-n4-order-216b68fb';template=R.parent/'westlake-generation-n5-6d001bb8'
out=R.parent/('westlake-generation-n7-'+sha(R/'bms/src/.work/n7-native/host/appspawn-x-1')[:8])
assert sha(base/'package.json')=='7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe'
assert not out.exists()
subprocess.run(['/bin/cp','-Rc',str(base),str(out)],check=True)
m=json.loads((out/'package.json').read_text());old=load_package(base);changes=[]
components={'appspawn-x':'host/appspawn-x-1','libapp_native_loader.so':'libapp_native_loader.so','libbionic_compat.so':'libbionic_compat.so'}
for rel,prev in list(m['files'].items()):
 n=Path(rel).name
 if n not in components:continue
 src=R/'bms/src/.work/n7-native'/components[n];p=out/rel;p.chmod(p.stat().st_mode|0o200);p.write_bytes(src.read_bytes());digest=sha(src);m['files'][rel]=digest
 for live,value in list(m['live_hashes'].items()):
  if value==prev and Path(live).name==n:m['live_hashes'][live]=digest
 changes.append(dict(file=rel,before=prev,after=digest))
rel='payload/android/lib64/westlake_flutter/libEGL.so';src=R/'bms/src/.work/n7-native/libEGL.so';shutil.copy2(src,out/rel);m['files'][rel]=sha(src);m['live_hashes']['/system/android/lib64/westlake_flutter/libEGL.so']=sha(src);changes.append(dict(file=rel,before=None,after=sha(src)))
# Reuse the verified r109c alias bytes, never patch the OH system zlib.
z=R.parent/'01.OH61AOSP16/real-work/.state/build-oh-component-hw248/m1-route-a-generation-20260825-r109c-zlib-global/route-a-generation/pass1/zlib/libz.so'
assert z.stat().st_size==1904
for rel in ['payload/android/lib64/libz.so','payload/android/lib64/westlake_native/libz.so']:
 shutil.copy2(z,out/rel);m['files'][rel]=sha(z);m['live_hashes']['/system/'+rel.removeprefix('payload/')]=sha(z);changes.append(dict(file=rel,before=None,after=sha(z)))
m['rollout_ready']=False;m['rollout_blocker']='N7 offline; unapproved N1/N2 findings and device binding evidence pending'
save(out/'package.json',m);identity=sha(out/'package.json');validate_upgrade(old,load_package(out))
# N5 carries the complete read-only system snapshot. Never modify it.
shutil.rmtree(out/'native-checks');subprocess.run(['/bin/cp','-Rc',str(template/'native-checks'),str(out/'native-checks')],check=True)
c=out/'native-checks';sm=json.loads((c/'scan-manifest.json').read_text())
for name,src in [('n4-host.c',H/'src/host.c'),('flutter_domain.inc',H/'flutter/flutter_domain.inc'),('n7-egl.c',H/'src/flutter_egl.c'),('n7-dlopen.cpp',H/'src/dlopen_ext_compat.cpp')]:
 shutil.copy2(src,c/name)
 if name!='flutter_domain.inc':sm['sources'][name]=dict(path=name,sha256=sha(src),origin=str(src.relative_to(R)),source_sha256=sha(src),first_line=1)
for name,source,artifact in [('egl-facade','n7-egl.c',rel),('bionic','n7-dlopen.cpp','payload/route/libbionic_compat.so')]:
 sm['profiles'].append(dict(name=name,rule='namespace',source=source,identity=dict(artifact=artifact)))
for p in sm['profiles']:p['identity'].update(package=out.name,manifest_sha256=identity,artifact_sha256=m['files'][p['identity']['artifact']])
save(c/'scan-manifest.json',sm)
ns=json.loads((c/'namespace-manifest.json').read_text());ns['config_sources'][0]['sha256']=sha(c/'flutter_domain.inc');save(c/'namespace-manifest.json',ns)
g=json.loads((c/'native-gates.json').read_text());g['package_manifest_sha256']=identity;g['initialization']['manifest']['sha256']=sha(c/'scan-manifest.json');g['namespaces']['manifest']['sha256']=sha(c/'namespace-manifest.json');g['namespaces']['owner_artifact']['sha256']=m['files']['payload/route/libapp_native_loader.so'];save(c/'native-gates.json',g)
sources={str(p.relative_to(R)):sha(p) for p in sorted(H.rglob('*')) if p.is_file() and p.suffix in ['.c','.cpp','.h','.inc','.map','.sh','.py'] and '__pycache__' not in str(p)}
save(c/'n7-source-binding.json',dict(sources=sources,changes=changes))
save(H/'package.json',dict(package=out.name,manifest_sha256=identity,base=base.name,changes=changes,source_binding_sha256=sha(c/'n7-source-binding.json'),board_writes=False));print(out)
subprocess.run([sys.executable,str(R/'scripts/lab/check_frozen.py'),'--package',str(out)],check=True)
