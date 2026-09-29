#!/usr/bin/env python3
"""Read-only early process maps, independent of the screenshot verdict."""
import subprocess,time
from pathlib import Path
r=Path(__file__).resolve().parent/'zigzag-maps';r.mkdir(exist_ok=True)
hdc=['/Users/zhaoyue/orca/workspaces/westlake-inputs/tools/hdc_mac.sh','-t','5cd1e3dd00000000000000000923012c','shell']
end=time.monotonic()+180; seen=set()
while time.monotonic()<end:
 try:
  s=subprocess.check_output(hdc+['ps -A -o PID,UID,NAME'],text=True,timeout=8)
  for line in s.splitlines():
   p=line.split()
   if len(p)>=3 and p[0].isdigit() and p[1]=='20010168':
    pid=p[0]
    data=subprocess.check_output(hdc+[f'cat /proc/{pid}/maps'],timeout=8)
    if b'libart.so' in data:
     tag=f'{pid}-{int(time.time())}'
     (r/(tag+'.txt')).write_bytes(data)
     if pid not in seen: print('observed',pid,flush=True);seen.add(pid)
  time.sleep(2)
 except (subprocess.SubprocessError,OSError):time.sleep(2)
