"""VM-owned short window: every exit restores U5 without waiting for the agent."""
import datetime,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
from compare_maps import compare
SERIAL='61b0657200000000000000000324012c'
end=datetime.datetime.fromisoformat(json.loads((H/'window.json').read_text())['expires_at']).timestamp()
cutoff=end-240
stop=H/'stop-now';active=None;observer=None;attempted=False

def bounded(cmd,name):
 global active
 with (H/(name+'.log')).open('w') as log:
  active=subprocess.Popen(cmd,cwd=R,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
  while active.poll() is None:
   if stop.exists() or time.time()>=cutoff:
    os.killpg(active.pid,signal.SIGTERM)
    try:active.wait(timeout=10)
    except subprocess.TimeoutExpired:os.killpg(active.pid,signal.SIGKILL);active.wait()
    raise RuntimeError('stop request or rollback reserve')
   time.sleep(1)
  rc=active.wait();active=None
  if rc:
   if Path(cmd[1]).name=='run_batch.py' and rc==1:
    run=H/'runs'/cmd[2]/SERIAL
    keys=cmd[3].split(',')
    records=[json.loads((run/key/'record.json').read_text()) for key in keys if (run/key/'record.json').exists()]
    if len(records)==len(keys) and all(r.get('finished_at') and len([s for s in r.get('screenshots',[]) if s.get('captured')])==2 for r in records):return
   raise RuntimeError(name+' rc='+str(rc))

def review(name):
 (H/'waiting-review.txt').write_text(name)
 while not (H/(name+'.accept')).exists():
  if stop.exists() or time.time()>=cutoff:raise RuntimeError('review declined or reserve')
  time.sleep(1)
 (H/'waiting-review.txt').unlink(missing_ok=True)

out={'started':datetime.datetime.now().astimezone().isoformat()}
try:
 bounded([sys.executable,str(H/'jar.py'),'capture'],'capture')
 bounded([sys.executable,str(H/'jar.py'),'baseline'],'baseline')
 d=json.loads((H/'jar-original.json').read_text())
 state=lab_paths.workspaces()/'westlake-generation-state'/SERIAL/(d['boot_id']+'-74d1d6d48210.json')
 assert state.exists(),state
 (H/'state-path.txt').write_text(str(state))
 observer=subprocess.Popen([sys.executable,str(H/'watch.py'),'u5'],stdout=(H/'observer-u5.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 bounded([sys.executable,str(H/'run_batch.py'),'n7-u5-baseline','localsend,fd-immich,fd-fluffychat,fd-kitchenowl,fd-libre,fd-saber,aegis'],'u5-baseline-apps')
 (H/'stop-watch').touch();observer.wait(timeout=30);observer=None;(H/'stop-watch').unlink()
 attempted=True
 bounded(['bash',str(H/'deploy.sh')],'activation')
 observer=subprocess.Popen([sys.executable,str(H/'watch.py'),'n7'],stdout=(H/'observer.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 bounded([sys.executable,str(H/'run_batch.py'),'n7-controls','helloworld,zigzag','--controls'],'controls')
 review('controls')
 bounded([sys.executable,str(H/'run_batch.py'),'n7-protection','aegis,fd-catima,ooniprobe,fd-auxio,fd-calendar,markor'],'protection')
 review('protection')
 for key in ['localsend','fd-immich','fd-fluffychat','fd-kitchenowl','fd-libre','fd-saber','firefox','fd-fennec_fdroid','mcdonalds','fd-im-vector-app']:
  run='n7-'+key
  bounded([sys.executable,str(H/'run_batch.py'),run,key],'batch-'+key)
  if key in ['localsend','fd-immich','fd-fluffychat','fd-kitchenowl','fd-libre','fd-saber']:
   check=compare(key,run)
   if check['status']!='no_added_duplicate_in_samples':raise RuntimeError('maps: '+key+' '+check['status'])
 out['tests']='completed'
except BaseException as e:
 out['stop_reason']=str(e);traceback.print_exc()
finally:
 (H/'stop-watch').touch()
 if observer:
  try:observer.wait(timeout=30)
  except subprocess.TimeoutExpired:os.killpg(observer.pid,signal.SIGTERM);observer.wait(timeout=10)
 # No model interaction is required from this point through release.
 try:
  if attempted:
   with (H/'automatic-rollback.log').open('w') as log:
    subprocess.run(['bash',str(H/'rollback.sh')],cwd=R,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=210)
  else:
   subprocess.run([sys.executable,str(H/'jar.py'),'final'],cwd=R,check=True,timeout=120)
  out['u5_restored']=True
  grant=json.loads((H/'window.json').read_text());grant.update(status='revoked',revoked_at=datetime.datetime.now().astimezone().isoformat());(H/'window.json').write_text(json.dumps(grant,indent=2)+'\n')
  subprocess.run(['mac',str(lab_paths.tools()/'board_note.sh'),'unlock',str(lab_paths.harness()/'.octos/boards/app-lighting.md'),SERIAL,'cx-t0'],check=True,timeout=20)
  out['unlocked']=True
 except BaseException as e:out['cleanup_error']=repr(e);traceback.print_exc()
 out['finished']=datetime.datetime.now().astimezone().isoformat();out['overrun_seconds']=max(0,time.time()-end)
 (H/'supervisor-result.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps(out),flush=True)
