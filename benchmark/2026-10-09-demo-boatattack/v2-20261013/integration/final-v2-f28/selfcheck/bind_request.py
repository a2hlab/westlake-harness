#!/usr/bin/env python3
"""Bind actual postinstall plan and optional independently collected WMS observation. Local only."""
import argparse
from pathlib import Path
import compile_selfcheck as c

def main():
    p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--running-parameter-evidence',type=Path);p.add_argument('--current-boot');p.add_argument('--base-selfcheck',type=Path);p.add_argument('--base-observation',type=Path);a=p.parse_args()
    q=c.read(a.template);plan=c.read(a.plan)
    c.need(plan['serial']==q['serial'] and plan.get('synthetic',False) is False,'actual plan serial/provenance')
    c.need(type(plan.get('boat_uid')) is int and plan['boat_uid']>20000000,'actual installed Boat UID')
    c.need(bool(a.running_parameter_evidence)==bool(a.current_boot),'running observation and independent current boot must be supplied together')
    q['placement_plan']=c.pinned(a.plan)
    # Rebind local sibling programs after exact landing; never depend on the producer worktree.
    board={'61b0657200000000000000000324012c':'board61b','5cd1e3dd00000000000000000923012c':'board5cd'}[q['serial']]
    root=c.HERE.parent/board
    q['provider_freeze']=c.pinned(root/'provider-freeze.json')
    q['programs']={role:c.pinned(root/'provider'/name) for role,name in [('executor','installer.py'),('contract','candidate_contract.py'),('identity','boat_identity.py')]}
    c.need(bool(a.base_selfcheck)==bool(a.base_observation),'base selfcheck and raw observation must be paired')
    if a.base_selfcheck:q['base'].update(selfcheck=c.pinned(a.base_selfcheck),observation=c.pinned(a.base_observation))
    if a.running_parameter_evidence:q.update(running_parameter_evidence=c.pinned(a.running_parameter_evidence),current_boot=a.current_boot)
    c.save(a.out,q);print('REQUEST_BOUND_DISABLED; compiler must still admit all inputs')
if __name__=='__main__':main()
