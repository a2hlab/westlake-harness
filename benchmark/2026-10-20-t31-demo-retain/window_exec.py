#!/usr/bin/env python3
"""T31 root-channel command wrapper. Preview by default; does not launch UI/reboot."""
import argparse,hashlib,json,subprocess,sys,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'recovery'))
from recovery_policy import require,data_check,sha,SERIAL

def command(mode,c,w,adfile,identity,out,origin_plan=None,origin_admission=None):
    d=Path(c['deploy']);data_check(d);ad=json.loads(adfile.read_text());ids=json.loads(identity.read_text());now=time.time()
    require(c['serial']==SERIAL and c['holder']==ad['holder'] and c['start']==ad['window_start'] and ids['boot']==ad['boot'],'current scope')
    require(0<=now-c['start']<(1200 if mode in ('preflight','apply') else 1800),'window cutoff')
    require(not out.exists() and out.parent.resolve()==w.resolve(),'unique output within window')
    if mode in ('preflight','apply'):
        require(ad.get('deployment_scope')=='T31_5CD_DEMO_CANDIDATE' and ad['origin_window_id']==w.name,'SCOPED apply admission required')
        exe=d/'executor.py';em=mode
    elif mode=='same-window-rollback':
        require(origin_plan and sha(origin_plan)==ad['origin_apply_plan_sha256'],'origin plan')
        op=json.loads(origin_plan.read_text());require(op['holder']==c['holder'] and op['start']==c['start'],'same window')
        exe=d/'executor.py';em='rollback'
    else:
        require(mode=='durable-recovery' and origin_plan and origin_admission,'durable inputs')
        require(c['purpose']=='T31_DURABLE_RECOVERY','recovery purpose');exe=Path(__file__).resolve().parent/'recovery/recovery.py';em='rollback'
    require(ad['executor_sha256']==sha(exe),'actual executor admission')
    argv=[sys.executable,str(exe),em,'--execute','--repo',c['repo'],'--inputs',str(Path(c['inputs'])),'--boot',ids['boot'],'--parent',str(ids['parent']),'--birth',str(ids['parent_birth']),'--hdc',c['hdc'],'--holder',c['holder'],'--start',str(c['start']),'--admission',str(adfile),'--out',str(out)]
    if origin_plan:argv+=['--apply-plan',str(origin_plan)]
    if mode=='durable-recovery':argv+=['--origin-data',str(d),'--origin-admission',str(origin_admission)]
    return argv

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['preflight','apply','same-window-rollback','durable-recovery'])
    for k in ('context','admission','identity','out','inputs'):p.add_argument('--'+k,type=Path,required=True)
    for k in ('origin-plan','origin-admission'):p.add_argument('--'+k,type=Path)
    p.add_argument('--execute',action='store_true');a=p.parse_args();c=json.loads(a.context.read_text());c['inputs']=str(a.inputs.resolve());w=a.context.parent
    argv=command(a.mode,c,w,a.admission,a.identity,a.out,a.origin_plan,a.origin_admission)
    if not a.execute:print(json.dumps({'status':'PREVIEW_ONLY','device_calls':0,'argv':argv},indent=2));return
    require(Path.cwd().resolve()==Path(c['repo']).resolve() and Path(c['repo']).name=='westlake-harness','root execution cwd MAIN')
    stem=w/(a.out.name+'-exec');require(not stem.with_suffix('.argv.json').exists(),'no repeated dispatch')
    stem.with_suffix('.argv.json').write_text(json.dumps(argv,indent=2)+'\n')
    left=c['start']+(1200 if a.mode in ('preflight','apply') else 1800)-time.time();require(left>0,'cutoff')
    with stem.with_suffix('.stdout').open('wb') as so,stem.with_suffix('.stderr').open('wb') as se:
        try:r=subprocess.run(argv,stdout=so,stderr=se,timeout=min(180,left))
        except subprocess.TimeoutExpired:stem.with_suffix('.rc').write_text('timeout\n');raise
    stem.with_suffix('.rc').write_text(str(r.returncode)+'\n');raise SystemExit(r.returncode)
if __name__=='__main__':main()
