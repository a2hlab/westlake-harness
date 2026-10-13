import hashlib,importlib.util,json,os,sys,tempfile,time,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import serial_dispatch as d
H=Path(__file__).resolve().parent
class Dispatch(unittest.TestCase):
 def run_case(self,owner,fail=None):
  with tempfile.TemporaryDirectory(dir=H) as td:
   root=Path(td);q=d.read(H/'request.disabled.json');q.update(out=str(root/'run'),batch_handoff=str(root/'handoff.json'),watch_handoff_events=str(root/'events.jsonl'))
   qr=root/'q.json';qr.write_text(json.dumps(q));ar=root/'auth.json';auth=d.read(H/'authorization.required.json');auth.update(request_sha256=d.sha(qr),stop_new_tests_epoch=time.time()+600,batch_expires_epoch=time.time()+1200);ar.write_text(json.dumps(auth))
   handoff=dict(approved_by='outer(codex)',new_batch_authorization=True,boot_id=auth['boot_id'],batch_authorization=dict(path=str(ar),sha256=d.sha(ar)));Path(q['batch_handoff']).write_text(json.dumps(handoff))
   Path(q['watch_handoff_events']).write_text(json.dumps(dict(kind='handoff_accepted',handoff=dict(path=q['batch_handoff'],sha256=d.sha(q['batch_handoff']))))+'\n')
   argv=['serial_dispatch','--request',str(qr),'--authorization',str(ar),'--authorization-sha256',d.sha(ar),'--execute'];commands=[];handlers={}
   held=(owner+' 123 2026-10-13T19:45:00+0800\n') if owner else ''
   def run(cmd,**kw):
    commands.append(cmd)
    if 'held' in cmd:return SimpleNamespace(returncode=0 if owner else 1,stdout=held,stderr='')
    if fail=='smoke' and len(cmd)==3 and cmd[1].endswith('demo_board_run.py'):return SimpleNamespace(returncode=1)
    if fail=='signal' and len(cmd)==3 and cmd[1].endswith('demo_board_run.py'):
     import signal
     handlers[signal.SIGTERM](signal.SIGTERM,None) # Must return while this child is alive.
    return SimpleNamespace(returncode=0)
   original_read=d.read
   def read(p):
    if Path(p).name=='board-run-result.json':return dict(before_unlock=0,smoke=0)
    return original_read(p)
   original_spec=importlib.util.spec_from_file_location
   def spec(name,p,*a,**kw):
    s=original_spec(name,p,*a,**kw)
    if name=='original_r6_driver':
     old=s.loader.exec_module
     def execute(m):
      old(m)
      sp=original_read(d.checked(q['pins']['smoke_original']));byname={x['name']:d.expand(x['keys_file']).read_text().split() for x in sp['shards']}
      m.regress.records=lambda p:{k:None for k in byname[Path(p).name]}
     s.loader.exec_module=execute
    return s
   error=None
   with patch.object(sys,'argv',argv),patch.object(d,'read',read),patch('subprocess.run',run),patch('importlib.util.spec_from_file_location',spec),patch('signal.signal',side_effect=lambda sig,fn:handlers.update({sig:fn})):
    try:d.main()
    except ValueError as e:error=e
   return commands,error
 def test_preview_no_transport(self):
  with patch.object(sys,'argv',['serial_dispatch','--request',str(H/'request.disabled.json')]),patch('subprocess.run',side_effect=AssertionError('transport forbidden')):self.assertEqual(d.main(),0)
 def test_unlocked_original_recovery(self):
  commands,error=self.run_case(None);self.assertIsNone(error)
  self.assertTrue(any(cmd[1].endswith('board_run.py') for cmd in commands if len(cmd)>1));self.assertFalse(any('unlock' in cmd for cmd in commands))
 def test_same_lock_original_recovery_and_unlock(self):
  commands,error=self.run_case('cx-t0');self.assertIsNone(error)
  phases=[cmd[2] for cmd in commands if len(cmd)>2 and cmd[1].endswith('retain_hooks.py')]
  self.assertEqual(phases,['recover-retained','verify-recovered']);self.assertEqual(commands[-1][-1],'cx-t0');self.assertIn('unlock',commands[-1])
  self.assertTrue(any(cmd[1].endswith('activation_smoke.py') for cmd in commands if len(cmd)>1))
 def test_smoke_failure_skips_full_and_recovers(self):
  commands,error=self.run_case('cx-t0','smoke');self.assertIsNotNone(error)
  self.assertFalse(any(cmd[1].endswith('run_candidate_post_reboot.py') for cmd in commands if len(cmd)>1));self.assertIn('unlock',commands[-1])
 def test_other_owner_preserved(self):
  commands,error=self.run_case('other-lane');self.assertIsNotNone(error)
  self.assertFalse(any('unlock' in cmd or 'recover-retained' in cmd for cmd in commands));self.assertIn('other owner',str(error))
 def test_signal_deferred_until_child_exit_and_recovery_completes(self):
  commands,error=self.run_case('cx-t0','signal');self.assertIsNotNone(error)
  self.assertIn('after child exited',str(error));self.assertIn('unlock',commands[-1])
  self.assertFalse(any(cmd[1].endswith('run_candidate_post_reboot.py') for cmd in commands if len(cmd)>1))
if __name__=='__main__':unittest.main(verbosity=2)
