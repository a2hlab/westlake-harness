"""VM: preserve raw evidence with deterministic gzip and source hashes."""
from board34 import *
import gzip,hashlib
root=pathlib.Path(__file__).resolve().parents[1];out=root/'evidence'
manifest=json.loads((out/'manifest.json').read_text())
entries={e['path']:e for e in manifest}
def save(p,name):
 raw=p.read_bytes();packed=len(raw)>65536 and p.suffix not in ('.jpeg','.png')
 data=gzip.compress(raw,mtime=0) if packed else raw
 name+= '.gz' if packed else ''
 q=out/name;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(data)
 entries[name]={'path':name,'source':str(p),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'raw_sha256':hashlib.sha256(raw).hexdigest(),'raw_bytes':len(raw),'gzip':packed}
for name in sys.argv[1:]:
 for p in sorted((R/name).iterdir()):
  if p.is_file() and (p.suffix in ('.json','.jsonl','.log','.txt','.jpeg','.stderr','.sh') or p.name=='child.stderr'):
   save(p,name+'/'+p.name)
for name in ('framework-candidate',):
 for p in sorted((R/name).iterdir()):
  if p.is_file() and p.suffix in ('.json','.log'):save(p,name+'/'+p.name)
build=pathlib.Path.home()/'a2hlab/ws/out-ability38'
for module in ('appvis','native-policy','inputtrace','native-trace','framework-trace','native-stack'):
 for p in sorted((build/module).iterdir()):
  if p.is_file() and p.suffix in ('.json','.log'):save(p,'build/'+module+'/'+p.name)
for group in ('c1','c2','c3','c4'):
 for p in sorted((root/'android-reference'/group).iterdir()):
  if p.is_file():save(p,'android-reference/'+group+'/'+p.name)
(out/'manifest.json').write_text(json.dumps(list(sorted(entries.values(),key=lambda e:e['path'])),indent=2)+'\n')
print('EXPORTED',len(entries))
