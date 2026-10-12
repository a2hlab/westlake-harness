"""Focused SYNTHETIC transport tests. No HDC, lock or board command is executed."""
import copy
import importlib.util
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('directory_transaction_tested', HERE / 'directory_transaction.py')
d = importlib.util.module_from_spec(spec); spec.loader.exec_module(d)
BOOT = '6e0e0000-0000-0000-0000-000000000000'


class FakeDevice:
    """Minimal directory state; every returned recording is synthetic."""
    def __init__(self):
        self.steps = []
        self.nodes = {d.ROOT: dict(d.META, identity='1:10', exists=True)}
        self.fail = None
        self.mutations = []
        self.unknown = False
        self.nonempty = False
        self.replaced_before_rmdir = False

    def shell(self, name, script):
        row = {'name': name, 'script': script, 'transport_rc': 0, 'remote_rc': 0, 'synthetic': True}
        self.steps.append(row)
        if self.fail == name:
            row['remote_rc'] = 7
            raise d.CommandError(name + ' injected remote rc=7')
        match = re.search(r'^p=(.*)$', script, re.M)
        path = shlex.split(match[1])[0]
        if name == 'probe-directory':
            if self.unknown:
                return 'UNKNOWN'
            node = self.nodes.get(path)
            if not node:
                return 'ABSENT'
            if node.get('symlink'):
                row['remote_rc'] = 1
                raise d.CommandError('symlink chain')
            return '\n'.join(['EXISTS', '%s %s %s' % (node['mode'],node['uid'],node['gid']),
                'drwxr-xr-x 2 %s %s %s 4096 2026-10-13 %s' % (node['uid'],node['gid'],node['label'],path), node['identity']])
        if name == 'mkdir-single':
            self.assert_intent()
            if path in self.nodes:
                raise d.CommandError('mkdir EEXIST')
            self.nodes[path] = dict(d.META, uid=0, gid=0, identity='1:11', exists=True)
            self.mutations.append(name)
            return '1:11'
        identity = re.search(r"test \"\$\(stat -c '%d:%i' \"\$p\"\)\" = ([^\n]+)", script)
        if self.replaced_before_rmdir and name == 'rmdir-owned-empty-only':
            self.nodes[path]['identity'] = '1:999'
        if not identity or shlex.split(identity[1])[0] != self.nodes[path]['identity']:
            row['remote_rc'] = 1
            raise d.CommandError('owned inode guard rejects')
        if name == 'chown':
            self.nodes[path].update(uid=20011300,gid=20011300)
        elif name == 'chmod':
            self.nodes[path]['mode'] = '755'
        elif name == 'chcon':
            self.nodes[path]['label'] = d.META['label']
        elif name == 'rmdir-owned-empty-only':
            if self.nonempty:
                row['remote_rc'] = 1
                raise d.CommandError('Directory not empty; user data preserved')
            del self.nodes[path]
        else:
            raise AssertionError('unexpected synthetic command ' + name)
        self.mutations.append(name)
        return ''

    def assert_intent(self):
        assert (self.out / 'intent.json').is_file(), 'intent must precede mkdir'
        assert not (self.out / 'owned.json').exists()


class DirectoryTransactionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='SYNTHETIC-directory-supplement-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name); self.out = self.root / 'transaction'
        self.dev = FakeDevice(); self.dev.out = self.out
        self.manifest = {'boot_id': BOOT, '_sha256': 'a' * 64}
        blocker = patch('subprocess.run', side_effect=AssertionError('test must not execute device/lock commands'))
        blocker.start(); self.addCleanup(blocker.stop)

    def apply(self):
        return d.transaction(self.manifest, self.dev, self.out, 'apply', {})

    def rollback(self):
        auth = {'journal_sha256': d.digest(self.out / 'journal.json')}
        return d.transaction(self.manifest, self.dev, self.out, 'rollback', auth)

    def test_create_metadata_verify_and_owned_empty_rollback(self):
        result = self.apply()
        self.assertEqual(result['state'], 'CREATED_VERIFIED')
        self.assertEqual(result['executor_rc'], 0)
        self.assertEqual(d.metadata(self.dev.nodes[d.TARGET]), d.META)
        self.assertEqual(self.dev.mutations, ['mkdir-single','chown','chmod','chcon'])
        self.assertEqual(self.rollback()['state'], 'ROLLED_BACK_EMPTY_DIRECTORY')
        self.assertNotIn(d.TARGET, self.dev.nodes)
        self.assertTrue((self.out / 'rollback.json').exists())
        scripts = '\n'.join(row['script'] for row in self.dev.steps)
        self.assertNotIn('mkdir -p', scripts)
        self.assertNotIn('rm ', scripts)
        self.assertNotIn('reboot', scripts)

    def test_existing_exact_is_readonly_and_never_transaction_owned(self):
        self.dev.nodes[d.TARGET] = dict(d.META, identity='1:12', exists=True)
        result = self.apply()
        self.assertEqual(result['state'], 'ALREADY_EQUAL')
        self.assertFalse(result['created'])
        self.assertEqual(self.dev.mutations, [])
        result = d.transaction(self.manifest,self.dev,self.out,'rollback',{'journal_sha256':'0'*64})
        self.assertNotEqual(result['executor_rc'],0)
        self.assertIn(d.TARGET,self.dev.nodes)

    def test_unknown_transport_symlink_parent_and_existing_drift_reject(self):
        cases = [('unknown', lambda: setattr(self.dev,'unknown',True)),
                 ('transport',lambda: setattr(self.dev,'fail','probe-directory')),
                 ('symlink',lambda: self.dev.nodes.update({d.TARGET:dict(d.META,identity='1:12',exists=True,symlink=True)})),
                 ('parent',lambda: self.dev.nodes[d.ROOT].update(uid=0)),
                 ('existing',lambda: self.dev.nodes.update({d.TARGET:dict(d.META,uid=1,identity='1:12',exists=True)}))]
        for name, mutate in cases:
            with self.subTest(name=name):
                self.dev=FakeDevice();self.out=self.root/name;self.dev.out=self.out;mutate()
                result=self.apply()
                self.assertNotEqual(result['executor_rc'],0)
                self.assertEqual(self.dev.mutations,[])

    def test_failed_mkdir_and_metadata_keep_real_rc_and_safe_rollback(self):
        self.dev.fail='mkdir-single'
        result=self.apply()
        self.assertNotEqual(result['executor_rc'],0)
        self.assertEqual(next(s for s in result['steps'] if s['name']=='mkdir-single')['remote_rc'],7)
        self.assertTrue((self.out/'intent.json').exists())
        self.assertFalse((self.out/'owned.json').exists())
        self.out=self.root/'partial';self.dev=FakeDevice();self.dev.out=self.out;self.dev.fail='chmod'
        result=self.apply()
        self.assertNotEqual(result['executor_rc'],0)
        self.assertEqual(next(s for s in result['steps'] if s['name']=='chmod')['remote_rc'],7)
        self.assertTrue((self.out/'journal.json').exists())
        self.dev.fail=None
        self.assertEqual(self.rollback()['executor_rc'],0)

    def test_nonempty_preserved_failure_then_explicit_retry(self):
        self.assertEqual(self.apply()['executor_rc'],0)
        self.dev.nonempty=True
        result=self.rollback()
        self.assertNotEqual(result['executor_rc'],0)
        self.assertIn(d.TARGET,self.dev.nodes)
        self.assertFalse((self.out/'rollback.json').exists())
        self.assertTrue(list(self.out.glob('failure-*.json')))
        # External user-data disposition is outside this executor. The fixture
        # only models the directory becoming empty before a separately authorized retry.
        self.dev.nonempty=False
        self.assertEqual(self.rollback()['executor_rc'],0)

    def test_identity_metadata_and_between_probe_rmdir_replacement_preserved(self):
        self.assertEqual(self.apply()['executor_rc'],0)
        saved=copy.deepcopy(self.dev.nodes[d.TARGET])
        for field,value in [('identity','1:99'),('uid',0),('label','u:object_r:other:s0')]:
            with self.subTest(field=field):
                self.dev.nodes[d.TARGET]=dict(saved,**{field:value})
                self.assertNotEqual(self.rollback()['executor_rc'],0)
                self.assertIn(d.TARGET,self.dev.nodes)
                self.assertFalse((self.out/'rollback.json').exists())
        self.dev.nodes[d.TARGET]=saved;self.dev.replaced_before_rmdir=True
        self.assertNotEqual(self.rollback()['executor_rc'],0)
        self.assertIn(d.TARGET,self.dev.nodes)

    def test_actual_shell_transport_and_remote_status_recorded(self):
        class Transport:
            def __init__(self, transport_rc=0, remote_rc=0, marker=True):
                self.transport_rc,self.remote_rc,self.marker=transport_rc,remote_rc,marker
            def run(self,name,argv):
                token=re.search(r'__R4_RC_[0-9a-f]+__',argv[-1])[0]
                return self.transport_rc, 'raw\n'+(token+str(self.remote_rc)+'\n' if self.marker else '')
        for host,remote,marker in [(0,0,True),(3,0,True),(0,7,True),(0,0,False)]:
            dev=object.__new__(d.Device);dev.hdc='SYNTHETIC-no-device';dev.steps=[];dev.transport=Transport(host,remote,marker)
            if host==remote==0 and marker:
                self.assertEqual(dev.shell('synthetic-read','true'),'raw')
            else:
                with self.assertRaises(d.CommandError):dev.shell('synthetic-read','true')
            self.assertEqual(dev.steps[0]['transport_rc'],host)
            self.assertEqual(dev.steps[0]['remote_rc'],remote if marker else None)

    def test_manifest_selfpin_raw_identity_and_independent_authority(self):
        # Real immutable source bytes; all authorization bytes are ephemeral
        # SYNTHETIC fixtures whose lock tool always fails. No CLI is executed.
        spec=importlib.util.spec_from_file_location('r4_prepare_fixture',HERE/'prepare.py')
        prep=importlib.util.module_from_spec(spec);spec.loader.exec_module(prep)
        main=HERE.parents[3]/'westlake-harness'
        run=main/'benchmark/2026-10-12-v1-seal-execution'
        manifest_path=self.root/'candidate.json'
        actual_boot='6e0e331f-dc28-4851-b082-709a3a1d515b'
        args=SimpleNamespace(out=manifest_path,origin_realization=run/'exact-5cd-placement/realization.json',
            prepared_plan=run/'exact-5cd-preview/plan.json',
            source_record=run/'61b-directory-source-readonly/001-source-directories.json',
            target_record=run/'5cd-prestate-predicates/001-readonly-predicates.json',boot_id=actual_boot)
        # prepare.pin intentionally requires WORKSPACES-local outputs; only its
        # local reporting serializer is substituted for this temporary fixture.
        with patch.object(prep,'pin',side_effect=lambda p:{'path':str(Path(p).resolve()),'sha256':d.digest(p)}):
            manifest=prep.prepare(args)
        lock=self.root/'SYNTHETIC-never-held.sh';lock.write_text('#!/bin/sh\nexit 99\n')
        auth_path=self.root/'SYNTHETIC-authorization-not-for-execution.json'
        auth={'schema':'exact-directory-authorization/v1','approved_by':'outer(codex)',
              'test_fixture':'SYNTHETIC; fake lock can never be held; no device execution',
              'manifest_sha256':d.digest(manifest_path),'executor_sha256':d.digest(HERE/'directory_transaction.py'),
              'serial':d.SERIAL,'boot_id':actual_boot,'action':'apply','expires_epoch':9999999999,
              'holder':'SYNTHETIC-NEVER-A-REAL-HOLDER','lock_tool':{'path':str(lock),'sha256':d.digest(lock)}}
        def validate():
            manifest_path.write_text(json.dumps(manifest));auth['manifest_sha256']=d.digest(manifest_path)
            auth_path.write_text(json.dumps(auth))
            return d.validate(manifest_path,d.digest(manifest_path),auth_path,d.digest(auth_path),d.SERIAL,actual_boot,'apply')
        self.assertEqual(validate()[0]['after'],d.META)
        auth['approved_by']='self'
        with self.assertRaisesRegex(ValueError,'outer authorization'):validate()
        auth['approved_by']='outer(codex)';auth['expires_epoch']=0
        with self.assertRaisesRegex(ValueError,'expired'):validate()
        auth['expires_epoch']=9999999999
        manifest['executor_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'self pin'):validate()
        manifest['executor_sha256']=d.digest(HERE/'directory_transaction.py')
        record=d.read(d.pin(manifest['evidence']['source_receipt'],HERE))
        record['argv'][2]=d.SERIAL
        changed=self.root/'SYNTHETIC-wrong-source-serial.json';changed.write_text(json.dumps(record))
        manifest['evidence']['source_receipt']={'path':str(changed),'sha256':d.digest(changed)}
        with self.assertRaisesRegex(ValueError,'argv/serial'):validate()


if __name__=='__main__':
    unittest.main(verbosity=2)
