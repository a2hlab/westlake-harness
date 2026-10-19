"""Fixed R12 policy. No device access; runtime and tests use these same decisions."""
import hashlib,json,os,re,struct,time
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
HOST_SHA='c6008509f6b4bd8b5766eaad671738364eaa01a039db00e5d94e47204972dbf1'
SERVER_SHA='13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a'
PROBE_SHA='8ab9acaff7c92098f764aa602272e51aeab5b4935af9ef42875c578b874e6c3c'
MARKER=0x1af0
PORT=5039
LIMIT=60
class Refuse(RuntimeError):pass
def need(v,s):
 if not v:raise Refuse(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(p):return Path(os.path.expandvars(os.path.expanduser(p))).resolve()
def stat(s):
 h,t=s.rsplit(') ',1);f=t.split();need(len(f)>=20,'short proc stat')
 return {'pid':int(h.split()[0]),'state':f[0],'ppid':int(f[1]),'birth':int(f[19])}
def sections(s):
 d={};k=None
 for line in s.splitlines():
  if line.startswith('R12_') and ' ' not in line and '\t' not in line:
   k=line[4:];need(k not in d,'duplicate section');d[k]=[]
  else:need(k is not None,'unexpected preamble');d[k].append(line)
 need('RC=0' in d and not d['RC=0'],'remote rc marker');return {k:'\n'.join(v) for k,v in d.items()}
def cmdhex(s):
 t=''.join(s.split());need(re.fullmatch('(?:[0-9a-fA-F]{2})+',t) is not None,'invalid command hex');return bytes.fromhex(t)
def listeners(text):
 out=[]
 for s in text.splitlines():
  f=s.split()
  if not f or f[0]=='sl':continue
  need(len(f)>=10 and ':' in f[1],'bad tcp table')
  if int(f[1].split(':')[-1],16)==PORT and f[3]=='0A':out.append({'address':f[1],'inode':int(f[9])})
 return out
def preflight(a):
 f=a['preflight'];need(sha(path(f['path']))==f['sha256'],'preflight raw SHA');d=sections(path(f['path']).read_text())
 need(d['BOOT']==d['BOOT_END']==a['boot'],'preflight boot');need(d['SELINUX']==a['selinux'],'preflight selinux');need(d['KERNEL']==a['kernel'],'preflight kernel')
 need(not listeners(d['TCP']) and not listeners(d['TCP6']),'port not initially free')
 need(d['ROOT']=='ABSENT','root existed before start')
 before={int(x.rsplit('/',1)[-1]) for x in d['PIDS'].split()};need(a['probe']['pid'] not in before and a['server']['pid'] not in before,'existing process selected')
 return d
def validate(a,now=None,files=True):
 now=time.time() if now is None else now
 need(a['schema']=='r12-admission-v1' and a['execution_enabled'] is True and a['approved_by']=='outer(codex)','explicit admission required')
 need(a['serial']==SERIAL and a['port']==PORT,'board/port scope')
 need(re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',a['boot']) is not None,'boot')
 need(0<=now-a['created_at']<=180 and now<a['expires_at']<=a['created_at']+900,'freshness/window')
 need(a.get('max_seconds',60)==60 and a.get('max_hits',2)==2,'fixed limits')
 root=a['remote_root'];need(re.fullmatch('/data/local/tmp/wl-debug-compat-'+a['boot'][:8]+'-[a-z0-9]{8,32}',root) is not None,'owned fresh root')
 need(a['selinux'] in ('Enforcing','Permissive') and bool(a['kernel']) and '\n' not in a['kernel'],'kernel/selinux')
 need(bool(a['holder']) and '\n' not in a['holder'],'held line')
 for name,pin in [('probe',PROBE_SHA),('server',SERVER_SHA)]:
  r=a[name];need(type(r['pid']) is int and r['pid']>1 and type(r['birth']) is int and r['birth']>0 and type(r['uid']) is int and r['uid']>=0,'process identity '+name)
  need(r['sha256']==pin and r['remote_path']==root+'/'+('probe' if name=='probe' else 'lldb-server'),'exact owned executable')
  need(type(r['device']) is int and r['device']>0 and type(r['inode']) is int and r['inode']>0,'file identity')
 need(a['probe']['pid']!=a['server']['pid'],'distinct PIDs')
 need(a['host']['sha256']==HOST_SHA,'host pin')
 for name in ('host','hdc','lock_script'):
  need(re.fullmatch('[a-f0-9]{64}',a[name]['sha256']) is not None,'tool hash')
  if files:need(sha(path(a[name]['path']))==a[name]['sha256'],'tool bytes '+name)
 if files:
  launch=a['launch_receipt'];need(sha(path(launch['path']))==launch['sha256'],'launch receipt SHA')
  lines=path(launch['path']).read_text().splitlines()
  for value in ['R12_OWNED_ROOT '+root,'R12_BOOT '+a['boot'],'R12_PROBE_PID '+str(a['probe']['pid']),'R12_SERVER_PID '+str(a['server']['pid'])]:need(lines.count(value)==1,'launch receipt binding '+value.split()[0])
  need(sha(path(a['probe']['local_path']))==PROBE_SHA,'local probe bytes');need(marker(path(a['probe']['local_path']))==MARKER,'marker ELF drift');preflight(a)
 return a

def marker(p):
 b=Path(p).read_bytes();need(b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183,'AArch64 ELF')
 shoff=struct.unpack_from('<Q',b,40)[0];sz,n=struct.unpack_from('<HH',b,58);ss=[struct.unpack_from('<IIQQQQIIQQ',b,shoff+i*sz) for i in range(n)];found=set()
 for s in ss:
  if s[1]!=2:continue
  st=ss[s[6]];strings=b[st[4]:st[4]+st[5]]
  for off in range(s[4],s[4]+s[5],s[9]):
   name,info,other,section,value,size=struct.unpack_from('<IBBHQQ',b,off)
   if strings[name:].split(b'\0',1)[0]==b'r12_marker' and info&15==2:found.add(value)
 need(len(found)==1,'marker symbol uniqueness');return found.pop()
def linux_dev(d):return (((d>>8)&0xfff)|((d>>32)&~0xfff),(d&255)|((d>>12)&~255))
def mapped_marker(text,a):
 p=a['probe'];b=path(p['local_path']).read_bytes();po=struct.unpack_from('<Q',b,32)[0];psz,pn=struct.unpack_from('<HH',b,54);loads=[]
 for i in range(pn):
  typ,flags,off,va,_,fs,ms,al=struct.unpack_from('<IIQQQQQQ',b,po+i*psz)
  if typ==1:loads.append((off&~4095,va&~4095,(off+fs+4095)&~4095,flags))
 rows=[]
 for s in text.splitlines():
  f=s.split(maxsplit=5)
  if len(f)!=6 or f[5]!=p['remote_path']:continue
  need((tuple(int(x,16) for x in f[3].split(':')),int(f[4]))==(linux_dev(p['device']),p['inode']),'probe mapped inode')
  lo,hi=[int(x,16) for x in f[0].split('-')];rows.append((lo,hi,int(f[2],16),f[1]))
 candidates=set()
 for lo,hi,off,perms in rows:
  for fo,va,end,flags in loads:
   if fo<=off<end and 'x' in perms and flags&1:
    bias=lo-va-off+fo;addr=bias+MARKER
    if lo<=addr<hi and any(o==0 and l==bias+v for l,h,o,pr in rows for f,v,e,fl in loads if f==0):candidates.add(addr)
 need(len(candidates)==1,'probe marker mapping ambiguous/missing');return candidates.pop()
class Hits:
 def __init__(self):self.rows=[]
 def add(self,tid,pc,x0,stop,expected,resume_stop):
  need(len(self.rows)<2 and tid>0 and pc==expected and stop>resume_stop,'hit identity/stop budget')
  if self.rows:need(stop>self.rows[-1]['stop_id'] and x0>self.rows[-1]['x0'] and tid==self.rows[-1]['tid'],'counter/TID/StopID progression')
  r={'tid':tid,'pc':hex(pc),'x0':x0,'stop_id':stop};self.rows.append(r);return r
