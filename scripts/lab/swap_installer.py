#!/usr/bin/env python3
"""Replace the FZ-001 installer pair (libbms.z.so + libapk_installer.so) on any whitelisted OH board.

Portable port of <workspaces>/westlake-installer-background-launcher-6aadb8b4/swap_services.py (the per-board
copies that hard-coded one serial and the old Mac's paths). The transaction is unchanged: verified backup of
the four live files -> atomic replace under a rw remount -> begetctl restart of foundation -> verify root and
foundation-root SHA plus a non-stale libbms mapping. Differences: --serial (must be in knowledge/boards.json),
--kit (the package dir holding manifest.json + the two libraries), paths from lab_paths, and
--accept-baseline for a board whose starting pair is not the manifest's baseline (a clean board brought up
elsewhere): the operator names the exact starting hashes, which are recorded in the state file.

    swap_installer.py {dry-run|apply|update|restart|verify|rollback} --serial <s> [--kit DIR] [--lane L]
                      [--accept-baseline LIBBMS_SHA:LIBAPK_SHA]
"""
import argparse,hashlib,json,shlex,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import lab_paths
MASTER=lab_paths.harness()
sys.path.insert(0,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch'))
import bms_batch as b
REMOTE='/data/local/tmp/installer-background-launcher'
q=shlex.quote
SERIAL=KIT=MANIFEST=LIBS=PATHS=BASE=None

def checked_hashes(board,paths):
 rc,text=board.shell('sha256sum '+' '.join(map(q,paths)))
 got={line.split()[-1]:line.split()[0] for line in text.splitlines() if len(line.split())==2 and len(line.split()[0])==64}
 if set(got)!=set(paths):raise RuntimeError('incomplete hashes')
 return got

def backup_name(path):return REMOTE+'/backup/'+path.replace('/','_')

def main():
 global SERIAL,KIT,MANIFEST,LIBS,PATHS,BASE
 p=argparse.ArgumentParser();p.add_argument('action',choices=['apply','update','restart','verify','rollback','dry-run'])
 p.add_argument('--serial',required=True,choices=sorted(lab_paths.boards('oh')))
 p.add_argument('--kit',type=Path,default=lab_paths.workspaces()/'westlake-installer-background-launcher-6aadb8b4')
 p.add_argument('--lane',default='outer');p.add_argument('--accept-baseline',default=None);a=p.parse_args()
 SERIAL=a.serial;KIT=a.kit.resolve();MANIFEST=json.loads((KIT/'manifest.json').read_text());LIBS=MANIFEST['candidate']
 PATHS=[d+'/'+n for n in LIBS for d in ['/system/lib64','/system/lib64/platformsdk']]
 BASE=lab_paths.workspaces()/'westlake-generation-state'/SERIAL/'installer-background-launcher'
 baseline=dict(MANIFEST['baseline'])
 if a.accept_baseline:
  bms_sha,apk_sha=a.accept_baseline.split(':');baseline={'libbms.z.so':bms_sha,'libapk_installer.so':apk_sha}
 sources={n:KIT/n for n in LIBS}
 if a.action in ['apply','update','dry-run']:
  for n,s in sources.items():
   if b.sha(s)!=LIBS[n]:raise RuntimeError('candidate changed: '+n)
 if a.action=='dry-run':
  print(json.dumps({'serial':SERIAL,'paths':PATHS,'candidate_sha256':LIBS,'backup':REMOTE+'/backup','device_io':False},indent=2));return
 out=BASE/(a.action+'-'+str(time.time_ns()));out.mkdir(parents=True)
 board=b.Board(SERIAL,'/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc',str(lab_paths.tools()/'board_note.sh'),a.lane,out)
 board.ready();statepath=BASE/'state.json';state=json.loads(statepath.read_text()) if statepath.exists() else None
 if a.action=='apply':
  if state is not None:raise RuntimeError('existing deployment state; verify or roll back explicitly')
  before=checked_hashes(board,PATHS)
  assert all(before[x]==baseline[Path(x).name] for x in PATHS), 'baseline service library changed (use --accept-baseline for a board that starts elsewhere)'
  runtime_before=checked_hashes(board,['/system/bin/appspawn-x','/system/android/framework/oh-adapter-runtime.jar','/system/android/lib64/liboh_adapter_bridge.so'])
  state={'runtime_before':runtime_before,'serial':SERIAL,'boot_before':board.boot,'before':before,'candidate':{x:LIBS[Path(x).name] for x in PATHS},'status':'backing_up','remote':REMOTE,'accepted_baseline':a.accept_baseline,'kit':str(KIT)}
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
    tmp=dest+'.b89-new'
    board.shell('cp -p '+q(source)+' '+q(tmp)+' && chmod 0755 '+q(tmp)+' && chown root:root '+q(tmp)+' && chcon u:object_r:system_lib_file:s0 '+q(tmp)+' && mv -f '+q(tmp)+' '+q(dest))
   assert checked_hashes(board,PATHS)==expected
  except Exception:
   if a.action != 'rollback':
    for dest in PATHS:
     source=backup_name(dest);tmp=dest+'.b89-rollback'
     board.shell('cp -p '+q(source)+' '+q(tmp)+' && chmod 0755 '+q(tmp)+' && chown root:root '+q(tmp)+' && chcon u:object_r:system_lib_file:s0 '+q(tmp)+' && mv -f '+q(tmp)+' '+q(dest),required=False)
    state['status']='apply_failed_rollback_attempted';b.save(statepath,state)
   raise
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
