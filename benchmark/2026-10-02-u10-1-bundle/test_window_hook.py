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


if __name__ == '__main__':
    unittest.main()
