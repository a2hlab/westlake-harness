import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('u9_partial_hook', H / 'native_window.py')
hook = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hook)


class PartialRetention(unittest.TestCase):
    def run_case(self, confirmed, smoke=True):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runner/smoke').mkdir(parents=True)
            (root / 'runner/smoke/smoke-result.json').write_text(json.dumps({'passed': smoke}))
            (root / 'transaction').mkdir()
            (root / 'transaction/journal.json').write_text('{}')
            facts = root / 'runner/original/run/serial/facts.txt'
            facts.parent.mkdir(parents=True)
            facts.write_text('TOTAL keys=3 screenshots_captured=6/6 alive_t5=3 alive_t20=3\n')
            keys = root / 'keys.txt'
            keys.write_text('a b c d')
            plan = root / 'plan.json'
            plan.write_text(json.dumps({
                'shards': [{'name': 'original', 'keys_file': str(keys)}],
                'partial_retention': {
                    'approved_ack': 'ACK(80) 2026-10-01T18:33:43+0800',
                    'outer_read_confirmed': confirmed,
                },
            }))
            with patch.object(hook, 'vm', return_value=0) as rollback, patch.object(
                hook.subprocess, 'run', return_value=SimpleNamespace(returncode=0)
            ) as command:
                self.assertEqual(hook.finish('test', root, plan), 0)
                argv = command.call_args.args[0][-1]
                return rollback.call_count, argv

    def test_incomplete_shard_requires_outer_read(self):
        count, command = self.run_case(False)
        self.assertEqual(count, 1)
        self.assertIn('--read-baseline', command)

    def test_explicit_outer_read_allows_partial_but_verifies_identity(self):
        count, command = self.run_case(True)
        self.assertEqual(count, 0)
        self.assertIn('--verify-final', command)

    def test_outer_read_never_overrides_smoke_failure(self):
        count, command = self.run_case(True, smoke=False)
        self.assertEqual(count, 1)
        self.assertIn('--read-baseline', command)

    def test_darwin_identity_read_routes_to_vm_without_local_device_io(self):
        with patch.object(hook.sys, 'platform', 'darwin'), patch.object(
            hook.subprocess, 'run', return_value=SimpleNamespace(returncode=0)
        ) as command, patch.object(hook.u, 'DeviceIO') as device:
            hook.verify_final('serial', Path('/tmp/u9-test'))
            device.assert_not_called()
            self.assertEqual(command.call_args.args[0][:3], ['orb', '-m', 'a2hlab'])
            self.assertIn('--verify-final', command.call_args.args[0][-1])


if __name__ == '__main__':
    unittest.main()
