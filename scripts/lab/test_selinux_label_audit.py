import copy
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import deploy_generation
import selinux_label_audit as audit


SERIAL = '5cd1e3dd00000000000000000923012c'
BOOT = '11111111-1111-1111-1111-111111111111'
HOST = '/system/bin/appspawn-x'
CHILD = '/system/lib64/appspawn/libwestlake_android_child.z.so'
GUARD = '/system/lib64/libwestlake_thread_guard_registry.so'
LIBRARY = '/system/android/lib64/liboh_android_runtime.so'
SYSTEM = 'u:object_r:system_file:s0'
LIB = 'u:object_r:system_lib_file:s0'
EXEC = 'u:object_r:appspawn_exec:s0'
ROUTE = '/system/lib64/westlake/route-a/' + 'a' * 64


def fixture():
    plan = {'mounts': [
        {'target': '/system/android', 'kind': 'directory'},
        {'target': HOST, 'kind': 'file'},
        {'target': CHILD, 'kind': 'file'},
        {'target': GUARD, 'kind': 'file'},
        {'target': ROUTE, 'kind': 'directory'},
        {'target': '/system/etc/sandbox/appdata-sandbox.json', 'kind': 'file'},
        {'target': '/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libmain.so', 'kind': 'file'}
    ]}
    labels = {
        '/system/android': SYSTEM,
        '/system/android/lib64': LIB,
        LIBRARY: LIB,
        '/system/android/lib64/liblzma.so': LIB,
        '/system/android/framework': SYSTEM,
        '/system/android/framework/framework.jar': SYSTEM,
        '/system/android/framework/arm64': SYSTEM,
        '/system/android/framework/arm64/boot.art': LIB,
        '/system/android/framework/arm64/boot.oat': LIB,
        '/system/android/framework/arm64/boot.vdex': LIB,
        '/system/android/etc': SYSTEM,
        '/system/android/etc/fonts.xml': 'u:object_r:system_fonts_file:s0',
        HOST: EXEC, CHILD: LIB, GUARD: LIB,
        ROUTE: LIB, ROUTE + '/libart.so': LIB,
        '/system/etc/sandbox/appdata-sandbox.json': 'u:object_r:system_etc_file:s0',
        '/data/app/el1/bundle/public/com.a2hlab.bridge.zigzag/android/lib/arm64-v8a/libmain.so': 'u:object_r:data_app_el1_file:s0'
    }
    return plan, labels


class FakeShell:
    def __init__(self, labels):
        self.labels = labels
        self.commands = []
        self.fail_chcon = False
        self.ignore_chcon = False

    def __call__(self, command):
        self.commands.append(command)
        if command == 'cat /proc/sys/kernel/random/boot_id':
            return BOOT
        if command.startswith('set -eu; test -'):
            match = re.search(r'test -(e|d) ([^;]+);', command)
            target = shlex.split(match.group(2))[0]
            if target not in self.labels:
                raise RuntimeError('missing mocked target')
            paths = [path for path in sorted(self.labels) if path == target or
                     (match.group(1) == 'd' and path.startswith(target + '/'))]
            return '\n'.join(self.labels[path] + ' ' + path for path in paths)
        if command.startswith('chcon -h '):
            if self.fail_chcon:
                raise RuntimeError('mock chcon permission denied')
            if not self.ignore_chcon:
                fields = shlex.split(command)
                for path in fields[3:]:
                    self.labels[path] = fields[2]
            return ''
        if command.startswith('sh -c '):
            result, commands = run_shell_fixture(command, self.labels, self.fail_chcon, self.ignore_chcon)
            self.commands.extend(commands)
            if result.returncode:
                raise RuntimeError(result.stdout + result.stderr)
            return result.stdout
        if command.startswith('stat -c '):
            return '660:0:6005:u:object_r:appspawn_socket:s0'
        if command.startswith('begetctl start_service ') or command.startswith('chown 0:6005 '):
            return ''
        raise AssertionError('unexpected command: ' + command)


def run_shell_fixture(command, labels, fail_chcon=False, ignore_chcon=False):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = root / 'labels.json'
        state.write_text(json.dumps(labels))
        log = root / 'commands.jsonl'
        shim = root / 'shim'
        shim.write_text('''#!''' + sys.executable + '''
import json, os
from pathlib import Path
import sys
name=Path(sys.argv[0]).name
args=sys.argv[1:]
state=Path(os.environ['MOCK_LABEL_STATE'])
labels=json.loads(state.read_text())
with open(os.environ['MOCK_LABEL_LOG'], 'a') as stream:
 stream.write(json.dumps([name, *args])+'\\n')
if name=='toybox':
 if args[0]!='test': sys.exit(99)
 path=args[-1]
 if args[1]=='-e': sys.exit(0 if path in labels else 1)
 if args[1]=='-d': sys.exit(0 if path in labels and any(key.startswith(path+'/') for key in labels) else 1)
 sys.exit(99)
elif name=='ls':
 path=args[-1]
 if path not in labels: sys.exit(1)
 print(labels[path]+' '+path)
elif name=='find':
 for path in sorted(labels):
  if path==args[0] or path.startswith(args[0]+'/'): print(path)
elif name=='chcon':
 if os.environ['MOCK_FAIL_CHCON']=='1': sys.exit(1)
 if os.environ['MOCK_IGNORE_CHCON']!='1':
  labels[args[-1]]=args[-2]
  state.write_text(json.dumps(labels))
else: sys.exit(99)
''')
        shim.chmod(0o755)
        for name in ['toybox', 'ls', 'find', 'chcon']:
            (root / name).symlink_to(shim)
        environment = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                           MOCK_LABEL_STATE=str(state), MOCK_LABEL_LOG=str(log),
                           MOCK_FAIL_CHCON='1' if fail_chcon else '0', MOCK_IGNORE_CHCON='1' if ignore_chcon else '0')
        result = subprocess.run(['/bin/sh', '-c', command], capture_output=True, text=True, env=environment, timeout=30)
        labels.clear()
        labels.update(json.loads(state.read_text()))
        commands = [' '.join(json.loads(line)) for line in log.read_text().splitlines()] if log.exists() else []
        return result, commands


class LabelAuditTests(unittest.TestCase):
    def setUp(self):
        self.plan, self.labels = fixture()
        self.shell = FakeShell(self.labels)

    def test_canonical_independent_fixture_passes_readonly(self):
        result = audit.audit(self.shell, self.plan)
        self.assertEqual(result['status'], 'PASS')
        self.assertEqual(result['path_count'], len(self.labels))
        self.assertTrue(all(command.startswith('set -eu; test -') for command in self.shell.commands))

    def test_both_observed_label_walls_report_exact_path_context(self):
        self.labels[HOST] = SYSTEM
        self.labels[LIBRARY] = 'u:object_r:data_local_tmp:s0'
        self.labels[GUARD] = 'u:object_r:data_file:s0'
        result = audit.audit(self.shell, self.plan)
        self.assertEqual(result['status'], 'FAIL')
        rows = {row['path']: row for row in result['mismatches']}
        self.assertEqual(set(rows), {HOST, LIBRARY, GUARD})
        self.assertEqual(rows[HOST]['expected'], EXEC)
        self.assertEqual(rows[LIBRARY]['expected'], LIB)
        self.assertEqual(rows[LIBRARY]['actual'], 'u:object_r:data_local_tmp:s0')

    def test_missing_ambiguous_and_foreign_listing_refuses(self):
        row = self.plan['mounts'][0]
        for text in ['', '? /system/android', SYSTEM + ' /system/android\n' + SYSTEM + ' /system/android',
                     SYSTEM + ' /system/android\n' + SYSTEM + ' /system/elsewhere']:
            with self.subTest(text=text), self.assertRaises(ValueError):
                audit.parse_labels(text, row)

    def test_invalid_scope_kind_and_duplicate_targets_refuse(self):
        recipe = audit.load_recipe()
        invalid = [[], {'changes': self.plan['mounts']}, {'mounts': self.plan['mounts'][:3]},
                   {'mounts': self.plan['mounts'] + [self.plan['mounts'][0]]}]
        for target in ['/system/android/../bin/x', '/system/android;reboot', '/system//android']:
            plan = copy.deepcopy(self.plan)
            plan['mounts'][0]['target'] = target
            invalid.append(plan)
        plan = copy.deepcopy(self.plan)
        plan['mounts'][0]['kind'] = None
        invalid.append(plan)
        for plan in invalid:
            with self.subTest(plan=plan), self.assertRaises(ValueError):
                audit.plan_targets(plan, recipe)

    def test_manifest_and_recovery_table_shapes(self):
        recipe = audit.load_recipe()
        manifest = {'mounts': [], 'files': {}}
        for index, row in enumerate(self.plan['mounts']):
            source = f'payload/item-{index}'
            manifest['mounts'].append(dict(source=source, target=row['target']))
            manifest['files'][source + ('/member' if row['kind'] == 'directory' else '')] = '0' * 64
        self.assertEqual(audit.plan_targets(manifest, recipe), self.plan['mounts'])
        self.assertEqual(audit.plan_targets({'recover_layers': self.plan['mounts']}, recipe), self.plan['mounts'])

    def test_overlapping_reads_cannot_hide_label_change(self):
        self.plan['mounts'].append(dict(target=LIBRARY, kind='file'))

        def shell(command):
            if command == audit.read_command(self.plan['mounts'][-1]):
                return SYSTEM + ' ' + LIBRARY
            return self.shell(command)

        with self.assertRaisesRegex(ValueError, 'changed during'):
            audit.audit(shell, self.plan)

    def cli(self, root, extra=None):
        plan = root / 'plan.json'
        plan.write_text(json.dumps(self.plan))

        def run(argv, **kwargs):
            self.assertEqual(argv[:4], ['mock-hdc', '-t', SERIAL, 'shell'])
            stdout = self.shell(argv[4])
            return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr='')

        with patch.object(audit.subprocess, 'run', side_effect=extra or run), redirect_stdout(io.StringIO()) as output:
            code = audit.main([SERIAL, str(plan), '--hdc', 'mock-hdc', '--out', str(root / 'out')])
        return code, output.getvalue(), json.loads((root / 'out/audit.json').read_text())

    def test_cli_fail_prints_every_mismatch_without_writes(self):
        self.labels[HOST] = SYSTEM
        self.labels[LIBRARY] = 'u:object_r:data_local_tmp:s0'
        with tempfile.TemporaryDirectory() as directory:
            code, output, report = self.cli(Path(directory))
        self.assertEqual(code, 1)
        self.assertIn(HOST + ' expected=' + EXEC + ' actual=' + SYSTEM, output)
        self.assertIn(LIBRARY, output)
        self.assertTrue(report['readonly'])
        self.assertFalse(any('chcon' in command for command in self.shell.commands))

    def test_cli_boot_drift_and_stderr_refuse_complete_pass(self):
        for mode in ['boot', 'stderr']:
            calls = []

            def run(argv, **kwargs):
                calls.append(argv[4])
                stdout = self.shell(argv[4])
                if mode == 'boot' and len(calls) > 1 and argv[4] == 'cat /proc/sys/kernel/random/boot_id':
                    stdout = '22222222-2222-2222-2222-222222222222'
                return subprocess.CompletedProcess(argv, 0, stdout=stdout, stderr='read incomplete' if mode == 'stderr' else '')

            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as directory:
                code, output, report = self.cli(Path(directory), run)
                self.assertEqual(code, 1)
                self.assertFalse(report['complete'])

    def shell_command(self, mode, sources=False):
        rows = []
        for index, row in enumerate(self.plan['mounts']):
            rows.append(row['kind'] + '\t' + row['target'] + ('\t/data/label-fixture/item-' + str(index) if sources else ''))
        return 'sh -c ' + shlex.quote(audit.generate_shell(audit.load_recipe())) + ' -- ' + mode + " - <<'MOCK_LABEL_PLAN'\n" + '\n'.join(rows) + '\nMOCK_LABEL_PLAN'

    def test_generated_shell_and_python_audit_same_json_same_verdict(self):
        for bad in [False, True]:
            with self.subTest(bad=bad):
                if bad:
                    self.labels[HOST] = SYSTEM
                    self.labels[LIBRARY] = 'u:object_r:data_local_tmp:s0'
                python_result = audit.audit(self.shell, self.plan)
                shell_result, commands = run_shell_fixture(self.shell_command('audit'), self.labels)
                self.assertEqual(shell_result.returncode, 0 if python_result['status'] == 'PASS' else 1, shell_result.stdout + shell_result.stderr)
                self.assertFalse(any(command.startswith('chcon ') for command in commands))
                if bad:
                    self.assertIn(HOST + ' expected=' + EXEC + ' actual=' + SYSTEM, shell_result.stdout)
                    self.assertIn(LIBRARY + ' expected=' + LIB, shell_result.stdout)

    def test_generated_recover_source_then_target_matches_deploy_path(self):
        source_labels = {}
        for index, row in enumerate(self.plan['mounts']):
            for path in self.labels:
                if path == row['target'] or (row['kind'] == 'directory' and path.startswith(row['target'] + '/')):
                    source_labels['/data/label-fixture/item-' + str(index) + path[len(row['target']):]] = 'u:object_r:data_local_tmp:s0'
        result, commands = run_shell_fixture(self.shell_command('apply-source', True), source_labels)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        for index, row in enumerate(self.plan['mounts']):
            for path, expected in self.labels.items():
                if path == row['target'] or (row['kind'] == 'directory' and path.startswith(row['target'] + '/')):
                    self.assertEqual(source_labels['/data/label-fixture/item-' + str(index) + path[len(row['target']):]], expected)
        self.assertTrue(any(command.startswith('chcon ') for command in commands))

    def test_generated_shell_is_deterministic_and_context_mode_uses_recipe(self):
        recipe = audit.load_recipe()
        self.assertEqual(audit.generate_shell(recipe), audit.generate_shell(copy.deepcopy(recipe)))
        result, commands = run_shell_fixture('sh -c ' + shlex.quote(audit.generate_shell(recipe)) + ' -- context ' + shlex.quote(HOST), self.labels)
        self.assertEqual(result.stdout.strip(), EXEC)
        self.assertEqual(result.returncode, 0)
        self.assertEqual(commands, [])

    def test_released_shell_matches_single_recipe(self):
        self.assertEqual(Path(audit.__file__).with_name('selinux_label_recipe.sh').read_text(),
                         audit.generate_shell(audit.load_recipe()))

    def test_removed_seccomp_exception_uses_generic_library_rule(self):
        target = '/system/lib64/seccomp/libapp_filter.z.so'
        self.assertEqual(audit.expected_label(target, audit.load_recipe()), (LIB, 'native-library'))
        self.assertNotIn('seccomp-stock', [row['id'] for row in audit.load_recipe()['rules']])

    def test_stock_seccomp_directory_default_is_still_an_explicit_mismatch(self):
        root = '/system/lib64/seccomp'
        self.plan['mounts'].append(dict(target=root, kind='directory'))
        self.labels[root] = LIB
        self.labels[root + '/libapp_filter.z.so'] = LIB
        report = audit.audit(self.shell, self.plan)
        self.assertEqual(report['mismatches'], [dict(path=root, expected=SYSTEM, actual=LIB,
                                                   rule='system-default', passed=False)])


class DeploymentLabelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        plan, labels = fixture()
        labels[HOST] = SYSTEM
        labels[LIBRARY] = 'u:object_r:data_local_tmp:s0'
        self.shell = FakeShell(labels)
        self.deploy = deploy_generation.Deployment.__new__(deploy_generation.Deployment)
        self.deploy.a = SimpleNamespace(no_label_recipe=False)
        self.deploy.m = plan
        self.deploy.out = Path(self.temp.name)
        self.deploy.shell = self.shell
        self.deploy.ps = lambda: [dict(name='appspawn-x', uid=0, pid=123)]
        self.deploy.hashes = lambda paths: {path: '0' * 64 for path in paths}

    def start(self):
        with patch.object(deploy_generation.time, 'sleep'):
            return self.deploy.start('0' * 64)

    def test_default_gate_repairs_and_audits_before_start(self):
        self.assertEqual(self.start(), 123)
        commands = self.shell.commands
        index = commands.index('begetctl start_service appspawn-x')
        self.assertTrue(any(command.startswith('chcon -h ') for command in commands[:index]))
        self.assertEqual(self.shell.labels[HOST], EXEC)
        self.assertEqual(self.shell.labels[LIBRARY], LIB)
        report = next(self.deploy.out.glob('label-recipe-*/after.json'))
        self.assertEqual(json.loads(report.read_text())['status'], 'PASS')

    def test_failed_or_nonsticking_chcon_never_starts(self):
        for mode in ['failure', 'nonsticking']:
            with self.subTest(mode=mode):
                self.shell.fail_chcon = mode == 'failure'
                self.shell.ignore_chcon = mode == 'nonsticking'
                with self.assertRaises(RuntimeError):
                    self.start()
                self.assertNotIn('begetctl start_service appspawn-x', self.shell.commands)
        self.assertEqual(len(list(self.deploy.out.glob('label-recipe-*/failure.json'))), 2)

    def test_missing_file_blocks_start_before_relabel(self):
        del self.shell.labels[GUARD]
        with self.assertRaises(RuntimeError):
            self.start()
        self.assertFalse(any(command.startswith(('chcon', 'begetctl')) for command in self.shell.commands))

    def test_explicit_optout_only_skips_new_gate(self):
        self.deploy.a.no_label_recipe = True
        self.assertEqual(self.start(), 123)
        self.assertEqual(self.shell.labels[HOST], SYSTEM)
        self.assertFalse(any(command.startswith('set -eu; test -') for command in self.shell.commands))
        self.assertTrue(any(command.startswith('chown 0:6005 ') for command in self.shell.commands))

    def test_mac_dispatch_carries_explicit_optout(self):
        gate = SimpleNamespace(configure_experiment=lambda *args: None, check=lambda *args: {'binding': 'mock'})
        with patch.dict(sys.modules, deployment_native_gate=gate), patch.object(deploy_generation, 'load_package', return_value={'generation': 'a' * 64}), \
                patch.object(deploy_generation, 'check_frozen_package'), patch.object(deploy_generation.platform, 'system', return_value='Darwin'), \
                patch.object(deploy_generation.subprocess, 'call', return_value=0) as dispatch, self.assertRaises(SystemExit) as result:
            deploy_generation.main([SERIAL, '/tmp/mock-package', '--no-label-recipe'])
        self.assertEqual(result.exception.code, 0)
        self.assertIn('--no-label-recipe', shlex.split(dispatch.call_args.args[0][-1]))


if __name__ == '__main__':
    unittest.main()
