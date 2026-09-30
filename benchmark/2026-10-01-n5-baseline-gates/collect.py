#!/usr/bin/env python3
"""Read-only U5 library inventory. Never sends files or executes device writes."""
import hashlib,json,shlex,subprocess,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent; ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'scripts/lab')); import lab_paths
SERIAL='5ea34a4500000000000000001123012c'
def hdc(args):
 cmd=['orb','-m','a2hlab','bash','-lc','export MAC_HOME='+shlex.quote(str(Path.home()))+'; '+shlex.join([str(lab_paths.tools()/'hdc_mac.sh'),'-t',SERIAL,*args])]
 with (HERE/'commands.jsonl').open('a') as f:f.write(json.dumps(cmd)+'\n')
 r=subprocess.run(cmd,capture_output=True,timeout=600)
 if r.returncode: raise RuntimeError(r.stderr.decode(errors='replace'))
 return r.stdout
if __name__=='__main__':
 (HERE/'boot-before.txt').write_bytes(hdc(['shell','cat /proc/sys/kernel/random/boot_id']))
 command="find /system/lib64 /system/android/lib64 /vendor/lib64 \\( -type f -o -type l \\) -name '*.so*' -exec sha256sum {} \\;"
 data=hdc(['shell',command]);(HERE/'inventory-raw.txt').write_bytes(data)
 rows=[];errors=[]
 for line in data.decode(errors='replace').splitlines():
  bits=line.split(None,1)
  if len(bits)==2 and len(bits[0])==64 and all(c in '0123456789abcdef' for c in bits[0]):rows.append(dict(target=bits[1].strip(),sha256=bits[0]))
  else:errors.append(line)
 (HERE/'inventory.json').write_text(json.dumps(dict(serial=SERIAL,rows=rows,errors=errors),indent=2)+'\n')
 (HERE/'boot-after.txt').write_bytes(hdc(['shell','cat /proc/sys/kernel/random/boot_id']))
 assert (HERE/'boot-before.txt').read_bytes()==(HERE/'boot-after.txt').read_bytes()
 print(json.dumps(dict(rows=len(rows),errors=len(errors))))
