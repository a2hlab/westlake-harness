"""Offline binding budget checks; subprocess is stubbed, never executed."""
from pathlib import Path
import tempfile,json
import execute_v8 as m
P=Path(__file__).resolve().parent
mono=m.time.monotonic;run=m.subprocess.run
checks=[]
try:
 clock=[0.0];m.time.monotonic=lambda:clock[0]
 w=object.__new__(m.Window);attempts=[]
 def once(*args):attempts.append(args);clock[0]=21;raise m.DescendantSetChanged()
 w._bind_once=once
 try:w.bind('fixture',m.BASELINE)
 except RuntimeError as exc:assert str(exc)=='binding20s deadline'
 else:raise AssertionError('deadline not enforced')
 assert len(attempts)==1 and w.binding_deadline is None;checks.append('20s_prevents_second_attempt')
 with tempfile.TemporaryDirectory(prefix='t146-budget-') as d:
  w=object.__new__(m.Window);w.run=Path(d);w.n=0;w.result={'device_commands':0};w.start=0;w.recovery=True;w.elapsed=lambda:1;w.binding_deadline=24;clock[0]=21;seen=[]
  class R:returncode=0
  def fake(argv,stdout,stderr,timeout):seen.append(timeout);return R()
  m.subprocess.run=fake;w.call('synthetic',['offline-fixture'])
  assert seen==[3] and json.loads(next(w.run.glob('*/command.json')).read_text())['timeout_seconds']==3;checks.append('each_command_limited_to_remaining_budget')
finally:m.time.monotonic=mono;m.subprocess.run=run
print(json.dumps({'offline_only':True,'passed':len(checks),'checks':checks}))
