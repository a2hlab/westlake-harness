"""Five approved capture-only baseline keys, copied from the signed 01:31 Toutiao window."""
import argparse
import datetime
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
W=REPO.parent
MASTER=W/'westlake-harness'
TOOLS=W/'westlake-inputs/tools'
BOARD=MASTER/'.octos/boards/app-lighting.md'
ROWS={
 '5ea':('5ea34a4500000000000000001123012c',['cv2-com-frequent-habits','fd-im-vector-app']),
 '5cd':('5cd1e3dd00000000000000000923012c',['fd-plus','fd-libretube']),
 '61b':('61b0657200000000000000000324012c',['mcdonalds']),
}
SPEC=importlib.util.spec_from_file_location('approved_longwait',REPO/'benchmark/2026-10-02-toutiao-longwait-cxt0/window.py')
old=importlib.util.module_from_spec(SPEC);SPEC.loader.exec_module(old)
STOP=False

def stop(signum,frame):
 global STOP
 STOP=True

def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def note(text):old.note(text)

def run(short,root):
 serial,keys=ROWS[short];old.SERIAL=serial
 root.mkdir(parents=True,exist_ok=False)
 old.prelock(root)  # only reads: vmgr/orb/lock/HDC/bind/boot/settings
 subprocess.run(['bash',TOOLS/'board_note.sh','lock',BOARD,serial,'cx-t0',
                 '#90 U10.1T8 capture-only unbound baseline <=20min'],check=True)
 start=time.time();deadline=start+1200
 save(root/'window.json',{'started':datetime.datetime.now().astimezone().isoformat(),'started_epoch':start,
                         'deadline_epoch':deadline,'serial':serial,'keys':keys,'base':'U10.1T8',
                         'deployment':False,'replacement':False,'jit':False})
 for sig in (signal.SIGTERM,signal.SIGHUP):signal.signal(sig,stop)
 before=None;failure=None
 try:
  held=subprocess.run(['bash',TOOLS/'board_note.sh','held',serial],capture_output=True,text=True,check=True)
  assert held.stdout.startswith('cx-t0 '),'lock owner differs'
  (root/'held.txt').write_text(held.stdout)
  before=old.identity(root/'before318')
  note(f'1/3 {short} capture-only LOCK+318/双指纹PASS，U10.1T8不换件，keys={keys}，截止epoch={deadline}')
  for key in keys:
   if STOP or (root/'STOP').exists() or time.time()+600+180>=deadline:
    save(root/('unmeasured-'+key+'.json'),{'key':key,'status':'unknown','reason':'stop requested or reserve final readback'})
    continue
   out=root/key;out.mkdir()
   manifest=MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json'
   input_root=str(Path.home()/'a2hlab/app-inputs') # pinned Mac corpus, as prior U10.1T8/U12 records
   if key.startswith('cv2-'):
    manifest=W/'westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json'
    input_root=str(W/'westlake-inputs/corpus-v2/app-inputs')
   args=['python3',MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py',
         '--execute','--serial',serial,'--lane','cx-t0','--manifest',manifest,'--input-root',input_root,
         '--keys',key,'--reinstall','--wait','95','--hilog','95','--shots','20,45,90',
         '--hdc-cmd',str(TOOLS/'hdc_mac.sh'),'--lock-cmd','mac '+str(TOOLS/'board_note.sh'),
         '--out',out,'--run-id',root.parent.name+'-'+short+'-'+key,
         '--stop-new-keys-at',str(deadline-180)]
   save(out/'command.json',{'argv':list(map(str,args))})
   with (out/'batch.log').open('w') as log:
    p=old.vm(args,stdout=log,stderr=subprocess.STDOUT,check=False,timeout=600)
   records=list(out.glob('*/*/*/record.json'))
   assert len(records)==1,'exactly one wrapped capture expected'
   record=records[0];rec=json.loads(record.read_text())
   save(out/'exit.json',{'return_code':p.returncode,'status':rec.get('status')})
   assert p.returncode in (0,1) and rec.get('status') in ('captured','foreground_unconfirmed','app_failed'),'batch infrastructure failed'
   facts=subprocess.run([sys.executable,MASTER/'scripts/lab/run_facts.py',record.parent.parent],capture_output=True,text=True,check=True)
   (out/'facts-verbatim.txt').write_text(facts.stdout);print(facts.stdout,flush=True)
   note(f'2/3 {short} {key} capture-only收尾rc={p.returncode}，{out}/facts-verbatim.txt；t20/t45/t90交外环读，继续或收窗')
 except Exception as exc:
  failure=str(exc);save(root/'failure.json',{'error':failure});print('WINDOW ERROR',failure,flush=True)
 finally:
  # Capture-only: there is no deployment to rollback. A failed final readback retains lock.
  after=old.identity(root/'final318')
  if before is not None:
   assert after['fingerprints']==before['fingerprints'] and after['boot_id']==before['boot_id'],'base drift'
  save(root/'finish.json',{'passed':True,'deployed':False,'identity_assertions':318,
                          'fingerprints':after['fingerprints'],'error':failure,'elapsed_seconds':time.time()-start})
  subprocess.run(['bash',TOOLS/'board_note.sh','unlock',BOARD,serial,'cx-t0'],check=True)
  subprocess.run([sys.executable,REPO/'benchmark/2026-10-02-u12-final-assembly/window4/sample_infra.py',root/'infra-after.json'],check=True)
  note(f'3/3 {short} capture-only final318 diff/absent空、双指纹/boot_id不变，UNLOCK；{root}/finish.json；无部署无需回滚。')
 return int(failure is not None)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--board',choices=ROWS,required=True);p.add_argument('--root',type=Path,required=True)
 a=p.parse_args();raise SystemExit(run(a.board,a.root))
