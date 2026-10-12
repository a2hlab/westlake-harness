"""Synthetic seal/source-WID evidence tests; no board, transport or real seal edits."""
import copy
from pathlib import Path
import tempfile
import unittest

import observations
import realization as r
import test_observations as fixtures


SOURCE_SERIAL = '61b0657200000000000000000324012c'
SOURCE_UID = 20011206
RUN_TARGET = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'
STATIC_TARGET = '/system/bin/synthetic-exact-static'


class SourceIdentityTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.root = self.fixture.root
        _, self.observed = self.fixture.fixture('running')
        self.observed.update(serial=SOURCE_SERIAL, host_uid=SOURCE_UID, host_gid=SOURCE_UID)
        self.fixture.replace_raw(self.observed, 'host_owner', f'{SOURCE_UID}:{SOURCE_UID}\n')
        status = (self.root / 'host_status.raw').read_text().replace('20011300', str(SOURCE_UID))
        self.fixture.replace_raw(self.observed, 'host_status', status)
        self.template = self.root / 'reviewed-run.sh'
        self.actual = self.root / 'captured-run.sh'
        self.template.write_bytes(b'#!/bin/sh\nexport ASX_RUNTIME_OWNER_UID=20011206\nexport WL_PARENT_ID=0\necho unchanged\n')
        self.actual.write_bytes(self.template.read_bytes().replace(b'WL_PARENT_ID=0', b'WL_PARENT_ID=33'))
        self.static = self.root / 'static-bytes'
        self.static.write_bytes(b'synthetic static content\n')
        self.identity_path = self.root / 'synthetic-seal.json'
        self.identity = {'schema': 'demo-seal/v1', 'synthetic': True, 'serial': SOURCE_SERIAL,
                         'boot_id': self.observed['boot_before'],
                         'files': {'runtime': {RUN_TARGET: r.digest(self.actual)},
                                   'boot': {STATIC_TARGET: r.digest(self.static)},
                                   'overlays': {}, 'installation': {STATIC_TARGET: r.digest(self.static)}},
                         'system_params': {'persist.westlake.synthetic': 'fixture-only'},
                         'packages': [{'package': 'synthetic.source.fixture', 'version_code': '1',
                                       'apk_path': STATIC_TARGET, 'apk_sha256': r.digest(self.static)}],
                         'inventories': []}
        self.request = {'source_files': {RUN_TARGET: {'path': str(self.actual), 'sha256': r.digest(self.actual)}},
                        'source_parameter_evidence': self.fixture.commit(self.observed)}
        self.original = {RUN_TARGET: (self.template, 'runtime')}

    def source_rows(self):
        r.write(self.identity_path, self.identity)
        ref = {'kind': 'seal', 'path': str(self.identity_path), 'sha256': r.digest(self.identity_path)}
        path, identity, rows = r.source_identity(ref, self.root)
        self.request['source_identity'] = ref
        self.request['source_seal'] = {key: value for key, value in ref.items() if key != 'kind'}
        return path, identity, rows

    def validate(self):
        path, identity, rows = self.source_rows()
        return r.validate_source_rows(self.request, self.root, path, identity, rows, self.original)

    def replace_actual(self, data):
        self.actual.write_bytes(data)
        digest = r.digest(self.actual)
        self.identity['files']['runtime'][RUN_TARGET] = digest
        self.request['source_files'][RUN_TARGET]['sha256'] = digest

    def test_seal_static_targets_and_sha_are_exactly_retained(self):
        _, _, rows = self.source_rows()
        self.assertEqual(set(rows), {RUN_TARGET, STATIC_TARGET})
        self.assertEqual(rows[STATIC_TARGET]['sha256'], r.digest(self.static))
        self.assertEqual(rows[RUN_TARGET]['sha256'], r.digest(self.actual))
        self.assertEqual(rows[STATIC_TARGET]['target'], STATIC_TARGET)
        self.assertEqual(self.identity['schema'], 'demo-seal/v1')
        self.assertTrue(self.identity['synthetic'])

    def test_same_boot_independent_wms_allows_only_source_window_difference(self):
        sources, receipt = self.validate()
        self.assertEqual(Path(sources[RUN_TARGET][0]).read_bytes(), self.actual.read_bytes())
        self.assertEqual(sources[RUN_TARGET][1], 'runtime')
        self.assertTrue(receipt)
        self.assertEqual(self.template.read_bytes().replace(b'WL_PARENT_ID=0', b'WL_PARENT_ID=33'), self.actual.read_bytes())
        # The original reviewed template remains byte-identical on disk.
        self.assertIn(b'export WL_PARENT_ID=0\n', self.template.read_bytes())

    def test_missing_source_window_evidence_rejects(self):
        del self.request['source_parameter_evidence']
        with self.assertRaises((ValueError, KeyError)):
            self.validate()

    def test_source_seal_boot_must_equal_independent_observation(self):
        self.identity['boot_id'] = '11111111-1111-1111-1111-111111111111'
        with self.assertRaises(ValueError):
            self.validate()

    def test_additional_bytes_and_wrong_source_uid_reject_even_when_rehashed(self):
        for changed in (
                self.actual.read_bytes() + b'# unapproved extra byte\n',
                self.actual.read_bytes().replace(b'OWNER_UID=20011206', b'OWNER_UID=20011300'),
                self.actual.read_bytes() + b'export WL_PARENT_ID=33\n'):
            with self.subTest(changed=changed):
                self.replace_actual(changed)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_run_file_claim_cannot_replace_wms_or_change_window(self):
        original = copy.deepcopy(self.observed)
        for variant in ('wrong_window', 'run_command', 'wrong_raw_uid'):
            with self.subTest(variant=variant):
                self.observed = copy.deepcopy(original)
                if variant == 'wrong_window':
                    self.observed['window_id'] = 47
                    self.fixture.replace_raw(self.observed, 'window_dump',
                        'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation\nimehost0 0 4344 47 1 1 0 101 0\n')
                elif variant == 'run_command':
                    self.observed['readings']['window_dump']['command'] = 'cat ' + RUN_TARGET
                else:
                    self.fixture.replace_raw(self.observed, 'host_owner', '20011300:20011300\n')
                self.request['source_parameter_evidence'] = self.fixture.commit(self.observed)
                with self.assertRaises(ValueError):
                    self.validate()

    def test_extra_seal_static_file_reaches_complete_proof_and_selfcheck_set(self):
        # Actual reviewed source corpus, synthetic seal envelope and local-only
        # extra bytes. This never edits the actual source fingerprint or seal.
        here = Path(__file__).resolve().parent
        request = r.read(here / 'request.5cd.placement.json')
        corpus = r.read(here / 'source-fingerprint.json')
        seal = {'schema': 'demo-seal/v1', 'serial': SOURCE_SERIAL,
                'boot_id': self.observed['boot_before'], 'synthetic': True,
                'files': {'runtime': {row['target']: row['sha256'] for row in corpus['files']},
                          'boot': {STATIC_TARGET: r.digest(self.static)},
                          'overlays': {}, 'installation': {}}}
        apk_row = next(row for row in corpus['files'] if row['target'].endswith('/toutiao.apk'))
        seal['files']['installation'][apk_row['target']] = apk_row['sha256']
        seal['system_params'] = {'persist.westlake.synthetic': 'fixture-only'}
        seal['packages'] = [{'package': 'com.ss.android.article.news', 'version_code': '1',
                             'apk_path': apk_row['target'], 'apk_sha256': apk_row['sha256']}]
        seal['inventories'] = []
        # A later source seal records a different independently observed WID.
        # Only that assignment changes; the placement still exactly rebuilds v6.
        original_run = next(row for row in corpus['files'] if row['target'] == RUN_TARGET)
        upstream = r.resolve(original_run['source']['path'], here).read_bytes()
        live47, _ = r.exact_numeric(upstream, rb'^export WL_PARENT_ID=([0-9]+)$', 47, 'window_id')
        later_run = self.root / 'later-source-run-wid47.sh'; later_run.write_bytes(live47)
        seal['files']['runtime'][RUN_TARGET] = r.digest(later_run)
        self.observed['window_id'] = 47
        self.fixture.replace_raw(self.observed, 'window_dump',
            'WindowName DisplayId Pid WinId Type Mode Flag ZOrd Orientation\nimehost0 0 4344 47 1 1 0 101 0\n')
        request['source_files'] = {RUN_TARGET: {'path': str(later_run), 'sha256': r.digest(later_run)}}
        request['source_parameter_evidence'] = self.fixture.commit(self.observed)
        path = self.root / 'full-synthetic-seal.json'
        r.write(path, seal)
        seal_pin = {'path': str(path), 'sha256': r.digest(path)}
        request['source_identity'] = dict(seal_pin, kind='seal')
        request['source_seal'] = seal_pin
        request_path = self.root / 'synthetic-seal-request.json'
        r.write(request_path, request)
        output = self.root / 'seal-realization'
        proof = r.compile_request(request_path, output)
        self.assertEqual(len(proof['files']), 807)
        self.assertEqual(proof['prepared_manifest_sha256'], r.MANIFEST_SHA)
        normalization = proof['source_window_normalization']
        self.assertEqual(len(normalization), 1)
        self.assertEqual(normalization[0]['edit']['old_hex'], b'33'.hex())
        self.assertEqual(normalization[0]['edit']['new_hex'], b'47'.hex())
        static = next(row for row in proof['files'] if row['target'] == STATIC_TARGET)
        self.assertEqual(static['sha256'], r.digest(self.static))
        self.assertEqual(static['edits'], [])
        proof.update(package=output / 'package', proof_sha256=r.digest(output / 'realization.json'))
        target_fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
        target_fixture.setUp(); self.addCleanup(target_fixture.doCleanups)
        expected, data = target_fixture.fixture('running')
        files, _ = r.running_files(proof, target_fixture.commit(data), target_fixture.root, expected['boot_id'])
        self.assertEqual(len(files), 807)
        self.assertEqual(files[STATIC_TARGET], r.digest(self.static))
        import selfcheck
        observation = {'schema': 'exact-live-observation/v1', 'serial': expected['serial'],
                       'boot_before': expected['boot_id'], 'boot_after': expected['boot_id'],
                       'files': files, 'parameter_evidence': target_fixture.commit(data),
                       'errors': [], 'synthetic': True,
                       'system_params': seal['system_params'],
                       'packages': {'com.ss.android.article.news': {'version_code': '1'}},
                       'inventories': []}
        report = selfcheck.compare(proof, observation, target_fixture.root,
                                   expected['serial'], expected['boot_id'], True)
        self.assertEqual(report['status'], 'OFFLINE_MATCH')
        observation['files'][STATIC_TARGET] = '0' * 64
        report = selfcheck.compare(proof, observation, target_fixture.root,
                                   expected['serial'], expected['boot_id'], True)
        self.assertEqual(report['status'], 'FAIL')
        self.assertTrue(any(row['target'] == STATIC_TARGET and not row['equal'] for row in report['checks']))
        import appendix
        candidate_dir = self.root / 'prior-candidate'
        r.compile_request(here / 'request.5cd.placement.json', candidate_dir)
        candidate_path = candidate_dir / 'realization.json'
        prior_sha = r.digest(candidate_path)
        result = appendix.bind(candidate_path, request_path, self.root / 'unsigned-appendix')
        self.assertEqual(result['status'], 'UNSIGNED_REQUIRES_OUTER_SIGNOFF')
        self.assertEqual(result['candidate_realization']['sha256'], prior_sha)
        self.assertEqual(result['source_seal'], seal_pin)
        self.assertEqual(result['additional_static_targets'], {STATIC_TARGET: r.digest(self.static)})
        self.assertEqual(result['complete_target_sha256'][STATIC_TARGET], r.digest(self.static))
        self.assertEqual(len(result['complete_target_sha256']), 807)
        self.assertEqual(result['source_window_normalization'][0]['edit']['new_hex'], b'47'.hex())
        self.assertIsNone(result['signed_by'])
        self.assertEqual(result['device_calls'], 0)
        self.assertEqual(r.digest(candidate_path), prior_sha)

    def test_unsafe_seal_target_and_bad_digest_reject(self):
        for target, digest in [('relative/path', r.digest(self.static)),
                               ('/system/../escape', r.digest(self.static)),
                               ('/system/bad\npath', r.digest(self.static)),
                               (STATIC_TARGET, 'x' * 64)]:
            with self.subTest(target=target, digest=digest):
                self.identity['files']['boot'] = {target: digest}
                with self.assertRaises(ValueError):
                    self.source_rows()


if __name__ == '__main__':
    unittest.main(verbosity=2)
