#!/usr/bin/env python3
"""Publish a complete, manually adjudicated sweep without changing its forecast."""
import argparse,csv,datetime,json,shutil
from pathlib import Path
from score import HERE,sha,verify,effective_profile,score
from audit_run import audit_run,observations_from_run

def select_first_attempts(runs):
 """Runs are declared chronological continuations. Never inspect outcome to select."""
 selected={};duplicates=[];summaries=[]
 for run in runs:
  summary=json.loads((run/'summary.json').read_text());summaries.append(summary)
  for record in summary['records']:
   key=record['key']
   if key in selected:duplicates.append({'key':key,'retained_run':str(selected[key]),'excluded_run':str(run),'reason':'later attempt; no best-result selection'})
   else:selected[key]=run
 return selected,duplicates,summaries

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--run',type=Path,action='append',required=True);ap.add_argument('--installer-readback',type=Path,required=True);ap.add_argument('--reviewed',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
 freeze=HERE/'freezes/v2';receipt=verify(freeze);predictions=json.loads((freeze/'predictions.json').read_text());by={p['key']:p for p in predictions}
 selected,duplicates,summaries=select_first_attempts(a.run)
 if set(selected)!=set(by):raise ValueError('full sweep is incomplete')
 if summaries[-1].get('not_run') or summaries[-1].get('batch_error'):raise ValueError('last continuation is incomplete')
 reviewed=list(csv.DictReader(a.reviewed.open(),delimiter='\t'))
 if len(reviewed)!=66 or {r['key'] for r in reviewed}!=set(by):raise ValueError('need exactly 66 explicit reviews, including unknown/excluded rows')
 audits={str(run):audit_run(run,installer_readback=a.installer_readback) for run in a.run}
 for run,audit in audits.items():
  if not audit['verified']:raise ValueError('actual profile audit failed: '+run+':'+str(audit['errors']))
 observations=[];adjudication_evidence=[]
 for row in reviewed:
  key=row['key'];p=by[key];run=selected[key];folder=run/key;raw=json.loads((folder/'record.json').read_text());shots=[s for s in raw.get('screenshots',[]) if s.get('captured') is True]
  if row['lit']!='unknown' and not shots:raise ValueError('UI verdict without capture: '+key)
  shot=next((s for s in shots if s.get('scheduled_seconds')==20),shots[-1] if shots else None)
  lines=[int(n) for n in row['log_lines'].split(',') if n];evidence=None
  if lines:
   content=(folder/'hilog.txt').read_text(errors='replace').splitlines()
   if min(lines)<1 or max(lines)>len(content):raise ValueError('invalid evidence line: '+key)
   evidence=';'.join(str(folder/'hilog.txt')+':'+str(n) for n in lines)
   indices=sorted({i for n in lines for i in range(max(1,n-2),min(len(content),n+3)+1)})
   adjudication_evidence.append({'key':key,'source':str(folder/'hilog.txt'),'sha256':sha(folder/'hilog.txt'),'cited_lines':lines,'context':[{'line':i,'text':content[i-1]} for i in indices]})
  if row['advance']!='unknown' and not evidence:raise ValueError('progress verdict without evidence: '+key)
  observations.append(dict(key=key,board=run.name,source_run=str(run),lit=row['lit'],screenshot_evidence=shot['path'] if shot else None,advance=row['advance'],progress_checkpoint=p['progress_checkpoint'],progress_evidence=evidence,prior_wall=p['prior_wall'],same_wall=row['same_wall'],wall_evidence=evidence or (str(folder/'record.json')+':error' if raw.get('error') else None),observed_wall=row['observed_wall'],note=row['note']))
 checked=[];facts=[]
 for o in observations:
  run=Path(o['source_run']);obs,rec=observations_from_run([o],run,audits[str(run)]);checked.extend(obs);facts.extend(rec)
 result=score(predictions,checked,effective_profile(freeze,HERE/'execution-amendment-5ea.json'),receipt['frozen_at'])
 result['protocol_strata']={}
 for run in a.run:
  subset=[o for o in checked if o['source_run']==str(run)]
  result['protocol_strata'][run.parent.name]=score(predictions,subset,effective_profile(freeze,HERE/'execution-amendment-5ea.json'),receipt['frozen_at'])['metrics']['all']
 result['protocol_scope']={'combined':'Execution-amended continuation, same measured runtime profile; not an unchanged-batch-protocol claim.','strict_original_batch':a.run[0].parent.name,'continuation_change':'e98d00c9 cold-stop helper cleanup; original-v2 batch-change exclusion remains disclosed.','policy':str(HERE/'continuation-policy.json'),'policy_sha256':sha(HERE/'continuation-policy.json')}
 counts={'records':len(facts),'captured':sum(f['captured_count'] for f in facts),'captures_verified':sum(s['valid'] for f in facts for s in f['captures'])}
 for stage in ('t5','t20'):
  measured=[f['processes'][stage] for f in facts if f['processes'][stage] is not None]
  counts[stage]={'measured_apps':len(measured),'unknown_apps':len(facts)-len(measured),'alive_apps':sum(p['alive'] for p in measured),'app_processes':sum(len(p['app_processes']) for p in measured),'same_uid_helpers_excluded':sum(len(p['same_uid_helpers']) for p in measured)}
 counts['visually_lit_keys']=[o['key'] for o in checked if o['lit']=='yes'];counts['visual_unknown_keys']=[o['key'] for o in checked if o['lit']=='unknown']
 result.update(created_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),freeze_sha256=sha(freeze/'freeze.json'),predictions_csv_sha256=sha(freeze/'predictions.csv'),execution_amendment_sha256=sha(HERE/'execution-amendment-5ea.json'),reviewed_sha256=sha(a.reviewed),runtime_audits=audits,duplicate_attempts_excluded=duplicates,attempt_selection='first terminal record in declared chronological run order; never select a better outcome',checked_observations=checked,record_facts=facts,counts=counts,review_status='agent_visual_review_pending_outer_acceptance')
 a.out.mkdir(parents=True,exist_ok=True)
 for name,data in [('observations.json',observations),('results.json',result),('adjudication-evidence.json',adjudication_evidence)]:
  with (a.out/name).open('x') as f:json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
 source=a.out/'run-identity';source.mkdir(exist_ok=True)
 for run in a.run:
  dest=source/run.parent.name;dest.mkdir(exist_ok=True)
  for name in ('facts.txt','runtime-fingerprint.txt','baseline.json','plan.json','summary.json'):
   shutil.copyfile(run/name,dest/name)
 shutil.copyfile(a.installer_readback,source/'installer-readback.txt')
 for key,run in selected.items():
  dest=a.out/'source-records'/key;dest.mkdir(parents=True,exist_ok=True)
  for name in ('record.json','bundle.txt','processes-t5.txt','processes-t20.txt'):
   src=run/key/name
   if src.exists():shutil.copyfile(src,dest/name)
 keyed={o['key']:o for o in checked};facted={f['key']:f for f in facts};rows=[]
 for r in result['rows']:
  o=keyed[r['key']];f=facted[r['key']]
  rows.append(dict(**r,lit=o['lit'],advance=o['advance'],same_wall=o['same_wall'],observed_wall=o['observed_wall'],note=o['note'],screenshot_evidence=o['screenshot_evidence'],progress_evidence=o['progress_evidence'],captured=f['captured_count'],t5_alive=f['processes']['t5']['alive'] if f['processes']['t5'] else 'unknown',t20_alive=f['processes']['t20']['alive'] if f['processes']['t20'] else 'unknown'))
 with (a.out/'backtest.csv').open('x') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
 print(json.dumps({'metrics':result['metrics']['all'],'counts':counts},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
