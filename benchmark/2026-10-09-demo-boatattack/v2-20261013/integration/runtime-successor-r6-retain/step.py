"""Root local command spool; default preview. No HDC calls or arbitrary coordinates."""
import argparse,hashlib,json,os
from pathlib import Path
def build(record,action,disposition=None,write=False):
 raw=record.read_bytes();r=json.loads(raw)
 if r['status']!='WAITING_FOR_ROOT_STEP' or r['evidence_group']!='root-stepped-experiment':raise ValueError('runner not waiting for root step')
 if action not in ['left','right','accelerate','reset','finish']:raise ValueError('unknown action')
 if action=='finish' and disposition not in ['retain','rollback']:raise ValueError('finish disposition required')
 d=dict(approved_by='outer(codex)',boot_id=r['boot_id'],child=r['child'],action=action,record_sha256=hashlib.sha256(raw).hexdigest())
 if action=='finish':d['disposition']=disposition
 p=record.parent/'steps'/('step-%03d.json'%r['next_step'])
 if write:
  # Atomic publication, no overwriting an already consumed step.
  tmp=p.with_suffix('.tmp-'+str(os.getpid()))
  try:
   with tmp.open('x') as f:json.dump(d,f);f.write('\n')
   os.link(tmp,p)
  finally:
   if tmp.exists():tmp.unlink()
 print(json.dumps(dict(status='LOCAL_STEP_WRITTEN' if write else 'PREVIEW_ONLY',path=str(p),step=d,device_calls=0)))
 return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--record',type=Path,required=True);p.add_argument('--action',choices=['left','right','accelerate','reset','finish'],required=True);p.add_argument('--disposition',choices=['retain','rollback']);p.add_argument('--write',action='store_true');a=p.parse_args();build(a.record,a.action,a.disposition,a.write)
