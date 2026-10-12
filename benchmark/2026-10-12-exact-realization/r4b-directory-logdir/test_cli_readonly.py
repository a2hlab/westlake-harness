#!/usr/bin/env python3
"""Actual CLI and frozen Transport, local fake HDC only; stop at first read probe."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(out):
    out.mkdir(exist_ok=False)
    with tempfile.TemporaryDirectory(prefix='r4b-local-only-') as tmp:
        root = Path(tmp)
        hdc = root / 'fake-hdc.py'
        hdc.write_text('''#!/usr/bin/env python3
import re,sys
command=sys.argv[-1]
assert sys.argv[1:4]==['-t','5cd1e3dd00000000000000000923012c','shell']
assert not re.search(r'\\b(mkdir|rmdir|chmod|chown|chcon|reboot|rm)\\b',command)
marker=re.search(r'(__R4_RC_[0-9a-f]+__)',command)[1]
print('LOCAL_FAKE_HDC_READONLY_STOP')
print(marker+'42')
''')
        hdc.chmod(0o700)
        lock = root / 'fake-lock.sh'
        lock.write_text('#!/bin/sh\ntest "$1" = held || exit 99\nprintf "%s\\n" r4b-local-test-holder\n')
        lock.chmod(0o700)
        auth = json.loads((HERE / 'authorization.fields.example.json').read_text())
        # A fixture, never a board authorization: only the local fake HDC is invoked.
        auth.update(approved_by='outer(codex)', holder='r4b-local-test-holder', expires_epoch=time.time()+60,
                    lock_tool={'path':str(lock),'sha256':sha(lock)})
        authpath=root/'local-fixture-authorization.json';authpath.write_text(json.dumps(auth))
        manifest = HERE/'manifest.5cd.json'; m=json.loads(manifest.read_text())
        txn = out/'transaction'
        argv=[sys.executable,'-B',str(HERE/'directory_transaction.py'),'--manifest',str(manifest),
              '--manifest-sha256',sha(manifest),'--authorization',str(authpath),'--authorization-sha256',sha(authpath),
              '--serial',m['serial'],'--boot-id',m['boot_id'],'--hdc',str(hdc),'--out',str(txn),'--action','apply','--execute']
        result=subprocess.run(argv,capture_output=True,text=True,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'))
        (out/'cli.stdout').write_text(result.stdout);(out/'cli.stderr').write_text(result.stderr)
        assert result.returncode==1,(result.returncode,result.stdout,result.stderr)
        receipt=json.loads(result.stdout)
        assert receipt['executor_rc']==1 and len(receipt['steps'])==1
        assert receipt['steps'][0]['transport_rc']==0 and receipt['steps'][0]['remote_rc']==42
        assert 'No such file or directory' not in result.stdout
        logs=list(out.glob('transaction.transport-*'));assert len(logs)==1
        raw=logs[0]/'001-probe-directory.stdout';record=logs[0]/'001-probe-directory.json'
        assert raw.is_file() and record.is_file()
        assert json.loads(record.read_text())['stdout_sha256']==sha(raw)
        assert not txn.exists() and not list(out.rglob('intent.json'))
        summary={'status':'PASS_LOCAL_FAKE_HDC_CLI_READONLY_PATH','synthetic_transport':True,'cli_rc':1,
                 'expected_remote_stop_rc':42,'raw_written':True,'raw_sha256':sha(raw),'raw_command_record_sha256':sha(record),
                 'probe_calls':1,'intent_files':0,'device_writes':0,'real_device_calls':0,'reboots':0,
                 'executor_sha256':sha(HERE/'directory_transaction.py'),'manifest_sha256':sha(manifest)}
        (out/'result.json').write_text(json.dumps(summary,indent=2)+'\n')
        print(json.dumps(summary))


if __name__=='__main__':
    if len(sys.argv) > 1:
        run(Path(sys.argv[1]).resolve())
    else:
        with tempfile.TemporaryDirectory(prefix='r4b-cli-default-') as directory:
            run(Path(directory) / 'evidence')
