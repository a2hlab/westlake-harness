#!/usr/bin/env python3
"""Run one command, persist argv/start/end/stdout/stderr/rc under <dir>/<name>.*; print short summary."""
import json, subprocess, sys, time, os
from pathlib import Path
d, name = Path(sys.argv[1]), sys.argv[2]
assert sys.argv[3] == '--'
argv = sys.argv[4:]
timeout = float(os.environ.get('REC_TIMEOUT', '120'))
d.mkdir(parents=True, exist_ok=True)
if any((d / f'{name}.{s}').exists() for s in ('argv', 'rc')):
    sys.exit(f'REFUSE existing record {name}')
(d / f'{name}.argv').write_text(json.dumps(argv) + '\n')
t0 = time.time(); (d / f'{name}.start').write_text(f'{t0:.6f} {time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t0))}\n')
try:
    p = subprocess.run(argv, capture_output=True, timeout=timeout)
    out, err, rc = p.stdout, p.stderr, p.returncode
except subprocess.TimeoutExpired as e:
    out, err, rc = e.stdout or b'', (e.stderr or b'') + b'\nREC_TIMEOUT', 'timeout'
t1 = time.time()
(d / f'{name}.stdout').write_bytes(out); (d / f'{name}.stderr').write_bytes(err)
(d / f'{name}.end').write_text(f'{t1:.6f} {time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(t1))}\n')
(d / f'{name}.rc').write_text(f'{rc}\n')
lines = out.decode(errors='replace').splitlines()
n = int(os.environ.get('REC_SHOW', '6'))
print(f'[{name}] rc={rc} dt={t1-t0:.1f}s out_lines={len(lines)} err_bytes={len(err)}')
for l in lines[:n]: print('  |', l[:200])
if len(lines) > n: print(f'  | ... ({len(lines)-n} more)')
if err.strip(): print('  E|', err.decode(errors="replace").strip()[:300])
