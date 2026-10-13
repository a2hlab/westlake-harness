"""Recheck frozen admit only. Blocks subprocess and execution; never runs HDC."""
import ast,hashlib,json,os,subprocess,types
from pathlib import Path
from unittest.mock import patch
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file()).parent)))
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def pinned(ref):
 p=Path(ref['path'].replace('$WORKSPACES',str(WS)));assert sha(p)==ref['sha256'];return p
def load(p,name):
 m=types.ModuleType(name);m.__file__=str(p);exec(compile(p.read_text(),str(p),'exec'),m.__dict__);return m
result=read(HERE/'admit-result.json');runner=pinned(result['runner']);planpath=pinned(result['synthetic_plan']);authpath=pinned(result['synthetic_authorization']);plan=read(planpath);auth=read(authpath)
actual=read(pinned(result['actual_plan']));cap=read(pinned(result['actual_capture']));assert plan['serial']==actual['serial']==cap['serial'] and len(plan['serial'])==32
assert plan['uid']==actual['boat_uid']==cap['boat_uid'] and plan['boot_id']==actual['boot_id']==cap['boot_before']==cap['boot_after']
assert plan['synthetic'] and auth['synthetic'];mod=load(runner,'offline_new');old=load(HERE/'rejected-runner.py.txt','offline_rejected')
def rejected(fn,reason):
 try:fn()
 except ValueError as e:assert str(e)==reason;return
 raise AssertionError('unexpected admit acceptance')
with patch('subprocess.run',side_effect=AssertionError('transport forbidden')) as run,patch('subprocess.Popen',side_effect=AssertionError('transport forbidden')) as popen,patch.object(mod,'run',side_effect=AssertionError('execution forbidden')) as execute,patch.object(mod.time,'time',return_value=result['clock_epoch']):
 mod.admit(plan,auth,sha(planpath))
 rejected(lambda:mod.admit(dict(plan,serial='5ea34a4500000000000000001123012c'),auth,sha(planpath)),'serial/boot missing')
 rejected(lambda:mod.admit(plan,dict(auth,runner_sha256='0'*64),sha(planpath)),'authorization pins differ')
 rejected(lambda:old.admit(plan,dict(auth,runner_sha256=sha(HERE/'rejected-runner.py.txt')),sha(planpath)),'serial/boot missing')
 assert run.call_count==popen.call_count==execute.call_count==0
print('OFFLINE_ADMIT: 4 PASS; zero subprocess/transport/execution; synthetic fixtures not board authority')
