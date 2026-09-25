"""Derive diagnostic timing; screenshots/lifecycle component association need review."""
import pathlib,json,gzip,re,sys
root=pathlib.Path(__file__).resolve().parents[1]
def read(p):
 if p.exists():return p.read_text(errors='replace')
 q=p.with_suffix(p.suffix+'.gz')
 return gzip.decompress(q.read_bytes()).decode(errors='replace') if q.exists() else ''
rows=[]
for name in sys.argv[1:]:
 r=root/'evidence'/name;s=read(r/'child.stderr');physical=read(r/'physical-result.txt')
 t=re.search(r'INPUT_BEFORE\s+(\d+\.\d+)',physical)
 row={'run':name,'input_before_ms':float(t[1])*1000 if t else None,'data':json.loads(read(r/'data-provenance.json') or '{}'),'events':[]}
 if t:
  t0=row['input_before_ms'];ends={}
  for m in re.finditer(r'^\[ABILITY38-DISPATCH\] phase=end seq=(\d+) uptime=(\d+)',s,re.M):ends.setdefault(m[1],[]).append(int(m[2]))
  for m in re.finditer(r'^\[ABILITY38-DISPATCH\] phase=begin seq=(\d+) uptime=(\d+) queueMs=(\d+) event=MotionEvent \{ action=(ACTION_\w+)',s,re.M):
   seq,begin,queue,action=m.groups();begin=int(begin)
   if not t0<=begin<t0+45000:continue
   end=next((v for v in ends.get(seq,[]) if v>=begin),None)
   row['events'].append({'seq':seq,'begin_ms':begin,'queue_ms':int(queue),'action':action,'dispatch_ms':end-begin if end else None})
  row['markers']={}
  for tag in ('RECEIVE','DECOR','FINISH','TARGET','CLICK','START','RESUMED'):
   lines=[]
   for line in s.splitlines():
    if not line.startswith('[ABILITY38-'+tag+']'):continue
    m=re.search(r'uptime=(\d+)',line)
    if m and t0<=int(m[1])<t0+60000:lines.append({'from_input_ms':round(int(m[1])-t0,3),'line':line})
   row['markers'][tag]=lines
  row['post_input_lifecycle']=read(r/'after-45s-lifecycle.txt').splitlines()
 row['failures']=[line for line in s.splitlines() if line.startswith('[INITCHILD-FAIL]') or line.startswith('Fatal signal')]
 row['fault_files']=[p.name for p in r.glob('cppcrash-*')]
 rows.append(row)
(root/'oh-summary.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
for row in rows:print(row['run'],row['input_before_ms'],row['events'],row['failures'])
