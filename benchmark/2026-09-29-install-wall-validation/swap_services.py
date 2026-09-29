#!/usr/bin/env python3
"""#79: replace the two reviewed OH service libraries; restore the exact saved four files.

Uses the verified B2/B3 backup -> replacement -> begetctl restart sequence, with
atomic renames, persistent backup identities and the master batch lock/boot guards.
Only the reassigned 61b serial is accepted. Invoke through the a2hlab VM.
"""
import argparse,hashlib,json,shlex,sys,time
from pathlib import Path
MASTER=Path('/Users/zhaoyue/orca/workspaces/westlake-harness')
sys.path.insert(0,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
SERIAL='61b0657200000000000000000324012c'
KIT=Path('/Users/zhaoyue/orca/workspaces/oh61-bms-kit-b79')
LIBS={'libbms.z.so':'2220df48c7bc5a64ca064879f80badc15b3a3ca140dc1d0067a7499f6a7e5e92','libinstalls.z.so':'51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'}
PATHS=[d+'/'+n for n in LIBS for d in ['/system/lib64','/system/lib64/platformsdk']]
BASE=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')/SERIAL/'b79-install-walls'
REMOTE='/data/local/tmp/b79-install-walls-0448366c-43bcde50'
q=shlex.quote

def checked_hashes(board,paths):
 rc,text=board.shell('sha256sum '+' '.join(map(q,paths)))
 got={line.split()[-1]:line.split()[0] for line in text.splitlines() if len(line.split())==2 and len(line.split()[0])==64}
 if set(got)!=set(paths):raise RuntimeError('incomplete hashes')
 return got

def backup_name(path):return REMOTE+'/backup/'+path.replace('/','_')

def main():
 p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','update','restart','verify','rollback','dry-run']);a=p.parse_args()
 sources={n:KIT/'out/wukong100/bundlemanager/bundle_framework'/n for n in LIBS}
 if a.action in ['apply','update','dry-run']:
  for n,s in sources.items():
   if b.sha(s)!=LIBS[n]:raise RuntimeError('candidate changed: '+n)
 if a.action=='dry-run':
  print(json.dumps({'serial':SERIAL,'paths':PATHS,'candidate_sha256':LIBS,'backup':REMOTE+'/backup','device_io':False},indent=2));return
 out=BASE/(a.action+'-'+str(time.time_ns()));out.mkdir(parents=True)
 board=b.Board(SERIAL,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out)
 board.ready();statepath=BASE/'state.json';state=json.loads(statepath.read_text()) if statepath.exists() else None
 if a.action=='apply':
  if state is not None:raise RuntimeError('existing deployment state; verify or roll back explicitly')
  before=checked_hashes(board,PATHS)
  assert all(before[x]==({'libbms.z.so':'f8ef078df8a0fa483b60c1a997831a8190448545e141b9568fb14eacaf9da105','libinstalls.z.so':'2c9a5294a253acb57394cc79956a4b30182a7a0ecad570844c395b38d34d82e0'}[Path(x).name]) for x in PATHS), 'baseline service library changed'
  runtime_before=checked_hashes(board,['/system/bin/appspawn-x','/system/android/framework/oh-adapter-runtime.jar','/system/android/lib64/liboh_adapter_bridge.so'])
  state={'runtime_before':runtime_before,'serial':SERIAL,'boot_before':board.boot,'before':before,'candidate':{x:LIBS[Path(x).name] for x in PATHS},'status':'backing_up','remote':REMOTE}
  b.save(statepath,state)
  board.shell('mkdir -p '+q(REMOTE+'/backup'))
  for path in PATHS:
   dest=backup_name(path);board.shell('test ! -e '+q(dest)+' && cp -p '+q(path)+' '+q(dest))
  got=checked_hashes(board,[backup_name(x) for x in PATHS])
  assert all(got[backup_name(x)]==before[x] for x in PATHS)
  state['status']='backup_verified';b.save(statepath,state)
  for n,s in sources.items():board.send(s,REMOTE+'/'+n)
  got=checked_hashes(board,[REMOTE+'/'+n for n in LIBS]);assert all(got[REMOTE+'/'+n]==LIBS[n] for n in LIBS)
 elif state is None:raise RuntimeError('missing original backup state')
 update_targets=PATHS
 if a.action=='update':
  assert checked_hashes(board,PATHS)==state['candidate'], 'live pair changed outside this transaction'
  update_targets=[x for x in PATHS if state['candidate'][x]!=LIBS[Path(x).name]]
  state.setdefault('previous_candidates',[]).append(state['candidate'])
  for n,source in sources.items():board.send(source,REMOTE+'/'+n)
  got=checked_hashes(board,[REMOTE+'/'+n for n in LIBS]);assert all(got[REMOTE+'/'+n]==LIBS[n] for n in LIBS)
  state['candidate']={x:LIBS[Path(x).name] for x in PATHS}
  b.save(statepath,state)
 if a.action in ['apply','update','rollback']:
  expected=state['candidate'] if a.action in ['apply','update'] else state['before']
  if a.action=='rollback':
   got=checked_hashes(board,[backup_name(x) for x in PATHS]);assert all(got[backup_name(x)]==state['before'][x] for x in PATHS)
  state['desired']='baseline' if a.action=='rollback' else 'candidate'
  state['status']=a.action+'_in_progress';b.save(statepath,state)
  board.shell('mount -o rw,remount /')
  try:
   for dest in update_targets:
    source=REMOTE+'/'+Path(dest).name if a.action in ['apply','update'] else backup_name(dest)
    tmp=dest+'.b79-new'
    board.shell('cp -p '+q(source)+' '+q(tmp)+' && chmod 0755 '+q(tmp)+' && chown root:root '+q(tmp)+' && chcon u:object_r:system_lib_file:s0 '+q(tmp)+' && mv -f '+q(tmp)+' '+q(dest))
   assert checked_hashes(board,PATHS)==expected
  finally:board.shell('mount -o ro,remount /',required=False)
  state['status']='installed_not_restarted' if a.action in ['apply','update'] else 'rolled_back_not_restarted';b.save(statepath,state)
 if a.action=='restart':
  state['restart_from_status']=state['status'];state['status']='restart_requested';b.save(statepath,state)
  # A reboot may interrupt the status marker. Persistent state deliberately precedes this call.
  board.shell('begetctl stop_service installs; begetctl stop_service foundation; sleep 3; begetctl start_service foundation',timeout=20)
 if a.action=='verify':
  expected=state['before'] if state.get('desired')=='baseline' else state['candidate']
  assert checked_hashes(board,PATHS)==expected
  ps=board.shell('ps -A -o PID,PPID,UID,NAME')[1];(out/'processes.txt').write_text(ps)
  matches=[x for x in b.processes(ps) if x['name']=='foundation'];assert len(matches)==1
  pid=matches[0]['pid'];rootpaths=[f'/proc/{pid}/root'+x for x in PATHS]
  got=checked_hashes(board,rootpaths);assert all(got[f'/proc/{pid}/root'+x]==expected[x] for x in PATHS)
  maps=board.shell(f'cat /proc/{pid}/maps')[1];(out/'foundation-maps.txt').write_text(maps)
  bms_maps=[x for x in maps.splitlines() if 'libbms.z.so' in x]
  if not bms_maps or any('(deleted)' in x for x in bms_maps):raise RuntimeError('foundation BMS mapping absent or stale')
  b.preflight(board,out)
  board.shell('power-shell wakeup')
  rec=b.capture(board,REMOTE+'/desktop-'+str(time.time_ns())+'.jpeg',out/'desktop.jpeg');b.save(out/'capture.json',rec)
  state.update(status='sha_verified_visual_pending',verified_boot=board.boot,foundation_pid=pid,verification=str(out));b.save(statepath,state)
 print(json.dumps({'state':str(statepath),'status':state['status'],'evidence':str(out)},indent=2))
if __name__=='__main__':main()
