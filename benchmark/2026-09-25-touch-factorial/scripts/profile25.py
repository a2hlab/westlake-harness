"""Midpoint-weighted SIGQUIT occupancy estimates, never exact method timings."""
import pathlib,json,re,datetime,collections,sys
root=pathlib.Path(sys.argv[1]);rows=json.loads((root/'summary.json').read_text())
clock=(root/'clock-calibration.txt').read_text().splitlines();boot=(float(clock[0])+float(clock[2]))/2-float(clock[1].split()[0])
profiles=[]
for row in rows:
 if 'diag' not in row['run'] or not row['touches']:continue
 touches=row['touches'][:2];start=min(t['post_ms'] for t in touches);end=max(t['run_ms'] for t in touches)
 points=[]
 for s in row['ui_stacks']:
  match=re.search(r' at (.+) -----',s['wall_time'] or '')
  if not match:continue
  stamp=re.sub(r'(\.\d{6})\d+',r'\1',match[1])
  stamp=re.sub(r'([+-]\d{2})(\d{2})$',r'\1:\2',stamp)
  when=(datetime.datetime.fromisoformat(stamp).timestamp()-boot)*1000
  if not start<=when<=end:continue
  frames=[x.strip()[3:] for x in s['stack'] if x.strip().startswith('at ')]
  if not frames:continue
  method=re.sub(r'\(.*','',frames[0])
  business=next((x for x in frames if not x.startswith(('android.','java.','javax.','libcore.','dalvik.','com.android.','kotlin.'))),None)
  points.append({'sample_ms':when,'line':s['line'],'tid':s['tid'],'top_method':method,'business_frame':business,'frames':frames})
 points.sort(key=lambda x:x['sample_ms']);totals=collections.defaultdict(lambda:{'estimated_ms':0,'hits':0,'lines':[]})
 for i,p in enumerate(points):
  left=start if i==0 else (points[i-1]['sample_ms']+p['sample_ms'])/2
  right=end if i==len(points)-1 else (p['sample_ms']+points[i+1]['sample_ms'])/2
  p['estimated_occupancy_ms']=round(right-left,3)
  t=totals[p['top_method']];t['estimated_ms']+=right-left;t['hits']+=1;t['lines'].append(p['line'])
 ranked=[{'method':k,**v} for k,v in sorted(totals.items(),key=lambda item:-item[1]['estimated_ms'])]
 for v in ranked:v['estimated_ms']=round(v['estimated_ms'],3)
 profiles.append({'run':row['run'],'window_start_ms':start,'window_end_ms':end,'window_ms':end-start,'sample_count':len(points),'max_sample_gap_ms':max((b['sample_ms']-a['sample_ms'] for a,b in zip(points,points[1:])),default=None),'first_sample_delay_ms':points[0]['sample_ms']-start if points else None,'last_sample_to_run_ms':end-points[-1]['sample_ms'] if points else None,'method':'midpoint bins clipped to post(DOWN)..run(UP); sampling occupancy estimate including unobserved intervals, NOT exclusive/instrumented method timing','top_methods':ranked,'samples':points})
(root/'profiles.json').write_text(json.dumps(profiles,indent=2,ensure_ascii=False)+'\n')
for p in profiles:
 print(p['run'],p['window_ms'],p['sample_count'],p['max_sample_gap_ms'])
 for t in p['top_methods'][:8]:print(t)
