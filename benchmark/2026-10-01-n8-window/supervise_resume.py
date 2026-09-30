"""VM-owned short window: every exit restores U5 without waiting for the agent."""
import datetime,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
from compare_maps import compare
SERIAL='61b0657200000000000000000324012c'
end=datetime.datetime.fromisoformat(json.loads((H/'extension.json').read_text())['expires_at']).timestamp()
cutoff=datetime.datetime.fromisoformat(json.loads((H/'extension.json').read_text())['stop_tests_at']).timestamp()
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
   if Path(cmd[1]).name in ['run_batch.py','run_priority.py'] and rc==1:
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
 assert (H/'state-path.txt').exists() and (H/'jar-original.json').exists()
 attempted=True
 (H/'stop-watch').unlink(missing_ok=True)
 observer=subprocess.Popen([sys.executable,str(H/'watch.py'),'n8'],stdout=(H/'observer-resume.log').open('w'),stderr=subprocess.STDOUT,start_new_session=True)
 keys=['localsend','fd-immich','fd-fluffychat','fd-kitchenowl','fd-libre','fd-saber','firefox','fd-fennec_fdroid','mcdonalds','fd-im-vector-app','fd-catima','fd-calendar','markor']
 bounded([sys.executable,str(H/'run_priority.py'),'n8-priority',','.join(keys)],'priority-batch')
 for key in keys:
  check=compare(key,'n8-priority')
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
