"""The isolated window configuration delegates to reviewed hooks, never a board fixture."""
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
 def test_config_keeps_reviewed_repository(self):
  old_repo=hook.R;self.configured();self.assertEqual(hook.H,H);self.assertEqual(dispatch.H,H);self.assertEqual(hook.R,old_repo)
  c=hook.composition();self.assertEqual(c['native_manifest_sha256'],'2a3fac8153e080f509cd0949bc521e5e9d81ec37937c312689fb1fec2b1494df')
  self.assertEqual(c['approved_unarmed_bundle_sha256'],'bf6c0fb67d76f1f1d54725738b78f58d24483ceeac66087e2e801d74d1b650ee')
 def test_vm_verifier_keeps_window_configuration(self):
  with patch.object(hook,'vm') as vm:
   self.configured();hook.vm(['python3',Path(hook.__file__).resolve(),'--verify-base'])
   self.assertEqual(vm.call_args.args[0],['python3',H/'runner.py','hook','--verify-base'])
 def test_original_offline_evidence_stays_unarmed(self):
  original=json.loads((H.parent/'composition.json').read_text());self.assertFalse(original['rollout_ready']);self.assertFalse(original['execution_enabled'])
  self.assertEqual(original['bundle_sha256'],'bf6c0fb67d76f1f1d54725738b78f58d24483ceeac66087e2e801d74d1b650ee')
if __name__=='__main__':unittest.main()
