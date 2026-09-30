"""Exercise cleanup ordering using local fake processes; never contacts a device."""
import contextlib,datetime,io,json,runpy,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
SOURCE=Path(__file__).with_name('supervise.py')
class Cleanup(unittest.TestCase):
 def exercise(self,failed='controls',rollback_fails=False):
  with tempfile.TemporaryDirectory() as tmp:
   root=Path(tmp);h=root/'benchmark/window';h.mkdir(parents=True);(h/'supervise.py').write_bytes(SOURCE.read_bytes());now=datetime.datetime.now().astimezone()
   (h/'window.json').write_text(json.dumps(dict(expires_at=(now+datetime.timedelta(minutes=29)).isoformat(),status='active')))

   for name in ['u5-zigzag','n8-zigzag-1','n8-zigzag-2','n8-zigzag-3','hw']:(h/(name+'.accept')).touch()
   state=root/'westlake-generation-state/61b0657200000000000000000324012c';state.mkdir(parents=True);(state/'boot-74d1d6d48210.json').touch()
   events=[]
   class Process:
    pid=900000
    def __init__(self,cmd,**kwargs):
     self.cmd=cmd;self.rc=0;name=Path(cmd[1]).name;events.append(('start',name,cmd[-1]))
     if name=='jar.py' and cmd[-1]=='capture':(h/'jar-original.json').write_text(json.dumps(dict(boot_id='boot')))
     if name=='run_batch.py' and 'n8-zigzag-1' in cmd and failed=='controls':self.rc=1
     if name=='run_batch.py' and 'n8-zigzag-1' in cmd and failed=='complete_rc1':
      self.rc=1
      for key in cmd[3].split(','):
       out=h/'runs'/cmd[2]/'61b0657200000000000000000324012c'/key;out.mkdir(parents=True)
       (out/'record.json').write_text(json.dumps(dict(finished_at=1,status='foreground_unconfirmed',screenshots=[dict(captured=True),dict(captured=True)])))
     if name=='jar.py' and cmd[-1]=='baseline' and failed=='baseline':self.rc=1
     if name=='deploy.sh' and failed=='activation':self.rc=1
    def poll(self):return self.rc
    def wait(self,**kwargs):return self.rc
   def run(cmd,**kwargs):
    if Path(cmd[1]).name=='rollback.sh':
     events.append(('rollback',))
     if rollback_fails:raise RuntimeError('rollback verify failed')
    elif cmd[0]=='mac':events.append(('unlock',))
    else:events.append(('final',))
    return types.SimpleNamespace(returncode=0)
   paths=types.SimpleNamespace(workspaces=lambda:root,tools=lambda:root/'tools',harness=lambda:root)
   maps=types.SimpleNamespace(compare=lambda *a:dict(status='no_added_duplicate_in_samples'))
   with patch.dict(sys.modules,{'lab_paths':paths,'compare_maps':maps}),patch('subprocess.Popen',Process),patch('subprocess.run',run),contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):
    runpy.run_path(str(h/'supervise.py'),run_name='__main__')
   return events,json.loads((h/'supervisor-result.json').read_text())
 def test_controls_failure_restores_before_unlock(self):
  events,out=self.exercise();self.assertLess(events.index(('rollback',)),events.index(('unlock',)));self.assertTrue(out['u5_restored']);self.assertIn('n8-zigzag-1 rc=1',out['stop_reason'])
 def test_complete_rc1_is_evidence_not_transport_failure(self):
  events,out=self.exercise('complete_rc1');self.assertEqual(out.get('tests'),'completed');self.assertNotIn('stop_reason',out);self.assertTrue(out['unlocked'])
 def test_activation_failure_still_restores(self):
  events,out=self.exercise('activation');self.assertIn(('rollback',),events);self.assertTrue(out['unlocked'])
 def test_baseline_failure_never_deploys(self):
  events,out=self.exercise('baseline');self.assertNotIn(('rollback',),events);self.assertIn(('final',),events);self.assertTrue(out['unlocked'])
 def test_failed_restore_retains_lock(self):
  events,out=self.exercise(rollback_fails=True);self.assertNotIn(('unlock',),events);self.assertIn('cleanup_error',out)
if __name__=='__main__':unittest.main()
