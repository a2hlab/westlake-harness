#!/usr/bin/env python3
"""G13 thin wrapper around swap_installer, bms_batch.collect_app and G06 hooks.

No operation occurs without an explicit phase and an outer-enabled plan.
"""
import argparse
import json
from pathlib import Path

PHASES = ['before', 'apply', 'install', 'restore', 'reconcile']

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('phase',choices=PHASES+['inspect'])
    p.add_argument('--plan',type=Path,required=True)
    p.add_argument('--execute',action='store_true')
    a=p.parse_args(); cfg=json.loads(a.plan.read_text())
    if a.phase=='inspect':
        print(json.dumps({'execution_enabled':cfg.get('execution_enabled'), 'phases':PHASES,
                          'provider':'bms_batch.collect_app', 'missing':[k for k,v in cfg.get('bindings',{}).items() if v is None]},indent=2));return
    if not a.execute or cfg.get('execution_enabled') is not True or cfg.get('approved_by')!='outer(codex)':
        raise SystemExit('G13_REFUSE: disabled or unreviewed plan; no device operation')
    from window_impl import execute
    execute(a.phase,cfg)

if __name__=='__main__': main()
