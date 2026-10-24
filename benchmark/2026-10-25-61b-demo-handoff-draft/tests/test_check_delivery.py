"""Synthetic tests for the read-only delivery checker. No device, no real evidence needed."""
import hashlib, importlib.util, json, tempfile, unittest
from pathlib import Path
spec = importlib.util.spec_from_file_location('check_delivery', Path(__file__).resolve().parents[1] / 'check_delivery.py')
C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)

class Checker(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory(); self.d = Path(self.t.name); self.ev = []
    def tearDown(self): self.t.cleanup()
    def put(self, role, name, obj, sha=None):
        p = self.d / name; p.write_text(json.dumps(obj)); s = hashlib.sha256(p.read_bytes()).hexdigest()
        self.ev.append(dict(role=role, path=str(p), sha256=sha or s)); return s
    def chain(self, b2=None, receipt_sha=None):
        hsha = self.put('t141_boot1_handoff', 'h.json', dict(phase='boot1', candidate_boot='B1'))
        self.put('t141_boot1_result', 'r1.json', dict(runtime_result='boot1_three_stages_passed_candidate_in_place_pending_boot2', released=True, boot1_handoff_sha256=hsha, closeout_review='passed', status='running'))
        self.put('t141_boot2_outer_receipt', 'o2.json', dict(phase='boot2', boot1_handoff_sha256=receipt_sha or hsha))
        if b2 is not None: self.put('t141_boot2_result', 'r2.json', b2)
    def run_check(self): return C.check(dict(evidence=self.ev))
    RETAINED = dict(status='running', runtime_result='retained_reentry_validated_av_pending', rollback='not_performed_candidate_retained', released=True,
                    closeout_review='passed', boots=['B1', 'B2'], speaker_audio='pending', video_audio_acceptance='pending', t4_full_seal='pending')
    def test_retained_chain_consistent_but_never_sealed(self):
        self.chain(self.RETAINED); r = self.run_check()
        self.assertTrue(r['evidence_consistent']); self.assertEqual(r['t141_state'], 'candidate_retained_av_pending')
        self.assertIs(r['sealed'], False); self.assertEqual(r['seal_claim'], 'not_made_by_checker')
        self.assertEqual(r['pending']['speaker_audio'], 'pending'); self.assertEqual(r['pending']['physical_power_cycle'], 'pending')
        self.assertIn('not_performed_by_checker', r['image_review']); self.assertNotIn('sealed', json.dumps(r).replace('"sealed": false', ''))
    def test_hash_mismatch_reported(self):
        self.chain(self.RETAINED); self.ev[0]['sha256'] = '0' * 64; r = self.run_check()
        self.assertFalse(r['evidence_consistent']); self.assertEqual(r['mismatches'][0]['problem'], 'sha256 mismatch')
    def test_missing_file_reported(self):
        self.ev.append(dict(role='image', path=str(self.d / 'absent.jpeg'), sha256='0' * 64)); r = self.run_check()
        self.assertEqual(r['mismatches'][0]['problem'], 'missing')
    def test_receipt_handoff_chain_broken(self):
        self.chain(self.RETAINED, receipt_sha='f' * 64); r = self.run_check()
        self.assertFalse(r['evidence_consistent']); self.assertTrue(any('outer receipt' in m['problem'] for m in r['mismatches']))
    def test_boot_mismatch_between_handoff_and_boot2(self):
        self.chain(dict(self.RETAINED, boots=['B7', 'B2'])); r = self.run_check(); self.assertFalse(r['evidence_consistent'])
    def test_boot1_only(self):
        self.chain(); self.assertEqual(self.run_check()['t141_state'], 'boot1_only_boot2_pending')
    def test_rolled_back_and_restored_idle(self):
        self.chain(dict(status='experiment_stopped', rollback='verified', released=True, boots=['B1'])); self.assertEqual(self.run_check()['t141_state'], 'candidate_not_retained_baseline_restored')
        self.ev = []; self.chain(dict(status='experiment_stopped', rollback='restored_idle_exact_object', released=True, boots=['B1']))
        self.assertEqual(self.run_check()['t141_state'], 'candidate_not_retained_restored_idle_not_running')
    def test_closeout_pending_and_unreleased(self):
        self.chain(dict(self.RETAINED, runtime_result='retained_reentry_closeout_review_pending', closeout_review='pending_outer_signoff'))
        self.assertEqual(self.run_check()['t141_state'], 'candidate_retained_closeout_signoff_pending')
        self.ev = []; self.chain(dict(self.RETAINED, released=False)); self.assertEqual(self.run_check()['t141_state'], 'boot2_unresolved_needs_outer')
    def test_script_pass_is_not_image_review(self):
        self.chain(self.RETAINED); self.put('review_receipt', 'rv.json', dict(label='s30', verdict='feed', reviewed_by='x', image_sha256='a' * 64))
        r = self.run_check(); self.assertEqual(r['review_receipts'][0]['verdict'], 'feed'); self.assertEqual(r['pending']['human_image_review_of_listed_evidence'], 'required')
    def test_bad_manifest_entry(self):
        with self.assertRaises(ValueError): C.check(dict(evidence=[dict(role='bogus', path='x', sha256='y')]))

if __name__ == '__main__': unittest.main(verbosity=2)
