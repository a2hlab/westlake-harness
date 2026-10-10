#!/usr/bin/env python3
"""Outer-approved one clean target boot, read-only provenance, one HW capture; caller unlocks after readout review."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];M=WS/'westlake-harness'
SN='5cd1e3dd00000000000000000923012c';OLD='6898d2a5-5534-4a1d-a580-9b40f585693d'
HDC=os.environ.get('HDC','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
def main():
 if sys.argv[1:]!=['--execute']:raise SystemExit('explicit approved one-reboot readout required')
 out=HERE/'suid-experiment/clean-reboot-r1';out.mkdir(exist_ok=False)
 sp=importlib.util.spec_from_file_location('guard',HERE/'safe_bare_prepare.py');g=importlib.util.module_from_spec(sp);sp.loader.exec_module(g);g.OUT=out;g.HDC=HDC;sh=g.Shell()
 result={'serial':SN,'old_boot':OLD,'reboot_attempts':0,'bind_changes':0,'cfg_changes':0,'lock_retained':True}
 def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def run(name,args,timeout=240):
  with (out/(name+'.log')).open('wb') as f:cp=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  return cp.returncode
 try:
  assert sh.read('preboot','cat /proc/sys/kernel/random/boot_id')==OLD
  sh.read('before-mountinfo','cat /proc/1/mountinfo')
  g.note('5cd已批一次干净target boot→原样PID1 mountinfo/fstab/boot-journal/同boot READY56/Enforcing→HW一次t20；不逐个去nosuid、不改recover或其他bind，完成归档UNLOCK。')
  result['reboot_attempts']=1;save()
  rc=run('target-boot',[HDC,'-t',SN,'target','boot'],25);result['target_boot_rc']=rc;save()
  deadline=time.monotonic()+240;new=None
  while time.monotonic()<deadline:
   time.sleep(5)
   try:
    boot=sh.read('wait-boot','cat /proc/sys/kernel/random/boot_id',12)
    receipt=sh.read('wait-receipt','cat /data/westlake-demo/u13/receipt.env',12)
    fields=dict(l.split('=',1) for l in receipt.splitlines() if '=' in l)
    if boot!=OLD and fields.get('boot_id')==boot and fields.get('state')=='FAILED':raise ValueError('recover FAILED')
    if boot!=OLD and fields.get('boot_id')==boot and fields.get('state')=='READY' and fields.get('layers')=='56':new=boot;break
   except (RuntimeError,subprocess.TimeoutExpired):pass
  if not new:raise RuntimeError('one reboot did not reach newboot READY56; no repeated boot')
  result['boot_id']=new;save()
  assert sh.read('enforce','getenforce')=='Enforcing'
  mounts=sh.read('pid1-mountinfo','cat /proc/1/mountinfo')
  rows={x.split()[4]:x.split() for x in mounts.splitlines() if x.strip()}
  for key in ['/data','/system/bin/appspawn-x']:
   result[key]={'row':rows[key],'nosuid':'nosuid' in rows[key][5].split(',')}
  sh.read('receipt','cat /data/westlake-demo/u13/receipt.env')
  sh.read('fstab','cat /vendor/etc/fstab.uis7885')
  sh.read('boot-journal','cat /data/westlake-demo/u13/boot-journal-'+new+'.log')
  sh.read('recover-log-and-boat','ls -l /data/westlake-demo/u13/recover-*; tail -n 8 /data/westlake-demo/u13/boat-overlay.log; sha256sum /system/etc/westlake-u13-recover.sh /system/bin/appspawn-x; ls -lZ /system/bin/appspawn-x')
  sh.read('no-boat','test ! -e /data/westlake-demo/u13/sources-boat && ! grep -q sources-boat /proc/mounts')
  result.update(status='NEWBOOT_READONLY_CAPTURED');save()
  args=['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3',str(M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial',SN,'--lane','cx-t0','--hdc-cmd',str(WS/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(g.NOTE),'--manifest',str(M/'knowledge/smoke/controls-apps.json'),'--input-root',str(WS/'westlake-b90-controls-inputs'),'--keys','helloworld','--launch-only','--wait','20','--hilog','20','--shots','20','--out',str(out/'hw'),'--run-id','clean-reboot-hw']
  result['hw_rc']=run('hw',args);save()
  records=list((out/'hw').glob('*/*/*/record.json'));assert len(records)==1
  rec=json.loads(records[0].read_text());assert rec.get('finished_at')
  run('facts',[sys.executable,str(M/'scripts/lab/run_facts.py'),str(records[0].parent.parent)])
  result['final319_rc']=run('final319',[sys.executable,str(M/'benchmark/2026-10-09-demo-baseline/t3/verify_identity.py'),'--serial',SN,'--out',str(out/'final319')],180)
  sh.read('dmesg-after','dmesg')
  assert sh.read('boot-final','cat /proc/sys/kernel/random/boot_id')==new
  result.update(status='READOUT_COMPLETE',ui_verdict='pending screenshot review');save();print(json.dumps(result))
 except BaseException as e:
  result.update(status='STOP_LOCK_RETAINED',error=str(e));save();raise
if __name__=='__main__':main()
