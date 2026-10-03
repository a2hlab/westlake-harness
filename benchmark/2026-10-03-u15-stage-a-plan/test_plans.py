import copy
import json
import subprocess
import sys
import unittest

import build_plans as build


class DisabledPlans(unittest.TestCase):
    def setUp(self):
        self.reference = build.read(build.HERE / 'provisional-reference.json')
        self.plans = {board: build.read(build.HERE / f'plan-{board}.json') for board in build.SERIALS}

    def groups(self):
        groups = build.groups_from(build.read(build.HERE / 'inputs/key-table.json'))
        for board, keys in build.read(build.HERE / 'results.json')['supplemental_keys'].items():
            groups[board].append(({'name': 'signed-gain-protection', 'runs_per_key': 1}, keys))
        return groups

    def test_provisional_reference_and_gain_coverage(self):
        self.assertEqual(len(build.validate(self.groups(), self.reference)), 129)
        self.assertEqual(self.reference['status'], 'pending-U14-promotion')
        self.assertEqual(sum(row['lit'] for row in self.reference['tallies'].values()), 129)
        self.assertEqual(len(build.read(build.HERE / 'signed-gains.json')), 3)
        rows = [row for row in self.plans['5cd']['shards'] if row['key'] == 'termux']
        self.assertEqual([(row['category'], row['trial']) for row in rows], [('white-watch', 1)])

    def test_bindings_null_disabled_restore_pending(self):
        for plan in self.plans.values():
            self.assertFalse(plan['execution_enabled'])
            self.assertFalse(plan['rollout_ready'])
            self.assertTrue(all(value is None for value in plan['bindings'].values()))
            self.assertIsNone(plan['restore']['package'])
            self.assertTrue(plan['restore']['unconditional'])
            self.assertEqual((plan['window_limit_minutes'], plan['stop_new_tests_by_minute']), (45, 35))

    def test_duplicate_rejected(self):
        groups = self.groups()
        groups['5ea'][-1][1].append(groups['5ea'][0][1][0])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            build.validate(groups, self.reference)

    def test_missing_reference_rejected(self):
        groups = self.groups()
        groups['5ea'][-1][1].clear()
        with self.assertRaisesRegex(ValueError, 'missing'):
            build.validate(groups, self.reference)

    def test_markers_match_raw_bare_hex_not_invented_prefix(self):
        markers = build.read(build.HERE / 'inputs/markers.json')
        for marker in markers:
            build.validate_marker(marker)
            self.assertGreater(marker['line'], 0)
            self.assertTrue(marker['source'].endswith('/hilog.txt'))
        marker = copy.deepcopy(next(marker for marker in markers if marker['id'] == 'flutter-anw'))
        marker['regex'] = marker['regex'].replace('(?:0x)?', '0x')
        with self.assertRaisesRegex(ValueError, 'original hilog'):
            build.validate_marker(marker)

    def test_zero_pointer_is_not_success(self):
        marker = copy.deepcopy(next(marker for marker in build.read(build.HERE / 'inputs/markers.json') if marker['id'] == 'flutter-anw'))
        marker['text'] = 'eglCreateWindowSurface: detected ANW shim 00000000, unwrapped to OH NativeWindow=00000000'
        with self.assertRaisesRegex(ValueError, 'zero pointer'):
            build.validate_marker(marker)

    def test_pending_61b_and_consecutive_lottery(self):
        self.assertEqual(self.plans['61b']['status'], 'pending-61b-reconnect')
        self.assertEqual([len(self.plans[board]['shards']) for board in ('5ea', '5cd', '61b')], [58, 60, 58])
        for plan in self.plans.values():
            for key in {row['key'] for row in plan['shards'] if row['category'] == 'lottery'}:
                positions = [number for number, row in enumerate(plan['shards']) if row['key'] == key]
                self.assertEqual(positions, list(range(positions[0], positions[0] + 6)))

    def test_default_guard_no_device(self):
        result = subprocess.run([sys.executable, str(build.HERE / 'draft_guard.py'), 'apply'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 78)
        self.assertIn('no device or lock action', result.stdout)

    def test_source_snapshot_pins(self):
        for row in build.read(build.HERE / 'inputs/provenance.json'):
            self.assertEqual(build.sha(build.HERE / row['snapshot']), row['snapshot_sha256'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
