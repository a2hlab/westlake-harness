#!/usr/bin/env python3
"""Four fixed T21 slots, 5cd only. Default preview; no ptrace or memory writes."""
import argparse,datetime,hashlib,importlib.util,json,re,shlex,sys,time,uuid
from pathlib import Path
HERE=Path(__file__).resolve().parent
SERIAL='5cd1e3dd00000000000000000923012c'
EXE='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
RT='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d'
MODULES={
 'player':('/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so','0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'),
 'bridge':('/data/local/tmp/asx/liboh_adapter_bridge.so','dca530eb4b1b53e5dd0ecc41c36953f7463609c5b70bbdf67a49dc3cae17f9d9'),
 'shim':('/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so','5cc23582d8cd8f28b24f89dc9bcf439de2177c0be33bb4783dd1baad3ab32eca'),
 'surface':('/system/lib64/chipset-sdk-sp/libsurface.z.so','8f1879f82a307d3a95555067575132918a05244fbdeee1c2f2db37834a58f4a3')}
SLOTS=[('player_lock','player',0x472490,'shim',0x6430),('player_unlock','player',0x472760,'shim',0x6444),('owner_reference','bridge',0x1740a0,'surface',0x66d78),('owner_unreference','bridge',0x173fc8,'surface',0x66ea4)]
def need(v,s):
 if not v:raise ValueError(s)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(name,p):
 spec=importlib.util.spec_from_file_location(name,p);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
def pin_guard(a,ns=None):
 q=shlex.quote;parts=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}']
 for role,uid in [('parent',0),('child',20011300)]:
  pid=getattr(a,role);birth=getattr(a,role+'_birth');ppid=1 if role=='parent' else a.parent
  stat=f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "$1" != Z; test "$1" != X; test "${{20}}" = {birth}; test "$2" = {ppid}'
  parts += [stat,f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}',f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = 0',f'e=$(sha256sum /proc/{pid}/exe); set -- $e; test "$1" = {EXE}',stat]
 parts += [f'pm=$(readlink /proc/{a.parent}/ns/mnt); cm=$(readlink /proc/{a.child}/ns/mnt); im=$(readlink /proc/1/ns/mnt); test "$pm" = "$cm"; test "$pm" != "$im"']
 if ns:parts += [f'test "$pm" = {q(ns[0])}; test "$im" = {q(ns[1])}']
 return '; '.join(parts)
def biases(role,rows,elf,donor):
 path,digest=MODULES[role];name=Path(path).name;selected=sorted([x for x in rows if x['path']==path],key=lambda x:x['lo']);starts=[x['lo'] for x in selected if x['offset']==0]
 need(starts,'no offset-zero mapped segment '+role);donor.PINS={name:(elf,digest)};expected='/data/local/tmp/asx/'+('lib/arm64-v8a/' if role=='player' else '')+name;out=[]
 # Exact four ELFs have their first PT_LOAD at file/virtual zero. Partition only
 # same-path mapping groups; donor then proves each bias using all PT_LOAD rows.
 for i,start in enumerate(starts):
  end=starts[i+1] if i+1<len(starts) else 1<<64
  group=[dict(x,path=expected) for x in selected if start<=x['lo']<end]
  value,_=donor.bias_for(name,group);need(value==start,'first PT_LOAD not zero');out.append(value)
 if role!='surface':need(len(out)==1,'multiple selected '+role+' instances')
 return out
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--repo',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--hdc');ap.add_argument('--boot');ap.add_argument('--holder');ap.add_argument('--offline-maps',type=Path)
 for key in ('parent','parent-birth','child','child-birth'):ap.add_argument('--'+key,type=int)
 for role in MODULES:ap.add_argument('--'+role+'-elf',type=Path)
 a=ap.parse_args()
 if not a.execute and not a.offline_maps:print(json.dumps({'execute':False,'serial':SERIAL,'memory_writes':0,'slots':SLOTS}));return
 need(a.repo,'repo required')
 for rel,h in json.loads((HERE/'slot-source-pins.json').read_text()).items():need(sha(a.repo/rel)==h,'source drift '+rel)
 r=load('t17_slot_reader',a.repo/'benchmark/2026-10-20-t17-network-reuse/read_binding.py');donor=load('r10_bias',a.repo/'benchmark/2026-10-19-toutiao-video-playback/candidate-r10/deployment/read_window_binding.py')
 for role,(_,h) in MODULES.items():need(getattr(a,role+'_elf') and sha(getattr(a,role+'_elf'))==h,'local ELF '+role)
 if a.offline_maps:
  rows=donor.map_rows(a.offline_maps.read_text());print(json.dumps({role:list(map(hex,biases(role,rows,getattr(a,role+'_elf'),donor))) for role in MODULES}));return
 need(re.fullmatch(r'[0-9a-f-]{36}',a.boot or ''),'explicit boot')
 for key in ('parent','parent_birth','child','child_birth'):need(type(getattr(a,key)) is int and getattr(a,key)>1,'explicit PID/birth')
 need(a.parent!=a.child and a.hdc and a.holder and a.out,'explicit distinct identities/transport/output')
 h=a.holder.split();need(len(h)==3 and h[1].isdigit(),'exact holder');start=datetime.datetime.fromisoformat(h[2]).timestamp();age=time.time()-start;need(0<=age<1200,'restore reserve');deadline=time.monotonic()+min(120,1200-age)
 need(a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent output');a.out.mkdir(parents=True,exist_ok=False)
 sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
 class Board(b.Board):
  def command(self,argv,timeout=60):
   left=deadline-time.monotonic();need(left>0,'120-second limit/restore reserve')
   try:return super().command(argv,min(left,timeout,15))
   except b.BatchStop as e:
    if hasattr(e.__cause__,'stdout'):
     stem=self.out/f'command-{self.index:05d}';stem.with_suffix('.stdout.txt').write_bytes(e.__cause__.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(e.__cause__.stderr or b'')
    raise
  def ready(self):
   super().ready();rc,text=self.command(self.lock+['held',SERIAL],10);need(rc==0 and text.strip()==a.holder,'exact holder')
 board=Board(SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),h[0],a.out/'commands');board.boot=a.boot
 ns=None;result={'status':'UNKNOWN','reader_sha256':sha(__file__),'serial':SERIAL,'boot':a.boot,'holder':a.holder,'parent':a.parent,'parent_birth':a.parent_birth,'child':a.child,'child_birth':a.child_birth,'memory_writes':0,'reads':[],'playback':'NOT_ASSESSED'}
 def save():(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
 def read(cmd):
  g=pin_guard(a,ns);return board.shell('( set -eu; '+g+'; '+cmd+'; '+g+' )')[1]
 save()
 try:
  raw=read(f'readlink /proc/{a.parent}/ns/mnt; readlink /proc/1/ns/mnt');need(len(raw.splitlines())==2,'namespace frame');ns=raw.splitlines();need(all(re.fullmatch(r'mnt:\[[0-9]+\]',x) for x in ns) and ns[0]!=ns[1],'private namespace');result['namespace']=ns
  def capture(phase):
   text=read(f'cat /proc/{a.child}/maps');(a.out/f'maps-{phase}.txt').write_text(text);rows=donor.map_rows(text);identities={}
   for role,(path,digest) in MODULES.items():
    physical=RT+path.removeprefix('/data/local/tmp/asx') if path.startswith('/data/local/tmp/asx/') else path
    command='; '.join(f'sha256sum {shlex.quote(p)}; stat -L -c %d:%i {shlex.quote(p)}' for p in [physical,f'/proc/{a.parent}/root{path}',f'/proc/{a.child}/root{path}'])
    text=read(command);(a.out/f'{phase}-{role}.txt').write_text(text);lines=text.splitlines();need(len(lines)==6,'file identity frame')
    records=[r.identity('\n'.join(lines[i:i+2]),path,digest,rows) for i in (0,2,4)];need(records[0]==records[1]==records[2],'physical/private ELF mismatch');identities[role]=records[0]
   return rows,identities
  rows,before=capture('before');bb={role:biases(role,rows,getattr(a,role+'_elf'),donor) for role in MODULES};result.update(files_before=before,biases={k:list(map(hex,v)) for k,v in bb.items()});save()
  for name,owner,offset,target,expected in SLOTS:
   address=bb[owner][0]+offset;need(any(x['path']==MODULES[owner][0] and x['raw'].split()[1].startswith('r') and x['lo']<=address and address+8<=x['hi'] for x in rows),'slot outside readable exact owner')
   token='T21_'+uuid.uuid4().hex.upper();text=read(r.word_command(a.child,address,token));(a.out/f'{name}.txt').write_text(text);value=r.parse_word(text,token)
   matches=[base for base in bb[target] if value==base+expected and any(x['path']==MODULES[target][0] and 'x' in x['raw'].split()[1] and x['lo']<=value<x['hi'] for x in rows)]
   result['reads'].append({'label':name,'address':hex(address),'value':hex(value),'matching_target_bases':list(map(hex,matches)),'match':len(matches)==1});save()
  after,files_after=capture('after');need(before==files_after,'file identity drift')
  for path,_ in MODULES.values():need([x for x in rows if x['path']==path]==[x for x in after if x['path']==path],'module mappings drift')
  result['files_after']=files_after;read('true');need(result['reads'][2]['matching_target_bases']==result['reads'][3]['matching_target_bases'],'owner reference targets cross instances')
  result['status']='FOUR_SLOTS_MATCH' if all(x['match'] for x in result['reads']) else 'FOUR_SLOTS_MISMATCH';save()
 except Exception as e:result['error']=str(e);save();raise
 print(json.dumps({'status':result['status'],'reads':result['reads'],'memory_writes':0}))
if __name__=='__main__':main()
