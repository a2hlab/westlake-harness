#!/usr/bin/env python3
"""Compile and run actual getter at a host seam; retain original raw logs."""
import argparse, hashlib, json, os, shutil, subprocess, time
from pathlib import Path
from derive import derive, HERE
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(argv,out,name):
    (out/(name+'.argv.json')).write_text(json.dumps(argv,indent=2)+'\n')
    with (out/(name+'.stdout')).open('wb') as o, (out/(name+'.stderr')).open('wb') as e:
        rc=subprocess.run(argv,stdout=o,stderr=e,timeout=60).returncode
    (out/(name+'.rc')).write_text(str(rc)+'\n')
    if rc: raise RuntimeError(name+' failed; see retained raw logs')
def main():
    p=argparse.ArgumentParser(); p.add_argument('--out',type=Path); a=p.parse_args()
    out=a.out or Path.home()/'.local/share/westlake/t18-hostchecks'/str(time.time_ns())
    out.mkdir(parents=True,exist_ok=False)
    source=derive()
    assert source.count(b'"native_get_buffer_size_frames"')==1
    original=(HERE/'source-profile/oh_audiotrack_shim.cpp').read_bytes()
    # Strip precisely the two additions to prove all existing owner bytes preserved.
    reconstructed=source.replace(b'#include "audiotrack_effective_size.inc"\n\n',b'').replace(b'\n        { {"native_get_buffer_size_frames", "()I", (void*)nGetEffectiveBufferSizeFrames}, true },',b'')
    assert reconstructed==original
    compiler=shutil.which(os.environ.get('CXX','clang++'))
    if not compiler: raise RuntimeError('host C++ compiler missing')
    run([compiler,'-std=c++17','-Wall','-Wextra','-Werror','-pthread','-I',str(HERE),str(HERE/'test_getter.cpp'),'-o',str(out/'host-test')],out,'compile')
    run([str(out/'host-test')],out,'run')
    result={'status':'HOST_SEAM_PASS_NOT_DEPLOYMENT','compiler_sha256':sha(compiler),'owner_sha256':sha(HERE/'source-profile/oh_audiotrack_shim.cpp'),'derived_owner_sha256':hashlib.sha256(source).hexdigest(),'getter_sha256':sha(HERE/'audiotrack_effective_size.inc'),'case_count':14,'owner_existing_bytes_unchanged':True}
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__': main()
