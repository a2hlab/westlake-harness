#!/usr/bin/env python3
"""Explicitly post-hoc v2 family calibration. Never rewrites a forecast."""
import collections,csv,gzip,hashlib,json,re,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
B10=ROOT/'benchmark/2026-09-29-static-wall-prediction';sys.path.insert(0,str(B10))
from rules_feedback_v2 import FAMILIES
V2=ROOT/'benchmark/2026-09-30-v3c-r17j-prospective';BACK=V2/'backtests/v2-5ea'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,indent=2,ensure_ascii=False)+'\n')
def table(p,rows):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader()
        for r in rows:w.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else v for k,v in r.items()})
def observation(key,o,scan):
    path=Path(o['source_run'])/key/'hilog.txt'
    ev=BACK/('evidence-continuation-c' if '-5ea-c/' in str(path) else 'evidence')/(key+'.json')
    if not path.exists() or not ev.exists():return {'key':key,'status':'unknown','reason':'No selected target-PID log'}
    pids=set(load(ev).get('target_pids',[]));all_lines=path.read_text(errors='replace').splitlines();rows=[]
    for n,line in enumerate(all_lines,1):
        m=re.match(r'\S+ \S+\s+(\d+)\s+(\d+)\s+',line)
        if m and m[1] in pids:rows.append({'line':n,'pid':m[1],'tid':m[2],'text':line})
    activities={a['target'] or a['class'] for a in scan.get('activities',[])};launchers=set(scan.get('launchers',[]));starts=[];pending={};aliases=[];snips=[]
    for x in rows:
        l=x['text'];ident=(x['pid'],x['tid'])
        a=re.search(r'\[B5-ALIAS\] alias=(\S+) target=(\S+)',l)
        if a:aliases.append({**x,'activity':(a[2] if a[2]!='null' else a[1]).replace('.','/')})
        m=re.search(r'\bStartAbility: bundle=([^,]+), ability=([^,]+)',l)
        if m:pending[ident]={**x,'target':m[2].replace('.','/')}
        ret=re.search(r'StartAbility returned (-?\d+)',l)
        if ret and ident in pending:
            start=pending.pop(ident)
            if start['target'] in activities-launchers:starts.append({**start,'return':int(ret[1]),'return_line':x['line']})
        if any(t in l for t in ['Sun provider not found','ClassNotFoundException: com.android.org.conscrypt.OpenSSLProvider','BootClassLoader','Providers.getSunProvider','ManifestEntryVerifier','java.util.ServiceLoader','J_invokeStaticMain_main_threw','EGL_NO_SURFACE','EGL_BAD_ALLOC','eglCreateWindowSurface','[B5-ALIAS]']):snips.append(x)
    provider=[x for x in rows if 'ClassNotFoundException: com.android.org.conscrypt.OpenSSLProvider' in x['text']]
    mainwall=False
    for i,x in enumerate(rows):
        if 'J_invokeStaticMain_main_threw' in x['text'] and any('Sun provider not found' in y['text'] or 'ClassNotFoundException: com.android.org.conscrypt.OpenSSLProvider' in y['text'] for y in rows[i:i+130] if y['pid']==x['pid'] and y['tid']==x['tid']):mainwall=True
    egl=[x for x in rows if 'EGL_NO_SURFACE' in x['text']]
    result={'key':key,'status':'observed','source':str(path),'sha256':sha(path),'target_pids':sorted(pids),'secondary_starts':starts,
            'accepted_secondary_targets':sorted({x['target'] for x in starts if x['return']==0}),
            'entry_aliases':aliases,'selected_entry':aliases[0]['activity'] if aliases else 'unknown',
            'provider_failure_observed':bool(provider),'provider_main_fatal_chain':mainwall,
            'provider_first_failure_line':provider[0]['line'] if provider else None,
            'egl_no_surface_observed':bool(egl),'same_native_window_recreation':'unknown-in-v2-unless-lifetime-logged',
            'snippets':snips,'absence_policy':'No matching log is unknown, not a proven negative; failed init can be tolerated.'}
    dump(HERE/'evidence/observed'/f'{key}.json',result);return result

def main():
    prior=load(V2/'freezes/v2/predictions.json');outs={r['key']:r for r in load(BACK/'results.json')['rows']};obs={r['key']:r for r in load(BACK/'observations.json')}
    matrix=[];predictions=[];calibration=[];scans={};observed={}
    for p in prior:
        key=p['key'];scan=json.load(gzip.open(HERE/'evidence'/f'{key}.json.gz','rt'));scans[key]=scan
        o=observation(key,obs[key],scan) if key in obs else {'status':'unknown'};observed[key]=o
        act=scan['activity'];pro=scan['provider'];eligible=outs[key]['eligible']
        strong=[x for x in act if x['verdict']=='explicit-startup-target'];provstrong=[x for x in pro if x['reason']!='classloader-resource-candidate'];provreach=[x for x in provstrong if x['startup_reachable']=='conditional-static']
        statuses={'authorized-secondary-activity':'conditional-startup-target' if strong else 'callback-or-target-candidate' if act else 'unknown-no-static-witness',
                  'boot-conscrypt-fallback':'conditional-startup-provider-requirement' if provreach else 'latent-provider-requirement' if provstrong else 'resource-only-candidate' if pro else 'unknown-no-static-witness',
                  'egl-window-recreation':'runtime-only'}
        for fam in FAMILIES:
            xs=act if fam==FAMILIES[0] else pro if fam==FAMILIES[1] else []
            risk=act if fam==FAMILIES[0] else provstrong if fam==FAMILIES[1] else []
            matrix.append({'key':key,'apk_sha256':p['apk_sha256'],'family':fam,'status':statuses[fam] if scan['status']=='scanned' else 'unknown-input',
                           'static_hit':bool(risk) if fam!=FAMILIES[2] and scan['status']=='scanned' else 'unknown','references':len(xs),'risk_references':len(risk),
                           'startup_references':sum(x.get('startup_reachable')=='conditional-static' for x in risk),
                           'all_startup_references':sum(x.get('startup_reachable')=='conditional-static' for x in xs),
                           'policy':'needs_real','stub_ok':False,'needs_real':True,
                           'effect':'grant can expose a successor Activity; grant is present in v2' if fam==FAMILIES[0] else 'boot providers missing if JAR verification invokes fallback' if fam==FAMILIES[1] else 'native-window lifetime requires runtime evidence',
                           'startup_roots':sorted({x['root']['method'] for x in xs if x.get('root')}),
                           'explicit_destinations':sorted({t for x in xs for t in x.get('non_launcher_targets',[])}),
                           'candidate_destinations':sorted({t for x in xs for t in x.get('class_hints',[])}),
                           'evidence':f'evidence/{key}.json.gz','proves_first_wall':False})
        known_targets=set(o.get('accepted_secondary_targets',[]));explicit={t for x in act for t in x['non_launcher_targets']};hints={t for x in act for t in x['class_hints']}
        startup_targets={t for x in strong for t in x['non_launcher_targets']}
        provider_hit=bool(provstrong);provider_obs=o.get('provider_failure_observed',False)
        calibration.append({'key':key,'v2_eligible':eligible,'scan_status':scan['status'],'frozen_forecast':p['forecast'],'v2_observed':outs[key]['observed'],
            'secondary_static_hit':bool(act),'secondary_explicit_startup':bool(strong),'secondary_observed_targets':sorted(known_targets),
            'secondary_explicit_target_matches':sorted(known_targets&explicit),'secondary_hint_target_matches':sorted(known_targets&hints),
            'secondary_startup_target_matches':sorted(known_targets&startup_targets),
            'selected_entry':o.get('selected_entry','unknown'),'selected_entry_differs_from_manifest_launcher':o.get('selected_entry') not in scan.get('launchers',[]) if o.get('entry_aliases') else 'unknown',
            'grant_causal_effect':'not isolated; installer entry selection and runtime repairs changed together',
            'provider_static_hit':provider_hit,'provider_static_startup':bool(provreach),'provider_observed_failure':provider_obs,
            'provider_any_resource_candidate':bool(pro),
            'provider_main_fatal_chain':o.get('provider_main_fatal_chain','unknown'),'egl_observed_no_surface':o.get('egl_no_surface_observed','unknown'),
            'egl_static_verdict':'runtime-only','log_evidence':f'evidence/observed/{key}.json' if o.get('status')=='observed' else 'unknown',
            'calibration':'post-hoc; no prospective credit'})
        candidates=[]
        if provreach:candidates.append('boot-conscrypt-fallback')
        if act:candidates.append('authorized-secondary-activity')
        if provstrong and not provreach:candidates.append('boot-conscrypt-fallback (reachability unknown)')
        predictions.append({'key':key,'frozen_forecast_unchanged':p['forecast'],'v2_observed':outs[key]['observed'],
            'prior_wall':p['prior_wall'],'posthoc_requirement_order':candidates,'runtime_only_requirement':'egl-window-recreation',
            'observed_egl_alert':o.get('egl_no_surface_observed','unknown'),'new_expected_lit':'unknown',
            'reason':'Requirements ordered by bounded startup evidence, not proven execution order; grant may expose a successor wall, provider init failure may be tolerated, and EGL needs runtime lifetime tracing.',
            'static_evidence':f'evidence/{key}.json.gz','outcome_evidence':f'evidence/observed/{key}.json','basis':'v2 post-hoc calibration'})
    positives=[r for r in calibration if r['v2_eligible'] and r['provider_observed_failure']]
    secondary=[r for r in calibration if r['v2_eligible'] and r['secondary_observed_targets']]
    results={'analysis':'post-hoc','keys':len(prior),'matrix_rows':len(matrix),'scanned':sum(s['status']=='scanned' for s in scans.values()),
        'prior_v2_score':{'exact_correct':30,'denominator':45,'accuracy':30/45,'always_unchanged_baseline':32/45,'unchanged':True},
        'provider':{'observed_failure_keys':[r['key'] for r in positives],'positive_witness_recall':[sum(r['provider_static_hit'] for r in positives),len(positives)],
                    'including_weak_resource_candidates_recall':[sum(r['provider_any_resource_candidate'] for r in positives),len(positives)],
                    'startup_positive_witness_recall':[sum(r['provider_static_startup'] for r in positives),len(positives)],
                    'static_alerts':sum(r['provider_static_hit'] for r in calibration),'precision':'unknown: no-log is not a negative; candidate is a requirement, not a promised fatal wall',
                    'observed_main_fatal_keys':[r['key'] for r in positives if r['provider_main_fatal_chain']]},
        'secondary':{'observed_accepted_transition_keys':[r['key'] for r in secondary],
                     'explicit_destination_recall':[sum(bool(r['secondary_explicit_target_matches']) for r in secondary),len(secondary)],
                     'startup_destination_recall':[sum(bool(r['secondary_startup_target_matches']) for r in secondary),len(secondary)],
                     'candidate_destination_recall':[sum(bool(r['secondary_explicit_target_matches'] or r['secondary_hint_target_matches']) for r in secondary),len(secondary)],
                     'static_alerts':sum(r['secondary_static_hit'] for r in calibration),'precision':'unknown: an unexecuted conditional branch is not a false API reference'},
        'egl':{'static':'runtime-only','observed_no_surface_keys':[r['key'] for r in calibration if r['v2_eligible'] and r['egl_observed_no_surface'] is True],
               'same_window_causality':'requires native-window generation/create/destroy experiment; no static detection credit'},
        'visual_authority':'Accepted v2 review; outer additionally signed Thunderbird/K9 database upgrade pages as lit. Cumulative campaign count is not this calibration denominator.',
        'remaining_misses':{'fd-tusky':'Only a generic Class.getResourceAsStream candidate in org.conscrypt.Conscrypt.<clinit>; v2 stack proves JAR verification but static resource provenance is unresolved. Not promoted to strong hit using that outcome.',
                            'anki':'Entry IntentHandler.a(Intent) delegates a supplied Intent; target dataflow and callback reachability are unresolved, although DeckPicker is observed.'},
        'calibration_known_answers':{k:next(r for r in calibration if r['key']==k) for k in ['fd-filemanager','aegis','fd-android','fd-k9','fd-AppManager','fd-droidify','newpipe','fd-catima','fd-com-amaze-filemanager','antennapod','noice','wikipedia']}}
    for name,rows in [('matrix',matrix),('predictions',predictions),('calibration',calibration)]:dump(HERE/(name+'.json'),rows);table(HERE/(name+'.csv'),rows)
    ranking=[]
    for family in FAMILIES:
        group=[r for r in matrix if r['family']==family]
        ranking.append({'family':family,'policy':'needs_real','startup_app_count':sum(r['startup_references']>0 for r in group),
                        'all_reference_app_count':sum(r['references']>0 for r in group),'risk_reference_app_count':sum(r['risk_references']>0 for r in group),'reference_count':sum(r['references'] for r in group),
                        'runtime_only':family==FAMILIES[2],'interpretation':'Conditional requirement exposure, not number of confirmed first walls'})
    ranking.sort(key=lambda r:(r['runtime_only'],-r['startup_app_count'],-r['all_reference_app_count']))
    table(HERE/'wall-ranking.csv',ranking)
    dump(HERE/'results.json',results)
    print(json.dumps({k:v for k,v in results.items() if k!='calibration_known_answers'},indent=2))
if __name__=='__main__':main()
