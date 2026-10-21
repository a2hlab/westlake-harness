#!/usr/bin/env python3
import hashlib
import json
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent

class PeerEvidence(unittest.TestCase):
    def test_archived_production_baseline_receipt(self):
        r = json.loads((HERE/'baseline-02/results.json').read_text())
        self.assertTrue(r['all_reproduced'])
        self.assertEqual(sum(x['kind'] == 'counterexample' for x in r['cases']), 3)

    def test_archived_candidate_counterexample_receipts(self):
        for snapshot in ('candidate-01','candidate-02'):
            pins=json.loads((HERE/snapshot/'pins.json').read_text())
            for row in pins['files']:
                p=HERE/snapshot/Path(row['path']).name
                self.assertEqual(hashlib.sha256(p.read_bytes()).hexdigest(),row['sha256'])
            receipt='candidate-replay-02' if snapshot=='candidate-01' else 'candidate-replay-03'
            r=json.loads((HERE/receipt/'results.json').read_text())
            self.assertTrue(r['all_reproduced'])
            self.assertFalse(r['candidate_accepted'])
            self.assertEqual(sum(x['kind']=='counterexample' for x in r['cases']),8)
            for row in r['cases']:
                self.assertEqual(hashlib.sha256((HERE/receipt/(row['case']+'.sh')).read_bytes()).hexdigest(),row['script_sha256'])

    def test_acceptance_is_not_overclaimed(self):
        matrix=json.loads((HERE/'acceptance-matrix.json').read_text())
        self.assertEqual(len(matrix['manual']),12)
        for row in matrix['manual']:
            self.assertEqual(row['status'],'pending')
            self.assertFalse(row['executed'])
            self.assertEqual(row['human_observation'],'not_observed')
        self.assertFalse(matrix['sound_reconfirmed'])
        r=json.loads((HERE/'results.json').read_text())
        self.assertFalse(r['device_access'])
        self.assertFalse(r['candidate_accepted'])
        self.assertIn(r['status'],('request_changes','function_safety_pass_assembly_pending','offline_checks_pass_pending_outer'))
        self.assertTrue(r['live_parent_environment'].startswith('unknown'))

    def test_latest_review_matches_immutable_receipts(self):
        latest=json.loads((HERE/'latest-review.json').read_text())
        summary=json.loads((HERE/latest['review']).read_text())
        self.assertEqual(latest['watchdog_sha256'],summary['watchdog_sha256'])
        self.assertEqual(latest['safety_counts'],summary['counts'])
        root=(HERE/latest['review']).parent
        result=json.loads((root/'replay/results.json').read_text())
        for row in result['cases']:
            self.assertEqual(hashlib.sha256((root/'replay'/(row['case']+'.sh')).read_bytes()).hexdigest(),row['script_sha256'])
        for row in result['source_pins']['files']:
            self.assertEqual(hashlib.sha256((root/'snapshot'/row['path']).read_bytes()).hexdigest(),row['sha256'])
        self.assertFalse(summary['candidate_accepted'])

    def test_latest_assembly_chain_and_scope(self):
        latest=json.loads((HERE/'latest-review.json').read_text())
        path=latest.get('assembly_receipt')
        if not path:
            self.assertIn('pending',latest['status']);return
        root=(HERE/path).parent
        receipt=json.loads((HERE/path).read_text())
        self.assertTrue(receipt['passed'])
        self.assertTrue(receipt['input_unchanged'])
        self.assertTrue(all(x['match'] for x in receipt['function_source_to_package']))
        self.assertFalse(receipt['execution'])
        self.assertFalse(receipt['authority']['deployment_authorized'])
        self.assertEqual(receipt['authority']['startup_enabled'],'0')
        self.assertEqual(hashlib.sha256((root/'package-snapshot/MANIFEST.sha256').read_bytes()).hexdigest(),receipt['package_manifest_sha256'])
        for name,expected in receipt['all_22_member_sha256'].items():
            file=root/'package-snapshot'/name
            if name not in ('screen-gate','decoder-probe.jpeg'):
                self.assertEqual(hashlib.sha256(file.read_bytes()).hexdigest(),expected)

if __name__=='__main__': unittest.main()
