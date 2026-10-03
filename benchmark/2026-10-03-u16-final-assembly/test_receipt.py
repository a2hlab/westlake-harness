import copy
import os
import subprocess
import unittest

import prepare


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.receipt = prepare.load(prepare.HERE / 'receipts/paired-run1.json')
        self.review = prepare.load(prepare.HERE / 'reproduction-review.json')

    def test_two_actual_receipts_complete_pending_exception(self):
        for number in (1, 2):
            receipt = prepare.load(prepare.HERE / f'receipts/paired-run{number}.json')
            prepare.validate_receipt(receipt, receipt['input_jars'], receipt['outputs'])
        self.assertEqual(self.review['strict_identical'], 26)
        self.assertFalse(self.review['exception_approved'])
        self.assertFalse(self.review['object_chain_verified'])
        prepare.validate_pair(self.review['comparisons'])

    def test_failed_tee_rejects(self):
        self.receipt['tee_exit_code'] = 1
        with self.assertRaisesRegex(ValueError, 'failed build or tee'):
            prepare.validate_receipt(self.receipt, self.receipt['input_jars'], self.receipt['outputs'])

    def test_missing_image_rejects(self):
        self.receipt['outputs'].pop('boot.oat')
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            prepare.validate_receipt(self.receipt, self.receipt['input_jars'], self.receipt['outputs'])

    def test_old_approval_not_transferred(self):
        self.receipt['exception_used'] = True
        with self.assertRaisesRegex(ValueError, 'no U16 exception'):
            prepare.validate_receipt(self.receipt, self.receipt['input_jars'], self.receipt['outputs'])

    def test_outside_identity_field_rejects(self):
        rows = copy.deepcopy(self.review['comparisons'])
        next(row for row in rows if not row['identical'])['offsets'].append('0x3e3c0')
        with self.assertRaisesRegex(ValueError, 'outside'):
            prepare.validate_pair(rows)

    def test_disabled_candidate_binding(self):
        for variant in ('common', '61b'):
            composition = prepare.load(prepare.HERE / variant / 'composition.json')
            self.assertFalse(composition['execution_enabled'])
            self.assertFalse(composition['rollout_ready'])
            self.assertIsNone(composition['transaction_base'])
            self.assertNotIn('/system/bin/appspawn-x', composition['changed'])

    def test_guard_rejects_without_remote_execution(self):
        for name in ('replay-outer.sh', 'dump-object-chain-hw248.sh'):
            result = subprocess.run(['/bin/bash', str(prepare.HERE / name)], capture_output=True, text=True,
                                    env={**os.environ, 'U16_OUTER_REPLAY': ''})
            self.assertEqual(result.returncode, 78)
            self.assertIn('no remote', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
