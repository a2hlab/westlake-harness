#!/usr/bin/env python3
import json,subprocess,sys,time,gzip
from pathlib import Path
H=Path(__file__).resolve().parent;SERIAL='5ea34a4500000000000000001123012c'
keys=['localsend','fd-immich','fd-fluffychat','fd-kitchenowl','fd-libre','fd-saber','aegis','fd-catima']
for key in keys:
 print('START',key,time.time(),flush=True)
 with (H/(key+'.log')).open('w') as f:
  rc=subprocess.call([sys.executable,str(H/'run_batch.py'),'5ea','n5-'+key,'--keys',key],stdout=f,stderr=subprocess.STDOUT)
 print('END',key,'rc',rc,flush=True)
 recpath=H/'runs'/('n5-'+key)/SERIAL/key/'record.json'
 if recpath.exists():
  rec=json.loads(recpath.read_text());uid=rec.get('bms',{}).get('uid');pids=set(rec.get('observed_pids',[]))
  for shot in rec.get('screenshots',[]):pids.update(shot.get('foreground',{}).get('observed_pids',[]))
  duplicates=[]
  for line in (H/'maps-observations.jsonl').read_text().splitlines():
   obs=json.loads(line)
   raw=gzip.decompress((H/obs['file']).read_bytes()).decode(errors='replace')
   uid_pids={int(v[0]) for line in raw.split('MAPS_BEGIN:')[0].splitlines() if len(v:=line.split())>=4 and v[0].isdigit() and v[2].isdigit() and int(v[2])==uid}
   for p in obs['processes']:
    if p['pid'] in (pids|uid_pids) and p['duplicate']:duplicates.append(dict(observation=obs['file'],process=p))
  if duplicates and key not in ['aegis','fd-catima']:
   (H/'duplicate-failure.json').write_text(json.dumps(dict(key=key,rows=duplicates),indent=2)+'\n');print('STOP duplicate inode',key,flush=True);break
 if rc and (not recpath.exists() or not rec.get('screenshots')):print('STOP infrastructure/batch failure',key,flush=True);break
