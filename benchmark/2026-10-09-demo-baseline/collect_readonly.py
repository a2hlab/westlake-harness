#!/usr/bin/env python3
"""Collect three-board fingerprints and /data capacity without remote writes or locks."""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

REPO = Path(__file__).resolve().parents[2]
WS = Path(os.environ.get('WORKSPACES', str(REPO.parent)))
MASTER = WS / 'westlake-harness'
SERIALS = {'5ea':'5ea34a4500000000000000001123012c',
           '5cd':'5cd1e3dd00000000000000000923012c',
           '61b':'61b0657200000000000000000324012c'}

class ReadOnlyBoard:
    def __init__(self, serial, out, allowed):
        self.serial, self.out, self.allowed = serial, out, set(allowed)
        self.calls = []
    def shell(self, command, required=False):
        if command not in self.allowed:
            raise ValueError('Not an explicitly declared read-only command')
        r = subprocess.run([str(MASTER/'scripts/lab/hdc_mac.sh'), '-t', self.serial,
                            'shell', command], text=True, capture_output=True, timeout=90)
        self.calls.append({'command':command, 'rc':r.returncode, 'stderr':r.stderr})
        return r.returncode, r.stdout

def main():
    if sys.platform == 'darwin':
        raise SystemExit('Run through orb -m a2hlab; no DeviceIO/Board constructor is used')
    ap=argparse.ArgumentParser(); ap.add_argument('--out', type=Path, required=True); a=ap.parse_args()
    if a.out.exists(): raise SystemExit('fresh output directory required')
    a.out.mkdir(parents=True)
    source=MASTER/'benchmark/2026-09-28-bms-route-deploy/batch/bms_batch.py'
    sys.path.insert(0,str(MASTER/'scripts/lab'))
    spec=importlib.util.spec_from_file_location('readonly_batch',source)
    batch=importlib.util.module_from_spec(spec); spec.loader.exec_module(batch)
    info={'boot-before':'cat /proc/sys/kernel/random/boot_id', 'uptime':'cat /proc/uptime',
          'storage':'df -k /data', 'parent':'pidof appspawn-x',
          'installation':'sha256sum '+ ' '.join(batch.installation_chain.PATHS),
          'boot-after':'cat /proc/sys/kernel/random/boot_id'}
    allowed=list(info.values())+[f'sha256sum {p} 2>/dev/null' for p in (batch.FINGERPRINT_PATHS,batch.BOOT_IMAGE_PATHS)]
    data={'schema':'demo-board-readonly/v1', 'captured_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
          'batch_source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(), 'remote_write_operations':0,
          'lock_operations':0, 'boards':{}}
    for tag,serial in SERIALS.items():
        out=a.out/tag;out.mkdir();b=ReadOnlyBoard(serial,out,allowed); row={'serial':serial}
        for name,command in info.items():
            if name=='boot-after': continue
            rc,text=b.shell(command);(out/(name+'.txt')).write_text(text)
            row[name]={'rc':rc,'text':text.strip()}
        row['runtime_fingerprint']=batch.runtime_fingerprint(b,out)
        row['boot_image_fingerprint']=batch.boot_image_fingerprint(b,out)
        rc,text=b.shell(info['boot-after']); (out/'boot-after.txt').write_text(text)
        row['boot-after']={'rc':rc,'text':text.strip()}
        row['same_boot']=row['boot-before']['rc']==rc==0 and bool(text.strip()) and row['boot-before']['text']==text.strip()
        row['commands']=b.calls
        data['boards'][tag]=row
        (a.out/'receipt.json').write_text(json.dumps(data,indent=2)+'\n')
        print(tag, row['runtime_fingerprint'], row['boot_image_fingerprint'], 'same_boot='+str(row['same_boot']),flush=True)
    return 0 if all(r['same_boot'] and all(c['rc']==0 for c in r['commands']) for r in data['boards'].values()) else 2
if __name__=='__main__': raise SystemExit(main())
