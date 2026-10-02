"""Known-answer binding/delegation checks; no device calls."""
import json,runpy,sys,unittest
from pathlib import Path
from unittest.mock import patch
H=Path(__file__).resolve().parent
sys.path.insert(0,str(H.parent))
import window_hook as hook,dispatch
class WindowConfig(unittest.TestCase):
 def setUp(self):self.old=(hook.H,hook.vm,dispatch.H)
 def tearDown(self):hook.H,hook.vm,dispatch.H=self.old
 def configured(self):
  with patch.object(sys,'argv',[str(H/'runner.py'),'hook']),patch.object(hook,'main') as main:
   runpy.run_path(str(H/'runner.py'),run_name='__main__');main.assert_called_once()
 def test_vm_verifier_keeps_approved_window(self):
  with patch.object(hook,'vm') as vm:
   self.configured();hook.vm(['python3',Path(hook.__file__).resolve(),'--verify-base'])
   self.assertEqual(vm.call_args.args[0],['python3',H/'runner.py','hook','--verify-base'])
 def test_wrong_bundle_rejected_before_apply(self):
  self.configured();p=json.loads((H/'plan-61b.json').read_text());hook.admission(p)
  p['bundle_sha256']='0'*64
  with self.assertRaisesRegex(AssertionError,'bundle drift'):hook.admission(p)
 def test_same_signed_artifacts_and_real_base(self):
  self.configured();c=hook.composition();au=json.loads((H.parent/'outer-window-authorization.json').read_text())
  self.assertEqual(c['approved_unarmed_bundle_sha256'],au['bundle_sha256'])
  self.assertEqual(c['base_bundle_sha256'],au['effective_baseline_bundle_sha256'])
  self.assertEqual(c['native_manifest_sha256'],au['native_manifest_sha256'])
  for name in ['5ea','5cd','61b']:
   p=json.loads((H/f'plan-{name}.json').read_text());hook.admission(p)
   self.assertEqual(p['restore']['identity_assertions'],318);self.assertTrue(p['restore']['unconditional'])
   self.assertEqual(p['window_limit_minutes'],45);self.assertEqual(p['stop_new_tests_by_minute'],35)
if __name__=='__main__':unittest.main()
