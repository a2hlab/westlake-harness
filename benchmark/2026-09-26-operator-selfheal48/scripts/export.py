from pathlib import Path
import hashlib,gzip,json
root=Path(__file__).resolve().parents[1];R=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/selfheal48';out=root/'evidence';out.mkdir(exist_ok=True);manifest=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R);parts=rel.parts
 if 'original' in parts or p.suffix in ('.tar','.art','.oat','.vdex','.jar','.so'):continue
 raw=p.read_bytes();packed=len(raw)>65536 and p.suffix not in ('.jpeg','.png');data=gzip.compress(raw,mtime=0) if packed else raw
 name=str(rel)+('.gz' if packed else '');q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 manifest.append(dict(path=name,source=str(p),bytes=len(data),sha256=hashlib.sha256(data).hexdigest(),raw_bytes=len(raw),raw_sha256=hashlib.sha256(raw).hexdigest(),gzip=packed))
(out/'manifest.json').write_text(json.dumps(manifest,indent=2));print('EXPORTED',len(manifest))
