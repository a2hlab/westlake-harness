"""Thin guarded adapters. Imported only after explicit outer-enabled execution."""
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from transaction import TransportUnknown,validate_kit,transact,unknown_resolved
from policy import APK,CANDIDATE,ORIGINAL,SERIAL,TARGETS,Refuse,need,guard,identity,maps_snapshot,check_coverage,processes

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(x,indent=2)+'\n')
def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def apply_attempt(cfg,window):
    """Permit a fresh read-only admission attempt, never replay a transaction."""
    need(not (window/'g13-transaction.json').exists(),'transaction exists; do not retry apply')
    previous=[p for p in window.glob('g13-apply*') if p.is_dir()]
    if not previous:return 'g13-apply'
    proof=cfg.get('admission_retry') or {}
    latest=max(previous,key=lambda p:p.stat().st_mtime_ns)
    need(proof.get('previous_attempt')==latest.name,'latest apply attempt lacks explicit refusal receipt')
    for field in ['receipt','stderr']:
        path=proof.get(field+'_path')
        need(path and Path(path).is_file() and sha(path)==proof.get(field+'_sha256'),'apply refusal '+field+' evidence missing/drift')
    receipt=json.loads(Path(proof['receipt_path']).read_text())
    argv=receipt.get('argv',[])
    need(receipt.get('rc')==1 and isinstance(receipt.get('start'),(int,float)) and isinstance(receipt.get('end'),(int,float)) and receipt['start']<=receipt['end']<=time.time(),'prior apply did not definitively finish with refusal')
    runner=Path(cfg['bindings']['repo'])/'benchmark/2026-10-21-commercial-game/apk-extractor/device-window/run_window.py'
    need(len(argv)==6 and Path(argv[1]).resolve()==runner.resolve() and argv[2:4]==['apply','--plan'] and argv[5]=='--execute','receipt is not this apply entry')
    failure=Path(proof['stderr_path']).read_text().strip().splitlines()
    need(failure and re.fullmatch(r'policy\.Refuse: uncovered non-observer PID [0-9]+',failure[-1]),'prior outcome is not the explicit maps admission refusal')
    return 'g13-apply-'+str(time.time_ns())

def close_maps(board,snapshot,before,after):
    """Close the observed PID set with at most two bounded supplemental reads.

    A ps-only newcomer is never classified by NAME. Only the existing exact
    hdcd observation ancestry exemption is retained. No failed read is empty.
    """
    def observer(pid,rows):
        row=rows[pid];parent=rows.get(row['ppid'],{})
        return (row['name']=='sh' and parent.get('name')=='hdcd') or (row['name']=='ps' and parent.get('name')=='sh' and rows.get(parent['ppid'],{}).get('name')=='hdcd')
    original=processes(before);current=processes(after);absent=set()
    def filtered_before():
        return '\n'.join(l for l in before.splitlines() if not (l.split() and l.split()[0].isdigit() and int(l.split()[0]) in absent))
    for turn in range(3):
        missing=[pid for pid in current.keys()-snapshot['identities'].keys() if not observer(pid,current)]
        vanished=[pid for pid in original.keys()-snapshot['identities'].keys()-current.keys()-absent if not observer(pid,original)]
        if not missing and not vanished:
            check_coverage(snapshot,filtered_before(),after)
            snapshot['closure_rounds']=turn;snapshot['confirmed_absent_before_pids']=sorted(absent)
            return snapshot
        need(turn<2,'maps closure still has uncovered PIDs after2 supplemental rounds')
        need(len(missing)+len(vanished)<=8,'maps closure delta exceeds bounded8 PID supplement')
        for pid in sorted(vanished):
            rc,text=board.shell(f'test ! -d /proc/{pid} && echo G13_ABSENT_{pid}',timeout=15)
            need(rc==0 and text.strip()==f'G13_ABSENT_{pid}','old before PID disappearance unproven')
            absent.add(pid)
        for pid in sorted(missing):
            command=(f'set -e; echo BEGIN_PROC /proc/{pid}; cat /proc/{pid}/stat; echo STAT_BEFORE_RC=0; '
                     f'cat /proc/{pid}/maps; echo MAPS_RC=0; cat /proc/{pid}/stat; echo STAT_AFTER_RC=0; '
                     f'echo END_PROC /proc/{pid}; echo PROC_COUNT=1')
            rc,text=board.shell(command,timeout=15);need(rc==0,'supplemental proc read failed')
            extra=maps_snapshot(text);need(set(extra['identities'])=={pid},'supplemental PID mismatch')
            need(extra['identities'][pid]['ppid']==current[pid]['ppid'],'supplemental parent drift')
            snapshot['identities'].update(extra['identities']);snapshot['hits'].extend(extra['hits'])
        rc,after=board.shell('ps -A -o PID,PPID,UID,NAME',timeout=15);need(rc==0,'closure ps failed')
        following=processes(after)
        for pid in current.keys()&following.keys():
            need((current[pid]['ppid'],current[pid]['uid'])==(following[pid]['ppid'],following[pid]['uid']),'closure ps parent/uid drift '+str(pid))
        need(not (absent&following.keys()),'previously absent PID reappeared during closure')
        current=following;snapshot['count']=len(snapshot['identities'])
    raise Refuse('maps closure incomplete')

def loader_role(stat,status,exe,cmdline_hex,passwd):
    ident=identity(stat)
    accounts=[line.split(':') for line in passwd.splitlines() if line.startswith('installs:')]
    need(len(accounts)==1 and len(accounts[0])==7 and accounts[0][2].isdigit(),'installs account unresolved')
    uid=int(accounts[0][2]);uids=re.findall(r'^Uid:\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$',status,re.M)
    need(len(uids)==1 and all(int(x)==uid for x in uids[0]),'loader UID differs from declared account')
    need(ident['comm']=='installs' and ident['ppid']==1 and exe.strip()=='/system/bin/sa_main','loader role/parent/executable mismatch')
    need(re.fullmatch(r'(?:[0-9a-fA-F]{2}(?:\s+|$))+',cmdline_hex.strip()) is not None,'malformed cmdline hex')
    args=[x for x in bytes.fromhex(cmdline_hex).split(b'\0') if x]
    need(args in [[b'installs'],[b'/system/bin/sa_main',b'/system/profile/installs.json']],'loader cmdline neither declared argv nor renamed process')
    return dict(identity=ident,uid=uid,cmdline_form='renamed' if args==[b'installs'] else 'declared')

def execute(phase,cfg):
    v=cfg['bindings'];need(all(v.get(k) is not None for k in ['repo','window','hdc','holder','lane','transaction','kit','hook_config','manifest','input_root','source_pins']),'missing binding')
    need(cfg['candidate_sha256']==CANDIDATE and cfg['original_sha256']==ORIGINAL and cfg['apk_sha256']==APK,'input pins drift')
    repo,window=Path(v['repo']),Path(v['window']);need(window.is_absolute(),'window must be absolute')
    need(bool(v['source_pins']), 'source pins empty')
    for rel,digest in v['source_pins'].items():need(sha(repo/rel)==digest,'source drift '+rel)
    need(bool(cfg.get('local_pins')), 'local pins missing')
    for name,digest in cfg['local_pins'].items():need(sha(name)==digest,'local pin drift '+name)
    attempt=apply_attempt(cfg,window) if phase=='apply' else (('g13-'+phase+'-'+str(time.time_ns())) if phase in ['restore','reconcile','launch-only'] else 'g13-'+phase)
    log=window/attempt;log.mkdir(parents=True,exist_ok=False)
    sys.path[:0]=[str(repo/'scripts/lab'),str(repo/'benchmark/2026-09-28-bms-route-deploy/batch')]
    import bms_batch as b
    g06=module('g13_g06',repo/'benchmark/2026-10-21-commercial-game/first-launch/recovery_hook.py')
    OriginalBoard=b.Board
    class Board(OriginalBoard):
        def __init__(self,*args,**kwargs):
            super().__init__(*args,**kwargs)
            need(self.serial==SERIAL and self.lane==v['lane'],'provider board/lane drift')
            self.hdc=[v['hdc']];self.out.mkdir(parents=True,exist_ok=True)
        def command(self,argv,timeout=60):
            self.index+=1;p=self.out/f'command-{self.index:05d}';start=time.time()
            save(p.with_suffix('.json'),dict(argv=argv,start=start,status='RUNNING'))
            # Stream both files from process creation: preserve evidence even if parent dies.
            with p.with_suffix('.stdout').open('wb') as out,p.with_suffix('.stderr').open('wb') as err:
                proc=subprocess.Popen(argv,stdout=out,stderr=err)
                try:rc=proc.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    proc.terminate()
                    try:proc.wait(timeout=3)
                    except subprocess.TimeoutExpired:proc.kill();proc.wait()
                    save(p.with_suffix('.json'),dict(argv=argv,start=start,end=time.time(),rc=124,remote_outcome='unknown; do not replay'))
                    raise TransportUnknown('timeout: no retry, remote outcome unknown')
            save(p.with_suffix('.json'),dict(argv=argv,start=start,end=time.time(),rc=rc))
            return rc,p.with_suffix('.stdout').read_text(errors='replace')+p.with_suffix('.stderr').read_text(errors='replace')
        def raw_shell(self,command,timeout=60):
            marker='__G13_RC_'+uuid.uuid4().hex+'='
            shell='sh -c '+shlex.quote(command)+'; r=$?; printf "\\n'+marker+'%s\\n" "$r"'
            rc,text=self.command(self.hdc+['-t',SERIAL,'shell',shell],timeout)
            m=re.search(re.escape(marker)+r'(\d+)\s*$',text)
            if rc!=0 or m is None:raise TransportUnknown('transport/status unknown; no retry')
            return int(m[1]),text[:m.start()].rstrip()
        def ready(self):
            rc,held=self.command(self.lock+['held',SERIAL],10);need(rc==0,'lock read failed')
            rc,boot=self.raw_shell('cat /proc/sys/kernel/random/boot_id',15);need(rc==0,'boot read failed')
            guard(cfg,held,boot,time.time());self.boot=boot
    b.Board=Board
    board=Board(SERIAL,v['hdc'],str(repo/'scripts/lab/board_note.sh'),v['lane'],log/'commands');board.ready()
    validate_kit(v['kit'],sha)
    need(str(Path(v['kit'])/'manifest.json') in cfg['local_pins'] and str(Path(v['kit'])/'libinstalls.z.so') in cfg['local_pins'],'actual kit pins missing')
    hook=json.loads(Path(v['hook_config']).read_text())
    need(hook['expected_boot']==cfg['expected_boot'] and hook['window']==str(window) and hook['lane']==v['lane'],'G06 config stale')
    need(hook['approved_by']=='outer(codex)','G06 config unsigned')
    need(hook['source_pins']==v['source_pins'], 'G06 source pins mismatch')
    manifest=json.loads(Path(v['manifest']).read_text());entry=manifest['apps'][0]
    need(len(manifest['apps'])==1 and entry['package']=='com.miHoYo.Yuanshen' and entry['apk_sha256']==APK,'not exact Genshin manifest')
    app=b.resolve_input(Path(v['input_root']),entry);need(app['apk_sha256']==APK and app['input_sha256']==hook['input_sha256'],'input mismatch')
    def call_main(mod,argv):
        old=sys.argv;sys.argv=[str(mod.__file__)]+argv
        try:return mod.main()
        finally:sys.argv=old
    def original_hook(action):
        config_path=v['hook_config']
        if action=='restore':
            attempt_window=log/'g06-attempt';attempt_window.mkdir()
            shutil.copyfile(window/'g06-context.json',attempt_window/'g06-context.json')
            source=window/'shards/genshin'
            if source.exists():
                target=attempt_window/'shards/genshin';target.mkdir(parents=True)
                for name in ['record.json','bundle.txt']:
                    if (source/name).is_file():shutil.copyfile(source/name,target/name)
            attempt_cfg=dict(hook,window=str(attempt_window));config_path=str(log/'g06-restore-config.json');save(config_path,attempt_cfg)
        return call_main(g06,[action,'--config',config_path,'--execute'])
    def fingerprint(candidate=False):
        for kind,members in hook['fingerprints'].items():
            expected=dict(members)
            if candidate:
                for path in set(TARGETS)&expected.keys():expected[path]=CANDIDATE
            got={}
            for offset in range(0,len(expected),24):
                paths=list(expected)[offset:offset+24];_,out=board.shell('sha256sum '+' '.join(map(shlex.quote,paths)))
                for l in out.splitlines():
                    f=l.split();need(len(f)==2 and re.fullmatch('[0-9a-f]{64}',f[0]),'fingerprint row malformed');need(f[1] not in got,'duplicate fingerprint');got[f[1]]=f[0]
            need(got==expected,'fingerprint drift '+kind)
    def aliases(expected):
        _,mounts=board.shell('cat /proc/mounts');root=[l.split() for l in mounts.splitlines() if len(l.split())==6 and l.split()[1]=='/']
        need(len(root)==1 and 'ro' in root[0][3].split(','),'root not read-only')
        for row in map(str.split,mounts.splitlines()):
            if len(row)!=6 or row[1]=='/':continue
            need(not any(t==row[1] or t.startswith(row[1].rstrip('/')+'/') for t in TARGETS),'alias affected by nested mount')
        observed=[]
        for t in TARGETS:
            _,out=board.shell('test ! -L '+shlex.quote(t)+' && stat -c "%d:%i %u:%g %a %h %F" '+shlex.quote(t)+' && ls -ldZ '+shlex.quote(t)+' && sha256sum '+shlex.quote(t))
            lines=out.splitlines();need(re.fullmatch(r'\d+:\d+ 0:0 755 1 regular file',lines[0]) is not None,'alias topology/metadata')
            need('u:object_r:system_lib_file:s0' in lines[1] and lines[-1].split()==[expected,t],'alias SHA/label')
            observed.append(dict(path=t,identity=lines[0]))
        need(observed[0]['identity'].split()[0]!=observed[1]['identity'].split()[0],'aliases share inode')
        return observed
    def consumers():
        next_plan=json.loads((repo/'benchmark/2026-10-21-commercial-game/apk-extractor/window-prep/next-reads.json').read_text())
        command=next(x['argv'][-1] for x in next_plan['commands'] if x['id']=='all-process-maps')
        _,before=board.shell('ps -A -o PID,PPID,UID,NAME')
        _,text=board.shell(command,timeout=45);snap=maps_snapshot(text)
        _,after=board.shell('ps -A -o PID,PPID,UID,NAME');snap=close_maps(board,snap,before,after)
        save(log/('consumers-'+str(time.time_ns())+'.json'),snap);return snap
    def declaration():
        _,text=board.shell('cat /system/etc/init/installs.cfg');data=json.loads(text)
        s=[s for s in data['services'] if s['name']=='installs'];need(len(s)==1 and s[0]['ondemand'] is True and s[0].get('uid')=='installs' and s[0]['path']==['/system/bin/sa_main','/system/profile/installs.json'],'init declaration drift')
        _,text=board.shell('cat /system/profile/installs.json');profile=json.loads(text);sa=[s for s in profile['systemability'] if s['name']==511]
        need(profile['process']=='installs' and len(sa)==1 and sa[0]['libpath']=='libinstalls.z.so' and sa[0]['run-on-create'] is False and sa[0]['stop-on-demand']['longtimeunused-unload']==180,'SA511 declaration drift')
    def loaded(snap,expected):
        need(snap['hits'],'actual loaded object unobserved');declaration();_,passwd=board.shell('cat /system/etc/passwd');result=[];seen=set()
        for row in snap['hits']:
            key=(row['pid'],row['path'],row['dev'],row['inode'])
            if key in seen:continue
            seen.add(key)
            pid=row['pid'];path=row['path'];need(path in TARGETS and '(deleted)' not in path,'unexpected/deleted loaded path')
            _,a=board.shell(f'cat /proc/{pid}/stat');_,exe=board.shell(f'readlink /proc/{pid}/exe');_,cmd_hex=board.shell(f'od -An -v -tx1 /proc/{pid}/cmdline')
            _,status=board.shell(f'cat /proc/{pid}/status');role=loader_role(a,status,exe,cmd_hex,passwd)
            _,out=board.shell(f'sha256sum /proc/{pid}/root{path}; stat -L -c "%d:%i" /proc/{pid}/root{path}')
            lines=out.splitlines();need(lines[0].split()[0]==expected,'process-root SHA mismatch');dev,ino=map(int,lines[1].split(':'))
            major=((dev>>8)&0xfff)|((dev>>32)&0xfffff000);minor=(dev&0xff)|((dev>>12)&0xffffff00)
            need(int(row['dev'].split(':')[0],16)==major and int(row['dev'].split(':')[1],16)==minor and ino==row['inode'],'mapped dev/inode mismatch')
            _,status_after=board.shell(f'cat /proc/{pid}/status');_,exe_after=board.shell(f'readlink /proc/{pid}/exe')
            _,z=board.shell(f'cat /proc/{pid}/stat');need(identity(a)==identity(z)==snap['identities'][pid],'loader identity drift')
            need(loader_role(z,status_after,exe_after,cmd_hex,passwd)==role,'loader role drift')
            result.append(dict(pid=pid,path=path,sha256=expected,identity=identity(a)))
        return result
    def swap(action):
        mod=module('g13_swap',repo/'scripts/lab/swap_installer.py')
        return transact(action,board,mod,cfg,window,log,save,sha)
    if phase=='reconcile':
        board.shell('cat /proc/mounts');board.shell('ps -A -o PID,PPID,UID,NAME')
        for path in TARGETS:
            board.shell('ls -ldZ '+shlex.quote(path)+'; sha256sum '+shlex.quote(path),required=False)
            board.shell('ls -ldZ '+shlex.quote(path+'.g13-new'),required=False)
        consumers();save(log/'result.json',dict(status='READONLY_RECONCILE',pending_remote_writer='unknown until outer proves completion',device_writes=0))
    elif phase=='before':
        frozen=subprocess.run([sys.executable,str(repo/'scripts/lab/check_frozen.py'),'--git',str(repo)],capture_output=True)
        (log/'frozen.stdout').write_bytes(frozen.stdout);(log/'frozen.stderr').write_bytes(frozen.stderr);need(frozen.returncode==0,'freeze gate failed')
        declaration();fingerprint();observed=aliases(ORIGINAL);original_hook('before')
        for i,t in enumerate(TARGETS):board.receive(t,log/f'original-{i}.so');need(sha(log/f'original-{i}.so')==ORIGINAL,'host backup SHA')
        save(window/'g13-before.json',dict(aliases=observed,boot=cfg['expected_boot'],holder=v['holder']))
    elif phase=='apply':
        guard(cfg,v['holder'],board.boot,time.time(),True)
        before=json.loads((window/'g13-before.json').read_text());need(before['holder']==v['holder'] and before['boot']==board.boot,'before stale')
        for i in range(2):need(sha(window/'g13-before'/f'original-{i}.so')==ORIGINAL,'host backup missing/drift')
        need(aliases(ORIGINAL)==before['aliases'],'alias inode changed before apply');declaration();fingerprint()
        need(not consumers()['hits'],'live consumer before apply')
        swap('apply');aliases(CANDIDATE);fingerprint(True);save(window/'g13-applied.json',dict(applied=True))
    elif phase=='install':
        guard(cfg,v['holder'],board.boot,time.time(),True);need((window/'g13-applied.json').is_file(),'apply not verified');aliases(CANDIDATE);fingerprint(True)
        need('com.miHoYo.Yuanshen' not in g06.packages(*board.shell('bm dump -a')),'package already present; never reinstall')
        original_shell=board.shell
        def install_shell(command,required=True,timeout=60):
            if command.startswith('bm install -p '):
                need('com.miHoYo.Yuanshen' not in g06.packages(*original_shell('bm dump -a')),'package appeared before install')
                guard(cfg,v['holder'],board.boot,time.time(),True)
                rc,body=original_shell(command,required=False,timeout=timeout)
                save(log/'install-result.json',dict(rc=rc,body=body,success=b.bm_success(rc,body,'install')))
                try:
                    snap=consumers();verification=dict(status='observed',objects=loaded(snap,CANDIDATE))
                except (Refuse,b.AppFailure,b.BatchStop) as exc:verification=dict(status='unobserved-or-mismatch',reason=str(exc))
                save(log/'loader.json',verification)
                return rc,body
            return original_shell(command,required,timeout)
        board.shell=install_shell
        desktop=b.desktop_launch
        def conditional_launch(*args,**kwargs):
            review=v.get('control_review')
            need_review=bool(cfg.get('launch_enabled') and review and Path(review).is_file())
            if need_review:
                r=json.loads(Path(review).read_text());need_review=r.get('reviewer')=='outer(codex)' and r.get('actual_t20_lit') is True and r.get('boot_id')==board.boot and r.get('holder')==v['holder']
            loader=json.loads((log/'loader.json').read_text())
            if not need_review or loader['status']!='observed':raise b.AppFailure('G13_FIRST_LAUNCH_NOT_TESTED: control review or loaded-candidate missing')
            guard(cfg,v['holder'],board.boot,time.time(),True);fingerprint(True);return desktop(*args,**kwargs)
        b.desktop_launch=conditional_launch
        rec=b.collect_app(board,entry,Path(v['input_root']),window/'shards/genshin','/data/local/tmp/'+v['transaction']+'/genshin',60,reinstall=False,hilog_seconds=60,shots=[5,20,60],focus_check=True)
        if str(rec.get('error','')).startswith('G13_FIRST_LAUNCH_NOT_TESTED'):
            rec['status']='installed_launch_not_tested';save(window/'shards/genshin/record.json',rec)
        save(log/'result.json',rec)
    elif phase=='launch-only':
        guard(cfg,v['holder'],board.boot,time.time(),True)
        need(cfg.get('launch_enabled') is True,'first launch disabled')
        review=v.get('control_review');need(review and Path(review).is_file(),'control review missing')
        r=json.loads(Path(review).read_text());need(r.get('reviewer')=='outer(codex)' and r.get('actual_t20_lit') is True and r.get('boot_id')==board.boot and r.get('holder')==v['holder'],'control review not bound to window')
        original=json.loads((window/'shards/genshin/record.json').read_text());context=json.loads((window/'g06-context.json').read_text())
        _,bundle=board.shell('bm dump -n com.miHoYo.Yuanshen');uid=b.parse_bundle(bundle,'com.miHoYo.Yuanshen')['uid']
        g06.install_origin(original,context,uid)
        aliases(CANDIDATE);fingerprint(True)
        objects=loaded(consumers(),CANDIDATE);save(log/'loader.json',dict(status='observed',objects=objects))
        # A separate output leaves the successful installation origin and failed observer receipt intact.
        rec=b.collect_app(board,entry,Path(v['input_root']),log/'genshin','/data/local/tmp/'+v['transaction']+'/launch-only',60,reinstall=False,launch_only=True,hilog_seconds=60,shots=[5,20,60],focus_check=True)
        save(log/'result.json',rec)
    elif phase=='restore':
        statefile=window/'g13-transaction.json'
        if not statefile.is_file():
            # G06 before/control may have succeeded before apply admission refused.
            # No transaction means no G13 library writes were started: verify, do not infer.
            need((window/'g06-context.json').is_file(),'no before context for settings-only restore')
            aliases(ORIGINAL);fingerprint()
            declaration();snap=consumers()
            observed=loaded(snap,ORIGINAL) if snap['hits'] else []
            save(log/'loader-restored.json',dict(status='observed' if observed else 'unobserved-demand-idle',objects=observed))
            original_hook('restore');aliases(ORIGINAL);fingerprint()
            save(window/'g13-restored.json',dict(status='RESTORED_BEFORE_ONLY_SETTINGS',library_writes=0,loaded_original='observed' if observed else 'unobserved-demand-idle',game_success=False,unlock_performed=False))
            return
        unknown_resolved(json.loads(statefile.read_text()),cfg,statefile,sha)
        declaration();snap=consumers()
        if snap['hits']:
            # No implicit wait or stop. External serialized observation may run later within budget.
            need(cfg.get('restore_live_installs_action')=='stop-bound-installs','consumer still present; allow180s idle and re-observe or outer bind exact stop')
            loaded(snap,CANDIDATE)
            board.shell('begetctl stop_service installs')
            need(not consumers()['hits'],'consumer remains after exact service stop')
        swap('rollback');aliases(ORIGINAL);fingerprint()
        snap=consumers();observed=loaded(snap,ORIGINAL) if snap['hits'] else []
        save(log/'loader-restored.json',dict(status='observed' if observed else 'unobserved-demand-idle',objects=observed))
        original_hook('restore');aliases(ORIGINAL);fingerprint()
        save(window/'g13-restored.json',dict(status='RESTORED',loaded_original='observed' if observed else 'unobserved-demand-idle',game_success=False,unlock_performed=False))
