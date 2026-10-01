"""Offline N10b smoke-plan wiring and strict failure regressions; no device I/O."""
import copy,hashlib,json,re,sys,unittest
from pathlib import Path
H=Path(__file__).resolve().parent;R=next(p for p in H.parents if (p/"scripts/lab/u7_executor.py").is_file());WS=R.parent
sys.path.insert(0,str(R/'scripts/lab'))
import activation_smoke as smoke,u7_executor as executor
class N10bSmoke(unittest.TestCase):
 def setUp(self):
  self.spec=json.loads((R/'knowledge/smoke/n10b.json').read_text())
  self.text={'helloworld':'[N10b-JNI-OWNER] bridge/runtime preloaded in westlake.sealed.child','cv2-com-ath0-rpn':'GraphicsJNI::setJavaVM initialized before Typeface registration','cv2-org-linaro-glmark2':'AssetManager.mObject cached in runtime and libandroid NDK owner','cv2-anupam-acrylic':'[N10b-EMBOSS] real OH m133 Emboss nativeConstructor registered'}
  self.runs={'smoke':dict(self.spec['expect'],alive_t20={'helloworld':'yes','zigzag':'yes'})}
  self.probe={'copies':{lib:['/route/'+lib] for lib in self.spec['probe']['single_copy']},'view':self.spec['probe']['files'].copy()}
 def test_complete_evidence_passes(self):
  ok,checks=smoke.evaluate(self.spec,self.runs,self.text,self.probe);self.assertTrue(ok,checks)
  self.assertEqual({f['id'] for f in self.spec['fixes']},{'N10b-JNI-OWNER','N10b-TYPEFACE-VM','N10b-NDK-ASSET-OFFSETS','N10b-EMBOSS'})
 def test_every_absent_activation_marker_fails(self):
  for fix in self.spec['fixes']:
   logs=self.text.copy();logs[fix['key']]='unrelated startup / fix not initialized'
   self.assertFalse(smoke.evaluate(self.spec,self.runs,logs,self.probe)[0],fix)
 def test_each_duplicate_owner_fails(self):
  for lib in self.spec['probe']['single_copy']:
   probe=copy.deepcopy(self.probe);probe['copies'][lib].append('/system/android/lib64/'+lib)
   self.assertFalse(smoke.evaluate(self.spec,self.runs,self.text,probe)[0],lib)
 def test_each_wrong_view_and_fingerprint_fails(self):
  for path in self.spec['probe']['files']:
   probe=copy.deepcopy(self.probe);probe['view'][path]='0'*64
   self.assertFalse(smoke.evaluate(self.spec,self.runs,self.text,probe)[0],path)
  for field in ['runtime_fp','boot_fp']:
   runs=copy.deepcopy(self.runs);runs['smoke'][field]='wrong'
   self.assertFalse(smoke.evaluate(self.spec,runs,self.text,self.probe)[0],field)
 def test_controls_and_zz_mount_safety(self):
  self.assertEqual(self.spec['groups'][0]['keys'],['helloworld','zigzag']);self.assertEqual(self.spec['groups'][0]['mode'],'launch-only')
  for key in ['helloworld','zigzag']:
   runs=copy.deepcopy(self.runs);runs['smoke']['alive_t20'][key]='no'
   self.assertFalse(smoke.evaluate(self.spec,runs,self.text,self.probe)[0],key)
 def test_spec_binds_actual_bundle_and_log_sources(self):
  row=json.loads((H/'u8-package.json').read_text())['batch'];plan=executor.prepare(WS/row['bundle'],WS/'westlake-generation-u8-j9-t7e/native')
  for key,paths in plan['reference_paths'].items():
   body='\n'.join(sorted(f'{plan["expected"][p]}  {p}' for p in paths))
   self.assertEqual(self.spec['expect']['runtime_fp' if key=='runtime' else 'boot_fp'],hashlib.sha256(body.encode()).hexdigest()[:12])
  for path,digest in self.spec['probe']['files'].items():self.assertEqual(digest,plan['expected'][path])
  source='\n'.join((H/'src'/name).read_text() for name in ['sealed_child_provider_loader.c','android_graphics_Typeface.cpp','asset-offsets-init.cpp','AndroidRuntime.cpp'])
  for text in self.text.values():self.assertIn(text,source)
if __name__=='__main__':unittest.main()
