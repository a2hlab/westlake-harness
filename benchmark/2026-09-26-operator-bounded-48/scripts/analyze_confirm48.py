from pathlib import Path
import json,re,struct,hashlib,subprocess
r=Path.home()/'a2hlab/board/61b0657200000000000000000324012c/bounded48';d=r/'confirm-warm-r1';f=d/'faults/event-396b-3aa8-1.txt';meta=f.read_text();maps=f.with_suffix('.maps').read_text().splitlines();binary=(d/'ld-musl-aarch64.so.1').read_bytes();phoff=struct.unpack_from('<Q',binary,32)[0];entsz,num=struct.unpack_from('<HH',binary,54);loads=[]
for i in range(num):
 t,flags,off,va,pa,filesz,memsz,align=struct.unpack_from('<IIQQQQQQ',binary,phoff+i*entsz)
 if t==1:loads.append((off,va,filesz))
result={'pid':14699,'tid':15016,'thread':'npth-worker','signal':11,'si_code':1,'fault_address':0,'stack_capture':'unavailable: mem_open_errno=0xd (EACCES); registers/maps captured, not a full backtrace','musl_sha256':hashlib.sha256(binary).hexdigest(),'addresses':{}}
for k in ['pc','lr']:
 addr=int(re.search(k+r'=0x([0-9a-f]+)',meta)[1],16)
 for line in maps:
  a=line.split();lo,hi=[int(v,16) for v in a[0].split('-')]
  if lo<=addr<hi:
   off=addr-lo+int(a[2],16);va=next(v+off-o for o,v,z in loads if o<=off<o+z);result['addresses'][k]={'absolute':hex(addr),'map':line,'file_offset':hex(off),'elf_vaddr':hex(va)}
result['instruction']='ELF vaddr 0xd6e20: strb wzr,[x14]; previous mov x14,xzr, preceded by cbz w14 check. Deliberate null write; exact private symbol/caller unresolved.'
(d/'crash-analysis.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
for n,screen,img in [('confirm-r1','feed/video cards after consent; no article input','during-150.jpeg'),('confirm-warm-r1','host after spontaneous SIG11 before article input','current.jpeg')]:
 (r/n/'visual-review.json').write_text(json.dumps({'body_text_visible':False,'final_screen':screen,'image':img},indent=2))
