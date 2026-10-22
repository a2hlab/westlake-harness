#!/usr/bin/env python3
"""Fresh persistent actual entry + identical normal/-O negative receipts."""
import argparse
import json
from pathlib import Path
import shutil
import sys
import time
from replay import ROOT, CASES, logged, require, sha

def snapshot(root):
    result={}
    for p in sorted(root.rglob('*')):
        name=str(p.relative_to(root))
        if p.is_symlink():result[name]=['symlink',p.readlink().as_posix()]
        elif p.is_file():result[name]=['file',sha(p)]
        elif p.is_dir():result[name]=['directory']
    return result

def check(out):
    out.mkdir(parents=True,exist_ok=False)
    runner=str(ROOT/'replay.py');run=out/'replay'
    require(logged([sys.executable,runner,'--out',str(run)],out/'positive')==0,'actual replay failed')
    receipt=json.loads((run/'receipt.json').read_text())
    require(receipt['passed'] and receipt['executions']==len(CASES)*2,'missing executions')
    before=snapshot(run)
    bad=out/'bad-sources';bad.mkdir()
    for v in ('baseline','candidate'):shutil.copytree(ROOT/v,bad/v)
    drift=bad/'candidate/route-b-owner.sh';drift.write_bytes(drift.read_bytes()+b'# synthetic drift\n')
    broken=out/'missing-trace';shutil.copytree(run,broken,symlinks=True)
    trace=broken/'candidate/first_birth_missing/trace.jsonl'
    rows=[json.loads(x) for x in trace.read_text().splitlines()]
    kept=[x for x in rows if x['event']!='classification_parent_listing']
    require(len(rows)>len(kept),'actual classification trace missing before removal')
    trace.write_text(''.join(json.dumps(x)+'\n' for x in kept))
    broken_before=snapshot(broken)
    negatives=[]
    for label,flags in [('normal',[]),('optimized',['-O'])]:
        tests=[('old-output',['--out',str(run)],'FileExistsError'),
               ('bad-pin',['--sources',str(bad),'--out',str(out/(label+'-must-not-exist'))],'source pin mismatch: candidate/route-b-owner.sh'),
               ('missing-trace',['--verify-only','--out',str(broken)],'required classification trace missing')]
        for name,args,error in tests:
            log=out/(label+'-'+name)
            rc=logged([sys.executable,*flags,runner,*args],log)
            require(rc!=0 and error in (log/'stderr').read_text(),'wrong refusal '+label+' '+name)
            negatives.append({'mode':label,'case':name,'rc':rc,'raw':{n:{'sha256':sha(log/n),'size':(log/n).stat().st_size} for n in ('argv.json','start','end','stdout','stderr','rc')}})
        require(not (out/(label+'-must-not-exist')).exists(),'bad source ran')
    require(snapshot(run)==before,'accepted output changed by refusal')
    require(snapshot(broken)==broken_before,'verify-only changed bad receipt')
    result={'passed':True,'executions':len(CASES)*2,'case_count':len(CASES),'negative_checks':negatives,
            'source_drift_sha256':sha(drift),'replay_receipt_sha256':sha(run/'receipt.json'),
            'raw_scope':'Every local shell and checker invocation has durable argv/start/end/stdout/stderr/rc. Rust also uses persistent .private output.'}
    (out/'checks.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'passed':True,'executions':len(CASES)*2,'negative_checks':len(negatives),'receipt':str(out/'checks.json')}))
if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path);a=ap.parse_args()
    check((a.out or ROOT/'.private'/('checks-'+str(time.time_ns()))).resolve())
