#!/usr/bin/env python3
"""Audit actual profile, then score exactly that frozen JAR column."""
import argparse,json
from pathlib import Path
import engine
from audit_run import audit_run,observations_from_run
H=Path(__file__).resolve().parent

def add_baselines(result):
 for name,m in result['metrics'].items():
  rs=result['rows'] if name=='all' else [r for r in result['rows'] if r['board']==name or r['prior_exposure']==name]
  scored=[r for r in rs if r['exact_correct'] is not None]
  m['always_unchanged_hits']=sum(r['observed']=='不变' for r in scored)
  m['always_unchanged_accuracy']=m['always_unchanged_hits']/len(scored) if scored else None
 return result

def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',type=Path,default=H/'freezes/v3');p.add_argument('--variant',choices=['r17o','r17p'],required=True);p.add_argument('--run',type=Path,action='append',required=True);p.add_argument('--installer-readback',type=Path);p.add_argument('--observations',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 f=engine.verify(a.freeze)
 for name in ['score.py','engine.py','audit_run.py']:
  if engine.sha(H/name)!=f['hashes']['code/'+name]:raise ValueError('scoring code differs from frozen code: '+name)
 variant=a.freeze/'variants'/a.variant;vf=engine.verify(variant);profile=json.loads((variant/'profile.json').read_text())
 audits={str(run):audit_run(run,variant,a.installer_readback,None) for run in a.run}
 supplied=json.loads(a.observations.read_text());checked=[];facts=[]
 for o in supplied:
  src=o.get('source_run',str(a.run[0]) if len(a.run)==1 else None)
  if src not in audits:raise ValueError('unknown source_run')
  obs,record=observations_from_run([o],Path(src),audits[src]);checked+=obs;facts+=record
 result=add_baselines(engine.score(json.loads((variant/'predictions.json').read_text()),checked,profile,vf['frozen_at']))
 result.update(variant=a.variant,freeze_sha256=engine.sha(a.freeze/'freeze.json'),runtime_audits=audits,checked_observations=checked,record_facts=facts)
 result['comparison_policy']='Each actual JAR separately; no alternative-column rescue. All non-post-freeze launches excluded; prior exposure strata retained.'
 with a.out.open('x') as out:json.dump(result,out,ensure_ascii=False,indent=2);out.write('\n')
 print(json.dumps(result['metrics'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
