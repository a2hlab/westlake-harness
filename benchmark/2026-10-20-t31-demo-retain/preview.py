#!/usr/bin/env python3
"""Read-only T31 plan preview, never device execution or signature."""
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'recovery'))
from recovery_policy import data_check

def plan(repo,wid):
    d=repo/'benchmark/2026-10-20-t30-request-recovery/deployment/final-01';data_check(d)
    if wid is not None and not 0<wid<2147483648:raise ValueError('invalid WID')
    return {'status':'PREVIEW_ONLY','device_calls':0,'writes':0,'wid_input_is_offline_only':True,'wid_branch':'FRESH_REQUIRED' if wid is None else 'REUSE_EXACT_693448' if wid==29 else 'WID_DERIVATION_REQUIRED_REFUSE_EXECUTION','fresh':dict(boot=None,parent=None,parent_birth=None,host=None,host_birth=None,holder=None,start=None),'cycle_seconds':{'play':20,'pause':3,'resume':10},'cycles':2,'audio':['PENDING_CORRESPONDING_CLIP_CONFIRMATION','PENDING_CORRESPONDING_CLIP_CONFIRMATION'],'recovery':'INDEPENDENT_SUCCESSOR_OFFLINE_REVIEW_REQUIRED_LIVE_PARENT_WID29_ONLY','retain':'NOT_AUTHORIZED_PENDING_HUMAN','origin':'THIS_T31_ACTUAL_APPLY_ONLY_NOT_T30_FIXTURE','dead_parent_or_other_wid':'REFUSE_OUT_OF_SCOPE_NEEDS_SEPARATE_REVIEW','deadlines':{'experiment_stop':1200,'hard_end':1800},'steps':['fresh read + new lock/context','same-plan before518+26','frozen fresh filler + scope_apply','executor preflight/apply five backups + ABSENT','freshboot + actual identity/bindings','two exact playback cycles and two audio receipts','before1200: explicit recoverable retention signoff OR original same-window rollback','power/param restored, actual final UI, unlock','E -> archive A -> remote R -> separate final S']}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--repo',type=Path,required=True);p.add_argument('--wid',type=int);a=p.parse_args()
    try:print(json.dumps(plan(a.repo,a.wid),indent=2))
    except (ValueError,AssertionError,FileNotFoundError) as e:p.exit(1,str(e)+'\n')
if __name__=='__main__':main()
