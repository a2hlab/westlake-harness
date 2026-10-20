#!/usr/bin/env python3
"""Small local renderer checks. No shell execution; bash -n only parses generated text."""
import argparse,datetime,importlib.util,json,subprocess,tempfile,time
from pathlib import Path
import prepare as p

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--repo',type=Path,required=True);a=ap.parse_args();repo=a.repo.resolve()
    old=Path(__file__).resolve().parents[1]/'fixtures'
    origin=p.read(old/'historical-t30-plan.json');ad=p.read(old/'historical-t30-admission.json')
    checks=[]
    def reject(label,call):
        try:call()
        except (ValueError,TypeError,KeyError):checks.append(label);return
        raise AssertionError('accepted '+label)
    t=p.template(repo)
    assert all(t[k] is None for k in ('approved_by','signed_at','signed_at_epoch','created_at','retained'))
    checks.append('template_null_signature')
    with tempfile.TemporaryDirectory(prefix='t31-render-') as root:
        w=Path(root)/'t31-5cd-window-01';(w/'apply').mkdir(parents=True)
        now=time.time();start=int(now)-30;holder='inner(cx-seal) 99999 '+datetime.datetime.fromtimestamp(start,datetime.timezone.utc).isoformat()
        data=repo/p.DATA
        c={'repo':str(repo),'serial':p.SERIAL,'deploy':str(data),'start':start,'holder':holder,'data_pins':{'executor.py':p.sha(data/'executor.py')}}
        (w/'context.json').write_text(json.dumps(c))
        ad.update(holder=holder,window_start=start,deployment_scope='T31_5CD_DEMO_CANDIDATE',origin_window_id=w.name,t31_context_sha256=p.sha(w/'context.json'))
        (w/'scoped-admission.json').write_text(json.dumps(ad))
        origin.update(holder=holder,start=start,admission_sha256=p.sha(w/'scoped-admission.json'))
        (w/'apply/plan.json').write_text(json.dumps(origin))
        _,plan=p.validate(repo,w,now);checks.append('synthetic_current_origin_validates')
        reject('expired_window_rejected',lambda:p.validate(repo,w,start+1200))
        bad=dict(c,holder='inner(cx-seal) 99998 '+holder.split()[2]);(w/'context.json').write_text(json.dumps(bad))
        reject('context_plan_drift_rejected',lambda:p.validate(repo,w,now))
        (w/'context.json').write_text(json.dumps(c))
        args=(plan,'11111111-2222-4333-8444-555555555555',12345,67890,12346,67891,'mnt:[4026533005]')
        shell=p.render(*args)
        assert shell.count('_physical_before_sha=')==6 and shell.count('_private_after_sha=')==6
        assert 'T31_SIX_READ_COMPLETE' in shell and 'test "$he_before" = "$he_after"' in shell
        assert not any(x in shell for x in ('chmod ','chown ',' rm ',' cp ',' mv ','uitest ','timeout -o','param set','reboot'))
        result=subprocess.run(['bash','-n'],input=shell,text=True,capture_output=True)
        assert result.returncode==0,result.stderr;checks.append('six_states_readonly_shell_syntax')
        reject('missing_birth_rejected',lambda:p.render(plan,args[1],12345,None,12346,67891,args[-1]))
        reject('namespace_injection_rejected',lambda:p.render(*args[:-1],'mnt:[3]; reboot'))
    print(json.dumps({'checks':checks,'passed':len(checks),'device_calls':0,'bash_execution':'syntax-only -n, no generated commands run','identity':'SYNTHETIC_ONLY_NOT_BOARD_EVIDENCE'}))
if __name__=='__main__':main()
