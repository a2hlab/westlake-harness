#!/usr/bin/env python3
"""Run the real successor's validation/generation blocks without importing BMS.
No executor main, shell, Board or device transport is invoked.
"""
import ast,copy,hashlib,json,re,shlex,tempfile
from pathlib import Path
from types import SimpleNamespace
D=Path(__file__).resolve().parent
S=(D/'video_guarded_window_r6.py').read_text();tree=ast.parse(S)
sha=lambda b:hashlib.sha256(b).hexdigest()
constants={}
for node in tree.body:
 if isinstance(node,ast.Assign) and all(isinstance(t,ast.Name) for t in node.targets):
  try:v=ast.literal_eval(node.value)
  except (ValueError,TypeError):continue
  for t in node.targets:constants[t.id]=v
BT=(D/'fixtures/before.run.sh').read_bytes();AT=(D/'fixtures/after.run.sh').read_bytes()
original=json.loads((D/'fixtures/original-r3-apply-plan.json').read_text())
assert sha(BT)==original['before_sha'] and sha(AT)==original['after_sha']
assert original['wid']=='33'
for t in [BT,AT]:assert t.count(b'export WL_PARENT_ID=33\n')==1
def derive(t,w):return t.replace(b'export WL_PARENT_ID=33\n',f'export WL_PARENT_ID={w}\n'.encode())
current='34' # synthetic independent WMS known answer, NOT a real board observation
B,A=derive(BT,current),derive(AT,current)
known=[sha(BT),sha(AT),sha(B),sha(A)];assert len(set(known))==4
fixture=dict(original,player_path=constants['PLAYER'],player_before_sha=constants['PBEFORE'],player_after_sha=constants['PAFTER'],player_metadata=constants['PLAYER_METADATA'],player_label=constants['PLAYER_LABEL'],player_input_rel=constants['PLAYER_INPUT_REL'])
block=S[S.index('expected=sha(before)'):S.index('parent_guard=')]
funcs=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ['pathguard','fg','swap']]
notes=[]
with tempfile.TemporaryDirectory(prefix='r4-offline-') as td:
 plan=Path(td)/'fixture.json'
 def env_for(mode='rollback',actual=None,media=None,player=None,dso=False,planvalue=None):
  plan.write_text(json.dumps(fixture if planvalue is None else planvalue))
  e=dict(constants,sha=sha,q=shlex.quote,re=re,json=json,Path=Path)
  e.update(a=SimpleNamespace(mode=mode,apply_plan=plan,boot='0dd753ea-94f7-444b-9d46-9966a999bf28',parent='4929',birth='6723',out=Path('offline-r4-output')),before=B,after=A,before_template=BT,after_template=AT,wid=current,actual=actual or sha(B),mactual=media or constants['MBEFORE'],pactual=player or constants['PBEFORE'],meta=original['run_metadata'],label=original['run_label'],dlabel=original['dso_label'],mmeta=original['media_metadata'],mlabel=original['media_label'],pmeta=constants['PLAYER_METADATA'],plabel=constants['PLAYER_LABEL'],read=lambda cmd:'yes' if dso else 'no')
  for f in funcs:exec(compile(ast.Module(body=[f],type_ignores=[]),'executor-functions','exec'),e)
  return e
 # Real source gate evaluated in isolation; no BMS import/device creation possible.
 gate=next(n for n in tree.body if isinstance(n,ast.If) and 'EXECUTION_REVIEW' in ast.unparse(n.test))
 for field,value in [('EXECUTION_REVIEW','UNAPPROVED'),('PAFTER','UNAPPROVED'),('PLAYER_INPUT_REL','UNAPPROVED')]:
  e=dict(constants,re=re,sys=__import__('sys'));e[field]=value
  try:exec(compile(ast.Module(body=[gate],type_ignores=[]),'gate','exec'),e)
  except SystemExit as ex:assert 'UNAPPROVED_DRAFT' in str(ex)
  else:raise AssertionError('unapproved accepted')
 notes.append('3 real early-refusal branches PASS; no import/transport')
 allowed=0
 for run in known:
  for media in [constants['MBEFORE'],constants['MAFTER']]:
   for player in [constants['PBEFORE'],constants['PAFTER']]:
    for dso in [False,True]:
     e=env_for(actual=run,media=media,player=player,dso=dso);exec(block,e);allowed+=1
 assert allowed==32
 notes.append('32 known run/media/player/compat-presence rollback source-branch states PASS')
 for change in [{'actual':sha(derive(BT,'35'))},{'actual':sha(B+b'\n')},{'media':'0'*64},{'player':'0'*64}]:
  try:exec(block,env_for(**change))
  except AssertionError:pass
  else:raise AssertionError('foreign accepted')
 for key,bad in [('before_sha','0'*64),('after_sha','0'*64),('wid','35'),('player_before_sha','0'*64),('player_after_sha','0'*64),('player_path','foreign'),('player_metadata','644:0:0')]:
  v=copy.deepcopy(fixture);v[key]=bad
  try:exec(block,env_for(planvalue=v))
  except AssertionError:pass
  else:raise AssertionError('tampered plan accepted '+key)
 notes.append('4 foreign current-byte cases + 7 altered original-plan cases rejected')
 # Actual producer preflight and script-generation code, no shell execution.
 precode=S[S.index('parent_guard='):S.index('\nshell(pre)')]
 scriptcode=S[S.index('script=pre'):S.index("(a.out/'swap.sh')")]
 generated={}
 for mode in ['apply','rollback']:
  e=env_for(mode=mode,actual=sha(B) if mode=='apply' else sha(AT),media=constants['MBEFORE'] if mode=='apply' else constants['MAFTER'],player=constants['PBEFORE'] if mode=='apply' else constants['PAFTER'],dso=mode=='rollback')
  exec(block,e);exec(precode,e)
  e.update(stage='/data/local/tmp/offline-stage',new=B if mode=='rollback' else A)
  exec(scriptcode,e);script=e['script'];generated[mode]=script
  first_mv=script.index('\nmv ')
  for name,digest in [('run.sh',sha(B) if mode=='apply' else sha(BT)),(constants['MEDIA'],constants['MBEFORE']),(constants['PLAYER'],constants['PBEFORE'])]:
   backup=e['RT']+'/'+name+'.ttvideo-before-'+(e['a'].boot[:8] if mode=='apply' else original['boot'][:8])
   fg=e['fg'](backup,digest,original['run_metadata'] if name=='run.sh' else original['media_metadata'],original['run_label'])
   assert script.index(fg)+len(fg)<first_mv
   if mode=='apply':assert script.index('cp -p '+e['RT']+'/'+name+' '+backup)<script.index(fg)
  paths=[constants['MEDIA'],constants['PLAYER'],'run.sh']+([constants['DSO']] if mode=='apply' else [])
  for name in paths:
   dst=e['RT']+'/'+name;tmp=dst+'.ttvideo-'+e['a'].boot[:8]+'-'+sha(str(e['a'].out).encode())[:8]+'.tmp'
   expected=None if name==constants['DSO'] else e['mactual'] if name==constants['MEDIA'] else e['pactual'] if name==constants['PLAYER'] else e['expected']
   fm=original['run_metadata'] if name=='run.sh' else original['media_metadata']
   cas=e['fg'](dst,expected,fm,original['run_label']) if expected is not None else e['pathguard'](dst)+f'test ! -e {shlex.quote(dst)}\n'
   assert cas+f'mv {shlex.quote(tmp)} {shlex.quote(dst)}\n' in script
  if mode=='rollback':assert e['fg'](e['RT']+'/'+constants['DSO'],constants['DSHA'],original['media_metadata'],original['run_label'])+f"rm {e['RT']}/{constants['DSO']}\n" in script
  assert 'VIDEO_FILES_SWAPPED_FRESH_BOOT_REQUIRED' in script
 # Exact label comparison (no substring grep) and correct original-boot backup roots.
 assert '| grep -F' not in generated['apply']
 assert 'ttvideo-before-da213fc2' in generated['rollback']
 notes.append('Generated apply: 3 backups verified before first of 4 target renames; each rename immediately follows exact SHA/meta/label or absence CAS')
 notes.append('Generated rollback: 3 original-boot backup checks before staging; known compat removal guarded; fresh-boot boundary retained')
 # Preserve only synthetic output, never mistake it for a real device command receipt.
 for mode,s in generated.items():(D/f'offline-{mode}.sh.txt').write_text(s)
result={'status':'PASS_OFFLINE_ONLY','scope':'Actual source validation/generation blocks; no Board import/transport or shell execution. Backup-missing and remote filesystem failure behavior inspected in emitted set-e sequence, not live-tested.','original_r3_plan_sha256':sha((D/'fixtures/original-r3-apply-plan.json').read_bytes()),'original_wid':'33','current_wid_fixture':'34','original_before':sha(BT),'original_after':sha(AT),'current_before':sha(B),'current_after':sha(A),'fixture_extension':'Only r4 player fields added in memory to real r3 plan; not a real r4 apply receipt.','checks':notes,'device_calls':0,'source_sha256':sha((D/'video_guarded_window_r6.py').read_bytes())}
(D/'offline-checks.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
