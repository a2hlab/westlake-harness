#!/usr/bin/env python3
"""Compile the original full ZipFile TU with host-only dependency shims; never execute an APK."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import time

D = Path(__file__).resolve().parent
EXACT = 'abd3c4d59217d78745a65aaa952367872354298bff5bc1ba2faae00b8f37a9cc'
SMALL = '5a56e0e39cc488e1f3b947d3801006d3b7450ec73c67f03195c64c5fd3b6bced'

def sha(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--apk',type=Path,required=True);p.add_argument('--control',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True);p.add_argument('--cxx',default=os.environ.get('CXX','clang++'))
    a=p.parse_args()
    assert sha(a.apk)==EXACT and a.apk.stat().st_size==513290344
    assert sha(a.control)==SMALL
    a.out.mkdir(parents=True,exist_ok=False)
    cxx=Path(shutil.which(a.cxx) or a.cxx).absolute()
    records=[]
    def run(tag,argv,expected):
        prefix=a.out/tag
        prefix.with_suffix('.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
        start=time.time()
        r=subprocess.run(argv,capture_output=True)
        for suffix,b in [('stdout',r.stdout),('stderr',r.stderr),('rc',str(r.returncode).encode())]:
            prefix.with_suffix('.'+suffix).write_bytes(b)
        records.append({'tag':tag,'rc':r.returncode,'expected_rc':expected,'start':start,'end':time.time()})
        (a.out/'steps.json').write_text(json.dumps(records,indent=2)+'\n')
        assert r.returncode==expected,(tag,r.returncode,r.stderr.decode(errors='replace')[-1000:])
    run('compiler-version',[str(cxx),'--version'],0)
    base=[str(cxx),'-std=c++17','-include',str(D/'host-shims/platform.h'),
          '-I'+str(D/'host-shims'),'-I'+str(D/'sources')]
    for variant,source in [('original','zip_file.cpp'),('compatible','zip_file.comment-compatible.cpp')]:
        run('compile-'+variant,base+[str(D/'sources'/source),str(D/'harness.cpp'),'-lz','-o',str(a.out/variant)],0)
    # Separate malformed fixture; the original signed APK is never written.
    with a.apk.open('rb') as f:(a.out/'truncated-prefix.apk').write_bytes(f.read(1024))
    for variant in ['original','compatible']:
        for name,file,expected in [('genshin',a.apk,2 if variant=='original' else 0),
                                   ('notes',a.control,0),('truncated',a.out/'truncated-prefix.apk',2)]:
            run(variant+'-'+name,[str(a.out/variant),str(file)],expected)
    assert sha(a.apk)==EXACT and sha(a.control)==SMALL
    receipt={'status':'OFFLINE_OPEN_BOUNDARY_REPRODUCED','deployment':'NOT_BUILT_NOT_TESTED',
             'apk_sha256':EXACT,'control_sha256':SMALL,'compiler_sha256':sha(cxx),
             'source_pins':{str(f.relative_to(D)):sha(f) for folder in ['sources','host-shims']
                            for f in sorted((D/folder).iterdir()) if f.is_file()},
             'steps':records,'artifacts':{v:sha(a.out/v) for v in ['original','compatible']},
             'limits':'host nonparallel ZipFile::Open only; shims do not replace parser logic; no device install proof'}
    (a.out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(receipt))

if __name__=='__main__':main()
