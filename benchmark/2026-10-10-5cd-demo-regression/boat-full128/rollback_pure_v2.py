#!/usr/bin/env python3
"""Authorized rollback only: preserve Boat sources, reboot once, verify pure v2 and HW."""
import importlib.util,json,os,re,shutil,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent; WS=HERE.parents[3]; M=WS/'westlake-harness'
SN='5cd1e3dd00000000000000000923012c'; OLD='3c0a3eba-534f-42d2-972c-bf8b925bacb4'
def main():
 if sys.argv[1:]!=['--execute']:raise SystemExit('explicit approved rollback required')
 out=HERE/'rollback-pure-v2';out.mkdir(exist_ok=False)
 spec=importlib.util.spec_from_file_location('safe',HERE/'safe_bare_prepare.py');safe=importlib.util.module_from_spec(spec);spec.loader.exec_module(safe);safe.OUT=out;sh=safe.Shell();hdc=safe.HDC
 result={'serial':SN,'reboots':0,'installer_called':False,'lock_retained':True}
 def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def run(name,args,timeout=240,check=True):
  with (out/(name+'.log')).open('wb') as f:r=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  if check and r.returncode:raise RuntimeError(name+' exit '+str(r.returncode))
  return r.returncode
 try:
  assert sh.read('boot-before','cat /proc/sys/kernel/random/boot_id')==OLD
  run('cleanup',['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3','-c',"import importlib.util;from pathlib import Path;s=importlib.util.spec_from_file_location('b',"+repr(str(M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'))+");b=importlib.util.module_from_spec(s);s.loader.exec_module(b);o=Path("+repr(str(out/'cleanup'))+");o.mkdir();d=b.Board("+repr(SN)+","+repr(str(WS/'westlake-inputs/tools/hdc_mac.sh'))+","+repr('mac '+str(safe.NOTE))+",'cx-t0',o);d.ready();pkg='org.secuso.privacyfriendlypaindiary';info=b.parse_bundle(d.shell('bm dump -n '+pkg)[1],pkg);assert info['uid'];assert b.cold_stop(d,pkg,info['uid'],o,'rollback');print('UID cold_stop verified')"])
  run('snapshot-before',[sys.executable,str(M/'scripts/lab/board_state_snapshot.py'),SN,'--hdc',hdc,'--plan',str(safe.TABLE),'--out',str(out/'snapshot-before'),'--label','boat-regression-rollback'],300)
  snap=json.loads((out/'snapshot-before/snapshot.json').read_text());assert snap['complete'] and snap['boot_stable']
  run('reverse',['bash',str(M/'scripts/lab/boat_layer_stage.sh'),'--serial',SN,'--reverse','--hdc',hdc,'--execute'])
  sh.read('sources-boat-absent','test ! -e /data/westlake-demo/u13/sources-boat')
  run('target-boot',[hdc,'-t',SN,'target','boot'],25);result['reboots']=1;save()
  deadline=time.monotonic()+180;new=None
  while time.monotonic()<deadline:
   time.sleep(5)
   try:
    boot=sh.read('wait-boot','cat /proc/sys/kernel/random/boot_id',12)
    receipt=sh.read('wait-receipt','cat /data/westlake-demo/u13/receipt.env',12)
    fields=dict(l.split('=',1) for l in receipt.splitlines() if '=' in l)
    if boot!=OLD and fields.get('boot_id')==boot and fields.get('state')=='READY' and fields.get('layers')=='56':new=boot;break
    if boot!=OLD and fields.get('boot_id')==boot and fields.get('state')=='FAILED':raise ValueError('recover FAILED')
   except (RuntimeError,subprocess.TimeoutExpired):pass
  if not new:raise RuntimeError('no newboot READY56; no repeated reboot')
  result['boot_id']=new;save();assert sh.read('enforcing','getenforce')=='Enforcing'
  sh.read('no-boat','test ! -e /data/westlake-demo/u13/sources-boat && ! grep -q sources-boat /proc/mounts')
  assert sh.read('preapp-socket','stat -c %a /dev/unix/socket/AppSpawnX')=='660'
  run('pre-identity',[sys.executable,str(HERE.parents[1]/'2026-10-09-demo-baseline/t3/verify_identity.py'),'--serial',SN,'--out',str(out/'pre-identity')],180,False)
  v=json.loads((out/'pre-identity/identity.json').read_text());assert v['unique_identity_paths']==319 and not v['diff'] and v['runtime']=='452447a4a0ba' and v['boot']=='ee927db88a67' and v['boot_before']==v['boot_after']==new
  run('hw',['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3',str(M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial',SN,'--lane','cx-t0','--hdc-cmd',str(WS/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(safe.NOTE),'--manifest',str(M/'knowledge/smoke/controls-apps.json'),'--input-root',str(WS/'westlake-b90-controls-inputs'),'--keys','helloworld','--launch-only','--wait','20','--hilog','20','--shots','20','--out',str(out/'hw'),'--run-id','boat-rollback-hw'],240,False)
  recs=list((out/'hw').glob('*/*/*/record.json'));assert len(recs)==1
  rec=json.loads(recs[0].read_text());assert rec.get('finished_at')
  run('facts',[sys.executable,str(M/'scripts/lab/run_facts.py'),str(recs[0].parent.parent)])
  run('final-identity',[sys.executable,str(HERE.parents[1]/'2026-10-09-demo-baseline/t3/verify_identity.py'),'--serial',SN,'--out',str(out/'final-identity')],180)
  assert sh.read('boot-final','cat /proc/sys/kernel/random/boot_id')==new
  result.update(status='PURE_V2_RESTORED',ui_verdict='pending outer screenshot review');save();print(json.dumps(result))
 except BaseException as e:
  result.update(status='STOP_PRESERVE_LOCK',error=str(e));save();raise
if __name__=='__main__':main()
