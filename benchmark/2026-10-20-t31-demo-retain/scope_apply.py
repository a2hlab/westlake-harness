#!/usr/bin/env python3
"""Local T31 scope binding AFTER the frozen fresh filler; before actual apply."""
import argparse,json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'recovery'))
from recovery_policy import require,data_check,sha,PIN_KEYS,SERIAL

def main():
    p=argparse.ArgumentParser()
    for k in ('context','fresh-admission','origin-data','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();c=json.loads(a.context.read_text());ad=json.loads(a.fresh_admission.read_text());data_check(a.origin_data)
    w=a.context.parent;require(re.fullmatch(r't31-5cd-window-[0-9]+',w.name),'new T31 window')
    require(c['serial']==ad['serial']==SERIAL and c['holder']==ad['holder'] and c['start']==ad['window_start'],'actual fresh context')
    require(0<=time.time()-c['start']<1200,'candidate budget')
    require(a.fresh_admission.stat().st_mtime>=c['start'],'fresh admission predates lock')
    require(Path(c['deploy']).resolve()==a.origin_data.resolve(),'deployment data')
    for k,n in PIN_KEYS.items():require(ad[k]==sha(a.origin_data/n),'source drift '+k)
    require(ad['status']=='FRESH_LOCAL_ADMISSION_EXECUTOR_PREFLIGHT_REQUIRED' and ad['fresh_three_slot_receipt_sha256'] is None,'fresh filler output')
    ad.update(deployment_scope='T31_5CD_DEMO_CANDIDATE',origin_window_id=w.name,t31_context_sha256=sha(a.context),fresh_filler_admission_sha256=sha(a.fresh_admission))
    with a.out.open('x') as f:json.dump(ad,f,indent=2);f.write('\n')
    print(json.dumps({'status':'LOCAL_SCOPE_ONLY_EXECUTOR_PREFLIGHT_REQUIRED','device_calls':0,'sha256':sha(a.out)}))
if __name__=='__main__':main()
