"""Known final identities, honest real-gate reports and fail-closed observation hooks."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
sys.path.insert(0,str(H));sys.path.insert(0,str(R/'scripts/lab'))
import generation_bundle as gb,u7_executor as u,board_run,window_hook as hook,dispatch
def read(p):return json.loads(Path(p).read_text())
def expand(p):return Path(p.replace('$WORKSPACES',str(W)))
class Final(unittest.TestCase):
 def test_members(self):
  c=read(H/'composition.json');root=expand(c['package']);base=expand(c['base_bundle']);b,m,_=gb.validate(root);old=read(base/'native/package.json')
  self.assertEqual(gb.sha(root/'bundle.json'),c['bundle_sha256']);self.assertEqual(gb.sha(root/'native/package.json'),c['native_manifest_sha256']);self.assertFalse(b['rollout_ready']);self.assertFalse(c['execution_enabled'])
  self.assertEqual(b['runtime_jar']['sha256'],'0482c9b13fbc6ab5bce3902807eb7972736463b772773fde276cae679ce9bd4f')
  self.assertEqual(m['files']['payload/android/framework/adapter-mainline-stubs.jar'],'615b8bbecaa7b07fa27d40d25bd13eb6dfb33e6ec6bc7660bc2fc9aeaff1e610')
  self.assertEqual(m['files']['payload/route/libnativeloader.so'],'2a6ec73fd87239ae90ba6464727649f5a4d73aab7588dda392df8803c2e76c4e');self.assertEqual(m['files']['payload/runtime/appspawn-x'],'2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e')
  self.assertEqual(len(c['new_native_paths']),3);self.assertNotIn('/system/android/lib64/libz.so',c['new_native_paths'])
  for rel in ['payload/route/libart.so','payload/runtime/libwestlake_android_child.z.so','payload/route/libbionic_compat.so','payload/zigzag/libmediandk.so']:self.assertEqual(m['files'][rel],old['files'][rel])
  receipt=u.receipt_check(root,b,m);self.assertEqual(receipt['status'],'verified');self.assertEqual(len(receipt['receipt']['input_jars']),9);self.assertEqual(len(receipt['receipt']['outputs']),27)
  self.assertEqual(gb.sha(expand(receipt['receipt']['build_log'])),receipt['receipt']['build_log_sha256']);self.assertEqual(set(c['deferred_to_U13']),{'N11h-r2','compat-relocation'})
 def test_gates(self):
  c=read(H/'composition.json');classification=read(H/'exception-classification.json');self.assertEqual((classification['identical'],classification['genuinely_new']),(156,1));self.assertEqual(classification['identical_by_gate'],{'N1':53,'N2':103});self.assertFalse(classification['registry_written']);self.assertFalse(classification['apply_used'])
  for s in ['mac','vm']:
   r=read(H/'gates'/s/'summary.json');self.assertEqual(r['bundle_sha256'],c['bundle_sha256']);self.assertEqual(r['native_manifest_sha256'],c['native_manifest_sha256']);self.assertEqual(r['tools'],'PASS');self.assertEqual((r['RB_exit_code'],r['T4b_exit_code'],r['frozen_exit_code']),(0,0,0));self.assertTrue(r['G1']);self.assertTrue(r['G2']);self.assertEqual(r['frozen_composed_violations'],0);self.assertEqual(r['production_dry_run_exit_code'],2);self.assertFalse(r['native_errors']);self.assertEqual(r['native_findings']['N1']['rejected'],53);self.assertEqual(r['native_findings']['N2']['rejected'],104)
   members={x['target']:x for x in r['static_members']}
   for name in ['adapter-mainline-stubs.jar','oh-adapter-runtime.jar']:self.assertEqual(members[gb.FW+name]['status'],'PASS')
   for p in c['new_native_paths']:self.assertEqual(members[p]['status'],'REJECT')
   self.assertEqual(members[u.HOST]['status'],'REVIEW_REQUIRED')
  proposal=read(H/'new-native-admissions-draft.json');self.assertEqual(len(proposal['admissions']),3)
  for row in proposal['admissions']:
   self.assertEqual(row['package_manifest_sha256'],c['native_manifest_sha256']);self.assertEqual(row['sha256'],c['board_changes'][row['target']]['after']);self.assertTrue(all((R/e).is_file() for e in row['evidence']))
 def test_plans(self):
  c=read(H/'composition.json');signed=read(R/'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json');recovery=read(H/'recovery-u101t8.json');allkeys=[];counts=[]
  for short in ['5ea','5cd','61b']:
   p=read(H/('plan-'+short+'.json'));self.assertFalse(p['execution_enabled']);self.assertEqual((p['window_limit_minutes'],p['stop_new_tests_by_minute']),(45,35));self.assertEqual(p['bundle_sha256'],c['bundle_sha256']);self.assertTrue(p['restore']['unconditional']);self.assertEqual(p['restore']['state'],'U10.1T8');self.assertEqual(p['restore']['identity_assertions'],318);self.assertEqual(p['regression_gate']['lit_required'],116);self.assertIsNotNone(board_run.precheck_problem(p['offline_precheck']))
   self.assertIn('--reference',p['pair_sheet_review']['command_prefix']);self.assertIn('--signoff',p['pair_sheet_review']['command_prefix'])
   rec=recovery['boards'][p['serial']];self.assertEqual(len(rec['expected']),316);self.assertEqual(rec['fingerprints'],p['restore']['fingerprints'])
   candidate=c['candidate_boards'][p['serial']];self.assertEqual(candidate['unique_paths'],319);self.assertEqual(candidate['identity_assertions'],321)
   keys=[k for shard in p['shards'] for k in expand(shard['keys_file']).read_text().split()];allkeys+=keys;counts.append(len(keys))
   with patch.object(dispatch.subprocess,'run') as transport:
    with self.assertRaisesRegex(RuntimeError,'REFUSE'):dispatch.prelock(p)
    transport.assert_not_called()
  self.assertEqual(counts,[55,55,56]);self.assertEqual(len(allkeys),len(set(allkeys)));self.assertEqual(set(allkeys),set(signed['keys']));self.assertEqual(sum(signed['keys'][k]['verdict']=='lit' for k in allkeys),116)
 def test_finish_order_and_fail_closed(self):
  calls=[]
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'transaction').mkdir();(root/'transaction/journal.json').write_text('{"status":"active"}')
   with patch.object(hook,'executor',side_effect=lambda *a,**k:calls.append('rollback')),patch.object(hook,'verify',side_effect=lambda *a,**k:calls.append('verify')),patch.object(hook.subprocess,'run',side_effect=lambda *a,**k:calls.append('smoke')):
    hook.finish('61b',root,Path('restored.json'))
   self.assertEqual(calls,['rollback','verify','smoke','verify']);self.assertFalse(read(root/'finish.json')['retained'])
   with patch.object(hook,'executor'),patch.object(hook,'verify',side_effect=RuntimeError('restore mismatch')),patch.object(hook.subprocess,'run') as smoke:
    with self.assertRaisesRegex(RuntimeError,'restore mismatch'):hook.finish('61b',root,Path('restored.json'))
    smoke.assert_not_called()
 def test_admission_never_arms_or_transports(self):
  plan=read(H/'plan-61b.json')
  with patch.object(hook,'vm') as vm:
   with self.assertRaisesRegex(AssertionError,'not enabled'):hook.apply(plan['serial'],Path('unused'),plan)
   vm.assert_not_called()
if __name__=='__main__':unittest.main()
