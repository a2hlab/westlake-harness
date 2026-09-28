"""VM-only export of small evidence; full originals and command receipts stay in VM."""
from pathlib import Path
import hashlib,json,re,shutil
root=Path(__file__).resolve().parent
base=Path.home()/'a2hlab/board'
runs={'wikipedia':('b5-alias-ab-5ea-20260928T1906','wikipedia'), 'helloworld':('b5-alias-ab-5ea-20260928T1906','helloworld'), 'negative':('b5-negative-ab-5ea-20260928T1918','negative'), 'negative-retry':('b5-negative-ab-5ea-attempt2','negative-retry')}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
index=[]
selected={'record.json','timeline.txt','click-before.txt','click-after.txt','t3.jpeg','final.jpeg','processes-after.txt','bundle.txt','snapshot3.txt','snapshot-final.txt','paths-before.txt'}
pattern=re.compile(r'B5-ALIAS|B43-BIND|ClassNotFound|Unable to instantiate|Caused by:|UnsatisfiedLinkError|exit with code|ActivityThread.main|performLaunchActivity|handleLaunchActivity|Activity.attach|getTheme|getApplicationInfo|J_invokeStaticMain|success pid|AppSpawnChild|AppSpawn.*result',re.I)
for key,(run,subdir) in runs.items():
 src=base/run/subdir;dst=root/'evidence'/key
 if dst.exists():shutil.rmtree(dst)
 dst.mkdir(parents=True)
 for p in sorted(src.iterdir()):
  if not p.is_file():continue
  item={'vm_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size}
  if p.name in selected:shutil.copyfile(p,dst/p.name);item['export']=str((dst/p.name).relative_to(root))
  elif p.name=='hilog.txt' or p.name.startswith('fault-'):
   lines=p.read_text(errors='replace').splitlines()
   excerpt=[]
   for n,line in enumerate(lines,1):
    if (p.name=='hilog.txt' and pattern.search(line)) or (p.name.startswith('fault-') and n<=44):
     excerpt.append(f'{n}: {line}')
   target=dst/(p.stem+'-excerpt.txt');target.write_text('\n'.join(excerpt)+'\n');item['export']=str(target.relative_to(root));item['transform']='Selected lines with original line numbers; full raw file retained at vm_path'
  index.append(item)
for name in ['identity-before.txt','identity-after.txt','shell-mountinfo.txt']:
 p=base/'b5-alias-ab-5ea-20260928T1906'/name;shutil.copyfile(p,root/'evidence'/name)
 index.append({'vm_path':str(p),'sha256':sha(p),'bytes':p.stat().st_size,'export':'evidence/'+name})
(root/'raw-evidence-index.json').write_text(json.dumps(index,indent=2)+'\n')
print('archived',len(index),'raw receipts')
