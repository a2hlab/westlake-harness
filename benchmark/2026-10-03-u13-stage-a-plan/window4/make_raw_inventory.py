"""Index persistent window evidence, including large files and symbolic links."""
import hashlib,json,os
from pathlib import Path
H=Path(__file__).resolve().parent
W=H.parents[3]
A=W/'westlake-inputs/generations/u13-stageA-window4-20261003'
I=A/'inventory'
I.mkdir(exist_ok=True)
def digest(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
 return h.hexdigest()
def normalize(s):
 return s.replace(str(W),'$WORKSPACES').replace(str(Path.home()),'$MAC_HOME')
rows=[];chunks=[];files=links=total_bytes=0

def flush():
 if not rows:return
 p=I/f'{len(chunks)+1:03d}.json'
 p.write_text(json.dumps(rows,indent=2)+'\n')
 chunks.append({'file':p.name,'sha256':digest(p),'entries':len(rows)})
 rows.clear()
for root,dirs,names in os.walk(A,followlinks=False):
 dirs.sort();names.sort()
 if Path(root)==A:dirs[:]=[d for d in dirs if d!='inventory']
 for name in list(dirs):
  p=Path(root)/name
  if p.is_symlink():names.append(name);dirs.remove(name)
 for name in sorted(names):
  p=Path(root)/name
  if p==A/'inventory-index.json':continue
  rel=str(p.relative_to(A))
  if p.is_symlink():
   rows.append({'path':rel,'type':'symlink','target':normalize(os.readlink(p))});links+=1
  elif p.is_file():
   n=p.stat().st_size;rows.append({'path':rel,'type':'file','bytes':n,'sha256':digest(p)});files+=1;total_bytes+=n
  else:raise RuntimeError(f'Unindexed special file: {rel}')
  if len(rows)>=750:flush()
flush()
index={'archive':'$WORKSPACES/westlake-inputs/generations/u13-stageA-window4-20261003','inventory_directory':'inventory','files':files,'symlinks':links,'bytes':total_bytes,'chunks':chunks,'excluded':'inventory itself and inventory-index.json only; no evidence files excluded'}
(A/'inventory-index.json').write_text(json.dumps(index,indent=2)+'\n')
(H/'raw-inventory-index.json').write_text(json.dumps(index,indent=2)+'\n')
print(json.dumps({k:v for k,v in index.items() if k!='chunks'},indent=2));print(f'chunks={len(chunks)}')
