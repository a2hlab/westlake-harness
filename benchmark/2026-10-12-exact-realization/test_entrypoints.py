"""Actual local shell entrypoints; child audit guard forbids device/process calls.

The real reviewed corpus is compiled in temporary storage. Preview remains
NOT_AUTHORIZED; neither a board transaction nor a lock is simulated.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import realization as r

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
BASELINE = '52747bb'


class EntrypointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory(prefix='exact-local-entrypoints-')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.root = Path(cls.temporary.name)
        cls.output = cls.root / 'realization'
        with patch('subprocess.run', side_effect=AssertionError('compiler attempted subprocess')):
            r.compile_request(HERE / 'request.5cd.placement.json', cls.output)
        cls.proof = cls.output / 'realization.json'
        cls.sentinel = cls.root / 'child-audit'
        cls.sentinel.mkdir()
        (cls.sentinel / 'sitecustomize.py').write_text(
            'import os, pathlib, sys\n'
            'pathlib.Path(os.environ["EXACT_TEST_GUARD_LOADED"]).write_text("loaded\\n")\n'
            'def deny(event, args):\n'
            '    if event in {"subprocess.Popen", "os.system", "os.exec", "os.posix_spawn"}:\n'
            '        pathlib.Path(os.environ["EXACT_TEST_GUARD_DENIED"]).write_text(event)\n'
            '        raise RuntimeError("offline entrypoint attempted child execution: " + event)\n'
            'sys.addaudithook(deny)\n')

    def wrapper(self, name, arguments):
        loaded = self.root / (name + '.guard-loaded')
        denied = self.root / (name + '.guard-denied')
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1',
                   PYTHONPATH=str(self.sentinel) + os.pathsep + os.environ.get('PYTHONPATH', ''),
                   EXACT_TEST_GUARD_LOADED=str(loaded), EXACT_TEST_GUARD_DENIED=str(denied))
        result = subprocess.run(['/bin/bash', str(REPO / 'scripts/lab/demo_restore.sh'), *arguments],
                                env=env, cwd=REPO, capture_output=True, text=True, timeout=120)
        self.assertTrue(loaded.is_file(), 'child Python audit guard did not load')
        self.assertFalse(denied.exists(), 'entrypoint attempted a subprocess/device command')
        return result

    def test_real_wrapper_default_preview_has_487_targets_and_no_authority(self):
        output = self.root / 'wrapper-preview'
        result = self.wrapper('preview', ['--realization', str(self.proof), '--out', str(output)])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        self.assertEqual(receipt['status'], 'PREVIEW_NOT_RESTORED')
        self.assertFalse(receipt['authority_created'])
        self.assertEqual(receipt['device_calls'], 0)
        self.assertIsNone(receipt['source_seal'])
        self.assertEqual(len(receipt['target_sha256']), 487)
        self.assertEqual(r.read(output / 'preview-receipt.json'), receipt)
        self.assertEqual(len(r.read(output / 'plan.json')['members']), 487)
        self.assertEqual(r.digest(output / 'executor.py'), r.EXECUTOR_SHA)
        self.assertEqual(receipt['executor_sha256'], r.EXECUTOR_SHA)
        self.assertEqual(r.read(output / 'activation.json')['status'], 'NOT_AUTHORIZED')
        self.assertFalse(any(path.name in {'transaction.json', 'authorization.json', 'admission.json'}
                             for path in output.rglob('*')))

    def test_real_wrapper_equals_form_execute_without_admission_refuses(self):
        output = self.root / 'must-not-execute'
        result = self.wrapper('execute-denied', ['--realization=' + str(self.proof),
                                                 '--execute', '--out', str(output)])
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('restore requires explicit execute plus independent pins', result.stderr)
        self.assertFalse(output.exists())
        self.assertFalse(Path(str(output) + '.realization-receipt.json').exists())

    def test_old_wrappers_are_byte_equal_after_removing_only_new_branch(self):
        for name, start, tail in (
                ('demo_restore.sh', b'# Explicit exact realization;',
                 b'exec python3 "$SELF_DIR/../../benchmark/2026-10-09-demo-baseline/t5/restore.py" "$@"'),
                ('demo_selfcheck.sh', b'# Exact realizations use independent boot/parameter evidence',
                 b'exec python3 - "$SELF_DIR" "$@" <<\'PY\'')):
            with self.subTest(wrapper=name):
                original = subprocess.run(['git', 'show', BASELINE + ':scripts/lab/' + name],
                                          cwd=Path(os.environ.get('EXACT_BASELINE_REPO',str(REPO))), capture_output=True, check=True).stdout
                current = (REPO / 'scripts/lab' / name).read_bytes()
                self.assertEqual(current.count(start), 1)
                self.assertEqual(current.count(tail), 1)
                branch_start, fallback_start = current.index(start), current.index(tail)
                self.assertLess(branch_start, fallback_start)
                self.assertEqual(current[:branch_start] + current[fallback_start:], original)
                self.assertIn(b'--realization|--realization=*)', current[branch_start:fallback_start])

    def test_both_shell_wrappers_parse(self):
        for name in ('demo_restore.sh', 'demo_selfcheck.sh'):
            with self.subTest(wrapper=name):
                result = subprocess.run(['/bin/bash', '-n', str(REPO / 'scripts/lab' / name)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == '__main__':
    unittest.main(verbosity=2)
