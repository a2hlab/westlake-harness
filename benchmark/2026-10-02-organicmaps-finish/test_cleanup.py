"""Offline rollback cleanup regression: ownership, bounded retry and fail-safe."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/lab'))
import u7_executor as u
spec = importlib.util.spec_from_file_location('executor_fixture', ROOT / 'benchmark/2026-10-01-u7-executor/test_executor.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
GUARD = 'other Android children are live; stop them before deployment'

class CleanupTests(unittest.TestCase):
    def device(self, out):
        io = u.DeviceIO.__new__(u.DeviceIO)
        io.boot = 'boot'; io.out = Path(out); io.board = object()
        io.guard = Mock()
        io.shell = Mock(return_value='BMS dump')
        io.stop = Mock(side_effect=[RuntimeError(GUARD), None])
        io.ps = Mock(return_value=[dict(pid=10, ppid=1, uid=0, name='appspawn-x'),
                                   dict(pid=20, ppid=10, uid=20010983, name='appspawn-x')])
        io.b = types.SimpleNamespace(parse_bundle=Mock(return_value={'uid':20010983}), cold_stop=Mock(return_value=True))
        return io
    def test_guard_cold_stops_then_reenters_original_guard(self):
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.stop_for_rollback()
            self.assertEqual(io.stop.call_count,2)
            self.assertEqual(io.b.cold_stop.call_args.args[1:3],('app.organicmaps',20010983))
            receipt=json.loads(next(Path(td).glob('*/cleanup.json')).read_text())
            self.assertTrue(receipt['quiesced']);self.assertEqual(receipt['parent'],10)
    def test_persistent_respawn_is_bounded_and_refuses(self):
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.stop.side_effect=RuntimeError(GUARD);io.b.cold_stop.return_value=False
            with self.assertRaisesRegex(RuntimeError,GUARD):io.stop_for_rollback()
            self.assertEqual(io.stop.call_count,3);self.assertEqual(io.b.cold_stop.call_count,2)
    def test_clean_stop_has_no_cleanup(self):
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.stop.side_effect=None;io.stop_for_rollback();io.shell.assert_not_called();io.b.cold_stop.assert_not_called()
    def test_unrelated_failure_is_not_retried(self):
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.stop.side_effect=RuntimeError('HDC lost remote status marker')
            with self.assertRaisesRegex(RuntimeError,'HDC lost'):io.stop_for_rollback()
            self.assertEqual(io.stop.call_count,1);io.b.cold_stop.assert_not_called()
    def test_wrong_uid_parent_root_and_unknown_app_refuse(self):
        variants=[{'uid':0},{'uid':None},{'uid':20010984}]
        for value in variants:
            with self.subTest(value=value),tempfile.TemporaryDirectory() as td:
                io=self.device(td);io.b.parse_bundle.return_value=value
                with self.assertRaisesRegex(RuntimeError,'ownership'):io.stop_for_rollback()
                io.b.cold_stop.assert_not_called()
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.ps.return_value[1]['ppid']=99
            with self.assertRaisesRegex(RuntimeError,'ownership'):io.stop_for_rollback()
            io.b.cold_stop.assert_not_called()
    def test_cleanup_transport_failure_keeps_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            io=self.device(td);io.b.cold_stop.side_effect=RuntimeError('transport failure')
            with self.assertRaisesRegex(RuntimeError,'transport'):io.stop_for_rollback()
            self.assertTrue(next(Path(td).glob('*/cleanup.json')).exists());self.assertEqual(io.stop.call_count,1)
    def test_failed_cleanup_keeps_transaction_and_layers_for_recovery(self):
        with tempfile.TemporaryDirectory() as td:
            p=f.fixture();io=f.Fake(p);tx=u.Transaction(io,Path(td)/'journal.json',p);tx.apply()
            candidate=dict(io.values);layers=io.mounts()
            io.stop_for_rollback=Mock(side_effect=RuntimeError(GUARD))
            with self.assertRaisesRegex(RuntimeError,GUARD):tx.rollback()
            self.assertEqual(tx.state['status'],'recovery_required');self.assertFalse(io.running)
            self.assertEqual(io.values,candidate);self.assertEqual(io.mounts(),layers)
    def test_successful_recovery_uses_original_full_verification(self):
        with tempfile.TemporaryDirectory() as td:
            p=f.fixture();io=f.Fake(p);tx=u.Transaction(io,Path(td)/'journal.json',p);tx.apply()
            io.stop_for_rollback=Mock(side_effect=io.stop)
            tx.rollback();io.stop_for_rollback.assert_called_once()
            self.assertEqual(tx.state['status'],'rolled_back');self.assertEqual(io.values,p['baseline']);self.assertEqual(io.stack,io.original)
if __name__ == '__main__': unittest.main()
