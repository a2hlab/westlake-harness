#!/usr/bin/env python3
"""Persist offline checks before executing; never dispatch devices or runtime builds."""
import datetime,json,os,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
def main():
    out=HERE/'.private/checks-01';out.mkdir(exist_ok=False)
    commands=[('binding',['python3',str(HERE/'test_binding.py')]),('u7-python',['python3',str(ROOT/'benchmark/2026-10-01-u7-executor/test_executor.py')]),('rust',['cargo','test','--manifest-path',str(ROOT/'tools/spec-checks/Cargo.toml'),'--test','u7_start_manifest_binding','--test','u7_executor','--test','selinux_label_recipe'])]
    records=[]
    for tag,argv in commands:
        record={'argv':argv,'started':datetime.datetime.now().astimezone().isoformat(),'runtime_build':False,'device_io':False};(out/(tag+'.argv.json')).write_text(json.dumps(record,indent=2)+'\n')
        with (out/(tag+'.stdout')).open('wb') as stdout,(out/(tag+'.stderr')).open('wb') as stderr:
            result=subprocess.run(argv,cwd=ROOT,stdout=stdout,stderr=stderr,timeout=180)
        record['rc']=result.returncode;record['ended']=datetime.datetime.now().astimezone().isoformat();(out/(tag+'.receipt.json')).write_text(json.dumps(record,indent=2)+'\n');records.append(record);print(tag+' rc='+str(result.returncode),flush=True)
    (out/'records.json').write_text(json.dumps(records,indent=2)+'\n')
    return int(any(r['rc'] for r in records))
if __name__=='__main__':raise SystemExit(main())
