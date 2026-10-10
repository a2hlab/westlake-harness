import copy
from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import audit_scope as audit


class ScopeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.recipe = audit.load_recipe()
        self.names = ['libcase' + str(index) + '.so' for index in range(23)]
        self.contexts = {audit.SANDBOX: 'u:object_r:system_etc_file:s0',
                         **{audit.ROUTE + 'generation/' + name: 'u:object_r:system_lib_file:s0' for name in self.names}}
        self.proofs = [dict(domain='appspawn', label=label, **{'class': 'file'}, perm=permission,
                            rule='SYNTHETIC allow fixture') for label in ['system_etc_file', 'system_lib_file']
                       for permission in ['read', 'open', 'getattr', 'map']]

    def snapshot(self, contexts=None, bad_raw=False):
        contexts = self.contexts if contexts is None else contexts
        (self.base / 'raw').mkdir(exist_ok=True)
        blob = ''.join(label + ' ' + path + '\n' for path, label in contexts.items()).encode()
        (self.base / 'raw/labels.txt').write_bytes(blob)
        (self.base / 'raw/stderr.txt').write_bytes(b'')
        snapshot = dict(schema_version=1, serial='fixture', boot_id='fixture-boot', boot_stable=True,
                        selinux_enforce='Enforcing', collection_complete=True, complete=False, errors=[],
                        labels=contexts, captured_at='2026-10-10T13:00:00+08:00', items={'labels': dict(
                            cmd='fixture only', rc=0, raw='raw/labels.txt', stderr_raw='raw/stderr.txt',
                            raw_sha256='0' * 64 if bad_raw else hashlib.sha256(blob).hexdigest(),
                            stderr_sha256=hashlib.sha256(b'').hexdigest())})
        path = self.base / 'snapshot.json'
        path.write_text(json.dumps(snapshot))
        return path

    def test_scoped_pass_does_not_require_full_reboot_inputs(self):
        report = audit.snapshot_rows(self.snapshot(), self.recipe, self.proofs, self.names)
        self.assertEqual(report['status'], 'PASS')
        self.assertFalse(report['declared_capture_coverage_complete'])
        self.assertEqual(len(report['checks']), 24)

    def test_missing_route_member_is_unknown(self):
        contexts = copy.deepcopy(self.contexts)
        del contexts[audit.ROUTE + 'generation/' + self.names[0]]
        report = audit.snapshot_rows(self.snapshot(contexts), self.recipe, self.proofs, self.names)
        self.assertEqual(report['status'], 'UNKNOWN')
        self.assertEqual(report['missing_route_basenames'], [self.names[0]])

    def test_data_label_fails_recipe_without_claiming_policy_denial(self):
        contexts = copy.deepcopy(self.contexts)
        contexts[audit.SANDBOX] = 'u:object_r:data_local_tmp:s0'
        report = audit.snapshot_rows(self.snapshot(contexts), self.recipe, self.proofs, self.names)
        row = next(row for row in report['checks'] if row['path'] == audit.SANDBOX)
        self.assertEqual(row['status'], 'FAIL')
        self.assertIn('denial is not inferred', row['reason'])
        self.assertEqual(row['policy_proofs'], [])

    def test_missing_positive_proof_or_label_raw_does_not_pass(self):
        path = self.snapshot()
        self.assertEqual(audit.snapshot_rows(path, self.recipe, [], self.names)['status'], 'UNKNOWN')
        snapshot = json.loads(path.read_text())
        snapshot['labels'][audit.SANDBOX] = 'u:object_r:system_lib_file:s0'
        path.write_text(json.dumps(snapshot))
        self.assertEqual(audit.snapshot_rows(path, self.recipe, self.proofs, self.names)['status'], 'FAIL')

    def test_raw_drift_refuses(self):
        with self.assertRaisesRegex(ValueError, 'integrity'):
            audit.snapshot_rows(self.snapshot(bad_raw=True), self.recipe, self.proofs, self.names)

    def test_manual_original_basename_count_and_identity(self):
        text = ''.join('u:object_r:data_local_tmp:s0 ' + name + '\n' for name in self.names + ['appdata-sandbox.json'])
        report = audit.manual_libraries(text)
        self.assertEqual(len(report), 24)
        self.assertEqual(report['libcase0.so']['line'], 1)
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            audit.manual_libraries(text + text.splitlines()[0])
        with self.assertRaisesRegex(ValueError, 'expected original'):
            audit.manual_libraries('\n'.join(text.splitlines()[:-1]))

    def test_readonly_capture_plan_explicitly_recurses_route(self):
        plan = json.loads((Path(__file__).parent / 'capture-scope-plan.json').read_text())
        targets = audit.load_recipe()['required_targets']
        self.assertFalse(plan['execution_enabled'])
        declared = __import__('selinux_label_audit').plan_targets(plan, self.recipe)
        route = next(row for row in declared if row['target'] == audit.ROUTE.rstrip('/'))
        self.assertEqual(route['kind'], 'directory')
        self.assertIn('find /system/lib64/westlake/route-a', __import__('selinux_label_audit').read_command(route))
        self.assertTrue(targets)

    def test_recorded_real_answers_are_scoped_not_reboot_authorization(self):
        recorded = json.loads((Path(__file__).parent / 'prediction.json').read_text())
        self.assertFalse(recorded['safe_to_reboot'])
        self.assertFalse(recorded['execution_enabled'])
        self.assertFalse(recorded['board_access'])
        for name, count in [('5cd', 58), ('5ea', 30)]:
            case = recorded['cases'][name]
            self.assertEqual(case['status'], 'PASS')
            self.assertEqual(len(case['checks']), count)
            self.assertEqual(case['missing_route_basenames'], [])
            self.assertTrue(all(row['evidence'] and row['policy_proofs'] and row['status'] == 'PASS'
                                for row in case['checks']))
        case = recorded['cases']['61b-pre-fix']
        self.assertEqual(case['affected_basename_count'], 24)
        self.assertEqual(case['status'], 'FAIL')
        libraries = [row for row in case['checks'] if row['phase'] == 'native-map']
        self.assertEqual(len(libraries), 23)
        self.assertEqual(sum(len(row['canonical_candidates']) > 1 for row in libraries), 22)
        self.assertTrue(all(row['actual'] == 'u:object_r:data_local_tmp:s0' and
                            row['status'] == 'FAIL' and not row['policy_denial_proven']
                            for row in case['checks']))

    def test_pinned_missing_drift_and_symlink_refuse(self):
        path = self.base / 'input.json'
        path.write_text('{}')
        reference = dict(path=str(path), sha256=audit.digest(path))
        self.assertEqual(audit.pinned(reference, self.base), path)
        path.write_text('{"drift": true}')
        with self.assertRaisesRegex(ValueError, 'drifted'):
            audit.pinned(reference, self.base)
        link = self.base / 'link.json'
        link.symlink_to(path)
        with self.assertRaisesRegex(ValueError, 'drifted'):
            audit.pinned(dict(path=str(link), sha256=audit.digest(path)), self.base)

    def test_label_without_exact_raw_row_stays_unknown(self):
        path = self.snapshot()
        snapshot = json.loads(path.read_text())
        blob = ''.join(label + ' ' + target + '\n' for target, label in self.contexts.items()
                       if target != audit.SANDBOX).encode()
        (self.base / 'raw/labels.txt').write_bytes(blob)
        snapshot['items']['labels']['raw_sha256'] = hashlib.sha256(blob).hexdigest()
        path.write_text(json.dumps(snapshot))
        self.assertEqual(audit.snapshot_rows(path, self.recipe, self.proofs, self.names)['status'], 'UNKNOWN')

    def test_preseal_cli_is_pinned_scoped_and_never_safe(self):
        source = self.snapshot()
        manifest = self.base / 'inputs.json'
        manifest.write_text('{}')
        manual = {name: {} for name in self.names}
        args = ['--inputs', str(manifest), '--observed-snapshot', str(source),
                '--snapshot-sha256', audit.digest(source), '--out', str(self.base / 'out')]
        with mock.patch.object(audit, 'context', return_value=(self.recipe, {'proofs': self.proofs}, manual)), \
                redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(audit.main(args), 0)
        report = json.loads((self.base / 'out/prediction.json').read_text())
        self.assertEqual(report['cases']['fixture']['status'], 'PASS')
        self.assertFalse(report['safe_to_reboot'])
        self.assertFalse(report['execution_enabled'])
        args[-1] = str(self.base / 'refused')
        args[args.index('--snapshot-sha256') + 1] = '0' * 64
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(audit.main(args), 2)
        self.assertFalse((self.base / 'refused').exists())


if __name__ == '__main__':
    unittest.main()
