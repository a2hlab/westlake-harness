#!/usr/bin/env python3
"""Reconstruct the exact offline candidate from pinned T47 bytes + published diff."""
import argparse
import json
from pathlib import Path
import shutil
from replay import ROOT, PINS, logged, require, sha

PATCH_SHA = 'e3bf649c5b61016880a80645fbbcbf87876a06ab8c17bdc25daf77caff566ed9'

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    for name in ('watchdog.sh','route-b-owner.sh'):
        require(sha(ROOT/'baseline'/name)==PINS['baseline/'+name], 'baseline drift')
    require(sha(ROOT/'candidate.patch')==PATCH_SHA,'patch drift')
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False)
    data=out/'candidate';shutil.copytree(ROOT/'baseline',data)
    rc=logged(['/usr/bin/patch','-p1','-i',str(ROOT/'candidate.patch')],out/'raw',cwd=data)
    require(rc==0,'patch failed')
    for name in ('watchdog.sh','route-b-owner.sh'):
        require(sha(data/name)==PINS['candidate/'+name], 'reconstructed candidate mismatch')
    receipt={'passed':True,'patch_sha256':PATCH_SHA,'candidate_pins':{n:sha(data/n) for n in ('watchdog.sh','route-b-owner.sh')},'rc':rc}
    (out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(receipt))
if __name__=='__main__':main()
