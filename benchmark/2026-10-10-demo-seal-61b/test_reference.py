import contextlib
import copy
import io
from pathlib import Path
import unittest
from unittest.mock import patch

import test_orchestration as fixtures


seal = fixtures.seal


class ReferenceTests(unittest.TestCase):
    def setUp(self):
        self.fixture = fixtures.OrchestrationTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.out = self.fixture.out

    def t3_fixture(self, mode='v1'):
        plan, authorization = self.fixture.bound_fixture(mode)
        signoff = self.out / seal.T3_SIGNOFF_SUFFIX
        fixtures.save(signoff, dict(board=seal.SERIAL, verdicts={
            'key-' + str(number): dict(verdict='lit', batch='fixture') for number in range(128)}))
        digest = seal.sha(signoff)
        image = self.out / 'fixture-image'
        image.write_bytes(b'MOCK image, not a live screenshot')

        def pin(path):
            return dict(path=str(path), sha256=seal.sha(path))

        index = dict(signoff_sha256=digest, records={})
        for number in range(128):
            key = 'key-' + str(number)
            record = self.out / 't3-records' / key / 'record.json'
            fixtures.save(record, dict(key=key, serial=seal.SERIAL))
            index['records'][key] = dict(record=pin(record), image=pin(image), batch='fixture')
        index_path = self.out / 't3-index.json'
        fixtures.save(index_path, index)
        enforce = self.out / 'enforce.txt'
        enforce.write_text('1\n')
        prior_rows = []
        notes = dict(serial=seal.BASELINE_SERIAL, signoff_sha256=digest, keys={}, enforce=pin(enforce))
        for number in range(89):
            key = 'key-' + str(number)
            record = self.out / 'prerun' / key / 'record.json'
            fixtures.save(record, dict(key=key, serial=seal.BASELINE_SERIAL, finished_at='fixture-only', apk_sha256='b' * 64))
            signature = dict(package='fixture.app', apk_sha256='b' * 64)
            row = dict(key=key, category='changed', signature=signature, reason=['image_sha256'],
                       semantic=dict(**{'class': 'suspect', 'reason': 'fixture-only'}))
            prior_rows.append(row)
            notes['keys'][key] = dict(record=pin(record), **{field: row[field] for field in ('category', 'signature', 'reason', 'semantic')})
        comparison = self.out / 'prerun-comparison.json'
        fixtures.save(comparison, dict(signoff_sha256=digest, keys=prior_rows))
        notes['comparison'] = pin(comparison)
        notes_path = self.out / 'prerun-notes.json'
        fixtures.save(notes_path, notes)
        plan['reference'] = dict(kind='61b-t3', signoff=pin(signoff), baseline_t3=str(self.out / 't3-records'),
                                 record_index=pin(index_path), enforcing_prerun=pin(notes_path))
        plan['inputs']['signoff_5cd'] = dict(path='<unused-5cd>', sha256=None)
        plan['baseline_5cd_t3'] = '<unused-5cd>'
        return plan, authorization, digest

    def test_both_references_pass_in_both_modes_and_seal_names_reference(self):
        for mode in ('v1', 'v2'):
            for kind in ('5cd', '61b-t3'):
                with self.subTest(mode=mode, reference=kind):
                    if kind == '61b-t3':
                        plan, authorization, digest = self.t3_fixture(mode)
                    else:
                        plan, authorization = self.fixture.bound_fixture(mode)
                        digest = seal.T3_SIGNOFF_SHA
                    with patch.object(seal, 'T3_SIGNOFF_SHA', digest):
                        seal.validate(plan, authorization, 'a' * 64, mode=mode, reference=kind)
                        transport = fixtures.FixtureTransport(self.out, plan)
                        workflow = seal.Workflow(plan, self.out, transport, mode=mode, reference=kind,
                                                  plan_sha='a' * 64, sleep=lambda seconds: None)
                        with contextlib.redirect_stdout(io.StringIO()):
                            workflow.run()
                    result = seal.read(self.out / 'seal.json')
                    self.assertEqual(result['seal_stage'], mode)
                    self.assertEqual(result['regression_reference']['kind'], kind)
                    self.assertEqual(result['regression_reference']['signoff'], plan['reference']['signoff'])
                    comparison = seal.read(self.out / 'regression/comparison.json')
                    self.assertEqual(comparison['summary']['changed'], 128)
                    if kind == '61b-t3':
                        self.assertEqual(comparison['enforcing_annotation']['suspect_keys'], 89)
                        self.assertEqual(comparison['enforcing_annotation']['automatic_exemptions'], 0)
                        self.assertEqual(comparison['keys'][0]['category'], 'changed')

    def test_bad_reference_file_sha_refuses_both_modes(self):
        for mode in ('v1', 'v2'):
            for kind in ('5cd', '61b-t3'):
                with self.subTest(mode=mode, reference=kind):
                    if kind == '61b-t3':
                        plan, authorization, digest = self.t3_fixture(mode)
                    else:
                        plan, authorization = self.fixture.bound_fixture(mode)
                        digest = seal.T3_SIGNOFF_SHA
                    plan['reference']['signoff']['sha256'] = '0' * 64
                    with patch.object(seal, 'T3_SIGNOFF_SHA', digest), self.assertRaisesRegex(ValueError, 'drifted input'):
                        seal.validate(plan, authorization, 'a' * 64, mode=mode, reference=kind)

    def test_t3_wrong_board_refuses_even_when_file_sha_matches(self):
        for mode in ('v1', 'v2'):
            plan, authorization, digest = self.t3_fixture(mode)
            source = Path(plan['reference']['signoff']['path'])
            value = seal.read(source)
            value['board'] = seal.BASELINE_SERIAL
            fixtures.save(source, value)
            plan['reference']['signoff']['sha256'] = seal.sha(source)
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'signed 61b-t3 baseline'):
                seal.validate(plan, authorization, 'a' * 64, mode=mode, reference='61b-t3')

    def test_t3_noncanonical_sha_refuses(self):
        plan, authorization, digest = self.t3_fixture()
        with self.assertRaisesRegex(ValueError, 'exact canonical t3 signoff SHA'):
            seal.validate(plan, authorization, 'a' * 64, reference='61b-t3')

    def test_cli_kind_cannot_differ_from_authorized_plan(self):
        plan, authorization = self.fixture.bound_fixture('v1')
        with self.assertRaisesRegex(ValueError, 'reference differs'):
            seal.validate(plan, authorization, 'a' * 64, reference='61b-t3')

    def test_unknown_reference_refuses(self):
        plan, authorization = self.fixture.bound_fixture('v1')
        plan['reference']['kind'] = 'unknown'
        with self.assertRaisesRegex(ValueError, 'unknown regression reference'):
            seal.validate_reference(plan, 'unknown', [])

    def test_5cd_receipt_cannot_use_61b_serial(self):
        plan, authorization = self.fixture.bound_fixture('v1')
        transport = fixtures.FixtureTransport(self.out, plan)
        original = transport.run

        def altered(name, argv, env=None):
            result = original(name, argv, env)
            if name == 'regression_review':
                path = self.out / 'regression_review.json'
                receipt = seal.read(path)
                receipt['baseline_serial'] = seal.SERIAL
                fixtures.save(path, receipt)
            return result

        transport.run = altered
        workflow = seal.Workflow(plan, self.out, transport, plan_sha='a' * 64)
        with contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'baseline serial/reference mismatch'):
            workflow.run()

    def test_t3_baseline_serial_and_signoff_sha_receipt_both_required(self):
        for field, value in [('baseline_serial', seal.BASELINE_SERIAL), ('signoff_sha256', '0' * 64),
                             ('reference_kind', '5cd')]:
            with self.subTest(field=field):
                plan, authorization, digest = self.t3_fixture()
                transport = fixtures.FixtureTransport(self.out, plan)
                original = transport.run

                def altered(name, argv, env=None):
                    result = original(name, argv, env)
                    if name == 'regression_review':
                        path = self.out / 'regression_review.json'
                        receipt = seal.read(path)
                        receipt[field] = value
                        fixtures.save(path, receipt)
                    return result

                transport.run = altered
                workflow = seal.Workflow(plan, self.out, transport, reference='61b-t3', plan_sha='a' * 64)
                with patch.object(seal, 'T3_SIGNOFF_SHA', digest), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'reference mismatch|signoff binding'):
                    workflow.run()

    def test_annotations_do_not_exempt_and_require_matching_app_identity(self):
        plan, authorization, digest = self.t3_fixture()
        notes = seal.read(plan['reference']['enforcing_prerun']['path'])
        rows = [dict(key='key-0', category='changed', signature=copy.deepcopy(notes['keys']['key-0']['signature']), reason=['image_sha256']),
                dict(key='key-1', category='same', signature=notes['keys']['key-1']['signature']),
                dict(key='key-2', category='changed', signature=dict(package='other.app', apk_sha256='b' * 64)),
                dict(key='key-127', category='changed', signature=dict(package='fixture.app', apk_sha256='b' * 64))]
        report = dict(keys=rows, summary=dict(changed=3, same=1, missing=0))
        before = copy.deepcopy(report['summary'])
        seal.annotate_enforcing(report, notes)
        self.assertEqual([row['env_enforcing_suspect'] for row in rows], [True, False, False, False])
        self.assertEqual(report['summary'], before)
        self.assertEqual(rows[0]['category'], 'changed')

    def test_changed_annotation_is_not_a_signed_review(self):
        plan, authorization, digest = self.t3_fixture()
        transport = fixtures.FixtureTransport(self.out, plan)
        transport.unsigned = True
        workflow = seal.Workflow(plan, self.out, transport, reference='61b-t3')
        with patch.object(seal, 'T3_SIGNOFF_SHA', digest), contextlib.redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, 'unsigned'):
            workflow.run()

    def test_prerun_record_drift_refuses(self):
        plan, authorization, digest = self.t3_fixture()
        notes = seal.read(plan['reference']['enforcing_prerun']['path'])
        Path(notes['keys']['key-0']['record']['path']).write_text('{}')
        with patch.object(seal, 'T3_SIGNOFF_SHA', digest), self.assertRaisesRegex(ValueError, 'drifted input'):
            seal.validate(plan, authorization, 'a' * 64, reference='61b-t3')


if __name__ == '__main__':
    unittest.main()
