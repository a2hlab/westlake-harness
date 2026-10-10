from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board_state_snapshot as snapshot
import board_state_diff as diff


SERIAL = '61b0657200000000000000000324012c'
BOOT = '11111111-1111-1111-1111-111111111111'
SYSTEM = 'u:object_r:system_file:s0'
LIB = 'u:object_r:system_lib_file:s0'
CFG = '{"services":[{"name":"appspawn-x","path":["/system/bin/appspawn-x"],"secon":"u:r:appspawn:s0"}]}\n'
REPLAY = Path(__file__).resolve().parents[2] / 'benchmark/2026-10-10-board-state-tools/first-board-fix/evidence/61b-5cd-selected-fields.json'


def fixture():
    rows = [{'kind': 'directory', 'target': '/system/android'},
            {'kind': 'file', 'target': '/system/bin/appspawn-x'},
            {'kind': 'file', 'target': '/system/lib64/appspawn/libwestlake_android_child.z.so'},
            {'kind': 'file', 'target': '/system/lib64/libwestlake_thread_guard_registry.so'}]
    rows += [dict(kind='file', target='/system/etc/mock-layer-' + str(index) + '.json') for index in range(52)]
    return dict(mounts=rows)


class FakeTransport:
    def __init__(self):
        self.commands = []
        self.boot_reads = 0
        self.reboot = False
        self.fail = None
        self.mode = 'Enforcing'
        self.dynamic_pid = False
        self.labels = {'/system/android': SYSTEM,
                       '/system/android/lib64': LIB,
                       '/system/android/lib64/liboh_android_runtime.so': LIB,
                       '/system/lib64/seccomp': LIB,
                       '/system/lib64/seccomp/libapp_filter.z.so': LIB,
                       '/system/lib64/appspawn': LIB,
                       '/system/bin/appspawn-x': 'u:object_r:appspawn_exec:s0',
                       '/system/lib64/appspawn/libwestlake_android_child.z.so': LIB,
                       '/system/lib64/libwestlake_thread_guard_registry.so': LIB}
        self.labels['/system/etc/sandbox/appdata-sandbox.json'] = 'u:object_r:system_etc_file:s0'
        for index in range(52):
            self.labels['/system/etc/mock-layer-' + str(index) + '.json'] = 'u:object_r:system_etc_file:s0'
        for index in range(85):
            self.labels['/system/lib64/extra-' + str(index) + '.so'] = LIB

    def run(self, command):
        self.commands.append(command)
        for prohibited in ['chcon ', 'chmod ', 'setenforce ', 'begetctl ', 'reboot', 'mount -', 'rm ']:
            if prohibited in command:
                raise AssertionError('write command in snapshotter: ' + command)
        if self.fail and self.fail in command:
            return 7, b'partial original stdout\n', b'original read failure\n'
        if command == 'cat /proc/sys/kernel/random/boot_id':
            self.boot_reads += 1
            boot = '22222222-2222-2222-2222-222222222222' if self.reboot and self.boot_reads > 1 else BOOT
            text = boot + '\n'
        elif command == 'cat /proc/uptime':
            text = '100.00 200.00\n'
        elif command == 'getenforce':
            text = self.mode + '\n'
        elif command == 'cat /proc/mounts':
            text = '\n'.join('/dev/mock /system/lib64/extra-' + str(index) + '.so ext4 ro,relatime 0 0' for index in range(85)) + '\n'
        elif command == 'cat /proc/1/mountinfo':
            text = '42 1 1:1 / /system ro - ext4 /dev/mock ro\n'
        elif command.startswith('set -eu; test -'):
            match = re.search(r'test -(e|d) ([^;]+);', command)
            target = match.group(2)
            text = '\n'.join(label + ' ' + path for path, label in sorted(self.labels.items())
                             if path == target or (match.group(1) == 'd' and path.startswith(target + '/'))) + '\n'
        elif command.startswith('ls -Zd '):
            target = command[len('ls -Zd '):]
            text = self.labels[target] + ' ' + target + '\n'
        elif command == 'param ls':
            text = '[const.product.name] = mock\n[const.cust.follow_x_rules] = false\n'
        elif command.startswith('param get '):
            return 1, b'', b'parameter unset\n'
        elif 'find "$root" -type f -name "*.cfg"' in command:
            text = hashlib.sha256(CFG.encode()).hexdigest() + '  /system/etc/init/appspawn-x.cfg\n'
        elif command == 'cat /system/etc/init/appspawn-x.cfg':
            text = CFG
        elif command.startswith('for root in '):
            return 0, b'LAYER /system\nDIR_PROBE_RC 0\nFILE_PROBE_RC 0\nLAYER /chipset\nDIR_PROBE_RC 2\nFILE_PROBE_RC 2\n', b'No such file or directory\n'
        elif 'find /system/lib64/seccomp -type f' in command:
            text = 'b' * 64 + '  /system/lib64/seccomp/libapp_filter.z.so\n'
        elif 'find /system/etc /system/android/etc -type f' in command:
            text = 'c' * 64 + '  /system/etc/sandbox/appdata-sandbox.json\n'
        elif 'found=$(pidof ' in command:
            text = 'NO_PROCESS\n' if 'pidof appspawn-x)' not in command else ('33 44\n' if self.dynamic_pid else '33\n')
        elif command.startswith('readlink /proc/'):
            text = '/system/bin/appspawn-x\n'
        elif '/attr/current' in command:
            text = 'u:r:appspawn:s0\n'
        elif command.endswith('/mountinfo'):
            text = '99 1 1:1 / /system ro - ext4 /dev/mock ro\n'
        elif '/environ ' in command:
            text = 'LD_LIBRARY_PATH\nPATH\nSECRET_TOKEN\n'
        else:
            raise AssertionError('unexpected read: ' + command)
        return 0, text.encode(), b''


class BoardStateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.transport = FakeTransport()

    def capture(self, name='one'):
        return snapshot.capture(self.transport, SERIAL, self.root / name, fixture(), 'mock-only')

    def test_full_56_targets_and_more_than_80_mount_labels(self):
        report = self.capture()
        self.assertTrue(report['complete'], report['errors'])
        self.assertEqual(report['plan_target_count'], 56)
        self.assertEqual(len(report['bind_targets']), 85)
        self.assertIn('/system/lib64/extra-84.so', report['labels'])
        self.assertEqual(report['labels']['/system/lib64/seccomp/libapp_filter.z.so'], LIB)
        self.assertEqual(report['params']['const.product.name'], 'mock')
        self.assertEqual(report['sha']['/system/lib64/seccomp/libapp_filter.z.so'], 'b' * 64)
        self.assertEqual(report['pids']['appspawn']['pids'], [])
        self.assertEqual(report['pids']['appspawn-x']['procs'][0]['attr_current'], 'u:r:appspawn:s0')
        self.assertIn('SECRET_TOKEN', report['pids']['appspawn-x']['procs'][0]['environ_keys'])
        for item in report['items'].values():
            self.assertEqual(hashlib.sha256((self.root / 'one' / item['raw']).read_bytes()).hexdigest(), item['raw_sha256'])

    def test_transport_failure_preserves_raw_stderr_and_nonzero(self):
        self.transport.fail = 'cat /proc/1/mountinfo'
        report = self.capture()
        self.assertFalse(report['complete'])
        record = report['items']['init_mountinfo']
        self.assertEqual(record['rc'], 7)
        self.assertEqual((self.root / 'one' / record['raw']).read_bytes(), b'partial original stdout\n')
        self.assertEqual((self.root / 'one' / record['stderr_raw']).read_bytes(), b'original read failure\n')

    def test_boot_change_and_missing_plan_have_distinct_grades(self):
        self.transport.reboot = True
        changed = self.capture()
        self.assertFalse(changed['boot_stable'])
        self.assertFalse(changed['collection_complete'])
        self.assertEqual(changed['capture_status'], 'INCOMPLETE_READS')
        self.transport = FakeTransport()
        report = snapshot.capture(self.transport, SERIAL, self.root / 'two', None)
        self.assertFalse(report['complete'])
        self.assertTrue(report['collection_complete'])
        self.assertEqual(report['capture_status'], 'PARTIAL_COVERAGE')
        self.assertFalse(report['coverage']['deployment_targets_complete'])
        self.assertFalse(report['errors'])
        self.assertTrue(any(row['item'] == 'deployment-plan' for row in report['coverage_warnings']))

    def test_cfg_read_race_and_malformed_label_cannot_be_complete(self):
        original = self.transport.run

        def altered(command):
            if command == 'cat /system/etc/init/appspawn-x.cfg':
                self.transport.commands.append(command)
                return 0, b'{"changed":true}\n', b''
            return original(command)

        self.transport.run = altered
        report = self.capture('one')
        self.assertFalse(report['complete'])
        self.assertTrue(any('inventory SHA' in row['reason'] for row in report['errors']))
        self.transport = FakeTransport()
        self.transport.labels['/system/bin/appspawn-x'] = '?'
        report = self.capture('two')
        self.assertFalse(report['complete'])

    def test_invalid_serial_never_calls_hdc(self):
        with patch.object(snapshot.subprocess, 'run') as run:
            with self.assertRaises(ValueError):
                snapshot.HdcTransport('mock-hdc', '61b')
            run.assert_not_called()

    def test_timeout_and_oserror_have_explicit_raw_codes(self):
        transport = snapshot.HdcTransport('mock-hdc', SERIAL)
        with patch.object(snapshot.subprocess, 'run', side_effect=subprocess.TimeoutExpired('mock', 120, output=b'partial')):
            self.assertEqual(transport.run('getenforce')[:2], (124, b'partial'))
        with patch.object(snapshot.subprocess, 'run', side_effect=FileNotFoundError('mock-only')):
            self.assertEqual(transport.run('getenforce')[0], 125)

    def test_offline_diff_identical_and_semantic_differences(self):
        self.capture('one')
        self.transport = FakeTransport()
        self.capture('two')
        report = diff.compare(self.root / 'one', self.root / 'two')
        self.assertTrue(report['comparable'])
        self.assertFalse(report['diffs']['labels'])
        self.assertFalse(report['diffs']['raw'])
        self.transport = FakeTransport()
        self.transport.mode = 'Permissive'
        self.transport.labels['/system/android/lib64/liboh_android_runtime.so'] = 'u:object_r:data_local_tmp:s0'
        self.capture('three')
        report = diff.compare(self.root / 'one', self.root / 'three')
        self.assertIn('selinux_enforce', report['diffs']['scalars'])
        self.assertIn('/system/android/lib64/liboh_android_runtime.so', report['diffs']['labels'])
        self.assertTrue(all(not row['causal_proof'] for row in report['seccomp_relevant_observations']))

    def test_deleted_modified_and_symlink_raw_are_not_equality(self):
        self.capture('one')
        self.transport = FakeTransport()
        self.capture('two')
        target = self.root / 'two/raw/init_mountinfo.txt'
        original = target.read_bytes()
        for mode in ['delete', 'modify', 'symlink']:
            with self.subTest(mode=mode):
                if target.exists() or target.is_symlink():
                    target.unlink()
                if mode == 'modify':
                    target.write_bytes(b'drift')
                elif mode == 'symlink':
                    target.symlink_to(self.root / 'one/raw/init_mountinfo.txt')
                report = diff.compare(self.root / 'one', self.root / 'two')
                self.assertFalse(report['comparable'])
                self.assertTrue(report['incomplete']['subject'])
                if target.is_symlink():
                    target.unlink()
                target.write_bytes(original)

    def test_multiple_same_exe_processes_are_not_collapsed(self):
        self.capture('one')
        self.transport = FakeTransport()
        self.transport.dynamic_pid = True
        report = self.capture('two')
        self.assertEqual(len(report['pids']['appspawn-x']['procs']), 2)
        comparison = diff.compare(self.root / 'one', self.root / 'two')
        self.assertIn('appspawn-x', comparison['diffs']['pids'])

    def test_cli_mock_transport_and_diff_preserve_no_board_contract(self):
        plan = self.root / 'plan.json'
        plan.write_text(json.dumps(fixture()))
        for name in ['one', 'two']:
            with patch.object(snapshot, 'HdcTransport', return_value=FakeTransport()), redirect_stdout(io.StringIO()):
                self.assertEqual(snapshot.main([SERIAL, '--plan', str(plan), '--hdc', 'mock-hdc', '--out', str(self.root / name)]), 0)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(diff.main([str(self.root / 'one'), str(self.root / 'two'), '--json', str(self.root / 'diff.json')]), 0)
        self.assertTrue(json.loads((self.root / 'diff.json').read_text())['readonly'])

    def test_each_board_uses_a_distinct_output_directory_without_overwrite(self):
        self.capture('captures/61b-pre')
        original = (self.root / 'captures/61b-pre/snapshot.json').read_bytes()
        self.transport = FakeTransport()
        snapshot.capture(self.transport, '5cd1e3dd00000000000000000923012c', self.root / 'captures/5cd-pre', fixture())
        with self.assertRaises(FileExistsError):
            self.capture('captures/61b-pre')
        self.assertEqual((self.root / 'captures/61b-pre/snapshot.json').read_bytes(), original)
        self.assertTrue((self.root / 'captures/5cd-pre/raw').is_dir())

    def test_missing_plan_marks_pathsets_not_comparable_keeps_observed(self):
        # No plan on either side -> labels/sha/bind_targets are PATH-SET scope and must be NOT-COMPARABLE
        # (this is the 5ea false "27 route-a missing" class); observed non-path-set fields still diff.
        for name in ['one', 'two']:
            snapshot.capture(FakeTransport(), SERIAL, self.root / name, None)
        report = diff.compare(self.root / 'one', self.root / 'two')
        self.assertFalse(report['plan_comparable'])
        self.assertFalse(report['comparable'])
        for section in ('labels', 'sha', 'bind_targets'):
            self.assertEqual(report['diffs'][section].get('status'), 'NOT-COMPARABLE', section)
        self.assertNotIn('status', report['diffs']['scalars'])   # observed fields still diffed
        self.assertEqual(report['comparison_scope'], 'observed-fields-only')
        (self.root / 'two/raw/param_ls.txt').write_bytes(b'drift')
        self.assertFalse(diff.compare(self.root / 'one', self.root / 'two')['comparable'])

    def test_differing_plan_sha_is_not_comparable_exit3(self):
        # Matching-plan captures are comparable; a differing plan_sha256 must flip path sets to NOT-COMPARABLE.
        plan = self.root / 'plan.json'
        plan.write_text(json.dumps(fixture()))
        for name in ['one', 'two']:
            with patch.object(snapshot, 'HdcTransport', return_value=FakeTransport()), redirect_stdout(io.StringIO()):
                snapshot.main([SERIAL, '--plan', str(plan), '--hdc', 'mock-hdc', '--out', str(self.root / name)])
        # tamper the subject's recorded plan_sha256 so the two no longer share a plan scope
        sub = self.root / 'two/snapshot.json'
        data = json.loads(sub.read_text()); data['plan_sha256'] = 'deadbeef'; sub.write_text(json.dumps(data))
        with redirect_stdout(io.StringIO()):
            rc = diff.main([str(self.root / 'one'), str(self.root / 'two'), '--json', str(self.root / 'd.json')])
        self.assertEqual(rc, 3)
        report = json.loads((self.root / 'd.json').read_text())
        self.assertFalse(report['plan_comparable'])
        for section in ('labels', 'sha', 'bind_targets'):
            self.assertEqual(report['diffs'][section].get('status'), 'NOT-COMPARABLE', section)

    def test_legacy_plan_only_incomplete_is_graded_but_not_other_errors(self):
        for name in ['one', 'two']:
            self.transport = FakeTransport()
            self.capture(name)
            target = self.root / name / 'snapshot.json'
            report = json.loads(target.read_text())
            for key in ['collection_complete', 'capture_status', 'coverage', 'coverage_warnings']:
                report.pop(key)
            report['complete'] = False
            report['errors'] = [dict(item='deployment-plan', reason='56-layer target plan not supplied; coverage incomplete')]
            target.write_text(json.dumps(report))
        report = diff.compare(self.root / 'one', self.root / 'two')
        self.assertTrue(report['comparable'])
        self.assertFalse(report['coverage_complete'])
        target = self.root / 'two/snapshot.json'
        broken = json.loads(target.read_text())
        broken['errors'].append(dict(item='init_cfgs', reason='read failure'))
        target.write_text(json.dumps(broken))
        self.assertFalse(diff.compare(self.root / 'one', self.root / 'two')['comparable'])

    def test_discovered_sandbox_json_label_is_captured_without_a_plan(self):
        self.transport.labels['/system/etc/sandbox/appdata-sandbox.json'] = 'u:object_r:data_local_tmp:s0'
        report = snapshot.capture(self.transport, SERIAL, self.root / 'one', None)
        self.assertEqual(report['labels']['/system/etc/sandbox/appdata-sandbox.json'], 'u:object_r:data_local_tmp:s0')
        self.assertIn('sandbox_label_000', report['items'])

    def test_prefixed_cust_parameters_and_system_data_labels_are_hints(self):
        first = dict(labels={'/system/lib64/a.so': 'u:object_r:data_file:s0'}, params={'const.cust.new_option': '1'})
        second = dict(labels={'/system/lib64/a.so': LIB}, params={'const.cust.new_option': '2'})
        changes = {key: diff.dictionary_diff(first.get(key, {}), second.get(key, {})) for key in ['scalars', 'labels', 'params', 'sha', 'raw']}
        changes['raw']['param_const_cust_new_option'] = dict(reference='failed query', subject='different failure')
        hints, counts = diff.seccomp_observations(first, second, changes)
        self.assertTrue(any(row['key'] == 'const.cust.new_option' for row in hints))
        self.assertTrue(any(row['key'] == 'param_const_cust_new_option' for row in hints))
        self.assertEqual(counts['reference']['data_file'], 1)
        self.assertEqual(counts['subject']['data_file'], 0)
        self.assertTrue(all(row['causal_proof'] is False for row in hints))

    def test_real_61b_5cd_selected_fields_replay_flags_the_missed_sandbox(self):
        replay = json.loads(REPLAY.read_text())
        first, second = replay['reference'], replay['subject']
        changes = {key: diff.dictionary_diff(first.get(key, {}), second.get(key, {})) for key in ['scalars', 'labels', 'params', 'sha', 'raw']}
        hints, counts = diff.seccomp_observations(first, second, changes)
        sandbox = next(row for row in hints if row['key'] == '/system/etc/sandbox/appdata-sandbox.json' and row['section'] == 'labels')
        self.assertEqual(sandbox['delta']['reference'], 'u:object_r:data_local_tmp:s0')
        self.assertEqual(sandbox['delta']['subject'], 'u:object_r:system_etc_file:s0')
        self.assertEqual(counts['reference']['data_local_tmp'], 24)
        self.assertEqual(counts['subject']['data_local_tmp'], 0)
        self.assertEqual(changes['sha'], {})
        self.assertEqual(changes['params'], {})
        self.assertTrue(all(row['causal_proof'] is False for row in hints))


if __name__ == '__main__':
    unittest.main()
