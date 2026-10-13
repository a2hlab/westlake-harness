"""Two explicit board_run hooks; reuse pinned executor, R5, BMS, snapshot and policy CLIs.
No action without root's independent current-window authorization. Not a deployment framework.
"""
import argparse,hashlib,importlib.util,json,os,subprocess,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent
RESUME_SHA='ba40a3cdff98f96c736276381e8a6566cd4a8df2e83221866f135d46521cb048'
SERIAL='5cd1e3dd00000000000000000923012c'
def need(ok,why):
 if not ok:raise ValueError(why)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):Path(p).write_text(json.dumps(x,indent=2)+'\n')
def resolve(p):return Path(os.path.expandvars(str(p))).resolve()
def pin(p):return {'path':str(Path(p).resolve()),'sha256':sha(p)}
def load(p,name):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);sys.modules[name]=m;s.loader.exec_module(m);return m
class Window:
 def __init__(self,a):
  self.reqpath=a.request.resolve();self.q=read(self.reqpath);self.out=resolve(self.q['out']);self.auth=read(a.authorization)
  need(sha(a.authorization)==a.authorization_sha256,'independent root authorization pin')
  need(self.auth['approved_by']=='outer(codex)' and self.auth['request_sha256']==sha(self.reqpath),'root request approval')
  need(self.q['serial']==self.auth['serial']==SERIAL,'scope/expiry')
  self.deadline=self.auth['rollback_expires_epoch'] if a.phase=='before-unlock' else self.auth['experiment_expires_epoch']
  need(self.auth['experiment_expires_epoch']<=self.auth['started_epoch']+1200 and self.auth['rollback_expires_epoch']>=self.auth['experiment_expires_epoch']+600 and self.auth['rollback_expires_epoch']<=self.auth['started_epoch']+1800,'separate20min experiment+10min rollback reserve required')
  need(self.deadline>time.time(),'this phase deadline expired')
  need(self.auth['allow_candidate_boot'] is True and self.auth['allow_rollback_boot'] is True,'both exact boot actions need authorization')
  need(self.auth['static_review']['accepted'] is True,'T0 static alignment pending')
  need(self.auth['static_review']['evidence']==self.q['static_checkpoint'],'static checkpoint identity')
  checkpoint=read(self.checkpin(self.q['static_checkpoint']));need(checkpoint['status']=='NO_KNOWN_STATIC_FATAL_GO_MINIMAL_AB_NOT_RUNTIME_ACCEPT','static fatal/pending result')
  for ref in list(self.q['programs'].values())+self.q['input_pins']:self.checkpin(ref)
  need(self.auth['hook_sha256']==sha(__file__),'hook self pin')
  self.out.mkdir(parents=True,exist_ok=True);self.logs=self.out/('hook-'+a.phase+'-'+str(time.time_ns()));self.logs.mkdir()
  self.n=0;self.hdc=self.q['hdc'];self.plan=read(resolve(self.q['plan']['path']));self.checkpin(self.q['plan'])
  need(self.plan['boot_id']==self.auth['origin_boot_id'],'origin capture boot')
  self.held();self.inst=load(self.program('installer'),'r5_inst');self.core=self.inst.core_for(self.plan);self.inst.validate(self.plan,self.core)
 def checkpin(self,r):
  p=resolve(r['path']);need(sha(p)==r['sha256'],'pin drift '+r['path']);return p
 def program(self,n):return self.checkpin(self.q['programs'][n])
 def held(self):
  r=subprocess.run(['bash',str(self.program('lock')),'held',SERIAL],capture_output=True,text=True,timeout=15)
  held=r.stdout.split()
  need(r.returncode==0 and not r.stderr and bool(held) and held[0]==self.auth['holder'],'lock owner mismatch')
  return r.stdout.strip()
 def run(self,name,argv,allow=()):
  self.held();need(time.time()<self.deadline,'window expired')
  self.n+=1;stem=self.logs/('%03d-%s'%(self.n,name));start=time.time()
  with stem.with_suffix('.stdout').open('xb') as o,stem.with_suffix('.stderr').open('xb') as e:
   r=subprocess.run([str(x) for x in argv],stdout=o,stderr=e,timeout=max(1,min(2700,self.deadline-time.time())))
  save(stem.with_suffix('.json'),{'argv':[str(x) for x in argv],'rc':r.returncode,'started':start,'finished':time.time()})
  need(r.returncode==0 or r.returncode in allow,name+' failed; logs retained')
  return stem.with_suffix('.stdout').read_text()
 def device(self,name,command):return self.run(name,[self.hdc,'-t',SERIAL,'shell',command]).strip()
 def boot_id(self):
  text=self.device('boot-id','cat /proc/sys/kernel/random/boot_id');need(__import__('re').fullmatch(r'[a-f0-9]{8}(?:-[a-f0-9]{4}){3}-[a-f0-9]{12}',text),'boot UUID');return text
 def foreground(self,tag,boot):
  # Exact desktop_launch/capture flow from root's proven recover_foreground.py; parameters only.
  self.held();need(time.time()<self.deadline,'foreground phase deadline')
  self.checkpin(self.q['foreground_source'])
  B=load(self.program('batch'),'r5_foreground_bms');out=self.out/tag;out.mkdir(exist_ok=False)
  b=B.Board(SERIAL,self.hdc,str(self.program('lock')),self.auth['holder'],out/'commands');b.ready();need(b.boot.strip()==boot,'foreground boot')
  record={'serial':SERIAL,'boot_id':boot,'package':'org.westlake.imehost','reason':'restore actual host foreground before original R5','consent_interaction':False}
  remote='/data/local/tmp/boat-r5-host-'+str(time.time_ns());b.shell('test ! -e '+remote+' && mkdir '+remote)
  B.desktop_launch(b,{'package':'org.westlake.imehost','launch_activity':'EntryAbility'},remote,out,record)
  B.save(out/'record.json',record);B.capture(b,remote+'/host.jpeg',out/'host.jpeg')
 def r5(self,tag,boot):
  ref=self.q['activation_binding'];self.checkpin(ref);out=self.out/(tag+'.json')
  self.run(tag,[sys.executable,self.program('r5'),'--checker','activation','--activation-binding',resolve(ref['path']),'--binding-sha256',ref['sha256'],'--serial',SERIAL,'--boot-id',boot,'--hdc',self.hdc,'--out',out])
  r=read(out);need(r['status']=='PASS' and r['passed'] and r['file_count']==940 and not r['synthetic'],'actual original940 R5 must PASS')
 def popups(self,tag):
  need(time.time()<self.auth['stop_new_tests_epoch'],'no new test past cutoff')
  out=self.out/tag
  self.run(tag,[sys.executable,self.program('batch'),'--execute','--serial',SERIAL,'--lane',self.auth['holder'],'--manifest',resolve(self.q['popup_manifest']),'--input-root',resolve(self.q['input_root']),'--keys',','.join(self.q['popup_keys']),'--launch-only','--hilog','--shots','5,10,20','--out',out],allow=(1,))
  records=list(out.glob('*/*/*/record.json'));got={r.parent.name for r in records}
  need(got==set(self.q['popup_keys']),'missing popup record; not a completed sample')
  for f in records:need(read(f).get('status') in ('captured','foreground_unconfirmed'),'popup process/infra failure')
 def preboot(self,tag):
  snapshot_path=resolve(self.q['baseline_snapshot_plan'] if tag=='baseline-return' else self.q['snapshot_plan'])
  if tag=='candidate' and 'candidate_snapshot_override' in self.auth:
   snapshot_path=self.checkpin(self.auth['candidate_snapshot_override'])
  self.run(tag+'-snapshot',[sys.executable,self.program('snapshot'),SERIAL,'--hdc',self.hdc,'--plan',snapshot_path,'--out',self.out/(tag+'-snapshot')])
  r=read(self.out/(tag+'-snapshot/snapshot.json'));need(r['complete'] and r['boot_stable'] and not r['errors'],'snapshot gate')
  self.run(tag+'-policy',[sys.executable,self.program('policy'),'--evidence',self.out/(tag+'-policy.json')])
  need(not read(self.out/(tag+'-policy.json'))['failures'],'policy gate')
 def reboot(self,tag,candidate):
  before=self.boot_id();intent=self.out/(tag+'-intent.json');need(not intent.exists(),'one boot per phase')
  save(intent,{'serial':SERIAL,'origin_boot':before,'authorization':self.auth,'epoch':time.time()})
  self.run(tag,[self.hdc,'-t',SERIAL,'target','boot'],allow=(1,))
  deadline=min(time.time()+240,self.deadline);boot=None
  while time.time()<deadline:
   time.sleep(5)
   try:
    boot=self.boot_id()
    if boot==before:continue
    raw=self.device(tag+'-ready','cat /data/westlake-demo/u13/receipt.env; param get sys.westlake.demo.u13.ready; getenforce')
    if not all(x in [line.strip() for line in raw.splitlines()] for x in ['state=READY','layers=56','boot_id='+boot,'true','Permissive']):continue
    if candidate:
     bound=self.device('boat-bound','cat '+self.inst.ROOT+'/boat-'+boot+'.receipt')
     need(all(x in bound.splitlines() for x in ['state=BOUND','layers=6','boot_id='+boot]),'candidate worker not BOUND6')
    save(self.out/(tag+'-result.json'),{'boot_id':boot,'ready':True,'raw':raw});return boot
   except (ValueError,subprocess.TimeoutExpired):continue
  raise ValueError('authorized boot did not become ready')
 def after_lock(self):
  need(self.boot_id()==self.plan['boot_id'],'fresh origin boot changed')
  if 'resume_after_baseline' in self.q:
   helper=HERE/'resume_baseline.py';need(sha(helper)==RESUME_SHA,'resume validator pin')
   resume=load(helper,'r5_resume');report=resume.validate(self.checkpin(self.q['resume_after_baseline']),self.q)
   save(self.out/'resumed-baseline.json',report)
  else:
   self.foreground('baseline-host',self.plan['boot_id']);self.r5('baseline-r5',self.plan['boot_id']);self.popups('popup-before')
   self.run('baseline-hw-zz',[sys.executable,self.program('smoke'),'--spec',resolve(self.q['baseline_smoke']),'--serial',SERIAL,'--lane',self.auth['holder'],'--out',self.out/'baseline-hw-zz'])
  need(time.time()<self.auth['stop_new_tests_epoch'] and time.time()<self.deadline,'no experiment budget for placement')
  enabled=dict(self.plan,execution_enabled=True);pf=self.out/'plan.enabled.json';save(pf,enabled)
  a={'approved_by':'outer(codex)','plan_sha256':sha(pf),'serial':SERIAL,'origin_boot_id':enabled['boot_id'],'boot_id':enabled['boot_id'],'expires_epoch':self.deadline,'action':'apply','holder':self.held()};af=self.out/'apply-authorization.json';save(af,a)
  self.run('apply',[sys.executable,self.program('installer'),'--plan',pf,'--action','apply','--execute','--authorization',af,'--authorization-sha256',sha(af),'--out',self.out/'transaction'])
  need(read(self.out/'transaction/placed.json')['state']=='PLACED_ONLY','placement receipt missing')
  need(time.time()<self.auth['stop_new_tests_epoch'],'cutoff before candidate boot; rollback unbooted placement')
  self.preboot('candidate');boot=self.reboot('candidate-boot',True)
  ip=dict(read(resolve(self.q['interaction_plan'])),execution_enabled=True,boot_id=boot,owner=self.auth['holder']);ipf=self.out/'interaction.plan.json';save(ipf,ip)
  ia={'approved_by':'outer(codex)','action':'boat-interaction','plan_sha256':sha(ipf),'runner_sha256':sha(self.program('interaction')),'serial':SERIAL,'owner':self.auth['holder'],'boot_id':boot,'expires_epoch':min(time.time()+330,self.deadline),'spare_board_authorized':True};iaf=self.out/'interaction.authorization.json';save(iaf,ia)
  self.run('boat',[sys.executable,self.program('interaction'),'--plan',ipf,'--out',self.out/'boat','--execute','--authorization',iaf,'--authorization-sha256',sha(iaf)])
  self.popups('popup-after')
 def before_unlock(self):
  txn=self.out/'transaction';pf=self.out/'plan.enabled.json'
  if not (txn/'transaction.json').exists():
   need(not list(txn.glob('intent-*.json')) and not list(txn.glob('directory-created-*.json')),'partial evidence without transaction; retain lock')
   boot=self.boot_id();self.foreground('no-placement-host',boot);self.r5('no-placement-r5',boot)
   save(self.out/'no-placement.json',{'no_transaction_or_intent':True,'host_foreground_restored':True,'original940_passed':True});return
  p=read(pf);boot=self.boot_id();p['_active_boot']=boot;core=self.inst.core_for(p);dev=core.Device(p,self.logs/'rollback-transport');(self.logs/'rollback-transport').mkdir()
  B=load(self.program('batch'),'r5_bms');b=B.Board(SERIAL,self.hdc,str(self.program('lock')),self.auth['holder'],self.logs/'coldstop');b.ready();need(b.boot.strip()==boot,'cleanup boot')
  self.held();_,raw=b.shell('ps -A -o PID,PPID,UID,NAME');remaining=[r for r in B.processes(raw) if r['uid']==p['boat_uid']]
  if remaining:B.cold_stop(b,p['boat_package'],p['boat_uid'],self.logs,tag='rollback')
  _,raw=b.shell('ps -A -o PID,PPID,UID,NAME');need(not [r for r in B.processes(raw) if r['uid']==p['boat_uid']],'Boat consumers remain')
  clean=self.logs/'cleanup.json';save(clean,{'serial':SERIAL,'boot_id':boot,'package':p['boat_package'],'uid':p['boat_uid'],'remaining_processes':[],'success':True})
  retained=[]
  for target in dev.shell('retained-audit','find '+core.q(self.inst.ROOT)+' -maxdepth 1 -type f').splitlines():
   if Path(target).name.startswith(('boat-','cfg-stage-')):
    obs=dev.probe(target);local=self.logs/Path(target).name;dev.recv('retain-audit',target,local);need(sha(local)==obs['sha256'],'audit archive SHA');retained.append(dict(target=target,**obs))
  a={'approved_by':'outer(codex)','plan_sha256':sha(pf),'serial':SERIAL,'origin_boot_id':p['boot_id'],'boot_id':boot,'expires_epoch':self.deadline,'action':'rollback','holder':self.held(),'cleanup_receipt':pin(clean),'retained_audit':retained};af=self.logs/'rollback-authorization.json';save(af,a)
  self.run('rollback',[sys.executable,self.program('installer'),'--plan',pf,'--action','rollback','--execute','--authorization',af,'--authorization-sha256',sha(af),'--out',txn])
  if (self.out/'candidate-boot-intent.json').exists():
   self.preboot('baseline-return');boot=self.reboot('baseline-return-boot',False)
  self.foreground('restored-host',boot);self.r5('restored-r5',boot)
  save(self.out/'closed.json',{'status':'RESTORED_PENDING_VISUAL_REVIEW','serial':SERIAL,'boot_id':boot,'runtime_repaired':False,'candidate_promoted':False})
def main():
 ap=argparse.ArgumentParser();ap.add_argument('phase',choices=['after-lock','before-unlock']);ap.add_argument('--request',type=Path,required=True);ap.add_argument('--authorization',type=Path,required=True);ap.add_argument('--authorization-sha256',required=True);a=ap.parse_args()
 try:
  w=Window(a);getattr(w,a.phase.replace('-','_'))();return 0
 except Exception as e:print('R5 WINDOW REFUSED: '+str(e),file=sys.stderr);return 2
if __name__=='__main__':raise SystemExit(main())
