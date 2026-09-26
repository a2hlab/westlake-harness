from boardjit50 import *
import gzip
out=ROOT/'evidence';out.mkdir(exist_ok=True)
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
