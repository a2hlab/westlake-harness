#!/usr/bin/env python3
"""Persist local argv and real output; no retries or alternative execution paths."""
import argparse, datetime, hashlib, json, os, subprocess
from pathlib import Path
D = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(); ap.add_argument('tag'); ap.add_argument('command', nargs=argparse.REMAINDER); a = ap.parse_args()
assert a.command and a.tag.replace('-', '').isalnum()
out = D / '.private' / a.tag; out.mkdir(exist_ok=False)
now = lambda: datetime.datetime.now().astimezone().isoformat()
r = {'argv': a.command, 'cwd': os.getcwd(), 'started_at': now()}
(out/'command.json').write_text(json.dumps(r, indent=2)+'\n')
with (out/'stdout').open('wb') as so, (out/'stderr').open('wb') as se:
    try: r['rc'] = subprocess.run(a.command, stdout=so, stderr=se, timeout=180).returncode
    except subprocess.TimeoutExpired: r['rc'] = 124; r['timeout'] = True
r['ended_at'] = now()
for n in ['stdout','stderr']:r[n+'_sha256'] = hashlib.sha256((out/n).read_bytes()).hexdigest()
(out/'receipt.json').write_text(json.dumps(r, indent=2)+'\n')
print((out/'stdout').read_text(errors='replace'), end=''); print((out/'stderr').read_text(errors='replace'), end=''); print('receipt:',out.relative_to(D),'rc:',r['rc'])
raise SystemExit(r['rc'])
