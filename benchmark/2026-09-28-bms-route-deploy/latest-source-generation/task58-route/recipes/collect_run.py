from pathlib import Path
import json,shutil,hashlib,re,sys
R=Path.cwd();T=Path(__file__).resolve().parents[1];src=Path(sys.argv[1]);label=sys.argv[2];dst=T/label;dst.mkdir(parents=True,exist_ok=True)
for p in src.iterdir():
 if p.is_file() and p.name in ['identity-before.txt','identity-after.txt','results.json','shell-mountinfo.txt']:shutil.copy2(p,dst/p.name)
for d in src.iterdir():
 if not d.is_dir() or not (d/'record.json').exists():continue
 o=dst/d.name;o.mkdir(exist_ok=True);rec=json.loads((d/'record.json').read_text())
 for p in d.iterdir():
  if p.is_file() and (p.name in ['record.json','t3.jpeg','final.jpeg','timeline.txt','processes-after.txt','click-before.txt','click-after.txt'] or p.name.endswith(('.sha256','.late-sha256','.late-maps','-maps.txt'))):shutil.copy2(p,o/p.name)
 pids=set(rec['pids_after'])
 for p in d.glob('child-proof-*.started'):pids.add(int(p.name.split('-')[2].split('.')[0]))
 for p in d.glob('child-proof-*.sha256'):pids.add(int(p.name.split('-')[2].split('.')[0]))
 lines=(d/'hilog.txt').read_text(errors='replace').splitlines()
 focused=[f'{i}: {l}' for i,l in enumerate(lines,1) if any(re.search(r'\s'+str(pid)+r'\s',l) for pid in pids)]
 (o/'hilog-excerpt.txt').write_text('\n'.join(focused)+'\n')
 for p in d.glob('fault-*.txt'):
  ls=p.read_text(errors='replace').splitlines();out=ls[:80]+['Relevant mappings:']+[l for l in ls if any(x in l for x in ['libart.so','libopenjdkjvm.so','libsigchain.so','libdfx_signalhandler'])];(o/(p.stem+'-excerpt.txt')).write_text('\n'.join(out)+'\n')
 (o/'provenance.json').write_text(json.dumps({'raw_directory':str(d),'pids':sorted(pids),'files':{p.name:{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size} for p in d.iterdir() if p.is_file()}},indent=2)+'\n')
 print(label,d.name,rec['pids_after'],rec['new_faults'])
