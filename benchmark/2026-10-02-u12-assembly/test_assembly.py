#!/usr/bin/env python3
"""Known-answer identities, coverage and fail-closed draft checks; no board transport."""
import copy,hashlib,json,os,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];W=R.parent
os.environ.setdefault('WORKSPACES',str(W));sys.path[:0]=[str(H),str(R/'scripts/lab')]
import draft_guard,board_run,generation_bundle as gb,u7_executor as u,installation_chain

def read(p):return json.loads(Path(p).read_text())
class Tests(unittest.TestCase):
 def test_native(self):
  c=read(H/'composition.json');root=Path(c['package'].replace('$WORKSPACES',str(W)));base=Path(c['base_bundle'].replace('$WORKSPACES',str(W)))
  self.assertEqual(c['bundle_sha256'],gb.sha(root/'bundle.json'));self.assertEqual(c['native_manifest_sha256'],gb.sha(root/'native/package.json'))
  d,m,_=gb.validate(root);old=read(base/'native/package.json');self.assertFalse(d['rollout_ready']);self.assertFalse(m['rollout_ready']);self.assertTrue(c['pending'])
  self.assertEqual(len(c['board_changes']),4);self.assertEqual([p for p,v in c['board_changes'].items() if v['before'] is None],['/system/android/lib64/libmediandk.so'])
  self.assertEqual(m['files']['payload/zigzag/libmediandk.so'],old['files']['payload/zigzag/libmediandk.so'])
  self.assertEqual(m['files']['payload/route/libnativeloader.so'],m['files']['payload/android/lib64/libnativeloader.so'])
  for k,r in c['inputs'].items():self.assertEqual(gb.sha(Path(r['path'].replace('$WORKSPACES',str(W)))),r['sha256'])
  classification=read(H/'exception-classification.json');self.assertEqual(classification['identical'],{'N1':53,'N2':103});self.assertEqual(classification['genuinely_new'],{'N1':0,'N2':0});self.assertTrue(classification['N2_all_103_identical']);self.assertFalse(classification['registry_written'])
  for surface in ['mac','vm']:
   report=read(H/'gates'/surface/'summary.json');self.assertEqual(report['tools'],'PASS');self.assertTrue(report['G1']);self.assertTrue(report['G2']);self.assertEqual(report['frozen_exit_code'],0);self.assertEqual(report['production_dry_run_exit_code'],2);self.assertEqual(report['native_manifest_sha256'],c['native_manifest_sha256']);self.assertFalse(report['native_errors'])
   self.assertEqual([(r['target'],r['status']) for r in report['static_members'] if r['status']!='PASS'],[('/system/android/lib64/libmediandk.so','REJECT')])
  artifacts={r['name']:r for r in read(H/'artifact-checks.json')};self.assertEqual(artifacts['libicu_jni.so']['exports'],63);self.assertFalse(artifacts['libicu_jni.so']['removed_exports']);self.assertFalse(artifacts['libnativeloader.so']['removed_exports']);self.assertEqual(artifacts['libmediandk.so']['dynamic']['needed'],['libc.so']);self.assertEqual(artifacts['libmediandk.so']['exports'],52)
 def test_plans(self):
  c=read(H/'composition.json');restore=read(H/'recovery-u101t8.json');coverage=read(H/'key-coverage.json');signed=read(R/'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json');self.assertEqual(len(coverage),166);self.assertEqual({r['key'] for r in coverage},set(signed['keys']));self.assertEqual(sum(r['baseline_verdict']=='lit' for r in coverage),116)
  expected_fp={'5ea':('f3b604c94df4','c29c4b415fe5'),'5cd':('f3b604c94df4','c29c4b415fe5'),'61b':('d6848fa2c989','58090b2982a7')};counts=[];all_keys=[]
  plan_preview=read(H/'prepare-plan.json');runtime=sorted(set(plan_preview['reference_paths']['runtime'])|set(installation_chain.PATHS))
  for short in ['5ea','5cd','61b']:
   p=read(H/('plan-'+short+'.json'));self.assertFalse(p['execution_enabled']);self.assertFalse(p['rollout_ready']);self.assertEqual((p['window_limit_minutes'],p['stop_new_tests_by_minute']),(45,35));self.assertIn('pending-final-artifacts-and-admission',board_run.precheck_problem(p['offline_precheck']));self.assertTrue(p['restore']['unconditional']);self.assertEqual(p['restore']['state'],'U10.1T8');self.assertEqual(p['restore']['identity_assertions'],318);self.assertEqual(p['regression_gate']['lit_required'],116);self.assertEqual(p['regression_gate']['minimum_trials_per_side'],3)
   base=restore['boards'][p['serial']];self.assertEqual(len(base['expected']),316);self.assertEqual(u.fingerprints(base['expected'],{'runtime':runtime,'boot':plan_preview['reference_paths']['boot']}),base['fingerprints']);self.assertEqual(base['fingerprints']['runtime']['sha256_12'],expected_fp[short][0]);candidate=c['candidate_boards'][p['serial']];self.assertEqual(candidate['fingerprints']['runtime']['sha256_12'],expected_fp[short][1]);self.assertEqual(candidate['fingerprints']['runtime']['files'],124);self.assertEqual(candidate['fingerprints']['boot']['sha256_12'],'e3806b65a079')
   keys=[]
   for shard in p['shards']:keys+=Path(shard['keys_file'].replace('$WORKSPACES',str(W))).read_text().splitlines()
   counts.append(len(keys));all_keys+=keys
   with self.assertRaisesRegex(ValueError,'DRAFT_REFUSED'):draft_guard.check(p)
   forced=copy.deepcopy(p);forced.update(execution_enabled=True,rollout_ready=True,pending=[])
   with self.assertRaisesRegex(ValueError,'hook has not been bound'):draft_guard.check(forced)
  self.assertEqual(counts,[55,55,56]);self.assertEqual(len(all_keys),len(set(all_keys)));self.assertEqual(set(all_keys),set(signed['keys']))
if __name__=='__main__':unittest.main()
