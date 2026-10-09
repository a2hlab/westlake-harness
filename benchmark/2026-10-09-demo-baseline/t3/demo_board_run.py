#!/usr/bin/env python3
"""Reuse master board_run lock/smoke/finally; only swap the demo batch adapter."""
import hashlib,importlib.util,json,os,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
WS=Path(os.environ.get('WORKSPACES',str(HERE.parents[3])))
p=WS/'westlake-harness/scripts/lab/board_run.py';s=importlib.util.spec_from_file_location('master_runner',p);m=importlib.util.module_from_spec(s);s.loader.exec_module(m)
plan=json.loads(Path(sys.argv[1]).read_text())
if plan['serial']!='61b0657200000000000000000324012c':raise SystemExit('61b only')
os.environ['DEMO_T3_MODE']=plan.get('demo_mode','launch');os.environ['DEMO_T3_SECONDS']=str(plan.get('demo_capture_seconds',20))

if plan.get('demo_install_index'):os.environ['DEMO_INSTALL_INDEX']=m.expand(plan['demo_install_index'])
if plan.get('demo_shot_tiers'):
 tiers=m.expand(plan['demo_shot_tiers']);digest=plan['demo_shot_tiers_sha256']
 if hashlib.sha256(Path(tiers).read_bytes()).hexdigest()!=digest:raise SystemExit('REFUSE: shot tier SHA drift; no lock taken')
 os.environ['DEMO_SHOT_TIERS']=tiers;os.environ['DEMO_SHOT_TIERS_SHA']=digest
os.environ['DEMO_ABILITY_PINS']=json.dumps(plan.get('demo_ability_pins',{}))
m.BATCH=HERE/'batch_adapter.py'
# master --detach would respawn master and lose the adapter; detach this entrypoint.
if '--detach' in sys.argv:
 import subprocess
 out=Path(m.expand(plan['out']));log=out.parent/(out.name+'.board-run.log')
 if plan.get('execution_enabled') is not True:raise SystemExit('REFUSE: disabled; no lock taken')
 if out.exists() or log.exists():raise SystemExit('REFUSE: fresh out and log required')
 problem=m.precheck_problem(plan.get('offline_precheck')) or m.silent_probe_problem(plan.get('offline_precheck'),m.expand(plan['smoke_spec']))
 if problem:raise SystemExit('REFUSE: '+problem)
 out.parent.mkdir(parents=True,exist_ok=True)
 with log.open('w') as f:c=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),sys.argv[1]],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,start_new_session=True)
 print('demo_board_run detached:',c.pid,'log',log)
else:raise SystemExit(m.main(sys.argv[1:]))
