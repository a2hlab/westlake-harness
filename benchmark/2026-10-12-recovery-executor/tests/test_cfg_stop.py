import hashlib,importlib.util,json,os,shutil,subprocess,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
D=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('executor',D/'executor.py');e=importlib.util.module_from_spec(spec);spec.loader.exec_module(e)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ShellDevice:
 def __init__(self,tmp,fail=False,initial='ro'):
  self.tmp=tmp;self.tools=tmp/'tools';self.tools.mkdir();self.mounts=tmp/'mounts';self.log=tmp/'mount.log';self.fail=fail
  self.mounts.write_text('dev / ext4 '+initial+' 0 0\n')
  for name,text in {'mount':'''#!/bin/bash
printf '%s\\n' "$*" >> "$CFG_TEST_LOG"
case "$*" in '-o rw,remount /') echo 'dev / ext4 rw 0 0' > "$CFG_TEST_MOUNTS";; '-o ro,remount /') echo 'dev / ext4 ro 0 0' > "$CFG_TEST_MOUNTS";; *) exit 4;; esac
''','chown':'#!/bin/bash\nexit 0\n','chcon':'#!/bin/bash\nexit 0\n','cp':'#!/bin/bash\n[ "$CFG_TEST_FAIL" != 1 ] || exit 44\nexec /bin/cp "$@"\n'}.items():(self.tools/name).write_text(text);(self.tools/name).chmod(0o755)
  self.scripts=[]
 def probe(self,p):
  p=Path(p)
  if not p.exists():return {'exists':False}
  return dict(exists=True,sha256=sha(p),mode='550',uid=0,gid=0,label='u:object_r:system_etc_file:s0')
 def send(self,name,source,target):Path(target).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
 def shell(self,name,script):
  self.scripts.append(script);script=script.replace('/proc/mounts',str(self.mounts))
  x=subprocess.run(['/bin/bash','-c',script],capture_output=True,text=True,env={**os.environ,'PATH':str(self.tools)+':/usr/bin:/bin','CFG_TEST_LOG':str(self.log),'CFG_TEST_MOUNTS':str(self.mounts),'CFG_TEST_FAIL':'1' if self.fail else '0'})
  if x.returncode:raise ValueError('real shell rc='+str(x.returncode))
  return x.stdout
class CFGTests(unittest.TestCase):
 def case(self,fail,initial='ro'):
  with tempfile.TemporaryDirectory() as t:
   tmp=Path(t);source=tmp/'source.cfg';source.write_text('new cfg\n');cfg=tmp/'target.cfg';cfg.write_text('original cfg\n');dev=ShellDevice(tmp,fail,initial)
   row=dict(target=str(cfg),source=str(source),sha256=sha(source),after={'mode':'550','uid':0,'gid':0,'label':'u:object_r:system_etc_file:s0'})
   with patch.object(e,'CFG',str(cfg)),patch.object(e,'ROOT',str(tmp/'candidate')):
    if fail:
     with self.assertRaises(ValueError):e.place(dev,row)
    else:e.place(dev,row)
   self.assertEqual(dev.mounts.read_text(),'dev / ext4 '+initial+' 0 0\n')
   self.assertEqual(cfg.read_text(),'original cfg\n' if fail else 'new cfg\n')
   if initial=='ro':self.assertEqual(dev.log.read_text().splitlines(),['-o rw,remount /','-o ro,remount /'])
   else:self.assertFalse(dev.log.exists())
 def test_success_restores_ro_and_atomic_bytes(self):self.case(False)
 def test_copy_failure_restores_ro_preserves_original(self):self.case(True)
 def test_original_rw_is_not_changed_to_ro(self):self.case(False,'rw')

class GuardDevice:
 def __init__(self,fail=False,reused=False):self.fail=fail;self.reused=reused;self.calls=[];self.files={};self.boot='11111111-1111-1111-1111-111111111111'
 def probe(self,p):return self.files.get(p,{'exists':p.endswith('/lock/owner')})
 def shell(self,name,script):
  self.calls.append((name,script))
  if name in ['guardian-lock-read','guardian-lock-exact']:return '123 456 '+self.boot
  if name=='guardian-exact-argv-birth':
   if self.fail:raise ValueError('PID/birth/NUL argv identity rejected')
   self.guard=script;return ''
  if name=='guardian-exit-read':return 'GONE' if not self.reused else 'ALIVE'
  if name=='rollback-stop-create':return ''
  raise AssertionError(name)
class StopTests(unittest.TestCase):
 def test_exact_guard_then_cooperative_flags_no_signal(self):
  dev=GuardDevice();e.request_cooperative_stop(dev,{'boot_id':dev.boot});names=[n for n,_ in dev.calls];self.assertLess(names.index('guardian-exact-argv-birth'),names.index('rollback-stop-create'));self.assertIn('sha256sum /proc/$p/cmdline',dev.guard);self.assertEqual(dev.guard.count('"${20}"'),2);self.assertNotIn('strings',dev.guard);self.assertNotIn('kill',dev.guard);self.assertNotIn('tr ',dev.guard)
 def test_identity_mismatch_no_stop_write(self):
  dev=GuardDevice(True)
  with self.assertRaises(ValueError):e.request_cooperative_stop(dev,{'boot_id':dev.boot})
  self.assertFalse(any(n=='rollback-stop-create' for n,_ in dev.calls))
 def test_no_exit_preserves_app_and_refuses_restore(self):
  dev=GuardDevice(reused=True)
  with patch.object(e.time,'sleep',lambda _:None):
   with self.assertRaisesRegex(ValueError,'no signals'):e.request_cooperative_stop(dev,{'boot_id':dev.boot})
  self.assertFalse(any('kill' in script for _,script in dev.calls));self.assertEqual(sum(n=='guardian-exit-read' for n,_ in dev.calls),20)
if __name__=='__main__':unittest.main(verbosity=2)
