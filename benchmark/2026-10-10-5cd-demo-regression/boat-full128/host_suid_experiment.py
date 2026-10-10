#!/usr/bin/env python3
"""Outer-approved single-existing-host-bind suid restoration; no reboot or cfg edit."""
import importlib.util,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;WS=HERE.parents[3];M=WS/'westlake-harness'
SN='5cd1e3dd00000000000000000923012c';BOOT='6898d2a5-5534-4a1d-a580-9b40f585693d'
HOST='/system/bin/appspawn-x';SHA='2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e'
HDC=os.environ.get('HDC','/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc')
def mounts(t):
 return {x.split()[0]:x.split() for x in t.splitlines() if x.strip()}
def main():
 if sys.argv[1:]!=['--execute']:raise SystemExit('explicit outer approval + --execute required')
 out=HERE/'suid-experiment/host-suid-r1';out.mkdir(exist_ok=False)
 s=importlib.util.spec_from_file_location('guard',HERE/'safe_bare_prepare.py');g=importlib.util.module_from_spec(s);s.loader.exec_module(g);g.OUT=out;g.HDC=HDC;sh=g.Shell()
 result={'serial':SN,'boot_id':BOOT,'status':'PRECHECK','lock_retained':True,'reboot':False,'cfg_edit':False};changed=False
 def save(): (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def run(name,args,timeout=240):
  with (out/(name+'.log')).open('wb') as f:cp=subprocess.run(args,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
  return cp.returncode
 try:
  assert sh.read('boot-before','cat /proc/sys/kernel/random/boot_id')==BOOT
  assert sh.read('enforce-before','getenforce')=='Enforcing'
  assert sh.read('host-sha-before','sha256sum '+HOST).split()[0]==SHA
  before=mounts(sh.read('mountinfo-before','cat /proc/1/mountinfo'))
  rows=[x for x in before.values() if x[4]==HOST];assert len(rows)==1
  row=rows[0];mid=row[0];flags=set(row[5].split(','));assert 'nosuid' in flags and 'noexec' not in flags
  assert row[3]=='/westlake-demo/u13/sources/seq2'
  stat=sh.read('host-stat-before',"stat -c '%a:%u:%g:%C' "+HOST);assert stat=='755:0:0:u:object_r:appspawn_exec:s0'
  result['before_flags']=sorted(flags);save()
  # Write attempt is treated as possibly effective even if its transport status is lost.
  changed=True
  sh.read('remount-suid','mount -o remount,bind,suid '+HOST)
  after=mounts(sh.read('mountinfo-after','cat /proc/1/mountinfo'))
  delta={k:{'before':before.get(k),'after':after.get(k)} for k in before.keys()|after.keys() if before.get(k)!=after.get(k)}
  (out/'mount-delta.json').write_text(json.dumps(delta,indent=2)+'\n')
  assert set(delta)=={mid},'more than host mount changed'
  expect=row.copy();expect[5]=','.join(x for x in row[5].split(',') if x!='nosuid')
  assert after[mid]==expect,'flags other than nosuid changed'
  assert sh.read('host-stat-after',"stat -c '%a:%u:%g:%C' "+HOST)==stat
  assert sh.read('host-sha-after','sha256sum '+HOST).split()[0]==SHA
  result.update(status='FLAG_ONLY_VERIFIED',after_flags=after[mid][5].split(','));save()
  args=['orb','-m','a2hlab','env','WORKSPACES='+str(WS),'MAC_HOME='+str(Path.home()),'python3',str(M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial',SN,'--lane','cx-t0','--hdc-cmd',str(WS/'westlake-inputs/tools/hdc_mac.sh'),'--lock-cmd','mac '+str(g.NOTE),'--manifest',str(M/'knowledge/smoke/controls-apps.json'),'--input-root',str(WS/'westlake-b90-controls-inputs'),'--keys','helloworld','--launch-only','--wait','20','--hilog','20','--shots','20','--out',str(out/'hw'),'--run-id','host-suid-hw']
  result['hw_rc']=run('hw',args);save()
  recs=list((out/'hw').glob('*/*/*/record.json'));assert len(recs)==1
  rec=json.loads(recs[0].read_text());assert rec.get('finished_at')
  run('facts',[sys.executable,str(M/'scripts/lab/run_facts.py'),str(recs[0].parent.parent)])
  rc=run('final319',[sys.executable,str(M/'benchmark/2026-10-09-demo-baseline/t3/verify_identity.py'),'--serial',SN,'--out',str(out/'final319')],180)
  ident=json.loads((out/'final319/identity.json').read_text());assert rc==0 and ident['passed'] and ident['unique_identity_paths']==319 and not ident['diff']
  assert rec.get('observed_pids'), 'HW has no observed child at capture; recovery gate failed'
  assert sh.read('boot-final','cat /proc/sys/kernel/random/boot_id')==BOOT
  sh.read('parent-socket',"ps -A -o PID,PPID,UID,NAME; ls -lZ /dev/unix/socket/AppSpawnX; grep AppSpawnX /proc/net/unix")
  result.update(status='PARENT_AND_319_VERIFIED',ui_verdict='pending screenshot review');save();print(json.dumps(result))
 except BaseException as e:
  result.update(status='FAILED_RESTORE_NOSUID',error=str(e));save()
  if changed:
   # Exact pre-experiment flags: restore nodev/noatime too if mount changed more than requested.
   opts=','.join(['remount','bind']+[x for x in row[5].split(',') if x!='rw'])
   try:
    sh.read('restore-original-flags','mount -o '+opts+' '+HOST)
    restored=mounts(sh.read('restore-readback','cat /proc/1/mountinfo'))
    assert restored[mid]==row
    result['original_host_flags_restored']=True
   except BaseException as f:result['restore_error']=str(f)
  save();raise
if __name__=='__main__':main()
