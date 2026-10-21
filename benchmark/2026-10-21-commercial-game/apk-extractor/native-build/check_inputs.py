#!/usr/bin/env python3
"""Read exact local kit inputs and exercise patch application, without a native build."""
import argparse
import json
from pathlib import Path
import shlex
import shutil
import subprocess
import time
from build_native import ARCHIVE,COMPILER,ORIGINAL,CANDIDATE,COMMAND,OBJECT,LIBRARY,SRC,OBJ,TARGET,sha,require,dump

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ['kit','archive','g08-dir','out']:p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    out=a.kit/'out/wukong100';seed=a.kit/'verified-seed/private-source/oh'/SRC
    cmd=a.kit/'verified-seed/metadata/narrow-commands/zip_file.cmd'
    pins={str(a.archive):ARCHIVE,str(seed):ORIGINAL,str(cmd):COMMAND,
          str(a.kit/'prebuilts/clang/ohos/linux-x86_64/llvm/bin/clang-15'):COMPILER,
          str(out/OBJ):OBJECT,str(out/TARGET):LIBRARY,
          str(a.g08_dir/'sources/zip_file.comment-compatible.cpp'):CANDIDATE}
    actual={name:sha(Path(name)) for name in pins};dump(a.out/'input-pins.json',actual)
    require(actual==pins,'input mismatch')
    argv=shlex.split(cmd.read_text());require(len(argv)==246,'not exact 246 argv')
    require(shlex.split((out/(TARGET+'.rsp')).read_text()).count(OBJ)==1,'object not unique')
    dump(a.out/'compile-argv.json',argv)
    f=a.out/'zip_file.cpp';shutil.copyfile(seed,f)
    patch=['patch','--batch','--fuzz=0',str(f.resolve()),str((a.g08_dir/'comment-compatibility.patch').resolve())]
    dump(a.out/'patch.argv.json',patch);start=time.time()
    with (a.out/'patch.stdout').open('xb') as stdout,(a.out/'patch.stderr').open('xb') as stderr:
        r=subprocess.run(patch,stdout=stdout,stderr=stderr)
    (a.out/'patch.rc').write_text(str(r.returncode)+'\n')
    dump(a.out/'patch.time.json',{'start':start,'end':time.time()})
    require(r.returncode==0 and sha(f)==CANDIDATE,'patch did not produce exact accepted source')
    result={'status':'INPUTS_AND_PATCH_VERIFIED_NO_NATIVE_BUILD','argc':len(argv),
            'candidate_source_sha256':sha(f),'pins':actual,'patch_sha256':sha(a.g08_dir/'comment-compatibility.patch')}
    dump(a.out/'results.json',result);print(json.dumps(result))

if __name__=='__main__':main()
