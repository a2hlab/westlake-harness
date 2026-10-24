"""Run actual frozen start.main/P0/owner with synthetic command I/O; no device calls."""
import datetime,hashlib,importlib.util,json,os,runpy,sys,types
from pathlib import Path
from unittest.mock import patch
PACKAGE=Path(__file__).resolve().parent.parent/'launch-package-v4'
HOME=Path(sys.argv[1]).resolve();MODE=sys.argv[2]
HOME.mkdir(exist_ok=False)
sys.path.insert(0,str(PACKAGE))
import start
from review_wait import publish_once
START=datetime.datetime.fromisoformat('2026-10-24T12:00:00+08:00')
tick=0.0;calls=[];RUN=None;PLAN=None;locked=False;clicked=False;released=False
initial=b'\xff\xd8'+b'L'*200;unlocked=b'\xff\xd8'+b'W'*200
lock={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'com.ohos.sceneboard','id':'ScreenLockRootComponent'}}
white={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'org.westlake.imehost'}}
desktop={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'com.ohos.sceneboard'},'children':[{'attributes':{'id':'SwiperPage_Grid_WorkSpace0'}},{'attributes':{'id':'AppIconCommonView_org.westlake.imehost.EntryAbility','bounds':'[100,200][200,300]','visible':True,'enabled':True,'clickable':True}}]}
def now():return tick
def wall():return (START+datetime.timedelta(seconds=tick)).isoformat()
def sleep(delay):
    global tick
    tick+=delay
    if tick>=20 and (RUN/'initial-ready.json').exists() and not (RUN/'inner-unlock-review.json').exists():
        publish_once(RUN/'inner-unlock-review.json',{'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],'image_sha256':hashlib.sha256(initial).hexdigest(),'reviewer':'inner-codex','verdict':'clock_wallpaper_no_credentials'})
    if tick>=66.388396 and (RUN/'final-image-ready.json').exists() and not (RUN/'outer-review.json').exists() and MODE!='absent':
        review={'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],'image':'unlocked.jpeg','image_sha256':hashlib.sha256(unlocked).hexdigest(),'reviewer':'outer-codex','verdict':'usable_toutiao' if MODE=='usable' else 'host_white','timestamp':(START+datetime.timedelta(seconds=66.388396)).isoformat()}
        if MODE=='invalid':review['boot']='wrong-boot'
        publish_once(RUN/'outer-review.json',review)
    feed_label='s120' if MODE=='delayed_feed' else 's10'
    feed_ready=RUN/(feed_label+'-image-ready.json')
    feed_due=MODE=='feed' or (MODE=='delayed_feed' and (RUN/'s120-recv.json').exists() and tick>=json.loads((RUN/'s120-recv.json').read_text())['end_monotonic']+5)
    if feed_due and feed_ready.exists() and not (RUN/'feed-review.json').exists():
        pin=json.loads(feed_ready.read_text())
        publish_once(RUN/'feed-review.json',{'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],'image':feed_label+'.jpeg','image_sha256':pin['image_sha256'],'reviewer':'outer-codex','verdict':'feed','timestamp':wall()})
def identity_text():
    rows=[PLAN['baseline_receipt']['boot'],'PID PPID UID ARGS','4958 379 20011206 org.westlake.imehost','5129 1 0 appspawn-x']
    if clicked and MODE=='child':rows+=['7777 5129 20011206 com.ss.android.article.news']
    for pid,ppid,birth,name in [(4958,379,10879,'imehost'),(5129,1,11126,'appspawn-x')]:
        if clicked and MODE=='identity_change' and pid==4958:birth+=1
        fields=['S',str(ppid)]+['0']*17+[str(birth)]
        rows.append(str(pid)+' ('+name+') '+' '.join(fields))
    return '\n'.join(rows)+'\n'
def call(label,cmd,deadline=120):
    global tick,locked,clicked,released
    assert tick<deadline,(label,tick,deadline)
    args=[a.replace('$MAIN',CTX['main']).replace('$RUN_ID',RUN.name).replace('$RUN',str(RUN)) for a in cmd['argv']]
    before=tick;tick+=.01;rc=0;output='ok\n';error=''
    with (RUN/(label+'.reserved')).open('x') as f:f.write('offline fixture')
    if label=='00-held':rc=0 if MODE=='busy' else 1;output='other-lane 999 stamp\n' if rc==0 else ''
    elif label=='04-lock':locked=True
    elif label=='cleanup-final-held':rc=1;output=''
    elif args[2:3]==['held']:output='codex-t123-ordinary-ui 123 fixture\n'
    elif label=='cleanup-unlock':locked=False;released=True
    elif 'identity' in label or label=='01-identity':output=identity_text()
    elif label=='03-hashes':
        output=''.join(d+'  '+p+'\n' for p,d in PLAN['control_expected_sha256'].items())
        if MODE=='bad_hash':output='0'*64+output[64:]
    elif label=='02-power' or label=='cleanup-power':output='ScreenOffTime: Timeout=30000ms  OverrideTimeout=10000ms\n'
    elif label in ('p2-2','post-layout-1','unlock-post-1') or label.endswith('-power'):output='ScreenOffTime: Timeout=30000ms  OverrideTimeout=600000ms\n'
    elif label=='p2-3':(RUN/'initial-layout.json').write_text(json.dumps(lock))
    elif label=='p2-5':(RUN/'initial.jpeg').write_bytes(initial)
    elif label=='unlocked-layout-command':(RUN/'unlocked-layout.json').write_text(json.dumps(lock if MODE=='residual_lock' else white))
    elif label=='unlocked-shot':(RUN/'unlocked.jpeg').write_bytes(unlocked)
    elif label=='page0-layout':(RUN/'page-0.json').write_text(json.dumps(desktop))
    elif label=='click-once':clicked=True
    elif label.startswith('s') and label.endswith('-recv'):(RUN/(label.split('-')[0]+'.jpeg')).write_bytes(unlocked)
    elif label=='failure-home-once' and MODE=='failure_home_error':rc=1;error='synthetic Home failure\n'
    if label=='s120-state' and MODE=='reserve':tick=360.01
    rec={'argv':args,'rc':rc,'timeout':False,'start_wallclock':wall(),'end_wallclock':wall(),'start_monotonic':before,'end_monotonic':tick,'timeout_seconds':min(cmd['timeout_seconds'],deadline-before)}
    publish_once(RUN/(label+'.begin.json'),{'argv':args,'start_monotonic':before})
    (RUN/(label+'.stdout')).write_text(output);(RUN/(label+'.stderr')).write_text(error)
    publish_once(RUN/(label+'.json'),rec)
    calls.append({'label':label,'pid':os.getpid(),'at':tick,'rc':rc})
    return rec,output,error

real_verify=start.verify
home_patch=None
def fixture_verify(expected):
    global home_patch
    result=real_verify(expected)
    home_patch=patch.object(Path,'home',return_value=HOME);home_patch.start()
    return result
start.verify=fixture_verify

def fixture_payload(run):
    global RUN,PLAN,CTX
    RUN=run;CTX=json.loads((run/'context.json').read_text());PLAN=json.loads((run/'plan.json').read_text())
    sys.path.insert(0,str(run))
    spec=importlib.util.spec_from_file_location('receipt_candidate',run/'receipt_candidate.py');receipt=importlib.util.module_from_spec(spec);sys.modules['receipt_candidate']=receipt;spec.loader.exec_module(receipt)
    receipt.call=call;receipt.time=types.SimpleNamespace(monotonic=now,sleep=sleep);receipt.wall=wall
    # Identity, power, good(), and actual P0/P1-P6 code are not replaced.
    sys.argv=[str(run/'p0.py')];runpy.run_path(str(run/'p0.py'),run_name='__main__')
start.execute_payload=fixture_payload
try:rc=start.main(['--manifest-sha',hashlib.sha256((PACKAGE/'manifest.json').read_bytes()).hexdigest(),'--execute'])
finally:
    if home_patch:home_patch.stop()
publish_once(HOME/'fixture-result.json',{'mode':MODE,'pid':os.getpid(),'run':str(RUN),'calls':calls,'elapsed':tick,'device_calls':0,'released':released,'launcher_rc':rc})
