#!/usr/bin/env python3
"""Only repeat an empty boot-ID read; never replay a device mutation."""
import subprocess,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'scripts/lab'))
import lab_paths
argv=[str(lab_paths.tools()/'hdc_mac.sh'),*sys.argv[1:]]
for attempt in range(2):
 p=subprocess.run(argv,capture_output=True)
 args=sys.argv[1:]
 boot_read=(len(args)==4 and args[:1]==['-t'] and args[2]=='shell' and args[3].startswith('cat /proc/sys/kernel/random/boot_id;'))
 if attempt==0 and p.returncode==0 and not p.stdout and not p.stderr and boot_read:
  sys.stderr.write('N3 transport: empty OrbStack boot-ID read; retry once (read-only)\n')
  continue
 sys.stdout.buffer.write(p.stdout);sys.stderr.buffer.write(p.stderr);sys.exit(p.returncode)
