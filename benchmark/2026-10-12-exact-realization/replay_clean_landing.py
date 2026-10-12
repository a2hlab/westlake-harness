#!/usr/bin/env python3
"""Replay the exact small delivery in a clean layout, never copy private payloads."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[1]
MODULES=['realization.py','exact_realization.py','observations.py','restore.py','sameboard.py',
         'selfcheck.py','seal_checks.py','appendix.py','test_realization.py','test_observations.py',
         'test_source_identity.py','test_sameboard.py','test_seal_checks.py','test_entrypoints.py',
         'source-fingerprint.json','request.5cd.placement.json']

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    if a.out.exists():raise ValueError('fresh replay evidence directory required')
    a.out.mkdir(parents=True)
    ws=Path(os.environ.get('WORKSPACES',str(REPO.parent))).resolve()
    start=time.time();copied=[]
    with tempfile.TemporaryDirectory(prefix='exact-clean-landing-') as temp:
        root=Path(temp)/'repo';dest=root/'benchmark'/HERE.name;dest.mkdir(parents=True)
        for name in MODULES:
            source=HERE/name;target=dest/name;shutil.copy2(source,target)
            copied.append({'path':str(target.relative_to(root)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        for name in ['demo_restore.sh','demo_selfcheck.sh']:
            source=REPO/'scripts/lab'/name;target=root/'scripts/lab'/name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
            copied.append({'path':str(target.relative_to(root)),'sha256':hashlib.sha256(source.read_bytes()).hexdigest()})
        env=dict(os.environ,WORKSPACES=str(ws),PYTHONDONTWRITEBYTECODE='1',EXACT_BASELINE_REPO=str(ws/'westlake-harness'))
        # The only external inputs are explicitly pinned main/t0/CAS and the
        # original wrapper at Git 52747bb; no t4 runtime/payload is copied.
        command=['python3','-m','unittest','discover','-p','test_*.py','-v']
        with (a.out/'tests.log').open('w') as log:
            result=subprocess.run(command,cwd=dest,env=env,stdout=log,stderr=subprocess.STDOUT)
    (a.out/'receipt.json').write_text(json.dumps({'schema':'exact-clean-landing-replay/v1','copied':copied,
        'command':command,'rc':result.returncode,'elapsed_seconds':time.time()-start,'copied_runtime_files':0,
        'device_calls':0,'external_inputs':'pinned main/t0/CAS plus main Git 52747bb wrapper baseline'},indent=2)+'\n')
    print('clean replay rc='+str(result.returncode));return result.returncode
if __name__=='__main__':raise SystemExit(main())
