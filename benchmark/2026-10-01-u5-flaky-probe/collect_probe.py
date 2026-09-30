#!/usr/bin/env python3
"""Archive the actual bounded probes, without manufacturing sweep records."""
from pathlib import Path
import gzip,hashlib,json,shutil,sys
P=Path(__file__).resolve().parent
rows=[]
for run in sys.argv[1:]:
 for board in (P/'runs'/run).iterdir():
  if not board.is_dir():continue
  out=P/'evidence'/run/board.name;out.mkdir(parents=True,exist_ok=True)
  for name in ['facts.txt','plan.json','baseline.json','preflight.json','runtime-fingerprint.txt','boot-image-fingerprint.txt']:
   f=board/name
   if f.exists():shutil.copy2(f,out/name)
  for f in sorted(board.glob('*/record.json')):
   d=json.loads(f.read_text());dest=out/d['key'];dest.mkdir(exist_ok=True)
   shutil.copy2(f,dest/f.name)
   for name in ['processes-t5.txt','processes-t20.txt']:
    source=f.parent/name
    if source.exists():(dest/(name+'.gz')).write_bytes(gzip.compress(source.read_bytes(),mtime=0))
   shots=[]
   for shot in d.get('screenshots',[]):
    if not shot.get('captured'):continue
    image=Path(shot['path']);assert hashlib.sha256(image.read_bytes()).hexdigest()==shot['sha256']
    shutil.copy2(image,dest/image.name);shots.append(str((dest/image.name).relative_to(P)))
   rows.append({'run':run,'serial':board.name,'key':d['key'],'status':d['status'],'finished_at':d.get('finished_at'),'record_sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'screenshots':shots,'visual_verdict':'pending_outer_review'})
(P/'probe-index.json').write_text(json.dumps(rows,indent=2)+'\n')
print('archived records:',len(rows))
