#!/usr/bin/env python3
"""Scores already-frozen task85 predictions. Observations are loaded only here."""
import argparse,datetime,hashlib,json,gzip
from pathlib import Path
from scan85 import OUT
from rules85 import FAMILIES
from scan_io import load
from finalize_v3 import dump,csvwrite
FAMILY_MAP={'window-type':'window-type-flags','bindService':'in-app-bindservice','velocitytracker':'velocitytracker-jni','musl-reloc':'native-bionic-header','prefs-npe':'sharedpreferences-null'}

def ratio(rows,predicate):
    hits=sum(bool(predicate(r)) for r in rows)
    return {'hits':hits,'total':len(rows),'rate':hits/len(rows) if rows else None}

def score_rows(rows):
    exact=[r for r in rows if r['identity']=='exact' and r['classifiable']]
    held=[r for r in exact if r['partition']=='held-out' and r['observed_family'] in FAMILIES]
    seed=[r for r in exact if r['partition']=='seed' and r['observed_family'] in FAMILIES]
    hit=lambda r:r['observed_family'] in r['predicted_families']
    first=lambda r:r['observed_family']==r['first_new_family']
    return {'held_out_family':ratio(held,hit),'seed_family':ratio(seed,hit),
        'held_out_first_fatal':ratio([r for r in held if r['observation_role']=='fatal'],first),
        'seed_first_fatal':ratio([r for r in seed if r['observation_role']=='fatal'],first),
        'conditional_key_family':ratio([r for r in rows if r['observed_family'] in FAMILIES and r.get('predicted_families')],hit),
        'all_classified_first_fatal':ratio([r for r in exact if r['observation_role']=='fatal'],first),
        'classified_outside_new_families':sum(r['classifiable'] and r['observed_family'] not in FAMILIES for r in rows),
        'identity_unknown':sum(r['identity']!='exact' for r in rows),
        'unclassified':sum(not r['classifiable'] for r in rows),
        'nonfatal_or_unproven':sum(r['observation_role']!='fatal' for r in rows)}

def logical_bytes(path):
    path=Path(path)
    if path.exists():return path.read_bytes()
    return gzip.decompress(Path(str(path)+'.gz').read_bytes())

def verify_freeze():
    freeze=load(OUT/'freeze.json')
    for item in freeze['inputs']+freeze['outputs']:
        if hashlib.sha256(logical_bytes(item['path'])).hexdigest()!=item['sha256']:raise ValueError('Frozen file changed: '+item['path'])
    if hashlib.sha256(logical_bytes(OUT/'provider-exports.json')).hexdigest()!=freeze['provider_manifest_sha256']:raise ValueError('Provider manifest changed')
    return freeze


def evaluate(triage_path):
    freeze=verify_freeze();predictions={r['app']:r for r in load(OUT/'predictions.json')}
    exposure=set(freeze['outcome_exposure']['seed_keys']);triage=load(triage_path)
    rows=[];records=[];seen=set()
    for run,group in triage['runs'].items():
        for observed in group['rows']:
            key=observed['key'];seen.add(key);record_path=Path(run)/key/'record.json'
            record=load(record_path) if record_path.exists() else {}
            digest=record.get('apk_sha256');prediction=predictions.get(key)
            identity='exact' if prediction and digest==prediction['apk_sha256'] else 'mismatch' if prediction and digest else 'unknown'
            finished=bool(record.get('finished_at'))
            family=FAMILY_MAP.get(observed['class'],observed['class'])
            text=observed.get('fatal') or ''
            # #83's old broad loader bucket is retained as provenance but not
            # allowed to turn /system loader warnings into app-native failures.
            system_noise='header failed for /system/' in text or observed['class']=='musl-system-noise'
            if system_noise:family='system-loader-noise'
            role='fatal' if observed.get('exit_line') and observed.get('alive') is not True and text and not system_noise else 'nonfatal-or-unproven'
            classified=family not in {'unclassified','no-fatal-found','alive-or-quiet','system-loader-noise'}
            if not finished:classified=False;role='incomplete-record'
            row={'app':key,'partition':'seed' if key in exposure else 'held-out','identity':identity,
                'observation_complete':finished,'predicted_apk_sha256':prediction['apk_sha256'] if prediction else None,
                'observed_apk_sha256':digest,'observed_raw_class':observed['class'],'observed_family':family,
                'observation_role':role,'classifiable':classified,'in_prediction_cohort':bool(prediction),
                'predicted_families':prediction['new_family_order'] if prediction else [],
                'first_new_family':prediction['predicted_first_new_family'] if prediction else 'unknown',
                'family_hit':bool(prediction and family in prediction['new_family_order']),
                'first_hit':bool(prediction and family==prediction['predicted_first_new_family']),
                'fatal_text':text,'exit_line':observed.get('exit_line'),'record_path':str(record_path),
                'exclusion':'not-in-32-APK-predictions' if not prediction else 'record-incomplete' if not finished else 'APK-identity-not-matched' if identity!='exact' else 'system-warning-not-app-native-wall' if system_noise else 'unclassified-observation' if not classified else '',
                'profile_note':'APK exactness uses recorded install SHA; native/r13 static inputs versus r14 execution remain conditional.'}
            rows.append(row)
            if record_path.exists():
                saved=OUT/'evidence/records'/key/'record.json';saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(record_path.read_bytes())
                records.append({'key':key,'source':str(record_path),'sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'finished_at':record.get('finished_at'),'apk_sha256':digest})
    for key,prediction in predictions.items():
        if key not in seen:
            rows.append({'app':key,'partition':'seed' if key in exposure else 'held-out','identity':'unknown',
                'observation_complete':False,'predicted_apk_sha256':prediction['apk_sha256'],'observed_apk_sha256':None,
                'observed_raw_class':'not-observed','observed_family':'unknown','observation_role':'incomplete-record','classifiable':False,
                'in_prediction_cohort':True,'predicted_families':prediction['new_family_order'],'first_new_family':prediction['predicted_first_new_family'],
                'family_hit':False,'first_hit':False,'fatal_text':'','exit_line':None,'record_path':None,'exclusion':'no-r14-record-at-cutoff','profile_note':'unknown'})
    # auto_triage omits app directories without hilog. Preserve their install
    # identity/completion, but never invent an observed wall for them.
    for row in rows:
        if row['exclusion']!='no-r14-record-at-cutoff':continue
        for run in triage['runs']:
            record_path=Path(run)/row['app']/'record.json'
            if not record_path.exists():continue
            record=load(record_path);digest=record.get('apk_sha256')
            row['observed_apk_sha256']=digest
            row['identity']='exact' if digest==row['predicted_apk_sha256'] else 'mismatch' if digest else 'unknown'
            row['observation_complete']=bool(record.get('finished_at'))
            row['record_path']=str(record_path)
            row['observation_role']='measurement-gap'
            row['exclusion']='triage-row-or-hilog-missing' if row['observation_complete'] else 'record-incomplete'
            saved=OUT/'evidence/records'/row['app']/'record.json';saved.parent.mkdir(parents=True,exist_ok=True);saved.write_bytes(record_path.read_bytes())
            records.append({'key':row['app'],'source':str(record_path),'sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'finished_at':record.get('finished_at'),'apk_sha256':digest})
            break
    frozen_epoch=datetime.datetime.fromisoformat(freeze['frozen_at']).timestamp()
    for row in rows:
        saved=OUT/'evidence/records'/row['app']/'record.json'
        record=load(saved) if saved.exists() else {}
        clicked=record.get('clicked_at')
        row['clicked_at']=clicked
        row['prediction_precedes_app_click']=(frozen_epoch<float(clicked)) if isinstance(clicked,(float,int)) else None
    metrics=score_rows(rows)
    per_family=[]
    for family in FAMILIES:
        for partition in ['seed','held-out']:
            target=[r for r in rows if r['identity']=='exact' and r['classifiable'] and r['observed_family']==family and r['partition']==partition]
            per_family.append({'family':family,'partition':partition,**ratio(target,lambda r:r['family_hit'])})
    result={'task':85,'evaluated_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),
        'freeze_verified':True,'frozen_at':freeze['frozen_at'],'prediction_file_sha256':freeze['outputs'][2]['sha256'],
        'triage_source':str(triage_path),'triage_sha256':hashlib.sha256(Path(triage_path).read_bytes()).hexdigest(),
        'metrics':metrics,'family_rates':per_family,
        'coverage':{'predicted_apks':len(predictions),'observed_rows':sum(len(v['rows']) for v in triage['runs'].values()),
            'exact_finished_predictions':sum(r['in_prediction_cohort'] and r['identity']=='exact' and r['observation_complete'] for r in rows),
            'missing_or_incomplete_predictions':[r['app'] for r in rows if r['in_prediction_cohort'] and not r['observation_complete']],
            'outside_prediction_cohort':[r['app'] for r in rows if not r['in_prediction_cohort']],
            'prediction_precedes_click':[r['app'] for r in rows if r['in_prediction_cohort'] and r['prediction_precedes_app_click'] is True]},
        'scoring_notes':['Primary metrics cover only the five new families, with exact recorded APK identity.',
            'Warnings without an exit are never first-fatal hits.',
            'Unclassified/out-of-cohort/missing outcomes are excluded with reasons, not successes.',
            'Held-out means outcome-blind until freeze; the r14 board run itself predates the prediction.',
            'Broad API references may be latent/censored risks; candidate coverage is not precision or runtime causation.',
            'Full-prediction class risks remain inherited from r13, not asserted unresolved under r14.'],
        'rows':rows}
    dump(OUT/'backtest.json',result);csvwrite(OUT/'backtest.csv',rows,list(rows[0]))
    dump(OUT/'evidence/record-inputs.json',records)
    csvwrite(OUT/'coverage-gaps.csv',[r for r in rows if r['exclusion']],list(rows[0]))
    dump(OUT/'missed-observations.json',[r for r in rows if r['in_prediction_cohort'] and r['observation_complete'] and (not r['family_hit'] or not r['classifiable'])])
    print(json.dumps({'metrics':metrics,'coverage':result['coverage']},ensure_ascii=False))
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--check-freeze',action='store_true');parser.add_argument('--triage',type=Path);args=parser.parse_args()
    if args.triage:evaluate(args.triage)
    else:
        receipt=verify_freeze();print(json.dumps({'verified':True,'frozen_at':receipt['frozen_at']}))
