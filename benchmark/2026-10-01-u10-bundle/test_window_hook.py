import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('u10_window_hook', Path(__file__).with_name('window_hook.py'))
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class RecoveryOrder(unittest.TestCase):
    def run_finish(self, status, fail=False):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'transaction').mkdir()
            (root / 'transaction/journal.json').write_text(json.dumps({'status': status}))
            events = []
            def execute(*args, **kwargs):
                events.append('rollback')
                self.assertTrue(kwargs['rollback'])
                if fail:
                    raise subprocess.CalledProcessError(1, 'rollback')
            with patch.object(hook, 'executor', execute), patch.object(hook, 'verify', lambda *a: events.append('verify')), patch.object(hook.subprocess, 'run', lambda *a, **k: events.append('smoke')):
                if fail:
                    with self.assertRaises(subprocess.CalledProcessError):
                        hook.finish('serial', root, Path('restored.json'))
                else:
                    hook.finish('serial', root, Path('restored.json'))
            return events

    def test_restore_precedes_smoke_and_final_identity(self):
        self.assertEqual(self.run_finish('active'), ['rollback', 'verify', 'smoke', 'verify'])

    def test_failed_restore_cannot_reach_success_smoke(self):
        self.assertEqual(self.run_finish('recovery_required', True), ['rollback'])

    def test_verified_automatic_rollback_is_not_applied_twice(self):
        self.assertEqual(self.run_finish('rolled_back'), ['verify', 'smoke', 'verify'])


class RetentionDecision(unittest.TestCase):
    def test_smoke_pass_retains_without_redeployment(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            smoke = root / 'runner/smoke'
            smoke.mkdir(parents=True)
            (smoke / 'smoke-result.json').write_text('{"passed": true}')
            with patch.object(hook.sys, 'platform', 'linux'), patch.object(hook, 'retain_candidate') as retain, patch.object(hook, 'executor') as executor:
                hook.finish('serial', root, Path('restored.json'))
                retain.assert_called_once_with('serial', root)
                executor.assert_not_called()

    def test_confirmed_regression_recovers_instead_of_retaining(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'runner/smoke').mkdir(parents=True)
            (root / 'runner/smoke/smoke-result.json').write_text('{"passed": true}')
            (root / 'confirmed-regression.json').write_text('{"confirmed": true}')
            with patch.object(hook, 'retain_candidate') as retain, patch.object(hook, 'verify') as verify, patch.object(hook.subprocess, 'run'):
                hook.finish('serial', root, Path('restored.json'))
                retain.assert_not_called()
                self.assertEqual(verify.call_count, 2)

    def test_final_retention_gate_failure_recovers(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / 'runner/smoke').mkdir(parents=True)
            (root / 'runner/smoke/smoke-result.json').write_text('{"passed": true}')
            with patch.object(hook.sys, 'platform', 'linux'), patch.object(hook, 'retain_candidate', side_effect=AssertionError('identity drift')), patch.object(hook, 'verify') as verify, patch.object(hook.subprocess, 'run'):
                hook.finish('serial', root, Path('restored.json'))
                self.assertTrue((root / 'retention-error.txt').exists())
                self.assertEqual(verify.call_count, 2)


if __name__ == '__main__':
    unittest.main()
