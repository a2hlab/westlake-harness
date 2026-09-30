#!/usr/bin/env python3
"""Save first raw matches; no inference that each warning terminated an app."""
from pathlib import Path
import json,hashlib
R=Path(__file__).resolve().parent
markers=['relocating failed:', 'Error loading shared library', 'failed to map header', 'No implementation found', 'FATAL EXCEPTION', 'UNCAUGHT in', 'Unable to start activity', 'Failed to resolve attribute', 'Signal:SIG', 'Fatal signal', 'finishActivity(', '[N3-OWNER]']
rows=[]
for f in sorted((R/'runs').glob('*/*/*/record.json')):
 d=json.loads(f.read_text());log=f.parent/'hilog.txt';lines=log.read_text(errors='replace').splitlines() if log.exists() else []
 matches=[]
 for marker in markers:
  selected=[{'line':i+1,'text':line} for i,line in enumerate(lines) if marker in line]
  if selected:matches.append({'marker':marker,'first':selected[0],'count':len(selected)})
 rows.append({'run':f.parents[2].name,'key':f.parent.name,'record':str(f.relative_to(R)),'log':str(log.relative_to(R)),'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest() if log.exists() else None,'status':d.get('status'),'error':d.get('error'),'raw_first_matches':matches,'causality':'requires PID/time and screenshot review; first occurrence is not automatically fatal'})
(R/'first-wall-candidates.json').write_text(json.dumps(rows,indent=2)+'\n')
print(len(rows),'app records indexed')
