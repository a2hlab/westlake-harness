from pathlib import Path
import json,shutil,hashlib
E=Path(__file__).resolve().parent
S=Path('/Users/zhaoyue/orca/workspaces/westlake-generation-state')
serial='61b0657200000000000000000324012c'
roots={'r1':S/'b87-r1-partial/b87-abi-vt-r1-61b'/serial,'r2':S/'b87-r2/b87-abi-vt-r2-61b'/serial,'r3':S/'b87-r3/b87-abi-vt-r3-61b'/serial,'r4':S/'b87-r4/b87-abi-vt-r4-61b'/serial,'controls-r1':S/'b87-controls-r1-61b','controls-r4':S/'b87-controls-r4-61b','anki-proof-r4':S/'b87-anki-proof-r4-61b','controls-restored':S/'b87-controls-restored-61b'}
need=('No implementation found','Error loading shared library','failed to map header','Xpm check failed','System.exit called','main_threw','VelocityTracker::','B87-NS','libnetguard.so','librsdroid.so','Caused by:','ensureBindApplication FAILED','JNI FatalError called:')
map_need=('libnetguard.so','librsdroid.so','liblog.so','libart.so','libc++.so','liboh_android_runtime.so','libapp_native_loader.so','liboh_adapter_bridge.so')
sources={};counts={};maps={}
for run,src in roots.items():
 if not (src/'facts.txt').is_file():continue
 sources[run]=str(src);dst=E/'evidence'/run;dst.mkdir(parents=True,exist_ok=True)
 shutil.copy2(src/'facts.txt',dst/'facts.txt');counts[run]=(src/'facts.txt').read_text()
 for record in src.glob('*/record.json'):
  app=record.parent;dest=dst/app.name;dest.mkdir(exist_ok=True)
  for name in ['record.json','processes-t5.txt','processes-t20.txt','t5.jpeg','t20.jpeg','t3.jpeg','final.jpeg','preflight.json']:
   if (app/name).exists():shutil.copy2(app/name,dest/name)
  log=app/'hilog.txt'
  if log.exists():(dest/'selected-hilog.txt').write_text('\n'.join(f'{i}:{s}' for i,s in enumerate(log.read_text(errors='replace').splitlines(),1) if any(n in s for n in need))+'\n')
  for f in app.glob('child-proof-*.sha256'):shutil.copy2(f,dest/f.name)
  rows=[]
  for f in app.glob('*maps*'):
   if not f.is_file():continue
   text=f.read_text();h=hashlib.sha256(f.read_bytes()).hexdigest()
   art=sorted({x.split()[-1] for x in text.splitlines() if x.endswith('/libart.so')})
   maps[str(f)]={'sha256':h,'art_paths':art}
   rows += ['# '+f.name+' SHA256 '+h]+[x for x in text.splitlines() if any(n in x for n in map_need)]
  if rows:(dest/'selected-maps.txt').write_text('\n'.join(rows)+'\n')
(E/'evidence-sources.json').write_text(json.dumps(sources,indent=2)+'\n')
(E/'facts.json').write_text(json.dumps(counts,indent=2)+'\n')
(E/'map-index.json').write_text(json.dumps(maps,indent=2)+'\n')
print('\n'.join(counts))
