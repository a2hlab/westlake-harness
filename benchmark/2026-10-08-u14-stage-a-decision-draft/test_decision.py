import json
from pathlib import Path
import tempfile
import unittest

import build_decision as builder


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        evidence = self.folder / 'hilog.txt'
        evidence.write_text('synthetic pre-bind observation\n')
        self.reference = dict(total_lit=126, keys={f'key-{index}': {'verdict': 'lit'} for index in range(126)})
        self.composition = dict(bundle_sha256='synthetic-bundle', native_manifest_sha256='synthetic-manifest')
        self.report = dict(schema_version=2, run_count=1, runs=[dict(record='synthetic/record.json',
            key='key-0', status='unknown', processes={}, complete_hilog=False, validateAead_OK_count=0, badtag_count=0)])
        self.review = dict(approved_by='outer(claude)', **self.composition, explanations=[dict(record='synthetic/record.json',
            key='key-0', pid='*', line_sha256='unknown', line_number=None, reason='synthetic missing probe, not success',
            evidence=str(evidence), evidence_sha256=builder.sha(evidence))])
        self.decision = dict(signed_by='outer(claude)', signed_at='synthetic-test-only', promotion_authorized=True,
            **self.composition, confirmed_regressions=[], explanations_file='explanations.json',
            stage_A_regression_verdict=dict(u14_reference_lit_total=126, measured=126,
                same_or_lit_within_k_of_n=126, confirmed_regressions=0), process_selftest_gate={})
        self.failure_count = 0
        self.bind()

    def bind(self):
        report = builder.write(self.folder, 'selftest-u14-stage-a.json', self.report)
        self.review['report_sha256'] = builder.sha(report)
        explanations = builder.write(self.folder, 'explanations.json', self.review)
        summary = builder.write(self.folder, 'selftest-summary.json', dict(report_sha256=builder.sha(report),
            failure_lines_any_pid=self.failure_count))
        self.decision['process_selftest_gate'] = dict(report_sha256=builder.sha(report),
            explanations_sha256=builder.sha(explanations), summary_sha256=builder.sha(summary), measured_records=['synthetic/record.json'])

    def reason(self):
        return builder.packet_reason(self.decision, self.composition, self.reference, self.folder)

    def test_correct_synthetic_input_passes(self):
        self.assertIsNone(self.reason())

    def test_wrong_bundle_rejects(self):
        self.decision['bundle_sha256'] = 'other-bundle'
        self.assertEqual(self.reason(), 'signoff belongs to another bundle')

    def test_real_common_decision_cannot_bind_61b_variant(self):
        common = json.loads((builder.HERE / 'decision-draft-common.json').read_text())
        other = json.loads((builder.HERE / 'decision-draft-61b.json').read_text())
        composition = dict(bundle_sha256=other['bundle_sha256'], native_manifest_sha256=other['native_manifest_sha256'])
        self.assertEqual(builder.packet_reason(common, composition, self.reference, builder.HERE),
            'signoff belongs to another bundle')

    def test_missing_one_explanation_rejects_even_when_rebound(self):
        self.review['explanations'] = []
        self.bind()
        self.assertEqual(self.reason(), 'not every selftest error/unknown has an exact outer explanation')

    def test_changed_report_bytes_reject(self):
        source = self.folder / 'selftest-u14-stage-a.json'
        source.write_text(source.read_text() + ' ')
        self.assertEqual(self.reason(), 'process selftest report not bound by outer')

    def test_badtag_rejects_even_when_rebound(self):
        self.report['runs'][0]['badtag_count'] = 1
        self.bind()
        self.assertIn('unconditionally rejects', self.reason())

    def test_any_pid_failure_rejects_even_without_pid_in_processes(self):
        hits = builder.aggregate.failure_lines_any_pid(['10-03 12:00:00.001 98765 98765 E test [WL-KS-PROBE] selftest AEADBadTagException'])
        self.assertEqual(hits, [1])
        self.failure_count = len(hits)
        self.bind()
        self.assertEqual(self.reason(), 'any-pid selftest failure unconditionally rejects promotion')

    def test_123_of_126_rejects(self):
        self.decision['stage_A_regression_verdict']['measured'] = 123
        self.assertEqual(self.reason(), 'all signed U14-reference-lit keys must be measured')

    def test_124_of_126_rejects(self):
        self.decision['stage_A_regression_verdict']['measured'] = 124
        self.assertEqual(self.reason(), 'all signed U14-reference-lit keys must be measured')

    def test_observed_125_of_126_also_rejects(self):
        self.decision['stage_A_regression_verdict']['measured'] = 125
        self.assertEqual(self.reason(), 'all signed U14-reference-lit keys must be measured')

    def test_missing_outer_authorization_rejects(self):
        self.decision['promotion_authorized'] = None
        self.assertEqual(self.reason(), 'promotion not authorized by outer')

    def test_evidence_byte_drift_rejects(self):
        (self.folder / 'hilog.txt').write_text('changed\n')
        self.assertEqual(self.reason(), 'selftest explanation evidence drift')

    def test_selector_includes_nested_candidate_and_excludes_control_copy_state(self):
        examples = {
            'window1/u14-A1/5ea/runner/group/key/record.json': 'candidate',
            'window6/u14-A6/5cd/candidate-r2/runner/key/record.json': 'candidate',
            'window6/u14-A6/5cd/control-r2/runner/key/record.json': 'U13-control',
            'window6/landing/5cd/candidate/runner/key/record.json': 'evidence-copy',
            'window1/evidence/key/record.json': 'evidence-copy',
            'evidence/fixture/record.json': 'known-answer',
            'window1/u14-A1/5ea/transaction/recovery-smoke-one/key/record.json': 'recovery-smoke',
            'window6/u14-A6/5cd/candidate/transaction/baseline/device/record.json': 'executor-state',
        }
        for relative, expected in examples.items():
            source = self.folder / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            source.write_text('{}')
            self.assertEqual(builder.record_class(self.folder, source), expected)

    def test_symlink_not_double_counted(self):
        root = self.folder / 'selection'
        source = root / 'window1/u14-A1/5ea/runner/key/record.json'
        source.parent.mkdir(parents=True)
        source.write_text('{}')
        alias = source.parent / 'alias/record.json'
        alias.parent.mkdir()
        alias.symlink_to(source)
        selected, excluded = builder.select(root)
        self.assertEqual(selected, [source])
        self.assertEqual(len(excluded['symlink']), 1)

    def test_unclassified_record_rejects(self):
        source = self.folder / 'unexpected/record.json'
        source.parent.mkdir()
        source.write_text('{}')
        with self.assertRaisesRegex(ValueError, 'unclassified'):
            builder.record_class(self.folder, source)

    def test_prelaunch_interruption_is_unknown_not_success(self):
        source = self.folder / 'interrupted/record.json'
        source.parent.mkdir()
        record = dict(status='batch_interrupted', clicked=False, error='HDC lost remote status marker', screenshots=[])
        reason = builder.interruption_reason(record, source)
        self.assertIn('unknown, not crypto success', reason)
        record['clicked'] = True
        self.assertIsNone(builder.interruption_reason(record, source))

    def test_unsigned_shipped_drafts_and_complete_issue_set(self):
        report = json.loads((builder.HERE / 'selftest-u14-stage-a.json').read_text())
        required = {(run['record'], pid) for run, pid in builder.aggregate.issues(report)}
        for tag in ['common', '61b']:
            decision = json.loads((builder.HERE / f'decision-draft-{tag}.json').read_text())
            review = json.loads((builder.HERE / f'selftest-explanations-{tag}.json').read_text())
            self.assertIsNone(decision['promotion_authorized'])
            self.assertIsNone(decision['signed_by'])
            self.assertFalse(decision['execution_enabled'])
            self.assertIsNone(review['approved_by'])
            self.assertEqual(builder.sha(builder.HERE / 'inputs/reference.json'), decision['reference_sha256'])
            self.assertEqual(required, {(row['record'], row['pid']) for row in review['explanations']})
            self.assertEqual(len(required), len(review['explanations']))

    def test_actual_partition_and_visual_pending_rows(self):
        selection = json.loads((builder.HERE / 'record-selection.json').read_text())
        visual = json.loads((builder.HERE / 'visual-summary.json').read_text())
        summary = json.loads((builder.HERE / 'selftest-summary.json').read_text())
        self.assertEqual(len(selection['selected']), summary['records'])
        self.assertEqual(len(set(selection['selected'])), summary['records'])
        self.assertEqual(summary['records'], 348)
        self.assertEqual(summary['windows']['window6'], 40)
        self.assertEqual(summary['failure_lines_any_pid'], 0)
        self.assertEqual(visual['pending_keys'], ['fd-organicmaps', 'fd-seal'])
        self.assertEqual(len(visual['measured_lit_keys']), 124)
        self.assertEqual(visual['reference_total'], 126)
        self.assertEqual(visual['observed_reference_keys'], 125)
        self.assertEqual(set(visual['gains']), {'vlc', 'termux', 'cv2-org-andresoviedo-dddmodel2'})


if __name__ == '__main__':
    unittest.main(verbosity=2)
