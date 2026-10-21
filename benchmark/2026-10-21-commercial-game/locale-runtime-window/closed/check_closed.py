#!/usr/bin/env python3
import argparse,hashlib,json,re
from pathlib import Path
D=Path(__file__).resolve().parent

def j(n):return json.loads((D/n).read_text())
def h(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def resolve(s):
 assert s.startswith('$HOME/')
 return Path.home()/s[len('$HOME/'):]

def main():
 p=argparse.ArgumentParser();p.add_argument('--raw',action='store_true');a=p.parse_args()
 r=j('results.json');assert r['status']=='CLOSED_RESTORED_GAME_FAILED' and r['elapsed_seconds']<1800
 assert r['apply']['operations']==r['rollback']['operations']==36
 assert not r['game']['frames_observed'] and r['game']['fault_pc']=='UNKNOWN'
 assert j('admission-retirement.json')['exceptions_retired']==318
 assert j('remote-archive-pending.json')['status']=='PENDING_REMOTE_RECEIPT'
 for x in j('receipts-index.json'):assert h(D/x['public_path'])==x['public_sha256']
 for x in j('images.json'):assert h(D/x['path'])==x['sha256']==x['source']['sha256']
 assert len(j('images.json'))==4
 assert 'screenshots_captured=2/2' in (D/'facts.txt').read_text()
 for f in D.rglob('*'):
  if not f.is_file() or '.private' in f.relative_to(D).parts or f.suffix=='.jpeg':continue
  if f.suffix in ['.json','.txt','.md']:
   t=f.read_text();assert not re.search(r'/(?:Users|home)/[^/\s]+',t),f.name
 if a.raw:
  index=j('private-raw-index.json');refs=index['files']+j('postclose-input-index.json')['files']+[j('postclose-input-index.json')['peer_review']]
  for x in refs:
   p=resolve(x['path']);assert p.stat().st_size==x['bytes'] and h(p)==x['sha256'],x['path']
  assert len(index['files'])==index['members'] and sum(x['bytes'] for x in index['files'])==index['total_bytes']
  w=resolve(index['root']);plan=json.loads((w/'apply.json').read_text());hs=json.loads((w/'closure/hashes.json').read_text())
  assert hs['direct']==hs['parent']==plan['plan']['baseline'] and len(hs['direct'])==319
  mounts={}
  for line in (w/'closure/fingerprint-mounts.stdout').read_text().splitlines():
   f=line.split()
   if len(f)>4 and f[4].startswith(('/system/','/data/app/')):mounts.setdefault(f[4],[]).append({'id':f[0],'root':f[3],'device':f[2]})
  assert mounts==plan['before_mounts'] and len(mounts)==61
  assert (w/'boat-before.stdout').read_bytes()==(w/'closure/boat-after.stdout').read_bytes()
  assert (D/'facts.txt').read_bytes()==(w/'facts.txt').read_bytes()
  print(f'PASS raw {len(refs)} SHA/size and original319/319 baseline/61 mount comparisons')
 print('PASS closure evidence consistency; game failed, PC/stack unknown; remote receipt pending')
if __name__=='__main__':main()
