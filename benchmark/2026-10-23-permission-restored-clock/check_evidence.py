from pathlib import Path
import json,hashlib
r=Path(__file__).resolve().parent;l=r/'.private/logs'
expected='8ab6742d58de5b9df94a2bfa80cebed46f136c0251083793fcbef8293cc23ab1'
records={}
for name in ['search','02-poll-xrefs','03-poll-decompile','04-wake-xrefs','05-wake-decompile']:
 rec=json.loads((l/(name+'.receipt.json')).read_text());assert rec['rc']==0
 d=json.loads((l/(name+'.stdout')).read_text());assert d['subject']['digest']['sha256']==expected
 records[name]={'evidence_id':d['evidence_id'],'operation':d['operation'],'parameters':d['parameters'],'rc':rec['rc']}
 if name.endswith('decompile'):
  s=d['raw_result']['value'];assert 'clock_gettime(1,' in s;assert 'tv_nsec / 1000000' in s;assert 'tv_sec * 1000' in s
  (l/(name+'.pseudocode.txt')).write_text(s)
  lines=s.splitlines();selected=[]
  # Keep only ordinary POLL/WAKE timing region in the public excerpt.
  start=next((i for i,x in enumerate(lines) if 'LAB_002bd714:' in x),0)
  for i in range(start,len(lines)):
   if any(q in lines[i] for q in ['clock_gettime','tv_nsec /','tv_sec *','[TOUCH21-POLL]','[TOUCH21-WAKE]']):
    selected.append({'line':i+1,'text':lines[i]})
    if 'fprintf' in lines[i] and i+1<len(lines):selected.append({'line':i+2,'text':lines[i+1]})
  records[name]['timing_excerpt']=selected
assert json.loads((l/'02-poll-xrefs.stdout').read_text())['raw_result']==['0x2bd768']
assert json.loads((l/'04-wake-xrefs.stdout').read_text())['raw_result']==['0x2bd858']
assert json.loads((l/'00-java.receipt.json').read_text())['rc']==0
h=Path.home()/'Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/linux/time.h'
header={'path':'$HOME/Library/Android/sdk/ndk/23.1.7779620/toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/linux/time.h','sha256':hashlib.sha256(h.read_bytes()).hexdigest(),'line':50,'text':h.read_text().splitlines()[49],'authority':'Linux UAPI naming reference only; not proven producer header or runtime libc binding'}
assert header['text']=='#define CLOCK_MONOTONIC 1'
(r/'evidence-index.json').write_text(json.dumps({'records':records,'clock_id_reference':header},indent=2)+'\n')
manifest={str(x.relative_to(r)):{'bytes':x.stat().st_size,'sha256':hashlib.sha256(x.read_bytes()).hexdigest()} for x in l.iterdir() if x.is_file()}
snap=r/'.private/analysis.snapshot.json';manifest[str(snap.relative_to(r))]={'bytes':snap.stat().st_size,'sha256':hashlib.sha256(snap.read_bytes()).hexdigest()}
(r/'raw-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
print('PASS: Java and five REA receipts rc=0; target identity; POLL/WAKE xrefs and clock expressions; snapshot/log hashes recorded.')
