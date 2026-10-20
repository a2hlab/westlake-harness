#!/usr/bin/env python3
"""Local preparation only; consumes fresh raw receipts, never calls a device."""
import argparse,json,time
from pathlib import Path
from recovery_core import fill,read_script
from recovery_policy import validate_origin,validate_window,require,sha,source_pins,PIN_KEYS,HERE

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='mode',required=True)
    r=s.add_parser('read-script');r.add_argument('--parent',type=int,required=True);r.add_argument('--host',type=int,required=True)
    f=s.add_parser('fill')
    for k in ('repo','origin-data','context','apply-plan','apply-admission','held-stdout','held-stderr','held-rc','read-stdout','read-stderr','read-rc','out'):f.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args()
    if a.mode=='read-script':print(read_script(a.parent,a.host),end='');return
    d=a.origin_data.resolve();plan,original=validate_origin(d,a.apply_plan,a.apply_admission)
    c=json.loads(a.context.read_text());now=time.time()
    for k in ('held','read'):
        require(getattr(a,k+'_rc').read_text().strip()=='0','raw host rc')
        require(not getattr(a,k+'_stderr').read_bytes(),'raw stderr')
        require(c['start']<=getattr(a,k+'_stdout').stat().st_mtime<=now+1,'raw freshness')
    ad,ids,budget=fill(a.repo,c,a.held_stdout.read_text(),a.read_stdout.read_text(),now,plan,original,d)
    for k in (*PIN_KEYS,'providers','cfg_sha256'):require(ad[k]==original[k],'origin/admission source drift '+k)
    ad.update(executor_sha256=sha(HERE/'recovery.py'),origin_apply_plan_sha256=sha(a.apply_plan),origin_apply_admission_sha256=sha(a.apply_admission),recovery_source_pins=source_pins(),recovery_no_parent=False,status='FRESH_T31_RECOVERY_ADMISSION_REMOTE_PREFLIGHT_REQUIRED')
    validate_window(ad,plan,c['holder'],c['start'],ad['boot'],now)
    a.out.mkdir(parents=True,exist_ok=False)
    for n,v in [('admission.json',ad),('budget.json',budget),('identity.json',dict(boot=ad['boot'],parent=ids['P'][0],parent_birth=ids['P'][2],host=ids['H'][0],host_birth=ids['H'][2])),('inputs.json',{k:sha(getattr(a,k)) for k in ('context','apply_plan','apply_admission','held_stdout','held_stderr','held_rc','read_stdout','read_stderr','read_rc')})]:
        (a.out/n).write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'status':'LOCAL_ONLY_REMOTE_PREFLIGHT_REQUIRED','device_calls':0,'out':str(a.out),**budget}))
if __name__=='__main__':main()
