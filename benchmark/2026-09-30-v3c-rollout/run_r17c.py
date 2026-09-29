#!/usr/bin/env python3
"""Run the baseline-JAR Auxio then two controls, using master batch."""
from pathlib import Path
import subprocess,sys
R=Path(__file__).resolve().parents[2]
MASTER='/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
OUT=R/'benchmark/2026-09-30-v3c-rollout/runs'
base=['python3',MASTER,'--execute','--serial','5cd1e3dd00000000000000000923012c','--lane','cx-t0','--hdc-cmd','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','--lock-cmd','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','--out',str(OUT),'--launch-only','--hilog','20','--shots','5,20','--focus-check']
rc=subprocess.call(base+['--keys','fd-auxio','--run-id','v3c-r17c-auxio-5cd'])
if rc not in (0,1):sys.exit(rc)
rc=subprocess.call(base+['--manifest',str(R/'benchmark/2026-09-29-network-rollout/controls.json'),'--keys','helloworld,zigzag','--input-root','/Users/zhaoyue/orca/workspaces/westlake-b90-controls-inputs','--run-id','v3c-r17c-controls-5cd'])
sys.exit(rc)
