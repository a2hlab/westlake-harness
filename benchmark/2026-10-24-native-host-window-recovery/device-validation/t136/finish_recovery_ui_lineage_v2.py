#!/usr/bin/env python3
"""T136 authorized recovery continuation: no payload write and no reboot."""
import importlib.util,json,re,sys,time
from pathlib import Path
P=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('t136_entry',P/'execute_v6.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
old=Path(sys.argv[1]).resolve()
assert json.loads((old/'result.json').read_text())['rollback']=='recovery_required'
old_receipts={p.parent.name.split('-',1)[1]:p.parent for p in old.glob('*/receipt.json')}
assert 'atomic-rollback' in old_receipts and 'rollback-reboot' in old_receipts
assert json.loads((old_receipts['atomic-rollback']/'receipt.json').read_text())['local_rc']==0
assert m.BASELINE in (old_receipts['rollback-disk']/'stdout').read_text()
from recovery_lineage import RecoveryWindow, select_main
w=RecoveryWindow();w.recovery=True
w.start=json.loads((old_receipts['held-before']/'command.json').read_text())['start_monotonic']
w.owner=(old_receipts['held-acquired']/'stdout').read_text().strip();assert w.owner.startswith(m.LANE+' ')
power=(old_receipts['power-before']/'stdout').read_text();b=re.search(r'Timeout=(\d+)ms',power);o=re.search(r'OverrideTimeout=(\d+)ms',power);assert b and o
w.prepower=dict(base=int(b.group(1)),override=int(o.group(1)))
sources=[old/name for name in ('fresh-binding.json','fresh-idle-admission.json') if (old/name).is_file()]
assert len(sources)==1, 'require exactly one authoritative preimage binding'
original_binding=json.loads(sources[0].read_text())
w.original=original_binding['identity']
expected=original_binding['object']
m.save(w.run/'continuation.json',{'original_run':old.name,'original_budget_start_monotonic':w.start,'scope':'service readiness, baseline ordinary UI/mapping, original power and own unlock only','entry_sha256':m.digest(P/'execute_v6.py'),'continuation_source_sha256':m.digest(Path(__file__)), 'lineage_source_sha256':m.digest(P/'recovery_lineage.py'), 'additional_recovery_click_authorized':1})
verified=False
try:
    w.held();until=min(time.monotonic()+120,w.start+1600)
    previous=m.parse_identity((old_receipts['rollback-reboot-before']/'stdout').read_text())['boot']
    # Source: scripts/lab/demo_seal_61b.py wait_boot, plus actual parseable UITest layout.
    while time.monotonic()<until-45:
        r,out,err=w.call('boot-completion-readiness',[m.HDC,'-t',m.SERIAL,'shell','cat /proc/sys/kernel/random/boot_id; param get bootevent.boot.completed'],True)
        lines=out.strip().splitlines()
        if r['local_rc']==0 and not err.strip() and len(lines)==2 and re.fullmatch(r'[0-9a-f-]{36}',lines[0]) and lines[0]!=previous and lines[1]=='true':
            assert lines[0]!=w.original['boot'], 'recovery must have new boot'
            w.keepawake('recovery-readiness-boot-ui')
            remote='/data/local/tmp/t136-'+w.run.name+'-ready-'+str(w.n)+'.json'
            rr,output,error=w.call('layout-readiness',[m.HDC,'-t',m.SERIAL,'shell','uitest dumpLayout -p '+m.q(remote)+'; r=$?; echo T136_UI_RC:$r'],True)
            if rr['local_rc']==0 and not error.strip() and output.rstrip().endswith('T136_UI_RC:0'):
                local=w.run/('readiness-layout-'+str(w.n)+'.json')
                fr,fo,fe=w.call('layout-readiness-recv',[m.HDC,'-t',m.SERIAL,'file','recv',remote,str(local)],True)
                if fr['local_rc']==0 and not fe.strip() and '[Fail]' not in fo and local.is_file():
                    try:parsed=json.loads(local.read_text())
                    except (OSError,ValueError):parsed=None
                    if isinstance(parsed,dict) and parsed:break
        time.sleep(2)
    else:raise RuntimeError('newboot/boot.completed/parseable layout not ready in bounded120s')
    assert w.object('baseline-disk-before',m.TARGET)==expected
    pic=w.screen('recovery-current')
    for review_step in range(4):
        r=w.review(pic,min(time.monotonic()+120,w.start+1600))
        verdict=r['verdict']
        if verdict=='clock_no_credentials':
            xy=r['swipe'];w.coords(xy,4);w.ui('ordinary-unlock','swipe '+' '.join(map(str,xy))+' 600');time.sleep(1.5);pic=w.screen('recovery-unlocked')
        elif verdict=='usb_dialog':
            # Current authorized dialog: preserve selected charge-only option; confirm only.
            xy=r.get('xy',[600,1183]);w.coords(xy,2)
            w.ui('charge-only-confirm','click '+' '.join(map(str,xy)));pic=w.screen('recovery-desktop')
        elif verdict in ('host_white','feed'):
            w.ui('ordinary-home','keyEvent Home');pic=w.screen('recovery-after-home')
        elif verdict=='desktop':break
        else:raise RuntimeError('unknown or credential screen; no interaction')
    else:raise RuntimeError('no desktop after bounded ordinary confirmations')
    for page in range(12):
        tree=json.loads((w.run/(pic['label']+'.layout.json')).read_text());matches=[];workspace=[]
        def walk(n,launcher=False,visible=True):
            at=n.get('attributes',{})
            if at.get('bundleName'):launcher=at['bundleName']=='com.ohos.sceneboard'
            visible=visible and at.get('visible') not in (False,'false') and at.get('enabled') not in (False,'false')
            if str(at.get('id','')).startswith('SwiperPage_Grid_WorkSpace') and launcher and visible:workspace.append(at)
            if at.get('id')=='AppIconCommonView_org.westlake.imehost.EntryAbility' and launcher and visible and all(at.get(k)=='true' for k in ('clickable','visible','enabled')):matches.append(at)
            for child in n.get('children',[]):walk(child,launcher,visible)
        walk(tree)
        bounds=list(map(int,re.findall(r'\d+',tree['attributes']['bounds'])));assert len(bounds)==4
        if len(matches)==1:
            v=list(map(int,re.findall(r'\d+',matches[0]['bounds'])));assert len(v)==4 and bounds[0]<=v[0]<v[2]<=bounds[2] and bounds[1]<=v[1]<v[3]<=bounds[3]
            print('TARGET_READY '+json.dumps(dict(pic,page=page)),flush=True)
            reviewed=w.review(pic,min(time.monotonic()+120,w.start+1600))
            if reviewed['verdict']!='desktop':raise RuntimeError('target image not confirmed desktop')
            xy=[(v[0]+v[2])//2,(v[1]+v[3])//2];w.ui('baseline-icon-once','click '+' '.join(map(str,xy)));break
        if len(matches)>1 or not workspace or page==11:raise RuntimeError('no unique visible target in bounded desktop pages')
        x1,y1,x2,y2=bounds;xy=[x1+(x2-x1)*4//5,(y1+y2)//2,x1+(x2-x1)//5,(y1+y2)//2]
        w.ui('page-next-'+str(page),'swipe '+' '.join(map(str,xy))+' 600');time.sleep(.5);pic=w.screen('desktop-page-'+str(page+1))
    began=time.monotonic();identity=None
    for seconds in (5,30,60,90):
        while time.monotonic()<began+seconds:time.sleep(.2)
        current=w.identity('baseline-s'+str(seconds)+'-identity')
        children=[c for c in current['processes'] if c['name']=='com.ss.android.article.news']
        if children:
            identity,obj=w.bind('baseline-s'+str(seconds),m.BASELINE)
            assert identity['boot']!=w.original['boot'], 'recovery must have new boot'
            w.screen('baseline-s'+str(seconds));break
        w.screen('baseline-s'+str(seconds))
    if identity is None:raise RuntimeError('no actual baseline child mapping within observation')
    assert w.object('baseline-disk-after',m.TARGET)==expected
    system=w.object('system-final',m.SYSTEM)
    assert system['sha256']==m.SYSTEM_SHA
    w.screen('final-recovery');verified=True
    w.result.update(status='baseline_mapping_verified',baseline_actual_mapping_verified=True,identity=identity)
except BaseException as e:w.result.update(status='recovery_required',error=str(e));print('RECOVERY_STOP '+str(e),flush=True)
finally:
    try:
        w.held();w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']));post=w.power('power-final');assert all(post[k]==w.prepower[k] for k in ('base','override'));w.result['power_final']=post
        if verified:
            w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,s,e=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True);w.result['released']=r['local_rc']==1 and not s.strip() and not e.strip()
    except BaseException as e:w.result['cleanup_error']=str(e)
    w.result['additional_recovery_icon_commands_rc0']=sum(json.loads(f.read_text())['local_rc']==0 for f in w.run.glob('*-baseline-icon-once/receipt.json'));w.result['elapsed_from_original_start']=w.elapsed();m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
