import copy, hashlib, json, subprocess, unittest
from pathlib import Path
import prepare,report
class Checks(unittest.TestCase):
 def setUp(self):
  self.run=(Path(__file__).parent/'fixture-run.sh').read_bytes()
  self.p=json.loads((Path(__file__).parent/'fixture-profile.json').read_text())
 def test_actual_source_profile_and_sh_syntax(self):
  a=prepare.prepare(self.p,self.run,'hdc');self.assertLess(len(a[-1].encode()),32768)
  self.assertEqual(subprocess.run(['sh','-n'],input=a[-1].encode(),capture_output=True).returncode,0)
 def test_wrong_identity_profiles_reject(self):
  for path,v in [(('serial',),'5cd1e3dd00000000000000000923012c'),(('parent','uid'),20011206),(('parent','exe_sha256'),'0'*64),(('host','pid'),self.p['parent']['pid']),(('parent','mnt'),self.p['init_mnt']),(('boot',),self.p['before_boot'])]:
   p=copy.deepcopy(self.p);d=p
   for k in path[:-1]:d=d[k]
   d[path[-1]]=v
   with self.subTest(path=path):
    with self.assertRaises(AssertionError):prepare.prepare(p,self.run,'hdc')
 def test_run_extra_change_reject(self):
  with self.assertRaises(AssertionError):prepare.prepare(self.p,self.run+b'\n# extra\n','hdc')
 def test_child_wrong_parent_reject(self):
  p=copy.deepcopy(self.p);p['child']={**p['parent'],'pid':99999,'uid':20011206,'ppid':123}
  with self.assertRaises(AssertionError):prepare.prepare(p,self.run,'hdc')
 def test_truncation_and_transport_failure_unknown(self):
  self.assertEqual(report.decode('CANDIDATE_VIEW_BEGIN',0)['status'],'INCOMPLETE_OR_REJECTED')
  self.assertEqual(report.decode('CANDIDATE_VIEW_END_IDENTITY_MATCH',1)['status'],'INCOMPLETE_OR_REJECTED')
if __name__=='__main__':unittest.main()
