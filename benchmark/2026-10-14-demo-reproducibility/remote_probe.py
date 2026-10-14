#!/usr/bin/env python3
"""Run by outer only: read existing remote archive hashes and member names."""
import hashlib,json,sys,tarfile
from pathlib import Path
req=json.load(sys.stdin);out=[]
for row in req['requests']:
 p=Path(row['remote_path']);r=dict(row)
 if not p.is_file():r.update(status='MISSING');out.append(r);continue
 h=hashlib.sha256()
 with p.open('rb') as f:
  for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
 r.update(actual_sha256=h.hexdigest(),bytes=p.stat().st_size,status='MATCH' if h.hexdigest()==row['expected_sha256'] else 'DRIFT')
 if p.name.endswith('.tar.gz'):
  with tarfile.open(p,'r|gz') as t:r['members']=[{'path':x.name,'type':x.type.decode(),'bytes':x.size,'link':x.linkname} for x in t]
 out.append(r)
print(json.dumps({'mode':'READONLY','results':out},indent=2))
raise SystemExit(0 if all(x['status']=='MATCH' for x in out) else 2)
