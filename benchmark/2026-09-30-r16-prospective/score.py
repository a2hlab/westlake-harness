"""Frozen evaluator for independently adjudicated prospective outcomes."""
import datetime,hashlib,json
from pathlib import Path

def score(predictions,outcomes,frozen_at):
 forecast={r['app']:r for r in predictions};epoch=datetime.datetime.fromisoformat(frozen_at).timestamp();rows=[]
 for key,p in forecast.items():
  o=outcomes.get(key,{});identity='exact' if o.get('apk_sha256')==p['apk_sha256'] else 'mismatch' if o.get('apk_sha256') else 'unknown'
  visual=o.get('visual','unknown');wall=o.get('first_wall','unknown')
  complete=o.get('complete') is True;click=o.get('clicked_at')
  eligible=identity=='exact' and complete and visual in {'lit','not-lit'}
  strict=isinstance(click,(int,float)) and click>epoch
  known_wall=eligible and visual=='not-lit' and wall not in {'unknown','none','',None}
  predicted_wall=p['expected_first_wall'];predicts_wall=predicted_wall not in {'unknown','',None}
  rows.append({'app':key,'identity':identity,'complete':complete,'visual':visual,'expected_lit':p['expected_lit'],'light_eligible':eligible,'light_correct':eligible and p['expected_lit']==(visual=='lit'),'strict_pre_click':strict,'clicked_at':click,'observed_first_wall':wall,'expected_first_wall':predicted_wall,'wall_observed':known_wall,'wall_eligible':known_wall and predicts_wall,'wall_correct':known_wall and predicted_wall==wall,'forecast_wall_abstained':known_wall and not predicts_wall,'profile':o.get('profile','unknown'),'exclusion':'identity-'+identity if identity!='exact' else 'incomplete' if not complete else 'visual-unknown' if visual not in {'lit','not-lit'} else ''})
 def ratio(items,field):
  return {'hits':sum(r[field] for r in items),'total':len(items),'rate':sum(r[field] for r in items)/len(items) if items else None}
 def summarize(group):
  return {'lighting':ratio([r for r in group if r['light_eligible']],'light_correct'),'first_wall_classified_forecasts':ratio([r for r in group if r['wall_eligible']],'wall_correct'),'first_wall_including_forecast_abstentions':ratio([r for r in group if r['wall_observed']],'wall_correct'),'unknown_visual':sum(r['visual']=='unknown' for r in group),'excluded':sum(bool(r['exclusion']) for r in group),'wall_forecast_abstentions':sum(r['forecast_wall_abstained'] for r in group)}
 return {'all_exact_adjudicated':summarize(rows),'strict_pre_click':summarize([r for r in rows if r['strict_pre_click']]),'profile_strata':{k:summarize([r for r in rows if r['profile']==k]) for k in sorted({r['profile'] for r in rows})},'rows':rows}
