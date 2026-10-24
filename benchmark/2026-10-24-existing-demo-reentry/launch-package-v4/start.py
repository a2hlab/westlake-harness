#!/usr/bin/env python3
"""Frozen T123 launcher. Default is offline verification; --execute needs outer acceptance."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import shutil
import sys
import uuid
sys.dont_write_bytecode=True
PACKAGE=Path(__file__).resolve().parent

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def verify(expected):
    manifest_path=PACKAGE/'manifest.json'
    if sha(manifest_path)!=expected:raise RuntimeError('manifest SHA mismatch')
    manifest=json.loads(manifest_path.read_text())
    for name,digest in manifest['files'].items():
        if Path(name).name!=name or sha(PACKAGE/name)!=digest:raise RuntimeError('package file SHA mismatch: '+name)
    sys.path.insert(0,str(PACKAGE))
    import lab_paths
    main=lab_paths.harness().resolve()
    for item in manifest['external']:
        if item['kind']=='main':path=main/item['path']
        elif item['kind']=='python':path=Path(sys.executable).resolve()
        elif item['kind']=='append':path=Path(os.environ.get('OLP_BOARD_APPEND',str(Path.home()/'workspace/octoscode/scripts/olp-board-append.sh'))).expanduser().resolve()
        else:path=Path(item['path'])
        if sha(path)!=item['sha256']:raise RuntimeError('external SHA mismatch: '+item['name'])
    if os.environ.get('BOARD_LOCK_DIR')!=manifest['board_lock_dir_env']:
        raise RuntimeError('board lock namespace differs from prepared context')
    return manifest,main

class Tee:
    def __init__(self,terminal,file):self.terminal=terminal;self.file=file
    def write(self,text):self.file.write(text);self.file.flush();return self.terminal.write(text)
    def flush(self):self.file.flush();self.terminal.flush()

def execute_payload(run):
    sys.path.insert(0,str(run));sys.argv=[str(run/'p0.py')]
    runpy.run_path(str(run/'p0.py'),run_name='__main__')

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest-sha',required=True)
    parser.add_argument('--execute',action='store_true')
    args=parser.parse_args(argv)
    manifest,main_tree=verify(args.manifest_sha)
    if not args.execute:
        print(json.dumps({'status':'OFFLINE_PACKAGE_VERIFIED_NO_DEVICE_CALLS','manifest_sha256':args.manifest_sha,'file_count':len(manifest['files'])}));return 0
    # All code bytes were prepared and verified before T0. No generated source in the run.
    root=Path.home()/'.local/share/westlake/existing-demo-reentry-20261024'
    root.mkdir(parents=True,exist_ok=True)
    name='run-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:8]
    run=root/name;run.mkdir(exist_ok=False)
    for filename in manifest['files']:
        shutil.copyfile(PACKAGE/filename,run/filename)
        if sha(run/filename)!=manifest['files'][filename]:raise RuntimeError('copy SHA mismatch')
    shutil.copyfile(PACKAGE/'manifest.json',run/'manifest.json')
    from review_wait import publish_once
    publish_once(run/'context.json',{'main':str(main_tree),'run':str(run),'owner_pid':os.getpid(),'manifest_sha256':args.manifest_sha,'package':str(PACKAGE)})
    publish_once(run/'package-verified.json',{'manifest_sha256':args.manifest_sha,'files':manifest['files'],'external':manifest['external'],'owner_pid':os.getpid()})
    # Context and byte-identical payload are complete before first formal preflight/T0.
    terminal_out,terminal_err=sys.stdout,sys.stderr
    with (run/'owner.stdout').open('x',buffering=1) as stdout,(run/'owner.stderr').open('x',buffering=1) as stderr:
        sys.stdout,sys.stderr=Tee(terminal_out,stdout),Tee(terminal_err,stderr)
        result=0
        try:
            print('RUN_READY '+json.dumps({'run':str(run),'owner_pid':os.getpid(),'manifest_sha256':args.manifest_sha}),flush=True)
            execute_payload(run)
        except SystemExit as ex:result=int(ex.code or 0)
        except BaseException as ex:
            result=1;print(repr(ex),file=sys.stderr,flush=True)
        finally:
            sys.stdout,sys.stderr=terminal_out,terminal_err
            publish_once(run/'launcher-exit.json',{'rc':result,'owner_pid':os.getpid(),'ended_at':datetime.datetime.now().astimezone().isoformat()})
    print('RUN_FINISHED '+json.dumps({'run':str(run),'rc':result}),flush=True)
    return result

if __name__=='__main__':raise SystemExit(main())
