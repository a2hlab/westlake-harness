#!/usr/bin/env python3
"""Archive observed run data; never infer UI from liveness."""
import gzip,json,subprocess,sys,tarfile
from pathlib import Path
from compare_maps import collect
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
facts=[];index=[];saved_maps=set();ev=H/'evidence';ev.mkdir(exist_ok=True)
for run in sorted((H/'runs').iterdir()):
 for board in run.iterdir():
  if not board.is_dir() or not (board/'baseline.json').exists():continue
  sys.path.insert(0,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch'))
  import bms_batch
  bms_batch.write_facts(board)
  facts += ['== '+run.name+' ==',(board/'facts.txt').read_text().rstrip(),'']
  for app in sorted(board.iterdir()):
   if not app.is_dir() or not (app/'record.json').exists():continue
   d=json.loads((app/'record.json').read_text());target=ev/run.name/app.name;target.mkdir(parents=True,exist_ok=True)
   for n in ['record.json','processes-after.txt','processes-before.txt','diagnostics.json']:
    p=app/n
    if p.exists():(target/n).write_bytes(p.read_bytes())
   t20=next((s['path'] for s in d.get('screenshots',[]) if s.get('scheduled_seconds')==20 and s.get('captured')),None)
   phase='u5' if run.name.startswith('n7-u5') else 'n7';m=collect(run.name,app.name,phase);pids={s['pid'] for s in m.get('samples',[])}
   # Retain first, maximum-library, and last samples per PID.
   for pid in pids:
    samples=[s for s in m['samples'] if s['pid']==pid]
    chosen=[samples[0],max(samples,key=lambda s:sum(len(v) for v in s['libraries'].values())),samples[-1]]
    saved_maps.update(s['file'] for s in chosen)
   raw=(app/'hilog.txt').read_bytes() if (app/'hilog.txt').exists() else b''
   (target/'hilog.txt.gz').write_bytes(gzip.compress(raw,mtime=0))
   child=[];dumps=set()
   for line in raw.decode(errors='replace').splitlines():
    f=line.split()
    if len(f)>3 and f[2].isdigit():
     pid=int(f[2])
     if 'DfxFaultLogger: Pid:' in line and any(line.endswith('Pid:'+str(p)) for p in pids):dumps.add(pid)
     if pid in pids or pid in dumps:child.append(line)
   (target/'child-hilog.txt.gz').write_bytes(gzip.compress(('\n'.join(child)+'\n').encode(),mtime=0))
   fatal=[l for l in child if any(x in l for x in ['FATAL EXCEPTION','Fatal signal','Reason:Signal:','DFX_SignalHandler :: signo','UnsatisfiedLinkError:','Flutter private preload','[OH_EglHijack]','OH_EglHijack:','N7-EGL'])]
   (target/'wall-evidence.txt').write_text('\n'.join(fatal[:100])+'\n')
   index.append(dict(run=run.name,key=app.name,record=str((app/'record.json').relative_to(R)),t20=t20,pids=sorted(pids),maps_status=m['status'],status=d.get('status'),first_fatal_candidates=fatal[:6],visual_verdict='pending_external_review'))
(H/'facts-all.txt').write_text('\n'.join(facts));(H/'run-index.json').write_text(json.dumps(index,indent=2)+'\n')
with tarfile.open(H/'selected-maps.tar.gz','w:gz') as tar:
 for name in sorted(saved_maps):tar.add(H/name,arcname=name)
print('records',len(index),'selected maps',len(saved_maps))
