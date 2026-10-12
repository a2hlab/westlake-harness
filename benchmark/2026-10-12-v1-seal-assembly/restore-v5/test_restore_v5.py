#!/usr/bin/env python3
"""Minimal r3 delta audit of the already-compiled disabled v5 package.

No transaction, full-worker fake context, lock/owner fixture, HDC or network.
The only shell executions are an isolated success case and helper diagnostics.
Source checkpoint is commit 69e15c4ae058d1fe17ba5f4355883e460ac9859b.
"""
import ast
import copy
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
V4 = HERE.parent / 'restore-v4'
spec = importlib.util.spec_from_file_location('v5_delta_provider', HERE / 'toutiao_provider.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)
HELPER_SHA = '6bce7c3c8f84ad1047313c5dd76bcb084637d9095b9163dc710c88aaee12fe4c'
WORKER_SHA = '2d3ce1546c9df1e3a222e23f19c39f8f4aec82fb551d59f37dbe7fd343573717'
CHECKPOINT_SHA = '857e9704cf6ee3a98be3fa690fe6d9d830c32567275dea12f65f09120d5f229d'


class RestoreV5DeltaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binding = p.read(HERE / 'binding.5cd.r3.disabled.json')
        cls.oldbinding = p.read(V4 / 'binding.5cd.r2b.disabled.json')
        cls.package = HERE / 'package-r3-disabled'
        cls.payload = cls.package / 'payload'
        cls.plan = p.read(cls.package / 'plan.json')
        cls.manifest = p.read(cls.package / 'manifest.json')
        cls.source = p.resolve(cls.binding['guardian_update']['path'], HERE).parent
        cls.oldsource = p.resolve(cls.oldbinding['guardian_update']['path'], V4).parent

    def test_actual_package_source_pins_and_unchanged_core_bytes(self):
        self.assertEqual(self.binding['guardian_update']['sha256'], CHECKPOINT_SHA)
        self.assertEqual(p.digest(self.source / 'checkpoint-manifest.json'), CHECKPOINT_SHA)
        checkpoint = p.read(self.source / 'checkpoint-manifest.json')
        self.assertEqual(checkpoint['schema'], 'lowfork-audit-checkpoint/v1')
        for row in checkpoint['files']:
            source = self.source / row['path']
            self.assertEqual(p.digest(source), row['sha256'])
            self.assertEqual(source.stat().st_size, row['bytes'])
        for name, sha in [('route-b-owner.sh', HELPER_SHA), ('readiness-probe.sh', WORKER_SHA)]:
            self.assertEqual(p.digest(self.source / 'candidate' / name), sha)
            self.assertEqual(p.digest(self.payload / name), sha)
        for name in ('watchdog.sh', 'launch-common.sh'):
            self.assertEqual((self.payload / name).read_bytes(), (V4 / 'package-r2b-disabled/payload' / name).read_bytes())

    def test_complete_boot_member_entry_startup_and_487_member_hash_chain(self):
        self.assertEqual(len(self.plan['members']), 487)
        self.assertEqual(self.manifest['plan_sha256'], p.digest(self.package / 'plan.json'))
        for row in self.manifest['files']:
            source = self.package / row['path']
            self.assertEqual(p.digest(source), row['sha256'], row['path'])
            self.assertEqual(source.stat().st_size, row['bytes'])
        for row in self.plan['members']:
            self.assertEqual(p.digest(self.package / row['source'].removeprefix('$PACKAGE/')), row['sha256'], row['target'])
        aliases = {'start-parent.sh': 'start-parent-prepared.sh', 'spawn.sh': 'spawn-prepared.sh', 'screen-gate': 'screen-gate-feed'}
        rows = [line.split() for line in (self.payload / 'members.tsv').read_text().splitlines()]
        self.assertEqual(len(rows), 13)
        self.assertEqual(len({row[1] for row in rows}), 13)
        for sha, name, mode in rows:
            self.assertEqual(p.digest(self.payload / aliases.get(name, name)), sha, name)
        startup = (self.payload / 'startup.env').read_text()
        fields = dict(re.findall(r"^([A-Z_]+)='([^']*)'$", startup, re.M))
        self.assertEqual(fields['STARTUP_MEMBERS_SHA'], p.digest(self.payload / 'members.tsv'))
        self.assertEqual((self.payload / 'startup.expected.sha256').read_text().strip(), p.digest(self.payload / 'startup.env'))
        for name in ('watchdog.sh', 'route-b-owner.sh'):
            self.assertIn(p.digest(self.payload / name), (self.payload / 'entry.sh').read_text())
        self.assertIn('AUTH_UID=20011300\n', (self.payload / 'config-common.sh').read_text())

    def test_all_v4_before_images_and_5cd_worker_evidence_preserved_disabled(self):
        for name in ('before', 'after', 'preserved', 'prerequisites', 'storage', 'new_storage_directories',
                     'runtime_file_metadata', 'stage_files', 'required_directories', 'control_source'):
            self.assertEqual(self.binding[name], self.oldbinding[name], name)
        oldplan = p.read(V4 / 'package-r2b-disabled/plan.json')
        self.assertEqual({r['target']: r['before'] for r in self.plan['members']},
                         {r['target']: r['before'] for r in oldplan['members']})
        target = self.binding['attempt_root'] + '/readiness-probe.sh'
        before = self.binding['before'][target]
        self.assertFalse(before['exists'])
        self.assertEqual(before['ancestor'], self.binding['attempt_root'])
        evidence = {name: p.pin(pin, HERE) for name, pin in before['evidence'].items()}
        summary = p.read(evidence['summary']); record = p.read(evidence['record'])
        self.assertEqual(summary['serial'], self.binding['serial'])
        self.assertEqual(summary['serial'], '5cd1e3dd00000000000000000923012c')
        self.assertTrue(summary['stable'])
        self.assertEqual(record['exit'], 0)
        self.assertEqual(record['stdout_sha256'], p.digest(evidence['stdout']))
        self.assertIn('PATH=' + before['ancestor'] + '\nABSENT\n', evidence['stdout'].read_text())
        self.assertFalse(self.binding['startup_enabled'])
        self.assertFalse(self.plan['execution_enabled'])
        self.assertNotIn('authorization', self.binding)
        startup = (self.payload / 'startup.env').read_text()
        self.assertIn("STARTUP_APPROVED_BY='PENDING'", startup)
        self.assertIn("STARTUP_ENABLED='0'", startup)
        self.assertFalse(list(self.package.glob('*authorization*')))

    def test_v4_invoke_and_new_executor_ast_unchanged(self):
        def functions(path):
            return {node.name: ast.dump(node, include_attributes=False) for node in ast.parse(path.read_text()).body
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        before, after = functions(V4 / 'toutiao_provider.py'), functions(HERE / 'toutiao_provider.py')
        for name in ('invoke', 'new_executor'):
            self.assertEqual(before[name], after[name], name)

    def test_guardian_checkpoint_pin_drift_refuses_before_package_output(self):
        binding = copy.deepcopy(self.binding)
        binding['guardian_update']['sha256'] = '0' * 64
        with tempfile.TemporaryDirectory(prefix='v5-pin-negative-') as temp:
            root = Path(temp); source = root / 'binding.json'; p.write(source, binding)
            with self.assertRaisesRegex(ValueError, 'SHA drift'):
                p.compile_package(source, root / 'must-not-exist')
            self.assertFalse((root / 'must-not-exist').exists())

    def test_exact_helper_emitter_and_worker_success_only_delta(self):
        old = (self.oldsource / 'candidate/readiness-probe.sh').read_text()
        new = (self.payload / 'readiness-probe.sh').read_text()
        expected = old.replace('   rb_guard_json readiness ready requires_final_original_child_owned || exit 5\n   exit 0;;',
                               '   # Success must leave the 2-second envelope without diagnostic subprocesses.\n'
                               '   # The caller still runs the final original complete child_owned guard.\n   exit 0;;')
        self.assertNotEqual(old, expected)
        self.assertEqual(new, expected)
        def omit_emitter(text):
            start = text.index('rb_guard_json(){'); end = text.index('\nrb_deny(){', start)
            return text[:start] + text[end:]
        self.assertEqual(omit_emitter((self.oldsource / 'candidate/route-b-owner.sh').read_text()),
                         omit_emitter((self.payload / 'route-b-owner.sh').read_text()))
        watchdog = (self.payload / 'watchdog.sh').read_text()
        self.assertIn('timeout 2 sh "$F/readiness-probe.sh"', watchdog)
        self.assertIn('child_owned "$child" "$child_birth" ||', watchdog)

    def test_isolated_exact_uid_success_case_has_zero_encoder_calls(self):
        # This intentionally tests only the changed case statement. It does NOT
        # execute the worker or claim any lock/context/readiness acceptance.
        text = (self.payload / 'readiness-probe.sh').read_text()
        start = text.index(' case "$child_uid" in'); end = text.index('\n esac', start) + len('\n esac')
        branch = text[start:end]
        script = ('RB_OWNER_UID=20011300; child_uid=20011300:20011300:20011300:20011300\n'
                  'rb_guard_json(){ echo forbidden_encoder >&2; exit 97; }\n'
                  'od(){ echo forbidden_od >&2; exit 98; }\n'
                  'reject(){ echo unexpected_reject >&2; exit 96; }\n' + branch)
        result = subprocess.run(['bash', '-c', script], capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout + result.stderr, '')

    def test_actual_helper_wrong_5cd_uid_has_one_od_and_json_diagnostic(self):
        helper = self.payload / 'route-b-owner.sh'
        with tempfile.TemporaryDirectory(prefix='v5-helper-only-') as temp:
            counter = Path(temp) / 'od-count'
            script = '''RB_OWNER_UID=20011300; RB_AUDIT_QUIET=1; export RB_AUDIT_QUIET
. "$1"
[ "$RB_AUDIT_QUIET" = 0 ] || exit 99
OD_COUNT=$2
od(){ printf 'od\\n' >> "$OD_COUNT"; command od "$@"; }
RB_AUDIT_PHASE=strict; RB_AUDIT_PID=101; RB_AUDIT_BIRTH=500
rb_deny uid "20011206:20011206:20011206:20011206" "$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"
'''
            result = subprocess.run(['bash', '-c', script, 'helper-only', str(helper), str(counter)],
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertEqual(counter.read_text().splitlines(), ['od'])
            rows = [json.loads(line) for line in result.stderr.splitlines()]
            self.assertEqual(rows, [{'phase': 'strict', 'pid': '101', 'birth': '500', 'field': 'uid',
                                     'actual': '20011206:20011206:20011206:20011206',
                                     'expected': '20011300:20011300:20011300:20011300'}])


if __name__ == '__main__':
    unittest.main(verbosity=2)
