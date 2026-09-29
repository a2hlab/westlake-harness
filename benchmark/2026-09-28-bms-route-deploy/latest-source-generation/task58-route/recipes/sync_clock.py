from pathlib import Path
import sys,time,json
R=Path(__file__).resolve().parents[5];sys.path.insert(0,str(R/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
out=Path.home()/'a2hlab/board/b6-task58-route-clock';out.mkdir(exist_ok=False);tools=R.parent/'westlake-inputs/tools'
board=b.Board('5ea34a4500000000000000001123012c',str(tools/'hdc_mac.sh'),'mac '+str(tools/'board_note.sh'),'cx-t0',out/'commands');board.ready();assert board.boot=='e36781a9-2ba1-4804-b8e5-2a1125c39a47'
_,before=board.shell('date +%s');epoch=int(time.time());board.shell('date -s @'+str(epoch));_,after=board.shell('date +%s');assert abs(int(after)-int(time.time()))<5
b.save(out/'result.json',{'boot':board.boot,'before_epoch':int(before),'host_epoch':epoch,'after_epoch':int(after),'before_skew_seconds':int(before)-epoch})
print('clock synchronized',int(before)-epoch)
