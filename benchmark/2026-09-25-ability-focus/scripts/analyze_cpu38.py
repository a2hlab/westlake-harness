"""Self CPU period accounting; never treat CPU proportions as wall-delay causality."""
import pathlib,re,json,gzip,collections
root=pathlib.Path(__file__).resolve().parents[1]
def read(rel):
 p=root/'evidence'/rel
 if p.exists():return p.read_text(errors='replace')
 return gzip.decompress(pathlib.Path(str(p)+'.gz').read_bytes()).decode(errors='replace')
def parse(rel,android=False):
 out=[]
 for line in read(rel).splitlines():
  pat=r'^\s*([\d.]+)%\s+(\d+)\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(.+)$' if android else r'^\s*([\d.]+)%\s+(\d+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(.+)$'
  m=re.match(pat,line)
  if not m:continue
  if android:pct,samples,ns,tid,comm,dso,sym=m.groups()
  else:pct,ns,tid,comm,dso,sym=m.groups();samples=None
  out.append(dict(percent=float(pct),ns=int(ns),tid=int(tid),comm=comm,dso=dso,symbol=sym.strip(),samples=int(samples) if samples else None))
 return out
def category(r):
 s=r['symbol'].lower();d=r['dso'].lower()
 if 'nterp' in s:return 'nterp'
 if 'executeswitch' in s or 'interpreter::' in s:return 'switch/other interpreter'
 if any(x in s for x in ['monitorenter','monitorexit','lock_object','mutex','futex','lockword','spin_lock','spin_unlock','rwsem']):return 'locks/synchronization'
 if any(x in s for x in ['verifier','classlinker','dexfile','findclassmethod','classloader','resolvetype','resolvedtype','internstrong','typelookup']):return 'class loading/verification/resolution'
 if any(x in s for x in ['art::gc::','garbage','waitforgctocomplete']):return 'GC'
 if any(x in s for x in ['art::jit::','jitcompile','compiler::']):return 'JIT compiler/cache'
 if r['dso']=='id.article.news':
  m=re.search(r'@0x([0-9a-f]+)',s)
  if m and 0x36000000<=int(m[1],16)<0x38000000:return 'JIT zygote executable mapping (unsymbolized)'
  if m and 0x3a000000<=int(m[1],16)<0x3c000000:return 'anonymous executable mapping (unsymbolized)'
  return 'unresolved app mapping'
 if 'liboh_' in d or 'adapter' in d or 'appspawn' in d:return 'westlake bridge/runtime'
 if 'libwebview' in d or 'libmonochrome' in d:return 'WebView native'
 if any(x in d for x in ['libhwui','libskia','libgles','libegl']):return 'graphics'
 if 'kernel.kallsyms' in d:return 'kernel other'
 if 'libart' in d:return 'ART other'
 if any(x in d for x in ['platformsdk','chipset','/system/lib64/libhilog','libace','librender_service']):return 'OH libraries'
 if 'libc.so' in d or 'ld-musl' in d:return 'libc'
 if any(x in d for x in ['.oat','.odex','jit-cache','dalvik-jit']):return 'compiled managed code'
 return 'other / unresolved'
profiles={}
for label,rel,android in [('OH consent','cpu-consent-2/report-main.txt',False),('Android consent','android-reference/cpu-1/report-main.txt',True)]:
 rows=parse(rel,android);tot=sum(x['ns'] for x in rows);cat=collections.Counter()
 for r in rows:r['category']=category(r);cat[r['category']]+=r['ns']
 profiles[label]={'source':rel,'cpu_ms':tot/1e6,'rows':rows,'categories_ms':{k:v/1e6 for k,v in cat.items()}}
for label,rel in [('OH detail main','cpu-detail-1/report-main.txt'),('OH detail RenderThread','cpu-detail-1/report-render.txt')]:
 try:rows=parse(rel)
 except FileNotFoundError:continue
 cat=collections.Counter()
 for r in rows:r['category']=category(r);cat[r['category']]+=r['ns']
 profiles[label]={'source':rel,'cpu_ms':sum(r['ns'] for r in rows)/1e6,'rows':rows,'categories_ms':{k:v/1e6 for k,v in cat.items()}}
(root/'cpu-summary.json').write_text(json.dumps(profiles,ensure_ascii=False,indent=2)+'\n')
md=['# CPU self-time profiles','', 'On-CPU task-clock periods only. Kernel time is included. These separate runs are excluded from queueMs cohorts. Consent profiles cover ~10 seconds starting immediately after the consent command; they are equal observation windows, not equal completed work. Unresolved executable samples remain explicit.','']
for label,p in profiles.items():
 md += ['## '+label,'',f"Sampled CPU: **{p['cpu_ms']:.1f} ms**. Raw report: `{p['source']}`.",'','| Self % | CPU ms | DSO | Symbol |','|---:|---:|---|---|']
 for r in p['rows'][:20]:md.append(f"| {r['percent']:.2f} | {r['ns']/1e6:.1f} | {pathlib.Path(r['dso']).name} | {r['symbol'].replace('|','/')} |")
 md+=['']
a=profiles['Android consent']['cpu_ms'];oh=profiles['OH consent']['cpu_ms']
md+=['## Consent-window decomposition','',f'OH/Android sampled main-thread CPU = {oh:.1f}/{a:.1f} = **{oh/a:.3f}×**. This is not the 665ms DOWN dispatch ratio and cannot be used to explain it causally: the window includes different executed work, waiting and runtime states. Off-CPU waiting is absent from a self CPU report.','', '| Category | OH CPU ms | Android CPU ms | OH contribution / Android total |','|---|---:|---:|---:|']
for k in sorted(set(profiles['OH consent']['categories_ms'])|set(profiles['Android consent']['categories_ms'])):
 x=profiles['OH consent']['categories_ms'].get(k,0);y=profiles['Android consent']['categories_ms'].get(k,0);md.append(f'| {k} | {x:.1f} | {y:.1f} | {x/a:.3f}× |')
md += ['', '## Observed DOWN dispatch factor (not a causal attribution)', '', 'Android reference DOWN mean = (3.710+5.273+5.240)/3 = 4.741ms. Idle OH article-target cold a4/a5/a7 DOWN mean = (124+111+207)/3 = 147.333ms. The old busy trace-2 value 665ms is 140.3× the Android mean; arithmetically this is 4.51× (busy/idle OH) times 31.08× (idle OH/Android). These are different trials and states, with diagnostic overhead and different hardware; they do not identify which subsystem caused either factor. CPU-category contributions above describe a separate consent window, not the DOWN event.']
md+=['','Both runs contain direct nterp leaf samples. No ExecuteSwitchImplCpp leaf sample in a limited profile does not prove it never executes. OH zygote-JIT and anonymous executable ranges are classified from that run’s maps; anonymous code is not given invented Java method names.']
md += ['', 'Endpoint /proc main-thread stat field39: OH CPU2 before / CPU7 after; Android CPU5 before / CPU4 after. These are last-executed CPU IDs, not continuous residency. Matching clock-frequency samples were not captured, so no frequency-normalized factor is claimed.']
(root/'CPU_PROFILE.md').write_text('\n'.join(md)+'\n')
print({k:v['cpu_ms'] for k,v in profiles.items()})
