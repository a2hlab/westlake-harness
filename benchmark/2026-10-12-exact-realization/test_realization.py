"""Four exact-realization scenarios, entirely offline.

Uses the actual pinned source corpus and temporary synthetic running evidence.
No executor transaction, production lock simulation, HDC, VM or network call.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
import observations
import realization as r
import restore
import selfcheck
import test_observations as fixtures

HERE = Path(__file__).resolve().parent


class RealizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.no_subprocess = patch('subprocess.run', side_effect=AssertionError('offline test attempted a subprocess'))
        cls.no_subprocess.start()
        cls.addClassCleanup(cls.no_subprocess.stop)
        cls.temp = tempfile.TemporaryDirectory(prefix='exact-realization-four-scenarios-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.request_path = HERE / 'request.5cd.placement.json'
        cls.output = cls.root / 'placement'
        cls.raw_proof = r.compile_request(cls.request_path, cls.output)
        cls.proof = dict(cls.raw_proof, package=cls.output / 'package',
                         proof_path=cls.output / 'realization.json',
                         proof_sha256=r.digest(cls.output / 'realization.json'))

    def test_roundtrip_actual_full_source_and_exact_v6_package(self):
        proof = r.verify(self.output / 'realization.json')
        self.assertEqual(proof['status'], 'candidate/not_sealed')
        self.assertIsNone(proof['source_seal'])
        self.assertIsNone(proof['signature'])
        self.assertFalse(proof['execution_enabled'])
        self.assertEqual(proof['device_calls'], 0)
        self.assertEqual(proof['route_targets'], 487)
        self.assertEqual(len(proof['files']), 806)
        self.assertEqual(len({row['target'] for row in proof['files']}), 806)
        self.assertEqual(r.digest(proof['package'] / 'manifest.json'), r.MANIFEST_SHA)
        self.assertEqual(r.digest(proof['package'] / 'executor.py'), r.EXECUTOR_SHA)
        unchanged = [row for row in proof['files'] if 'source' not in row]
        self.assertEqual(len(unchanged), 319)
        for row in unchanged:
            self.assertEqual(row['sha256'], row['template_sha256'])
            self.assertEqual(row['edits'], [])
        request_row = next(row for row in proof['files'] if row.get('source') == '$PACKAGE/runtime/stage/request.bin')
        self.assertEqual([edit['offset'] for edit in request_row['edits']], [312, 316])
        self.assertEqual([edit['parameter'] for edit in request_row['edits']], ['host_uid', 'host_gid'])
        self.assertEqual(proof['parameter_evidence']['host_uid'], 20011300)
        self.assertIsNone(proof['parameters']['window_id'])

    def test_reject_bad_pins_unknown_bytes_and_duplicate_assignments(self):
        for name, mutate in (
                ('source_sha', lambda req: req['source_identity'].update(sha256='0' * 64)),
                ('v6_sha', lambda req: req['v6']['provider'].update(sha256='0' * 64)),
                ('false_seal', lambda req: req.update(source_seal={'path': str(HERE / 'source-fingerprint.json'), 'sha256': '0' * 64})),
                ('placement_window', lambda req: req['parameters'].update(window_id=33))):
            with self.subTest(name=name):
                request = r.read(self.request_path)
                request['source_identity']['path'] = str(HERE / 'source-fingerprint.json')
                mutate(request)
                path = self.root / (name + '.json')
                r.write(path, request)
                output = self.root / ('rejected-' + name)
                with self.assertRaises(ValueError):
                    r.compile_request(path, output)
                self.assertFalse(output.exists())
        for text in (b'export WL_PARENT_ID=0\nexport WL_PARENT_ID=33\n',
                     b'echo export WL_PARENT_ID=0\n'):
            with self.assertRaisesRegex(ValueError, 'exactly one known assignment'):
                r.exact_numeric(text, rb'^export WL_PARENT_ID=([0-9]+)$', 33, 'window_id')
        request = r.read(self.request_path)
        candidate = r.read(HERE / 'source-fingerprint.json')
        row = next(row for row in candidate['files'] if 'runtime' in row['groups'])
        row['sha256'] = '0' * 64  # A re-pinned JSON cannot authorize altered source bytes.
        candidate_path = self.root / 'one-byte-source-claim.json'
        r.write(candidate_path, candidate)
        request['source_identity'] = {'kind': 'candidate-fingerprint', 'path': str(candidate_path), 'sha256': r.digest(candidate_path)}
        path = self.root / 'source-byte-reject.json'; r.write(path, request)
        with self.assertRaises(ValueError):
            r.compile_request(path, self.root / 'source-byte-output')
        self.assertFalse((self.root / 'source-byte-output').exists())

    def test_selfcheck_independent_running_window_and_stale_boot(self):
        fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        expected, data = fixture.fixture('running')
        observation_ref = fixture.commit(data)
        files, dynamic = r.running_files(self.proof, observation_ref, fixture.root, expected['boot_id'])
        original = {row['target']: row['sha256'] for row in self.proof['files']}
        changed = [target for target in original if files[target] != original[target]]
        self.assertEqual(changed, [dynamic['target']])
        self.assertTrue(changed[0].endswith('/run.sh'))
        self.assertEqual(dynamic['parameter_evidence']['window_id'], 33)
        self.assertEqual(dynamic['parameter_evidence']['host_birth'], 918273)
        self.assertEqual(dynamic['device_write_operations'], 0)
        observed = {'schema': 'exact-live-observation/v1', 'serial': expected['serial'],
                    'boot_before': expected['boot_id'], 'boot_after': expected['boot_id'],
                    'files': files, 'parameter_evidence': observation_ref, 'errors': [], 'synthetic': True}
        report = selfcheck.compare(self.proof, observed, fixture.root, expected['serial'], expected['boot_id'], True)
        self.assertEqual(report['status'], 'OFFLINE_MATCH')
        self.assertNotEqual(report['status'], 'PASS')
        with self.assertRaises(ValueError):
            r.running_files(self.proof, observation_ref, fixture.root, '11111111-1111-1111-1111-111111111111')
        data['readings']['window_dump']['command'] = 'cat /data/local/tmp/run.sh'
        with self.assertRaises(ValueError):
            r.running_files(self.proof, fixture.commit(data), fixture.root, expected['boot_id'])

    def test_restore_preview_and_unchanged_executor_guards(self):
        package = self.root / 'activation-preview'
        preview = restore.prepare(self.proof, package)
        self.assertEqual(preview['status'], 'PREVIEW_NOT_RESTORED')
        self.assertFalse(preview['authority_created'])
        self.assertEqual(preview['device_calls'], 0)
        self.assertIsNone(preview['source_seal'])
        self.assertEqual(len(preview['target_sha256']), 487)
        self.assertEqual(r.digest(package / 'executor.py'), r.EXECUTOR_SHA)
        plan = r.read(package / 'plan.json'); plan['_sha'] = r.digest(package / 'plan.json')
        executor = r.load(package / 'executor.py', 'exact_realization_guard_test_executor')
        with self.assertRaisesRegex(ValueError, 'missing outer authorization'):
            executor.validate(plan)
        wrong = copy.deepcopy(plan); wrong['serial'] = 'not-the-target-board'
        with self.assertRaisesRegex(ValueError, 'wrong serial'):
            executor.validate(wrong)
        auth = {'approved_by': 'outer(codex)', 'plan_sha256': plan['_sha'],
                'serial': plan['serial'], 'boot_id': plan['boot_id'],
                'expires_epoch': 100, 'actions': ['place-only', 'one-reboot', 'rollback-safe']}
        path = self.root / 'synthetic-guard-only-authorization.json'
        r.write(path, auth)
        with self.assertRaisesRegex(ValueError, 'expired'):
            executor.validate(plan, path, now=101, authorization_sha256=r.digest(path))
        unknown = copy.deepcopy(plan); unknown['members'][0]['before']['exists'] = None
        with self.assertRaisesRegex(ValueError, 'unknown preimage'):
            executor.validate(unknown, path, now=1, authorization_sha256=r.digest(path))
        stale = copy.deepcopy(auth); stale['origin_boot_id'] = '11111111-1111-1111-1111-111111111111'
        r.write(path, stale)
        with self.assertRaisesRegex(ValueError, 'authorization origin'):
            executor.validate(plan, path, now=1, authorization_sha256=r.digest(path))


if __name__ == '__main__':
    unittest.main(verbosity=2)
