"""Count D-state intervals up to successful wakeup, not the next on-CPU switch."""
import re,json,pathlib,sys,gzip
STAMP=re.compile(r'\s(\d+\.\d+):\s+(\w+):\s+(.*)')
SWITCH=re.compile(r'prev_pid=(\d+).*?prev_state=(\S+).*?next_pid=(\d+)')
WAKE=re.compile(r'\bpid=(\d+)')
def analyze(lines,tid,begin,seconds=23):
 end=begin+seconds;pending=None;spans=[];fallback=[];times=[];lost=[]
 for n,line in enumerate(lines,1):
  if 'LOST' in line or 'entries-in-buffer' in line:lost.append(line.strip())
  m=STAMP.search(line)
  if not m:continue
  t=float(m[1]);event=m[2];body=m[3];times.append(t)
  if event=='sched_switch':
   x=SWITCH.search(body)
   if not x:continue
   if int(x[3])==tid and pending is not None:
    fallback.append({'start':pending,'end':t,'line':n});spans.append((pending,t));pending=None
   if int(x[1])==tid and 'D' in x[2]:pending=t
  elif event in ('sched_wakeup','sched_wakeup_new'):
   x=WAKE.search(body)
   if x and int(x[1])==tid and pending is not None:spans.append((pending,t));pending=None
 clipped=[(max(a,begin),min(b,end)) for a,b in spans if min(b,end)>max(a,begin)]
 return {'tid':tid,'window_begin':begin,'window_end':end,'D_seconds':sum(b-a for a,b in clipped),'D_intervals':len(clipped),'max_D_seconds':max([b-a for a,b in clipped],default=0),'missing_wakeup_fallbacks':fallback,'unclosed_D_start':pending,'trace_time_range':[min(times),max(times)] if times else [],'trace_headers':lost,'intervals':clipped}
if __name__=='__main__':
 p=pathlib.Path(sys.argv[1]);d=json.loads((p/'device-report.json').read_text());s=(p/'child.stderr').read_text(errors='replace');m=re.search(r'WESTLAKE-GONW\] 1 ENTER tid=(\d+)',s)
 ids={'process_main':int(d['child'])};rows={}
 if m:ids['java_ui']=int(m[1])
 for role,tid in ids.items():
  with (gzip.open(p/'sched.trace.gz','rt',errors='replace') if (p/'sched.trace.gz').exists() else (p/'sched.trace').open(errors='replace')) as f:rows[role]=analyze(f,tid,float(d['spawn_uptime_before'].split()[0]))
 (p/'trace-summary.json').write_text(json.dumps(rows,indent=2)+'\n');print(json.dumps({k:{a:b for a,b in v.items() if a!='intervals'} for k,v in rows.items()},indent=2))
