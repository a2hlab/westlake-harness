"""Actual wrapper subclass + pinned original BMS shell/raw_shell; transport fixture only."""
import argparse,datetime,json,re,subprocess,sys,tempfile,time,unittest
from pathlib import Path
import ui
ap=argparse.ArgumentParser();ap.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[2]);args,rest=ap.parse_known_args()
B=ui.load_bms(args.source_root);UI=ui.board_class(B)
class Cases(unittest.TestCase):
 def test_actual_class_awake_intent_and_recovery(self):
  rows=[]
  for case in ('success','lost_icon_reply','awake_failure','identity_drift','restore_after_child_parent_guardian_change','wrong_holder'):
   with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
    p=Path(d);calls=[];power_value={'timeout':10000,'override':10000};record={'selected_icon':{'center':[736,507]}}
    profile={'boot':'dcc12383-c47d-4a54-acf2-b437f44a3823','parent':{'pid':6101,'birth':16617},'guardian':{'pid':4016,'birth':3964},'holder':'outer(codex) 123 fixture'}
    class Fixture(UI):
     def command(self,argv,timeout=60):
      calls.append(argv)
      if argv==self.lock+['held',ui.SERIAL]:return 0,'outer(codex) 456 wrong' if case=='wrong_holder' else profile['holder']
      if argv==self.hdc+['list','targets']:return 0,ui.SERIAL
      text=argv[-1];marker=re.search(r'__BMS_REMOTE_RC_[0-9a-f]+__',text).group()
      guarded='/proc/6101/stat' in text
      rc=0;out=''
      if guarded and case in ('identity_drift','restore_after_child_parent_guardian_change'):rc=2
      elif 'cat /proc/sys/kernel/random/boot_id' in text and not guarded:out=profile['boot']
      elif 'uitest ' in text:
       power_value['override']=10000
       if 'uiInput click 736 507' in text and case=='lost_icon_reply':return 0,'lost remote marker'
      elif text.startswith('power-shell timeout -o '):
       if case=='awake_failure' and record.get('clicked'):raise B.BatchStop('awake command failed')
       power_value['override']=int(re.search(r'-o (\d+)',text).group(1))
      elif text.startswith('power-shell dump -s'):out=f"ScreenOffTime: Timeout={power_value['timeout']}ms OverrideTimeout={power_value['override']}ms"
      return 0,out+'\n'+marker+str(rc)+'\n'
    board=Fixture(ui.SERIAL,'fixture-hdc','bash fixture-lock','outer(codex)',p/'commands')
    board.profile=profile;board.profile_sha='fixture';board.state=p;board.boot=profile['boot'];board.action='launch';board.recovery=case=='restore_after_child_parent_guardian_change';board.original_power={'timeout':10000,'override':30000};board.record=record;board.record_path=p/'record.json'
    error=None
    try:
     if board.recovery:
      board.shell('power-shell timeout -o 30000');_,raw=board.shell('power-shell dump -s');self.assertEqual(ui.power(raw),board.original_power)
     else:
      board.shell('uitest uiInput keyEvent Home')
      board.shell('uitest dumpLayout -p /fixture/layout.json')
      board.shell('uitest uiInput click 736 507')
    except Exception as ex:error=str(ex)
    remote=[x[-1] for x in calls if len(x)>=4 and 'shell' in x]
    icons=[x for x in remote if 'uitest uiInput click 736 507' in x]
    if case=='success':
     self.assertIsNone(error);self.assertTrue(record['clicked']);self.assertEqual(len(record['awake_readbacks']),3);self.assertEqual(power_value['override'],86400000)
     before=len(icons)
     with self.assertRaises(FileExistsError):board.shell('uitest uiInput click 736 507')
     self.assertEqual(sum('uitest uiInput click 736 507' in x[-1] for x in calls),before)
    elif case=='lost_icon_reply':
     self.assertEqual(len(icons),1);self.assertFalse(record.get('clicked'));self.assertEqual(record['ui_calls'][-1]['result'],'unknown');self.assertTrue((p/'icon-dispatch.intent.json').exists())
    elif case in ('identity_drift','wrong_holder'):self.assertIsNotNone(error);self.assertFalse(record.get('clicked'))
    elif board.recovery:
     self.assertIsNone(error);self.assertFalse(any('/proc/6101/' in x or '/proc/4016/' in x or 'uitest ' in x for x in remote))
    elif case=='awake_failure':self.assertIsNotNone(error);self.assertTrue(record['clicked']);self.assertEqual(record['ui_calls'][-1]['remote_rc'],0)
    rows.append({'case':case,'icon_remote_dispatches':len(icons),'awake_readbacks':len(record.get('awake_readbacks',[])),'clicked':record.get('clicked',False),'error':error,'device_calls':0})
  print(json.dumps(rows,indent=2))
 def test_original_transport_timeout_retains_partial_streams(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);obj=UI(ui.SERIAL,'fixture-hdc','bash fixture-lock','outer(codex)',root/'commands');obj.deadline=time.monotonic()+5;obj.wall_deadline=time.time()+5
   calls=[];old=B.subprocess.run
   def expired(argv,**kwargs):
    calls.append(argv);raise subprocess.TimeoutExpired(argv,1,output=b'partial-out\x00',stderr=b'partial-err')
   try:
    B.subprocess.run=expired
    with self.assertRaises(B.BatchStop):obj.command(['fixture'])
   finally:B.subprocess.run=old
   prefix=obj.out/f'command-{obj.index:05d}'
   self.assertEqual(prefix.with_suffix('.stdout.txt').read_bytes(),b'partial-out\x00');self.assertEqual(prefix.with_suffix('.stderr.txt').read_bytes(),b'partial-err');self.assertTrue(prefix.with_suffix('.error.txt').exists());self.assertEqual(len(calls),1)
   print(json.dumps({'case':'original_BMS_timeout_partial_streams','transport_calls':len(calls),'stdout_hex':prefix.with_suffix('.stdout.txt').read_bytes().hex(),'stderr_hex':prefix.with_suffix('.stderr.txt').read_bytes().hex(),'error_file_retained':True,'device_calls':0}))
 def test_deadline_production_command_and_power_parser(self):
  # Keep actual UI.command; intercept only original transport implementation.
  calls=[];old=B.Board.command
  try:
   B.Board.command=lambda self,argv,timeout:(calls.append(timeout) or (0,'fixture'))
   obj=UI.__new__(UI);obj.deadline=time.monotonic()+5;obj.wall_deadline=time.time()+5
   obj.command(['fixture'],60);self.assertTrue(0<calls[-1]<=5)
   obj.deadline=time.monotonic()-1
   with self.assertRaises(B.BatchStop):obj.command(['fixture'])
   self.assertEqual(len(calls),1)
  finally:B.Board.command=old
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);profile=json.loads((Path(__file__).with_name('profile.example.json')).read_text());now=datetime.datetime.now().astimezone()
   profile.update(holder='outer(codex) 123 '+now.isoformat(),window_start=now.timestamp(),state_dir=str(root/'no-writes'))
   (root/'profile.json').write_text(json.dumps(profile))
   r=subprocess.run([sys.executable,str(Path(ui.__file__)),'preflight','--profile',str(root/'profile.json'),'--state',profile['state_dir'],'--repo',str(args.source_root),'--hdc','NEVER_HDC'],capture_output=True,text=True)
   self.assertEqual(r.returncode,0,r.stderr);self.assertEqual(json.loads(r.stdout)['device_calls'],0);self.assertFalse((root/'no-writes').exists())
  self.assertEqual(ui.power('ScreenOffTime: Timeout=30000ms OverrideTimeout=10000ms'),{'timeout':30000,'override':10000})
  for raw in ('missing','ScreenOffTime: Timeout=10000ms OverrideTimeout=-1ms'):
   with self.assertRaises(ValueError):ui.power(raw)
if __name__=='__main__':unittest.main(argv=['test_ui.py']+rest)
