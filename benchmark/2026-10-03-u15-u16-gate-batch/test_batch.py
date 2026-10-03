import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import apply_batch as apply
from core import encoded, digest, patch_bytes, append_rows, prepared_bytes

HERE = Path(__file__).resolve().parent


def fixture(root):
    before = encoded(dict(exceptions=[]))
    target = 'knowledge/gates/native-predeploy-exceptions.json'
    path = root / target
    path.parent.mkdir(parents=True)
    path.write_bytes(before)
    stages = []
    for number in [1, 2]:
        rows = [dict(gate='N1', package_manifest_sha256=str(number) * 64,
            inputs_sha256='a' * 64, issue_id=str(number) * 64)]
        after = append_rows(before, rows)
        relative = f'rows-{number}.json'
        (root / relative).write_bytes(encoded(rows))
        patch_file = f'patch-{number}.txt'
        raw_patch = patch_bytes(before, after, target)
        (root / patch_file).write_bytes(raw_patch)
        change = dict(kind='append-exceptions', target=target, before_sha256=digest(before), after_sha256=digest(after),
            rows=relative, rows_sha256=digest(encoded(rows)), patch=patch_file, patch_sha256=digest(raw_patch))
        stages.append(dict(name='stage-' + str(number), changes=[change]))
        before = after
    plan = dict(serials=['test-serial'], selftests=[])
    output = root / 'attempt'
    output.mkdir()
    return stages, plan, output, path


class BatchTests(unittest.TestCase):
    def test_signed_counts_and_exact_scope_projection(self):
        plan = json.loads((HERE / 'change-plan.json').read_text())
        counts = plan['counts']
        self.assertEqual((counts['u15_native'], counts['u16_native'], counts['u16_inherited'], counts['u16_explicit']), (204, 208, 202, 6))
        self.assertEqual(counts['native_after'] - counts['native_before'], 412)
        self.assertEqual(counts['image_after'] - counts['image_before'], 1)
        self.assertEqual(len(json.loads((HERE / 'rows/native-u15-204.json').read_text())), 204)
        self.assertEqual(len(json.loads((HERE / 'rows/native-u16-208.json').read_text())), 208)
        proof = json.loads((HERE / 'evidence/u16-208-proof.json').read_text())
        self.assertEqual(sum(row['classification'] == 'strict-inherited' for row in proof), 202)
        self.assertEqual(sum(row['classification'] == 'explicit-signed' for row in proof), 6)
        self.assertTrue(all(not row['differences'] for row in proof))
        self.assertFalse(plan['execution_enabled'])

    def test_held_requires_documented_empty_exit_one(self):
        apply.held_empty(subprocess.CompletedProcess([], 1, b'', b''))
        for code, stdout, stderr in [(0, b'cx-t0 42 now\n', b''), (0, b'', b''), (2, b'', b''), (1, b'', b'failure')]:
            with self.subTest(code=code, stdout=stdout), self.assertRaises(RuntimeError):
                apply.held_empty(subprocess.CompletedProcess([], code, stdout, stderr))

    def test_stale_target_writes_nothing(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            path.write_bytes(b'drift')
            with self.assertRaises(ValueError):
                apply.transaction(root, root, plan, stages, output, lambda *args: None, lambda *args: None)
            self.assertEqual(path.read_bytes(), b'drift')

    def test_success_keeps_prior_rows_and_independent_stage_checks(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            checked, validated = [], []
            result = apply.transaction(root, root, plan, stages, output,
                lambda *args: checked.append(args[-1].name), lambda *args: validated.append(args[-1].name))
            self.assertEqual(result['status'], 'applied')
            self.assertEqual(checked, ['stage-1', 'stage-1', 'stage-2', 'stage-2'])
            self.assertEqual(validated, ['stage-1', 'stage-2'])
            self.assertEqual(len(json.loads(path.read_text())['exceptions']), 2)

    def test_held_stage_refuses_without_target_write(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            before = path.read_bytes()
            def held(*args):
                raise RuntimeError('held')
            with self.assertRaisesRegex(RuntimeError, 'held'):
                apply.transaction(root, root, plan, stages, output, held, lambda *args: None)
            self.assertEqual(path.read_bytes(), before)

    def test_later_validator_failure_restores_all_original_bytes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            before = path.read_bytes()
            def validate(*args):
                if args[-1].name == 'stage-2':
                    raise RuntimeError('validator failed')
            with self.assertRaisesRegex(RuntimeError, 'validator failed'):
                apply.transaction(root, root, plan, stages, output, lambda *args: None, validate)
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads((output / 'journal.json').read_text())['status'], 'rolled-back')

    def test_partial_write_failure_restores_preimage(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            before = path.read_bytes()
            def failing_write(target, data, mode):
                apply.atomic_write(target, data, mode)
                raise OSError('after rename failure')
            with self.assertRaises(OSError):
                apply.transaction(root, root, plan, stages, output, lambda *args: None, lambda *args: None, write=failing_write)
            self.assertEqual(path.read_bytes(), before)

    def test_rollback_will_not_clobber_external_edits(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            result = apply.transaction(root, root, plan, stages, output, lambda *args: None, lambda *args: None)
            path.write_bytes(b'external-edit')
            with self.assertRaisesRegex(RuntimeError, 'external target drift'):
                apply.restore(root, output, result)
            self.assertEqual(path.read_bytes(), b'external-edit')

    def test_explicit_rollback_restores_original(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            before = path.read_bytes()
            result = apply.transaction(root, root, plan, stages, output, lambda *args: None, lambda *args: None)
            apply.restore(root, output, result)
            self.assertEqual(path.read_bytes(), before)

    def test_patch_tampering_rejected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            (root / stages[0]['changes'][0]['patch']).write_bytes(b'tampered')
            with self.assertRaisesRegex(ValueError, 'unified patch mismatch'):
                prepared_bytes(stages[0]['changes'][0], path.read_bytes(), root)

    def test_static_policies_derived_only_not_bundle_targets(self):
        plan = json.loads((HERE / 'change-plan.json').read_text())
        static = plan['stages'][-1]['changes']
        for change in static:
            candidate = prepared_bytes(change, None, HERE)
            data = json.loads(candidate)
            self.assertFalse(data['execution_enabled'])
            self.assertIn('/.artifacts/applied-static/', change['target'])
            self.assertTrue(all(row['approved_by'] == 'outer(claude)' for row in data['jars'].values()))
            self.assertTrue(all(not row.get('allow_drop') and not row.get('allow_reshape') for row in data['jars'].values()))
        self.assertEqual(sum(len(row['allow_add']) for row in json.loads((HERE / 'inputs/static-u15-after.json').read_text())['jars'].values()), 13)
        self.assertEqual(sum(len(row['allow_add']) for row in json.loads((HERE / 'inputs/static-u16-after.json').read_text())['jars'].values()), 8)

    def test_new_owner_context_binds_exact_class_and_field(self):
        supplement = json.loads((HERE / 'evidence/object-owner-supplement.json').read_text())
        data = (HERE / supplement['context']['snapshot']).read_bytes()
        self.assertEqual(digest(data), 'e358fa5747480aafdd424ab6ad26b22770dba1d904429e300acd1ee7f678f249')
        self.assertLess(supplement['class_header_line'], supplement['static_field_line'])
        self.assertEqual(supplement['class_name'], 'sun.nio.ch.PendingFuture')

    def test_missing_outer_flag_never_enters_transaction(self):
        plan_path = HERE / 'change-plan.json'
        arguments = ['apply_batch.py', '--expected-plan-sha', digest(plan_path.read_bytes())]
        with patch.object(apply.sys, 'argv', arguments), patch.object(apply, 'verify_prerequisites'), \
             patch.object(apply, 'simulate', return_value=[]), patch.object(apply, 'check_held') as held, \
             patch.object(apply, 'transaction') as transaction:
            apply.main()
            held.assert_not_called()
            transaction.assert_not_called()

    def test_image_exact_scope_and_no_extra_rows(self):
        rows = json.loads((HERE / 'rows/image-u16-1.json').read_text())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row['status'], 'approved')
        self.assertEqual(len(row['input_jars']), 9)
        self.assertEqual(row['object']['file_offset_start'], '0x3e3b8')
        self.assertEqual(row['object']['file_offset_end_exclusive'], '0x3e3c0')
        self.assertEqual(row['object']['observed_changed_offsets'], ['0x3e3b9', '0x3e3ba', '0x3e3bb'])
        self.assertEqual(sum(row['identical'] for row in row['outputs']), 26)

    def test_maintenance_mutex_blocks_unrecorded_holder(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict(apply.os.environ, {'BOARD_LOCK_DIR': temporary}):
            root = Path(temporary)
            serials = ['first', 'second']
            for serial in serials:
                (root / (serial + '.lock')).touch()
            with apply.maintenance_mutexes(serials):
                with self.assertRaisesRegex(RuntimeError, 'mutex busy'):
                    with apply.maintenance_mutexes(serials):
                        self.fail('Must not enter')
            with apply.maintenance_mutexes(serials):
                pass

    def test_static_output_removal_on_later_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = json.loads((HERE / 'change-plan.json').read_text())
            stage = copy.deepcopy(before['stages'][-1])
            target = root / stage['changes'][0]['target']
            output = root / 'attempt'
            output.mkdir()
            def validate(*args):
                raise RuntimeError('fail static known answer')
            with patch.object(apply, 'original_policy_check'), self.assertRaises(RuntimeError):
                apply.transaction(root, HERE, before, [stage], output, lambda *args: None, validate)
            self.assertFalse(target.exists())

    def test_image_row_input_tampering_refuses_exact_patch(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            before = encoded(dict(exceptions=[]))
            rows = json.loads((HERE / 'rows/image-u16-1.json').read_text())
            after = append_rows(before, rows)
            target = 'knowledge/gates/image-provenance-exceptions.json'
            (root / 'rows.json').write_bytes(encoded(rows))
            raw = patch_bytes(before, after, target)
            (root / 'image.patch').write_bytes(raw)
            change = dict(kind='append-exceptions', target=target, before_sha256=digest(before), after_sha256=digest(after),
                rows='rows.json', rows_sha256=digest(encoded(rows)), patch='image.patch', patch_sha256=digest(raw))
            self.assertEqual(prepared_bytes(change, before, root), after)
            rows[0]['input_jars']['adapter-mainline-stubs.jar'] = '0' * 64
            (root / 'rows.json').write_bytes(encoded(rows))
            with self.assertRaisesRegex(ValueError, 'row digest mismatch'):
                prepared_bytes(change, before, root)

    def test_corrupt_backup_refuses_before_other_output_deleted(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            stages, plan, output, path = fixture(root)
            result = apply.transaction(root, root, plan, stages, output, lambda *args: None, lambda *args: None)
            original = next(iter(result['originals'].values()))
            (output / original['backup']).write_bytes(b'corrupt-backup')
            relative = 'benchmark/2026-10-03-u15-u16-gate-batch/.artifacts/applied-static/static-policy-u15-approved.json'
            new_path = root / relative
            new_path.parent.mkdir(parents=True)
            new_path.write_bytes(b'generated')
            result['originals'][relative] = dict(target=relative, sha256=None, mode=0o644,
                backup=None, allowed_postimages=[digest(b'generated')])
            with self.assertRaisesRegex(RuntimeError, 'backup SHA mismatch'):
                apply.restore(root, output, result)
            self.assertEqual(new_path.read_bytes(), b'generated')


if __name__ == '__main__':
    unittest.main()
