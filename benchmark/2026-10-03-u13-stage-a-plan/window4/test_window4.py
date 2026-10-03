"""Known answers: the outer's corrected16 protection keys and signed per-board bases."""
import json,unittest,hashlib
from pathlib import Path
H=Path(__file__).resolve().parent;W=H.parents[3];M=W/'westlake-harness'
class Window4(unittest.TestCase):
 def test_authoritative_keys_and_unchanged_admission(self):
  authority=M/'benchmark/2026-10-03-u13-stage-a-plan/window3-signoff/lit-reference-unmeasured.txt';expected=authority.read_text().split();got=[]
  auth=json.loads((H.parent/'outer-window-authorization.json').read_text())
  for b,n in [('5ea',6),('5cd',6),('61b',4)]:
   d=H if b!='61b' else H.parent/'window4-61b-r2';p=json.loads((d/f'plan-{b}.json').read_text());c=json.loads((d/'composition.json').read_text());keys=[]
   for s in p['shards']:keys+=Path(s['keys_file'].replace('$WORKSPACES',str(W))).read_text().split()
   self.assertEqual(len(keys),n);got+=keys
   self.assertEqual(c['approved_unarmed_bundle_sha256'],auth['per_board'][p['serial']]['bundle_sha256']);self.assertEqual(c['base_bundle_sha256'],auth['per_board'][p['serial']]['effective_baseline_bundle_sha256'])
   self.assertEqual(p['window_limit_minutes'],45);self.assertEqual(p['stop_new_tests_by_minute'],35);self.assertTrue(p['restore']['unconditional']);self.assertEqual(p['restore']['identity_assertions'],318);self.assertIn('--finish',p['before_unlock']);self.assertTrue(b=='5ea' or 'after_shards' not in p)
  self.assertCountEqual(got,expected);self.assertEqual(len(set(got)),16)
 def test_actual_manifest_order_and_isolated_seal_continuation(self):
  import importlib.util,sys
  sys.path.insert(0,str(M/'scripts/lab'))
  source=M/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py';spec=importlib.util.spec_from_file_location('known_window4_batch',source);b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
  order=[a['key'] for a in b.load_apps(source.with_name('apps.json'),keys='fd-k9,fd-netguard,fd-seal,fd-organicmaps')]
  self.assertEqual(order,['fd-netguard','fd-k9','fd-organicmaps','fd-seal'])
  d=H.parent/'window4-61b-seal';p=json.loads((d/'plan-61b.json').read_text());self.assertEqual(len(p['shards']),1)
  keypath=Path(p['shards'][0]['keys_file'].replace('$WORKSPACES',str(W)));self.assertEqual(keypath.read_text().split(),['fd-seal'])
  self.assertEqual(p['bundle_sha256'],json.loads((H.parent/'window4-61b-r2/plan-61b.json').read_text())['bundle_sha256']);self.assertTrue(p['restore']['unconditional']);self.assertEqual(p['window_limit_minutes'],30);self.assertEqual(p['stop_new_tests_by_minute'],20)
 def test_fallback_is_exact_identity_and_recorded(self):
  s=(H/'capture_minesweeper.py').read_text();pin=json.loads((H/'minesweeper-identity.json').read_text())
  self.assertIn(pin['apk_sha256'],s);self.assertIn(pin['launch_activity'],s);self.assertIn("launch_method='ability-fallback'",s);self.assertIn("record['bms']['queryable']",s);self.assertIn("capture_clock_origin='aa-start-success-return'",s)
if __name__=='__main__':unittest.main()
