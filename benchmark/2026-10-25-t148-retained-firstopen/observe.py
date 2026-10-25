#!/usr/bin/env python3
"""One software reboot and one icon activation of the retained candidate. No deployment/recovery."""
import importlib.util,json,time,datetime,uuid,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
REPO=next(p for p in HERE.parents if (p/'scripts/lab/lab_paths.py').is_file())
SOURCE=REPO/'benchmark/2026-10-24-native-host-window-recovery/demo-seal/reentry/execute_retain.py'
spec=importlib.util.spec_from_file_location('retained_ui',SOURCE);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
assert m.digest(SOURCE)=='be8336df180ee124d921a11d3a3f66cf5943c06dd303d2cf798a37cc85ad6e4d'
PROVENANCE=SOURCE.parent/'.private/execute-20261025-050733-e42601/second-closeout-binding.json'
assert m.digest(PROVENANCE)=='9a54d5dc4aab3dfb47d91e59e1fedd1130d8d67b7dace700088a99d1d24daeca'
m.HERE=HERE;m.LANE='t148-retained-firstopen'

class Observation(m.Window):
    def __init__(self):
        super().__init__();self.reboots=0;self.icons=0
    def call(self,label,argv,allow_failure=False,timeout=15):
        if self.start is not None and self.elapsed()>=900:raise RuntimeError('T148 900s hard deadline')
        if argv[0]==m.HDC:
            assert argv[1:3]==['-t',m.SERIAL] or argv==[m.HDC,'list','targets']
            assert not ('file' in argv and 'send' in argv),'no device payload upload'
            if argv[3:]==['target','boot']:
                assert self.reboots==0,'no second reboot';self.reboots+=1
        return super().call(label,argv,allow_failure,min(timeout,15))
    def ui(self,label,command):
        if label=='firstopen-icon-once':
            assert self.icons==0;self.icons+=1
        return super().ui(label,command)
    def ordinary_logs(self,ident):
        # Read only named normal startup output; no controller/config content.
        paths=[('window-record','/data/app/el2/100/base/org.westlake.imehost/haps/entry/files/window-state.json',8192)]
        seen={p['pid'] for row in self.result['identities'] for p in row['identity']['processes'] if p['name']==m.CHILD}
        for pid in sorted(seen):paths.append(('child-'+str(pid),f'/data/service/el1/public/appspawnx/adapter_child_{pid}.stderr',1048576))
        for name,path,limit in paths:
            token='T148_LOG_'+uuid.uuid4().hex
            script='( set -e; stat -L -c '+m.q('%d|%i|%u|%g|%a|%s|%Y')+' '+m.q(path)+'; tail -c '+str(limit)+' '+m.q(path)+'; echo; stat -L -c '+m.q('%d|%i|%u|%g|%a|%s|%Y')+' '+m.q(path)+' ); r=$?; echo '+token+':$r'
            r,s,e=self.call('ordinary-'+name,[m.HDC,'-t',m.SERIAL,'shell',script],True)
            self.result.setdefault('ordinary_logs',[]).append(dict(label=name,path=path,limit=limit,transport_rc=r['local_rc'],remote_ok=s.rstrip().endswith(token+':0'),stderr_empty=not e.strip()))

def main():
    w=Observation();w.start=time.monotonic();w.result.update(task='T148',software_reboot_not_power_cycle=True,candidate_redeployed=False,rollback=False,identities=[],frames=[],feed_observed=False,swipe_verified=False)
    m.save(w.run/'entry.json',dict(entry_sha256=m.digest(Path(__file__)),reuse_sha256=m.digest(SOURCE),provenance_sha256=m.digest(PROVENANCE)))
    print('T0 '+str(w.start),flush=True)
    try:
        r,s,e=w.call('held-before',['bash',str(m.NOTE),'held',m.SERIAL],True);assert r['local_rc']==1 and not s.strip() and not e.strip(),'another owner or lock query failure'
        w.call('devices',[m.HDC,'list','targets']);w.original=w.identity('preflight-identity')
        obj=w.object('preflight-candidate',m.TARGET);assert obj==json.loads(PROVENANCE.read_text())['object'];w.published=obj
        system=w.object('preflight-system',m.SYSTEM);assert system['sha256']==m.SYSTEM_SHA
        w.prepower=w.power('preflight-power');assert w.prepower['override'] is not None
        m.save(w.run/'preflight.json',dict(identity=w.original,object=obj,system=system,power=w.prepower))
        print('READ_ONLY_READY '+json.dumps(dict(boot=w.original['boot'],object=obj,power=w.prepower)),flush=True)
        w.call('lock',['bash',str(m.NOTE),'lock',str(m.BOARD),m.SERIAL,m.LANE,'T148 one software reboot/one icon; retain candidate; max900s'])
        r,s,e=w.call('held-acquired',['bash',str(m.NOTE),'held',m.SERIAL]);w.owner=s.strip();assert w.owner.startswith(m.LANE+' ')
        print('LOCK '+w.owner,flush=True);w.held();assert w.identity('locked-identity')==w.original;assert w.object('locked-candidate',m.TARGET)==obj
        boot=w.reboot('software-reboot');assert boot!=w.original['boot'];w.result['boot']=boot
        xy=w.desktop('firstopen-before',min(time.monotonic()+120,w.start+600));assert w.elapsed()<660
        w.held();assert w.identity('preclick-identity')['boot']==boot
        # Click's remote command return is recorded separately from the post-UITest power check.
        w.ui('firstopen-icon-once','click '+' '.join(map(str,xy)))
        rec=next(w.run.glob('*-firstopen-icon-once/receipt.json'));click=json.loads(rec.read_text());clicked=click['end_monotonic']
        w.result['click']=dict(receipt=str(rec.relative_to(w.run)),return_monotonic=clicked,return_utc=click['end_utc'],coordinates=xy)
        schedule=iter((5,30,60,90,120));nxt=next(schedule);pics=[];handled=set();last_identity=0;feed=None
        while time.monotonic()<clicked+180:
            now=time.monotonic()
            if nxt is not None and now>=clicked+nxt:
                label='firstopen-s'+str(nxt);ident=w.identity(label+'-identity');assert ident['boot']==boot
                w.result['identities'].append(dict(seconds=time.monotonic()-clicked,identity=ident));last_identity=time.monotonic()
                began=time.monotonic();pic=w.screen(label);pics.append(pic)
                w.result['frames'].append(dict(label=label,scheduled_seconds=nxt,start_seconds=began-clicked,ready_seconds=time.monotonic()-clicked,**{k:v for k,v in pic.items() if k!='label'}));nxt=next(schedule,None)
            elif now<clicked+120 and now-last_identity>=5:
                ident=w.identity('presence-'+str(w.n));assert ident['boot']==boot;last_identity=time.monotonic();w.result['identities'].append(dict(seconds=last_identity-clicked,identity=ident))
            for pic in pics:
                if pic['label'] in handled:continue
                review=w.review(pic,clicked+180,False,context='stage',allowed_touch=('swipe',))
                if review:
                    handled.add(pic['label'])
                    if review['verdict']=='feed':feed=(pic,review);break
            if feed:break
            if nxt is None and len(handled)==len(pics):break
            time.sleep(.2)
        if feed:
            pic,review=feed;w.result['feed_observed']=True;w.result['feed_frame']=pic
            bound,bobj=w.bind('feed-mapping',m.CANDIDATE);assert bobj==obj
            assert w.elapsed()<780;w.ui('feed-swipe-once','swipe '+' '.join(map(str,review['touch_coordinates']))+' 600')
            after,identity,frames=w.observe_content('feed-swipe',bound,min(time.monotonic()+60,w.start+840))
            w.result.update(swipe_verified=True,content_frames=frames,status='firstopen_feed_and_swipe_verified')
        else:w.result['status']='firstopen_no_feed_within_sample_window' if len(handled)==len(pics) else 'firstopen_visual_review_incomplete'
    except BaseException as exc:
        w.result.update(status='observation_stopped',error=str(exc));print('STOP '+repr(exc),flush=True)
    finally:
        if w.owner:
            try:
                w.held();ident=w.identity('final-identity');w.result['final_identity']=ident
                assert w.object('candidate-final',m.TARGET)==w.published;w.result['candidate_unchanged']=True
                assert w.object('system-final',m.SYSTEM)==system
                if not w.result['swipe_verified']:w.ordinary_logs(ident)
            except BaseException as exc:w.result['final_evidence_error']=str(exc)
            try:
                w.held();w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']));p=w.power('power-final');assert all(p[k]==w.prepower[k] for k in ('base','override'));w.result.update(power_restored=True,power_final=p)
                w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,s,e=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True);w.result['released']=r['local_rc']==1 and not s.strip() and not e.strip()
            except BaseException as exc:w.result['cleanup_error']=str(exc)
        w.result.update(elapsed_seconds=w.elapsed(),software_reboot_count=w.reboots,icon_attempt_count=w.icons)
        m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
if __name__=='__main__':main()
