from pathlib import Path
import json,re,struct,hashlib,subprocess
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/narrow48';d=r/'narrow-r2'
f=d/'faults/event-1c7c-1d97-1.txt';meta=f.read_text();maps=f.with_suffix('.maps').read_text().splitlines()
binpath=r.parent/'bounded48/confirm-warm-r1/ld-musl-aarch64.so.1';binary=binpath.read_bytes()
phoff=struct.unpack_from('<Q',binary,32)[0];entsz,num=struct.unpack_from('<HH',binary,54);loads=[]
for i in range(num):
 t,flags,off,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',binary,phoff+i*entsz)
 if t==1:loads.append((off,va,filesz))
result={'pid':7292,'tid':7575,'thread':'ChromiumNet0','signal':11,'si_code':1,'fault_address':'0x71f292f33205c4ca','stack_capture':'unavailable: mem_open_errno=0xd (EACCES); registers/maps captured, not full backtrace','musl_sha256':hashlib.sha256(binary).hexdigest(),'addresses':{},'maps_lines':len(maps)}
for k in ['pc','lr']:
 addr=int(re.search(k+r'=0x([0-9a-f]+)',meta)[1],16)
 for line in maps:
  a=line.split();lo,hi=[int(v,16) for v in a[0].split('-')]
  if lo<=addr<hi:
   off=addr-lo+int(a[2],16);va=next(v+off-o for o,v,z in loads if o<=off<o+z);result['addresses'][k]={'absolute':hex(addr),'map':line,'file_offset':hex(off),'elf_vaddr':hex(va)}
refused=['libgodzilla-memsponge','libjato','libmonitorcollector-lib','libsysoptimizer','libnpth_vm_monitor','libnpth_xasan','libnpth_heap_tracker']
result['refused_mapped']=[n for n in refused if any('/'+n+'.so' in l for l in maps)]
result['hotfix_mapped']=any('/libhotfix-opt.so' in l for l in maps)
(d/'crash-analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
objdump=Path.home()/'a2hlab/ws/toolchains/ohos-sdk/native/llvm/bin/llvm-objdump'
for k,v in result['addresses'].items():
 pc=int(v['elf_vaddr'],16)
 p=subprocess.run([str(objdump),'-d','--start-address='+hex(pc-48),'--stop-address='+hex(pc+48),str(binpath)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20)
 (d/('musl-'+k+'-disassembly.txt')).write_text(p.stdout)
 print(p.stdout)
for n,feed,img,desc in [('narrow-r1',True,'during-80.jpeg','Real feed titles and thumbnail at 80s; final frame inducement login; no article input sent.'),('narrow-r2',False,'current.jpeg','Host visible before spontaneous SIG11; no feed or article input.')]:
 (r/n/'visual-review.json').write_text(json.dumps({'body_text_visible':False,'feed_real_titles':feed,'image':img,'notes':desc},indent=2))
