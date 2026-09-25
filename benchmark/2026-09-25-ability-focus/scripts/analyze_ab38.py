"""VM originals: fixed-age physical trials and measured off-CPU observations."""
from board34 import *
import collections
root=pathlib.Path(__file__).resolve().parents[1]
rows=[]
for d in sorted(R.glob('ab-*-*')):
 p=d/'child.stderr'
 if not p.exists():continue
 s=p.read_text(errors='replace');row={'run':d.name,'visual_article_acceptance':'not evaluated by this parser'}
 if (d/'ab-config.json').exists():row['config']=json.loads((d/'ab-config.json').read_text())
 physical=(d/'physical-result.txt').read_text() if (d/'physical-result.txt').exists() else ''
 m=re.search(r'INPUT_BEFORE\s+([\d.]+)',physical)
 if not m:row['invalid']='no timed physical article touch';rows.append(row);continue
 t0=round(float(m[1])*1000);row['input_ms']=t0
 starts=[]
 for m in re.finditer(r'^\[ABILITY38-START\] uptime=(\d+) intent=.*',s,re.M):
  if int(m[1])>=t0:starts.append({'delta_ms':int(m[1])-t0,'line':m[0]})
 row['starts']=starts
 entry=re.search(r'^\[B47-SLA\] ENTRY .*ability=com\.ss\.android\.detail\.feature\.detail2\.view\.NewDetailActivity recordId=(\d+).*',s,re.M)
 resume=None
 if entry:
  q=re.search(r'^\[ABILITY38-RESUMED\] uptime=(\d+) token=(\S+)',s[entry.end():],re.M)
  if q and int(q[1])>t0:resume=int(q[1]);row['resume_ms']=resume;row['resume_delta_ms']=resume-t0;row['detail_record_id']=entry[1];row['resumed_token']=q[2]
 events=[]
 for m in re.finditer(r'^\[ABILITY38-DISPATCH\] phase=begin seq=(\d+) uptime=(\d+) queueMs=(\d+).*action=(ACTION_\w+)',s,re.M):
  seq,ms,q,action=m.groups();ms=int(ms)
  if not t0<=ms<t0+45000:continue
  end=re.search(r'^\[ABILITY38-DISPATCH\] phase=end seq='+seq+r' uptime=(\d+)',s[m.end():],re.M)
  events.append({'action':action,'queue_ms':int(q),'dispatch_ms':int(end[1])-ms if end else None})
 row['events']=events
 if (d/'offcpu.txt').exists():
  samples=[]
  for line in (d/'offcpu.txt').read_text().splitlines():
   cols=line.split('\t')
   if len(cols)!=4 or not cols[0].isdigit() or ') ' not in cols[3]:continue
   st=cols[3].rsplit(') ',1)[1].split();samples.append({'ms':int(cols[0]),'wchan':cols[1].strip(),'syscall':cols[2].strip(),'state':st[0],'cpu_ticks':int(st[11])+int(st[12]),'cpu':st[36]})
  row['offcpu']={}
  for label,lo,hi in [('click_to_resume',t0,resume or t0+45000),('webview_2.1_to_10.2s',t0+2100,min(t0+10200,resume or t0+10200))]:
   selected=[x for x in samples if lo<=x['ms']<hi];states=collections.Counter();waits=collections.Counter();syscalls=collections.Counter();futex=collections.Counter()
   for x,y in zip(selected,selected[1:]):
    weight=min(250,y['ms']-x['ms']);states[x['state']]+=weight;waits[x['wchan']]+=weight
    fields=x['syscall'].split();call=fields[0] if fields else 'unknown';syscalls[call]+=weight
    if call=='98' and len(fields)>2:futex[fields[1]+' op='+fields[2]]+=weight
   row['offcpu'][label]={'sample_count':len(selected),'state_ms':dict(states),'wchan_ms':dict(waits),'syscall_ms':dict(syscalls),'futex_address_ms':dict(futex),'cpu_ticks_delta':selected[-1]['cpu_ticks']-selected[0]['cpu_ticks'] if selected else None,'note':'State R includes runnable time. CPU ticks need CLK_TCK. Wait ownership and OH service identity are not inferred from address alone.'}
 row['jit_disabled_log']='ART JIT DISABLED' in (d/'parent.log').read_text(errors='replace')
 row['oat_maps']=[line for line in (d/'maps-before.txt').read_text().splitlines() if '/oat/arm64/toutiao.' in line] if (d/'maps-before.txt').exists() else []
 rows.append(row)
(root/'ab-summary.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for r in rows:print(r['run'],'resume',r.get('resume_delta_ms'),r.get('invalid'),r.get('offcpu',{}))
