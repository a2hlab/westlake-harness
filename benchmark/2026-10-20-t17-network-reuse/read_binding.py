#!/usr/bin/env python3
"""T17: read two known media GOT slots, no device writes. Preview by default."""
import argparse, datetime, hashlib, importlib.util, json, re, shlex, sys, time, uuid
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
RUN='/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'
EXE='a7a358c60bec293c26531b0eecbf14979f77411c227cec4767742c0c82791a0c'
MEDIA='d2882303bf5dc34e297a404e4b57a214d9c30ddaf0f496eb2ef9f7dcac09c4b4'
NET='f6c354d1513071533fddcc91749f44e57a626177a584fb1bb9f48bf6446ef01e'
PLAYER='0b4d95c5f9d96826a95ede998df20be037299eaf6fbfcd1cd2afa39793ba9471'
R9='11d3d671bd501205a98ee386e64bf1274501d0458a4cdb35945f7424a388244a'
DONOR='benchmark/2026-10-19-toutiao-video-playback/candidate-r9/read_network_binding.py'
SLOTS=[('getaddrinfo',4782456,0x23f4),('freeaddrinfo',4782944,0x2a00)]
def need(v,s):
    if not v: raise ValueError(s)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def validate(p,run):
    need(p['serial']==SERIAL and re.fullmatch('[0-9a-f-]{36}',p['boot']),'serial/boot')
    need(p['run_path']==RUN and sha(run)==p['run_sha256'],'run original bytes')
    raw=Path(run).read_bytes();matches=list(re.finditer(rb'^export WL_PARENT_ID=([0-9]+)\n',raw,re.M))
    need(len(matches)==1 and 0<int(matches[0][1])<2147483648,'one numeric WID')
    m=matches[0];need(hashlib.sha256(raw[:m.start()]+b'export WL_PARENT_ID=29\n'+raw[m.end():]).hexdigest()==R9,'exact R9 run except WID')
    for role,uid in [('parent',0),('child',20011300)]:
        x=p[role];need(all(type(x[k]) is int and x[k]>0 for k in ('pid','ppid','birth')),'identity integers')
        need(x['uid']==uid and x['exe_sha256']==EXE and re.fullmatch(r'mnt:\[[0-9]+\]',x['mnt']),'UID/exe/namespace')
    need(p['parent']['ppid']==1 and p['child']['ppid']==p['parent']['pid'],'ancestry')
    need(re.fullmatch(r'mnt:\[[0-9]+\]',p['init_mnt']) and p['parent']['mnt']==p['child']['mnt']!=p['init_mnt'],'private namespace')
    need(p['libc']['path']=='/system/lib/ld-musl-aarch64.so.1' and re.fullmatch('[0-9a-f]{64}',p['libc']['sha256']),'fresh libc pin')
    need(re.fullmatch('[0-9a-f]{64}',p['readonly_receipt_sha256']),'receipt')
    return p

def guard(p):
    q=shlex.quote;parts=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(p["boot"])}',f'test "$(readlink /proc/1/ns/mnt)" = {q(p["init_mnt"])}']
    for role in ('parent','child'):
        x=p[role];pid=x['pid']
        stat=f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "$1" != Z; test "$1" != X; test "${{20}}" = {x["birth"]}; test "$2" = {x["ppid"]}'
        parts += [stat,f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = {x["uid"]}:{x["uid"]}:{x["uid"]}:{x["uid"]}',f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = 0',f'test "$(readlink /proc/{pid}/ns/mnt)" = {q(x["mnt"])}',f'e=$(sha256sum /proc/{pid}/exe); set -- $e; test "$1" = {EXE}',stat]
    parts += [f'e=$(sha256sum {q(RUN)}); set -- $e; test "$1" = {p["run_sha256"]}']
    for role in ('parent','child'):
        parts += [f'test "$(stat -L -c %d:%i {q(RUN)})" = "$(stat -L -c %d:%i /proc/{p[role]["pid"]}/root/data/local/tmp/asx/run.sh)"']
    return '; '.join(parts)

def word_command(pid,address,token):
    need(type(pid) is int and pid>1 and type(address) is int and address>0 and address%8==0,'known aligned slot')
    need(re.fullmatch('[A-Z0-9_]+',token),'token')
    # FD3 preserves an explicit dd status beside od's ASCII bytes. HDC merges stderr;
    # retain diagnostics, never route them into od or suppress them. No remote temp files.
    return f'printf "{token}_BEGIN\\n"; {{ {{ if dd if=/proc/{pid}/mem bs=8 skip={address//8} count=1; then d=0; else d=$?; fi; printf "\\n{token}_DD_RC:%s\\n" "$d" >&3; }} | od -An -tx1; }} 3>&1; printf "{token}_END\\n"'

def parse_word(text,token):
    lines=text.splitlines();need(lines.count(token+'_BEGIN')==1 and lines.count(token+'_END')==1,'word frame')
    lo=lines.index(token+'_BEGIN');hi=lines.index(token+'_END');need(lo<hi,'word order')
    body=lines[lo+1:hi];need([x for x in body if x.startswith(token+'_DD_RC:')]==[token+'_DD_RC:0'],'dd failure/missing rc')
    hexlines=[x.split() for x in body if re.fullmatch(r'\s*(?:[0-9a-fA-F]{2}\s+)*[0-9a-fA-F]{2}\s*',x)]
    need(len(hexlines)==1 and len(hexlines[0])==8,'exact eight bytes')
    return int.from_bytes(bytes(int(x,16) for x in hexlines[0]),'little')

def identity(text,path,digest,rows):
    lines=text.splitlines();need(len(lines)==2 and lines[0].split()[0]==digest,'private ELF SHA')
    device,inode=map(int,lines[1].split(':'));major=((device>>8)&0xfff)|((device>>32)&~0xfff);minor=(device&0xff)|((device>>12)&~0xff)
    selected=[r for r in rows if r['path']==path];need(selected,'missing exact mapping')
    need(all(int(r['inode'])==inode and tuple(int(v,16) for v in r['device'].split(':'))==(major,minor) for r in selected),'mapped object dev/inode')
    return {'sha256':digest,'device_inode':lines[1]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true')
    for k in ('repo','profile','receipt','run-file','inputs','net-elf','out'):ap.add_argument('--'+k,type=Path)
    ap.add_argument('--hdc');ap.add_argument('--holder');ap.add_argument('--start',type=float);a=ap.parse_args()
    if not a.execute: print(json.dumps({'execute':False,'device_calls':0,'serial':SERIAL,'slots':SLOTS}));return
    need(all([a.repo,a.profile,a.receipt,a.run_file,a.inputs,a.net_elf,a.out,a.hdc,a.holder,a.start]),'explicit inputs')
    here=Path(__file__).resolve().parent
    for rel,digest in json.loads((here/'reader-source-pins.json').read_text()).items():need(sha(a.repo/rel)==digest,'source pin '+rel)
    p=validate(json.loads(a.profile.read_text()),a.run_file);need(sha(a.receipt)==p['readonly_receipt_sha256'],'actual receipt')
    need(0<=time.time()-p['observed_at']<=120,'fresh profile')
    need(abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1,'holder/start')
    age=time.time()-a.start;need(0<=age<1200,'reserve 10 minutes for restore')
    deadline=time.monotonic()+min(120,1200-age)
    need(a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent output');a.out.mkdir(parents=True,exist_ok=False)
    spec=importlib.util.spec_from_file_location('r9_reader',a.repo/DONOR);donor=importlib.util.module_from_spec(spec);spec.loader.exec_module(donor)
    donor.PINS={'libmffmpeg.so':(a.inputs/'libmffmpeg.so',MEDIA),'libandroid_native_network_compat.so':(a.net_elf,NET)}
    for path,digest in donor.PINS.values():need(sha(path)==digest,'local ELF')
    need(sha(a.inputs/'libttmplayer.so')==PLAYER,'local player')
    sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
    class Board(b.Board):
        def command(self,argv,timeout=60):
            remaining=deadline-time.monotonic();need(remaining>0,'120 second reader deadline/recovery reserve')
            try:return super().command(argv,min(timeout,remaining,15))
            except b.BatchStop as e:
                if hasattr(e.__cause__,'stdout'):
                    stem=self.out/f'command-{self.index:05d}';stem.with_suffix('.stdout.txt').write_bytes(e.__cause__.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(e.__cause__.stderr or b'')
                raise
        def ready(self):
            super().ready();rc,held=self.command(self.lock+['held',SERIAL],10);need(rc==0 and held.strip()==a.holder,'exact holder')
    board=Board(SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),a.holder.split()[0],a.out/'commands');board.boot=p['boot']
    g=guard(p)
    def read(cmd):return board.shell('( set -eu; '+g+'; '+cmd+'; '+g+' )')[1]
    result={'status':'UNKNOWN','serial':SERIAL,'profile_sha256':sha(a.profile),'reader_sha256':sha(__file__),'holder':a.holder,'memory_writes':0,'playback':'unknown','audio':'unknown','reads':[]}
    def save(): (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    save()
    try:
        raw=read(f'cat /proc/{p["child"]["pid"]}/maps');(a.out/'maps-before.txt').write_text(raw);rows=donor.map_rows(raw)
        paths={'media':('/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so',MEDIA),'player':('/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so',PLAYER),'netcompat':('/data/local/tmp/asx/libandroid_native_network_compat.so',NET),'libc':(p['libc']['path'],p['libc']['sha256'])}
        def files(phase,current):
            values={}
            for role,(path,digest) in paths.items():
                private=shlex.quote(f'/proc/{p["child"]["pid"]}/root{path}');text=read(f'sha256sum {private}; stat -L -c %d:%i {private}');(a.out/f'{phase}-{role}.txt').write_text(text);values[role]=identity(text,path,digest,current)
            return values
        result['files_before']=files('before',rows)
        media=donor.bias_for('libmffmpeg.so',rows)[0];net=donor.bias_for('libandroid_native_network_compat.so',rows)[0]
        result['biases']={'media':hex(media),'netcompat':hex(net)}
        for label,offset,target in SLOTS:
            address=media+offset;need(any(r['path']==paths['media'][0] and r['raw'].split()[1].startswith('r') and r['lo']<=address and address+8<=r['hi'] for r in rows),'slot not in exact readable media mapping')
            token='T17_'+uuid.uuid4().hex.upper();text=read(word_command(p['child']['pid'],address,token));(a.out/f'{label}.txt').write_text(text);value=parse_word(text,token)
            need(any(r['path']==paths['netcompat'][0] and 'x' in r['raw'].split()[1] and r['lo']<=net+target<r['hi'] for r in rows),'expected target not in exact executable provider mapping')
            result['reads'].append({'label':label,'address':hex(address),'value':hex(value),'expected':hex(net+target),'match':value==net+target});save()
        raw=read(f'cat /proc/{p["child"]["pid"]}/maps');(a.out/'maps-after.txt').write_text(raw);after=donor.map_rows(raw)
        for path,_ in paths.values():need([r for r in rows if r['path']==path]==[r for r in after if r['path']==path],'relevant maps drift')
        result['files_after']=files('after',after);need(result['files_before']==result['files_after'],'private object drift')
        read('true');result['status']='PAIRED_BINDING_MATCH' if all(x['match'] for x in result['reads']) else 'PAIRED_BINDING_MISMATCH';save();need(result['status']=='PAIRED_BINDING_MATCH','binding mismatch; outer restore required')
    except Exception as e:
        result['error']=str(e);save();raise
    print(json.dumps(result))
if __name__=='__main__':main()
