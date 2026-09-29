#!/usr/bin/env python3
"""Preserve the actual V1 cohort; tracked V2 loader is not this build input."""
import difflib,hashlib,json,shlex,shutil,tarfile
from pathlib import Path
E=Path(__file__).resolve().parent;R=E.parents[1];W=R/'bms/src/.work/b68-generation';OLD=W.parent/'b67-generation'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
S=E/'source';S.mkdir(exist_ok=True)
paths=['adapter/framework/appspawn-x/src/adapter_bridge_identity.cpp']
P='adapter/framework/appspawn-x/security_specialization/stock_child_plugin/'
paths += [P+'src/'+n for n in ['westlake_stock_host_main.c','westlake_android_child_plugin.c','sealed_child_provider_loader.c']]
paths += [P+'verify_target_artifacts.py','adapter/build/inner/compile_oh_adapter_bridge_arm64.sh','adapter/build/inner/bridge_manifest_inputs.sh']
paths += [str(p.relative_to(W)) for p in W.glob('*.sh')]
rows=[]
for name in paths:
 p=W/name;q=OLD/name;t=S/name;t.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,t)
 row={'path':name,'sha256':sha(p)}
 if q.exists():
  row['before_sha256']=sha(q)
  diff=''.join(difflib.unified_diff(q.read_text().splitlines(True),p.read_text().splitlines(True),fromfile='b67/'+name,tofile='b68/'+name))
  if diff:(S/(name+'.patch')).write_text(diff)
 rows.append(row)
# Full actual build tree plus all external bridge compiler dependencies.
inputs=set()
for dep in (W/'bridge-v3-objects').glob('*.d'):
 for name in shlex.split(dep.read_text().replace('\\\n',' ').split(':',1)[1]):
  p=Path(name)
  if p.is_file():inputs.add(p.resolve())
for p in [W.parent/'b6-art14-recovery/build/cxx-sdk15',W.parent/'b6-art14-recovery/build/sdk15-declarations.h']:
 inputs.add(p.resolve())
external=sorted(p for p in inputs if not p.is_relative_to(W))
root=Path('/Users/zhaoyue/orca/workspaces/westlake-b9-v3-source-74d1d6d4');root.mkdir(exist_ok=True)
archive=root/'build-inputs.tar.gz'
with tarfile.open(archive,'w:gz',compresslevel=1) as tar:
 tar.add(W,arcname=str(W).lstrip('/'),recursive=True)
 for p in external:tar.add(p,arcname=str(p).lstrip('/'),recursive=False)
# Toolchain paths are content hashed, including the compiler symlink target.
compiler=W/'.work/product-tls-generation/frozen/toolchain/bin/clang-15'
meta={'source_tree':str(W),'base_tree':str(OLD),'changed_or_recipe_files':rows,'bridge_dependency_files':len(inputs),'external_dependencies':[{'path':str(p),'sha256':sha(p)} for p in external], 'toolchain':{'clang15':{'path':str(compiler),'sha256':sha(compiler)}},'archive':{'path':str(archive),'sha256':sha(archive),'bytes':archive.stat().st_size},'remote_directory':'/home/alvin/westlake-oh6.1-b9-v3-74d1d6d4-source','remote_copied':False}
(E/'source-preservation.json').write_text(json.dumps(meta,indent=2)+'\n')
print(json.dumps(meta['archive']),flush=True)
