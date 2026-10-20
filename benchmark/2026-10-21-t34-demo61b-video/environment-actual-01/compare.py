from pathlib import Path
import re,json,argparse
root=Path.home()/'.local/share/westlake/t34-environment-read-20261021'
def parse(role):
 s=(root/f'receipts/{role}.stdout').read_text();ls=s.splitlines();begin=ls.index('MAPS_BEFORE_BEGIN');end=ls.index('MAPS_AFTER_BEGIN');maps=[{},{}]
 for phase,seq in enumerate([ls[begin+1:end],ls[end+1:]]):
  for i,l in enumerate(seq):
   m=re.match(r'^([0-9a-f]+)-([0-9a-f]+)\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+):([0-9a-f]+)\s+(\d+)\s+(/.*)$',l)
   if m:maps[phase].setdefault(m[8],set()).add((int(m[5],16),int(m[6],16),int(m[7])))
 files={}
 for i,l in enumerate(ls):
  if l.startswith('FILE_BEGIN '):
   _,kind,p=l.split(' ',2);path=re.sub(r'^/proc/\d+/root','',p)
   if not ls[i+1].startswith('IDENTITY_SIZE '):files[path]={'kind':kind,'error':ls[i+1]};continue
   dev,ino,size=map(int,ls[i+1].split()[1].split(':'));digest=ls[i+2].split()[1];ident=(((dev>>8)&0xfff)|((dev>>32)&0xfffff000),(dev&255)|((dev>>12)&0xffffff00),ino)
   match=[ident in x.get(path,set()) for x in maps]
   files[path]={'kind':kind,'sha256':digest,'bytes':size,'identity':[dev,ino],'maps_before_after_match':match,'maps_before':[list(t) for t in maps[0].get(path,set())],'maps_after':[list(t) for t in maps[1].get(path,set())],'stdout_line':i+1}
 return files,maps,ls
if __name__=='__main__':
 parser=argparse.ArgumentParser(description='Offline two-board parent receipt comparison; no transport')
 parser.add_argument('--root',type=Path,default=root)
 root=parser.parse_args().root
 a,am,al=parse('5cd');b,bm,bl=parse('61b')
 for cat in ['BCP','BOOT_IMAGE','MAPPED_SHARED']:
  keys=set(k for k,v in a.items() if v['kind']==cat)|set(k for k,v in b.items() if v['kind']==cat)
  print(cat,'union',len(keys),'equal',sum(k in a and k in b and a[k].get('sha256')==b[k].get('sha256') for k in keys))
  for k in sorted(keys):
   if k not in a or k not in b or a[k].get('sha256')!=b[k].get('sha256'):print(k,a.get(k),b.get(k))
 for role,f in [('5cd',a),('61b',b)]:
  bad={k:v for k,v in f.items() if v['kind']=='MAPPED_SHARED' and v.get('maps_before_after_match')!=[True,True]};print('BIND_BAD',role,bad)
 print('ENV_DIFF')
 print(set(l for l in al[:al.index('FILE_BEGIN BCP /proc/5866/root/data/local/tmp/asx/fw/core-oj.jar')] if '=' in l)-set(l for l in bl[:bl.index('FILE_BEGIN BCP /proc/4992/root/data/local/tmp/asx/fw/core-oj.jar')] if '=' in l))
