"""COMMERCIAL-G07 checks for scripts/lab/board_run.py per-shard wait_seconds/shots (offline, no device)."""
import json, math, sys, tempfile, unittest
from pathlib import Path
from unittest import mock
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / 'scripts/lab'))
sys.path.insert(0, str(REPO / 'benchmark/2026-09-28-bms-route-deploy/batch'))
import board_run
import bms_batch

PLAN = {'serial': '5ea34a4500000000000000001123012c', 'lane': 'cc-video'}
SHARD = {'name': '01-genshin', 'manifest': '/m.json', 'input_root': '/in'}


def historical(shard, cutoff=None):
    # the literal pre-G07 construction, copied from board_run.py @ ba67fa17bd
    cmd = [sys.executable, str(board_run.BATCH), '--execute', '--serial', PLAN['serial'], '--lane', PLAN['lane'],
           '--manifest', board_run.expand(shard['manifest']), '--input-root', board_run.expand(shard['input_root']),
           '--keys', 'genshin', '--reinstall', '--hilog', '--shots', '5,20', '--out', '/o/01-genshin']
    return cmd + (['--stop-new-keys-at', str(cutoff)] if cutoff is not None else [])


class Sampling(unittest.TestCase):
    def test_default_unchanged(self):
        for cutoff in (None, 1792567652.5):
            got = board_run.shard_command(PLAN, dict(SHARD), 'genshin', Path('/o/01-genshin'), cutoff)
            self.assertEqual(got, historical(SHARD, cutoff))
            self.assertNotIn('--wait', got)
        self.assertIsNone(board_run.shard_sampling_problem(dict(SHARD)))

    def test_sixty_second_observation(self):
        shard = dict(SHARD, wait_seconds=60, shots=[5, 20, 60])
        self.assertIsNone(board_run.shard_sampling_problem(shard))
        got = board_run.shard_command(PLAN, shard, 'genshin', Path('/o/01-genshin'), 1792567652.5)
        i = got.index('--shots'); self.assertEqual(got[i + 1], '5,20,60')
        j = got.index('--wait'); self.assertEqual(got[j + 1], '60')
        for flag in ('--execute', '--reinstall', '--hilog', '--stop-new-keys-at'):
            self.assertIn(flag, got)
        # the passed strings are accepted by bms_batch's own parsers
        self.assertEqual(bms_batch.shot_offsets(got[i + 1]), [5.0, 20.0, 60.0])
        self.assertEqual(float(got[j + 1]), 60.0)

    def test_fractional_and_shots_only(self):
        shard = dict(SHARD, shots=[2.5, 30])
        got = board_run.shard_command(PLAN, shard, 'genshin', Path('/o/01-genshin'), None)
        self.assertEqual(got[got.index('--shots') + 1], '2.5,30'); self.assertNotIn('--wait', got)
        self.assertIsNone(board_run.shard_sampling_problem(dict(SHARD, wait_seconds=120)))

    def test_invalid_rejected_with_field(self):
        bad = [('wait_seconds', -1), ('wait_seconds', 0), ('wait_seconds', 121), ('wait_seconds', True),
               ('wait_seconds', math.nan), ('wait_seconds', math.inf), ('wait_seconds', '60'), ('wait_seconds', None),
               ('shots', [20, 5]), ('shots', [5, 5]), ('shots', []), ('shots', '5,20;reboot'), ('shots', [5, True]),
               ('shots', [5, 121]), ('shots', [5, math.nan]), ('shots', [-5, 20]), ('shots', ['5', '20']),
               ('shots', list(range(1, 34))), ('wait_seconds', 10**400), ('shots', [5, 10**400])]
        for field, value in bad:
            with self.subTest(field=field, value=value):
                problem = board_run.shard_sampling_problem(dict(SHARD, **{field: value}))
                self.assertIsNotNone(problem); self.assertIn(field, problem)
        problem = board_run.shard_sampling_problem(dict(SHARD, wait_seconds=30, shots=[5, 20, 60]))
        self.assertIn('wait_seconds', problem); self.assertIn('last shot', problem)

    def test_main_refuses_before_lock_or_device(self):
        cases = [dict(SHARD, keys_file='/k', wait_seconds=121), dict(SHARD, keys_file='/k', shots=[60, 20]),
                 dict(SHARD, keys_file='/k', wait_seconds=True), dict(SHARD, keys_file='/k', wait_seconds=10**400),
                 dict(SHARD, keys_file='/k', shots=[5, 10**400])]
        for shard in cases:
            with self.subTest(shard=shard), tempfile.TemporaryDirectory() as tmp:
                plan = dict(PLAN, entry='91', why='g07 test', board='/nonexistent/board.md', out=str(Path(tmp) / 'out'),
                            smoke_spec='/nonexistent/smoke.json', execution_enabled=True, shards=[shard])
                path = Path(tmp) / 'plan.json'; path.write_text(json.dumps(plan))
                with mock.patch.object(board_run.subprocess, 'run', side_effect=AssertionError('device/lock call')), \
                     mock.patch.object(board_run.subprocess, 'Popen', side_effect=AssertionError('spawn')):
                    with self.assertRaises(SystemExit) as cm:
                        board_run.main([str(path)])
                    self.assertIn('REFUSE', str(cm.exception)); self.assertIn('no lock taken', str(cm.exception))
                    with self.assertRaises(SystemExit):
                        board_run.main([str(path), '--dispatch'])
                self.assertFalse((Path(tmp) / 'out').exists())


if __name__ == '__main__':
    unittest.main()
