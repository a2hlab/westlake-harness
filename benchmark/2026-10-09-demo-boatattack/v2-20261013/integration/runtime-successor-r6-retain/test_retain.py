import contextlib,importlib.util,io,json,os,subprocess,sys,tempfile,time,types,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;WS=next(p for p in H.parents if (p/'westlake-harness').is_dir());os.environ['WORKSPACES']=str(WS)
def load(path,name):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
P=load(H/'prepare_retain.py','prepare_retain');E=load(H/'retain_evidence.py','retain_evidence');S=load(H/'step.py','step')
W=H/'window-reviewed-disabled';M=load(W/'retain_hooks.py','retain_hooks')
class Tests(unittest.TestCase):
 def test_actual_cli_preview_and_exact_donor_preservation(self):
  r=subprocess.run([sys.executable,str(W/'interaction_steps.py'),'--plan',str(W/'interaction.plan.disabled.json'),'--out',str(W/'never-executed')],capture_output=True,text=True)
  self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['board_commands'],0)
  original=(W/'interaction_runner.py').read_text();actual=(W/'interaction_steps.py').read_text();lo=original.index('  for n,(name,cmd) in enumerate(TOUCHES,1):');hi=original.index("  child_view();rec['status']='CAPTURED_PENDING_HUMAN'",lo)
  self.assertEqual(actual,original[:lo]+P.STEPS+original[hi:]);self.assertNotIn('WATER_FACING_COURSE',actual)
  donor=(H/'derived-14a4/window_hooks.py').read_text();body=donor[donor.index(' def before_unlock(self):'):donor.index('def main():')]
  body=body.replace(' def before_unlock(self):',' def rollback_before_unlock(self):',1).replace("self.out/'closed.json'","self.out/('recovery-closed.json' if (self.out/'closed.json').exists() else 'closed.json')")
  self.assertIn(body,(W/'retain_hooks.py').read_text())
 def test_real_smoke_shape_and_failed_child_view(self):
  source=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/board-run/smoke/smoke-result.json';d=E.read(source)
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'smoke.json';p.write_text(json.dumps(d));E.smoke(p,d['spec'],0)
   d['probe']['view']['/system/android/lib64/liboh_android_runtime.so']='947';p.write_text(json.dumps(d))
   with self.assertRaisesRegex(ValueError,'f28 child'):E.smoke(p,d['spec'],0)
 def test_step_publish_exact_identity_no_overwrite(self):
  with tempfile.TemporaryDirectory() as t,contextlib.redirect_stdout(io.StringIO()):
   p=Path(t);(p/'steps').mkdir();r=p/'record.json';r.write_text(json.dumps(dict(status='WAITING_FOR_ROOT_STEP',evidence_group='root-stepped-experiment',next_step=1,boot_id='actual',child={'pid':42,'birth':99})))
   S.build(r,'left');self.assertFalse(list((p/'steps').iterdir()))
   S.build(r,'left',write=True);d=json.loads((p/'steps/step-001.json').read_text());self.assertEqual(d['child'],{'pid':42,'birth':99});self.assertEqual(d['action'],'left')
   with self.assertRaises(FileExistsError):S.build(r,'right',write=True)
 def test_retain_failure_runs_actual_original_rollback_order(self):
  with tempfile.TemporaryDirectory() as t:
   w=M.Window.__new__(M.Window);w.out=Path(t);tx=w.out/'transaction';tx.mkdir();(tx/'intent-000.json').write_text('{}');(tx/'transaction.json').write_text('{}');(w.out/'candidate-boot-intent.json').write_text('{}')
   w.auth={'allow_retain':False};w.deadline=time.time()+600;w.inst=types.SimpleNamespace(OLD='947');w.q={'baseline_smoke':'/fixture/smoke'};w.auth['holder']='outer(codex)';events=[]
   w.action=lambda action:events.append(action);w.preboot=lambda tag:events.append(tag);w.reboot=lambda *a:events.append('boot947');w.verify=lambda *a,**kw:events.append('verify947');w.program=lambda key:'/fixture/'+key;w.run=lambda *a,**kw:events.append('hwzz')
   w.before_unlock();self.assertEqual(events,['rollback','baseline-return','boot947','verify947','hwzz']);self.assertTrue(M.read(w.out/'closed.json')['success'])
 def test_no_intent_and_later_recovery_receipt_preserved(self):
  with tempfile.TemporaryDirectory() as t:
   w=M.Window.__new__(M.Window);w.out=Path(t);w.auth={'allow_retain':False};w.deadline=time.time()+600;w.inst=types.SimpleNamespace(OLD='947');seen=[]
   w.verify=lambda *a,**kw:seen.append(kw);w.before_unlock();self.assertEqual(seen,[{'worker':False}])
   self.assertEqual(M.read(w.out/'closed.json')['reboots'],0)
   old=(w.out/'closed.json').read_bytes();w.rollback_before_unlock();self.assertEqual((w.out/'closed.json').read_bytes(),old);self.assertTrue((w.out/'recovery-closed.json').exists())
 def test_experiment_retain_is_not_game_or_batch_pass(self):
  with tempfile.TemporaryDirectory(dir=H) as t:
   w=M.Window.__new__(M.Window);w.out=Path(t);tx=w.out/'transaction';tx.mkdir();(w.out/'boat').mkdir()
   def put(p,x):p.write_text(json.dumps(x))
   w.reqpath=w.out/'request.json';put(w.reqpath,{})
   put(w.out/'retain-ready.json',dict(success=True,request_sha256=M.sha(w.reqpath),boot_id='candidate'))
   put(w.out/'boat/record.json',dict(status='CAPTURED_PENDING_HUMAN',experiment_disposition='retain'))
   put(w.out/'plan.enabled.json',{});put(tx/'placed.json',{'state':'PLACED_ONLY'})
   put(tx/'transaction.json',dict(plan_sha256=M.sha(w.out/'plan.enabled.json'),boot_id='origin',serial=M.SERIAL))
   for i in range(3):
    for name in ['intent','placed']:put(tx/('%s-%03d.json'%(name,i)),{})
   put(tx/'source-apply-1.json',{})
   actual=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-experiment-main/board-run/smoke/smoke-result.json'
   w.q=dict(retain_smoke_result=str(actual),candidate_smoke=E.read(actual)['spec'],plan={},programs={'installer':{}})
   w.plan=dict(boot_id='origin',candidate_runtime_sha256=E.RUNTIME);now=time.time();w.deadline=now+600
   w.auth=dict(allow_retain=True,retain_scope='bounded-experiment-not-promotion',retain_until_epoch=now+200,experiment_expires_epoch=now+300,started_epoch=0,rollback_expires_epoch=now+900,holder='outer(codex)')
   reg=w.out/'registration.json';put(reg,dict(registered=True))
   w.q['recovery_plan']=E.pin(reg);w.auth['recovery_watch']=dict(registered=True,responsible='outer(codex)',start_by_epoch=now+200,plan=w.q['recovery_plan'],registration=E.pin(reg));w.checkpin=lambda ref: E.resolve(ref['path'])
   w.boot_id=lambda:'candidate';w.program=lambda key:str(H/'retain_evidence.py');w.verify=lambda *a,**kw:put(w.out/'retain-final.json',dict(success=True))
   w.rollback_before_unlock=lambda:self.fail('unexpected rollback')
   w.before_unlock();r=E.read(w.out/'retained.json');self.assertFalse(r['game_pass']);self.assertEqual(r['status'],'BOUNDED_EXPERIMENT_NOT_PROMOTED');self.assertIn('pending',r['full337_admission']);self.assertEqual(w.deadline,now+600)
 def test_zero_reserve_and_unregistered_watch_refuse(self):
  w=M.Window.__new__(M.Window);now=time.time();w.auth=dict(allow_retain=True,retain_scope='bounded-experiment-not-promotion',retain_until_epoch=now+900,experiment_expires_epoch=now+900,rollback_expires_epoch=now+900)
  with self.assertRaisesRegex(ValueError,'ten-minute'):w.retain_scope()
  w.auth.update(retain_until_epoch=now+300,recovery_watch={'registered':False})
  with self.assertRaisesRegex(ValueError,'registered recovery'):w.retain_scope()
if __name__=='__main__':unittest.main()
