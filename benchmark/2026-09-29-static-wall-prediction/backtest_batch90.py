#!/usr/bin/env python3
"""Score immutable predictions against a completed full batch; no device I/O.

Triage labels are observations, not proven root causes. The output retains
unknown/partial/out-of-cohort exclusions and does not infer own UI from survival.
"""
import argparse,datetime,hashlib,json
from pathlib import Path
from collections import Counter
from update90 import dump,table,target_processes

ALIASES={'window-type':'window-type-flags','bindService':'in-app-bindservice','velocitytracker':'velocitytracker-jni','musl-reloc':'native-bionic-header','prefs-npe':'sharedpreferences-null','theme-appcompat':'theme-appcompat','jobscheduler':'jobscheduler-startup','dlopen-ns':'app-native-loader'}
UNKNOWN={'unclassified','no-fatal-found','alive-or-quiet','system-loader-noise','not-observed'}

def read(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def frozen_predictions(directory):
 freeze=read(directory/'freeze.json');items=freeze['outputs']
 item=next(x for x in items if Path(x['path']).name=='predictions.json')
 file=directory/'predictions.json'
 if digest(file)!=item['sha256']:raise ValueError('Prediction hash changed after freeze')
 return {r['app']:r for r in read(file)},freeze

def classify(row):
 text=row.get('fatal') or '';cls=row.get('class','not-observed')
 if 'header failed for /system/' in text:return 'system-loader-noise'
 # Refine missing triage labels, only from the selected attributed exception.
 if 'No implementation found' in text:
  if 'nativeSubscribeCommonEvent' in text or 'nativePublishCommonEvent' in text:return 'common-event-jni'
  if 'VelocityTracker.' in text:return 'velocitytracker-jni'
  if 'Camera.' in text or 'EGLImpl.' in text:return 'egl-camera-jni'
 if 'current thread is not READY for guest dlopen' in text:return 'guest-thread-ready'
 if 'Native library' in text and 'libjnidispatch' in text:return 'jna-native-resource'
 if 'CoroutineStart' in text:return 'coroutine-class-warning'
 if 'IConnectivityManager' in text:return 'connectivity-interface-warning'
 return ALIASES.get(cls,cls)

def score(rows):
 eligible=[r for r in rows if r['eligible_fatal']]
 hit=sum(r['candidate_hit'] for r in eligible);first=sum(r['first_hit'] for r in eligible)
 return {'classified_fatal_candidate_recall':{'hits':hit,'total':len(eligible),'rate':hit/len(eligible) if eligible else None},'classified_first_fatal_agreement':{'hits':first,'total':len(eligible),'rate':first/len(eligible) if eligible else None},'excluded':dict(Counter(r['exclusion'] for r in rows if r['exclusion'])),'nonfatal_or_unproven':sum(r['observation_role']!='fatal' for r in rows),'not_precision':'Unobserved latent candidates are censored, not false positives.'}

def evaluate(prediction_dir,triage_file,out,expected_keys=66,allow_partial=False):
 predictions,freeze=frozen_predictions(prediction_dir);triage=read(triage_file);epoch=datetime.datetime.fromisoformat(freeze['frozen_at']).timestamp();rows=[];keys=set();sources=[]
 for run,group in triage['runs'].items():
  run=Path(run);plan=read(run/'plan.json');obs={r['key']:r for r in group['rows']}
  for app in plan['apps']:
   key=app['key']
   if key in keys:raise ValueError('Duplicate key across batch shards: '+key)
   keys.add(key);path=run/key/'record.json'
   rec=read(path) if path.exists() else {};o=obs.get(key,{})
   pred=predictions.get(key);identity='exact' if pred and pred['apk_sha256']==rec.get('apk_sha256') else 'mismatch' if pred else 'outside-cohort'
   complete=bool(rec.get('finished_at'));family=classify(o)
   ps=run/key/'processes-t5.txt';proc=target_processes(ps.read_text(),rec.get('bms',{}).get('uid')) if ps.exists() else None
   alive=bool(proc) if proc is not None else None
   role='fatal' if o.get('exit_line') and o.get('alive') is False and alive is not True and family not in {'system-loader-noise','coroutine-class-warning','connectivity-interface-warning'} else 'nonfatal-or-unproven'
   if family in {'coroutine-class-warning','connectivity-interface-warning'}:role='diagnostic-warning'
   classified=family not in UNKNOWN
   candidates=pred.get('candidate_wall_order',pred.get('new_family_order',pred.get('observed_wall_order',[]))) if pred else []
   # A native-bionic static match cannot cover arbitrary dlopen namespace failure.
   first=pred.get('predicted_first_new_family',pred.get('next_first_wall_candidate','unknown')) if pred else 'unknown'
   exclusion='not-complete' if not complete else 'APK-'+identity if identity!='exact' else 'unclassified' if not classified else 'not-proven-fatal' if role!='fatal' else ''
   clicked=rec.get('clicked_at');prospective=isinstance(clicked,(int,float)) and clicked>epoch
   rows.append({'app':key,'apk_sha256':rec.get('apk_sha256'),'identity':identity,'complete':complete,'family':family,'raw_class':o.get('class'),'observation_role':role,'eligible_fatal':not exclusion,'exclusion':exclusion,'candidate_hit':family in candidates,'first_hit':family==first,'predicted_order':candidates,'predicted_first':first,'alive_t5':alive,'prediction_precedes_click':prospective,'captured':sum(s.get('captured') is True for s in rec.get('screenshots',[])),'record':str(path),'fatal_text':o.get('fatal'),'exit_line':o.get('exit_line')})
   if path.exists():sources.append({'path':str(path),'sha256':digest(path)})
 complete=len(keys)==expected_keys and all(r['complete'] for r in rows)
 if not complete and not allow_partial:raise ValueError(f'Full-batch gate failed: {len(keys)}/{expected_keys} keys; incomplete {[r["app"] for r in rows if not r["complete"]]}')
 result={'prediction_dir':str(prediction_dir),'predictions_sha256':digest(prediction_dir/'predictions.json'),'frozen_at':freeze['frozen_at'],'triage':str(triage_file),'triage_sha256':digest(triage_file),'generated_at':datetime.datetime.now().astimezone().isoformat(),'full_batch_complete':complete,'expected_keys':expected_keys,'observed_keys':len(keys),'metrics':score(rows),'temporal_note':'Precedes click is a timing check, not proof of blind evaluation; prior triage exposure and runtime generation must be considered separately.','profile_note':'Static r13 / r15c-informed predictions and subsequent runtime versions differ; recalled families are conditional observations, not repairs.','records':sources,'rows':rows}
 dump(out/'results.json',result);table(out/'backtest.csv',rows)
 missed=[r for r in rows if r['identity']=='exact' and r['complete'] and (not r['candidate_hit'] or r['exclusion'])]
 table(out/'missed-or-unresolved.csv',missed,list(rows[0]))
 print(json.dumps({'full_batch_complete':complete,'observed_keys':len(keys),'metrics':result['metrics']},ensure_ascii=False));return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--predictions',type=Path,required=True);p.add_argument('--triage',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--expected-keys',type=int,default=66);p.add_argument('--allow-partial',action='store_true');a=p.parse_args();evaluate(a.predictions,a.triage,a.out,a.expected_keys,a.allow_partial)
