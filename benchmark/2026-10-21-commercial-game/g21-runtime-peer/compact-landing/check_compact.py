#!/usr/bin/env python3
"""Offline compact evidence validator. Optional external paths are read only."""
import argparse,gzip,hashlib,json
from pathlib import Path
P=Path(__file__).resolve().parent
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(n):return json.loads((P/n).read_text())
def main():
 a=argparse.ArgumentParser();a.add_argument('--main',type=Path);a.add_argument('--raw',type=Path);args=a.parse_args()
 manifest=read('manifest.json')['files']
 for name,row in manifest.items():
  f=P/name;assert f.is_file() and digest(f)==row['sha256'] and f.stat().st_size==row['size'],name
 files=[f for f in P.rglob('*') if f.is_file() and '__pycache__' not in f.parts]
 total=sum(f.stat().st_size for f in files);assert total<1000000,total
 assert not any('stderr' in f.name or f.name.startswith('journal') or f.suffix=='.jpeg' for f in files)
 ix=json.loads(gzip.decompress((P/'original-sha-index.json.gz').read_bytes()))
 assert len(ix)==read('source-index.json')['original_files']==9922
 assert 'journal.json' not in ix and ix['journal-after-automatic-rollback.json']['sha256']=='e4ead80b9dfe744df841309a5e928cf2a03981380412f7955657012517e3ca95'
 if args.raw:
  for rel,row in ix.items():
   f=args.raw/rel;assert f.stat().st_size==row['size'] and digest(f)==row['sha256'],rel
 if args.main:
  for row in read('public-evidence-refs.json')['files']:
   f=args.main/row['repository_path'];assert f.stat().st_size==row['size'] and digest(f)==row['sha256'],str(f)
 initial=read('initial/results.json');recovery=read('recovery/results.json');closure=read('closure/results.json')
 assert initial['rc']==2 and recovery['rc']==0 and closure['game_started'] is False
 baseline=read('initial/hash-stages.json')['baseline_after_unmount']['observed'];assert len(baseline)==319
 for stage in read('recovery/hash-stages.json').values():assert stage['observed']==baseline
 for stage in read('initial/hash-stages.json').values():assert len(stage['observed'])==319
 labels=read('label-summary.json')['audits'];assert len(labels)==4 and all(x['paths']==295 for x in labels)
 assert labels[-1]['audit']=='after' and labels[-1]['status']=='PASS' and labels[-1]['mismatches']==0
 assert closure['closure_receipt']['lock_released'] and closure['boat_preserved_hashes']==3
 print(json.dumps({'status':'PASS','package_bytes':total,'indexed_originals':len(ix),'private_originals':'verified' if args.raw else 'SKIPPED: --raw omitted','main_refs':'verified' if args.main else 'SKIPPED: --main omitted','device_io':False}))
if __name__=='__main__':main()
