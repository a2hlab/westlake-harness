"""Extract trace pairs and ActivityThread.main stacks, retaining source line numbers."""
import pathlib,re,json,sys,gzip
root=pathlib.Path(sys.argv[1]);results=[]
for r in sorted(root.iterdir()):
 if not r.is_dir():continue
 p=r/'child.stderr'
 if not p.exists():p=r/'child.stderr.gz'
 if not p.exists():continue
 text=gzip.open(p,'rt',errors='replace').read() if p.suffix=='.gz' else p.read_text(errors='replace')
 lines=text.splitlines();posts={};touches=[];stacks=[]
 wall=None;block=[];begin=None
 def finish():
  if block and any('at android.app.ActivityThread.main(' in l for l in block):
   text='\n'.join(block);tid=re.search(r'sysTid=(\d+)',text)
   if tid:stacks.append({'line':begin,'wall_time':wall,'tid':int(tid[1]),'stack':block})
 for n,line in enumerate(lines,1):
  m=re.search(r'\[TOUCH21\] (post|run|return) action=(\d+) now=(\d+) event=(\d+)',line)
  if m:
   phase,action,now,event=m.groups();key=(action,event)
   if phase=='post':posts[key]=(int(now),n)
   elif phase=='run' and key in posts:
    t,ln=posts.pop(key);touches.append({'action':int(action),'event':int(event),'post_ms':t,'run_ms':int(now),'latency_ms':int(now)-t,'post_line':ln,'run_line':n})
  if line.startswith('----- pid ') and ' at ' in line:wall=line
  if re.match(r'^".*" (?:daemon )?prio=',line):
   finish();block=[line];begin=n
  elif block:
   if not line.strip():finish();block=[];begin=None
   else:block.append(line)
 finish()
 result={'run':r.name,'touches':touches,'unconsumed_posts':[{'action':k[0],'event':k[1],'post_ms':v[0],'line':v[1]} for k,v in posts.items()],'ui_stacks':stacks,'fatal_signals':[{'line':i,'text':s} for i,s in enumerate(lines,1) if 'Fatal signal' in s],'ui_exit_lines':[i for i,s in enumerate(lines,1) if '[INITCHILD-FAIL]' in s]}
 results.append(result)
 print(r.name,'touches',[(t['action'],t['latency_ms']) for t in touches], 'stacks',len(stacks),'fatal',len(result['fatal_signals']))
(root/'summary.json').write_text(json.dumps(results,indent=2,ensure_ascii=False)+'\n')
