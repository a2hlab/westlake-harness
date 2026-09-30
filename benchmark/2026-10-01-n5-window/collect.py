#!/usr/bin/env python3
import collections,gzip,hashlib,json,re,shutil,subprocess,tarfile
from pathlib import Path
H=Path(__file__).resolve().parent;R=H.parents[1];S='5ea34a4500000000000000001123012c'
def write(p,x):p.write_text(json.dumps(x,indent=2)+'\n')
def process_samples(phase,uid):
 p=H/('maps-observations.jsonl' if phase=='n5' else 'maps-observations-u5.jsonl');found=[]
 for line in p.read_text().splitlines():
  obs=json.loads(line);raw=gzip.decompress((H/obs['file']).read_bytes()).decode(errors='replace')
  pids={int(v[0]) for line in raw.split('MAPS_BEGIN:')[0].splitlines() if len(v:=line.split())>=4 and v[0].isdigit() and v[2].isdigit() and int(v[2])==uid}
  for child in obs['processes']:
   if child['pid'] in pids:found.append(dict(time=obs['time'],file=obs['file'],**child))
 return found
runs=[];facts=[];e=H/'evidence';e.mkdir(exist_ok=True)
for root in sorted((H/'runs').glob('*/'+S)):
 if not (root/'facts.txt').exists():continue
 facts.append('== '+root.parent.name+' ==\n'+(root/'facts.txt').read_text())
 for p in root.glob('*/record.json'):
  rec=json.loads(p.read_text());dest=e/root.parent.name/rec['key'];dest.mkdir(parents=True,exist_ok=True)
  for name in ['record.json','t5.jpeg','t20.jpeg','processes-t5.txt','processes-t20.txt','processes-after.txt','diagnostics.json']:
   if (p.parent/name).exists():shutil.copy2(p.parent/name,dest/name)
  for name in ['facts.txt','runtime-fingerprint.txt','boot-image-fingerprint.txt','preflight.json','baseline.json']:
   if (root/name).exists():shutil.copy2(root/name,dest/name)
  if (p.parent/'hilog.txt').exists():(dest/'hilog.txt.gz').write_bytes(gzip.compress((p.parent/'hilog.txt').read_bytes(),mtime=0))
  runs.append(dict(run=root.parent.name,key=rec['key'],uid=rec.get('bms',{}).get('uid'),t20=str((dest/'t20.jpeg').relative_to(H)),record=str((dest/'record.json').relative_to(H))))
(H/'facts-all.txt').write_text('\n'.join(facts))
compare={}
for phase,run in [('n5','n5-localsend'),('u5','u5-after-n5-localsend')]:
 selected=next((x for x in runs if x['run']==run),None)
 if not selected:continue
 samples=process_samples(phase,selected['uid']);compare[phase]=dict(uid=selected['uid'],samples=samples,observed_pids=sorted({x['pid'] for x in samples}),duplicate_seen=any(x['duplicate'] for x in samples))
 if samples:
  first=next((s for s in samples if s['duplicate']),samples[0]);raw=gzip.decompress((H/first['file']).read_bytes()).decode(errors='replace');(H/(phase+'-localsend-maps.txt')).write_text(raw)
  log=gzip.decompress((H/selected['record']).parent.joinpath('hilog.txt.gz').read_bytes()).decode(errors='replace');pids=set(compare[phase]['observed_pids'])
  child_lines=[line for line in log.splitlines() if len(v:=line.split())>3 and v[2].isdigit() and int(v[2]) in pids]
  (H/(phase+'-localsend-child-hilog.txt.gz')).write_bytes(gzip.compress(('\n'.join(child_lines)+'\n').encode(),mtime=0))
  proposed=json.loads((H.parent/'2026-10-01-n5-baseline-gates/exception-proposal.json').read_text())['entries'];names={x['finding']['needed'] for x in proposed if x['classification']=='n5-only'}
  errors=[line for line in child_lines if any(n in line for n in names) and any(t in line.lower() for t in ['dlopen_impl load library header failed','library not found','error loading shared library'])]
  compare[phase]['dependency_error_lines']=errors
  (H/(phase+'-dependency-errors.txt')).write_text('\n'.join(errors)+'\n')
if len(compare)==2:
 compare['conclusion']='preexisting_alias_double_mapping' if compare['u5']['duplicate_seen'] else ('n5_only_duplicate_observed' if compare['u5']['samples'] else 'baseline_unknown_no_maps')
write(H/'duplicate-baseline.json',compare);write(H/'run-index.json',runs)
with tarfile.open(H/'maps-evidence.tar.gz','w:gz') as archive:
 for p in sorted((H/'maps').glob('*')):archive.add(p,arcname='maps/'+p.name)
print(json.dumps({k:{kk:vv for kk,vv in v.items() if kk not in ['samples','dependency_error_lines']} if isinstance(v,dict) else v for k,v in compare.items()},indent=2))
