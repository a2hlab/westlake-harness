#!/usr/bin/env python3
"""T17 read-only fresh profile collector. Preview default, explicit new identities."""
import argparse,datetime,hashlib,importlib.util,json,re,shlex,sys,time,uuid
from pathlib import Path
import read_binding as r
HERE=Path(__file__).resolve().parent
MODULES={'media':('/data/local/tmp/asx/lib/arm64-v8a/libmffmpeg.so',r.MEDIA),'player':('/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so',r.PLAYER),'netcompat':('/data/local/tmp/asx/libandroid_native_network_compat.so',r.NET),'libc':('/system/lib/ld-musl-aarch64.so.1',None)}

def validate_args(a):
    r.need(re.fullmatch('[0-9a-f-]{36}',a.boot or ''),'explicit boot')
    for role in ('parent','child','host'):
        r.need(type(getattr(a,role)) is int and getattr(a,role)>1 and type(getattr(a,role+'_birth')) is int and getattr(a,role+'_birth')>0,'explicit PID/birth')
    r.need(len({a.parent,a.child,a.host})==3,'distinct processes')
    r.need(a.holder and a.start is not None and abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1,'exact holder/start')

def pin_guard(a):
    q=shlex.quote;parts=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(a.boot)}']
    for role,uid in [('parent',0),('child',20011300),('host',20011300)]:
        pid=getattr(a,role);birth=getattr(a,role+'_birth')
        parts += [f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "$1" != Z; test "$1" != X; test "${{20}}" = {birth}']
        if role!='host':parts += [f'test "$2" = {1 if role=="parent" else a.parent}']
        parts += [f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = {uid}:{uid}:{uid}:{uid}',f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = 0']
    parts += [f'cmd=$(strings /proc/{a.host}/cmdline); printf "%s\\n" "$cmd" | grep -Fx org.westlake.imehost >/dev/null']
    return '; '.join(parts)

def sections(text,token):
    matches=list(re.finditer(r'^'+re.escape(token)+r'_([A-Z0-9_]+)(?:\n|$)',text,re.M));result={}
    for i,m in enumerate(matches):
        key=m[1];r.need(key not in result,'duplicate section');result[key]=text[m.end():matches[i+1].start() if i+1<len(matches) else len(text)].rstrip('\n')
    r.need(result.get('COMPLETE')=='','completion marker');return result

def parse_process(text,pid,birth,uid):
    lines=text.splitlines();r.need(len(lines)==5,'process receipt line count')
    stat=lines[0];mnt=lines[3];exe=lines[4];uidlines=[x for x in lines[1:3] if x.startswith('Uid:')];tracerlines=[x for x in lines[1:3] if x.startswith('TracerPid:')];r.need(len(uidlines)==len(tracerlines)==1,'status fields');uids=uidlines[0];tracer=tracerlines[0];m=re.fullmatch(r'(\d+) \(.*\) (.*)',stat);r.need(m and int(m[1])==pid,'stat PID');tail=m[2].split()
    r.need(len(tail)>=20 and tail[0] not in ('X','Z') and int(tail[19])==birth,'birth/state')
    r.need(uids.split()==['Uid:',*[str(uid)]*4] and tracer.split()==['TracerPid:','0'],'UID/tracer')
    r.need(re.fullmatch(r'mnt:\[[0-9]+\]',mnt) and re.fullmatch('[0-9a-f]{64}',exe.split()[0]),'mnt/exe')
    return dict(pid=pid,ppid=int(tail[1]),birth=birth,uid=uid,mnt=mnt,exe_sha256=exe.split()[0])

def script(a,token):
    parts=['set -eu',pin_guard(a)]
    def section(name,cmd):parts.extend([f'printf "{token}_{name}\\n"',cmd])
    section('INIT_MNT','readlink /proc/1/ns/mnt')
    for phase in ('BEFORE','AFTER'):
        for role in ('parent','child','host'):
            pid=getattr(a,role);section(phase+'_'+role.upper(),f'cat /proc/{pid}/stat; sed -n "/^Uid:/p;/^TracerPid:/p" /proc/{pid}/status; readlink /proc/{pid}/ns/mnt; sha256sum /proc/{pid}/exe')
        section(phase+'_MAPS',f'cat /proc/{a.child}/maps')
        for key,(path,_) in MODULES.items():
            physical=path if key=='libc' else r.RUN.rsplit('/',1)[0]+path.removeprefix('/data/local/tmp/asx')
            for label,p in [('PHYSICAL',physical),('PRIVATE',f'/proc/{a.child}/root{path}')]:section(phase+'_'+key.upper()+'_'+label,f'sha256sum {shlex.quote(p)}; stat -L -c %d:%i {shlex.quote(p)}')
        section(phase+'_RUN',f'sha256sum {r.RUN}; stat -L -c %d:%i {r.RUN}; stat -L -c %d:%i /proc/{a.parent}/root/data/local/tmp/asx/run.sh; stat -L -c %d:%i /proc/{a.child}/root/data/local/tmp/asx/run.sh')
        if phase=='BEFORE':
            section('RUN_HEX',f'od -An -v -tx1 {r.RUN}')
            section('PS','ps -A -o PID,PPID,UID,NAME')
            section('WMS',"hidumper -s WindowManagerService -a '-a'")
    parts.append(pin_guard(a));section('INIT_MNT_AFTER','readlink /proc/1/ns/mnt');section('COMPLETE',':')
    return '( '+ '; '.join(parts)+' )'

def derive(a,parts,out,receipt_sha,donor):
    p={'serial':r.SERIAL,'boot':a.boot,'run_path':r.RUN,'readonly_receipt_sha256':receipt_sha,'init_mnt':parts['INIT_MNT']}
    r.need(parts['INIT_MNT']==parts['INIT_MNT_AFTER'],'init namespace drift')
    for role,uid in [('parent',0),('child',20011300),('host',20011300)]:
        first=parse_process(parts['BEFORE_'+role.upper()],getattr(a,role),getattr(a,role+'_birth'),uid);last=parse_process(parts['AFTER_'+role.upper()],getattr(a,role),getattr(a,role+'_birth'),uid);r.need(first==last,'process identity drift');p[role]=first
    run=parts['BEFORE_RUN'].splitlines();r.need(run==parts['AFTER_RUN'].splitlines() and len(run)==4 and len(set(run[1:]))==1,'run hash/private inode drift')
    hextext=''.join(parts['RUN_HEX'].split());r.need(re.fullmatch('(?:[0-9a-fA-F]{2})+',hextext),'run hex framing');raw=bytes.fromhex(hextext);(out/'run.sh').write_bytes(raw);p['run_sha256']=run[0].split()[0]
    before=donor.map_rows(parts['BEFORE_MAPS']);after=donor.map_rows(parts['AFTER_MAPS']);identities={}
    for key,(path,fixed) in MODULES.items():
        fields={label:parts['BEFORE_'+key.upper()+'_'+label].splitlines() for label in ('PHYSICAL','PRIVATE')}
        r.need(all(len(x)==2 for x in fields.values()),'module receipt')
        digest=fields['PRIVATE'][0].split()[0];r.need(fixed is None or fixed==digest,'candidate module SHA')
        r.need(fields['PHYSICAL'][0].split()[0]==digest and fields['PHYSICAL'][1]==fields['PRIVATE'][1],'physical/private object mismatch')
        for label in ('PHYSICAL','PRIVATE'):r.need(parts['BEFORE_'+key.upper()+'_'+label]==parts['AFTER_'+key.upper()+'_'+label],'module drift')
        identities[key]=r.identity(parts['BEFORE_'+key.upper()+'_PRIVATE'],path,digest,before)
        r.need([x for x in before if x['path']==path]==[x for x in after if x['path']==path],'relevant maps drift')
        if key=='libc':p['libc']={'path':path,'sha256':digest}
    r.validate(p,out/'run.sh');return p,identities

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true')
    for name in ('repo','out'):ap.add_argument('--'+name,type=Path)
    for name in ('parent','parent-birth','child','child-birth','host','host-birth'):ap.add_argument('--'+name,type=int)
    for name in ('boot','holder','hdc'):ap.add_argument('--'+name)
    ap.add_argument('--start',type=float);a=ap.parse_args()
    if not a.execute:print(json.dumps({'execute':False,'device_calls':0,'serial':r.SERIAL}));return
    validate_args(a);r.need(a.repo and a.out and a.hdc,'explicit paths/transport')
    for rel,h in json.loads((HERE/'collector-source-pins.json').read_text()).items():r.need(r.sha(a.repo/rel)==h,'source pin '+rel)
    age=time.time()-a.start;r.need(0<=age<1080,'leave 120 seconds for paired reader plus recovery reserve');deadline=time.monotonic()+min(90,1080-age)
    r.need(a.out.is_absolute() and not str(a.out).startswith(('/tmp/','/private/tmp/')),'persistent output');a.out.mkdir(parents=True,exist_ok=False)
    sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
    class Board(b.Board):
        def command(self,argv,timeout=60):
            left=deadline-time.monotonic();r.need(left>0,'collector deadline')
            try:return super().command(argv,min(timeout,left))
            except b.BatchStop as e:
                if hasattr(e.__cause__,'stdout'):
                    stem=self.out/f'command-{self.index:05d}';stem.with_suffix('.stdout.txt').write_bytes(e.__cause__.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(e.__cause__.stderr or b'')
                raise
        def ready(self):
            super().ready();rc,held=self.command(self.lock+['held',r.SERIAL],10);r.need(rc==0 and held.strip()==a.holder,'exact holder')
    board=Board(r.SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),a.holder.split()[0],a.out/'commands');board.boot=a.boot
    token='T17PROFILE_'+uuid.uuid4().hex.upper();result={'status':'UNKNOWN','collector_sha256':r.sha(__file__),'holder':a.holder,'start':a.start,'boot':a.boot}
    try:
        _,text=board.shell(script(a,token),timeout=60);raw=(board.out/f'command-{board.index:05d}.stdout.txt').read_bytes();(a.out/'receipt.raw').write_bytes(raw)
        parts=sections(text,token)
        for key in ('BEFORE_MAPS','AFTER_MAPS','PS','WMS'):(a.out/(key.lower()+'.txt')).write_text(parts[key]+'\n')
        spec=importlib.util.spec_from_file_location('r9_reader',a.repo/r.DONOR);donor=importlib.util.module_from_spec(spec);spec.loader.exec_module(donor)
        p,identities=derive(a,parts,a.out,hashlib.sha256(raw).hexdigest(),donor)
        # The accepted reader's whole guard now validates the derived identities.
        board.shell('( set -eu; '+r.guard(p)+'; '+pin_guard(a)+' )',timeout=20)
        p['observed_at']=time.time();(a.out/'profile.json').write_text(json.dumps(p,indent=2)+'\n');result.update(status='PROFILE_READY_NOT_BINDING_PROOF',profile_sha256=r.sha(a.out/'profile.json'),receipt_sha256=r.sha(a.out/'receipt.raw'),run_sha256=r.sha(a.out/'run.sh'),modules=identities)
    except Exception as e:result['error']=str(e);raise
    finally:(a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
if __name__=='__main__':main()
