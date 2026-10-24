"""T146: entry-version regression; runs on public fixtures + synthetic bytes, fresh-clone safe."""
"""Offline production-path checks; never constructs a live Window."""
import importlib.util,json,tempfile
from pathlib import Path
P=Path(__file__).resolve().parent
import t146_patch as _t146
spec=importlib.util.spec_from_file_location('t136_entry',P/'execute.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
import t146_patch as _t146
_t146.patch_module(m)
checks=[]
assert m.linux_device_pair(66352)==(259,48)==tuple(int(x,16) for x in '103:30'.split(':'))
checks.append('actual_linux_stat66352_matches_maps103_30_and_mount259_48')
text=(P/'execute.py').read_text()
assert 'enumerate((5,30,60,90))' in text and '((30,60,90,120)[index])' in text
checks.append('last_frame90_review_deadline120')
def case(name,fn):fn();checks.append(name)
assert not m.same_process(dict(pid=1,birth=2,uid=3),dict(pid=1,birth=4,uid=3));checks.append('same_pid_new_birth_is_different')
# Exercise the actual power-maintenance method against deterministic device replies.
for initial,verify,fail in [(None,600000,False),(10000,600000,False),(None,None,True),(600000,600000,False)]:
 w=object.__new__(m.Window);w.prepower={'base':30000,'override':10000};w.held=lambda:None;seq=iter([dict(base=30000,override=initial,state='AWAKE'),dict(base=30000,override=verify,state='AWAKE')]);w.power=lambda label:next(seq);calls=[];w.shell=lambda label,cmd:calls.append(cmd)
 try:w.keepawake('synthetic');failed=False
 except AssertionError:failed=True
 assert failed==fail
 if initial is None:assert calls==['power-shell timeout -o 600000']
 checks.append('override_'+str(initial)+'_post_'+str(verify))
# Run the actual try/finally path with a stopped publication and synthetic recovery.
with tempfile.TemporaryDirectory(prefix='entry-test-') as d:
 w=object.__new__(m.Window);w.run=Path(d);w.owner=None;w.start=None;w.n=0;w.recovery=False;w.publish_attempted=False;w.backup=None;w.prepower=None;w.published=None;w.original=None;w.result={}
 obj=dict(dev=66352,inode=560578,uid=20011206,gid=20011206,mode='644',size=2023136,mtime=1,selinux=m.LABEL,sha256=m.BASELINE)
 ident={'boot':'original','processes':[]};actions=[]
 w.bind=lambda label,expected:(ident,obj.copy());w.power=lambda label:dict(base=30000,override=10000,state='AWAKE');w.held=lambda:None;w.elapsed=lambda:1
 def call(label,argv,allow_failure=False):
  actions.append(label)
  if label in ('held-before','final-held'):return {'local_rc':1},'', ''
  if label=='held-acquired':return {'local_rc':0},m.LANE+' 123 now',''
  if label=='preimage-recv':(w.run/'baseline.so').write_bytes((m.INPUT/'rollback.so').read_bytes())
  return {'local_rc':0},'', ''
 w.call=call
 def object_(label,path):
  if label.startswith('system'):return dict(obj,sha256=m.SYSTEM_SHA)
  if label in ('staged','rollback-current'):return dict(obj,sha256=m.CANDIDATE,inode=560579)
  return obj.copy()
 w.object=object_
 def shell(label,command):
  actions.append(label)
  if label=='atomic-publish':raise RuntimeError('synthetic publication result unknown')
  return ''
 w.shell=shell;w.reboot=lambda label:actions.append(label);w.stage=lambda *a:ident;w.screen=lambda label:actions.append(label)
 w.run_window()
 assert actions.index('atomic-publish')<actions.index('atomic-rollback')<actions.index('rollback-reboot')<actions.index('power-restore')<actions.index('unlock')
 assert w.result['rollback']=='verified' and w.result['released']
 checks.append('actual_finally_after_unknown_publish_restores_before_unlock')
print(json.dumps({'synthetic_only':True,'checks':checks,'passed':len(checks)}))
