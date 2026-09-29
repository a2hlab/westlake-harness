from pathlib import Path
import sys,subprocess
R=Path(__file__).resolve().parents[5];sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
T=Path(__file__).resolve().parents[1];out=Path.home()/'a2hlab/board/b6-task58-route-wikipedia-debug2-config';out.mkdir(exist_ok=False);tools=R.parent/'westlake-inputs/tools'
board=b.Board('5ea34a4500000000000000001123012c',str(tools/'hdc_mac.sh'),'mac '+str(tools/'board_note.sh'),'cx-t0',out/'commands');board.ready();assert board.boot=='e36781a9-2ba1-4804-b8e5-2a1125c39a47'
_,before=board.shell('param get hilog.private.on',required=False)
board.shell('hilog -p off')
try:
 p=subprocess.run([sys.executable,str(T/'observe.py'),'--run','b6-task58-route-wikipedia-debug2-5ea','--case','wikipedia:org.wikipedia']);rc=p.returncode
finally:
 board.shell('hilog -p on')
 _,after=board.shell('param get hilog.private.on',required=False)
 b.save(out/'result.json',{'boot':board.boot,'before':before,'after':after,'restored_privacy_on':True})
sys.exit(rc)
