#!/usr/bin/env python3
"""Apply frozen score.py to independently adjudicated observations."""
import argparse,datetime,json
from pathlib import Path
from collect_results import HERE,verify,sha
from score import score
def main(observations,out):
 freeze=verify();obs=json.loads(observations.read_text())
 for key,r in obs.items():
  if r.get('visual') in {'lit','not-lit'} and (not r.get('reviewer') or not r.get('visual_evidence')):
   raise ValueError('Adjudicated visual needs reviewer and screenshot/source evidence: '+key)
  if r.get('first_wall') not in {None,'unknown','none',''} and not r.get('first_wall_evidence'):
   raise ValueError('Classified first wall needs evidence: '+key)
 predictions=json.loads((HERE/'predictions.json').read_text())
 result=score(predictions,obs,freeze['frozen_at'])
 result.update({'evaluated_at':datetime.datetime.now().astimezone().isoformat(),'frozen_at':freeze['frozen_at'],'predictions_sha256':sha(HERE/'predictions.json'),'observation_file':str(observations),'observation_sha256':sha(observations),'status':'partial-adjudication' if result['all_exact_adjudicated']['excluded'] else 'all-keys-adjudicated'})
 out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
 print(json.dumps({k:v for k,v in result.items() if k!='rows'},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--observations',type=Path,required=True);p.add_argument('--out',type=Path,default=HERE/'backtest.json');a=p.parse_args();main(a.observations,a.out)
