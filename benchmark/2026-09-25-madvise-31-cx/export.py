from pathlib import Path
import gzip,json,hashlib,re,shutil,sys
from analyze_trace import analyze,STAMP,SWITCH,WAKE
root=Path(__file__).resolve().parent
vm=Path('/Users/zhaoyue/OrbStack/a2hlab/home/zhaoyue/a2hlab')
r=vm/'board/5cd1e3dd00000000000000000923012c/madvise31cx';o=vm/'ws/out-madvise31-cx'
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def put(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if src.suffix in ('.stderr','.log','.jsonl','.txt'):
  with src.open('rb') as f,gzip.GzipFile(str(dst)+'.gz','wb',mtime=0) as g:shutil.copyfileobj(f,g)
 else:shutil.copyfile(src,dst)
rows=[]
for name in sys.argv[1:]:
 p=r/name;e=root/'evidence'/name;e.mkdir(parents=True,exist_ok=True)
 d=json.loads((p/'device-report.json').read_text());raw=(p/'child.stderr').read_bytes();lines=raw.decode(errors='replace').splitlines();text='\n'.join(lines);match=re.search(r'WESTLAKE-GONW\] 1 ENTER tid=(\d+)',text);ui=int(match[1]) if match else None;ids={int(d['child'])};ids.update([ui] if ui else [])
 src=p/('sched.trace.gz' if (p/'sched.trace.gz').exists() else 'sched.trace');first=last=None;count=0
 with (gzip.open(src,'rt',errors='replace') if src.suffix=='.gz' else src.open(errors='replace')) as f,gzip.GzipFile(str(e/'threads.trace.gz'),'wb',mtime=0) as g:
  for line in f:
   m=STAMP.search(line);keep=line.startswith('#')
   if m:
    if first is None:first=line;keep=True
    last=line
    if m[2]=='sched_switch':
     x=SWITCH.search(m[3]);keep=bool(x and (int(x[1]) in ids or int(x[3]) in ids)) or keep
    elif m[2] in ('sched_wakeup','sched_wakeup_new'):
     x=WAKE.search(m[3]);keep=bool(x and int(x[1]) in ids) or keep
   if keep:g.write(line.encode());count+=1
  if last:g.write(last.encode())
 full=json.loads((p/'trace-summary.json').read_text())
 for role,tid in [('process_main',int(d['child']))]+([('java_ui',ui)] if ui else []):
  with gzip.open(e/'threads.trace.gz','rt') as f:filtered=analyze(f,tid,float(d['spawn_uptime_before'].split()[0]))
  assert filtered['intervals']==[tuple(x) for x in full[role]['intervals']]
 (e/'trace-provenance.json').write_text(json.dumps({'full_trace_path':str(src),'full_trace_sha256':sha(src),'full_trace_bytes':src.stat().st_size,'kept_lines':count,'selection':'Exact headers, first/last event, sched_switch prev/next pid and sched_wakeup pid for process-main and Java UI. Full intervals independently compared.'},indent=2))
 for f in p.iterdir():
  if f.is_file() and f.name not in ['sched.trace','sched.trace.gz','launch-inputs.tar','host_spawn','touchfwd','source_app_namespace'] and (f.suffix in ['.json','.jsonl','.txt','.jpeg','.stderr','.log','.sh'] or f.name.startswith('cppcrash')):put(f,e/f.name)
 hits=lambda term:[{'line':i,'text':line} for i,line in enumerate(lines,1) if term in line]
 rows.append({'run':name,'child':d['child'],'java_ui_tid':ui,'stderr_sha256':hashlib.sha256(raw).hexdigest(),'trace':full,'measurement_complete':ui is not None and full['java_ui']['trace_time_range'][1]>=full['java_ui']['window_end'],'fatal':hits('Fatal signal'),'uncaught':hits('[UNCAUGHT] thread='),'ui_failure':hits('[INITCHILD-FAIL]'),'faults':[f.name for f in p.glob('cppcrash*')]})
for f in r.glob('*.json'):put(f,root/'evidence'/f.name)
for f in o.glob('*.json'):put(f,root/'evidence/build'/f.name)
for f in o.glob('*.log'):put(f,root/'evidence/build'/f.name)
for f in (r/'framework').glob('*'):
 if f.suffix in ['.json','.log']:put(f,root/'evidence/framework'/f.name)
for f in (o/'scripts').glob('*.py'):put(f,root/'scripts'/f.name)
put(o/'probe-local/tools/probe_source_app.py',root/'scripts/probe_source_app.py')
(root/'results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
manifest=[{'path':str(f.relative_to(root)),'sha256':sha(f),'bytes':f.stat().st_size} for f in sorted((root/'evidence').rglob('*')) if f.is_file()]
(root/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print('EXPORTED',len(rows),len(manifest))
