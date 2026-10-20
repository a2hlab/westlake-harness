#!/usr/bin/env python3
"""Replay selected real compiled C cases after validating their immutable pins."""
import argparse,os,subprocess,time,json
from pathlib import Path
from check_receipt import check
P=Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--suite',choices=['layout','bounds','failures','route','ownership','regression','receipt'],required=True);a=p.parse_args()
out=Path(os.environ['T26_HOST_OUT']);check(out)
cases={'route':['wrong_caller','wrong_lock','wrong_unlock','wrong_geometry','valid'],'failures':['geometry_failure','unmap_failure','flush_failure','alloc_failure','format_refuse','precheck_failure','abort_failure','owner_release_failure'],'regression':['rgb','unknown']}
commands=([[str(out/'test_route'),x] for x in cases[a.suite]] if a.suite in cases else [[str(out/'test_yv12')]] if a.suite!='receipt' else [['python3','-m','unittest','discover','-s',str(P),'-p','test_receipt.py','-v']])
raw=P/'.private'/'selector-runs'/f'{a.suite}-{time.time_ns()}';raw.mkdir(parents=True)
for i,cmd in enumerate(commands):
 stem=raw/str(i);stem.with_suffix('.argv.json').write_text(json.dumps(cmd)+'\n')
 with stem.with_suffix('.stdout').open('wb') as so,stem.with_suffix('.stderr').open('wb') as se:r=subprocess.run(cmd,stdout=so,stderr=se)
 stem.with_suffix('.rc').write_text(str(r.returncode)+'\n');print(a.suite,i,r.returncode)
 if r.returncode:raise SystemExit(r.returncode)
