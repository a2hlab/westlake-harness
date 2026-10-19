"""Offline 5cd-only admission and exact ELF/read-range checks."""
import hashlib, json, re, struct
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
BOOT='0525bb05-f714-42ad-90f0-ecdb10356c4f'
UID=20011300
CFG='19d0201b59a6edac821feffa5f51ca8e9a08d6ba87d5bc9fd15b4e4d00775152'
RUN='5a3aef638000e49f2a966b2179d57fe7628c29a4897921209fec539bd5dc1b79'
PLAYER='b427614d57e4a7279f362b3f341de3cdd4b9f9a8859257016bcda24e5f6d3a02'
EXE='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
FUNCTIONS={'ANativeWindow_fromSurface','ANativeWindow_lock','ANativeWindow_unlockAndPost','ANativeWindow_getWidth','ANativeWindow_getHeight','ANativeWindow_getFormat','ANativeWindow_setBuffersGeometry','ANativeWindow_release'}
class Refuse(ValueError):pass
def need(condition,message):
    if not condition:raise Refuse(message)
def digest(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def profile_check(p,serial,boot):
    need(serial==p['serial']==SERIAL,'serial')
    need(boot==p['boot']==BOOT,'boot requires new reviewed profile')
    need(p['uid']==UID,'UID')
    need(p['files'][p['cfg_path']]==CFG and p['files'][p['run_path']]==RUN,'cfg/run')
    return p

def stat(raw,pid):
    head,tail=raw.strip().rsplit(') ',1);f=tail.split()
    need(len(f)>=20 and int(head.split()[0])==pid,'stat PID/length')
    need(f[0] not in ('Z','X'),'dead process')
    return {'pid':pid,'ppid':int(f[1]),'birth':int(f[19]),'state':f[0]}
def same_stat(first,last):
    need(all(first[k]==last[k] for k in ('pid','ppid','birth')),'PID/PPID/birth drift')
def select(ps):
    rows=[r for line in ps.splitlines() if len(r:=line.split())==4 and r[3]=='com.ss.android.article.news']
    need(len(rows)<=1,'ambiguous children')
    if not rows:return None
    r=rows[0];need(int(r[2])==UID,'child UID')
    return {'pid':int(r[0]),'ppid':int(r[1])}
def status(raw,uid=None):
    d={s.split(':',1)[0]:s.split(':',1)[1].strip() for s in raw.splitlines() if ':' in s}
    need(d.get('TracerPid')=='0','traced process')
    ids=[int(x) for x in d['Uid'].split()];need(len(ids)==4 and len(set(ids))==1,'UID set')
    if uid is not None:need(ids==[uid]*4,'UID mismatch')
    return ids[0]
def maps(raw):
    result=[]
    for line in raw.splitlines():
        f=line.split(maxsplit=5);need(len(f)>=5,'maps format')
        lo,hi=(int(v,16) for v in f[0].split('-'))
        result.append({'lo':lo,'hi':hi,'perms':f[1],'offset':int(f[2],16),'dev':f[3],'inode':int(f[4]),'path':f[5] if len(f)==6 else ''})
    return result

def elf_player(path):
    b=Path(path).read_bytes();need(hashlib.sha256(b).hexdigest()==PLAYER,'exact local player SHA')
    need(b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183,'ELF type')
    po,so=struct.unpack_from('<QQ',b,32);pes,pn,ses,sn=struct.unpack_from('<HHHH',b,54)
    loads=[]
    for i in range(pn):
        t,flags,off,va,_,fs,ms,al=struct.unpack_from('<IIQQQQQQ',b,po+i*pes)
        if t==1:loads.append((off&~4095,va&~4095,(off+fs+4095)&~4095,flags))
    sections=[struct.unpack_from('<IIQQQQIIQQ',b,so+i*ses) for i in range(sn)]
    slots={}
    for s in sections:
        if s[1]!=4:continue
        sym=sections[s[6]];strings=sections[sym[6]];text=b[strings[4]:strings[4]+strings[5]]
        for pos in range(s[4],s[4]+s[5],s[9] or 24):
            addr,info,addend=struct.unpack_from('<QQq',b,pos)
            if (info&0xffffffff) not in (1025,1026):continue
            no,flag,other,sec,value,size=struct.unpack_from('<IBBHQQ',b,sym[4]+(info>>32)*(sym[9] or 24))
            end=text.find(b'\0',no);name=text[no:end].decode('ascii')
            if name in FUNCTIONS:
                need(name not in slots,'duplicate import slot');need(sec==0,'not imported symbol');slots[name]=addr
    need(bool(slots),'no admitted imports');return loads,slots

def load_bias(rows,path,loads):
    rr=[r for r in rows if r['path']==path];values=set()
    for r in rr:
        for off,va,end,flags in loads:
            if off<=r['offset']<end:
                bias=r['lo']-va-r['offset']+off
                if any(x['offset']==0 and x['lo']==bias+v for x in rr for o,v,e,f in loads if o==0) and any('x' in x['perms'] and any(o<=x['offset']<e and x['lo']==bias+v+x['offset']-o for o,v,e,f in loads) for x in rr):values.add(bias)
    need(len(values)==1,'player bias ambiguous');return values.pop()
def readable_slot(rows,address):
    need(address%8==0 and len([r for r in rows if r['lo']<=address and address+8<=r['hi'] and 'r' in r['perms']])==1,'GOT range')
def receipt_check(r):
    need(r['serial']==SERIAL and r['boot']==BOOT and r['uid']==UID,'receipt identity')
    need(r['playback']=='unknown' and r['audio']=='unknown' and r['visual_verdict']=='pending_review','no inferred UI/playback')
    need(r['device_mutations']==0 and r['app_starts']==0 and r['attach']==0,'collector scope')
