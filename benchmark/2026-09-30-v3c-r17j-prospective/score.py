#!/usr/bin/env python3
"""Evidence-gated future sweep scoring; predictions are never edited."""
import argparse,collections,datetime,hashlib,json
from pathlib import Path
HERE=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def date(value):
 try:
  d=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
  return d if d.tzinfo else None
 except (AttributeError,ValueError):return None
def verify(root):
 f=json.loads((root/'freeze.json').read_text())
 for name,h in f['hashes'].items():
  if sha(root/name)!=h:raise ValueError('frozen file changed: '+name)
 return f
def effective_profile(root,amendment):
 profile=json.loads((root/'profile.json').read_text())
 if amendment is None:return profile
 a=json.loads(amendment.read_text())
 if a['frozen_receipt_sha256']!=sha(root/'freeze.json'):raise ValueError('amendment freeze mismatch')
 if a['added_boards']!=['5ea34a4500000000000000001123012c']:raise ValueError('unauthorized execution-board amendment')
 profile['boards']=profile['boards']+a['added_boards']
 profile['require_runtime_audit']=True
 return profile
def score(predictions,observations,profile,frozen_at):
 by={p['key']:p for p in predictions};rows=[];seen=set()
 for o in observations:
  identity=(o['board'],o['key'])
  if identity in seen:raise ValueError('duplicate board/key')
  seen.add(identity);p=by.get(o['key']);reasons=[]
  if not p:reasons.append('key_unknown')
  elif o.get('apk_sha256')!=p['apk_sha256']:reasons.append('apk_mismatch')
  if o['board'] not in profile['boards']:reasons.append('board_mismatch')
  for k in ('package_sha256','jar_sha256','installer_sha256'):
   if o.get(k)!=profile[k]:reasons.append(k+'_mismatch')
  for k in ('grant_verified','select_launcher_verified','batch_sidecars_enabled'):
   if o.get(k) is not True:reasons.append(k+'_unknown')
  clicked=date(o.get('clicked_at'))
  if not clicked or clicked<=date(frozen_at):reasons.append('not_post_freeze')
  if not o.get('profile_evidence'):reasons.append('profile_evidence_missing')
  if profile.get('require_runtime_audit') and o.get('runtime_audit_verified') is not True:reasons.append('runtime_audit_unverified')
  lit=o.get('lit','unknown') if o.get('screenshot_evidence') else 'unknown'
  advance=o.get('advance','unknown') if o.get('progress_evidence') and p and o.get('progress_checkpoint')==p['progress_checkpoint'] else 'unknown'
  same=o.get('same_wall','unknown') if o.get('wall_evidence') and p and o.get('prior_wall')==p['prior_wall'] else 'unknown'
  observed='亮' if lit=='yes' else '推进' if lit=='no' and advance=='yes' else '不变' if lit=='no' and advance=='no' and same=='yes' else 'unknown'
  predicted=p['forecast'] if p else 'unknown';eligible=not reasons
  exact=eligible and predicted!='unknown' and observed!='unknown'
  minimum=None
  if eligible:
   if predicted=='亮' and lit!='unknown':minimum=lit=='yes'
   elif predicted=='推进':
    if lit=='yes' or advance=='yes':minimum=True
    elif advance=='no':minimum=False
   elif predicted=='不变' and observed!='unknown':minimum=observed=='不变'
  rows.append(dict(key=o['key'],board=o['board'],eligible=eligible,reasons=reasons,predicted=predicted,observed=observed,exact_correct=(predicted==observed) if exact else None,minimum_correct=minimum,prior_exposure=p.get('prior_exposure') if p else None))
 def metrics(rs):
  known=[r for r in rs if r['eligible'] and r['observed']!='unknown'];scored=[r for r in known if r['exact_correct'] is not None];floor=[r for r in rs if r['minimum_correct'] is not None]
  eligible=sum(r['eligible'] for r in rs)
  return dict(eligible=eligible,known=len(known),scored=len(scored),exact_hits=sum(r['exact_correct'] for r in scored),abstentions=sum(r['predicted']=='unknown' for r in known),exact_accuracy=sum(r['exact_correct'] for r in scored)/len(scored) if scored else None,coverage=len(scored)/len(known) if known else None,outcome_coverage=len(known)/eligible if eligible else None,scored_coverage=len(scored)/eligible if eligible else None,minimum_scored=len(floor),minimum_hits=sum(r['minimum_correct'] for r in floor),minimum_accuracy=sum(r['minimum_correct'] for r in floor)/len(floor) if floor else None,confusion=dict(collections.Counter(r['predicted']+' -> '+r['observed'] for r in scored)))
 groups={'all':rows}
 for board in profile['boards']:groups[board]=[r for r in rows if r['board']==board]
 for exposure in sorted({r['prior_exposure'] for r in rows if r['prior_exposure']}):groups[exposure]=[r for r in rows if r['prior_exposure']==exposure]
 return dict(rows=rows,metrics={k:metrics(v) for k,v in groups.items()},missing=[{'board':b,'key':k} for b in profile['boards'] for k in by if (b,k) not in seen])
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',type=Path,default=HERE/'freezes/v2');p.add_argument('--amendment',type=Path,default=HERE/'execution-amendment-5ea.json');p.add_argument('--run',type=Path,action='append',required=True);p.add_argument('--installer-readback',type=Path);p.add_argument('--observations',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 from audit_run import audit_run,observations_from_run
 f=verify(a.freeze);audits={str(run):audit_run(run,a.freeze,a.installer_readback,a.amendment) for run in a.run}
 supplied=json.loads(a.observations.read_text());observations=[];records=[]
 for o in supplied:
  source=o.get('source_run',str(a.run[0]) if len(a.run)==1 else None)
  if source not in audits:raise ValueError('observation source_run must name an audited --run')
  checked,facts=observations_from_run([o],Path(source),audits[source]);observations.extend(checked);records.extend(facts)
 result=score(json.loads((a.freeze/'predictions.json').read_text()),observations,effective_profile(a.freeze,a.amendment),f['frozen_at'])
 result.update(runtime_audits=audits,checked_observations=observations,record_facts=records)
 result.update(freeze_sha256=sha(a.freeze/'freeze.json'),observations_sha256=sha(a.observations))
 result['execution_amendment_sha256']=sha(a.amendment)
 with a.out.open('x') as out:json.dump(result,out,indent=2,ensure_ascii=False);out.write('\n')
 print(json.dumps(result['metrics'],ensure_ascii=False,indent=2))
if __name__=='__main__':main()
