#!/usr/bin/env python3
"""Run the T49 real entry and its refusal checks into a fresh persistent directory."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from replay import ROOT, logged, require, sha

def snapshot(root):
    return {str(f.relative_to(root)):sha(f) for f in root.rglob('*') if f.is_file()}

def check(out):
    out.mkdir(parents=True,exist_ok=False)
    runner=str(ROOT/'replay.py')
    run=out/'replay'
    positive=[sys.executable,runner,'--out',str(run)]
    require(logged(positive,out/'positive')==0,'actual replay failed')
    receipt=json.loads((run/'receipt.json').read_text())
    require(receipt['passed'] and receipt['executions']==8,'eight executions missing')
    before=snapshot(run)
    require(logged(positive,out/'old-output')!=0,'old output accepted')
    require(snapshot(run)==before,'old output changed on refusal')
    require('FileExistsError' in (out/'old-output/stderr').read_text(),'wrong old-output refusal')
    bad=out/'bad-sources';bad.mkdir()
    for variant in ('baseline','candidate'):
        shutil.copytree(ROOT/variant,bad/variant)
    drift=bad/'candidate/route-b-owner.sh'
    drift.write_bytes(drift.read_bytes()+b'# synthetic source drift\n')
    for name,flags in [('bad-pin',[]),('bad-pin-optimized',['-O'])]:
        target=out/(name+'-output')
        argv=[sys.executable,*flags,runner,'--sources',str(bad),'--out',str(target)]
        require(logged(argv,out/name)!=0,'drift accepted: '+name)
        require(not target.exists(),'drift produced output: '+name)
        require('source pin mismatch: candidate/route-b-owner.sh' in (out/name/'stderr').read_text(),'wrong source refusal')
    broken=out/'missing-trace';shutil.copytree(run,broken)
    trace=broken/'baseline/first_missing/trace.jsonl'
    lines=trace.read_text().splitlines()
    removed=False
    kept=[]
    for line in lines:
        event=json.loads(line)
        if not removed and event.get('event')=='birth' and event.get('pid')=='42' and event.get('rc')==1:
            removed=True
        else:kept.append(line)
    require(removed,'actual failure trace to remove was absent')
    trace.write_text('\n'.join(kept)+'\n')
    broken_before=snapshot(broken)
    argv=[sys.executable,runner,'--verify-only','--out',str(broken)]
    require(logged(argv,out/'missing-trace-check')!=0,'missing adjacent read accepted')
    require('required adjacent birth sequence not covered' in (out/'missing-trace-check/stderr').read_text(),'wrong missing-trace refusal')
    require(snapshot(broken)==broken_before,'verify-only changed evidence')
    require(snapshot(run)==before,'negative checks changed accepted replay')
    result={'passed':True,'executions':8,'checks':['four_timings_times_two_actual_main_sources','old_output_refused_unchanged',
        'candidate_source_drift_refused_before_output','same_drift_refused_under_python_O',
        'actual_missing_failure_trace_refused_without_mutation'],
        'source_drift_sha256':sha(drift),'replay_receipt_sha256':sha(run/'receipt.json'),
        'scope':'All case and checker subprocess streams/timestamps remain in this persistent output directory.'}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args()
    destination=a.out or ROOT/'.private'/('checks-'+str(time.time_ns()))
    check(destination.resolve())
