#!/usr/bin/env python3
from common import *
import argparse,hashlib,time
p=argparse.ArgumentParser();p.add_argument('stage');p.add_argument('--candidate',action='store_true');a=p.parse_args()
out=R/a.stage;out.mkdir(exist_ok=True,parents=True);dev=board(a.stage)
pkg=CANDIDATE if a.candidate else BASE
expected=dict(json.loads((pkg/'package.json').read_text())['live_hashes']);expected[JAR]=JAR_SHA
for row in json.loads((REPO/'knowledge/frozen/frozen.json').read_text())['entries']:
 if row['id']=='FZ-001':
  for v in row['artifacts']:expected[v['path']]=v['sha256']
actual={};paths=list(expected)
for i in range(0,len(paths),60):
 text=dev.shell('sha256sum '+' '.join(shlex.quote(s) for s in paths[i:i+60]))[1]
 actual.update({s.split()[1]:s.split()[0] for s in text.splitlines() if len(s.split())==2})
fp=b.runtime_fingerprint(dev,out);assert actual==expected, {k:(v,actual.get(k)) for k,v in expected.items() if actual.get(k)!=v}
if not a.candidate:assert fp=='0b81cdbe0ed9',fp
b.save(out/'identity.json',{'time':time.time(),'boot_id':dev.boot,'package':str(pkg),'manifest_sha256':hashlib.sha256((pkg/'package.json').read_bytes()).hexdigest(),'runtime_fingerprint':fp,'expected':expected,'actual':actual,'verified':True})
b.save(out/'baseline.json',{'boot_id':dev.boot})
(out/'mountinfo.txt').write_text(dev.shell('cat /proc/self/mountinfo')[1])
state=W/'westlake-generation-state'/SERIAL
for f in state.glob(dev.boot+'*.json'):
 d=json.loads(f.read_text());b.save(out/'active-ledger.json',d)
 if a.stage=='before':assert d['package_path']==str(BASE)
print(a.stage,fp,'SHA paths',len(expected),'JAR',JAR_SHA,'verified',flush=True)
