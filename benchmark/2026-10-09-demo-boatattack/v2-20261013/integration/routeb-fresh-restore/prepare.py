#!/usr/bin/env python3
"""Exact current-prestate rebase of the original487 transaction. Offline only."""
import argparse,copy,hashlib,importlib.util,json,os,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[5])))
MAIN=WS/'westlake-harness'
OLD=MAIN/'benchmark/2026-10-12-v1-seal-execution/exact-5cd-preview'
OLD_PLAN_SHA='088dd4cdf67438426dae214671375a5001aedc86ea8ed807ea354f3c536d1592'
OLD_EXECUTOR_SHA='496fa979f4af71b8c01c44a474aed4074b64544d5d1eb500709c649679831d0d'
UNION_SHA='58ee3bf945eae2ed69b3b689813a389bc44a3c4786ebda570c2ae724f61b4acb'
META=('mode','uid','gid','label')
def need(ok,msg):
 if not ok:raise ValueError(msg)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def resolve(s):return Path(str(s).replace('$WORKSPACES',str(WS))).resolve()
def portable(p):return '$WORKSPACES/'+str(Path(p).resolve().relative_to(WS))
def pin(p):return dict(path=portable(p),sha256=sha(p))
def checked(ref):
 p=resolve(ref['path']);need(set(ref)=={'path','sha256'} and p.is_file() and sha(p)==ref['sha256'],'input SHA drift');return p

def load(p,name):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def directories(folder,boot):
 import capture_directories as collect
 receipt=read(folder/'receipt.json');result=read(folder/'result.json')
 need(receipt['collector_sha256']==sha(HERE/'capture_directories.py') and receipt['source_plan_sha256']==OLD_PLAN_SHA,'readonly collector/origin pin')
 need(receipt['rc']==0 and receipt['device_writes']==0 and not (folder/'stderr.txt').read_bytes(),'readonly collection failed')
 need(receipt['stdout_sha256']==sha(folder/'stdout.txt') and receipt['stderr_sha256']==sha(folder/'stderr.txt'),'raw pin')
 command='/system/bin/sh -c '+collect.shlex.quote(collect.script(boot))+'; rc=$?; printf "\\nFRESH_DIR_RC=%s\\n" "$rc"'
 need(receipt['argv'][1:]==['-t',collect.SERIAL,'shell',command],'exact readonly command')
 parsed=collect.parse((folder/'stdout.txt').read_text(),boot);parsed['receipt_sha256']=sha(folder/'receipt.json');need(result==parsed,'directory output differs from raw')
 return result

def render(request_path,out):
 req=read(request_path);need(req['schema']=='routeb-current-prestate-request/v1' and req['execution_enabled'] is False and req.get('signed_by') is None,'disabled recipe request')
 compiler=checked(req['union_compiler']);need(sha(compiler)==UNION_SHA,'frozen f28 union compiler')
 c=load(compiler,'routeb_frozen_union');qpath=checked(req['union_request']);q,boat,seal,proof,expected,binary,history=c.inputs(qpath)
 need(q['serial'].startswith('5cd') and history['history']['placed_count']==487 and history['history']['executor_rc']==0,'actual original487 history')
 cap_path=c.pin(boat['capture'],qpath.parent);cap=c.read(cap_path);boot=cap['boot_after']
 need(cap['complete'] is True and cap['boot_before']==boat['boot_id']==boot,'current capture boot')
 folder=checked(req['directory_result']).parent;dirs=directories(folder,boot)
 need(sha(OLD/'plan.json')==OLD_PLAN_SHA and sha(OLD/'executor.py')==OLD_EXECUTOR_SHA,'frozen old transaction')
 old=read(OLD/'plan.json');need(len(old['members'])==487,'exact original487');p=copy.deepcopy(old)
 for row in old['directories']+old['directory_prerequisites']:
  need({k:dirs['directories'][row['target']][k] for k in META}==row['after'],'existing directory differs from original metadata')
 supplement=dirs['directories']['/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/webview-t-data']
 need({k:supplement[k] for k in META}==dict(mode='755',uid=20011300,gid=20011300,label='u:object_r:appdat:s0'),'r4b supplement metadata')
 p.update(execution_enabled=False,boot_id=boot,directories=[],storage_directories=[],retained_directories=[])
 p['directory_prerequisites']=[dict(target=t,exists=True,after={k:v[k] for k in META}) for t,v in sorted(dirs['directories'].items())]
 p['preserved']=[dict(target='/data/local/tmp/operator45/selfheal48/stop',before=dirs['preserved_stop'])]
 # Full original R5 independently admitted the WMS/host observation, not run.sh itself.
 observed=c.pin(q['base']['observation'],qpath.parent);oref=c.read(observed)['parameter_evidence']
 running,dynamic=binary.original.realization.running_files(proof,oref,observed.parent,boot)
 raw=(proof['package']/'runtime/run.sh').read_bytes();run_bytes,_=binary.original.realization.exact_numeric(raw,rb'^export WL_PARENT_ID=([0-9]+)$',dynamic['parameter_evidence']['window_id'],'window_id')
 need(hashlib.sha256(run_bytes).hexdigest()==dynamic['sha256']==expected[dynamic['target']],'whole run.sh SHA after independent WID derivation')
 for row in p['members']:
  target=row['target'];source=OLD/row['source'].removeprefix('$PACKAGE/')
  digest=sha(source)
  if target==dynamic['target']:
   source=out/'run.sh';digest=hashlib.sha256(run_bytes).hexdigest()
  need(digest==expected[target]==cap['files'][target]['sha256'],'source/current R5/capture disagree: '+target)
  need({k:cap['files'][target][k] for k in META}==row['after'],'original/current metadata differs: '+target)
  row.update(source=portable(source),sha256=digest,before=dict(cap['files'][target],source=portable(source)))
 p['fresh_rebase']={'schema':'routeb-current-prestate/v1','original_plan':pin(OLD/'plan.json'),'original_executor':pin(OLD/'executor.py'),'capture':pin(cap_path),'directory_result':pin(folder/'result.json'),'union_request':pin(qpath),'union_compiler':pin(compiler),'original_activation_binding':q['base']['activation_binding'],'original_realization':q['base']['realization'],'independent_window_derivation':dynamic,'all_directories':dirs['directories'],'member_count':487,'reboots':0,'atomic_existing_files':True}
 p['fresh_rebase']['executor']=pin(HERE/'executor.py');p['fresh_rebase']['generator']=pin(HERE/'prepare.py');p['fresh_rebase']['request']=pin(request_path)
 need(all(row['before']['exists'] is True for row in p['members']),'this revision requires actual existing487')
 # Never reinterpret a missing directory as an existing one.
 need(len(dirs['directories'])==29 and all(v['exists'] is True for v in dirs['directories'].values()),'exact existing29 directories')
 return p,run_bytes

def build(request,out):
 need(not out.exists(),'fresh output required');p,run_bytes=render(request,out);out.mkdir(parents=True);(out/'run.sh').write_bytes(run_bytes)
 (out/'plan.disabled.json').write_text(json.dumps(p,indent=2)+'\n')
 proof={'schema':'routeb-current-prestate-recipe/v1','execution_enabled':False,'signed_by':None,'plan':pin(out/'plan.disabled.json'),'executor':pin(HERE/'executor.py'),'generator':pin(HERE/'prepare.py'),'request':pin(request),'origin':p['fresh_rebase'],'serial':p['serial'],'boot_id':p['boot_id'],'mode':'restore-directory-complete','targets':{r['target']:r['sha256'] for r in p['members']},'directory_count':29,'device_calls':0}
 (out/'recipe.json').write_text(json.dumps(proof,indent=2)+'\n');return proof

def verify(recipe_path,recipe_sha):
 need(sha(recipe_path)==recipe_sha,'recipe independent pin');r=read(recipe_path);need(r['schema']=='routeb-current-prestate-recipe/v1' and r['execution_enabled'] is False and r['signed_by'] is None and r['mode']=='restore-directory-complete','recipe disabled scope')
 need(checked(r['generator'])==HERE/'prepare.py' and checked(r['executor'])==HERE/'executor.py','local exact generator/executor')
 path=checked(r['plan']);p=read(path);want,data=render(checked(r['request']),path.parent)
 need(p==want and (path.parent/'run.sh').read_bytes()==data,'exact current prestate regeneration')
 need(r['origin']==p['fresh_rebase'] and r['serial']==p['serial'] and r['boot_id']==p['boot_id'] and r['targets']=={m['target']:m['sha256'] for m in p['members']} and r['directory_count']==29,'recipe complete membership')
 return r,p,path

if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 try:build(a.request.resolve(),a.out.resolve());print('PREPARED_DISABLED_CURRENT487_DIRECTORIES29_ZERO_DEVICE')
 except (ValueError,KeyError,TypeError,OSError,AssertionError) as e:print('REFUSE '+str(e),file=sys.stderr);raise SystemExit(2)
