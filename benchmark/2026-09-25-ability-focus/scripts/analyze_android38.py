"""Match Android atrace cookies; no substring-only Activity acceptance."""
import json,pathlib,re
root=pathlib.Path(__file__).resolve().parents[1];results=[]
for name in ('c2','c3','c4'):
 p=root/'android-reference'/name
 t0=float(re.search(r'INPUT_BEFORE\n([\d.]+)',(p/'physical-reference.txt').read_text())[1])
 pending={};consumer={};events=[]
 for line in (p/'atrace.txt').open():
  m=re.search(r'\s([\d.]+): tracing_mark_write: ([SFB])\|(\d+)\|(.*)',line)
  if not m:continue
  stamp=float(m[1]);kind=m[2];pid=m[3];payload=m[4]
  if not t0 <= stamp <= t0+2 or 'id.article.news-' not in line:continue
  if kind=='S' and payload.startswith('InputConsumer processing on ') and '.activity.MainActivity ' in payload:consumer[pid]=stamp
  if payload.startswith('deliverInputEvent|'):
   cookie=payload.split('|')[1];key=(pid,cookie)
   if kind=='S':pending[key]={'pid':int(pid),'cookie':cookie,'dispatch_begin':stamp,'consumer_begin':consumer.get(pid)}
   elif kind=='F' and key in pending:
    event=pending.pop(key);event['dispatch_end']=stamp
    event['dispatch_ms']=(stamp-event['dispatch_begin'])*1000
    event['receive_to_dispatch_ms']=(event['dispatch_begin']-event['consumer_begin'])*1000 if event['consumer_begin'] else None
    events.append(event)
  elif kind=='B' and payload.startswith('deliverInputEvent src=0x1002 '):
   em=re.search(r'eventTimeNano=(\d+) id=0x([0-9a-f]+)',payload)
   if em:
    signed=int(em[2],16);signed=signed if signed<2**31 else signed-2**32
    e=pending.get((pid,str(signed)))
    if e:e.update(event_time=int(em[1])/1e9,event_age_ms=(stamp-int(em[1])/1e9)*1000)
 lifecycle=[]
 for line in (p/'logcat.txt').open(errors='replace'):
  m=re.match(r'\s*(\d+\.\d+)',line)
  if m and t0<float(m[1])<t0+5 and 'wm_on_resume_called:' in line and ',com.ss.android.detail.feature.detail2.view.NewDetailActivity,' in line:lifecycle.append({'uptime':float(m[1]),'line':line.strip()})
 assert len(events)==2,(name,events)
 assert len(lifecycle)==1,(name,lifecycle)
 results.append({'name':name,'input_before':t0,'input_path':'Android input tap (reference only, not OH uinput)','events':events,'detail_resume_ms':(lifecycle[0]['uptime']-t0)*1000,'lifecycle':lifecycle[0]})
(root/'android-summary.json').write_text(json.dumps(results,indent=2)+'\n')
for r in results:print(r['name'],'receive->dispatch',[round(e['receive_to_dispatch_ms'],3) for e in r['events']],'dispatch',[round(e['dispatch_ms'],3) for e in r['events']],'resume',round(r['detail_resume_ms'],1))
