#!/usr/bin/env python3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bind_status as bs  # noqa: E402


class BindStatus(unittest.TestCase):
    def _mk(self, root, key, text):
        d = root / 'run' / 'ser' / key
        d.mkdir(parents=True)
        (d / 'hilog.txt').write_text(text)

    def test_three_states(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._mk(root, 'key-bound', 'x [B43-BIND] handleBindApplication returned OK\n')
            self._mk(root, 'key-fatal', 'x DfxFaultLogger: Pid:100\n')
            self._mk(root, 'key-unbound', 'x nothing interesting\n')
            rows = {r['key']: r for r in bs.scan([root])}
            self.assertEqual(rows['key-bound']['key_status'], 'bound')
            self.assertEqual(rows['key-fatal']['key_status'], 'fatal_before_bind')
            self.assertEqual(rows['key-unbound']['key_status'], 'unbound_at_capture')
            # fatal + bound in the same run -> bound
            self._mk(root, 'key-both', 'x [B43-BIND] handleBindApplication returned OK\nx JniAbort\n')
            rows = {r['key']: r for r in bs.scan([root])}
            self.assertEqual(rows['key-both']['key_status'], 'bound')

    def test_multiple_runs_any_bound_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._mk(root, 'key-x', 'x nothing\n')
            self._mk(root / 'run2', 'key-x', 'x [B43-BIND] handleBindApplication returned OK\n')
            rows = {r['key']: r for r in bs.scan([root])}
            self.assertEqual(rows['key-x']['runs'], 2)
            self.assertEqual(rows['key-x']['key_status'], 'bound')


class BindFailed(unittest.TestCase):
    def test_bind_failed_with_caused(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import bind_status as bs
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / 'run' / 'ser' / 'key-bf'
            d.mkdir(parents=True)
            (d / 'hilog.txt').write_text(
                'x [B43-BIND] ensureBindApplication FAILED\n'
                'x Caused by: java.lang.IllegalStateException: ScanCallback not registered\n')
            rows = {r['key']: r for r in bs.scan([root])}
            self.assertEqual(rows['key-bf']['key_status'], 'bind_failed')
            self.assertEqual(rows['key-bf']['bind_failed_runs'], 1)
            self.assertIn('ScanCallback', rows['key-bf']['caused'])

    def test_bind_failed_beats_fatal(self):
        import sys as _sys
        _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        import bind_status as bs
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            d = root / 'run' / 'ser' / 'key-bf2'
            d.mkdir(parents=True)
            (d / 'hilog.txt').write_text(
                'x [B43-BIND] ensureBindApplication FAILED\n'
                'x JniAbort\n')
            rows = {r['key']: r for r in bs.scan([root])}
            self.assertEqual(rows['key-bf2']['key_status'], 'bind_failed')


if __name__ == '__main__':
    unittest.main()
