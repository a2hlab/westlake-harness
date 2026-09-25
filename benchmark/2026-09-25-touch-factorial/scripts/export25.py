"""Export only task evidence; keep the large prior-task cleanup archive in the VM."""
from board25 import *
import gzip,hashlib,shutil,tarfile
out=pathlib.Path(__file__).resolve().parents[1]/'evidence';out.mkdir(exist_ok=True)
records=[]
for p in sorted(R.rglob('*')):
 if not p.is_file():continue
 rel=p.relative_to(R)
 if p.name in {'old-logs.tar','launch-inputs.tar','host_spawn','touchfwd','source_app_namespace','request.bin','summary.json'}:continue
 if p.suffix not in {'.txt','.json','.jsonl','.log','.stderr','.sh','.tar'} and not p.name.startswith('cppcrash-'):continue
 raw=p.read_bytes();compress=p.suffix in {'.stderr','.log','.jsonl','.tar'} or (p.suffix=='.txt' and len(raw)>50000)
 dest=out/(str(rel)+('.gz' if compress else ''));dest.parent.mkdir(parents=True,exist_ok=True)
 dest.write_bytes(gzip.compress(raw,mtime=0) if compress else raw)
 assert (gzip.decompress(dest.read_bytes()) if compress else dest.read_bytes())==raw
 records.append({'file':str(dest.relative_to(out)),'raw_bytes':len(raw),'raw_sha256':hashlib.sha256(raw).hexdigest(),'stored_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'gzip':compress})
old=R/'old-logs.tar'
with tarfile.open(old) as t:members=[{'name':x.name,'bytes':x.size} for x in t]
(out/'old-archive.json').write_text(json.dumps({'location':str(old),'bytes':old.stat().st_size,'sha256':hashlib.sha256(old.read_bytes()).hexdigest(),'members':members},indent=2))
(out/'files.json').write_text(json.dumps(records,indent=2)+'\n')
print('Exported',len(records),'files',sum((out/x['file']).stat().st_size for x in records),'stored bytes')
