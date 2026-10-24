from receipt_candidate import *
from review_wait import wait_for_review, publish_once
import sys
import hashlib
pre=json.loads((RUN/'p0-result.json').read_text());assert pre['status']=='P0_PASS'
clock=json.loads((RUN/'clock.json').read_text());owned=None;changed=False;lock_attempt=False
status={'stage':'START'}
def own(label):
    r,s,e=call(label,PLAN['phases'][1]['commands'][1],480);good(r,s,e)
    if s.strip()!=owned:raise RuntimeError('lock tuple changed')
def run_after_review():
    global status
    selector=Path(sys.argv[1])
    base=PLAN['phases'][2]['commands'][0]['argv'][:-1]
    def sh(text,cap=10):return {'argv':base+[text],'timeout_seconds':cap}
    def identity_gate(label):
        own(label+'-held');r,s,e=call(label+'-identity',PLAN['phases'][1]['commands'][2],180);good(r,s,e);assert identity(s)==pre['identity']
    def keep(label):
        r,s,e=call(label+'-override',sh('power-shell timeout -o 600000'),180);good(r,s,e)
        r,s,e=call(label+'-power',PLAN['phases'][2]['commands'][2],180);good(r,s,e);assert power(s)=={'base':pre['power_preimage']['base'],'override':600000}
    identity_gate('home');r,s,e=call('home',sh('uitest uiInput keyEvent Home'),180);good(r,s,e);keep('home')
    selected=None
    for page in range(12):
        assert time.monotonic()<clock['monotonic']+170
        identity_gate('page'+str(page))
        remote='/data/local/tmp/t123-'+RUN.name+'-page-'+str(page)+'.json';local=RUN/('page-'+str(page)+'.json')
        r,s,e=call('page'+str(page)+'-layout',sh('uitest dumpLayout -p '+remote,15),180);good(r,s,e)
        r,s,e=call('page'+str(page)+'-recv',{'argv':base[:3]+['file','recv',remote,str(local)],'timeout_seconds':15},180);good(r,s,e)
        parsed=json.loads(subprocess.check_output([sys.executable,str(selector),str(local)],text=True));publish_once(RUN/('page-'+str(page)+'-selection.json'),parsed);keep('page'+str(page))
        if parsed['credential_like_ids'] or parsed['lock_ids'] or not parsed['valid_desktop']:raise RuntimeError('not confirmed desktop layout')
        if len(parsed['target'])>1:raise RuntimeError('nonunique target')
        if parsed['target_actionable']:selected=parsed;break
        if parsed['target']:raise RuntimeError('target not actionable')
        if page==11:break
        identity_gate('swipe'+str(page));xy=parsed['page_swipe_next']
        r,s,e=call('swipe'+str(page),sh('uitest uiInput swipe '+' '.join(map(str,xy))+' 600'),180);good(r,s,e);keep('swipe'+str(page))
    if selected is None:raise RuntimeError('no unique actionable icon within bounded pages')
    identity_gate('click');assert time.monotonic()<clock['monotonic']+180
    clicktime=time.monotonic();publish_once(RUN/'single-click-reservation.json',{'at':wall(),'monotonic':clicktime,'xy':selected['target_center'],'page':page})
    r,s,e=call('click-once',sh('uitest uiInput click '+' '.join(map(str,selected['target_center']))),180);good(r,s,e);keep('click')
    print('CLICKED_ONCE '+json.dumps({'elapsed':clicktime-clock['monotonic'],'page':page}),flush=True)
    for offset in (10,30,60,90,120):
        while time.monotonic()<clicktime+offset:
            if (RUN/'feed-review.json').exists() or (RUN/'cleanup-now').exists():break
            time.sleep(min(.2,max(0,clicktime+offset-time.monotonic())))
        if (RUN/'feed-review.json').exists() or (RUN/'cleanup-now').exists():break
        own('s'+str(offset)+'-held');assert time.monotonic()<clock['monotonic']+360
        remote='/data/local/tmp/t123-'+RUN.name+'-s'+str(offset)+'.jpeg';local=RUN/('s'+str(offset)+'.jpeg')
        r,s,e=call('s'+str(offset)+'-shot',sh('snapshot_display -f '+remote,15),360);good(r,s,e)
        r,s,e=call('s'+str(offset)+'-recv',{'argv':base[:3]+['file','recv',remote,str(local)],'timeout_seconds':15},360);good(r,s,e)
        print('IMAGE_READY '+json.dumps({'path':str(local),'sha256':hashlib.sha256(local.read_bytes()).hexdigest(),'offset_actual':time.monotonic()-clicktime}),flush=True)
        r,s,e=call('s'+str(offset)+'-identity',PLAN['phases'][5]['commands_per_sample'][3],360);good(r,s,e);assert s.splitlines()[0]==PLAN['baseline_receipt']['boot']
        r,s,e=call('s'+str(offset)+'-state',PLAN['phases'][5]['commands_per_sample'][4],360);good(r,s,e)
    status={'stage':'SAMPLING_ENDED','feed_review_present':(RUN/'feed-review.json').exists(),'click_count':1,'home_count':1}
try:
    lock_attempt=True
    r,s,e=call('04-lock',PLAN['phases'][1]['commands'][0],90);good(r,s,e)
    r,s,e=call('05-held',PLAN['phases'][1]['commands'][1],90);good(r,s,e)
    fields=s.split();assert len(fields)==3 and fields[0]=='codex-t123-ordinary-ui' and fields[1].isdigit()
    owned=s.strip()
    with (RUN/'lock-tuple.txt').open('x') as lock_file:lock_file.write(owned+'\n')
    r,s,e=call('06-identity',PLAN['phases'][1]['commands'][2],90);good(r,s,e);assert identity(s)==pre['identity']
    commands=PLAN['phases'][2]['commands']
    for i,cmd in enumerate(commands):
        if i in (0,1,3):own('p2-held-'+str(i))
        if i==0:changed=True # wake or layout may alter override; always restore after attempted wake
        r,s,e=call('p2-'+str(i),cmd,90);good(r,s,e)
        if i==2:assert power(s)=={'base':pre['power_preimage']['base'],'override':600000}
        if i==4:
            layout=json.loads((RUN/'initial-layout.json').read_text());assert isinstance(layout,dict) and layout
            for j,post in enumerate(PLAN['phases'][2]['post_uitest']):
                if j==0:own('post-layout-held')
                r,s,e=call('post-layout-'+str(j),post,90);good(r,s,e)
                if j==1:assert power(s)=={'base':pre['power_preimage']['base'],'override':600000}
    image=RUN/'initial.jpeg';assert image.stat().st_size>100 and image.read_bytes()[:2]==b'\xff\xd8'
    status={'stage':'INITIAL_IMAGE_READY_PAUSED_NO_HOME_NO_CLICK','image':str(image),'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'T0':clock,'elapsed':time.monotonic()-clock['monotonic'],'review_remaining':clock['monotonic']+120-time.monotonic(),'total_remaining':clock['monotonic']+480-time.monotonic(),'lock_tuple':owned,'power_preimage':pre['power_preimage']}
    publish_once(RUN/'initial-ready.json',status);print(json.dumps(status),flush=True)
    # This owner completes unlock/capture before fixing the final image binding.
    selector=Path(sys.argv[1])
    layout=json.loads(subprocess.check_output([sys.executable,str(selector),str(RUN/'initial-layout.json')],text=True))
    if layout['credential_like_ids']:
        raise RuntimeError('credential controls: stop without unlock')
    final_image=RUN/'initial.jpeg'
    if layout['lock_ids']:
        inner=None
        while time.monotonic()<clock['monotonic']+90:
            if (RUN/'cleanup-now').exists():raise RuntimeError('explicit cleanup')
            try:
                r=json.loads((RUN/'inner-unlock-review.json').read_text())
                assert r['run_id']==RUN.name and r['serial']==PLAN['serial'] and r['boot']==PLAN['baseline_receipt']['boot']
                assert r['image_sha256']==status['image_sha256'] and r['verdict']=='clock_wallpaper_no_credentials'
                assert r['reviewer']=='inner-codex'
                inner=r;break
            except (FileNotFoundError,json.JSONDecodeError,KeyError,AssertionError,TypeError):
                time.sleep(min(.25,max(0,clock['monotonic']+90-time.monotonic())))
        if inner is None:raise RuntimeError('inner lockscreen review deadline')
        publish_once(RUN/'inner-review-consumed.json',{'review':inner,'observed_monotonic':time.monotonic()})
        own('unlock-held')
        r,t,e=call('unlock-identity',PLAN['phases'][1]['commands'][2],90);good(r,t,e);assert identity(t)==pre['identity']
        base=PLAN['phases'][2]['commands'][0]['argv'][:-1]
        def unlock_cmd(text,cap=10):return {'argv':base+[text],'timeout_seconds':cap}
        xy=layout['unlock_swipe']
        publish_once(RUN/'unlock-reservation.json',{'xy':xy,'at':wall()})
        r,t,e=call('unlock-once',unlock_cmd('uitest uiInput swipe '+' '.join(map(str,xy))+' 600'),90);good(r,t,e)
        remote='/data/local/tmp/t123-'+RUN.name+'-unlocked'
        r,t,e=call('unlocked-layout',unlock_cmd('uitest dumpLayout -p '+remote+'.json',15),90);good(r,t,e)
        r,t,e=call('unlocked-layout-recv',{'argv':base[:3]+['file','recv',remote+'.json',str(RUN/'unlocked-layout.json')],'timeout_seconds':15},90);good(r,t,e)
        unlocked=json.loads(subprocess.check_output([sys.executable,str(selector),str(RUN/'unlocked-layout.json')],text=True))
        if unlocked['credential_like_ids'] or unlocked['lock_ids']:raise RuntimeError('unlock not confirmed or credentials visible')
        for j,post in enumerate(PLAN['phases'][2]['post_uitest']):
            r,t,e=call('unlock-post-'+str(j),post,90);good(r,t,e)
            if j==1:assert power(t)=={'base':pre['power_preimage']['base'],'override':600000}
        r,t,e=call('unlocked-shot',unlock_cmd('snapshot_display -f '+remote+'.jpeg',15),90);good(r,t,e)
        final_image=RUN/'unlocked.jpeg'
        r,t,e=call('unlocked-image-recv',{'argv':base[:3]+['file','recv',remote+'.jpeg',str(final_image)],'timeout_seconds':15},90);good(r,t,e)
        assert final_image.stat().st_size>100 and final_image.read_bytes()[:2]==b'\xff\xd8'
    expected={'run_id':RUN.name,'serial':PLAN['serial'],'boot':PLAN['baseline_receipt']['boot'],
              'image':final_image.name,'image_sha256':hashlib.sha256(final_image.read_bytes()).hexdigest()}
    publish_once(RUN/'final-image-ready.json',dict(expected,elapsed=time.monotonic()-clock['monotonic']))
    print('FINAL_IMAGE_READY '+json.dumps(dict(expected,path=str(final_image),review_remaining=clock['monotonic']+120-time.monotonic())),flush=True)
    decision=wait_for_review(RUN,expected,clock,now=time.monotonic,sleep=time.sleep)
    if decision['decision']=='continue':
        run_after_review()
    else:
        status['stop_reason']=decision

except Exception as ex:
    status={'stage':'STOP','error':str(ex)};print(json.dumps(status),flush=True)
finally:
    cleanup={'power_changed_or_attempted':changed,'restored':not changed,'lock_released':False}
    try:
        if lock_attempt and owned is None:
            r,s,e=call('cleanup-held-after-lock-attempt',PLAN['phases'][1]['commands'][1],480)
            if r['rc']==0 and not e and s.split()[0]=='codex-t123-ordinary-ui':owned=s.strip()
        if owned:
            own('cleanup-held')
            if changed:
                cmd=PLAN['phases'][-1]['commands'][1]
                cmd={'argv':[a.replace('$PRE_OVERRIDE_MS',str(pre['power_preimage']['override'])) for a in cmd['argv']],'timeout_seconds':10}
                r,s,e=call('cleanup-restore',cmd,480);good(r,s,e)
                r,s,e=call('cleanup-power',PLAN['phases'][-1]['commands'][2],480);good(r,s,e)
                cleanup['power_after']=power(s);cleanup['restored']=power(s)==pre['power_preimage']
    except Exception as ex:cleanup['restore_error']=str(ex)
    finally:
        if owned:
            try:
                own('cleanup-before-unlock')
                r,s,e=call('cleanup-unlock',PLAN['phases'][-1]['commands'][3],480);good(r,s,e)
                r,s,e=call('cleanup-final-held',PLAN['phases'][-1]['commands'][4],480)
                cleanup['lock_released']=r['rc']==1 and not r['timeout'] and s=='' and e==''
            except Exception as ex:cleanup['unlock_error']=str(ex)
    status['cleanup']=cleanup;status['end_wallclock']=wall();status['elapsed']=time.monotonic()-clock['monotonic']
    publish_once(RUN/'owner-result.json',status);print(json.dumps(status),flush=True)
