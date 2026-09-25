"""VM: classify saved signals by evidence, leaving unavailable unwind roots unknown."""
from board34 import *
root=pathlib.Path(__file__).resolve().parents[1]
def resolve(addr,text):
 for line in text.splitlines():
  m=re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+\S+\s+([0-9a-f]+)\s+(.*)',line)
  if m and int(m[1],16)<=addr<int(m[2],16):
   rest=m[4];p=rest[rest.find('/'):] if '/' in rest else rest
   return {'mapping':line,'dso':p,'file_offset':hex(addr-int(m[1],16)+int(m[3],16))}
 return None
rows=[]
for d in sorted(R.iterdir()):
 p=d/'child.stderr'
 if not p.is_file():continue
 s=p.read_text(errors='replace');maps=[]
 for q in [*d.glob('maps-*.txt'),*d.glob('cppcrash-*')]:maps.append((q.name,q.read_text(errors='replace')))
 signals=[]
 for m in re.finditer(r'^Fatal signal.*',s,re.M):
  block=s[m.start():m.start()+1700];t=re.search(r'^Thread: (\d+) "([^"]+)"',block,re.M)
  row={'line':s[:m.start()].count('\n')+1,'signal':m[0],'thread':list(t.groups()) if t else None,'original_fault_cause':'unknown: empty native backtrace'}
  for reg,pat in [('pc',r'\bpc:\s*(0x[0-9a-f]+)'),('lr',r'\bx30:\s*(0x[0-9a-f]+)'),('x20',r'\bx20:\s*(0x[0-9a-f]+)'),('x21',r'\bx21:\s*(0x[0-9a-f]+)')]:
   a=re.search(pat,block)
   if not a:continue
   row[reg]=a[1]
   if reg in ('pc','lr'):
    for source,text in maps:
     found=resolve(int(a[1],16),text)
     if found:row[reg+'_mapping']={'source':source,**found};break
  signals.append(row)
 faults=[]
 for q in d.glob('cppcrash-*'):
  text=q.read_text(errors='replace');a=re.search(r'Fault thread info:\s*Tid:(\d+), Name:([^\n]+)\n#00 pc ([0-9a-f]+) ([^\n]+)',text);reason=re.search(r'Reason:([^\n]+)',text)
  faults.append({'file':q.name,'reason':reason[1] if reason else None,'thread_pc_dso':list(a.groups()) if a else None})
 if signals or faults:rows.append({'run':d.name,'signals':signals,'faults':faults})
(root/'crash-classification.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
md=['# Signal inventory','', 'A stderr Fatal signal banner does not prove the app main process died. Classify the emitting thread/process and preserve missing backtraces. All saved #38 runs are listed, including rounds added after the outer review’s original 13.','', '| Run | stderr signal / thread | PC / LR mapping | Separate OH faultlog |','|---|---|---|---|']
for r in rows:
 sig='; '.join(x['signal']+' / '+str(x['thread']) for x in r['signals'])
 mappings=[]
 for x in r['signals']:
  for reg in ('pc','lr'):
   m=x.get(reg+'_mapping');mappings.append(reg+'='+((m['dso']+'+'+m['file_offset']) if m else 'unknown'))
 fs='; '.join(str(x['thread_pc_dso'])+' '+str(x['reason']) for x in r['faults']) or 'not captured'
 md.append('| '+r['run']+' | '+sig+' | '+'; '.join(mappings)+' | '+fs+' |')
md += ['', 'For cold-a4, the faultlog’s mappings resolve the SIGABRT banner’s PC to musl and LR to libnpth.so+0x13854. The preserved disassembly shows the preceding instruction calls syscall(240, getpid(), gettid(), signal, siginfo): this is signal re-delivery by the crash handler, **not proof that libnpth caused the original fault**. Registers x20/x21 both contain the work_thread ID (13890), distinct from the app PID 10823; this is evidence of a separate process context. The main app continues logging afterward. Other runs without same-run mappings are not assigned an invented cause or DSO.','', 'The cold-a4 RenderThread SIGSEGV at NULL in libwebviewchromium.so+0x3e026f0 is an independently captured app-process fault. It must not be merged into the work_thread SIGABRT group. No new ICU cause is asserted from a signal banner alone.']
md += ['', 'Additional startup failures excluded from article timing: warm-b9 has an ART fatal No pending exception expected, with a pending NullPointerException invoking IWebViewUpdateService.waitForAndGetProvider() during CookieManager/WebView provider initialization (child.stderr). warm-b11 exits before the test; its saved tail includes WebView native loading but no captured fault stack, so the exit cause is unknown. These are not assigned to the work_thread SIGABRT or RenderThread groups.']
(root/'CRASHES.md').write_text('\n'.join(md)+'\n')
print('CLASSIFIED',len(rows),'runs',sum(len(r['signals']) for r in rows),'stderr signals')
