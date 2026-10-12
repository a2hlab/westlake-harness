"""R3-only offline tests. All successful transaction recordings are SYNTHETIC.

No executor is executed, no device/lock command is sent. Frozen compilers rebuild
real packages locally; fake placement journals never imply actual installation.
"""
import copy
from contextlib import contextmanager
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('r3_checker_under_test', HERE / 'selfcheck.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)


class ActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.block = patch('subprocess.run', side_effect=AssertionError('r3 test must not execute transport/transaction'))
        cls.block.start(); cls.addClassCleanup(cls.block.stop)
        cls.temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-r3-activation-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        main = s.obs.workspace_root(HERE) / 'westlake-harness'
        cls.origin_path = main / 'benchmark/2026-10-12-v1-seal-execution/exact-5cd-placement/realization.json'
        s.select_frozen(cls.origin_path)
        cls.origin = s.r.verify(cls.origin_path)
        cls.package = cls.root / 'activation-package'
        prepared = s.restore.prepare(cls.origin, cls.package)
        cls.plan = s.read(cls.package / 'plan.json')
        cls.tx = cls.root / 'synthetic-transaction'; cls.tx.mkdir()
        (cls.tx / 'SYNTHETIC.json').write_text(json.dumps({'synthetic': True, 'scope': 'all sibling placement/backup receipts are test fixtures; no executor ran'}))
        cls.auth_path = cls.root / 'synthetic-authorization.json'
        auth = {'synthetic': True, 'approved_by': 'outer(codex)', 'plan_sha256': prepared['plan_sha256'],
                'serial': cls.plan['serial'], 'boot_id': cls.plan['boot_id'], 'expires_epoch': 1,
                'derived_manifest_sha256': prepared['prepared_manifest_sha256'],
                'actions': ['place-only', 'one-reboot', 'rollback-safe'], 'holder': 'SYNTHETIC test holder'}
        cls.auth_path.write_text(json.dumps(auth))
        cls.admission_path = cls.root / 'synthetic-admission.json'
        adapter = s.FROZEN / 'r2-timeout/restore.py'
        admission = {'schema': 'exact-realization-admission/v1', 'synthetic': True, 'admitted': True,
                     'signed_by': 'outer(claude)', 'generator_sha256': s.digest(adapter),
                     'realization_sha256': cls.origin['proof_sha256'],
                     'source_identity_sha256': cls.origin['source_identity']['sha256'], 'source_seal_sha256': None,
                     'prepared_manifest_sha256': prepared['prepared_manifest_sha256'], 'plan_sha256': prepared['plan_sha256'],
                     'executor_sha256': s.r.EXECUTOR_SHA, 'serial': cls.plan['serial'], 'boot_id': cls.plan['boot_id'],
                     'expires_epoch': 1, 'action': 'apply', 'holder': auth['holder'], 'target_sha256': prepared['target_sha256']}
        admission['lock_tool'] = s.pinned(main / 'scripts/lab/board_note.sh')
        cls.admission_path.write_text(json.dumps(admission))
        backups, members = [], []
        for n, row in enumerate(cls.plan['members']):
            backup_name = f'backup-{n:03d}' if row['before']['exists'] else None
            if backup_name:
                source = s.r.resolve(row['before']['source'], s.FROZEN)
                shutil.copyfile(source, cls.tx / backup_name)
            backups.append({'target': row['target'], 'before': row['before'], 'backup': backup_name, 'candidate_sha256': row['sha256']})
            path = cls.tx / f'placed-{n:03d}.json'; path.write_text(json.dumps({'target': row['target'], 'sha256': row['sha256']}))
            members.append(s.pinned(path))
        (cls.tx / 'transaction.json').write_text(json.dumps({'synthetic': True, 'plan_sha256': prepared['plan_sha256'],
            'serial': cls.plan['serial'], 'boot_id': cls.plan['boot_id'], 'backups': backups}))
        (cls.tx / 'placed.json').write_text(json.dumps({'state': 'PLACED_ONLY', 'ui_accepted': False, 'seal_signed': False, 'reboots': 0}))
        cls.execution_path = cls.root / 'synthetic-parent.json'
        execution = {'schema': 'exact-restoration-receipt/v1', 'synthetic': True, 'action': 'apply',
                     'realization_sha256': cls.origin['proof_sha256'], 'source_identity': cls.origin['source_identity'],
                     'source_seal': cls.origin['source_seal'], 'plan_sha256': prepared['plan_sha256'],
                     'executor_rc': 0, 'seal_signed': False, 'ui_accepted': False,
                     'command': [sys.executable, str(cls.package / 'executor.py'), '--plan', str(cls.package / 'plan.json'),
                                 '--execute', '--authorization', str(cls.auth_path), '--authorization-sha256', s.digest(cls.auth_path),
                                 '--out', str(cls.tx), '--action', 'apply']}
        cls.execution_path.write_text(json.dumps(execution))
        cls.binding = {'schema': 'exact-activation-selfcheck-binding/v1', 'checker_sha256': s.digest(HERE / 'selfcheck.py'),
                       'synthetic': True, 'realization': s.pinned(cls.origin_path), 'origin_realization': s.pinned(cls.origin_path),
                       'prepared_manifest': s.pinned(cls.package / 'manifest.json'), 'admission': s.pinned(cls.admission_path),
                       'restore_adapter': s.pinned(adapter), 'execution_receipt': s.pinned(cls.execution_path),
                       'transaction': s.pinned(cls.tx / 'transaction.json'), 'placed': s.pinned(cls.tx / 'placed.json'),
                       'member_receipts': members, 'appendix': None, 'execution_cwd': str(cls.root)}

    def bind(self, binding=None, filename='binding.json'):
        path = self.root / filename
        path.write_text(json.dumps(binding or self.binding))
        return path, s.digest(path)

    @contextmanager
    def altered(self, path, mutate):
        before = path.read_bytes()
        obj = json.loads(before); mutate(obj); path.write_text(json.dumps(obj))
        try:
            yield s.pinned(path)
        finally:
            path.write_bytes(before)

    def history(self, binding=None):
        return s.validate_history(binding or self.binding, self.root, self.origin)

    def test_01_full_offline_admission_exactly_two_activation_changes(self):
        path, sha = self.bind()
        proof, history = s.admit(path, sha, offline=True)
        changes = history['activation_changes']
        self.assertEqual({Path(row['target']).name for row in changes}, {'startup.env', 'startup.expected.sha256'})
        self.assertEqual(history['history']['placed_count'], 487)
        self.assertEqual(len(history['history']['member_receipts']), 487)
        self.assertTrue(history['history']['admission_expired_now'])
        self.assertFalse(history['execution_authority_created'])
        self.assertEqual(s.digest(self.package / 'executor.py'), s.r.EXECUTOR_SHA)
        self.assertEqual(len(proof['files']), 806)

    def test_02_failed_actual_parent_and_synthetic_live_rejected_before_reads(self):
        path, sha = self.bind()
        with self.assertRaisesRegex(ValueError, 'synthetic transaction'):
            s.admit(path, sha, offline=False)
        failed = s.obs.workspace_root(HERE) / 'westlake-harness/benchmark/2026-10-12-v1-seal-execution/exact-5cd-transaction.realization-receipt.json'
        self.assertEqual(s.read(failed)['executor_rc'], -15)
        binding = copy.deepcopy(self.binding); binding['synthetic'] = False; binding['execution_receipt'] = s.pinned(failed)
        path, sha = self.bind(binding)
        with self.assertRaisesRegex(ValueError, 'executor did not succeed'):
            s.admit(path, sha, offline=True)

    def test_03_missing_duplicate_or_drifted_placed_members_rejected(self):
        binding = copy.deepcopy(self.binding); binding['member_receipts'].pop()
        with self.assertRaisesRegex(ValueError, 'placed receipt set incomplete'):
            self.history(binding)
        path = self.tx / 'placed-486.json'
        for mutate in (lambda row: row.update(sha256='0' * 64),
                       lambda row: row.update(target=self.plan['members'][0]['target'])):
            with self.altered(path, mutate) as ref:
                binding = copy.deepcopy(self.binding); binding['member_receipts'][486] = ref
                with self.assertRaisesRegex(ValueError, 'placed target/SHA mismatch'):
                    self.history(binding)

    def test_04_transaction_origin_and_preimage_binding_rejected(self):
        for mutate in (lambda tx: tx.update(boot_id='11111111-1111-1111-1111-111111111111'),
                       lambda tx: tx.update(serial='61b0657200000000000000000324012c'),
                       lambda tx: tx.update(plan_sha256='0' * 64),
                       lambda tx: tx['backups'][0]['before'].update(exists=None)):
            with self.altered(self.tx / 'transaction.json', mutate) as ref:
                binding = copy.deepcopy(self.binding); binding['transaction'] = ref
                with self.assertRaises(ValueError):
                    self.history(binding)

    def test_05_other_file_metadata_or_admission_map_cannot_be_relaxed(self):
        for mutate in (lambda ad: ad.update(signed_by='different-role'),
                       lambda ad: ad.update(prepared_manifest_sha256='0' * 64),
                       lambda ad: ad['target_sha256'].update({self.plan['members'][0]['target']: '0' * 64})):
            with self.altered(self.admission_path, mutate) as ref:
                binding = copy.deepcopy(self.binding); binding['admission'] = ref
                with self.assertRaises(ValueError):
                    self.history(binding)
        with self.altered(self.package / 'plan.json', lambda plan: plan['members'][0]['after'].update(uid=123)):
            with self.assertRaisesRegex(ValueError, 'restoration member drift'):
                self.history()

    def test_06_new_boot_wid_and_activated_sha_all_required(self):
        fixtures = s.load(s.FROZEN / 'test_observations.py', 'r3_synthetic_observation_fixture')
        fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        _, data = fixture.fixture('running')
        boot = '11111111-1111-1111-1111-111111111111'
        data['boot_before'] = data['boot_after'] = boot
        for kind in ('boot_before', 'boot_after'):
            fixture.replace_raw(data, kind, boot + '\n')
        ref = fixture.commit(data)
        # The admission was fully checked in test 01; avoid a second compiler run
        # for pure comparison negatives, retaining exact actual generated bytes.
        proof = copy.deepcopy(self.origin)
        for row in proof['files']:
            if row['target'] in {m['target'] for m in self.plan['members']}:
                row['sha256'] = next(m['sha256'] for m in self.plan['members'] if m['target'] == row['target'])
        files, _ = s.r.running_files(proof, ref, fixture.root, boot)
        observed = {'schema': 'exact-live-observation/v1', 'synthetic': True, 'serial': self.plan['serial'],
                    'boot_before': boot, 'boot_after': boot, 'files': files, 'errors': [], 'parameter_evidence': ref}
        result = s.compare(proof, {'synthetic': True}, observed, fixture.root, self.plan['serial'], boot, True)
        self.assertEqual(result['status'], 'OFFLINE_MATCH')
        self.assertNotEqual(boot, self.plan['boot_id'])
        target = self.origin['parameters']['control_root'] + '/startup.env'
        observed['files'][target] = next(row['sha256'] for row in self.origin['files'] if row['target'] == target)
        self.assertEqual(s.compare(proof, {'synthetic': True}, observed, fixture.root, self.plan['serial'], boot, True)['status'], 'FAIL')
        with self.assertRaises(ValueError):
            s.compare(proof, {'synthetic': True}, observed, fixture.root, self.plan['serial'], self.plan['boot_id'], True)

    def test_07_final_seal_extra_five_are_preserved_and_appendix_drift_rejected(self):
        request_path = Path(self.origin['request']['path'])
        request = s.read(request_path)
        _, _, source_rows = s.r.source_identity(request['source_identity'], request_path.parent)
        hashes = {target: row['sha256'] for target, row in source_rows.items()}
        extra = {'/system/etc/SYNTHETIC-r3-extra-%d' % n: s.hashlib.sha256(('synthetic-' + str(n)).encode()).hexdigest() for n in range(5)}
        apk = next(target for target in hashes if target.endswith('/toutiao.apk'))
        seal = {'schema': 'demo-seal/v1', 'synthetic': True, 'serial': '61b0657200000000000000000324012c',
                'boot_id': self.plan['boot_id'], 'files': {'runtime': hashes, 'boot': extra, 'overlays': {}, 'installation': {apk: hashes[apk]}},
                'system_params': {'persist.westlake.synthetic': 'r3-test-only'},
                'packages': [{'package': 'com.ss.android.article.news', 'version_code': '1', 'apk_path': apk, 'apk_sha256': hashes[apk]}], 'inventories': []}
        seal_path = self.root / 'synthetic-final-seal.json'; seal_path.write_text(json.dumps(seal))
        request['source_identity'] = dict(s.pinned(seal_path), kind='seal'); request['source_seal'] = s.pinned(seal_path)
        request_path = self.root / 'synthetic-sealed-request.json'; request_path.write_text(json.dumps(request))
        appendix_module = s.load(s.r.HERE / 'appendix.py', 'r3_frozen_appendix')
        appendix_dir = self.root / 'synthetic-appendix'
        appendix_module.bind(self.origin_path, request_path, appendix_dir)
        binding = copy.deepcopy(self.binding)
        binding['appendix'] = s.pinned(appendix_dir / 'appendix.json')
        binding['realization'] = s.pinned(appendix_dir / 'sealed-realization/realization.json')
        path, sha = self.bind(binding)
        proof, history = s.admit(path, sha, True)
        self.assertEqual(len(proof['files']), 811)
        self.assertEqual(history['appendix']['additional_static_targets'], extra)
        self.assertEqual({row['target']: row['sha256'] for row in proof['files'] if row['target'] in extra}, extra)
        fixtures = s.load(s.FROZEN / 'test_observations.py', 'r3_extra_observation_fixture')
        fixture = fixtures.ObservationTests('test_running_raw_identity_matches')
        fixture.setUp(); self.addCleanup(fixture.doCleanups)
        _, data = fixture.fixture('running')
        ref = fixture.commit(data)
        boot = self.plan['boot_id']
        files, _ = s.r.running_files(proof, ref, fixture.root, boot)
        observed = {'schema': 'exact-live-observation/v1', 'synthetic': True, 'serial': self.plan['serial'],
                    'boot_before': boot, 'boot_after': boot, 'files': files, 'errors': [], 'parameter_evidence': ref,
                    'system_params': seal['system_params'], 'packages': {'com.ss.android.article.news': {'version_code': '1'}},
                    'inventories': []}
        self.assertEqual(s.compare(proof, history, observed, fixture.root, self.plan['serial'], boot, True)['status'], 'OFFLINE_MATCH')
        for target, expected in extra.items():
            observed['files'].pop(target)
            self.assertEqual(s.compare(proof, history, observed, fixture.root, self.plan['serial'], boot, True)['status'], 'FAIL')
            observed['files'][target] = '0' * 64
            self.assertEqual(s.compare(proof, history, observed, fixture.root, self.plan['serial'], boot, True)['status'], 'FAIL')
            observed['files'][target] = expected
        final = s.r.verify(appendix_dir / 'sealed-realization/realization.json')
        with self.altered(appendix_dir / 'appendix.json', lambda doc: doc['complete_target_sha256'].update({next(iter(extra)): '0' * 64})) as ref:
            binding['appendix'] = ref
            with self.assertRaisesRegex(ValueError, 'complete file set mismatch'):
                s.verify_appendix(binding, self.root, self.origin, final)

    def test_08_nested_synthetic_and_historical_lock_pin_cannot_be_hidden(self):
        for location in ('parameter_evidence', 'source_window_normalization'):
            proof = copy.deepcopy(self.origin)
            if location == 'parameter_evidence':
                proof['parameter_evidence']['synthetic'] = True
            else:
                proof['source_window_normalization'] = [{'parameter_evidence': {'synthetic': True}}]
            with self.assertRaisesRegex(ValueError, 'synthetic proof evidence'):
                s.validate_proof_synthetic(proof, {'synthetic': False})
        identity_path = self.root / 'synthetic-identity-only.json'
        identity_path.write_text(json.dumps({'synthetic': True}))
        proof = copy.deepcopy(self.origin); proof['source_identity'] = s.pinned(identity_path)
        with self.assertRaisesRegex(ValueError, 'synthetic proof evidence'):
            s.validate_proof_synthetic(proof, {'synthetic': False})
        with self.altered(self.admission_path, lambda ad: ad['lock_tool'].update(sha256='0' * 64)) as ref:
            binding = copy.deepcopy(self.binding); binding['admission'] = ref
            with self.assertRaises(ValueError):
                self.history(binding)


if __name__ == '__main__':
    unittest.main(verbosity=2)
