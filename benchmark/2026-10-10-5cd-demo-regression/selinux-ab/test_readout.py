"""Known answers: observed child CANTOPEN, harmless handled signal, no prep writes."""
import importlib.util,json
from pathlib import Path
import tempfile,unittest
HERE=Path(__file__).resolve().parent
def load(name,p):
 s=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
m=load('ab_readout',HERE/'readout.py')
class ReadoutTests(unittest.TestCase):
 def test_handled_signal_is_not_first_fatal(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'record.json').write_text(json.dumps({'key':'a','package':'com.example.a','observed_pids':[],'screenshots':[],'status':'foreground_unconfirmed'}))
   (p/'hilog.txt').write_text('10-10 18:00:00.000 877 8 I AppMS: spawned pname_com.example.a, pid_42, idx_0\n10-10 18:00:01.000 42 43 E SQLite: SQLITE_CANTOPEN\n10-10 18:00:02.000 42 43 W MUSL-SIGCHAIN: signal_chain_handler action for signal: 11\n10-10 18:00:03.000 99 9 E App: JniAbort unrelated\n10-10 18:00:04.000 42 43 I Java: J_invokeStaticMain_main_threw: cause\n10-10 18:00:05.000 877 8 W WMSMain: add failed. Main/com.example.a/entry/0 already existed in array\n10-10 18:00:06.000 877 8 W WMSMain: add failed. Main/com.other/entry/0 already existed in array\n')
   r=m.analyze(p/'record.json');self.assertEqual(r['target_pids'],[42]);self.assertEqual(r['target_cantopen_log_lines'],1);self.assertEqual(r['first_fatal']['line'],5);self.assertEqual(r['wms_already_existed_log_lines'],2);self.assertEqual(r['target_wms_already_existed_log_lines'],1)
 def test_unlaunched_zero_is_unknown(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'record.json').write_text(json.dumps({'key':'a','package':'com.example.a','status':'app_failed','screenshots':[]}));r=m.analyze(p/'record.json');self.assertEqual(r['target_cantopen_log_lines'],0);self.assertTrue(r['fatal_unknown']);self.assertEqual(r['target_pids'],[])
 def test_prep_wrapper_issues_no_board_write(self):
  from unittest.mock import Mock
  wrapper=load('readonly_prep',HERE/'batch_readonly_prep.py');board=Mock()
  with tempfile.TemporaryDirectory() as t:
   receipt=wrapper.unchanged_sandbox(board,'com.example.a',20010101,Path(t));record={};wrapper.unchanged_sidecars(board,{'native_sidecars':[{'name':'x'}]},'/remote',Path(t),record);self.assertEqual(receipt['status'],'not_modified');self.assertEqual(board.mock_calls,[])
 def test_existing_real_child_answer(self):
  paths=list((HERE/'window2').glob('enforcing-*/*/*/fd-uhabits/record.json'))
  if not paths:self.skipTest('large runtime evidence not bundled')
  r=m.analyze(paths[0]);self.assertEqual(r['target_cantopen_log_lines'],5);self.assertIn('J_invokeStaticMain_main_threw',r['first_fatal']['text'])
if __name__=='__main__':unittest.main()
