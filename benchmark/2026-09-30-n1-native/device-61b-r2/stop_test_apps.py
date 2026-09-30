from pathlib import Path
import sys,json
R=Path(__file__).resolve().parent
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
board=b.Board('61b0657200000000000000000324012c','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','cx-t0',R/'stop/commands');board.ready()
for pkg in ['org.schabi.newpipe','org.isoron.uhabits','com.beemdevelopment.aegis','com.looker.droidify','is.xyz.mpv','chat.fluffy.fluffychat','app.alextran.immich','com.tombursch.kitchenowl','deckers.thibault.aves.libre','com.adilhanney.saber','org.localsend.localsend_app']:
 data=b.parse_bundle(board.shell('bm dump -n '+pkg,required=False)[1],pkg)
 if data['uid'] is not None:
  if not b.cold_stop(board,pkg,data['uid'],R/'stop',pkg):raise RuntimeError('cold stop '+pkg)
