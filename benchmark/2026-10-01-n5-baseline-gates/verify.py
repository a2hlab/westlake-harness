#!/usr/bin/env python3
import hashlib,json,sys,gzip
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
def read(name):
 p=HERE/name
 return json.loads(p.read_text() if p.exists() else gzip.decompress((HERE/(name+'.gz')).read_bytes()))
if sys.argv[1]=='snapshot':
 inventory=read('inventory.json');metadata=read('metadata.json');snapshot=read('snapshot.json')
 assert len(inventory['rows'])==len(snapshot)==3278 and not inventory['errors'] and not metadata['failures']
 assert len(metadata['files'])==len({r['sha256'] for r in inventory['rows']})
 assert (HERE/'boot-before.txt').read_bytes()==(HERE/'boot-after-snapshot.txt').read_bytes()
 for label in ['u5','n5']:
  report=read(label+'-gate.json');assert not report['errors']
  assert report['status']=='REJECT'
 assert read('u5-gate.json')['package_manifest_sha256']=='7bc02de79f989d48cedb1e5020df1be3b5cd58f6d2229df8f1a3f08cc4f5ffbe'
 assert read('n5-gate.json')['package_manifest_sha256']=='b446d8db35e30a9180760f8dc8a4837b93e23c5187217e30b9901f94d66b68f7'
elif sys.argv[1]=='proposal':
 p=read('exception-proposal.json');assert p['status']=='PENDING_OUTER_APPROVAL'
 reports={k:read(k.lower()+'-gate.json') for k in ['U5','N5']}
 ids={(label,g,f['issue_id']) for label,r in reports.items() for g,v in r['gates'].items() for f in v['findings']}
 assert ids=={(x['package'],x['gate'],x['finding']['issue_id']) for x in p['entries']}
 for x in p['entries']:
  assert x['approval']=='PENDING' and x['reason']
  assert all((ROOT/e).is_file() for e in x['evidence'])
 assert not read('registry-at-proposal.json')['exceptions']
else:raise SystemExit('unknown case')
print('PASS',sys.argv[1])
