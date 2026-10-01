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
    def transaction(self, smoke_rc=0, cleanup_rc=0, smoke_error=False):
        calls = []
        with tempfile.TemporaryDirectory() as d:
            plan = json.loads(EXAMPLE.read_text())
            plan.update(out=str(Path(d) / 'out'), shards=[], before_unlock=['rollback-verify'])
            p = Path(d) / 'p.json'; p.write_text(json.dumps(plan))
            def run(argv, **kwargs):
                calls.append(argv)
                if 'held' in argv:
                    return subprocess.CompletedProcess(argv, 0, stdout=plan['lane']+' 123')
                if any('activation_smoke.py' in str(x) for x in argv):
                    if smoke_error: raise OSError('transport failure')
                    return subprocess.CompletedProcess(argv, smoke_rc)
                return subprocess.CompletedProcess(argv, cleanup_rc if argv == ['rollback-verify'] else 0)
            with patch.object(board_run.subprocess, 'run', side_effect=run):
                if cleanup_rc:
                    with self.assertRaisesRegex(RuntimeError, 'lock retained'):
                        board_run.main([str(p)])
                elif smoke_error:
                    with self.assertRaises(OSError): board_run.main([str(p)])
                else:
                    self.assertEqual(board_run.main([str(p)]), int(bool(smoke_rc)))
            report = json.loads((Path(d)/'out/board-run-result.json').read_text())
            self.assertEqual(report['before_unlock'], cleanup_rc)
        events = ['rollback' if x == ['rollback-verify'] else 'unlock' if 'unlock' in x else 'other' for x in calls]
        if cleanup_rc: self.assertNotIn('unlock', events)
        else: self.assertLess(events.index('rollback'), events.index('unlock'))

    def test_rollback_precedes_unlock_after_pass(self): self.transaction()
    def test_rollback_precedes_unlock_after_smoke_fail(self): self.transaction(smoke_rc=1)
    def test_rollback_precedes_unlock_after_exception(self): self.transaction(smoke_error=True)
    def test_failed_rollback_keeps_lock(self): self.transaction(cleanup_rc=2)

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
