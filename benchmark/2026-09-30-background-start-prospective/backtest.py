#!/usr/bin/env python3
"""Score adjudicated post-grant observations against an immutable freeze."""
import argparse,collections,datetime,hashlib,json
from pathlib import Path

def date(value):
    if not isinstance(value,str):return None
    try:
        result=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
        return result if result.tzinfo else None
    except ValueError:return None

def verify_freeze(root):
    receipt=json.loads((root/'freeze.json').read_text())
    for name,h in receipt['hashes'].items():
        if hashlib.sha256((root/name).read_bytes()).hexdigest()!=h:raise ValueError('frozen file changed: '+name)
    return receipt

def score(predictions,observations,frozen_at,require_pre_intervention=True):
    preds={x['key']:x for x in predictions};rows=[];seen=set();freeze=date(frozen_at)
    if not freeze:raise ValueError('invalid freeze timestamp')
    for obs in observations:
        key=obs['key']
        if key in seen:raise ValueError('duplicate observation key; score one homogeneous run at a time: '+key)
        seen.add(key);p=preds.get(key);reasons=[]
        if p is None:reasons.append('key_not_predicted')
        elif obs.get('apk_sha256')!=p['apk_sha256']:reasons.append('apk_identity_mismatch')
        if obs.get('grant_verified') is not True:reasons.append('grant_not_verified')
        clicked=date(obs.get('clicked_at'));installed=date(obs.get('intervention_at'))
        if not clicked:reasons.append('click_time_unknown')
        elif clicked<=freeze:reasons.append('not_strictly_post_freeze')
        if not installed:reasons.append('intervention_time_unknown')
        elif clicked and clicked<=installed:reasons.append('not_post_intervention')
        if require_pre_intervention and installed and installed<=freeze:reasons.append('freeze_not_before_intervention')
        row=dict(key=key,eligible=not reasons,reasons=reasons,calibration=p.get('calibration',False) if p else False,negative_control=p.get('negative_control',False) if p else False,profile_stratum=('matched' if obs.get('comparable_profile') is True else 'mismatch' if obs.get('comparable_profile') is False else 'unknown'),outcomes={})
        for axis,pfield,ofield in [('advance','expected_advance','advance_observed'),('page','expected_page','predicted_page_observed')]:
            forecast=p.get(pfield,'unknown') if p else 'unknown';actual=obs.get(ofield,'unknown')
            if actual not in {'yes','no','unknown'}:raise ValueError('bad observation label')
            evidence=obs.get('screenshot_evidence') if axis=='page' else obs.get('transition_evidence')
            if actual!='unknown' and not evidence:actual='unknown'
            row['outcomes'][axis]=dict(predicted=forecast,observed=actual,scored=not reasons and forecast!='unknown' and actual!='unknown',correct=(forecast==actual) if not reasons and forecast!='unknown' and actual!='unknown' else None)
        rows.append(row)
    def summarize(selected,axis):
        eligible=[r for r in selected if r['eligible']];known=[r for r in eligible if r['outcomes'][axis]['observed']!='unknown'];scored=[r for r in known if r['outcomes'][axis]['scored']]
        correct=sum(r['outcomes'][axis]['correct'] for r in scored)
        confusion=collections.Counter((r['outcomes'][axis]['predicted'],r['outcomes'][axis]['observed']) for r in scored)
        return dict(eligible=len(eligible),known_outcomes=len(known),scored=len(scored),abstentions=len(known)-len(scored),correct=correct,accuracy=correct/len(scored) if scored else None,coverage=len(scored)/len(known) if known else None,coverage_adjusted=correct/len(known) if known else None,tp=confusion['yes','yes'],fp=confusion['yes','no'],tn=confusion['no','no'],fn=confusion['no','yes'])
    groups={'all':rows,'calibration':[r for r in rows if r['calibration']],'unseen':[r for r in rows if not r['calibration'] and not r['negative_control']],'negative_control':[r for r in rows if r['negative_control']]}
    for label in ('matched','mismatch','unknown'):groups['profile_'+label]=[r for r in rows if r['profile_stratum']==label]
    return dict(rows=rows,missing_observations=sorted(set(preds)-seen),metrics={key:{axis:summarize(group,axis) for axis in ('advance','page')} for key,group in groups.items()},excluded_reasons=dict(collections.Counter(reason for r in rows for reason in r['reasons'])))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--freeze',type=Path,required=True);p.add_argument('--observations',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    receipt=verify_freeze(a.freeze);preds=[x['prediction'] for x in json.loads((a.freeze/'predictions.json').read_text())];obs=json.loads(a.observations.read_text())
    policy=json.loads((a.freeze/'policy.json').read_text());strict=policy.get('require_freeze_before_intervention',False)
    result=score(preds,obs,receipt['frozen_at'],require_pre_intervention=strict);result.update(timing_scope='strict-before-intervention' if strict else 'pre-click-only-initial-policy',freeze_sha256=hashlib.sha256((a.freeze/'freeze.json').read_bytes()).hexdigest(),observation_sha256=hashlib.sha256(a.observations.read_bytes()).hexdigest())
    if a.out.exists():raise ValueError('refuse overwriting a prior backtest')
    a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result['metrics'],indent=2))
if __name__=='__main__':main()
