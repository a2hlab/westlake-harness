"""Amend a NEW disabled, freshly rebound window; preserve the original rollback body."""
import argparse,hashlib,json,os
from pathlib import Path
HERE=Path(__file__).resolve().parent
HOOK='b1460782caa7f368e9845bfe761d355297a3bfc7421899342e66bcfc0233a295'
def need(ok,msg):
 if not ok:raise ValueError(msg)
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def resolve(p):return Path(os.path.expandvars(str(p))).resolve()
def pin(p):return dict(path='$WORKSPACES/'+str(resolve(p).relative_to(resolve(os.environ['WORKSPACES']))),sha256=sha(p))
def save(p,d):Path(p).write_text(json.dumps(d,indent=2)+'\n')
AFTER=''' def retain_scope(self):
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
'''
BEFORE=''' def before_unlock(self):
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
'''
STEPS='''  # Root-controlled supplement. No orientation precondition and no synthesized visual PASS.
  steps=out/'steps';steps.mkdir();rec['evidence_group']='root-stepped-experiment';save(out/'record.json',rec)
  commands=dict(TOUCHES)
  for n in range(1,21):
   request=steps/('step-%03d.json'%n)
   rec['status']='WAITING_FOR_ROOT_STEP';rec['next_step']=n;save(out/'record.json',rec)
   while not request.exists():
    need(time.monotonic()<start+plan['max_runtime_seconds'] and (authority is None or time.time()<authority['expires_epoch']),'step experiment deadline reached')
    time.sleep(.1)
   choice=json.loads(request.read_text())
   need(choice.get('approved_by')=='outer(codex)' and choice.get('boot_id')==plan['boot_id'] and choice.get('child')==identity,'root step identity')
   action=choice.get('action');need(action in commands or action=='finish','only existing source-derived commands')
   rec.setdefault('step_requests',[]).append({'index':n,'sha256':sha(request),'choice':choice})
   rec['target_window']=window('step-%d'%n);guard();child_view()
   if action=='finish':
    need(choice.get('disposition') in ('retain','rollback'),'explicit finish disposition')
    rec['experiment_disposition']=choice['disposition'];break
   cmd=commands[action];rc,text=b.shell(cmd,required=False)
   rec['inputs'].append({'index':n,'name':action,'command':cmd,'injection_rc':rc,'response':text,'visual_response':'pending_human'});save(out/'record.json',rec);need(rc==0,'input command failed')
   if action=='reset':time.sleep(2)
   guard();shot('step-%d-after'%n);window('step-%d-after'%n);child_view()
  need('experiment_disposition' in rec,'bounded steps exhausted without root finish')
'''
def build(window):
 window=window.resolve();need(not (window/'run').exists() and not (window/'board-run').exists(),'fresh disabled window only')
 q=read(window/'request.json');bp=read(window/'board-run.disabled.json');a=read(window/'authorization.required.json')
 need(bp['execution_enabled'] is False and a['approved_by'] is None,'never amend authorized window')
 source=resolve(bp['after_lock'][1]);need(sha(source)==HOOK and bp['before_unlock'][1]==bp['after_lock'][1],'exact original window hook')
 src=source.read_text();start=src.index(' def after_lock(self):');end=src.index(' def before_unlock(self):')
 out=window/'retain_hooks.py';need(not out.exists(),'fresh retain hook')
 rollback=src[end:].replace(' def before_unlock(self):',' def rollback_before_unlock(self):',1)
 rollback=rollback.replace("self.out/'closed.json'","self.out/('recovery-closed.json' if (self.out/'closed.json').exists() else 'closed.json')")
 derived=src[:start]+AFTER+BEFORE+rollback
 derived=derived.replace("choices=['after-lock','before-unlock']","choices=['after-lock','before-unlock','recover-retained','verify-recovered']")
 derived=derived.replace("try:w=Window(a);getattr(w,a.phase.replace('-','_'))();return 0","try:\n  requested=a.phase;a.phase='after-lock' if requested=='after-lock' else 'before-unlock'\n  w=Window(a);getattr(w,requested.replace('-','_'))();return 0")
 out.write_text(derived)
 runner=resolve(q['programs']['interaction']['path']);need(sha(runner)=='8c8f89e2216816c2d2a4be452b1367560fb311c0a82a35466ba74682affd6aa1','original runner only')
 r=runner.read_text();lo=r.index('  for n,(name,cmd) in enumerate(TOUCHES,1):');hi=r.index("  child_view();rec['status']='CAPTURED_PENDING_HUMAN'",lo)
 step=window/'interaction_steps.py';step.write_text(r[:lo]+STEPS+r[hi:]);q['programs']['interaction']=pin(step)
 q['programs']['retain_evidence']=pin(HERE/'retain_evidence.py');q['input_pins'] += [pin(source),pin(Path(__file__))]
 q['candidate_smoke']=pin(window/'candidate-smoke.json')['path'];q['retain_smoke_result']=bp['out']+'/smoke/smoke-result.json'
 save(window/'request.json',q)
 for phase in ['after_lock','before_unlock']:bp[phase][1]=pin(out)['path']
 bp['why']='5ea temporary f28 candidate bounded interactive supplement; no promotion; strict947 rollback on any failure'
 bp['offline_precheck']['expect']={'confirm':'coldboot319/7bind/3source and original HW/ZZ; explicit root experimental retain; game PASS still pending','refute':'any missing/failed evidence: original strict947 recovery, no retain'}
 save(window/'board-run.disabled.json',bp)
 recovery=json.loads(json.dumps(bp));recovery['out']=pin(window/'request.json')['path'].rsplit('/',1)[0]+'/recovery-board-run'
 recovery['why']='Explicit retained experiment expiry/FAIL recovery to original947; never batch promotion'
 recovery['smoke_spec']=q['baseline_smoke'];recovery['window_limit_minutes']=10;recovery['stop_new_tests_by_minute']=10
 for key,phase in [('after_lock','recover-retained'),('before_unlock','verify-recovered')]:
  recovery[key][2]=phase;recovery[key]=[x.replace('$R6_AUTH_SHA','$R6_RECOVERY_AUTH_SHA').replace('$R6_AUTH','$R6_RECOVERY_AUTH') for x in recovery[key]]
 save(window/'recovery-board-run.disabled.json',recovery)
 q['recovery_plan']=pin(window/'recovery-board-run.disabled.json');q['input_pins'].append(q['recovery_plan']);q['recovery_smoke_result']=recovery['out']+'/smoke/smoke-result.json'
 save(window/'request.json',q)
 a.update(request_sha256=sha(window/'request.json'),hook_sha256=sha(out),allow_retain=False,retain_scope='bounded-experiment-not-promotion',retain_until_epoch=None,recovery_receipt=None,recovery_watch=dict(registered=False,responsible='outer(codex)',start_by_epoch=None,plan=q['recovery_plan'],registration=None))
 save(window/'authorization.required.json',a)
 save(window/'retain-derivation.json',dict(status='DISABLED_PENDING_FRESH_CAPTURE_AND_EXPERIMENT_AUTH',device_calls=0,donor=pin(source),derived=pin(out),rollback_body_unchanged_except_separate_recovery_receipt_path=True,changed=['original runner: fixed five inputs replaced with bounded root steps using the same commands and guards','experimental retention only; no game PASS or heading precondition','strict original source/snapshot/boot947/319/7bind/HWZZ recovery; explicit recover-retained entry']))
 print(json.dumps(dict(status='DISABLED_RETAIN_PREPARED',hook=pin(out),request=pin(window/'request.json'),device_calls=0)))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--window',type=Path,required=True);a=p.parse_args();build(a.window)
