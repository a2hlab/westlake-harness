#!/usr/bin/env python3
"""Guarded, boot-bound Java overlay transitions for this two-board rollout."""
import argparse, json, shlex, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
ROWS={
 '61b':('61b0657200000000000000000324012c','6fd44228-d33e-4f0e-9bf9-9a34842c72bf','r17b-61b','8636782cc919e6c1d4f4c70311bc102092e22fb83ebbc638a99bb17c96bdbc62'),
 '5cd':('5cd1e3dd00000000000000000923012c','a42f2d6c-d29d-40aa-8145-51b4f85d0187','r17c-5cd','2b201bda4655fb36498d87b64c0389249b96e04a74f3e42567e5633f2a27bae1')}
BASE='d5000c4e19e74e3ec7a72300ed425fa2c5ba521aa4b04cb6e688e165e6ba5554'
NEW='a5cbd8d77ad7cb1592db5d64f9ec1f7ce7da9732fdbe8c4b180c8fa1ea95c2e7'
LOCAL=Path('/Users/zhaoyue/orca/workspaces/vm-copies/r17m-a5cbd8d7/oh-adapter-runtime.jar')
TARGET='/system/android/framework/oh-adapter-runtime.jar'
p=argparse.ArgumentParser();p.add_argument('board',choices=ROWS);p.add_argument('action',choices=['expose-old','expose-new','install-new','restore-old']);p.add_argument('--tag',default='first');a=p.parse_args()
serial,boot,old_dir,old_sha=ROWS[a.board]
out=ROOT/a.board/(a.action+'-'+a.tag)
board=b.Board(serial,'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
if board.boot!=boot:raise RuntimeError('boot changed')
def sha(path):return board.shell('sha256sum '+shlex.quote(path))[1].split()[0]
def top():return {x.split()[4]:x.split()[3] for x in board.shell('cat /proc/self/mountinfo')[1].splitlines()}.get(TARGET)
old_source='/data/local/tmp/'+old_dir+'/oh-adapter-runtime.jar'
new_source='/data/local/tmp/v3c-next-r17m-'+a.board+'/oh-adapter-runtime.jar'
source,digest=(old_source,old_sha) if a.action.endswith('old') else (new_source,NEW)
b.save(out/'before.json',{'serial':serial,'boot_id':boot,'sha256':sha(TARGET),'mount_root':top(),'old_source':old_source,'old_sha256':old_sha})
if a.action.startswith('expose'):
 if sha(TARGET)!=digest or top()!=source[len('/data'):]:raise RuntimeError('overlay identity/owner mismatch')
 board.shell('umount '+shlex.quote(TARGET))
 if sha(TARGET)!=BASE:raise RuntimeError('underlying package JAR mismatch')
else:
 if sha(TARGET)!=BASE:raise RuntimeError('package JAR not exposed')
 if a.action=='install-new':
  if b.sha(LOCAL)!=NEW:raise RuntimeError('local JAR changed')
  board.shell('mkdir -p '+shlex.quote(str(Path(source).parent)))
  rc,_=board.shell('test -e '+shlex.quote(source),required=False)
  if rc:board.send(LOCAL,source)
 if sha(source)!=digest:raise RuntimeError('overlay source SHA mismatch')
 board.shell('mount --bind '+shlex.quote(source)+' '+shlex.quote(TARGET))
 if sha(TARGET)!=digest:raise RuntimeError('overlay readback mismatch')
b.save(out/'receipt.json',{'serial':serial,'boot_id':boot,'action':a.action,'sha256':sha(TARGET),'mount_root':top()})
print(a.board,a.action,'verified',sha(TARGET),flush=True)
