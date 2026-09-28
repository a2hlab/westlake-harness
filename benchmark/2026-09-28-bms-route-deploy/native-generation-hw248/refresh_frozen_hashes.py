"""Record authorized hw248 checksum drift and pin actual local input bytes."""
from pathlib import Path
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[3]
GEN=ROOT/'bms/src/.work/product-tls-generation'
original=GEN/'frozen.hw248-original.sha256'
if not original.exists():shutil.copy2(GEN/'frozen.sha256',original)
changes=[];lines=[]
for line in original.read_text().splitlines():
 expected,name=line.split(maxsplit=1);name=name.lstrip('*')
 p=GEN/'frozen'/name
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 actual=h.hexdigest()
 if actual!=expected:changes.append({'path':name,'declared_sha256':expected,'actual_sha256':actual})
 lines.append(actual+'  '+name)
(GEN/'frozen.sha256').write_text('\n'.join(lines)+'\n')
(Path(__file__).resolve().parent/'frozen-payload-drift.json').write_text(json.dumps(changes,indent=2)+'\n')
print('frozen entries',len(lines),'drift',len(changes))
