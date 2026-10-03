"""Require fresh per-process crypto PASS for both U14 smoke controls."""
import argparse
import importlib.util
import json
import os
from pathlib import Path

H=Path(__file__).resolve().parent
W=Path(os.environ.get('WORKSPACES',H.parents[2]))
S=W/'westlake-harness/benchmark/2026-10-03-u13-stage-a-plan/process_selftest.py'
spec=importlib.util.spec_from_file_location('u14_schema2',S)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

def check(root):
    data=m.report(root)
    controls={k:[r for r in data['runs'] if r['key']==k] for k in ['helloworld','zigzag']}
    selected=[r for rows in controls.values() for r in rows]
    passed=all(controls.values()) and all(r['status']=='PASS' and r['error_count']==0 for r in selected)
    return {'schema':1,'source_schema':2,'passed':bool(passed),'controls':controls,
            'selftest_error_count':sum(r['selftest_error_count'] for r in selected),
            'badtag_count':sum(r['badtag_count'] for r in selected),
            'probe_error_count':sum(r['probe_error_count'] for r in selected),
            'unknown_runs':sum(r['status']=='unknown' for r in selected)}

def main():
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);p.add_argument('--out',type=Path)
    a=p.parse_args();data=check(a.root);body=json.dumps(data,indent=2)+'\n'
    if a.out:a.out.write_text(body)
    print(body,end='');return 0 if data['passed'] else 1

if __name__=='__main__':raise SystemExit(main())
