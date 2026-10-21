#!/usr/bin/env python3
"""Exact G30 ELF increment/constructor/ctype pointer check; no target execution."""
import argparse,hashlib,json,re,struct,subprocess
from pathlib import Path
BASE='d20530661a30b8af7bbfb30a6b7138d0b6a6bb5d82e6cb8d733a41ae23886c65'
CANDIDATE='4296f8052b6ccc130df83366717903695eba38fcde19c462ee64521414696f0b'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
class Elf:
 def __init__(self,p):
  self.b=p.read_bytes();assert self.b[:6]==b'\x7fELF\x02\x01';h=struct.unpack_from('<HHIQQQIHHHHHH',self.b,16);assert h[0]==3 and h[1]==183
  headers=[struct.unpack_from('<IIQQQQIIQQ',self.b,h[5]+i*h[10]) for i in range(h[11])];names=headers[h[12]];st=self.b[names[4]:names[4]+names[5]]
  self.sections={st[s[0]:].split(b'\0',1)[0].decode():s for s in headers};self.headers=headers;self.symbols={};self.addresses={}
  for name in ['.symtab','.dynsym']:
   s=self.sections[name];ss=headers[s[6]];strings=self.b[ss[4]:ss[4]+ss[5]]
   for o in range(s[4],s[4]+s[5],s[9]):
    n,info,other,idx,value,size=struct.unpack_from('<IBBHQQ',self.b,o);n=strings[n:].split(b'\0',1)[0].decode()
    if n and idx:
     self.symbols[n]=(value,size,info&15,idx)
     if info&15==2:self.addresses[value]=n
  self.relative={}
  for s in headers:
   if s[1]==4:
    for o in range(s[4],s[4]+s[5],s[9]):
     loc,info,add=struct.unpack_from('<QQq',self.b,o)
     if info&0xffffffff==1027:self.relative[loc]=add
 def data(self,n):s=self.sections[n];return self.b[s[4]:s[4]+s[5]]
 def va(self,a,n):
  for s in self.sections.values():
   if s[1]!=8 and s[3]<=a and a+n<=s[3]+s[5]:return self.b[s[4]+a-s[3]:s[4]+a-s[3]+n]
  raise AssertionError(('VA_NOT_FILE_BACKED',a,n))
 def arrays(self,n):
  s=self.sections[n];out=[]
  for a in range(s[3],s[3]+s[5],8):
   v=self.relative.get(a,struct.unpack('<Q',self.va(a,8))[0]);assert v in self.addresses,(n,a,v);out.append(self.addresses[v])
  return out
 def ctype(self):
  a,size,typ,_=self.symbols['_ctype_'];assert (size,typ)==(8,1);assert a in self.relative
  t=self.relative[a];assert self.symbols['kBionicCtypeTable'][:2]==(t,257);return self.va(t,257)
def dynsyms(s):
 out={}
 for l in s.splitlines():
  m=re.match(r'\s*\d+:\s+[0-9a-f]+\s+(\d+)\s+(\w+)\s+(\w+)\s+(\w+)\s+(\S+)\s+(\S+)',l)
  if m:
   size,typ,bind,vis,idx,n=m.groups();out[n]=(int(size),typ,bind,vis,idx=='UND')
 return out
def expected(c):
 if c<0 or c>127:return 0
 f=32 if c<32 or c==127 else 0
 if c==32 or 9<=c<=13:f|=8
 if c==32:f|=128
 if 65<=c<=90:f|=1
 if 97<=c<=122:f|=2
 if 48<=c<=57:f|=4
 if 65<=c<=70 or 97<=c<=102:f|=64
 if 33<=c<=126 and not f&7:f|=16
 return f
def validate_abi(bs,cs):
 assert bs and cs
 for n,v in bs.items():assert cs.get(n)==v,('OLD_ABI_DRIFT',n,v,cs.get(n))
 extra=set(cs)-set(bs);assert extra=={'_ctype_@@LIBC','strtoll_l@@LIBC','strtoull_l@@LIBC','strtoll','strtoull'},extra
 assert cs['_ctype_@@LIBC']==(8,'OBJECT','GLOBAL','DEFAULT',False)
 for n in ['strtoll_l@@LIBC','strtoull_l@@LIBC']:assert cs[n]==(4,'FUNC','GLOBAL','DEFAULT',False)
 for n in ['strtoll','strtoull']:assert cs[n][-1]
 return extra
def main():
 a=argparse.ArgumentParser();a.add_argument('--baseline',type=Path,required=True);a.add_argument('--candidate',type=Path,required=True);a.add_argument('--raw',type=Path,required=True);a.add_argument('--out',type=Path,required=True);x=a.parse_args();assert sha(x.baseline)==BASE;assert sha(x.candidate)==CANDIDATE
 b=Elf(x.baseline);c=Elf(x.candidate);read=lambda n:(x.raw/n).read_text();bs=dynsyms(read('baseline-symbols.stdout'));cs=dynsyms(read('candidate-symbols.stdout'));assert bs and cs
 extra=validate_abi(bs,cs)
 bd=read('baseline-dynamic.stdout');cd=read('candidate-dynamic.stdout');needed=lambda s:re.findall(r'\(NEEDED\).*\[(.*?)\]',s)
 assert needed(bd)==needed(cd)==['libc.so'];assert 'TEXTREL' not in bd+cd
 for tag in ['SONAME','FLAGS','FLAGS_1','VERDEFNUM','INIT_ARRAYSZ','FINI_ARRAYSZ']:
  get=lambda s:re.search(r'\('+tag+r'\)\s+(.*)',s).group(1).strip()
  assert get(bd)==get(cd),tag
 arrays={}
 for name in ['.init_array','.fini_array']:assert b.arrays(name)==c.arrays(name);arrays[name]=c.arrays(name)
 for name in ['.init','.fini']:assert b.data(name)==c.data(name),name
 table=c.ctype();assert table==bytes(expected(i) for i in range(-1,256))
 br=json.loads((x.baseline.parent/'receipt.json').read_text());cr=json.loads((x.candidate.parent/'receipt.json').read_text());assert cr['old_objects_byte_identical']
 for name in ['native_abi.o','stdio.o']:assert sha(x.baseline.parent/name)==sha(x.candidate.parent/name)==br['objects'][name]
 r={'status':'ELF_STATIC_INCREMENT_PASS','baseline_sha256':BASE,'candidate_sha256':CANDIDATE,'preserved_dynsym_tuples':len(bs),'added_exports':sorted(extra-{'strtoll','strtoull'}),'added_imports':['strtoll','strtoull'],'needed':needed(cd),'constructors_and_destructors':arrays,'init_fini_bytes_identical':True,'old_objects_byte_identical':True,'ctype_pointer_size':8,'ctype_table_bytes_verified':257,'runtime_namespace_binding':'UNKNOWN','OH_callbacks_execution':'NOT_TESTED','scope':'ELF/static and unchanged original object behavior; no device acceptance'}
 x.out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
if __name__=='__main__':main()
