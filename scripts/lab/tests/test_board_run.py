#!/usr/bin/env python3
"""board_run: the dispatch text carries every fixed rule; a plan missing a field or reusing an output dir is refused."""
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

HERE = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(HERE))
import board_run  # noqa: E402

EXAMPLE = HERE.parents[1] / 'knowledge/smoke/example-board-run.json'


class BoardRun(unittest.TestCase):
    def transaction(self, smoke_rc=0, cleanup_rc=0, smoke_error=False, deploy_rc=None):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text())
            plan.update(out=str(Path(d) / 'out'), shards=[], before_unlock=['rollback-verify'])
            if deploy_rc is not None:
                plan['after_lock'] = ['deploy-overlay']
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            def run(argv, **kwargs):
                calls.append(argv)
                if 'held' in argv:
                    return subprocess.CompletedProcess(argv, 0, stdout=plan['lane']+' 123')
                if any('activation_smoke.py' in str(x) for x in argv):
                    if smoke_error: raise OSError('transport failure')
                    return subprocess.CompletedProcess(argv, smoke_rc)
                if argv == ['deploy-overlay']:
                    return subprocess.CompletedProcess(argv, deploy_rc)
                return subprocess.CompletedProcess(argv, cleanup_rc if argv == ['rollback-verify'] else 0)
            with patch.object(board_run.subprocess, 'run', side_effect=run):
                if cleanup_rc:
                    with self.assertRaisesRegex(RuntimeError, 'lock retained'):
                        board_run.main([str(p)])
                elif smoke_error:
                    with self.assertRaises(OSError): board_run.main([str(p)])
                else:
                    self.assertEqual(board_run.main([str(p)]), int(bool(smoke_rc or deploy_rc)))
            report = json.loads((Path(d)/'out/board-run-result.json').read_text())
            self.assertEqual(report['before_unlock'], cleanup_rc)
        events = ['rollback' if x == ['rollback-verify'] else 'deploy' if x == ['deploy-overlay'] else
                  'smoke' if any('activation_smoke.py' in str(y) for y in x) else 'unlock' if 'unlock' in x else 'other'
                  for x in calls]
        if deploy_rc is not None:
            self.assertLess(events.index('deploy'), events.index('rollback'))
            if deploy_rc: self.assertNotIn('smoke', events)
            else: self.assertLess(events.index('deploy'), events.index('smoke'))
        if cleanup_rc: self.assertNotIn('unlock', events)
        else: self.assertLess(events.index('rollback'), events.index('unlock'))

    def test_seal_makes_run_dir_undeletable(self):
        import os, shutil
        d = tempfile.mkdtemp()
        try:
            run = Path(d) / 'v1' / 'serial' / 'key'
            run.mkdir(parents=True)
            (run / 'hilog.txt').write_text('x')
            board_run.seal(Path(d) / 'v1')
            self.assertFalse(os.access(run / 'hilog.txt', os.W_OK))
            with self.assertRaises(PermissionError):
                (run / 'hilog.txt').unlink()          # what git clean / rm would do
            self.assertTrue((run / 'hilog.txt').exists())
        finally:
            subprocess.run(['chmod', '-R', 'u+w', d]); shutil.rmtree(d)

    def test_rollback_precedes_unlock_after_pass(self): self.transaction()
    def test_rollback_precedes_unlock_after_smoke_fail(self): self.transaction(smoke_rc=1)
    def test_rollback_precedes_unlock_after_exception(self): self.transaction(smoke_error=True)
    def test_failed_rollback_keeps_lock(self): self.transaction(cleanup_rc=2)
    def test_deploy_runs_after_lock_before_smoke(self): self.transaction(deploy_rc=0)
    def test_failed_deploy_skips_smoke_still_rolls_back(self): self.transaction(deploy_rc=3)

    def test_batch_stop_skips_remaining_shards_but_restores(self):
        self.shard_exit(2, expected_batches=1)

    def test_shard_rc1_all_records_wrapped_continues(self):
        # bms_batch exits 1 even when the shard finished every key (focus gate stays foreground_unconfirmed):
        # an all-wrapped rc=1 shard must NOT stop the board -> both shards run, board_run returns 0.
        self.shard_rc1({'test-key': 'foreground_unconfirmed'}, expected_batches=2, expected_return=0)

    def test_shard_rc1_started_record_stops(self):
        # a 'started' (or 'batch_interrupted', or a missing) record means the shard did not finish on its own ->
        # still stop the remaining shards; board_run returns 1.
        self.shard_rc1({'test-key': 'started'}, expected_batches=1, expected_return=1)

    def test_shard_rc1_missing_record_stops(self):
        # rc=1 with no record written at all -> cannot confirm wrap-up -> stop.
        self.shard_rc1({}, expected_batches=1, expected_return=1)

    def test_successful_shard_continues_next_shard(self):
        self.shard_exit(0, expected_batches=2)

    def test_cleanup_failure_after_shard_stop_retains_lock(self):
        self.shard_exit(2, expected_batches=1, cleanup_rc=2)

    def test_interrupted_shard_skips_remaining_shards_but_restores(self):
        self.shard_exit(-15, expected_batches=1)

    def shard_exit(self, first_rc, expected_batches, cleanup_rc=0):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text())
            keys = Path(d) / 'keys.txt'; keys.write_text('test-key\n')
            shards = [dict(name=n, keys_file=str(keys), manifest='manifest.json', input_root=d)
                      for n in ('first', 'second')]
            plan.update(out=str(Path(d) / 'out'), shards=shards,
                        before_unlock=['rollback-verify'])
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            def run(argv, **kwargs):
                calls.append(argv)
                if 'held' in argv:
                    return subprocess.CompletedProcess(argv, 0, stdout=plan['lane']+' 123')
                if str(board_run.BATCH) in argv:
                    count = sum(str(board_run.BATCH) in a for a in calls)
                    return subprocess.CompletedProcess(argv, first_rc if count == 1 else 0)
                if argv == ['rollback-verify']:
                    return subprocess.CompletedProcess(argv, cleanup_rc)
                return subprocess.CompletedProcess(argv, 0)
            with patch.object(board_run.subprocess, 'run', side_effect=run):
                if cleanup_rc:
                    with self.assertRaisesRegex(RuntimeError, 'lock retained'):
                        board_run.main([str(p)])
                else:
                    self.assertEqual(board_run.main([str(p)]), first_rc)
            report = json.loads((Path(d)/'out/board-run-result.json').read_text())
            self.assertEqual(len(report['shards']), expected_batches)
            self.assertEqual(report['before_unlock'], cleanup_rc)
        self.assertEqual(sum(str(board_run.BATCH) in a for a in calls), expected_batches)
        restore = calls.index(['rollback-verify'])
        if cleanup_rc:
            self.assertFalse(any('unlock' in a for a in calls))
        else:
            unlock = next(i for i,a in enumerate(calls) if 'unlock' in a)
            self.assertLess(restore, unlock)

    def shard_rc1(self, records, expected_batches, expected_return):
        """First shard exits 1 after writing `records` ({key: status}) into <sout>/<serial>/<key>/record.json;
        board_run continues iff every requested key wrapped up, else stops. Always a clean rollback+unlock."""
        calls = []
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text())
            keys = Path(d) / 'keys.txt'; keys.write_text('test-key\n')
            shards = [dict(name=n, keys_file=str(keys), manifest='manifest.json', input_root=d)
                      for n in ('first', 'second')]
            plan.update(out=str(Path(d) / 'out'), shards=shards, before_unlock=['rollback-verify'])
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            def run(argv, **kwargs):
                calls.append(argv)
                if 'held' in argv:
                    return subprocess.CompletedProcess(argv, 0, stdout=plan['lane']+' 123')
                if str(board_run.BATCH) in argv:
                    count = sum(str(board_run.BATCH) in a for a in calls)
                    if count == 1:  # first shard: write records then exit 1 (the all-captured-only gate)
                        sout = Path(argv[argv.index('--out') + 1])
                        for key, status in records.items():
                            rec = sout / plan['serial'] / key / 'record.json'
                            rec.parent.mkdir(parents=True, exist_ok=True)
                            rec.write_text(json.dumps({'status': status}))
                        return subprocess.CompletedProcess(argv, 1)
                    return subprocess.CompletedProcess(argv, 0)
                return subprocess.CompletedProcess(argv, 0)
            with patch.object(board_run.subprocess, 'run', side_effect=run):
                self.assertEqual(board_run.main([str(p)]), expected_return)
            report = json.loads((Path(d) / 'out/board-run-result.json').read_text())
            self.assertEqual(len(report['shards']), expected_batches)
            self.assertEqual(report['before_unlock'], 0)
        self.assertEqual(sum(str(board_run.BATCH) in a for a in calls), expected_batches)
        restore = calls.index(['rollback-verify'])
        unlock = next(i for i, a in enumerate(calls) if 'unlock' in a)
        self.assertLess(restore, unlock)

    def test_detach_starts_new_session_and_returns(self):
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text())
            plan.update(out=str(Path(d) / 'out'), shards=[])
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            with patch.object(board_run.subprocess, 'Popen') as popen, \
                 patch.object(board_run.subprocess, 'run') as run:
                popen.return_value.pid = 4242
                self.assertEqual(board_run.main([str(p), '--detach']), 0)
            self.assertTrue(popen.call_args.kwargs['start_new_session'])
            self.assertNotIn('--detach', popen.call_args.args[0])
            run.assert_not_called()                                   # no lock taken by the parent
            self.assertFalse((Path(d) / 'out').exists())              # the child creates it
            self.assertTrue((Path(d) / 'out.board-run.log').exists())

    def test_offline_precheck_required(self):
        self.assertIn('offline_precheck', board_run.precheck_problem(None))
        good = {'hypothesis': 'h', 'evidence': ['.octos/KNOWLEDGE-DIGEST.md'], 'result': 'not-falsified',
                'expect': {'confirm': 'marker hit and key lit', 'refute': 'marker hit, same fatal'}}
        self.assertIn('discriminate', board_run.precheck_problem(dict(good, expect={'confirm': 'x'})))
        self.assertIsNone(board_run.precheck_problem(good))
        self.assertIn('not found', board_run.precheck_problem(dict(good, evidence=['no/such/file'])))
        self.assertIn('falsified', board_run.precheck_problem(dict(good, result='falsified')))
        self.assertIn('empty', board_run.precheck_problem(dict(good, evidence=[])))
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text()); plan.pop('offline_precheck')
            plan.update(out=str(Path(d) / 'out'), shards=[])
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            with patch.object(board_run.subprocess, 'run') as run:
                with self.assertRaises(SystemExit) as cm:
                    board_run.main([str(p)])
            self.assertIn('offline precheck', str(cm.exception))
            run.assert_not_called()                                   # refused before LOCK

    def test_probe_tag_in_expect_must_be_a_smoke_marker(self):
        pre = {'expect': {'confirm': 'one [N11d-PROBE] branch=... line', 'refute': 'no [N11d-PROBE] line appears'}}
        with tempfile.TemporaryDirectory() as d:
            spec = Path(d) / 'smoke.json'
            spec.write_text(json.dumps({'fixes': [{'id': 'N10b', 'markers': ['\\[N10b-JNI-OWNER\\] preloaded']}]}))
            self.assertIn('N11d-PROBE', board_run.silent_probe_problem(pre, spec))    # the N11d r2 window
            spec.write_text(json.dumps({'fixes': [{'id': 'N11e', 'markers': ['\\[N11d-PROBE\\] entry']}]}))
            self.assertIsNone(board_run.silent_probe_problem(pre, spec))
            self.assertIn('unreadable', board_run.silent_probe_problem(pre, Path(d) / 'none.json'))
        self.assertIsNone(board_run.silent_probe_problem({'expect': {'confirm': 'key lit', 'refute': 'dark'}}, 'x'))

    def test_dispatch_has_every_rule(self):
        text = board_run.dispatch_text(json.loads(EXAMPLE.read_text()), EXAMPLE)
        for rule in board_run.RULES:
            self.assertIn(rule, text)
        for must in ('--hilog', 'LOCK', '冒烟', '只跑一个', '不删'):
            self.assertIn(must, text)

    def test_missing_field_refused(self):
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text()); del plan['smoke_spec']
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            r = subprocess.run([sys.executable, str(HERE / 'board_run.py'), str(p)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('plan missing smoke_spec', r.stderr)

    def test_existing_output_refused_before_lock(self):
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text()); plan['out'] = d     # exists already
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            r = subprocess.run([sys.executable, str(HERE / 'board_run.py'), str(p)], capture_output=True, text=True)
            self.assertNotEqual(r.returncode, 0); self.assertIn('exists', r.stderr)


if __name__ == '__main__':
    unittest.main()
