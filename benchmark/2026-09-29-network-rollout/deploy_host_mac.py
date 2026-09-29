#!/usr/bin/env python3
"""Use the existing generation verifier/replacer with direct Mac HDC transport."""
import argparse,sys,types
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/lab'))
import deploy_generation as d
sys.path.insert(0,'/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-28-bms-route-deploy/batch')
import bms_batch as b
HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
LOCK='/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/board_note.sh'
class MacBoard(b.Board):
    def __init__(self,serial,hdc,lock,lane,out):super().__init__(serial,HDC,LOCK,lane,out)
p=argparse.ArgumentParser();p.add_argument('serial',choices=['61b0657200000000000000000324012c','5cd1e3dd00000000000000000923012c']);p.add_argument('package',type=Path);p.add_argument('--rollback',action='store_true');p.add_argument('--replay',action='store_true');a=p.parse_args()
a.package=a.package.resolve();a.state_root=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state');a.lane='cx-t0';a.tools=str(Path(LOCK).parent)
module=types.SimpleNamespace(**{k:getattr(b,k) for k in dir(b)});module.Board=MacBoard
job=d.Deployment(a,d.load_package(a.package),module)
if a.rollback:job.rollback_single()
elif a.replay:job.deploy()
else:job.replace('/system/bin/appspawn-x')
print(job.statepath,job.d['status'],job.out,flush=True)
