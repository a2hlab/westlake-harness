"""Offline admission checks for the supplemental plans; never opens a device."""
import csv
import json
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parent
ORIGINAL = HERE.parent / '2026-10-02-u10-1-bundle'


class SupplementalPlans(unittest.TestCase):
    def test_same_safety_chain_and_base_per_board(self):
        for board in ('5ea', '5cd', '61b'):
            with self.subTest(board=board):
                old = json.loads((ORIGINAL / 'window' / f'plan-{board}.json').read_text())
                new = json.loads((HERE / 'retry-plans' / f'plan-{board}.json').read_text())
                for field in ('serial', 'smoke_spec', 'window_limit_minutes', 'stop_new_tests_by_minute'):
                    self.assertEqual(new[field], old[field])
                for field in ('after_lock', 'before_unlock'):
                    self.assertEqual([x.replace('/retry-window/boards/', '/window/boards/')
                                      for x in new[field]], old[field])
                self.assertIn('--apply', new['after_lock'])
                self.assertIn('--finish', new['before_unlock'])
                self.assertIn('--restored-spec', new['before_unlock'])
                self.assertIn('/retry-window/boards/$U101_RUN_ID/', new['out'])
                self.assertTrue(new['approval'].startswith('PROPOSED'))

    def test_exact_prediction_subsets_cover_unobserved_keys(self):
        with (ORIGINAL / 'predictions-v5.csv').open() as f:
            expected = {r['key']: r for r in csv.DictReader(f)}
        all_retry = []
        for board, count in [('5ea', 55), ('5cd', 26), ('61b', 56)]:
            plan = json.loads((HERE / 'retry-plans' / f'plan-{board}.json').read_text())
            keys = []
            for shard in plan['shards']:
                key_file = HERE / 'retry-plans' / Path(shard['keys_file']).name
                keys += key_file.read_text().split()
            with (HERE / 'retry-plans' / f'predictions-{board}.csv').open() as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(len(keys), count)
            self.assertEqual({r['key'] for r in rows}, set(keys))
            for row in rows:
                self.assertEqual(row, expected[row['key']])
            all_retry += keys
        fivecd = json.loads((HERE / 'retry-plans/plan-5cd.json').read_text())
        retained = fivecd['retained_observations']['5cd_completed_keys']
        retained += (ORIGINAL / 'window/keys-5cd-original.txt').read_text().split()
        self.assertEqual(len(all_retry + retained), 166)
        self.assertEqual(set(all_retry + retained), set(expected))
        self.assertEqual(len(set(all_retry + retained)), 166)
        self.assertEqual([s['name'] for s in fivecd['shards']], ['cv2'])


if __name__ == '__main__':
    unittest.main()
