import importlib.util,json,os,shutil,tempfile,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;WS=next(p for p in H.parents if (p/'westlake-harness').is_dir());os.environ['WORKSPACES']=str(WS)
def module(name):
 s=importlib.util.spec_from_file_location(name,H/(name+'.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
R=module('rebind');B=module('prepare_behavior')
class Tests(unittest.TestCase):
 def capture(self,d):
  source=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-5ea-readonly';shutil.copytree(source,d)
  boot='11111111-2222-3333-4444-555555555555'
  for name in ['probe.stdout.txt','control/metadata.stdout.txt']:
   p=d/name;p.write_text(p.read_text().replace(R.OLD_BOOT,boot).replace('66352:67173','66352:99999'))
  p=d/'probe.stdout.txt';p.write_text(p.read_text().rstrip('\n')+'\n'+boot+'\n')
  p=d/'probe.json';x=R.read(p);x['stdout_sha256']=R.sha(d/'probe.stdout.txt');R.save(p,x)
  return boot
 def test_new_boot_inode(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'capture';boot=self.capture(p);self.assertEqual(R.inspect(p),(boot,'66352:99999'))
 def test_old_boot_rejected(self):
  p=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/outer/r6-5ea-readonly'
  with self.assertRaisesRegex(ValueError,'fresh real'):R.inspect(p)
 def test_control_drift_rejected(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'capture';self.capture(p);(p/'control/worker.sh').write_text('foreign')
   with self.assertRaisesRegex(ValueError,'control bytes'):R.inspect(p)
 def test_supplement_exact_insertion(self):
  source=WS/'westlake-harness/benchmark/2026-10-09-demo-boatattack/v2-20261013/integration/runtime-successor-r6/window-final4-disabled'
  with tempfile.TemporaryDirectory(dir=H) as t:
   p=Path(t)
   for n in ['interaction_runner.py','interaction.plan.disabled.json','request.json','authorization.required.json']:shutil.copyfile(source/n,p/n)
   B.build(p);before=(p/'interaction_runner.py').read_text();after=(p/'interaction_reset_baseline.py').read_text();self.assertEqual(after.replace(B.INSERT,''),before)
   compile(after,'supplement','exec');self.assertEqual(after.count('time.sleep(delay)'),1)
   self.assertIn("image_sha256')==sha(out/'reset-baseline.jpeg')",after)
   self.assertIn("approved.get('child')==identity",after)
   self.assertIn("rec['cadence']=[3,6,6,15]",after)
   q=B.read(p/'request.json');self.assertEqual(q['programs']['interaction']['sha256'],B.sha(p/'interaction_reset_baseline.py'))
 def test_existing_run_refused(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t);(p/'run').mkdir()
   with self.assertRaisesRegex(ValueError,'never amend'):B.build(p)
if __name__=='__main__':unittest.main()
