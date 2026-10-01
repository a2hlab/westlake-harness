"""Offline checks of the reviewed safety chain and before_unlock paths."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
from unittest.mock import Mock,patch
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('n11g_hook',H/'window_hook.py');hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(hook)
class Window(unittest.TestCase):
 def test_finish_rollback_precedes_restored_smoke_and_final(self):
  for status in ('active_verified','recovery_required','rolled_back'):
   with self.subTest(status=status),tempfile.TemporaryDirectory() as td:
    root=Path(td);(root/'transaction').mkdir();(root/'transaction/journal.json').write_text(json.dumps({'status':status}));events=[]
    with patch.object(hook,'executor',side_effect=lambda *a,**kw:events.append('rollback')),patch.object(hook,'verify',side_effect=lambda *a:events.append('verify')),patch.object(hook.subprocess,'run',side_effect=lambda *a,**kw:events.append('smoke')):
     hook.finish('61b',root,H/'restored-smoke.json')
    self.assertEqual(events,(['rollback'] if status!='rolled_back' else [])+['verify','smoke','verify'])
 def test_restore_refusal_never_runs_smoke_or_unlock(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'transaction').mkdir();(root/'transaction/journal.json').write_text('{"status":"active_verified"}')
   with patch.object(hook,'executor',side_effect=RuntimeError('restore refused')),patch.object(hook,'verify') as verify,patch.object(hook.subprocess,'run') as run:
    with self.assertRaisesRegex(RuntimeError,'restore refused'):hook.finish('61b',root,H/'restored-smoke.json')
    verify.assert_not_called();run.assert_not_called()
 def test_live_probe_and_one_file_plan(self):
  plan=json.loads((H/'plan-61b.json').read_text());smoke=json.loads((H/'smoke.json').read_text());delta=json.loads((H/'candidate-delta.json').read_text())
  self.assertEqual(plan['serial'],'61b0657200000000000000000324012c');self.assertEqual(plan['window_limit_minutes'],30);self.assertEqual(plan['stop_new_tests_by_minute'],20)
  self.assertEqual(set(delta),{'/system/lib64/appspawn/libwestlake_android_child.z.so'})
  self.assertEqual(set(smoke['probe']['single_copy']),{'libart.so','libopenjdkjvm.so','liboh_adapter_bridge.so','liboh_android_runtime.so'})
  self.assertIn('N11g-SEALED-OPEN',str(smoke['fixes']));self.assertIn('--finish',plan['before_unlock'])
  self.assertTrue(plan['offline_precheck']['expect']['confirm']);self.assertTrue(plan['offline_precheck']['expect']['refute'])
if __name__=='__main__':unittest.main()
