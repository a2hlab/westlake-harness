import copy,json,tempfile,unittest
from pathlib import Path
import candidate_identity as c
from absence_reader import decode
import test_candidate as fixtures

class R4Delta(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  fixtures.CandidateTests.setUpClass();cls.proof=fixtures.CandidateTests.proof
 @classmethod
 def tearDownClass(cls):fixtures.CandidateTests.tearDownClass()
 def test_r4_actual_members(self):
  e=c.validate(self.proof);self.assertEqual(len(e),337)
  self.assertEqual(e[c.OWN+'/worker.sh'],'3f1a464338ce5b2f4c4d93ed0dc0db9c5fdf52c1e3156fae4d7e9e056b6898c2')
  self.assertEqual(e[c.CFG],'897f9ca073c0396c47c681860a601aaa14ba812c63b083711d7e386785e1a762')
  self.assertNotIn(c.ROUTEB,e)
 def test_stock_cannot_pass_candidate_gate(self):
  d=copy.deepcopy(self.proof);d['expected'][c.RUNTIME]=c.read(c.BASE)['expected'][c.RUNTIME];d['generation_sha256']=c.generation(d)
  with self.assertRaises(ValueError):c.validate(d)
 def test_old_libandroid_cannot_pass(self):
  d=copy.deepcopy(self.proof);d['expected'][c.ANDROID]=c.read(c.BASE)['expected'][c.ANDROID];d['generation_sha256']=c.generation(d)
  with self.assertRaises(ValueError):c.validate(d)
 def test_missing_libandroid_durable_source_rejected(self):
  d=copy.deepcopy(self.proof);target=c.OWN+'/sources/libandroid.so'
  d['additional_files']=[r for r in d['additional_files'] if r['target']!=target];del d['expected'][target];d['generation_sha256']=c.generation(d)
  with self.assertRaises(ValueError):c.validate(d)
 def test_old_r3_schema_rejected(self):
  d=copy.deepcopy(self.proof);d['schema']='boat-candidate-identity/v3'
  with self.assertRaisesRegex(ValueError,'schema'):c.validate(d)
 def test_smoke10_actual_t20_preparation(self):
  import contextlib,io
  from prepare_smoke10 import prepare
  with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
   out=Path(tmp)/'smoke';proof_path=fixtures.CandidateTests.out/'compiled/candidate-proof.json'
   receipt=prepare(out,proof_path,c.sha(proof_path),'00000000-0000-0000-0000-000000000000')
   self.assertEqual(receipt['capture_seconds'],20);self.assertEqual(len(receipt['smoke_keys']),10)
   plan=c.read(c.expand(receipt['first_plan']));tiers={r['key']:r for r in c.read(c.expand(plan['demo_shot_tiers']))['apps']}
   self.assertTrue(all(tiers[k]['screenshot_seconds']==20 for k in receipt['smoke_keys']))
   self.assertFalse(plan['execution_enabled']);self.assertEqual(plan['demo_mode'],'launch')
 def test_missing_runtime_durable_source_rejected(self):
  d=copy.deepcopy(self.proof);target=c.OWN+'/sources/liboh_android_runtime.so'
  d['additional_files']=[r for r in d['additional_files'] if r['target']!=target];del d['expected'][target];d['generation_sha256']=c.generation(d)
  with self.assertRaises(ValueError):c.validate(d)
 def test_r2_plan_cannot_borrow_r4_identity(self):
  d=copy.deepcopy(self.proof);d['placement_plan']=c.pin(c.MAIN/'benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/candidate-window1/plan.json');d['generation_sha256']=c.generation(d)
  with self.assertRaisesRegex(ValueError,'r4 placement pin'):c.validate(d)
 def test_5cd_cannot_borrow_5ea_absence(self):
  d=copy.deepcopy(self.proof);d['serial']='5cd1e3dd00000000000000000923012c';d['generation_sha256']=c.generation(d)
  with self.assertRaisesRegex(ValueError,'5ea only'):c.validate(d)
 def test_absence_cannot_be_omitted(self):
  d=copy.deepcopy(self.proof);d['absent_files']=[];d['generation_sha256']=c.generation(d)
  with self.assertRaisesRegex(ValueError,'typed 5ea'):c.validate(d)
 def test_cfg_cap_addition_is_exact(self):
  d=copy.deepcopy(self.proof);row=next(r for r in d['additional_files'] if r['target']==c.CFG)
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'bad.cfg';p.write_bytes(c.pinned(row['source']).read_bytes().replace(b'"SYS_PTRACE"',b'"SYS_ADMIN"',1))
   row['source']=c.pin(p);row['sha256']=c.sha(p);d['expected'][c.CFG]=c.sha(p);d['generation_sha256']=c.generation(d)
   with self.assertRaisesRegex(ValueError,'two paths plus two'):c.validate(d)
 def test_absence_unknown_transport_never_absent(self):
  for rc,out,err in [(1,'ABSENT\nM0\n',''),(0,'ABSENT\nM1\n',''),(0,'',''),(0,'ABSENT\nM0\n','permission denied')]:
   with self.subTest(rc=rc,out=out,err=err),self.assertRaises(ValueError):decode(rc,out,err,'M')
 def test_absence_explicit_present_false(self):
  self.assertTrue(decode(0,'ABSENT\nM0\n','','M'));self.assertFalse(decode(0,'PRESENT\nM0\n','','M'))
if __name__=='__main__':unittest.main()
