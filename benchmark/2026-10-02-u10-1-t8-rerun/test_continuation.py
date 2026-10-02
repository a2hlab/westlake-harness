import copy
import hashlib
import importlib.util
import json
import tempfile
from pathlib import Path
import unittest

H = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('continuation', H / 'continue_observation.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)


class ContinuationSafety(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.root = self.base / 'prior'
        keys = self.base / 'keys.txt'
        keys.write_text('bright\ninterrupted\nuntested\ninstall-failed\n')
        self.plan = {'phase': 'A', 'serial': 'serial', 'bundle_sha256': 'bundle', 'package_manifest_sha256': 'manifest',
            'shards': [{'name': 'lit', 'keys_file': str(keys)}],
            'after_lock': ['apply', '--root', 'old', '--plan', 'oldplan'], 'before_unlock': ['finish', '--root', 'old']}
        self.fp = {'runtime': {'sha256_12': hashlib.sha256(b'runtime').hexdigest()[:12]},
                   'boot': {'sha256_12': hashlib.sha256(b'boot').hexdigest()[:12]}}
        self.receipt = {**{k: self.plan[k] for k in ['phase', 'serial', 'bundle_sha256', 'package_manifest_sha256']},
            'expected_fingerprints': self.fp, 'plan': self.plan, 'assigned_shards': {'lit': keys.read_text().split()}}
        self.root.mkdir()
        self.save('window-input.json', self.receipt)
        self.save('runner/board-run-result.json', {'before_unlock': 0})
        self.save('observation-restored.json', {'passed': True, 'serial': 'serial'})
        batch = self.root / 'runner/lit/run/serial'
        batch.mkdir(parents=True)
        (batch / 'runtime-fingerprint.txt').write_text('runtime\n')
        (batch / 'boot-image-fingerprint.txt').write_text('boot\n')
        for key, status in [('bright', 'foreground_unconfirmed'), ('interrupted', 'batch_interrupted'), ('install-failed', 'app_failed')]:
            self.save('runner/lit/run/serial/' + key + '/record.json', {'key': key, 'serial': 'serial', 'status': status, 'finished_at': 123})

    def save(self, name, value):
        p = self.root / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(value))

    def test_terminal_outcomes_only_no_lighting_inference(self):
        self.assertEqual(c.measured(self.plan, [self.root]), {'bright', 'install-failed'})
        target = c.prepare(self.plan, [self.root], self.base / 'continuation', self.base / 'new-run')
        result = json.loads(target.read_text())
        self.assertEqual(c.keys_of(result), ['interrupted', 'untested'])
        self.assertFalse(result['execution_enabled'])
        self.assertEqual(result['bundle_sha256'], 'bundle')
        self.assertEqual(result['after_lock'][-1], str(target))

    def test_failed_cleanup_blocks_continuation(self):
        self.save('runner/board-run-result.json', {'before_unlock': 1})
        with self.assertRaisesRegex(AssertionError, 'prior finish failed'):
            c.measured(self.plan, [self.root])

    def test_binding_mismatch_blocks_continuation(self):
        for field in ['serial', 'phase', 'bundle_sha256', 'package_manifest_sha256']:
            receipt = copy.deepcopy(self.receipt)
            receipt[field] = 'wrong'
            self.save('window-input.json', receipt)
            with self.assertRaisesRegex(AssertionError, 'receipt mismatch'):
                c.measured(self.plan, [self.root])

    def test_missing_or_wrong_candidate_fingerprint_blocks(self):
        fp = self.root / 'runner/lit/run/serial/runtime-fingerprint.txt'
        fp.write_text('wrong')
        with self.assertRaisesRegex(AssertionError, 'fingerprint mismatch'):
            c.measured(self.plan, [self.root])
        fp.unlink()
        with self.assertRaisesRegex(AssertionError, 'fingerprint evidence absent'):
            c.measured(self.plan, [self.root])

    def test_failed_restore_or_reused_output_blocks(self):
        self.save('observation-restored.json', {'passed': False, 'serial': 'serial'})
        with self.assertRaisesRegex(AssertionError, 'restoration receipt'):
            c.measured(self.plan, [self.root])
        self.save('observation-restored.json', {'passed': True, 'serial': 'serial'})
        with self.assertRaisesRegex(AssertionError, 'fresh continuation'):
            c.prepare(self.plan, [self.root], self.root, self.base / 'new-run')
        with self.assertRaisesRegex(AssertionError, 'fresh transaction'):
            c.prepare(self.plan, [self.root], self.base / 'continuation', self.root)

    def test_smoke_controls_and_started_records_do_not_consume_keys(self):
        self.save('runner/smoke/bright/record.json', {'key': 'untested', 'serial': 'serial', 'status': 'captured', 'finished_at': 1})
        self.save('runner/lit/run/serial/untested/record.json', {'key': 'untested', 'serial': 'serial', 'status': 'started', 'finished_at': 1})
        self.assertNotIn('untested', c.measured(self.plan, [self.root]))


if __name__ == '__main__':
    unittest.main()
