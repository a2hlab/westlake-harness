#!/usr/bin/env python3
"""Verify checkpoint integrity; production acceptance additionally requires --build-run."""
import argparse
import json
from pathlib import Path
from build_native import sha,require,OBJECT,LIBRARY,CANDIDATE
D=Path(__file__).resolve().parent

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--build-run',type=Path);a=p.parse_args()
    r=json.loads((D/'results.json').read_text());m=json.loads((D/'manifest.json').read_text());repo=D.parents[3]
    for row in m['files']:
        f=repo/row['path'];require(f.is_file() and sha(f)==row['sha256'] and f.stat().st_size==row['bytes'],'manifest drift '+row['path'])
    if a.build_run:
        b=json.loads((a.build_run/'receipt.json').read_text())
        require(b['status']=='BASELINE_IDENTICAL_CANDIDATE_BUILT','native build incomplete')
        require(b['baseline']['object_sha256']==OBJECT and b['baseline']['library_sha256']==LIBRARY,'baseline mismatch')
        require(b['candidate']['source_sha256']==CANDIDATE,'candidate source mismatch')
        for name in ['baseline','candidate']:
            require(sha(a.build_run/name/'zip_file.o')==b[name]['object_sha256'],'object mismatch')
            require(sha(a.build_run/name/'libinstalls.z.so')==b[name]['library_sha256'],'library mismatch')
            for stage in ['compile','link']:
                require((a.build_run/(name+'-'+stage+'.rc')).read_text().strip()=='0','actual compile/link failed')
        require(b['recipe_sha256']==sha(D/'build_native.py'),'recipe drift')
        print('PASS actual baseline/candidate build receipts; deployment still not authorized')
    else:
        require(r['native_build_performed'] is True and r['status']=='BASELINE_IDENTICAL_CANDIDATE_BUILT','production summary drift')
        require(r['baseline']['object_sha256']==OBJECT and r['baseline']['library_sha256']==LIBRARY,'public baseline mismatch')
        b=json.loads((D/r['actual_receipt']).read_text())
        require(b['status']==r['status'] and b['candidate']==r['candidate'],'public receipt mismatch')
        require(len(b['steps'])==13 and all(x['rc']==0 for x in b['steps']),'actual stage failure')
        require(b['recipe_sha256']==sha(D/'build_native.py'),'public recipe drift')
        require(r['apk_before_sha256']==r['apk_after_sha256'],'APK drift')
        print('PASS public actual-build receipts; use --build-run to rehash private ELF/object outputs; no device acceptance')

if __name__=='__main__':main()
