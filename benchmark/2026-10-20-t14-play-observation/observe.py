#!/usr/bin/env python3
"""T14 existing-process UI observation, explicit actions; default preview."""
import argparse, datetime, fcntl, hashlib, json, re, shlex, sys, time, uuid
from pathlib import Path
from framing import script as frame_script, decode

SERIAL = '5cd1e3dd00000000000000000923012c'
RUN = '/data/app/el2/100/base/org.westlake.imehost/files/a2hlab-source-c91d26bfb4db4fd5a002287011c4916d/run.sh'


def need(ok, reason):
    if not ok: raise ValueError(reason)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def profile(p):
    need(p['serial'] == SERIAL and re.fullmatch('[0-9a-f-]{36}', p['boot']), 'board/boot')
    need(p['run_path'] == RUN and re.fullmatch('[0-9a-f]{64}', p['run_sha256']), 'run')
    need(re.fullmatch('[0-9a-f]{64}', p['readonly_receipt_sha256']), 'readonly receipt')
    for role in ('parent','child','host'):
        x=p[role]
        need(all(type(x[k]) is int and x[k]>=0 for k in ('pid','ppid','birth','uid')) and x['pid']>1 and x['birth']>0,'process integers')
        need(re.fullmatch('[0-9a-f]{64}',x['exe_sha256']) and re.fullmatch(r'mnt:\[[0-9]+\]',x['mnt']),'exe/mnt')
    need(p['child']['ppid']==p['parent']['pid'] and p['child']['uid']==p['host']['uid']==20011300,'child ownership')
    need(p['parent']['mnt']==p['child']['mnt'] and p['parent']['mnt']!=p['init_mnt'],'private namespace')
    need(all(type(p[k]) is int and 0<p[k]<=8192 for k in ('width','height')),'display')
    return p


def guard(p):
    parts=[f'test "$(cat /proc/sys/kernel/random/boot_id)" = {shlex.quote(p["boot"])}']
    for role in ('parent','child','host'):
        x=p[role]; pid=x['pid']
        parts += [f'r=$(cat /proc/{pid}/stat); z=${{r##*) }}; set -- $z; test "$1" != Z; test "$1" != X; test "${{20}}" = {x["birth"]}; test "$2" = {x["ppid"]}',
                  f'u=$(sed -n "s/^Uid:[[:space:]]*//p" /proc/{pid}/status); set -- $u; test "$#" = 4; test "$1:$2:$3:$4" = {x["uid"]}:{x["uid"]}:{x["uid"]}:{x["uid"]}',
                  f'test "$(sed -n "s/^TracerPid:[[:space:]]*//p" /proc/{pid}/status)" = 0',
                  f'test "$(readlink /proc/{pid}/ns/mnt)" = {shlex.quote(x["mnt"])}',
                  f'e=$(sha256sum /proc/{pid}/exe); set -- $e; test "$1" = {x["exe_sha256"]}']
    parts += [f'e=$(sha256sum {shlex.quote(RUN)}); set -- $e; test "$1" = {p["run_sha256"]}',
              f'test "$(stat -L -c %d:%i {shlex.quote(RUN)})" = "$(stat -L -c %d:%i /proc/{p["parent"]["pid"]}/root/data/local/tmp/asx/run.sh)"']
    return '; '.join(parts)


def power(text):
    m=re.search(r'\bTimeout=(\d+)ms\s+OverrideTimeout=(\d+)ms',text)
    need(m is not None,'power dump'); return tuple(map(int,m.groups()))


def ui_command(kind, coords, p, reviewed, latest, used):
    need(kind not in used and reviewed==latest and re.fullmatch('[0-9a-f]{64}',reviewed or ''),'once/current screenshot')
    need(len(coords)==(4 if kind=='unlock' else 2),'coordinates')
    need(all(0<=v<(p['width'] if i%2==0 else p['height']) for i,v in enumerate(coords)),'coordinate range')
    return 'uitest uiInput '+('swipe ' if kind=='unlock' else 'click ')+' '.join(map(str,coords))


def main():
    ap=argparse.ArgumentParser(); ap.add_argument('action',choices=['begin','capture','ui','log-start','log-read','restore','probe'])
    for key in ('repo','profile','receipt','root'): ap.add_argument('--'+key,type=Path,required=True)
    ap.add_argument('--hdc'); ap.add_argument('--holder'); ap.add_argument('--start',type=float)
    ap.add_argument('--kind',choices=['unlock','front','tab','play']);ap.add_argument('--coords',type=int,nargs='+');ap.add_argument('--reviewed-sha');ap.add_argument('--execute',action='store_true');a=ap.parse_args()
    p=profile(json.loads(a.profile.read_text())); need(sha(a.receipt)==p['readonly_receipt_sha256'],'receipt pin')
    if not a.execute: print(json.dumps({'execute':False,'device_calls':0,'action':a.action,'serial':SERIAL}));return
    for rel,digest in json.loads(Path(__file__).with_name('source-pins.json').read_text()).items():
        need(sha(a.repo/rel)==digest,'reused source pin '+rel)
    need(a.hdc and a.holder and a.start is not None,'explicit execution inputs')
    need(abs(a.start-datetime.datetime.fromisoformat(a.holder.split()[2]).timestamp())<1,'holder timestamp')
    age=time.time()-a.start;need(0<=age<600,'window')
    deadline=time.monotonic()+600-age
    need(a.root.is_absolute() and not str(a.root).startswith(('/tmp/','/private/tmp/')),'persistent root')
    if a.action=='begin': a.root.mkdir(parents=True,exist_ok=False)
    need(a.root.is_dir() and not a.root.is_symlink(),'window root')
    with (a.root/'action.lock').open('a') as lf:
        fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
        statefile=a.root/'state.json'
        state=json.loads(statefile.read_text()) if statefile.exists() else {'profile_sha256':sha(a.profile),'holder':a.holder,'start':a.start,'used':[], 'power_original':None,'stopped':False,'remote':'/data/local/tmp/t14-'+uuid.uuid4().hex}
        state.setdefault('monotonic_deadline',deadline)
        deadline=min(deadline,state['monotonic_deadline'])
        need(state['profile_sha256']==sha(a.profile) and state['holder']==a.holder and state['start']==a.start,'state binding')
        need(a.action=='begin' or statefile.exists(),'begin required')
        need(not state['stopped'] or a.action=='restore','stopped window')
        sys.path.insert(0,str(a.repo/'benchmark/2026-09-28-bms-route-deploy/batch'));import bms_batch as b
        sys.path.insert(0,str(a.repo/'benchmark/2026-10-20-t12-medialoader-chain/log-delta'));import delta
        out=a.root/(f'{time.time_ns()}-'+a.action);out.mkdir(); restoring=a.action=='restore'
        def save(): b.save(statefile,state)
        class B(b.Board):
            def command(self,argv,timeout=60):
                left=deadline-time.monotonic()-(0 if restoring else 60)
                need(left>0,'deadline; restore only')
                try:return super().command(argv,min(timeout,left,10))
                except b.BatchStop as e:
                    cause=e.__cause__
                    if hasattr(cause,'stdout'):
                        stem=self.out/f'command-{self.index:05d}'
                        stem.with_suffix('.stdout.txt').write_bytes(cause.stdout or b'');stem.with_suffix('.stderr.txt').write_bytes(cause.stderr or b'')
                    raise
            def ready(self):
                super().ready();rc,held=self.command(self.lock+['held',SERIAL],10);need(rc==0 and held.strip()==a.holder,'exact holder')
            def shell(self,cmd,required=True,timeout=60):
                g=guard(p) if not restoring else 'true'
                return super().shell('(set -eu; '+g+'; '+cmd+'; '+g+')',required,timeout)
        board=B(SERIAL,a.hdc,'bash '+shlex.quote(str(a.repo/'scripts/lab/board_note.sh')),a.holder.split()[0],out/'commands');board.boot=p['boot']
        def read(cmd):return board.shell(cmd)[1]
        def awake():
            read('power-shell timeout -o 86400000');need(power(read('power-shell dump -s'))[1]==86400000,'awake readback')
        def restore():
            nonlocal restoring
            restoring=True
            if state['power_original']:
                read('power-shell timeout -o '+str(state['power_original'][1]));need(power(read('power-shell dump -s'))==tuple(state['power_original']),'restore mismatch')
            state['restored']=True;state['stopped']=True;state['recovery_required']=False;save()
        def shot():
            read('power-shell wakeup');got=b.capture(board,state['remote']+'/'+str(time.time_ns())+'.jpeg',out/'screen.jpeg');state['latest_shot']=got['sha256'];b.save(out/'screenshot.json',got);save()
        log='/data/service/el1/public/appspawnx/adapter_child_'+str(p['child']['pid'])+'.stderr'
        def logstat():
            need(read('readlink /proc/'+str(p['child']['pid'])+'/fd/2').strip()==log,'fd2 target')
            return delta.snapshot(log,read(delta.stat_body(log)),sha(a.profile))
        try:
            if a.action=='begin':
                need(0<=time.time()-p['observed_at']<=120,'fresh readonly profile');read('true');state['power_original']=power(read('power-shell dump -s'));save();awake();read('mkdir '+state['remote']);shot()
            elif a.action=='restore':restore()
            elif a.action=='capture':awake();shot();(out/'maps.txt').write_text(read('cat /proc/'+str(p['child']['pid'])+'/maps'));(out/'windows.txt').write_text(read("hidumper -s WindowManagerService -a '-a'"))
            elif a.action=='ui':
                need(a.kind is not None,'UI kind')
                cmd=ui_command(a.kind,a.coords or [],p,a.reviewed_sha,state.get('latest_shot'),state['used'])
                if a.kind in ('tab','play'):need(b.foreground(read("hidumper -s WindowManagerService -a '-a'"),[p['child']['pid'],p['host']['pid']])['confirmed'],'foreground')
                if a.kind=='play':need('log_before' in state,'log baseline before play')
                state['used'].append(a.kind);state['last_ui']={'command':cmd,'status':'unknown','screenshot':a.reviewed_sha};save()
                read(cmd);state['last_ui']['status']='completed';save();awake();shot()
            elif a.action=='log-start':
                need('log_before' not in state,'baseline once');state['log_before']=logstat().__dict__;save()
            elif a.action=='probe':
                read('printf "T14_STDOUT_probe\\n"; printf "T14_STDERR_probe\\n" >&2')
            elif a.action=='log-read':
                need('play' in state['used'] and not state.get('log_read_attempted'),'one post-play read');state['log_read_attempted']=True;save()
                before=delta.Snapshot(**state['log_before']);after=logstat();recipe=delta.read_recipe(before,after,guard(p),'DELTA_'+uuid.uuid4().hex,65536)
                tok=uuid.uuid4().hex;g=guard(p)+f'; test "$(stat -L -c %d:%i {log})" = {before.dev}:{before.inode}; test "$(stat -L -c %s {log})" -ge {after.size}'
                cmd=frame_script(log,before.size,recipe['selected_bytes'],tok,state['remote']+'/dd-diagnostic.txt',g)
                board.ready();rc,_=board.command(board.hdc+['-t',SERIAL,'shell',cmd],10)
                stem=board.out/f'command-{board.index:05d}';raw=stem.with_suffix('.stdout.txt').read_bytes();result=decode(raw,recipe['selected_bytes'],tok,rc);(out/'selected.raw').write_bytes(result.pop('payload'));result['recipe']=recipe;b.save(out/'delta-result.json',result);state['delta_status']=result['status'];save();need(result['status']=='BOUNDED_BYTES_COMPLETE','partial log frame')
        except Exception as e:
            if a.action=='log-read':state['delta_status']='PARTIAL_UNVERIFIED'
            state.update(stopped=True,error=str(e),recovery_required=bool(state['power_original']));save()
            try:restore();state['recovery_required']=False;save()
            except Exception as recovery:state['restore_error']=str(recovery);save()
            raise
        finally:save()
        print(json.dumps({'out':str(out),'action':a.action,'playback':'unknown','visual_verdict':'pending_review'}))


if __name__=='__main__':main()
