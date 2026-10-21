#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
D=Path(__file__).resolve().parent;W=D.parents[3].parent;C=Path.home()/'.local/share/westlake/commercial-game-20261021'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  while b:=f.read(1024*1024):h.update(b)
 return h.hexdigest()
def load(n):return json.loads((D/n).read_text())
def expand(p):return Path(p.replace('$COMMERCIAL',str(C)).replace('$WORKSPACES',str(W)))
a=argparse.ArgumentParser();a.add_argument('--raw',action='store_true');args=a.parse_args()
r=load('results.json');rows=load('32-elf-comparison.json');assert len(rows)==32 and len({x['sha256'] for x in rows})==32
assert r['runtime_changes']==r['device_calls']==r['builds']==0 and not r['game_success']
g=next(x for x in rows if x['library']=='libyuanshen.so')
assert [s['symbol'] for s in g['routes']['current']['unresolved']]==['__register_atfork','__FD_SET_chk','__FD_ISSET_chk']
assert not g['routes']['native_cluster']['unresolved']
assert [s['symbol'] for s in g['routes']['single_atfork']['unresolved']]==['__FD_SET_chk','__FD_ISSET_chk']
assert r['ABI_only_covered_import_pairs']==sum(len(x['routes']['native_cluster']['abi_only_covered']) for x in rows)==20
assert r['new_namespace_gap']['count']==1
assert next(x for x in rows if x['library']=='libmsaoaidsec.so')['unknown_dynamic_names']
assert 'libmediandk.so' in next(x for x in rows if x['library']=='libcri_vip_unity.so')['needed']
for f in load('manifest.json')['files']:assert sha(D/f['path'])==f['sha256'] and (D/f['path']).stat().st_size==f['bytes']
verified=0
if args.raw:
 for e in load('evidence-index.json'):
  p=expand(e['path']);assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],p;verified+=1
 for e in load('first-slice.json')['sources']:assert sha(expand(e['path']))==e['sha256']
print(json.dumps({'status':'PASS','ELFs':32,'raw_hashes_verified':verified,'core_native_coverage':3,'core_single_coverage':1,'runtime_acceptance':False}))
