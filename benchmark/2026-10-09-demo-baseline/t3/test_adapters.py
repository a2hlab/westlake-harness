"""Known answers for install-once/launch-only without HDC."""
import importlib.util,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
p=Path(__file__).with_name('batch_adapter.py');s=importlib.util.spec_from_file_location('adapter',p);a=importlib.util.module_from_spec(s);s.loader.exec_module(a)
class Arguments(unittest.TestCase):
 def test_expired_cutoff_returns_without_loading_or_device_access(self):
  with patch.object(a.time,'time',return_value=100),patch.object(a.b,'main') as run,patch.object(a.b,'load_apps') as load:
   self.assertEqual(a.main(['--serial','5cd1e3dd00000000000000000923012c','--stop-new-keys-at','99']),0)
   run.assert_not_called();load.assert_not_called()
 def test_no_reinstall_or_uninstall_on_launch(self):
  args=a.launch_args(['--execute','--reinstall','--shots','5,20','--hilog'],20)
  self.assertNotIn('--reinstall',args);self.assertIn('--launch-only',args);self.assertEqual(args[args.index('--shots')+1],'5,20')
 def test_t10_arguments(self):
  args=a.launch_args(['--execute','--reinstall','--shots','5,20'],10);self.assertEqual(args[args.index('--shots')+1],'5,10');self.assertEqual(args[-2:],['--wait','10'])
 def test_approved_real_tiers_and_drift(self):
  import json,hashlib
  p=Path(__file__).with_name('shot-tiers-approved.json');rows=json.loads(p.read_text())['apps'];digest=hashlib.sha256(p.read_bytes()).hexdigest()
  for seconds in (10,20):
   row=next(r for r in rows if r['screenshot_seconds']==seconds)
   self.assertEqual(a.tier_seconds([row],p,digest),seconds)
  with self.assertRaises(ValueError):a.tier_seconds([rows[0]],p,'0'*64)
  with self.assertRaises(ValueError):a.tier_seconds([dict(rows[0],apk_sha256='0'*64)],p,digest)
 def test_install_replace_without_uninstall(self):
  class Board:
   serial='61b0657200000000000000000324012c'
   def __init__(self):self.calls=[]
   def shell(self,c,**kw):
    self.calls.append(c)
    return (0,'d'*64+'  /tmp/apk') if c.startswith('sha256sum') else (0,'install bundle successfully')
   def send(self,*args):self.calls.append('send')
  board=Board();app={'key':'demo','package':'org.demo','apk_sha256':'d'*64,'phase':'blocked'}
  with tempfile.TemporaryDirectory() as td,patch.object(a.b,'resolve_input',return_value=dict(app,apk='fake.apk')),patch.object(a.b,'parse_bundle',return_value={'queryable':True,'uid':20000001}),patch.object(a.b,'cold_stop',return_value=True) as stop:
   r=a.install_one(board,app,Path(td),Path(td)/'app','/data/local/tmp/demo')
   self.assertEqual(r['status'],'installed');self.assertEqual(stop.call_count,2);self.assertTrue(any(c.startswith('bm install -r -p ') for c in board.calls));self.assertFalse(any('uninstall' in c for c in board.calls))
 def test_failed_install_never_launches_stale_app(self):
  import json,os
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);manifest=root/'apps.json';manifest.write_text(json.dumps({'apps':[{'key':'demo','package':'org.demo','apk_sha256':'d'*64,'phase':'blocked'}]}));index=root/'index.json';index.write_text(json.dumps({'demo':{'apk_sha256':'d'*64,'success':False}}))
   with patch.dict(os.environ,{'DEMO_T3_MODE':'launch','DEMO_INSTALL_INDEX':str(index)}),patch.object(a.b,'main') as launch:
    rc=a.main(['--serial','61b0657200000000000000000324012c','--manifest',str(manifest),'--keys','demo','--out',str(root/'out')]);self.assertEqual(rc,1);launch.assert_not_called();records=list((root/'out').glob('*/*/*/record.json'));self.assertEqual(len(records),1);self.assertIn('stale',json.loads(records[0].read_text())['error'])
class AbilityFallback(unittest.TestCase):
 def exercise(self,sha='d'*64,reason=None):
  import json
  pin={'package':'org.demo','apk_sha256':'d'*64,'ability':'org.demo.Main'}
  if reason is not None:pin['reason']=reason
  class Board:
   def __init__(self):self.calls=[]
   def shell(self,c,**kw):self.calls.append(c);return 0,'start ability successfully'
  board=Board();app=dict(pin,launch_activity=pin['ability']);app['apk_sha256']=sha
  rec={'key':'demo','bms':{'queryable':True,'desktop_activity':pin['ability']}}
  with tempfile.TemporaryDirectory() as td:
   out=Path(td);(out/'bundle.txt').write_text(json.dumps({'hapModuleInfos':[{'abilityInfos':[{'name':pin['ability'],'enabled':True,'visible':True}]}]}))
   original=a.install_ability_overrides({'demo':pin})
   try:a.b.desktop_launch(board,app,'remote',out,rec)
   finally:a.b.desktop_launch=original
  return board,rec
 def test_exact_pinned_ability_and_clock(self):
  board,r=self.exercise();self.assertEqual(board.calls[0],'aa start -b org.demo -a org.demo.Main');self.assertEqual(r['launch_method'],'ability-fallback');self.assertFalse(r['clicked']);self.assertEqual(r['capture_clock_origin'],'aa-start-success-return')
 def test_changed_apk_rejected(self):
  with self.assertRaises(a.b.AppFailure):self.exercise('0'*64)
 def test_continuation_reason_does_not_claim_capture01_approval(self):
  board,r=self.exercise(reason='t3 continuation: exact desktop icon absent in capture-05')
  self.assertEqual(r['fallback_reason'],'t3 continuation: exact desktop icon absent in capture-05')
  self.assertEqual(board.calls[0],'aa start -b org.demo -a org.demo.Main')

class SupervisorGuards(unittest.TestCase):
 def check(self,serial):
  import json,subprocess,sys
  with tempfile.TemporaryDirectory() as td:
   root=Path(td);plan=root/'plan.json';plan.write_text(json.dumps({'serial':serial,'execution_enabled':False,'out':str(root/'runner')}))
   r=subprocess.run([sys.executable,str(Path(__file__).with_name('demo_board_run.py')),str(plan),'--detach'],capture_output=True,text=True)
   self.assertNotEqual(r.returncode,0);self.assertFalse((root/'runner').exists());self.assertFalse((root/'runner.board-run.log').exists());return r
 def test_full_serial_disabled_refuses_before_detach(self):
  r=self.check('61b0657200000000000000000324012c');self.assertIn('disabled; no lock taken',r.stderr)
 def test_short_serial_refuses_before_detach(self):
  r=self.check('61b0657200000000000000324012c');self.assertIn('whitelist',r.stderr)
if __name__=='__main__':unittest.main()
