#!/usr/bin/env python3
"""T34 exact-executor transport adapter. No payload edits or write retries."""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import re
import runpy
import shlex
import sys
import time

EXECUTOR_SHA='d75ecd42714f03b52db167c0978ec14c3ed7bcb5ad7e96c98be0d5b594c7060e'
BOARD_SHA='f41efa6ae2450adadda1f02c3c09335b74479c7d025872bbf95b3c8a444b177c'
SERIAL='61b0657200000000000000000324012c'
THRESHOLD=32768  # Transport choice, not a claimed HDC limit.
sha=lambda b:hashlib.sha256(b).hexdigest()
q=shlex.quote

def adapter(original,scope,folder):
    counter=0
    def raw_shell(self,command,timeout=60):
        nonlocal counter
        payload=command.encode('utf-8')
        if len(payload)<=THRESHOLD:
            return original(self,command,timeout)
        assert self.serial==SERIAL and self.boot==scope.boot
        reserve=0 if scope.mode=='rollback' else 600
        remaining=lambda:scope.deadline-time.monotonic()-reserve
        def check():
            assert remaining()>0,'transport deadline/recovery reserve'
            self.ready()  # exact subclass holder + boot checks; its reads stay short
            assert self.boot==scope.boot
        check()
        counter+=1
        local=folder/f'payload-{counter:02d}.sh'
        with local.open('xb') as f:f.write(payload)
        digest=sha(payload)
        remote=f'/data/local/tmp/t34-transport-{scope.boot[:8]}-{sha(str(folder).encode())[:12]}-{counter:02d}'
        target=remote+'/payload.sh'
        record={'payload_sha256':digest,'payload_bytes':len(payload),'original_timeout':timeout,
                'mode':scope.mode,'boot':scope.boot,'holder':scope.holder,'start':scope.start,
                'remote':target,'device_writes_may_have_executed':False,'retries':0}
        receipt=folder/f'payload-{counter:02d}.json'
        def save():receipt.write_text(json.dumps(record,indent=2)+'\n')
        def short(text,limit):
            check()
            return original(self,text,min(limit,remaining()))
        save()
        try:
            walk=f'walk={q(remote)}; while [ "$walk" != / ]; do test ! -L "$walk"; walk=$(dirname "$walk"); done'
            rc,text=short(f'( set -eu; {walk}; test ! -e {q(remote)}; mkdir {q(remote)}; chmod 700 {q(remote)} )',15)
            assert rc==0,('transport stage rejected',rc,text)
            check()
            # Board.send retains its usual ready/command receipts and bounded command implementation.
            self.send(local,target)
            guard=f"""test ! -L {q(target)}; test -f {q(target)}; test "$(sha256sum {q(target)} | cut -d' ' -f1)" = {digest}"""
            rc,text=short(f'( set -eu; {guard} )',15)
            assert rc==0,('payload SHA readback rejected',rc,text)
            check()
            record['device_writes_may_have_executed']=True
            record['execution_status']='DISPATCHING_ONCE'
            save()
            # Original command bytes retain their own (set -eu; ... ) subshell.
            # -eu also protects file-level execution; the original raw_shell adds its fresh rc marker.
            rc,text=original(self,f'( set -eu; {guard}; /system/bin/sh -eu {q(target)} )',min(timeout,remaining()))
            record.update(execution_status='REMOTE_RC_OBSERVED',remote_rc=rc,stdout=text)
            save()
            return rc,text
        except BaseException as exc:
            record.update(execution_status='FAILED_OR_UNKNOWN_NO_RETRY',error=type(exc).__name__+': '+str(exc))
            save()
            raise
    return raw_shell

def main():
    assert '--' in sys.argv,'usage: file_transport.py --executor PATH -- ORIGINAL_EXECUTOR_ARGS'
    split=sys.argv.index('--')
    p=argparse.ArgumentParser();p.add_argument('--executor',type=Path,required=True)
    wrapper=p.parse_args(sys.argv[1:split]);args=sys.argv[split+1:]
    assert sha(wrapper.executor.read_bytes())==EXECUTOR_SHA,'frozen executor drift'
    read=argparse.ArgumentParser(add_help=False)
    read.add_argument('mode',choices=['preflight','apply','rollback'])
    for name in ('boot','holder'):read.add_argument('--'+name)
    for name in ('out','repo'):read.add_argument('--'+name,type=Path)
    read.add_argument('--start',type=float);read.add_argument('--execute',action='store_true')
    scope,_=read.parse_known_args(args)
    if not scope.execute:
        sys.argv=[str(wrapper.executor),*args]
        runpy.run_path(str(wrapper.executor),run_name='__main__')
        return
    assert scope.out and scope.repo and scope.boot and scope.holder and scope.start
    assert re.fullmatch(r'inner\(cc-video\) [1-9][0-9]* [^ ]+',scope.holder)
    assert re.fullmatch(r'[0-9a-f-]{36}',scope.boot)
    assert abs(datetime.datetime.fromisoformat(scope.holder.split()[2]).timestamp()-scope.start)<1
    age=time.time()-scope.start
    assert 0<=age<(1800 if scope.mode=='rollback' else 1200)
    scope.deadline=time.monotonic()+1800-age
    assert scope.out.is_absolute() and not str(scope.out).startswith(('/tmp/','/private/tmp/'))
    folder=scope.out.parent/(scope.out.name+'.transport')
    folder.mkdir(parents=True,exist_ok=False)
    module=scope.repo/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
    assert sha(module.read_bytes())==BOARD_SHA
    sys.path.insert(0,str(module.parent))
    import bms_batch
    original=bms_batch.Board.raw_shell
    (folder/'source.json').write_text(json.dumps({
        'adapter_sha256':sha(Path(__file__).read_bytes()),'executor_sha256':EXECUTOR_SHA,
        'bms_batch_sha256':BOARD_SHA,'threshold_bytes':THRESHOLD,'mode':scope.mode,
        'holder':scope.holder,'start':scope.start,'boot':scope.boot,
        'policy':'No write retry. No payload, executor, admission or source-pin edits.'
    },indent=2)+'\n')
    bms_batch.Board.raw_shell=adapter(original,scope,folder)
    try:
        sys.argv=[str(wrapper.executor),*args]
        runpy.run_path(str(wrapper.executor),run_name='__main__')
    finally:
        bms_batch.Board.raw_shell=original

if __name__=='__main__':main()
