"""Known answers: report actual t10/t20 liveness without converting missing evidence to death."""
import importlib.util,json,sys,tempfile,unittest
from pathlib import Path
HERE=Path(__file__).resolve().parents[1];sys.path.insert(0,str(HERE))
import run_facts
sp=importlib.util.spec_from_file_location('facts_batch',HERE.parents[1]/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py');batch=importlib.util.module_from_spec(sp);sp.loader.exec_module(batch)
class LastShotFacts(unittest.TestCase):
 def fixture(self,base,seconds,present=True):
  d=base/'key';d.mkdir();(d/'record.json').write_text(json.dumps({'key':'key','bms':{'uid':20012345},'status':'foreground_unconfirmed','screenshots':[{'captured':True,'scheduled_seconds':5},{'captured':True,'scheduled_seconds':seconds}]}))
  ps='PID PPID UID NAME\n123 1 20012345 appspawn-x\n';(d/'processes-t5.txt').write_text(ps)
  if present:(d/f'processes-t{seconds}.txt').write_text(ps)
  return d
 def test_t10_without_t20_is_alive_at_t10(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);f=run_facts.facts(self.fixture(root,10));self.assertTrue(f['alive_t10']);self.assertIsNone(f['alive_t20']);lines,total=run_facts.format_rows([f]);self.assertIn('t10=yes',lines[0]);self.assertIn('alive_t10=1',total);self.assertNotIn('alive_t20=',total)
   batch.write_facts(root);self.assertEqual((root/'facts.txt').read_text().splitlines()[-1],total)
 def test_t20_preserves_existing_liveness(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);f=run_facts.facts(self.fixture(root,20));self.assertTrue(f['alive_t20']);self.assertTrue(f['alive_last']);lines,total=run_facts.format_rows([f]);self.assertIn('t20=yes',lines[0]);self.assertIn('alive_t20=1',total);batch.write_facts(root);self.assertEqual((root/'facts.txt').read_text().splitlines()[-1],total)
 def test_missing_last_process_file_stays_unknown(self):
  with tempfile.TemporaryDirectory() as td:
   f=run_facts.facts(self.fixture(Path(td),10,False));self.assertIsNone(f['alive_last']);lines,total=run_facts.format_rows([f]);self.assertIn('t10=?',lines[0]);self.assertIn('alive_unknown=1',total)
 def test_unrelated_uid_is_not_survival(self):
  with tempfile.TemporaryDirectory() as td:
   d=self.fixture(Path(td),10);(d/'processes-t10.txt').write_text('PID PPID UID NAME\n123 1 20099999 appspawn-x\n');self.assertFalse(run_facts.facts(d)['alive_last'])
 def test_mixed_tiers_have_separate_actual_counts(self):
  with tempfile.TemporaryDirectory() as a,tempfile.TemporaryDirectory() as b:
   rows=[run_facts.facts(self.fixture(Path(a),10)),run_facts.facts(self.fixture(Path(b),20))];_,total=run_facts.format_rows(rows);self.assertIn('alive_t10=1',total);self.assertIn('alive_t20=1',total)
if __name__=='__main__':unittest.main()
