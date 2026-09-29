#!/usr/bin/env python3
"""Record, temporarily retire, and restore the exact current JAR overlay."""
import argparse,json,shlex,sys
from pathlib import Path
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
p=argparse.ArgumentParser();p.add_argument('action',choices=['capture','expose','restore']);a=p.parse_args()
serial='5cd1e3dd00000000000000000923012c';target='/system/android/framework/oh-adapter-runtime.jar'
base='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'
board=b.Board(serial,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'jar'/a.action/'commands');board.ready()
def sha(p):return board.shell('sha256sum '+shlex.quote(p))[1].split()[0]
def top():return {x.split()[4]:x.split()[3] for x in board.shell('cat /proc/self/mountinfo')[1].splitlines()}.get(target)
p=R/'jar/original.json'
if a.action=='capture':
 if p.exists():raise RuntimeError('do not overwrite original overlay receipt')
 mount=top()
 if not mount or not mount.startswith('/local/tmp/') or not mount.endswith('/oh-adapter-runtime.jar'):raise RuntimeError('unrecognized overlay mount')
 source='/data'+mount;digest=sha(target)
 if digest==base or sha(source)!=digest:raise RuntimeError('overlay source/target mismatch')
 b.save(p,{'serial':serial,'boot_id':board.boot,'source':source,'mount_root':mount,'sha256':digest,'base_sha256':base})
else:
 row=json.loads(p.read_text())
 if row['boot_id']!=board.boot:raise RuntimeError('boot changed')
 layers=row.setdefault('layers',[{k:row[k] for k in ['source','mount_root','sha256']}])
 if a.action=='expose':
  while sha(target)!=base:
   mount=top()
   if not mount or not mount.startswith('/local/tmp/') or not mount.endswith('/oh-adapter-runtime.jar'):raise RuntimeError('unrecognized underlying overlay')
   source='/data'+mount;digest=sha(target)
   if sha(source)!=digest:raise RuntimeError('underlying overlay source mismatch')
   if not any(x['mount_root']==mount for x in layers):
    layers.append({'source':source,'mount_root':mount,'sha256':digest});b.save(p,row)
   board.shell('umount '+shlex.quote(target))
  b.save(p,row)
 else:
  if sha(target)!=base:raise RuntimeError('base JAR not exposed')
  for layer in reversed(layers):
   if sha(layer['source'])!=layer['sha256']:raise RuntimeError('saved source changed')
   board.shell('mount --bind '+shlex.quote(layer['source'])+' '+shlex.quote(target))
   if sha(target)!=layer['sha256'] or top()!=layer['mount_root']:raise RuntimeError('overlay restore mismatch')
 b.save(R/'jar'/a.action/'receipt.json',{'boot_id':board.boot,'sha256':sha(target),'mount_root':top(),'layers':layers,'verified':True})
print(a.action,'verified',sha(target),flush=True)
