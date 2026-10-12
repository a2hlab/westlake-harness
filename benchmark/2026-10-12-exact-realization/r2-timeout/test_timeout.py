"""Three synthetic adapter checks; no production lock, device or executor run."""
import ast
import contextlib
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import realization as r
spec = importlib.util.spec_from_file_location('synthetic_timeout_adapter', HERE / 'restore.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


class TimeoutTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='synthetic-timeout-only-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.proof = {'proof_sha256': '1' * 64, 'source_identity': {'sha256': '2' * 64}, 'source_seal': None}
        self.lock_ref = {'path': 'synthetic-not-executed', 'sha256': '3' * 64}
        self.guard_result = ({'serial': 'synthetic-serial'}, {'lock_tool': self.lock_ref},
                             {'holder': 'synthetic-holder'}, self.root / 'authorization.json',
                             {'plan_sha256': '4' * 64})

    def invoke(self, runner):
        # Prerequisites are stubbed; the fake runner asserts adapter plumbing only.
        # No lock protocol, production holder or executor transaction is simulated.
        with patch.object(adapter, 'guard', return_value=self.guard_result), \
             patch.object(r, 'pin', return_value=self.root / 'not-an-executable'), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            return adapter.execute(self.proof, self.root / 'package', {},
                                   {'sha256': '5' * 64}, self.lock_ref, self.root,
                                   self.root / 'fresh-transaction', runner=runner)

    def test_normal_executor_receives_2700_and_unchanged_result(self):
        calls = []
        def fake_runner(cmd, **kwargs):
            calls.append((cmd, kwargs))
            if len(calls) == 1:
                self.assertEqual(kwargs['timeout'], 15)
                return subprocess.CompletedProcess(cmd, 0, 'synthetic-holder\n', '')
            self.assertEqual(kwargs, {'capture_output': True, 'text': True, 'timeout': 2700})
            return subprocess.CompletedProcess(cmd, 7, 'synthetic-output\n', 'synthetic-error\n')
        receipt, rc = self.invoke(fake_runner)
        self.assertEqual(len(calls), 2)
        self.assertEqual((rc, receipt['executor_rc']), (7, 7))
        self.assertNotIn('status', receipt)
        self.assertEqual(receipt['plan_sha256'], '4' * 64)
        self.assertFalse(receipt['seal_signed'])
        # The admission, prepared-package and target guards are byte-structure exact.
        old = ast.parse((HERE.parent / 'restore.py').read_text())
        new = ast.parse((HERE / 'restore.py').read_text())
        for name in ('prepare', 'checked_package', 'guard'):
            self.assertEqual(ast.dump(next(n for n in old.body if getattr(n, 'name', None) == name)),
                             ast.dump(next(n for n in new.body if getattr(n, 'name', None) == name)))

    def test_timeout_returns_unknown_receipt_124_without_rollback_claim(self):
        calls = []
        def fake_runner(cmd, **kwargs):
            calls.append(cmd)
            if len(calls) == 1:
                return subprocess.CompletedProcess(cmd, 0, 'synthetic-holder\n', '')
            self.assertEqual(kwargs['timeout'], 2700)
            raise subprocess.TimeoutExpired(cmd, 2700, output=b'partial preimage\n', stderr=b'partial stderr\n')
        receipt, rc = self.invoke(fake_runner)
        self.assertEqual(len(calls), 2)  # No automatic replay or rollback.
        self.assertEqual(rc, 124)
        self.assertEqual(receipt['status'], 'UNKNOWN')
        self.assertIsNone(receipt['executor_rc'])
        self.assertEqual(receipt['adapter_rc'], 124)
        self.assertEqual(receipt['timeout_seconds'], 2700)
        self.assertEqual(receipt['process_state'], 'UNKNOWN')
        self.assertEqual(receipt['rollback_state'], 'UNKNOWN')
        self.assertEqual(receipt['partial_stdout'], 'partial preimage\n')
        self.assertEqual(receipt['partial_stderr'], 'partial stderr\n')
        self.assertFalse(receipt['ui_accepted'])
        path = self.root / 'synthetic.realization-receipt.json'
        r.write(path, receipt)
        self.assertEqual(r.read(path), receipt)

    def test_old_generator_admission_pin_rejected_by_real_guard(self):
        path = self.root / 'synthetic-admission.json'
        r.write(path, {'schema': 'exact-realization-admission/v1', 'admitted': True,
                       'signed_by': 'outer(claude)', 'generator_sha256': r.digest(HERE.parent / 'restore.py')})
        ref = {'path': str(path), 'sha256': r.digest(path)}
        self.assertNotEqual(r.digest(HERE.parent / 'restore.py'), r.digest(HERE / 'restore.py'))
        with patch.object(adapter, 'checked_package', return_value=({}, {})):
            with self.assertRaisesRegex(ValueError, 'restore adapter independent self pin'):
                adapter.guard({}, self.root, ref, {}, self.root, now=1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
