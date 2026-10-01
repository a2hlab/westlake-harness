"""Offline checks for the production runner and its loaded-instance gate."""
import csv
import json
import os
from pathlib import Path
import sys
import unittest

HERE = Path(__file__).resolve().parent
W = HERE.parents[2]
os.environ.setdefault('WORKSPACES', str(W))
os.environ.setdefault('U101_RUN_ID', 'offline-preflight-only')
sys.path.insert(0, str(W / 'westlake-harness/scripts/lab'))
import board_run
import activation_smoke


class ProposedPlans(unittest.TestCase):
    def test_production_precheck_and_full_prediction_coverage(self):
        keys = []
        for board in ('5ea', '5cd', '61b'):
            plan = json.loads((HERE / f'window/plan-{board}.json').read_text())
            self.assertIsNone(board_run.precheck_problem(plan['offline_precheck']))
            smoke = board_run.expand(plan['smoke_spec'])
            self.assertIsNone(board_run.silent_probe_problem(plan['offline_precheck'], smoke))
            self.assertEqual(plan['stop_new_tests_by_minute'], 35)
            self.assertLessEqual(plan['window_limit_minutes'], 45)
            self.assertIn('--apply', plan['after_lock'])
            self.assertIn('--finish', plan['before_unlock'])
            for shard in plan['shards']:
                self.assertTrue(Path(board_run.expand(shard['manifest'])).is_file())
                keys += Path(board_run.expand(shard['keys_file'])).read_text().split()
        with (HERE / 'predictions-v5.csv').open() as f:
            predicted = {row['key'] for row in csv.DictReader(f)}
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(set(keys), predicted)

    def test_same_inode_at_two_bases_counts_as_two_loaded_instances(self):
        maps = '\n'.join([
            '1000-2000 r--p 00000000 00:01 7 /route/liboh_adapter_bridge.so',
            '2000-3000 r-xp 00001000 00:01 7 /route/liboh_adapter_bridge.so',
            '9000-a000 r--p 00000000 00:01 7 /route/liboh_adapter_bridge.so',
        ])
        copies = activation_smoke.copies(maps, ['liboh_adapter_bridge.so'])
        self.assertEqual(len(copies['liboh_adapter_bridge.so']), 2)
        for p in HERE.glob('window/*.json'):
            spec = json.loads(p.read_text())
            if 'probe' not in spec:
                continue
            probe = spec['probe']
            self.assertTrue(set(probe.get('expect_copies', {})) <= set(probe['single_copy']))


if __name__ == '__main__':
    unittest.main()
