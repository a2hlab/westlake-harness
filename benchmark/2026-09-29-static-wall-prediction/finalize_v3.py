#!/usr/bin/env python3
"""Publish static lists, then separately score frozen/updated predictions against receipts."""
import collections,csv,gzip,hashlib,json,subprocess
from pathlib import Path
from scan_jni import HERE,BASE,REPO,sha,R8HASH
from scan_apps import load_apps
OUT=HERE/'v3'
P75=BASE/'westlake-harness-b4/benchmark/2026-09-29-manifest-classes/p73-fatal.json'
P78=BASE/'westlake-harness-bms-deploy/benchmark/2026-09-29-v3a-prospective-rerun'

def read(path):
    path=Path(path)
    if not path.exists() and Path(str(path)+'.gz').exists():path=Path(str(path)+'.gz')
    return json.loads(gzip.open(path,'rt').read() if path.suffix=='.gz' else path.read_text())
def dump(path,data):
    encoded=(json.dumps(data,indent=2)+'\n').encode();path.write_bytes(encoded)
    if len(encoded)>1000000 or Path(str(path)+'.gz').exists():Path(str(path)+'.gz').write_bytes(gzip.compress(encoded,mtime=0))
def csvwrite(path,rows,fields):
    with path.open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields,lineterminator='\n');w.writeheader()
        for r in rows:w.writerow({k:json.dumps(r[k],separators=(',',':')) if isinstance(r.get(k),(dict,list)) else r.get(k) for k in fields})
    if path.stat().st_size>1000000 or Path(str(path)+'.gz').exists():Path(str(path)+'.gz').write_bytes(gzip.compress(path.read_bytes(),mtime=0))

def fatal_wall(text):
    # Fatal-only input. Never call this with caught first_exception text.
    if not text:return 'unknown'
    if 'path is outside app domain' in text:return 'flutter-native-path'
    if any(s in text for s in ['dlopen_ns failed','relocating failed: symbol not found']):return 'dlopen-namespace'
    if 'KoinApplication has not been started' in text:return 'koin-initialization'
    if 'WorkManager is not initialized properly' in text:return 'workmanager-initialization'
    if 'INotificationManager' in text:return 'service:notification'
    if 'Theme.AppCompat' in text:return 'activity-theme'
    if 'InvalidDisplay' in text or 'specified window type' in text:return 'window-display-contract'
    if 'SharedPreferences' in text and 'NullPointerException' in text:return 'attach-context-contract'
    if 'bindService() failed' in text:return 'service-bind-contract'
    if 'Attribute not found' in text:return 'resource-attribute'
    if 'NullPointerException' in text:return 'attach-or-startup-npe:unknown-target'
    return 'unknown'

def matched(wall,observed):
    if wall['wall']==observed:return True
    if wall['wall']=='attach-service-contract' and observed=='service:'+wall.get('basis',wall.get('evidence',{})).get('service',''):return True
    return False

def ratio(rows,predicate):
    return {'hits':sum(bool(predicate(r)) for r in rows),'total':len(rows),
            'rate':sum(bool(predicate(r)) for r in rows)/len(rows) if rows else None}

def predict():
    apps={a['key']:a for a in load_apps()}
    with (OUT/'evidence/v2-predictions.csv').open() as f:before=list(csv.DictReader(f))
    risks=read(OUT/'risk-results.json')['rows'];predictions=[]
    for old in before:
        app=old['app'];profile=old['profile'];walls=json.loads(old['walls'])
        for w in walls:
            w['origin']='v2-static';w.setdefault('runtime_condition','Conditional risk; first execution order unproved.')
        for r in risks:
            if r['app']==app and r['profile']==profile:
                walls.append({'wall':r['wall'],'priority':r['priority'],'confidence':'risk-candidate',
                    'basis':r['evidence'],'startup_reachable':r['startup_reachable'],'stub_ok':r['stub_ok'],
                    'needs_real':r['needs_real'],'runtime_condition':r['runtime_condition'],'origin':'v3-static',
                    'copy_source':copy_source(r['wall'])})
        walls=[w for w in walls if w['wall']!='unknown'] or [{'wall':'unknown','priority':999,
            'confidence':'unknown','startup_reachable':'unknown','stub_ok':False,'needs_real':False,
            'basis':'No bounded static risk found; not a pass.','copy_source':'unknown','origin':'v3-static'}]
        walls.sort(key=lambda w:(w['startup_reachable']!='yes-static',w['priority'],w['wall']))
        seen=set();unique=[]
        for w in walls:
            # Distinct nullable service contracts retain their target service.
            key=(w['wall'],w.get('basis',{}).get('service') if isinstance(w.get('basis'),dict) else '')
            if key not in seen:seen.add(key);unique.append(w)
        predictions.append({'app':app,'profile':profile,'apk_sha256':apps[app]['sha256'],
            'predicted_first':unique[0]['wall'],'wall_order':[w['wall'] for w in unique],
            'stub_ok':[w['wall'] for w in unique if w['stub_ok']],
            'needs_real':[w['wall'] for w in unique if w['needs_real']],
            'startup_known_walls':[w['wall'] for w in unique if w['startup_reachable']=='yes-static'],
            'walls':unique,'ordering':'Bounded startup reachability, then heuristic priority. A risk is not a proof of runtime failure.',
            'rules_evidence':'v3/risk-results.json','v2_first':old['predicted_first']})
    fields=['app','profile','apk_sha256','predicted_first','wall_order','stub_ok','needs_real','startup_known_walls','ordering','walls','rules_evidence','v2_first']
    dump(OUT/'predictions.json',predictions)
    compact=[]
    for i,p in enumerate(predictions):
        walls=[{k:v for k,v in w.items() if k not in {'basis','startup_evidence'}} | {'basis_reference':f'v3/predictions.json#/{i}/walls/{j}'} for j,w in enumerate(p['walls'])]
        compact.append({**p,'walls':walls})
    csvwrite(OUT/'predictions.csv',compact,fields)
    # Public entrypoint replaces old predictions only after the exact #78 baseline was frozen.
    csvwrite(HERE/'predictions.csv',compact,fields)
    groups={}
    for p in predictions:
        for w in p['walls']:
            key=(p['profile'],w['wall']);r=groups.setdefault(key,{'profile':p['profile'],'wall':w['wall'],
                'stub_ok':w['stub_ok'],'needs_real':w['needs_real'],'apps':set(),'startup_apps':set(),'copy_source':w['copy_source']})
            r['apps'].add(p['app'])
            if w['startup_reachable']=='yes-static':r['startup_apps'].add(p['app'])
    ranking=[]
    for r in groups.values():
        r['full_reference_apps']=len(r['apps']);r['startup_affected_apps']=len(r['startup_apps'])
        r['apps']=sorted(r['apps']);r['startup_apps']=sorted(r['startup_apps']);ranking.append(r)
    ranking.sort(key=lambda r:(not r['stub_ok'],-r['startup_affected_apps'],-r['full_reference_apps'],r['wall'],r['profile']))
    dump(OUT/'wall-ranking.json',ranking);dump(HERE/'wall-ranking.json',ranking)
    fields=['profile','wall','stub_ok','needs_real','startup_affected_apps','startup_apps','full_reference_apps','apps','copy_source']
    csvwrite(OUT/'wall-ranking.csv',ranking,fields);csvwrite(HERE/'wall-ranking.csv',ranking,fields)
    return predictions,ranking

def copy_source(wall):
    root=REPO/'bms/src/adapter/framework'
    paths={'dlopen-namespace':root/'native-loader-oh/src/native_loader_registry.cpp',
      'flutter-native-path':root/'native-loader-oh/src/native_loader.cpp',
      'koin-initialization':root/'activity/java/AppSchedulerBridge.java',
      'workmanager-initialization':Path('/Users/zhaoyue/orca/00.Workspace/src/adapter/framework/activity/java/ManifestComponentProjection.java'),
      'attach-service-contract':root/'core/java/OHServiceManager.java',
      'attach-context-contract':root/'activity/java/AppSchedulerBridge.java'}
    p=paths.get(wall)
    if p and p.exists():
        needles={'koin-initialization':'private static synchronized void ensureBindApplication',
            'attach-context-contract':'private static synchronized void ensureBindApplication',
            'attach-service-contract':'lookupAdapter', 'workmanager-initialization':'ProviderInfo',
            'dlopen-namespace':'app_permitted_paths', 'flutter-native-path':'SplitColonStrict'}
        line=next((i for i,s in enumerate(p.read_text().splitlines(),1) if needles.get(wall,'class ') in s),1)
        return str(p)+':'+str(line)+' (repair lead, not a verified complete fix)'
    return 'unknown: no verified complete implementation in the bounded scan'

def backtest(predictions):
    by={(r['app'],r['profile']):r for r in predictions};apps={a['key']:a for a in load_apps()}
    obs=read(P75);rows=[]
    for key,o in obs['apps'].items():
        pred=by[(key,'6cb40cd6+r8b')];observed=fatal_wall(o['fatal'])
        rows.append({'task':75,'app':key,'profile':'6cb40cd6+r8b','apk_sha256':apps[key]['sha256'],
            'observed_apk_identity':'not present in p73-fatal receipt; cohort-key comparison only',
            'eligible':True,'exact_identity_eligible':False,
            'observed_wall':observed,'caught_first_exception':o['first_exception'],'fatal':o['fatal'],
            'pid':o['pid'],'exit_line':o['exit_line'],'v2_first':pred['v2_first'],
            'v3_first':pred['predicted_first'],'v2_first_hit':pred['v2_first']==observed,
            'v3_first_hit':matched(pred['walls'][0],observed),
            'v3_any_candidate_hit':any(matched(w,observed) for w in pred['walls']),
            'reason':'Retrospective, rules informed by this cohort; missing observed APK hash prevents exact-identity scoring.',
            'evidence':str(P75),'evidence_sha256':sha(P75)})
    p75={'kind':'retrospective conditional cohort agreement; not prospective accuracy',
        'observed_counts':dict(collections.Counter(r['observed_wall'] for r in rows)),
        'metrics':{'v2_first':ratio(rows,lambda r:r['v2_first_hit']),
                   'v3_first':ratio(rows,lambda r:r['v3_first_hit']),
                   'v3_any_candidate':ratio(rows,lambda r:r['v3_any_candidate_hit']),
                   'exact_identity_first':ratio([],lambda r:False)},'rows':rows}
    if not (P78/'results.json').exists():
        return {'p75':p75,'p78':{'status':'pending','metrics':{},'rows':[]},'new_observations_used_to_generate_static_predictions':False}
    frozen=read(P78/'predictions-before.json');result=read(P78/'results.json');frozen_by={r['key']:r for r in frozen['predictions']}
    baseline=OUT/'evidence/v2-predictions.csv'
    if sha(baseline)!=frozen['source_sha256']:raise ValueError('task 78 frozen prediction SHA mismatch')
    rows78=[]
    for o in result['apps']:
        k=o['key'];prior=frozen_by[k];observed=fatal_wall((o.get('first_fatal') or {}).get('text'))
        exact_apk=k in apps and apps[k]['sha256']==o['apk_sha256']
        eligible=prior['prediction']!='unknown' and exact_apk
        evidence=[]
        prerequisite=False
        if eligible and prior['prediction']=='service:jobscheduler':
            # Do not infer causality merely from WorkManager's final message.
            # Preserve task 78's additional same-APK nr2.a callsite + caught-stack proof.
            cp=read(P78/'ooni-callsite.json');bc=P78/'ooni-nr2-bytecode.txt';log=P78/'evidence/ooniprobe/hilog-excerpt.txt'
            prerequisite=(cp['apk_sha256']==o['apk_sha256'] and any(c['service']=='jobscheduler' and c['method'].startswith('nr2.a:') for c in cp['calls'])
                          and 'getSystemService' in bc.read_text() and 'nr2.a' in log.read_text())
            evidence=[{'path':str(p),'sha256':sha(p)} for p in [P78/'ooni-callsite.json',bc,log]]
        rows78.append({'task':78,'app':k,'eligible':eligible,'apk_sha256':o['apk_sha256'],
            'exact_apk_match':exact_apk,'profile_match':'component-conditional: frozen v3+r8b versus observed v3a+r8b',
            'exact_generation_eligible':False,'frozen_prediction':prior['prediction'],'observed_wall':observed,
            'strict_fatal_first_hit':eligible and prior['prediction']==observed,
            'evidenced_prerequisite_hit':eligible and (prerequisite or prior['prediction']==observed),
            'prerequisite_evidence':evidence,'fatal':o.get('first_fatal'),
            'reason':prior.get('reason','Frozen OONI service row; actual final fatal differs from its prerequisite.')})
    eligible=[r for r in rows78 if r['eligible']]
    p78={'kind':'original frozen prospective rows only; no post-run filling','status':'available',
        'frozen_source_sha256':frozen['source_sha256'],'frozen_at':frozen['frozen_at'],
        'receipt_sha256':sha(P78/'results.json'),'source':str(P78/'results.json'),
        'metrics':{'strict_fatal_first':ratio(eligible,lambda r:r['strict_fatal_first_hit']),
                   'evidenced_prerequisite':ratio(eligible,lambda r:r['evidenced_prerequisite_hit']),
                   'exact_generation_first':ratio([],lambda r:False)},
        'prediction_coverage':{'covered':len(eligible),'total':len(rows78)},'rows':rows78}
    return {'p75':p75,'p78':p78,'new_observations_used_to_generate_static_predictions':False,
            'rules_informed_by_observations':True,'note':'v3 evaluation is retrospective; only task78 frozen v2 rows are prospective.'}

def main():
    predictions,ranking=predict() # frozen to disk before the observation join
    b=backtest(predictions);dump(OUT/'backtest.json',b)
    flat=b['p75']['rows']+b['p78']['rows']
    csvwrite(OUT/'backtest.csv',flat,['task','app','profile','apk_sha256','eligible','observed_wall','v2_first','v3_first',
        'v2_first_hit','v3_first_hit','v3_any_candidate_hit','frozen_prediction','strict_fatal_first_hit','evidenced_prerequisite_hit','reason'])
    csvwrite(OUT/'coverage-gaps.csv',[r for r in b['p78']['rows'] if not r['eligible']],
        ['app','apk_sha256','frozen_prediction','exact_apk_match','reason'])
    # Keep historical metrics explicitly labelled instead of overwriting their meaning.
    previous=read(HERE/'results.json');legacy=previous.get('legacy_backtest',previous.get('backtest'))
    jni=read(OUT/'jni-summary.json')
    results={'task':72,'version':3,'offline':True,'scope':'Timeboxed source attribution and static risk follow-up; no runtime repairs or board operations',
        'jni':{'counts':{g:r['counts'] for g,r in jni.items()},'summary':jni,
               'known_answers':previous['jni']['known_answers'],'known_answer_count':6,
               'approved_exceptions':len(read(HERE/'jni-allowlist.json')['exceptions']),
               'allowlist_sha256':sha(HERE/'jni-allowlist.json'),'method_inventory':'jni-results.json.gz'},
        'services':previous['services'],'predictions':{'version':3,'rows':len(predictions),'ranking':ranking,
            'stub_ok_ranking':[r for r in ranking if r['stub_ok']],
            'needs_real_ranking':[r for r in ranking if r['needs_real']]},
        'legacy_backtest':legacy,'backtest':b,
        'backtest_scope':'Current #75/#78 metrics are backtest; legacy_backtest retains the prior v2 5/7 historical cohort.',
        'build':previous.get('build'),'limitations':[
            'Source attribution and ELF table presence do not prove registration executes or resolves in the effective namespace.',
            '335 unknown methods per package remain after approved exceptions; gate stays failing.',
            'Risk candidates are conditional; no successful bind, load, install or frame is claimed.',
            'Task75 receipt omits APK hashes, so its 12-key cohort metrics are conditional; exact-identity denominator is zero.',
            'Task78 service comparison is conditional on v3/v3a component compatibility; 12 absent APK predictions remain excluded.'],
        'screenshots':'unknown: offline, no captured/process table collected','commit':'outer-lane-to-commit'}
    dump(OUT/'results.json',results);dump(HERE/'results.json',results)
    print(json.dumps({k:v['metrics'] for k,v in b.items() if k in ['p75','p78']},indent=2))
if __name__=='__main__':main()
