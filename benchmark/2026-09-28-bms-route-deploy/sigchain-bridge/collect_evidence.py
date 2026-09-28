"""VM: curate existing logs without running board commands."""
from pathlib import Path
import json,hashlib,shutil,re
r=Path(__file__).resolve().parent;index=[]
for run,label in [('b6-musl-fixed-5ea','rejected'),('b6-musl-rollback-baseline-5ea','rollback')]:
 for app in ['wikipedia','helloworld','zigzag']:
  src=Path.home()/'a2hlab/board'/run/app
  if not src.exists():continue
  dest=r/'evidence'/label/app;dest.mkdir(parents=True,exist_ok=True)
  rec=json.loads((src/'record.json').read_text());uid=str(rec['bms']['uid'])
  for p in src.iterdir():
   if not p.is_file():continue
   index.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
   if p.name in ['record.json','final.jpeg','timeline.txt'] or p.name.startswith('child-proof-'):shutil.copyfile(p,dest/p.name)
   if p.name=='hilog.txt':
    lines=p.read_text(errors='replace').splitlines();relevant=[s for s in lines if 'WLCGATE:' in s or ('APPSPAWN' in s and 'exit with code:' in s)];(dest/'loader-hilog.txt').write_text('\n'.join(relevant)+'\n')
(r/'evidence-index.json').write_text(json.dumps(index,indent=2)+'\n')
print(len(index))
