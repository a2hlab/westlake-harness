"""Offline real-record replay and production binding regressions; no device."""
from pathlib import Path
from t146_patch import fixture, patch_module, SYNTH_BASELINE_SHA, SYNTH_CANDIDATE_SHA
import copy,json,tempfile
import recovery_roles as r
m=r.m;P=Path(__file__).resolve().parent;run=fixture('execute-20261025-033355-1e6bc7')
before=m.parse_identity((run/'0114-firstopen-s30-identity-before/stdout').read_text());after=m.parse_identity((run/'0119-firstopen-s30-identity-after/stdout').read_text());empty=m.parse_identity((run/'0198-baseline-restored-early-presence-1/stdout').read_text())
checks=[]
assert r.select_main(empty,True)==(None,[]);checks.append('real0198_no_parent_no_child_empty')
assert r.select_main(after,True)[0]['pid']==6927;checks.append('real_main_not_swallowed')
x=copy.deepcopy(after);x['processes'].append(dict(pid=999,birth=1,uid=0,parent=5012,name='appspawn-x'));assert r.select_parent(x)['pid']==5012;checks.append('transitional_appspawn_not_second_root')
x['processes'][-1]['parent']=1
try:r.select_parent(x)
except RuntimeError:checks.append('two_roots_rejected')
else:raise AssertionError('two roots')
obj=json.loads(fixture('execute-20261025-032931-2688cd','baseline-early-17-binding.json').read_text())['object']
for mode in ['added_then_stable','main_birth_changed','host_changed','unknown_descendant_uid','object_sha_wrong','object_inode_wrong','three_races_limit']:
 with tempfile.TemporaryDirectory(prefix='t146-rroles-') as d:
  w=object.__new__(r.RecoveryWindow);w.run=Path(d);calls=[];sequence=[copy.deepcopy(before),copy.deepcopy(after),copy.deepcopy(after),copy.deepcopy(after)]
  if mode=='main_birth_changed':sequence[1]['processes'][2]['birth']+=1
  if mode=='host_changed':sequence[1]['processes'][0]['birth']+=1
  if mode=='unknown_descendant_uid':sequence[1]['processes'][-1]['uid']=0
  if mode=='three_races_limit':sequence=[copy.deepcopy(before),copy.deepcopy(after)]*3
  def identity(label):calls.append(label);return sequence.pop(0)
  w.identity=identity
  def object_(label,path):
   o=obj.copy()
   if mode=='object_sha_wrong':o['sha256']=m.CANDIDATE
   return o
  w.object=object_
  def shell(label,cmd):
   if label.endswith('maps'):
    assert 'cat /proc/' in cmd and 'awk' not in cmd
    return f'0-1 r-xp 0 103:30 {obj["inode"]+(mode=="object_inode_wrong")} {m.MAPPED}\n'
   return str(Path(m.TARGET).parent).removeprefix('/data')+' /data/local/tmp/asx\nmnt:[123]'
  w.shell=shell
  try:w.bind('fixture',m.BASELINE);failed=False
  except (RuntimeError,AssertionError):failed=True
  assert failed==(mode!='added_then_stable'),mode
  if mode=='added_then_stable':assert len(calls)==4 and json.loads((w.run/'fixture-binding.json').read_text())['successful_attempt']==2
  elif mode=='three_races_limit':assert len(calls)==6
  else:assert len(calls)<=2,mode
  checks.append('production_'+mode)
print(json.dumps({'offline_only':True,'passed':len(checks),'checks':checks}))
