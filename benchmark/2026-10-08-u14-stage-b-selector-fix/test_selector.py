import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
STAGE_B = REPO / 'benchmark/2026-10-03-u14-stage-b'
sys.path.insert(0, str(STAGE_B))
import test_promotion_u14 as stage_tests

tool = stage_tests.tool
hook = stage_tests.hook
LEGACY = 'window*/u14-A*/*/runner/**/record.json'


def record(root, relative, observed=False, **fields):
    source = root / relative / 'record.json'
    source.parent.mkdir(parents=True, exist_ok=True)
    value = dict(key='fixture', package='fixture.app', bms=dict(uid=1001), diagnostics=dict(complete=True))
    value.update(fields)
    source.write_text(json.dumps(value))
    if observed:
        (source.parent / 'processes-t20.txt').write_text('10 1 1001 appspawn-x\n')
        (source.parent / 'hilog.txt').write_text('10-03 11:00:00.000 10 10 I app [WL-KS-PROBE] validateAead=OK\n')
    return source


def complete_fixture(root):
    for index in range(308):
        record(root, 'window1/u14-A-fixture/5ea/runner/apps/%03d' % index, observed=True)
    for index in range(40):
        record(root, 'window6/u14-A-fixture/5cd/candidate-r2/runner/apps/%03d' % index, observed=True)
    for kind, count, prefix in [
        ('recovery-smoke', 72, 'window2/u14-A-fixture/61b/transaction/recovery-smoke-restored'),
        ('executor-state', 125, 'window3/u14-A-fixture/5ea/transaction/baseline/device'),
        ('U13-control', 14, 'window6/u14-A-fixture/5cd/control-r2/runner/apps'),
        ('evidence-copy', 6, 'window6/landing/5cd/candidate/runner/apps'),
    ]:
        for index in range(count):
            source = record(root, prefix + '/%03d' % index)
            if tool.u14_record_class(root, source) != kind:
                raise AssertionError(kind)


class SelectorTests(unittest.TestCase):
    def test_joint_348_and_classified_217_cli_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'u14-stage-a-plan'
            complete_fixture(root)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(tool.main(['--root', str(root), '--selector', tool.U14_SELECTION]), 0)
            summary = json.loads(stdout.getvalue())
            self.assertEqual((summary['records'], summary['PASS'], summary['unknown'], summary['REJECT']), (348, 348, 0, 0))
            self.assertEqual(summary['excluded'], {'known-answer': 0, 'recovery-smoke': 72, 'executor-state': 125,
                'U13-control': 14, 'evidence-copy': 6, 'symlink': 0})

    def test_legacy_direct_308_cli_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'u14-stage-a-plan'
            complete_fixture(root)
            self.assertEqual(len(list(root.glob(LEGACY))), 308)
            with self.assertRaisesRegex(SystemExit, 'selected=308 expected=348 missing=40 extra=0'):
                tool.main(['--root', str(root), '--pattern', LEGACY])

    def test_stage_b_complete_348_passes_mock_only(self):
        with tempfile.TemporaryDirectory() as directory:
            value, reference, decision, _ = stage_tests.fixture(Path(directory))
            gate = decision['process_selftest_gate']
            root = Path(gate['root'])
            for index in range(306):
                record(root, 'window1/u14-A-fixture/5ea/runner/apps/%03d' % index, observed=True)
            for index in range(40):
                record(root, 'window6/u14-A-fixture/5cd/candidate-r2/runner/apps/%03d' % index, observed=True)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(tool.main(['--root', str(root), '--selector', tool.U14_SELECTION,
                    '--out', str(Path(gate['report']).parent)]), 0)
            summary_path = Path(gate['summary'])
            summary_path.write_text(stdout.getvalue())
            gate.update(report_sha256=hook.gb.sha(gate['report']), explanations_sha256=hook.gb.sha(gate['explanations']),
                summary_sha256=hook.gb.sha(summary_path), measured_records=[row['record'] for row in stage_tests.load(Path(gate['report']))['runs']])
            self.assertEqual(len(gate['measured_records']), 348)
            self.assertIsNone(hook.retention_reason(decision, value, reference, {'passed': True}))

    def test_u13_control_mixed_in_cli_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'u14-stage-a-plan'
            record(root, 'window6/u14-A-fixture/5cd/candidate/runner/apps/a')
            record(root, 'window6/u14-A-fixture/5cd/control-r2/runner/apps/a')
            with self.assertRaisesRegex(SystemExit, 'extra=1'):
                tool.main(['--root', str(root), '--pattern', 'window*/u14-A*/*/*/runner/**/record.json'])

    def test_unknown_path_hard_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record(root, 'window1/u14-A-fixture/5ea/runner/apps/a')
            record(root, 'window6/unreviewed/runner/apps/a')
            with self.assertRaisesRegex(SystemExit, 'unclassified U14 record'):
                tool.candidate_records(root, tool.U14_SELECTION)

    def test_symlinks_never_count_as_candidate(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = record(root, 'window1/u14-A-fixture/5ea/runner/apps/a')
            alias = root / 'window1/u14-A-fixture/5ea/runner/apps/alias'
            alias.mkdir()
            (alias / 'record.json').symlink_to(source)
            selected, omitted = tool.u14_domain(root)
            self.assertEqual(selected, [source])
            self.assertEqual(len(omitted['symlink']), 1)

    def test_prelaunch_missing_hilog_unknown_not_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record(root, 'window2/u14-A-fixture/61b/runner/lottery-antennapod-6/a', key='antennapod',
                status='batch_interrupted', clicked=False, error='HDC lost remote status marker', screenshots=[])
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                self.assertEqual(tool.main(['--root', str(root), '--selector', tool.U14_SELECTION]), 0)
            summary = json.loads(stdout.getvalue())
            self.assertEqual((summary['PASS'], summary['unknown'], summary['REJECT']), (0, 1, 0))
            self.assertEqual(len(summary['pre_launch_board_loss']), 1)

    def test_other_missing_hilog_not_silently_explained(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            record(root, 'window1/u14-A-fixture/5ea/runner/apps/a', status='batch_interrupted', clicked=True)
            with self.assertRaises(FileNotFoundError):
                tool.build(root, tool.U14_SELECTION)

    def test_stage_b_forged_legacy_summary_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            value, reference, decision, _ = stage_tests.fixture(Path(directory))
            value['stage_a_selection']['pattern'] = LEGACY
            gate = decision['process_selftest_gate']
            gate['pattern'] = LEGACY
            summary_path = Path(gate['summary'])
            summary = stage_tests.load(summary_path)
            summary['pattern'] = LEGACY
            stage_tests.save(summary_path, summary)
            gate['summary_sha256'] = hook.gb.sha(summary_path)
            self.assertIn('legacy glob refused', hook.retention_reason(decision, value, reference, {'passed': True}))

    def test_stage_b_control_report_refused_even_with_rebound_hashes(self):
        with tempfile.TemporaryDirectory() as directory:
            value, reference, decision, _ = stage_tests.fixture(Path(directory))
            gate = decision['process_selftest_gate']
            root = Path(gate['root'])
            control = record(root, 'window6/u14-A-fixture/5ea/control-r2/runner/apps/a')
            report_path, summary_path = Path(gate['report']), Path(gate['summary'])
            data = stage_tests.load(report_path)
            data['runs'][0]['record'] = str(control)
            stage_tests.save(report_path, data)
            summary = stage_tests.load(summary_path)
            summary['report_sha256'] = hook.gb.sha(report_path)
            stage_tests.save(summary_path, summary)
            gate.update(summary_sha256=hook.gb.sha(summary_path), report_sha256=hook.gb.sha(report_path),
                measured_records=[row['record'] for row in data['runs']])
            self.assertIn('missing or control record', hook.retention_reason(decision, value, reference, {'passed': True}))

    def test_stage_b_domain_growth_requires_fresh_report(self):
        with tempfile.TemporaryDirectory() as directory:
            value, reference, decision, _ = stage_tests.fixture(Path(directory))
            root = Path(decision['process_selftest_gate']['root'])
            record(root, 'window6/u14-A-fixture/5ea/candidate-r2/runner/apps/new', observed=True)
            self.assertIn('missing or control record', hook.retention_reason(decision, value, reference, {'passed': True}))

    def test_portable_entry_paths_preserve_exact_record_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            value, reference, decision, _ = stage_tests.fixture(Path(directory))
            gate = decision['process_selftest_gate']
            gate['root'] = '$WORKSPACES/stage-a'
            gate['measured_records'] = [item.replace(directory + '/', '$WORKSPACES/') for item in gate['measured_records']]
            with patch.object(hook, 'W', Path(directory)):
                self.assertIsNone(hook.retention_reason(decision, value, reference, {'passed': True}))


if __name__ == '__main__':
    unittest.main(verbosity=2)
