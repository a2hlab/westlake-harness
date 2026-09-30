#!/usr/bin/env python3
"""Run the master batch unchanged, with read-only child maps sampling."""
from pathlib import Path
import subprocess,sys,time,json
R=Path(__file__).resolve().parent
MASTER=Path('/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
sys.path.insert(0,str(MASTER));import bms_batch as b
run=sys.argv[1]; keys=sys.argv[2]
board=b.Board('61b0657200000000000000000324012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'maps'/run/'commands');board.ready()
cmd=[sys.executable,str(MASTER/'bms_batch.py'),'--execute','--serial',board.serial,'--lane','cx-t0','--hdc-cmd','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','--lock-cmd','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','--manifest',str(R.parent/'apps.json'),'--keys',keys,'--input-root','/home/zhaoyue/a2hlab/app-inputs','--out',str(R/'runs'),'--run-id',run,'--reinstall','--hilog','20','--shots','5,20','--focus-check']
p=subprocess.Popen(cmd);seen={};summary=[]
while p.poll() is None:
 try:
  rows=b.processes(board.shell('ps -A -o PID,PPID,UID,NAME')[1])
  for row in rows:
   pid=row['pid']
   if row['name']!='appspawn-x' or row['uid']==0 or seen.get(pid,0)>=8:continue
   rc,text=board.shell('cat /proc/'+str(pid)+'/maps',required=False)
   n=seen.get(pid,0);seen[pid]=n+1
   if rc==0:
    out=R/'maps'/run/(str(pid)+'-'+str(n)+'.txt');out.parent.mkdir(parents=True,exist_ok=True);out.write_text(text)
    hit='/libflutter.so' in text
    summary.append({**row,'sample':n,'maps':str(out),'engine_mapped':hit})
    if hit:seen[pid]=8
 except Exception as e:
  summary.append({'read_error':str(e)})
 time.sleep(3)
b.save(R/'maps'/run/'index.json',summary)
sys.exit(p.wait())
