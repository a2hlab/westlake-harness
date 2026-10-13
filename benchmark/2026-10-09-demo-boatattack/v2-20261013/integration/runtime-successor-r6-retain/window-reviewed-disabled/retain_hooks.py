"""5ea three-source successor window; transport/popups/snapshot from actual r4 Window."""
import argparse,hashlib,importlib.util,json,os,re,shlex,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ['WORKSPACES'])
BASE=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/experiment-r5-hook-r3/window_hooks.r4.py'
BASE_SHA='c04c9706c97742fa7901962482c530fdf80d13b91fbc20beddb4ea63ae7685b0'.lower()
# Captured final r4 hook (snapshot override + per-line READY strip).
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def save(p,x):
 with Path(p).open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def resolve(p):return Path(os.path.expandvars(str(p))).resolve()
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
need(sha(BASE)==BASE_SHA,'r4 donor pin');Base=load(BASE,'r6_original_window')
SERIAL='5ea34a4500000000000000001123012c';Base.SERIAL=SERIAL
class Window(Base.Window):
 def __init__(self,a):
  self.reqpath=a.request.resolve();self.q=read(self.reqpath);self.out=resolve(self.q['out']);self.auth=read(a.authorization)
  need(sha(a.authorization)==a.authorization_sha256,'independent root authorization pin')
  need(self.auth['approved_by']=='outer(codex)' and self.auth['request_sha256']==sha(self.reqpath),'root request approval')
  need(self.q['serial']==self.auth['serial']==SERIAL,'scope')
  self.deadline=self.auth['rollback_expires_epoch'] if a.phase=='before-unlock' else self.auth['experiment_expires_epoch']
  need(self.auth['experiment_expires_epoch']<=self.auth['started_epoch']+1200 and self.auth['rollback_expires_epoch']>=self.auth['experiment_expires_epoch']+600 and self.auth['rollback_expires_epoch']<=self.auth['started_epoch']+1800,'separate20min+10min reserve')
  need(self.deadline>time.time() and self.auth['stop_new_tests_epoch']<=self.auth['experiment_expires_epoch'],'phase deadline')
  need(self.auth['allow_candidate_boot'] is True and self.auth['allow_rollback_boot'] is True,'both boot authorizations')
  need(self.auth['static_review']['accepted'] is True and self.auth['static_review']['evidence']==self.q['static_checkpoint'],'root static review')
  self.checkpin(self.q['static_checkpoint'])
  for ref in list(self.q['programs'].values())+self.q['input_pins']:self.checkpin(ref)
  need(self.auth['hook_sha256']==sha(__file__),'hook self pin')
  self.out.mkdir(parents=True,exist_ok=True);self.logs=self.out/('hook-'+a.phase+'-'+str(time.time_ns()));self.logs.mkdir()
  self.n=0;self.hdc=self.q['hdc'];self.plan=read(self.checkpin(self.q['plan']))
  need(self.plan['boot_id']==self.auth['origin_boot_id'],'origin boot')
  self.held();self.inst=load(self.program('installer'),'r6_successor');self.inst.validate(self.plan)
  self.core=self.inst.load(self.plan['core'],'r6_window_core')
 def device(self,name,command):
  # Same explicit remote status convention as the reused core transport.
  shell='/system/bin/sh -c '+shlex.quote(command)+'; rc=$?; printf "\\nR6_RC=%s\\n" "$rc"'
  raw=self.run(name,[self.hdc,'-t',SERIAL,'shell',shell]).replace('\r','')
  hit=re.search(r'\nR6_RC=(\d+)\n?\Z',raw);need(hit and hit.group(1)=='0','remote status '+name);return raw[:hit.start()].strip()
 def verify(self,tag,runtime,sources,worker=True):
  c=self.core;p=dict(self.plan,_active_boot=self.boot_id());dpath=self.logs/(tag+'-transport');dpath.mkdir()
  w=self
  class D(c.Device):
   def command(self,name,argv):
    w.held();need(time.time()<w.deadline,'verify deadline');return super().command(name,argv)
  dev=D(p,dpath);bms=self.inst.load(p['bms'],'r6_verify_bms');self.inst.identity(c,dev,p,runtime,bms)
  for r in p['members']:
   expected=r['before'] if sources=='before' else dict(exists=True,sha256=r['sha256'],**r['after'])
   need(c.equal(dev.probe(r['target']),expected),'three-source verification')
  for row in p['binds']:
   target=row['target'];source=row['source']
   self.device(tag+'-owner','set -eu; test "$(stat -c %d:%i '+shlex.quote(target)+')" = "$(stat -c %d:%i '+shlex.quote(source)+')"')
  bound=self.device(tag+'-bound','cat '+self.inst.ROOT+'/boat-'+p['_active_boot']+'.receipt')
  need(all(v in [line.strip() for line in bound.splitlines()] for v in ['state=BOUND','layers=7','boot_id='+p['_active_boot']]),'sameboot BOUND7')
  if worker:self.device(tag+'-worker','/system/bin/sh '+self.inst.ROOT+'/worker.sh --verify-bound')
  save(self.out/(tag+'.json'),dict(success=True,boot_id=p['_active_boot'],members=319,binds=7,sources=3,runtime_sha256=runtime))
 def reboot(self,tag,candidate):
  before=self.boot_id();intent=self.out/(tag+'-intent.json');need(not intent.exists(),'one boot per phase')
  save(intent,dict(serial=SERIAL,origin_boot=before,authorization=self.auth,epoch=time.time()))
  self.run(tag,[self.hdc,'-t',SERIAL,'target','boot'],allow=(1,))
  deadline=min(time.time()+240,self.deadline)
  while time.time()<deadline:
   time.sleep(5)
   try:
    boot=self.boot_id()
    if boot==before:continue
    raw=self.device(tag+'-ready','cat /data/westlake-demo/u13/receipt.env; param get sys.westlake.demo.u13.ready; getenforce')
    need(all(x in [s.strip() for s in raw.splitlines()] for x in ['state=READY','layers=56','boot_id='+boot,'true','Permissive']),'READY56 pending')
    bound=self.device(tag+'-bound','cat '+self.inst.ROOT+'/boat-'+boot+'.receipt')
    need(all(x in [s.strip() for s in bound.splitlines()] for x in ['state=BOUND','layers=7','boot_id='+boot]),'BOUND7 pending')
    save(self.out/(tag+'-result.json'),dict(boot_id=boot,ready=True,raw=raw,bound=bound));return boot
   except (ValueError,subprocess.TimeoutExpired):continue
  raise ValueError('authorized boot not READY56/BOUND7')
 def action(self,action):
  pf=self.out/'plan.enabled.json';boot=self.boot_id()
  live=self.device('live-runtime','sha256sum '+self.inst.RT).split()[0]
  a=dict(approved_by='outer(codex)',plan_sha256=sha(pf),serial=SERIAL,origin_boot_id=self.plan['boot_id'],boot_id=boot,expires_epoch=self.deadline,action=action,holder=self.held(),live_runtime_sha256=live,source_restore_only=(action=='rollback'))
  af=self.logs/(action+'-authorization.json');save(af,a)
  self.run(action,[sys.executable,self.program('installer'),'run','--plan',pf,'--action',action,'--execute','--authorization',af,'--authorization-sha256',sha(af),'--out',self.out/'transaction'])
 def retain_scope(self):
  need(self.auth.get('allow_retain') is True and self.auth.get('retain_scope')=='bounded-experiment-not-promotion','explicit experiment-only retention authority')
  need(time.time()<self.auth['retain_until_epoch']<=min(self.auth['experiment_expires_epoch'],self.auth['rollback_expires_epoch']-600),'ten-minute recovery reserve')
  watch=self.auth['recovery_watch']
  need(watch['registered'] is True and watch['responsible']==self.auth['holder']=='outer(codex)','root registered recovery responsibility')
  need(time.time()<watch['start_by_epoch']<=self.auth['retain_until_epoch'],'recovery start-by')
  need(watch['plan']==self.q['recovery_plan'],'exact recovery plan binding');self.checkpin(watch['plan'])
  need(self.checkpin(watch['registration']).stat().st_size>0,'actual root watcher registration receipt')
 def after_lock(self):
  self.retain_scope()
  need(self.boot_id()==self.plan['boot_id'],'fresh origin boot changed')
  self.verify('before',self.inst.OLD,'before')
  need(time.time()<self.auth['stop_new_tests_epoch'],'no experiment budget')
  save(self.out/'plan.enabled.json',dict(self.plan,execution_enabled=True));self.action('apply')
  need(read(self.out/'transaction/placed.json')['state']=='PLACED_ONLY','actual placement required')
  need(time.time()<self.auth['stop_new_tests_epoch'],'cutoff before candidate boot')
  self.preboot('candidate');boot=self.reboot('candidate-boot',True)
  self.verify('candidate',self.plan['candidate_runtime_sha256'],'after')
  ip=dict(read(resolve(self.q['interaction_plan'])),execution_enabled=True,boot_id=boot,owner=self.auth['holder']);ipf=self.out/'interaction.plan.json';save(ipf,ip)
  ia=dict(approved_by='outer(codex)',action='boat-interaction',plan_sha256=sha(ipf),runner_sha256=sha(self.program('interaction')),serial=SERIAL,owner=self.auth['holder'],boot_id=boot,expires_epoch=min(time.time()+330,self.deadline),spare_board_authorized=True)
  iaf=self.out/'interaction.authorization.json';save(iaf,ia)
  self.run('boat',[sys.executable,self.program('interaction'),'--plan',ipf,'--out',self.out/'boat','--execute','--authorization',iaf,'--authorization-sha256',sha(iaf)])
  save(self.out/'retain-ready.json',dict(success=True,boot_id=boot,request_sha256=sha(self.reqpath)))
  # Original board_run performs HW/ZZ once, before before_unlock.
 def before_unlock(self):
  rollback_deadline=self.deadline
  try:
   self.retain_scope();self.deadline=min(self.deadline,self.auth['experiment_expires_epoch'])
   e=load(self.program('retain_evidence'),'r6_retain_evidence')
   ready=read(self.out/'retain-ready.json');game=read(self.out/'boat/record.json')
   need(game['status']=='CAPTURED_PENDING_HUMAN' and game.get('experiment_disposition')=='retain','root did not finish with retain request')
   need(ready['success'] is True and ready['request_sha256']==sha(self.reqpath),'after-lock did not complete')
   need(self.boot_id()==ready['boot_id'],'candidate boot changed before retain')
   e.smoke(resolve(self.q['retain_smoke_result']),resolve(self.q['candidate_smoke']),self.auth['started_epoch'])
   self.verify('retain-final',self.plan['candidate_runtime_sha256'],'after')
   need(self.boot_id()==ready['boot_id'],'candidate boot changed during final verification')
   txn=self.out/'transaction';need(read(txn/'placed.json')['state']=='PLACED_ONLY','actual placed receipt')
   tx=read(txn/'transaction.json')
   need(tx['plan_sha256']==sha(self.out/'plan.enabled.json') and tx['boot_id']==self.plan['boot_id'] and tx['serial']==SERIAL,'actual deployment transaction binding')
   for pattern in ['intent-*.json','placed-*.json']:need(len(list(txn.glob(pattern)))==3,'three actual '+pattern)
   need(list(txn.glob('source-apply-*.json')),'source apply receipt missing')
   evidence=sorted(p for p in self.out.rglob('*') if p.is_file())
   evidence += [self.reqpath,resolve(self.q['retain_smoke_result'])]
   receipt=dict(schema='r6-retained-experiment/v1',status='BOUNDED_EXPERIMENT_NOT_PROMOTED',success=True,serial=SERIAL,boot_id=ready['boot_id'],origin_boot_id=self.plan['boot_id'],runtime_sha256=self.plan['candidate_runtime_sha256'],successor_plan=self.q['plan'],successor_program=self.q['programs']['installer'],retain_until_epoch=self.auth['retain_until_epoch'],authorization=self.auth,expected_319=319,binds=7,sources=3,game_pass=False,full337_admission='pending independent T0 Reader and actual game PASS',evidence=[e.pin(p) for p in evidence])
   save(self.out/'retained.json',receipt)
   save(self.out/'closed.json',dict(success=True,status='BOUNDED_F28_EXPERIMENT_RETAINED',candidate_promoted=False,receipt=e.pin(self.out/'retained.json')))
   return
  except Exception as exc:
   save(self.out/('retain-refused-'+str(time.time_ns())+'.json'),dict(retained=False,reason=str(exc)))
  finally:self.deadline=rollback_deadline
  self.rollback_before_unlock()
 def recover_retained(self):
  need(self.auth.get('allow_retain') is False,'recovery must not retain')
  need(self.checkpin(self.auth['recovery_receipt']).resolve()==(self.out/'retained.json').resolve(),'exact retained transaction receipt')
  self.rollback_before_unlock()
 def verify_recovered(self):
  need(read(self.out/'recovery-closed.json')['success'] is True,'recovery did not close; retain lock')
  e=load(self.program('retain_evidence'),'r6_recovery_smoke')
  e.smoke(resolve(self.q['recovery_smoke_result']),resolve(self.q['baseline_smoke']),self.auth['started_epoch'],self.inst.OLD)
  self.verify('recovery-unlock',self.inst.OLD,'before',worker=False)
 def rollback_before_unlock(self):
  txn=self.out/'transaction';intents=list(txn.glob('intent-*.json'))
  if not intents:
   need(not (self.out/'candidate-boot-intent.json').exists(),'boot without placement intent')
   self.verify('no-placement',self.inst.OLD,'before',worker=False)
   save(self.out/('recovery-closed.json' if (self.out/'closed.json').exists() else 'closed.json'),dict(success=True,no_intent=True,reboots=0));return
  need((txn/'transaction.json').is_file(),'intent without exact transaction; retain lock')
  self.action('rollback')
  if (self.out/'candidate-boot-intent.json').exists():
   self.preboot('baseline-return');self.reboot('baseline-return-boot',False)
  self.verify('restored',self.inst.OLD,'before')
  self.run('restored-hw-zz',[sys.executable,self.program('smoke'),'--spec',resolve(self.q['baseline_smoke']),'--serial',SERIAL,'--lane',self.auth['holder'],'--out',self.out/'restored-hw-zz'])
  save(self.out/('recovery-closed.json' if (self.out/'closed.json').exists() else 'closed.json'),dict(success=True,status='W3_947_RESTORED_PENDING_VISUAL_REVIEW',candidate_promoted=False))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['after-lock','before-unlock','recover-retained','verify-recovered']);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--authorization',type=Path,required=True);ap.add_argument('--authorization-sha256',required=True);a=ap.parse_args()
 try:
  requested=a.phase;a.phase='after-lock' if requested=='after-lock' else 'before-unlock'
  w=Window(a);getattr(w,requested.replace('-','_'))();return 0
 except Exception as e:print('R6 WINDOW REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
