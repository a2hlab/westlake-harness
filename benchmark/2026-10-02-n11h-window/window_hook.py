"""Host-only stopped-parent transaction, restoring signed U10.1T8, never U9.

Reuse the production U7 journal, stage/bind, process and rollback primitives.
No boot/JAR remount: their signed bytes are asserted throughout this transaction.
"""
import argparse, fcntl, hashlib, json, os, subprocess, sys, uuid
from pathlib import Path
H=Path(__file__).resolve().parent; R=H.parents[1]
sys.path.insert(0,str(H));sys.path.insert(0,str(R/'scripts/lab'))
import prepare as config
import u7_executor as u, generation_bundle as gb, deployment_native_gate as ng, lab_paths

def save(p,d):config.save(p,d)
def vm(argv):
 return subprocess.run(['orb','-m','a2hlab','env','WORKSPACES='+str(config.W),'MAC_HOME='+str(Path.home()),'LAB_HOME='+os.environ['LAB_HOME'],*argv],check=True)
def identity(candidate=False):
 data=json.loads((H/'expected.json').read_text());return data['candidate' if candidate else 'base'],data['candidate_fingerprints' if candidate else 'base_fingerprints'],data['reference_paths']
def composition():
 data=json.loads((H/'composition.json').read_text())
 assert gb.sha(config.BASE/'bundle.json')==data['base_bundle_sha256'],'signed base drift'
 assert gb.sha(config.BASE/'native/package.json')==data['base_native_manifest_sha256'],'base native drift'
 assert gb.sha(config.PKG/'package.json')==data['package_manifest_sha256'],'candidate manifest drift'
 assert gb.sha(config.PKG/'native-checks/native-gates.json')==data['inputs_sha256'],'candidate inputs drift'
 old=u.native.load_package(config.BASE/'native');new=u.native.load_package(config.PKG)
 source=u.native.validate_replacement(old,new,u.HOST)
 assert old['files'][source]==config.OLD and new['files'][source]==config.NEW
 assert {p for p in identity()[0] if identity()[0][p]!=identity(True)[0][p]}=={u.HOST}
 return data,new,source

def preflight():
 data,new,source=composition()
 tickets=[ng.check(config.PKG),ng.check(config.BASE/'native')]
 for p in (config.PKG,config.BASE/'native'):u.native.check_frozen_package(p)
 old,oldfp,paths=identity();expected,newfp,_=identity(True)
 u.native.check_frozen_restore(old);u.native.check_frozen_restore(expected)
 return {'schema':'n11h-host-only/v1','root':str(config.PKG),'baseline_native':str(config.BASE/'native'),'generation':new['generation'],
  'baseline':old,'expected':expected,'additions':[], 'reference_paths':paths,
  'changes':[{'source':source,'target':u.HOST,'sha256':config.NEW}], 'native_tickets':tickets,
  'composition_sha256':gb.sha(H/'composition.json'),'expected_sha256':gb.sha(H/'expected.json'),
  'gates_passed':True,'device_io':False,'boot_and_jars':'unchanged; signed base per-path SHA checked, no image/JAR bind operations'}

class HostIO(u.DeviceIO):
 def check_ticket(self,plan):
  composition()
  assert gb.sha(H/'composition.json')==plan['composition_sha256'],'composition changed during transaction'
  assert gb.sha(H/'expected.json')==plan['expected_sha256'],'identity input changed during transaction'
  assert plan['changes']==[{'source':'payload/runtime/appspawn-x','target':u.HOST,'sha256':config.NEW}]
  for ticket in plan['native_tickets']:ng.assert_unchanged(ticket)

 def cleanup_toutiao(self):
  """Only the explicitly observed app; preserve the stock UID/PPID kill guard."""
  pkg='com.ss.android.article.news'
  data=self.b.parse_bundle(self.shell('bm dump -n '+pkg),pkg)
  assert type(data['uid']) is int and data['uid']>=20000000,'unidentified Toutiao UID'
  before=self.ps(); targets=[r for r in before if r['uid']==data['uid']]
  if not targets:
   save(self.out/'toutiao-cleanup.json',{'package':pkg,'uid':data['uid'],'before':before,'after':before,'absent':True});return
  try:
   assert self.b.cold_stop(self.board,pkg,data['uid'],self.out,'toutiao-residual'),'Toutiao remains live'
  finally:save(self.out/'toutiao-cleanup.json',{'package':pkg,'uid':data['uid'],'before':before,'after':self.ps()})

 def stop_for_rollback(self):
  # Do not allow a stale approved observation key to obstruct a safe rollback.
  # Exactly identify each residual by BMS UID from this window's key inventory.
  manifest_paths=[lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch/apps.json',
     config.W/'westlake-harness-t4/benchmark/2026-10-01-corpus-v2-inputs/apps-v2.json']
  import importlib.util
  # cold_stop remains the production per-PID/UID/PPID guard; unknown ownership refuses.
  manifest_apps=[]
  for path in manifest_paths:
   obj=json.loads(path.read_text()); manifest_apps += obj if isinstance(obj,list) else obj.get('apps',[])
  allowed=set(json.loads((H/'key-inventory.json').read_text())['keys'])
  apps={a['package']:a for a in manifest_apps if a.get('key') in allowed}
  rows=[r for r in self.ps() if r['name']=='appspawn-x' and r['uid']!=0]
  for pkg in apps:
   if not rows:break
   rc,text=self.board.shell('bm dump -n '+pkg,required=False)
   if rc:continue
   data=self.b.parse_bundle(text,pkg)
   if any(r['uid']==data['uid'] for r in rows):
    assert self.b.cold_stop(self.board,pkg,data['uid'],self.out,'rollback-'+uuid.uuid4().hex),'observed child still live'
    rows=[r for r in self.ps() if r['name']=='appspawn-x' and r['uid']!=0]
  super().stop_for_rollback()

def verify(serial,out,candidate=False):
 expected,fp,paths=identity(candidate);io=HostIO(serial,'cx-t0',out/'device');got,absent=io.snapshot(sorted(expected))
 diff={p:{'expected':s,'actual':got.get(p)} for p,s in expected.items() if got.get(p)!=s}
 actual=u.fingerprints(got,paths) if not absent else None
 save(out/'identity-318.json',{'identity_assertions':318,'unique_paths':len(got),'diff':diff,'absent':absent,'fingerprints':actual,'expected_fingerprints':fp,'boot_id':io.boot})
 assert not diff and not absent and actual==fp,'full identity/fingerprint mismatch'
 return io

def local(action,root):
 if action=='verify-base':verify(config.SERIAL,root);return
 if action=='cleanup':
  io=verify(config.SERIAL,root/'before');io.cleanup_toutiao();verify(config.SERIAL,root/'after');return
 lock=config.W/'westlake-generation-state'/config.SERIAL/'u7-executor.lock';lock.parent.mkdir(parents=True,exist_ok=True)
 with lock.open('a') as handle:
  fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
  journal=root/'transaction/journal.json'
  if action=='apply':
   assert not journal.exists(),'fresh window required'
   assert json.loads((H/'plan-61b.json').read_text())['execution_enabled'] is True,'outer plan authorization pending'
   plan=preflight();io=verify(config.SERIAL,root/'baseline');io.cleanup_toutiao()
   tx=u.Transaction(io,journal,plan);tx.apply();verify(config.SERIAL,root/'candidate',True)
  elif action=='rollback':
   if journal.exists():
    state=json.loads(journal.read_text())
    if state['status']!='rolled_back':u.Transaction(HostIO(config.SERIAL,'cx-t0',root/'rollback-device'),journal,state['plan']).rollback()
   verify(config.SERIAL,root/('restored-'+uuid.uuid4().hex))

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True)
 p.add_argument('--action',choices=['dry-run','apply','finish','verify-base','cleanup','rollback'],required=True);a=p.parse_args()
 if a.action=='dry-run':save(a.root/'dry-run.json',preflight());return
 if sys.platform=='darwin':
  def run(action):vm(['python3',str(Path(__file__).resolve()),'--action',action,'--root',str(a.root)])
  if a.action=='finish':
   run('rollback')
   subprocess.run([sys.executable,str(lab_paths.harness()/'scripts/lab/activation_smoke.py'),'--serial',config.SERIAL,'--lane','cx-t0','--spec',str(H/'restored-smoke.json'),'--out',str(a.root/('recovery-smoke-'+uuid.uuid4().hex))],check=True)
   run('verify-base');save(a.root/'finish.json',{'restored':'U10.1T8','passed':True,'runtime_fp':'d6848fa2c989','boot_fp':'e3806b65a079','identity_assertions':318})
  else:run(a.action)
 else:local(a.action,a.root)
if __name__=='__main__':main()
