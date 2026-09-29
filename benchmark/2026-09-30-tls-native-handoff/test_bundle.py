import importlib.util,subprocess,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('deploy_bundle.py');s=importlib.util.spec_from_file_location('bundle',p);b=importlib.util.module_from_spec(s);s.loader.exec_module(b)
class Bundle(unittest.TestCase):
 def test_second_failure_rolls_back_first(self):
  seen=[]
  def call(cmd,check=False):
   seen.append(cmd)
   if cmd==['html']:raise subprocess.CalledProcessError(1,cmd)
   return subprocess.CompletedProcess(cmd,0)
  def commands(*args,**kw):return [['check-tls'],['check-html']] if kw.get('dry') else [['tls'],['html']]
  with patch.object(b,'commands',commands),patch.object(b.subprocess,'run',call):
   with self.assertRaises(subprocess.CalledProcessError):b.run(Path('.'),'serial','lane')
  self.assertEqual(seen,[['check-tls'],['check-html'],['tls'],['html'],['tls','--rollback']])
 def test_preflight_failure_does_not_mutate(self):
  seen=[]
  def call(cmd,check=False):seen.append(cmd);raise subprocess.CalledProcessError(1,cmd)
  with patch.object(b,'commands',return_value=[['check']]),patch.object(b.subprocess,'run',call):
   with self.assertRaises(subprocess.CalledProcessError):b.run(Path('.'),'serial','lane')
  self.assertEqual(seen,[['check']])
if __name__=='__main__':unittest.main()
