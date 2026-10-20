from pathlib import Path
import os,sys,json,time,datetime,subprocess,hashlib,copy,importlib.util
from types import SimpleNamespace
ROOT=Path(__file__).resolve().parent
BASE=ROOT.parent/'implementation-01/source'
MAIN=Path(os.environ['T31_MAIN']).resolve()
os.environ['T31_MAIN']=str(MAIN)
sys.path.insert(0,str(BASE));sys.path.insert(0,str(BASE/'recovery'))
import check_offline as fixture
import recovery_policy as policy
DATA=fixture.DATA
win=ROOT/'t31-5cd-window-97';win.mkdir();apply=win/'apply';apply.mkdir()
start=time.time()-5; holder='inner(cx-seal) 99997 '+datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat()
ad=copy.deepcopy(fixture.OA);ad.update(holder=holder,window_start=start,status='FRESH_LOCAL_ADMISSION_EXECUTOR_PREFLIGHT_REQUIRED')
assert 'deployment_scope' not in ad and 'origin_window_id' not in ad
fresh=win/'fresh-admission.json';fresh.write_text(json.dumps(ad,indent=2)+'\n')
context=win/'context.json';context.write_text(json.dumps(dict(serial=policy.SERIAL,holder=holder,start=start,deploy=str(DATA))))
scoped=win/'scoped-admission.json';argv=[sys.executable,str(BASE/'scope_apply.py'),'--context',str(context),'--fresh-admission',str(fresh),'--origin-data',str(DATA),'--out',str(scoped)]
(ROOT/'scope.argv.json').write_text(json.dumps(argv)+'\n');r=subprocess.run(argv,capture_output=True);(ROOT/'scope.stdout').write_bytes(r.stdout);(ROOT/'scope.stderr').write_bytes(r.stderr);(ROOT/'scope.rc').write_text(str(r.returncode)+'\n');assert r.returncode==0,r.stderr
case=fixture.Checks();case.setUp()
try:
 e=case.env();e['a']=SimpleNamespace(mode='apply',holder=holder,start=start,admission=scoped,boot=ad['boot'],parent='5793',birth='9986',recovery_no_parent=False,out=apply)
 e.update(board=SimpleNamespace(serial=policy.SERIAL),apply_plan=None,PLAYER_INPUT_REL=fixture.OLD['player_input_rel'])
 source=DATA/'executor.py';assert policy.sha(source)==policy.EXECUTOR;e['__file__']=str(source)
 original=source.read_text();block=original[original.index("plan={'mode'"):original.index("if a.mode=='preflight':print(json.dumps(plan))")]
 (ROOT/'actual-executor-plan-block.py').write_text(block)
 exec(compile(block,str(source),'exec'),e)
 planpath=apply/'plan.json';pb=planpath.read_bytes();p,o=policy.validate_origin(DATA,planpath,scoped)
 assert p['admission_sha256']==policy.sha(scoped) and o['deployment_scope']=='T31_5CD_DEMO_CANDIDATE'
 assert 'deployment_scope' not in p and 'origin_window_id' not in p
 assert p['start']==start and p['holder']==holder
 rejected={}
 for name,input_ad in [('unscoped_original',fresh)]:
  try:policy.validate_origin(DATA,planpath,input_ad)
  except ValueError as ex:rejected[name]=str(ex)
  else:raise AssertionError(name+' not rejected')
 saved=scoped.read_bytes();v=json.loads(saved);v['origin_window_id']='t31-5cd-window-98';scoped.write_text(json.dumps(v))
 try:policy.validate_origin(DATA,planpath,scoped)
 except ValueError as ex:rejected['posthoc_admission_change']=str(ex)
 else:raise AssertionError('posthoc not rejected')
 scoped.write_bytes(saved);assert planpath.read_bytes()==pb
 results=dict(status='PASS',device_calls=0,scope_cli_rc=r.returncode,actual_original_executor_sha256=policy.sha(source),actual_plan_block_sha256=policy.sha(ROOT/'actual-executor-plan-block.py'),scope_source_sha256=policy.sha(BASE/'scope_apply.py'),policy_source_sha256=policy.sha(BASE/'recovery/recovery_policy.py'),plan_sha256=policy.sha(planpath),scoped_admission_sha256=policy.sha(scoped),rejected=rejected,limits='Actual scope_apply CLI and verbatim original executor plan-generation block, then actual validate_origin. Synthetic fresh identity fixture; no full executor CLI, remote guard or device transaction executed. Plan is never patched after generation.')
 (ROOT/'results.json').write_text(json.dumps(results,indent=2)+'\n');print(json.dumps(results))
finally:case.doCleanups()
