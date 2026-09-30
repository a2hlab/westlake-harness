"""Run master batch using a pinned, merged-input manifest."""
import argparse,os,shlex,subprocess,sys
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];sys.path.insert(0,str(R/'scripts/lab'));import lab_paths
p=argparse.ArgumentParser();p.add_argument('run');p.add_argument('keys');p.add_argument('--controls',action='store_true');a=p.parse_args()
cmd=[sys.executable,str(lab_paths.harness()/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'),'--execute','--serial','61b0657200000000000000000324012c','--lane','cx-t0','--hdc-cmd',str(R/'benchmark/2026-09-30-n3-61b/transport/hdc_mac.sh'),'--lock-cmd','mac '+shlex.quote(str(lab_paths.tools()/'board_note.sh')),'--out',str(H/'runs'),'--run-id',a.run,'--hilog','20','--shots','5,20','--focus-check','--keys',a.keys]
if a.controls:cmd+=['--manifest',str(R/'benchmark/2026-09-30-n3-61b/controls.json'),'--input-root',str(lab_paths.workspaces()/'westlake-b90-controls-inputs'),'--launch-only']
else:cmd+=['--manifest',str(H/'priority-manifest.json'),'--input-root',str(H/'inputs'),'--launch-only' if a.run.startswith('n8-u5') else '--reinstall']
os.execv(sys.executable,cmd)
