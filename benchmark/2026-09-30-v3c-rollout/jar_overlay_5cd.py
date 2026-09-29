#!/usr/bin/env python3
"""Guarded 5cd JAR overlay transition: original r17c, package r8b, selected r17g."""
import argparse,json,shlex,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
p=argparse.ArgumentParser();p.add_argument('phase',choices=['expose','restore','new','expose-new']);a=p.parse_args()
r=json.loads((ROOT/'5cd-before-jar.json').read_text());out=ROOT/('jar-'+a.phase)
board=b.Board(r['serial'],'/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
if board.boot!=r['boot_id']:raise RuntimeError('boot differs from the received JAR overlay')
target=r['target'];source=r['remote_source']
def sha(path):return board.shell('sha256sum '+shlex.quote(path))[1].split()[0]
def top():
 text=board.shell('cat /proc/self/mountinfo')[1]
 return {x.split()[4]:x.split()[3] for x in text.splitlines()}.get(target)
if a.phase in ['new','expose-new']:
 source='/data/local/tmp/v3c-r17g-5cd/oh-adapter-runtime.jar'
 r['deployed_sha256']='a35a782e0ad255e25b4dbb9f0d84baa3c95a9730bc8e80120163735e21ba10f2'
 if a.phase=='new':
  local=Path('/Users/zhaoyue/orca/workspaces/vm-copies/r17g-a35a782e/oh-adapter-runtime.jar')
  if b.sha(local)!=r['deployed_sha256']:raise RuntimeError('new local JAR changed')
  if sha(target)!=r['baseline_sha256']:raise RuntimeError('package JAR not exposed')
  board.shell('mkdir -p /data/local/tmp/v3c-r17g-5cd')
  board.shell('test ! -e '+shlex.quote(source))
  board.send(local,source)
expected_root=source[len('/data'):]
if a.phase in ['expose','expose-new']:
 if sha(target)!=r['deployed_sha256'] or top()!=expected_root:raise RuntimeError('JAR overlay identity/owner differs')
 board.shell('umount '+shlex.quote(target))
 if sha(target)!=r['baseline_sha256']:raise RuntimeError('baseline JAR SHA mismatch')
else:
 if sha(target)!=r['baseline_sha256'] or sha(source)!=r['deployed_sha256']:raise RuntimeError('JAR restore SHA mismatch')
 if top()==expected_root:raise RuntimeError('r17b overlay already active')
 board.shell('mount --bind '+shlex.quote(source)+' '+shlex.quote(target))
 if sha(target)!=r['deployed_sha256']:raise RuntimeError('restored JAR SHA mismatch')
b.save(out/'receipt.json',{'phase':a.phase,'serial':r['serial'],'boot_id':board.boot,'target':target,'sha256':sha(target),'top_mount':top()})
print('JAR '+a.phase+' verified')
