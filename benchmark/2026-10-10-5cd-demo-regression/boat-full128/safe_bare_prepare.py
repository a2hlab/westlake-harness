#!/usr/bin/env python3
"""Authorized 5cd Boat safe prefix only: snapshot, DISABLED, bare reboot, exact base assertion.
Calls the existing demo_seal_61b no-bind and bare-base checks verbatim. Never installs/enables/starts apps.
"""
import hashlib,importlib.util,json,os,re,shutil,subprocess,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',HERE.parents[3]));MASTER=WS/'westlake-harness'
SERIAL='5cd1e3dd00000000000000000923012c';BOOT='707ef9d2-038c-48e1-8036-f0d9e50eb5c2'
NOTE=WS/'westlake-inputs/tools/board_note.sh';BOARD=MASTER/'.octos/boards/app-lighting.md'
HDC=os.environ.get('HDC') or shutil.which('hdc');OUT=HERE/'safe-bare-prepare'
BASE=MASTER/'benchmark/2026-10-03-u14-stage-a-plan/inputs/recovery-61b.json'
TABLE=MASTER/'benchmark/2026-10-10-u13-autostart/payload/u13-recover-table.json'
BASE_SHA='e7eb814913ae3a63fd55b20eaec02d7ee656710677e1a3de1c69972d9d1451e2'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def held():
 t=subprocess.check_output([str(NOTE),'held',SERIAL],text=True,timeout=15)
 if not re.match(r'^cx-t0\s+\d+\s+',t):raise RuntimeError('expected cx-t0 held, got '+repr(t))
def note(s):subprocess.run([str(NOTE),'progress',str(BOARD),'91','cx-t0',s],check=True,timeout=15)
class Shell:
 def __init__(self):self.n=0
 def read(self,name,command,timeout=25):
  held();self.n+=1;marker='__SAFE_BARE_'+uuid.uuid4().hex+'__'
  # Subshell captures the final command status without a preceding failure being hidden by the sentinel.
  script='( '+command+' ); s=$?; printf "\\n'+marker+'%s\\n" "$s"'
  p=subprocess.run([HDC,'-t',SERIAL,'shell',script],capture_output=True,text=True,timeout=timeout)
  stem=OUT/('%03d-%s'%(self.n,name));stem.with_suffix('.stdout.txt').write_text(p.stdout);stem.with_suffix('.stderr.txt').write_text(p.stderr)
  m=re.search(re.escape(marker)+r'(\d+)\s*$',p.stdout)
  save(stem.with_suffix('.json'),{'command':command,'hdc_exit':p.returncode,'remote_exit':int(m[1]) if m else None,'stdout_sha256':sha(stem.with_suffix('.stdout.txt')),'stderr_sha256':sha(stem.with_suffix('.stderr.txt'))})
  if p.returncode or not m or int(m[1]):raise RuntimeError(name+': HDC/remote refusal: '+p.stdout+p.stderr)
  return p.stdout[:m.start()].strip()
def main():
 if sys.argv[1:]!=['--execute']:raise SystemExit('explicit outer safe-prefix authorization + --execute required')
 assert HDC and sha(BASE)==BASE_SHA
 OUT.mkdir(exist_ok=False);os.environ['WORKSPACES']=str(WS)
 sh=Shell();result={'serial':SERIAL,'mode':'safe-prefix-only','installer_called':False,'ENABLE_called':False,'app_launches':0,'lock_retained':True}
 try:
  held();assert sh.read('boot-before','cat /proc/sys/kernel/random/boot_id')==BOOT
  assert sh.read('enforce-before','getenforce')=='Enforcing'
  note('宣布5cd Boat安全前半段<=60min：用户批snapshot→DISABLED→裸target boot→原assert_bare_base；128全量无法60min完成，按批文停在installer/ENABLE前。现持cx-t0锁，零其他板动作。')
  subprocess.run([sys.executable,str(MASTER/'scripts/lab/board_state_snapshot.py'),SERIAL,'--hdc',HDC,'--plan',str(TABLE),'--out',str(OUT/'before'),'--label','cx-t0-boat-safe-prefix'],check=True,timeout=300)
  snap=json.loads((OUT/'before/snapshot.json').read_text());assert snap['boot_stable'] and snap['complete'] and snap['boot_id']==BOOT
  assert sh.read('boot-after-snapshot','cat /proc/sys/kernel/random/boot_id')==BOOT
  # Exact existing demo_seal_61b disabled-marker sequence, not an installer rerun.
  sh.read('disable','test -d /data/westlake-demo/u13 && touch /data/westlake-demo/u13/DISABLED && test -f /data/westlake-demo/u13/DISABLED')
  result['disabled']=True;save(OUT/'result.json',result)
  held();p=subprocess.run([HDC,'-t',SERIAL,'target','boot'],capture_output=True,text=True,timeout=25)
  (OUT/'target-boot.txt').write_text(p.stdout+p.stderr);result['target_boot_exit']=p.returncode;save(OUT/'result.json',result)
  if p.returncode:raise RuntimeError('target boot rejected: '+p.stdout+p.stderr)
  deadline=time.monotonic()+300;after=None
  while time.monotonic()<deadline:
   time.sleep(5)
   try:
    text=sh.read('wait-boot','cat /proc/sys/kernel/random/boot_id; param get bootevent.boot.completed',timeout=12);lines=text.splitlines()
    if len(lines)==2 and re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',lines[0]) and lines[0]!=BOOT and lines[1]=='true':after=lines[0];break
   except (RuntimeError,subprocess.TimeoutExpired):pass
  if after is None:raise RuntimeError('USB/new ready boot did not return within300s; no repeated reboot, preserve lock')
  result.update(boot_before=BOOT,boot_after=after);save(OUT/'result.json',result)
  sh.read('bare-disabled','test -f /data/westlake-demo/u13/DISABLED')
  assert sh.read('bare-enforce','getenforce')=='Enforcing'
  spec=importlib.util.spec_from_file_location('seal',MASTER/'scripts/lab/demo_seal_61b.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  class ExistingAssertions(m.Workflow):
   def shell(self,name,command,criterion,allowed=(0,)):
    print(name+': '+criterion,flush=True);return 0,sh.read(name,command)
  check=object.__new__(ExistingAssertions);check.preview=False;check.plan={'inputs':{'baseline_319':{'path':str(BASE)},'recover_table':{'path':str(TABLE)}}}
  check.assert_no_binds();check.assert_bare_base()
  assert sh.read('boot-after-assert','cat /proc/sys/kernel/random/boot_id')==after
  result.update(bare_base_passed=True,status='STOPPED_AS_AUTHORIZED_BEFORE_INSTALLER_ENABLE',assertion_source_sha256=sha(MASTER/'scripts/lab/demo_seal_61b.py'),baseline_319_sha256=sha(BASE));save(OUT/'result.json',result)
  note('5cd Boat安全前半段完成：新boot='+after+'，DISABLED在；原assert_no_binds+assert_bare_base PASS，seq1逐件SHA/成员匹配、物理/system/android=0；按用户60min分段批文停在installer/ENABLE前，保锁。raw='+str(OUT).replace(str(WS),'$WORKSPACES'))
 except BaseException as e:
  result.update(status='STOP_GUARD_PRESERVE_LOCK',error=str(e));save(OUT/'result.json',result)
  note('5cd Boat安全前半段拒绝，保锁、无installer/ENABLE：'+str(e)+'；raw='+str(OUT).replace(str(WS),'$WORKSPACES'))
  raise
if __name__=='__main__':main()
