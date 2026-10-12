"""Actual 806-source corpus plus independently pinned synthetic 61b raw evidence.

All generated observations, realizations and receipts stay in temporary storage.
These are offline comparisons, not board verification or restoration authority.
"""
import copy
import io
from contextlib import redirect_stdout
from pathlib import Path
import re
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
SERIAL = '61b0657200000000000000000324012c'
BOOT = '33333333-3333-3333-3333-333333333333'
UID = 20011206


def running_fixture(window_id):
    """Reuse the raw fixture, independently change every claimed/raw identity."""
    fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
    fixture.setUp()
    fixture.expected.update(serial=SERIAL, boot_id=BOOT, host_uid=UID, host_gid=UID)
    expected, data = fixture.fixture('running')
    expected['window_id'] = data['window_id'] = window_id
    fixture.replace_raw(data, 'host_owner', f'{UID}:{UID}\n')
    status = (fixture.root / 'host_status.raw').read_text().replace('20011300', str(UID))
    fixture.replace_raw(data, 'host_status', status)
    window = (fixture.root / 'window_dump.raw').read_text().replace('4344 33', f'4344 {window_id}')
    fixture.replace_raw(data, 'window_dump', window)
    ref = fixture.commit(data)
    ref['path'] = str(fixture.root / ref['path'])
    return fixture, expected, data, ref


class SameBoardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # This is a denial guard, not a transport/observation simulation.
        guard = patch('subprocess.run', side_effect=AssertionError('offline sameboard test attempted subprocess'))
        guard.start(); cls.addClassCleanup(guard.stop)
        temp = tempfile.TemporaryDirectory(prefix='exact-sameboard-806-')
        cls.addClassCleanup(temp.cleanup); cls.root = Path(temp.name)
        fixture, expected, _, ref = running_fixture(44)
        cls.addClassCleanup(fixture.doCleanups)
        cls.source_path = HERE / 'source-fingerprint.json'
        cls.source = r.read(cls.source_path)
        cls.source_rows = {row['target']: row for row in cls.source['files']}
        cls.request = r.read(HERE / 'request.5cd.placement.json')
        cls.request.update(phase='running', parameters=expected, parameter_evidence=ref)
        cls.request['source_identity'] = {'kind': 'candidate-fingerprint',
                                         'path': str(cls.source_path), 'sha256': r.digest(cls.source_path)}
        cls.request_path = cls.root / 'sameboard-request.json'
        r.write(cls.request_path, cls.request)
        cls.output = cls.root / 'compiled'
        cls.compiled = r.compile_request(cls.request_path, cls.output)
        cls.proof = r.verify(cls.output / 'realization.json')
        cls.run_target = next(row['target'] for row in cls.proof['files']
                              if row.get('source') == '$PACKAGE/runtime/run.sh')
        cls.run_raw = r.pin(cls.source_rows[cls.run_target]['source'], HERE).read_bytes()

    def test_real_806_roundtrip_preserves_every_target_except_single_wid(self):
        proof = self.proof
        self.assertEqual(len(self.source_rows), 806)
        self.assertEqual(len(proof['files']), 806)
        actual = {row['target']: row['sha256'] for row in proof['files']}
        original = {target: row['sha256'] for target, row in self.source_rows.items()}
        self.assertEqual(set(actual), set(original))
        self.assertEqual([target for target in original if actual[target] != original[target]], [self.run_target])
        expected = re.sub(rb'(?m)^export WL_PARENT_ID=33$', b'export WL_PARENT_ID=44', self.run_raw)
        self.assertEqual((proof['package'] / 'runtime/run.sh').read_bytes(), expected)
        self.assertIn(b'export ASX_RUNTIME_OWNER_UID=20011206\n', expected)
        self.assertEqual(actual[self.run_target], r.bytes_sha(expected))
        self.assertEqual(proof['purpose'], 'same-board-selfcheck')
        self.assertEqual(proof['route_targets'], 0)
        self.assertFalse(proof['execution_enabled'])
        self.assertFalse(proof['restore_allowed'])
        self.assertTrue(proof['parameter_evidence']['synthetic'])
        self.assertEqual(proof['source_identity']['sha256'], r.digest(self.source_path))
        self.assertIsNone(proof['source_seal'])
        self.assertIsNone(proof['signature'])
        self.assertEqual({str(p.relative_to(proof['package'])) for p in proof['package'].rglob('*') if p.is_file()},
                         {'runtime/run.sh', 'manifest.json'})

    def test_standard_selfcheck_two_independent_wid_changes_are_offline_only(self):
        for wid in (55, 66):
            with self.subTest(window_id=wid):
                fixture, expected, _, ref = running_fixture(wid)
                self.addCleanup(fixture.doCleanups)
                # Compute the readback independently from source bytes, not running_files.
                raw = re.sub(rb'(?m)^export WL_PARENT_ID=33$', f'export WL_PARENT_ID={wid}'.encode(), self.run_raw)
                files = {target: row['sha256'] for target, row in self.source_rows.items()}
                files[self.run_target] = r.bytes_sha(raw)
                observation = {'schema': 'exact-live-observation/v1', 'serial': SERIAL,
                               'boot_before': BOOT, 'boot_after': BOOT, 'files': files,
                               'parameter_evidence': ref, 'errors': [], 'synthetic': True}
                path = fixture.root / 'readback.json'; r.write(path, observation)
                receipt = self.root / f'selfcheck-{wid}.json'
                with redirect_stdout(io.StringIO()):
                    rc = selfcheck.main(['--realization', str(self.output / 'realization.json'),
                                         '--serial', SERIAL, '--boot-id', BOOT,
                                         '--observed', str(path), '--out', str(receipt)])
                self.assertEqual(rc, 0)
                report = r.read(receipt)
                self.assertEqual(report['status'], 'OFFLINE_MATCH')
                self.assertEqual(report['file_count'], 806)
                self.assertTrue(all(row['equal'] for row in report['checks']))
                self.assertEqual(report['dynamic_receipt']['parameter_evidence']['window_id'], wid)
                self.assertEqual(report['dynamic_receipt']['sha256'], files[self.run_target])
                self.assertTrue(report['synthetic'])
                self.assertEqual(report['remote_write_operations'], 0)
                with self.assertRaises(ValueError):
                    selfcheck.compare(self.proof, observation, fixture.root, SERIAL,
                                      '44444444-4444-4444-4444-444444444444', True)
                with self.assertRaises(ValueError):
                    selfcheck.compare(self.proof, observation, fixture.root, SERIAL, BOOT, False)

    def test_sameboard_restore_prepare_refuses_before_creating_output(self):
        output = self.root / 'must-not-restore'
        with self.assertRaisesRegex(ValueError, 'no restoration authority'):
            restore.prepare(self.proof, output)
        self.assertFalse(output.exists())

    def test_real_raw_foreign_uid_and_missing_source_pin_fail_closed(self):
        fixture, expected, data, ref = running_fixture(44)
        self.addCleanup(fixture.doCleanups)
        fixture.replace_raw(data, 'host_status', (fixture.root / 'host_status.raw').read_text().replace(str(UID), '20011300'))
        ref = fixture.commit(data); ref['path'] = str(fixture.root / ref['path'])
        request = copy.deepcopy(self.request); request['parameter_evidence'] = ref
        path = self.root / 'foreign-uid.json'; r.write(path, request)
        out = self.root / 'foreign-uid-rejected'
        with self.assertRaisesRegex(ValueError, 'Uid mismatch'):
            r.compile_request(path, out)
        self.assertFalse(out.exists())
        candidate = copy.deepcopy(self.source)
        # A full 806-row candidate with one unavailable byte source must not pass.
        row = next(row for row in candidate['files'] if row['groups'] == ['baseline'])
        del row['source']
        source = self.root / 'missing-source-fingerprint.json'; r.write(source, candidate)
        request = copy.deepcopy(self.request)
        request['source_identity'] = {'kind': 'candidate-fingerprint', 'path': str(source), 'sha256': r.digest(source)}
        path = self.root / 'missing-source.json'; r.write(path, request)
        out = self.root / 'missing-source-rejected'
        with self.assertRaisesRegex(ValueError, 'pinned source bytes missing'):
            r.compile_request(path, out)
        self.assertFalse(out.exists())


if __name__ == '__main__':
    unittest.main(verbosity=2)
