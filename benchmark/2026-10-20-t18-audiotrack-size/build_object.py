#!/usr/bin/env python3
"""Preview by default; compile owner object only, never link a production DSO."""
import argparse, hashlib, json, os, subprocess
from pathlib import Path
from derive import derive, HERE
sha=lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser(); p.add_argument('--sdk',type=Path,required=True); p.add_argument('--out',type=Path,required=True); p.add_argument('--execute',action='store_true'); a=p.parse_args()
    sdk=a.sdk.resolve(); out=a.out.absolute(); compiler=sdk/'llvm/bin/clang++'
    pins=json.loads((HERE/'build-inputs.json').read_text())
    for path,expected in pins['source_pins'].items():
        if sha(HERE/path)!=expected: raise ValueError('source pin: '+path)
    for path,expected in pins['sdk_pins'].items():
        if sha(sdk/path)!=expected: raise ValueError('SDK pin: '+path)
    source=derive()
    argv=[str(compiler),'--target=aarch64-linux-ohos','--sysroot='+str(sdk/'sysroot'),'-fPIC','-O2','-std=c++17','-Wall','-Wextra','-Wno-writable-strings','-ffile-prefix-map='+str(out)+'=/build/t18','-ffile-prefix-map='+str(HERE)+'=/src/t18','-ffile-prefix-map='+str(sdk)+'=/toolchain/native','-I'+str(HERE/'source-profile/include'),'-MD','-MF',str(out/'owner.d'),'-c',str(out/'oh_audiotrack_shim.cpp'),'-o',str(out/'owner.o')]
    if not a.execute:
        print(json.dumps({'status':'PREVIEW_OBJECT_ONLY','argv':argv,'device_calls':0},indent=2)); return
    out.mkdir(parents=True,exist_ok=False)
    (out/'oh_audiotrack_shim.cpp').write_bytes(source)
    (out/'audiotrack_effective_size.inc').write_bytes((HERE/'audiotrack_effective_size.inc').read_bytes())
    (out/'argv.json').write_text(json.dumps(argv,indent=2)+'\n')
    with (out/'stdout').open('wb') as o, (out/'stderr').open('wb') as e:
        try:
            rc=subprocess.run(argv,stdout=o,stderr=e,timeout=60,env=dict(os.environ,LC_ALL='C',TZ='UTC')).returncode
        except subprocess.TimeoutExpired:
            rc=124
    (out/'rc').write_text(str(rc)+'\n')
    result={'status':'OBJECT_COMPILE_PASS_NOT_DEPLOYMENT' if rc==0 else ('COMPILE_TIMEOUT' if rc==124 else 'COMPILE_FAILED'),'rc':rc,'source_pins':pins['source_pins'],'sdk_pins':pins['sdk_pins']}
    if rc==0:
        result['object_sha256']=sha(out/'owner.o')
        # Dependency list is retained verbatim; hash every actual include as read.
        import shlex
        dep=(out/'owner.d').read_text().replace('\\\n',' ')
        paths=shlex.split(dep.split(': ',1)[1])
        result['actual_dependencies']=[{'path':x,'sha256':sha(x)} for x in paths]
    (out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'rc':rc})); raise SystemExit(rc)
if __name__=='__main__': main()
