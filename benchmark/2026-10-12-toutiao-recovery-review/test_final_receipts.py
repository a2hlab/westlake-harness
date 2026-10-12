#!/usr/bin/env python3
"""Verify completed independent replays and new live sources without re-execution."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import review


class FinalReceiptTests(unittest.TestCase):
    def test_accepted_revision_identity_and_fourteen_receipts(self):
        result = review.accepted_revision_review()
        self.assertEqual(result['candidate_sha256'], '9763171a0b6dab1b23b72e454cb2c6256181298bc282e81b6ae8e38fa9577072')
        self.assertEqual(len(result['cases']), 14)
        self.assertFalse(result['deployment_allowed'])
        self.assertFalse(result['ui_signed'])
        self.assertFalse(result['seal_signed'])

    def test_previous_final_blockers_remain_separate(self):
        result = json.loads((review.HERE / 'evidence/final-4d3a8e53-cases.json').read_text())
        self.assertEqual(result['candidate_sha256'], '4d3a8e530bb50d93bf0170040bc29ea8b9787ef854190342bb2524f3a1859232')
        self.assertEqual(sum(case['verdict'] == 'blocker' for case in result['cases']), 6)
        self.assertEqual(review.checkpoint_review()['status'], 'blocker')

    def test_current_capture_and_live_helper_code(self):
        entries = json.loads((review.HERE / 'evidence/followup-1406-sources.json').read_text())
        for entry in entries:
            path = review.WORKSPACES / 'westlake-harness' / entry['path']
            self.assertEqual(review.digest(path), entry['sha256'])
        root = review.WORKSPACES / 'westlake-harness/benchmark/2026-10-12-toutiao-recovery-readonly/followup-1406'
        index = json.loads((root / 'index.json').read_text())
        self.assertEqual(index['boot_id'], review.BOOT)
        self.assertEqual(len(index['captures']), 9)
        for entry in index['captures']:
            self.assertEqual(review.digest(root / entry['path']), entry['sha256'])
        live = (root / 'owner-0.txt').read_text().splitlines()
        candidate = (review.HERE / 'io-9763171a/payload/route-b-owner.sh').read_text().splitlines()
        noncomments = lambda lines: [line for line in lines if not line.lstrip().startswith('#')]
        self.assertEqual(noncomments(live), noncomments(candidate))

    def test_old_driver_exit_is_not_new_authority(self):
        entries = json.loads((review.HERE / 'evidence/driver-end-sources.json').read_text())
        for entry in entries:
            self.assertEqual(review.digest(review.resolve(entry['path'])), entry['sha256'])
        record = json.loads(review.resolve(entries[0]['path']).read_text())
        self.assertEqual(record['exit'], 124)
        result = review.accepted_revision_review()
        self.assertEqual(result['integration_status'], 'pending t4 concrete package')


if __name__ == '__main__':
    unittest.main(verbosity=2)
