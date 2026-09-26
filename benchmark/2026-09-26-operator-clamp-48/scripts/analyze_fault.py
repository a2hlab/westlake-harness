from pathlib import Path
import json,re,struct,hashlib,subprocess
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/clamp48'
binpath=r.parent/'bounded48/confirm-warm-r1/ld-musl-aarch64.so.1';binary=binpath.read_bytes();phoff=struct.unpack_from('<Q',binary,32)[0];entsz,num=struct.unpack_from('<HH',binary,54);loads=[]
for i in range(num):
 t,flags,off,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',binary,phoff+i*entsz)
 if t==1:loads.append((off,va,filesz))
for d in sorted(r.glob('*-r*')):
 events=[]
 for f in sorted((d/'faults').glob('*.txt')):
  meta=f.read_text();maps=f.with_suffix('.maps').read_text().splitlines()
  vals=dict(re.findall(r'\[CRASH42\] (\w+)=(0x[0-9a-f]+)',meta));result={k:int(v,16) for k,v in vals.items()};result['thread']=re.search(r'thread=(.*)',meta)[1];result['addresses']={};result['maps_lines']=len(maps);result['stack_capture']='mem_open EACCES, no complete backtrace' if result.get('mem_open_errno')==13 else 'inspect files';result['loaded_monitors']=sorted({l.split('/')[-1] for l in maps if any('/'+n in l for n in ['libnpth','libjato','libsysoptimizer','libgodzilla','libmonitorcollector','libshadowhook','libbytehook'])})
  for k in ['pc','lr']:
   addr=result[k]
   for line in maps:
    a=line.split();lo,hi=[int(v,16) for v in a[0].split('-')]
    if lo<=addr<hi:
     off=addr-lo+int(a[2],16);v={'absolute':hex(addr),'mapping':line,'file_offset':hex(off)}
     if 'ld-musl-aarch64.so.1' in line:
      va=next(v+off-o for o,v,z in loads if o<=off<o+z);v['elf_vaddr']=hex(va);result['musl_sha256']=hashlib.sha256(binary).hexdigest()
      p=subprocess.run([str(Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump'),'-d','--start-address='+hex(va-40),'--stop-address='+hex(va+40),str(binpath)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=10)
      (d/(f.stem+'-musl-'+k+'-disassembly.txt')).write_text(p.stdout)
     result['addresses'][k]=v
  result['event']=f.stem;events.append(result)
 if events:
  events.sort(key=lambda e:e['monotonic_ns'])
  (d/'crash-analysis.json').write_text(json.dumps(events[0],indent=2))
  (d/'crash-events.json').write_text(json.dumps(events,indent=2))
  print(d.name, json.dumps([{'thread':e['thread'],'signal':e['signal'],'addresses':e['addresses'],'event':e['event']} for e in events]))
