import copy, hashlib, json, subprocess, unittest, tempfile, shlex
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
 def test_wrong_digest_keeps_real_bytes_and_continues(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/'actual';path.write_bytes(b'actual file content\n');digest=hashlib.sha256(path.read_bytes()).hexdigest()
   script='set -eu\nstat() { command gstat "$@"; }\nOBS_BAD=0\n'+prepare.FILE_READ
   script+=f'file_read parent run.sh {shlex.quote(str(path))} '+('0'*64)+'\n'
   script+=f'file_read child run.sh {shlex.quote(str(path)+".missing")} '+digest+'\n'
   script+=f'file_read physical run.sh {shlex.quote(str(path))} '+digest+'\n'
   script+='echo CANDIDATE_VIEW_END_IDENTITY_MATCH\nexit "$OBS_BAD"\n'
   r=subprocess.run(['sh'],input=script.encode(),capture_output=True)
   text=r.stdout.decode();self.assertEqual(r.returncode,82)
   self.assertIn('CV_FILE_HASH|parent|run.sh|'+digest,text)
   self.assertIn('CV_FILE_PRESTAT|parent|run.sh|',text)
   self.assertIn('CV_FILE_ERROR|parent|run.sh|SHA_MISMATCH',text)
   self.assertIn('CV_FILE_ERROR|child|run.sh|MISSING_OR_NOT_REGULAR',text)
   self.assertIn('CV_FILE_HASH|physical|run.sh|'+digest,text)
   result=report.decode(text,r.returncode)
   self.assertEqual(result['status'],'INCOMPLETE_OR_REJECTED')
   self.assertTrue(result['final_identity_marker']);self.assertTrue(result['observed_lines'])
 def test_actual_init_guard_rejects_wrong_namespace(self):
  shell=prepare.prepare(self.p,self.run,'hdc')[-1]
  guards=[l for l in shell.splitlines() if 'readlink /proc/1/ns/mnt' in l]
  self.assertEqual(len(guards),2)
  for actual,rc in [('mnt:[9]',81),(self.p['init_mnt'],0)]:
   # Explicit readlink seam; executes the exact generated shell test, no device.
   script='readlink() { printf "%s\\n" '+shlex.quote(actual)+'; }\n'+guards[0]+'\n'
   self.assertEqual(subprocess.run(['sh'],input=script.encode(),capture_output=True).returncode,rc)
  p=copy.deepcopy(self.p);p['init_mnt']='invalid'
  with self.assertRaises(AssertionError):prepare.prepare(p,self.run,'hdc')
if __name__=='__main__':unittest.main()
