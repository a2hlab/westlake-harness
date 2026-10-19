"""R11 fixed admission and observation decisions; shared by runtime and offline tests."""
import hashlib, json, os, re, struct, time
from pathlib import Path
SERIAL='61b0657200000000000000000324012c'
HOST_SHA='c6008509f6b4bd8b5766eaad671738364eaa01a039db00e5d94e47204972dbf1'
SERVER_SHA='d6d9a233fd3b9bd2ff60a69eec78aa2e70eaf4d94b98e0cbb55fae90706fb229'
PINS={'player':'0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471','android':'76512d97758c308acf7baff4647f07db792c02b8fae2eda93399bd18eda03727','shim':'85c789f48b2bc0c31658c9dc591cd27784cc0ddfe559005e8d36d1d7d220476a','bridge':'d4fae8e5802f3153a85175243edf665714900381d463ffc5ca1e64d0b308775b','hwui':'a11c9154ca16dd7acf5e3ea99727ae37c25b1b4494a9133816bc58c553c128e2'}
EXE_SHA='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
MAX_SECONDS=120; MAX_FROM=4; MAX_LOCK=4
class Refuse(RuntimeError): pass
def need(ok,msg):
    if not ok: raise Refuse(msg)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def path(s): return Path(os.path.expandvars(os.path.expanduser(s))).resolve()
def positive(v): return type(v) is int and v>0
def validate(a,now=None,files=True):
    now=time.time() if now is None else now
    need(a['schema']=='r11-admission-v1' and a['execution_enabled'] is True and a['approved_by']=='outer(codex)','authorization')
    need(a['serial']==SERIAL,'serial')
    need(type(a['created_at']) in (float,int) and 0<=now-a['created_at']<=300,'stale admission')
    need(now<a['expires_at']<=a['created_at']+1800,'expiry')
    need(a.get('max_seconds',120)==120 and a.get('max_fromSurface',4)==4 and a.get('max_lock',4)==4,'budget override')
    e=a['identity'];need(re.fullmatch('[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}',e['boot']) is not None,'boot')
    for key in ['parent','parent_birth','child','child_birth','uid']:need(positive(e[key]),key)
    need(e['child']!=e['parent'] and e['uid']==20011206 and type(e['parent_uid']) is int and e['parent_uid']==0,'dedicated host UID')
    for key in ['child_exe_sha256','parent_exe_sha256']:need(e[key]==EXE_SHA,key)
    s=a['server'];need(positive(s['pid']) and positive(s['birth']) and s['pid'] not in (e['child'],e['parent']) and type(s['uid']) is int and s['uid']>=0,'server identity')
    need(s['sha256']==SERVER_SHA and a['host']['sha256']==HOST_SHA,'tool pin')
    need(type(a['holder']) is str and bool(a['holder']) and '\n' not in a['holder'],'holder')
    for tool in ['hdc','lock_script']:
        need(re.fullmatch('[0-9a-f]{64}',a[tool]['sha256']) is not None,'tool SHA')
    need(set(a['modules'])==set(PINS),'exact module roles')
    for k,m in a['modules'].items():
        need(m['sha256']==PINS[k] and positive(m['device']) and positive(m['inode']),'module pin '+k)
        need(m['remote_path'].startswith('/data/') and not any(c in m['remote_path'] for c in ['\n','\r','\x00']),'module path')
        if files:need(sha(path(m['local_path']))==PINS[k],'local module '+k)
    if files:
        for k in ['host','hdc','lock_script']:need(sha(path(a[k]['path']))==a[k]['sha256'],'local tool '+k)
    return a

def stat_fields(s):
    head,tail=s.rsplit(') ',1);f=tail.split();need(len(f)>=20,'short stat')
    return {'pid':int(head.split(' ',1)[0]),'state':f[0],'ppid':int(f[1]),'birth':int(f[19])}
def parse_maps(s):
    rows=[]
    for line in s.splitlines():
        f=line.split(maxsplit=5);need(len(f)>=5,'bad maps')
        lo,hi=(int(x,16) for x in f[0].split('-'));need(lo<hi,'bad map range')
        rows.append({'lo':lo,'hi':hi,'perms':f[1],'off':int(f[2],16),'dev':tuple(int(x,16) for x in f[3].split(':')),'ino':int(f[4]),'path':f[5] if len(f)==6 else '', 'raw':line})
    need(bool(rows),'empty maps');return rows
def linux_dev(d):return (((d>>8)&0xfff)|((d>>32)&~0xfff),(d&255)|((d>>12)&~255))
def segments(p):
    b=path(p).read_bytes();need(b[:6]==b'\x7fELF\x02\x01' and struct.unpack_from('<H',b,18)[0]==183,'ELF aarch64')
    off=struct.unpack_from('<Q',b,32)[0];sz,n=struct.unpack_from('<HH',b,54);out=[]
    for i in range(n):
        t,flags,fo,va,_,fs,ms,al=struct.unpack_from('<IIQQQQQQ',b,off+i*sz)
        if t==1 and fs:out.append((fo&~4095,va&~4095,(fo+fs+4095)&~4095,flags))
    need(bool(out),'no loads');return out

def mapped_module(rows,m):
    rr=[r for r in rows if r['path']==m['remote_path']];need(bool(rr),'missing map '+m['remote_path'])
    need(all((r['dev'],r['ino'])==(linux_dev(m['device']),m['inode']) for r in rr),'mapped inode')
    return rr

def biases(rows,m):
    rr=mapped_module(rows,m);loads=segments(m['local_path']);cand={}
    for r in rr:
        for off,va,end,flags in loads:
            if off<=r['off']<end:
                b=r['lo']-va-r['off']+off
                cand.setdefault(b,set()).add(r['lo'])
    # Multiple genuine instances are allowed; each needs header+executable segment evidence.
    out=[]
    for b,rs in cand.items():
        header=any(r['off']==0 and r['lo']==b+va for r in rr for off,va,end,flags in loads if off==0)
        executable=any('x' in r['perms'] and r['lo'] in rs for r in rr)
        if header and executable and len(rs)>=2:out.append(b)
    need(bool(out),'no unambiguous PT_LOAD instance');return sorted(out)

def containing(rows,addr,size=1,perm='r'):
    return [r for r in rows if r['lo']<=addr and addr+size<=r['hi'] and perm in r['perms']]

def wrapper(read,address):
    result={'pointer':hex(address),'class':'unknown','same_object_generation':'unknown'}
    if not address: result['reason']='null';return result
    try:
        magic=read(address,4);result['magic_at_0']=hex(int.from_bytes(magic,'little'))
        if int.from_bytes(magic,'little')!=0x5f776e64:result['reason']='magic_mismatch';return result
        tag=read(address+0xc8,4);result['tag_at_c8']=hex(int.from_bytes(tag,'little'))
        if int.from_bytes(tag,'little')!=0x414e5731:result['reason']='tag_mismatch';return result
        handle=int.from_bytes(read(address+0xc0,8),'little');result['handle_at_c0']=hex(handle)
        if not handle:result['reason']='null_handle';return result
        result['class']='AdapterAnw_layout_matches';result['reason']='both_exact_magics'
    except Exception as ex:result['reason']='read_failed';result['error']=str(ex)
    return result

class Calls:
    def __init__(self):self.pending=None;self.from_count=0;self.lock_count=0
    def tail(self,tid,sp,ret,winner):
        need(self.pending is None,'overlapping fromSurface unsupported')
        need(self.from_count<MAX_FROM and tid>0 and sp>0 and ret>0,'fromSurface budget/context')
        self.from_count+=1;self.pending={'tid':tid,'sp':sp,'pc':ret,'seq':self.from_count,'winner':winner};return dict(self.pending)
    def returned(self,tid,sp,pc):
        p=self.pending;need(p is not None and (tid,sp,pc)==(p['tid'],p['sp'],p['pc']),'return TID/SP/PC mismatch')
        self.pending=None;return p
    def lock(self):need(self.lock_count<MAX_LOCK,'lock budget');self.lock_count+=1;return self.lock_count
    def complete(self):return self.from_count==MAX_FROM and self.lock_count==MAX_LOCK and self.pending is None
