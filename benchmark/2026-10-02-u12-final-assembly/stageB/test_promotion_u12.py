import copy,json,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
import promotion_hook_u12 as h
CERT=h.M/'benchmark/2026-10-02-u12-final-assembly/stageB/outer-stage-a.json'
class Promotion(unittest.TestCase):
 def setUp(self):
  self.c=json.loads((h.H/'composition.json').read_text());self.d=json.loads(CERT.read_text());self.base=json.loads((h.M/'benchmark/2026-10-02-u10-1-t8-sweep/outer-signoff.json').read_text())
 def reason(self,d=None,smoke=None):return h.retention_reason(d or self.d,self.c,self.base,{'passed':True} if smoke is None else smoke)
 def test_current_certificate_revoked(self):
  with self.assertRaisesRegex(AssertionError,'separate Stage B outer authorization'):h.stage_a_admission(CERT)
  self.assertFalse(self.d['promotion_authorized'])
 def test_paused_admission_fails_before_vm(self):
  with patch.object(h.previous,'vm') as vm:
   with self.assertRaisesRegex(AssertionError,'promotion paused'):h.admission()
   vm.assert_not_called()
 def test_wrong_bundle(self):
  d=copy.deepcopy(self.d);d['bundle_sha256']='0'*64;self.assertIn('another bundle',self.reason(d))
 def test_all116_required(self):
  d=copy.deepcopy(self.d);d['stage_A_regression_verdict']['measured']=115;self.assertIsNotNone(self.reason(d))
 def test_total_matches_independent_signed_baseline(self):
  d=copy.deepcopy(self.d);d['stage_A_regression_verdict']['u10_1_t8_lit_total']=115;self.assertIsNotNone(self.reason(d))
 def test_same_or_lit_required(self):
  d=copy.deepcopy(self.d);d['stage_A_regression_verdict']['same_or_lit_within_k_of_n']=115;self.assertIsNotNone(self.reason(d))
 def test_confirmed_regression_rejected(self):
  d=copy.deepcopy(self.d);d['confirmed_regressions']=['key'];self.assertIsNotNone(self.reason(d))
 def test_smoke_required(self):self.assertIsNotNone(self.reason(smoke={'passed':False}))
 def test_outer_signature_required(self):
  d=copy.deepcopy(self.d);d['signed_by']='not-outer';self.assertIsNotNone(self.reason(d))
 def test_toutiao_is_not_u12_condition(self):self.assertNotIn('toutiao_walls_1_2_absent',self.d);self.assertIsNone(self.reason())
 def test_fresh_decision_mismatch_restores_base(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'runner/smoke').mkdir(parents=True);(root/'runner/smoke/smoke-result.json').write_text('{"passed":true}')
   d={'signed_by':'outer(claude)','serial':'wrong','phase':'B','window_root':str(root),'bundle_sha256':self.c['bundle_sha256'],'native_manifest_sha256':self.c['native_manifest_sha256'],'controls_t20_lit':['helloworld','zigzag'],'confirmed_regressions':[]};p=root/'decision.json';p.write_text(json.dumps(d))
   with patch.object(h.previous,'finish') as rollback,patch.object(h,'verify_candidate') as verify:
    h.finish('61b0657200000000000000000324012c',root,root/'restored.json',p,CERT);rollback.assert_called_once();verify.assert_not_called();self.assertFalse(json.loads((root/'retention.json').read_text())['retained'])
 def test_valid_fresh_decision_retains_only_after_identity(self):
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);(root/'runner/smoke').mkdir(parents=True);(root/'runner/smoke/smoke-result.json').write_text('{"passed":true}')
   serial='61b0657200000000000000000324012c';d={'signed_by':'outer(claude)','serial':serial,'phase':'B','window_root':str(root),'bundle_sha256':self.c['bundle_sha256'],'native_manifest_sha256':self.c['native_manifest_sha256'],'controls_t20_lit':['helloworld','zigzag'],'confirmed_regressions':[]};p=root/'decision.json';p.write_text(json.dumps(d))
   with patch.object(h.previous,'finish') as rollback,patch.object(h,'admission') as admission,patch.object(h,'verify_candidate') as verify:
    # Isolated authorized-fixture branch: this is not the revoked production certificate.
    approved=copy.deepcopy(self.d);approved['promotion_authorized']=True;fixture=root/'synthetic-stage-a.json';fixture.write_text(json.dumps(approved))
    h.finish(serial,root,root/'restored.json',p,fixture);rollback.assert_not_called();admission.assert_called_once();verify.assert_called_once();self.assertTrue(json.loads((root/'retention.json').read_text())['retained'])
if __name__=='__main__':unittest.main()
