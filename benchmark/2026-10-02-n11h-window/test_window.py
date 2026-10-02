import copy,importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;sys.path.insert(0,str(H));import prepare as c,window_hook as hook,dispatch
sys.path.insert(0,str(c.R/'scripts/lab'));import board_run
class WindowTests(unittest.TestCase):
 def transaction_fixture(self):
  spec=importlib.util.spec_from_file_location('u7_transaction_fixture',c.R/'benchmark/2026-10-01-u7-executor/test_executor.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
  old,fp,paths=hook.identity();new,_,_=hook.identity(True)
  plan={'root':str(c.PKG),'generation':hook.composition()[1]['generation'],'baseline':old,'expected':new,'additions':[],'changes':[{'source':'payload/runtime/appspawn-x','target':c.u.HOST,'sha256':c.NEW}],'reference_paths':paths}
  return plan,m.Fake(plan)
 def test_actual_journal_single_host_and_exact_rollback(self):
  plan,io=self.transaction_fixture()
  with tempfile.TemporaryDirectory() as td:
   tx=c.u.Transaction(io,Path(td)/'journal.json',plan);tx.apply()
   self.assertEqual([x for x in io.log if isinstance(x,tuple)],[('bind',c.u.HOST)])
   self.assertEqual(len(tx.state['operations']),1)
   tx.rollback();self.assertEqual(io.values,plan['baseline']);self.assertEqual(io.stack,io.original)
   self.assertEqual(tx.state['status'],'rolled_back')
 def test_lost_bind_reply_restores_current_base(self):
  plan,io=self.transaction_fixture();io.fail=('after',1)
  with tempfile.TemporaryDirectory() as td:
   tx=c.u.Transaction(io,Path(td)/'journal.json',plan)
   with self.assertRaisesRegex(RuntimeError,'lost bind response'):tx.apply()
   self.assertEqual(io.values,plan['baseline']);self.assertEqual(tx.state['status'],'rolled_back')
 def test_dirty_base_no_bind_or_service_stop(self):
  plan,io=self.transaction_fixture();io.values[c.u.HOST]='1d3b0881-U9-is-wrong'
  with tempfile.TemporaryDirectory() as td:
   tx=c.u.Transaction(io,Path(td)/'journal.json',plan)
   with self.assertRaisesRegex(RuntimeError,'full identity mismatch'):tx.apply()
   self.assertEqual(io.log,[])
 def test_real_single_member_and_aliases(self):
  d,m,source=hook.composition();self.assertEqual(source,'payload/runtime/appspawn-x')
  self.assertEqual(d['changed_members'],['/system/bin/appspawn-x'])
  self.assertEqual(c.u.effective_files(m)[c.u.HOST]['sha256'],c.NEW)
 def test_current_promoted_identity_not_u9(self):
  base,fp,paths=hook.identity();candidate,newfp,_=hook.identity(True)
  self.assertEqual(len(base),316);self.assertEqual(fp['runtime']['sha256_12'],'d6848fa2c989')
  self.assertEqual(fp['boot']['sha256_12'],'e3806b65a079')
  self.assertEqual({p for p in base if base[p]!=candidate[p]},{c.u.HOST})
  self.assertEqual(c.u.fingerprints(candidate,paths),newfp)
 def test_bad_live_alias_refused(self):
  _,good,_=hook.composition();old=json.loads((c.BASE/'native/package.json').read_text());bad=copy.deepcopy(good)
  bad['live_hashes'][c.u.HOST]=c.OLD
  with self.assertRaises(ValueError):c.u.native.validate_replacement(old,bad,c.u.HOST)
 def test_plan_no_placeholders_or_wrong_base(self):
  plan=json.loads((H/'plan-61b.json').read_text());self.assertFalse(plan['execution_enabled'])
  self.assertEqual(plan['stop_new_tests_by_minute'],20);self.assertEqual(plan['window_limit_minutes'],30)
  self.assertNotIn('FILL_',json.dumps(plan));self.assertIsNone(board_run.precheck_problem(plan['offline_precheck']))
  self.assertEqual(plan['expect']['base_runtime_fp'],'d6848fa2c989')
 def test_scope_and_budget_evidence(self):
  inventory=json.loads((H/'key-inventory.json').read_text());self.assertEqual(len(inventory['asset_observations']),7)
  self.assertTrue(set(inventory['asset_observations'])<=set(inventory['keys']))
  self.assertIn('fd-fennec_fdroid',inventory['keys'])
  plan=json.loads((H/'plan-61b.json').read_text())
  for shard in plan['shards']:
   keys=Path(board_run.expand(shard['keys_file'])).read_text().splitlines();self.assertTrue(keys);self.assertTrue(all('#' not in k and ' ' not in k for k in keys))
 def test_conditional_marker_not_hard_gate(self):
  smoke=json.loads((H/'smoke.json').read_text());self.assertEqual(len(smoke['fixes']),2)
  self.assertEqual(smoke['probe']['expect_copies']['liboh_android_runtime.so'],1)
  self.assertTrue(all(p.startswith('/system/') for p in smoke['probe']['files']))
  restored=json.loads((H/'restored-smoke.json').read_text());self.assertEqual(restored['probe']['files'][c.u.HOST],c.OLD)
  self.assertEqual(restored['probe']['expect_copies']['liboh_android_runtime.so'],2)
 def test_disabled_no_infra_or_lock(self):
  plan=json.loads((H/'plan-61b.json').read_text())
  with patch('subprocess.run') as run:
   with self.assertRaises(AssertionError):dispatch.prelock(plan,H/'unused')
   run.assert_not_called()
 def test_failure_keeps_recovery_lock(self):
  calls=[]
  def run(argv,**kw):
   calls.append(argv);return type('Result',(),{'stdout':'cx-t0 pid'})()
  with patch('subprocess.run',side_effect=run),patch.object(hook,'vm',side_effect=RuntimeError('UID/PPID guard refused')):
   with self.assertRaises(RuntimeError):dispatch.cleanup_before_experiment('board',H/'unused')
  self.assertFalse(any('unlock' in call for call in calls))
 def test_auto_identical_real_reports(self):
  rows=json.loads((H/'registry-delta.json').read_text())['exceptions'];self.assertEqual(len(rows),156)
  self.assertEqual(sum(r['gate']=='N1' for r in rows),53);self.assertEqual(sum(r['gate']=='N2' for r in rows),103)
  d=hook.composition()[0];self.assertTrue(all(r['package_manifest_sha256']==d['package_manifest_sha256'] and r['inputs_sha256']==d['inputs_sha256'] for r in rows))
if __name__=='__main__':unittest.main()
