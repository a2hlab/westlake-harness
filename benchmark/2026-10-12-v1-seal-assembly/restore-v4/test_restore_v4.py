#!/usr/bin/env python3
"""Actual v4 binding/bytes, isolated execution flag, modeled transport only.

Every command is interpreted by FakeDevice; no shell/HDC/network executes.
The checked-in disabled binding remains byte-identical throughout the tests.
"""
import argparse
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import struct
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('restore_v4_under_test', HERE / 'toutiao_provider.py')
p = importlib.util.module_from_spec(spec); spec.loader.exec_module(p)


def pin(path):
    return {'path': str(path), 'sha256': p.digest(path)}


class FakeDevice:
    """File/directory/metadata state with one-shot fault injection, no execution."""
    def __init__(self, plan):
        self.plan = plan
        self.files = {}
        self.dirs = {d['target']: copy.deepcopy(d['after']) for d in plan['directory_prerequisites']}
        self.identities = {target: '1:' + str(i + 100) for i, target in enumerate(self.dirs)}
        self.next_inode = 1000
        self.events = []
        self.rows = {r['target']: r for r in plan['members']}
        self.dirrows = {r['target']: r for r in plan['directories'] + plan['directory_prerequisites']}
        self.fail_create_before = None
        self.fail_create_after = None
        self.fail_readback = None
        self.fail_send = None
        self.user_data = {}
        for row in plan['members'] + plan['preserved']:
            if row['before']['exists']:
                self.files[row['target']] = copy.deepcopy(row['before'])
        for row in plan['prerequisites']:
            self.files[row['target']] = {'exists': True, 'sha256': row['sha256']}

    def probe(self, target):
        return copy.deepcopy(self.files.get(target, {'exists': False}))

    def recv(self, name, target, dest):
        shutil.copyfile(self.files[target]['source'], dest)

    def send(self, name, source, target):
        self.events.append((name, target))
        if self.fail_send == target:
            self.fail_send = None
            self.files[target] = {'exists': True, 'sha256': hashlib.sha256(b'partial').hexdigest(),
                                  'mode': '600', 'uid': 0, 'gid': 0, 'label': 'u:object_r:data_file:s0'}
            raise ValueError('injected partial send with read-only observable bytes')
        self.files[target] = {'exists': True, 'sha256': p.digest(source), 'source': str(source),
                              'mode': '600', 'uid': 0, 'gid': 0, 'label': 'u:object_r:data_file:s0'}

    def shell(self, name, script):
        self.events.append((name, script))
        if name == 'boot': return self.plan['boot_id']
        if name in ('directory-absence', 'unknown-directory-must-be-absent'):
            target = re.search(r'test ! -e ([^ ;]+)', script)[1].strip("'")
            if target in self.dirs or target in self.files or target in self.user_data:
                raise ValueError('unknown or existing directory retained: ' + target)
            return ''
        if name == 'directory-create':
            target = re.search(r'mkdir ([^ ;]+)', script)[1].strip("'")
            if target == self.fail_create_before:
                self.fail_create_before = None
                raise ValueError('injected mkdir failure before creation')
            if target in self.dirs: raise ValueError('mkdir target already exists')
            if str(Path(target).parent) not in self.dirs:
                raise ValueError('mkdir parent missing: ' + target)
            self.dirs[target] = copy.deepcopy(self.dirrows[target]['after'])
            self.next_inode += 1; self.identities[target] = '1:' + str(self.next_inode)
            if target == self.fail_create_after:
                self.fail_create_after = None
                raise ValueError('injected metadata failure after mkdir')
            return ''
        if name in ('existing-host-directory', 'directory-readback'):
            target = re.search(r'test -d ([^ ;]+)', script)[1].strip("'")
            if target == self.fail_readback:
                self.fail_readback = None
                raise ValueError('injected directory readback failure')
            meta = self.dirs[target]
            result = f"{meta['mode']}:{meta['uid']}:{meta['gid']}\n{meta['label']} dir"
            return result + ("\n" + self.identities[target] if name == "directory-readback" else "")
        if name == 'parent-directory-read':
            target = re.search(r'test -d ([^ ;]+)', script)[1].strip("'")
            if target not in self.dirs: raise ValueError('unrecorded parent')
            return ''
        if name == 'control-metadata':
            tokens = shlex.split(script.replace(';', ' ; '))
            i = tokens.index('chown'); uid, gid = map(int, tokens[i + 1].split(':')); target = tokens[i + 2]
            self.files[target].update(uid=uid, gid=gid, mode=tokens[tokens.index('chmod') + 1],
                                      label=tokens[tokens.index('chcon') + 1])
            return ''
        if name == 'cfg-atomic-remount':
            source = next(v for k, v in self.files.items() if '/cfg-stage-' in k and k in script)
            self.files[p.CFG] = dict(source, **self.rows[p.CFG]['after'])
            return ''
        if name == 'cfg-remove-added-remount':
            if p.CFG not in self.files: raise ValueError('CFG already absent')
            if self.files[p.CFG]['sha256'] not in script: raise ValueError('CFG hash guard mismatch')
            self.files.pop(p.CFG)
            return ''
        if name == 'rollback-stop-create':
            target = re.search(r': > ([^ ;]+)', script)[1].strip("'")
            self.files[target] = {'exists': True, 'sha256': hashlib.sha256(b'').hexdigest(),
                                  'mode': '600', 'uid': 0, 'gid': 0, 'label': 'u:object_r:data_file:s0'}
            return ''
        if name == 'remove-own-addition':
            target = script.rsplit('rm ', 1)[1].strip("'")
            self.files.pop(target, None)
            return ''
        if name == 'remove-empty-owned-storage-directory':
            target = re.search(r'rmdir ([^ ;]+)', script)[1].strip("'")
            if target not in self.dirs: return ''
            identity = re.search(r'''stat -c '%d:%i' [^;]+\)" = ([0-9]+:[0-9]+);''', script)
            if not identity or identity[1] != self.identities.get(target):
                raise ValueError('directory dev:inode changed; replacement retained')
            if self.dirs[target] != self.dirrows[target]['after']:
                raise ValueError('directory metadata differs from owned identity')
            if any(k.startswith(target + '/') for k in list(self.dirs) + list(self.files) + list(self.user_data)):
                raise ValueError('nonempty directory retained')
            del self.dirs[target]
            return ''
        raise AssertionError('unmodeled command, never execute: ' + name)


class RestoreV4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='offline-route-b-v4-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.actual = HERE / 'binding.5cd.r2b.disabled.json'
        cls.actual_sha = p.digest(cls.actual)
        cls.binding = copy.deepcopy(p.read(cls.actual))
        cls.binding['startup_enabled'] = True
        cls.bp = cls.root / 'test-binding.json'; p.write(cls.bp, cls.binding)
        cls.package = cls.root / 'package'; p.compile_package(cls.bp, cls.package)
        cls.plan = p.read(cls.package / 'plan.json')

    @classmethod
    def tearDownClass(cls):
        if p.digest(cls.actual) != cls.actual_sha:
            raise AssertionError('actual disabled binding changed')

    def transaction(self, name):
        root = self.root / name; root.mkdir()
        model = FakeDevice(self.plan); calls = []
        def runner(command, **kwargs):
            calls.append(command)
            if command[0] == 'bash': return subprocess.CompletedProcess(command, 0, 'isolated-holder\n', '')
            spec = importlib.util.spec_from_file_location('isolated_v4_executor', self.package / 'executor.py')
            mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            mod.Device = lambda plan, out: model
            out, err = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err): rc = mod.main(command[2:])
            return subprocess.CompletedProcess(command, rc, out.getvalue(), err.getvalue())
        lock = root / 'lock.sh'; lock.write_text('# fake lock, never executed\n')
        auth = root / 'authorization.json'
        p.write(auth, {'approved_by': 'outer(codex)', 'serial': self.plan['serial'], 'boot_id': self.plan['boot_id'],
                       'expires_epoch': time.time() + 600, 'plan_sha256': p.digest(self.package / 'plan.json'),
                       'derived_manifest_sha256': p.digest(self.package / 'manifest.json'), 'holder': 'isolated-holder',
                       'actions': ['place-only', 'one-reboot', 'rollback-safe']})
        prov = {'layer': 'toutiao-route-b', 'program': pin(HERE / 'toutiao_provider.py'),
                'targets': [r['target'] for r in self.plan['members']],
                'prepared': {'path': str(self.package), 'manifest_sha256': p.digest(self.package / 'manifest.json')},
                'authorization': pin(auth), 'lock_tool': pin(lock), 'action': 'apply'}
        dep = {'schema': 'demo-restore-deployment/v1', 'execution_enabled': True, 'providers': [prov]}
        seal = {'schema': 'demo-seal/v1', 'files': {'overlays': {r['target']: r['sha256'] for r in self.plan['members']}}}
        dp = root / 'deployment.json'; sp = root / 'seal.json'; p.write(dp, dep); p.write(sp, seal)
        args = argparse.Namespace(seal=str(sp), serial=self.plan['serial'], deployment=str(dp), out=str(root / 'tx'))
        return root, model, calls, runner, dep, args

    def call(self, args, runner):
        original = p.invoke; p.invoke = lambda a: original(a, runner)
        out, err = io.StringIO(), io.StringIO()
        try:
            with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                rc = p.main(['--seal', args.seal, '--serial', args.serial,
                             '--deployment', args.deployment, '--out', args.out])
        finally: p.invoke = original
        return rc, out.getvalue() + err.getvalue()

    def rollback(self, tx, attempt):
        root, model, calls, runner, dep, args = tx
        dep['providers'][0].update(action='rollback', transaction_dir=str(root / 'tx'))
        Path(args.deployment).write_text(json.dumps(dep)); args.out = str(root / attempt)
        return self.call(args, runner)

    def assert_all_preimages(self, model):
        for row in self.plan['members']:
            actual = model.probe(row['target'])
            for key, value in row['before'].items():
                if key in ('exists', 'sha256', 'mode', 'uid', 'gid', 'label'):
                    self.assertEqual(actual.get(key), value, (row['target'], key))

    def compile_reject(self, binding, reason):
        with tempfile.TemporaryDirectory(dir=self.root) as temp:
            root = Path(temp); bp = root / 'negative-binding.json'; p.write(bp, binding)
            with self.assertRaisesRegex(ValueError, reason):
                p.compile_package(bp, root / 'must-not-exist')
            self.assertFalse((root / 'must-not-exist').exists())

    def test_control_source_four_pins_reject_drift_before_output(self):
        for field in ('plan', 'composition', 'base_plan', 'worker_preimage'):
            with self.subTest(field):
                binding = copy.deepcopy(self.binding)
                binding['control_source'][field]['sha256'] = '0' * 64
                self.compile_reject(binding, 'SHA drift')

    def test_missing_worker_target_preimage_rejected(self):
        binding = copy.deepcopy(self.binding)
        del binding['before'][binding['attempt_root'] + '/readiness-probe.sh']
        self.compile_reject(binding, 'preimage missing')

    def test_foreign_worker_target_does_not_replace_required_before(self):
        binding = copy.deepcopy(self.binding)
        target = binding['attempt_root'] + '/readiness-probe.sh'
        binding['before'][p.OLD_ROOT + '/readiness-probe.sh'] = binding['before'].pop(target)
        self.compile_reject(binding, 'preimage missing')

    def test_control_source_missing_or_foreign_worker_target_rejects(self):
        for mode in ('missing', 'foreign'):
            with self.subTest(mode):
                binding = copy.deepcopy(self.binding)
                original = p.resolve(binding['control_source']['composition']['path'], HERE).parent
                copied = self.root / ('control-source-' + mode)
                shutil.copytree(original, copied)
                plan_path = copied / 'plan.enabled.json'
                plan = p.read(plan_path)
                target = p.OLD_ROOT + '/readiness-probe.sh'
                if mode == 'missing':
                    plan['members'] = [r for r in plan['members'] if r['target'] != target]
                else:
                    next(r for r in plan['members'] if r['target'] == target)['target'] = p.OLD_ROOT + '/foreign/readiness-probe.sh'
                plan_path.write_text(json.dumps(plan))
                binding['control_source']['plan'] = pin(plan_path)
                binding['control_source']['composition'] = pin(copied / 'composition.json')
                self.compile_reject(binding, 'control24 target set drift')

    def test_worker_members_startup_entry_full_hash_chain(self):
        payload = self.package / 'payload'
        worker_target = self.binding['attempt_root'] + '/readiness-probe.sh'
        worker = next(row for row in self.plan['members'] if row['target'] == worker_target)
        self.assertEqual(worker['before'], self.binding['before'][worker_target])
        self.assertFalse(worker['before']['exists'])
        self.assertEqual(worker['sha256'], p.digest(payload / 'readiness-probe.sh'))
        manifest = {row['path']: row for row in p.read(self.package / 'manifest.json')['files']}
        aliases = {'start-parent.sh': 'start-parent-prepared.sh', 'spawn.sh': 'spawn-prepared.sh',
                   'screen-gate': 'screen-gate-feed'}
        rows = [line.split() for line in (payload / 'members.tsv').read_text().splitlines()]
        self.assertEqual(len(rows), 13)
        self.assertEqual(len({row[1] for row in rows}), 13)
        self.assertIn('readiness-probe.sh', {row[1] for row in rows})
        for sha, name, mode in rows:
            source = payload / aliases.get(name, name)
            self.assertEqual(p.digest(source), sha, name)
            self.assertEqual(manifest['payload/' + source.name]['sha256'], sha)
        startup = (payload / 'startup.env').read_text()
        fields = dict(re.findall(r"^([A-Z_]+)='([^']*)'$", startup, re.M))
        self.assertEqual(fields['STARTUP_MEMBERS_SHA'], p.digest(payload / 'members.tsv'))
        self.assertEqual((payload / 'startup.expected.sha256').read_text().strip(), p.digest(payload / 'startup.env'))
        self.assertEqual(manifest['payload/startup.env']['sha256'], p.digest(payload / 'startup.env'))
        entry = (payload / 'entry.sh').read_text()
        for name in ('watchdog.sh', 'route-b-owner.sh'):
            self.assertIn(p.digest(payload / name), entry)
        for row in self.plan['members']:
            source = self.package / row['source'].removeprefix('$PACKAGE/')
            self.assertEqual(row['sha256'], p.digest(source), row['target'])

    def test_guardian_cores_match_r2b_helper_and_ee50_worker_watchdog(self):
        source = p.resolve(self.binding['control_source']['composition']['path'], HERE).parent / 'payload'
        expected = {'watchdog.sh': '423e60f7445a99c720071e7990e5ba21f60745252b949eac3216009431f44601',
                    'route-b-owner.sh': '68abf028c80d5c036334fcbd974c609b0d967083ea72ead14b27928346856107',
                    'readiness-probe.sh': 'c0326a4b89b1d4f4ea63b190c5312e77d9656259f06f638cdfefddde9c31c55b'}
        for name, sha in expected.items():
            with self.subTest(name):
                baseline = p.resolve(self.binding['guardian_update']['path'], HERE).parent / 'candidate' if name == 'route-b-owner.sh' else source
                self.assertEqual(p.digest(baseline / name), sha)
                self.assertEqual(p.digest(self.package / 'payload' / name), sha)

    def test_guardian_update_checkpoint_pin_drift_rejects_before_output(self):
        binding = copy.deepcopy(self.binding)
        binding['guardian_update']['sha256'] = '0' * 64
        self.compile_reject(binding, 'SHA drift')

    def quiet_fixture(self):
        source = p.resolve(self.binding['guardian_update']['path'], HERE).parent
        test_source = source / 'test_quiet_scan.py'
        manifest = p.read(source / 'checkpoint-manifest.json')
        row = next(row for row in manifest['files'] if row['path'] == 'test_quiet_scan.py')
        self.assertEqual(p.digest(test_source), row['sha256'])
        helper = self.package / 'payload/route-b-owner.sh'
        self.assertEqual(p.digest(helper), p.digest(source / 'candidate/route-b-owner.sh'))
        spec = importlib.util.spec_from_file_location('pinned_r2b_offline_quiet_fixture', test_source)
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        return mod.QuietScanTests(), helper

    def test_final_payload_quiet_enumeration_has_zero_od(self):
        fixture, helper = self.quiet_fixture()
        result, calls = fixture.scan(helper)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), ['151', '152'])
        self.assertEqual(result.stderr, '')
        self.assertEqual(calls, 0)

    def test_final_payload_target_wrong_uid_diagnostic_is_nonempty(self):
        fixture, helper = self.quiet_fixture()
        result, calls = fixture.scan(helper, target=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(calls, 6)
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['field'], 'uid')
        self.assertEqual(rows[0]['actual'], '0:0:0:0')
        self.assertEqual(rows[0]['expected'], '20011206:20011206:20011206:20011206')

    def test_final_payload_resets_inherited_quiet_and_logs_uid_error(self):
        _, helper = self.quiet_fixture()
        script = '\n'.join([
            'RB_AUDIT_QUIET=1; export RB_AUDIT_QUIET',
            '. "$1"',
            '[ "$RB_AUDIT_QUIET" = 0 ] || exit 99',
            'RB_AUDIT_PID=101; RB_AUDIT_BIRTH=500; RB_AUDIT_PHASE=strict',
            'rb_deny uid "0:0:0:0" "20011300:20011300:20011300:20011300"',
        ])
        result = subprocess.run(['bash', '-c', script, 'local-fixture', str(helper)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1)
        rows = [json.loads(line) for line in result.stderr.splitlines()]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['field'], 'uid')
        self.assertEqual(rows[0]['actual'], '0:0:0:0')
        self.assertEqual(rows[0]['expected'], '20011300:20011300:20011300:20011300')

    def test_actual_uid_projection_is_20011300_and_wrong_uid_rejects(self):
        self.assertEqual(self.binding['host_uid'], 20011300)
        config = (self.package / 'payload/config-common.sh').read_text()
        self.assertEqual(re.findall(r'^AUTH_UID=(.*)$', config, re.M), ['20011300'])
        entry = (self.package / 'payload/entry.sh').read_text()
        self.assertIn('TT_OWNER_UID="$AUTH_UID"', entry)
        request = (self.package / 'runtime/stage/request.bin').read_bytes()
        self.assertEqual(struct.unpack_from('<II', request, 312), (20011300, 20011300))
        worker = (self.package / 'payload/readiness-probe.sh').read_text()
        self.assertIn('RB_OWNER_UID=${TT_OWNER_UID:-}', worker)
        self.assertIn('"$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID:$RB_OWNER_UID"', worker)
        self.assertNotIn('20011206', worker)
        binding = copy.deepcopy(self.binding); binding['host_uid'] = 20011301
        self.compile_reject(binding, 'metadata projection|host directory|host UID')

    def test_full_apply_rollback_restores_absent_cfg(self):
        self.assertEqual(len(self.plan['members']), 487)
        self.assertEqual(len(self.plan['directories']), 22)
        self.assertFalse(next(r for r in self.plan['members'] if r['target'] == p.CFG)['before']['exists'])
        tx = self.transaction('full'); root, model, calls, runner, dep, args = tx
        rc, output = self.call(args, runner); self.assertEqual(rc, 0, output)
        self.assertEqual(len(list((root / 'tx').glob('directory-created-*.json'))), 22)
        rc, output = self.rollback(tx, 'rollback'); self.assertEqual(rc, 0, output)
        self.assert_all_preimages(model)
        self.assertFalse(model.probe(p.CFG)['exists'])
        self.assertTrue((root / 'tx/rollback.json').exists())
        self.assertTrue(any(e[0] == 'cfg-remove-added-remount' for e in model.events))
        self.assertFalse(set(model.dirs) & {d['target'] for d in self.plan['storage_directories']})

    def test_first_mkdir_failure_rolls_back_all_new_directories(self):
        tx = self.transaction('first-mkdir'); root, model, calls, runner, dep, args = tx
        model.fail_create_before = self.plan['directories'][0]['target']
        rc, output = self.call(args, runner); self.assertNotEqual(rc, 0, output)
        self.assertEqual(len(list((root / 'tx').glob('directory-intent-*.json'))), 1)
        self.assertFalse(list((root / 'tx').glob('directory-created-*.json')))
        rc, output = self.rollback(tx, 'rollback'); self.assertEqual(rc, 0, output)
        self.assertFalse(set(model.dirs) & {d['target'] for d in self.plan['directories']})
        self.assert_all_preimages(model)

    def test_mkdir_metadata_or_readback_failure_retains_unknown_until_operator_removes(self):
        for mode in ('fail_create_after', 'fail_readback'):
            with self.subTest(mode):
                tx = self.transaction(mode); root, model, calls, runner, dep, args = tx
                target = self.plan['directories'][3]['target']; setattr(model, mode, target)
                rc, output = self.call(args, runner); self.assertNotEqual(rc, 0, output)
                self.assertIn(target, model.dirs)
                self.assertFalse((root / 'tx/directory-created-003.json').exists())
                rc, output = self.rollback(tx, 'rollback'); self.assertNotEqual(rc, 0, output)
                self.assertFalse((root / 'tx/rollback.json').exists())
                self.assertIn(target, model.dirs)
                self.assertTrue(list((root / 'tx').glob('rollback-cleanup-failed-*.json')))
                del model.dirs[target]  # Explicit modeled operator remediation, never automatic deletion.
                rc, output = self.rollback(tx, 'retry'); self.assertEqual(rc, 0, output)
                self.assertFalse(set(model.dirs) & {d['target'] for d in self.plan['directories']})

    def test_owned_nonempty_storage_retains_user_data_then_retry(self):
        tx = self.transaction('nonempty'); root, model, calls, runner, dep, args = tx
        rc, output = self.call(args, runner); self.assertEqual(rc, 0, output)
        target = self.plan['storage_directories'][-1]['target']; key = target + '/user-kept'
        model.user_data[key] = b'preserve me'
        rc, output = self.rollback(tx, 'rollback'); self.assertNotEqual(rc, 0, output)
        self.assertFalse((root / 'tx/rollback.json').exists())
        self.assertEqual(model.user_data[key], b'preserve me')
        self.assertTrue(list((root / 'tx').glob('rollback-cleanup-failed-*.json')))
        moved = model.user_data.pop(key)  # Modeled operator moves bytes; provider never deletes them.
        rc, output = self.rollback(tx, 'retry'); self.assertEqual(rc, 0, output)
        self.assertEqual(moved, b'preserve me'); self.assert_all_preimages(model)

    def test_partial_file_send_failure_rolls_back_exact_observed_partial(self):
        tx = self.transaction('partial-send'); root, model, calls, runner, dep, args = tx
        row = next(r for r in self.plan['members'] if r['target'].startswith(self.binding['runtime_root'] + '/'))
        model.fail_send = row['target']
        rc, output = self.call(args, runner); self.assertNotEqual(rc, 0, output)
        failures = list((root / 'tx').glob('failed-*.json')); self.assertEqual(len(failures), 1)
        self.assertEqual(p.read(failures[0])['observation']['sha256'], hashlib.sha256(b'partial').hexdigest())
        rc, output = self.rollback(tx, 'rollback'); self.assertEqual(rc, 0, output)
        self.assert_all_preimages(model)

    def test_same_metadata_replacement_inode_is_never_deleted(self):
        tx = self.transaction('replacement-inode'); root, model, calls, runner, dep, args = tx
        rc, output = self.call(args, runner); self.assertEqual(rc, 0, output)
        row = self.plan['storage_directories'][-1]; target = row['target']
        model.identities[target] = '1:999999'
        rc, output = self.rollback(tx, 'rollback'); self.assertNotEqual(rc, 0, output)
        self.assertEqual(model.dirs[target], row['after'])
        self.assertEqual(model.identities[target], '1:999999')
        self.assertFalse((root / 'tx/rollback.json').exists())
        partial = list((root / 'tx').glob('rollback-cleanup-failed-*.json'))
        self.assertTrue(partial)
        self.assertIn('dev:inode', p.read(partial[0])['residual_or_unverified'][0]['error'])

    def test_unknown_same_metadata_directory_is_never_deleted(self):
        tx = self.transaction('unknown-equal'); root, model, calls, runner, dep, args = tx
        model.fail_create_before = self.plan['directories'][0]['target']
        rc, output = self.call(args, runner); self.assertNotEqual(rc, 0, output)
        row = self.plan['directories'][0]; model.dirs[row['target']] = copy.deepcopy(row['after'])
        rc, output = self.rollback(tx, 'rollback'); self.assertNotEqual(rc, 0, output)
        self.assertEqual(model.dirs[row['target']], row['after'])
        self.assertFalse((root / 'tx/rollback.json').exists())
        self.assertFalse(any(name == 'remove-empty-owned-storage-directory' for name, _ in model.events))


if __name__ == '__main__':
    unittest.main(verbosity=2)
