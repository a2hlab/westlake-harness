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

    def test_rollback_precedes_unlock_after_pass(self): self.transaction()
    def test_rollback_precedes_unlock_after_smoke_fail(self): self.transaction(smoke_rc=1)
    def test_rollback_precedes_unlock_after_exception(self): self.transaction(smoke_error=True)
    def test_failed_rollback_keeps_lock(self): self.transaction(cleanup_rc=2)
    def test_deploy_runs_after_lock_before_smoke(self): self.transaction(deploy_rc=0)
    def test_failed_deploy_skips_smoke_still_rolls_back(self): self.transaction(deploy_rc=3)

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
