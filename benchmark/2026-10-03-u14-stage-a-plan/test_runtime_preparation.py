"""Known answers for metadata-only arming and strict smoke crypto."""
import json
import tempfile
import unittest
from pathlib import Path
import control_selftest as control
H=Path(__file__).resolve().parent

class Preparation(unittest.TestCase):
    def test_metadata_only_and_actual_payload_manifest(self):
        for v in ['common','61b']:
            p=json.loads((H/'window1'/v/'arming-proof.json').read_text())
            self.assertEqual(set(p['bundle_field_diff']),{'rollout_ready','rollout_blocker'})
            self.assertTrue(p['other_files_byte_identical']);self.assertEqual(p['other_files_count'],3555)
            self.assertEqual(p['manifest_sha256'],'3460435aa75195a3103a6da5b3e85e9299d9389ac64fedb7ee098d4bcb6103cf')
    def test_not_enabled_before_outer_smoke_review(self):
        for v in ['common','61b']:
            c=json.loads((H/'window1'/v/'composition.json').read_text())
            self.assertIs(c['execution_enabled'],False)
            for b in ['5ea','5cd'] if v=='common' else ['61b']:
                s=json.loads((H/'window1'/v/f'smoke-{b}-proposal.json').read_text())
                self.assertTrue(s['pending_outer_review']);self.assertNotIn('expect_copies',s['probe'])
                for row in c['candidate_boards'].values():
                    r=json.loads((H/'window1'/v/'recovery-u13.json').read_text())['boards']
                    base=next(iter(r.values()))['expected']
                    for path,sha in row['expected'].items():
                        if base.get(path)!=sha:self.assertEqual(s['probe']['files'][path],sha)

class Crypto(unittest.TestCase):
    def run_case(self,line,second=True):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            for k in ['helloworld','zigzag'] if second else ['helloworld']:
                p=root/k;p.mkdir();(p/'record.json').write_text(json.dumps({'key':k,'bms':{'uid':123},'diagnostics':{'complete':True}}))
                (p/'processes-t20.txt').write_text('456 1 123 appspawn-x\n')
                (p/'hilog.txt').write_text('10-03 10:00:00.000 456 x [WL-KS-PROBE] '+line+'\n')
            return control.check(root)
    def test_success_round_trip(self):self.assertTrue(self.run_case('validateAead round-trip=OK')['passed'])
    def test_badtag_not_masked_by_ok(self):
        d=self.run_case('validateAead=OK\n10-03 10:00:00.001 456 x [WL-KS-PROBE] selftest AEADBadTagException via default provider')
        self.assertFalse(d['passed']);self.assertEqual(d['badtag_count'],2)
    def test_selftest_error(self):self.assertFalse(self.run_case('selftest error: GCM cipher needs to be initialised')['passed'])
    def test_probe_error(self):self.assertFalse(self.run_case('probe error: failure')['passed'])
    def test_silence_is_unknown(self):self.assertFalse(self.run_case('entry only')['passed'])
    def test_missing_control_rejects(self):self.assertFalse(self.run_case('validateAead=OK',second=False)['passed'])

if __name__=='__main__':unittest.main()
