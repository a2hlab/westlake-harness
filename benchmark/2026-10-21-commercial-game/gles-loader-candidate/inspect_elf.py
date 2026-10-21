#!/usr/bin/env python3
"""Decode actual ELF policy string_view arrays through RELA, then trace their compiled consumers."""
import argparse, json, re, struct
from pathlib import Path
from prepare_inputs import HERE, sha, save
from build_candidate import run

class Elf:
 def __init__(self,path):
  self.data=Path(path).read_bytes();d=self.data
  assert d[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',d,18)[0]==183
  shoff=struct.unpack_from('<Q',d,40)[0];ents,num,strings=struct.unpack_from('<HHH',d,58)
  self.sections=[struct.unpack_from('<IIQQQQIIQQ',d,shoff+i*ents) for i in range(num)]
  self.symbols={};self.dynamic=[];self.reloc={}
  for sec in self.sections:
   if sec[1] in (2,11):
    table=self.sections[sec[6]];names=d[table[4]:table[4]+table[5]]
    for off in range(sec[4],sec[4]+sec[5],sec[9]):
     no,info,other,ndx,value,size=struct.unpack_from('<IBBHQQ',d,off);name=names[no:].split(b'\0',1)[0].decode()
     row={'name':name,'info':info,'other':other,'ndx':ndx,'address':value,'size':size}
     if sec[1]==2:self.symbols[name]=row
     elif name:self.dynamic.append((name,info,other,ndx!=0))
   elif sec[1]==4:
    for off in range(sec[4],sec[4]+sec[5],sec[9]):
     address,info,value=struct.unpack_from('<QQq',d,off)
     if info&0xffffffff==1027:self.reloc[address]=value
  self.needed=[]
  for sec in self.sections:
   if sec[1]==6:
    strings=self.sections[sec[6]];names=d[strings[4]:strings[4]+strings[5]]
    for off in range(sec[4],sec[4]+sec[5],16):
     tag,value=struct.unpack_from('<qQ',d,off)
     if tag==1:self.needed.append(names[value:].split(b'\0',1)[0].decode())
 def offset(self,address):
  matches=[s[4]+address-s[3] for s in self.sections if s[1]!=8 and s[3] and s[3]<=address<s[3]+s[5]]
  assert len(matches)==1,(address,matches)
  return matches[0]
 def array(self,suffix):
  matches=[v for k,v in self.symbols.items() if k.endswith(suffix+'E')];assert len(matches)==1
  symbol=matches[0];assert symbol['size']%16==0
  values=[];locations=[]
  for i in range(symbol['size']//16):
   address=symbol['address']+i*16;offset=self.offset(address)
   pointer,length=struct.unpack_from('<QQ',self.data,offset);pointer=self.reloc.get(address,pointer)
   assert address in self.reloc and 0<length<512
   off=self.offset(pointer);value=self.data[off:off+length].decode();assert self.data[off+length]==0
   values.append(value);locations.append({'slot':hex(address),'rela_target':hex(pointer),'length':length})
  return {'symbol':symbol,'values':values,'relocations':locations}

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--build',default='build-01');ap.add_argument('--out',default='elf-01');a=ap.parse_args()
 output=HERE/'.private'/a.out;output.mkdir(parents=True,exist_ok=False);result={};disassembly={}
 for variant in ['baseline','candidate']:
  path=HERE/'.private'/a.build/variant/'libnativeloader-candidate.so';elf=Elf(path)
  run(output,variant+'-symbols',['/opt/homebrew/bin/llvm-readelf','-sW',path],output)
  run(output,variant+'-dynamic',['/opt/homebrew/bin/llvm-readelf','-dW',path],output)
  run(output,variant+'-disasm',['/opt/homebrew/bin/llvm-objdump','-d','--no-show-raw-insn',path],output)
  text=(output/'commands'/(variant+'-disasm')/'stdout').read_text();blocks=dict(re.findall(r'^([0-9a-f]+ <[^>]+>):\n(.*?)(?=^[0-9a-f]+ <|\Z)',text,re.M|re.S))
  shared=elf.array('kBridgeSharedSonames');system=elf.array('kSystemLibraries');count=len(shared['values'])
  own=[(k,v) for k,v in blocks.items() if 'OwnPolicyILm'+str(count)+'E' in k];assert len(own)==1
  own_name=own[0][0].split('<',1)[1][:-1]
  assert 'kBridgeSharedSonamesE>' in own[0][1] and '#0x'+format(count*16,'x') in own[0][1]
  consumers={}
  for name in ['CreateClassLoaderNamespace','OpenNativeLibrary']:
   block=[(k,v) for k,v in blocks.items() if k.endswith('<'+name+'>')];assert len(block)==1
   calls=[line.strip() for line in block[0][1].splitlines() if '\tbl\t' in line and '<'+own_name+'>' in line];assert len(calls)==1
   consumers[name]=calls[0]
  disassembly[variant]='\n'.join([own[0][0]+':\n'+own[0][1]]+[name+': '+call for name,call in consumers.items()])
  manifest=json.loads((HERE/'sources'/variant/'policy/native_bridge_policy.v1.json').read_text())
  assert shared['values']==manifest['shared_sonames']
  assert system['values']==[s for item in manifest['system_libraries'] for s in (item['soname'],item['path'])]
  result[variant]={'sha256':sha(path),'shared':shared,'system':system,'dynamic_abi':sorted(elf.dynamic),'needed':elf.needed,'compiled_consumers':consumers}
 assert result['candidate']['shared']['values']==result['baseline']['shared']['values']+['libGLESv2.so']
 assert result['baseline']['system']['values']==result['candidate']['system']['values']
 assert result['baseline']['dynamic_abi']==result['candidate']['dynamic_abi']
 assert result['baseline']['needed']==result['candidate']['needed']
 result['status']='ELF_ARRAYS_AND_TWO_COMPILED_CONSUMERS_VERIFIED'
 save(HERE/'elf-review.json',result)
 (HERE/'elf-consumers.txt').write_text('\n\n'.join(k+'\n'+v for k,v in disassembly.items()))
 print('shared7→8 via ELF RELA/string_view; system7 unchanged; both public config consumers call OwnPolicy; ABI/NEEDED identical')
if __name__=='__main__':main()
