#!/usr/bin/env python3
"""Run master batch controls and the three assigned apps on one locked board."""
import argparse,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('board',choices=['5cd','61b']);a=p.parse_args()
serial={'5cd':'5cd1e3dd00000000000000000923012c','61b':'61b0657200000000000000000324012c'}[a.board]
master='/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
base=['python3',master,'--execute','--serial',serial,'--lane','cx-t0','--hdc-cmd','/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','--lock-cmd','mac /Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh','--out',str(ROOT/'runs'),'--launch-only','--hilog','20','--shots','5,20','--focus-check']
rc=subprocess.call(base+['--manifest',str(ROOT.parents[0]/'2026-09-29-network-rollout/controls.json'),'--keys','helloworld,zigzag','--input-root','/Users/zhaoyue/orca/workspaces/westlake-b90-controls-inputs','--run-id','v3c-next-r17m-controls-'+a.board])
if rc not in (0,1):sys.exit(rc)
rc=subprocess.call(base+['--keys','fd-auxio,fd-netguard,fd-droidify','--run-id','v3c-next-r17m-apps-'+a.board])
sys.exit(rc)
