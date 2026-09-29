#!/usr/bin/env python3
"""Offline ELF64/AArch64 inventory for board item 53. Never executes inputs."""
import argparse, collections, difflib, hashlib, json, re, struct, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent
LLVM = Path('/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/native/llvm/bin')
BASE = Path.home() / 'orca/workspaces'
DEPLOY = BASE / 'westlake-harness-bms-deploy/bms/src/.work'
INPUTS = {
 'host': [(BASE/'westlake-bms-suite/var/state/b6-quick/candidates/b5-alias-b6-context/files/appspawn-x','1f6cf53b'),(DEPLOY/'b6-task50/candidate/appspawn-x','02c611c8')],
 'child': [(DEPLOY/'b6-task44/board-consumer-scan/files/system/lib64/appspawn/libwestlake_android_child.z.so','0976dee8'),(DEPLOY/'b6-task50/candidate/libwestlake_android_child.z.so','587e7a85')],
 'runtime-provider': [(DEPLOY/'b6-r155/live/74e6f75976087d7890088b29c08482f17573a588fa5857cb6ca39264838ce16d/libwestlake_android_runtime_provider.so','80c9aee0f39b860b1ce8d72af106e4fde49c0dbf41ef1b426c1e3103086d9b2f'),(DEPLOY/'b6-task50/candidate/libwestlake_android_runtime_provider.so','8d109259')],
}
def sha(b): return hashlib.sha256(b).hexdigest()
def clean(s): return s.replace(str(Path.home()), '~').replace('\x00', r'\0')
def save(path, obj):
 path.parent.mkdir(parents=True, exist_ok=True)
 path.write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def tool(name, args, path):
 return clean(subprocess.run([str(LLVM/name),*args,str(path)],check=True,capture_output=True,text=True).stdout)
def check_hash(data, expected):
 if not sha(data).startswith(expected): raise ValueError('input identity mismatch: '+expected)
def cstr(data, off): return data[off:data.find(b'\0',off)].decode('utf-8','replace')
class ELF:
 def __init__(self,path,expected):
  self.data=path.read_bytes();check_hash(self.data,expected)
  assert self.data[:6]==b'\x7fELF\x02\x01'
  h=struct.unpack_from('<16sHHIQQQIHHHHHH',self.data)
  assert h[2]==183
  self.sections=[]
  for i in range(h[12]):
   s=struct.unpack_from('<IIQQQQIIQQ',self.data,h[6]+i*h[11])
   self.sections.append(dict(zip(('name_offset','type','flags','addr','offset','size','link','info','align','entsize'),s),index=i))
  ns=self.sections[h[13]]; names=self.bytes(ns)
  for s in self.sections:s['name']=cstr(names,s['name_offset'])
  self.byname={s['name']:s for s in self.sections}
  self.segments=[]
  for i in range(h[10]):
   p=struct.unpack_from('<IIQQQQQQ',self.data,h[5]+i*h[9])
   self.segments.append(dict(zip(('type','flags','offset','vaddr','paddr','filesz','memsz','align'),p)))
  self.tables={}
  for s in self.sections:
   if s['type'] not in (2,11):continue
   names=self.bytes(self.sections[s['link']]);table=[]
   for j in range(0,s['size'],s['entsize']):
    n,info,other,ndx,val,size=struct.unpack_from('<IBBHQQ',self.data,s['offset']+j)
    table.append(dict(name=cstr(names,n),type=info&15,bind=info>>4,visibility=other&3,section=ndx,value=val,size=size))
   self.tables[s['index']]=table
  self.symbols=next(t for i,t in self.tables.items() if self.sections[i]['type']==2)
  self.dynsymbols=next(t for i,t in self.tables.items() if self.sections[i]['type']==11)
  self.relocs=[]
  for s in self.sections:
   if s['type']!=4:continue
   for j in range(0,s['size'],s['entsize']):
    off,info,addend=struct.unpack_from('<QQq',self.data,s['offset']+j)
    sym=self.tables[s['link']][info>>32]
    self.relocs.append(dict(section=s['name'],offset=off,type=info&0xffffffff,symbol=sym['name'],addend=addend))
 def bytes(self,s):return b'' if s['type']==8 else self.data[s['offset']:s['offset']+s['size']]
 def locate(self,addr):
  exact=sorted({s['name'] for s in self.symbols if s['value']==addr and s['section'] not in (0,0xfff1) and s['name'] and not s['name'].startswith('$')})
  if exact:return '|'.join(exact)
  for s in self.sections:
   if s['flags']&2 and s['addr']<=addr<s['addr']+s['size']:
    return s['name']+'+'+hex(addr-s['addr'])
  return hex(addr)
 def arrays(self):
  out={};rel={r['offset']:r for r in self.relocs}
  for name in ('.init_array','.fini_array'):
   s=self.byname.get(name);out[name]=[]
   if not s:continue
   for i in range(0,s['size'],8):
    value=struct.unpack_from('<Q',self.bytes(s),i)[0];r=rel.get(s['addr']+i)
    target=r['addend'] if r and r['type']==1027 else value
    out[name].append(dict(slot=i//8,raw=hex(value),target=self.locate(target) if not (r and r['symbol']) else r['symbol'],relocation=r))
  return out

def dynamic(text):
 out=collections.defaultdict(list)
 for line in text.splitlines():
  m=re.match(r'\s*0x[0-9a-f]+ \(([^)]+)\)\s*(.*)',line)
  if m:out[m[1]].append(m[2].strip())
 return dict(out)
def symbol_set(elf, imported):
 return sorted({f"{s['name']} [type={s['type']},bind={s['bind']},visibility={s['visibility']}]" for s in elf.dynsymbols if s['name'] and (s['section']==0)==imported})
def strings(elf):
 out=[]
 for s in elf.sections:
  # All printable runs in non-executable alloc PROGBITS/STRTAB plus symbol/debug string tables.
  if not ((s['flags']&2 and not s['flags']&4 and s['type'] in (1,3)) or s['type']==3 or s['name'] in ('.debug_str','.debug_line_str','.comment')):continue
  for m in re.finditer(rb'[\x20-\x7e]{4,}',elf.bytes(s)):
   out.append(dict(section=s['name'],offset=m.start(),allocated=bool(s['flags']&2),text=clean(m[0].decode())))
 return out

def inventory(kind,version,path,expected):
 e=ELF(path,expected);folder=ROOT/'evidence'/kind/version;folder.mkdir(parents=True,exist_ok=True)
 dumps={'dynamic':['-dW'],'headers':['-hW','-lW','-SW'],'symbols':['-sW'],'relocations':['-rW'],'versions':['-VW'],'notes':['-nW']}
 raw={}
 for label,args in dumps.items():
  raw[label]=tool('llvm-readelf',args,path);(folder/(label+'.txt')).write_text(raw[label])
 (folder/'nm.txt').write_text(tool('llvm-nm',['-a','-S','--format=posix'],path))
 st=strings(e);save(folder/'strings.json',st)
 inv=dict(path=clean(str(path)),sha256=sha(e.data),size=len(e.data),dynamic=dynamic(raw['dynamic']),
  tls=[dict(p,initial_bytes=e.data[p['offset']:p['offset']+p['filesz']].hex()) for p in e.segments if p['type']==7],
  arrays=e.arrays(),relocations=dict(collections.Counter(str(r['type']) for r in e.relocs)),
  relocations_by_section={s:dict(collections.Counter(str(r['type']) for r in e.relocs if r['section']==s)) for s in sorted({r['section'] for r in e.relocs})},
  imports=symbol_set(e,True),exports=symbol_set(e,False),
  sections=[dict(s,sha256=sha(e.bytes(s))) for s in e.sections],
  function_symbols=[s for s in e.symbols if s['type'] in (2,10) and s['section']!=0])
 save(folder/'inventory.json',inv)
 return e,inv,st

def disposition(category,key):
 if category=='strings':
  section,allocated,txt=key
  if not allocated:return 'harmless','Non-allocated string/symbol/debug metadata does not execute; name delta is cross-checked against function inventory.'
  if section=='.dynstr':return 'restore-review','Dynamic link name change; inspect the corresponding import/export/dependency record before restoring.'
  return 'restore-review','Allocated data may affect paths, environment, diagnostics or protocol; no runtime equivalence established. See decision matrix for family-specific disposition.'
 if category=='dynamic':
  if key in ('NEEDED','SONAME','RUNPATH','RPATH','FLAGS','FLAGS_1'):return 'restore','Preserve R155 loader contract; exact behavioral effect remains runtime-unverified.'
  return 'harmless-layout','Address/count bookkeeping follows rebuilt sections; underlying functions/relocations are reviewed separately.'
 return 'restore-review','Potential ABI or lifecycle change; restore parity unless the decision matrix identifies an intentional compatible change.'
def delta(a,b):return dict(removed=sorted(set(a)-set(b)),added=sorted(set(b)-set(a)))
def stage1():
 results={'stage':'v1-metadata','board_item':53,'device_commands':0,'runtime_causality':'unverified','artifacts':{}}
 objects={}
 for kind,entries in INPUTS.items():
  pair=[inventory(kind,v,*p) for v,p in zip(('r155','new'),entries)];objects[kind]=pair
  a,b=[p[1] for p in pair];out={'r155':{k:a[k] for k in ('path','sha256','size')},'new':{k:b[k] for k in ('path','sha256','size')},'dynamic':{},'imports':delta(a['imports'],b['imports']),'exports':delta(a['exports'],b['exports'])}
  for k in sorted(set(a['dynamic'])|set(b['dynamic'])):
   if a['dynamic'].get(k)!=b['dynamic'].get(k):
    d,why=disposition('dynamic',k);out['dynamic'][k]=dict(r155=a['dynamic'].get(k),new=b['dynamic'].get(k),disposition=d,basis=why)
  for k in ('tls','arrays','relocations','relocations_by_section'):
   out[k]=dict(r155=a[k],new=b[k],equal=a[k]==b[k],disposition='restore-review' if a[k]!=b[k] else 'unchanged')
  sa,sb=[{(s['section'],s['allocated'],s['text']) for s in p[2]} for p in pair]
  sd=[]
  for direction,items in [('removed',sa-sb),('added',sb-sa)]:
   for key in sorted(items):
    d,why=disposition('strings',key)
    sd.append(dict(change=direction,section=key[0],allocated=key[1],text=key[2],disposition=d,basis=why))
  save(ROOT/'evidence'/kind/'strings-diff.json',sd)
  out['strings']={'added':sum(s['change']=='added' for s in sd),'removed':sum(s['change']=='removed' for s in sd),'allocated_added':sum(s['change']=='added' and s['allocated'] for s in sd),'allocated_removed':sum(s['change']=='removed' and s['allocated'] for s in sd),'evidence':f'evidence/{kind}/strings-diff.json'}
  save(ROOT/'evidence'/kind/'metadata-diff.json',out);results['artifacts'][kind]=out
 save(ROOT/'results.json',results)
 return results,objects

def normal_line(line, start=0, registers=False):
 """Conservative text pass: direct control targets only; never erase data offsets."""
 line=re.sub(r'\s+',' ',line.strip())
 # LLVM's adrp nearest-function annotation is misleading; strip comment, not immediate.
 if line.startswith('adrp '):line=re.sub(r' <[^>]+>','',line)
 else:line=re.sub(r'0x[0-9a-f]+ <([^>]+)>',r'<\1>',line)
 if registers:line=re.sub(r'\b([xwvsdqhb])\d+\b',r'\1R',line)
 return line

def data_target(e,addr):
 for r in e.relocs:
  if r['offset']==addr:
   return 'reloc:'+str(r['type'])+':'+(r['symbol'] or e.locate(r['addend']))
 exact=[s['name'] for s in e.symbols if s['value']==addr and s['type'] in (1,6) and s['section']!=0 and s['name']]
 if exact:return 'object:'+'|'.join(sorted(exact))
 for sym in e.symbols:
  if sym['type'] in (1,2) and sym['section']!=0 and sym['value']<=addr<sym['value']+sym['size']:
   return ('object:' if sym['type']==1 else 'function:')+sym['name']+'+'+hex(addr-sym['value'])
 for s in e.sections:
  if s['flags']&2 and s['addr']<=addr<s['addr']+s['size']:
   off=addr-s['addr'];b=e.bytes(s)[off:]
   if s['name']=='.rodata' and b:
    m=re.match(rb'[\x09\x0a\x0d\x20-\x7e]*\x00',b)
    if m:return 'string:'+repr(m[0][:-1].decode())
   # Keep unresolved offsets: equality is never inferred by removing these.
   return e.locate(addr)
 return hex(addr)

def instruction_map(e,path,folder):
 raw=tool('llvm-objdump',['-d','--no-show-raw-insn'],path)
 (folder/'disassembly.txt').write_text(raw)
 ins={};labels={};lines={};section=''
 for num,line in enumerate(raw.splitlines(),1):
  m=re.match(r'Disassembly of section (.+):',line)
  if m:section=m[1]
  m=re.match(r'([0-9a-f]+) <(.+)>:',line)
  if m:labels[int(m[1],16)]=m[2]
  m=re.match(r'\s*([0-9a-f]+):\s+(.+)',line)
  if m:ins[int(m[1],16)]=(m[2].strip(),section);lines[int(m[1],16)]=num
 return ins,labels,lines

def function_inventory(e,path,folder):
 ins,labels,lines=instruction_map(e,path,folder)
 syms=[s for s in e.symbols if s['type'] in (2,10) and s['section']!=0]
 syms.sort(key=lambda s:(s['value'],s['name']))
 funcs={};covered=set()
 for sym in syms:
  name=sym['name'];start=sym['value'];end=start+sym['size']
  if not sym['size']:
   sec=e.sections[sym['section']];end=min([s['value'] for s in syms if s['section']==sym['section'] and s['value']>start]+[sec['addr']+sec['size']])
  selected=[a for a in ins if start<=a<end];covered.update(selected)
  # Qualified key only if a compiler produced repeated local symbol names.
  key=name
  if key in funcs:key=name+'#'+str(sum(x['name']==name for x in funcs.values())+1)
  norm=[];raw=[];pages={};resolved=[]
  for addr in selected:
   text=ins[addr][0];raw.append(text);line=normal_line(text)
   m=re.match(r'adrp\s+(x\d+),\s*(0x[0-9a-f]+)',text)
   if m:
    pages[m[1]]=int(m[2],16);line='adrp '+m[1]+', <PAGE>'
   else:
    adr=re.match(r'adr\s+(x\d+),\s*#(-?(?:0x[0-9a-f]+|\d+))',text)
    if adr:
     target=data_target(e,addr+int(adr[2],0));line=f'adr {adr[1]}, <{target}>';resolved.append(target)
    m=re.match(r'(add)\s+(x\d+),\s*(x\d+),\s*#(0x[0-9a-f]+|\d+)',text)
    if m and m[3] in pages:
     target=data_target(e,pages[m[3]]+int(m[4],0));line=f'add {m[2]}, {m[3]}, <{target}>';resolved.append(target)
    m=re.match(r'(ldr\w*|str\w*)\s+([^,]+),\s*\[(x\d+)(?:,\s*#(0x[0-9a-f]+|\d+))?\]',text)
    if m and m[3] in pages:
     target=data_target(e,pages[m[3]]+int(m[4] or '0',0));line=f'{m[1]} {m[2]}, [{m[3]}, <{target}>]';resolved.append(target)
    # Only propagate unmodified adrp values inside straight-line basic blocks.
    op=text.split()[0]
    dest=re.match(r'\S+\s+([xw]\d+)',text)
    if dest and not op.startswith(('str','stp','stur','cmp','tst','cb','tb')):
     pages.pop('x'+dest[1][1:],None)
    if op in ('bl','blr'):
     pages={k:v for k,v in pages.items() if 19<=int(k[1:])<=29}
    elif op in ('b','br','ret') or op.startswith(('b.','cb','tb')):pages.clear()
   norm.append(line)
  loose=[normal_line(x,registers=True) for x in norm]
  funcs[key]=dict(name=name,address=hex(start),size=sym['size'],inferred_zero_size=not sym['size'],instructions=len(selected),line=lines.get(start),norm=norm,register_normalized=loose,raw=raw,resolved_targets=sorted(set(resolved)),bytes_sha256=sha(e.data[e.sections[sym['section']]['offset']+start-e.sections[sym['section']]['addr']:e.sections[sym['section']]['offset']+end-e.sections[sym['section']]['addr']]))
 # PLT and init/fini blocks absent from STT_FUNC are explicit supplemental blocks.
 for start,name in sorted(labels.items()):
  if start in covered:continue
  sec=ins.get(start,('',None))[1]
  if not sec:continue
  end=min([a for a in labels if a>start and ins.get(a,('',None))[1]==sec]+[e.byname[sec]['addr']+e.byname[sec]['size']])
  selected=[a for a in ins if start<=a<end and a not in covered]
  if not selected:continue
  covered.update(selected);norm=[normal_line(ins[a][0]) for a in selected]
  funcs['block:'+name]=dict(name=name,address=hex(start),size=end-start,supplemental=True,instructions=len(selected),line=lines.get(start),norm=norm,register_normalized=[normal_line(x,registers=True) for x in norm],raw=[ins[a][0] for a in selected],resolved_targets=[],bytes_sha256='')
 remaining=[dict(address=hex(a),instruction=ins[a][0],section=ins[a][1]) for a in ins if a not in covered]
 coverage=dict(function_symbols=len(syms),records=len(funcs),decoded_instructions=len(ins),covered_instructions=len(covered),uncovered=remaining)
 save(folder/'function-inventory.json',{k:{kk:vv for kk,vv in v.items() if kk not in ('norm','register_normalized','raw')} for k,v in funcs.items()});save(folder/'coverage.json',coverage)
 return funcs,coverage

def stage2(results,objects):
 for kind,pair in objects.items():
  inventories=[function_inventory(p[0],INPUTS[kind][i][0],ROOT/'evidence'/kind/v) for i,(v,p) in enumerate(zip(('r155','new'),pair))]
  a,b=[p[0] for p in inventories];out=[];folder=ROOT/'evidence'/kind/'functions';folder.mkdir(exist_ok=True)
  for stale in folder.glob('*.diff'):stale.unlink()
  for name in sorted(set(a)|set(b)):
   old=a.get(name);new=b.get(name)
   state='added' if not old else 'removed' if not new else 'normalized_equal' if old['norm']==new['norm'] else 'modified'
   record=dict(name=name,register_state='added' if not old else 'removed' if not new else 'normalized_equal' if old['register_normalized']==new['register_normalized'] else 'modified',state=state,r155={k:v for k,v in (old or {}).items() if k not in ('norm','register_normalized','raw')},new={k:v for k,v in (new or {}).items() if k not in ('norm','register_normalized','raw')},register_normalized_equal=bool(old and new and old['register_normalized']==new['register_normalized']),raw_equal=bool(old and new and old['raw']==new['raw']))
   if state!='normalized_equal':
    fn=sha(name.encode())[:16]+'.diff';diff=''.join(difflib.unified_diff([x+'\n' for x in (old or {}).get('norm',[])],[x+'\n' for x in (new or {}).get('norm',[])],fromfile='R155/'+name,tofile='NEW/'+name,n=4))
    (folder/fn).write_text(diff);record['diff']=f'evidence/{kind}/functions/{fn}';record['disposition']='pending-review'
    regfile=fn.replace('.diff','.register.diff')
    (folder/regfile).write_text(''.join(difflib.unified_diff([x+'\n' for x in (old or {}).get('register_normalized',[])],[x+'\n' for x in (new or {}).get('register_normalized',[])],fromfile='R155/'+name,tofile='NEW/'+name,n=4)))
    record['register_diff']=f'evidence/{kind}/functions/{regfile}'
   out.append(record)
  save(ROOT/'evidence'/kind/'functions.json',out)
  results['artifacts'][kind]['functions']=dict(counts=dict(collections.Counter(f['state'] for f in out)),core_counts=dict(collections.Counter(f['state'] for f in out if not f['name'].startswith('block:'))),register_counts=dict(collections.Counter(f['register_state'] for f in out)),register_normalized_equal=sum(f['register_normalized_equal'] for f in out),coverage={v:p[1] for v,p in zip(('r155','new'),inventories)})
 results['stage']='v2-functions-pending-assessment';save(ROOT/'results.json',results)

def main():
 p=argparse.ArgumentParser();p.add_argument('--functions',action='store_true');args=p.parse_args()
 results,objects=stage1()
 if args.functions:stage2(results,objects)
 print(json.dumps({k:dict(hashes=[a['r155']['sha256'][:8],a['new']['sha256'][:8]],symbols={s:{d:len(a[s][d]) for d in ('added','removed')} for s in ('imports','exports')},strings=a['strings']) for k,a in results['artifacts'].items()},indent=2))
if __name__=='__main__': main()
