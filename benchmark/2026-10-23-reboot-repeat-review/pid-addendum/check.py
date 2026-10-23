#!/usr/bin/env python3
"""Parse saved ordinary ps/WMS receipts only; never execute their argv."""
import argparse, hashlib, json, re
from pathlib import Path
P=Path(__file__).resolve().parent
ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=Path.home()/'.local/share/westlake');ap.add_argument('--capture',action='store_true');a=ap.parse_args()
roots={ 'T108':a.root/'spare-board-boot-entry-20261023','T109':a.root/'spare-board-reboot-repeat-20261023'}
def digest(b):return hashlib.sha256(b).hexdigest()
if a.capture:
 pins=[]
 for card,root in roots.items():
  paths=set(root.glob('raw/**/*.argv'))
  names=['raw/OLD_BOOT','raw/NEW_BOOT']
  for stem in ['01/reboot','05/click']+[f'05/{q}{t}{s}' for t in [10,30,60,90,120] for q,s in [('p',''),('s','_shot'),('s','_rs')]]:
   names += ['raw/'+stem+'.'+ext for ext in ['argv','start','end','rc','stdout','stderr']]
  names += [f'raw/05/s{t}.jpeg' for t in [10,30,60,90,120]]
  paths.update(root/n for n in names if (root/n).is_file())
  for f in sorted(paths):
   b=f.read_bytes();pins.append(dict(card=card,path=str(f.relative_to(root)),sha256=digest(b),bytes=len(b)))
 (P/'input-index.json').write_text(json.dumps(pins,indent=2)+'\n')
data={}
for row in json.loads((P/'input-index.json').read_text()):
 b=(roots[row['card']]/row['path']).read_bytes()
 if digest(b)!=row['sha256'] or len(b)!=row['bytes']:raise ValueError('Changed input: '+row['path'])
 data[row['card'],row['path']]=b

def txt(card,n):
 b=data.get((card,n));return None if b is None else b.decode(errors='replace').strip()
def rec(card,stem):
 d={e:txt(card,'raw/'+stem+'.'+e) for e in ['start','end','rc','stdout','stderr','argv']}
 if any(x is None for x in d.values()):return {'ref':'raw/'+stem,'status':'pending'}
 return dict(ref='raw/'+stem,status='complete',rc=int(d['rc']),start=float(d['start'].split()[0]),end=float(d['end'].split()[0]),stdout=d['stdout'])
result={'scope':'Sampled process presence only; no birth identity, continuous survival, exit cause or relaunch initiator established','runs':{},'visual_source':'Outer message: T109 s60 white; T108 existing outer/sentry: t30 white, t60 feed','pending':['T109 final record/facts and restore not reviewed in this addendum','Other T109 images require outer visual review','No prefix/state-event causal analysis performed']}
for card in roots:
 click=rec(card,'05/click');counts={'reboot':0,'ui_click':0}
 for (c,n),b in data.items():
  if c!=card or not n.endswith('.argv'):continue
  cmd=json.loads(b)
  if 'shell' not in cmd:continue
  if cmd[-1]=='reboot':counts['reboot']+=1
  if re.fullmatch(r'uitest uiInput click \d+ \d+',cmd[-1]):counts['ui_click']+=1
 run={'boot':txt(card,'raw/NEW_BOOT'),'recorded_commands':counts,'click':click,'samples':[]}
 for t in [10,30,60,90,120]:
  r=rec(card,f'05/p{t}');row={'label':f'p{t}','receipt':{k:v for k,v in r.items() if k!='stdout'}}
  if r['status']=='complete' and r['rc']==0:
   body=r['stdout'];procs=[]
   for ln,line in enumerate(body.splitlines(),1):
    m=re.fullmatch(r'\s*(\d+)\s+(\d+)\s+(\d+)\s+(.+)',line)
    if m and (m[4] in ['org.westlake.imehost','com.ss.android.article.news'] or m[4].startswith('appspawn-x ')):
     procs.append(dict(pid=int(m[1]),ppid=int(m[2]),uid=int(m[3]),name=m[4].split()[0],stdout_line=ln))
   row.update(processes=procs,child_rows=[x for x in procs if x['name']=='com.ss.android.article.news'],child_absence_scope='Not listed by this filtered ps sample; not a continuous exit observation',device_time_label=body.splitlines()[0],uptime_line=body.splitlines()[1],focus_window=re.findall(r'^Focus window: (\d+)$',body,re.M),relative_to_click_s=[round(r['start']-click['end'],6),round(r['end']-click['start'],6)])
  shot=rec(card,f'05/s{t}_shot');recv=rec(card,f'05/s{t}_rs');b=data.get((card,f'raw/05/s{t}.jpeg'))
  row['image']={'ref':f'raw/05/s{t}.jpeg','shot_rc':shot.get('rc'),'recv_rc':recv.get('rc'),'sha256':digest(b) if b else None,'visual':'outer_reported_white' if card=='T109' and t==60 else 'not_reviewed_here'}
  run['samples'].append(row)
 result['runs'][card]=run
result['finding']='T109 p30 child7011/PPID5201, p60 child9860/PPID5201; neither package child listed at p90/p120. One recorded UI click. No same-child-through-end or trigger attribution.'
print(json.dumps(result,indent=2))
