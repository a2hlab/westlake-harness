#!/usr/bin/env python3
from common import *
import argparse,subprocess
p=argparse.ArgumentParser();p.add_argument('run_id');p.add_argument('--controls',action='store_true');p.add_argument('--keys');a=p.parse_args()
cmd=[sys.executable,str(MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial',SERIAL,'--lane','cx-t0','--hdc-cmd',str(R/'transport/hdc_mac.sh'),'--lock-cmd','mac '+shlex.quote(str(TOOLS/'board_note.sh')),'--out',str(R/'runs'),'--run-id',a.run_id,'--hilog','20','--shots','5,20','--focus-check']
if a.controls:cmd+=['--manifest',str(R/'controls.json'),'--input-root',str(W/'westlake-b90-controls-inputs'),'--launch-only']
else:
 if not a.keys:raise ValueError('keys required')
 cmd+=['--keys',a.keys,'--reinstall']
subprocess.run(cmd,check=True)
