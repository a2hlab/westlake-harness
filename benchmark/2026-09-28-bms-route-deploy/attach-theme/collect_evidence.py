"""Read-only extraction of existing VM experiments; no board commands."""
from pathlib import Path
import hashlib,json,shutil
r=Path(__file__).resolve().parent
index=[]
for run,label in [('b6-context-fixed-5ea','rejected-full-cohort'),('b6-rollback-baseline-5ea','rollback-baseline')]:
 base=Path.home()/'a2hlab/board'/run
 for app in ['wikipedia','helloworld','zigzag']:
  src=base/app
  if not src.exists():continue
  dest=r/'evidence'/label/app;dest.mkdir(parents=True,exist_ok=True)
  for p in src.iterdir():
   if not p.is_file():continue
   index.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
   if p.name in ['record.json','final.jpeg','t3.jpeg','timeline.txt','processes-after.txt'] or p.name.startswith('child-proof-'):shutil.copy2(p,dest/p.name)
   if p.name.startswith('fault-'):
    lines=p.read_text(errors='replace').splitlines();(dest/(p.stem+'-excerpt.txt')).write_text('\n'.join(lines[:90])+'\n')
   if p.name=='hilog.txt':
    lines=p.read_text(errors='replace').splitlines();sel=[s for s in lines if any(t in s for t in ['B6ContextWrapper','InflaterInputStream','ContextWrapper.getApplicationInfo','ContextImpl.getTheme','LaunchActivityAliasProjection'])];(dest/'hilog-excerpt.txt').write_text('\n'.join(sel)+'\n')
for name in ['baseline-boot-probe','extension-boot','extension-boot-v2']:
 p=Path('/home/zhaoyue/a2hlab/build-runs/20260928-oh6.1.0.31-b6')/name/'stderr.log'
 if p.exists():
  index.append({'path':str(p),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size})
  lines=p.read_text(errors='replace').splitlines();sel=[s for s in lines if any(t in s for t in ['Error reading','error:', 'Check failed','Fatal','SIGSEGV'])];(r/(name+'-failure.txt')).write_text('\n'.join(sel[:20])+'\n')
(r/'evidence-index.json').write_text(json.dumps(index,indent=2)+'\n')
print('archived',len(index),'files in index')
