#!/usr/bin/env python3
import hashlib, importlib.util, json, re, tempfile, unittest
from pathlib import Path
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('back51_build',H/'build.py');b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
PAT=r'(?ms)^\.method public onBackPressed\(Landroid/os/IBinder;Landroid/app/IRequestFinishCallback;\)V\n.*?^\.end method'
class Overlay(unittest.TestCase):
 def test_only_callback_method_changed(self):
  old=(H/'evidence/before.smali').read_text();new=(H/'evidence/after.smali').read_text()
  self.assertEqual(len(re.findall(PAT,old)),1);self.assertEqual(len(re.findall(PAT,new)),1)
  self.assertEqual(re.sub(PAT,'TARGET',old),re.sub(PAT,'TARGET',new))
 def test_callback_guard_and_exception(self):
  m=re.search(PAT,(H/'evidence/after.smali').read_text())[0]
  self.assertLess(m.index('if-eqz p2'),m.index('invoke-interface {p2}'))
  self.assertEqual(m.count('->requestFinish()V'),1);self.assertIn('.catch Landroid/os/RemoteException;',m)
  self.assertNotIn('->finishActivity',m);self.assertNotIn('nativeBackPressed',m)
 def test_exact_input_reject_before_output(self):
  with tempfile.TemporaryDirectory() as t:
   p=Path(t)/'bad.jar';p.write_bytes(b'foreign');out=Path(t)/'out'
   with self.assertRaisesRegex(ValueError,'input SHA'):b.build(p,out,Path(t),'NO_JAVA','NO_JAVAC')
   self.assertFalse(out.exists())
 def test_bcp_unique_real_binding(self):
  j=json.loads((H/'bcp-binding.json').read_text());self.assertEqual(len(j['rows']),9)
  self.assertEqual(set(j['unique_definitions'].values()),{1});self.assertEqual(j['rows'][8]['sha256'],b.EXPECTED)
 def test_real_build_receipts(self):
  j=json.loads((H/'evidence/results.json').read_text());self.assertEqual(j['classes'],170)
  self.assertTrue(j['unchanged_other_definitions']);self.assertEqual([r['rc'] for r in j['commands']],[0]*4)
  self.assertEqual(j['ui_result'],'PENDING');self.assertEqual(len(json.loads((H/'evidence/unchanged-classes.json').read_text())),169)
 def test_no_root_semantics_claim(self):
  j=json.loads((H/'deployment.disabled.json').read_text());self.assertFalse(j['execution_enabled'])
  self.assertEqual(j['scope'],'NON_ROOT_ARTICLE_EXPERIMENT_ONLY');self.assertEqual(j['root_home_acceptance'],'NOT_IMPLEMENTED_NOT_CLAIMED')
if __name__=='__main__':unittest.main()
