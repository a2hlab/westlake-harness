#!/usr/bin/env python3
"""Offline ELF/read-receipt inspection. No target execution or device commands."""
import argparse, hashlib, json, re, struct, subprocess
from pathlib import Path
D=Path(__file__).resolve().parent
PIN={'appspawn-x':'2a87118e7e8e62fb73ef71a436517cda406c308668753a478cf52331e996072e','libapp_native_loader.so':'eebd62f2e9107e7915745280d4de85d44e4106a589508d25fa5f867007b2473c','libnativeloader.so':'b8be63d2f617ba202373e4a60b34cc4eadba84bcfe31e42b64cfe4f01bfa62f7','libbionic_compat.so':'b8a87f6fe2902b1d1c9e8440714d32dbdfd05d75dc1a2993fd2624af91d15abc','libGLESv2.so':'befb6ec78f52f3f54b955e268fa04faa6192d78c61cc08aac9a2e6828f1aee9f'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,x):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--input',type=Path,required=True);ap.add_argument('--llvm',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args(); raw=a.out/'raw';raw.mkdir(parents=True,exist_ok=True)
 def run(tag,args):
  p=raw/tag;put(p.with_suffix('.argv.json'),args)
  with p.with_suffix('.stdout').open('wb') as o,p.with_suffix('.stderr').open('wb') as e:r=subprocess.run(args,stdout=o,stderr=e)
  p.with_suffix('.rc').write_text(str(r.returncode)+'\n');assert r.returncode==0,tag
  return p.with_suffix('.stdout').read_text()
 rows=[]
 for i,(name,pin) in enumerate(PIN.items()):
  f=a.input/name;assert sha(f)==pin
  receipts={}
  for phase in ['before','recv','after']:
   j=a.input/f'obj{i}-{phase}.json';s=a.input/f'obj{i}-{phase}.stdout';assert json.loads(j.read_text())['rc']==0
   if phase!='recv':assert s.read_text().split()[0]==pin
   receipts[phase]={'receipt_sha256':sha(j),'stdout_sha256':sha(s)}
  dyn=run(f'elf-{i}-dynamic',[str(a.llvm/'llvm-readelf'),'-d',str(f)])
  sym=run(f'elf-{i}-symbols',[str(a.llvm/'llvm-readelf'),'--dyn-syms','--wide',str(f)])
  defined=[];undefined=[]
  for line in sym.splitlines():
   t=line.split()
   if len(t)>=8 and t[0].rstrip(':').isdigit():(undefined if t[6]=='UND' else defined).append(t[7])
  rows.append({'name':name,'sha256':pin,'bytes':f.stat().st_size,'before_recv_after':receipts,'defined':defined,'undefined':undefined,'needed':re.findall(r'\(NEEDED\).*?\[(.*?)\]',dyn)})
 # Exact std::string_view array: use symbol size, RELATIVE relocations, PT_LOAD file mapping.
 f=a.input/'libnativeloader.so';b=f.read_bytes();assert b[:6]==b'\x7fELF\x02\x01'
 nm=run('policy-symbols',[str(a.llvm/'llvm-nm'),'-SC',str(f)])
 rel=run('policy-relocations',[str(a.llvm/'llvm-readelf'),'-r',str(f)])
 phoff=struct.unpack_from('<Q',b,32)[0];phsize,phnum=struct.unpack_from('<HH',b,54)
 seg=[struct.unpack_from('<IIQQQQQQ',b,phoff+i*phsize) for i in range(phnum)]
 def offset(va,size=1):
  hits=[o+va-v for t,fl,o,v,p,fs,ms,al in seg if t==1 and v<=va and va+size<=v+fs];assert len(hits)==1;return hits[0]
 reloc={int(m[0],16):int(m[1],16) for m in re.findall(r'^([0-9a-f]+)\s+\S+\s+R_AARCH64_RELATIVE\s+([0-9a-f]+)',rel,re.M)}
 policy={}
 for key in ['kBridgeSearchPaths','kBridgePermittedPaths','kBridgeSharedSonames']:
  m=re.search(r'^([0-9a-f]+) ([0-9a-f]+) \w .*::'+key+'$',nm,re.M);assert m,key
  addr,size=map(lambda x:int(x,16),m.groups());assert size%16==0
  entries=[]
  for va in range(addr,addr+size,16):
   ptr=reloc[va];length=struct.unpack_from('<Q',b,offset(va+8,8))[0];assert length<1024
   entries.append({'slot':hex(va),'string_va':hex(ptr),'length':length,'text':b[offset(ptr,length):offset(ptr,length)+length].decode()})
  policy[key]={'symbol_va':hex(addr),'size':size,'entries':entries}
 run('host-namespace',[str(a.llvm/'llvm-objdump'),'-d','--no-show-raw-insn','--start-address=0xcc68','--stop-address=0xd4ec',str(a.input/'appspawn-x')])
 routes=[]
 for r in json.loads((a.input/'route-receipts.json').read_text()):
  pin=sha(a.input/r['local_name']);assert pin==r['local_sha']==r['historical_sha']
  for c in r['commands']:
   assert c['rc']==0
   if c['phase'] in ['before','after']:assert c['stdout'].split()[0]==pin
  routes.append({'path':r['path'],'sha256':pin,'before_after_verified':True,'same_as_system':pin==PIN[Path(r['path']).name]})
 assert (a.input/'boot-before.stdout').read_bytes()==(a.input/'boot-after.stdout').read_bytes()
 def stat(p):
  t=p.read_text();tail=t[t.rfind(')')+2:].split();return {'pid':int(t.split()[0]),'ppid':int(tail[1]),'birth':int(tail[19])}
 before=stat(a.input/'parent-stat-before.stdout');after=stat(a.input/'parent-stat-after.stdout');assert before==after
 put(a.out/'analysis.json',{'system':rows,'policy':policy,'routes':routes,'parent':before,'boot':(a.input/'boot-before.stdout').read_text().strip(),'libEGL_android_path':'ABSENT: sha/recv stdout fail despite transport rc0','child_maps':'NOT_CAPTURED','child_environ':'NOT_CAPTURED','parent_environ':'NOT_COLLECTED','tool_sha256':{n:sha(a.llvm/n) for n in ['llvm-readelf','llvm-nm','llvm-objdump']}})
 print(json.dumps({'status':'PASS','system_elfs':len(rows),'route_elfs':len(routes),'shared_sonames':[x['text'] for x in policy['kBridgeSharedSonames']['entries']]}))
if __name__=='__main__':main()
