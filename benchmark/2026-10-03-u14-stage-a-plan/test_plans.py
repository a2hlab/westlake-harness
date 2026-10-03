import subprocess
import sys
import unittest

import build_plans as b


class DisabledPlans(unittest.TestCase):
    def setUp(self):
        self.table = b.read(b.HERE/'inputs/key-table.json')
        self.reference = b.read(b.HERE/'inputs/reference.json')
        self.bindings = b.read(b.HERE/'inputs/bindings.json')
        self.groups = b.load_groups(self.table, b.HERE/'inputs/accepted-keys')

    def test_known_126_disjoint_board_correct(self):
        protected, lottery = b.validate(self.groups, self.reference, self.bindings)
        self.assertEqual((len(protected), len(lottery)), (107, 6))
        self.assertFalse(set(protected) & set(lottery))

    def test_wrong_armed_base_refuses(self):
        self.bindings['variants']['61b']['transaction_base_sha256'] = '0'*64
        with self.assertRaisesRegex(ValueError, 'armed U13'):
            b.validate(self.groups, self.reference, self.bindings)

    def test_lottery_regression_overlap_refuses(self):
        lottery = next(keys for shard, keys in self.groups['5ea'] if shard['name']=='lottery')
        protected = next(keys for shard, keys in self.groups['5ea'] if shard['name']=='lit-regression')
        protected.append(lottery[0])
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            b.validate(self.groups, self.reference, self.bindings)

    def test_mover_regression_overlap_refuses(self):
        movers = next(keys for shard, keys in self.groups['5ea'] if shard['name']=='movers')
        protected = next(keys for shard, keys in self.groups['5ea'] if shard['name']=='lit-regression')
        protected.append(movers[0])
        with self.assertRaisesRegex(ValueError, 'disjoint'):
            b.validate(self.groups, self.reference, self.bindings)

    def test_missing_reference_refuses(self):
        self.reference['keys'].pop(next(iter(self.reference['keys'])))
        with self.assertRaises(ValueError):
            b.validate(self.groups, self.reference, self.bindings)

    def test_all_plan_keys_have_manifest_rows(self):
        paths = {b.manifest_for('a')[0], b.manifest_for('cv2-a')[0]}
        manifests = {p: {a['key'] for a in b.read(b.WORKSPACES/p.replace('$WORKSPACES/', ''))['apps']} for p in paths}
        for board, count in [('5ea',54),('5cd',57),('61b',58)]:
            p = b.read(b.HERE/f'plan-{board}.json')
            self.assertFalse(p['execution_enabled'])
            self.assertEqual(len(p['shards']), count)
            self.assertEqual(p['restore']['state'], 'U13')
            self.assertTrue(p['restore']['unconditional'])
            self.assertEqual(p['restore']['identity_assertions'], 321)
            self.assertEqual((p['window_limit_minutes'],p['stop_new_tests_by_minute']), (45,35))
            for shard in p['shards']:
                self.assertIn(shard['key'], manifests[shard['manifest']])

    def test_execution_refuses_before_lock(self):
        result = subprocess.run([sys.executable, str(b.WORKSPACES/'westlake-harness/scripts/lab/board_run.py'),
                                 str(b.HERE/'plan-61b.json')], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('execution_enabled is false; no lock taken', result.stderr)
        result = subprocess.run([sys.executable, str(b.HERE/'draft_guard.py'), 'apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 78)
        self.assertIn('no device or lock action', result.stdout)


if __name__ == '__main__':
    unittest.main()
