#!/usr/bin/env python3
"""Descriptive cross-profile evidence only; no prospective accuracy or UI inference."""
import argparse,collections,csv,datetime,hashlib,html,json,re,shutil,sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
sys.path.insert(0,str(HERE.parent/'2026-09-30-r17op-execution-revision'))
import profile_audit as pa
from audit_run import record_facts
OLD=HERE.parent/'2026-09-30-v3c-r17j-prospective/backtests/v2-5ea'
DEFAULT_RUN=Path('/Users/zhaoyue/orca/workspaces/westlake-harness/benchmark/2026-09-30-r17p-61b-sweep/runs/r17p-all-61b/61b0657200000000000000000324012c')
PERMS={'background':'ohos.permission.START_ABILITIES_FROM_BACKGROUND','internet':'ohos.permission.INTERNET'}
PID=re.compile(r'^\S+ \S+\s+(\d+)\s+\d+ ')
TRACE=re.compile(r'\[([0-9a-f]{12,})(?:,|\])')
CLUE=re.compile(r'main_threw|FATAL EXCEPTION|Caused by:|Unable to (?:start|resume)|dlopen_ns failed|Error relocating|Error loading shared library|No implementation found|StartAbility returned|EGL_NO_SURFACE|SIGABRT|SIGSEGV|\b(?:bind|attach) (?:FAILED|failed)|startActivity.*(?:component|cmp=)|\[B8-.*(?:FAIL|fail)',re.I)

def dump(path,data):path.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def permission_state(path,name):
    if not path.exists():return 'unknown'
    try:
        text=path.read_text();b=json.loads(text[text.index('{'):]);names=b['reqPermissions'];states=b['reqPermissionStates']
        if not isinstance(names,list) or not isinstance(states,list):return 'unknown'
        if name not in names:return 'absent'
        i=names.index(name)
        if i>=len(states):return 'unknown'
        return 'granted' if states[i]==0 else 'not_granted'
    except (ValueError,KeyError,TypeError):return 'unknown'

def extract(record):
    r=json.loads(record.read_text());log=record.parent/'hilog.txt'
    result={'key':r['key'],'record':str(record),'record_sha256':sha(record),'log':str(log),'log_sha256':None,'target_pids':[],'clues':[],'startability_returns':[],'launch_requests':[],'background_trace_evidence':[],'background_denials':[],'scope':'exact bundle PID anchor; system denial additionally requires matching app-requested target and exact trace ID'}
    if not log.exists():return result
    result['log_sha256']=sha(log);lines=log.read_text(errors='replace').splitlines();pids=set()
    for line in lines:
        if 'nativeOnScheduleLaunchApplication ENTRY bundle='+str(r.get('package'))+' ' in line:
            m=PID.match(line)
            if m:pids.add(m[1])
    result['target_pids']=sorted(map(int,pids))
    targets=set()
    for n,line in enumerate(lines,1):
        m=PID.match(line)
        if m and m[1] in pids:
            call=re.search(r'nativeStartAbility: bundle=([^,]+), ability=([^,]+)',line)
            if call and call[1]==r.get('package'):
                targets.add(call[2]);result['launch_requests'].append({'line':n,'pid':int(m[1]),'target':call[2],'text':line})
    traces=set()
    for n,line in enumerate(lines,1):
        trace=TRACE.search(line)
        if trace and 'NotifySCBPendingActivation' in line and any(re.search(r'target:\s*'+re.escape(t)+r'(?:requestId|\s|$)',line) for t in targets):
            traces.add(trace[1]);result['background_trace_evidence'].append({'line':n,'trace':trace[1],'text':line})
    for n,line in enumerate(lines,1):
        trace=TRACE.search(line)
        if trace and trace[1] in traces and ('DisallowActivationFromPendingBackground' in line or ('permission_verification' in line and 'BACKGROUND' in line)):
            item={'line':n,'trace':trace[1],'text':line};result['background_trace_evidence'].append(item)
            if 'no permission to start ability from Background' in line:result['background_denials'].append(item)
    for n,line in enumerate(lines,1):
        m=PID.match(line)
        if not m or m[1] not in pids or not CLUE.search(line):continue
        result['clues'].append({'line':n,'pid':int(m[1]),'text':line})
        code=re.search(r'StartAbility returned\s+(-?\d+)',line)
        if code:result['startability_returns'].append({'code':int(code[1]),'line':n,'pid':int(m[1])})
    return result

def coverage(run,keys):
    path=run/'summary.json'
    if not path.exists():return {'complete':False,'reason':'summary_missing','terminal_keys':[]}
    s=json.loads(path.read_text());terminal=[r['key'] for r in s.get('records',[])]
    missing=sorted(set(keys)-set(terminal));unexpected=sorted(set(terminal)-set(keys))
    repeated=sorted(k for k,n in collections.Counter(terminal).items() if n>1)
    reasons=[]
    if missing:reasons.append('missing_terminal_records')
    if unexpected:reasons.append('unexpected_keys')
    if repeated:reasons.append('duplicate_terminal_keys')
    if s.get('not_run') or s.get('batch_error'):reasons.append('batch_incomplete')
    if not (run/'facts.txt').exists():reasons.append('facts_missing')
    for k in terminal:
        p=run/k/'record.json'
        if not p.exists():reasons.append('record_missing:'+k)
        elif json.loads(p.read_text())!=next(r for r in s['records'] if r['key']==k):reasons.append('summary_record_disagrees:'+k)
    return {'complete':not reasons,'reason':reasons,'terminal_keys':terminal,'missing':missing,'unexpected':unexpected,'duplicates':repeated,'summary_sha256':sha(path)}

def classify_installer(row):
    if row['apk_same'] is not True:return 'identity_unknown_or_changed'
    if row['launcher_changed'] is True:return 'launcher_selection_changed; outcome_confounded'
    if row['new_background']=='absent' and row['old_background']=='granted':
        if row.get('new_background_denials'):return 'background_grant_lost_and_trace_linked_WMS_denial; UI_effect_pending'
        if any(c!=0 for c in row['new_startability_codes']):return 'background_grant_lost_and_nonzero_dispatch; causal_link_unproven'
        return 'background_grant_lost; impact_unproven'
    if row['new_internet']=='absent' and row['old_internet']=='granted':return 'internet_grant_lost; impact_unproven'
    return 'no_mechanism_difference_demonstrated_or_unknown'

def comparable_identity(row,old):
    # A prelaunch validation failure may still record the expected APK hash.
    return bool(row['apk_same'] is True and row.get('new_clicked') is True and
        old.get('clicked') is True and not row.get('new_record_errors') and not old.get('errors'))

def count_records(facts):
    counts={'records':len(facts),'captured':sum(f['captured_count'] for f in facts),'captures_verified':sum(s['valid'] for f in facts for s in f['captures'])}
    for stage in ('t5','t20'):
        measured=[f['processes'][stage] for f in facts if f['processes'][stage] is not None]
        counts[stage]={'measured_apps':len(measured),'unknown_apps':len(facts)-len(measured),'alive_apps':sum(p['alive'] for p in measured),'app_processes':sum(len(p['app_processes']) for p in measured),'same_uid_helpers_excluded':sum(len(p['same_uid_helpers']) for p in measured)}
    return counts

def build(run,out,partial=False,installer_readback=None):
    profiles,package=pa.context();preds=json.loads((pa.FREEZE/'predictions.json').read_text());keys=[p['key'] for p in preds]
    if sha(OLD/'results.json')!=sha(pa.FREEZE/'evidence/v2-results.json'):
        raise ValueError('accepted baseline differs from v3-pinned v2 evidence')
    cov=coverage(run,keys)
    if not partial and not cov['complete']:raise ValueError('refuse final incomplete sweep: '+str(cov))
    if out.exists():raise ValueError('output exists; use a fresh snapshot path')
    out.mkdir(parents=True)
    profile=pa.report([run],profiles,package,installer_readback)
    if profile['runs'][0]['same_profile_score_eligible']:raise ValueError('unexpected matching profile; reassess declared descriptive scope')
    dump(out/'profile-strata.json',profile)
    baseline=json.loads((run/'baseline.json').read_text());run_audit={'boot_id':baseline.get('boot_id'),'board':run.name,'runtime_fingerprint':baseline.get('runtime_fingerprint')}
    old_result=json.loads((OLD/'results.json').read_text());oldfacts={f['key']:f for f in old_result['record_facts']};oldobs={o['key']:o for o in old_result['checked_observations']}
    data=[];facts=[];evidence=[]
    old_csv={r['key']:r for r in csv.DictReader((OLD/'backtest.csv').open())}
    for key in keys:
        rec=run/key/'record.json';old=oldfacts[key];old_record=OLD/'source-records'/key/'record.json';oldraw=json.loads(old_record.read_text());ob=oldobs[key]
        if sha(old_record)!=old['record_sha256']:raise ValueError('baseline record changed: '+key)
        row={'key':key,'new_record_status':'pending','new_lit':'pending_outer_review','old_lit':ob['lit'],'old_observed':old_csv[key]['observed'],'old_wall':ob.get('observed_wall'), 'old_launcher':old['actual_launcher'],'new_launcher':None,'launcher_changed':None,'apk_same':None,'new_captured':None,'new_t5_alive':None,'new_t20_alive':None,'old_t5_alive':old['processes']['t5']['alive'] if old['processes']['t5'] else None,'old_t20_alive':old['processes']['t20']['alive'] if old['processes']['t20'] else None,'new_startability_codes':[],'old_startability_codes':[],'new_background_denials':[],'old_background_denials':[],'installer_effect_causal':'unknown; board/JAR/installer/protocol/app state change together','new_record':str(rec),'old_record':str(old_record),'old_source_run':ob.get('source_run'),'new_screenshots':[],'old_screenshot':ob.get('screenshot_evidence'),'same_profile_score_eligible':False}
        for label,name in PERMS.items():
            row['new_'+label]=permission_state(run/key/'bundle.txt',name)
            row['old_'+label]=permission_state(old_record.parent/'bundle.txt',name)
        # Pull accepted old source logs; do not rely on a grep of unrelated processes.
        old_source=Path(ob['source_record']) if ob.get('source_record') else Path(ob['source_run'])/key/'record.json'
        if old_source.exists():
            old_clues=extract(old_source);row['old_startability_codes']=[x['code'] for x in old_clues['startability_returns']];row['old_background_denials']=old_clues['background_denials'];evidence.append(dict(side='5ea_v2',**old_clues))
        if rec.exists():
            raw=json.loads(rec.read_text());f=record_facts(rec,run_audit);facts.append(f);clues=extract(rec);evidence.append(dict(side='61b_r17p',**clues))
            row.update(new_record_status=raw['status'],new_launcher=f['actual_launcher'],new_apk_sha256=f['apk_sha256'],old_apk_sha256=old['apk_sha256'],apk_same=bool(f['apk_sha256'] and f['apk_sha256']==old['apk_sha256']),new_clicked=f['clicked'],new_clicked_at=f['clicked_at'],new_record_errors=f['errors'],new_captured=f['captured_count'],new_captures_verified=sum(s['valid'] for s in f['captures']),new_startability_codes=[x['code'] for x in clues['startability_returns']],new_record_error=f['record_error'],new_target_pids=clues['target_pids'],new_screenshots=f['captures'],new_log_sha256=clues['log_sha256'],new_clue_count=len(clues['clues']))
            if f['actual_launcher'] and old['actual_launcher']:row['launcher_changed']=f['actual_launcher']!=old['actual_launcher']
            for stage in ('t5','t20'):row['new_'+stage+'_alive']=f['processes'][stage]['alive'] if f['processes'][stage] else None
            row['new_background_denials']=clues['background_denials']
            row['new_first_observed_clue']=clues['clues'][0] if clues['clues'] else None
            row['first_clue_policy']='chronological observed diagnostic, may be tolerated; not adjudicated first blocking wall'
            if not raw.get('clicked'):row['new_lit']='not_observed_prelaunch'
        row['recorded_apk_sha_same']=row['apk_same']
        row['comparison_identity_verified']=comparable_identity(row,old)
        if not row['comparison_identity_verified']:row['apk_same']=None
        row['installer_mechanism']=classify_installer(row);data.append(row)
    counts=count_records(facts)
    mechanisms={'background_grant_lost_keys':[r['key'] for r in data if r['apk_same'] is True and r['old_background']=='granted' and r['new_background']=='absent'],
        'internet_grant_lost_keys':[r['key'] for r in data if r['apk_same'] is True and r['old_internet']=='granted' and r['new_internet']=='absent'],
        'launcher_changed_keys':[r['key'] for r in data if r['apk_same'] is True and r['launcher_changed'] is True],
        'trace_linked_background_denial_keys':[r['key'] for r in data if r['new_background_denials']],
        'zero_return_and_async_denial_keys':[r['key'] for r in data if r['new_background_denials'] and 0 in r['new_startability_codes']],
        'causal_lighting_effect':'unknown; needs controlled installer-only follow-up plus screenshot review'}
    result={'kind':'cross-profile descriptive comparison','created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'run':str(run),'complete':cov['complete'],'coverage':cov,'profile_classification':profile['runs'][0]['classification'],'same_profile_accuracy':None,'same_profile_denominator':0,'visual_status':'pending_outer_review','counts':counts,'rows':data,'record_facts':facts,'baseline_source':str(OLD),'baseline_results_sha256':sha(OLD/'results.json'),'baseline_reviewed_sha256':sha(OLD/'reviewed.tsv'),'frozen_receipt_sha256':sha(pa.FREEZE/'freeze.json'),'confounders':['board','JAR r17j -> r17p','installer pair','batch protocol and app state; no randomized intervention'],'runtime_limit':'Run-start fingerprint only; no resident-map proof or permission-to-outcome causal attribution.'}
    result['installer_mechanisms']=mechanisms
    dump(out/'results.json',result);dump(out/'log-evidence.json',evidence)
    fields=list(dict.fromkeys(k for row in data for k in row))
    with (out/'per-key.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(dict,list)) else 'unknown' if v is None else v for k,v in row.items()} for row in data)
    installer_fields=['key','apk_same','old_background','new_background','old_internet','new_internet','old_launcher','new_launcher','launcher_changed','old_startability_codes','new_startability_codes','old_background_denials','new_background_denials','old_lit','new_lit','installer_mechanism','installer_effect_causal']
    with (out/'installer-comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=installer_fields);w.writeheader();w.writerows({k:json.dumps(row[k]) if isinstance(row[k],list) else 'unknown' if row[k] is None else row[k] for k in installer_fields} for row in data)
    sources=out/'source-records';sources.mkdir();identity=out/'run-identity';identity.mkdir()
    for name in ('facts.txt','runtime-fingerprint.txt','baseline.json','plan.json','summary.json','installer-readback.txt'):
        if (run/name).exists():shutil.copyfile(run/name,identity/name)
    for f in facts:
        rec=Path(f['record']);dest=sources/f['key'];dest.mkdir()
        for name in ('record.json','processes-t5.txt','processes-t20.txt','bundle.txt'):
            if (rec.parent/name).exists():shutil.copyfile(rec.parent/name,dest/name)
    page=['<!doctype html><meta charset="utf-8"><title>61b r17p: outer review pending</title><style>img{max-height:400px;max-width:31%}section{border-top:1px solid;padding:10px}</style><h1>61b r17p / 5ea v2: descriptive review, no same-profile score</h1>']
    for row in data:
        page.append('<section><h2>'+html.escape(row['key'])+'</h2><p>'+html.escape('61b: '+row['new_record_status']+'; lighting pending outer review. 5ea prior: '+str(row['old_lit']))+'</p>')
        for shot in row['new_screenshots']:
            if shot['valid']:page.append('<a href="'+html.escape(Path(shot['path']).as_uri())+'"><img src="'+html.escape(Path(shot['path']).as_uri())+'" alt="61b '+html.escape(str(shot['scheduled_seconds']))+'s"></a>')
        if row['old_screenshot']:page.append('<a href="'+html.escape(Path(row['old_screenshot']).as_uri())+'">5ea accepted comparison screenshot</a>')
        page.append('</section>')
    (out/'review.html').write_text('\n'.join(page))
    dump(out/'outer-review-template.json',[{'key':r['key'],'lit':'unknown','reviewer':None,'screenshot_sha256':None,'note':''} for r in data])
    print(json.dumps({'complete':cov['complete'],'counts':counts,'profile':result['profile_classification']},indent=2))
    return result

def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,default=DEFAULT_RUN);p.add_argument('--out',type=Path,required=True);p.add_argument('--partial',action='store_true');p.add_argument('--installer-readback',type=Path);a=p.parse_args();build(a.run,a.out,a.partial,a.installer_readback)
if __name__=='__main__':main()
