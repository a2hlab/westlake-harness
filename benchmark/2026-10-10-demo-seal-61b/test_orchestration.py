import contextlib
import copy
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
SPEC = importlib.util.spec_from_file_location('seal61b', REPO / 'scripts/lab/demo_seal_61b.py')
seal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(seal)
BOOTS = ['11111111-1111-1111-1111-111111111111', '22222222-2222-2222-2222-222222222222',
         '33333333-3333-3333-3333-333333333333']


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value))


class FixtureTransport:
    def __init__(self, out, plan):
        self.out, self.plan, self.calls = out, plan, []
        self.fail = None
        self.live_view = None
        self.same_boot = False
        self.unsigned = False
        self.socket = '660:0:6005:u:object_r:appspawn_socket:s0'
        self.parent = '44 1 0 appspawn-x'
        self.invalid = False
        self.advisory_exit = 0
        self.baseline_drift = False
        self.second_same_boot = False
        self.installer_drift = False
        self.boot_counter = 0
        self.omit_boat = False
        self.slot_boot = None
        self.slot_enabled = True
        self.seal_stage = None
        self.archive_missing = False
        self.archive_sha_drift = False
        self.archive_extra = False
        self.physical_files = []

    def run(self, name, argv, env=None):
        self.calls.append((name, argv, env))
        if name == self.fail:
            return 7, 'fixture failure'
        if name in ('initial-boot', 'pre-disable-boot'):
            return 0, BOOTS[0]
        if name == 'pre-autonomous-boot':
            return 0, BOOTS[1]
        if name == 'final-boot':
            return 0, BOOTS[2]
        if name.startswith('wait-'):
            boot = BOOTS[0] if self.same_boot else BOOTS[1 if name == 'wait-bare-boot' else 2]
            if name == 'wait-autonomous-boot' and self.second_same_boot:
                boot = BOOTS[1]
            return 0, boot + '\ntrue\n'
        if name in ('pre-enforcing', 'post-enforcing'):
            return 0, 'Enforcing\n'
        if name == 'pre-319':
            expected = seal.read(self.plan['inputs']['baseline_319']['path'])['expected']
            return 0, '\n'.join(('e' * 64 if self.baseline_drift else expected[target]) + '  ' + target for target in argv[-1].split()[1:])
        if name == 'bare-seq1-inventory':
            expected = seal.archived_base(seal.read(self.plan['inputs']['baseline_319']['path'])['expected'])
            paths = list(expected)
            if self.archive_missing:
                paths.pop()
            if self.archive_extra:
                paths.append(seal.ROOT + '/sources/seq1/unexpected.so')
            return 0, '\n'.join(paths) + '\n'
        if name == 'bare-seq1-sha':
            expected = seal.archived_base(seal.read(self.plan['inputs']['baseline_319']['path'])['expected'])
            return 0, '\n'.join(('e' * 64 if self.archive_sha_drift else expected[target]) + '  ' + target
                                for target in argv[-1].split()[1:])
        if name == 'bare-physical-inventory':
            return 0, '\n'.join(self.physical_files)
        if name.startswith('no-live-recover-bind-'):
            mounts = '1 0 0:1 / / rw - ext4 /dev/root rw\n'
            if name == 'no-live-recover-bind-' + str(self.live_view):
                mounts += '2 1 0:2 /westlake-demo/u13/sources/seq1 /system/android rw - ext4 /dev/data rw\n'
            return 0, mounts
        if name == 'installer-sha':
            return 0, ('e' * 64 if self.installer_drift else self.plan['installer']['sha256']) + '  ' + self.plan['installer']['board_path']
        if name == 'installer':
            return 0, 'INSTALL_OK\n'
        if name in seal.PROVIDERS:
            receipt = dict(serial=seal.SERIAL, plan_sha256=env['DEMO_SEAL_PLAN_SHA'],
                           boot_id=env['DEMO_SEAL_BOOT_ID'], no_conflict=True, enabled=True,
                           uid_mode='installed-host-dynamic', reconcile_checked=True, immutable_preserved=True,
                           approved_by='outer(claude)' if not self.unsigned else 'fixture-unapproved',
                           approved_at='fixture-only', no_mac_repair=True,
                           checks={key: True for key in ('parent_init', 'socket_0660', 'hw_t20_lit',
                                'zz_t20_lit', 'boat_five_touch_lap', 'toutiao_desktop_click_refresh_article',
                                'all_128_observed', 'no_regression_vs_5cd', 'no_regression_vs_reference', 'identity_unchanged')},
                           evidence=[dict(path=str(self.out / 'fixture-evidence'), sha256=seal.sha(self.out / 'fixture-evidence'))])
            save(self.out / (name + '.json'), receipt)
            if name == 'acceptance' and self.omit_boat:
                receipt['checks'].pop('boat_five_touch_lap')
                save(self.out / (name + '.json'), receipt)
            if name == 'toutiao_slot':
                receipt.update(boot_id=self.slot_boot or env['DEMO_SEAL_BOOT_ID'], enabled=self.slot_enabled)
                save(self.out / (name + '.json'), receipt)
            if name == 'regression_review':
                receipt['comparison_sha256'] = seal.sha(self.out / 'regression/comparison.json')
                receipt['baseline_serial'] = seal.BASELINE_SERIAL if env['DEMO_SEAL_REFERENCE'] == '5cd' else seal.SERIAL
                receipt['reference_kind'] = env['DEMO_SEAL_REFERENCE']
                receipt['signoff_sha256'] = env['DEMO_SEAL_REFERENCE_SIGNOFF_SHA']
                save(self.out / (name + '.json'), receipt)
            if name == 'seal_snapshot':
                save(self.out / 'seal-snapshot.json', dict(serial=seal.SERIAL, boot_before=BOOTS[2], boot_after=BOOTS[2]))
            return 0, ''
        if name.startswith('snapshot-') and name != 'snapshot-diff':
            phase = name.removeprefix('snapshot-')
            save(self.out / phase / 'snapshot.json', dict(serial=seal.SERIAL, complete=True,
                 boot_stable=True, boot_id=BOOTS[1 if phase == 'pre' else 2]))
        if name == 'reboot-sim-advisory':
            save(self.out / 'prediction/prediction.json', dict(status='UNKNOWN' if self.advisory_exit else 'PASS'))
            return self.advisory_exit, ''
        if name == 'post-parent':
            return 0, 'PID PPID UID NAME\n' + self.parent + '\n'
        if name == 'post-socket':
            return 0, self.socket
        if name in ('post-dmesg', 'post-apps-dmesg'):
            return 0, 'invalid:appspawn-x' if self.invalid else 'fixture clean log'
        if name.startswith('regress-vs-'):
            rows = [dict(key='key-' + str(number), category='changed',
                    signature=dict(package='fixture.app', apk_sha256='b' * 64), reason=['image_sha256']) for number in range(128)]
            if self.plan['reference']['kind'] == '61b-t3':
                index = seal.read(self.plan['reference']['record_index']['path'])['records']
                for row in rows:
                    row['baseline_record'] = index[row['key']]['record']['path']
            save(self.out / 'regression/comparison.json', dict(keys=rows,
                    signoff_sha256=self.plan['reference']['signoff']['sha256'],
                    extra_keys=[], summary=dict(missing=0, changed=128, same=0)))
        if name == 'build-seal':
            save(self.out / 'seal.json', dict(seal_stage=self.seal_stage or self.plan['mode']))
        return 0, ''


class OrchestrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name)
        self.plan = copy.deepcopy(seal.read(HERE / 'plan-template.json'))
        self.plan['mode'] = 'v2'
        self.plan['boot_timeout_seconds'] = 1
        expected = {'/system/android/lib64/fixture-' + str(number) + '.so': 'b' * 64 for number in range(246)}
        expected.update({'/system/fixture-' + str(number): 'c' * 64 for number in range(73)})
        save(self.out / 'baseline.json', dict(expected=expected))
        save(self.out / 'table.json', dict(recover_layers=[dict(target='/system/android')]))
        save(self.out / 'manifest.json', dict(apps=[dict(key='key-' + str(number), install=True) for number in range(128)]))
        for key, filename in [('baseline_319', 'baseline.json'), ('recover_table', 'table.json'), ('manifest', 'manifest.json')]:
            self.plan['inputs'][key] = dict(path=str(self.out / filename), sha256=seal.sha(self.out / filename))
        self.plan['installer']['sha256'] = 'c' * 64
        self.plan['reference'] = dict(kind='5cd', signoff=dict(path='<fixture>', sha256='d' * 64), baseline_t3=str(self.out))
        self.plan['providers'] = {name: dict(argv=['fixture-provider', name]) for name in seal.PROVIDERS}
        (self.out / 'fixture-evidence').write_text('MOCK evidence; not UI acceptance')
        self.transport = FixtureTransport(self.out, self.plan)
        self.workflow = seal.Workflow(self.plan, self.out, self.transport, plan_sha='a' * 64,
                                      sleep=lambda seconds: None, mode='v2')

    def run_workflow(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.workflow.run()

    def bound_fixture(self, mode='v2'):
        plan = copy.deepcopy(self.plan)
        stub = self.out / 'fixture-provider.py'
        stub.write_text('raise SystemExit("fixture-only: never dispatch")\n')
        program = dict(path=str(stub), sha256=seal.sha(stub))
        plan.update(mode=mode, execution_enabled=True, pending=[], driver_sha256=seal.sha(SPEC.origin),
                    baseline_5cd_t3=str(self.out))
        plan['tools'] = {name: copy.deepcopy(program) for name in seal.TOOLS}
        plan['toutiao_slot'] = dict(placement=copy.deepcopy(program))
        for name in seal.INPUTS:
            if name not in ('baseline_319', 'recover_table', 'manifest'):
                source = self.out / (name + '-fixture.json')
                save(source, {})
                plan['inputs'][name] = dict(path=str(source), sha256=seal.sha(source))

        def input_json(name, value):
            source = Path(plan['inputs'][name]['path'])
            save(source, value)
            plan['inputs'][name]['sha256'] = seal.sha(source)

        input_json('recover_table', dict(recover_layers=[dict(target='/system/android')] +
                     [dict(target='/system/target-' + str(number)) for number in range(55)]))
        input_json('overlays', dict(seal_stage=mode, items=[dict(id='toutiao-route-b', state='active'),
                    dict(id='boatattack', state='active' if mode == 'v2' else 'absent', files=[],
                         reason='Boat not part of v1')]))
        input_json('signoff_5cd', dict(board=seal.BASELINE_SERIAL,
                     verdicts={'key-' + str(number): dict(verdict='lit', batch='fixture') for number in range(128)}))
        plan['reference'] = dict(kind='5cd', signoff=plan['inputs']['signoff_5cd'], baseline_t3=str(self.out))
        input_json('regression_admission', dict(approved_by='outer(claude)', overlay_aware=True,
                    post_reboot_sha256=program['sha256'], overlays_sha256=plan['inputs']['overlays']['sha256']))
        plan['installer']['source'] = copy.deepcopy(program)
        plan['installer']['sha256'] = program['sha256']
        guard = self.out / 'guard.json'
        save(guard, dict(approved_by='outer(claude)', live_bind_fail_closed=True, bare_boot_supported=True,
                         installer_sha256=program['sha256']))
        plan['installer']['guard_approval'] = dict(path=str(guard), sha256=seal.sha(guard))
        plan['providers'] = {name: dict(argv=['python3', str(stub)], pins=[copy.deepcopy(program)])
                             for name in seal.PROVIDERS}
        authorization = self.out / 'authorization.json'
        save(authorization, dict(approved_by='outer(claude)', approved_at='fixture-only', serial=seal.SERIAL,
                                plan_sha256='a' * 64, execution_authorized=True))
        return plan, authorization

    def test_complete_fixture_binding_validates_without_dispatch(self):
        plan, authorization = self.bound_fixture()
        with patch.object(seal.subprocess, 'run', side_effect=AssertionError('transport forbidden')):
            seal.validate(plan, authorization, 'a' * 64, mode='v2')

    def test_guard_not_bare_ready_refuses_before_dispatch(self):
        plan, authorization = self.bound_fixture()
        guard = Path(plan['installer']['guard_approval']['path'])
        value = seal.read(guard)
        value['bare_boot_supported'] = False
        save(guard, value)
        plan['installer']['guard_approval']['sha256'] = seal.sha(guard)
        with self.assertRaisesRegex(ValueError, 'bare-boot installer approval pending'):
            seal.validate(plan, authorization, 'a' * 64, mode='v2')

    def test_u13_only_regression_admission_refuses(self):
        plan, authorization = self.bound_fixture()
        source = Path(plan['inputs']['regression_admission']['path'])
        value = seal.read(source)
        value['overlay_aware'] = False
        save(source, value)
        plan['inputs']['regression_admission']['sha256'] = seal.sha(source)
        with self.assertRaisesRegex(ValueError, 'effective identity runner admission pending'):
            seal.validate(plan, authorization, 'a' * 64, mode='v2')

    def test_61b_reference_cannot_masquerade_as_5cd(self):
        plan, authorization = self.bound_fixture()
        source = Path(plan['inputs']['signoff_5cd']['path'])
        value = seal.read(source)
        value['board'] = seal.SERIAL
        save(source, value)
        plan['inputs']['signoff_5cd']['sha256'] = seal.sha(source)
        with self.assertRaisesRegex(ValueError, 'signed 5cd baseline required'):
            seal.validate(plan, authorization, 'a' * 64, mode='v2')

    def test_v1_binding_needs_only_toutiao_active_no_v2_admission(self):
        plan, authorization = self.bound_fixture('v1')
        plan['inputs']['regression_admission'] = dict(path='<v2-only-unbound>', sha256=None)
        with patch.object(seal.subprocess, 'run', side_effect=AssertionError('transport forbidden')):
            seal.validate(plan, authorization, 'a' * 64)

    def test_mode_cannot_differ_from_authorized_plan(self):
        plan, authorization = self.bound_fixture('v1')
        with self.assertRaisesRegex(ValueError, 'mode differs'):
            seal.validate(plan, authorization, 'a' * 64, mode='v2')

    def test_boat_state_must_match_both_modes(self):
        for mode in ('v1', 'v2'):
            with self.subTest(mode=mode):
                plan, authorization = self.bound_fixture(mode)
                source = Path(plan['inputs']['overlays']['path'])
                value = seal.read(source)
                value['items'][1]['state'] = 'active' if mode == 'v1' else 'absent'
                save(source, value)
                plan['inputs']['overlays']['sha256'] = seal.sha(source)
                with self.assertRaisesRegex(ValueError, 'Boat layer disagrees'):
                    seal.validate(plan, authorization, 'a' * 64, mode=mode)

    def test_v1_workflow_excludes_boat_and_emits_v1(self):
        self.plan['mode'] = 'v1'
        self.workflow.mode = 'v1'
        self.transport.omit_boat = True
        self.run_workflow()
        installer = next(argv[-1] for name, argv, env in self.transport.calls if name == 'installer')
        self.assertIn('WITH_BOAT=0', installer)
        self.assertEqual(seal.read(self.out / 'seal.json')['seal_stage'], 'v1')
        self.assertNotIn('boat_five_touch_lap', seal.read(self.out / 'acceptance.json')['checks'])

    def test_v2_workflow_requires_boat_and_emits_v2(self):
        self.run_workflow()
        self.assertEqual(seal.read(self.out / 'seal.json')['seal_stage'], 'v2')
        self.transport.omit_boat = True
        with self.assertRaisesRegex(ValueError, 'acceptance: missing/failed criterion'):
            self.run_workflow()

    def test_build_seal_wrong_mode_refuses(self):
        self.transport.seal_stage = 'v1'
        with self.assertRaisesRegex(ValueError, 'compiled seal mode mismatch'):
            self.run_workflow()

    def test_toutiao_disabled_or_wrong_bare_boot_never_enables_u13(self):
        for wrong in ('disabled', 'boot'):
            with self.subTest(wrong=wrong):
                self.transport.slot_enabled = wrong != 'disabled'
                self.transport.slot_boot = BOOTS[0] if wrong == 'boot' else None
                self.workflow.events = []
                with self.assertRaisesRegex(ValueError, 'not verified/enabled on bare boot'):
                    self.run_workflow()
                self.assertNotIn('enable', self.workflow.events)

    def test_exact_order_and_two_target_boots(self):
        self.run_workflow()
        ordered = ['lock_check', 'pre-319', 'disable', 'bare-reboot', 'wait-bare-boot',
                   'no-live-recover-bind-self', 'bare-seq1-inventory', 'bare-seq1-sha',
                   'bare-physical-inventory', 'installer', 'toutiao_slot', 'enable', 'snapshot-pre',
                   'sepolicy-gate', 'reboot-sim-advisory', 'autonomous-reboot', 'wait-autonomous-boot',
                   'acceptance', 'post-parent', 'snapshot-post', 'snapshot-diff', 'prepare-128',
                   'run-128', 'regress-vs-5cd', 'regression_review', 'seal_snapshot', 'build-seal']
        events = self.workflow.events
        self.assertEqual([events.index(name) for name in ordered], sorted(events.index(name) for name in ordered))
        reboots = [argv for name, argv, env in self.transport.calls if name in ('bare-reboot', 'autonomous-reboot')]
        self.assertEqual(reboots, [[self.plan['hdc'], '-t', seal.SERIAL, 'target', 'boot']] * 2)
        installer = next(argv for name, argv, env in self.transport.calls if name == 'installer')[-1]
        self.assertIn('WITH_BOAT=1', installer)
        self.assertIn(seal.SERIAL, next(argv for name, argv, env in self.transport.calls if name == 'run-128'))
        self.assertEqual(self.workflow.boot_id, BOOTS[2])

    def test_seq1_missing_or_extra_member_stops_before_installer(self):
        for problem in ('missing', 'extra'):
            with self.subTest(problem=problem):
                self.transport.archive_missing = problem == 'missing'
                self.transport.archive_extra = problem == 'extra'
                self.workflow.events = []
                with self.assertRaisesRegex(ValueError, 'BARE_BASE_REFUSE seq1 membership'):
                    self.run_workflow()
                self.assertNotIn('installer', self.workflow.events)
                self.assertNotIn('toutiao_slot', self.workflow.events)

    def test_seq1_same_count_wrong_sha_stops_before_installer(self):
        self.transport.archive_sha_drift = True
        with self.assertRaisesRegex(ValueError, 'BARE_BASE_REFUSE seq1 SHA mismatch'):
            self.run_workflow()
        self.assertNotIn('installer', self.workflow.events)
        self.assertNotIn('toutiao_slot', self.workflow.events)

    def test_nonempty_physical_stops_before_installer(self):
        self.transport.physical_files = ['/system/android/lib64/leftover.so']
        with self.assertRaisesRegex(ValueError, 'BARE_BASE_REFUSE physical /system/android not empty'):
            self.run_workflow()
        self.assertNotIn('installer', self.workflow.events)
        self.assertNotIn('toutiao_slot', self.workflow.events)

    def test_bare_inventory_command_failure_is_not_zero_files(self):
        for step in ('bare-seq1-inventory', 'bare-seq1-sha', 'bare-physical-inventory'):
            with self.subTest(step=step):
                self.transport.fail = step
                self.workflow.events = []
                with self.assertRaisesRegex(ValueError, 'exit=7'):
                    self.run_workflow()
                self.assertNotIn('installer', self.workflow.events)

    def test_archive_count_is_signed_subset_not_a_hardcoded_246(self):
        expected = seal.read(self.out / 'baseline.json')['expected']
        digest = expected.pop('/system/android/lib64/fixture-245.so')
        expected['/system/fixture-extra'] = digest
        save(self.out / 'baseline.json', dict(expected=expected))
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.workflow.run()
        self.assertIn('seq1_files=245 sha_diff={} physical_files=0 decision=REUSE', output.getvalue())

    def test_empty_signed_subset_refuses_before_dispatch(self):
        with self.assertRaisesRegex(ValueError, 'signed /system/android baseline missing'):
            seal.archived_base({'/system/android-other/fixture.so': 'a' * 64})

    def test_main_stops_and_prints_recovery_on_bare_guard_failure(self):
        for problem in ('sha', 'physical'):
            with self.subTest(problem=problem):
                self.transport.archive_sha_drift = problem == 'sha'
                self.transport.physical_files = ['/system/android/fixture'] if problem == 'physical' else []
                plan, authorization = self.bound_fixture('v1')
                plan_path = self.out / ('plan-' + problem + '.json')
                save(plan_path, plan)
                new_out = self.out / ('execution-' + problem)

                def fixture_transport(out, timeout):
                    self.transport.out = Path(out)
                    self.transport.plan = plan
                    (Path(out) / 'fixture-evidence').write_text('MOCK evidence; no board access')
                    return self.transport

                with patch.object(seal, 'validate'), patch.object(seal, 'Transport', side_effect=fixture_transport):
                    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as error:
                        code = seal.main(['--plan', str(plan_path), '--execute', '--authorization', str(authorization),
                                          '--out', str(new_out)])
                self.assertEqual(code, 1)
                self.assertIn('SEAL-STOP: BARE_BASE_REFUSE', error.getvalue())
                self.assertIn('RECOVERY (not executed): fresh cx-t0 U13 61b native-ticket replay', error.getvalue())
                self.assertNotIn('installer', seal.read(new_out / 'steps.json'))

    def test_live_bind_in_either_view_refuses_installer(self):
        for view in ('self', '1'):
            with self.subTest(view=view):
                self.transport.live_view = view
                self.workflow.events = []
                with self.assertRaisesRegex(ValueError, 'LIVE_BIND_REFUSE'):
                    self.run_workflow()
                self.assertNotIn('installer', self.workflow.events)
                self.assertNotIn('toutiao_slot', self.workflow.events)

    def test_failed_step_never_runs_later_step(self):
        self.transport.fail = 'installer'
        with self.assertRaisesRegex(ValueError, 'exit=7'):
            self.run_workflow()
        self.assertNotIn('enable', self.workflow.events)

    def test_319_drift_stops_before_disable(self):
        self.transport.baseline_drift = True
        with self.assertRaisesRegex(ValueError, '319 baseline mismatch'):
            self.run_workflow()
        self.assertNotIn('disable', self.workflow.events)

    def test_staged_installer_drift_stops(self):
        self.transport.installer_drift = True
        with self.assertRaisesRegex(ValueError, 'staged installer drift'):
            self.run_workflow()
        self.assertNotIn('installer', self.workflow.events)

    def test_unchanged_boot_refuses(self):
        self.transport.same_boot = True
        with patch.object(seal.time, 'monotonic', side_effect=[0, 0, 2]):
            with self.assertRaisesRegex(ValueError, 'no changed, ready boot'):
                self.run_workflow()
        self.assertNotIn('installer', self.workflow.events)

    def test_second_boot_must_change_too(self):
        self.transport.second_same_boot = True
        with patch.object(seal.time, 'monotonic', side_effect=[0, 0, 0, 0, 2]):
            with self.assertRaisesRegex(ValueError, 'no changed, ready boot'):
                self.run_workflow()
        self.assertNotIn('acceptance', self.workflow.events)

    def test_unsigned_ui_receipt_is_not_success(self):
        self.transport.unsigned = True
        with self.assertRaisesRegex(ValueError, 'stale/unsigned/repaired'):
            self.run_workflow()
        self.assertNotIn('build-seal', self.workflow.events)

    def test_socket_0666_refuses(self):
        self.transport.socket = '666:0:6005:u:object_r:appspawn_socket:s0'
        with self.assertRaisesRegex(ValueError, 'socket identity'):
            self.run_workflow()
        self.assertNotIn('snapshot-post', self.workflow.events)

    def test_non_init_parent_refuses(self):
        self.transport.parent = '44 22 0 appspawn-x'
        with self.assertRaisesRegex(ValueError, 'parent/UID'):
            self.run_workflow()

    def test_invalid_init_refuses(self):
        self.transport.invalid = True
        with self.assertRaisesRegex(ValueError, 'INVALID'):
            self.run_workflow()

    def test_advisory_unknown_retained_not_claimed_pass(self):
        self.transport.advisory_exit = 1
        self.run_workflow()
        self.assertEqual(seal.read(self.out / 'prediction/prediction.json')['status'], 'UNKNOWN')

    def test_missing_simulator_inputs_stop(self):
        self.transport.advisory_exit = 2
        with self.assertRaisesRegex(ValueError, 'exit=2'):
            self.run_workflow()
        self.assertNotIn('autonomous-reboot', self.workflow.events)

    def test_default_preview_zero_transport_and_output_writes(self):
        out = self.out / 'not-created'
        with patch.object(seal.subprocess, 'run', side_effect=AssertionError('transport forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(seal.main(['--out', str(out)]), 0)
        self.assertFalse(out.exists())
        self.assertIn('WITH_BOAT=0', output.getvalue())
        self.assertNotIn('boat_five_touch_lap', output.getvalue())
        self.assertIn('319 signed paths', output.getvalue())

    def test_explicit_v2_preview_has_boat_zero_transport(self):
        out = self.out / 'not-created-v2'
        with patch.object(seal.subprocess, 'run', side_effect=AssertionError('transport forbidden')):
            with contextlib.redirect_stdout(io.StringIO()) as output:
                self.assertEqual(seal.main(['--mode', 'v2', '--out', str(out)]), 0)
        self.assertFalse(out.exists())
        self.assertIn('WITH_BOAT=1', output.getvalue())
        self.assertIn('boat_five_touch_lap', output.getvalue())

    def test_disabled_template_execute_refuses_before_transport(self):
        with patch.object(seal.subprocess, 'run', side_effect=AssertionError('transport forbidden')):
            with contextlib.redirect_stderr(io.StringIO()) as output:
                self.assertEqual(seal.main(['--execute', '--out', str(self.out / 'never'),
                                            '--authorization', str(self.out / 'unbound.json')]), 1)
        self.assertFalse((self.out / 'never').exists())
        self.assertIn('RECOVERY (not executed)', output.getvalue())

    def test_mountinfo_malformed_not_negative(self):
        for text in ('', 'malformed'):
            with self.assertRaises(ValueError):
                seal.live_binds(text, ['/system/android'])

    def test_component_boundary_and_escaped_mount(self):
        clean = '1 0 0:1 / / rw - ext4 /dev/root rw\n2 1 0:2 / /system/android-other rw - ext4 /dev/data rw\n'
        self.assertEqual(seal.live_binds(clean, ['/system/android']), [])
        bad = clean + '3 1 0:3 /src /system/android/lib64/has\\040space rw - ext4 /dev/data rw\n'
        self.assertEqual(len(seal.live_binds(bad, ['/system/android'])), 1)


if __name__ == '__main__':
    unittest.main()
