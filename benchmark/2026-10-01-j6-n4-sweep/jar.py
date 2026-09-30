#!/usr/bin/env python3
"""Capture U3 J3 ownership, expose the package JAR, deploy J6 and verify both process views."""
from pathlib import Path
import argparse,hashlib,json,shlex,sys,time,uuid
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab'));import lab_paths
sys.path.insert(0,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
p=argparse.ArgumentParser();p.add_argument('board',choices=['5ea','61b']);p.add_argument('action',choices=['capture','expose','j5b','j3','j6','baseline','final']);a=p.parse_args()
serial=next(s for s in lab_paths.boards('oh') if s.startswith(a.board));out=HERE/a.board/(a.action+'-'+str(time.time_ns()));out.mkdir(parents=True)
board=b.Board(serial,str(ROOT/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),'cx-t0',out/'commands');board.ready()
TARGET='/system/android/framework/oh-adapter-runtime.jar';BASE='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554';J5='ce2c3baf7586b3a6f50202fc4b8a75740cbf5beb7e953ab97693566f1d2c3652';J3='75c2068ca9818ea8a61cd2d7e258ef70b36fb426c87036f2f8e2c472d47e6697'
def shell(cmd):return board.shell(cmd)[1]
def sha(path):return shell('sha256sum '+shlex.quote(path)).split()[0]
def top():return {l.split()[4]:l.split()[3] for l in shell('cat /proc/self/mountinfo').splitlines()}.get(TARGET)
receipt=HERE/a.board/'jar-original.json'
if a.action=='capture':
 assert not receipt.exists()
 assert sha(TARGET)==J3
 mount=top();assert mount and mount.startswith('/local/tmp/') and mount.endswith('/oh-adapter-runtime.jar')
 source='/data'+mount;assert sha(source)==J3
 data={'serial':serial,'boot_id':board.boot,'source':source,'mount_root':mount,'sha256':J3}
 b.save(receipt,data)
else:
 data=json.loads(receipt.read_text());assert data['boot_id']==board.boot
 if a.action=='expose':
  assert sha(TARGET)==J3 and top()==data['mount_root']
  shell('umount '+TARGET);assert sha(TARGET)==BASE
 elif a.action in ['j5b','j3','j6']:
  assert sha(TARGET)==BASE
  source=data['source'];digest=J5
  if a.action=='j3':
   source=data['source'];digest=J3
  if a.action=='j6':
   local=lab_paths.workspaces()/'vm-copies/j6-2488052f/oh-adapter-runtime.jar'
   digest='2488052f029909165c841d8fb6fc207bfb67b16c57f447f5a044ebe6f1238eca'
   assert hashlib.sha256(local.read_bytes()).hexdigest()==digest
   source='/data/local/tmp/j6-n4-'+uuid.uuid4().hex+'/oh-adapter-runtime.jar'
   shell('mkdir -p '+str(Path(source).parent));board.send(local,source)
   shell('chmod 0644 '+source+' && chcon u:object_r:system_file:s0 '+source)
  assert sha(source)==digest
  shell('mount --bind '+source+' '+TARGET);assert sha(TARGET)==digest
  parents=[p for p in b.processes(shell('ps -A -o PID,PPID,UID,NAME')) if p['name']=='appspawn-x' and p['uid']==0];assert len(parents)==1
  assert sha(f"/proc/{parents[0]['pid']}/root"+TARGET)==digest
  data.update(new_source=source,new_sha256=digest)
 else:
  package=lab_paths.workspaces()/('westlake-generation-n2-51a78bde' if a.action=='baseline' else 'westlake-generation-n4-1617080a')/'package.json';m=json.loads(package.read_text())
  expected=dict(m['live_hashes']);expected[TARGET]=J3 if a.action=='baseline' else '2488052f029909165c841d8fb6fc207bfb67b16c57f447f5a044ebe6f1238eca'
  expected.update({'/system/lib64/libbms.z.so':'6aadb8b4ca9ad7d1dbaf6d99ca70f4603e3e7a2ec152fb60aee49137751afbf9','/system/lib64/libapk_installer.so':'7048c7c50a828fc744b5f06e4e9ec50ac317a2272f33789249fc63e43a655a18'})
  parents=[p for p in b.processes(shell('ps -A -o PID,PPID,UID,NAME')) if p['name']=='appspawn-x' and p['uid']==0];assert len(parents)==1
  pid=parents[0]['pid'];both=dict(expected);both.update({f'/proc/{pid}/root'+p:h for p,h in expected.items()})
  actual={l.split()[1]:l.split()[0] for l in shell('sha256sum '+' '.join(map(shlex.quote,both))).splitlines()};assert actual==both
  fp=b.runtime_fingerprint(board,out)
  if a.action=='baseline':assert fp=='0b81cdbe0ed9',fp
  data.update(verified=True,actual=actual,paths_per_view=len(expected),fingerprint=fp,parent_pid=pid)
data.update(action=a.action,live_sha256=sha(TARGET),live_mount_root=top());b.save(out/'receipt.json',data)
print(json.dumps({'receipt':str(out/'receipt.json'),'action':a.action,'sha256':data['live_sha256'],'fingerprint':data.get('fingerprint')}),flush=True)
