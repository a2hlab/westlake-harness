#!/usr/bin/env python3
"""Run once on hw248 in a NEW directory, using exact frozen inputs/argv.
A private mount namespace redirects only the embedded output path to fresh files.
No originals are edited. A mismatch never updates a bundle or reference image.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()


def inventory(directory,names):return {n:sha(directory/n) for n in names}
def save(path,data):path.write_text(json.dumps(data,indent=2)+'\n')
def now():return datetime.datetime.now().astimezone().isoformat()


def main():
    p=argparse.ArgumentParser();p.add_argument('--config',type=Path,required=True);p.add_argument('--work',type=Path,required=True);p.add_argument('--child',action='store_true');a=p.parse_args()
    c=json.loads(a.config.read_text());work=a.work.resolve()
    tools=c['frozen_tools'];receipt=c['reference'];inputs=Path(receipt['paths']['inputs']);original=Path(receipt['paths']['outputs'])
    command=shlex.split(receipt['build_command']);dex=Path(command[0]);script=Path(next(k for k in tools if k.endswith('t5_gen_image.sh')))
    for path,digest in tools.items():
        if sha(path)!=digest:raise RuntimeError('frozen tool changed: '+path)
    if inventory(inputs,receipt['input_jars'])!=receipt['input_jars']:raise RuntimeError('input drift')
    if not a.child and inventory(original,receipt['outputs'])!=receipt['outputs']:raise RuntimeError('original outputs drift')
    if str(dex) not in tools:raise RuntimeError('unfrozen compiler')
    allowed={'--image='+str(original/'boot.art'),'--oat-file='+str(original/'boot.oat')}
    outputs={v for v in command if v.startswith(('--image=','--oat-file='))}
    if outputs!=allowed:raise RuntimeError('unexpected compiler output path')
    if a.child:
        # This process is entered exclusively via unshare --mount --propagation private.
        parent_ns=os.environ['U7_PARENT_MNT_NS']
        if os.readlink('/proc/self/ns/mnt')==parent_ns:raise RuntimeError('not in private mount namespace')
        def run(args):subprocess.run(args,check=True)
        for path in [inputs,dex.parent.parent,script.parent]:
            run(['mount','--bind',str(path),str(path)])
            run(['mount','-o','remount,bind,ro',str(path)])
        run(['mount','--bind',str(work/'arm64'),str(original)])
        run(['mount','--bind',str(work/'tmp'),'/tmp'])
        (work/'namespace-mountinfo.txt').write_text(Path('/proc/self/mountinfo').read_text())
        env=os.environ.copy();env['LD_LIBRARY_PATH']=str(dex.parent.parent/'lib64');env['TMPDIR']=str(work/'tmp')
        env['HOME']=str(work/'home')
        with (work/'compiler.log').open('w') as log:
            result=subprocess.run(command,cwd=work,env=env,stdout=log,stderr=subprocess.STDOUT)
        save(work/'compiler-exit.json',{'returncode':result.returncode,'finished_at':now()})
        return result.returncode
    # Refuse directory reuse. The containing directory has only the uploaded driver/config.
    work.mkdir()
    for n in ['arm64','tmp','home']:(work/n).mkdir()
    start=now();before={p:sha(p) for p in tools}
    # Keep the full host library cohort identity as part of the NEW reproduction receipt.
    host_libs={str(f):sha(f) for f in sorted((dex.parent.parent/'lib64').glob('*.so')) if f.is_file()}
    save(work/'before.json',dict(time=start,host=socket.gethostname(),uname=list(os.uname()),tools=before,
                               inputs=receipt['input_jars'],original_outputs=receipt['outputs'],host_libraries=host_libs))
    ref=work/'reference.sha256'
    ref.write_text(''.join(f'{h}  {n}\n' for n,h in receipt['input_jars'].items())+
                   ''.join(f'{h}  arm64/{n}\n' for n,h in receipt['outputs'].items()))
    check=['bash',str(script),'--check','--dex2oat',str(dex),'--jars-dir',str(inputs),
           '--work',str(work/'generator-work'),'--out',str(work/'arm64'),'--ref',str(ref)]
    with (work/'generator-check.log').open('w') as log:subprocess.run(check,check=True,stdout=log,stderr=subprocess.STDOUT)
    save(work/'command.json',dict(generator_check=check,compiler=command,
          note='Frozen generator input check; exact embedded argv executed directly to retain original OAT path strings. Private namespace redirects original output to fresh work/arm64.'))
    env=os.environ.copy();env['U7_PARENT_MNT_NS']=os.readlink('/proc/self/ns/mnt')
    result=subprocess.run(['unshare','--mount','--propagation','private',sys.executable,str(Path(__file__).resolve()),
                          '--child','--config',str(a.config.resolve()),'--work',str(work)],env=env)
    actual={f.name:sha(f) for f in sorted((work/'arm64').iterdir()) if f.is_file()}
    comparisons=[dict(file=n,reference=h,actual=actual.get(n),identical=actual.get(n)==h) for n,h in receipt['outputs'].items()]
    after={p:sha(p) for p in tools};original_after=inventory(original,receipt['outputs']);inputs_after=inventory(inputs,receipt['input_jars'])
    unchanged=before==after and original_after==receipt['outputs'] and inputs_after==receipt['input_jars']
    success=result.returncode==0 and len(actual)==27 and all(r['identical'] for r in comparisons) and unchanged
    save(work/'result.json',dict(status='verified' if success else 'mismatch',started_at=start,finished_at=now(),
         host=socket.gethostname(),compiler_exit=result.returncode,matched=sum(r['identical'] for r in comparisons),
         expected_count=27,actual_count=len(actual),originals_and_frozen_tools_unchanged=unchanged,
         comparisons=comparisons,extra_outputs=sorted(set(actual)-set(receipt['outputs'])),
         tools=before,tools_after=after,input_jars=receipt['input_jars'],outputs=actual,
         build_command=receipt['build_command'],build_log_sha256=sha(work/'compiler.log') if (work/'compiler.log').exists() else None,
         toolchain_identity_sha256=sha(work/'before.json'),config_sha256=sha(a.config),driver_sha256=sha(__file__)))
    print(json.dumps({'status':'verified' if success else 'mismatch','matched':sum(r['identical'] for r in comparisons),'work':str(work),'unchanged':unchanged}))
    return 0 if success else 2

if __name__=='__main__':raise SystemExit(main())
