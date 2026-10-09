"""Execute the actual .sh CLI with known seal/observation pairs, never a board."""
import copy
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]
SERIAL='61b0657200000000000000000324012c'
RUNTIME='/system/android/lib64/liboh_android_runtime.so'
BOOT='/system/android/framework/arm64/boot.art'
INSTALL='/system/lib64/libinstalls.z.so'
APK='/data/app/el1/bundle/public/org.demo/android/base.apk'

def fixture():
 s={'schema':'demo-seal/v1','serial':SERIAL,'files':{'runtime':{RUNTIME:'a'*64},'boot':{BOOT:'b'*64},'overlays':{},'installation':{INSTALL:'c'*64}},'system_params':{'const.ohos.fullname':'OpenHarmony-6.1.0.31'},'packages':[{'package':'org.demo','version_code':3,'apk_path':APK,'apk_sha256':'d'*64}],'inventories':[{'patterns':['/system/android/lib64/*.so'],'paths':[RUNTIME]}]}
 o={'serial':SERIAL,'boot_before':'boot-known','boot_after':'boot-known','files':{RUNTIME:'a'*64,BOOT:'b'*64,INSTALL:'c'*64,APK:'d'*64},'system_params':dict(s['system_params']),'packages':{'org.demo':{'version_code':'3'}},'inventories':[[RUNTIME]],'errors':[]}
 return s,o

class SelfcheckTests(unittest.TestCase):
 def run_cli(self,change=None):
  seal,obs=fixture()
  if change:change(seal,obs)
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);(d/'seal.json').write_text(json.dumps(seal));(d/'obs.json').write_text(json.dumps(obs))
   env=dict(os.environ);env['PATH']=str(d)+os.pathsep+env['PATH']
   # Any accidental transport call makes this actual CLI known answer fail.
   for name in ('orb','hdc','mac'):
    p=d/name;p.write_text('#!/bin/sh\necho unexpected-transport >&2\nexit 97\n');p.chmod(0o755)
   r=subprocess.run(['bash',str(REPO/'scripts/lab/demo_selfcheck.sh'),'--seal',str(d/'seal.json'),'--serial',SERIAL,'--observed',str(d/'obs.json'),'--out',str(d/'result.json')],env=env,capture_output=True,text=True)
   result=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else None
   return r,result
 def test_all_equal_offline_not_live_pass(self):
  r,d=self.run_cli();self.assertEqual(r.returncode,0);self.assertEqual(d['status'],'OFFLINE_MATCH');self.assertEqual(d['lock_operations'],0);self.assertNotIn('unexpected-transport',r.stderr)
 def test_drift_names_path_and_two_shas(self):
  r,d=self.run_cli(lambda s,o:o['files'].update({RUNTIME:'e'*64}));self.assertEqual(r.returncode,1);self.assertIn('DRIFT '+RUNTIME+' expected='+'a'*64+' actual='+'e'*64,r.stdout)
 def test_absent_component_rejected(self):
  r,_=self.run_cli(lambda s,o:o['files'].pop(BOOT));self.assertEqual(r.returncode,1);self.assertIn(BOOT,r.stdout)
 def test_changed_package_and_apk_rejected(self):
  def c(s,o):o['packages']['org.demo']['version_code']='4';o['files'][APK]='e'*64
  r,_=self.run_cli(c);self.assertEqual(r.returncode,1);self.assertIn('package:org.demo:versionCode expected=3 actual=4',r.stdout);self.assertIn(APK,r.stdout)
 def test_changed_system_rejected(self):
  r,_=self.run_cli(lambda s,o:o['system_params'].update({'const.ohos.fullname':'other'}));self.assertEqual(r.returncode,1)
 def test_boot_changed_rejected(self):
  r,_=self.run_cli(lambda s,o:o.update(boot_after='new-boot'));self.assertEqual(r.returncode,1)
 def test_wrong_serial_rejects_before_transport(self):
  r,d=self.run_cli(lambda s,o:s.update(serial='bad'));self.assertEqual(r.returncode,2);self.assertIsNone(d)
 def test_unsafe_path_rejects_before_transport(self):
  r,_=self.run_cli(lambda s,o:s['files']['overlays'].update({'/tmp/x;reboot':'a'*64}));self.assertEqual(r.returncode,2)
 def test_added_inventory_member_rejected(self):
  r,_=self.run_cli(lambda s,o:o['inventories'][0].append('/system/android/lib64/extra.so'));self.assertEqual(r.returncode,1)
 def test_incomplete_seal_rejected(self):
  r,_=self.run_cli(lambda s,o:s['files'].pop('installation'));self.assertEqual(r.returncode,2)
 def test_unknown_read_errors_not_pass(self):
  r,_=self.run_cli(lambda s,o:o.update(errors=['lost remote status marker']));self.assertEqual(r.returncode,1)

class TransportKnownAnswers(unittest.TestCase):
 def live_cli(self,lost=False):
  seal,obs=fixture()
  with tempfile.TemporaryDirectory() as td:
   d=Path(td);tools=d/'westlake-inputs/tools';tools.mkdir(parents=True);boards=d/'westlake-harness/knowledge';boards.mkdir(parents=True)
   (boards/'boards.json').write_text(json.dumps({'boards':[{'serial':SERIAL,'kind':'oh','label':'61b'}]}))
   (d/'seal.json').write_text(json.dumps(seal));(d/'obs.json').write_text(json.dumps(obs));log=d/'commands.jsonl'
   fake=tools/'hdc_mac.sh'
   fake.write_text('#!/usr/bin/env python3\n'+r"""import json,os,re,sys
from pathlib import Path
command=sys.argv[-1];plain=command.split('; demo_rc=')[0]
with Path(os.environ['FAKE_LOG']).open('a') as f:f.write(json.dumps(plain)+'\n')
o=json.loads(Path(os.environ['FAKE_OBS']).read_text())
if plain=='cat /proc/sys/kernel/random/boot_id':print(o['boot_before'])
elif plain.startswith('sha256sum '):
 paths=plain.split()[1:]
 if '*' in plain:paths=o['inventories'][0]
 for p in paths:print(o['files'][p]+'  '+p)
elif plain.startswith('param get '):print(o['system_params'][plain.split()[-1]])
elif plain.startswith('bm dump -n '):print('bm dump header\n'+json.dumps({'name':'org.demo','versionCode':3}))
else:raise SystemExit('non-read command')
if os.environ.get('FAKE_LOST')!='yes':print(re.search(r'__DEMO_READ_RC_[0-9a-f]+__',command).group(0)+'0')
""")
   fake.chmod(0o755)
   bindir=d/'bin';bindir.mkdir();orb=bindir/'orb';orb.write_text('#!/bin/sh\nshift 3\nexec "$@"\n');orb.chmod(0o755)
   env=dict(os.environ,WORKSPACES=str(d),FAKE_LOG=str(log),FAKE_OBS=str(d/'obs.json'),FAKE_LOST='yes' if lost else 'no');env['PATH']=str(bindir)+os.pathsep+env['PATH']
   r=subprocess.run(['bash',str(REPO/'scripts/lab/demo_selfcheck.sh'),'--seal',str(d/'seal.json'),'--serial',SERIAL,'--out',str(d/'result.json')],capture_output=True,text=True,env=env)
   result=json.loads((d/'result.json').read_text()) if (d/'result.json').exists() else None
   commands=[json.loads(l) for l in log.read_text().splitlines()] if log.exists() else []
   return r,result,commands
 def test_transport_parses_bm_and_hashes_readonly(self):
  r,d,commands=self.live_cli();self.assertEqual(r.returncode,0,r.stderr+r.stdout);self.assertEqual(d['status'],'PASS');self.assertGreater(len(commands),3)
  self.assertTrue(all(c.startswith(('cat /proc/','sha256sum /','param get ','bm dump -n ')) for c in commands))
 def test_lost_remote_status_fails_closed(self):
  r,d,_=self.live_cli(True);self.assertEqual(r.returncode,1,r.stderr+r.stdout);self.assertEqual(d['status'],'FAIL');self.assertIn('status marker unavailable',r.stdout)

if __name__=='__main__':unittest.main()
