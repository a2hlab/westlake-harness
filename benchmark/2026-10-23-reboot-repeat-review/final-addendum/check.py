#!/usr/bin/env python3
"""Offline closure/facts/event extraction; never executes captured argv."""
import argparse,hashlib,json,re,subprocess,sys
from pathlib import Path
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--root',type=Path,default=Path.home()/'.local/share/westlake/spare-board-reboot-repeat-20261023');p.add_argument('--main',type=Path,required=True);p.add_argument('--video',type=Path,required=True);p.add_argument('--capture',action='store_true');a=p.parse_args()
roots={'RAW':a.root,'MAIN':a.main,'PUBLIC':a.video/'benchmark/2026-10-23-spare-board-reboot-repeat'}
def sha(b):return hashlib.sha256(b).hexdigest()
if a.capture:
 fs=[('RAW',f) for f in sorted((a.root/'raw/07').iterdir()) if f.is_file()]
 fs += [('RAW',f) for f in sorted((a.root/'raw/06').glob('guardian.*'))]
 fs += [('RAW',f) for f in sorted((a.root/'run').rglob('*')) if f.is_file()]
 fs += [('RAW',a.root/n) for n in ['raw/LOCK_EPOCH','raw/NEW_BOOT','raw/03/pw.stdout']]
 for t in [10,30,60,90,120]:
  fs += [('RAW',a.root/f'raw/05/s{t}{s}') for s in ['.jpeg','_shot.rc','_rs.rc']]
 fs += [('MAIN',a.main/'scripts/lab/run_facts.py'),('PUBLIC',roots['PUBLIC']/'results.json')]
 pins=[dict(root=k,path=str(f.relative_to(roots[k])),sha256=sha(f.read_bytes()),bytes=f.stat().st_size) for k,f in fs]
 (P/'input-index.json').write_text(json.dumps(pins,indent=2)+'\n')
data={}
for pin in json.loads((P/'input-index.json').read_text()):
 b=(roots[pin['root']]/pin['path']).read_bytes()
 if sha(b)!=pin['sha256'] or len(b)!=pin['bytes']:raise ValueError('Changed input '+pin['path'])
 data[pin['root'],pin['path']]=b

def txt(n):return data['RAW',n].decode().strip()
events=[]
for line,body in enumerate(txt('raw/06/guardian.stdout').splitlines(),1):
 m=re.match(r'^(\d+) boot=(\S+) seq=(\d+) child=(\S+) child_birth=(\S+) parent=(\S+) parent_birth=(\S+) reason=(.*)$',body)
 if m:events.append(dict(stdout_line=line,time_value=int(m[1]),boot=m[2],seq=int(m[3]),child=m[4],child_birth=m[5],parent=m[6],parent_birth=m[7],reason_raw=m[8]))
assert int(txt('raw/06/guardian.rc'))==0
assert all(e['boot']==txt('raw/NEW_BOOT') for e in events)
record=json.loads(txt('run/t109-5cd/record.json'))
for s in record['screenshots']:
 t=int(s['label'][1:]);b=data['RAW',f'raw/05/s{t}.jpeg']
 assert s['captured'] and sha(b)==s['sha256'] and len(b)==s['bytes']
 assert txt(f'raw/05/s{t}_shot.rc')=='0' and txt(f'raw/05/s{t}_rs.rc')=='0'
r=subprocess.run([sys.executable,str(a.main/'scripts/lab/run_facts.py'),str(a.root/'run')],capture_output=True,text=True)
assert r.returncode==0 and r.stdout.strip()==txt('run/facts.txt')
restore={}
for stem in ['pr','po','pw','tmp']:
 restore[stem]={e:txt(f'raw/07/{stem}.{e}') for e in ['start','end','rc','stdout']}
 assert restore[stem]['rc']=='0'
public=json.loads(data['PUBLIC','results.json'])
lock=int(txt('raw/LOCK_EPOCH'));unlock=txt('raw/07/UNLOCK_T')
from datetime import datetime
start_label=datetime.fromtimestamp(lock).strftime('%H:%M:%S')
def secs(t):
 h,m,s=map(int,t.split(':'));return h*3600+m*60+s
out=dict(verdict='FINAL_RECEIPTS_REVIEWED_NOT_FEED_SUCCESS',facts_equal=True,facts_verbatim=r.stdout.splitlines(),record_images_verified=len(record['screenshots']),boot=txt('raw/NEW_BOOT'),guardian_receipt='raw/06/guardian.stdout',guardian_state=txt('raw/06/guardian.stdout').split('---STATE\n')[1].splitlines()[0],guardian_events=events,event_time_scope='Original leading event values retained; source/config not read, no cross-clock conversion or causal inference.',snapshot_error_events=[e for e in events if 'snapshot_error_rc=126' in e['reason_raw']],restore=restore,preimage_power=txt('raw/03/pw.stdout'),lock_epoch=lock,unlock_label=unlock,label_elapsed_seconds=(secs(unlock)-secs(start_label))%86400,held_after_rc_author_report=public['lock']['held_after_rc'],held_after_independent_rc='unknown: separate rc absent; empty raw/07/held.out not sufficient',visual_author_report=public['samples'],limitations=['Public author reports white through t120; visual acceptance remains outer responsibility.','Timeout values restored to 10000/10000; AWAKE is not identical to preimage SLEEP.','tmp rc0 plus empty output only establishes no matching lines in the captured compound command.','seq3 child12688 is an event-log claim, not observed by the p30/p60/p90/p120 process samples.','No cause, restart initiator, API-log analysis, device call, or stopped source inspection.'],author_commit=None)
print(json.dumps(out,indent=2))
