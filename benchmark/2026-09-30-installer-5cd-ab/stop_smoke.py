from pathlib import Path
import sys
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
out=Path(__file__).resolve().parent/'board/stop-replay-smoke'
board=b.Board('5cd1e3dd00000000000000000923012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',out/'commands');board.ready()
pkg='com.example.helloworld';uid=b.parse_bundle(board.shell('bm dump -n '+pkg)[1],pkg)['uid']
assert b.cold_stop(board,pkg,uid,out);print('HelloWorld replay smoke stopped')
