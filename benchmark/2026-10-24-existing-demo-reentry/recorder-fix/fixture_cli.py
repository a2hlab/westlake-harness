"""Offline full candidate CLI: synthetic ordinary I/O only, no HDC subprocess."""
import datetime
import hashlib
import json
import os
from pathlib import Path
import runpy
import subprocess
import sys
import time
import types
from review_wait import publish_once

HERE=Path(__file__).resolve().parent
RUN=Path(sys.argv[1]).resolve();MODE=sys.argv[2]
PLAN=json.loads((HERE.parent/'plan.json').read_text())
START=datetime.datetime.fromisoformat('2026-10-24T10:34:06.993177+08:00')
clock={'wallclock':START.isoformat(),'monotonic':0.0}
pre={'status':'P0_PASS','identity':{'bound':True},'power_preimage':{'base':30000,'override':10000}}
publish_once(RUN/'clock.json',clock);publish_once(RUN/'p0-result.json',pre)
initial=b'\xff\xd8'+b'L'*200;unlocked=b'\xff\xd8'+b'W'*200
calls=[];tick=0.0;released=False;inner_written=False;outer_written=False
lock={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'com.ohos.sceneboard','id':'ScreenLockRootComponent'}}
white={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'org.westlake.imehost'}}
desktop={'attributes':{'bounds':'[0,0][1200,1920]','bundleName':'com.ohos.sceneboard'},'children':[{'attributes':{'id':'SwiperPage_Grid_WorkSpace0'}},{'attributes':{'id':'AppIconCommonView_org.westlake.imehost.EntryAbility','bounds':'[100,200][200,300]','visible':True,'enabled':True,'clickable':True}}]}
def now():return tick
def wall():return (START+datetime.timedelta(seconds=tick)).isoformat()
def sleep(delay):
    global tick,inner_written,outer_written
    tick+=delay
    if tick>=20 and not inner_written:
        publish_once(RUN/'inner-unlock-review.json',{'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],'image_sha256':hashlib.sha256(initial).hexdigest(),'reviewer':'inner-codex','verdict':'clock_wallpaper_no_credentials'});inner_written=True
    if tick>=66.388396 and not outer_written and MODE!='absent':
        value={'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],'image':'unlocked.jpeg','image_sha256':hashlib.sha256(unlocked).hexdigest(),'initial_image_sha256':hashlib.sha256(unlocked).hexdigest(),'reviewer':'outer-codex','verdict':'host_white','timestamp':(START+datetime.timedelta(seconds=66.388396)).isoformat(),'elapsed':66.388396}
        if MODE=='invalid':value['boot']='wrong-boot'
        publish_once(RUN/'outer-review.json',value);outer_written=True

def call(label,cmd,deadline=120):
    global tick,released
    assert now()<deadline,('deadline',label,now(),deadline)
    tick+=.01
    calls.append({'label':label,'argv':cmd['argv'],'pid':os.getpid(),'at':tick})
    if label=='home' and MODE=='continuation_error':raise RuntimeError('synthetic Home error')
    r={'rc':0,'timeout':False,'argv':cmd['argv']}
    if label=='cleanup-final-held':r['rc']=1;return r,'',''
    if cmd['argv'][2:3]==['held']:return r,'codex-t123-ordinary-ui 123 fixture',''
    if label=='cleanup-unlock':released=True
    if label=='cleanup-power':return r,json.dumps(pre['power_preimage']),''
    if label in ('p2-2','post-layout-1','unlock-post-1') or label.endswith('-power'):return r,json.dumps({'base':30000,'override':600000}),''
    if label=='p2-3':(RUN/'initial-layout.json').write_text(json.dumps(lock))
    if label=='p2-5':(RUN/'initial.jpeg').write_bytes(initial)
    if label=='unlocked-layout':(RUN/'unlocked-layout.json').write_text(json.dumps(white))
    if label=='unlocked-shot':(RUN/'unlocked.jpeg').write_bytes(unlocked)
    if label=='page0-layout':(RUN/'page-0.json').write_text(json.dumps(desktop))
    if label.startswith('s') and label.endswith('-recv'):
        (RUN/(label.split('-')[0]+'.jpeg')).write_bytes(unlocked)
    if label.startswith('s') and label.endswith('-identity'):return r,PLAN['baseline_receipt']['boot']+'\nfixture ordinary process table',''
    return r,'ok',''

fake=types.ModuleType('receipt_candidate')
fake.__dict__.update(RUN=RUN,CTX={},PLAN=PLAN,Path=Path,json=json,time=types.SimpleNamespace(monotonic=now,sleep=sleep),wall=wall,call=call,good=lambda r,s,e:None,power=json.loads,identity=lambda s:pre['identity'],subprocess=subprocess)
sys.modules['receipt_candidate']=fake
sys.argv=[str(HERE/'initial_stage_candidate.py'),str(HERE.parent/'select_icon.py')]
runpy.run_path(str(HERE/'initial_stage_candidate.py'),run_name='__main__')
publish_once(RUN/'fixture-result.json',{'mode':MODE,'pid':os.getpid(),'calls':calls,'elapsed':tick,'device_calls':0,'released':released})
