#!/usr/bin/env python3
"""T131 bounded ordinary UI observation. No payload/config/power changes."""
import datetime, hashlib, json, subprocess, sys, time, uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
REPO=ROOT.parents[1]
sys.path.insert(0,str(REPO/'scripts/lab'))
import lab_paths
MAIN=lab_paths.harness()
SERIAL='61b0657200000000000000000324012c'
HDC='/Applications/DevEco-Studio.app/Contents/sdk/default/openharmony/toolchains/hdc'
NOTE=MAIN/'scripts/lab/board_note.sh'
BOARD=MAIN/'.octos/boards/app-lighting.md'
LANE='codex-t131-ordinary-ui'
TARGET='/data/app/el2/100/base/org.westlake.imehost/haps/entry/files/window-state.json'
RUN=ROOT/'.private'/('run-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'-'+uuid.uuid4().hex[:6])
RUN.mkdir(parents=True)
PRIOR=Path(sys.argv[1]).resolve()
START=json.loads((PRIOR/'list/command.json').read_text())['start_monotonic']
if time.monotonic()>=START+480:raise RuntimeError('original budget insufficient for continuation')
owned=None;lock_attempt=False
facts={'original_t0_monotonic':START,'prior_run':str(PRIOR),'wake_count':0,'unlock_swipe_count':0,'home_count':0,'click_count':0,'images':[],'samples':[],'device_power_changes':0,'outcome':'pending'}
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,x):
    with p.open('x') as f:json.dump(x,f,indent=2);f.write('\n')
def call(label,argv,timeout=15):
    if time.monotonic()-START>570 and label not in ('unlock','final-held'):raise RuntimeError('hard cleanup reserve')
    d=RUN/label;d.mkdir();r={'argv':argv,'start_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'start_monotonic':time.monotonic(),'timeout_seconds':timeout};save(d/'command.json',r)
    with (d/'stdout').open('wb') as out,(d/'stderr').open('wb') as err:
        try:r['local_rc']=subprocess.run(argv,stdout=out,stderr=err,timeout=timeout).returncode
        except subprocess.TimeoutExpired:r['local_rc']=124
    r.update(end_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),end_monotonic=time.monotonic(),stdout_sha256=sha(d/'stdout'),stderr_sha256=sha(d/'stderr'));save(d/'receipt.json',r)
    return r,(d/'stdout').read_text(errors='replace'),(d/'stderr').read_text(errors='replace')
def ok(result):
    r,s,e=result
    if r['local_rc']!=0 or e.strip() or any(w in s for w in ['Connect server failed','[Fail]','Permission denied','not found']):raise RuntimeError('command failed: '+str(r['argv']))
    return s
def shell(label,s):return call(label,[HDC,'-t',SERIAL,'shell',s])
def held(label):
    r,s,e=call(label,['bash',str(NOTE),'held',SERIAL],10)
    if r['local_rc']!=0 or e.strip() or s.strip()!=owned:raise RuntimeError('self lock tuple lost')
def image(label):
    remote='/data/local/tmp/t131-'+RUN.name+'-'+label+'.jpeg';p=RUN/(label+'.jpeg')
    ok(shell(label+'-capture','snapshot_display -f '+remote));ok(call(label+'-recv',[HDC,'-t',SERIAL,'file','recv',remote,str(p)]))
    if not p.is_file() or p.stat().st_size==0:raise RuntimeError('no image bytes')
    x={'label':label,'path':str(p),'sha256':sha(p),'received_monotonic':time.monotonic()};facts['images'].append(x);print('IMAGE_READY '+json.dumps(x),flush=True);return x
def layout(label):
    remote='/data/local/tmp/t131-'+RUN.name+'-'+label+'.json';p=RUN/(label+'.json')
    ok(shell(label+'-capture','uitest dumpLayout -p '+remote));ok(call(label+'-recv',[HDC,'-t',SERIAL,'file','recv',remote,str(p)]));return p
IDENTITY="echo BOOT; cat /proc/sys/kernel/random/boot_id; echo UPTIME; cat /proc/uptime; echo PROCESSES; ps -A -o PID,PPID,UID,NAME | while read p pp uid name; do case \"$name\" in org.westlake.imehost|com.ss.android.article.news|appspawn-x) echo PROC:$p:$pp:$uid:$name; cat /proc/$p/stat;; esac; done; echo IDENTITY_END"
def identity(label):
    s=ok(shell(label,IDENTITY));ls=s.splitlines()
    if len(ls)<2 or ls[0]!='BOOT' or 'IDENTITY_END' not in ls:raise RuntimeError('incomplete identity')
    return ls[1]
def sample(label):
    script=IDENTITY+"; echo RECORD_STAT_BEFORE; stat -L -c '%d|%i|%u|%g|%a|%s|%Y' "+TARGET+"; echo HEX_BEGIN; od -An -v -tx1 -N8192 "+TARGET+"; echo HEX_END; echo RECORD_STAT_AFTER; stat -L -c '%d|%i|%u|%g|%a|%s|%Y' "+TARGET+"; echo BOOT_AFTER; cat /proc/sys/kernel/random/boot_id"
    r,s,e=shell(label,script);ok((r,s,e))
    if not s.startswith('BOOT\n'+boot+'\n') or s.splitlines()[-1]!=boot:raise RuntimeError('boot drift')
    if 'HEX_BEGIN\n' not in s or '\nHEX_END' not in s:raise RuntimeError('hex envelope incomplete')
    data=bytes.fromhex(s.split('HEX_BEGIN\n',1)[1].split('\nHEX_END',1)[0]);assert len(data)<=8192
    p=RUN/label/'record.bin';p.write_bytes(data)
    facts['samples'].append({'label':label,'start_monotonic':r['start_monotonic'],'end_monotonic':r['end_monotonic'],'record_bytes':len(data),'record_sha256':sha(p)})
def review(label,picture):
    deadline=min(START+480,time.monotonic()+75)
    print('REVIEW_NEEDED '+json.dumps({'label':label,'file':str(RUN/(label+'-review.json')),'image':picture}),flush=True)
    while time.monotonic()<deadline:
        p=RUN/(label+'-review.json')
        if p.exists():
            try:x=json.loads(p.read_text())
            except (OSError,ValueError):time.sleep(.2);continue
            if x.get('image_sha256')!=picture['sha256'] or x.get('run')!=RUN.name:raise RuntimeError('review binding mismatch')
            return x
        time.sleep(.2)
    raise RuntimeError('visual review deadline')
print('RUN '+str(RUN),flush=True)
save(RUN/'source.json',{'source':str(Path(__file__).resolve()),'sha256':sha(Path(__file__))})
try:
    targets=ok(call('list',[HDC,'list','targets']))
    if SERIAL not in targets.splitlines():raise RuntimeError('target missing')
    r,s,e=call('held-before',['bash',str(NOTE),'held',SERIAL],10)
    if r['local_rc']!=1 or s.strip() or e.strip():raise RuntimeError('existing lock/ambiguous held; do not acquire')
    boot=identity('identity-before');lock_attempt=True
    ok(call('lock',['bash',str(NOTE),'lock',str(BOARD),SERIAL,LANE,'T131 ordinary UI record observation max10min'],10))
    r,s,e=call('held-owned',['bash',str(NOTE),'held',SERIAL],10);ok((r,s,e));owned=s.strip()
    if not owned.startswith(LANE+' '):raise RuntimeError('wrong owner')
    facts.update(boot=boot,lock_tuple=owned,locked_monotonic=r['end_monotonic'])
    ok(shell('power-before',"hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"))
    held('held-before-wake');ok(shell('wake','power-shell wakeup'));facts['wake_count']=1
    initial=image('initial');layout('initial-layout');x=review('initial',initial)
    if x.get('verdict')=='clock_no_credentials':
        xy=x.get('swipe');assert isinstance(xy,list) and len(xy)==4 and all(type(v) is int and 0<=v<=3000 for v in xy)
        assert x.get('layout_sha256')==sha(RUN/'initial-layout.json')
        held('held-before-swipe');ok(shell('unlock-swipe','uitest uiInput swipe '+' '.join(map(str,xy))+' 600'));facts['unlock_swipe_count']=1
        time.sleep(1.5);unlocked=image('unlocked');layout('unlocked-layout');x=review('unlocked',unlocked)
    if x.get('verdict') in ('locked','credentials','unknown'):facts['outcome']='stopped_initial_'+x['verdict']
    elif x.get('verdict') in ('desktop','host_white','toutiao'):
        held('held-before-home')
        if identity('identity-before-home')!=boot:raise RuntimeError('boot changed')
        if x['verdict']!='desktop':
            ok(shell('home','uitest uiInput keyEvent Home'));facts['home_count']=1
        desktop=image('desktop');layout('desktop-layout');y=review('desktop',desktop)
        if y.get('verdict')!='desktop' or not isinstance(y.get('xy'),list) or len(y['xy'])!=2:raise RuntimeError('no confirmed desktop and unique actionable target')
        # Coordinates must come from an actually reviewed fresh layout, never historical coordinates.
        if y.get('layout_sha256')!=sha(RUN/'desktop-layout.json'):raise RuntimeError('layout review mismatch')
        xy=y['xy'];assert all(type(v) is int and 0<=v<=3000 for v in xy)
        held('held-before-click');sample('pre-click')
        click_start=time.monotonic();save(RUN/'click-reserved.json',{'xy':xy,'monotonic':click_start,'review':y})
        ok(shell('click-once','uitest uiInput click '+' '.join(map(str,xy))));facts['click_count']=1;facts['click_start_monotonic']=click_start
        print('CLICKED_ONCE '+json.dumps({'monotonic':click_start}),flush=True)
        for offset in [*range(16),30,60,90]:
            if time.monotonic()-click_start>=120:raise RuntimeError('observation120 deadline')
            while time.monotonic()<click_start+offset:time.sleep(min(.2,click_start+offset-time.monotonic()))
            sample('sample-'+str(offset))
            if offset in (5,15,30,60,90):image('s'+str(offset))
        facts['outcome']='sampled_once_visual_pending_review'
    else:raise RuntimeError('invalid initial visual verdict')
except BaseException as e:
    facts['outcome']='stopped';facts['error']=str(e);print('STOP '+repr(e),flush=True)
finally:
    # Never change power/screen settings or issue UI during cleanup.
    if owned:
        try:
            ok(shell('power-after',"hidumper -s PowerManagerService -a '-a' | grep -E 'ScreenOffTime|Current State'"))
            held('held-before-unlock');r,s,e=call('unlock',['bash',str(NOTE),'unlock',str(BOARD),SERIAL,LANE],10);facts['unlock_local_rc']=r['local_rc']
            r,s,e=call('final-held',['bash',str(NOTE),'held',SERIAL],10);facts['released']=r['local_rc']==1 and not s.strip() and not e.strip()
        except BaseException as e:facts['cleanup_error']=str(e)
    elif lock_attempt:facts['cleanup_error']='lock attempted but tuple not acquired; requires outer inspection, no foreign unlock'
    facts['ended_monotonic']=time.monotonic();save(RUN/'facts.json',facts);print('DONE '+json.dumps(facts),flush=True)
