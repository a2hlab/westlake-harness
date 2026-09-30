#!/usr/bin/env python3
"""Summarize captured maps by the app's BMS UID; mapping is not a UI verdict."""
from pathlib import Path
import json
P=Path(__file__).resolve().parent
out=[]
for run in sorted((P/'runs').iterdir()):
 index=P/'maps'/run.name/'index.json'
 if not index.exists():continue
 samples=json.loads(index.read_text())
 for f in sorted(run.glob('61b*/*/record.json')):
  d=json.loads(f.read_text());uid=d.get('bms',{}).get('uid');rows=[]
  for x in samples:
   if uid is None or x.get('uid')!=uid or 'maps' not in x:continue
   m=Path(x['maps']);paths=sorted({s.split()[-1] for s in m.read_text().splitlines() if len(s.split())>=6 and s.split()[-1].startswith('/')})
   selected={name:[v for v in paths if v.endswith('/'+name)] for name in ['libart.so','liboh_android_runtime.so','libflutter.so','libjnidispatch.so','libwestlake_native_abi.so','libsoundpool.so','libsurface.z.so','liblog.so','libdfx_signalhandler.z.so']}
   rows.append({'pid':x['pid'],'sample':x['sample'],'maps':str(m.relative_to(P)),'selected_paths':selected,'art_path_count':len(selected['libart.so'])})
  out.append({'run':run.name,'key':d['key'],'uid':uid,'samples':rows,'inference_limit':'only sampled PID/UID mappings, not successful JNI initialization or lighting'})
(P/'maps-summary.json').write_text(json.dumps(out,indent=2)+'\n')
print('mapped app records',len(out))
