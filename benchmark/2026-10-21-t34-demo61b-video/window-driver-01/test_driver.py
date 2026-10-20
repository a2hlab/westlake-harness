import copy,json,subprocess,sys,tempfile,unittest,os
from pathlib import Path
from types import SimpleNamespace
import common,recover_driver
MAIN=Path(os.environ.get('T34_MAIN',str(common.HERE.parents[2]))).resolve()
BOUND=MAIN/common.REL/'bound-data-01'

def restored_text(parent,fresh):
 lines=[]
 for root in [common.RT,f'/proc/{parent["pid"]}/root/data/local/tmp/asx']:
  lines += [h+'  '+root+'/'+rel for rel,h in recover_driver.ORIGINAL.items()]
 lines += [h+'  '+p for p,h in fresh['controls'].items()]
 lines += [fresh['cfg_sha256']+'  '+recover_driver.CFG,fresh['hap_sha256']+'  '+recover_driver.HAP,'PHYSICAL_COMPAT_ABSENT','PRIVATE_COMPAT_ABSENT','ScreenOffTime: Timeout=30000ms  OverrideTimeout=86400000ms','DEBUG_PROCESS_RC=0','Get parameter "debug.ttplayer.log.enable" fail! errNum is:106!','RESTORE_IDENTITY_MATCH']
 return '\n'.join(lines)+'\n'

class FakeRecovery:
 def __init__(self,tmp,wrong=False):
  self.w=tmp;self.out=tmp/'out';self.out.mkdir();self.repo=MAIN;self.holder='inner(cc-video) 1 2026-10-21T00:00:00+0800';self.start=1;self.actions=[]
  self.fresh=json.loads((BOUND/'fresh.json').read_text());(tmp/'data').mkdir();common.dump(tmp/'data/fresh.json',self.fresh)
  (tmp/'data/run61b.before.reference.sh').write_bytes((BOUND/'run61b.before.reference.sh').read_bytes())
  self.origin={'fresh_data_sha256':common.digest(tmp/'data/fresh.json')};common.dump(tmp/'rollback-admission.json',{'boot':'old'})
  self.op=['fixture-rollback'];self.cv=common.load_module('test_cv',MAIN/common.REL/'candidate-view-01/prepare.py')
  self.parent={'pid':4992,'birth':5694,'uid':0,'ppid':1,'exe_sha256':self.cv.EXE,'mnt':'mnt:[4026533005]'}
  self.text=restored_text(self.parent,self.fresh)
  if wrong:self.text=self.text.replace(recover_driver.ORIGINAL['liboh_adapter_bridge.so']+'  /proc/',('0'*64)+'  /proc/')
 def boot(self):return 'old'
 def held(self):pass
 def raw(self,tag,argv,to=30,allow_failure=False):
  self.actions.append(tag)
  if tag=='rollback':return 0,b'PHYSICAL_FILES_RESTORED_REQUIRES_FRESH_BOOT',b''
  if tag=='held-after':return 1,b'',b''
  return 0,b'',b''
 def reboot(self,old):return 'new'
 def ui(self,boot,tag,action,seconds):self.actions.append('ui-'+action)
 def discover(self,boot,include_child=True):
  assert not include_child;self.actions.append('discover');return self.parent,{},None,30,'mnt:[4026531841]'
 def shell(self,tag,body,to=35):self.actions.append('verify');self.script=body;return True,self.text

class Tests(unittest.TestCase):
 def test_timeout_preserves_bytes_and_rc124(self):
  with tempfile.TemporaryDirectory() as t:
   out=Path(t)/'receipt';rc,body,err=common.run_record(out,[sys.executable,'-c','import sys,time;sys.stdout.buffer.write(b"\\xffraw");sys.stdout.flush();time.sleep(2)'],.15)
   self.assertEqual(rc,124);self.assertEqual((out/'stdout').read_bytes(),b'\xffraw');self.assertEqual((out/'rc').read_text(),'124\n')
   with self.assertRaises(FileExistsError):common.run_record(out,['true'],1)
 def test_child_renamed_is_selected_but_ambiguous_unknown(self):
  r={'pid':7043,'ppid':4992,'uid':20011206,'name':'com.ss.android.article.news'}
  self.assertEqual(common.select_child([r],4992),7043)
  self.assertIsNone(common.select_child([r,{**r,'pid':7044}],4992));self.assertIsNone(common.select_child([{**r,'ppid':5}],4992))
 def test_restore_order_and_real_generated_compat_gate(self):
  with tempfile.TemporaryDirectory() as t:
   d=FakeRecovery(Path(t));recover_driver.restore(d)
   self.assertLess(d.actions.index('ui-launch'),d.actions.index('ui-power'));self.assertLess(d.actions.index('ui-power'),d.actions.index('verify'));self.assertLess(d.actions.index('verify'),d.actions.index('unlock'))
   self.assertEqual(subprocess.run(['sh','-n'],input=d.script.encode(),capture_output=True).returncode,0)
   present=Path(t)/'present';present.write_bytes(b'present')
   line=next(x for x in d.script.splitlines() if x.startswith('test ! -e '))
   # Execute the exact generated test operator against a real present file.
   line=line.replace(common.q(common.RT+'/libopensles_android_compat.so'),common.q(str(present)))
   result=subprocess.run(['sh','-c',line+'\necho FALSE_ABSENT'],capture_output=True)
   self.assertEqual(result.returncode,81);self.assertNotIn(b'FALSE_ABSENT',result.stdout)
 def test_bad_private_hash_never_unlocks(self):
  with tempfile.TemporaryDirectory() as t:
   d=FakeRecovery(Path(t),True)
   with self.assertRaises(AssertionError):recover_driver.restore(d)
   self.assertNotIn('unlock',d.actions)
 def test_total_gate_negative_fields(self):
  with tempfile.TemporaryDirectory() as t:
   d=FakeRecovery(Path(t));base=d.text
   mutations=[base.replace('PRIVATE_COMPAT_ABSENT','PRIVATE_COMPAT_PRESENT'),base.replace('OverrideTimeout=86400000','OverrideTimeout=10000'),base.replace('DEBUG_PROCESS_RC=0','DEBUG_PROCESS_RC=1'),base.replace('errNum is:106!','errNum is:105!'),base.replace(d.fresh['cfg_sha256'],'0'*64),base.replace(d.fresh['hap_sha256'],'0'*64),base.replace(next(iter(d.fresh['controls'].values())),'0'*64)]
   for text in mutations:
    with self.subTest(text=text[-150:]):
     with self.assertRaises(AssertionError):recover_driver.verify_text(text,d.parent,'new',d.fresh['controls'],d.fresh['cfg_sha256'],d.fresh['hap_sha256'],0)
if __name__=='__main__':unittest.main()
