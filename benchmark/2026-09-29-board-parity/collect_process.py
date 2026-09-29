#!/usr/bin/env python3
"""Read one explicitly identified HelloWorld process; host outputs only."""
import argparse
import json
from pathlib import Path
import collect

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--collection', type=Path, required=True)
p.add_argument('--serial', choices=collect.SERIALS, required=True)
p.add_argument('--pid', type=int, required=True)
p.add_argument('--out', type=Path, required=True)
p.add_argument('--hdc', default=collect.HDC)
a = p.parse_args()
if a.pid <= 0:
    p.error('pid must be positive')
base = next(b for b in json.loads(a.collection.read_text())['boards'] if b['serial'] == a.serial)
r = collect.Reader(a.hdc, a.serial, a.out)
r.known_names = {Path(x).name for x in base['files']}
boot = r.read('boot-before', collect.BOOT)
if boot['stdout'].strip() != base['boot_before']:
    raise SystemExit('boot differs from original collection; do not merge')
stat = r.read('identity-stat', f'cat /proc/{a.pid}/stat')
try:
    ppid = int(stat['stdout'].rsplit(')', 1)[1].split()[1])
except (IndexError, ValueError):
    raise SystemExit('unreadable process identity')
proc = r.process(a.pid, 'helloworld', ppid)
raw_maps = json.loads((a.out/f'helloworld-{a.pid}-maps.json').read_text())['stdout']
package_path = '/data/app/el1/bundle/public/com.example.helloworld/android/base.apk'
if not any(line.split()[-1] == package_path for line in raw_maps.splitlines() if line.split()):
    raise SystemExit('maps do not identify HelloWorld APK; preserve evidence but do not merge')
last_boot = r.read('boot-after', collect.BOOT)
result = {'serial': a.serial, 'boot_before': boot['stdout'].strip(), 'boot_after': last_boot['stdout'].strip(),
          'process': proc, 'package_map_path': package_path, 'commands': r.commands,
          'base_collection': str(a.collection.resolve())}
(a.out/'supplement.json').write_text(json.dumps(result, indent=2)+'\n')
print(json.dumps({'pid': a.pid, 'ppid': ppid, 'stable': proc['stable_process'], 'maps_stable': proc['stable_maps'], 'files': len(proc['files']), 'unverified': proc['unverified_files'], 'output': str(a.out/'supplement.json')}, indent=2))
