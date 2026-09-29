#!/usr/bin/env python3
"""Publish v2 exactly once; does not read target full-sweep results."""
import collections,csv,datetime,hashlib,json,shutil
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2,ensure_ascii=False)+'\n')
def main():
 decisions={r['key']:r for r in csv.DictReader((HERE/'decisions.tsv').open(),delimiter='\t')}
 old=ROOT/'benchmark/2026-09-30-background-start-prospective/freezes/v1/predictions.json'
 entries=[r['prediction'] for r in json.loads(old.read_text())];assert len(entries)==66 and set(decisions)=={r['key'] for r in entries}
 profile=json.loads((HERE/'profile.json').read_text());rows=[]
 for e in entries:
  key=e['key'];decision=decisions[key];prior=HERE/'evidence/prior'/(key+'.json');d=json.loads(prior.read_text());snips=d['snippets']
  refs=[f'evidence/prior/{key}.json'];fatal=[x for x in snips if 'J_invokeStaticMain_main_threw' in x['text']];lead=fatal[:1] or snips[-1:]
  source_lines=';'.join(str(x['line']) for x in lead) if lead else 'record error: '+str(d.get('record_error'))
  exposure='prior-sweep-only'
  if key in {'fd-filemanager','fd-gallery','fd-binaryeye','fd-tusky','vlc','anki'}:refs+=['evidence/bglaunch-backtest.csv'];exposure='prior-grant-calibration'
  if key in {'fd-auxio','fd-netguard','ooniprobe','noice','fd-noice'}:refs+=['evidence/v3c-handoff-excerpts.txt','evidence/pre-sweep-board-excerpts.txt'];exposure='prior-v3c-targeted'
  if key=='wikipedia':refs+=['evidence/v3c-handoff-excerpts.txt'];exposure='prior-r17j-targeted'
  if decision['forecast']=='亮':refs+=['evidence/r16-backtest.csv','evidence/r16-visual.json','evidence/pre-sweep-board-excerpts.txt']
  rows.append(dict(**decision,apk_sha256=e['apk_sha256'],package=e['package'],confidence='low' if any(s in decision['reason'] for s in ['low-confidence','low confidence','app-domain','SONAME','namespace']) else 'medium',expected_lit='yes' if decision['forecast']=='亮' else 'no' if decision['forecast']=='不变' else 'unknown',prior_exposure=exposure,prior_record_sha256=d['record_sha256'],prior_log_sha256=d['source_sha256'],prior_log_lines=source_lines,evidence=';'.join(refs),patch_evidence='evidence/build-result-r17j.json;evidence/native-inputs.json;evidence/B7BindFixes.java:145;evidence/SystemServiceFetcherStubs.java:23;evidence/WindowSessionProxy.java:98'))
 out=HERE/'freezes/v2';out.mkdir(parents=True,exist_ok=False)
 with (out/'predictions.csv').open('w') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
 save(out/'predictions.json',rows);shutil.copy2(HERE/'profile.json',out/'profile.json');shutil.copy2(HERE/'decisions.tsv',out/'decisions.tsv');shutil.copytree(HERE/'evidence',out/'evidence')
 policy={'labels':{'亮':'Predict own app UI, including existing UI retained; screenshot adjudication required.','推进':'Predict passing the named prior wall/checkpoint, possibly still blocked before UI. Higher UI outcome meets the minimum prediction but is distinct in exact four-class accuracy.','不变':'Predict still blocked by the named unresolved wall, not merely no screenshot and not a functioning UI remaining unchanged.','unknown':'Abstain; insufficient identity, first-wall evidence or profile-specific evidence.'},'timing':'Only clicked_at after frozen_at; exposure to prior single-app r17j/v3c tests is disclosed separately. No new full-sweep outcomes read.','identity':'Exact APK, candidate manifest, JAR, installer hashes and feature verification required. Score each board separately; no best-board selection.','scoring':'Report exact four-class accuracy, minimum-promised-outcome accuracy and coverage separately. Missing screenshot/progress/wall evidence stays unknown.','scope':'Prior bounded static Activity scan retained as hints only; per-key decisions combine prior target-PID logs, signed UI and exact pinned patch inputs. Mere file presence does not prove app namespace visibility.','exceptions':'Subway input mismatch remains unknown. Batch validation failures remain part of outcome. Any extra native/JAR/batch behavioral patch is a different profile requiring a new freeze.'}
 save(out/'policy.json',policy)
 for name in ['freeze.py','score.py']:shutil.copy2(HERE/name,out/name)
 save(out/'inputs.json',{'prior_v1_sha256':sha(old),'source_scope':'r16 adjudication, r17c historical sweep, v0 background-launch backtest, named prior v3c/r17j targeted handoffs; no upcoming full sweep','prior_jar_source_commit':'d50325c6','board_excerpt_original_line_numbers':True})
 receipt={'version':'v2','frozen_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'keys':len(rows),'counts':dict(collections.Counter(r['forecast'] for r in rows)),'new_full_sweep_results_read':False,'hashes':{str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}}
 save(out/'freeze.json',receipt);print(json.dumps({k:v for k,v in receipt.items() if k!='hashes'},ensure_ascii=False,indent=2));print('predictions.csv SHA256',receipt['hashes']['predictions.csv'])
if __name__=='__main__':main()
