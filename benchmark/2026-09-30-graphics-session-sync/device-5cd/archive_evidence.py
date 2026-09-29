#!/usr/bin/env python3
"""Archive actual record/process/screenshot evidence; never infer capture or liveness counts."""
from pathlib import Path
import json,re,shutil
R=Path(__file__).resolve().parent
for run in (R/'runs').iterdir():
 if not run.is_dir():continue
 for serial in run.iterdir():
  if not serial.is_dir():continue
  dest=R/'evidence'/run.name;dest.mkdir(parents=True,exist_ok=True)
  if (serial/'facts.txt').exists():shutil.copy2(serial/'facts.txt',dest/'facts.txt')
  elif (run/'facts.txt').exists():shutil.copy2(run/'facts.txt',dest/'facts.txt')
  for name in ['preflight.json','runtime-fingerprint.json','runtime-fingerprint.txt']:
   if (serial/name).exists():shutil.copy2(serial/name,dest/name)
  rows=[]
  for record in serial.glob('*/record.json'):
   src=record.parent;d=json.loads(record.read_text());out=dest/d['key'];out.mkdir(exist_ok=True)
   shutil.copy2(record,out/'record.json')
   for f in src.glob('*process*'):
    if f.is_file():(out/f.name).write_text('\n'.join(line.rstrip() for line in f.read_text().splitlines())+'\n')
   for s in d['screenshots']:
    if s.get('captured'):shutil.copy2(s['path'],out/Path(s['path']).name)
   lines=(src/'hilog.txt').read_text(errors='replace').splitlines() if (src/'hilog.txt').exists() else []
   pids=set(x for s in d['screenshots'] for x in s.get('foreground',{}).get('observed_pids',[]))
   for l in lines:
    if 'BLASTBufferQueue registered 13/13' in l:
     m=re.match(r'\S+\s+\S+\s+(\d+)\s+',l)
     if m:pids.add(int(m[1]))
   selected=[];fatals=[];surfaces=[];registered=[];background=[]
   for i,l in enumerate(lines):
    parts=l.split()
    own=len(parts)>3 and parts[2].isdigit() and int(parts[2]) in pids
    if not own:continue
    if any(x in l for x in ['JNI FatalError called:','FATAL EXCEPTION:','Fatal signal ','ABORT:']):fatals.append({'line':i+1,'text':l})
    if 'background thread ' in l and 'uncaught' in l:background.append({'line':i+1,'text':l})
    if 'BLASTBufferQueue registered 13/13' in l:registered.append({'line':i+1,'text':l})
    if "SC.create 'OH_Surface_" in l:surfaces.append({'line':i+1,'text':l})
    if any(x in l for x in ['JNI FatalError called:','FATAL EXCEPTION:','ABORT:','registered 13/13',"SC.create 'OH_Surface_",'oh_rs_flush_transaction','TransactionHang:','finishDrawing:','uncaught, thread ended','SURFACE_CHANGED(firstCreate)','eglCreateWindowSurface']):selected.append(f'{i+1}: {l}'.rstrip())
   (out/'hilog-excerpt.txt').write_text('\n'.join(selected)+'\n')
   rows.append({'key':d['key'],'desktop_activity':d.get('desktop_activity'),'status':d['status'],'pids':sorted(pids),'first_fatal':fatals[0] if fatals else None,'fatal_absence_scope':'captured hilog target PIDs only; not proof of no fault','background_uncaught':background,'blast_registration':registered,'surface_bindings':surfaces,'source_record':str(record),'source_hilog':str(src/'hilog.txt')})
  (dest/'observations.json').write_text(json.dumps(rows,indent=2)+'\n')
  print(dest)
