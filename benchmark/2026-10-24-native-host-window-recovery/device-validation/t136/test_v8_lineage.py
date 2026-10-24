"""Offline actual-method regressions; no live Window and no device commands."""
import copy,json,tempfile
from pathlib import Path
import execute_v8 as m
import t146_patch as _t; _t.patch_module(m)
from t146_patch import fixture, patch_module, SYNTH_BASELINE_SHA, SYNTH_CANDIDATE_SHA
P=Path(__file__).resolve().parent
raw=fixture('execute-20261025-031657-eafd14','0060-baseline-s30-identity-before','stdout')
ident=m.parse_identity(raw.read_text());checks=[]
main,desc=m.select_main(ident);assert main['pid']==7331 and desc[0]['lineage_to_main']==[8080,7331];checks.append('actual_ppid_main_and_descendant')
for name,mutate in [('two_direct',lambda x:x['processes'][-1].update(parent=5537)),('unknown_lineage',lambda x:x['processes'][-1].update(parent=123)),('wrong_uid',lambda x:x['processes'][-1].update(uid=0))]:
 x=copy.deepcopy(ident);mutate(x)
 try:m.select_main(x)
 except RuntimeError:checks.append(name)
 else:raise AssertionError(name)
actual=json.loads(fixture('execute-20261025-032931-2688cd','baseline-early-17-binding.json').read_text())['identity']
assert m.select_main(actual)[0]['pid']==29773
assert m.select_main(actual,allow_empty=True)[0]['pid']==29773
empty=dict(actual,processes=[x for x in actual['processes'] if x['name']!='com.ss.android.article.news'])
assert m.select_main(empty,allow_empty=True)==(None,[])
checks.append('actual2688cd_main29773_allow_empty_does_not_swallow_child')
base=json.loads(m.IDLE_SOURCE.read_text())['object']
for mode in ['valid','descendant_not_mapped','wrong_published_inode','wrong_descendant_sha','wrong_descendant_inode','identity_birth_drift']:
 with tempfile.TemporaryDirectory(prefix='t146-bind-') as d:
  w=object.__new__(m.Window);w.run=Path(d);w.published=dict(base);w.published['sha256']=m.CANDIDATE
  obj=dict(base,sha256=m.CANDIDATE)
  if mode=='wrong_published_inode':w.published['inode']+=1
  def identity(label):
   x=copy.deepcopy(ident)
   if mode=='identity_birth_drift' and label.endswith('after'):x['processes'][-1]['birth']+=1
   return x
  w.identity=identity
  def object_(label,path):
   x=obj.copy()
   if 'descendant' in label and mode=='wrong_descendant_sha':x['sha256']=m.BASELINE
   return x
  w.object=object_
  def shell(label,command):
   if label.endswith('maps'):
    assert 'cat /proc/' in command and 'awk' not in command
    other='0-1 r--p 0 00:00 0 /unrelated.so\n'
    if 'descendant' in label and mode=='descendant_not_mapped':return other
    inode=obj['inode']+(1 if 'descendant' in label and mode=='wrong_descendant_inode' else 0)
    return other+f'1-2 r-xp 0 103:30 {inode} {m.MAPPED}\n'
   return str(Path(m.TARGET).parent).removeprefix('/data')+' /data/local/tmp/asx\nmnt:[123]'
  w.shell=shell
  try:bound,result=w.bind('fixture',m.CANDIDATE);failed=False
  except (AssertionError,RuntimeError):failed=True
  assert failed==(mode not in ('valid','descendant_not_mapped')),mode
  if not failed:
   record=json.loads((w.run/'fixture-binding.json').read_text());assert record['identity']==ident and len(record['same_name_descendants'])==1
   assert record['mappings'][1]['mapping']==('not_mapped' if mode=='descendant_not_mapped' else 'verified')
  checks.append('production_bind_'+mode)
# Actual admission forwards the full identity, including descendant, to strict bind.
w=object.__new__(m.Window);w.result={};w.identity=lambda label:ident;called=[]
w.bind=lambda label,expected:(called.append(expected) or (ident,base))
assert w.admit('test')[0]==ident and called==[m.BASELINE];checks.append('production_admit_descendant_not_second_main')
# Actual stage accepts same old main under a new host and verifies click response.
for recovery in [False,True]:
 w=object.__new__(m.Window);w.recovery=recovery;w.start=0;w.original={'boot':'original'};w.elapsed=lambda:1;actions=[];w.desktop=lambda *a:[120,400];w.ui=lambda label,cmd:actions.append(cmd)
 current=copy.deepcopy(ident);old=copy.deepcopy(ident);old['processes'][0]['pid']-=1;old['processes'][0]['birth']-=1
 polls=[0]
 def identity(label):
  polls[0]+=1
  if recovery and polls[0]==1:return dict(current,processes=[p for p in current['processes'] if p['name']!='com.ss.android.article.news'])
  return current
 w.identity=identity;w.bind=lambda *a:(current,base);w.screen=lambda label:{'label':label};w.review=lambda pic,*a:{'verdict':'usable'} if pic['label'].endswith('content-after') else {'verdict':'feed','touch_kind':'click','touch_coordinates':[120,400]}
 realmono=m.time.monotonic;realsleep=m.time.sleep;t=[0]
 def tick():t[0]+=.5;return t[0]
 m.time.monotonic=tick;m.time.sleep=lambda _:None
 try:assert w.stage('baseline-restored' if recovery else 'recreated',m.BASELINE if recovery else m.CANDIDATE,None if recovery else old)==current
 finally:m.time.monotonic=realmono;m.time.sleep=realsleep
 assert len(actions)==(1 if recovery else 2)
 checks.append('production_recovery_early_identity' if recovery else 'production_recreated_click_with_descendant')
print(json.dumps({'synthetic_or_record_replay_only':True,'passed':len(checks),'checks':checks}))
