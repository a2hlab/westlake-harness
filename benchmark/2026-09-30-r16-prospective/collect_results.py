#!/usr/bin/env python3
"""Gate on 66 completed records; never infer screenshot content from processes."""
import argparse,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
DEFAULT=Path('/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-r16-sweep/runs')
PARTS=('r16full-A-5cd','r16full-B-61b')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text())
def verify():
 f=read(HERE/'freeze.json')
 for x in f['outputs']:
  if sha(HERE/x['path'])!=x['sha256']:raise ValueError('Frozen output changed: '+x['path'])
 return f
def status(root):
 groups=[]
 for part in PARTS:
  plans=list((root/part).rglob('plan.json')) if (root/part).exists() else []
  if len(plans)!=1:
   groups.append({'part':part,'planned':0,'finished':0,'ready':False,'reason':'missing-or-ambiguous-plan'});continue
  plan=read(plans[0]);records=[];finished=0
  for app in plan['apps']:
   p=plans[0].parent/app['key']/'record.json'
   try:r=read(p)
   except (ValueError,OSError):r={}
   finished+=bool(r.get('finished_at'));records.append((app,p,r))
  groups.append({'part':part,'plan':str(plans[0]),'planned':len(records),'finished':finished,'ready':len(records)==33 and finished==33,'records':records})
 return groups
def collect(root,out):
 freeze=verify();groups=status(root)
 summary=[{k:v for k,v in g.items() if k!='records'} for g in groups]
 if not all(g['ready'] for g in groups):
  print(json.dumps({'complete':False,'groups':summary},ensure_ascii=False));return False
 records=[x for g in groups for x in g['records']]
 keys=[a['key'] for a,_,_ in records]
 if len(keys)!=66 or len(set(keys))!=66:raise ValueError('Need 66 distinct keys across A/B')
 predictions={r['app']:r for r in read(HERE/'predictions.json')}
 if set(keys)!=set(predictions):raise ValueError('Cohort keys differ from frozen forecast')
 out.mkdir(parents=True,exist_ok=True);observations={};sources=[]
 epoch=datetime.datetime.fromisoformat(freeze['frozen_at']).timestamp()
 for app,path,record in records:
  key=app['key'];base=path.parent;copied=out/'records'/key;copied.mkdir(parents=True,exist_ok=True)
  (copied/'record.json').write_bytes(path.read_bytes())
  process_rows={};uid=record.get('bms',{}).get('uid')
  for moment in ['t5','t10','t20']:
   p=base/f'processes-{moment}.txt'
   if not p.exists():process_rows[moment]=None;continue
   text=p.read_text();(copied/p.name).write_text(text);rows=[]
   for n,line in enumerate(text.splitlines(),1):
    cols=line.split()
    if len(cols)>=4 and cols[0].isdigit() and cols[2].isdigit() and uid is not None and int(cols[2])==int(uid):
     rows.append({'line':n,'pid':int(cols[0]),'ppid':int(cols[1]),'uid':int(cols[2]),'name':' '.join(cols[3:])})
   process_rows[moment]=rows
  screenshots=[{'path':s.get('path'),'sha256':s.get('sha256'),'captured':s.get('captured'),'scheduled_seconds':s.get('scheduled_seconds'),'automatic_focus_accepted':s.get('accepted'),'visual_verdict':'unknown'} for s in record.get('screenshots',[])]
  observations[key]={'apk_sha256':record.get('apk_sha256'),'complete':bool(record.get('finished_at')),'clicked_at':record.get('clicked_at'),'serial':record.get('serial'),'boot_id':record.get('boot_id'),'profile':'unknown','visual':'unknown','first_wall':'unknown','reviewer':None,'visual_evidence':[],'first_wall_evidence':[],'screenshots':screenshots,'captured':sum(s['captured'] is True for s in screenshots),'target_uid_processes':process_rows,'record_path':str(path),'record_sha256':sha(path),'strict_pre_click':isinstance(record.get('clicked_at'),(float,int)) and record['clicked_at']>epoch}
  sources.append({'path':str(path),'sha256':sha(path),'diagnostics':record.get('diagnostics',{})})
 def write(name,d): (out/name).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
 write('observations-pending.json',observations);write('record-inputs.json',sources)
 write('collection.json',{'collected_at':datetime.datetime.now().astimezone().isoformat(),'full_batch_complete':True,'groups':summary,'keys':len(keys),'captured':sum(r['captured'] for r in observations.values()),'strict_pre_click':sum(r['strict_pre_click'] for r in observations.values()),'pending_visual_reviews':66,'status':'awaiting-independent-screenshot-and-first-wall-adjudication'})
 print(json.dumps(read(out/'collection.json'),ensure_ascii=False));return True
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=DEFAULT);p.add_argument('--out',type=Path,default=HERE/'observed');p.add_argument('--status',action='store_true');a=p.parse_args()
 if a.status:print(json.dumps([{k:v for k,v in g.items() if k!='records'} for g in status(a.root)],ensure_ascii=False))
 else:collect(a.root,a.out)
