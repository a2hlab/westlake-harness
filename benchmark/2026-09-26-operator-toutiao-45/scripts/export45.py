from board45 import *
import gzip
root=pathlib.Path(__file__).resolve().parents[1];out=root/'evidence';out.mkdir(exist_ok=True);manifest=[]
for p in sorted(R.rglob('*')):
 if not p.is_file() or 'overlay' in p.parts or p.suffix not in ('.json','.jsonl','.txt','.log','.sh','.jpeg','.stderr'):continue
 raw=p.read_bytes();packed=len(raw)>65536 and p.suffix!='.jpeg';data=gzip.compress(raw,mtime=0) if packed else raw
 name=str(p.relative_to(R))+('.gz' if packed else '');q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 manifest.append({'path':name,'source':str(p),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'raw_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'gzip':packed})
wanted={entry['path'] for entry in manifest}|{'manifest.json'}
for old in out.rglob('*'):
 if old.is_file() and str(old.relative_to(out)) not in wanted:old.unlink()
(out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('EXPORTED',len(manifest))
