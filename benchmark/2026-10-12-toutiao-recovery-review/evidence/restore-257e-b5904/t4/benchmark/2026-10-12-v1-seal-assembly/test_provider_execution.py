#!/usr/bin/env python3
"""Offline subprocess contract tests: board/executor modules are local doubles.

Production provider entry points run with the standard t5 argv. The deployment
uses a test-only pinned executor and a fake or actual missing-only install entry; no HDC, remote host or device exists
in this fixture. These results are never live acceptance evidence.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

HERE = Path(__file__).resolve().parent
SERIAL = '5cd1e3dd00000000000000000923012c'
BOOT = '43bc3915-04bd-42ca-895e-26e8292911fa'

FAKE_EXECUTOR = r'''
import hashlib,json,os,re
from pathlib import Path
SENTINEL='pinned-executor-double'
class BatchStop(RuntimeError): pass
class AppFailure(RuntimeError): pass
def state(): return json.loads(Path(os.environ['PROVIDER_TEST_STATE']).read_text())
def save_state(s): Path(os.environ['PROVIDER_TEST_STATE']).write_text(json.dumps(s))
def event(kind, **kw):
 with Path(os.environ['PROVIDER_TEST_EVENTS']).open('a') as f:f.write(json.dumps(dict(kind=kind,**kw))+'\n')
def save(path,value):
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
def bm_success(rc,text,operation):return rc==0 and 'successfully' in text

def parse_bundle(text,name):
 try: obj=json.loads(text)
 except ValueError:raise AppFailure('bundle absent')
 if obj.get('name')!=name:raise AppFailure('bundle mismatch')
 return {'queryable':True,'uid':20011300,'package':name}
def cold_stop(board,name,uid,out,stage):
 raise AssertionError('cold_stop forbidden in missing-only profile')

def resolve_input(root,app):
 p=Path(root)/(app['key']+'.apk')
 h=hashlib.sha256(p.read_bytes()).hexdigest()
 if h != app['apk_sha256']:raise AppFailure('APK byte drift')
 return dict(app,apk=str(p))
class Board:
 def __init__(self,serial,hdc,lock,lane,out):self.serial=serial;self.boot=None
 def ready(self):
  event('ready')
  s=state()
  if s.get('transport_failed'):raise BatchStop('test transport failure')
  self.boot=s['boot']
 def send(self,local,remote):
  self.ready();s=state();h=hashlib.sha256(Path(local).read_bytes()).hexdigest()
  s.setdefault('staged',{})[remote]=h;save_state(s);event('send',remote=remote)
 def shell(self,command,required=False,timeout=60):
  self.ready();event('read',command=command);s=state()
  if command.startswith('if [ -f '):
   p=command.split()[3]
   h=s['hashes'].get(p)
   return (0,h+'  '+p if h else 'VERIFIED_ABSENT')
  if command=='cat /data/westlake-demo/u13/receipt.env':return 0,s['controls']
  if command=='cat /data/westlake-demo/u13/u13-recover-table.tsv':return 0,s['table']
  if command=='cat /proc/mounts':return 0,s['mounts']
  if '/data/westlake-demo/u13/DISABLED' in command:return 0,'ENABLED'
  if command.startswith('bm dump -n '):
   if s.get('unknown_bms'):return 0,'unexpected BMS response'
   name=command.split()[-1];v=s['packages'].get(name)
   return (0,json.dumps({'name':name,'versionCode':v})) if v is not None else (0,'error: failed to get information and the parameters may be wrong.')
  if command.startswith('mkdir -p '):return 0,''
  if command.startswith('sha256sum '):
   p=command.split()[-1]
   return 0,s['staged'][p]+'  '+p
  if command.startswith('bm install -p '):
   remote=command.split()[-1];h=s['staged'][remote]
   app=next(a for a in s['apps'] if a['apk_sha256']==h)
   event('bm_install',key=app['key'],command=command);rc=s.get('install_rc',0)
   if rc==0:
    s['hashes'][app['apk_path']]=h;s['packages'][app['package']]=int(app['version_code']);save_state(s)
   return rc,'install bundle successfully' if rc==0 else 'test bm install failure'
  raise AssertionError('unexpected command in isolated test: '+command)
'''
FAKE_ENTRY = r'''
b=None
def install_one(board,app,root,out,remote):
 assert b.SENTINEL=='pinned-executor-double','entry must use pinned executor'
 out.mkdir(parents=True)
 b.event('install',key=app['key'])
 s=b.state()
 if s.get('batch_stop'):raise b.BatchStop('test interrupted install')
 rc=s.get('install_rc',0)
 if rc==0:
  s['hashes'][app['apk_path']]=app['apk_sha256']
  s['packages'][app['package']]=int(app['version_code'])
  b.save_state(s)
 return {'key':app['key'],'status':'installed' if rc==0 else 'app_failed',
         'install':{'return_code':rc,'success_text':rc==0},'error':None if rc==0 else 'test install failure'}
'''


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class ProviderExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='offline-provider-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.events_path = self.root / 'events.jsonl'
        self.state_path = self.root / 'state.json'
        self.exe = self.root / 'executor.py'
        self.entry = self.root / 'entry.py'
        self.exe.write_text(FAKE_EXECUTOR)
        self.entry.write_text(FAKE_ENTRY)
        self.input_root = self.root / 'inputs'
        self.input_root.mkdir()
        self.apps = []
        for key in ('alpha', 'bravo'):
            apk = self.input_root / (key + '.apk')
            apk.write_bytes(('isolated-test-apk-' + key).encode())
            self.apps.append(dict(key=key, package='org.test.' + key,
                                  apk_path='/data/test/' + key + '.apk',
                                  apk_sha256=sha(apk), version_code='2', phase='controls'))
        self.manifest = self.root / 'manifest.json'
        self.manifest.write_text(json.dumps({'apps': self.apps}))
        self.seal = {'schema': 'demo-seal/v1', 'serial': SERIAL,
                     'files': {'runtime': {'/system/runtime': 'a' * 64},
                               'boot': {'/system/boot': 'b' * 64},
                               'installation': {'/system/installer': 'c' * 64}, 'overlays': {}},
                     'packages': self.apps}
        hashes = {p: h for group in self.seal['files'].values() for p, h in group.items()}
        hashes.update({app['apk_path']: app['apk_sha256'] for app in self.apps})
        self.state = {'boot': BOOT, 'hashes': hashes, 'apps': self.apps,
                      'packages': {app['package']: 2 for app in self.apps},
                      'controls': 'state=READY\nlayers=56\nboot_id=' + BOOT + '\n'}
        self.state['table'] = '\n'.join(
            f'{n}\tfile\tbase\t/system/test-mount-{n}\t/data/source-{n}\t' + 'a' * 64
            for n in range(56))
        self.state['mounts'] = '\n'.join(
            f'/dev/test /system/test-mount-{n} ext4 ro 0 0' for n in range(56))
        self.prov = dict(layer='u13', serial=SERIAL, boot_id=BOOT,
                         program=self.pin(HERE / 'u13_provider.py'),
                         common=self.pin(HERE / 'provider_common.py'), executor=self.pin(self.exe),
                         targets=list(hashes), transport={'hdc_cmd': 'FORBIDDEN-test-only',
                                                          'lock_cmd': 'FORBIDDEN-test-only', 'lane': 'test-double'})
        self.prov['apk_install'] = dict(program=self.pin(HERE / 'apk_provider.py'),
                                      common=self.pin(HERE / 'provider_common.py'),
                                      executor=self.pin(self.exe), entry=self.pin(self.entry),
                                      manifest=self.pin(self.manifest), input_root=str(self.input_root),
                                      keys='alpha,bravo')
        self.dep = {'schema': 'demo-restore-deployment/v1', 'execution_enabled': True,
                    'providers': [self.prov]}

    def pin(self, path):
        return {'path': str(path), 'sha256': sha(path)}

    def invoke(self, program='apk_provider.py', serial=SERIAL):
        seal = self.root / 'seal.json'
        dep = self.root / 'deployment.json'
        seal.write_text(json.dumps(self.seal))
        dep.write_text(json.dumps(self.dep))
        self.state_path.write_text(json.dumps(self.state))
        env = dict(os.environ, PROVIDER_TEST_STATE=str(self.state_path),
                   PROVIDER_TEST_EVENTS=str(self.events_path), PYTHONDONTWRITEBYTECODE='1')
        return subprocess.run([sys.executable, str(HERE / program), '--seal', str(seal),
                               '--serial', serial, '--deployment', str(dep), '--out', str(self.root / 'out')],
                              env=env, capture_output=True, text=True, timeout=20)

    def events(self, kind=None):
        events = [json.loads(line) for line in self.events_path.read_text().splitlines()] if self.events_path.exists() else []
        return [e for e in events if kind is None or e['kind'] == kind]

    def assert_ok(self, result):
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def make_delta(self, key='bravo'):
        app = next(a for a in self.apps if a['key'] == key)
        self.state['hashes'][app['apk_path']] = 'd' * 64

    def make_missing(self, key='bravo'):
        app = next(a for a in self.apps if a['key'] == key)
        self.state['hashes'].pop(app['apk_path'], None)
        self.state['packages'].pop(app['package'], None)

    def test_existing_version_drift_refuses(self):
        self.state['packages'][self.apps[1]['package']] = 99
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_unknown_bms_response_refuses(self):
        self.make_missing()
        self.state['unknown_bms'] = True
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_disabled_executes_no_board_or_install(self):
        self.dep['execution_enabled'] = False
        self.assert_ok(self.invoke('u13_provider.py'))
        self.assertEqual(self.events(), [])
        self.assertFalse((self.root / 'out').exists())

    def test_self_pin_refuses_before_board(self):
        self.prov['apk_install']['program']['sha256'] = '0' * 64
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events(), [])

    def test_executor_drift_refuses_before_board(self):
        self.exe.write_text(FAKE_EXECUTOR + '\n# drift\n')
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events(), [])

    def test_u13_ready_baseline_skips_replay_and_dispatches_apk(self):
        self.assert_ok(self.invoke('u13_provider.py'))
        receipt = json.loads((self.root / 'out/receipt.json').read_text())
        self.assertFalse(receipt['replay_executed'])
        self.assertFalse(receipt['installer_executed'])
        self.assertEqual(receipt['base_status'], 'verified-existing-skip')
        self.assertEqual(receipt['apk_rc'], 0)
        self.assertTrue((self.root / 'out/apk/receipt.json').is_file())
        self.assertEqual(self.events('install'), [])

    def test_u13_missing_mount_refuses_before_apk_dispatch(self):
        self.state['mounts'] = '\n'.join(self.state['mounts'].splitlines()[:-1])
        self.assertNotEqual(self.invoke('u13_provider.py').returncode, 0)
        receipt = json.loads((self.root / 'out/receipt.json').read_text())
        self.assertEqual(receipt['missing_mounts'], ['/system/test-mount-55'])
        self.assertFalse((self.root / 'out/apk').exists())
        self.assertEqual(self.events('install'), [])

    def test_existing_apk_hash_drift_refuses(self):
        self.make_delta()
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_real_install_rc7_is_saved_and_batch_stops(self):
        self.make_missing('alpha')
        self.make_missing('bravo')
        self.state['install_rc'] = 7
        result = self.invoke()
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual([e['key'] for e in self.events('install')], ['alpha'])
        receipt = json.loads((self.root / 'out/receipt.json').read_text())
        def find_rc(obj):
            if isinstance(obj, dict):
                return obj.get('return_code') == 7 or any(find_rc(v) for v in obj.values())
            return isinstance(obj, list) and any(find_rc(v) for v in obj)
        self.assertTrue(find_rc(receipt), receipt)

    def test_missing_package_and_apk_installs_only_missing_key(self):
        app = self.apps[1]
        del self.state['packages'][app['package']]
        del self.state['hashes'][app['apk_path']]
        self.assert_ok(self.invoke())
        self.assertEqual([e['key'] for e in self.events('install')], ['bravo'])

    def test_generic_bms_absence_with_present_apk_refuses(self):
        del self.state['packages'][self.apps[1]['package']]
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_local_apk_drift_never_installs(self):
        self.make_missing('alpha')
        (self.input_root / 'bravo.apk').write_bytes(b'changed')
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_common_pin_drift_refuses_before_board(self):
        self.prov['apk_install']['common']['sha256'] = '0' * 64
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events(), [])

    def test_u13_self_pin_refuses_before_board(self):
        self.prov['program']['sha256'] = '0' * 64
        self.assertNotEqual(self.invoke('u13_provider.py').returncode, 0)
        self.assertEqual(self.events(), [])

    def test_u13_executor_drift_refuses_before_board(self):
        self.exe.write_text(FAKE_EXECUTOR + '\n# drift\n')
        self.assertNotEqual(self.invoke('u13_provider.py').returncode, 0)
        self.assertEqual(self.events(), [])

    def use_actual_missing_entry(self):
        entry = HERE / 'missing_apk_entry.py'
        self.assertTrue(entry.is_file(), 'actual missing-only entry required: ' + str(entry))
        self.prov['apk_install']['entry'] = self.pin(entry)

    def test_actual_missing_install_one_success_via_standard_argv(self):
        self.use_actual_missing_entry()
        self.make_missing('bravo')
        self.assert_ok(self.invoke())
        self.assertEqual([e['key'] for e in self.events('bm_install')], ['bravo'])
        self.assertEqual(self.events('install'), [], 'fake install entry must not run')
        record_path = self.root / 'out/bravo/record.json'
        record = json.loads(record_path.read_text())
        self.assertEqual(record['status'], 'installed')
        self.assertEqual(record['install']['return_code'], 0)
        self.assertTrue(record['install_only'])
        self.assertIn('finished_at', record)
        self.assertTrue((record_path.parent / 'install.txt').is_file())
        self.assertEqual(self.events('cold_stop'), [])
        self.assertNotIn(' -r ', self.events('bm_install')[0]['command'])

    def test_actual_missing_install_one_rc7_via_standard_argv(self):
        self.use_actual_missing_entry()
        self.make_missing('alpha')
        self.make_missing('bravo')
        self.state['install_rc'] = 7
        result = self.invoke()
        self.assertEqual(result.returncode, 7, result.stdout + result.stderr)
        self.assertEqual([e['key'] for e in self.events('bm_install')], ['alpha'])
        self.assertEqual(self.events('install'), [], 'fake install entry must not run')
        record = json.loads((self.root / 'out/alpha/record.json').read_text())
        self.assertEqual(record['status'], 'app_failed')
        self.assertEqual(record['install']['return_code'], 7)
        receipt = json.loads((self.root / 'out/receipt.json').read_text())
        self.assertEqual(receipt['results']['alpha']['record']['install']['return_code'], 7)
        self.assertFalse((self.root / 'out/bravo').exists())

    def test_transport_failure_never_installs(self):
        self.make_delta()
        self.state['transport_failed'] = True
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_cross_boot_never_installs(self):
        self.make_delta()
        self.state['boot'] = '00000000-0000-0000-0000-000000000000'
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual(self.events('install'), [])

    def test_cross_serial_refuses_before_board(self):
        self.assertNotEqual(self.invoke(serial='61b0657200000000000000000324012c').returncode, 0)
        self.assertEqual(self.events(), [])

    def test_batch_stop_never_touches_next_key(self):
        self.make_missing('alpha')
        self.make_missing('bravo')
        self.state['batch_stop'] = True
        self.assertNotEqual(self.invoke().returncode, 0)
        self.assertEqual([e['key'] for e in self.events('install')], ['alpha'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
