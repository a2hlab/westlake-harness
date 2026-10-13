"""Actual5cd captured plan; no transport. Narrow delta tests only."""
import ast,copy,hashlib,json,os,subprocess,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parent
os.environ.setdefault('WORKSPACES',str(next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file()).parent))
sys.path.insert(0,str(HERE/'provider'))
import installer,candidate_contract as c
OLD=HERE.parent/'final-v2-rehearsal-5cd/provider'
class Tests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  import prepare
  cls.temp=tempfile.TemporaryDirectory();cls.package=Path(cls.temp.name)/'package';cls.plan=prepare.build(c.resolve('$WORKSPACES/westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/5cd-v2-postinstall-capture/capture.json'),cls.package)
 @classmethod
 def tearDownClass(cls):cls.temp.cleanup()
 def test_actual_10_6_preserves_stock_and_full_routeb(self):
  installer.validate(self.plan,installer.core_for(self.plan))
  self.assertEqual((len(self.plan['members']),len(self.plan['binds']),len(self.plan['preserved'])),(10,6,496))
  self.assertFalse(self.plan['execution_enabled']);self.assertEqual(self.plan['boat_uid'],20011301)
  self.assertNotIn(c.RUNTIME,{r['target'] for r in self.plan['binds']})
  self.assertEqual(next(r for r in self.plan['preserved'] if r['target']==c.RUNTIME)['before']['sha256'],c.STOCK_RUNTIME)
 def test_runtime_or_routeb_omission_rejected(self):
  for target in [c.RUNTIME,next(iter(c.protected()))]:
   plan=copy.deepcopy(self.plan);plan['preserved']=[r for r in plan['preserved'] if r['target']!=target]
   with self.assertRaises(ValueError):installer.validate(plan,installer.core_for(plan))
 def test_947_or_seventh_bind_rejected(self):
  old=c.read(OLD/'r4-reference/plan.disabled.json')
  plan=copy.deepcopy(self.plan);plan['binds'].append(next(r for r in old['binds'] if r['target']==c.RUNTIME))
  with self.assertRaises(ValueError):installer.validate(plan,installer.core_for(plan))
  plan=copy.deepcopy(self.plan);next(r for r in plan['preserved'] if r['target']==c.RUNTIME)['before']['sha256']='94718e0d0b617a0f9a860e0b50b879b0d7d4639f32e8230b1f90f8e26e2c1354'
  with self.assertRaises(ValueError):installer.validate(plan,installer.core_for(plan))
 def test_rollback_logic_original_AST(self):
  def fn(p,n):return next(x for x in ast.parse(p.read_text()).body if isinstance(x,ast.FunctionDef) and x.name==n)
  for name in ['rollback_preflight','rollback','no_consumers','audit_rows','audit_verify']:
   a,b=fn(OLD/'installer.py',name),fn(HERE/'provider/installer.py',name)
   for tree in [a,b]:
    if isinstance(tree.body[0],ast.Expr) and isinstance(tree.body[0].value,ast.Constant) and isinstance(tree.body[0].value.value,str):tree.body.pop(0)
   self.assertEqual(ast.dump(a),ast.dump(b),name)
 def test_worker_guards_and_shell_syntax(self):
  old=(OLD/'r4-reference/worker.sh').read_text();new=(HERE/'prepared-disabled/worker.sh').read_text()
  self.assertEqual(old.count('    no_parent'),new.count('    no_parent'))
  for token in ['SELF_MOUNT_NS_READ','INIT_MOUNT_NS_READ','NOT_INIT_MOUNT_NS','PREIMAGE_$n','PRE_BIND_DRIFT_$n','ALREADY_ATTEMPTED_THIS_BOOT','OWNER_$n']:
   self.assertIn(token,new)
  self.assertEqual(new.count(c.STOCK_RUNTIME),2);self.assertIn('layers=6',new)
  self.assertEqual(subprocess.run(['sh','-n',str(HERE/'prepared-disabled/worker.sh')]).returncode,0)
 def test_real_cli_preview_and_disabled_execution_refusal(self):
  args=[sys.executable,str(HERE/'provider/installer.py'),'--plan',str(self.package/'plan.disabled.json')]
  r=subprocess.run(args,capture_output=True,text=True);self.assertEqual(r.returncode,0,r.stderr)
  self.assertEqual(json.loads(r.stdout)['boot_binds'],6)
  r=subprocess.run(args+['--execute'],capture_output=True,text=True);self.assertEqual(r.returncode,2);self.assertIn('disabled/synthetic/incomplete plan',r.stderr)
 def test_concrete_boardrun_hooks_and_coordinates(self):
  import importlib.util
  r=HERE/'interaction_runner.py';spec=importlib.util.spec_from_file_location('interaction_test',r);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  self.assertEqual(m.SERIALS,{c.SERIAL});self.assertEqual(len(m.ASSETS),7)
  self.assertIn('1794 1074',m.TOUCHES[0][1]);self.assertIn('154 1046 49 1046',m.TOUCHES[1][1]);self.assertIn('154 1046 259 1046',m.TOUCHES[3][1]);self.assertIn('1584 1074',m.TOUCHES[4][1])
  self.assertIn("[(3,'t3'),(6,'t9'),(6,'t15'),(15,'ready')]",r.read_text())
  bp=c.read(HERE/'window-disabled/board-run.disabled.json');self.assertEqual(bp['shards'],[])
  self.assertIn('after-lock',bp['after_lock']);self.assertIn('before-unlock',bp['before_unlock']);self.assertFalse(bp['execution_enabled'])
 def test_unauthorized_hook_zero_runner_calls(self):
  import importlib.util
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('window_hooks_test',HERE/'window_hooks.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  class A:pass
  a=A();a.request=HERE/'window-disabled/request.json';a.authorization=HERE/'window-disabled/authorization.required.json';a.authorization_sha256=m.sha(a.authorization);a.phase='after-lock'
  with patch.object(m.subprocess,'run',side_effect=AssertionError('no subprocess before valid approval')):
   with self.assertRaises(ValueError):m.Window(a)
 def test_no_placement_recovers_foreground_then_R5(self):
  import importlib.util
  from unittest.mock import Mock
  spec=importlib.util.spec_from_file_location('window_cleanup_test',HERE/'window_hooks.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as t:
   w=m.Window.__new__(m.Window);w.out=Path(t);events=[];w.boot_id=lambda:'actual-current-boot';w.foreground=lambda tag,boot:events.append('foreground');w.r5=lambda tag,boot:events.append('r5')
   w.before_unlock();self.assertEqual(events,['foreground','r5']);self.assertTrue(m.read(w.out/'no-placement.json')['original940_passed'])
 def test_expired_experiment_still_admits_reserved_cleanup(self):
  import importlib.util,time
  from unittest.mock import patch
  spec=importlib.util.spec_from_file_location('window_deadline_test',HERE/'window_hooks.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  with tempfile.TemporaryDirectory() as t:
   q=m.read(HERE/'window-disabled/request.json');q['out']=t+'/run';qp=Path(t)/'request.json';m.save(qp,q)
   a=m.read(HERE/'window-disabled/authorization.required.json');now=time.time();a.update(approved_by='outer(codex)',request_sha256=m.sha(qp),started_epoch=now-1201,experiment_expires_epoch=now-1,rollback_expires_epoch=now+599,stop_new_tests_epoch=now-1,allow_candidate_boot=True,allow_rollback_boot=True);a['static_review']['accepted']=True
   ap=Path(t)/'synthetic-authorization.json';m.save(ap,a)
   class Args:pass
   args=Args();args.request=qp;args.authorization=ap;args.authorization_sha256=m.sha(ap);args.phase='after-lock'
   with patch.object(m.Window,'held'),patch.object(m.subprocess,'run',side_effect=AssertionError('no external command in offline test')):
    with self.assertRaises(ValueError):m.Window(args)
    args.phase='before-unlock';w=m.Window(args);self.assertEqual(w.deadline,a['rollback_expires_epoch'])
 def test_all_five_actual_input_resolutions(self):
  r=c.read(HERE/'window-disabled/resolve-inputs.json');self.assertEqual(len(r['results']),5);self.assertTrue(all(x['rc']==0 for x in r['results']));self.assertEqual(r['device_calls'],0)
if __name__=='__main__':unittest.main(verbosity=2)
