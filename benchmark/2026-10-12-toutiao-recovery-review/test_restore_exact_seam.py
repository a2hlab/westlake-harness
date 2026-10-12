import hashlib
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest


HERE = Path(__file__).resolve().parent
MAIN = HERE.parents[2] / 'westlake-harness'
sys.path.insert(0, str(MAIN / 'scripts/lab'))
SPEC = importlib.util.spec_from_file_location(
    'current_exact_restore', MAIN / 'benchmark/2026-10-09-demo-baseline/t5/restore.py')
RESTORE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(RESTORE)


class ExactSealSeamTests(unittest.TestCase):
    def test_serial_only_projection_does_not_authorize_uid_derivation(self):
        original = (MAIN / 'benchmark/2026-10-12-recovery-executor/payload/real-start-parent-bounded.sh').read_bytes()
        self.assertIn(b'20011206', original)
        derived = original.replace(b'20011206', b'20011300')
        self.assertNotEqual(original, derived)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            artifact = root / 'source.sh'
            artifact.write_bytes(original)
            source_sha = hashlib.sha256(original).hexdigest()
            target = '/data/local/tmp/exact-seam-fixture/real-start-parent-bounded.sh'
            pin = {'path': str(artifact), 'sha256': source_sha}
            seal = {'schema': 'demo-seal/v1', 'serial': '61b',
                    'files': {'runtime': {target: source_sha}, 'boot': {},
                              'overlays': {}, 'installation': {}},
                    'packages': [], 'overlay_deployments': []}
            deployment = {'schema': 'demo-restore-deployment/v1', 'execution_enabled': True,
                          'files': [{'target': target, 'mode': 'restore', 'source': pin}],
                          'providers': [{'layer': 'u13', 'interpreter': 'python3',
                                         'program': pin, 'rollback': pin, 'targets': [target]}]}
            self.assertEqual(RESTORE.validate(seal, deployment, root), {target: source_sha})
            projected = dict(seal, serial='5cd')
            artifact.write_bytes(derived)
            pin['sha256'] = hashlib.sha256(derived).hexdigest()
            with self.assertRaisesRegex(ValueError, 'source differs from sealed SHA'):
                RESTORE.validate(projected, deployment, root)


if __name__ == '__main__':
    unittest.main(verbosity=2)
