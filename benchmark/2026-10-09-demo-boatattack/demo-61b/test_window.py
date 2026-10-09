import importlib.util,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('window_hook.py');s=importlib.util.spec_from_file_location('boat',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
class TransactionTests(unittest.TestCase):
 def test_six_inputs_match(self):m.checked_inputs()
 def test_changed_input_refuses(self):
  with patch.object(m,'sha',return_value='0'*64),self.assertRaisesRegex(RuntimeError,'SHA mismatch'):m.checked_inputs()
 def test_only_owned_top_can_rollback(self):
  x={'attempted':True,'push_root':'/local/tmp/a','sha256':'a'*64};top='1 2 3 /local/tmp/a /target rw - x x x'
  self.assertTrue(m.removable(x,top,'a'*64));self.assertFalse(m.removable(x,top,'b'*64));self.assertFalse(m.removable(x,top.replace('/local/tmp/a','/foreign'),'a'*64));self.assertFalse(m.removable(dict(x,attempted=False),top,'a'*64))
 def test_real_data_mount_root(self):
  with patch.object(m,'command',return_value='1 2 0:1 / / rw - root root rw\n2 1 8:1 / /data rw - x x rw'):
   self.assertEqual(m.push_root(None,'/data/local/tmp/a'),'/local/tmp/a')
 def test_exact_ten_outer_lit_two_games(self):
  import json
  a=json.loads(p.with_name('regression-apps.json').read_text())['apps'];sig=json.loads(p.with_name('selected-signoff.json').read_text());self.assertEqual(len(a),10);self.assertEqual(sum(x['is_game'] for x in a),2);self.assertTrue(all(sig[x['key']]['verdict']=='lit' for x in a))
 def test_regression_never_reinstall(self):
  import json
  a=json.loads(p.with_name('plan.json').read_text());self.assertEqual(a['demo_mode'],'launch');self.assertNotIn('demo_shot_tiers',a);self.assertEqual(a['demo_capture_seconds'],20);self.assertEqual(a['window_limit_minutes'],30)
 def test_restored_groups_get_real_hdc_in_path(self):
  import tempfile,types
  with tempfile.TemporaryDirectory() as tmp,patch.object(m,'OUT',Path(tmp)),patch.object(m.subprocess,'run',return_value=types.SimpleNamespace(returncode=0)) as run:
   self.assertEqual(m.smoke_restore(Path(tmp)/'smoke'),0)
   self.assertEqual(run.call_args.kwargs['env']['PATH'].split(':')[0],str(Path(tmp)/'vm-tools'))
   self.assertTrue((Path(tmp)/'vm-tools/hdc').is_file())
if __name__=='__main__':unittest.main()
