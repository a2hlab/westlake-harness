from pathlib import Path
import sys
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
T='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/'
out=Path.home()/'a2hlab/board/b87-stop-test-apps';out.mkdir(exist_ok=True)
board=b.Board('61b0657200000000000000000324012c',T+'hdc_mac.sh','mac '+T+'board_note.sh','cx-t0',out/'commands');board.ready()
for pkg in ['com.ichi2.anki','eu.faircode.netguard','org.oxycblt.auxio']:
 d=out/pkg;d.mkdir(exist_ok=True)
 _,s=board.shell('bm dump -n '+pkg);info=b.parse_bundle(s,pkg)
 assert b.cold_stop(board,pkg,info['uid'],d),pkg
 print(pkg,'stopped',flush=True)
