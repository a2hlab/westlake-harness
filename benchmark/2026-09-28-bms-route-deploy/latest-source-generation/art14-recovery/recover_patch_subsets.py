"""Recover exact frozen bytes using only subsets of existing patch hunks.

A candidate is written only when its SHA256 equals the frozen file fingerprint.
No candidate is accepted merely because patch application or compilation works.
"""
import argparse,hashlib,itertools,json,re
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--destination',type=Path,required=True);p.add_argument('--manifest',type=Path,required=True);p.add_argument('--patch-root',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
want={name.removeprefix('./aosp/art/'):sha for sha,name in (line.split(maxsplit=1) for line in a.manifest.read_text().splitlines()) if name.startswith('./aosp/art/')}
records=[]
for patch in sorted(a.patch_root.rglob('*.patch')):
    lines=patch.read_text().splitlines(keepends=True)
    targets=[x[6:].strip() for x in lines if x.startswith('+++ b/')]
    if len(targets)!=1 or targets[0] not in want:continue
    target=targets[0];source=a.base/target
    if not source.is_file():continue
    destination=a.destination/target
    if destination.is_file() and hashlib.sha256(destination.read_bytes()).hexdigest()==want[target]:continue
    if not target.endswith(('.cc','.h')):continue
    hunks=[]
    for line in lines:
        if line.startswith('@@'):
            m=re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@',line)
            hunks.append({'start':int(m[1])-1,'old':[],'new':[]})
        elif hunks:
            if line.startswith((' ','-')):hunks[-1]['old'].append(line[1:])
            if line.startswith((' ','+')):hunks[-1]['new'].append(line[1:])
    rec={'target':target,'patch':str(patch),'patch_sha256':hashlib.sha256(patch.read_bytes()).hexdigest(),'hunk_count':len(hunks),'expected_sha256':want[target]}
    base=source.read_text().splitlines(keepends=True);segments=[];end=0
    if len(hunks)>18 or not hunks:
        rec['status']='not_enumerated';records.append(rec);continue
    valid=True
    for h in hunks:
        if h['start']<end or base[h['start']:h['start']+len(h['old'])]!=h['old']:valid=False;break
        segments.append(''.join(base[end:h['start']]).encode());end=h['start']+len(h['old'])
        h['old']=''.join(h['old']).encode();h['new']=''.join(h['new']).encode()
    if not valid:
        rec['status']='context_mismatch';records.append(rec);continue
    tail=''.join(base[end:]).encode();rec['status']='no_matching_subset'
    for flags in itertools.product([False,True],repeat=len(hunks)):
        data=b''.join(s+h['new' if f else 'old'] for s,h,f in zip(segments,hunks,flags))+tail
        if hashlib.sha256(data).hexdigest()==want[target]:
            destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(data)
            rec['status']='exact_match';rec['selected_hunks']=[i+1 for i,f in enumerate(flags) if f];break
    records.append(rec);print(target,rec['status'],flush=True)
a.out.write_text(json.dumps(records,indent=2)+'\n')
