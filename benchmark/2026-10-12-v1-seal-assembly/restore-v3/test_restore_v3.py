#!/usr/bin/env python3
"""Actual v3 binding/bytes, isolated execution flag, modeled transport only.

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
import tempfile
import time
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('restore_v3_under_test', HERE / 'toutiao_provider.py')
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


class RestoreV3Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='offline-route-b-v3-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        cls.actual = HERE / 'binding.5cd.disabled.json'
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
            spec = importlib.util.spec_from_file_location('isolated_v3_executor', self.package / 'executor.py')
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

    def test_full_apply_rollback_restores_absent_cfg(self):
        self.assertEqual(len(self.plan['members']), 486)
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
