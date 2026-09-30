#!/usr/bin/env python3
import json,shlex,sys,time
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1];sys.path.insert(0,str(ROOT/'scripts/lab'));import lab_paths
sys.path.insert(0,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
SERIAL='5ea34a4500000000000000001123012c';TARGET='/system/android/framework/oh-adapter-runtime.jar';J6='2488052f029909165c841d8fb6fc207bfb67b16c57f447f5a044ebe6f1238eca';BASE='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'
a=sys.argv[1];out=HERE/('jar-'+a+'-'+str(time.time_ns()));out.mkdir();board=b.Board(SERIAL,str(ROOT/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),'cx-t0',out/'commands');board.ready()
def shell(c):return board.shell(c)[1]
def sha(p):return shell('sha256sum '+shlex.quote(p)).split()[0]
def top():return {l.split()[4]:l.split()[3] for l in shell('cat /proc/self/mountinfo').splitlines()}.get(TARGET)
r=HERE/'jar-original.json'
if a=='capture':
 assert not r.exists() and sha(TARGET)==J6
 mount=top();assert mount.startswith('/local/tmp/') and mount.endswith('/oh-adapter-runtime.jar')
 source='/data'+mount;assert sha(source)==J6
 d=dict(serial=SERIAL,boot_id=board.boot,source=source,mount_root=mount,sha256=J6);b.save(r,d)
else:
 d=json.loads(r.read_text());assert d['boot_id']==board.boot
 if a=='expose':
  assert sha(TARGET)==J6 and top()==d['mount_root'];shell('umount '+TARGET);assert sha(TARGET)==BASE
 elif a=='restore':
  assert sha(TARGET)==BASE and sha(d['source'])==J6
  shell('mount --bind '+shlex.quote(d['source'])+' '+TARGET);assert sha(TARGET)==J6
 elif a in ['baseline','final']:
  m=json.loads((lab_paths.workspaces()/'westlake-generation-n4-order-216b68fb/package.json').read_text());expected=dict(m['live_hashes']);expected[TARGET]=J6
  parent=[p for p in b.processes(shell('ps -A -o PID,PPID,UID,NAME')) if p['name']=='appspawn-x' and p['uid']==0];assert len(parent)==1
  expected.update({f"/proc/{parent[0]['pid']}/root"+p:h for p,h in list(expected.items())})
  actual={l.split()[1]:l.split()[0] for l in shell('sha256sum '+' '.join(map(shlex.quote,expected))).splitlines()};assert actual==expected
  fp=b.runtime_fingerprint(board,out);bf=b.boot_image_fingerprint(board,out);assert fp=='73ecf422dba2' and bf=='0876029078e2',(fp,bf)
  d.update(fingerprint=fp,boot_image_fingerprint=bf,actual=actual)
 else:raise ValueError(a)
d.update(action=a,live_sha256=sha(TARGET));b.save(out/'receipt.json',d);print(json.dumps(d))
