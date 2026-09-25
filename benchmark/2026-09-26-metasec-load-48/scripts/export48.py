from board48 import *
import gzip,shutil
out=ROOT/'evidence';out.mkdir(exist_ok=True)
# Keep build commands/results and the actual patch, without committing ELF payloads.
build=pathlib.Path.home()/'a2hlab/ws/out-operator48';b=R/'a1-build';b.mkdir(exist_ok=True)
for name in ('commands.json','build.log','undefined-added.txt','result.json'):
 if (build/name).exists():shutil.copyfile(build/name,b/name)
source=pathlib.Path.home()/'a2hlab/ws/art-build-operator48'
if source.exists():
 (b/'source.diff.txt').write_text(subprocess.check_output(['git','-C',str(source),'diff','9acbaec','HEAD'],text=True))
 (b/'source-commit.txt').write_text(subprocess.check_output(['git','-C',str(source),'log','-3','--oneline'],text=True))
manifest=[]
for p in sorted(R.rglob('*')):
 if not p.is_file() or p.suffix not in ('.json','.jsonl','.txt','.log','.stderr','.sh','.jpeg'):continue
 raw=p.read_bytes();packed=len(raw)>65536 and p.suffix!='.jpeg'
 data=gzip.compress(raw,mtime=0) if packed else raw
 name=str(p.relative_to(R))+('.gz' if packed else '')
 q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 manifest.append(dict(path=name,source=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),gzip=packed))
expected={e['path'] for e in manifest}|{'manifest.json'}
for p in out.rglob('*'):
 if p.is_file() and str(p.relative_to(out)) not in expected:p.unlink()
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('EXPORTED',len(manifest))
