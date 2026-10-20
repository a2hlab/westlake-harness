from pathlib import Path
import argparse,sys,subprocess,json,time
from window_paths import WINDOW,BASE,context,budget,deploy,tag,load,sha

def command(mode,boot,parent,birth,adfile,label,c):
    assert mode in ('preflight','apply','rollback')
    tag(label);tag(adfile) if '/' not in adfile else None
    ad=(WINDOW/adfile).resolve();assert ad.is_relative_to(WINDOW) and ad.is_file()
    a=load(ad);assert a['boot']==boot and a['holder']==c['holder'] and a['window_start']==c['start']
    argv=[sys.executable,str(deploy()/'executor.py'),mode,'--execute','--repo',c['repo'],
          '--inputs',str(BASE/'t30-candidate-inputs'),'--boot',boot,'--parent',str(parent),
          '--birth',str(birth),'--hdc',c['hdc'],'--holder',c['holder'],'--start',str(c['start']),
          '--admission',str(ad),'--out',str(WINDOW/label)]
    if mode=='rollback':
        plan=WINDOW/'apply/plan.json';assert a['origin_apply_plan_sha256']==sha(plan)
        original=load(plan);assert original['holder']==c['holder'] and original['start']==c['start']
        argv+=['--apply-plan',str(plan)]
    else:assert a['origin_apply_plan_sha256'] is None
    return argv

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['preflight','apply','rollback'])
    for n in ('boot','parent','birth','adfile','tag'):p.add_argument(n)
    a=p.parse_args();c=context();left=budget(c,a.mode=='rollback');argv=command(a.mode,a.boot,a.parent,a.birth,a.adfile,a.tag,c)
    stem=WINDOW/(a.tag+'-exec');assert not stem.with_suffix('.argv.json').exists()
    stem.with_suffix('.argv.json').write_text(json.dumps(argv));start=time.monotonic()
    with stem.with_suffix('.stdout').open('wb') as so,stem.with_suffix('.stderr').open('wb') as se:
        try:r=subprocess.run(argv,stdout=so,stderr=se,timeout=min(180,left))
        except subprocess.TimeoutExpired:stem.with_suffix('.rc').write_text('timeout\n');raise
    stem.with_suffix('.rc').write_text(str(r.returncode)+'\n');print(json.dumps({'rc':r.returncode,'elapsed':time.monotonic()-start,'out':str(WINDOW/a.tag)}));sys.exit(r.returncode)
if __name__=='__main__':main()
