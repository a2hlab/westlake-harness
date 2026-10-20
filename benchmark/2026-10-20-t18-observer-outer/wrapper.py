#!/usr/bin/env python3
"""Outer-only 5cd server/forward ownership around the pinned T18 observer."""
import argparse,datetime,hashlib,importlib.util,json,re,shlex,signal,subprocess,sys,time,uuid
from pathlib import Path
SERIAL='5cd1e3dd00000000000000000923012c'
SERVER='13c0b4bfcb0b8b83cd9d73df2be0ebffcb1cc5fea2eb420cb7b2f5629254a06a'
HOST='c6008509f6b4bd8b5766eaad671738364eaa01a039db00e5d94e47204972dbf1'
PATHS={'player':'/data/local/tmp/asx/lib/arm64-v8a/libttmplayer.so','android':'/data/local/tmp/asx/webview-t-lib/libandroid.so','shim':'/data/local/tmp/asx/webview-t-lib/libwebview_bionic_shim.so','bridge':'/data/local/tmp/asx/liboh_adapter_bridge.so','hwui':'/data/local/tmp/asx/libhwui.so'}
HERE=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=shlex.quote
def need(v,msg):
    if not v:raise ValueError(msg)
def save(p,d):p.write_text(json.dumps(d,indent=2)+'\n')
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

def forward_lines(text,port):
    token='tcp:'+str(port)
    return [line for line in text.splitlines() if token in line.split()]

def stop_host(proc):
    if proc is None or proc.poll() is not None:return
    proc.terminate()
    try:proc.wait(timeout=3)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=3)


def process_guard(p,tracer=0):
    parts=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {q(p["boot"])}',f'test "$(readlink /proc/1/ns/mnt)" = {q(p["init_mnt"])}']
    running='test "$1" != T; test "$1" != t; ' if tracer==0 else ''
    for role in ('parent','child','host'):
        x=p[role];pid=x['pid'];stat=f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "$1" != Z; test "$1" != X; {running}test "${{20}}" = {x["birth"]}; test "$2" = {x["ppid"]}'
        parts.extend([stat,f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = {x["uid"]}:{x["uid"]}:{x["uid"]}:{x["uid"]}',f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = {tracer if role=="child" else 0}',f'test "$(readlink /proc/{pid}/ns/mnt)" = {q(x["mnt"])}',f'e=$(sha256sum /proc/{pid}/exe); set -- $e; test "$1" = {x["exe_sha256"]}',stat])
    parts.append(f'c=$(strings /proc/{p["host"]["pid"]}/cmdline); printf "%s\\n" "$c" | grep -Fx org.westlake.imehost >/dev/null')
    if 'run_path' in p:
        parts += [f'e=$(sha256sum {q(p["run_path"])}); set -- $e; test "$1" = {p["run_sha256"]}']
        for role in ('parent','child'):parts += [f'test "$(stat -L -c %d:%i {q(p["run_path"])})" = "$(stat -L -c %d:%i /proc/{p[role]["pid"]}/root/data/local/tmp/asx/run.sh)"']
    return '; '.join(parts)

def validate_local(a,repo,profile_dir):
    need(a.get('schema')=='t18-outer-v1' and a.get('execution_enabled') is True and a.get('approved_by')=='outer(codex)','outer admission')
    need(a.get('wrapper_sha256')==sha(__file__) and a.get('serial')==SERIAL,'wrapper/serial')
    need(type(a.get('port')) is int and 1024<=a['port']<=65535,'port')
    need(abs(a['start']-datetime.datetime.fromisoformat(a['holder'].split()[2]).timestamp())<1,'holder/start')
    need(0<=time.time()-a['start']<960,'leave observation and recovery budget')
    p=json.loads((profile_dir/'profile.json').read_text());r=json.loads((profile_dir/'result.json').read_text())
    need(r['status']=='PROFILE_READY_NOT_BINDING_PROOF' and r['holder']==a['holder'] and r['start']==a['start'],'collector receipt status/holder')
    need(p['serial']==SERIAL and p['boot']==a['boot'] and r['boot']==a['boot'],'profile boot/serial')
    need(sha(profile_dir/'profile.json')==r['profile_sha256'] and sha(profile_dir/'receipt.raw')==p['readonly_receipt_sha256']==r['receipt_sha256'],'actual profile receipt SHA')
    need(0<=time.time()-p['observed_at']<=120,'fresh collector profile')
    for rel,h in json.loads((HERE/'source-pins.json').read_text()).items():need(sha(repo/rel)==h,'source pin '+rel)
    sys.path.insert(0,str(repo/'benchmark/2026-10-20-t17-network-reuse'));import read_binding as reader
    reader.validate(p,profile_dir/'run.sh')
    for role in ('parent','child','host'):
        need(p[role]['pid']==a[role]['pid'] and p[role]['birth']==a[role]['birth'],'explicit identity '+role)
    need(all(type(p['host'][k]) is int and p['host'][k]>0 for k in ('pid','ppid','birth')) and re.fullmatch(r'mnt:\[[0-9]+\]',p['host']['mnt']) and re.fullmatch('[0-9a-f]{64}',p['host']['exe_sha256']),'host types')
    need(p['host']['uid']==20011300 and len({p[x]['pid'] for x in ('parent','child','host')})==3,'host/distinct processes')
    observer=repo/a['observer_path'];need(sha(observer)==a['observer_sha256'],'reviewed T18 observer')
    t18=load('t18_outer_reviewed_observer',observer);core=t18.load_t18_core(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-t16')
    for role,digest in core.MODULE_PINS.items():need(sha(a['module_files'][role])==digest,'local module '+role)
    for name,digest in [('server_file',SERVER),('host_file',HOST)]:need(sha(a[name])==digest,'local tool '+name)
    need(sha(a['hdc_file'])==a['hdc_sha256']=='72534d4284d40a2184cf01c987bc6dcdbdd73f171637cab24a965dc1ea79042b','hdc tool')
    return p,r,reader,t18,core

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--execute',action='store_true');ap.add_argument('--repo',type=Path);ap.add_argument('--plan',type=Path);ap.add_argument('--profile-dir',type=Path);ap.add_argument('--out',type=Path);args=ap.parse_args()
    if not args.execute:print(json.dumps({'execute':False,'device_calls':0,'serial':SERIAL,'observer_seconds':120,'needs_outer_admission':True}));return
    need(all([args.repo,args.plan,args.profile_dir,args.out]),'explicit inputs');repo=args.repo.resolve();a=json.loads(args.plan.read_text());p,rec,reader,t18,core=validate_local(a,repo,args.profile_dir)
    out=args.out.absolute();need(not str(out).startswith(('/tmp/','/private/tmp/')),'persistent output');out.mkdir(parents=True,exist_ok=False)
    save(out/'plan.json',a);save(out/'profile.json',p)
    normal_end=time.monotonic()+min(240,1200-(time.time()-a['start']));recovery_end=time.monotonic()+min(330,1800-(time.time()-a['start']));cleaning=False
    sys.path.insert(0,str(repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
    class Board(b.Board):
        def command(self,argv,timeout=60):
            left=(recovery_end if cleaning else normal_end)-time.monotonic();need(left>0,'outer deadline')
            try:return super().command(argv,min(timeout,left,20))
            except b.BatchStop as ex:
                cause=ex.__cause__
                if isinstance(cause,subprocess.TimeoutExpired):
                    stem=self.out/f'command-{self.index:05d}';stem.with_suffix('.stdout.txt').write_bytes(cause.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(cause.stderr or b'')
                raise
        def ready(self):
            super().ready();rc,held=self.command(self.lock+['held',SERIAL],10);need(rc==0 and held.strip()==a['holder'],'exact holder')
    board=Board(SERIAL,q(a['hdc_file']),'bash '+q(str(repo/'scripts/lab/board_note.sh')),a['holder'].split()[0],out/'commands');board.boot=p['boot']
    token=uuid.uuid4().hex;remote='/data/local/tmp/t18-lldb-'+p['boot'][:8]+'-'+token;server=remote+'/lldb-server';port=a['port'];porthex=f'{port:04X}'
    result={'status':'INCOMPLETE','server_start_attempted':False,'forward_attempted':False,'cleanup':{'verified':False},'remote':remote,'playback':'UNKNOWN','audio':'UNKNOWN'};owned_server=None;forward_before=None;proc=None
    def cancel(signum,frame):
        if not cleaning:raise RuntimeError('outer signal '+str(signum))
    old_handlers={n:signal.signal(n,cancel) for n in (signal.SIGTERM,signal.SIGINT)}
    def persist():save(out/'result.json',result)
    def shell(cmd):return board.shell('( set -eu; '+cmd+' )',timeout=20)[1]
    def guarded(cmd,tracer=0):g=process_guard(p,tracer);return shell(g+'; '+cmd+'; '+g)
    def hcmd(tail):
        board.ready();rc,text=board.command(board.hdc+['-t',SERIAL]+tail);need(rc==0,'hdc '+repr(tail));return text
    def server_identity():
        text=shell('cat '+remote+'/launch.pid');need(re.fullmatch('[0-9]+',text.strip()),'launch pid');pid=int(text.strip());need(pid>1 and pid not in {p[x]['pid'] for x in ('parent','child','host')},'server distinct')
        raw=shell(f'cat /proc/{pid}/stat');sf=load('r13_outer_stat',repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/core.py').stat_fields(raw)
        birth=sf['birth'];need(sf['pid']==pid and sf['state'] not in ('Z','X'),'server stat')
        status=shell(f'cat /proc/{pid}/status');uids=next(x.split()[1:] for x in status.splitlines() if x.startswith('Uid:'));need(len(uids)==4 and len(set(uids))==1,'server uid');uid=int(uids[0])
        need(shell(f'sha256sum /proc/{pid}/exe').split()[0]==SERVER,'server executable')
        argv=[server,'gdbserver','127.0.0.1:'+str(port),'--attach',str(p['child']['pid'])]
        need(bytes.fromhex(shell(f'od -An -v -tx1 /proc/{pid}/cmdline'))==b'\0'.join(x.encode() for x in argv)+b'\0','server cmdline')
        sf2=load('r13_outer_stat2',repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13/core.py').stat_fields(shell(f'cat /proc/{pid}/stat'));need(sf2['birth']==birth and sf2['pid']==pid,'server birth drift')
        return {'pid':pid,'birth':birth,'uid':uid,'sha256':SERVER}
    persist()
    try:
        # Gate every real module's private bytes and mapped dev/inode before any staging.
        guarded('true');maps=guarded(f'cat /proc/{p["child"]["pid"]}/maps');(out/'before_maps.txt').write_text(maps)
        donor=load('t18_outer_maps',repo/reader.DONOR);rows=donor.map_rows(maps);mods={}
        for role,path in PATHS.items():
            text=guarded(f'sha256sum /proc/{p["child"]["pid"]}/root{path}; stat -L -c %d:%i /proc/{p["child"]["pid"]}/root{path}');ident=reader.identity(text,path,core.MODULE_PINS[role],rows);dev,ino=map(int,ident['device_inode'].split(':'));mods[role]={'local_path':a['module_files'][role],'sha256':core.MODULE_PINS[role],'remote_path':path,'device':dev,'inode':ino}
        after=guarded(f'cat /proc/{p["child"]["pid"]}/maps');(out/'after_maps.txt').write_text(after)
        for path in PATHS.values():need([x for x in maps.splitlines() if x.split()[-1]==path]==[x for x in after.splitlines() if x.split()[-1]==path],'module maps drift')
        forward_before=hcmd(['fport','ls']);need(not forward_lines(forward_before,port),'preexisting forward');(out/'forwards-before.txt').write_text(forward_before)
        tcp=guarded('cat /proc/net/tcp; cat /proc/net/tcp6');need(not any(len(f)>3 and f[1].endswith(':'+porthex) and f[3]=='0A' for l in tcp.splitlines() if (f:=l.split())),'existing listener')
        guarded('test ! -e '+remote+'; mkdir '+remote+'; chmod 700 '+remote);board.send(a['server_file'],server);guarded('e=$(sha256sum '+server+'); set -- $e; test "$1" = '+SERVER+'; chmod 700 '+server)
        result['forward_attempted']=True;persist();hcmd(['fport','tcp:'+str(port),'tcp:'+str(port)]);fw=hcmd(['fport','ls']);need(len(forward_lines(fw,port))==1 and forward_lines(fw,port)[0].split().count('tcp:'+str(port))==2,'owned forward exact');result['forward_line']=forward_lines(fw,port)[0];persist()
        result['server_start_attempted']=True;persist()
        # No second launch on timeout; finally recovers identity only from this owned launch.pid.
        shell(process_guard(p)+'; ( '+server+' gdbserver 127.0.0.1:'+str(port)+' --attach '+str(p['child']['pid'])+' >'+remote+'/server.stdout 2>'+remote+'/server.stderr < /dev/null & echo $! >'+remote+'/launch.pid )')
        owned_server=server_identity();result['server']=owned_server;persist()
        ready_end=min(normal_end,time.monotonic()+8)
        while True:
            tracer=shell(f'sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{p["child"]["pid"]}/status').strip()
            if tracer==str(owned_server['pid']):break
            need(tracer=='0' and time.monotonic()<ready_end,'attach readiness/foreign tracer');time.sleep(.2)
        guarded('true',owned_server['pid'])
        tcp=shell('cat /proc/net/tcp');fds=shell(f'ls -l /proc/{owned_server["pid"]}/fd');listeners=[l.split() for l in tcp.splitlines() if len(l.split())>9 and l.split()[1]=='0100007F:'+porthex and l.split()[3]=='0A'];need(len(listeners)==1 and 'socket:['+listeners[0][9]+']' in fds,'server owned listener')
        admission={'schema':'t16-admission-v1','execution_enabled':True,'approved_by':'outer(codex)','serial':SERIAL,'created_at':time.time(),'expires_at':min(time.time()+180,a['start']+1200),'holder':a['holder'],'max_seconds':120,'max_fromSurface':4,'max_lock':4,'identity':{'boot':p['boot'],'parent':p['parent']['pid'],'parent_birth':p['parent']['birth'],'parent_uid':p['parent']['uid'],'child':p['child']['pid'],'child_birth':p['child']['birth'],'uid':p['child']['uid'],'parent_exe_sha256':p['parent']['exe_sha256'],'child_exe_sha256':p['child']['exe_sha256'],'mnt':p['child']['mnt'],'fresh_profile':True},'server':owned_server,'modules':mods,'host':{'path':a['host_file'],'sha256':HOST},'hdc':{'path':a['hdc_file'],'sha256':a['hdc_sha256']},'lock_script':{'path':str(repo/'scripts/lab/board_note.sh'),'sha256':sha(repo/'scripts/lab/board_note.sh')},'require_hardware_breakpoint':True,'hardware_explicit':True,'no_software_fallback':True,'no_stepout':True,'no_expr':True,'observed_fields':['magic','tag','handle','winner_module'],'installs_r15':False,'addresses':[{'role':'android','slot':0x472688,'expected_elf':0x3b9c,'pc':0x3bd4},{'role':'shim','slot':0x472490,'expected_elf':0x5e48,'pc':0x5e48}]}
        core.t16_validate(admission);save(out/'observer-admission.json',admission);obsout=out/'observe';obsout.mkdir()
        body='import sys; sys.path.insert(0, '+repr(str((repo/a['observer_path']).parent))+'); import t18_observer; t18_observer.entry('+', '.join(map(repr,[str(out/'observer-admission.json'),str(obsout),port,str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-r13'),str(repo/'benchmark/2026-10-19-toutiao-video-playback/diagnostic-t16')]))+')'
        argv=[a['host_file'],'--no-lldbinit','--batch','-o','script '+body,'-o','quit'];save(out/'host.argv.json',argv)
        with (out/'host.stdout').open('wb') as stdout,(out/'host.stderr').open('wb') as stderr:
            need(normal_end-time.monotonic()>=130,'insufficient full observation budget')
            proc=subprocess.Popen(argv,stdout=stdout,stderr=stderr,start_new_session=True)
            try:rc=proc.wait(timeout=min(145,normal_end-time.monotonic()))
            except subprocess.TimeoutExpired:
                result['host_timeout']=True;stop_host(proc);rc=proc.returncode
        result['host_rc']=rc;persist();need(rc==0 and not result.get('host_timeout'),'observer host incomplete');result['observer_result']=json.loads((obsout/'result.json').read_text());need(result['observer_result']['cleanup']['verified'],'observer detach unverified');need(result['observer_result'].get('exit_reason')=='event_budget_complete','observer incomplete');result['status']='OBSERVATION_RETURNED_NOT_PLAYBACK'
    except Exception as ex:result['error']=str(ex)
    finally:
        cleaning=True;errors=[]
        try:stop_host(proc)
        except Exception as ex:errors.append('host cleanup unknown: '+str(ex))
        if result['server_start_attempted']:
            try:
                pidtext=shell('cat '+remote+'/launch.pid').strip();need(re.fullmatch('[0-9]+',pidtext),'owned launch pid missing')
                pid=int(pidtext);need(pid>1 and pid not in {p[x]['pid'] for x in ('parent','child','host')},'server distinct')
                present=shell(f'if test -e /proc/{pid}/stat; then printf PRESENT; else printf GONE; fi').strip()
                if present=='PRESENT':
                    current=server_identity()
                    if owned_server:need(current==owned_server,'server ownership drift')
                    owned_server=current
                    need(server_identity()==owned_server,'server changed before TERM')
                    shell(f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "${{20}}" = {owned_server["birth"]}; kill -TERM {pid}')
                    stop_end=min(recovery_end,time.monotonic()+8)
                    while shell(f'if test -e /proc/{pid}/stat; then printf PRESENT; else printf GONE; fi').strip()!='GONE':
                        need(time.monotonic()<stop_end,'owned server remains after TERM');time.sleep(.2)
                else:need(present=='GONE','server absence unknown')
                result['cleanup']['owned_server_gone']=True
            except Exception as ex:errors.append('server cleanup unknown: '+str(ex))
        if result['forward_attempted']:
            try:
                lines=forward_lines(hcmd(['fport','ls']),port);need(len(lines)<=1,'ambiguous forward cleanup')
                if lines:
                    need(lines[0].split().count('tcp:'+str(port))==2 and (not result.get('forward_line') or lines[0]==result['forward_line']),'foreign forward');hcmd(['fport','rm','tcp:'+str(port),'tcp:'+str(port)])
                need(not forward_lines(hcmd(['fport','ls']),port),'forward remains')
            except Exception as ex:errors.append('forward cleanup unknown: '+str(ex))
        try:
            guarded('true');state=shell(f'r=$(cat /proc/{p["child"]["pid"]}/stat); z=${{r##*) }}; set -- $z; test "$1" != T; test "$1" != t');result['cleanup']['child_identity_tracer0_nonstopped']=True
        except Exception as ex:errors.append('child resume unknown: '+str(ex))
        result['cleanup'].update(verified=not errors,errors=errors);result['outer_recovery_required']=bool(errors) or result.get('host_timeout',False) or result['status']!='OBSERVATION_RETURNED_NOT_PLAYBACK';persist()
    for signum,handler in old_handlers.items():signal.signal(signum,handler)
    print(json.dumps(result));raise SystemExit(0 if result['cleanup']['verified'] and result['status']=='OBSERVATION_RETURNED_NOT_PLAYBACK' else 2)
if __name__=='__main__':main()
