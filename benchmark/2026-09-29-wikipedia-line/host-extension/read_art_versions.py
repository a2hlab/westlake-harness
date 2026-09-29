"""Read ELF symbol-backed ART format constants without executing the tool."""
import struct,json,hashlib,sys
from pathlib import Path

def inspect(path):
 p=Path(path);b=p.read_bytes();r={'path':str(p),'sha256':hashlib.sha256(b).hexdigest(),'format_constants':{}}
 if b[:6]!=b'\x7fELF\x02\x01':return r
 shoff=struct.unpack_from('<Q',b,40)[0];ents,num=struct.unpack_from('<HH',b,58)
 sections=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*ents) for i in range(num)]
 for s in sections:
  if s[1] not in (2,11) or not s[9]:continue
  st=sections[s[6]];strings=b[st[4]:st[4]+st[5]]
  for off in range(s[4],s[4]+s[5],s[9]):
   name,info,other,ndx,val,size=struct.unpack_from('<IBBHQQ',b,off)
   name=strings[name:strings.find(b'\0',name)].decode(errors='replace')
   if (name.endswith('kOatVersionE') or name.endswith('kImageVersionE')) and 0<ndx<len(sections):
    d=sections[ndx];pos=d[4]+val-d[3];r['format_constants'][name]=b[pos:pos+min(size,16)].hex()
 return r

if __name__=='__main__':
 paths=json.loads(sys.argv[1]);out=[];seen=set()
 for name in paths:
  p=Path(name);candidates=[p]
  for root in [p.parent,p.parent/'lib64',p.parent.parent/'lib64',p.parent.parent/'lib']:
   candidates.extend(root.glob('libart*.so'))
  for c in candidates:
   if str(c) not in seen and c.is_file():seen.add(str(c));out.append(inspect(c))
 print(json.dumps(out,indent=2))
