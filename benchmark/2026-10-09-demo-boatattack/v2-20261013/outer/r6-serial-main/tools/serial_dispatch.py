#!/usr/bin/env python3
"""Thin serial wrapper: original smoke10, original full128, original finally recovery."""
import argparse,hashlib,json,os,signal,subprocess,sys,time
from pathlib import Path
SERIAL='5ea34a4500000000000000001123012c'
def need(x,m):
 if not x:raise ValueError(m)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def read(p):return json.loads(Path(p).read_text())
def expand(p):return Path(os.path.expandvars(str(p))).resolve()
def checked(r):
 p=expand(r['path']);need(sha(p)==r['sha256'],'pin drift '+str(p));return p
def save(p,j):
 with Path(p).open('x') as f:json.dump(j,f,indent=2);f.write('\n')
def marker(round_dir,boot):
 need(read(round_dir/'observed-post-reboot-boot.json')=={'boot_id':boot},'root must seed exact fresh admitted marker')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--request',type=Path,required=True);ap.add_argument('--authorization',type=Path);ap.add_argument('--authorization-sha256');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
 q=read(a.request)
 need(q['schema']=='r6-original-serial-dispatch/v1' and q['execution_enabled'] is False,'disabled root-signed request')
 for r in q['pins'].values():checked(r)
 admit=read(checked(q['pins']['admission']));game=read(checked(q['pins']['game']));boot=admit['candidate_boot']
 need(admit['state']=='FRESH_BOUND_DISABLED' and admit['identity']['passed'] is True and admit['identity']['candidate_paths']==337,'actual fresh337 admission')
 need(game['status']=='GAME_PASS' and game['boot_id']==boot and game['approved_by']=='outer(codex)','actual sameboot GAME_PASS')
 if not a.execute:
  print(json.dumps({'status':'DISABLED_PREVIEW','device_calls':0,'boot_id':boot,'sequence':['original smoke10 first plan + originalprelock','original full128 eight-window driver','finally original retained recovery']}));return 0
 need(a.authorization and sha(a.authorization)==a.authorization_sha256,'new root batch authorization pin');auth=read(a.authorization)
 need(auth['approved_by']=='outer(codex)' and auth['script_sha256']==sha(__file__) and auth['request_sha256']==sha(a.request),'root batch author binding')
 need(auth['serial']==SERIAL and auth['boot_id']==boot and auth['renew_recovery_authorization'] is True,'root scope and finally recovery responsibility')
 need(time.time()<auth['stop_new_tests_epoch']<=auth['batch_expires_epoch'],'new batch deadline')
 # Root supplies executable COPIES. The originals and their pins are never overwritten.
 smoke=checked(q['smoke_enabled_plan']);full=checked(q['full_execution_round']);restore=checked(q['restore_enabled_plan']);restore_template=checked(q['recovery_authorization_template'])
 original_smoke=read(checked(q['pins']['smoke_original']));sp=read(smoke);need(sp==dict(original_smoke,execution_enabled=True),'only smoke enabled copy change')
 original_restore=read(checked(q['pins']['restore_original']));need(read(restore)==dict(original_restore,execution_enabled=True),'only original recovery enabled copy change')
 original_full=read(checked(q['pins']['full_original']));fc=read(full)
 need(fc['serial']==SERIAL and fc['apps']==128 and len(fc['windows'])==len(fc['window_bindings'])==8 and fc['bindings']==original_full['bindings'] and fc['generation_sha256']==original_full['generation_sha256'],'original full128 binding/membership')
 need({k:v for k,v in fc.items() if k not in ('windows','window_bindings')}=={k:v for k,v in original_full.items() if k not in ('windows','window_bindings')},'original full128 configuration guards')
 need(full!=checked(q['pins']['full_original']),'full128 must use root execution copy; original driver enables its plans')
 for old,new,ref in zip(original_full['windows'],fc['windows'],fc['window_bindings']):
  newpath=expand(new);need(newpath!=expand(old) and checked(ref)==newpath,'separate pinned execution window')
  op=read(expand(old));np=read(newpath)
  # Relocate only per-window output paths and identity round/out arguments.
  expected=json.loads(json.dumps(op));expected['out']=str(newpath.parent/'runner')
  for phase,leaf in [('after_lock','before-identity'),('before_unlock','after-identity')]:
   cmd=expected[phase];cmd[cmd.index('--round')+1]=str(full.parent);cmd[cmd.index('--out')+1]=str(newpath.parent/leaf)
  need(np==expected,'full128 execution copy changed a guard/parameter')
 for directory in (expand(q['smoke_round']),full.parent):marker(directory,boot)
 handoff_path=expand(q['batch_handoff']);handoff=read(handoff_path);need(handoff['approved_by']=='outer(codex)' and handoff['new_batch_authorization'] is True and handoff['boot_id']==boot,'new root retained responsibility handoff')
 need(checked(handoff['batch_authorization'])==a.authorization.resolve(),'handoff batch author pin')
 events=expand(q['watch_handoff_events']);accepted=False
 for line in events.read_text().splitlines():
  try:event=json.loads(line)
  except json.JSONDecodeError:continue # A trailing append may still be in progress.
  if event.get('kind')=='handoff_accepted':
   receipt=event.get('handoff',{})
   if receipt.get('sha256')==sha(handoff_path) and expand(receipt.get('path',''))==handoff_path:accepted=True
 need(accepted,'old recovery watch has not accepted actual handoff SHA')
 out=expand(q['out']);out.mkdir(parents=True,exist_ok=False);env=dict(os.environ,WORKSPACES=os.environ['WORKSPACES'],MAC_HOME=os.environ.get('MAC_HOME',str(Path.home())))
 env['PATH']=str(checked(q['pins']['hdc_shim']).parent)+os.pathsep+env['PATH']
 stop_requested=False;recovering=False
 def call(name,argv,extra=None):
  started=time.time()
  with (out/(name+'.stdout')).open('xb') as stdout,(out/(name+'.stderr')).open('xb') as stderr:
   r=subprocess.run(argv,stdout=stdout,stderr=stderr,env=dict(env,**(extra or {})))
  save(out/(name+'.json'),dict(argv=argv,rc=r.returncode,started=started,finished=time.time()));need(r.returncode==0,name+' failed; original evidence retained')
  if not recovering:need(not stop_requested,'stop requested after child exited; original finally recovery')
 def deadline():need(not stop_requested and time.time()<auth['stop_new_tests_epoch'],'batch stop/cutoff; restore now')
 def interrupt(signum,frame):
  nonlocal stop_requested
  stop_requested=True # Never raise while the original child may still write the board.
 for sig in (signal.SIGTERM,signal.SIGHUP):signal.signal(sig,interrupt)
 try:
  deadline()
  call('smoke10-prelock',['orb','-m','a2hlab','env','WORKSPACES='+env['WORKSPACES'],'MAC_HOME='+env['MAC_HOME'],'python3',str(checked(q['pins']['identity'])),'--round',str(expand(q['smoke_round'])),'--out',str(out/'smoke10-prelock')])
  call('smoke10',[sys.executable,str(checked(q['pins']['demo_runner'])),str(smoke)])
  result=read(expand(sp['out'])/'board-run-result.json');need(result.get('before_unlock')==0 and result.get('smoke')==0,'original smoke result gates')
  # Same original record parser used by full128: all ten exact keys and records required.
  import importlib.util
  dp=checked(q['pins']['driver']);s=importlib.util.spec_from_file_location('original_r6_driver',dp);driver=importlib.util.module_from_spec(s);s.loader.exec_module(driver)
  found={}
  for shard in sp['shards']:
   keys=set(expand(shard['keys_file']).read_text().split());rows=driver.regress.records(expand(sp['out'])/shard['name'])
   need(set(rows)==keys and not set(found)&set(rows),'smoke10 missing/duplicate record');found.update(rows)
  need(len(found)==10,'ten original records required');deadline()
  call('full128',[sys.executable,str(dp),'--out',str(full.parent),'--execute','--serial',SERIAL,'--authorization',str(a.authorization.resolve())])
 finally:
  recovering=True # A deferred stop never interrupts the original recovery chain.
  # Root explicitly authorizes a fresh bounded copy at recovery time: never reuse expired20min auth.
  lock=checked(q['pins']['lock']);held=subprocess.run(['bash',str(lock),'held',SERIAL],capture_output=True,text=True,env=env)
  save(out/'finally-held.json',dict(rc=held.returncode,stdout=held.stdout,stderr=held.stderr))
  words=held.stdout.strip().split();need(not held.stderr and ((held.returncode==0 and len(words)==3) or (held.returncode==1 and not words)),'ambiguous held result; retain lock and report root')
  owner=words[0] if words else None;need(owner in (None,'cx-t0'),'other owner; retain lock and report root')
  recovery=read(restore_template);now=time.time();recovery.update(started_epoch=now,experiment_expires_epoch=now+600,rollback_expires_epoch=now+1200,stop_new_tests_epoch=now+600,allow_retain=False,holder=owner or original_restore['lane'])
  need(recovery['approved_by']=='outer(codex)' and recovery['serial']==SERIAL,'original recovery root authorization')
  rp=out/'recovery.authorization.json';save(rp,recovery)
  renv={'R6_RECOVERY_AUTH':str(rp),'R6_RECOVERY_AUTH_SHA':sha(rp)}
  if owner is None:
   call('restore-retained',[sys.executable,str(checked(q['pins']['master_runner'])),str(restore)],renv)
  else:
   # Same retained cx-t0 lock: no board_run, no second lock acquisition.
   rr=read(checked(q['pins']['restore_request']));hook=checked(q['pins']['retain_hook'])
   base=[sys.executable,str(hook)]
   tail=['--request',str(checked(q['pins']['restore_request'])),'--authorization',str(rp),'--authorization-sha256',sha(rp)]
   call('same-lock-recover',base+['recover-retained']+tail,renv)
   call('same-lock-original-hwzz',[sys.executable,str(checked(q['pins']['activation_smoke'])),'--spec',str(expand(rr['baseline_smoke'])),'--serial',SERIAL,'--lane',owner,'--out',str(expand(rr['recovery_smoke_result']).parent)],renv)
   call('same-lock-verify',base+['verify-recovered']+tail,renv)
   current=subprocess.run(['bash',str(lock),'held',SERIAL],capture_output=True,text=True,env=env)
   need(current.returncode==0 and not current.stderr and current.stdout==held.stdout,'held owner changed; retain lock')
   call('same-lock-unlock',['bash',str(lock),'unlock',str(expand(original_restore['board'])),SERIAL,owner])
 return 0
if __name__=='__main__':raise SystemExit(main())
