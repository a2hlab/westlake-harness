import copy, hashlib, importlib.util, json, tempfile, unittest
from unittest.mock import patch
from pathlib import Path
H=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('runtime_hook',H/'promotion_hook_u13_runtime.py')
hook=importlib.util.module_from_spec(spec);spec.loader.exec_module(hook)
D=hook.M/'benchmark/2026-10-03-u13-stage-a-decision'
spec=importlib.util.spec_from_file_location('decision_build',D/'build_decision.py')
b=importlib.util.module_from_spec(spec);spec.loader.exec_module(b)
class Promotion(unittest.TestCase):
 def setup_tag(self,tag):
  hook.H=H/tag
  self.c=json.loads((hook.H/'composition.json').read_text())
  self.d=json.loads((D/('outer-stage-a-'+tag+'.json')).read_text())
  self.reference=json.loads(b.REFERENCE.read_text())
 def test_signed_both_packages(self):
  for tag in ['common','61b']:
   self.setup_tag(tag)
   self.assertIsNone(hook.retention_reason(self.d,self.c,self.reference,{'passed':True}))
 def test_wrong_bundle(self):
  self.setup_tag('common');self.d['bundle_sha256']='0'*64
  self.assertEqual(hook.retention_reason(self.d,self.c,self.reference,{'passed':True}),'signoff belongs to another bundle')
 def test_one_badtag(self):
  self.setup_tag('common');report=json.loads((D/'selftest-u13-stage-a.json').read_text());report['runs'][0]['badtag_count']=1
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp)/'r.json';p.write_text(json.dumps(report));self.d['process_selftest_gate']['report_sha256']=hashlib.sha256(p.read_bytes()).hexdigest()
   reason=hook.criteria.retention_reason(self.d,hook.signed_composition(self.c),self.reference,{'passed':True},p,D/'selftest-explanations-common.json')
   self.assertIn('unconditionally rejects',reason)
 def test_smoke_failure(self):
  self.setup_tag('61b');self.assertEqual(hook.retention_reason(self.d,self.c,self.reference,{'passed':False}),'activation smoke did not pass')
 def test_armed_payload_drift(self):
  self.setup_tag('common');self.c['bundle_sha256']='0'*64
  with self.assertRaisesRegex(AssertionError,'armed bundle drift'):hook.signed_composition(self.c)
 def run_fresh_finish(self, change):
  self.setup_tag('common')
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);(root/'runner/smoke').mkdir(parents=True);(root/'post-apply').mkdir()
   smoke=root/'runner/smoke/smoke-result.json';smoke.write_text('{"passed":true}')
   identity=root/'post-apply/candidate-318.json';identity.write_text('{"diff":{},"absent":[]}')
   decision={'signed_by':'outer(claude)','serial':'5ea34a4500000000000000001123012c','phase':'B','window_root':str(root),'bundle_sha256':self.c['bundle_sha256'],'native_manifest_sha256':self.c['native_manifest_sha256'],'controls_t20_lit':['helloworld','zigzag'],'confirmed_regressions':[],'smoke_sha256':hook.gb.sha(smoke),'identity_sha256':hook.gb.sha(identity)}
   decision.update(change);p=root/'outer.json';p.write_text(json.dumps(decision))
   with patch.object(hook,'stage_a_admission'),patch.object(hook,'admission'),patch.object(hook,'verify_candidate'),patch.object(hook.previous,'finish') as restore:
    hook.finish(decision['serial'],root,root/'restored-spec.json',p,D/'outer-stage-a-common.json')
    kept=json.loads((root/'retention.json').read_text())['retained'];self.assertEqual(restore.called,not kept)
    return kept
 def test_fresh_same_window_retains(self):self.assertTrue(self.run_fresh_finish({}))
 def test_wrong_window_restores(self):self.assertFalse(self.run_fresh_finish({'window_root':'another-window'}))
 def test_stale_smoke_sha_restores(self):self.assertFalse(self.run_fresh_finish({'smoke_sha256':'0'*64}))
if __name__=='__main__':unittest.main()
