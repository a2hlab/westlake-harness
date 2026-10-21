#!/usr/bin/env python3
"""Read local outer receipts; never contact a device."""
import hashlib
import json
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent
RAW = Path.home()/'.local/share/westlake/commercial-game-20261021/apk-extractor/fresh-20261021T1722'

def main():
    records=json.loads((RAW/'records.json').read_text())
    assert len(records)==14 and all(r['transport_rc']==0 and str(r['remote_rc'])=='0' for r in records)
    boot=(RAW/'boot-before.stdout').read_text().splitlines()[0]
    assert boot==(RAW/'boot-after.stdout').read_text().splitlines()[0]
    assert boot=='a1d869b4-69a2-40a4-937e-4860f5b54239'
    aliases=(RAW/'aliases.stdout').read_text()
    assert '66336:5576 0:0 755 1 regular file' in aliases and '66336:3342 0:0 755 1 regular file' in aliases
    original='51e1b52538b3198d2a8a3236a9479bf8512f51acc74c0d68e34acca358f39be5'
    assert aliases.count(original)==2
    processes=(RAW/'processes.stdout').read_text()
    assert not re.search(r'^\s*\d+\s+\d+\s+\d+\s+installs\s*$',processes,re.M)
    wifi=(RAW/'wifi-device.stdout').read_text()
    assert 'Connection.ssid: UpstreamLabs_Compatibility' in wifi and 'status: connected' in wifi
    raw=[dict(file=p.name,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),bytes=p.stat().st_size) for p in sorted(RAW.iterdir()) if p.is_file()]
    mounts=[s.split() for s in (RAW/'mounts.stdout').read_text().splitlines() if len(s.split())==6]
    targets=['/system/lib64/libinstalls.z.so','/system/lib64/platformsdk/libinstalls.z.so']
    affecting=[r for r in mounts if any(t==r[1] or t.startswith(r[1].rstrip('/')+'/') for t in targets)]
    result=dict(raw_alias='$HOME/.local/share/westlake/commercial-game-20261021/apk-extractor/fresh-20261021T1722',
        raw=raw,commands=14,transport_remote_all_zero=True,boot_id=boot,boot_differs_from_G06=True,
        aliases=[dict(path=t,sha256=original,device=66336,inode=i,uid=0,gid=0,mode='0755',nlink=1,type='regular',selinux='u:object_r:system_lib_file:s0') for t,i in zip(targets,[5576,3342])],
        mounts_affecting_installs=affecting,installs_name_observed=False,actual_consumer_status='unknown: complete maps not yet collected',
        foundation_observation=dict(pid=878,ppid=1,uid=5523,usable_for_action=False),
        network=dict(intended_name='upstreamlabswifi',actual_ssid='UpstreamLabs_Compatibility',connected=True,band='2.4GHz',interpretation="observed readonly; outer preserves current configuration",network_mutation=False),
        runtime_recovered='unknown: mounts exist but full fresh hashes and recovery inputs missing',
        next='next-reads.json',device_admission=False)
    (BASE/'fresh-review.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__': main()
