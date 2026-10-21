#!/usr/bin/env python3
"""Offline receipt/negative-path check; never imports a device-executing entry point."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path
D=Path(__file__).resolve().parent

def main():
    manifest=json.loads((D/'manifest.json').read_text())
    root=D.parents[2]
    for row in manifest['files']:
        p=root/row['path']
        if p.stat().st_size != row['bytes'] or hashlib.sha256(p.read_bytes()).hexdigest()!=row['sha256']:
            raise SystemExit('manifest mismatch: '+row['path'])
    fresh=json.loads((D/'fresh-inputs.json').read_text())
    assert fresh['apk_sha256']!=fresh['metadata_sha256']
    assert fresh['fingerprint_members']=={'runtime':124,'boot':36}
    assert json.loads((D/'results.json').read_text())['device_execution']=='NOT_REQUESTED'
    p=subprocess.run([sys.executable,'-m','unittest','discover','-s',str(D),'-p','test_recovery.py'])
    if p.returncode:return p.returncode
    print('G06 OFFLINE_CHECK_PASS; device/human scenarios PENDING_REVIEW')
    return 0

if __name__=='__main__':sys.exit(main())
