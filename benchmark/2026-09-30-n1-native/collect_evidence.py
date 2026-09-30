#!/usr/bin/env python3
"""Create a small index; retain raw runs on disk and stage only review evidence."""
from pathlib import Path
import json,hashlib,re
P=Path(__file__).resolve().parent;R=P.parents[1];rows=[];staged=[]
for run in sorted((P/'device-61b/runs').iterdir()):
 for dev in run.iterdir():
  if not dev.is_dir():continue
  for name in ['facts.txt','baseline.json','runtime-fingerprint.txt','plan.json','preflight.json']:
   f=dev/name
   if f.exists():staged.append(str(f.relative_to(R)))
  for record in sorted(dev.glob('*/record.json')):
   d=json.loads(record.read_text());h=record.parent/'hilog.txt';text=h.read_text(errors='replace') if h.exists() else ''
   patterns=r'FATAL EXCEPTION|Reason:Signal:|Unable to start activity|UnsatisfiedLinkError|nativeOpenAssetFd|Implement me|\[WL-N1|\[OH_EglHijack\]|Caused by:'
   hits=[{'line':i+1,'text':s} for i,s in enumerate(text.splitlines()) if re.search(patterns,s)]
   # These are candidates for review, not automatic attribution of every error.
   excerpt=record.parent/'selected-log-lines.json';excerpt.write_text(json.dumps({'hilog_sha256':hashlib.sha256(h.read_bytes()).hexdigest() if h.exists() else None,'hits':hits},indent=2)+'\n')
   fs=[record,excerpt]+[record.parent/n for n in ['t20.jpeg','processes-t5.txt','processes-t20.txt']]
   for f in fs:
    if f.exists():staged.append(str(f.relative_to(R)))
   rows.append({'run':run.name,'key':d['key'],'status':d['status'],'record':str(record.relative_to(R)),'screenshots':d.get('screenshots',[]),'hilog_sha256':hashlib.sha256(h.read_bytes()).hexdigest() if h.exists() else None,'log_excerpt':str(excerpt.relative_to(R))})
(P/'device-index.json').write_text(json.dumps(rows,indent=2)+'\n');(P/'evidence-files.txt').write_text('\n'.join(staged)+'\n');print('indexed',len(rows),'records')
