import importlib.util,json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
R=Path(__file__).resolve().parents[2]
s=importlib.util.spec_from_file_location('deploy',R/'scripts/lab/deploy_generation.py');d=importlib.util.module_from_spec(s);s.loader.exec_module(d)
class GenerationStates(unittest.TestCase):
 def setup_state(self,root,gen):
  args=SimpleNamespace(package=root,serial=next(iter(d.SERIALS)),state_root=root,lane='cx-t0',tools='/unused')
  board=SimpleNamespace(boot='boot1',ready=lambda:None)
  return args,d.Deployment(args,{'generation':gen},SimpleNamespace(Board=Mock(return_value=board)))
 def test_generation_upgrade_has_separate_rollback_state(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);_,a=self.setup_state(r,'a'*64);_,b=self.setup_state(r,'b'*64)
   self.assertNotEqual(a.statepath,b.statepath)
 def test_reuse_legacy_only_for_matching_generation(self):
  with tempfile.TemporaryDirectory() as t:
   r=Path(t);a,x=self.setup_state(r,'a'*64);legacy=r/a.serial/'boot1.json';legacy.write_text(json.dumps({'generation':'a'*64,'status':'active_verified'}))
   _,same=self.setup_state(r,'a'*64);_,other=self.setup_state(r,'b'*64)
   self.assertEqual(same.statepath,legacy);self.assertEqual(same.d['status'],'active_verified');self.assertIsNone(other.d)
if __name__=='__main__':unittest.main()
