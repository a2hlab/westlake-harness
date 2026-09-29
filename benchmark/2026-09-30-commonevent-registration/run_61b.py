#!/usr/bin/env python3
"""Run the requested five applications then two controls, using master batch."""
from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[2]
MASTER='/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
OUT=R/'benchmark/2026-09-30-commonevent-registration/runs'
base=['python3',MASTER,'--execute','--serial','61b0657200000000000000000324012c','--lane','cx-t0','--hdc-cmd','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','--lock-cmd','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','--out',str(OUT),'--launch-only','--hilog','20','--shots','5,20','--focus-check']
rc=subprocess.call(base+['--keys','vlc,fd-gallery,fd-etar,termux,fd-auxio','--run-id','b91-ce-gapfill-r17b-61b'])
if rc not in (0,1):sys.exit(rc)
rc=subprocess.call(base+['--manifest',str(R/'benchmark/2026-09-29-network-rollout/controls.json'),'--keys','helloworld,zigzag','--input-root','/Users/zhaoyue/orca/workspaces/westlake-b90-controls-inputs','--run-id','b91-ce-gapfill-controls-61b'])
sys.exit(rc)
