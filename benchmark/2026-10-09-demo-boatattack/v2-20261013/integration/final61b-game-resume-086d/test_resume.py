import ast,copy,importlib.util,json,os,time,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file() and (p/'scripts/lab/lab_paths.py').is_file())
if not os.environ.get('WORKSPACES'):
 paths_spec=importlib.util.spec_from_file_location('resume_lab_paths',ROOT/'scripts/lab/lab_paths.py');paths=importlib.util.module_from_spec(paths_spec);paths_spec.loader.exec_module(paths)
 os.environ['WORKSPACES']=str(paths.workspaces(start=ROOT))
spec=importlib.util.spec_from_file_location('resume',HERE/'interaction_resume.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
class ResumeTests(unittest.TestCase):
 def setUp(self):
  self.p=json.loads((HERE/'plan.disabled.json').read_text());self.p['execution_enabled']=True
 def test_real_record_admit(self):
  a=dict(approved_by='outer(codex)',action='boat-interaction',plan_sha256='local-fixture',runner_sha256=m.sha(m.__file__),serial=self.p['serial'],owner=self.p['owner'],boot_id=self.p['boot_id'],expires_epoch=time.time()+240,spare_board_authorized=True)
  with patch('subprocess.run',side_effect=AssertionError('device forbidden')),patch('subprocess.Popen',side_effect=AssertionError('device forbidden')):m.admit(self.p,a,'local-fixture')
 def test_changed_child(self):
  self.p['resume']['child']['birth']+=1
  with self.assertRaisesRegex(ValueError,'resume child differs'):m.resume_binding(self.p)
 def test_changed_boot(self):
  self.p['boot_id']='00000000-0000-0000-0000-000000000000'
  with self.assertRaisesRegex(ValueError,'prior identity differs'):m.resume_binding(self.p)
 def test_changed_surface(self):
  self.p['resume']['surface_node']='1'
  with self.assertRaisesRegex(ValueError,'resume surface differs'):m.resume_binding(self.p)
 def test_changed_record(self):
  self.p['resume']['record_sha256']='0'*64
  with self.assertRaisesRegex(ValueError,'prior record pin differs'):m.resume_binding(self.p)
 def test_no_launch_and_preserved_assets_inputs(self):
  tree=ast.parse(Path(m.__file__).read_text());names=[n.func.attr for n in ast.walk(tree) if isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute)]
  self.assertNotIn('desktop_launch',names)
  src=json.loads((HERE/'source.json').read_text());old=ast.parse((ROOT/src['original_runner']).read_text())
  def function(t,n):return ast.dump(next(x for x in t.body if isinstance(x,ast.FunctionDef) and x.name==n))
  self.assertEqual(function(tree,'proc_identity'),function(old,'proc_identity'))
  self.assertEqual(function(tree,'target_window'),function(old,'target_window'))
  self.assertEqual(len(m.ASSETS),7)
if __name__=='__main__':unittest.main()
