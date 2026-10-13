"""Incremental isolated checks; no subprocess/HDC/VM/SSH."""
import hashlib,importlib.util,json,sys,tempfile,time,types,unittest
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('interaction',HERE/'interaction_runner.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
STAT=lambda pid,ppid,birth: str(pid)+' (boat) '+' '.join(['S',str(ppid)]+['0']*17+[str(birth)])+'\n'
WMS=lambda pid,focus: 'com.Unity3d.BoatAtta 0 '+str(pid)+' 33 1001 1 0 -1 0 [ 0 0 1920 1200 ] [ 0 0 ]\nFocus window: '+str(focus)+'\n'
# Minimal JPEG header fixture is explicitly synthetic, never a UI verdict.
JPEG=b'\xff\xd8\xff\xc0\x00\x11\x08\x04\xb0\x07\x80'+b'\x00'*10

class FakeBoard:
 def __init__(self,serial,hdc,lock,owner,out):self.boot='9f5af7c8-d359-4c25-99c6-63206b50cf0a';self.commands=[]
 def command(self,argv,timeout=60):return 0,'fake transport'
 def ready(self):pass
 def send(self,*args):self.commands.append(('send',args))
 def shell(self,cmd,required=True,timeout=60):
  self.commands.append(cmd)
  if cmd.startswith('bm dump'):return 0,'bundle'
  if cmd=='ps -A -o PID,PPID,UID,NAME':return 0,'processes'
  if cmd=='cat /proc/5000/stat':return 0,STAT(5000,1000,50)
  if cmd=='cat /proc/1000/stat':return 0,STAT(1000,1,10)
  if cmd=='cat /proc/5000/status':return 0,'Uid:\t20011300\t20011300\t20011300\t20011300\n'
  if cmd=='readlink /proc/1000/exe':return 0,'/system/bin/appspawn-x'
  if cmd.startswith('hidumper'):return 0,WMS(5000,self.focus)
  if cmd.startswith('stat -c'):return 0,'1:2'
  if cmd.endswith('/owner') and cmd.startswith('cat '):return 0,'cx-t0'
  if cmd.startswith('sha256sum '):
   p=cmd[len('sha256sum '):]
   if p.endswith('/android/base.apk'):return 0,'8dc636657cccdad1310332928b8cc8eca7da03f4b528de6fb0c63118173e0444  '+p
   if p.endswith('/keeper.sh'):return 0,r.DONORS['keeper'][1]+'  '+p
   target=p.removeprefix('/proc/5000/root');return 0,('0'*64 if self.bad_asset else r.ASSETS[target])+'  '+p
  return 0,'captured raw log'
 focus=33;bad_asset=False

class Checks(unittest.TestCase):
 def setUp(self):
  tmp=tempfile.TemporaryDirectory(prefix='boat-offline-');self.addCleanup(tmp.cleanup);self.out=Path(tmp.name)/'fresh';self.out.mkdir()
  self.plan={'execution_enabled':True,'serial':'5cd1e3dd00000000000000000923012c','owner':'cx-t0','boot_id':'9f5af7c8-d359-4c25-99c6-63206b50cf0a','uid':20011300,'hdc':sys.executable,'max_runtime_seconds':240}
 def run_fake(self,bad=False,focus=33,expire_after_launch=False,missing_window=False):
  instances=[];clock=[0]
  def make(*a):
   x=FakeBoard(*a);x.bad_asset=bad;x.focus=focus
   if missing_window:
    raw=x.shell
    x.shell=lambda cmd,**kw: (0,'no WMS target') if cmd.startswith('hidumper') else raw(cmd,**kw)
   instances.append(x);return x
  def capture(b,remote,path):Path(path).write_bytes(JPEG);return {'sha256':hashlib.sha256(JPEG).hexdigest(),'path':str(path),'synthetic':True}
  def desktop(b,app,remote,out,rec):
   b.commands.append(('desktop_launch',app));rec['click_monotonic']=0
   if expire_after_launch:clock[0]=1000
  batch=types.SimpleNamespace(Board=make,parse_bundle=lambda *a:{'uid':20011300,'desktop_activity':r.ABILITY},processes=lambda x:[{'pid':5000,'ppid':1000,'uid':20011300}],capture=capture,desktop_launch=desktop)
  loader=types.SimpleNamespace(exec_module=lambda module:setattr(module,'B',batch))
  with patch.object(r.importlib.util,'spec_from_file_location',return_value=types.SimpleNamespace(loader=loader)),patch.object(r.importlib.util,'module_from_spec',return_value=types.SimpleNamespace()),patch.object(r.time,'sleep'),patch.object(r.time,'monotonic',side_effect=lambda:clock[0]):
   rc=r.run(self.plan,self.out,{'rehearsal':Path('fake-donor'),'keeper':Path('fake-keeper')})
  return rc,instances[0],json.loads((self.out/'record.json').read_text())
 def test_success_collects_five_exact_touches_without_ui_pass(self):
  rc,b,rec=self.run_fake();self.assertEqual(rc,0);self.assertFalse(rec['accepted']);self.assertEqual(rec['status'],'CAPTURED_PENDING_HUMAN');self.assertEqual([x['command'] for x in rec['inputs']],[x[1] for x in r.TOUCHES]);self.assertTrue(any(isinstance(c,tuple) and c[0]=='desktop_launch' for c in b.commands));self.assertFalse(any(isinstance(c,str) and any(x in c for x in ['aa start','kill ','kill -9','bm install','mount --bind','hilog -r']) for c in b.commands))
 def test_runtime_or_private_mismatch_rejects_all_touches_and_keeps_evidence(self):
  rc,b,rec=self.run_fake(bad=True);self.assertEqual(rc,2);self.assertEqual(rec['inputs'],[]);self.assertIn('mismatch',rec['error']);self.assertTrue((self.out/'hilog-final.txt').exists());self.assertIn('final',rec['images'])
 def test_wrong_focus_refuses_touch_preserves_before_and_raw_logs(self):
  rc,b,rec=self.run_fake(focus=29);self.assertEqual(rc,2);self.assertEqual(rec['inputs'],[]);self.assertIn('focus',rec['error']);self.assertIn('touch-1-before',rec['images']);self.assertTrue((self.out/'hilog-final.txt').exists())
 def test_true_target_window_is_pid_package_geometry_not_generic_scene(self):
  self.assertEqual(r.target_window(WMS(5000,33),5000)['window_id'],33)
  for text,pid in [(WMS(5000,33),6000),(WMS(5000,33).replace('com.Unity3d.BoatAtta','imehost0'),5000),(WMS(5000,33).replace('1920 1200','1200 1920'),5000)]:
   with self.assertRaises(ValueError):r.target_window(text,pid)
 def test_missing_wms_does_not_discard_timed_frames(self):
  rc,b,rec=self.run_fake(missing_window=True);self.assertEqual(rc,2);self.assertEqual(rec['inputs'],[])
  for tag in ['t15','t30','t45']:self.assertIn(tag,rec['images']);self.assertIn('wms_diagnostic_error',rec['images'][tag])
  self.assertIn('touch-1-before',rec['images'])
 def test_cleanup_has_own_budget_after_interaction_timeout(self):
  rc,b,rec=self.run_fake(expire_after_launch=True);self.assertEqual(rc,2);self.assertIn('deadline',rec['error']);self.assertIn('final',rec['images']);self.assertTrue((self.out/'hilog-final.txt').exists());self.assertTrue(rec['cleanup']['keeper_stop_requested'])
 def test_disabled_wrong_boot_wrong_owner_and_runner_pin_refuse(self):
  auth={'approved_by':'outer(codex)','action':'boat-interaction','plan_sha256':'p','runner_sha256':r.sha(r.__file__),'serial':self.plan['serial'],'owner':self.plan['owner'],'boot_id':self.plan['boot_id'],'expires_epoch':time.time()+500,'spare_board_authorized':True}
  r.admit(self.plan,auth,'p')
  for change in [{'boot_id':'wrong'},{'owner':'foreign'},{'runner_sha256':'0'*64},{'expires_epoch':0}]:
   with self.assertRaises(ValueError):r.admit(self.plan,{**auth,**change},'p')
  with self.assertRaises(ValueError):r.admit({**self.plan,'execution_enabled':False},auth,'p')
 def test_pid_birth_guard_tuple_changes_when_birth_changes(self):
  b=FakeBoard(None,None,None,None,None);old=r.proc_identity(b,5000,20011300);self.assertEqual(old['birth'],50)
  original=b.shell
  def changed(cmd,**kw):return (0,STAT(5000,1000,51)) if cmd=='cat /proc/5000/stat' else original(cmd,**kw)
  b.shell=changed;self.assertNotEqual(r.proc_identity(b,5000,20011300),old)
 def test_real_history_frame_dimensions_and_donor_pins(self):
  self.assertEqual(r.jpeg_size(r.WS.parent/'00.Workspace-games-ad1ab0a7/var/state/reproduce-boat-attack-apk/20260924T080718Z-quick/ready.jpeg'),(1920,1200));self.assertEqual(set(r.donors()),set(r.DONORS))

if __name__=='__main__':unittest.main(verbosity=2)
