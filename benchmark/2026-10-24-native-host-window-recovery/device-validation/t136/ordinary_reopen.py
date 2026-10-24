"""One ordinary baseline desktop reopen; no deployment, reboot or process control."""
import argparse,json,time,uuid
from pathlib import Path
import execute_v8 as m
P=Path(__file__).resolve().parent

class Observation(m.Window):
    def call(self,label,argv,allow_failure=False):
        if self.start is not None and self.elapsed()>=600:raise RuntimeError('ordinary600s deadline')
        return super().call(label,argv,allow_failure)
    def log(self,label,path,limit):
        token='ORDINARY_LOG_'+uuid.uuid4().hex
        script='( set -e; stat -L -c '+m.q('%d|%i|%u|%g|%a|%s|%Y')+' '+m.q(path)+'; head -c '+str(limit)+' '+m.q(path)+'; echo; stat -L -c '+m.q('%d|%i|%u|%g|%a|%s|%Y')+' '+m.q(path)+' ); r=$?; echo '+token+':$r'
        r,out,err=self.call(label,[m.HDC,'-t',m.SERIAL,'shell',script],True)
        # Log text is data: words such as "not found" inside a successful log are not transport failures.
        return r['local_rc']==0 and not err.strip() and out.rstrip().endswith(token+':0')
    def logs(self,label,boot):
        base='/data/westlake-demo/toutiao/recovery-attempts/icon-manual-20261021-r3/boots/'+boot
        return {name:self.log(label+'-'+name,path,limit) for name,path,limit in [
            ('parent','/data/local/tmp/a2hlab-app-c91d26bfb4db4fd5a002287011c4916d/parent.log',1048576),
            ('events',base+'/events.log',65536),('snapshot',base+'/snapshot.log',65536),
            ('window-record','/data/app/el2/100/base/org.westlake.imehost/haps/entry/files/window-state.json',8192)]}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outer-receipt',type=Path,required=True);a=ap.parse_args()
    plan=json.loads((P/'ordinary-reopen-plan.json').read_text());approval=json.loads(a.outer_receipt.read_text())
    assert approval['decision']=='approve_ordinary_reopen' and approval['serial']==m.SERIAL
    assert approval['entry_sha256']==m.digest(Path(__file__)) and approval['plan_sha256']==m.digest(P/'ordinary-reopen-plan.json')
    for rel,sha in plan['pins'].items():assert m.digest(P/rel)==sha,rel
    m.save(P/'.private'/('used-ordinary-'+m.digest(a.outer_receipt)+'.json'),{'receipt_sha256':m.digest(a.outer_receipt)})
    w=Observation();w.start=time.monotonic();w.recovery=True;w.published=None;w.prepower=None
    expected=json.loads((P/plan['preflight']).read_text());w.result={'task':'ordinary_baseline_reopen','candidate3291_validation':False,'device_commands':0,'status':'running','content_verified':False}
    m.save(w.run/'plan.json',plan);m.save(w.run/'approval.json',approval)
    try:
        r,out,err=w.call('held-before',['bash',str(m.NOTE),'held',m.SERIAL],True);assert r['local_rc']==1 and not out.strip() and not err.strip()
        before=w.identity('fresh-before');assert before==expected['identity'];assert w.object('baseline-before',m.TARGET)==expected['object'];assert w.object('system-before',m.SYSTEM)==expected['system']
        w.prepower=w.power('power-before');assert all(w.prepower[k]==expected['power'][k] for k in ('base','override'))
        w.call('lock',['bash',str(m.NOTE),'lock',str(m.BOARD),m.SERIAL,m.LANE,'ordinary baseline one desktop click max600s no deployment'])
        r,out,err=w.call('held-acquired',['bash',str(m.NOTE),'held',m.SERIAL]);w.owner=out.strip();assert w.owner.startswith(m.LANE+' ')
        w.held();assert w.identity('under-lock')==before;assert w.object('baseline-under-lock',m.TARGET)==expected['object']
        w.original=before;w.result['logs_before']=w.logs('before',before['boot'])
        # Existing desktop helper performs reviewed unlock/Home and fresh unique-icon selection.
        xy=w.desktop('ordinary-before',min(time.monotonic()+120,w.start+180))
        time.sleep(2);w.held();assert w.identity('immediate-preclick')['boot']==before['boot']
        w.ui('ordinary-icon-once','click '+' '.join(map(str,xy)));clicked=time.monotonic()
        schedule=iter((5,20,40,60));next_sample=next(schedule);last_poll=0;bound=None;pic=None;seen=[];ended=False
        while time.monotonic()<clicked+75 and w.elapsed()<480:
            now=time.monotonic()
            if now-clicked<=60 and now-last_poll>=1.5:
                last_poll=now;ident=w.identity('ordinary-presence-'+str(w.n));assert ident['boot']==before['boot'];main,desc=m.select_main(ident,True)
                seen.append({'at_seconds':time.monotonic()-clicked,'identity':ident})
                if main is None:bound=None
                elif bound is None or not m.same_process(main,m.select_main(bound)[0]):
                    try:bound,obj=w.bind('ordinary-binding-'+str(w.n),m.BASELINE)
                    except RuntimeError as exc:
                        if str(exc)!='main child baseline not mapped':raise
                        bound=None
                    else:assert obj==expected['object']
            if next_sample is not None and now>=clicked+next_sample:
                pic=w.screen('ordinary-s'+str(next_sample));w.logs('s'+str(next_sample),before['boot']);next_sample=next(schedule,None)
            if pic is not None:
                review=w.review(pic,min(clicked+75,w.start+480),False)
                if review and review['verdict']=='feed':
                    assert bound is not None,'feed without actual baseline mapping';assert review['touch_kind']=='swipe';xy=review['touch_coordinates'];w.coords(xy,4)
                    w.ui('ordinary-feed-swipe','swipe '+' '.join(map(str,xy))+' 600');swiped=w.screen('ordinary-swiped')
                    after=w.review(swiped,min(time.monotonic()+60,w.start+480));assert after['verdict']=='usable' and after['touch_kind']=='click';xy=after['touch_coordinates'];w.coords(xy,2)
                    w.ui('ordinary-content-click','click '+' '.join(map(str,xy)));content=w.screen('ordinary-content')
                    final=w.review(content,min(time.monotonic()+60,w.start+480));assert final['verdict']=='usable'
                    w.result['content_verified']=True;ended=True;break
            time.sleep(.2)
        w.result.update(status='observation_complete',feed_observed_and_verified=ended,identities=seen)
    except BaseException as exc:w.result.update(status='observation_stopped',error=str(exc))
    finally:
        if w.owner:
            try:
                w.held();w.result['final_identity']=w.identity('final-identity');w.result['logs_after']=w.logs('after',w.result['final_identity']['boot']);assert w.object('baseline-final',m.TARGET)==expected['object'];assert w.object('system-final',m.SYSTEM)==expected['system'];w.screen('ordinary-final')
            except BaseException as exc:w.result['final_evidence_error']=str(exc)
            try:
                w.held();w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']));power=w.power('power-final');assert all(power[k]==w.prepower[k] for k in ('base','override'));w.result['power_final']=power
                w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,out,err=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True);w.result['released']=r['local_rc']==1 and not out.strip() and not err.strip()
            except BaseException as exc:w.result['cleanup_error']=str(exc)
        w.result['elapsed_seconds']=w.elapsed();m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
if __name__=='__main__':main()
