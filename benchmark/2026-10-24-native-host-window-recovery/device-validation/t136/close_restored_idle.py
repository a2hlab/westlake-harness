"""Named exact-object idle closure; no app launch, UI input, reboot or payload write."""
import argparse,json,re,time
from pathlib import Path
import execute_v7 as m
from recovery_roles import select_parent
P=Path(__file__).resolve().parent


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--outer-receipt',type=Path,required=True);args=ap.parse_args()
    plan_path=P/'restored-idle-plan.json';plan=json.loads(plan_path.read_text());approval=json.loads(args.outer_receipt.read_text())
    assert approval['decision']=='approve_restored_idle_exact_object' and approval['serial']==m.SERIAL
    assert approval['entry_sha256']==m.digest(Path(__file__)) and approval['plan_sha256']==m.digest(plan_path)
    for rel,sha in plan['pins'].items():assert m.digest(P/rel)==sha,rel
    m.save(P/'.private'/('used-idle-closure-'+m.digest(args.outer_receipt)+'.json'),{'receipt_sha256':m.digest(args.outer_receipt)})
    original=P/plan['original_run'];w=m.Window();w.recovery=True
    w.start=json.loads((P/plan['t0_command']).read_text())['start_monotonic']
    w.owner=(P/plan['owner_stdout']).read_text().strip();assert w.owner.startswith(m.LANE+' ')
    w.prepower=plan['power_preimage'];verified=False
    m.save(w.run/'approval.json',approval);m.save(w.run/'closure-plan.json',plan)
    def identity(label):
        raw=w.shell(label,'set -e; echo BOOT; cat /proc/sys/kernel/random/boot_id; echo UPTIME; cat /proc/uptime; ps -A -o PID,PPID,UID,NAME | while read p pp uid name; do case "$name" in org.westlake.imehost|com.ss.android.article.news*|appspawn-x) echo PROC:$p:$pp:$uid:$name; cat /proc/$p/stat;; esac; done')
        result=m.parse_identity(raw)
        assert not any(x['name'].startswith('com.ss.android.article.news') for x in result['processes']), 'article process present; idle closure prohibited'
        assert result['boot']==plan['restored_boot'] and result['boot']!=plan['original_boot'] and result['boot']!=plan['candidate_boot']
        return result
    def roles(ident):return {'boot':ident['boot'],'host':m.one(ident,'org.westlake.imehost'),'parent':select_parent(ident)}
    try:
        w.held();before=identity('idle-before');assert roles(before)==plan['expected_roles']
        target=w.object('idle-target',m.TARGET);assert target==plan['target_preimage']
        system=w.object('idle-system',m.SYSTEM);assert system==plan['system_preimage']
        power=w.power('power-before-closure')
        if any(power[k]!=w.prepower[k] for k in ('base','override')):
            assert power['base']==w.prepower['base'], 'base drift; no base mutation authorized'
            w.shell('power-restore','power-shell timeout -o '+str(w.prepower['override']))
        power=w.power('power-final');assert all(power[k]==w.prepower[k] for k in ('base','override'))
        # Snapshot the actual current screen, even if asleep; no wake, UITest, Home or touch.
        remote='/data/local/tmp/t136-'+w.run.name+'-final-idle.jpeg'
        w.shell('final-capture','snapshot_display -f '+m.q(remote))
        image=w.run/'final-idle.jpeg';w.call('final-recv',[m.HDC,'-t',m.SERIAL,'file','recv',remote,str(image)])
        assert image.is_file() and image.stat().st_size>0
        pic={'run':w.run.name,'label':'final-idle','image_sha256':m.digest(image),'path':str(image)}
        m.save(w.run/'final-idle.image.json',pic);print('IMAGE_READY '+json.dumps(pic),flush=True)
        time.sleep(1);after=identity('idle-after');assert roles(after)==roles(before)
        assert w.object('idle-target-final',m.TARGET)==target
        assert w.object('idle-system-final',m.SYSTEM)==system
        finalpower=w.power('power-after-snapshot');assert all(finalpower[k]==w.prepower[k] for k in ('base','override'))
        w.held()
        evidence={'status':'restored_idle_exact_object','mapping_now':'not_running','baseline_actual_mapping_verified':False,'identity_before':before,'identity':after,'object':target,'system':system,'power_final':finalpower,'final_image':pic,'historical_provenance':plan['historical_provenance'],'current_maps_claim':False,'application_health_claim':False,'candidate_pass':False}
        m.save(w.run/'restored-idle-evidence.json',evidence)
        w.call('unlock',['bash',str(m.NOTE),'unlock',str(m.BOARD),m.SERIAL,m.LANE]);r,out,err=w.call('final-held',['bash',str(m.NOTE),'held',m.SERIAL],True)
        assert r['local_rc']==1 and not out.strip() and not err.strip(),'unlock not established'
        evidence['released']=True;m.save(w.run/'restored-idle-binding.json',evidence)
        w.result.update(evidence);verified=True
    except BaseException as exc:
        w.result.update(status='recovery_required',error=str(exc),baseline_actual_mapping_verified=False)
    finally:
        if not verified:
            try:
                w.held();w.shell('power-restore-on-failure','power-shell timeout -o '+str(w.prepower['override']));power=w.power('power-final-on-failure');assert all(power[k]==w.prepower[k] for k in ('base','override'));w.result['power_final']=power
            except BaseException as exc:w.result['cleanup_error']=str(exc)
        w.result['elapsed_from_original_start']=w.elapsed();m.save(w.run/'result.json',w.result);print('DONE '+json.dumps(w.result),flush=True)
if __name__=='__main__':main()
