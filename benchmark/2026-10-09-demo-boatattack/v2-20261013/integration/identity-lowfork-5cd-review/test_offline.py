import importlib.util,json,os,shlex,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
ROOT=next(p for p in HERE.parents if (p/'AGENTS.md').is_file() and (p/'scripts/lab/lab_paths.py').is_file())
if not os.environ.get('WORKSPACES'):
 paths_spec=importlib.util.spec_from_file_location('test_lab_paths',ROOT/'scripts/lab/lab_paths.py');paths=importlib.util.module_from_spec(paths_spec);paths_spec.loader.exec_module(paths)
 os.environ['WORKSPACES']=str(paths.workspaces(start=ROOT))
spec=importlib.util.spec_from_file_location('compare',HERE/'compare_metadata.py');c=importlib.util.module_from_spec(spec);spec.loader.exec_module(c)
class Offline(unittest.TestCase):
 def setUp(self):self.p=c.read(HERE/'plan.disabled.json');self.mods=c.validate(self.p)
 def test_real5cd_commands_only_parent_delta(self):
  results=[];inventory={**self.p['files'],**self.p['directories']}
  for factory in [self.mods[0].with_presence,self.mods[1].with_presence]:
   commands=[]
   class Capture(factory(object)):
    def _presence_read(self,name,command):
     self.assert_metadata_name=name;commands.append(command)
     paths=shlex.split(command.split('for p in ',1)[1].split('; do ',1)[0]);return '\n'.join(t+'|'+'|'.join(str(inventory[t][k]) for k in ('mode','uid','gid','label')) for t in paths)
   with patch('subprocess.run',side_effect=AssertionError('No process/device calls')):Capture().verify_metadata(self.p['files'],self.p['directories'])
   results.append(commands)
  self.assertEqual(len(results[0]),23);self.assertEqual(len(results[1]),23)
  for old,new in zip(*results):self.assertEqual(old.replace('walk=$(dirname "$walk")',self.mods[1].PARENT_STEP),new)
 def test_serial_rejected_before_any_source_or_transport(self):
  self.p['serial']='61b0657200000000000000000324012c'
  with patch('subprocess.run',side_effect=AssertionError('No process/device calls')),self.assertRaisesRegex(ValueError,'5cd-only'):c.validate(self.p)
 def test_real5cd_uids(self):
  self.assertEqual(self.p['boat_uid'],20011301);self.assertEqual(self.p['routeb_uid'],20011300)
  self.assertTrue(all(m['uid'] not in (20011206,20011207) for m in self.p['files'].values()))
  self.assertEqual(sum(v['uid']==20011300 for v in self.p['directories'].values()),3)
if __name__=='__main__':unittest.main()
