"""Reproduce the real stale-capture failure without device I/O."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import u7_executor as u

class VerificationEvidenceTests(unittest.TestCase):
    def test_failed_apply_then_rollback_keeps_separate_captures(self):
        with tempfile.TemporaryDirectory() as td:
            io = u.DeviceIO.__new__(u.DeviceIO)
            io.out = Path(td)
            io.board = object()
            io.serial = 'offline'
            io.boot = 'unchanged'
            io.ps = lambda: [dict(name='appspawn-x', uid=0, pid=10, ppid=1),
                             dict(name='appspawn-x', uid=2001, pid=20, ppid=10)]
            digest = 'a' * 64
            io.snapshot = lambda paths: ({p: digest for p in paths}, [])
            io.hashes = lambda paths: {p: digest for p in paths}
            io.shell = lambda command: 'offline maps' if command.endswith('/maps') else ''
            captures = []
            def launch(board, app, remote, out, record):
                marker = out / 'settle-0.json'
                if marker.exists():
                    raise RuntimeError('refuse stale local evidence')
                marker.write_text('original capture ' + str(len(captures)))
                captures.append(out)
            io.b = SimpleNamespace(parse_bundle=lambda *args: dict(uid=2001, desktop_activity='Main'),
                                   cold_stop=Mock(return_value=True), desktop_launch=launch)
            with patch.object(u.time, 'sleep'), patch.object(u.native, 'check_maps',
                    side_effect=[dict(passed=False), dict(passed=True)]):
                with self.assertRaisesRegex(RuntimeError, 'single ART'):
                    io.verify({u.HOST:digest}, 'generation')
                result = io.verify({u.HOST:digest}, 'generation')
            self.assertEqual(len(captures), 2)
            self.assertNotEqual(captures[0], captures[1])
            self.assertEqual((captures[0]/'settle-0.json').read_text(), 'original capture 0')
            self.assertEqual((captures[1]/'settle-0.json').read_text(), 'original capture 1')
            self.assertEqual(Path(result['evidence_directory']), captures[1])
            self.assertTrue((captures[1]/'child-20-maps.txt').exists())
            self.assertEqual([c.args[3] for c in io.b.cold_stop.call_args_list], captures)

if __name__ == '__main__':
    unittest.main()
