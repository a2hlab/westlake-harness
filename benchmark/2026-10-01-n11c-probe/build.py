"""Offline child-only rebuild using the exact N10b recipe and object inputs."""
import hashlib,json,os,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=Path(os.environ.get('WORKSPACES',R.parent))
old=R/'benchmark/2026-10-01-n11b-early-owner'
receipt=json.loads((old/'build-receipt.json').read_text())['candidate']
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
# Find the recorded workspace prefix by its stable checkout name, not its user.
first=receipt['commands'][0][0];recorded_root=first.split('/westlake-harness-bms-deploy/')[0]
commands=[[arg.replace(recorded_root,str(W)) for arg in cmd] for cmd in receipt['commands']]
cc,ld=commands;seed=Path(ld[ld.index('-o')+1]).parent
for name,digest in receipt['objects'].items():assert sha(seed/name)==digest,name
out=Path(os.environ.get('N11C_BUILD_OUT',W/'westlake-n11c-probe-build'))
assert not out.exists();out.mkdir()
env=os.environ.copy();env['LD_LIBRARY_PATH']=str(W/'westlake-harness-bms-deploy/bms/src/.work/b68-generation/.work/product-tls-generation/frozen/toolchain/runtime')
records={}
for name in ['baseline','candidate','repeat']:
 d=out/name;d.mkdir()
 for p in seed.glob('*.o'):shutil.copy2(p,d/p.name)
 c=list(cc);c[c.index('-c')+1]=str(old/'src/sealed_child_provider_loader.c') if name=='baseline' else str(H/'src/sealed_child_provider_loader.c');c[c.index('-o')+1]=str(d/'sealed_child_provider_loader.o')
 link=[str(d/Path(x).name) if x.endswith('.o') and Path(x).parent==seed else x for x in ld];link[link.index('-o')+1]=str(d/'libwestlake_android_child.z.so')
 with (d/'build.log').open('w') as f:
  for cmd in [c,link]:subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,check=True)
 records[name]={'sha256':sha(d/'libwestlake_android_child.z.so'),'source_sha256':sha(Path(c[c.index('-c')+1])),'commands':[[arg.replace(str(W),'$WORKSPACES') for arg in cmd] for cmd in [c,link]],'objects':{p.name:sha(p) for p in d.glob('*.o')}}
 if name=='baseline':assert records[name]['sha256']==receipt['sha256'],'N11b baseline not reproduced'
 if name=='repeat':assert records[name]['sha256']==records['candidate']['sha256'],'repeat mismatch'
 (H/'build-receipt.json').write_text(json.dumps(records,indent=2)+'\n');print(name,records[name]['sha256'],flush=True)
