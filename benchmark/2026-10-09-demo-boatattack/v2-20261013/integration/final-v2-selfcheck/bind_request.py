#!/usr/bin/env python3
"""Bind actual postinstall plan and optional independently collected WMS observation. Local only."""
import argparse
from pathlib import Path
import compile_selfcheck as c

def main():
    p=argparse.ArgumentParser();p.add_argument('--template',type=Path,required=True);p.add_argument('--plan',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--running-parameter-evidence',type=Path);p.add_argument('--current-boot');a=p.parse_args()
    q=c.read(a.template);plan=c.read(a.plan)
    c.need(plan['serial']==q['serial'] and plan.get('synthetic',False) is False,'actual plan serial/provenance')
    c.need(type(plan.get('boat_uid')) is int and plan['boat_uid']>20000000,'actual installed Boat UID')
    c.need(bool(a.running_parameter_evidence)==bool(a.current_boot),'running observation and independent current boot must be supplied together')
    q['placement_plan']=c.pinned(a.plan)
    if a.running_parameter_evidence:q.update(running_parameter_evidence=c.pinned(a.running_parameter_evidence),current_boot=a.current_boot)
    c.save(a.out,q);print('REQUEST_BOUND_DISABLED; compiler must still admit all inputs')
if __name__=='__main__':main()
