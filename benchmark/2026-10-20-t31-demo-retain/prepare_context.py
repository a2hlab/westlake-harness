#!/usr/bin/env python3
"""Persist a NEW local context from root's actual held receipt. No lock/device call."""
import argparse,datetime,json,re,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'recovery'))
from recovery_policy import require,data_check,sha,SERIAL

def main():
    p=argparse.ArgumentParser()
    for k in ('repo','origin-data','held-stdout','held-stderr','held-rc','out'):p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--hdc',required=True);p.add_argument('--recovery',action='store_true');a=p.parse_args()
    require(a.held_rc.read_text().strip()=='0' and not a.held_stderr.read_bytes(),'actual held rc/stderr')
    holder=a.held_stdout.read_text().strip();t=holder.split();require(len(t)==3 and t[0]=='inner(cx-seal)' and t[1].isdigit(),'holder')
    start=datetime.datetime.fromisoformat(t[2]).timestamp();now=time.time();limit=1800 if a.recovery else 1200
    require(0<=now-start<limit,'new window budget');require(start<=a.held_stdout.stat().st_mtime<=now+1,'held freshness')
    pattern=r't31-recovery-window-[0-9]+' if a.recovery else r't31-5cd-window-[0-9]+'
    require(re.fullmatch(pattern,a.out.name) and not a.out.exists(),'unique new window root')
    require(a.repo.resolve().name=='westlake-harness','MAIN repository')
    pins=data_check(a.origin_data)
    c=dict(repo=str(a.repo.resolve()),deploy=str(a.origin_data.resolve()),serial=SERIAL,hdc=a.hdc,holder=holder,start=start,purpose='T31_DURABLE_RECOVERY' if a.recovery else 'T31_FINAL_ACCEPTANCE',data_pins=pins,held_receipt_sha256=sha(a.held_stdout),device_calls=0)
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'context.json').write_text(json.dumps(c,indent=2)+'\n')
    print(json.dumps({'status':'LOCAL_CONTEXT_FROM_ROOT_HELD','window':str(a.out),'holder':holder,'start':start,'device_calls':0}))
if __name__=='__main__':main()
