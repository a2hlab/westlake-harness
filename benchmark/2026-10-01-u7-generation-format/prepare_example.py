"""Assemble an offline U7 format example, not an accepted generation."""
import hashlib,json,shutil,subprocess
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
out=W/'westlake-generation-u7-format-example-u5';assert not out.exists();out.mkdir()
subprocess.run(['/bin/cp','-Rc',str(W/'westlake-generation-n4-order-216b68fb'),str(out/'native')],check=True)
(out/'boot/arm64').mkdir(parents=True);(out/'framework').mkdir();(out/'reference').mkdir()
def row(src,relative,target=None):
 dest=out/relative;shutil.copyfile(src,dest)
 d=dict(source=relative,sha256=sha(dest))
 if target:d['target']=target
 return d
members=[row(p,'boot/arm64/'+p.name,'/system/android/framework/arm64/'+p.name) for p in sorted((W/'_hw248-t7d/arm64').iterdir()) if p.suffix in ['.art','.oat','.vdex']]
assert len(members)==27
members.append(row(W/'_hw248-t7d/adapter-mainline-stubs.jar','framework/adapter-mainline-stubs.jar','/system/android/framework/adapter-mainline-stubs.jar'))
runtime=row(W/'_u6-stage/oh-adapter-runtime.jar','framework/oh-adapter-runtime.jar','/system/android/framework/oh-adapter-runtime.jar')
ref=R/'benchmark/2026-10-01-n7-window/evidence/n7-u5-baseline'
refs={k:row(ref/(name+'-fingerprint.txt'),'reference/'+name+'.txt') for k,name in [('runtime','runtime'),('boot','boot-image')]}
d=dict(schema='westlake-generation-bundle/v1',native=dict(directory='native',manifest=dict(source='native/package.json',sha256=sha(out/'native/package.json'))),boot_group=dict(id='boot-image-and-stubs',members=members),runtime_jar=runtime,reference=refs,rollout_ready=False,paired_build_receipt=None)
(out/'bundle.json').write_text(json.dumps(d,indent=2)+'\n')
(H/'example-identity.json').write_text(json.dumps(dict(path=out.name,bundle_sha256=sha(out/'bundle.json'),native_manifest=d['native']['manifest']['sha256'],stubs_sha256=members[-1]['sha256'],runtime_sha256=runtime['sha256'],images=27,board_writes=False),indent=2)+'\n');print(out)
